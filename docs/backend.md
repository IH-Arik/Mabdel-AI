# Backend API Reference

## Overview

This backend exposes a versioned REST API at `/api/v1` plus a small `/api` compatibility surface for legacy clients. It is designed for frontend and mobile integration first:

- JSON request and response bodies
- JWT bearer authentication for protected routes
- Swagger and OpenAPI contracts generated directly from the FastAPI app
- Realtime inbox and conversation updates over WebSocket

OpenAPI sources:

- Runtime spec: `/openapi.json`
- Static snapshot: [openapi.json](openapi.json)

## Base URLs

- Local app root: `http://127.0.0.1:8000`
- Versioned API base: `http://127.0.0.1:8000/api/v1`

## Standard Response Format

Successful responses use this envelope:

```json
{
  "success": true,
  "message": "Human-readable message",
  "data": {}
}
```

Error responses use this envelope:

```json
{
  "success": false,
  "message": "Request failed.",
  "error": {
    "code": "ERROR_CODE",
    "details": null
  }
}
```

## Authentication

### Auth Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/send-otp`
- `POST /api/v1/auth/resend-otp`
- `POST /api/v1/auth/verify-otp`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/refresh-token`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

### Frontend Auth Flow

1. Register user with `POST /auth/register`
2. Verify OTP with `POST /auth/verify-otp`
3. Login with `POST /auth/login`
4. Store the `access_token` and `refresh_token`
5. Send `Authorization: Bearer <access_token>` on protected routes
6. Refresh with `POST /auth/refresh-token`
7. Logout with `POST /auth/logout`

### Login Example

Request:

```json
{
  "email": "arik@example.com",
  "password": "SecurePass2024!"
}
```

Response:

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

## Public and Bootstrap Endpoints

### Health

- `GET /health`
- `GET /ready`

### App Bootstrap

- `GET /api/v1/app/config`

Query parameters:

- `current_version`
- `user_id`
- `device_id`

Use this endpoint to bootstrap splash-screen config, version gating, feature flags, and onboarding visibility.

### Onboarding

- `GET /api/v1/onboarding/slides`
- `GET /api/v1/onboarding/progress`
- `POST /api/v1/onboarding/progress`
- `POST /api/v1/onboarding/skip`
- `POST /api/v1/onboarding/complete`
- `POST /api/v1/onboarding/reset`

Frontend note:

- Guest clients can use `device_id`
- Logged-in clients can use `user_id`

### Permissions

- `GET /api/v1/app/permissions`
- `PUT /api/v1/app/permissions`
- `POST /api/v1/app/permissions/accept-all`

## Protected Domain APIs

All routes below require:

```http
Authorization: Bearer <jwt-access-token>
```

### SmartFlow

Primary namespace:

- `/api/v1/smartflow`

Coverage:

- Home dashboard
- Contacts
- Conversations
- Messages
- Typing state
- AI chat and voice flows
- Bulk messaging
- Calendar events
- Documents
- Call logs
- Integrations and OAuth
- Notifications
- Groups
- User settings
- Push token registration

Key routes:

- `GET /api/v1/smartflow/home`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/contacts`
- `GET|POST /api/v1/smartflow/conversations`
- `GET /api/v1/smartflow/conversations/{conversation_id}`
- `GET /api/v1/smartflow/conversations/{conversation_id}/messages`
- `POST|PATCH /api/v1/smartflow/messages`
- `POST /api/v1/smartflow/ai/chat`
- `GET /api/v1/smartflow/ai/history`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/calendar/events`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/documents`
- `GET|POST|PATCH /api/v1/smartflow/calls`
- `GET|POST|DELETE /api/v1/smartflow/integrations`
- `GET|POST|PATCH /api/v1/smartflow/groups`
- `GET|PATCH /api/v1/smartflow/settings`

### Invoice API

- `GET /api/v1/invoices`
- `POST /api/v1/invoices`
- `GET /api/v1/invoices/{invoice_id}`
- `PATCH /api/v1/invoices/{invoice_id}`
- `DELETE /api/v1/invoices/{invoice_id}`
- `POST /api/v1/invoices/{invoice_id}/send`
- `POST /api/v1/invoices/{invoice_id}/share`
- `POST /api/v1/invoices/{invoice_id}/remind`
- `POST /api/v1/invoices/{invoice_id}/status`
- `GET /api/v1/invoices/{invoice_id}/timeline`
- `GET /api/v1/invoices/{invoice_id}/pdf`
- `GET /api/v1/invoices/shared/{share_token}/pdf`

Invoice list supports:

- `page`
- `page_size`
- `search`
- `status`

### AI / Utility Endpoints

- `POST /api/v1/ai/command`
- `POST /api/v1/email/draft`
- `POST /api/v1/calendar/schedule`
- `POST /api/v1/groups`
- `POST /api/v1/calls/incoming`

## Compatibility Routes

These routes exist for older clients:

- `GET /api/inbox`
- `GET /api/contacts`
- `GET /api/calendar/events`
- `POST /api/calendar/connect`
- `GET /api/integrations`
- `POST /api/integrations/connect`
- `GET /api/ai-call-analytics`
- `GET /api/documents/types`
- `POST /api/calls/{callId}/callback`

New frontend integrations should prefer `/api/v1/*`.

## WebSockets

Protected WebSocket routes:

- `/api/v1/smartflow/ws/conversations/{conversation_id}?token=<access-token>`
- `/api/v1/smartflow/ws/inbox?token=<access-token>`

Use cases:

- Live inbox updates
- Live conversation updates
- Typing state and new message propagation

## Example Protected Request

```http
GET /api/v1/smartflow/conversations?page=1&page_size=20
Authorization: Bearer <jwt-access-token>
```

Example response shape:

```json
{
  "success": true,
  "message": "Conversations fetched successfully.",
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 0,
      "total_pages": 0
    },
    "summary": {
      "total_unread": 0,
      "by_platform": {}
    }
  }
}
```

## Integration Notes

- `CORS_ORIGINS` should include the future frontend origin in non-development environments.
- `TRUSTED_HOSTS` should be locked to the deployed API hostnames.
- File upload routes such as `POST /api/v1/smartflow/ai/voice-chat-upload` require `multipart/form-data`.
- OTP and invoice email delivery can use SMTP or Resend.
- Social integrations depend on provider credentials and callback URLs being configured in `.env`.

## Recommended Frontend Entry Points

For a new client integration, start with:

1. `GET /health`
2. `GET /api/v1/app/config`
3. `GET /api/v1/onboarding/slides`
4. `POST /api/v1/auth/register`
5. `POST /api/v1/auth/verify-otp`
6. `POST /api/v1/auth/login`
7. `GET /api/v1/auth/me`
8. Protected SmartFlow or invoice routes as needed

