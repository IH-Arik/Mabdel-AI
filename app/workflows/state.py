from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Intent = Literal["invoice", "email", "calendar", "group", "call", "unknown"]


@dataclass
class WorkflowState:
    command: str
    intent: Intent = "unknown"
    summary: str = ""
    action_required: bool = False
    output: dict = field(default_factory=dict)
