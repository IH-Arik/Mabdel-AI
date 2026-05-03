from __future__ import annotations

from app.workflows.edges import route_by_intent
from app.workflows.nodes.collect_data import collect_data
from app.workflows.nodes.create_group import create_group
from app.workflows.nodes.create_invoice import create_invoice
from app.workflows.nodes.finalize import finalize
from app.workflows.nodes.handle_call import handle_call
from app.workflows.nodes.parse_intent import parse_intent
from app.workflows.nodes.schedule_meeting import schedule_meeting
from app.workflows.nodes.send_email import send_email
from app.workflows.state import WorkflowState


def run_assistant_workflow(command: str) -> WorkflowState:
    state = WorkflowState(command=command)
    state = parse_intent(state)
    state = collect_data(state)

    route = route_by_intent(state)
    if route == "create_invoice":
        state = create_invoice(state)
    elif route == "send_email":
        state = send_email(state)
    elif route == "schedule_meeting":
        state = schedule_meeting(state)
    elif route == "create_group":
        state = create_group(state)
    elif route == "handle_call":
        state = handle_call(state)

    return finalize(state)
