from __future__ import annotations

import httpx

from app.core.config import settings
from app.tests.test_auth import _register_user, _verify_signup_otp


def _login_and_get_token(client, email: str, password: str = "SecurePass2024!") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_calendar_connect_returns_oauth_url_when_not_connected(client, mock_db, monkeypatch) -> None:
    email = "oauth-calendar@example.com"
    _register_user(client, email=email)
    _verify_signup_otp(client, mock_db, email=email)
    token = _login_and_get_token(client, email)

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/smartflow/integrations/google_business/oauth/callback")

    response = client.post("/api/calendar/connect", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["connected"] is False
    assert "accounts.google.com" in payload["auth_url"]
    assert payload["state"]


def test_integrations_connect_returns_oauth_url_when_access_token_missing(client, mock_db, monkeypatch) -> None:
    email = "oauth-instagram@example.com"
    _register_user(client, email=email)
    _verify_signup_otp(client, mock_db, email=email)
    token = _login_and_get_token(client, email)

    monkeypatch.setattr(settings, "META_CLIENT_ID", "meta-client-id")
    monkeypatch.setattr(settings, "META_CLIENT_SECRET", "meta-secret")
    monkeypatch.setattr(settings, "META_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/smartflow/integrations/instagram/oauth/callback")

    response = client.post(
        "/api/integrations/connect",
        json={"platform": "instagram"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["connected"] is False
    assert "facebook.com" in payload["auth_url"]
    assert payload["platform"] == "instagram"


def test_integration_catalog_returns_supported_platform_cards_with_status(client, mock_db, monkeypatch) -> None:
    email = "catalog@example.com"
    _register_user(client, email=email)
    _verify_signup_otp(client, mock_db, email=email)
    token = _login_and_get_token(client, email)

    monkeypatch.setattr(settings, "META_CLIENT_ID", "meta-client-id")
    monkeypatch.setattr(settings, "META_CLIENT_SECRET", "meta-secret")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "google-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "linkedin-client-id")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_SECRET", "linkedin-secret")
    monkeypatch.setattr(settings, "TWITTER_CLIENT_ID", None)
    monkeypatch.setattr(settings, "TWITTER_CLIENT_SECRET", None)

    connect_response = client.post(
        "/api/v1/smartflow/integrations",
        json={"platform": "instagram", "access_token": "abc123", "external_account_id": "insta-account"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert connect_response.status_code == 201

    catalog_response = client.get(
        "/api/v1/smartflow/integrations/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert catalog_response.status_code == 200
    items = catalog_response.json()["data"]

    instagram = next(item for item in items if item["platform"] == "instagram")
    assert instagram["platform_label"] == "Instagram"
    assert instagram["connected"] is True
    assert instagram["cta_label"] == "Connected"
    assert instagram["health_status"] == "connected"

    twitter = next(item for item in items if item["platform"] == "twitter_x")
    assert twitter["platform_label"] == "Twitter (X)"
    assert twitter["is_configured"] is False
    assert twitter["status"] == "misconfigured"
    assert twitter["cta_label"] == "Unavailable"

    telegram = next(item for item in items if item["platform"] == "telegram")
    assert telegram["auth_mode"] == "manual"
    assert telegram["is_available"] is True
    assert telegram["cta_label"] == "Connect"


def test_telegram_manual_connect_registers_webhook_and_stores_secret(client, mock_db, monkeypatch) -> None:
    email = "telegram-manual@example.com"
    _register_user(client, email=email)
    _verify_signup_otp(client, mock_db, email=email)
    token = _login_and_get_token(client, email)

    monkeypatch.setattr(settings, "PUBLIC_BACKEND_URL", "https://api.example.com")

    captured: dict[str, object] = {}

    async def fake_post(self, url, data=None, headers=None, **kwargs):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        request = httpx.Request("POST", str(url))
        return httpx.Response(200, json={"ok": True, "result": True}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    response = client.post(
        "/api/v1/smartflow/integrations/telegram/manual-connect",
        json={
            "bot_token": "123456:ABCDEF_bot_token",
            "bot_username": "mabdel_bot",
            "secret_token": "telegram-secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    payload = response.json()["data"]

    assert payload["platform"] == "telegram"
    assert payload["connected"] is True
    assert payload["secret_token"] == "telegram-secret"
    assert payload["webhook_url"].startswith("https://api.example.com/api/v1/smartflow/integrations/telegram/webhook?user_id=")
    assert payload["integration"]["platform"] == "telegram"
    assert payload["integration"]["connected"] is True
    assert captured["url"] == "https://api.telegram.org/bot123456:ABCDEF_bot_token/setWebhook"
    assert captured["data"]["secret_token"] == "telegram-secret"
