# Backend API Reference

## Overview

The Mabdel backend exposes a versioned REST API at `/api/v1` along with a compatibility layer at `/api` for legacy clients. It is built using FastAPI and follows a modular architecture designed for high-performance AI workflows, real-time messaging, and multi-tenant dashboard management.

Key Features:
- **FastAPI Core**: Async-first, high-performance API.
- **Authentication**: JWT-based bearer authentication with refresh tokens and OTP verification.
- **AI Workflows**: LangGraph-powered intent routing for automated tasks (Invoices, Leases, etc.).
- **Real-time**: WebSocket support for live chat, inbox updates, and voice streaming.
- **Multi-Tenant Dashboard**: Separate admin and super-admin interfaces for platform management.
- **Integrations**: Support for Twilio, Meta, Google, LinkedIn, Twitter, and Snapchat.

OpenAPI sources:
- Runtime spec: `/openapi.json`
- Static snapshot: [openapi.json](openapi.json)
- Interactive Docs: `/docs` (Swagger) or `/redoc` (ReDoc)

## Base URLs

- Local Host: `http://127.0.0.1:8000`
- API V1 Base: `http://127.0.0.1:8000/api/v1`
- Dashboard Base: `http://127.0.0.1:8000/api/v1/dashboard`

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
  "message": "Detailed error message.",
  "error": {
    "code": "ERROR_CODE",
    "details": null
  }
}
```

---

## Environment Configuration

The backend is configured via environment variables (typically in a `.env` file).

| Variable | Description | Default |
| --- | --- | --- |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `PUBLIC_BACKEND_URL` | Public origin of the API | `http://127.0.0.1:8000` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `SECRET_KEY` | JWT signing key | *Required* |
| `OPENAI_API_KEY` | API key for GPT models | *Optional (Fallback enabled)* |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID for voice/SMS | *Optional* |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | *Optional* |
| `FCM_SERVER_KEY` | Firebase Cloud Messaging key | *Optional* |
| `RESEND_API_KEY` | API key for email delivery | *Optional* |

---

## Authentication

### Auth Endpoints
- `POST /api/v1/auth/register`: Register new user.
- `POST /api/v1/auth/send-otp`: Trigger email OTP.
- `POST /api/v1/auth/verify-otp`: Verify OTP to activate account.
- `POST /api/v1/auth/login`: Authenticate and receive tokens.
- `POST /api/v1/auth/google`: Social login via Google.
- `POST /api/v1/auth/refresh-token`: Exchange refresh token for new access token.
- `POST /api/v1/auth/forgot-password`: Request password reset.
- `POST /api/v1/auth/reset-password`: Set new password with OTP.
- `GET /api/v1/auth/me`: Get current user profile.
- `POST /api/v1/auth/logout`: Invalidate session.

### Auth Flow
1. **Register**: `POST /auth/register` -> `POST /auth/verify-otp`.
2. **Login**: `POST /auth/login` returns `access_token` and `refresh_token`.
3. **Authorize**: Include `Authorization: Bearer <access_token>` in headers.

---

## SmartFlow API (Protected)

The primary domain for client applications. All routes require a valid JWT.

### Contacts & Conversations
- `GET|POST /api/v1/smartflow/contacts`: Manage contacts.
- `GET /api/v1/smartflow/contacts/{id}`: Detailed contact view.
- `GET|POST /api/v1/smartflow/conversations`: Chat list and metadata.
- `POST /api/v1/smartflow/conversations/{id}/archive`: Archive a thread.
- `POST /api/v1/smartflow/conversations/{id}/mark-read`: Bulk read action.
- `GET /api/v1/smartflow/messages/unread-summary`: Get unread counts per platform.

### AI & Workflows
- `POST /api/v1/smartflow/ai/chat`: Interactive AI assistant.
- `POST /api/v1/smartflow/ai/voice-chat`: Process audio commands.
- `POST /api/v1/smartflow/ai/workflow-prefill`: Extract form data from transcript.
- `GET /api/v1/smartflow/ai/history`: View past AI interactions.
- `POST /api/v1/smartflow/ai/history/{id}/replay`: Re-run an AI command.

