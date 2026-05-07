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

### App Content

- `GET /api/v1/content/pages/{slug}`
- `GET /api/v1/content/about-us`
- `GET /api/v1/content/terms-and-conditions`
- `GET /api/v1/content/privacy-policy`
- `GET /api/v1/content/help-support`

Content responses include `title`, `display_style`, `version`, ordered `blocks`, and `updated_at`. The mobile app can render About Us as a numbered list and legal/help pages as sections.

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
- Business profile
- Subscription state
- Report and support submission
- Account deletion
- Push token registration

Key routes:

- `GET /api/v1/smartflow/home`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/contacts`
- `GET /api/v1/smartflow/contacts/{contact_id}`
- `POST /api/v1/smartflow/contacts/{contact_id}/avatar`
- `GET|POST /api/v1/smartflow/conversations`
- `GET /api/v1/smartflow/conversations/{conversation_id}`
- `GET /api/v1/smartflow/conversations/{conversation_id}/messages`
- `POST|PATCH /api/v1/smartflow/messages`
- `POST /api/v1/smartflow/messages/{message_id}/reply`
- `POST /api/v1/smartflow/messages/{message_id}/forward`
- `GET|POST /api/v1/smartflow/conversations/{conversation_id}/typing`
- `POST /api/v1/smartflow/ai/chat`
- `GET /api/v1/smartflow/ai/history`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/calendar/events`
- `GET|POST|PATCH|DELETE /api/v1/smartflow/documents`
- `GET|POST|PATCH /api/v1/smartflow/calls`
- `GET /api/v1/smartflow/calls/summary`
- `GET /api/v1/smartflow/calls/{call_id}`
- `GET|PUT /api/v1/smartflow/calls/{call_id}/recording`
- `GET|PUT /api/v1/smartflow/calls/{call_id}/transcript`
- `GET|PUT /api/v1/smartflow/calls/{call_id}/ai-summary`
- `POST /api/v1/smartflow/calls/{call_id}/callback`
- `GET|POST|DELETE /api/v1/smartflow/integrations`
- `GET /api/v1/smartflow/integrations/catalog`
- `GET /api/v1/smartflow/integrations/status`
- `POST /api/v1/smartflow/integrations/{platform}/sync`
- `GET|POST /api/v1/smartflow/integrations/{platform}/webhook`
- `GET /api/v1/smartflow/notifications`
- `PATCH /api/v1/smartflow/notifications/{notification_id}/read`
- `POST /api/v1/smartflow/notifications/mark-all-read`
- `DELETE /api/v1/smartflow/notifications/{notification_id}`
- `POST /api/v1/smartflow/notifications/dispatch-pending`
- `GET|POST /api/v1/smartflow/groups`
- `GET|PATCH|DELETE /api/v1/smartflow/groups/{group_id}`
- `POST /api/v1/smartflow/groups/{group_id}/members`
- `PATCH|DELETE /api/v1/smartflow/groups/{group_id}/members/{member_id}`
- `POST /api/v1/smartflow/groups/{group_id}/invites`
- `DELETE /api/v1/smartflow/groups/{group_id}/invites/{invite_id}`
- `POST /api/v1/smartflow/groups/{group_id}/leave`
- `GET|PATCH /api/v1/smartflow/settings`
- `POST /api/v1/smartflow/settings/avatar`
- `GET|PATCH /api/v1/smartflow/settings/notifications`
- `POST /api/v1/smartflow/settings/change-password`
- `POST /api/v1/smartflow/settings/revoke-sessions`
- `GET|PATCH /api/v1/smartflow/business-profile`
- `POST /api/v1/smartflow/business-profile/logo`
- `GET /api/v1/smartflow/subscription/plans`
- `GET /api/v1/smartflow/subscription/current`
- `GET /api/v1/smartflow/reports/categories`
- `POST /api/v1/smartflow/reports`
- `POST /api/v1/smartflow/support/tickets`
- `GET|POST /api/v1/smartflow/support/session`
- `GET|POST /api/v1/smartflow/support/messages`
- `DELETE /api/v1/smartflow/account`

### Contacts Screen API Map

For the provided Contacts and Add Contact screens, the frontend needs 6 contact APIs:

