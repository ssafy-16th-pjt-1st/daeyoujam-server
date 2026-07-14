from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.place import Place
from app.models.review import Review
from app.schemas.review import RatingResponse, ReviewCreate, ReviewRead

router = APIRouter()


@router.get("/places/{place_id}/reviews", response_model=list[ReviewRead])
def list_reviews(place_id: int, db: Session = Depends(get_db)):
    if not db.get(Place, place_id):
        raise HTTPException(status_code=404, detail="Place not found")
    return db.scalars(select(Review).where(Review.place_id == place_id).order_by(Review.id.desc())).all()


@router.post("/places/{place_id}/reviews", response_model=ReviewRead, status_code=201)
def create_review(place_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    if not db.get(Place, place_id):
        raise HTTPException(status_code=404, detail="Place not found")
    review = Review(place_id=place_id, **payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/places/{place_id}/rating", response_model=RatingResponse)
def get_rating(place_id: int, db: Session = Depends(get_db)):
    if not db.get(Place, place_id):
        raise HTTPException(status_code=404, detail="Place not found")
    row = db.execute(
        select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where(Review.place_id == place_id)
    ).one()
    return {"place_id": place_id, "average_rating": round(float(row[0] or 0), 1), "review_count": int(row[1] or 0)}

