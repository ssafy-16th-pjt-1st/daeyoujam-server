from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ai.services.openai_service import build_llm_chat_answer, check_llm_health
from app.ai.services.rag_service import build_chat_answer, build_sources, retrieve_ranked_places
from app.ai.services.review_summary_service import build_review_summary
from app.models.ai_summary import AiSummary
from app.models.place import Place
from app.models.review import Review
from app.schemas.place import PlaceRead

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    user_profile: dict = Field(default_factory=dict)
    limit: int = Field(default=4, ge=1, le=8)


class ChatPlace(PlaceRead):
    recommendation_reason: str


class ChatResponse(BaseModel):
    answer: str
    places: list[ChatPlace]
    sources: list[dict]


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    ranked_places = retrieve_ranked_places(
        db,
        message=payload.message.strip(),
        user_profile=payload.user_profile,
        limit=payload.limit,
    )
    places = []
    for item in ranked_places:
        place = item.place
        serialized = place.__dict__.copy()
        serialized["average_rating"] = place.average_rating
        serialized["review_count"] = place.review_count
        serialized["recommendation_reason"] = item.recommendation_reason
        places.append(serialized)

    message = payload.message.strip()
    answer = build_llm_chat_answer(message, payload.user_profile, ranked_places)
    if answer is None:
        answer = build_chat_answer(message, payload.user_profile, ranked_places)

    return {
        "answer": answer,
        "places": places,
        "sources": build_sources([item.place for item in ranked_places]),
    }


@router.get("/health")
def llm_health():
    return check_llm_health()


@router.post("/reviews/{place_id}/summary")
def summarize_reviews(place_id: int, db: Session = Depends(get_db)):
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    reviews = db.scalars(select(Review).where(Review.place_id == place_id).order_by(desc(Review.id))).all()
    row = db.execute(
        select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where(Review.place_id == place_id)
    ).one()
    average_rating = round(float(row[0] or 0), 1)
    review_count = int(row[1] or 0)

    latest = db.scalars(
        select(AiSummary)
        .where(AiSummary.place_id == place_id, AiSummary.review_count == review_count)
        .order_by(desc(AiSummary.generated_at), desc(AiSummary.id))
    ).first()
    if latest and "?" not in latest.summary:
        return {
            "place_id": place_id,
            "summary": [line for line in latest.summary.splitlines() if line.strip()],
            "review_count": latest.review_count,
            "average_rating": average_rating,
        }

    summary = build_review_summary(place, reviews, average_rating)
    db.add(AiSummary(place_id=place_id, summary="\n".join(summary), review_count=review_count))
    db.commit()
    return {
        "place_id": place_id,
        "summary": summary,
        "review_count": review_count,
        "average_rating": average_rating,
    }
