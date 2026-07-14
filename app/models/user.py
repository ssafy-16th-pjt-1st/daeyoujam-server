from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("age_group IN ('10대','20대','30대','40대','50대','60대 이상','응답 안 함')", name="ck_users_age_group"),
        CheckConstraint("gender IN ('남성','여성','기타','응답 안 함')", name="ck_users_gender"),
        CheckConstraint("travel_style IN ('힐링','맛집 탐방','문화생활','사진 촬영','액티비티','축제','쇼핑','가족 나들이','무관')", name="ck_users_travel_style"),
        CheckConstraint("companion_type IN ('혼자','친구','연인','가족','아이 동반','반려동물','무관')", name="ck_users_companion_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    guest_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(50), index=True)
    age_group: Mapped[str | None] = mapped_column(String(30))
    gender: Mapped[str | None] = mapped_column(String(30))
    province: Mapped[str] = mapped_column(String(80), index=True)
    city: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    interests: Mapped[str] = mapped_column(Text)
    preferred_keywords: Mapped[str | None] = mapped_column(Text)
    travel_style: Mapped[str | None] = mapped_column(String(30))
    companion_type: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
