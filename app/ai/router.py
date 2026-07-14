from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.ai.services.openai_service import build_llm_chat_answer, check_llm_health
from app.ai.services.rag_service import build_chat_answer, build_sources, retrieve_ranked_places
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
def summarize_reviews(place_id: int):
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "replace_with_new_openai_api_key":
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Set backend/.env for AI APIs.")
    return {"place_id": place_id, "summary": [], "review_count": 0}
