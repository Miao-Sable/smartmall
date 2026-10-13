"""认证：注册 / 登录（JWT）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.profiles import get_or_create_default_profile

router = APIRouter()


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        email=user.email,
    )


@router.post("/register", response_model=TokenResponse)
def register(data: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    exists = session.exec(select(User).where(User.email == data.email)).first()
    if exists is not None:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(email=data.email, phone=data.phone, hashed_password=hash_password(data.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    get_or_create_default_profile(session, user.id)  # 注册即建默认档案「我」
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.email == data.email)).first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    return _token_response(user)
