# Mabdel Backend API

Mabdel Backend API is a FastAPI service that powers authentication, onboarding, app bootstrap, permissions, invoicing, and SmartFlow communication workflows for the future Mabdel client applications.

This repository contains backend-only code. It is prepared so a frontend or mobile developer can integrate against a stable API contract without needing to reverse-engineer the service internals.

## Project Overview

- Framework: FastAPI
- Primary datastore: MongoDB via Motor
- Auth model: JWT access and refresh tokens with OTP verification
- API documentation:
  - Swagger UI: `/docs`
  - ReDoc: `/redoc`
  - OpenAPI JSON: `/openapi.json`
  - Static reference: [docs/backend.md](docs/backend.md)
  - OpenAPI snapshot: [docs/openapi.json](docs/openapi.json)

## Backend Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Motor / MongoDB
- Pydantic v2
- `python-jose` for JWT handling
- `passlib` + `bcrypt` for password hashing
- `resend` and SMTP-compatible email delivery
- Pytest + `mongomock-motor` for API tests

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run Locally

1. Copy `.env.example` to `.env`.
2. Set the required environment variables.
3. Start MongoDB locally, or point `MONGODB_URI` at a remote instance.
4. Run the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Base URL while running locally:

```text
http://127.0.0.1:8000
```

Health checks:

```text
GET /health
GET /ready
```

## Environment Variables

Important variables are documented in [.env.example](.env.example). The most important ones are:

| Variable | Required | Purpose |
| --- | --- | --- |
| `APP_NAME` | No | Displayed in API docs |
| `ENVIRONMENT` | No | `development`, `staging`, or `production` |
| `DEBUG` | No | Enables FastAPI debug behavior |
| `PUBLIC_BACKEND_URL` | No | Public base URL used in docs and callback flows |
| `MONGODB_URI` | Yes | MongoDB connection string |
| `DATABASE_NAME` | Yes | MongoDB database name |
| `SECRET_KEY` | Yes | JWT signing key |
| `OAUTH_TOKEN_ENCRYPTION_KEY` | Recommended | Encrypts third-party integration tokens |
| `MAIL_FROM` | Recommended | Sender email address |
| `SMTP_HOST` / `SMTP_USERNAME` / `SMTP_PASSWORD` | Optional | SMTP delivery configuration |
| `RESEND_API_KEY` | Optional | Email delivery fallback |
| `CORS_ORIGINS` | Yes for frontend integration | Allowed browser origins |
| `TRUSTED_HOSTS` | Recommended | Allowed host headers |

## API Base URL

- Local: `http://127.0.0.1:8000`
- Versioned API prefix: `/api/v1`
- Full local API base URL: `http://127.0.0.1:8000/api/v1`

## Available Endpoints

High-level endpoint groups:

- Health: `/health`, `/ready`
- Auth: `/api/v1/auth/*`
- App bootstrap: `/api/v1/app/config`
- Onboarding: `/api/v1/onboarding/*`
- Permissions: `/api/v1/app/permissions*`
- AI helpers: `/api/v1/ai/command`, `/api/v1/email/draft`, `/api/v1/calendar/schedule`, `/api/v1/groups`
- Invoices: `/api/v1/invoices*`
- SmartFlow: `/api/v1/smartflow/*`
- Compatibility routes: `/api/*`

For the full endpoint inventory, request payloads, and integration notes, see [docs/backend.md](docs/backend.md) or open [docs/openapi.json](docs/openapi.json).

## Request / Response Examples

Register a user:

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "full_name": "Arik Hasan",
  "email": "arik@example.com",
  "password": "SecurePass2024!"
}
```

Example response:

```json
{
  "success": true,
  "message": "Registration completed. OTP sent successfully.",
  "data": {
    "message": "Registration completed. OTP sent successfully.",
    "reset_token": null
  }
}
```

Login:

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "arik@example.com",
  "password": "SecurePass2024!"
}
```

Example response:

```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "<jwt-access-token>",
    "refresh_token": "<jwt-refresh-token>",
    "token_type": "bearer",
    "user": {
      "id": "user_id",
      "full_name": "Arik Hasan",
      "email": "arik@example.com",
      "is_verified": true,
      "auth_provider": "email",
      "avatar_url": null,
      "language_preference": "EN",
      "created_at": "2026-05-04T10:00:00Z"
    }
  }
}
```

Authenticated request example:

```http
GET /api/v1/auth/me
Authorization: Bearer <jwt-access-token>
```

## Authentication Flow

1. `POST /api/v1/auth/register`
2. `POST /api/v1/auth/verify-otp`
3. `POST /api/v1/auth/login`
4. Use the returned bearer access token for protected routes
5. Refresh with `POST /api/v1/auth/refresh-token` when the access token expires
6. Revoke the current session with `POST /api/v1/auth/logout`

## Testing

Run the backend test suite:

```bash
python -m pytest -q
```

## Deployment Notes

- The service is stateless; application sessions are token-based.
- MongoDB is required in every environment.
- Set a strong `SECRET_KEY` outside development.
- Set `OAUTH_TOKEN_ENCRYPTION_KEY` outside development if social integrations are enabled.
- Lock down `CORS_ORIGINS` and `TRUSTED_HOSTS` in staging and production.
- Mount the app behind a reverse proxy or load balancer and expose only the API port.
- Use the `/ready` endpoint for container readiness checks.

## Docker

```bash
docker compose up --build
```

This starts:

- `api`
- `mongo`

