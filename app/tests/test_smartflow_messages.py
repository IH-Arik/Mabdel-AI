from __future__ import annotations

import asyncio

from app.core.realtime import conversation_realtime_hub, inbox_realtime_hub


def _get_latest_otp(db, email: str, purpose: str) -> dict:
    otp = asyncio.run(
        db.otp_codes.find_one(
            {"email": email, "purpose": purpose},
            sort=[("created_at", -1)],
        )
    )
    assert otp is not None
    return otp


def _auth_headers(client, mock_db, email: str = "messages@example.com") -> dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Message User", "email": email, "password": "SecurePass2024!"},
    )
    assert register_response.status_code == 201

    otp = _get_latest_otp(mock_db, email=email, purpose="signup")
    verify_response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": email, "code": otp["code"], "purpose": "signup"},
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass2024!"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _create_conversation(client, headers: dict[str, str], *, title: str) -> str:
    response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"title": title, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_contact(client, headers: dict[str, str], *, name: str, email: str, presence: str = "offline") -> str:
    response = client.post(
        "/api/v1/smartflow/contacts",
        headers=headers,
        json={"name": name, "email": email, "phone": "+8801700000000"},
    )
    assert response.status_code == 201
    contact_id = response.json()["data"]["id"]
    if presence != "offline":
        update_response = client.patch(
            f"/api/v1/smartflow/contacts/{contact_id}",
            headers=headers,
            json={"presence": presence},
        )
        assert update_response.status_code == 200
    return contact_id


def test_reply_and_forward_endpoints_include_message_context(client, mock_db):
    headers = _auth_headers(client, mock_db)
    primary_conversation_id = _create_conversation(client, headers, title="Primary")
    forwarded_conversation_id = _create_conversation(client, headers, title="Forward Target")

    message_response = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": primary_conversation_id,
            "platform": "whatsapp",
            "direction": "inbound",
            "content": "Regional sales summary is ready.",
        },
    )
    assert message_response.status_code == 201
    source_message_id = message_response.json()["data"]["id"]

    reply_response = client.post(
        f"/api/v1/smartflow/messages/{source_message_id}/reply",
        headers=headers,
        json={
            "content": "Please send me the underperforming regions.",
            "platform": "whatsapp",
        },
    )
    assert reply_response.status_code == 201
    reply_payload = reply_response.json()["data"]
    assert reply_payload["reply_to_message_id"] == source_message_id
    assert reply_payload["reply_to_message_preview"]["content"] == "Regional sales summary is ready."

    forward_response = client.post(
        f"/api/v1/smartflow/messages/{source_message_id}/forward",
        headers=headers,
        json={
            "conversation_id": forwarded_conversation_id,
            "platform": "whatsapp",
        },
    )
    assert forward_response.status_code == 201
    forward_payload = forward_response.json()["data"]
    assert forward_payload["forward_from_message_id"] == source_message_id
    assert forward_payload["forward_from_message_preview"]["content"] == "Regional sales summary is ready."
    assert forward_payload["content"] == "Regional sales summary is ready."

    list_response = client.get(
        f"/api/v1/smartflow/conversations/{forwarded_conversation_id}/messages",
        headers=headers,
    )
    assert list_response.status_code == 200
    listed_message = list_response.json()["data"]["items"][0]
    assert listed_message["forward_from_message_preview"]["content"] == "Regional sales summary is ready."


def test_typing_state_endpoint_round_trip(client, mock_db):
    headers = _auth_headers(client, mock_db, email="typing@example.com")
    conversation_id = _create_conversation(client, headers, title="Typing Conversation")

    initial_response = client.get(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
    )
    assert initial_response.status_code == 200
    assert initial_response.json()["data"]["is_typing"] is False

    typing_response = client.post(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
        json={"is_typing": True, "actor_name": "Mabdel AI", "actor_type": "ai"},
    )
    assert typing_response.status_code == 200
    typing_payload = typing_response.json()["data"]
    assert typing_payload["is_typing"] is True
    assert typing_payload["actor_name"] == "Mabdel AI"
    assert typing_payload["expires_at"] is not None

    fetch_response = client.get(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
    )
    assert fetch_response.status_code == 200
    fetch_payload = fetch_response.json()["data"]
    assert fetch_payload["is_typing"] is True
    assert fetch_payload["actor_type"] == "ai"


