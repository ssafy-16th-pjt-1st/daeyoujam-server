from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.place import Place
from app.models.post import Post
from app.models.review import Review
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, RecommendedPostsResponse

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
def recommend(payload: RecommendationRequest, db: Session = Depends(get_db)):
    avg_rating = func.coalesce(func.avg(Review.rating), 0).label("average_rating")
    review_count = func.count(Review.id).label("review_count")
    rows = db.execute(select(Place, avg_rating, review_count).outerjoin(Review).group_by(Place.id)).all()

    scored = []
    for place, rating, count in rows:
        score = 0
        reasons = []
        if place.content_type in payload.interests:
            score += 40
            reasons.append(f"{place.content_type} 관심사")
        if payload.district and place.addr1 and payload.district in place.addr1:
            score += 25
            reasons.append(f"{payload.district} 지역")
        score += min(float(rating or 0), 5) * 6
        score += min(int(count or 0), 10) * 2
        if place.first_image or place.first_image2:
            score += 5
        place.average_rating = round(float(rating or 0), 1)
        place.review_count = int(count or 0)
        reason = ", ".join(reasons) + "를 함께 반영한 추천이에요." if reasons else "대전·충청권 인기 장소 후보예요."
        scored.append((score, place, reason))

    scored.sort(key=lambda item: item[0], reverse=True)
    items = []
    for _, place, reason in scored[: payload.limit]:
        item = place.__dict__.copy()
        item["average_rating"] = place.average_rating
        item["review_count"] = place.review_count
        item["recommendation_reason"] = reason
        items.append(item)
    return {"items": items}


@router.post("/posts", response_model=RecommendedPostsResponse)
def recommend_posts(payload: RecommendationRequest, db: Session = Depends(get_db)):
    posts = db.scalars(select(Post).order_by(Post.id.desc()).limit(100)).all()
    keywords = [payload.district or "", *payload.interests]
    scored = []
    for post in posts:
        score = 0
        if post.category in payload.interests:
            score += 30
        for keyword in keywords:
            if keyword and (keyword in post.title or keyword in post.content or keyword in post.category):
                score += 10
        score += min(post.view_count, 20)
        reason = f"{post.category} 관심사와 최근 지역 이야기를 반영했어요." if post.category in payload.interests else "최근 올라온 지역 이야기예요."
        scored.append((score, post, reason))
    scored.sort(key=lambda item: item[0], reverse=True)
    return {
        "items": [
            {
                "id": post.id,
                "category": post.category,
                "title": post.title,
                "content": post.content,
                "nickname": post.nickname,
                "view_count": post.view_count,
                "recommendation_reason": reason,
            }
            for _, post, reason in scored[:6]
        ]
    }
