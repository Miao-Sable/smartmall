"""社区：商品评价流"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.community import Review
from app.models.user import User, UserProfile
from app.schemas.community import ReviewCreate, ReviewOut

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
    review = Review(
        user_id=user.id,
        content=content,
        product_name=data.product_name.strip(),
        tag=data.tag,
        barcode=data.barcode.strip(),
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return _to_review_out(session, review)
