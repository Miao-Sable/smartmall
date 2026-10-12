"""用户相关表：账号、档案、过敏源/饮食偏好字典与关联"""
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    phone: str | None = Field(default=None, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utcnow)


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profile"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    nickname: str = ""
    gender: str = ""  # male / female / other
    birth_year: int | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class Allergen(SQLModel, table=True):
    __tablename__ = "allergen"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    category: str = ""
    keywords: list = Field(default_factory=list, sa_column=Column(JSON))  # 关键词列表
    description: str = ""


class UserAllergen(SQLModel, table=True):
    """legacy：过敏源原挂在账号上，现已迁到 Profile（见 ProfileAllergen）。仅保留用于数据迁移。"""

    __tablename__ = "user_allergen"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    allergen_id: int = Field(foreign_key="allergen.id")


class DietPreference(SQLModel, table=True):
    __tablename__ = "diet_preference"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    keywords: list = Field(default_factory=list, sa_column=Column(JSON))
    description: str = ""


class UserDiet(SQLModel, table=True):
    """legacy：饮食偏好原挂在账号上，现已迁到 Profile（见 ProfileDiet）。仅保留用于数据迁移。"""

    __tablename__ = "user_diet"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    diet_id: int = Field(foreign_key="diet_preference.id")


class Profile(SQLModel, table=True):
    """家庭档案：账号下的「给谁买」对象，每个档案有独立过敏源与饮食偏好。"""

    __tablename__ = "profile"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = ""  # 称呼：我 / 宝宝 / 奶奶
    emoji: str = ""  # 头像 emoji
    birth_year: int | None = None
    scenario: str = ""  # child/elder/pregnant/low_sugar/low_fat/fitness/vegetarian/gluten_free/custom
    is_default: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class ProfileAllergen(SQLModel, table=True):
    __tablename__ = "profile_allergen"

    id: int | None = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", index=True)
    allergen_id: int = Field(foreign_key="allergen.id")


class ProfileDiet(SQLModel, table=True):
    __tablename__ = "profile_diet"

    id: int | None = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profile.id", index=True)
    diet_id: int = Field(foreign_key="diet_preference.id")
