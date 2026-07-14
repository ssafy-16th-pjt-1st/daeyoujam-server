from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.comment import Comment
from app.models.post import Post
from app.schemas.post import CommentCreate, CommentDelete, CommentRead, PostCreate, PostDelete, PostListResponse, PostRead, PostUpdate

router = APIRouter()


@router.get("", response_model=PostListResponse)
def list_posts(q: str = "", category: str | None = None, limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(Post)
    count_stmt = select(func.count(Post.id))
    if category:
        stmt = stmt.where(Post.category == category)
        count_stmt = count_stmt.where(Post.category == category)
    if q.strip():
        pattern = f"%{q.strip()}%"
        condition = or_(Post.title.like(pattern), Post.content.like(pattern), Post.category.like(pattern))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    items = db.scalars(stmt.order_by(Post.id.desc()).limit(limit)).all()
    return {"items": items, "total": db.scalar(count_stmt) or 0}


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return post


@router.post("", response_model=PostRead, status_code=201)
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    post = Post(**payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.put("/{post_id}", response_model=PostRead)
def update_post(post_id: int, payload: PostUpdate, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.edit_password != payload.edit_password:
        raise HTTPException(status_code=403, detail="Invalid edit password")
    post.title = payload.title
    post.category = payload.category
    post.content = payload.content
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
def delete_post(post_id: int, payload: PostDelete, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.edit_password != payload.edit_password:
        raise HTTPException(status_code=403, detail="Invalid edit password")
    db.delete(post)
    db.commit()


@router.get("/{post_id}/comments", response_model=list[CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    if not db.get(Post, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    return db.scalars(select(Comment).where(Comment.post_id == post_id).order_by(Comment.id.asc())).all()


@router.post("/{post_id}/comments", response_model=CommentRead, status_code=201)
def create_comment(post_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    if not db.get(Post, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(post_id=post_id, **payload.model_dump())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/{post_id}/comments/{comment_id}", status_code=204)
def delete_comment(post_id: int, comment_id: int, payload: CommentDelete, db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    if not comment or comment.post_id != post_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.edit_password != payload.edit_password:
        raise HTTPException(status_code=403, detail="Invalid edit password")
    db.delete(comment)
    db.commit()
