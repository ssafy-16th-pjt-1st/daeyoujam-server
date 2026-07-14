from fastapi import APIRouter

from app.api.v1 import places, posts, recommendations, reviews, users

api_router = APIRouter()
api_router.include_router(places.router, prefix="/api/v1/places", tags=["places"])
api_router.include_router(posts.router, prefix="/api/v1/posts", tags=["posts"])
api_router.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
api_router.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
api_router.include_router(users.router, prefix="/api/v1/users", tags=["users"])
