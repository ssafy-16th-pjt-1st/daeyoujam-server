def fallback_review_summary(review_count: int):
    if review_count < 3:
        return ["리뷰가 더 쌓이면 AI 브리핑을 제공할 수 있어요."]
    return ["리뷰 요약 생성 준비가 완료되었습니다."]

