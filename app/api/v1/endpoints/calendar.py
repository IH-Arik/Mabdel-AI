from __future__ import annotations

from fastapi import APIRouter

from app.schemas.calendar import CalendarEventRequest, CalendarEventResponse
from app.services.calendar_service import CalendarService
from app.utils.responses import success_response

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.post("/schedule")
async def schedule_meeting(payload: CalendarEventRequest) -> dict:
    result: CalendarEventResponse = CalendarService().schedule(payload)
    return success_response(data=result.model_dump(), message="Meeting scheduled successfully.")
