import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession


def get_or_create_chat_session(db: Session, guest_id: str, session_id: int | None = None) -> ChatSession:
    session = None
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.guest_id != guest_id:
            session = None
    if not session:
        session = db.scalars(
            select(ChatSession).where(ChatSession.guest_id == guest_id).order_by(desc(ChatSession.updated_at), desc(ChatSession.id))
        ).first()
    if not session:
        session = ChatSession(guest_id=guest_id)
        db.add(session)
        db.flush()
    return session


def get_latest_chat_session(db: Session, guest_id: str) -> ChatSession | None:
    return db.scalars(
        select(ChatSession).where(ChatSession.guest_id == guest_id).order_by(desc(ChatSession.updated_at), desc(ChatSession.id))
    ).first()


def get_chat_session(db: Session, guest_id: str, session_id: int) -> ChatSession | None:
    return db.scalars(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.guest_id == guest_id)
    ).first()


def add_chat_message(
    db: Session,
    *,
    session: ChatSession,
    role: str,
    content: str,
    places: list[dict] | None = None,
    sources: list[dict] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session.id,
        role=role,
        content=content,
        places_json=json.dumps(places or [], ensure_ascii=False),
        sources_json=json.dumps(sources or [], ensure_ascii=False),
    )
    db.add(message)
    return message


def serialize_chat_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "text": message.content,
        "places": _loads_json_list(message.places_json),
        "sources": _loads_json_list(message.sources_json),
        "created_at": message.created_at,
    }


def serialize_chat_messages(messages: list[ChatMessage]) -> list[dict]:
    return [serialize_chat_message(message) for message in messages]


def clear_chat_history(db: Session, guest_id: str) -> None:
    sessions = db.scalars(select(ChatSession).where(ChatSession.guest_id == guest_id)).all()
    for session in sessions:
        db.delete(session)


def _loads_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []
