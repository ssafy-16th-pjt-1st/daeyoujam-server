from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.place import Place
from app.models.review import Review


CONTENT_KEYWORDS = {
    "관광지": ["관광", "명소", "구경", "산책", "나들이", "자연", "풍경", "데이트"],
    "음식점": ["맛집", "음식", "밥", "식사", "카페", "빵", "디저트", "먹"],
    "문화시설": ["문화", "전시", "박물관", "공연", "실내", "아이", "가족"],
    "축제공연행사": ["축제", "행사", "공연", "이벤트"],
    "숙박": ["숙박", "호텔", "펜션", "여행", "1박"],
    "쇼핑": ["쇼핑", "시장", "기념품"],
    "레포츠": ["레포츠", "운동", "액티비티", "체험"],
    "여행코스": ["코스", "일정", "하루", "반나절", "동선"],
}


@dataclass
class RankedPlace:
    place: Place
    recommendation_reason: str
    score: float


def build_sources(places):
    return [{"place_id": place.id, "content_id": place.content_id, "title": place.title} for place in places]


def infer_categories(message: str, interests: list[str]) -> list[str]:
    categories = [interest for interest in interests if interest in CONTENT_KEYWORDS]
    for category, keywords in CONTENT_KEYWORDS.items():
        if any(keyword in message for keyword in keywords) and category not in categories:
            categories.append(category)
    return categories


def _keyword_tokens(message: str, district: str | None, interests: list[str]) -> list[str]:
    tokens = [token.strip() for token in message.replace(",", " ").split() if len(token.strip()) >= 2]
    tokens.extend([interest for interest in interests if interest])
    if district:
        tokens.append(district)
    return list(dict.fromkeys(tokens))


def retrieve_ranked_places(
    db: Session,
    *,
    message: str,
    user_profile: dict,
    limit: int = 4,
) -> list[RankedPlace]:
    district = user_profile.get("district")
    interests = user_profile.get("interests") or []
    categories = infer_categories(message, interests)
    tokens = _keyword_tokens(message, district, interests)

    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("average_rating")
    review_count = func.count(Review.id).label("review_count")

    def base_stmt():
        return select(Place, avg_rating, review_count).outerjoin(Review).group_by(Place.id)

    token_filters = []
    for token in tokens[:8]:
        pattern = f"%{token}%"
        token_filters.append(
            or_(
                Place.title.like(pattern),
                Place.addr1.like(pattern),
                Place.addr2.like(pattern),
                Place.content_type.like(pattern),
            )
        )

    candidate_conditions = []
    category_condition = Place.content_type.in_(categories) if categories else None
    district_condition = Place.addr1.like(f"%{district}%") if district else None

    if category_condition is not None and district_condition is not None:
        candidate_conditions.append(and_(category_condition, district_condition))
    if category_condition is not None:
        candidate_conditions.append(category_condition)
    if district_condition is not None:
        candidate_conditions.append(district_condition)
    if token_filters:
        candidate_conditions.append(or_(*token_filters))

    rows = []
    seen_ids = set()
    for condition in candidate_conditions:
        for row in db.execute(base_stmt().where(condition).limit(80)).all():
            place = row[0]
            if place.id in seen_ids:
                continue
            seen_ids.add(place.id)
            rows.append(row)

    if not rows:
        rows = db.execute(base_stmt().limit(80)).all()

    ranked = []
    for place, rating, count in rows:
        score = 0.0
        reasons = []
        haystack = " ".join(
            [
                place.title or "",
                place.addr1 or "",
                place.addr2 or "",
                place.content_type or "",
            ]
        )

        if district and place.addr1 and district in place.addr1:
            score += 32
            reasons.append(f"{district} 생활권")
        if place.content_type in interests:
            score += 28
            reasons.append(f"{place.content_type} 관심사")
        if place.content_type in categories:
            score += 22
            if f"{place.content_type} 관심사" not in reasons:
                reasons.append(f"질문에 맞는 {place.content_type}")
        for token in tokens:
            if token and token in haystack:
                score += 8
        score += min(float(rating or 0), 5) * 5
        score += min(int(count or 0), 10) * 1.5
        if place.first_image or place.first_image2:
            score += 4

        place.average_rating = round(float(rating or 0), 1)
        place.review_count = int(count or 0)
        if not reasons:
            reasons.append("대전·충청권 장소 데이터")
        reason = ", ".join(reasons[:3]) + "를 근거로 추천했어요."
        ranked.append(RankedPlace(place=place, recommendation_reason=reason, score=score))

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:limit]


def build_chat_answer(message: str, user_profile: dict, ranked_places: list[RankedPlace]) -> str:
    nickname = user_profile.get("nickname") or "여행자"
    district = user_profile.get("district")
    interests = user_profile.get("interests") or []
    categories = infer_categories(message, interests)

    if not ranked_places:
        return (
            "지금 조건에 맞는 장소를 찾지 못했어요. "
            "지역을 대전 전체로 넓히거나 관심사를 관광지, 음식점, 문화시설처럼 조금 더 크게 잡아서 다시 물어봐 주세요."
        )

    top_items = ranked_places[:3]
    top_titles = ", ".join(item.place.title for item in top_items)
    primary = top_items[0].place
    category_label = ", ".join(categories[:2]) if categories else primary.content_type or "장소"
    area_label = f"{district}에서 " if district else ""

    detail_bits = []
    if primary.addr1:
        detail_bits.append(f"첫 번째 추천지는 {primary.addr1}에 있어요.")
    if primary.first_image or primary.first_image2:
        detail_bits.append("사진이 있는 장소를 우선 보여드렸어요.")
    if primary.review_count:
        detail_bits.append(f"리뷰 {primary.review_count}개도 함께 참고할 수 있어요.")
    detail_sentence = " ".join(detail_bits)

    if "오늘" in message or "지금" in message:
        note = "다만 현재 데이터에는 실시간 운영 여부가 없어서 방문 전 공식 안내나 전화 확인을 권장해요."
    elif "아이" in message or "가족" in message:
        note = "아이와 함께라면 이동 거리와 실내 여부를 카드 상세에서 먼저 확인해 보세요."
    elif "맛집" in message or "먹" in message or "카페" in message:
        note = "메뉴나 영업시간은 변동될 수 있으니 상세 보기에서 위치를 확인한 뒤 한 번 더 확인해 주세요."
    else:
        note = "아래 카드에서 사진, 위치, 평점 정보를 보고 마음에 드는 곳을 자세히 볼 수 있어요."

    return (
        f"{nickname}님 질문에는 {area_label}{category_label} 쪽으로 {top_titles}를 먼저 추천할게요. "
        f"{detail_sentence} {note}"
    )