- Contact list/search: `GET /api/v1/smartflow/contacts` with `page`, `page_size`, and `search`
- Add contact: `POST /api/v1/smartflow/contacts`
- Contact detail after tapping a row: `GET /api/v1/smartflow/contacts/{contact_id}`
- Edit contact: `PATCH /api/v1/smartflow/contacts/{contact_id}`
- Delete contact: `DELETE /api/v1/smartflow/contacts/{contact_id}`
- Upload/change contact avatar: `POST /api/v1/smartflow/contacts/{contact_id}/avatar` with multipart field `avatar_file`

The add/edit payload accepts either legacy `name` or mobile-form fields `first_name` and `last_name`, plus `phone`, `email`, `address`, `date_of_birth`, `notes`, `avatar_url`, and optional `presence`. List/detail responses include frontend-ready display fields: `name`, `first_name`, `last_name`, `primary_detail`, `initials`, `presence_label`, `is_online`, `avatar_url`, `address`, `date_of_birth`, and `notes`.

### Call History Screen API Map

For the provided Call History and call detail/recording screens, the frontend needs 13 call APIs:

- Call history list/search/filter: `GET /api/v1/smartflow/calls` with `page`, `page_size`, `search`, `status`, and optional `contact_id`
- Create/import a call log: `POST /api/v1/smartflow/calls`
- Start real outbound callback through Twilio: `POST /api/v1/smartflow/calls/outbound`
- Call analytics counters: `GET /api/v1/smartflow/calls/summary`
- Call detail for the profile/recording screen: `GET /api/v1/smartflow/calls/{call_id}`
- Edit call metadata/status: `PATCH /api/v1/smartflow/calls/{call_id}`
- Recording metadata: `GET /api/v1/smartflow/calls/{call_id}/recording`
- Attach/update recording URL: `PUT /api/v1/smartflow/calls/{call_id}/recording`
- Transcript view: `GET /api/v1/smartflow/calls/{call_id}/transcript`
- Attach/update transcript and speaker segments: `PUT /api/v1/smartflow/calls/{call_id}/transcript`
- AI summary view: `GET /api/v1/smartflow/calls/{call_id}/ai-summary`
- Attach/update AI summary: `PUT /api/v1/smartflow/calls/{call_id}/ai-summary`
- Mark callback requested from a history row: `POST /api/v1/smartflow/calls/{call_id}/callback`

Call list/detail responses include `contact`, `contact_name`, `phone_number`, `initials`, `repeat_count`, `call_type_label`, `duration_label`, `display_time_label`, `date_bucket`, `status_label`, `status_tone`, `recording_available`, `transcript_available`, `ai_summary_available`, and `actions` so the mobile list buttons can render without extra client-side mapping.

### Settings/Profile Screen API Map

For the provided mobile settings screens, the frontend needs these API calls:

- Settings profile header and edit profile: `GET|PATCH /api/v1/smartflow/settings`
- Profile image upload: `POST /api/v1/smartflow/settings/avatar` with multipart field `avatar_file`
- Notification toggle screen: `GET|PATCH /api/v1/smartflow/settings/notifications` for `general_notification`, `sound`, and `vibrate` plus granular push categories
- Main settings rows already backed by existing APIs: notification inbox via `GET /api/v1/smartflow/notifications`, AI voice command history via `GET /api/v1/smartflow/ai/history`, logout via `POST /api/v1/auth/logout`
- Account settings: authenticated password change via `POST /api/v1/smartflow/settings/change-password`, forgot/reset password via `POST /api/v1/auth/forgot-password` then `POST /api/v1/auth/reset-password`, legal/about content via `/api/v1/content/*`, delete account via `DELETE /api/v1/smartflow/account`
- Business profile view/edit: `GET|PATCH /api/v1/smartflow/business-profile`, logo upload via `POST /api/v1/smartflow/business-profile/logo`
- Live support chat: `GET|POST /api/v1/smartflow/support/session`, `GET|POST /api/v1/smartflow/support/messages`
- Subscription/help/report rows: `GET /api/v1/smartflow/subscription/plans`, `GET /api/v1/smartflow/subscription/current`, `GET /api/v1/content/help-support`, `POST /api/v1/smartflow/support/tickets`, `GET /api/v1/smartflow/reports/categories`, `POST /api/v1/smartflow/reports`

### Notifications Screen API Map

For the provided Notifications screen, the frontend needs 6 notification APIs:

