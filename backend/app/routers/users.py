from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.geo import PITTSBURGH_LAT, PITTSBURGH_LNG
from app.models import User
from app.schemas import OnboardingIn, ProfilePatch
from app.serialize import dump_tags, user_public
from app.tags import TAG_DICTIONARY, normalize_tags

router = APIRouter(tags=["users"])


@router.get("/tags")
def list_tags():
    return {"tags": TAG_DICTIONARY}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.patch("/me")
def patch_me(
    body: ProfilePatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        user.name = body.name.strip()
    if body.phone is not None:
        user.phone = body.phone.strip() or None
    if body.tags is not None:
        user.tags = dump_tags(normalize_tags(body.tags))
    if body.lat is not None:
        user.lat = body.lat
    if body.lng is not None:
        user.lng = body.lng
    if body.default_radius_mi is not None:
        user.default_radius_mi = body.default_radius_mi
    db.commit()
    db.refresh(user)
    return user_public(user)


@router.post("/me/onboarding")
def onboard(
    body: OnboardingIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.name = body.name.strip()
    user.phone = (body.phone or "").strip() or None
    user.tags = dump_tags(normalize_tags(body.tags))
    user.lat = body.lat if body.lat is not None else PITTSBURGH_LAT
    user.lng = body.lng if body.lng is not None else PITTSBURGH_LNG
    user.onboarded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user_public(user)
