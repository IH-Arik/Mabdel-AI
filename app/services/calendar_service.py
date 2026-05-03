from __future__ import annotations

from app.schemas.calendar import CalendarEventRequest, CalendarEventResponse


class CalendarService:
    def schedule(self, payload: CalendarEventRequest) -> CalendarEventResponse:
        return CalendarEventResponse(
            title=payload.title,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            attendees=payload.attendees,
        )
