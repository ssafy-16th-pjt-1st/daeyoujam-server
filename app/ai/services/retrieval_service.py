from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.place import Place


def retrieve_places(db: Session, query: str, category: str | None = None, district: str | None = None, limit: int = 8):
    stmt = select(Place)
    if category:
        stmt = stmt.where(Place.content_type == category)
    if district:
        stmt = stmt.where(Place.addr1.like(f"%{district}%"))
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Place.title.like(pattern), Place.addr1.like(pattern), Place.content_type.like(pattern)))
    return db.scalars(stmt.limit(limit)).all()

