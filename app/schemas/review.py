from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1)
    edit_password: str = Field(min_length=1, max_length=255)


class ReviewRead(BaseModel):
    id: int
    place_id: int
    nickname: str
    rating: int
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RatingResponse(BaseModel):
    place_id: int
    average_rating: float
    review_count: int

