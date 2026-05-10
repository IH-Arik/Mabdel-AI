from __future__ import annotations

import base64
import binascii
from collections.abc import Iterable
from io import BytesIO

from app.core.config import settings
from app.core.exceptions import AppException
from app.workflows.graph import run_assistant_workflow


class MabdelAIService:
    system_prompt = (
        "You are Mabdel, a business operations assistant for SmartFlow. "
        "Help with sales, revenue summaries, quarterly analysis, discrepancy checks, "
        "margin comparisons, projections, tax reports, project updates, and email drafting. "
        "When the user message came from voice, it has already been transcribed for you. "
        "Respond normally to the request itself. Do not say you can only assist through text, "
        "do not claim you cannot hear audio, and do not mention platform limitations unless the user asks."
    )

    voice_presets = [
        {"id": "male_exec", "label": "Male Executive", "gender": "male", "style": "clear and confident", "provider_voice": "ash"},
        {"id": "male_warm", "label": "Male Warm", "gender": "male", "style": "warm and calm", "provider_voice": "verse"},
        {"id": "female_exec", "label": "Female Executive", "gender": "female", "style": "professional and polished", "provider_voice": "sage"},
        {"id": "female_warm", "label": "Female Warm", "gender": "female", "style": "friendly and supportive", "provider_voice": "coral"},
        {"id": "neutral_assistant", "label": "Neutral Assistant", "gender": "neutral", "style": "balanced and steady", "provider_voice": "alloy"},
    ]

    def generate_response(self, user_text: str, history: Iterable[dict] | None = None) -> dict:
        normalized = user_text.lower().strip()
        history_list = list(history or [])
        workflow_state = run_assistant_workflow(user_text, history=history_list)
        if workflow_state.intent != "unknown":
            command_type = workflow_state.intent
            navigation = self._navigation_for_intent(workflow_state.intent, user_text)
            return {
                "state": "responded",
                "content": workflow_state.summary or self._workflow_response_text(workflow_state.intent),
                "command_type": command_type,
                "workflow": {
                    "engine": workflow_state.output.get("workflow_engine"),
                    "intent": workflow_state.intent,
                    "summary": workflow_state.summary,
                    "output": workflow_state.output,
                },
                "navigation": navigation,
            }

        llm_response = self._generate_with_openai(user_text, history)
        if llm_response:
            return {
                "state": "responded",
                "content": llm_response,
                "command_type": self._infer_command_type(normalized),
                "workflow": None,
                "navigation": self._navigation_for_intent(self._infer_command_type(normalized), user_text),
            }

        if "tax" in normalized:
            summary = "Prepared a tax reporting outline with deductions, liabilities, and filing checkpoints."
            command_type = "report"
        elif "email" in normalized or "draft" in normalized:
            summary = "Drafted a business-ready email with concise next steps."
            command_type = "email"
        elif "invoice" in normalized:
            summary = "Prepared an invoice workflow response with follow-up and status guidance."
            command_type = "invoice"
        elif "sales" in normalized or "revenue" in normalized or "margin" in normalized:
            summary = "Generated a revenue summary with notable variance signals and target comparisons."
            command_type = "report"
        elif "project" in normalized or "update" in normalized:
            summary = "Prepared a project update with blockers, completed work, and next actions."
            command_type = "message"
        else:
            summary = "Processed the request and prepared an operations-focused response."
            command_type = "message"

        return {
            "state": "responded",
            "content": f"{summary} Context turns reviewed: {len(history_list)}. Request: {user_text.strip()}",
            "command_type": command_type,
            "workflow": None,
            "navigation": self._navigation_for_intent(command_type, user_text),
        }

    def list_voice_presets(self) -> list[dict]:
        return list(self.voice_presets)

    def transcribe_voice(
        self,
        transcript: str | None = None,
        audio_url: str | None = None,
        audio_base64: str | None = None,
        audio_mime_type: str = "audio/wav",
        audio_filename: str = "voice.wav",
    ) -> dict:
        if transcript and transcript.strip():
            text = transcript.strip()
            source = "text"
            status = "provided"
            error = None
        elif audio_base64:
            text, error = self._transcribe_audio_with_openai(audio_base64, audio_mime_type, audio_filename)
            source = "audio"
            status = "transcribed" if text else "transcription_failed"
        elif audio_url:
            text = f"Transcribed voice request from {audio_url}"
            source = "audio_url"
            status = "placeholder"
            error = None
        else:
            text = None
            source = "unknown"
            status = "missing_input"
            error = "No transcript or audio input was provided."

        if not text:
            raise AppException(
                status_code=400,
                code="VOICE_TRANSCRIPTION_FAILED",
                message="Could not understand the voice input. Please try again with a clearer recording.",
                details={"status": status, "source": source, "error": error, "mime_type": audio_mime_type},
            )

        return {
            "state": "responded",
            "transcript": text,
            "source": source,
            "status": status,
        }

    def synthesize_speech(self, text: str, voice_id: str | None = None) -> dict | None:
        preset = self._resolve_voice_preset(voice_id)
        if not settings.OPENAI_API_KEY:
            return {
                "voice_id": preset["id"],
                "provider_voice": preset["provider_voice"],
                "mime_type": "audio/mpeg",
                "audio_base64": None,
                "preview_text": text,
                "status": "unavailable_without_openai_key",
            }

        try:
            from openai import OpenAI
        except ImportError:
            return {
                "voice_id": preset["id"],
                "provider_voice": preset["provider_voice"],
                "mime_type": "audio/mpeg",
                "audio_base64": None,
                "preview_text": text,
                "status": "openai_package_missing",
            }

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            speech = client.audio.speech.create(
                model="tts-1",
                voice=preset["provider_voice"],
                input=text,
                response_format="wav",
            )
            audio_bytes = speech.read()
            return {
                "voice_id": preset["id"],
                "provider_voice": preset["provider_voice"],
                "mime_type": "audio/wav",
                "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                "status": "generated",
            }
        except Exception as exc:
            return {
                "voice_id": preset["id"],
                "provider_voice": preset["provider_voice"],
                "mime_type": "audio/mpeg",
                "audio_base64": None,
                "preview_text": text,
                "status": "generation_failed",
                "error": str(exc)[:240],
            }

    def _generate_with_openai(self, user_text: str, history: Iterable[dict] | None) -> str | None:
        if not settings.OPENAI_API_KEY:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        messages = [{"role": "system", "content": self.system_prompt}]
        for item in list(history or [])[-8:]:
            role = "assistant" if item.get("direction") == "outbound" else "user"
            content = str(item.get("content", "")).strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_text})

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(model=settings.OPENAI_MODEL, messages=messages)
            text = response.choices[0].message.content.strip()
            return text or None
        except Exception:
            return None

    def _transcribe_audio_with_openai(self, audio_base64: str, audio_mime_type: str, audio_filename: str) -> tuple[str | None, str | None]:
        if not settings.OPENAI_API_KEY:
            return None, "OPENAI_API_KEY is not configured."

        try:
            from openai import OpenAI
        except ImportError:
            return None, "openai package is not installed."

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except (binascii.Error, ValueError):
            return None, "Audio payload could not be decoded."

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            buffer = BytesIO(audio_bytes)
            buffer.name = audio_filename or self._filename_from_mime(audio_mime_type)
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=buffer,
            )
            text = getattr(transcription, "text", "").strip()
            return (text or None), None if text else "OpenAI returned an empty transcript."
        except Exception as exc:
            return None, str(exc)[:240]

    def _resolve_voice_preset(self, voice_id: str | None) -> dict:
        if voice_id:
            for preset in self.voice_presets:
                if preset["id"] == voice_id:
                    return preset
        return self.voice_presets[0]

    @staticmethod
    def _filename_from_mime(audio_mime_type: str) -> str:
        if "mpeg" in audio_mime_type or "mp3" in audio_mime_type:
            return "voice.mp3"
        if "webm" in audio_mime_type:
            return "voice.webm"
        if "ogg" in audio_mime_type:
            return "voice.ogg"
        return "voice.wav"

    @staticmethod
    def _infer_command_type(normalized: str) -> str:
        if "tax" in normalized or "sales" in normalized or "revenue" in normalized or "margin" in normalized:
            return "report"
        if "bulk" in normalized and ("email" in normalized or "mail" in normalized or "message" in normalized or "sms" in normalized):
            return "bulk_message"
        if "email" in normalized or "draft" in normalized:
            return "email"
        if "invoice" in normalized:
            return "invoice"
        if "lease" in normalized or "rental agreement" in normalized or "rent agreement" in normalized:
            return "lease"
        if "agreement" in normalized or "contract" in normalized or "nda" in normalized:
            return "agreement"
        return "message"

    @staticmethod
    def _workflow_response_text(intent: str) -> str:
        messages = {
            "invoice": "Sure, opening the invoice creator now.",
            "email": "Sure, opening the email draft workflow now.",
            "bulk_message": "Sure, opening the bulk email workflow now.",
            "calendar": "Sure, opening the scheduling workflow now.",
            "lease": "Sure, opening the lease creator now.",
            "agreement": "Sure, opening the agreement creator now.",
            "group": "Sure, opening the group workflow now.",
            "call": "Sure, opening the call workflow now.",
        }
        return messages.get(intent, "Sure, I found the right workflow.")

    @staticmethod
    def _navigation_for_intent(intent: str, user_text: str) -> dict:
        routes = {
            "invoice": {
                "action": "open_screen",
                "route_name": "invoice_create",
                "screen": "CreateInvoice",
                "path": "/invoices/create",
                "label": "Create Invoice",
            },
            "email": {
                "action": "open_screen",
                "route_name": "email_draft",
                "screen": "EmailDraft",
                "path": "/email/draft",
                "label": "Draft Email",
            },
            "bulk_message": {
                "action": "open_screen",
                "route_name": "bulk_message_create",
                "screen": "CreateBulkMessage",
                "path": "/bulk-messages/create",
                "label": "Create Bulk Email",
            },
            "calendar": {
                "action": "open_screen",
                "route_name": "calendar_create",
                "screen": "CreateCalendarEvent",
                "path": "/calendar/events/create",
                "label": "Schedule Meeting",
            },
            "lease": {
                "action": "open_screen",
                "route_name": "lease_create",
                "screen": "CreateLease",
                "path": "/leases/create",
                "label": "Create Lease",
            },
            "agreement": {
                "action": "open_screen",
                "route_name": "agreement_create",
                "screen": "CreateAgreement",
                "path": "/agreements/create",
                "label": "Create Agreement",
            },
            "group": {
                "action": "open_screen",
                "route_name": "group_create",
                "screen": "CreateGroup",
                "path": "/groups/create",
                "label": "Create Group",
            },
            "call": {
                "action": "open_screen",
                "route_name": "call_history",
                "screen": "CallHistory",
                "path": "/calls",
                "label": "Open Calls",
            },
        }
        route = routes.get(intent)
        if not route:
            return {
                "should_redirect": False,
                "action": "none",
                "route_name": None,
                "screen": None,
                "path": None,
                "label": None,
                "params": {},
            }
        return {
            "should_redirect": True,
            **route,
            "params": {
                "source": "mabdel_ai",
                "prefill_prompt": user_text.strip(),
                "intent": intent,
            },
        }
