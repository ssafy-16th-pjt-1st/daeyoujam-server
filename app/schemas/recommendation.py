from pydantic import BaseModel, Field

from app.schemas.place import PlaceRead


class RecommendationRequest(BaseModel):
    age_group: str | None = None
    gender: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    category: str | None = Field(default=None, max_length=50)
    interests: list[str] = Field(default_factory=list)
    limit: int = Field(default=12, ge=1, le=50)


class RecommendationItem(PlaceRead):
    recommendation_reason: str


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]


class RecommendedPost(BaseModel):
    id: int
    category: str
    title: str
    content: str
    nickname: str
    view_count: int
    recommendation_reason: str


class RecommendedPostsResponse(BaseModel):
    items: list[RecommendedPost]
