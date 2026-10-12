"""首页仪表板统计"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.scan import ScanHistory
from app.models.user import Profile, User
from app.schemas.stats import DailyCount, StatsOverview

router = APIRouter()


@router.get("/overview", response_model=StatsOverview)
def overview(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    profile_id: int | None = None,
) -> StatsOverview:
    # 个人开发版数据量小，先全量读取；后续可改为 SQL 聚合
    query = select(ScanHistory).where(ScanHistory.user_id == user.id)
    if profile_id is not None:
        # 按档案筛选：校验档案归属该账号，不归属则 404
        profile = session.get(Profile, profile_id)
        if profile is None or profile.user_id != user.id:
            raise HTTPException(status_code=404, detail="档案不存在")
        query = query.where(ScanHistory.profile_id == profile_id)
    scans = session.exec(query).all()
    today = date.today()

    counts: dict[str, int] = {}
    for s in scans:
        d = s.created_at.date().isoformat()
        counts[d] = counts.get(d, 0) + 1

    days = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    recent_days = [DailyCount(date=d, count=counts.get(d, 0)) for d in days]

    avg = round(sum(s.score for s in scans) / len(scans), 1) if scans else 0.0

    return StatsOverview(
        total_scans=len(scans),
        allergen_alerts=sum(1 for s in scans if s.has_allergen),
        today_scans=counts.get(today.isoformat(), 0),
        avg_score=avg,
        recent_days=recent_days,
    )