- Notification inbox list: `GET /api/v1/smartflow/notifications` with `page`, `page_size`, and `unread_only`
- Mark one notification as read after opening a row: `PATCH /api/v1/smartflow/notifications/{notification_id}/read`
- Mark all as read header action: `POST /api/v1/smartflow/notifications/mark-all-read`
- Swipe-to-delete row action: `DELETE /api/v1/smartflow/notifications/{notification_id}`
- Register/update the device token used to deliver push notifications: `POST /api/v1/smartflow/devices/push-token`
- Manual retry/admin-safe dispatch hook for queued push jobs: `POST /api/v1/smartflow/notifications/dispatch-pending`

List responses are frontend-ready for the mobile UI. They include a flat paginated `items` array, `summary.unread_count`/`summary.new_count` for the `3 NEW` badge, and `sections[]` grouped as `TODAY` and `EARLIER`. Each item includes `title`, `body`, `type`, `read`, `unread`, `icon_key`, `accent_tone`, `date_bucket`, `display_time_label`, `primary_action`, `action_url`, and `metadata`, so the client can render unread dots, icons, left accent colors, relative times, and row navigation without extra mapping.

### Agreements Screen API Map

For the provided Agreements, Agreement Creator, and Contract Preview screens, the frontend needs these API calls:

- Agreement list/search/filter: `GET /api/v1/smartflow/agreements` with `page`, `page_size`, `search`, `status`, and `agreement_type`
- Creator dropdown metadata: `GET /api/v1/smartflow/agreements/metadata`, plus `GET /api/v1/smartflow/agreements/types` and `GET /api/v1/smartflow/agreements/priorities`
- Generate with AI before saving: `POST /api/v1/smartflow/agreements/generate`
- Improve unsaved draft content: `POST /api/v1/smartflow/agreements/improve`
- Review unsaved draft content: `POST /api/v1/smartflow/agreements/review`
- Save and preview an agreement: `POST /api/v1/smartflow/agreements`, `GET /api/v1/smartflow/agreements/{agreement_id}`
- Edit/delete an agreement: `PATCH /api/v1/smartflow/agreements/{agreement_id}`, `DELETE /api/v1/smartflow/agreements/{agreement_id}`
- Improve/review saved agreement content: `POST /api/v1/smartflow/agreements/{agreement_id}/improve`, `POST /api/v1/smartflow/agreements/{agreement_id}/review`
- Signature workflow: `POST /api/v1/smartflow/agreements/{agreement_id}/send-signature`, `POST /api/v1/smartflow/agreements/{agreement_id}/sign`
- Public signing link for external clients: `GET|POST /api/v1/smartflow/agreements/signing/{signature_token}`
- Expired agreement renewal: `POST /api/v1/smartflow/agreements/{agreement_id}/renew`
- Download contract preview as PDF: `GET /api/v1/smartflow/agreements/{agreement_id}/pdf`

### Lease Documents Screen API Map

For the provided Lease Documents, Lease Preview, and Lease Agreement generator screens, the frontend needs 17 lease-specific API calls:

- Lease metadata for dropdowns, filters, due days, and signature toggles: `GET /api/v1/smartflow/leases/metadata`
- Lease list/search/filter cards: `GET /api/v1/smartflow/leases` with `page`, `page_size`, `search`, and `status=all|active|pending_signature|expired|draft|cancelled`
- Generate lease with AI from prompt plus form fields: `POST /api/v1/smartflow/leases/generate`
- Enhance unsaved custom terms: `POST /api/v1/smartflow/leases/enhance-terms`
- Review unsaved lease draft: `POST /api/v1/smartflow/leases/review`
- Save draft or generated lease: `POST /api/v1/smartflow/leases`
- Preview/detail: `GET /api/v1/smartflow/leases/{lease_id}`
- Edit lease details/content/status: `PATCH /api/v1/smartflow/leases/{lease_id}`
- Delete a lease: `DELETE /api/v1/smartflow/leases/{lease_id}`
- AI review saved lease: `POST /api/v1/smartflow/leases/{lease_id}/review`
- Fix/enhance saved lease terms with AI: `POST /api/v1/smartflow/leases/{lease_id}/enhance-terms`
- Send lease for signature: `POST /api/v1/smartflow/leases/{lease_id}/send-signature`
- Owner/manual signing: `POST /api/v1/smartflow/leases/{lease_id}/sign`
- Public signing preview and submit: `GET|POST /api/v1/smartflow/leases/signing/{signature_token}`
- Renew expired lease: `POST /api/v1/smartflow/leases/{lease_id}/renew`
- Download PDF: `GET /api/v1/smartflow/leases/{lease_id}/pdf`

