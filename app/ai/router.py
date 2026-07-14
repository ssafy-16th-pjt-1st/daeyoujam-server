from fastapi import APIRouter, HTTPException

from app.core.config import get_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
def chat():
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "replace_with_new_openai_api_key":
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Set backend/.env for AI APIs.")
    return {"answer": "AI chat is ready to connect.", "sources": []}


@router.post("/reviews/{place_id}/summary")
def summarize_reviews(place_id: int):
    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key == "replace_with_new_openai_api_key":
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Set backend/.env for AI APIs.")
    return {"place_id": place_id, "summary": [], "review_count": 0}

