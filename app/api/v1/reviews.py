from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_summary import AiSummary
from app.models.place import Place
from app.models.review import Review
from app.models.user import User
from app.schemas.review import RatingResponse, ReviewCreate, ReviewDelete, ReviewRead, ReviewUpdate

router = APIRouter()


def _get_place_or_404(db: Session, place_id: int) -> Place:
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


def _get_review_or_404(db: Session, place_id: int, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if not review or review.place_id != place_id:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


def _ensure_edit_password(review: Review, submitted_password: str) -> None:
    if review.edit_password != submitted_password:
        raise HTTPException(status_code=403, detail="Invalid edit password")


def _invalidate_review_summary(db: Session, place_id: int) -> None:
    db.query(AiSummary).filter(AiSummary.place_id == place_id).delete(synchronize_session=False)


@router.get("/places/{place_id}/reviews", response_model=list[ReviewRead])
def list_reviews(place_id: int, db: Session = Depends(get_db)):
    _get_place_or_404(db, place_id)
    return db.scalars(select(Review).where(Review.place_id == place_id).order_by(Review.id.desc())).all()


@router.post("/places/{place_id}/reviews", response_model=ReviewRead, status_code=201)
def create_review(place_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    _get_place_or_404(db, place_id)
    user = db.scalars(select(User).where(User.guest_id == payload.guest_id)).first()
    if not user:
        raise HTTPException(status_code=400, detail="User profile not found")
    review = Review(
        place_id=place_id,
        nickname=user.nickname,
        rating=payload.rating,
        content=payload.content,
        edit_password=payload.edit_password,
    )
    db.add(review)
    _invalidate_review_summary(db, place_id)
    db.commit()
    db.refresh(review)
    return review


@router.put("/places/{place_id}/reviews/{review_id}", response_model=ReviewRead)
def update_review(place_id: int, review_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)):
    _get_place_or_404(db, place_id)
    review = _get_review_or_404(db, place_id, review_id)
    _ensure_edit_password(review, payload.edit_password)
    review.rating = payload.rating
    review.content = payload.content
    _invalidate_review_summary(db, place_id)
    db.commit()
    db.refresh(review)
    return review


@router.delete("/places/{place_id}/reviews/{review_id}", status_code=204)
def delete_review(place_id: int, review_id: int, payload: ReviewDelete, db: Session = Depends(get_db)):
    _get_place_or_404(db, place_id)
    review = _get_review_or_404(db, place_id, review_id)
    _ensure_edit_password(review, payload.edit_password)
    db.delete(review)
    _invalidate_review_summary(db, place_id)
    db.commit()


@router.get("/places/{place_id}/rating", response_model=RatingResponse)
def get_rating(place_id: int, db: Session = Depends(get_db)):
    _get_place_or_404(db, place_id)
    row = db.execute(
        select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where(Review.place_id == place_id)
    ).one()
    return {"place_id": place_id, "average_rating": round(float(row[0] or 0), 1), "review_count": int(row[1] or 0)}
