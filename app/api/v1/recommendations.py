from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.place import Place
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.review import Review
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, RecommendedPostsResponse

router = APIRouter()

STYLE_KEYWORDS = {
    "힐링": ["공원", "수목원", "휴양", "산", "호수", "둘레", "산책", "자연"],
    "맛집 탐방": ["맛", "식당", "카페", "커피", "빵", "시장", "음식", "성심당"],
    "문화생활": ["문화", "박물관", "미술관", "전시", "공연", "기념관", "극장"],
    "사진 촬영": ["전망", "야경", "공원", "거리", "스카이", "정원", "마을"],
    "액티비티": ["체험", "레포츠", "스포츠", "월드", "자전거", "등산"],
    "축제": ["축제", "공연", "행사", "페스티벌"],
    "쇼핑": ["시장", "쇼핑", "백화점", "상점", "거리"],
    "가족 나들이": ["공원", "체험", "어린이", "가족", "과학", "동물"],
}

COMPANION_KEYWORDS = {
    "혼자": ["산책", "카페", "도서관", "공원", "전시"],
    "친구": ["거리", "시장", "카페", "체험", "맛"],
    "연인": ["야경", "전망", "공원", "카페", "정원"],
    "가족": ["공원", "체험", "어린이", "가족", "과학", "동물"],
    "아이 동반": ["어린이", "체험", "과학", "동물", "공원"],
    "반려동물": ["공원", "산책", "둘레", "야외"],
}


def _is_specific_city(city: str | None) -> bool:
    if not city:
        return False
    broad_suffixes = ("광역시", "특별시", "특별자치시", "도")
    return not city.endswith(broad_suffixes)


def _place_text(place: Place) -> str:
    return " ".join(
        value
        for value in [
            place.title,
            place.content_type,
            place.addr1,
            place.addr2,
            place.category1,
            place.category2,
            place.category3,
            place.lcls_system1,
            place.lcls_system2,
            place.lcls_system3,
        ]
        if value
    )


def _keyword_score(place: Place, keywords: list[str], weight: float) -> tuple[float, list[str]]:
    text = _place_text(place)
    matched = []
    for keyword in keywords:
        normalized = keyword.strip()
        if normalized and normalized in text:
            matched.append(normalized)
    return min(len(matched), 4) * weight, matched[:3]


def _score_place(payload: RecommendationRequest, place: Place, rating: float, count: int) -> tuple[float, str]:
    score = 0.0
    reasons = []

    if payload.category and place.content_type == payload.category:
        score += 30
        reasons.append(f"{payload.category} 카테고리")
    if place.content_type in payload.interests:
        score += 45
        reasons.append(f"{place.content_type} 관심사")

    keyword_score, keyword_matches = _keyword_score(place, payload.preferred_keywords, 14)
    if keyword_score:
        score += keyword_score
        reasons.append(f"{', '.join(keyword_matches)} 키워드")

    style_keywords = STYLE_KEYWORDS.get(payload.travel_style or "", [])
    style_score, _ = _keyword_score(place, style_keywords, 8)
    if style_score:
        score += style_score
        reasons.append(f"{payload.travel_style} 스타일")

    companion_keywords = COMPANION_KEYWORDS.get(payload.companion_type or "", [])
    companion_score, _ = _keyword_score(place, companion_keywords, 6)
    if companion_score:
        score += companion_score
        reasons.append(f"{payload.companion_type} 동행")

    if payload.district and place.addr1 and payload.district in place.addr1:
        score += 42
        reasons.append(f"{payload.district} 인근")
    elif _is_specific_city(payload.city) and place.addr1 and payload.city in place.addr1:
        score += 12
        reasons.append(f"{payload.city} 생활권")

    score += min(float(rating or 0), 5) * 5
    score += min(int(count or 0), 10) * 1.5
    if place.first_image or place.first_image2:
        score += 5

    if reasons:
        return score, f"다음 조건을 반영했어요: {', '.join(reasons)}."
    return score, "평점, 리뷰 수, 사진 정보를 기준으로 추천했어요."


def _blend_categories(scored: list[tuple[float, Place, str]], limit: int) -> list[tuple[float, Place, str]]:
    buckets: dict[str, list[tuple[float, Place, str]]] = {}
    for item in scored:
        category = item[1].content_type or "기타"
        buckets.setdefault(category, []).append(item)

    max_per_category = max(2, min(4, (limit + 2) // 3))
    selected = []
    used_ids = set()

    while len(selected) < limit:
        added = False
        ranked_categories = sorted(
            buckets,
            key=lambda category: buckets[category][0][0] if buckets[category] else -1,
            reverse=True,
        )
        for category in ranked_categories:
            if len(selected) >= limit:
                break
            current_count = sum(1 for item in selected if (item[1].content_type or "기타") == category)
            if current_count >= max_per_category:
                continue
            while buckets[category] and buckets[category][0][1].id in used_ids:
                buckets[category].pop(0)
            if not buckets[category]:
                continue
            item = buckets[category].pop(0)
            selected.append(item)
            used_ids.add(item[1].id)
            added = True
        if not added:
            break

    if len(selected) < limit:
        for item in scored:
            if item[1].id in used_ids:
                continue
            selected.append(item)
            used_ids.add(item[1].id)
            if len(selected) >= limit:
                break

    return selected[:limit]


@router.post("", response_model=RecommendationResponse)
def recommend(payload: RecommendationRequest, db: Session = Depends(get_db)):
    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("average_rating")
    review_count = func.count(Review.id).label("review_count")
    stmt = select(Place, avg_rating, review_count).outerjoin(Review).group_by(Place.id)
    if payload.category:
        stmt = stmt.where(Place.content_type == payload.category)
    rows = db.execute(stmt).all()

    scored = []
    for place, rating, count in rows:
        place.average_rating = round(float(rating or 0), 1)
        place.review_count = int(count or 0)
        score, reason = _score_place(payload, place, rating, count)
        scored.append((score, place, reason))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[: payload.limit] if payload.category else _blend_categories(scored, payload.limit)

    items = []
    for _, place, reason in selected:
        item = place.__dict__.copy()
        item["average_rating"] = place.average_rating
        item["review_count"] = place.review_count
        item["recommendation_reason"] = reason
        items.append(item)
    return {"items": items}


@router.post("/posts", response_model=RecommendedPostsResponse)
def recommend_posts(payload: RecommendationRequest, db: Session = Depends(get_db)):
    recent_cutoff = datetime.now() - timedelta(days=2)
    like_count = func.count(PostLike.id).label("like_count")
    rows = db.execute(
        select(Post, like_count)
        .outerjoin(PostLike)
        .where(Post.created_at >= recent_cutoff)
        .group_by(Post.id)
        .order_by(Post.view_count.desc(), Post.id.desc())
        .limit(payload.limit)
    ).all()
    keywords = [payload.district or "", *payload.interests, *payload.preferred_keywords]
    items = []
    for post, count in rows:
        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword and (keyword in post.title or keyword in post.content or keyword in post.category)
        ][:2]
        reason = (
            f"최근 2일 내 조회수가 높은 {post.category} 관심 글이에요."
            if post.category in payload.interests
            else "최근 2일 내 조회수가 높은 지역 이야기예요."
        )
        if matched_keywords:
            reason += f" 관련 키워드: {', '.join(matched_keywords)}."
        items.append(
            {
                "id": post.id,
                "category": post.category,
                "title": post.title,
                "content": post.content,
                "nickname": post.nickname,
                "view_count": post.view_count,
                "like_count": int(count or 0),
                "recommendation_reason": reason,
            }
        )
    return {"items": items}
