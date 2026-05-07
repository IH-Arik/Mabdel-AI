from __future__ import annotations

from app.workflows.state import WorkflowState


def parse_intent(state: WorkflowState) -> WorkflowState:
    text = state.command.lower()
    if "bulk" in text and ("email" in text or "mail" in text or "message" in text or "sms" in text):
        state.intent = "bulk_message"
    elif "invoice" in text or "bill" in text:
        state.intent = "invoice"
    elif "lease" in text or "rental agreement" in text or "rent agreement" in text:
        state.intent = "lease"
    elif "agreement" in text or "contract" in text or "nda" in text:
        state.intent = "agreement"
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