Lease list responses are tailored for the mobile card UI: `tenant_name`, `lease_number`, `property_address`, `property_type_label`, `monthly_rent_label`, `duration_label`, `created_date_label`, `status`, `status_tone`, `primary_action`, and `actions` are all returned directly. Detail responses include full `content`, `ai_review`, `signature_fields`, structured `property`, `rent`, `duration`, and `signature_request_url` when pending.

The invoice-style screen showing total outstanding is already backed by `GET /api/v1/invoices`, which returns `items` and `summary.total_outstanding`.

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

`POST /api/v1/ai/command` uses a compiled LangGraph workflow. It parses intent, collects normalized state, conditionally routes to invoice, email, bulk email, calendar, lease, agreement, group, or call nodes, and finalizes the response. The response includes `output.workflow_engine: "langgraph"` when the dependency is installed.

SmartFlow AI chat and voice endpoints also return navigation hints for app redirects:

- `POST /api/v1/smartflow/ai/chat`
- `POST /api/v1/smartflow/ai/voice-chat`
- `POST /api/v1/smartflow/ai/voice-chat-upload`
- `POST /api/v1/smartflow/voice/transcribe`

When the user says a command like "create invoice", LangGraph classifies the intent as `invoice` and the response includes:

```json
{
  "workflow": {"engine": "langgraph", "intent": "invoice"},
  "navigation": {
    "should_redirect": true,
    "action": "open_screen",
    "route_name": "invoice_create",
    "screen": "CreateInvoice",
    "path": "/invoices/create",
    "params": {
      "source": "mabdel_ai",
      "prefill_prompt": "Create invoice for Sarah",
      "intent": "invoice"
    }
  }
}
```

The frontend should show the processing/listening state while the request is pending, then redirect when `navigation.should_redirect` is `true`.

For mic buttons inside creation screens, use:

- `POST /api/v1/smartflow/ai/workflow-prefill`

Request:

```json
{
  "workflow_intent": "invoice",
  "transcript": "Create invoice for Sarah worth $500",
  "current_values": {}
}
```

`workflow_intent` can be `invoice`, `bulk_message`, `calendar`, `lease`, or `agreement`. The same endpoint also accepts `audio_base64`, `audio_url`, `audio_mime_type`, and `audio_filename`, matching the other voice endpoints.

Response:

```json
{
  "transcript": "Create invoice for Sarah worth $500",
  "workflow": {"engine": "langgraph", "intent": "invoice"},
  "navigation": {"should_redirect": true, "screen": "CreateInvoice"},
  "prefill": {
    "client_name": "Sarah",
    "currency": "USD",
    "items": [{"description": "Service", "quantity": 1, "unit_price": 500}]
  },
  "missing_fields": [],
  "ready_to_create": true,
  "create_endpoint": "/api/v1/invoices",
  "create_method": "POST",
  "next_action": "create"
}
```

The frontend should merge `prefill` into the visible form. If `missing_fields` is empty, it can enable the create/generate button or auto-submit after user confirmation. If fields are missing, keep the user on the screen and highlight those fields.

Supported AI redirect intents:

| User intent | LangGraph intent | `route_name` | `screen` | `path` |
| --- | --- | --- | --- | --- |
| Create invoice | `invoice` | `invoice_create` | `CreateInvoice` | `/invoices/create` |
| Draft normal email | `email` | `email_draft` | `EmailDraft` | `/email/draft` |
| Send bulk email/message | `bulk_message` | `bulk_message_create` | `CreateBulkMessage` | `/bulk-messages/create` |
| Schedule meeting/calendar event | `calendar` | `calendar_create` | `CreateCalendarEvent` | `/calendar/events/create` |
| Create lease/rental agreement | `lease` | `lease_create` | `CreateLease` | `/leases/create` |
| Create agreement/contract/NDA | `agreement` | `agreement_create` | `CreateAgreement` | `/agreements/create` |

### Twilio Voice Endpoints

- `POST /api/v1/calls/incoming`
- `POST /api/v1/calls/status`
- `WS /api/v1/calls/stream/{call_id}`
- `POST /api/v1/smartflow/calls/outbound`

Purpose:

- receive Twilio Voice webhooks
- return TwiML that connects the live call to a WebSocket media stream
- receive status callbacks for call lifecycle events
- initiate outbound calls from authenticated app users

Integration notes:

