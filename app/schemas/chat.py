from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.place import PlaceRead


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    guest_id: str | None = Field(default=None, max_length=64)
    session_id: int | None = None
    user_profile: dict = Field(default_factory=dict)
    limit: int = Field(default=4, ge=1, le=8)


class ChatPlace(PlaceRead):
    recommendation_reason: str


class ChatResponse(BaseModel):
    answer: str
    places: list[ChatPlace]
    sources: list[dict]
    session_id: int | None = None


class ChatHistoryMessage(BaseModel):
    id: int
    role: str
    text: str
    places: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    session_id: int | None = None
    messages: list[ChatHistoryMessage] = Field(default_factory=list)
