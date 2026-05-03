from __future__ import annotations

from app.workflows.state import WorkflowState


def route_by_intent(state: WorkflowState) -> str:
    if state.intent == "invoice":
        return "create_invoice"
    if state.intent == "email":
        return "send_email"
    if state.intent == "calendar":
        return "schedule_meeting"
    if state.intent == "group":
        return "create_group"
    if state.intent == "call":
        return "handle_call"
    return "finalize"
