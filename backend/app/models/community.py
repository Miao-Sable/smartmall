"""社区：商品评价"""
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.user import utcnow


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    content: str = ""            # 评价正文
    product_name: str = ""       # 可选：关联商品名（自由文本，不建外键）
    tag: str = ""                # 可选：recommend / avoid / ""（无标签）
    barcode: str = Field(default="", index=True)  # 可选：关联商品条码，用于商品详情页评价
    created_at: datetime = Field(default_factory=utcnow)
