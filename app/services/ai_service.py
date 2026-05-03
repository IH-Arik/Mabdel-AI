from __future__ import annotations

from app.schemas.ai import AICommandRequest, AICommandResponse
from app.schemas.email import EmailDraftRequest, EmailDraftResponse
from app.workflows.graph import run_assistant_workflow


class AIService:
    def handle_command(self, payload: AICommandRequest) -> AICommandResponse:
        state = run_assistant_workflow(payload.command)
        return AICommandResponse(
            intent=state.intent,
            summary=state.summary,
            action_required=state.action_required,
            output=state.output,
        )

    def draft_email(self, payload: EmailDraftRequest) -> EmailDraftResponse:
        subject = payload.subject_hint.strip().rstrip(".")
        body = (
            f"Hello,\n\n"
            f"{payload.instruction.strip()}\n\n"
            f"Regards,\n"
            f"Mabdel AI Assistant"
        )
        return EmailDraftResponse(recipient=payload.recipient, subject=subject, body=body)
