from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    content_type_id: Mapped[int | None] = mapped_column(Integer, index=True)
    content_type: Mapped[str | None] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    addr1: Mapped[str | None] = mapped_column(Text, index=True)
    addr2: Mapped[str | None] = mapped_column(Text)
    zipcode: Mapped[str | None] = mapped_column(String(32))
    tel: Mapped[str | None] = mapped_column(String(255))
    mapx: Mapped[float | None] = mapped_column(Float)
    mapy: Mapped[float | None] = mapped_column(Float)
    mlevel: Mapped[int | None] = mapped_column(Integer)
    first_image: Mapped[str | None] = mapped_column(Text)
    first_image2: Mapped[str | None] = mapped_column(Text)
    created_time: Mapped[str | None] = mapped_column(String(14))
    modified_time: Mapped[str | None] = mapped_column(String(14), index=True)
    copyright_type: Mapped[str | None] = mapped_column(String(32))
    area_code: Mapped[str | None] = mapped_column(String(32), index=True)
    sigungu_code: Mapped[str | None] = mapped_column(String(32), index=True)
    region_code: Mapped[str | None] = mapped_column(String(32))
    signgu_code: Mapped[str | None] = mapped_column(String(32))
    category1: Mapped[str | None] = mapped_column(String(32), index=True)
    category2: Mapped[str | None] = mapped_column(String(32), index=True)
    category3: Mapped[str | None] = mapped_column(String(32), index=True)
    lcls_system1: Mapped[str | None] = mapped_column(String(32), index=True)
    lcls_system2: Mapped[str | None] = mapped_column(String(32), index=True)
    lcls_system3: Mapped[str | None] = mapped_column(String(32), index=True)

    reviews = relationship("Review", back_populates="place", cascade="all, delete-orphan")
