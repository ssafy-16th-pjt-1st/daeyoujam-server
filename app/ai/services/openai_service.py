import logging

from fastapi import HTTPException
from openai import OpenAI

from app.core.config import get_settings
from app.ai.services.rag_service import RankedPlace

logger = logging.getLogger(__name__)
GROQ_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"


def require_openai_key() -> str:
    key = get_settings().openai_api_key
    if not key or key in {"replace_with_new_openai_api_key", "OPENAI_API_KEY"}:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured. Set backend/.env for AI APIs.")
    return key


def _resolve_base_url(key: str, model: str, configured_base_url: str) -> str | None:
    if configured_base_url:
        return configured_base_url
    if key.startswith("gsk_") or model.startswith("groq/"):
        return GROQ_OPENAI_BASE_URL
    return None


def build_llm_chat_answer(
    message: str,
    user_profile: dict,
    ranked_places: list[RankedPlace],
) -> str | None:
    """Generate a natural Korean answer when an OpenAI-compatible API is configured.

    Returning None lets the caller use the deterministic local fallback.
    """
    settings = get_settings()
    key = settings.openai_api_key
    if not key or key in {"replace_with_new_openai_api_key", "OPENAI_API_KEY"}:
        return None

    places_context = []
    for item in ranked_places:
        place = item.place
        places_context.append(
            {
                "title": place.title,
                "category": place.content_type,
                "address": " ".join(part for part in [place.addr1, place.addr2] if part),
                "rating": place.average_rating,
                "review_count": place.review_count,
                "reason": item.recommendation_reason,
            }
        )

    nickname = user_profile.get("nickname") or "사용자"
    district = user_profile.get("district") or "지정 없음"
    interests = user_profile.get("interests") or []

    try:
        base_url = _resolve_base_url(key, settings.openai_model, settings.openai_base_url)
        client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.45,
            max_tokens=450,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 대전·충청권 장소 추천 챗봇이다. "
                        "제공된 장소 데이터만 근거로 한국어로 답한다. "
                        "없는 정보는 단정하지 말고, 사용자가 다음에 확인할 점을 짧게 말한다."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"사용자 닉네임: {nickname}\n"
                        f"생활권: {district}\n"
                        f"관심사: {', '.join(interests) if interests else '없음'}\n"
                        f"질문: {message}\n"
                        f"추천 후보: {places_context}\n\n"
                        "답변은 3~5문장으로 작성하고, 첫 문장부터 질문에 직접 답해줘. "
                        "장소명 2~4개를 자연스럽게 언급하고, 카드에서 확인할 수 있는 정보도 안내해줘."
                    ),
                },
            ],
        )
    except Exception as exc:
        logger.warning("OpenAI chat completion failed: %s: %s", type(exc).__name__, exc)
        return None

    answer = response.choices[0].message.content if response.choices else None
    return answer.strip() if answer else None
