from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CalendarEventRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    starts_at: datetime
    ends_at: datetime
    attendees: list[str] = Field(default_factory=list)


class CalendarEventResponse(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime
    attendees: list[str] = Field(default_factory=list)
    status: str = "scheduled"