### Invoices & Documents
- `GET|POST /api/v1/invoices`: Invoice management.
- `GET /api/v1/invoices/{id}/pdf`: Download/Stream invoice PDF.
- `POST /api/v1/invoices/{id}/remind`: Send payment reminder.
- `GET|POST /api/v1/smartflow/documents`: File storage and management.

### Leases & Agreements
- `GET /api/v1/smartflow/leases`: List rental agreements.
- `POST /api/v1/smartflow/leases/generate`: AI-powered lease generation.
- `POST /api/v1/smartflow/leases/{id}/send-signature`: Initiate e-signature.
- `GET /api/v1/smartflow/agreements`: Legal contract management.

### Calls & Voice
- `GET /api/v1/smartflow/calls`: Call history logs.
- `POST /api/v1/smartflow/calls/outbound`: Trigger callback via Twilio.
- `GET /api/v1/smartflow/calls/{id}/transcript`: AI-generated call transcript.

---

## Dashboard API (Admin)

Restricted to users with `admin` or `super_admin` roles.

### Organization Management
- `GET /api/v1/dashboard/admin/summary`: High-level metrics.
- `GET /api/v1/dashboard/admin/users`: User list and moderation.
- `PATCH /api/v1/dashboard/admin/users/{id}/status`: Block/Unblock users.
- `GET /api/v1/dashboard/admin/earnings`: Revenue and transaction history.

### Monitoring & Support
- `GET /api/v1/dashboard/admin/ai/stats`: AI performance monitoring.
- `GET /api/v1/dashboard/admin/ai/logs`: Detailed AI interaction traces.
- `GET /api/v1/dashboard/admin/chats`: View and respond to user support chats.
- `GET /api/v1/dashboard/admin/reports`: Manage user-submitted reports/complaints.

### Super Admin (Global)
- `GET /api/v1/dashboard/super/platform-summary`: Multi-org global metrics.
- `GET /api/v1/dashboard/super/global-growth`: Platform-wide growth trends.

---

## WebSocket APIs

WebSockets provide real-time updates for chat, notifications, and media streaming.

- `WS /api/v1/smartflow/ws/inbox?token=<token>`: Global inbox updates.
- `WS /api/v1/smartflow/ws/conversations/{id}?token=<token>`: Specific thread updates.
- `WS /api/v1/calls/stream/{call_id}`: Bi-directional Twilio media stream.

---

## Frontend Integration Maps

### Contacts Screen
- List: `GET /smartflow/contacts` (supports `search`, `page`).
- Add: `POST /smartflow/contacts`.
- Edit: `PATCH /smartflow/contacts/{id}`.
- Avatar: `POST /smartflow/contacts/{id}/avatar` (Multipart).

### Notifications Screen
- List: `GET /smartflow/notifications` (supports `unread_only`).
- Mark Read: `PATCH /smartflow/notifications/{id}/read`.
- Mark All Read: `POST /smartflow/notifications/mark-all-read`.
- Push Token: `POST /smartflow/devices/push-token`.

### AI Command Redirects
When using `POST /api/v1/smartflow/ai/chat`, the response may include a `navigation` object for auto-routing:

| Intent | Screen | Path |
| --- | --- | --- |
| `invoice` | `CreateInvoice` | `/invoices/create` |
| `bulk_message` | `CreateBulkMessage` | `/bulk-messages/create` |
| `calendar` | `CreateCalendarEvent` | `/calendar/events/create` |
| `lease` | `CreateLease` | `/leases/create` |

---

## Integration Notes

- **CORS**: Ensure `CORS_ORIGINS` in `.env` includes the frontend domain.
- **File Uploads**: Use `multipart/form-data` for avatars, logos, and voice chat uploads.
- **Rate Limiting**: Auth routes have a default limit (20 req / 60 sec).
- **Twilio**: Publicly accessible URL is required for TwiML webhooks and media streams.
- **OpenAI**: Fallback logic is implemented; however, `OPENAI_API_KEY` is required for production-grade AI features.
