from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.services.vector_store_service import retrieve_place_ids_by_vector
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

TERM_EXPANSIONS = {
    "카페": ["카페", "커피", "로스터리", "디저트", "베이커리"],
    "커피": ["커피", "카페", "로스터리"],
    "빵": ["빵", "베이커리", "제과", "성심당"],
    "디저트": ["디저트", "빵", "베이커리"],
    "성심당": ["성심당", "빵", "베이커리", "음식점"],
    "실내": ["실내", "전시", "박물관", "문화", "공연"],
    "산책": ["산책", "공원", "수목원", "호수", "거리"],
}

STOPWORDS = {
    "추천",
    "추천해줘",
    "알려줘",
    "알아",
    "어디",
    "근처",
    "주변",
    "가까운",
    "같이",
    "갈",
    "만한",
    "좋은",
    "장소",
    "일정",
    "분위기",
    "오늘",
    "내일",
    "대전",
    "대전광역시",
}

DISTRICTS = ["동구", "중구", "서구", "유성구", "대덕구"]
CAFE_TERMS = {"카페", "커피", "로스터리", "디저트"}
BAKERY_TERMS = {"빵", "베이커리", "제과", "성심당"}


@dataclass
class RankedPlace:
    place: Place
    recommendation_reason: str
    score: float


@dataclass
class QueryIntent:
    district: str | None
    interests: list[str]
    categories: list[str]
    tokens: list[str]
    focus_terms: list[str]
    anchor: Place | None
    near_anchor: bool


def build_sources(places):
    return [{"place_id": place.id, "content_id": place.content_id, "title": place.title} for place in places]


def infer_categories(message: str, interests: list[str]) -> list[str]:
    categories = [interest for interest in interests if interest in CONTENT_KEYWORDS]
    for category, keywords in CONTENT_KEYWORDS.items():
        if any(keyword in message for keyword in keywords) and category not in categories:
            categories.append(category)
    return categories


def _keyword_tokens(message: str, district: str | None, interests: list[str]) -> list[str]:
    tokens = [token.strip() for token in re.split(r"[\s,.;!?/]+", message) if len(token.strip()) >= 2]
    tokens.extend([interest for interest in interests if interest])
    if district:
        tokens.append(district)
    return list(dict.fromkeys(tokens))


def _expanded_terms(tokens: list[str]) -> list[str]:
    expanded = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        expanded.append(token)
        expanded.extend(TERM_EXPANSIONS.get(token, []))
    return list(dict.fromkeys(term for term in expanded if term and term not in STOPWORDS))


def _place_document(place: Place) -> str:
    return " ".join(
        part
        for part in [
            place.title,
            place.addr1,
            place.addr2,
            place.content_type,
            place.category1,
            place.category2,
            place.category3,
            place.lcls_system1,
            place.lcls_system2,
            place.lcls_system3,
        ]
        if part
    )


def _find_anchor_place(db: Session, message: str) -> Place | None:
    candidates = db.scalars(select(Place).where(Place.title.is_not(None))).all()
    matched = [place for place in candidates if place.title and place.title in message]
    if not matched:
        return None
    exact = [place for place in matched if place.title == message.strip()]
    pool = exact or matched
    return sorted(pool, key=lambda place: len(place.title or ""), reverse=True)[0]


def _distance_km(origin: Place | None, place: Place) -> float | None:
    if not origin or origin.mapx is None or origin.mapy is None or place.mapx is None or place.mapy is None:
        return None

    lon1, lat1, lon2, lat2 = map(radians, [origin.mapx, origin.mapy, place.mapx, place.mapy])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    haversine = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(haversine))


def _build_intent(db: Session, message: str, user_profile: dict) -> QueryIntent:
    district = next((name for name in DISTRICTS if name in message), None) or user_profile.get("district")
    interests = user_profile.get("interests") or []
    categories = infer_categories(message, interests)
    tokens = _keyword_tokens(message, district, interests)
    anchor = _find_anchor_place(db, message)
    anchor_tokens = set(_keyword_tokens(anchor.title, None, []) if anchor else [])
    anchor_expanded_terms = set(_expanded_terms(list(anchor_tokens)))
    message_tokens = _keyword_tokens(message, district, [])
    focus_terms = [
        term
        for term in _expanded_terms(message_tokens)
        if term not in anchor_tokens and term not in anchor_expanded_terms and term not in CONTENT_KEYWORDS
    ]
    near_anchor = bool(anchor and any(keyword in message for keyword in ["근처", "주변", "가까운", "인근"]))
    return QueryIntent(
        district=district,
        interests=interests,
        categories=categories,
        tokens=tokens,
        focus_terms=focus_terms,
        anchor=anchor,
        near_anchor=near_anchor,
    )


