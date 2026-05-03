from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.pagination import PaginatedPayload

PlatformType = Literal["whatsapp", "facebook_messenger", "instagram", "linkedin", "twitter_x", "telegram", "sms", "email", "google_business", "ai"]
MessageDirection = Literal["inbound", "outbound"]
MessageStatus = Literal["sent", "delivered", "read"]
ConversationType = Literal["direct", "group", "ai"]
BulkMessageChannel = Literal["email", "sms"]
BulkMessageStatus = Literal["draft", "scheduled", "processing", "sent", "partial_failed", "failed", "cancelled"]
BulkRecipientStatus = Literal["queued", "sent", "failed", "skipped"]
AIResponseState = Literal["thinking", "processing", "responded"]
VoiceState = Literal["listening", "processing", "responded"]
AIResponseMode = Literal["text", "audio", "both"]
CommandType = Literal["invoice", "voice", "email", "report", "message", "agreement", "calendar", "bulk_message", "legal", "document"]
CommandStatus = Literal["completed", "archived", "exported", "delivered", "scheduled", "processing", "failed"]
DocumentType = Literal["agreement", "invoice", "lease", "others"]
CallType = Literal["scheduled", "missed", "completed"]
CallStatus = Literal["ai_ready", "callback", "missed", "completed"]
IntegrationStatus = Literal["connected", "disconnected"]
NotificationType = Literal["message", "missed_call", "scheduled_call", "ai_task", "calendar"]
MeetingMode = Literal["offline", "online"]
MeetingStatus = Literal["scheduled", "cancelled", "completed"]


class PlatformIdentity(BaseModel):
    platform: PlatformType
    external_id: str = Field(min_length=1, max_length=255)
    handle: str | None = None


class ContactCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    identities: list[PlatformIdentity] = Field(default_factory=list)


class ContactUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    identities: list[PlatformIdentity] | None = None
    presence: str | None = None


class ContactResponse(BaseModel):
    id: str
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    identities: list[PlatformIdentity] = Field(default_factory=list)
    presence: str = "offline"
    created_at: datetime
    updated_at: datetime


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    contact_id: str | None = None
    member_ids: list[str] = Field(default_factory=list)
    type: ConversationType = "direct"
    platform: PlatformType = "whatsapp"


class ConversationResponse(BaseModel):
    id: str
    title: str | None = None
    type: ConversationType
    platform: PlatformType
    platform_label: str = "WhatsApp"
    platform_icon_key: str = "whatsapp"
    platform_badge_color: str = "#25D366"
    member_ids: list[str] = Field(default_factory=list)
    archived: bool = False
    avatar_url: str | None = None
    presence: str = "offline"
    presence_label: str = "Offline"
    is_ai_assistant: bool = False
    is_group: bool = False
    contact_name: str | None = None
    participant_preview: list[str] = Field(default_factory=list)
    last_message_preview: str | None = None
    last_message_sender_name: str | None = None
    unread_count: int = 0
    has_unread: bool = False
    delivery_state: str | None = None
    display_time_label: str | None = None
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    conversation_id: str
    contact_id: str | None = None
    platform: PlatformType
    direction: MessageDirection
    content: str = Field(min_length=1)
    media_url: str | None = None
    reply_to_message_id: str | None = None
    forward_from_message_id: str | None = None


class MessageUpdateRequest(BaseModel):
    status: MessageStatus | None = None
    is_archived: bool | None = None
    unread_count: int | None = Field(default=None, ge=0)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    contact_id: str | None = None
    platform: PlatformType
    direction: MessageDirection
    content: str
    media_url: str | None = None
    status: MessageStatus
    timestamp: datetime
    unread_count: int = 0
    is_archived: bool = False
    read_at: datetime | None = None
    delivered_at: datetime | None = None
    is_read: bool = False
    read_receipt_label: str | None = None
    status_timestamps: dict[str, datetime | None] = Field(default_factory=dict)
    reply_to_message_id: str | None = None
    forward_from_message_id: str | None = None
    reply_to_message_preview: dict[str, Any] | None = None
    forward_from_message_preview: dict[str, Any] | None = None


