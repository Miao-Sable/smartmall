"""社区：商品评价流"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.community import Review
from app.models.user import User, UserProfile
from app.schemas.community import ReviewCreate, ReviewOut
from app.services.mock_data import find_product_by_barcode, match_product

router = APIRouter()


def _author_nickname(session: Session, user_id: int) -> str:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    if profile and profile.nickname:
        return profile.nickname
    user = session.get(User, user_id)
    return (user.email or "").split("@")[0] if user else ""


def _to_review_out(session: Session, review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        content=review.content,
        product_name=review.product_name,
        tag=review.tag,
        barcode=review.barcode,
        author_nickname=_author_nickname(session, review.user_id),
        created_at=review.created_at,
    )


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    barcode: str = "",
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ReviewOut]:
    stmt = select(Review).order_by(Review.created_at.desc()).limit(200)
    if barcode:
        stmt = select(Review).where(Review.barcode == barcode).order_by(Review.created_at.desc()).limit(200)
    reviews = session.exec(stmt).all()
    return [_to_review_out(session, r) for r in reviews]


@router.post("/reviews", response_model=ReviewOut)
def create_review(
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ReviewOut:
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="评价内容不能为空")

    # 商品名/条码必须对应已收录商品：优先按条码，否则按名称精确/模糊匹配
    barcode = data.barcode.strip()
    product_name = data.product_name.strip()
    product = None
    if barcode:
        product = find_product_by_barcode(barcode)
    if product is None and product_name:
        _, candidates = match_product(product_name)
        if candidates:
            product = candidates[0]

    if product is None and (barcode or product_name):
        raise HTTPException(status_code=404, detail="暂无该商品，无法评价")

    review = Review(
        user_id=user.id,
        content=content,
        product_name=product["name"] if product else "",
        tag=data.tag,
        barcode=str(product["barcode"]) if product else "",
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return _to_review_out(session, review)