def test_message_read_receipt_fields_are_returned(client, mock_db):
    headers = _auth_headers(client, mock_db, email="receipts@example.com")
    conversation_id = _create_conversation(client, headers, title="Receipts")

    message_response = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "platform": "whatsapp",
            "direction": "outbound",
            "content": "I need the regional breakdown.",
        },
    )
    assert message_response.status_code == 201
    message_id = message_response.json()["data"]["id"]

    read_response = client.patch(
        f"/api/v1/smartflow/messages/{message_id}",
        headers=headers,
        json={"status": "read"},
    )
    assert read_response.status_code == 200
    payload = read_response.json()["data"]
    assert payload["status"] == "read"
    assert payload["is_read"] is True
    assert payload["delivered_at"] is not None
    assert payload["read_at"] is not None
    assert payload["read_receipt_label"].startswith("READ ")
    assert payload["status_timestamps"]["sent_at"] is not None
    assert payload["status_timestamps"]["delivered_at"] is not None
    assert payload["status_timestamps"]["read_at"] is not None


def test_conversation_list_is_enriched_for_inbox_cards(client, mock_db):
    headers = _auth_headers(client, mock_db, email="inbox@example.com")
    direct_contact_id = _create_contact(client, headers, name="David Henderson", email="david@example.com", presence="online")
    group_contact_id = _create_contact(client, headers, name="Alex Johnson", email="alex@example.com")

    direct_response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"contact_id": direct_contact_id, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    assert direct_response.status_code == 201
    direct_conversation_id = direct_response.json()["data"]["id"]

    group_response = client.post(
        "/api/v1/smartflow/groups",
        headers=headers,
        json={"name": "Product Team", "member_ids": [group_contact_id]},
    )
    assert group_response.status_code == 201
    group_conversation_id = group_response.json()["data"]["conversation_id"]

    direct_message = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": direct_conversation_id,
            "contact_id": direct_contact_id,
            "platform": "whatsapp",
            "direction": "inbound",
            "content": "Did you see the final draft?",
        },
    )
    assert direct_message.status_code == 201

    group_message = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": group_conversation_id,
            "contact_id": group_contact_id,
            "platform": "ai",
            "direction": "inbound",
            "content": "The new design files are ready.",
        },
    )
    assert group_message.status_code == 201

    ai_message = client.post(
        "/api/v1/smartflow/ai/chat",
        headers=headers,
        json={"content": "Generate sales projections", "response_mode": "text"},
    )
    assert ai_message.status_code == 200

    list_response = client.get("/api/v1/smartflow/conversations", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()["data"]
    items = payload["items"]
    assert payload["summary"]["total_unread"] >= 2
    assert payload["summary"]["by_platform"]["whatsapp"] >= 1

    ai_item = next(item for item in items if item["type"] == "ai")
    assert ai_item["is_ai_assistant"] is True
    assert ai_item["presence_label"] == "Online"
    assert ai_item["platform_label"] == "AI"

    direct_item = next(item for item in items if item["id"] == direct_conversation_id)
    assert direct_item["title"] == "David Henderson"
    assert direct_item["presence"] == "online"
    assert direct_item["unread_count"] == 1
    assert direct_item["has_unread"] is True
    assert direct_item["last_message_preview"] == "Did you see the final draft?"
    assert direct_item["platform_icon_key"] == "whatsapp"
    assert direct_item["delivery_state"] == "unread"

    group_item = next(item for item in items if item["id"] == group_conversation_id)
    assert group_item["is_group"] is True
    assert group_item["last_message_sender_name"] == "Alex Johnson"
    assert group_item["last_message_preview"].startswith("Alex Johnson:")


def test_conversation_unread_filter_search_and_mark_read(client, mock_db):
    headers = _auth_headers(client, mock_db, email="inbox-filters@example.com")
    maria_contact_id = _create_contact(client, headers, name="Maria Garcia", email="maria@example.com")

    unread_conversation_response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"contact_id": maria_contact_id, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    assert unread_conversation_response.status_code == 201
    unread_conversation_id = unread_conversation_response.json()["data"]["id"]

    read_conversation_id = _create_conversation(client, headers, title="HR Department")

    unread_message = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": unread_conversation_id,
            "contact_id": maria_contact_id,
            "platform": "whatsapp",
            "direction": "inbound",
            "content": "Can we reschedule for tomorrow?",
        },
    )
    assert unread_message.status_code == 201

    read_message = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": read_conversation_id,
            "platform": "whatsapp",
            "direction": "outbound",
            "content": "Your leave request has been approved.",
        },
    )
    assert read_message.status_code == 201

    unread_response = client.get("/api/v1/smartflow/conversations?unread_only=true", headers=headers)
    assert unread_response.status_code == 200
    unread_items = unread_response.json()["data"]["items"]
    assert len(unread_items) == 1
    assert unread_items[0]["id"] == unread_conversation_id

    search_response = client.get("/api/v1/smartflow/conversations?search=reschedule", headers=headers)
    assert search_response.status_code == 200
    assert search_response.json()["data"]["items"][0]["id"] == unread_conversation_id

    mark_read_response = client.post(f"/api/v1/smartflow/conversations/{unread_conversation_id}/mark-read", headers=headers)
    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["data"]["unread_count"] == 0