class BulkMessageRecipientRef(BaseModel):
    id: str | None = None
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    initials: str | None = None
    source: Literal["contact", "group_member", "raw_email"]


class BulkMessageAttachment(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=5, max_length=1000)


class BulkRecipientValidationRequest(BaseModel):
    channel: BulkMessageChannel = "email"
    recipient_emails: list[str] = Field(default_factory=list)
    contact_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)


class BulkRecipientValidationResponse(BaseModel):
    channel: BulkMessageChannel
    valid_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    recipients: list[BulkMessageRecipientRef] = Field(default_factory=list)
    invalid_entries: list[str] = Field(default_factory=list)
    duplicate_entries: list[str] = Field(default_factory=list)
    unavailable_contact_ids: list[str] = Field(default_factory=list)
    unavailable_group_ids: list[str] = Field(default_factory=list)


class BulkMessageCreateRequest(BaseModel):
    channel: BulkMessageChannel = "email"
    recipient_emails: list[str] = Field(default_factory=list)
    contact_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    attachments: list[BulkMessageAttachment] = Field(default_factory=list)
    scheduled_at: datetime | None = None
    timezone: str = Field(default="UTC", max_length=64)
    send_now: bool = True
    ai_transcript: str | None = None


class BulkMessageUpdateRequest(BaseModel):
    recipient_emails: list[str] | None = None
    contact_ids: list[str] | None = None
    group_ids: list[str] | None = None
    subject: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    attachments: list[BulkMessageAttachment] | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    send_now: bool | None = None
    ai_transcript: str | None = None


class BulkMessageRecipientDelivery(BaseModel):
    target: str
    contact_id: str | None = None
    name: str | None = None
    status: BulkRecipientStatus
    error: str | None = None
    sent_at: datetime | None = None


class BulkMessageResponse(BaseModel):
    id: str
    channel: BulkMessageChannel
    status: BulkMessageStatus
    subject: str | None = None
    content: str
    attachments: list[BulkMessageAttachment] = Field(default_factory=list)
    recipient_emails: list[str] = Field(default_factory=list)
    contact_ids: list[str] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)
    recipients: list[BulkMessageRecipientRef] = Field(default_factory=list)
    deliveries: list[BulkMessageRecipientDelivery] = Field(default_factory=list)
    scheduled_at: datetime | None = None
    timezone: str = "UTC"
    ai_transcript: str | None = None
    character_count: int = 0
    segment_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None = None


class AIChatRequest(BaseModel):
    content: str = Field(min_length=1)
    response_mode: AIResponseMode = "text"
    voice_id: str | None = None


class AIVoiceOption(BaseModel):
    id: str
    label: str
    gender: Literal["male", "female", "neutral"]
    style: str
    provider_voice: str


class AIChatResponse(BaseModel):
    conversation_id: str
    state: AIResponseState
    user_message: MessageResponse
    ai_message: MessageResponse
    audio: dict[str, Any] | None = None


class VoiceCommandRequest(BaseModel):
    transcript: str | None = None
    audio_url: str | None = None
    audio_base64: str | None = None
    audio_mime_type: str = "audio/wav"
    audio_filename: str = "voice.wav"
    response_mode: AIResponseMode = "both"
    voice_id: str | None = None


class VoiceCommandResponse(BaseModel):
    state: VoiceState
    transcript: str
    ai_response: str
    history_id: str
    audio: dict[str, Any] | None = None


class ReplyMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    platform: PlatformType
    contact_id: str | None = None
    media_url: str | None = None


class ForwardMessageRequest(BaseModel):
    conversation_id: str
    platform: PlatformType
    contact_id: str | None = None
    content: str | None = Field(default=None, min_length=1)
    media_url: str | None = None


class TypingStateRequest(BaseModel):
    is_typing: bool = True
    actor_name: str | None = Field(default=None, max_length=120)
    actor_type: Literal["user", "ai", "contact"] = "ai"
    preview_text: str | None = Field(default=None, max_length=280)
    state_label: str | None = Field(default=None, max_length=80)


