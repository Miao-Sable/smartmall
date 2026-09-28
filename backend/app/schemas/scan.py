"""扫码相关模型"""
from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    barcode: str
    source: str = "manual"  # camera / manual


class AllergenHit(BaseModel):
    allergen_name: str
    ingredient: str


class ScoreReason(BaseModel):
    type: str  # allergen / diet / nutrition / price
    label: str
    delta: int


class AnalysisOut(BaseModel):
    score: int
    level: str
    traffic_light: str = "green"  # green / yellow / red
    traffic_label: str = "适合"  # 适合 / 谨慎 / 不建议
    allergen_hits: list[AllergenHit] = []
    reasons: list[ScoreReason] = []
    recommended: bool


class ScanOut(BaseModel):
    id: int
    barcode: str
    product_id: int | None = None
    product_name: str = ""
    score: int = 0
    level: str = ""
    has_allergen: bool = False
    source: str = "manual"
    created_at: datetime
    analysis: AnalysisOut | None = None
