from __future__ import annotations

from app.workflows.state import WorkflowState


def collect_data(state: WorkflowState) -> WorkflowState:
    state.output["command"] = state.command
    state.output["intent"] = state.intent
    return state
