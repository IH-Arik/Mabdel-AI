from fastapi import APIRouter, Depends, Request, Header
from Dashboard.app.services.dashboard_service import DashboardService
from Dashboard.app.dependencies import get_dashboard_service
from Dashboard.app.schemas.dashboard_schemas import BaseResponse
import json

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Endpoint for Stripe Webhooks. 
    In production, you should verify the stripe signature here.
    """
    payload = await request.body()
    try:
        # For now, we just parse the JSON. 
        # Once you have STRIPE_WEBHOOK_SECRET, you should use stripe.Webhook.construct_event
        event = json.loads(payload)
    except Exception as e:
        return {"error": str(e)}

    await service.handle_stripe_webhook(event)
    
    return {"status": "success"}
