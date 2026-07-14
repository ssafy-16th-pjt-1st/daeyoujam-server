from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    guest_id: str
    nickname: str
    age_group: str | None = None
    gender: str | None = None
    province: str
    city: str
    district: str | None = None
    interests: list[str] = []
    preferred_keywords: list[str] = []
    travel_style: str | None = None
    companion_type: str | None = None


class UserRead(BaseModel):
    id: int
    guest_id: str
    nickname: str
    age_group: str | None = None
    gender: str | None = None
    province: str
    city: str
    district: str | None = None
    interests: str
    preferred_keywords: str | None = None
    travel_style: str | None = None
    companion_type: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