class TypingStateResponse(BaseModel):
    conversation_id: str
    is_typing: bool
    actor_name: str | None = None
    actor_type: Literal["user", "ai", "contact"] = "ai"
    preview_text: str | None = None
    state_label: str | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class AICommandHistoryItem(BaseModel):
    id: str
    user_id: str
    command_text: str
    command_type: CommandType
    status: CommandStatus
    timestamp: datetime
    is_replayable: bool = True
    command_type_label: str
    status_label: str
    icon: str
    accent_tone: str
    date_bucket: Literal["today", "yesterday", "older"]
    related_resource: dict[str, Any] | None = None
    preview_payload: dict[str, Any] | None = None


class CalendarEventCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    contact_ids: list[str] = Field(default_factory=list)
    meeting_mode: MeetingMode = "offline"
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    notify_via_push: bool = True
    notify_via_email: bool = False
    notify_via_sms: bool = False
    timezone: str = Field(default="UTC", max_length=64)
    reminder_minutes: int = Field(default=15, ge=0, le=10080)
    google_event_id: str | None = None
    status: MeetingStatus = "scheduled"


class CalendarEventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    contact_ids: list[str] | None = None
    meeting_mode: MeetingMode | None = None
    location: str | None = Field(default=None, max_length=200)
    meeting_link: str | None = Field(default=None, max_length=500)
    notify_via_push: bool | None = None
    notify_via_email: bool | None = None
    notify_via_sms: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)
    google_event_id: str | None = None
    status: MeetingStatus | None = None


class CalendarAttendeeResponse(BaseModel):
    id: str
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    initials: str


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    contact_ids: list[str] = Field(default_factory=list)
    attendees: list[CalendarAttendeeResponse] = Field(default_factory=list)
    attendee_count: int = 0
    meeting_mode: MeetingMode = "offline"
    location: str | None = None
    meeting_link: str | None = None
    notify_via_push: bool = True
    notify_via_email: bool = False
    notify_via_sms: bool = False
    timezone: str = "UTC"
    reminder_minutes: int
    google_event_id: str | None = None
    sync_status: str = "local"
    status: MeetingStatus = "scheduled"
    share_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CalendarEventShareRequest(BaseModel):
    channel: Literal["email", "link", "manual"] = "link"
    recipient_email: EmailStr | None = None
    message: str | None = Field(default=None, max_length=1000)


class CalendarEventShareResponse(BaseModel):
    event_id: str
    channel: Literal["email", "link", "manual"]
    recipient_email: EmailStr | None = None
    share_url: str | None = None


class DocumentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: DocumentType = "others"
    file_url: str = Field(min_length=5)
    contact_id: str | None = None
    conversation_id: str | None = None


class DocumentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    type: DocumentType | None = None
    file_url: str | None = Field(default=None, min_length=5)
    contact_id: str | None = None
    conversation_id: str | None = None


class DocumentResponse(BaseModel):
    id: str
    name: str
    type: DocumentType
    file_url: str
    preview_url: str
    contact_id: str | None = None
    conversation_id: str | None = None
    created_at: datetime


class CallLogCreateRequest(BaseModel):
    contact_id: str | None = None
    call_type: CallType
    scheduled_at: datetime | None = None
    duration: int = Field(default=0, ge=0)
    ai_ready: bool = False
    callback_requested: bool = False


class CallLogUpdateRequest(BaseModel):
    call_type: CallType | None = None
    scheduled_at: datetime | None = None
    duration: int | None = Field(default=None, ge=0)
    ai_ready: bool | None = None
    callback_requested: bool | None = None
    status: CallStatus | None = None


class CallLogResponse(BaseModel):
    id: str
    contact_id: str | None = None
    call_type: CallType
    scheduled_at: datetime | None = None
    duration: int
    ai_ready: bool
    callback_requested: bool
    timestamp: datetime
    status: CallStatus


class SocialIntegrationUpsertRequest(BaseModel):
    platform: PlatformType
    access_token: str = Field(min_length=1)
    refresh_token: str | None = None
    external_account_id: str | None = None


