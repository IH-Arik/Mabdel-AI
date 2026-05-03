from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.realtime import conversation_realtime_hub, inbox_realtime_hub
from app.core.security import decode_token
from app.core.exceptions import AppException
from app.dependencies import get_current_user, get_mongo_database
from app.repositories.auth_repository import AuthRepository
from app.schemas.smartflow import (
    AIVoiceOption,
    AIChatRequest,
    BulkMessageCreateRequest,
    BulkMessageUpdateRequest,
    BulkRecipientValidationRequest,
    CalendarEventCreateRequest,
    CalendarEventShareRequest,
    CalendarEventUpdateRequest,
    CallLogCreateRequest,
    CallLogUpdateRequest,
    ChangePasswordRequest,
    ContactCreateRequest,
    ContactUpdateRequest,
    ConversationCreateRequest,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    GroupCreateRequest,
    GroupUpdateRequest,
    ForwardMessageRequest,
    MessageCreateRequest,
    MessageUpdateRequest,
    PushTokenRequest,
    ReplyMessageRequest,
    SettingsUpdateRequest,
    SocialIntegrationUpsertRequest,
    TelegramManualConnectRequest,
    TypingStateRequest,
    VoiceCommandRequest,
)
from app.services.smartflow_service import SmartFlowService
from app.utils.responses import success_response

router = APIRouter(prefix="/smartflow", tags=["SmartFlow"])


def get_smartflow_service(db: AsyncIOMotorDatabase = Depends(get_mongo_database)) -> SmartFlowService:
    return SmartFlowService(db)


@router.websocket("/ws/conversations/{conversation_id}")
async def conversation_stream(websocket: WebSocket, conversation_id: str, token: str) -> None:
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            await websocket.close(code=1008)
            return
        db = await get_mongo_database()
        user = await AuthRepository(db).get_user_by_id(claims.get("sub", ""))
        if not user:
            await websocket.close(code=1008)
            return
        service = SmartFlowService(db)
        await service.get_conversation(str(user["_id"]), conversation_id)
        await conversation_realtime_hub.connect(conversation_id, websocket)
        await websocket.send_json({"event": "connected", "conversation_id": conversation_id, "data": {"connected": True}})
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except AppException:
        await websocket.close(code=1008)
    finally:
        await conversation_realtime_hub.disconnect(conversation_id, websocket)


@router.websocket("/ws/inbox")
async def inbox_stream(websocket: WebSocket, token: str) -> None:
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            await websocket.close(code=1008)
            return
        db = await get_mongo_database()
        user = await AuthRepository(db).get_user_by_id(claims.get("sub", ""))
        if not user:
            await websocket.close(code=1008)
            return
        user_id = str(user["_id"])
        service = SmartFlowService(db)
        await inbox_realtime_hub.connect(user_id, websocket)
        summary = await service.get_unread_message_summary(user_id, None)
        await websocket.send_json({"event": "connected", "channel": "inbox", "data": {"connected": True, "summary": summary}})
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except AppException:
        await websocket.close(code=1008)
    finally:
        if 'user_id' in locals():
            await inbox_realtime_hub.disconnect(user_id, websocket)


