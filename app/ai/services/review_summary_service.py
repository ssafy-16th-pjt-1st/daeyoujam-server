import logging

from app.ai.services.openai_service import build_openai_client
from app.core.config import get_settings
from app.models.place import Place
from app.models.review import Review

logger = logging.getLogger(__name__)


def fallback_review_summary(place: Place, reviews: list[Review], average_rating: float) -> list[str]:
    if not reviews:
        return [
            f"{place.title}에는 아직 등록된 리뷰가 없어 방문자 반응을 단정하기 어렵습니다.",
            "첫 리뷰가 쌓이면 만족 포인트와 아쉬운 점을 함께 정리해 드릴게요.",
            "현재는 주소, 카테고리, 사진 정보를 기준으로 장소 분위기를 먼저 확인해 보세요.",
        ]

    positive = [review for review in reviews if review.rating >= 4]
    critical = [review for review in reviews if review.rating <= 2]
    review_count = len(reviews)
    positive_ratio = len(positive) / review_count

    lines = [
        f"전체 {review_count}개 리뷰 기준 평균 별점은 {average_rating:.1f}점이며, 긍정 리뷰 비중은 {positive_ratio:.0%}입니다.",
        "방문자들은 별점 흐름을 기준으로 장소의 전반적인 만족도를 판단하고 있습니다.",
    ]
    if critical:
        lines.append(f"낮은 별점 리뷰도 {len(critical)}개 있어 혼잡도나 기대와 다른 점이 있는지 함께 확인하는 편이 좋습니다.")
    else:
        lines.append("방문 전에는 사진, 위치, 연락처를 함께 확인하고 리뷰가 더 쌓이면 만족 흐름을 다시 보는 것이 좋습니다.")
    return lines


def build_review_summary(place: Place, reviews: list[Review], average_rating: float) -> list[str]:
    if not reviews:
        return fallback_review_summary(place, reviews, average_rating)

    settings = get_settings()
    if not settings.openai_api_key or settings.openai_api_key in {"replace_with_new_openai_api_key", "OPENAI_API_KEY"}:
        return fallback_review_summary(place, reviews, average_rating)

    review_context = [
        {
            "nickname": review.nickname,
            "rating": review.rating,
            "content": review.content,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
        for review in reviews[:50]
    ]

    try:
        client, _ = build_openai_client()
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.25,
            max_tokens=420,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 장소 리뷰를 요약하는 한국어 에디터다. "
                        "실제 리뷰 전체의 공통 흐름을 근거로 2~3줄의 짧은 종합 요약을 작성한다. "
                        "특정 최신 리뷰나 일부 리뷰만 강조하지 말고, 전체적인 만족 포인트와 주의점을 균형 있게 말한다. "
                        "없는 사실은 만들지 않는다."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"장소명: {place.title}\n"
                        f"분류: {place.content_type or '정보 없음'}\n"
                        f"주소: {' '.join(part for part in [place.addr1, place.addr2] if part) or '정보 없음'}\n"
                        f"평균 별점: {average_rating:.1f}\n"
                        f"리뷰 수: {len(reviews)}\n"
                        f"리뷰 데이터: {review_context}\n\n"
                        "전체 리뷰를 종합한 한국어 문장 3개를 JSON 없이 줄바꿈으로만 작성해줘. "
                        "'최근 리뷰', '최근에는'처럼 최신성 중심 표현은 쓰지 마."
                    ),
                },
            ],
        )
    except Exception as exc:
        logger.warning("Review summary generation failed: %s: %s", type(exc).__name__, exc)
        return fallback_review_summary(place, reviews, average_rating)

    content = response.choices[0].message.content if response.choices else ""
    lines = [line.strip("-*• \t") for line in (content or "").splitlines() if line.strip()]
    if len(lines) < 2:
        return fallback_review_summary(place, reviews, average_rating)
    return lines[:4]
