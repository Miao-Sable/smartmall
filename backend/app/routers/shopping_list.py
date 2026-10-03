"""购物清单预检与重匹配"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models.user import User
from app.schemas.shopping_list import (
    PrecheckItemOut,
    ProductBrief,
    RematchRequest,
    ShoppingListPrecheckOut,
    ShoppingListPrecheckRequest,
)
from app.services.precheck import precheck_items, rematch_candidates

router = APIRouter()


@router.post("/precheck", response_model=ShoppingListPrecheckOut)
def precheck(
    data: ShoppingListPrecheckRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ShoppingListPrecheckOut:
    items = [PrecheckItemOut(**item) for item in precheck_items(session, user.id, data.items)]
    return ShoppingListPrecheckOut(items=items)


@router.post("/rematch", response_model=list[ProductBrief])
def rematch(
    data: RematchRequest,
    user: User = Depends(get_current_user),
) -> list[ProductBrief]:
    return [ProductBrief(**c) for c in rematch_candidates(data.name, data.exclude_ids)]
