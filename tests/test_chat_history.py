from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_is_saved_and_loaded_by_guest_id():
    guest_id = "chat-history-guest"

    response = client.post(
        "/api/ai/chat",
        json={
            "guest_id": guest_id,
            "message": "유성구 맛집 알려줘",
            "user_profile": {"nickname": "아나", "district": "유성구", "interests": ["음식점"]},
            "limit": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]

    history = client.get("/api/ai/chat/history", params={"guest_id": guest_id})
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["session_id"] == body["session_id"]
    assert [message["role"] for message in history_body["messages"][-2:]] == ["user", "bot"]
    assert history_body["messages"][-2]["text"] == "유성구 맛집 알려줘"
    assert history_body["messages"][-1]["places"]


def test_security_blocked_chat_is_saved_without_places():
    guest_id = "chat-security-guest"

    response = client.post(
        "/api/ai/chat",
        json={
            "guest_id": guest_id,
            "message": ".env",
            "user_profile": {"nickname": "아나", "district": "유성구", "interests": ["쇼핑"]},
        },
    )
    assert response.status_code == 200
    assert response.json()["places"] == []

    history = client.get("/api/ai/chat/history", params={"guest_id": guest_id})
    messages = history.json()["messages"]
    assert messages[-1]["places"] == []
    assert "보안상 제공할 수 없어요" in messages[-1]["text"]


def test_chat_history_can_be_deleted():
    guest_id = "chat-delete-guest"
    created = client.post(
        "/api/ai/chat",
        json={
            "guest_id": guest_id,
            "message": "성심당 어디있어?",
            "user_profile": {"nickname": "아나", "district": "중구", "interests": ["음식점"]},
        },
    )
    assert created.status_code == 200

    deleted = client.delete("/api/ai/chat/history", params={"guest_id": guest_id})
    assert deleted.status_code == 204

    history = client.get("/api/ai/chat/history", params={"guest_id": guest_id})
    assert history.status_code == 200
    assert history.json() == {"session_id": None, "messages": []}
