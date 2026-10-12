"""基础字典模型（过敏源 / 饮食偏好）"""
from pydantic import BaseModel


class AllergenOut(BaseModel):
    id: int
    name: str
    category: str = ""
    keywords: list[str] = []
    description: str = ""


class DietOut(BaseModel):
    id: int
    name: str
    keywords: list[str] = []
    description: str = ""


class ScenarioOut(BaseModel):
    key: str
    name: str
    emoji: str = ""
    description: str = ""
    allergen_ids: list[int] = []
    diet_ids: list[int] = []
