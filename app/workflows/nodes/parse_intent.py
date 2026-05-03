from __future__ import annotations

from app.workflows.state import WorkflowState


def parse_intent(state: WorkflowState) -> WorkflowState:
    text = state.command.lower()
    if "invoice" in text or "bill" in text:
        state.intent = "invoice"
    elif "email" in text or "mail" in text:
        state.intent = "email"
    elif "meeting" in text or "calendar" in text or "schedule" in text:
        state.intent = "calendar"
    elif "group" in text or "team" in text:
        state.intent = "group"
    elif "call" in text or "phone" in text or "twilio" in text:
        state.intent = "call"
    else:
        state.intent = "unknown"
    return state
