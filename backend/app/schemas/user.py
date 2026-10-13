"""用户档案相关模型"""
from pydantic import BaseModel


class UserProfileOut(BaseModel):
    user_id: int
    email: str
    nickname: str = ""
    gender: str = ""
    birth_year: int | None = None
    default_profile_id: int | None = None
    onboarded: bool = False


class UserProfileUpdate(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    birth_year: int | None = None


class ProfileOut(BaseModel):
    id: int
    name: str = ""
    emoji: str = ""
    birth_year: int | None = None
    scenario: str = ""
    is_default: bool = False
    allergen_ids: list[int] = []
    diet_ids: list[int] = []


class ProfileCreate(BaseModel):
    name: str = ""
    emoji: str = ""
    birth_year: int | None = None
    scenario: str = ""
    allergen_ids: list[int] = []
    diet_ids: list[int] = []


class ProfileUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    birth_year: int | None = None
    scenario: str | None = None
    allergen_ids: list[int] = []
    diet_ids: list[int] = []