class TelegramManualConnectRequest(BaseModel):
    bot_token: str = Field(min_length=10, max_length=255)
    bot_username: str | None = Field(default=None, max_length=255)
    secret_token: str | None = Field(default=None, min_length=8, max_length=255)


class TelegramManualConnectResponse(BaseModel):
    connected: bool = True
    platform: Literal["telegram"] = "telegram"
    webhook_url: str
    secret_token: str
    integration: SocialIntegrationResponse


class SocialIntegrationResponse(BaseModel):
    id: str
    platform: PlatformType
    status: IntegrationStatus
    connected: bool = False
    platform_label: str = "WhatsApp"
    description: str | None = None
    icon_key: str | None = None
    brand_color: str | None = None
    cta_label: str = "Connect"
    is_available: bool = True
    is_configured: bool = False
    auth_mode: Literal["oauth", "manual", "hybrid"] = "oauth"
    health_status: Literal["connected", "disconnected", "pending", "needs_reauth", "misconfigured", "error"] = "disconnected"
    external_account_id: str | None = None
    connected_at: datetime | None = None
    last_webhook_at: datetime | None = None


class SocialIntegrationCatalogItem(BaseModel):
    platform: PlatformType
    platform_label: str
    description: str
    icon_key: str
    brand_color: str
    status: Literal["connected", "disconnected", "pending", "needs_reauth", "misconfigured", "error"]
    connected: bool = False
    cta_label: str = "Connect"
    is_available: bool = True
    is_configured: bool = False
    auth_mode: Literal["oauth", "manual", "hybrid"] = "oauth"
    external_account_id: str | None = None
    connected_at: datetime | None = None
    last_webhook_at: datetime | None = None


class WebhookMessageRequest(BaseModel):
    event_id: str = Field(min_length=1)
    contact_external_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    media_url: str | None = None
    timestamp: datetime | None = None


class NotificationPreferences(BaseModel):
    new_messages: bool = True
    missed_calls: bool = True
    scheduled_calls: bool = True
    ai_tasks: bool = True
    calendar_reminders: bool = True


class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    title: str
    body: str
    read: bool = False
    created_at: datetime


class PushTokenRequest(BaseModel):
    device_id: str = Field(min_length=1)
    token: str = Field(min_length=8)
    platform: Literal["ios", "android", "web"] = "ios"


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    member_ids: list[str] = Field(default_factory=list)
    admin_ids: list[str] = Field(default_factory=list)


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    member_ids: list[str] | None = None
    admin_ids: list[str] | None = None


class GroupResponse(BaseModel):
    id: str
    name: str
    member_ids: list[str] = Field(default_factory=list)
    admin_ids: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    created_at: datetime


class SettingsUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = None
    language_preference: str | None = Field(default=None, min_length=2, max_length=10)
    notification_preferences: NotificationPreferences | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SettingsResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    avatar_url: str | None = None
    language_preference: str = "EN"
    notification_preferences: NotificationPreferences
    integrations: list[SocialIntegrationResponse] = Field(default_factory=list)


class HomeDashboardResponse(BaseModel):
    greeting_name: str
    language_preference: str = "EN"
    inbox: dict[str, Any]
    contacts: dict[str, Any]
    calendar: dict[str, Any]
    integrations: dict[str, Any]
    documents: dict[str, Any]
    ai_call_analytics: dict[str, Any]
    notifications: dict[str, Any]


ContactListResponse = PaginatedPayload[ContactResponse]
ConversationListResponse = PaginatedPayload[ConversationResponse]
MessageListResponse = PaginatedPayload[MessageResponse]
HistoryListResponse = PaginatedPayload[AICommandHistoryItem]
CalendarListResponse = PaginatedPayload[CalendarEventResponse]
DocumentListResponse = PaginatedPayload[DocumentResponse]
CallLogListResponse = PaginatedPayload[CallLogResponse]
NotificationListResponse = PaginatedPayload[NotificationResponse]
GroupListResponse = PaginatedPayload[GroupResponse]
