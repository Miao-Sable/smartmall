"""扫描历史与分析结果"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScanHistory(SQLModel, table=True):
    __tablename__ = "scan_history"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    barcode: str = Field(index=True)
    product_id: int | None = None  # 商品数据来自 mock，故不设外键
    product_name: str = ""  # 冗余保存，历史列表免联表
    score: int = 0  # 匹配度评分 0-100
    level: str = ""  # 非常适合 / 比较适合 / 一般 / 不适合
    has_allergen: bool = False  # 是否命中过敏源
    source: str = "manual"  # camera / manual
    created_at: datetime = Field(default_factory=utcnow)


class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis_result"

    id: int | None = Field(default=None, primary_key=True)
    scan_id: int = Field(foreign_key="scan_history.id", unique=True)
    allergen_hits: list = Field(default_factory=list, sa_column=Column(JSON))  # [{allergen_name, ingredient}]
    reasons: list = Field(default_factory=list, sa_column=Column(JSON))  # [{type, label, delta}]
    score: int = 0
    level: str = ""
    traffic_light: str = "green"  # green / yellow / red
    recommended: bool = True
