from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.place import Place
from app.models.review import Review


def _with_rating(stmt):
    return (
        stmt.outerjoin(Review, Review.place_id == Place.id)
        .group_by(Place.id)
        .add_columns(func.coalesce(func.avg(Review.rating), 0).label("average_rating"))
        .add_columns(func.count(Review.id).label("review_count"))
    )


def list_places(db: Session, *, category: str | None, q: str | None, page: int, size: int):
    base = select(Place)
    count_stmt = select(func.count(Place.id))
    if category:
        base = base.where(Place.content_type == category)
        count_stmt = count_stmt.where(Place.content_type == category)
    if q:
        pattern = f"%{q}%"
        condition = or_(
            Place.title.like(pattern),
            Place.addr1.like(pattern),
            Place.addr2.like(pattern),
            Place.content_type.like(pattern),
        )
        base = base.where(condition)
        count_stmt = count_stmt.where(condition)
    total = db.scalar(count_stmt) or 0
    rows = db.execute(_with_rating(base.order_by(Place.id).offset((page - 1) * size).limit(size))).all()
    return rows, total


def get_place(db: Session, place_id: int):
    stmt = _with_rating(select(Place).where(Place.id == place_id))
    return db.execute(stmt).first()


def get_place_by_content_id(db: Session, content_id: int):
    stmt = select(Place).where(Place.content_id == content_id)
    return db.execute(stmt).scalar_one_or_none()
