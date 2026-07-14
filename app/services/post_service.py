from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories import post_repository
from app.schemas.post import CommentCreate, CommentDelete, PostCreate, PostDelete, PostUpdate


def list_posts(db: Session, *, q: str = "", category: str | None = None, limit: int = 30):
    items, total = post_repository.list_posts(db, q=q, category=category, limit=limit)
    return {"items": items, "total": total}


def get_post_or_404(db: Session, post_id: int):
    post = post_repository.get_post(db, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    return post


def read_post(db: Session, post_id: int):
    post = get_post_or_404(db, post_id)
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return post


def create_post(db: Session, payload: PostCreate):
    post = post_repository.create_post(db, payload)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post_id: int, payload: PostUpdate):
    post = get_post_or_404(db, post_id)
    _ensure_edit_password(post.edit_password, payload.edit_password)
    post_repository.update_post(post, payload)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post_id: int, payload: PostDelete) -> None:
    post = get_post_or_404(db, post_id)
    _ensure_edit_password(post.edit_password, payload.edit_password)
    post_repository.delete_post(db, post)
    db.commit()


def list_comments(db: Session, post_id: int):
    get_post_or_404(db, post_id)
    return post_repository.list_comments(db, post_id)


def create_comment(db: Session, post_id: int, payload: CommentCreate):
    get_post_or_404(db, post_id)
    comment = post_repository.create_comment(db, post_id, payload)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, post_id: int, comment_id: int, payload: CommentDelete) -> None:
    comment = post_repository.get_comment(db, comment_id)
    if comment is None or comment.post_id != post_id:
        raise NotFoundError("Comment not found")
    _ensure_edit_password(comment.edit_password, payload.edit_password)
    post_repository.delete_comment(db, comment)
    db.commit()


def _ensure_edit_password(actual_password: str, submitted_password: str) -> None:
    if actual_password != submitted_password:
        raise ForbiddenError("Invalid edit password")

