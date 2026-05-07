from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response, WebSocket
from fastapi.responses import PlainTextResponse

from app.dependencies import get_mongo_database
from app.schemas.call import TwilioStatusCallbackPayload, TwilioWebhookPayload
from app.services.smartflow_service import SmartFlowService
from app.utils.responses import success_response
from app.services.call_service import CallService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(tags=["Calls"])
call_service = CallService()


def get_smartflow_service(db: AsyncIOMotorDatabase = Depends(get_mongo_database)) -> SmartFlowService:
    return SmartFlowService(db)


@router.post("/calls/incoming")
async def incoming_call(request: Request) -> Response:
    """
    Twilio Voice webhook.
    Returns TwiML that connects the live call to a WebSocket media stream.
    """
    form_data = await request.form()
    form_payload = {key: str(value) for key, value in form_data.multi_items()} if form_data else {}
    await call_service.validate_twilio_request(request, form_payload)

    payload = TwilioWebhookPayload.model_validate(form_payload) if form_payload else TwilioWebhookPayload()
    call_id = payload.call_sid or request.headers.get("x-call-id", "live-call")
    twiml = call_service.build_twiml_response(
        websocket_url=call_service.build_media_stream_url(call_id),
        call_id=call_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/calls/status", status_code=200)
async def call_status(
    request: Request,
    user_id: str | None = Query(default=None),
    call_log_id: str | None = Query(default=None),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    """
    Twilio status callback webhook.
    """
    form_data = await request.form()
    form_payload = {key: str(value) for key, value in form_data.multi_items()} if form_data else {}
    await call_service.validate_twilio_request(request, form_payload)
    payload = TwilioStatusCallbackPayload.model_validate(form_payload) if form_payload else TwilioStatusCallbackPayload()
    response_data = payload.model_dump()
    if user_id and call_log_id:
        updated_log = await service.update_call_log_from_provider_callback(
            user_id=user_id,
            call_log_id=call_log_id,
            twilio_call_sid=payload.call_sid,
            call_status=payload.call_status,
            call_duration=payload.call_duration,
            from_number=payload.from_number,
            to_number=payload.to_number,
        )
        response_data["call_log"] = updated_log
    return success_response(
        data=response_data,
        message="Twilio call status received successfully.",
    )


@router.websocket("/calls/stream/{call_id}", name="call_stream")
async def call_stream(websocket: WebSocket, call_id: str) -> None:
    """
    Receive live audio chunks, send AI audio reply.
    """
    await websocket.accept()
    await websocket.send_json(call_service.build_connected_event(call_id).model_dump())

    try:
        while True:
            raw_message = await websocket.receive()
            if raw_message.get("type") == "websocket.disconnect":
                break
            if "bytes" in raw_message and raw_message["bytes"] is not None:
                await websocket.send_json(call_service.build_audio_ack(call_id, len(raw_message["bytes"])).model_dump())
                continue
            text_payload = raw_message.get("text")
            if text_payload is None:
                continue

            stream_message = call_service.parse_stream_message(text_payload)
            if stream_message is None:
                await websocket.send_json(call_service.build_text_ack(call_id, text_payload).model_dump())
                continue

            if stream_message.event == "start":
                await websocket.send_json(
                    call_service.build_stream_started_event(call_id, stream_sid=stream_message.stream_sid).model_dump()
                )
            elif stream_message.event == "media":
                await websocket.send_json(
                    call_service.build_audio_ack(
                        call_id,
                        call_service.media_payload_size(stream_message),
                        stream_sid=stream_message.stream_sid,
                    ).model_dump()
                )
            elif stream_message.event == "stop":
                await websocket.send_json(
                    call_service.build_stream_stopped_event(call_id, stream_sid=stream_message.stream_sid).model_dump()
                )
                break
            else:
                await websocket.send_json(
                    call_service.build_text_ack(
                        call_id,
                        stream_message.event,
                        stream_sid=stream_message.stream_sid,
                    ).model_dump()
                )
    finally:
        await websocket.close()
