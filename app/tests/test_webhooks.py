from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.security import create_access_token, hash_password


async def _create_user(mock_db, email: str = "webhook@example.com") -> str:
    user = {
        "full_name": "Webhook User",
        "email": email,
        "password_hash": hash_password("SecurePass2024!"),
        "is_verified": True,
        "auth_provider": "email",
        "avatar_url": None,
        "language_preference": "EN",
        "notification_preferences": {
            "new_messages": True,
            "missed_calls": True,
            "scheduled_calls": True,
            "ai_tasks": True,
            "calendar_reminders": True,
        },
        "device_tokens": [],
    }
    result = await mock_db.users.insert_one(user)
    return str(result.inserted_id)


def test_meta_webhook_verification(client, monkeypatch):
    monkeypatch.setattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "verify-me")
    response = client.get(
        "/api/v1/smartflow/integrations/instagram/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["challenge"] == "12345"


def test_webhook_processing_is_idempotent(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SHARED_SECRET", "super-secret")
    user_id = asyncio.run(_create_user(mock_db))
    asyncio.run(
        mock_db.social_integrations.insert_one(
            {
                "user_id": user_id,
                "platform": "telegram",
                "status": "connected",
            }
        )
    )

    payload = {
        "message": {
            "message_id": 77,
            "text": "Hello from Telegram",
            "from": {"id": 999},
        }
    }
    first = client.post(
        f"/api/v1/smartflow/integrations/telegram/webhook?user_id={user_id}",
        json=payload,
        headers={"X-Webhook-Secret": "super-secret"},
    )
    second = client.post(
        f"/api/v1/smartflow/integrations/telegram/webhook?user_id={user_id}",
        json=payload,
        headers={"X-Webhook-Secret": "super-secret"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["status"] == "processed"
    assert second.json()["data"]["status"] == "ignored"


def test_webhook_rejects_invalid_secret(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SHARED_SECRET", "super-secret")
    user_id = asyncio.run(_create_user(mock_db, email="webhook2@example.com"))
    payload = {"event_id": "evt-1", "contact_external_id": "abc", "content": "Hello"}

    response = client.post(
        f"/api/v1/smartflow/integrations/telegram/webhook?user_id={user_id}",
        json=payload,
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "WEBHOOK_UNAUTHORIZED"


def test_telegram_webhook_accepts_native_secret_header(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SHARED_SECRET", "fallback-secret")
    user_id = asyncio.run(_create_user(mock_db, email="webhook3@example.com"))
    asyncio.run(
        mock_db.social_integrations.insert_one(
            {
                "user_id": user_id,
                "platform": "telegram",
                "status": "connected",
                "telegram_secret_token": "telegram-secret",
            }
        )
    )

    payload = {
        "message": {
            "message_id": 88,
            "text": "Telegram native secret works",
            "from": {"id": 321},
        }
    }
    response = client.post(
        f"/api/v1/smartflow/integrations/telegram/webhook?user_id={user_id}",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "telegram-secret"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "processed"
