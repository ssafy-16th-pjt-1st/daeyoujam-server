from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.place_repository import get_place, get_place_by_content_id, list_places


def _to_read(row):
    place, average_rating, review_count = row
    place.average_rating = round(float(average_rating or 0), 1)
    place.review_count = int(review_count or 0)
    return place


def get_places(db: Session, *, category: str | None, q: str | None, page: int, size: int):
    rows, total = list_places(db, category=category, q=q, page=page, size=size)
    return [_to_read(row) for row in rows], total


def get_place_or_404(db: Session, place_id: int):
    row = get_place(db, place_id)
    if not row:
        raise NotFoundError("Place not found")
    return _to_read(row)


def get_place_by_content_id_or_404(db: Session, content_id: int):
    place = get_place_by_content_id(db, content_id)
    if not place:
        raise NotFoundError("Place not found")
    return place

