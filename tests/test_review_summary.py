from types import SimpleNamespace

from app.ai.services.review_summary_service import fallback_review_summary


def test_fallback_review_summary_uses_overall_review_language():
    place = SimpleNamespace(title="테스트 장소")
    reviews = [
        SimpleNamespace(rating=5, content="산책하기 좋고 조용했습니다."),
        SimpleNamespace(rating=4, content="가족과 가기 괜찮았습니다."),
        SimpleNamespace(rating=2, content="주차가 조금 불편했습니다."),
    ]

    summary = fallback_review_summary(place, reviews, average_rating=3.7)
    joined = " ".join(summary)

    assert "전체 3개 리뷰 기준" in joined
    assert "최근 리뷰" not in joined
