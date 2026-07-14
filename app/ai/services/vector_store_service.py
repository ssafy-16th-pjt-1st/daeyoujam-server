from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.place import Place

TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "") if len(token) >= 2]


def _ngrams(token: str) -> list[str]:
    if len(token) <= 2:
        return [token]
    return [token[index : index + 2] for index in range(len(token) - 1)]


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    vector = [0.0] * settings.vector_embedding_dim
    for token in _tokens(text):
        features = [token, *_ngrams(token)]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % settings.vector_embedding_dim
            sign = 1 if digest[4] % 2 == 0 else -1
            vector[index] += sign / math.sqrt(len(features))

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


def build_place_document(place: Place) -> str:
    fields = [
        f"장소명 {place.title}",
        f"분류 {place.content_type}",
        f"주소 {place.addr1} {place.addr2 or ''}",
        f"카테고리 {place.category1 or ''} {place.category2 or ''} {place.category3 or ''}",
        f"시스템분류 {place.lcls_system1 or ''} {place.lcls_system2 or ''} {place.lcls_system3 or ''}",
    ]
    return "\n".join(part for part in fields if part and part.strip())


def build_user_query_document(message: str, user_profile: dict) -> str:
    interests = user_profile.get("interests") or []
    profile_parts = [
        f"질문 {message}",
        f"생활권 {user_profile.get('district') or ''}",
        f"연령대 {user_profile.get('age_group') or ''}",
        f"성별 {user_profile.get('gender') or ''}",
        f"관심사 {' '.join(interests)}",
    ]
    return "\n".join(part for part in profile_parts if part and part.strip())


@lru_cache
def _get_collection():
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    settings = get_settings()
    client = chromadb.PersistentClient(
        path=settings.vector_store_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.vector_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def ensure_place_vector_index(db: Session) -> None:
    collection = _get_collection()
    places = db.scalars(select(Place)).all()
    expected_count = len(places)
    if expected_count and collection.count() == expected_count:
        return

    ids = [str(place.id) for place in places]
    if ids:
        collection.delete(ids=ids)

    batch_size = 128
    for offset in range(0, len(places), batch_size):
        batch = places[offset : offset + batch_size]
        documents = [build_place_document(place) for place in batch]
        collection.add(
            ids=[str(place.id) for place in batch],
            documents=documents,
            embeddings=[embed_text(document) for document in documents],
            metadatas=[
                {
                    "place_id": place.id,
                    "content_type": place.content_type or "",
                    "title": place.title or "",
                    "addr1": place.addr1 or "",
                }
                for place in batch
            ],
        )


def retrieve_place_ids_by_vector(db: Session, message: str, user_profile: dict, limit: int = 80) -> list[int]:
    ensure_place_vector_index(db)
    query_document = build_user_query_document(message, user_profile)
    result = _get_collection().query(
        query_embeddings=[embed_text(query_document)],
        n_results=limit,
        include=["metadatas", "distances"],
    )
    ids = result.get("ids", [[]])[0]
    return [int(place_id) for place_id in ids]