def _score_place(
    place: Place,
    rating: float,
    count: int,
    intent: QueryIntent,
    vector_rank: int | None = None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []
    document = _place_document(place)
    title = place.title or ""
    title_terms = set(term for term in CAFE_TERMS | BAKERY_TERMS if term in title)

    if intent.anchor and place.id == intent.anchor.id:
        if intent.near_anchor:
            score -= 80
        else:
            score += 120
            reasons.append("질문에서 직접 언급한 장소")

    if CAFE_TERMS.intersection(intent.focus_terms):
        if CAFE_TERMS.intersection(title_terms):
            score += 42
            reasons.append("카페 키워드와 직접 일치")
        else:
            score -= 34

    if BAKERY_TERMS.intersection(intent.focus_terms):
        if BAKERY_TERMS.intersection(title_terms):
            score += 28
            reasons.append("베이커리 키워드와 직접 일치")

    if intent.categories and place.content_type not in intent.categories:
        score -= 55
    elif place.content_type in intent.categories:
        score += 36
        reasons.append(f"질문 의도와 맞는 {place.content_type}")

    if intent.district and place.addr1 and intent.district in place.addr1:
        score += 16
        reasons.append(f"{intent.district} 생활권")

    for term in intent.focus_terms:
        if term in title:
            score += 24
            reasons.append(f"'{term}' 키워드와 일치")
        elif term in document:
            score += 9

    if intent.anchor:
        distance = _distance_km(intent.anchor, place)
        if place.id != intent.anchor.id and distance is not None:
            if distance <= 1:
                score += 38
                reasons.append(f"{intent.anchor.title}에서 약 {distance:.1f}km")
            elif distance <= 3:
                score += 28
                reasons.append(f"{intent.anchor.title}에서 약 {distance:.1f}km")
            elif distance <= 8:
                score += 12
            elif intent.near_anchor:
                score -= min(distance, 30)

    if place.content_type in intent.interests:
        score += 12

    score += min(float(rating or 0), 5) * 4
    score += min(int(count or 0), 10) * 1.2
    if place.first_image or place.first_image2:
        score += 4

    if vector_rank is not None:
        score += max(8, 48 - vector_rank * 0.8)
        reasons.insert(0, "프로필과 질문의 의미 유사도")

    if not reasons:
        reasons.append("질문과 장소 정보의 유사도")

    return score, list(dict.fromkeys(reasons))[:3]


def _query_candidate_rows(db: Session, intent: QueryIntent, vector_ids: list[int], limit: int):
    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("average_rating")
    review_count = func.count(Review.id).label("review_count")

    candidate_ids = set(vector_ids[: max(limit * 8, 40)])
    if intent.anchor:
        candidate_ids.add(intent.anchor.id)

    token_filters = []
    for token in intent.tokens[:10]:
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
    if candidate_ids:
        candidate_conditions.append(Place.id.in_(candidate_ids))
    if intent.categories:
        candidate_conditions.append(Place.content_type.in_(intent.categories))
    if intent.district:
        candidate_conditions.append(Place.addr1.like(f"%{intent.district}%"))
    if token_filters:
        candidate_conditions.append(or_(*token_filters))

    stmt = select(Place, avg_rating, review_count).outerjoin(Review).group_by(Place.id)
    if candidate_conditions:
        stmt = stmt.where(or_(*candidate_conditions))
    return db.execute(stmt).all()


def retrieve_ranked_places(
    db: Session,
    *,
    message: str,
    user_profile: dict,
    limit: int = 4,
) -> list[RankedPlace]:
    intent = _build_intent(db, message, user_profile)

    try:
        vector_ids = retrieve_place_ids_by_vector(db, message, user_profile, limit=120)
    except Exception:
        vector_ids = []
    vector_rank_by_id = {place_id: rank for rank, place_id in enumerate(vector_ids)}

    rows = _query_candidate_rows(db, intent, vector_ids, limit)

    ranked = []
    for place, rating, count in rows:
        score, reasons = _score_place(
            place,
            float(rating or 0),
            int(count or 0),
            intent,
            vector_rank=vector_rank_by_id.get(place.id),
        )
        place.average_rating = round(float(rating or 0), 1)
        place.review_count = int(count or 0)
        reason = ", ".join(reasons[:3]) + "를 근거로 추천했어요."
        ranked.append(RankedPlace(place=place, recommendation_reason=reason, score=score))

    ranked.sort(key=lambda item: item.score, reverse=True)
    if intent.anchor and not intent.near_anchor and not intent.focus_terms:
        anchor_ranked = [item for item in ranked if item.place.id == intent.anchor.id]
        if anchor_ranked:
            return anchor_ranked[:1]
    return ranked[:limit]


def build_chat_answer(message: str, user_profile: dict, ranked_places: list[RankedPlace]) -> str:
    nickname = user_profile.get("nickname") or "여행자"
    district = user_profile.get("district")
    interests = user_profile.get("interests") or []
    categories = infer_categories(message, interests)

    if not ranked_places:
        return (
            "지금 조건에 맞는 장소를 찾지 못했어요. "
            "지역을 더 넓히거나 관심사를 관광지, 음식점, 문화시설처럼 조금 더 크게 잡아 다시 물어봐 주세요."
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

    if primary.title and primary.title in message:
        note = "아래 카드에서 위치, 사진, 별점과 리뷰를 바로 확인할 수 있어요."
    elif "오늘" in message or "지금" in message:
        note = "다만 현재 데이터에는 실시간 운영 여부가 없어 방문 전 공식 안내나 전화 확인을 권장해요."
    elif "아이" in message or "가족" in message:
        note = "아이와 함께라면 이동 거리와 실내 여부를 카드 상세에서 먼저 확인해 보세요."
    elif "맛집" in message or "먹" in message or "카페" in message:
        note = "메뉴와 영업시간은 변동될 수 있으니 상세 보기에서 위치를 확인한 뒤 한 번 더 확인해 주세요."
    else:
        note = "아래 카드에서 사진, 위치, 평점 정보를 보고 마음에 드는 곳을 자세히 볼 수 있어요."

    return (
        f"{nickname}님 질문에는 {area_label}{category_label} 쪽으로 {top_titles} 먼저 추천할게요. "
        f"{detail_sentence} {note}"
    )
