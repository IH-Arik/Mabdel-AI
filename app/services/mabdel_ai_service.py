from __future__ import annotations

import base64
import binascii
from collections.abc import Iterable
from io import BytesIO

from app.core.config import settings
from app.core.exceptions import AppException


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
        history_count = len(list(history or []))
        llm_response = self._generate_with_openai(user_text, history)
        if llm_response:
            return {
                "state": "responded",
                "content": llm_response,
                "command_type": self._infer_command_type(normalized),
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
            "content": f"{summary} Context turns reviewed: {history_count}. Request: {user_text.strip()}",
            "command_type": command_type,
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
                model="gpt-4o-mini-tts",
                voice=preset["provider_voice"],
                input=text,
                response_format="mp3",
            )
            audio_bytes = speech.read()
            return {
                "voice_id": preset["id"],
                "provider_voice": preset["provider_voice"],
                "mime_type": "audio/mpeg",
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
            response = client.responses.create(model=settings.OPENAI_MODEL, input=messages)
            text = getattr(response, "output_text", "").strip()
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
                model="gpt-4o-mini-transcribe",
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
        if "email" in normalized or "draft" in normalized:
            return "email"
        if "invoice" in normalized:
            return "invoice"
        return "message"
