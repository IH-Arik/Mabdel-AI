from __future__ import annotations

from fastapi import APIRouter, Request, WebSocket

from app.schemas.call import TwilioWebhookPayload
from app.services.call_service import CallService

router = APIRouter(tags=["Calls"])
call_service = CallService()


@router.post("/calls/incoming")
async def incoming_call(request: Request) -> dict:
    """
    Call provider webhook.
    Create call session and connect audio stream.
    """
    form_data = await request.form()
    payload = TwilioWebhookPayload.model_validate(dict(form_data)) if form_data else TwilioWebhookPayload()
    call_id = payload.call_sid or request.headers.get("x-call-id", "live-call")
    websocket_base = request.url_for("call_stream", call_id=call_id)
    websocket_url = websocket_base.replace(scheme="wss")

    return call_service.build_incoming_response(str(websocket_url), call_id).model_dump()


@router.websocket("/calls/stream/{call_id}", name="call_stream")
async def call_stream(websocket: WebSocket, call_id: str) -> None:
    """
    Receive live audio chunks, send AI audio reply.
    """
    await websocket.accept()
    await websocket.send_json(call_service.build_connected_event(call_id).model_dump())

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"] is not None:
                await websocket.send_json(call_service.build_audio_ack(call_id, len(message["bytes"])).model_dump())
            elif "text" in message and message["text"] is not None:
                await websocket.send_json(call_service.build_text_ack(call_id, message["text"]).model_dump())
    finally:
        await websocket.close()
