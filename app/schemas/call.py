from __future__ import annotations

from pydantic import BaseModel, Field


class IncomingCallResponse(BaseModel):
    action: str = "connect_stream"
    websocket_url: str
    call_id: str


class CallStreamEvent(BaseModel):
    event: str
    call_id: str
    bytes_received: int | None = None
    message: str | None = None


class TwilioWebhookPayload(BaseModel):
    call_sid: str | None = Field(default=None, alias="CallSid")
    from_number: str | None = Field(default=None, alias="From")
    to_number: str | None = Field(default=None, alias="To")

    model_config = {"populate_by_name": True}
