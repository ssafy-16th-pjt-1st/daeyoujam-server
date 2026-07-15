from app.ai.services.rag_service import retrieve_ranked_places
from app.core.database import SessionLocal


def test_named_place_anchor_ignores_profile_district():
    db = SessionLocal()
    try:
        ranked = retrieve_ranked_places(
            db,
            message="성심당 어디있어?",
            user_profile={"nickname": "아나", "district": "유성구", "interests": ["음식점"]},
            limit=4,
        )
    finally:
        db.close()

    assert ranked
    assert ranked[0].place.title == "성심당"


def test_museum_question_returns_culture_places():
    db = SessionLocal()
    try:
        ranked = retrieve_ranked_places(
            db,
            message="박물관 아는거 알아?",
            user_profile={"nickname": "아나", "district": "유성구", "interests": ["음식점"]},
            limit=4,
        )
    finally:
        db.close()

    assert ranked
    assert all(item.place.content_type == "문화시설" for item in ranked)
    assert any("박물관" in item.place.title for item in ranked)


def test_cafe_question_returns_cafes():
    db = SessionLocal()
    try:
        ranked = retrieve_ranked_places(
            db,
            message="안녕 근처 카페",
            user_profile={"nickname": "아나", "district": "유성구", "interests": ["음식점"]},
            limit=4,
        )
    finally:
        db.close()

    assert ranked
    assert all(item.place.content_type == "음식점" for item in ranked)
    assert any("카페" in item.place.title or "커피" in item.place.title for item in ranked)
