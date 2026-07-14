from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.place import PlaceListResponse, PlaceRead
from app.services.place_service import get_place_or_404, get_places

router = APIRouter()


@router.get("", response_model=PlaceListResponse)
def read_places(
    category: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = get_places(db, category=category, q=None, page=page, size=size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/search", response_model=PlaceListResponse)
def search_places(
    q: str = Query("", max_length=100),
    category: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = get_places(db, category=category, q=q.strip() or None, page=page, size=size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{place_id}", response_model=PlaceRead)
def read_place(place_id: int, db: Session = Depends(get_db)):
    return get_place_or_404(db, place_id)

