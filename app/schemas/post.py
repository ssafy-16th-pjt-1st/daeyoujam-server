from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    nickname: str = Field(min_length=1, max_length=50)
    edit_password: str = Field(min_length=1, max_length=255)


class PostUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    edit_password: str = Field(min_length=1, max_length=255)


class PostDelete(BaseModel):
    edit_password: str = Field(min_length=1, max_length=255)


class PostRead(BaseModel):
    id: int
    category: str
    title: str
    content: str
    nickname: str
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    items: list[PostRead]
    total: int


class CommentCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    edit_password: str = Field(min_length=1, max_length=255)


class CommentDelete(BaseModel):
    edit_password: str = Field(min_length=1, max_length=255)


class CommentRead(BaseModel):
    id: int
    post_id: int
    nickname: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