@router.get("/home")
async def get_home_dashboard(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_home_dashboard(current_user)
    return success_response(data=data, message="Home dashboard fetched successfully.")


@router.get("/contacts")
async def list_contacts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_contacts(str(current_user["_id"]), page, page_size, search)
    return success_response(data=data, message="Contacts fetched successfully.")


@router.post("/contacts", status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_contact(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Contact created successfully.")


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    payload: ContactUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_contact(str(current_user["_id"]), contact_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Contact updated successfully.")


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    await service.delete_contact(str(current_user["_id"]), contact_id)
    return success_response(data={"deleted": True}, message="Contact deleted successfully.")


@router.get("/conversations")
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    platform: str | None = None,
    archived: bool | None = None,
    unread_only: bool = False,
    type_filter: str | None = Query(default=None, alias="type"),
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_conversations(str(current_user["_id"]), page, page_size, search, platform, archived, unread_only, type_filter)
    return success_response(data=data, message="Conversations fetched successfully.")


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_conversation(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Conversation created successfully.")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_conversation(str(current_user["_id"]), conversation_id)
    return success_response(data=data, message="Conversation fetched successfully.")


@router.patch("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    archived: bool = True,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.archive_conversation(str(current_user["_id"]), conversation_id, archived)
    return success_response(data=data, message="Conversation updated successfully.")


@router.post("/conversations/{conversation_id}/mark-read")
async def mark_conversation_read(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.mark_conversation_read(str(current_user["_id"]), conversation_id)
    return success_response(data=data, message="Conversation marked as read successfully.")


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    platform: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_messages(str(current_user["_id"]), conversation_id, page, page_size, search, platform)
    return success_response(data=data, message="Messages fetched successfully.")


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_message(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Message created successfully.")


@router.patch("/messages/{message_id}")
async def update_message(
    message_id: str,
    payload: MessageUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_message(str(current_user["_id"]), message_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Message updated successfully.")


@router.post("/messages/{message_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_to_message(
    message_id: str,
    payload: ReplyMessageRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.reply_to_message(str(current_user["_id"]), message_id, payload.model_dump())
    return success_response(data=data, message="Reply created successfully.")


@router.post("/messages/{message_id}/forward", status_code=status.HTTP_201_CREATED)
async def forward_message(
    message_id: str,
    payload: ForwardMessageRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.forward_message(str(current_user["_id"]), message_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Message forwarded successfully.")


@router.get("/messages/unread-summary")
async def unread_summary(
    platform: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_unread_message_summary(str(current_user["_id"]), platform)
    return success_response(data=data, message="Unread summary fetched successfully.")


@router.get("/conversations/{conversation_id}/typing")
async def get_typing_state(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_typing_state(str(current_user["_id"]), conversation_id)
    return success_response(data=data, message="Typing state fetched successfully.")


@router.post("/conversations/{conversation_id}/typing")
async def set_typing_state(
    conversation_id: str,
    payload: TypingStateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.set_typing_state(str(current_user["_id"]), conversation_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Typing state updated successfully.")


@router.post("/ai/chat")
async def ai_chat(
    payload: AIChatRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.chat_with_ai(
        str(current_user["_id"]),
        payload.content,
        response_mode=payload.response_mode,
        voice_id=payload.voice_id,
    )
    return success_response(data=data, message="AI response generated successfully.")


@router.get("/ai/voices")
async def list_ai_voices(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_ai_voices()
    return success_response(data=data, message="AI voices fetched successfully.")


@router.get("/ai/history")
async def list_ai_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    command_type: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: str | None = None,
    date_to: str | None = None,
    replayable_only: bool = False,
    group_by: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_ai_history(
        str(current_user["_id"]),
        page,
        page_size,
        search,
        command_type,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        replayable_only=replayable_only,
        group_by=group_by,
    )
    return success_response(data=data, message="AI command history fetched successfully.")


@router.post("/bulk-messages/recipients/validate")
async def validate_bulk_recipients(
    payload: BulkRecipientValidationRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.validate_bulk_recipients(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Bulk recipients validated successfully.")


@router.get("/bulk-messages")
async def list_bulk_messages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    channel: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_bulk_messages(str(current_user["_id"]), page, page_size, search, status_filter, channel)
    return success_response(data=data, message="Bulk messages fetched successfully.")


@router.get("/bulk-messages/{bulk_message_id}")
async def get_bulk_message(
    bulk_message_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_bulk_message(str(current_user["_id"]), bulk_message_id)
    return success_response(data=data, message="Bulk message fetched successfully.")


@router.post("/bulk-messages", status_code=status.HTTP_201_CREATED)
async def create_bulk_message(
    payload: BulkMessageCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_bulk_message(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Bulk message created successfully.")


@router.patch("/bulk-messages/{bulk_message_id}")
async def update_bulk_message(
    bulk_message_id: str,
    payload: BulkMessageUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_bulk_message(str(current_user["_id"]), bulk_message_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Bulk message updated successfully.")


@router.post("/bulk-messages/{bulk_message_id}/send")
async def send_bulk_message(
    bulk_message_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.send_bulk_message(str(current_user["_id"]), bulk_message_id)
    return success_response(data=data, message="Bulk message dispatched successfully.")


@router.post("/bulk-messages/{bulk_message_id}/cancel")
async def cancel_bulk_message(
    bulk_message_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.cancel_bulk_message(str(current_user["_id"]), bulk_message_id)
    return success_response(data=data, message="Bulk message cancelled successfully.")


@router.post("/ai/history/{history_id}/replay")
async def replay_ai_history(
    history_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.replay_ai_command(str(current_user["_id"]), history_id)
    return success_response(data=data, message="AI command replayed successfully.")


@router.post("/voice/transcribe")
async def transcribe_voice(
    payload: VoiceCommandRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.process_voice_command(
        str(current_user["_id"]),
        payload.transcript,
        payload.audio_url,
        audio_base64=payload.audio_base64,
        audio_mime_type=payload.audio_mime_type,
        audio_filename=payload.audio_filename,
        response_mode=payload.response_mode,
        voice_id=payload.voice_id,
    )
    return success_response(data=data, message="Voice command processed successfully.")


@router.post("/ai/voice-chat")
async def ai_voice_chat(
    payload: VoiceCommandRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.process_voice_command(
        str(current_user["_id"]),
        payload.transcript,
        payload.audio_url,
        audio_base64=payload.audio_base64,
        audio_mime_type=payload.audio_mime_type,
        audio_filename=payload.audio_filename,
        response_mode=payload.response_mode,
        voice_id=payload.voice_id,
    )
    return success_response(data=data, message="AI voice chat processed successfully.")


@router.post("/ai/voice-chat-upload")
async def ai_voice_chat_upload(
    audio_file: UploadFile = File(...),
    response_mode: str = Form(default="audio"),
    voice_id: str | None = Form(default=None),
    transcript: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    audio_bytes = await audio_file.read()
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else None
    data = await service.process_voice_command(
        str(current_user["_id"]),
        transcript,
        None,
        audio_base64=audio_base64,
        audio_mime_type=audio_file.content_type or "audio/wav",
        audio_filename=audio_file.filename or "voice.wav",
        response_mode=response_mode,
        voice_id=voice_id,
    )
    return success_response(data=data, message="AI voice chat processed successfully.")


@router.get("/calendar/events")
async def list_calendar_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    upcoming_only: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    contact_id: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_calendar_events(
        str(current_user["_id"]),
        page,
        page_size,
        search,
        upcoming_only,
        date_from=date_from,
        date_to=date_to,
        contact_id=contact_id,
    )
    return success_response(data=data, message="Calendar events fetched successfully.")


@router.get("/calendar/events/{event_id}")
async def get_calendar_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_calendar_event(str(current_user["_id"]), event_id)
    return success_response(data=data, message="Calendar event fetched successfully.")


@router.post("/calendar/events", status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    payload: CalendarEventCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_calendar_event(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Calendar event created successfully.")


@router.patch("/calendar/events/{event_id}")
async def update_calendar_event(
    event_id: str,
    payload: CalendarEventUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_calendar_event(str(current_user["_id"]), event_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Calendar event updated successfully.")


@router.post("/calendar/events/{event_id}/share")
async def share_calendar_event(
    event_id: str,
    payload: CalendarEventShareRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.share_calendar_event(str(current_user["_id"]), event_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Calendar event shared successfully.")


@router.delete("/calendar/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    await service.delete_calendar_event(str(current_user["_id"]), event_id)
    return success_response(data={"deleted": True}, message="Calendar event deleted successfully.")


@router.get("/documents")
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    doc_type: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_documents(str(current_user["_id"]), page, page_size, search, doc_type)
    return success_response(data=data, message="Documents fetched successfully.")


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_document(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Document created successfully.")


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_document(str(current_user["_id"]), document_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Document updated successfully.")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    await service.delete_document(str(current_user["_id"]), document_id)
    return success_response(data={"deleted": True}, message="Document deleted successfully.")


@router.get("/calls")
async def list_calls(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_call_logs(str(current_user["_id"]), page, page_size, status_filter)
    return success_response(data=data, message="Call logs fetched successfully.")


@router.post("/calls", status_code=status.HTTP_201_CREATED)
async def create_call_log(
    payload: CallLogCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_call_log(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Call log created successfully.")


@router.patch("/calls/{call_id}")
async def update_call_log(
    call_id: str,
    payload: CallLogUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_call_log(str(current_user["_id"]), call_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Call log updated successfully.")


@router.get("/calls/summary")
async def get_call_summary(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_call_summary(str(current_user["_id"]))
    return success_response(data=data, message="Call analytics fetched successfully.")


@router.get("/integrations")
async def list_integrations(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_integrations(str(current_user["_id"]))
    return success_response(data=data, message="Integrations fetched successfully.")


@router.get("/integrations/catalog")
async def list_integration_catalog(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_integration_catalog(str(current_user["_id"]))
    return success_response(data=data, message="Integration catalog fetched successfully.")


@router.post("/integrations", status_code=status.HTTP_201_CREATED)
async def connect_integration(
    payload: SocialIntegrationUpsertRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.upsert_integration(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Integration connected successfully.")


@router.post("/integrations/telegram/manual-connect", status_code=status.HTTP_201_CREATED)
async def connect_telegram_manual(
    payload: TelegramManualConnectRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.connect_telegram_manual(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Telegram connected successfully.")


@router.get("/integrations/{platform}/oauth/start")
async def start_integration_oauth(
    platform: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.start_integration_oauth(str(current_user["_id"]), platform)
    return success_response(data=data, message="Integration OAuth started successfully.")


@router.get("/integrations/{platform}/oauth/callback")
async def complete_integration_oauth(
    platform: str,
    code: str,
    state: str,
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.complete_integration_oauth(platform, code, state)
    return success_response(data=data, message="Integration OAuth completed successfully.")


@router.delete("/integrations/{platform}")
async def disconnect_integration(
    platform: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.disconnect_integration(str(current_user["_id"]), platform)
    return success_response(data=data, message="Integration disconnected successfully.")


@router.get("/integrations/{platform}/webhook")
async def verify_platform_webhook(
    platform: str,
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    if platform in {"instagram", "facebook_messenger", "whatsapp"}:
        service.validate_meta_webhook_challenge(hub_mode, hub_verify_token)
        return success_response(data={"challenge": hub_challenge}, message="Webhook verified successfully.")
    return success_response(data={"verified": True}, message="Webhook verification not required for this platform.")


@router.post("/integrations/{platform}/webhook")
async def receive_platform_webhook(
    platform: str,
    request: Request,
    user_id: str = Query(..., min_length=1),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    if platform == "telegram":
        await service.validate_platform_webhook_secret(user_id, platform, x_telegram_bot_api_secret_token or x_webhook_secret)
    else:
        service.validate_webhook_secret(x_webhook_secret)
    raw_payload = await request.json()
    if isinstance(raw_payload, dict):
        normalized = raw_payload
    else:
        raise AppException(status_code=400, code="WEBHOOK_PAYLOAD_INVALID", message="Webhook payload must be a JSON object.")
    data = await service.handle_inbound_webhook(user_id, platform, normalized)
    return success_response(data=data, message="Webhook processed successfully.")


@router.get("/notifications")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_notifications(str(current_user["_id"]), page, page_size, unread_only)
    return success_response(data=data, message="Notifications fetched successfully.")


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.mark_notification_read(str(current_user["_id"]), notification_id)
    return success_response(data=data, message="Notification marked as read.")


@router.post("/notifications/dispatch-pending")
async def dispatch_pending_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.dispatch_pending_push_notifications(str(current_user["_id"]), limit=limit)
    return success_response(data={"items": data}, message="Pending push notifications dispatched successfully.")


@router.get("/groups")
async def list_groups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.list_groups(str(current_user["_id"]), page, page_size, search)
    return success_response(data=data, message="Groups fetched successfully.")


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.create_group(str(current_user["_id"]), payload.model_dump())
    return success_response(data=data, message="Group created successfully.")


@router.patch("/groups/{group_id}")
async def update_group(
    group_id: str,
    payload: GroupUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_group(str(current_user["_id"]), group_id, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Group updated successfully.")


@router.get("/settings")
async def get_settings(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.get_settings(current_user)
    return success_response(data=data, message="Settings fetched successfully.")


@router.patch("/settings")
async def update_settings(
    payload: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.update_settings(current_user, payload.model_dump(exclude_unset=True))
    return success_response(data=data, message="Settings updated successfully.")


@router.post("/devices/push-token")
async def register_push_token(
    payload: PushTokenRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.register_push_token(current_user, payload.model_dump())
    return success_response(data=data, message="Push token registered successfully.")


@router.post("/settings/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.change_password(current_user, payload.current_password, payload.new_password)
    return success_response(data=data, message="Password changed successfully.")


@router.post("/settings/revoke-sessions")
async def revoke_sessions(
    current_user: dict = Depends(get_current_user),
    service: SmartFlowService = Depends(get_smartflow_service),
) -> dict:
    data = await service.revoke_sessions(current_user)
    return success_response(data=data, message="Sessions revoked successfully.")
