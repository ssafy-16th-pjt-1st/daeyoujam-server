from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.post import Post
from app.schemas.post import CommentCreate, PostCreate, PostUpdate


def list_posts(
    db: Session,
    *,
    q: str = "",
    category: str | None = None,
    limit: int = 30,
) -> tuple[list[Post], int]:
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
    total = db.scalar(count_stmt) or 0
    return items, total


def get_post(db: Session, post_id: int) -> Post | None:
    return db.get(Post, post_id)


def create_post(db: Session, payload: PostCreate) -> Post:
    post = Post(**payload.model_dump())
    db.add(post)
    return post


def update_post(post: Post, payload: PostUpdate) -> Post:
    post.title = payload.title
    post.category = payload.category
    post.content = payload.content
    return post


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)


def list_comments(db: Session, post_id: int) -> list[Comment]:
    return db.scalars(select(Comment).where(Comment.post_id == post_id).order_by(Comment.id.asc())).all()


def get_comment(db: Session, comment_id: int) -> Comment | None:
    return db.get(Comment, comment_id)


def create_comment(db: Session, post_id: int, payload: CommentCreate) -> Comment:
    comment = Comment(post_id=post_id, **payload.model_dump())
    db.add(comment)
    return comment


def delete_comment(db: Session, comment: Comment) -> None:
    db.delete(comment)

