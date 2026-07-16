from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ai.services.chat_history_service import (
    add_chat_message,
    clear_chat_history,
    get_chat_session,
    get_latest_chat_session,
    get_or_create_chat_session,
    serialize_chat_messages,
)
from app.ai.services.openai_service import build_llm_chat_answer, check_llm_health
from app.ai.services.rag_service import build_chat_answer, build_sources, retrieve_ranked_places
from app.ai.services.review_summary_service import build_review_summary
from app.ai.services.security_service import (
    assess_prompt_safety,
    blocked_prompt_answer,
    sanitize_user_profile,
    sanitize_user_text,
)
from app.models.ai_summary import AiSummary
from app.models.chat import ChatMessage
from app.models.place import Place
from app.models.review import Review
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/ai", tags=["ai"])

STALE_REVIEW_SUMMARY_MARKERS = ("최근 리뷰", "최근에는")


def _is_usable_review_summary_cache(summary: str) -> bool:
    return bool(summary and "?" not in summary and not any(marker in summary for marker in STALE_REVIEW_SUMMARY_MARKERS))


def _serialize_chat_place(item) -> dict:
    place = item.place
    return {
        "id": place.id,
        "content_id": place.content_id,
        "content_type_id": place.content_type_id,
        "content_type": place.content_type,
        "title": place.title,
        "addr1": place.addr1,
        "addr2": place.addr2,
        "zipcode": place.zipcode,
        "tel": place.tel,
        "mapx": place.mapx,
        "mapy": place.mapy,
        "mlevel": place.mlevel,
        "first_image": place.first_image,
        "first_image2": place.first_image2,
        "created_time": place.created_time,
        "modified_time": place.modified_time,
        "copyright_type": place.copyright_type,
        "area_code": place.area_code,
        "sigungu_code": place.sigungu_code,
        "region_code": place.region_code,
        "signgu_code": place.signgu_code,
        "category1": place.category1,
        "category2": place.category2,
        "category3": place.category3,
        "lcls_system1": place.lcls_system1,
        "lcls_system2": place.lcls_system2,
        "lcls_system3": place.lcls_system3,
        "average_rating": getattr(place, "average_rating", 0),
        "review_count": getattr(place, "review_count", 0),
        "recommendation_reason": item.recommendation_reason,
    }


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    message = sanitize_user_text(payload.message.strip())
    user_profile = sanitize_user_profile(payload.user_profile)
    guest_id = payload.guest_id or user_profile.get("guestId") or user_profile.get("guest_id")
    session = get_or_create_chat_session(db, guest_id, payload.session_id) if guest_id else None

    if session:
        add_chat_message(db, session=session, role="user", content=message)

    safety = assess_prompt_safety(message)
    if safety.blocked:
        answer = blocked_prompt_answer(safety.reason)
        if session:
            add_chat_message(db, session=session, role="bot", content=answer, places=[], sources=[])
            db.commit()
        return {
            "answer": answer,
            "places": [],
            "sources": [],
            "session_id": session.id if session else None,
        }

    ranked_places = retrieve_ranked_places(
        db,
        message=message,
        user_profile=user_profile,
        limit=payload.limit,
    )
    places = []
    for item in ranked_places:
        places.append(_serialize_chat_place(item))
    sources = build_sources([item.place for item in ranked_places])

    answer = build_llm_chat_answer(message, user_profile, ranked_places)
    if answer is None:
        answer = build_chat_answer(message, user_profile, ranked_places)

    if session:
        add_chat_message(db, session=session, role="bot", content=answer, places=places, sources=sources)
        db.commit()

    return {
        "answer": answer,
        "places": places,
        "sources": sources,
        "session_id": session.id if session else None,
    }


@router.get("/chat/history", response_model=ChatHistoryResponse)
def chat_history(
    guest_id: str = Query(..., min_length=1, max_length=64),
    session_id: int | None = None,
    db: Session = Depends(get_db),
):
    if session_id:
        session = get_chat_session(db, guest_id, session_id)
    else:
        session = get_latest_chat_session(db, guest_id)
    if not session:
        return {"session_id": None, "messages": []}

    messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.id)).all()
    return {"session_id": session.id, "messages": serialize_chat_messages(messages)}


@router.delete("/chat/history", status_code=204)
def delete_chat_history(
    guest_id: str = Query(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    clear_chat_history(db, guest_id)
    db.commit()


@router.get("/health")
def llm_health():
    return check_llm_health()


@router.post("/reviews/{place_id}/summary")
def summarize_reviews(place_id: int, db: Session = Depends(get_db)):
    place = db.get(Place, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    reviews = db.scalars(select(Review).where(Review.place_id == place_id).order_by(Review.id.asc())).all()
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
    if latest and _is_usable_review_summary_cache(latest.summary):
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
