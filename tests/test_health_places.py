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


def test_post_like_toggles_by_guest_id():
    created = client.post(
        "/api/v1/posts",
        json={"category": "잡담", "title": "좋아요 테스트", "content": "내용", "nickname": "tester", "edit_password": "1234"},
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    liked = client.post(f"/api/v1/posts/{post_id}/likes", json={"guest_id": "like-guest"})
    assert liked.status_code == 200
    assert liked.json()["liked_by_viewer"] is True
    assert liked.json()["like_count"] == 1

    listed = client.get("/api/v1/posts", params={"guest_id": "like-guest"})
    item = next(item for item in listed.json()["items"] if item["id"] == post_id)
    assert item["liked_by_viewer"] is True
    assert item["like_count"] == 1

    unliked = client.post(f"/api/v1/posts/{post_id}/likes", json={"guest_id": "like-guest"})
    assert unliked.status_code == 200
    assert unliked.json()["liked_by_viewer"] is False
    assert unliked.json()["like_count"] == 0


def test_posts_list_paginates():
    for index in range(2):
        created = client.post(
            "/api/v1/posts",
            json={
                "category": "잡담",
                "title": f"페이지네이션 테스트 {index}",
                "content": "내용",
                "nickname": "tester",
                "edit_password": "1234",
            },
        )
        assert created.status_code == 201

    first_page = client.get("/api/v1/posts", params={"page": 1, "limit": 1})
    second_page = client.get("/api/v1/posts", params={"page": 2, "limit": 1})

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()["total"] >= 2
    assert len(first_page.json()["items"]) == 1
    assert len(second_page.json()["items"]) == 1
    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]


def test_recommendations_shape():
    response = client.post(
        "/api/v1/recommendations",
        json={"age_group": "20대", "gender": "응답 안 함", "district": "유성구", "interests": ["음식점"], "limit": 3},
    )
    assert response.status_code == 200
    assert "items" in response.json()


def test_user_save_accepts_all_frontend_travel_styles():
    travel_styles = ["힐링", "맛집 탐방", "문화생활", "사진 촬영", "액티비티", "축제", "쇼핑", "가족 나들이", "무관"]

    for index, travel_style in enumerate(travel_styles):
        response = client.post(
            "/api/v1/users",
            json={
                "guest_id": f"frontend-style-guest-{index}",
                "nickname": "style-tester",
                "age_group": "응답 안 함",
                "gender": "응답 안 함",
                "province": "대전광역시",
                "city": "대전광역시",
                "district": "유성구",
                "interests": ["관광지"],
                "preferred_keywords": [],
                "travel_style": travel_style,
                "companion_type": "무관",
            },
        )
        assert response.status_code == 201
        assert response.json()["travel_style"] == travel_style


def test_user_save_normalizes_legacy_walk_travel_style():
    response = client.post(
        "/api/v1/users",
        json={
            "guest_id": "legacy-style-guest",
            "nickname": "legacy-style-tester",
            "age_group": "응답 안 함",
            "gender": "응답 안 함",
            "province": "대전광역시",
            "city": "대전광역시",
            "district": "유성구",
            "interests": ["관광지"],
            "preferred_keywords": [],
            "travel_style": "느긋한 산책",
            "companion_type": "무관",
        },
    )
    assert response.status_code == 201
    assert response.json()["travel_style"] == "힐링"


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
