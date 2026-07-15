import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter()

TRAVEL_STYLE_ALIASES = {
    "느긋한 산책": "힐링",
}


def normalize_travel_style(value: str | None) -> str | None:
    if value is None:
        return None
    return TRAVEL_STYLE_ALIASES.get(value, value)


@router.post("", response_model=UserRead, status_code=201)
def upsert_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.guest_id == payload.guest_id).first()
    if not user:
        user = User(guest_id=payload.guest_id, nickname=payload.nickname)
        db.add(user)
    user.nickname = payload.nickname
    user.age_group = payload.age_group
    user.gender = payload.gender
    user.province = payload.province
    user.city = payload.city
    user.district = payload.district
    user.interests = json.dumps(payload.interests, ensure_ascii=False)
    user.preferred_keywords = json.dumps(payload.preferred_keywords, ensure_ascii=False)
    user.travel_style = normalize_travel_style(payload.travel_style)
    user.companion_type = payload.companion_type
    db.commit()
    db.refresh(user)
    return user
