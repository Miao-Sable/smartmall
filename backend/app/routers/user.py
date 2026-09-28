"""用户档案：查看 / 更新（过敏源与饮食偏好关联）"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.scan import AnalysisResult, ScanHistory
from app.models.user import User, UserAllergen, UserDiet, UserProfile
from app.schemas.user import UserProfileOut, UserProfileUpdate
from app.services.matching import analyze_product, load_user_allergens, load_user_diets
from app.services.mock_data import find_product_by_barcode

router = APIRouter()


def _recompute_scan_analysis(session: Session, user_id: int) -> None:
    """过敏源 / 饮食偏好变化后，重算该用户历史扫描的分析结果与过敏提醒"""
    allergens = load_user_allergens(session, user_id)
    diets = load_user_diets(session, user_id)
    scans = session.exec(select(ScanHistory).where(ScanHistory.user_id == user_id)).all()
    for scan in scans:
        product = find_product_by_barcode(scan.barcode)
        if product is None:
            continue
        analysis = analyze_product(product, allergens, diets)
        scan.score = analysis["score"]
        scan.level = analysis["level"]
        scan.has_allergen = bool(analysis["allergen_hits"])
        result = session.exec(select(AnalysisResult).where(AnalysisResult.scan_id == scan.id)).first()
        if result is None:
            result = AnalysisResult(scan_id=scan.id)
            session.add(result)
        result.allergen_hits = analysis["allergen_hits"]
        result.reasons = analysis["reasons"]
        result.score = analysis["score"]
        result.level = analysis["level"]
        result.traffic_light = analysis["traffic_light"]
        result.recommended = analysis["recommended"]


@router.get("/profile", response_model=UserProfileOut)
def get_profile(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> UserProfileOut:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    allergen_ids = [row.allergen_id for row in session.exec(select(UserAllergen).where(UserAllergen.user_id == user.id))]
    diet_ids = [row.diet_id for row in session.exec(select(UserDiet).where(UserDiet.user_id == user.id))]
    return UserProfileOut(
        user_id=user.id,
        email=user.email,
        nickname=profile.nickname if profile else "",
        gender=profile.gender if profile else "",
        birth_year=profile.birth_year if profile else None,
        allergen_ids=allergen_ids,
        diet_ids=diet_ids,
        onboarded=profile is not None,
    )


@router.put("/profile", response_model=UserProfileOut)
def update_profile(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserProfileOut:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)
    profile.nickname = data.nickname
    profile.gender = data.gender
    profile.birth_year = data.birth_year

    # 全量替换过敏源 / 饮食偏好关联
    for row in session.exec(select(UserAllergen).where(UserAllergen.user_id == user.id)):
        session.delete(row)
    for row in session.exec(select(UserDiet).where(UserDiet.user_id == user.id)):
        session.delete(row)
    for aid in data.allergen_ids:
        session.add(UserAllergen(user_id=user.id, allergen_id=aid))
    for did in data.diet_ids:
        session.add(UserDiet(user_id=user.id, diet_id=did))

    # 过敏源 / 饮食偏好变化后，重算历史扫描的分析结果与过敏提醒
    _recompute_scan_analysis(session, user.id)

    session.commit()
    return get_profile(user=user, session=session)
