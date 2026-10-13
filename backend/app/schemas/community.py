"""社区评价请求/响应模型"""
from datetime import datetime

from pydantic import BaseModel


class ReviewCreate(BaseModel):
    content: str
    product_name: str = ""
    tag: str = ""
    barcode: str = ""


class ReviewOut(BaseModel):
    id: int
    content: str
    product_name: str
    tag: str
    barcode: str
    author_nickname: str
    created_at: datetime
