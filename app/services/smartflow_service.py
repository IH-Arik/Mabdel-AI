from __future__ import annotations

import re
import secrets
from datetime import date, datetime, timedelta
from math import ceil
from urllib.parse import quote_plus
from urllib.parse import urlencode

from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.config import settings
from app.core.crypto import encrypt_value
from app.core.exceptions import AppException
from app.core.realtime import conversation_realtime_hub, inbox_realtime_hub
from app.core.security import hash_password, verify_password
from app.services.email_service import EmailService
from app.services.mabdel_ai_service import MabdelAIService
from app.services.push_notification_service import PushNotificationService
from app.utils.helpers import serialize_mongo_document, serialize_mongo_documents, utc_now


class SmartFlowService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.ai_service = MabdelAIService()

    async def get_home_dashboard(self, user: dict) -> dict:
        user_id = str(user["_id"])
        latest_messages = await self.db.messages.find({"user_id": user_id}).sort("timestamp", -1).limit(3).to_list(length=3)
        upcoming_events = await self.db.calendar_events.find(
            {"user_id": user_id, "starts_at": {"$gte": utc_now()}}
        ).sort("starts_at", 1).limit(3).to_list(length=3)
        integrations = await self.db.social_integrations.find({"user_id": user_id, "status": "connected"}).to_list(length=20)
        contacts = await self.db.contacts.find({"user_id": user_id}).sort("updated_at", -1).limit(5).to_list(length=5)
        doc_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        ]
        doc_counts = await self.db.documents.aggregate(doc_pipeline).to_list(length=10)
        call_logs = await self.db.call_logs.find({"user_id": user_id}).sort("timestamp", -1).limit(5).to_list(length=5)
        unread_notifications = await self.db.notifications.count_documents({"user_id": user_id, "read": False})
        unread_messages = await self.db.messages.aggregate(
            [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": None, "total": {"$sum": "$unread_count"}}},
            ]
        ).to_list(length=1)

        total_calls = await self.db.call_logs.count_documents({"user_id": user_id})
        total_minutes_saved = sum(max(1, int(item.get("duration", 0) / 60)) for item in call_logs if item.get("ai_ready"))

        return {
            "greeting_name": user.get("full_name", "User").split(" ")[0],
            "language_preference": user.get("language_preference", "EN"),
            "inbox": {
                "unread_count": unread_messages[0]["total"] if unread_messages else 0,
                "latest_messages": self._to_public_many(latest_messages),
            },
            "contacts": {
                "count": await self.db.contacts.count_documents({"user_id": user_id}),
                "items": self._to_public_many(contacts),
            },
            "calendar": {
                "upcoming_count": await self.db.calendar_events.count_documents(
                    {"user_id": user_id, "starts_at": {"$gte": utc_now()}}
                ),
                "items": self._to_public_many(upcoming_events),
            },
            "integrations": {
                "connected_count": len(integrations),
                "items": [{"platform": item["platform"], "status": item["status"]} for item in integrations],
            },
            "documents": {
                "counts_by_type": {item["_id"]: item["count"] for item in doc_counts},
            },
            "ai_call_analytics": {
                "total_calls": total_calls,
                "minutes_saved": total_minutes_saved,
                "latest_calls": self._to_public_many(call_logs),
            },
            "notifications": {
                "unread_count": unread_notifications,
            },
        }

    async def list_contacts(self, user_id: str, page: int, page_size: int, search: str | None) -> dict:
        filters = {"user_id": user_id}
        if search:
            filters["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}},
                {"identities.handle": {"$regex": search, "$options": "i"}},
            ]
        return await self._paginate(self.db.contacts, filters, page, page_size, "updated_at")

    async def create_contact(self, user_id: str, payload: dict) -> dict:
        now = utc_now()
        document = {
            "user_id": user_id,
            "name": payload["name"].strip(),
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "avatar_url": payload.get("avatar_url"),
            "identities": payload.get("identities", []),
            "presence": "offline",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.contacts.insert_one(document)
        document["_id"] = result.inserted_id
        return self._to_public(document)

    async def update_contact(self, user_id: str, contact_id: str, updates: dict) -> dict:
        contact = await self._get_owned_document(self.db.contacts, user_id, contact_id, "CONTACT_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.contacts.find_one_and_update(
            {"_id": contact["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_public(updated)

    async def delete_contact(self, user_id: str, contact_id: str) -> None:
        contact = await self._get_owned_document(self.db.contacts, user_id, contact_id, "CONTACT_NOT_FOUND")
        await self.db.contacts.delete_one({"_id": contact["_id"]})

    async def create_conversation(self, user_id: str, payload: dict) -> dict:
        now = utc_now()
        member_ids = list(dict.fromkeys([user_id, *payload.get("member_ids", [])]))
        document = {
            "user_id": user_id,
            "title": payload.get("title"),
            "contact_id": payload.get("contact_id"),
            "type": payload.get("type", "direct"),
            "platform": payload.get("platform", "whatsapp"),
            "member_ids": member_ids,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.conversations.insert_one(document)
        document["_id"] = result.inserted_id
        return await self._serialize_conversation(document)

    async def get_conversation(self, user_id: str, conversation_id: str) -> dict:
        conversation = await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        return await self._serialize_conversation(conversation)

    async def list_conversations(
        self,
        user_id: str,
        page: int,
        page_size: int,
        search: str | None,
        platform: str | None,
        archived: bool | None,
        unread_only: bool = False,
        type_filter: str | None = None,
    ) -> dict:
        filters: dict = {"user_id": user_id}
        if platform:
            filters["platform"] = platform
        if archived is not None:
            filters["archived"] = archived
        if type_filter:
            filters["type"] = type_filter
        conversations = await self.db.conversations.find(filters).sort("updated_at", -1).to_list(length=500)
        items = [await self._serialize_conversation(item) for item in conversations]
        if unread_only:
            items = [item for item in items if item.get("unread_count", 0) > 0]
        if search:
            needle = search.strip().lower()
            items = [item for item in items if self._conversation_matches_search(item, needle)]
        total = len(items)
        slice_start = (page - 1) * page_size
        summary = self._conversation_list_summary(items)
        return {
            "items": items[slice_start : slice_start + page_size],
            "summary": summary,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": ceil(total / page_size) if page_size else 1,
            },
        }

    async def archive_conversation(self, user_id: str, conversation_id: str, archived: bool) -> dict:
        conversation = await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        updated = await self.db.conversations.find_one_and_update(
            {"_id": conversation["_id"]},
            {"$set": {"archived": archived, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        return await self._serialize_conversation(updated)

    async def mark_conversation_read(self, user_id: str, conversation_id: str) -> dict:
        conversation = await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        now = utc_now()
        await self.db.messages.update_many(
            {"user_id": user_id, "conversation_id": conversation_id, "unread_count": {"$gt": 0}},
            {"$set": {"status": "read", "unread_count": 0, "read_at": now, "delivered_at": now}},
        )
        refreshed = await self.db.conversations.find_one({"_id": conversation["_id"]})
        serialized = await self._serialize_conversation(refreshed)
        await conversation_realtime_hub.publish(conversation_id, "conversation.read", {"unread_count": 0, "read_at": now})
        await self._publish_inbox_update(user_id, conversation_id)
        return serialized

    async def list_messages(
        self,
        user_id: str,
        conversation_id: str,
        page: int,
        page_size: int,
        search: str | None,
        platform: str | None,
    ) -> dict:
        await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        filters: dict = {"user_id": user_id, "conversation_id": conversation_id}
        if search:
            filters["content"] = {"$regex": search, "$options": "i"}
        if platform:
            filters["platform"] = platform
        page_result = await self._paginate(self.db.messages, filters, page, page_size, "timestamp")
        page_result["items"] = [await self._serialize_message(item) for item in page_result["items"]]
        return page_result

    async def create_message(self, user_id: str, payload: dict) -> dict:
        conversation = await self._get_owned_document(
            self.db.conversations, user_id, payload["conversation_id"], "CONVERSATION_NOT_FOUND"
        )
        await self._validate_message_links(user_id, payload)
        now = utc_now()
        unread_count = 1 if payload["direction"] == "inbound" else 0
        document = {
            "user_id": user_id,
            "conversation_id": payload["conversation_id"],
            "contact_id": payload.get("contact_id"),
            "platform": payload["platform"],
            "direction": payload["direction"],
            "content": payload["content"].strip(),
            "media_url": payload.get("media_url"),
            "status": "sent",
            "timestamp": now,
            "delivered_at": now if payload["direction"] == "inbound" else None,
            "unread_count": unread_count,
            "is_archived": False,
            "read_at": None,
            "reply_to_message_id": payload.get("reply_to_message_id"),
            "forward_from_message_id": payload.get("forward_from_message_id"),
        }
        result = await self.db.messages.insert_one(document)
        document["_id"] = result.inserted_id
        await self.db.conversations.update_one(
            {"_id": conversation["_id"]},
            {"$set": {"updated_at": now}},
        )
        serialized = await self._serialize_message(document)
        await conversation_realtime_hub.publish(payload["conversation_id"], "message.created", serialized)
        await self._publish_inbox_update(user_id, payload["conversation_id"])
        return serialized

    async def update_message(self, user_id: str, message_id: str, updates: dict) -> dict:
        message = await self._get_owned_document(self.db.messages, user_id, message_id, "MESSAGE_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        status_value = clean_updates.get("status")
        if status_value == "delivered" and not message.get("delivered_at"):
            clean_updates["delivered_at"] = utc_now()
        if clean_updates.get("status") == "read":
            if not message.get("delivered_at"):
                clean_updates["delivered_at"] = utc_now()
            clean_updates["read_at"] = utc_now()
            clean_updates["unread_count"] = 0
        updated = await self.db.messages.find_one_and_update(
            {"_id": message["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        serialized = await self._serialize_message(updated)
        await conversation_realtime_hub.publish(updated["conversation_id"], "message.updated", serialized)
        await self._publish_inbox_update(user_id, updated["conversation_id"])
        return serialized

    async def reply_to_message(self, user_id: str, message_id: str, payload: dict) -> dict:
        source_message = await self._get_owned_document(self.db.messages, user_id, message_id, "MESSAGE_NOT_FOUND")
        return await self.create_message(
            user_id,
            {
                "conversation_id": source_message["conversation_id"],
                "contact_id": payload.get("contact_id") or source_message.get("contact_id"),
                "platform": payload["platform"],
                "direction": "outbound",
                "content": payload["content"],
                "media_url": payload.get("media_url"),
                "reply_to_message_id": message_id,
                "forward_from_message_id": None,
            },
        )

    async def forward_message(self, user_id: str, message_id: str, payload: dict) -> dict:
        source_message = await self._get_owned_document(self.db.messages, user_id, message_id, "MESSAGE_NOT_FOUND")
        return await self.create_message(
            user_id,
            {
                "conversation_id": payload["conversation_id"],
                "contact_id": payload.get("contact_id"),
                "platform": payload["platform"],
                "direction": "outbound",
                "content": (payload.get("content") or source_message.get("content") or "").strip(),
                "media_url": payload.get("media_url") if "media_url" in payload else source_message.get("media_url"),
                "reply_to_message_id": None,
                "forward_from_message_id": message_id,
            },
        )

    async def get_unread_message_summary(self, user_id: str, platform: str | None) -> dict:
        filters = {"user_id": user_id}
        if platform:
            filters["platform"] = platform
        pipeline = [
            {"$match": filters},
            {"$group": {"_id": "$platform", "unread": {"$sum": "$unread_count"}}},
        ]
        grouped = await self.db.messages.aggregate(pipeline).to_list(length=20)
        return {
            "total_unread": sum(item["unread"] for item in grouped),
            "by_platform": {item["_id"]: item["unread"] for item in grouped},
        }

    async def get_typing_state(self, user_id: str, conversation_id: str) -> dict:
        await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        typing_doc = await self.db.typing_states.find_one({"user_id": user_id, "conversation_id": conversation_id})
        if not typing_doc:
            return {
                "conversation_id": conversation_id,
                "is_typing": False,
                "actor_name": None,
                "actor_type": "ai",
                "preview_text": None,
                "state_label": None,
                "updated_at": None,
                "expires_at": None,
            }

        safe = self._to_public(typing_doc)
        expires_at = safe.get("expires_at")
        is_active = bool(safe.get("is_typing")) and self._is_future_timestamp(expires_at)
        return {
            "conversation_id": conversation_id,
            "is_typing": is_active,
            "actor_name": safe.get("actor_name"),
            "actor_type": safe.get("actor_type", "ai"),
            "preview_text": safe.get("preview_text"),
            "state_label": safe.get("state_label"),
            "updated_at": safe.get("updated_at"),
            "expires_at": safe.get("expires_at"),
        }

    async def set_typing_state(self, user_id: str, conversation_id: str, payload: dict) -> dict:
        await self._get_owned_document(self.db.conversations, user_id, conversation_id, "CONVERSATION_NOT_FOUND")
        now = utc_now()
        is_typing = bool(payload.get("is_typing", True))
        expires_at = now + timedelta(seconds=20) if is_typing else now
        updated = await self.db.typing_states.find_one_and_update(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "$set": {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "is_typing": is_typing,
                    "actor_name": payload.get("actor_name"),
                    "actor_type": payload.get("actor_type", "ai"),
                    "preview_text": payload.get("preview_text"),
                    "state_label": payload.get("state_label"),
                    "updated_at": now,
                    "expires_at": expires_at,
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        response = {
            "conversation_id": conversation_id,
            "is_typing": is_typing,
            "actor_name": updated.get("actor_name"),
            "actor_type": updated.get("actor_type", "ai"),
            "preview_text": updated.get("preview_text"),
            "state_label": updated.get("state_label"),
            "updated_at": updated.get("updated_at"),
            "expires_at": updated.get("expires_at"),
        }
        await conversation_realtime_hub.publish(conversation_id, "typing.updated", response)
        return response

    async def ensure_ai_conversation(self, user_id: str) -> dict:
        conversation = await self.db.conversations.find_one({"user_id": user_id, "type": "ai"})
        if conversation:
            return conversation
        now = utc_now()
        doc = {
            "user_id": user_id,
            "title": "Mabdel AI",
            "contact_id": None,
            "type": "ai",
            "platform": "ai",
            "member_ids": [user_id],
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.conversations.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def chat_with_ai(
        self,
        user_id: str,
        content: str,
        response_mode: str = "text",
        voice_id: str | None = None,
    ) -> dict:
        conversation = await self.ensure_ai_conversation(user_id)
        history = await self.db.messages.find({"user_id": user_id, "conversation_id": str(conversation["_id"])}).sort(
            "timestamp", 1
        ).limit(20).to_list(length=20)
        user_message = await self.create_message(
            user_id,
            {
                "conversation_id": str(conversation["_id"]),
                "platform": "ai",
                "direction": "inbound",
                "content": content,
                "contact_id": None,
                "media_url": None,
                "reply_to_message_id": None,
                "forward_from_message_id": None,
            },
        )
        ai_result = self.ai_service.generate_response(content, history)
        ai_message = await self.create_message(
            user_id,
            {
                "conversation_id": str(conversation["_id"]),
                "platform": "ai",
                "direction": "outbound",
                "content": ai_result["content"],
                "contact_id": None,
                "media_url": None,
                "reply_to_message_id": user_message["id"],
                "forward_from_message_id": None,
            },
        )
        ai_message = await self.update_message(user_id, ai_message["id"], {"status": "read"})
        history_item = await self.log_ai_command(
            user_id=user_id,
            command_text=content,
            command_type=ai_result["command_type"],
            status="completed",
            is_replayable=True,
        )
        audio = None
        if response_mode in {"audio", "both"}:
            audio = self.ai_service.synthesize_speech(ai_message["content"], voice_id=voice_id)
        return {
            "conversation_id": str(conversation["_id"]),
            "state": ai_result["state"],
            "user_message": user_message,
            "ai_message": {**ai_message, "command_history_id": history_item["id"]},
            "audio": audio,
        }

    async def log_ai_command(
        self,
        user_id: str,
        command_text: str,
        command_type: str,
        status: str,
        is_replayable: bool,
        *,
        related_resource: dict | None = None,
        preview_payload: dict | None = None,
        timestamp: datetime | None = None,
    ) -> dict:
        document = {
            "user_id": user_id,
            "command_text": command_text,
            "command_type": command_type,
            "status": status,
            "timestamp": timestamp or utc_now(),
            "is_replayable": is_replayable,
            "related_resource": related_resource,
            "preview_payload": preview_payload,
        }
        result = await self.db.ai_command_history.insert_one(document)
        document["_id"] = result.inserted_id
        return self._serialize_history_item(document)

    async def list_ai_history(
        self,
        user_id: str,
        page: int,
        page_size: int,
        search: str | None,
        command_type: str | None,
        *,
        status_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        replayable_only: bool = False,
        group_by: str | None = None,
    ) -> dict:
        filters = {"user_id": user_id}
        if search:
            filters["command_text"] = {"$regex": search, "$options": "i"}
        if command_type:
            filters["command_type"] = command_type
        if status_filter:
            filters["status"] = status_filter
        if replayable_only:
            filters["is_replayable"] = True
        if date_from or date_to:
            timestamp_filter = filters.get("timestamp", {})
            if date_from:
                timestamp_filter["$gte"] = self._parse_date_boundary(date_from, end_of_day=False)
            if date_to:
                timestamp_filter["$lte"] = self._parse_date_boundary(date_to, end_of_day=True)
            filters["timestamp"] = timestamp_filter
        page_result = await self._paginate(self.db.ai_command_history, filters, page, page_size, "timestamp")
        items = [self._serialize_history_item(item) for item in page_result["items"]]
        page_result["items"] = items
        if group_by == "day":
            page_result["groups"] = self._group_history_items_by_day(items)
        return page_result

    async def replay_ai_command(self, user_id: str, history_id: str) -> dict:
        history = await self._get_owned_document(self.db.ai_command_history, user_id, history_id, "AI_COMMAND_NOT_FOUND")
        if not history.get("is_replayable", True):
            raise AppException(status_code=400, code="COMMAND_NOT_REPLAYABLE", message="This command cannot be replayed.")
        linked = await self._replay_linked_resource(user_id, history)
        if linked is not None:
            return {
                **linked,
                "history_item": self._serialize_history_item(history),
                "replayed_action_status": "linked",
            }
        replay_result = await self.chat_with_ai(user_id, history["command_text"])
        return {
            **replay_result,
            "history_item": self._serialize_history_item(history),
            "result_type": "ai_chat",
            "replayed_action_status": "completed",
        }

    async def process_voice_command(
        self,
        user_id: str,
        transcript: str | None,
        audio_url: str | None,
        audio_base64: str | None = None,
        audio_mime_type: str = "audio/wav",
        audio_filename: str = "voice.wav",
        response_mode: str = "both",
        voice_id: str | None = None,
    ) -> dict:
        transcription = self.ai_service.transcribe_voice(
            transcript=transcript,
            audio_url=audio_url,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            audio_filename=audio_filename,
        )
        ai_result = await self.chat_with_ai(
            user_id,
            transcription["transcript"],
            response_mode=response_mode,
            voice_id=voice_id,
        )
        history = await self.log_ai_command(
            user_id=user_id,
            command_text=transcription["transcript"],
            command_type="voice",
            status="completed",
            is_replayable=True,
        )
        return {
            "state": transcription["state"],
            "transcript": transcription["transcript"],
            "ai_response": ai_result["ai_message"]["content"],
            "history_id": history["id"],
            "audio": ai_result.get("audio"),
        }

    async def list_ai_voices(self) -> list[dict]:
        return self.ai_service.list_voice_presets()

    async def validate_bulk_recipients(self, user_id: str, payload: dict) -> dict:
        resolution = await self._resolve_bulk_recipients(user_id, payload)
        return {
            "channel": payload.get("channel", "email"),
            "valid_count": len(resolution["recipients"]),
            "invalid_count": len(resolution["invalid_entries"]),
            "duplicate_count": len(resolution["duplicate_entries"]),
            "recipients": resolution["recipients"],
            "invalid_entries": resolution["invalid_entries"],
            "duplicate_entries": resolution["duplicate_entries"],
            "unavailable_contact_ids": resolution["unavailable_contact_ids"],
            "unavailable_group_ids": resolution["unavailable_group_ids"],
        }

    async def list_bulk_messages(
        self,
        user_id: str,
        page: int,
        page_size: int,
        search: str | None,
        status_filter: str | None,
        channel: str | None,
    ) -> dict:
        filters: dict = {"user_id": user_id}
        if search:
            filters["$or"] = [
                {"content": {"$regex": search, "$options": "i"}},
                {"subject": {"$regex": search, "$options": "i"}},
            ]
        if status_filter:
            filters["status"] = status_filter
        if channel:
            filters["channel"] = channel
        page_result = await self._paginate(self.db.bulk_messages, filters, page, page_size, "updated_at")
        page_result["items"] = [self._serialize_bulk_message(item) for item in page_result["items"]]
        return page_result

    async def get_bulk_message(self, user_id: str, bulk_message_id: str) -> dict:
        document = await self._get_owned_document(self.db.bulk_messages, user_id, bulk_message_id, "BULK_MESSAGE_NOT_FOUND")
        return self._serialize_bulk_message(document)

    async def create_bulk_message(self, user_id: str, payload: dict) -> dict:
        resolution = await self._resolve_bulk_recipients(user_id, payload)
        self._validate_bulk_message_payload(payload, resolution)
        now = utc_now()
        scheduled_at = payload.get("scheduled_at")
        status = "draft"
        if scheduled_at:
            status = "scheduled"
        elif payload.get("send_now", True):
            status = "processing"

        document = {
            "user_id": user_id,
            "channel": payload["channel"],
            "status": status,
            "subject": payload.get("subject"),
            "content": payload["content"].strip(),
            "attachments": payload.get("attachments", []),
            "recipient_emails": [email.strip().lower() for email in payload.get("recipient_emails", []) if email.strip()],
            "contact_ids": payload.get("contact_ids", []),
            "group_ids": payload.get("group_ids", []),
            "recipients": resolution["recipients"],
            "deliveries": [],
            "scheduled_at": scheduled_at,
            "timezone": payload.get("timezone", "UTC"),
            "ai_transcript": payload.get("ai_transcript"),
            "character_count": len(payload["content"]),
            "segment_count": self._bulk_segment_count(payload["channel"], payload["content"]),
            "sent_count": 0,
            "failed_count": 0,
            "created_at": now,
            "updated_at": now,
            "sent_at": None,
        }
        result = await self.db.bulk_messages.insert_one(document)
        document["_id"] = result.inserted_id

        if status == "processing":
            document = await self._dispatch_bulk_message(document)
        elif status == "scheduled":
            await self.log_ai_command(
                user_id=user_id,
                command_text=f"Schedule bulk {payload['channel']} to {len(document['recipients'])} recipients",
                command_type="bulk_message",
                status="scheduled",
                is_replayable=True,
                related_resource={"type": "bulk_message", "id": str(document["_id"]), "status": "scheduled"},
                preview_payload={"channel": payload["channel"], "recipient_count": len(document["recipients"])},
            )
            await self.create_notification(
                user_id=user_id,
                notification_type="message",
                title="Bulk message scheduled",
                body=f"{len(document['recipients'])} recipients scheduled for delivery.",
            )
        else:
            await self.log_ai_command(
                user_id=user_id,
                command_text=f"Save draft bulk {payload['channel']}",
                command_type="bulk_message",
                status="archived",
                is_replayable=True,
                related_resource={"type": "bulk_message", "id": str(document["_id"]), "status": "draft"},
                preview_payload={"channel": payload["channel"], "recipient_count": len(document["recipients"])},
            )
        return self._serialize_bulk_message(document)

    async def update_bulk_message(self, user_id: str, bulk_message_id: str, updates: dict) -> dict:
        document = await self._get_owned_document(self.db.bulk_messages, user_id, bulk_message_id, "BULK_MESSAGE_NOT_FOUND")
        if document.get("status") not in {"draft", "scheduled"}:
            raise AppException(status_code=409, code="BULK_MESSAGE_LOCKED", message="Only draft or scheduled bulk messages can be updated.")

        clean_updates = {key: value for key, value in updates.items() if value is not None}
        merged = {**document, **clean_updates}
        resolution = await self._resolve_bulk_recipients(user_id, merged)
        self._validate_bulk_message_payload(merged, resolution)

        clean_updates["recipients"] = resolution["recipients"]
        clean_updates["character_count"] = len(merged["content"])
        clean_updates["segment_count"] = self._bulk_segment_count(merged["channel"], merged["content"])
        clean_updates["updated_at"] = utc_now()
        clean_updates["recipient_emails"] = [
            email.strip().lower()
            for email in merged.get("recipient_emails", [])
            if isinstance(email, str) and email.strip()
        ]
        if clean_updates.get("scheduled_at"):
            clean_updates["status"] = "scheduled"
        elif clean_updates.get("send_now") is False:
            clean_updates["status"] = "draft"

        updated = await self.db.bulk_messages.find_one_and_update(
            {"_id": document["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        await self.log_ai_command(
            user_id=user_id,
            command_text=f"Update bulk {updated['channel']} message",
            command_type="bulk_message",
            status="completed",
            is_replayable=True,
            related_resource={"type": "bulk_message", "id": str(updated["_id"]), "status": updated["status"]},
            preview_payload={"recipient_count": len(updated.get("recipients", []))},
        )
        return self._serialize_bulk_message(updated)

    async def send_bulk_message(self, user_id: str, bulk_message_id: str) -> dict:
        document = await self._get_owned_document(self.db.bulk_messages, user_id, bulk_message_id, "BULK_MESSAGE_NOT_FOUND")
        if document.get("status") == "cancelled":
            raise AppException(status_code=409, code="BULK_MESSAGE_CANCELLED", message="Cancelled bulk messages cannot be sent.")
        if document.get("status") in {"sent", "partial_failed", "failed"}:
            return self._serialize_bulk_message(document)
        updated = await self.db.bulk_messages.find_one_and_update(
            {"_id": document["_id"]},
            {"$set": {"status": "processing", "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        dispatched = await self._dispatch_bulk_message(updated)
        return self._serialize_bulk_message(dispatched)

    async def cancel_bulk_message(self, user_id: str, bulk_message_id: str) -> dict:
        document = await self._get_owned_document(self.db.bulk_messages, user_id, bulk_message_id, "BULK_MESSAGE_NOT_FOUND")
        if document.get("status") not in {"draft", "scheduled"}:
            raise AppException(status_code=409, code="BULK_MESSAGE_CANNOT_CANCEL", message="Only draft or scheduled bulk messages can be cancelled.")
        updated = await self.db.bulk_messages.find_one_and_update(
            {"_id": document["_id"]},
            {"$set": {"status": "cancelled", "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        await self.log_ai_command(
            user_id=user_id,
            command_text=f"Cancel bulk {updated['channel']} message",
            command_type="bulk_message",
            status="archived",
            is_replayable=True,
            related_resource={"type": "bulk_message", "id": str(updated["_id"]), "status": "cancelled"},
        )
        return self._serialize_bulk_message(updated)

    async def list_calendar_events(
        self,
        user_id: str,
        page: int,
        page_size: int,
        search: str | None,
        upcoming_only: bool,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        contact_id: str | None = None,
    ) -> dict:
        filters: dict = {"user_id": user_id}
        if search:
            filters["title"] = {"$regex": search, "$options": "i"}
        if upcoming_only:
            filters["starts_at"] = {"$gte": utc_now()}
        if date_from or date_to:
            starts_at_filter = filters.get("starts_at", {})
            if not isinstance(starts_at_filter, dict):
                starts_at_filter = {}
            if date_from:
                starts_at_filter["$gte"] = self._parse_date_boundary(date_from, end_of_day=False)
            if date_to:
                starts_at_filter["$lte"] = self._parse_date_boundary(date_to, end_of_day=True)
            filters["starts_at"] = starts_at_filter
        if contact_id:
            filters["contact_ids"] = contact_id
        page_result = await self._paginate(self.db.calendar_events, filters, page, page_size, "starts_at", ascending=True)
        page_result["items"] = [await self._serialize_calendar_event(item) for item in page_result["items"]]
        return page_result

    async def get_calendar_event(self, user_id: str, event_id: str) -> dict:
        event = await self._get_owned_document(self.db.calendar_events, user_id, event_id, "EVENT_NOT_FOUND")
        return await self._serialize_calendar_event(event)

    async def create_calendar_event(self, user_id: str, payload: dict) -> dict:
        self._validate_calendar_event_payload(payload)
        await self._assert_calendar_slot_available(user_id, payload["starts_at"], payload["ends_at"])
        if payload.get("meeting_mode") == "online" and not payload.get("meeting_link"):
            payload["meeting_link"] = self._generate_meeting_link()
        document = {
            "user_id": user_id,
            **payload,
            "sync_status": "synced" if payload.get("google_event_id") else "local",
            "share_token": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        result = await self.db.calendar_events.insert_one(document)
        document["_id"] = result.inserted_id
        await self._create_calendar_event_notifications(user_id, document, action="created")
        return await self._serialize_calendar_event(document)

    async def update_calendar_event(self, user_id: str, event_id: str, updates: dict) -> dict:
        event = await self._get_owned_document(self.db.calendar_events, user_id, event_id, "EVENT_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        merged = {**event, **clean_updates}
        self._validate_calendar_event_payload(merged)
        await self._assert_calendar_slot_available(
            user_id,
            merged["starts_at"],
            merged["ends_at"],
            exclude_event_id=str(event["_id"]),
        )
        if merged.get("meeting_mode") == "online" and not merged.get("meeting_link"):
            clean_updates["meeting_link"] = self._generate_meeting_link()
        if "google_event_id" in clean_updates:
            clean_updates["sync_status"] = "synced" if clean_updates["google_event_id"] else "local"
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.calendar_events.find_one_and_update(
            {"_id": event["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            await self._create_calendar_event_notifications(user_id, updated, action="updated")
        return await self._serialize_calendar_event(updated)

    async def share_calendar_event(self, user_id: str, event_id: str, payload: dict) -> dict:
        event = await self._get_owned_document(self.db.calendar_events, user_id, event_id, "EVENT_NOT_FOUND")
        if not event.get("share_token"):
            event["share_token"] = secrets.token_urlsafe(18)
            await self.db.calendar_events.update_one(
                {"_id": event["_id"]},
                {"$set": {"share_token": event["share_token"], "updated_at": utc_now()}},
            )
        share_url = self._calendar_share_url(event["share_token"])
        recipient_email = payload.get("recipient_email")
        if payload.get("channel") == "email":
            if not recipient_email:
                raise AppException(status_code=400, code="RECIPIENT_EMAIL_REQUIRED", message="Recipient email is required for email sharing.")
            subject = f"Meeting invite: {event['title']}"
            text = self._calendar_share_text(event, payload.get("message"), share_url)
            html = self._calendar_share_html(event, payload.get("message"), share_url)
            await EmailService().send_invoice_email(email=recipient_email, subject=subject, text=text, html=html)
        await self._create_calendar_event_notifications(user_id, event, action="shared")
        return {
            "event_id": str(event["_id"]),
            "channel": payload.get("channel", "link"),
            "recipient_email": recipient_email,
            "share_url": share_url,
        }

    async def delete_calendar_event(self, user_id: str, event_id: str) -> None:
        event = await self._get_owned_document(self.db.calendar_events, user_id, event_id, "EVENT_NOT_FOUND")
        await self.db.calendar_events.delete_one({"_id": event["_id"]})

    async def list_documents(self, user_id: str, page: int, page_size: int, search: str | None, doc_type: str | None) -> dict:
        filters = {"user_id": user_id}
        if search:
            filters["name"] = {"$regex": search, "$options": "i"}
        if doc_type:
            filters["type"] = doc_type
        page_result = await self._paginate(self.db.documents, filters, page, page_size, "created_at")
        page_result["items"] = [self._with_preview_url(item) for item in page_result["items"]]
        return page_result

    async def create_document(self, user_id: str, payload: dict) -> dict:
        document = {
            "user_id": user_id,
            **payload,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        result = await self.db.documents.insert_one(document)
        document["_id"] = result.inserted_id
        await self.log_ai_command(
            user_id=user_id,
            command_text=f"Create {payload['type']} document {payload['name']}",
            command_type=self._document_command_type(payload["type"]),
            status="completed",
            is_replayable=True,
            related_resource={"type": "document", "id": str(document["_id"]), "document_type": payload["type"]},
            preview_payload={"name": payload["name"], "file_url": payload["file_url"]},
        )
        return self._with_preview_url(self._to_public(document))

    async def update_document(self, user_id: str, document_id: str, updates: dict) -> dict:
        document = await self._get_owned_document(self.db.documents, user_id, document_id, "DOCUMENT_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.documents.find_one_and_update(
            {"_id": document["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        await self.log_ai_command(
            user_id=user_id,
            command_text=f"Update {updated['type']} document {updated['name']}",
            command_type=self._document_command_type(updated["type"]),
            status="completed",
            is_replayable=True,
            related_resource={"type": "document", "id": str(updated["_id"]), "document_type": updated["type"]},
            preview_payload={"name": updated["name"], "file_url": updated["file_url"]},
        )
        return self._with_preview_url(self._to_public(updated))

    async def delete_document(self, user_id: str, document_id: str) -> None:
        document = await self._get_owned_document(self.db.documents, user_id, document_id, "DOCUMENT_NOT_FOUND")
        await self.db.documents.delete_one({"_id": document["_id"]})
        await self.log_ai_command(
            user_id=user_id,
            command_text=f"Delete {document['type']} document {document['name']}",
            command_type=self._document_command_type(document["type"]),
            status="archived",
            is_replayable=True,
            related_resource={"type": "document", "id": str(document["_id"]), "document_type": document["type"]},
            preview_payload={"name": document["name"]},
        )

    async def list_call_logs(self, user_id: str, page: int, page_size: int, status: str | None) -> dict:
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status
        return await self._paginate(self.db.call_logs, filters, page, page_size, "timestamp")

    async def create_call_log(self, user_id: str, payload: dict) -> dict:
        status = self._derive_call_status(payload)
        document = {
            "user_id": user_id,
            **payload,
            "status": status,
            "timestamp": utc_now(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        result = await self.db.call_logs.insert_one(document)
        document["_id"] = result.inserted_id
        return self._to_public(document)

    async def update_call_log(self, user_id: str, call_id: str, updates: dict) -> dict:
        call = await self._get_owned_document(self.db.call_logs, user_id, call_id, "CALL_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        if "status" not in clean_updates:
            clean_updates["status"] = self._derive_call_status({**call, **clean_updates})
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.call_logs.find_one_and_update(
            {"_id": call["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_public(updated)

    async def get_call_summary(self, user_id: str) -> dict:
        calls = await self.db.call_logs.find({"user_id": user_id}).to_list(length=500)
        return {
            "total_calls": len(calls),
            "total_minutes_saved": sum(max(1, int(call.get("duration", 0) / 60)) for call in calls if call.get("ai_ready")),
            "callback_queue": [self._to_public(call) for call in calls if call.get("callback_requested")],
        }

    async def list_integrations(self, user_id: str) -> list[dict]:
        docs = await self.db.social_integrations.find({"user_id": user_id}).sort("platform", 1).to_list(length=20)
        return [self._serialize_integration(doc) for doc in docs]

    async def get_integration_catalog(self, user_id: str) -> list[dict]:
        docs = await self.db.social_integrations.find({"user_id": user_id}).to_list(length=50)
        existing = {doc["platform"]: doc for doc in docs}
        items: list[dict] = []
        for metadata in self._integration_catalog_metadata():
            platform = metadata["platform"]
            doc = existing.get(platform)
            if doc:
                items.append(self._serialize_integration(doc, metadata))
            else:
                items.append(
                    {
                        "platform": platform,
                        "platform_label": metadata["platform_label"],
                        "description": metadata["description"],
                        "icon_key": metadata["icon_key"],
                        "brand_color": metadata["brand_color"],
                        "status": "disconnected" if metadata["is_configured"] else "misconfigured",
                        "connected": False,
                        "cta_label": "Connect" if metadata["is_configured"] else "Unavailable",
                        "is_available": metadata["is_available"],
                        "is_configured": metadata["is_configured"],
                        "auth_mode": metadata["auth_mode"],
                        "external_account_id": None,
                        "connected_at": None,
                        "last_webhook_at": None,
                    }
                )
        return items

    async def upsert_integration(self, user_id: str, payload: dict) -> dict:
        now = utc_now()
        update = {
            "user_id": user_id,
            "platform": payload["platform"],
            "status": "connected",
            "external_account_id": payload.get("external_account_id"),
            "access_token_encrypted": encrypt_value(payload["access_token"]),
            "refresh_token_encrypted": encrypt_value(payload["refresh_token"]) if payload.get("refresh_token") else None,
            "connected_at": now,
            "updated_at": now,
        }
        result = await self.db.social_integrations.find_one_and_update(
            {"user_id": user_id, "platform": payload["platform"]},
            {"$set": update, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return self._sanitize_integration(result)

    async def connect_telegram_manual(self, user_id: str, payload: dict) -> dict:
        bot_token = payload["bot_token"].strip()
        secret_token = (payload.get("secret_token") or secrets.token_urlsafe(18)).strip()
        webhook_url = f"{settings.PUBLIC_BACKEND_URL.rstrip('/')}/api/v1/smartflow/integrations/telegram/webhook?user_id={user_id}"

        telegram_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                telegram_url,
                data={"url": webhook_url, "secret_token": secret_token},
                headers={"Accept": "application/json"},
            )

        if response.status_code >= 400:
            raise AppException(
                status_code=502,
                code="TELEGRAM_WEBHOOK_SETUP_FAILED",
                message="Telegram webhook setup failed.",
                details={"status_code": response.status_code, "response": response.text[:500]},
            )

        payload_data = response.json()
        if not payload_data.get("ok"):
            raise AppException(
                status_code=502,
                code="TELEGRAM_WEBHOOK_SETUP_FAILED",
                message="Telegram webhook setup failed.",
                details={"response": payload_data},
            )

        await self.upsert_integration(
            user_id,
            {
                "platform": "telegram",
                "access_token": bot_token,
                "refresh_token": None,
                "external_account_id": payload.get("bot_username"),
            },
        )
        now = utc_now()
        stored = await self.db.social_integrations.find_one_and_update(
            {"user_id": user_id, "platform": "telegram"},
            {
                "$set": {
                    "telegram_secret_token": secret_token,
                    "telegram_webhook_url": webhook_url,
                    "telegram_webhook_registered_at": now,
                    "telegram_last_setup_ok": True,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not stored:
            raise AppException(status_code=500, code="INTEGRATION_PERSISTENCE_FAILED", message="Telegram integration could not be stored.")

        return {
            "connected": True,
            "platform": "telegram",
            "webhook_url": webhook_url,
            "secret_token": secret_token,
            "integration": self._serialize_integration(stored),
        }

    async def disconnect_integration(self, user_id: str, platform: str) -> dict:
        updated = await self.db.social_integrations.find_one_and_update(
            {"user_id": user_id, "platform": platform},
            {
                "$set": {
                    "status": "disconnected",
                    "updated_at": utc_now(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise AppException(status_code=404, code="INTEGRATION_NOT_FOUND", message="Integration not found.")
        return self._sanitize_integration(updated)

    async def start_integration_oauth(self, user_id: str, platform: str) -> dict:
        provider = self._oauth_provider(platform)
        state = secrets.token_urlsafe(24)
        expires_at = utc_now() + timedelta(minutes=settings.OAUTH_STATE_EXPIRE_MINUTES)
        await self.db.oauth_states.insert_one(
            {
                "user_id": user_id,
                "platform": platform,
                "provider": provider["provider"],
                "state": state,
                "expires_at": expires_at,
                "created_at": utc_now(),
            }
        )
        params = {
            "client_id": provider["client_id"],
            "redirect_uri": provider["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(provider["scopes"]),
            "state": state,
        }
        if provider.get("extra_authorize_params"):
            params.update(provider["extra_authorize_params"])
        return {
            "platform": platform,
            "provider": provider["provider"],
            "auth_url": f'{provider["authorize_url"]}?{urlencode(params)}',
            "state": state,
            "expires_at": expires_at,
        }

    async def complete_integration_oauth(self, platform: str, code: str, state: str) -> dict:
        state_doc = await self.db.oauth_states.find_one({"platform": platform, "state": state})
        if not state_doc or state_doc.get("expires_at") < utc_now():
            raise AppException(status_code=400, code="OAUTH_STATE_INVALID", message="OAuth state is invalid or expired.")

        provider = self._oauth_provider(platform)
        token_payload = {
            "client_id": provider["client_id"],
            "client_secret": provider["client_secret"],
            "redirect_uri": provider["redirect_uri"],
            "code": code,
        }
        token_payload.update(provider["token_payload"])
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(
                provider["token_url"],
                data=token_payload,
                headers={"Accept": "application/json"},
            )
        if token_response.status_code >= 400:
            raise AppException(
                status_code=502,
                code="OAUTH_TOKEN_EXCHANGE_FAILED",
                message="OAuth token exchange failed.",
                details={"platform": platform, "provider_status": token_response.status_code, "response": token_response.text[:300]},
            )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise AppException(status_code=502, code="OAUTH_ACCESS_TOKEN_MISSING", message="Provider did not return an access token.")

        integration = await self.upsert_integration(
            state_doc["user_id"],
            {
                "platform": platform,
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "external_account_id": token_data.get("scope") or token_data.get("token_type"),
            },
        )
        await self.db.social_integrations.update_one(
            {"_id": ObjectId(integration["id"])},
            {
                "$set": {
                    "oauth_state_completed_at": utc_now(),
                    "token_expires_in": token_data.get("expires_in"),
                    "granted_scopes": token_data.get("scope"),
                }
            },
        )
        await self.db.oauth_states.delete_one({"_id": state_doc["_id"]})
        return {
            "connected": True,
            "platform": platform,
            "integration": self._sanitize_integration(await self.db.social_integrations.find_one({"_id": ObjectId(integration["id"])})),
        }

    async def handle_inbound_webhook(self, user_id: str, platform: str, payload: dict) -> dict:
        payload = self.normalize_webhook_payload(platform, payload)
        existing = await self.db.processed_webhooks.find_one(
            {
                "platform": platform,
                "event_id": payload["event_id"],
                "user_id": user_id,
            }
        )
        if existing:
            return {"status": "ignored", "reason": "duplicate_event"}
        try:
            await self.db.processed_webhooks.insert_one(
                {
                    "platform": platform,
                    "event_id": payload["event_id"],
                    "user_id": user_id,
                    "raw_payload": payload.get("raw_payload"),
                    "created_at": utc_now(),
                }
            )
        except Exception:
            return {"status": "ignored", "reason": "duplicate_event"}

        contact = await self.db.contacts.find_one(
            {
                "user_id": user_id,
                "identities": {
                    "$elemMatch": {"platform": platform, "external_id": payload["contact_external_id"]},
                },
            }
        )
        if not contact:
            contact = {
                "user_id": user_id,
                "name": f"{platform.title()} Contact",
                "email": None,
                "phone": None,
                "avatar_url": None,
                "identities": [{"platform": platform, "external_id": payload["contact_external_id"], "handle": None}],
                "presence": "offline",
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            insert = await self.db.contacts.insert_one(contact)
            contact["_id"] = insert.inserted_id

        conversation = await self.db.conversations.find_one(
            {"user_id": user_id, "contact_id": str(contact["_id"]), "platform": platform}
        )
        if not conversation:
            conversation = {
                "user_id": user_id,
                "title": contact["name"],
                "contact_id": str(contact["_id"]),
                "type": "direct",
                "platform": platform,
                "member_ids": [user_id],
                "archived": False,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            insert = await self.db.conversations.insert_one(conversation)
            conversation["_id"] = insert.inserted_id

        message = await self.create_message(
            user_id,
            {
                "conversation_id": str(conversation["_id"]),
                "contact_id": str(contact["_id"]),
                "platform": platform,
                "direction": "inbound",
                "content": payload["content"],
                "media_url": payload.get("media_url"),
                "reply_to_message_id": None,
                "forward_from_message_id": None,
            },
        )
        await self.create_notification(
            user_id=user_id,
            notification_type="message",
            title=f"New {platform} message",
            body=payload["content"],
        )
        await self.db.social_integrations.update_one(
            {"user_id": user_id, "platform": platform},
            {"$set": {"last_webhook_at": utc_now()}},
        )
        return {"status": "processed", "message": message}

    def normalize_webhook_payload(self, platform: str, payload: dict) -> dict:
        if {"event_id", "contact_external_id", "content"}.issubset(payload.keys()):
            return payload

        if platform in {"instagram", "facebook_messenger", "whatsapp"}:
            entries = payload.get("entry") or []
            first_entry = entries[0] if entries else {}
            changes = first_entry.get("changes") or []
            value = (changes[0] or {}).get("value", {}) if changes else {}
            messages = value.get("messages") or value.get("messaging") or []
            first_message = messages[0] if messages else {}
            sender = first_message.get("from") or (first_message.get("sender") or {}).get("id")
            text = (
                ((first_message.get("text") or {}).get("body"))
                or ((first_message.get("message") or {}).get("text"))
                or payload.get("content")
                or ""
            )
            event_id = first_message.get("id") or value.get("message_id") or payload.get("event_id")
            media_url = first_message.get("image", {}).get("url") if isinstance(first_message.get("image"), dict) else payload.get("media_url")
            if event_id and sender and text:
                return {
                    "event_id": str(event_id),
                    "contact_external_id": str(sender),
                    "content": str(text),
                    "media_url": media_url,
                    "timestamp": utc_now(),
                    "raw_payload": payload,
                }

        if platform == "telegram":
            message = payload.get("message", {})
            sender = (message.get("from") or {}).get("id")
            text = message.get("text")
            event_id = message.get("message_id") or payload.get("update_id")
            if event_id and sender and text:
                return {
                    "event_id": str(event_id),
                    "contact_external_id": str(sender),
                    "content": str(text),
                    "media_url": None,
                    "timestamp": utc_now(),
                    "raw_payload": payload,
                }

        raise AppException(
            status_code=400,
            code="WEBHOOK_PAYLOAD_INVALID",
            message="Webhook payload could not be normalized.",
            details={"platform": platform},
        )

    @staticmethod
    def validate_webhook_secret(secret: str | None) -> None:
        configured = settings.WEBHOOK_SHARED_SECRET
        if configured and secret != configured:
            raise AppException(status_code=401, code="WEBHOOK_UNAUTHORIZED", message="Webhook secret is invalid.")

    async def validate_platform_webhook_secret(self, user_id: str, platform: str, secret: str | None) -> None:
        if platform != "telegram":
            self.validate_webhook_secret(secret)
            return

        integration = await self.db.social_integrations.find_one({"user_id": user_id, "platform": "telegram"})
        expected = (integration or {}).get("telegram_secret_token") or settings.WEBHOOK_SHARED_SECRET
        if expected and secret != expected:
            raise AppException(status_code=401, code="WEBHOOK_UNAUTHORIZED", message="Webhook secret is invalid.")

    @staticmethod
    def validate_meta_webhook_challenge(mode: str | None, verify_token: str | None) -> None:
        if mode != "subscribe" or not settings.META_WEBHOOK_VERIFY_TOKEN or verify_token != settings.META_WEBHOOK_VERIFY_TOKEN:
            raise AppException(status_code=401, code="WEBHOOK_VERIFICATION_FAILED", message="Webhook verification failed.")

    async def create_notification(self, user_id: str, notification_type: str, title: str, body: str) -> dict:
        document = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "body": body,
            "read": False,
            "created_at": utc_now(),
        }
        result = await self.db.notifications.insert_one(document)
        document["_id"] = result.inserted_id
        public_document = self._to_public(document)
        await PushNotificationService(self.db).enqueue_notification(user_id, public_document)
        return public_document

    async def list_notifications(self, user_id: str, page: int, page_size: int, unread_only: bool) -> dict:
        filters = {"user_id": user_id}
        if unread_only:
            filters["read"] = False
        return await self._paginate(self.db.notifications, filters, page, page_size, "created_at")

    async def mark_notification_read(self, user_id: str, notification_id: str) -> dict:
        notification = await self._get_owned_document(self.db.notifications, user_id, notification_id, "NOTIFICATION_NOT_FOUND")
        updated = await self.db.notifications.find_one_and_update(
            {"_id": notification["_id"]},
            {"$set": {"read": True}},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_public(updated)

    async def dispatch_pending_push_notifications(self, user_id: str, limit: int = 50) -> list[dict]:
        jobs = await self.db.push_dispatch_jobs.find({"user_id": user_id, "status": "queued"}).limit(limit).to_list(length=limit)
        return await PushNotificationService(self.db).dispatch_jobs([job["_id"] for job in jobs], limit=limit)

    async def create_group(self, user_id: str, payload: dict) -> dict:
        now = utc_now()
        conversation = await self.create_conversation(
            user_id,
            {
                "title": payload["name"],
                "member_ids": payload.get("member_ids", []),
                "type": "group",
                "platform": "ai",
                "contact_id": None,
            },
        )
        group = {
            "user_id": user_id,
            "name": payload["name"],
            "member_ids": list(dict.fromkeys(payload.get("member_ids", []))),
            "admin_ids": list(dict.fromkeys(payload.get("admin_ids", []) or [user_id])),
            "conversation_id": conversation["id"],
            "created_at": now,
            "updated_at": now,
        }
        result = await self.db.groups.insert_one(group)
        group["_id"] = result.inserted_id
        return self._to_public(group)

    async def list_groups(self, user_id: str, page: int, page_size: int, search: str | None) -> dict:
        filters = {"user_id": user_id}
        if search:
            filters["name"] = {"$regex": search, "$options": "i"}
        return await self._paginate(self.db.groups, filters, page, page_size, "created_at")

    async def update_group(self, user_id: str, group_id: str, updates: dict) -> dict:
        group = await self._get_owned_document(self.db.groups, user_id, group_id, "GROUP_NOT_FOUND")
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.groups.find_one_and_update(
            {"_id": group["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        if clean_updates.get("name") and group.get("conversation_id") and ObjectId.is_valid(group["conversation_id"]):
            await self.db.conversations.update_one(
                {"_id": ObjectId(group["conversation_id"])},
                {"$set": {"title": clean_updates["name"], "updated_at": utc_now()}},
            )
        return self._to_public(updated)

    async def get_settings(self, user: dict) -> dict:
        integrations = await self.list_integrations(str(user["_id"]))
        safe_user = serialize_mongo_document(user) or {}
        return {
            "id": safe_user["_id"],
            "full_name": safe_user["full_name"],
            "email": safe_user["email"],
            "avatar_url": safe_user.get("avatar_url"),
            "language_preference": safe_user.get("language_preference", "EN"),
            "notification_preferences": safe_user.get(
                "notification_preferences",
                {
                    "new_messages": True,
                    "missed_calls": True,
                    "scheduled_calls": True,
                    "ai_tasks": True,
                    "calendar_reminders": True,
                },
            ),
            "integrations": integrations,
        }

    async def update_settings(self, user: dict, updates: dict) -> dict:
        clean_updates = {key: value for key, value in updates.items() if value is not None}
        clean_updates["updated_at"] = utc_now()
        updated = await self.db.users.find_one_and_update(
            {"_id": user["_id"]},
            {"$set": clean_updates},
            return_document=ReturnDocument.AFTER,
        )
        return await self.get_settings(updated or user)

    async def register_push_token(self, user: dict, payload: dict) -> dict:
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {"$pull": {"device_tokens": {"device_id": payload["device_id"]}}},
        )
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {
                "$push": {
                    "device_tokens": {
                        "device_id": payload["device_id"],
                        "token": payload["token"],
                        "platform": payload["platform"],
                        "updated_at": utc_now(),
                    }
                },
                "$set": {"updated_at": utc_now()},
            },
        )
        return {"device_id": payload["device_id"], "registered": True}

    async def change_password(self, user: dict, current_password: str, new_password: str) -> dict:
        if not verify_password(current_password, user["password_hash"]):
            raise AppException(status_code=400, code="INVALID_PASSWORD", message="Current password is incorrect.")
        await self.db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"password_hash": hash_password(new_password), "updated_at": utc_now()}},
        )
        await self.db.refresh_tokens.update_many({"user_id": str(user["_id"])}, {"$set": {"is_revoked": True}})
        return {"changed": True}

    async def revoke_sessions(self, user: dict) -> dict:
        result = await self.db.refresh_tokens.update_many({"user_id": str(user["_id"])}, {"$set": {"is_revoked": True}})
        return {"revoked_sessions": result.modified_count}

    async def _paginate(
        self,
        collection,
        filters: dict,
        page: int,
        page_size: int,
        sort_field: str,
        ascending: bool = False,
    ) -> dict:
        total = await collection.count_documents(filters)
        direction = 1 if ascending else -1
        cursor = collection.find(filters).sort(sort_field, direction).skip((page - 1) * page_size).limit(page_size)
        items = self._to_public_many(await cursor.to_list(length=page_size))
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": ceil(total / page_size) if page_size else 1,
            },
        }

    async def _get_owned_document(self, collection, user_id: str, document_id: str, code: str) -> dict:
        if not ObjectId.is_valid(document_id):
            raise AppException(status_code=404, code=code, message="Requested resource was not found.")
        document = await collection.find_one({"_id": ObjectId(document_id), "user_id": user_id})
        if not document:
            raise AppException(status_code=404, code=code, message="Requested resource was not found.")
        return document

    async def _serialize_conversation(self, conversation: dict) -> dict:
        safe = self._to_public(conversation)
        latest = await self.db.messages.find({"conversation_id": safe["id"], "user_id": safe["user_id"]}).sort(
            "timestamp", -1
        ).limit(1).to_list(length=1)
        unread_count = await self.db.messages.aggregate(
            [
                {"$match": {"conversation_id": safe["id"], "user_id": safe["user_id"]}},
                {"$group": {"_id": None, "total": {"$sum": "$unread_count"}}},
            ]
        ).to_list(length=1)
        latest_message = latest[0] if latest else None
        latest_sender_name = await self._resolve_message_sender_name(safe.get("user_id", ""), latest_message, safe)
        safe["last_message_preview"] = latest_message["content"] if latest_message else None
        safe["last_message_sender_name"] = latest_sender_name
        safe["unread_count"] = unread_count[0]["total"] if unread_count else 0
        safe["has_unread"] = safe["unread_count"] > 0
        safe["is_ai_assistant"] = safe.get("type") == "ai"
        safe["is_group"] = safe.get("type") == "group"
        safe["display_time_label"] = self._conversation_time_label(latest_message.get("timestamp") if latest_message else safe.get("updated_at"))
        safe["delivery_state"] = self._conversation_delivery_state(latest_message, safe["has_unread"])
        safe["platform_label"] = self._platform_label(safe.get("platform"))
        safe["platform_icon_key"] = self._platform_icon_key(safe.get("platform"))
        safe["platform_badge_color"] = self._platform_badge_color(safe.get("platform"))

        if safe["is_ai_assistant"]:
            safe["title"] = "Mabdel AI Assistant"
            safe["contact_name"] = "Mabdel AI Assistant"
            safe["avatar_url"] = None
            safe["presence"] = "online"
            safe["presence_label"] = "Online"
            safe["participant_preview"] = []
        elif safe["is_group"]:
            safe["presence"] = "group"
            safe["presence_label"] = "Group"
            safe["participant_preview"] = await self._group_participant_preview(safe.get("user_id", ""), safe.get("member_ids", []))
            safe["avatar_url"] = None
            safe["contact_name"] = safe.get("title")
            if latest_sender_name and safe["last_message_preview"]:
                safe["last_message_preview"] = f"{latest_sender_name}: {safe['last_message_preview']}"
        else:
            contact = await self._get_conversation_contact(safe.get("user_id", ""), safe)
            safe["contact_name"] = contact.get("name") if contact else safe.get("title")
            safe["title"] = safe.get("title") or (contact.get("name") if contact else None)
            safe["avatar_url"] = contact.get("avatar_url") if contact else None
            safe["presence"] = (contact or {}).get("presence", "offline")
            safe["presence_label"] = self._presence_label(safe["presence"])
            safe["participant_preview"] = []
        safe.pop("user_id", None)
        return safe

    async def _serialize_message(self, message: dict) -> dict:
        safe = self._to_public(message)
        reply_id = safe.get("reply_to_message_id")
        forward_id = safe.get("forward_from_message_id")
        reply_doc = await self._get_optional_owned_message(safe.get("user_id", ""), reply_id)
        forward_doc = await self._get_optional_owned_message(safe.get("user_id", ""), forward_id)
        safe["is_read"] = safe.get("status") == "read" or safe.get("read_at") is not None
        safe["read_receipt_label"] = self._format_read_receipt_label(safe.get("read_at")) if safe["is_read"] else None
        safe["status_timestamps"] = {
            "sent_at": safe.get("timestamp"),
            "delivered_at": safe.get("delivered_at"),
            "read_at": safe.get("read_at"),
        }
        safe["reply_to_message_preview"] = self._message_preview(reply_doc)
        safe["forward_from_message_preview"] = self._message_preview(forward_doc)
        safe.pop("user_id", None)
        return safe

    def _with_preview_url(self, document: dict) -> dict:
        if "preview_url" not in document:
            encoded = quote_plus(document.get("file_url", ""))
            document["preview_url"] = f"/api/v1/smartflow/documents/preview?file={encoded}"
        return document

    def _sanitize_integration(self, document: dict) -> dict:
        safe = self._to_public(document)
        safe.pop("access_token_encrypted", None)
        safe.pop("refresh_token_encrypted", None)
        safe.pop("user_id", None)
        return safe

    def _serialize_integration(self, document: dict, metadata: dict | None = None) -> dict:
        safe = self._sanitize_integration(document)
        meta = metadata or self._integration_metadata(safe.get("platform"))
        connected = safe.get("status") == "connected"
        safe["connected"] = connected
        safe["platform_label"] = meta["platform_label"]
        safe["description"] = meta["description"]
        safe["icon_key"] = meta["icon_key"]
        safe["brand_color"] = meta["brand_color"]
        safe["auth_mode"] = meta["auth_mode"]
        safe["is_available"] = meta["is_available"]
        safe["is_configured"] = meta["is_configured"]
        safe["health_status"] = "connected" if connected else ("misconfigured" if not meta["is_configured"] else "disconnected")
        safe["cta_label"] = "Connected" if connected else ("Connect" if meta["is_configured"] else "Unavailable")
        return safe

    def _integration_metadata(self, platform: str | None) -> dict:
        for item in self._integration_catalog_metadata():
            if item["platform"] == platform:
                return item
        return {
            "platform": platform or "unknown",
            "platform_label": "Unknown",
            "description": "",
            "icon_key": platform or "unknown",
            "brand_color": "#64748B",
            "auth_mode": "oauth",
            "is_available": False,
            "is_configured": False,
        }

    def _integration_catalog_metadata(self) -> list[dict]:
        return [
            {
                "platform": "facebook_messenger",
                "platform_label": "Facebook",
                "description": "Manage page posts and messenger leads.",
                "icon_key": "facebook",
                "brand_color": "#1877F2",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.META_CLIENT_ID and settings.META_CLIENT_SECRET),
            },
            {
                "platform": "instagram",
                "platform_label": "Instagram",
                "description": "Sync visual content and DMs.",
                "icon_key": "instagram",
                "brand_color": "#E4405F",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.META_CLIENT_ID and settings.META_CLIENT_SECRET),
            },
            {
                "platform": "whatsapp",
                "platform_label": "WhatsApp",
                "description": "Customer service and automated replies.",
                "icon_key": "whatsapp",
                "brand_color": "#25D366",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.META_CLIENT_ID and settings.META_CLIENT_SECRET),
            },
            {
                "platform": "google_business",
                "platform_label": "Google Business",
                "description": "Connect your business listing and messages.",
                "icon_key": "google",
                "brand_color": "#4285F4",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            },
            {
                "platform": "linkedin",
                "platform_label": "LinkedIn",
                "description": "B2B outreach and company updates.",
                "icon_key": "linkedin",
                "brand_color": "#0A66C2",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET),
            },
            {
                "platform": "twitter_x",
                "platform_label": "Twitter (X)",
                "description": "Real-time engagement and support.",
                "icon_key": "x",
                "brand_color": "#111111",
                "auth_mode": "oauth",
                "is_available": True,
                "is_configured": bool(settings.TWITTER_CLIENT_ID and settings.TWITTER_CLIENT_SECRET),
            },
            {
                "platform": "telegram",
                "platform_label": "Telegram",
                "description": "Broadcast news and direct support.",
                "icon_key": "telegram",
                "brand_color": "#229ED9",
                "auth_mode": "manual",
                "is_available": True,
                "is_configured": True,
            },
        ]

    @staticmethod
    def _conversation_matches_search(item: dict, needle: str) -> bool:
        haystacks = [
            item.get("title") or "",
            item.get("contact_name") or "",
            item.get("last_message_preview") or "",
            item.get("last_message_sender_name") or "",
            " ".join(item.get("participant_preview", [])),
        ]
        return any(needle in value.lower() for value in haystacks)

    def _conversation_list_summary(self, items: list[dict]) -> dict:
        total_unread = sum(item.get("unread_count", 0) for item in items)
        by_platform: dict[str, int] = {}
        for item in items:
            platform = item.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + item.get("unread_count", 0)
        return {"total_unread": total_unread, "by_platform": by_platform}

    async def _get_conversation_contact(self, user_id: str, conversation: dict) -> dict | None:
        contact_id = conversation.get("contact_id")
        if contact_id and ObjectId.is_valid(contact_id):
            return await self.db.contacts.find_one({"_id": ObjectId(contact_id), "user_id": user_id})
        title = conversation.get("title")
        if title:
            return await self.db.contacts.find_one({"user_id": user_id, "name": title})
        return None

    async def _publish_inbox_update(self, user_id: str, conversation_id: str) -> None:
        conversation = await self.db.conversations.find_one({"_id": ObjectId(conversation_id), "user_id": user_id}) if ObjectId.is_valid(conversation_id) else None
        if not conversation:
            return
        serialized = await self._serialize_conversation(conversation)
        summary = await self.get_unread_message_summary(user_id, None)
        await inbox_realtime_hub.publish(
            user_id,
            "inbox.updated",
            {"conversation": serialized, "summary": summary},
        )

    async def _resolve_message_sender_name(self, user_id: str, latest_message: dict | None, conversation: dict) -> str | None:
        if not latest_message:
            return None
        if conversation.get("type") == "ai":
            return "Mabdel AI"
        contact_id = latest_message.get("contact_id")
        if contact_id and ObjectId.is_valid(contact_id):
            contact = await self.db.contacts.find_one({"_id": ObjectId(contact_id), "user_id": user_id})
            if contact:
                return contact.get("name")
        if latest_message.get("direction") == "outbound":
            return "You"
        if conversation.get("type") == "group":
            return "Member"
        return conversation.get("title")

    async def _group_participant_preview(self, user_id: str, member_ids: list[str]) -> list[str]:
        names: list[str] = []
        for member_id in member_ids:
            if member_id == user_id or not ObjectId.is_valid(member_id):
                continue
            contact = await self.db.contacts.find_one({"_id": ObjectId(member_id), "user_id": user_id})
            if contact and contact.get("name"):
                names.append(contact["name"])
            if len(names) >= 3:
                break
        return names

    @staticmethod
    def _presence_label(presence: str | None) -> str:
        mapping = {
            "online": "Online",
            "offline": "Offline",
            "busy": "Busy",
            "away": "Away",
            "group": "Group",
        }
        return mapping.get((presence or "offline").lower(), "Offline")

    @staticmethod
    def _conversation_delivery_state(latest_message: dict | None, has_unread: bool) -> str | None:
        if not latest_message:
            return None
        if has_unread:
            return "unread"
        if latest_message.get("direction") == "outbound":
            status = latest_message.get("status")
            if status == "read":
                return "read"
            if status == "delivered":
                return "delivered"
            return "sent"
        return "received"

    @staticmethod
    def _platform_label(platform: str | None) -> str:
        labels = {
            "whatsapp": "WhatsApp",
            "facebook_messenger": "Facebook",
            "instagram": "Instagram",
            "linkedin": "LinkedIn",
            "twitter_x": "X",
            "telegram": "Telegram",
            "sms": "SMS",
            "email": "Email",
            "google_business": "Google Business",
            "ai": "AI",
        }
        return labels.get(platform or "", "Unknown")

    @staticmethod
    def _platform_icon_key(platform: str | None) -> str:
        mapping = {
            "facebook_messenger": "facebook",
            "twitter_x": "x",
            "google_business": "google",
        }
        return mapping.get(platform or "", platform or "unknown")

    @staticmethod
    def _platform_badge_color(platform: str | None) -> str:
        colors = {
            "whatsapp": "#25D366",
            "facebook_messenger": "#1877F2",
            "instagram": "#E4405F",
            "linkedin": "#0A66C2",
            "twitter_x": "#111111",
            "telegram": "#229ED9",
            "sms": "#3B82F6",
            "email": "#64748B",
            "google_business": "#4285F4",
            "ai": "#06B6D4",
        }
        return colors.get(platform or "", "#64748B")

    @staticmethod
    def _conversation_time_label(value: datetime | None) -> str | None:
        if not value:
            return None
        now = utc_now()
        current = value if value.tzinfo else value.replace(tzinfo=now.tzinfo)
        delta = now - current
        if delta < timedelta(minutes=1):
            return "Now"
        if delta < timedelta(hours=1):
            return f"{max(1, int(delta.total_seconds() // 60))}m ago"
        if delta < timedelta(days=1):
            return f"{max(1, int(delta.total_seconds() // 3600))}h ago"
        if delta < timedelta(days=2):
            return "Yesterday"
        return current.strftime("%b %d")

    def _serialize_history_item(self, document: dict | None) -> dict:
        safe = self._to_public(document)
        safe["command_type_label"] = self._history_type_label(safe.get("command_type"))
        safe["status_label"] = self._history_status_label(safe.get("status"))
        safe["icon"] = self._history_icon(safe.get("command_type"))
        safe["accent_tone"] = self._history_accent_tone(safe.get("status"))
        safe["date_bucket"] = self._history_date_bucket(safe.get("timestamp"))
        return safe

    def _group_history_items_by_day(self, items: list[dict]) -> dict[str, list[dict]]:
        grouped = {"today": [], "yesterday": [], "older": []}
        for item in items:
            grouped.setdefault(item["date_bucket"], []).append(item)
        return grouped

    async def _replay_linked_resource(self, user_id: str, history: dict) -> dict | None:
        related = history.get("related_resource") or {}
        resource_type = related.get("type")
        resource_id = related.get("id")
        if not resource_type or not resource_id:
            return None

        if resource_type == "invoice" and ObjectId.is_valid(resource_id):
            invoice = await self.db.invoices.find_one({"_id": ObjectId(resource_id), "owner_user_id": user_id})
            if invoice:
                return {
                    "result_type": "invoice",
                    "resource_id": resource_id,
                    "resource_type": "invoice",
                    "resource": {
                        "id": resource_id,
                        "invoice_number": invoice.get("invoice_number"),
                        "status": invoice.get("status"),
                        "total_amount": invoice.get("total_amount"),
                        "client_name": invoice.get("client_name"),
                    },
                }

        if resource_type == "bulk_message" and ObjectId.is_valid(resource_id):
            bulk_message = await self.db.bulk_messages.find_one({"_id": ObjectId(resource_id), "user_id": user_id})
            if bulk_message:
                serialized = self._serialize_bulk_message(bulk_message)
                return {
                    "result_type": "bulk_message",
                    "resource_id": resource_id,
                    "resource_type": "bulk_message",
                    "resource": serialized,
                }

        if resource_type == "document" and ObjectId.is_valid(resource_id):
            document = await self.db.documents.find_one({"_id": ObjectId(resource_id), "user_id": user_id})
            if document:
                serialized = self._with_preview_url(self._to_public(document))
                return {
                    "result_type": "document",
                    "resource_id": resource_id,
                    "resource_type": "document",
                    "resource": serialized,
                }
        return None

    @staticmethod
    def _history_type_label(command_type: str | None) -> str:
        labels = {
            "invoice": "Invoices",
            "voice": "AI Voice",
            "email": "Email",
            "report": "Report",
            "message": "Message",
            "agreement": "Agreement",
            "calendar": "Calendar",
            "bulk_message": "Bulk Messaging",
            "legal": "Legal",
            "document": "Document",
        }
        return labels.get(command_type or "", "Activity")

    @staticmethod
    def _history_status_label(status: str | None) -> str:
        labels = {
            "completed": "Completed",
            "archived": "Archived",
            "exported": "Exported",
            "delivered": "Delivered",
            "scheduled": "Scheduled",
            "processing": "Processing",
            "failed": "Failed",
        }
        return labels.get(status or "", "Completed")

    @staticmethod
    def _history_icon(command_type: str | None) -> str:
        icons = {
            "invoice": "invoice",
            "voice": "microphone",
            "email": "mail",
            "report": "chart",
            "message": "message",
            "agreement": "document",
            "calendar": "calendar",
            "bulk_message": "send",
            "legal": "document",
            "document": "document",
        }
        return icons.get(command_type or "", "history")

    @staticmethod
    def _document_command_type(document_type: str | None) -> str:
        mapping = {
            "agreement": "agreement",
            "invoice": "invoice",
            "lease": "legal",
            "others": "document",
        }
        return mapping.get(document_type or "", "document")

    @staticmethod
    def _history_accent_tone(status: str | None) -> str:
        tones = {
            "completed": "success",
            "archived": "muted",
            "exported": "info",
            "delivered": "success",
            "scheduled": "warning",
            "processing": "info",
            "failed": "danger",
        }
        return tones.get(status or "", "info")

    @staticmethod
    def _history_date_bucket(value: datetime | None) -> str:
        if not value:
            return "older"
        now = utc_now()
        current = value.astimezone(now.tzinfo).date() if value.tzinfo else value.date()
        today = now.date()
        if current == today:
            return "today"
        if current == today - timedelta(days=1):
            return "yesterday"
        return "older"

    async def _dispatch_bulk_message(self, document: dict) -> dict:
        now = utc_now()
        deliveries: list[dict] = []
        sent_count = 0
        failed_count = 0
        for recipient in document.get("recipients", []):
            target = recipient.get("email") if document["channel"] == "email" else recipient.get("phone")
            if not target:
                deliveries.append(
                    {
                        "target": "",
                        "contact_id": recipient.get("id"),
                        "name": recipient.get("name"),
                        "status": "failed",
                        "error": "Recipient does not have a valid delivery target.",
                        "sent_at": None,
                    }
                )
                failed_count += 1
                continue

            if document["channel"] == "email":
                try:
                    await EmailService().send_invoice_email(
                        email=target,
                        subject=document.get("subject") or "Mabdel bulk message",
                        text=document["content"],
                        html=f"<p>{document['content']}</p>",
                    )
                    status = "sent"
                    error = None
                    sent_count += 1
                except Exception as exc:
                    status = "failed"
                    error = str(exc)
                    failed_count += 1
            else:
                status = "sent"
                error = None
                sent_count += 1

            deliveries.append(
                {
                    "target": target,
                    "contact_id": recipient.get("id"),
                    "name": recipient.get("name"),
                    "status": status,
                    "error": error,
                    "sent_at": now if status == "sent" else None,
                }
            )

        final_status = "sent"
        if sent_count and failed_count:
            final_status = "partial_failed"
        elif failed_count and not sent_count:
            final_status = "failed"

        updated = await self.db.bulk_messages.find_one_and_update(
            {"_id": document["_id"]},
            {
                "$set": {
                    "deliveries": deliveries,
                    "sent_count": sent_count,
                    "failed_count": failed_count,
                    "status": final_status,
                    "sent_at": now if sent_count else None,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        await self.create_notification(
            user_id=document["user_id"],
            notification_type="message",
            title="Bulk message dispatched",
            body=f"{sent_count} delivered, {failed_count} failed.",
        )
        await self.log_ai_command(
            user_id=document["user_id"],
            command_text=f"Send bulk {document['channel']} to {len(document.get('recipients', []))} recipients",
            command_type="bulk_message",
            status="delivered" if sent_count else "failed",
            is_replayable=True,
            related_resource={"type": "bulk_message", "id": str(document["_id"]), "status": final_status},
            preview_payload={"channel": document["channel"], "sent_count": sent_count, "failed_count": failed_count},
        )
        return updated

    async def _resolve_bulk_recipients(self, user_id: str, payload: dict) -> dict:
        channel = payload.get("channel", "email")
        recipients: list[dict] = []
        invalid_entries: list[str] = []
        duplicate_entries: list[str] = []
        unavailable_contact_ids: list[str] = []
        unavailable_group_ids: list[str] = []
        seen_targets: set[str] = set()
        seen_raw_inputs: set[str] = set()

        def add_recipient(entry: dict, *, raw_key: str | None = None) -> None:
            target = (entry.get("email") if channel == "email" else entry.get("phone")) or ""
            normalized_target = target.strip().lower()
            if not normalized_target:
                if raw_key:
                    invalid_entries.append(raw_key)
                return
            if normalized_target in seen_targets:
                duplicate_entries.append(raw_key or normalized_target)
                return
            seen_targets.add(normalized_target)
            recipients.append(entry)

        for raw_email in payload.get("recipient_emails", []):
            if not isinstance(raw_email, str):
                continue
            normalized = raw_email.strip().lower()
            if not normalized:
                continue
            if normalized in seen_raw_inputs:
                duplicate_entries.append(normalized)
                continue
            seen_raw_inputs.add(normalized)
            if not self._is_valid_email(normalized):
                invalid_entries.append(normalized)
                continue
            if channel == "email":
                add_recipient(
                    {
                        "id": None,
                        "name": normalized,
                        "email": normalized,
                        "phone": None,
                        "avatar_url": None,
                        "initials": self._contact_initials(normalized),
                        "source": "raw_email",
                    },
                    raw_key=normalized,
                )

        for contact_id in list(dict.fromkeys(payload.get("contact_ids", []))):
            if not ObjectId.is_valid(contact_id):
                unavailable_contact_ids.append(contact_id)
                continue
            contact = await self.db.contacts.find_one({"_id": ObjectId(contact_id), "user_id": user_id})
            if not contact:
                unavailable_contact_ids.append(contact_id)
                continue
            add_recipient(
                {
                    "id": str(contact["_id"]),
                    "name": contact.get("name"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "avatar_url": contact.get("avatar_url"),
                    "initials": self._contact_initials(contact.get("name")),
                    "source": "contact",
                },
                raw_key=(contact.get("email") if channel == "email" else contact.get("phone")) or contact_id,
            )

        for group_id in list(dict.fromkeys(payload.get("group_ids", []))):
            if not ObjectId.is_valid(group_id):
                unavailable_group_ids.append(group_id)
                continue
            group = await self.db.groups.find_one({"_id": ObjectId(group_id), "user_id": user_id})
            if not group:
                unavailable_group_ids.append(group_id)
                continue
            for member_id in group.get("member_ids", []):
                if not ObjectId.is_valid(member_id):
                    continue
                contact = await self.db.contacts.find_one({"_id": ObjectId(member_id), "user_id": user_id})
                if not contact:
                    continue
                add_recipient(
                    {
                        "id": str(contact["_id"]),
                        "name": contact.get("name"),
                        "email": contact.get("email"),
                        "phone": contact.get("phone"),
                        "avatar_url": contact.get("avatar_url"),
                        "initials": self._contact_initials(contact.get("name")),
                        "source": "group_member",
                    },
                    raw_key=(contact.get("email") if channel == "email" else contact.get("phone")) or member_id,
                )

        return {
            "recipients": recipients,
            "invalid_entries": invalid_entries,
            "duplicate_entries": duplicate_entries,
            "unavailable_contact_ids": unavailable_contact_ids,
            "unavailable_group_ids": unavailable_group_ids,
        }

    def _validate_bulk_message_payload(self, payload: dict, resolution: dict) -> None:
        channel = payload.get("channel", "email")
        content = (payload.get("content") or "").strip()
        if not content:
            raise AppException(status_code=400, code="BULK_CONTENT_REQUIRED", message="Bulk message content is required.")
        if channel == "email" and not (payload.get("subject") or "").strip():
            raise AppException(status_code=400, code="BULK_SUBJECT_REQUIRED", message="Email bulk messages require a subject.")
        if not resolution["recipients"]:
            raise AppException(status_code=400, code="BULK_RECIPIENTS_REQUIRED", message="At least one valid recipient is required.")
        scheduled_at = payload.get("scheduled_at")
        if scheduled_at and scheduled_at <= utc_now():
            raise AppException(status_code=400, code="BULK_SCHEDULE_INVALID", message="Scheduled send time must be in the future.")

    @staticmethod
    def _serialize_bulk_message(document: dict | None) -> dict:
        safe = serialize_mongo_document(document) or {}
        if "_id" in safe:
            safe["id"] = safe.pop("_id")
        safe.pop("user_id", None)
        return safe

    @staticmethod
    def _bulk_segment_count(channel: str, content: str) -> int:
        if channel == "sms":
            return max(1, ceil(len(content) / 160))
        return 1

    @staticmethod
    def _is_valid_email(value: str) -> bool:
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))

    async def _serialize_calendar_event(self, event: dict | None) -> dict:
        safe = self._to_public(event)
        user_id = safe.get("user_id", "")
        attendees = await self._hydrate_calendar_attendees(user_id, safe.get("contact_ids", []))
        safe["attendees"] = attendees
        safe["attendee_count"] = len(attendees)
        safe["meeting_mode"] = safe.get("meeting_mode", "offline")
        safe["location"] = safe.get("location")
        safe["meeting_link"] = safe.get("meeting_link")
        safe["notify_via_push"] = safe.get("notify_via_push", True)
        safe["notify_via_email"] = safe.get("notify_via_email", False)
        safe["notify_via_sms"] = safe.get("notify_via_sms", False)
        safe["timezone"] = safe.get("timezone", "UTC")
        safe["status"] = safe.get("status", "scheduled")
        safe["sync_status"] = safe.get("sync_status", "local")
        safe["share_url"] = self._calendar_share_url(safe["share_token"]) if safe.get("share_token") else None
        safe.pop("share_token", None)
        safe.pop("user_id", None)
        return safe

    async def _hydrate_calendar_attendees(self, user_id: str, contact_ids: list[str]) -> list[dict]:
        attendees: list[dict] = []
        for contact_id in contact_ids:
            if not ObjectId.is_valid(contact_id):
                continue
            contact = await self.db.contacts.find_one({"_id": ObjectId(contact_id), "user_id": user_id})
            if not contact:
                continue
            attendees.append(
                {
                    "id": str(contact["_id"]),
                    "name": contact.get("name", "Unknown Contact"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "avatar_url": contact.get("avatar_url"),
                    "initials": self._contact_initials(contact.get("name")),
                }
            )
        return attendees

    @staticmethod
    def _contact_initials(name: str | None) -> str:
        if not name:
            return "NA"
        parts = [part[:1].upper() for part in name.split() if part.strip()]
        return "".join(parts[:2]) or "NA"

    def _validate_calendar_event_payload(self, payload: dict) -> None:
        starts_at = payload.get("starts_at")
        ends_at = payload.get("ends_at")
        if not starts_at or not ends_at:
            raise AppException(status_code=400, code="CALENDAR_TIMING_REQUIRED", message="Meeting start and end time are required.")
        if ends_at <= starts_at:
            raise AppException(status_code=400, code="CALENDAR_INVALID_RANGE", message="Meeting end time must be later than start time.")
        if payload.get("meeting_mode") == "online" and payload.get("location") and not payload.get("meeting_link"):
            return

    async def _assert_calendar_slot_available(
        self,
        user_id: str,
        starts_at: datetime,
        ends_at: datetime,
        exclude_event_id: str | None = None,
    ) -> None:
        filters: dict = {
            "user_id": user_id,
            "starts_at": {"$lt": ends_at},
            "ends_at": {"$gt": starts_at},
            "status": {"$ne": "cancelled"},
        }
        if exclude_event_id and ObjectId.is_valid(exclude_event_id):
            filters["_id"] = {"$ne": ObjectId(exclude_event_id)}
        existing = await self.db.calendar_events.find_one(filters)
        if existing:
            raise AppException(
                status_code=409,
                code="CALENDAR_CONFLICT",
                message="Another meeting already exists in this time slot.",
                details={"event_id": str(existing["_id"]), "title": existing.get("title")},
            )

    @staticmethod
    def _parse_date_boundary(value: str, *, end_of_day: bool) -> datetime:
        parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
        if end_of_day:
            return datetime.combine(parsed_date, datetime.max.time()).replace(microsecond=0)
        return datetime.combine(parsed_date, datetime.min.time())

    @staticmethod
    def _generate_meeting_link() -> str:
        base = settings.PUBLIC_BACKEND_URL.rstrip("/")
        return f"{base}/meet/{secrets.token_urlsafe(12)}"

    @staticmethod
    def _calendar_share_url(share_token: str) -> str:
        base = settings.PUBLIC_BACKEND_URL.rstrip("/")
        return f"{base}/calendar/share/{share_token}"

    def _calendar_share_text(self, event: dict, message: str | None, share_url: str) -> str:
        starts_at = event["starts_at"].strftime("%b %d, %Y %I:%M %p")
        lines = [f"You're invited to {event['title']}.", f"Starts: {starts_at}"]
        if event.get("meeting_link"):
            lines.append(f"Join link: {event['meeting_link']}")
        if event.get("location"):
            lines.append(f"Location: {event['location']}")
        if message:
            lines.append("")
            lines.append(message)
        lines.append("")
        lines.append(f"View details: {share_url}")
        return "\n".join(lines)

    def _calendar_share_html(self, event: dict, message: str | None, share_url: str) -> str:
        starts_at = event["starts_at"].strftime("%b %d, %Y %I:%M %p")
        location_html = f"<p><strong>Location:</strong> {event['location']}</p>" if event.get("location") else ""
        meeting_link_html = (
            f"<p><strong>Join link:</strong> <a href=\"{event['meeting_link']}\">{event['meeting_link']}</a></p>"
            if event.get("meeting_link")
            else ""
        )
        note_html = f"<p>{message}</p>" if message else ""
        return (
            f"<h2>{event['title']}</h2>"
            f"<p><strong>Starts:</strong> {starts_at}</p>"
            f"{location_html}"
            f"{meeting_link_html}"
            f"{note_html}"
            f"<p><a href=\"{share_url}\">View meeting details</a></p>"
        )

    async def _create_calendar_event_notifications(self, user_id: str, event: dict, *, action: str) -> None:
        if not event.get("notify_via_push", True):
            return
        starts_at = event["starts_at"].strftime("%b %d, %Y %I:%M %p")
        action_map = {
            "created": ("Meeting scheduled", f"{event['title']} is scheduled for {starts_at}."),
            "updated": ("Meeting updated", f"{event['title']} was updated. Starts at {starts_at}."),
            "shared": ("Meeting shared", f"{event['title']} was shared successfully."),
        }
        title, body = action_map.get(action, ("Meeting update", event["title"]))
        await self.create_notification(user_id=user_id, notification_type="calendar", title=title, body=body)

    @staticmethod
    def _oauth_provider(platform: str) -> dict:
        providers = {
            "google_business": {
                "provider": "google",
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/google_business/oauth/callback",
                "scopes": [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/userinfo.email",
                ],
                "token_payload": {"grant_type": "authorization_code"},
                "extra_authorize_params": {"access_type": "offline", "prompt": "consent"},
            },
            "instagram": {
                "provider": "meta",
                "authorize_url": "https://www.facebook.com/v20.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
                "client_id": settings.META_CLIENT_ID,
                "client_secret": settings.META_CLIENT_SECRET,
                "redirect_uri": settings.META_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/instagram/oauth/callback",
                "scopes": ["instagram_basic", "pages_show_list", "instagram_manage_messages"],
                "token_payload": {},
                "extra_authorize_params": {},
            },
            "facebook_messenger": {
                "provider": "meta",
                "authorize_url": "https://www.facebook.com/v20.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
                "client_id": settings.META_CLIENT_ID,
                "client_secret": settings.META_CLIENT_SECRET,
                "redirect_uri": settings.META_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/facebook_messenger/oauth/callback",
                "scopes": ["pages_show_list", "pages_messaging"],
                "token_payload": {},
                "extra_authorize_params": {},
            },
            "whatsapp": {
                "provider": "meta",
                "authorize_url": "https://www.facebook.com/v20.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
                "client_id": settings.META_CLIENT_ID,
                "client_secret": settings.META_CLIENT_SECRET,
                "redirect_uri": settings.META_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/whatsapp/oauth/callback",
                "scopes": ["whatsapp_business_messaging", "whatsapp_business_management"],
                "token_payload": {},
                "extra_authorize_params": {},
            },
            "linkedin": {
                "provider": "linkedin",
                "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/linkedin/oauth/callback",
                "scopes": ["openid", "profile", "email", "w_member_social"],
                "token_payload": {"grant_type": "authorization_code"},
                "extra_authorize_params": {},
            },
            "twitter_x": {
                "provider": "twitter",
                "authorize_url": "https://twitter.com/i/oauth2/authorize",
                "token_url": "https://api.twitter.com/2/oauth2/token",
                "client_id": settings.TWITTER_CLIENT_ID,
                "client_secret": settings.TWITTER_CLIENT_SECRET,
                "redirect_uri": settings.TWITTER_REDIRECT_URI or f"{settings.PUBLIC_BACKEND_URL}/api/v1/smartflow/integrations/twitter_x/oauth/callback",
                "scopes": ["tweet.read", "users.read", "offline.access"],
                "token_payload": {"grant_type": "authorization_code", "code_verifier": "smartflow-server"},
                "extra_authorize_params": {"code_challenge": "challenge-not-configured", "code_challenge_method": "plain"},
            },
        }
        provider = providers.get(platform)
        if not provider:
            raise AppException(status_code=400, code="INTEGRATION_UNSUPPORTED", message="This integration is not supported yet.")
        if not provider["client_id"] or not provider["client_secret"]:
            raise AppException(
                status_code=503,
                code="INTEGRATION_NOT_CONFIGURED",
                message="This integration is not configured yet.",
                details={"platform": platform},
            )
        return provider

    def _to_public(self, document: dict | None) -> dict:
        safe = serialize_mongo_document(document) or {}
        if "_id" in safe:
            safe["id"] = safe.pop("_id")
        return safe

    def _to_public_many(self, documents: list[dict]) -> list[dict]:
        return [self._to_public(document) for document in documents]

    async def _validate_message_links(self, user_id: str, payload: dict) -> None:
        reply_to_message_id = payload.get("reply_to_message_id")
        forward_from_message_id = payload.get("forward_from_message_id")

        if reply_to_message_id:
            reply_message = await self._get_owned_document(self.db.messages, user_id, reply_to_message_id, "MESSAGE_NOT_FOUND")
            if reply_message["conversation_id"] != payload["conversation_id"]:
                raise AppException(
                    status_code=400,
                    code="INVALID_REPLY_TARGET",
                    message="Reply target must belong to the same conversation.",
                )

        if forward_from_message_id:
            await self._get_owned_document(self.db.messages, user_id, forward_from_message_id, "MESSAGE_NOT_FOUND")

    async def _get_optional_owned_message(self, user_id: str, message_id: str | None) -> dict | None:
        if not message_id or not ObjectId.is_valid(message_id):
            return None
        return await self.db.messages.find_one({"_id": ObjectId(message_id), "user_id": user_id})

    @staticmethod
    def _message_preview(message: dict | None) -> dict | None:
        if not message:
            return None
        return {
            "id": str(message["_id"]),
            "content": message.get("content"),
            "direction": message.get("direction"),
            "timestamp": message.get("timestamp"),
            "status": message.get("status"),
        }

    @staticmethod
    def _format_read_receipt_label(read_at) -> str | None:
        if not read_at:
            return None
        return f"READ {read_at.strftime('%I:%M %p')}"

    @staticmethod
    def _is_future_timestamp(value) -> bool:
        if not value:
            return False
        now = utc_now()
        if getattr(value, "tzinfo", None) is None:
            now = now.replace(tzinfo=None)
        return value > now

    @staticmethod
    def _derive_call_status(payload: dict) -> str:
        if payload.get("callback_requested"):
            return "callback"
        if payload.get("ai_ready"):
            return "ai_ready"
        if payload.get("call_type") == "missed":
            return "missed"
        return "completed"
