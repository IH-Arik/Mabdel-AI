from __future__ import annotations

from app.schemas.call import CallStreamEvent, IncomingCallResponse


class CallService:
    def build_incoming_response(self, websocket_url: str, call_id: str) -> IncomingCallResponse:
        return IncomingCallResponse(websocket_url=websocket_url, call_id=call_id)

    def build_connected_event(self, call_id: str) -> CallStreamEvent:
        return CallStreamEvent(event="connected", call_id=call_id)

    def build_audio_ack(self, call_id: str, chunk_size: int) -> CallStreamEvent:
        return CallStreamEvent(event="audio_ack", call_id=call_id, bytes_received=chunk_size)

    def build_text_ack(self, call_id: str, message: str) -> CallStreamEvent:
        return CallStreamEvent(event="text_ack", call_id=call_id, message=message)
