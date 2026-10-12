"""家庭档案解析：默认档案与 profile_id 归属校验"""
from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.user import Profile


def get_or_create_default_profile(session: Session, user_id: int) -> Profile:
    """返回账号的默认档案；不存在则创建「我」。"""
    profile = session.exec(
        select(Profile).where(Profile.user_id == user_id, Profile.is_default.is_(True))
    ).first()
    if profile is None:
        profile = Profile(user_id=user_id, name="我", is_default=True)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def resolve_profile_id(session: Session, user_id: int, profile_id: int | None = None) -> int:
    """解析请求中的 profile_id：为空则取默认档案；否则校验档案归属该账号。

    返回档案 id；不归属则 404。
    """
    if profile_id is None:
        return get_or_create_default_profile(session, user_id).id
    profile = session.get(Profile, profile_id)
    if profile is None or profile.user_id != user_id:
        raise HTTPException(status_code=404, detail="档案不存在")
    return profile.id
