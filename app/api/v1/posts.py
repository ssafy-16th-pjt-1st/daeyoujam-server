from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.post import (
    CommentCreate,
    CommentDelete,
    CommentRead,
    PostCreate,
    PostDelete,
    PostListResponse,
    PostLikeResponse,
    PostLikeToggle,
    PostRead,
    PostUpdate,
)
from app.services import post_service

router = APIRouter()

@router.post("/{post_id}/verify")
def verify_post_password(post_id: int, payload: PostDelete, db: Session = Depends(get_db)):
    print(f"디버그: verify 요청 도달! ID={post_id}, 데이터={payload}")
    # 서비스 계층 호출
    post_service.verify_post_password(db, post_id, payload.edit_password)
    return {"message": "Success"}

@router.get("", response_model=PostListResponse)
def list_posts(
    q: str = "",
    category: str | None = None,
    guest_id: str | None = Query(default=None, max_length=64),
    limit: int = Query(30, ge=1, le=100),
    sort: str = Query("recent", pattern="^(recent|likes|views)$"),
    db: Session = Depends(get_db),
):
    return post_service.list_posts(db, q=q, category=category, limit=limit, guest_id=guest_id, sort=sort)

@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, guest_id: str | None = Query(default=None, max_length=64), db: Session = Depends(get_db)):
    return post_service.read_post(db, post_id, guest_id=guest_id)


@router.post("/{post_id}/likes", response_model=PostLikeResponse)
def toggle_post_like(post_id: int, payload: PostLikeToggle, db: Session = Depends(get_db)):
    return post_service.toggle_post_like(db, post_id, payload.guest_id)


@router.post("", response_model=PostRead, status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    return post_service.create_post(db, payload)


@router.put("/{post_id}", response_model=PostRead)
def update_post(post_id: int, payload: PostUpdate, db: Session = Depends(get_db)):
    return post_service.update_post(db, post_id, payload)


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, payload: PostDelete, db: Session = Depends(get_db)):
    post_service.delete_post(db, post_id, payload)


@router.get("/{post_id}/comments", response_model=list[CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    return post_service.list_comments(db, post_id)


@router.post("/{post_id}/comments", response_model=CommentRead, status_code=201)
def create_comment(post_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    return post_service.create_comment(db, post_id, payload)


@router.delete("/{post_id}/comments/{comment_id}", status_code=204)
def delete_comment(post_id: int, comment_id: int, payload: CommentDelete, db: Session = Depends(get_db)):
    post_service.delete_comment(db, post_id, comment_id, payload)


