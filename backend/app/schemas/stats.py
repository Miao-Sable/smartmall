"""首页仪表板统计模型"""
from pydantic import BaseModel


class DailyCount(BaseModel):
    date: str
    count: int


class StatsOverview(BaseModel):
    total_scans: int = 0
    allergen_alerts: int = 0
    today_scans: int = 0
    avg_score: float = 0
    recent_days: list[DailyCount] = []


# ---- 健康周报 ----


class CategoryTrend(BaseModel):
    """商品品类趋势"""
    category: str
    count: int
    percentage: float


class NutritionSummary(BaseModel):
    """营养警示汇总"""
    high_sugar_count: int = 0  # 高糖商品数量
    high_sodium_count: int = 0  # 高钠商品数量
    high_fat_count: int = 0  # 高脂商品数量


class WeeklyReport(BaseModel):
    """健康周报"""
    period_start: str  # 周期开始日期
    period_end: str  # 周期结束日期
    total_scans: int = 0  # 扫描总数
    allergen_avoided: int = 0  # 避开过敏风险次数
    avg_score: float = 0  # 平均匹配度评分
    score_trend: str = ""  # 评分趋势描述，如 "较上周上升 12%"
    category_trends: list[CategoryTrend] = []  # 商品类别选择趋势
    nutrition_summary: NutritionSummary  # 营养警示汇总
    top_products: list[str] = []  # 高频扫描商品（top 5）
