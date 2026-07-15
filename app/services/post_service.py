from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.post import Post
from app.models.post_like import PostLike
from app.repositories import post_repository
from app.schemas.post import CommentCreate, CommentDelete, PostCreate, PostDelete, PostUpdate


def list_posts(db: Session, *, q: str = "", category: str | None = None, limit: int = 30, guest_id: str | None = None):
    items, total = post_repository.list_posts(db, q=q, category=category, limit=limit)
    attach_like_state(db, items, guest_id)
    return {"items": items, "total": total}


def get_post_or_404(db: Session, post_id: int):
    post = post_repository.get_post(db, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    return post


def read_post(db: Session, post_id: int, guest_id: str | None = None):
    post = get_post_or_404(db, post_id)
    post.view_count += 1
    db.commit()
    db.refresh(post)
    attach_like_state(db, [post], guest_id)
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

def verify_post_password(db: Session, post_id: int, edit_password: str):
    post = get_post_or_404(db, post_id)
    _ensure_edit_password(post.edit_password, edit_password)
    return True


def attach_like_state(db: Session, posts: list[Post], guest_id: str | None = None) -> None:
    if not posts:
        return
    post_ids = [post.id for post in posts]
    count_rows = db.execute(
        select(PostLike.post_id, func.count(PostLike.id)).where(PostLike.post_id.in_(post_ids)).group_by(PostLike.post_id)
    ).all()
    counts = {post_id: int(count) for post_id, count in count_rows}
    liked_ids = set()
    if guest_id:
        liked_ids = set(
            db.scalars(
                select(PostLike.post_id).where(PostLike.post_id.in_(post_ids), PostLike.guest_id == guest_id)
            ).all()
        )
    for post in posts:
        post.like_count = counts.get(post.id, 0)
        post.liked_by_viewer = post.id in liked_ids


def toggle_post_like(db: Session, post_id: int, guest_id: str):
    get_post_or_404(db, post_id)
    like = db.scalars(select(PostLike).where(PostLike.post_id == post_id, PostLike.guest_id == guest_id)).first()
    liked = False
    if like:
        db.delete(like)
    else:
        db.add(PostLike(post_id=post_id, guest_id=guest_id))
        liked = True
    db.commit()
    like_count = db.scalar(select(func.count(PostLike.id)).where(PostLike.post_id == post_id)) or 0
    return {"post_id": post_id, "like_count": int(like_count), "liked_by_viewer": liked}
