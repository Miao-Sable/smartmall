"""首页仪表板统计"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.scan import ScanHistory
from app.models.user import Profile, User
from app.schemas.stats import (
    CategoryTrend,
    DailyCount,
    NutritionSummary,
    StatsOverview,
    WeeklyReport,
)
from app.services.mock_data import find_product_by_id

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


@router.get("/weekly-report", response_model=WeeklyReport)
def weekly_report(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    profile_id: int | None = None,
) -> WeeklyReport:
    """健康周报：最近 7 天（本周）的扫描数据分析，含与上周的趋势对比"""
    # 注意：created_at 列带时区（UTC），查询边界必须同样带时区，否则会触发
    # SQLModel "Datetime values must have timezone information" 报错。
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    # 按档案筛选：校验档案归属该账号，不归属则 404（与 overview 一致）
    if profile_id is not None:
        profile = session.get(Profile, profile_id)
        if profile is None or profile.user_id != user.id:
            raise HTTPException(status_code=404, detail="档案不存在")

    def load_scans(start: datetime, end: datetime) -> list[ScanHistory]:
        query = select(ScanHistory).where(
            ScanHistory.user_id == user.id,
            ScanHistory.created_at >= start,
            ScanHistory.created_at < end,
        )
        if profile_id is not None:
            query = query.where(ScanHistory.profile_id == profile_id)
        return list(session.exec(query).all())

    current_scans = load_scans(week_ago, now)
    prev_scans = load_scans(prev_week_start, week_ago)

    # 基础统计
    total_scans = len(current_scans)
    allergen_avoided = sum(1 for s in current_scans if s.has_allergen)
    avg_score = round(sum(s.score for s in current_scans) / total_scans, 1) if current_scans else 0.0

    # 评分趋势（与上周对比）
    prev_avg = round(sum(s.score for s in prev_scans) / len(prev_scans), 1) if prev_scans else 0.0
    score_trend = ""
    if prev_avg > 0:
        change = ((avg_score - prev_avg) / prev_avg) * 100
        score_trend = f"较上周{'上升' if change > 0 else '下降'} {abs(change):.1f}%"
    elif avg_score > 0:
        score_trend = "首次记录"

    # 品类/商品选择趋势 + 营养警示（阈值与 matching.py 保持一致）
    category_counter: Counter[str] = Counter()
    product_counter: Counter[str] = Counter()
    high_sugar = high_sodium = high_fat = 0

    for scan in current_scans:
        if not scan.product_id:
            continue
        product = find_product_by_id(scan.product_id)
        if not product:
            continue
        category_counter[product["category"]] += 1
        product_counter[product["name"]] += 1

        nutrition = {n["name"]: n for n in product.get("nutrition", [])}
        for name, threshold in (("碳水化合物", 60.0), ("钠", 600.0), ("脂肪", 20.0)):
            item = nutrition.get(name)
            if item is None:
                continue
            try:
                value = float(item["value"])
            except (TypeError, ValueError):
                continue
            if value >= threshold:
                if name == "碳水化合物":
                    high_sugar += 1
                elif name == "钠":
                    high_sodium += 1
                else:
                    high_fat += 1

    total = sum(category_counter.values())
    category_trends = [
        CategoryTrend(
            category=cat,
            count=cnt,
            percentage=round(cnt / total * 100, 1) if total > 0 else 0,
        )
        for cat, cnt in category_counter.most_common(5)
    ]

    return WeeklyReport(
        period_start=week_ago.date().isoformat(),
        period_end=now.date().isoformat(),
        total_scans=total_scans,
        allergen_avoided=allergen_avoided,
        avg_score=avg_score,
        score_trend=score_trend,
        category_trends=category_trends,
        nutrition_summary=NutritionSummary(
            high_sugar_count=high_sugar,
            high_sodium_count=high_sodium,
            high_fat_count=high_fat,
        ),
        top_products=[name for name, _ in product_counter.most_common(5)],
    )