def test_conversation_detail_and_rich_typing_state_for_chat_screen(client, mock_db):
    headers = _auth_headers(client, mock_db, email="chat-detail@example.com")
    contact_id = _create_contact(client, headers, name="Sarah Jenkins", email="sarah@example.com", presence="online")

    conversation_response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"contact_id": contact_id, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    assert conversation_response.status_code == 201
    conversation_id = conversation_response.json()["data"]["id"]

    detail_response = client.get(f"/api/v1/smartflow/conversations/{conversation_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["title"] == "Sarah Jenkins"
    assert detail["presence_label"] == "Online"
    assert detail["contact_name"] == "Sarah Jenkins"

    typing_response = client.post(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
        json={
            "is_typing": True,
            "actor_name": "Mabdel AI",
            "actor_type": "ai",
            "preview_text": "Processing those files now...",
            "state_label": "Active Now",
        },
    )
    assert typing_response.status_code == 200
    typing_payload = typing_response.json()["data"]
    assert typing_payload["preview_text"] == "Processing those files now..."
    assert typing_payload["state_label"] == "Active Now"

    fetch_response = client.get(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
    )
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()["data"]
    assert fetched["preview_text"] == "Processing those files now..."
    assert fetched["state_label"] == "Active Now"


def test_conversation_websocket_stream_connects_and_service_publishes_events(client, mock_db, monkeypatch):
    headers = _auth_headers(client, mock_db, email="chat-realtime@example.com")
    token = headers["Authorization"].split(" ", 1)[1]
    contact_id = _create_contact(client, headers, name="Sarah Jenkins", email="sarah@example.com")

    conversation_response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"contact_id": contact_id, "type": "direct", "platform": "whatsapp", "member_ids": []},
    )
    assert conversation_response.status_code == 201
    conversation_id = conversation_response.json()["data"]["id"]

    published_events = []

    async def fake_publish(conversation_id_arg: str, event: str, data: dict) -> None:
        published_events.append((conversation_id_arg, event, data))

    monkeypatch.setattr(conversation_realtime_hub, "publish", fake_publish)

    with client.websocket_connect(f"/api/v1/smartflow/ws/conversations/{conversation_id}?token={token}") as websocket:
        connected = websocket.receive_json()
        assert connected["event"] == "connected"

    message_response = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "contact_id": contact_id,
            "platform": "whatsapp",
            "direction": "inbound",
            "content": "Realtime message arrived.",
        },
    )
    assert message_response.status_code == 201
    assert published_events[-1][1] == "message.created"

    typing_response = client.post(
        f"/api/v1/smartflow/conversations/{conversation_id}/typing",
        headers=headers,
        json={"is_typing": True, "actor_name": "Mabdel AI", "actor_type": "ai", "preview_text": "Thinking..."},
    )
    assert typing_response.status_code == 200
    assert published_events[-1][1] == "typing.updated"

    read_response = client.post(
        f"/api/v1/smartflow/conversations/{conversation_id}/mark-read",
        headers=headers,
    )
    assert read_response.status_code == 200
    assert published_events[-1][1] == "conversation.read"


def test_inbox_publish_and_stream_contract_for_unified_conversations(client, mock_db, monkeypatch):
    headers = _auth_headers(client, mock_db, email="unified-inbox@example.com")
    token = headers["Authorization"].split(" ", 1)[1]
    contact_id = _create_contact(client, headers, name="Alex Rivera", email="alex@example.com")

    conversation_response = client.post(
        "/api/v1/smartflow/conversations",
        headers=headers,
        json={"contact_id": contact_id, "type": "direct", "platform": "facebook_messenger", "member_ids": []},
    )
    assert conversation_response.status_code == 201
    conversation_id = conversation_response.json()["data"]["id"]

    published_events = []

    async def fake_publish(channel: str, event: str, data: dict) -> None:
        published_events.append((channel, event, data))

    monkeypatch.setattr(inbox_realtime_hub, "publish", fake_publish)

    with client.websocket_connect(f"/api/v1/smartflow/ws/inbox?token={token}") as websocket:
        connected = websocket.receive_json()
        assert connected["event"] == "connected"
        assert connected["channel"] == "inbox"
        assert "summary" in connected["data"]

    message_response = client.post(
        "/api/v1/smartflow/messages",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "contact_id": contact_id,
            "platform": "facebook_messenger",
            "direction": "inbound",
            "content": "Can we jump on a quick call today?",
        },
    )
    assert message_response.status_code == 201
    assert published_events[-1][0]
    assert published_events[-1][1] == "inbox.updated"
    assert published_events[-1][2]["conversation"]["platform_label"] == "Facebook"