- `POST /api/v1/calls/incoming` expects Twilio form-encoded webhook payloads
- the endpoint returns `application/xml` TwiML, not JSON
- `PUBLIC_BACKEND_URL` must be set to the public API origin so generated stream URLs are correct
- when `TWILIO_VALIDATE_SIGNATURE=true`, requests must include a valid `X-Twilio-Signature`
- Twilio Media Streams require a public `wss://` endpoint in production
- `POST /api/v1/smartflow/calls/outbound` requires a bearer token and accepts either `phone_number` or `contact_id`

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

## Group and Chat Contracts

### Create a frontend-ready group

```http
POST /api/v1/smartflow/groups
Authorization: Bearer <jwt-access-token>
Content-Type: application/json

{
  "name": "Marketing Team",
  "avatar_url": "https://cdn.example.com/groups/marketing-team.png",
  "description": "Brand, campaign, and design collaborators",
  "member_ids": ["contact_id_1", "contact_id_2"],
  "admin_ids": ["contact_id_1"]
}
```

Response highlights:

- `member_count`
- `pending_invite_count`
- `members[]` with `role`, `presence`, and avatar/email/phone fields
- `conversation_id` to open the group chat screen

### Add a rich group chat message

```http
POST /api/v1/smartflow/messages
Authorization: Bearer <jwt-access-token>
Content-Type: application/json

{
  "conversation_id": "group_conversation_id",
  "contact_id": "sender_contact_id",
  "platform": "ai",
  "direction": "inbound",
  "content": "Here is the moodboard and project brief.",
  "attachments": [
    {
      "type": "image",
      "url": "https://cdn.example.com/uploads/moodboard.png",
      "thumbnail_url": "https://cdn.example.com/uploads/moodboard-thumb.png"
    },
    {
      "type": "document",
      "url": "https://cdn.example.com/uploads/project-brief-q1.pdf",
      "file_name": "Project_Brief_Q1.pdf",
      "mime_type": "application/pdf",
      "file_size_bytes": 2400000
    }
  ],
  "mentions": ["contact_id_2"]
}
```

Response highlights:

- `attachments[]`
- `attachment_count`
- `has_attachments`
- `mentions[]`
- `sender_name`, `sender_avatar_url`, `sender_presence`

New frontend integrations should prefer `/api/v1/*`.

## WebSockets

Protected WebSocket routes:

- `/api/v1/smartflow/ws/conversations/{conversation_id}?token=<access-token>`
- `/api/v1/smartflow/ws/inbox?token=<access-token>`

Public provider WebSocket route:

- `/api/v1/calls/stream/{call_id}`

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
- Business logo upload uses `POST /api/v1/smartflow/business-profile/logo` with multipart field `logo_file`. Configure `MEDIA_ROOT` as persistent storage in production.
- OTP and invoice email delivery can use SMTP, Resend, or Mailtrap. In non-development environments, email sends fail fast when no provider is configured.
- Google login is implemented at `POST /api/v1/auth/google` and requires `GOOGLE_CLIENT_ID`; social integrations still depend on provider credentials and callback URLs being configured in `.env`.
- AI endpoints return deterministic fallback content without `OPENAI_API_KEY`; configure it before relying on production AI output.
- Push delivery supports FCM for Android/web and APNs for iOS. Configure `FCM_SERVER_KEY` plus `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_BUNDLE_ID`, and `APNS_PRIVATE_KEY` before enabling real device notifications.
- Twilio Voice requires `TWILIO_AUTH_TOKEN` for signature validation and a public HTTPS base URL for stream generation.
- Unified social conversations use `/api/v1/smartflow/conversations`; pass `platform=whatsapp` for one channel or `platforms=whatsapp,facebook_messenger,instagram` for combined inbox tabs.
- Social integrations expose `sync_status`, `last_sync_at`, `last_error`, `external_account_name`, `message_sync_enabled`, and `webhook_status` for the Connect Social screen.
- Provider webhooks are matched by platform account ID or Telegram secret token; legacy `user_id` query webhooks still work for development/testing.
- Unsupported provider inbox APIs do not emit fake messages. They return `needs_provider_access` or `unsupported_by_provider` from the sync endpoint.
- Snapchat is included as `snapchat` for Snap Public Profile Messaging. Snap states this messaging API is brand-to-creator and allowlist-gated, so real sync needs `SNAPCHAT_CLIENT_ID`, `SNAPCHAT_CLIENT_SECRET`, OAuth callback setup, and Public Profile conversation metadata.

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
