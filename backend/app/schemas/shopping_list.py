"""购物清单预检与重匹配相关模型"""
from pydantic import BaseModel

from app.schemas.scan import AllergenHit


class ProductBrief(BaseModel):
    id: int
    name: str
    barcode: str = ""
    category: str = ""
    price: float = 0.0


class PrecheckItemOut(BaseModel):
    name: str  # 用户输入的原商品名
    match_type: str = "not_found"  # exact / fuzzy / not_found
    product: ProductBrief | None = None  # 匹配到的商品；not_found 时为 None
    is_high_risk: bool = False
    allergen_hits: list[AllergenHit] = []
    diet_hits: list[str] = []  # 违反的饮食偏好名称（软提示）
    alternatives: list[ProductBrief] = []


class ShoppingListPrecheckRequest(BaseModel):
    items: list[str] = []


class ShoppingListPrecheckOut(BaseModel):
    items: list[PrecheckItemOut] = []


class RematchRequest(BaseModel):
    name: str
    exclude_ids: list[int] = []
