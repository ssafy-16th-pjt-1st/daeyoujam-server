from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_places_list_shape():
    response = client.get("/api/v1/places")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body


def test_post_create_read_and_wrong_password_update():
    created = client.post(
        "/api/v1/posts",
        json={"category": "음식점", "title": "테스트 글", "content": "내용", "nickname": "tester", "edit_password": "1234"},
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    read = client.get(f"/api/v1/posts/{post_id}")
    assert read.status_code == 200
    assert read.json()["title"] == "테스트 글"

    failed = client.put(
        f"/api/v1/posts/{post_id}",
        json={"category": "음식점", "title": "수정", "content": "수정", "edit_password": "wrong"},
    )
    assert failed.status_code == 403


def test_recommendations_shape():
    response = client.post(
        "/api/v1/recommendations",
        json={"age_group": "20대", "gender": "응답 안 함", "district": "유성구", "interests": ["음식점"], "limit": 3},
    )
    assert response.status_code == 200
    assert "items" in response.json()


def test_recommendations_respect_selected_category():
    response = client.post(
        "/api/v1/recommendations",
        json={
            "age_group": "20대",
            "gender": "응답 안 함",
            "district": "유성구",
            "category": "문화시설",
            "interests": ["음식점"],
            "limit": 5,
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["content_type"] == "문화시설" for item in items)


def test_comment_delete_requires_password():
    created = client.post(
        "/api/v1/posts",
        json={"category": "잡담", "title": "댓글 테스트", "content": "내용", "nickname": "tester", "edit_password": "1234"},
    )
    post_id = created.json()["id"]
    comment = client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"nickname": "commenter", "content": "댓글", "edit_password": "abcd"},
    )
    comment_id = comment.json()["id"]

    wrong = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}/comments/{comment_id}",
        json={"edit_password": "wrong"},
    )
    assert wrong.status_code == 403

    deleted = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}/comments/{comment_id}",
        json={"edit_password": "abcd"},
    )
    assert deleted.status_code == 204


def test_review_uses_saved_user_nickname():
    places = client.get("/api/v1/places")
    assert places.status_code == 200
    place_id = places.json()["items"][0]["id"]

    user = client.post(
        "/api/v1/users",
        json={
            "guest_id": "review-guest",
            "nickname": "saved-nickname",
            "province": "Daejeon",
            "city": "Daejeon",
            "interests": [],
            "preferred_keywords": [],
        },
    )
    assert user.status_code == 201

    review = client.post(
        f"/api/v1/places/{place_id}/reviews",
        json={
            "guest_id": "review-guest",
            "nickname": "forged-nickname",
            "rating": 5,
            "content": "good",
            "edit_password": "1234",
        },
    )
    assert review.status_code == 201
    assert review.json()["nickname"] == "saved-nickname"
