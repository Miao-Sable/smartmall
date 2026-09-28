"""扫码：保存扫描记录、历史查询（每次扫码自动生成分析结果）"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.scan import AnalysisResult, ScanHistory
from app.models.user import User
from app.schemas.scan import AnalysisOut, ScanCreate, ScanOut
from app.services.matching import analyze_product, light_label, load_user_allergens, load_user_diets
from app.services.mock_data import find_product_by_barcode

router = APIRouter()


def _to_scan_out(scan: ScanHistory, result: Optional[AnalysisResult]) -> ScanOut:
    analysis = None
    if result is not None:
        analysis = AnalysisOut(
            score=result.score,
            level=result.level,
            traffic_light=result.traffic_light or "green",
            traffic_label=light_label(result.traffic_light or "green"),
            allergen_hits=result.allergen_hits or [],
            reasons=result.reasons or [],
            recommended=result.recommended,
        )
    return ScanOut(
        id=scan.id,
        barcode=scan.barcode,
        product_id=scan.product_id,
        product_name=scan.product_name,
        score=scan.score,
        level=scan.level,
        has_allergen=scan.has_allergen,
        source=scan.source,
        created_at=scan.created_at,
        analysis=analysis,
    )


@router.post("", response_model=ScanOut)
def create_scan(
    data: ScanCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ScanOut:
    product = find_product_by_barcode(data.barcode)
    if product is None:
        raise HTTPException(status_code=404, detail="暂无该商品数据，请尝试扫描其他条码")

    analysis = analyze_product(
        product,
        load_user_allergens(session, user.id),
        load_user_diets(session, user.id),
    )

    scan = ScanHistory(
        user_id=user.id,
        barcode=data.barcode,
        product_id=product["id"],
        product_name=product["name"],
        score=analysis["score"],
        level=analysis["level"],
        has_allergen=bool(analysis["allergen_hits"]),
        source=data.source,
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)

    result = AnalysisResult(
        scan_id=scan.id,
        allergen_hits=analysis["allergen_hits"],
        reasons=analysis["reasons"],
        score=analysis["score"],
        level=analysis["level"],
        traffic_light=analysis["traffic_light"],
        recommended=analysis["recommended"],
    )
    session.add(result)
    session.commit()

    return _to_scan_out(scan, result)


@router.get("/history", response_model=list[ScanOut])
def get_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ScanOut]:
    scans = session.exec(
        select(ScanHistory).where(ScanHistory.user_id == user.id).order_by(ScanHistory.created_at.desc()).limit(100)
    ).all()
    ids = [s.id for s in scans]
    results: dict[int, AnalysisResult] = {}
    if ids:
        for r in session.exec(select(AnalysisResult).where(AnalysisResult.scan_id.in_(ids))):
            results[r.scan_id] = r
    return [_to_scan_out(s, results.get(s.id)) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan_detail(
    scan_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ScanOut:
    scan = session.get(ScanHistory, scan_id)
    if scan is None or scan.user_id != user.id:
        raise HTTPException(status_code=404, detail="扫描记录不存在")
    result = session.exec(select(AnalysisResult).where(AnalysisResult.scan_id == scan.id)).first()
    return _to_scan_out(scan, result)
