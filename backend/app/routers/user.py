"""用户档案：账号信息 + 家庭档案（过敏源与饮食偏好挂在档案上）"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.database import get_session
from app.deps import get_current_user
from app.models.scan import AnalysisResult, ScanHistory
from app.models.user import Profile, ProfileAllergen, ProfileDiet, User, UserProfile
from app.schemas.user import (
    ProfileCreate,
    ProfileOut,
    ProfileUpdate,
    UserProfileOut,
    UserProfileUpdate,
)
from app.services.matching import analyze_product, load_profile_allergens, load_profile_diets
from app.services.mock_data import find_product_by_barcode
from app.services.profiles import get_or_create_default_profile

router = APIRouter()


def _profile_out(session: Session, profile: Profile) -> ProfileOut:
    allergen_ids = [
        r.allergen_id for r in session.exec(select(ProfileAllergen).where(ProfileAllergen.profile_id == profile.id))
    ]
    diet_ids = [r.diet_id for r in session.exec(select(ProfileDiet).where(ProfileDiet.profile_id == profile.id))]
    return ProfileOut(
        id=profile.id,
        name=profile.name,
        emoji=profile.emoji,
        birth_year=profile.birth_year,
        scenario=profile.scenario,
        is_default=profile.is_default,
        allergen_ids=allergen_ids,
        diet_ids=diet_ids,
    )


def _set_profile_prefs(session: Session, profile_id: int, allergen_ids: list[int], diet_ids: list[int]) -> None:
    """全量替换某档案的过敏源 / 饮食偏好关联"""
    for row in session.exec(select(ProfileAllergen).where(ProfileAllergen.profile_id == profile_id)):
        session.delete(row)
    for row in session.exec(select(ProfileDiet).where(ProfileDiet.profile_id == profile_id)):
        session.delete(row)
    for aid in allergen_ids:
        session.add(ProfileAllergen(profile_id=profile_id, allergen_id=aid))
    for did in diet_ids:
        session.add(ProfileDiet(profile_id=profile_id, diet_id=did))


def _recompute_scan_analysis(session: Session, profile_id: int) -> None:
    """档案的过敏源 / 饮食偏好变化后，重算该档案名下历史扫描的分析结果与过敏提醒"""
    allergens = load_profile_allergens(session, profile_id)
    diets = load_profile_diets(session, profile_id)
    scans = session.exec(select(ScanHistory).where(ScanHistory.profile_id == profile_id)).all()
    for scan in scans:
        product = find_product_by_barcode(scan.barcode)
        if product is None:
            continue
        analysis = analyze_product(product, allergens, diets)
        scan.score = analysis["score"]
        scan.level = analysis["level"]
        scan.has_allergen = bool(analysis["allergen_hits"])
        result = session.exec(select(AnalysisResult).where(AnalysisResult.scan_id == scan.id)).first()
        if result is None:
            result = AnalysisResult(scan_id=scan.id)
            session.add(result)
        result.allergen_hits = analysis["allergen_hits"]
        result.reasons = analysis["reasons"]
        result.score = analysis["score"]
        result.level = analysis["level"]
        result.traffic_light = analysis["traffic_light"]
        result.recommended = analysis["recommended"]


# ---------- 账号级档案（昵称/性别/出生年） ----------

@router.get("/profile", response_model=UserProfileOut)
def get_profile(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> UserProfileOut:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    default = session.exec(
        select(Profile).where(Profile.user_id == user.id, Profile.is_default.is_(True))
    ).first()
    return UserProfileOut(
        user_id=user.id,
        email=user.email,
        nickname=profile.nickname if profile else "",
        gender=profile.gender if profile else "",
        birth_year=profile.birth_year if profile else None,
        default_profile_id=default.id if default else None,
        onboarded=profile is not None,
    )


@router.put("/profile", response_model=UserProfileOut)
def update_profile(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserProfileOut:
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        session.add(profile)
    if data.nickname is not None:
        profile.nickname = data.nickname
    if data.gender is not None:
        profile.gender = data.gender
    if data.birth_year is not None:
        profile.birth_year = data.birth_year
    session.commit()
    return get_profile(user=user, session=session)


# ---------- 家庭档案 CRUD ----------

@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[ProfileOut]:
    profiles = session.exec(select(Profile).where(Profile.user_id == user.id).order_by(Profile.id)).all()
    if not profiles:
        get_or_create_default_profile(session, user.id)
        profiles = session.exec(select(Profile).where(Profile.user_id == user.id).order_by(Profile.id)).all()
    return [_profile_out(session, p) for p in profiles]


@router.post("/profiles", response_model=ProfileOut)
def create_profile(
    data: ProfileCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProfileOut:
    count = len(session.exec(select(Profile).where(Profile.user_id == user.id)).all())
    profile = Profile(
        user_id=user.id,
        name=data.name or "新成员",
        emoji=data.emoji,
        birth_year=data.birth_year,
        scenario=data.scenario,
        is_default=(count == 0),  # 首个档案自动设为默认
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    _set_profile_prefs(session, profile.id, data.allergen_ids, data.diet_ids)
    session.commit()
    return _profile_out(session, profile)


@router.put("/profiles/{profile_id}", response_model=ProfileOut)
def update_profile_by_id(
    profile_id: int,
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ProfileOut:
    profile = session.get(Profile, profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="档案不存在")
    if data.name is not None:
        profile.name = data.name
    if data.emoji is not None:
        profile.emoji = data.emoji
    if data.birth_year is not None:
        profile.birth_year = data.birth_year
    if data.scenario is not None:
        profile.scenario = data.scenario
    _set_profile_prefs(session, profile.id, data.allergen_ids, data.diet_ids)
    session.commit()
    _recompute_scan_analysis(session, profile.id)
    session.commit()
    return _profile_out(session, profile)


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(
    profile_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    profile = session.get(Profile, profile_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="档案不存在")
    if profile.is_default:
        raise HTTPException(status_code=400, detail="默认档案不可删除")
    for row in session.exec(select(ProfileAllergen).where(ProfileAllergen.profile_id == profile.id)):
        session.delete(row)
    for row in session.exec(select(ProfileDiet).where(ProfileDiet.profile_id == profile.id)):
        session.delete(row)
    session.delete(profile)
    session.commit()
    return Response(status_code=204)
