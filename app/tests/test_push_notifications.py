from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.security import create_access_token
from app.services.smartflow_service import SmartFlowService


async def _create_push_user(mock_db, *, notifications_enabled: bool = True) -> str:
    user = {
        "full_name": "Push User",
        "email": "push@example.com",
        "password_hash": "hashed",
        "is_verified": True,
        "auth_provider": "email",
        "avatar_url": None,
        "language_preference": "EN",
        "notification_preferences": {
            "new_messages": notifications_enabled,
            "missed_calls": True,
            "scheduled_calls": True,
            "ai_tasks": True,
            "calendar_reminders": True,
        },
        "device_tokens": [
            {
                "device_id": "device-1",
                "token": "push-token-1",
                "platform": "android",
            }
        ],
    }
    result = await mock_db.users.insert_one(user)
    return str(result.inserted_id)


def test_create_notification_enqueues_push_job_when_device_registered(mock_db, monkeypatch):
    monkeypatch.setattr(settings, "PUSH_DELIVERY_SYNC", True)
    monkeypatch.setattr(settings, "FCM_SERVER_KEY", None)
    user_id = asyncio.run(_create_push_user(mock_db))
    service = SmartFlowService(mock_db)

    notification = asyncio.run(service.create_notification(user_id, "message", "New message", "You have a new message"))
    jobs = asyncio.run(mock_db.push_dispatch_jobs.find({"notification_id": notification["id"]}).to_list(length=10))

    assert len(jobs) == 1
    assert jobs[0]["status"] == "skipped"
    assert jobs[0]["provider_response"]["reason"] == "fcm_not_configured"


def test_create_notification_skips_push_when_preference_disabled(mock_db, monkeypatch):
    monkeypatch.setattr(settings, "PUSH_DELIVERY_SYNC", True)
    user_id = asyncio.run(_create_push_user(mock_db, notifications_enabled=False))
    service = SmartFlowService(mock_db)

    notification = asyncio.run(service.create_notification(user_id, "message", "Muted", "Do not push"))
    jobs = asyncio.run(mock_db.push_dispatch_jobs.find({"notification_id": notification["id"]}).to_list(length=10))

    assert jobs == []


def test_dispatch_pending_push_notifications_endpoint(client, mock_db, monkeypatch):
    monkeypatch.setattr(settings, "PUSH_DELIVERY_SYNC", False)
    user_id = asyncio.run(_create_push_user(mock_db))
    notification_id = asyncio.run(
        mock_db.notifications.insert_one(
            {
                "user_id": user_id,
                "type": "message",
                "title": "Queued",
                "body": "Pending dispatch",
                "read": False,
            }
        )
    ).inserted_id
    asyncio.run(
        mock_db.push_dispatch_jobs.insert_one(
            {
                "user_id": user_id,
                "notification_id": str(notification_id),
                "device_id": "device-1",
                "token": "push-token-1",
                "platform": "android",
                "title": "Queued",
                "body": "Pending dispatch",
                "badge": 1,
                "status": "queued",
                "attempts": 0,
            }
        )
    )

    token = create_access_token(user_id, "push@example.com")
    response = client.post(
        "/api/v1/smartflow/notifications/dispatch-pending",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["status"] in {"failed", "skipped", "sent"}
