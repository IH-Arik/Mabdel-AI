from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.dependencies import get_mongo_database, require_role
from Dashboard.app.dependencies import get_dashboard_service
from Dashboard.app.schemas.dashboard_schemas import (
    BaseResponse, DashboardSummary, GrowthMetrics, PaginatedResponse, 
    UserListItem, AdminCreateRequest, EarningsSummary, TransactionListItem, 
    TransactionDetails, SubscriptionPlan, SubscriptionPlanCreate, AIStats, AILog,
    UserReportListItem, ProfileUpdateRequest, ChangePasswordRequest,
    ForgotPasswordRequest, VerifyOTPRequest, ResetPasswordRequest, SettingsContent,
    ChatConversation, ChatMessage
)

router = APIRouter()

pass


@router.get("/summary", response_model=BaseResponse[DashboardSummary])
async def get_admin_summary(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get a high-level summary of organization metrics including user counts, AI usage, and revenue.
    """
    org_id = current_user.get("organization_id")
    data = await service.get_admin_summary(org_id)
    return BaseResponse(data=data)


@router.get("/users", response_model=BaseResponse[PaginatedResponse[UserListItem]])
async def list_users(
    limit: int = 10,
    offset: int = 0,
    search: str | None = None,
    status: str | None = None,  # active, blocked
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get a paginated list of users for the dashboard table. Supports searching and filtering by status (Blocked/Active).
    """
    data = await service.get_paginated_users(
        organization_id=current_user.get("organization_id"),
        limit=limit,
        offset=offset,
        search=search,
        status=status
    )
    return BaseResponse(data=data)


@router.get("/users/{user_id}", response_model=BaseResponse[UserListItem])
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get detailed information about a specific user. Supports the 'User Details' and 'Provider Details' screens.
    """
    data = await service.get_user_by_id(user_id)
    return BaseResponse(data=data)


@router.patch("/users/{user_id}/status", response_model=BaseResponse[bool])
async def update_user_status(
    user_id: str,
    status: str,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Update a user's status (e.g., 'active', 'blocked'). This corresponds to the 'Block/Unblock' buttons in the UI.
    """
    success = await service.toggle_user_status(user_id, status)
    return BaseResponse(data=success, message=f"User status updated to {status}" if success else "Failed to update status")


@router.post("/create-admin", response_model=BaseResponse[str])
async def create_organization_admin(
    request: AdminCreateRequest,
    current_user: dict = Depends(require_role(["super_admin"])),
    db: AsyncIOMotorDatabase = Depends(get_mongo_database),
):
    """
    Create a new administrator for an organization. 
    Strictly restricted to Super Admins. Corresponds to the 'Create Admin' screen.
    """
    # 1. Check if email already exists
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        from app.core.exceptions import AppException
        raise AppException(status_code=400, code="EMAIL_EXISTS", message="User with this email already exists")

    # 2. Hash password and prepare user document
    # In a real app, use pwd_context.hash(request.password)
    from Dashboard.app.services.dashboard_service import utc_now
    new_admin = {
        "full_name": request.full_name,
        "email": request.email,
        "password": request.password, # Note: Always hash this in production!
        "role": request.role, # admin or super_admin
        "organization_id": request.organization_id,
        "status": "active",
        "created_at": utc_now(),
        "is_subscribed": False
    }
    
    result = await db.users.insert_one(new_admin)
    return BaseResponse(data=str(result.inserted_id), message=f"New {request.role} created successfully")


@router.get("/users-growth", response_model=BaseResponse[GrowthMetrics])
async def get_users_growth(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get analytical data for user growth trends over time for charting.
    """
    data = await service.get_growth_metrics("users", organization_id=current_user.get("organization_id"))
    return BaseResponse(data=data)


@router.get("/earnings", response_model=BaseResponse[EarningsSummary])
async def get_earnings_report(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get a summary of earnings (Today, This Month, Total) for the organization.
    """
    data = await service.get_earnings_summary(current_user.get("organization_id"))
    return BaseResponse(data=data)


@router.get("/earnings/transactions", response_model=BaseResponse[PaginatedResponse[TransactionListItem]])
async def list_transactions(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get a paginated list of transactions for the Earnings table.
    """
    data = await service.get_paginated_transactions(
        organization_id=current_user.get("organization_id"),
        limit=limit,
        offset=offset
    )
    return BaseResponse(data=data)


@router.get("/earnings/transactions/{trx_id}", response_model=BaseResponse[TransactionDetails])
async def get_trx_details(
    trx_id: str,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get detailed information about a specific transaction for the 'Transaction Details' pop-up.
    """
    data = await service.get_transaction_details(trx_id)
    return BaseResponse(data=data)


@router.get("/earnings/transactions/{trx_id}/invoice")
async def download_invoice(
    trx_id: str,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
):
    """
    Download the PDF invoice for a transaction.
    """
    return BaseResponse(data=None, message="PDF Generation logic will be integrated with your invoice service")


@router.get("/reports", response_model=BaseResponse[PaginatedResponse[UserReportListItem]])
async def get_user_reports(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get a paginated list of user reports (Moderation/Complaints). Corresponds to the 'Report' screen.
    """
    data = await service.get_paginated_user_reports(limit, offset)
    return BaseResponse(data=data)


@router.get("/profile", response_model=BaseResponse[UserListItem])
async def get_admin_profile(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    db: AsyncIOMotorDatabase = Depends(get_mongo_database),
):
    """
    Get the profile of the currently logged-in admin. Corresponds to 'Settings' or profile icon.
    """
    user = await db.users.find_one({"_id": current_user["_id"]})
    return BaseResponse(data=UserListItem(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"]
    ))


@router.patch("/profile", response_model=BaseResponse[bool])
async def update_admin_profile(
    update_data: dict, # Simplified for example, should use a proper Schema
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    db: AsyncIOMotorDatabase = Depends(get_mongo_database),
):
    """
    Update admin's own profile info (Name, Password, Image).
    """
    result = await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    return BaseResponse(data=result.modified_count > 0)


@router.get("/admins", response_model=BaseResponse[list[UserListItem]])
async def list_admins(
    current_user: dict = Depends(require_role(["super_admin"])),
    db: AsyncIOMotorDatabase = Depends(get_mongo_database),
):
    """
    List all administrators. Only accessible by Super Admins.
    """
    cursor = db.users.find({"role": {"$in": ["admin", "super_admin"]}})
    admins = await cursor.to_list(length=100)
    data = [
        UserListItem(
            id=str(a["_id"]),
            full_name=a["full_name"],
            email=a["email"],
            role=a["role"],
            status=a["status"],
            created_at=a["created_at"]
        ) for a in admins
    ]
    return BaseResponse(data=data)


@router.get("/settings", response_model=BaseResponse[dict])
async def get_dashboard_settings(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
):
    """
    Get dashboard specific settings and configurations.
    """
    return BaseResponse(data={}, message="Settings placeholder")


@router.get("/subscriptions", response_model=BaseResponse[list[SubscriptionPlan]])
async def list_subscriptions(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    List all available subscription plans for the organization.
    """
    data = await service.get_subscription_plans()
    return BaseResponse(data=data)


@router.post("/subscriptions", response_model=BaseResponse[str])
async def create_subscription_plan(
    plan: SubscriptionPlanCreate,
    current_user: dict = Depends(require_role(["super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Create a new subscription plan (Price, Interval, Features). Only for Super Admins.
    """
    plan_id = await service.create_subscription_plan(plan)
    return BaseResponse(data=plan_id, message="Subscription plan created successfully")


@router.get("/ai/stats", response_model=BaseResponse[AIStats])
async def get_ai_stats(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get AI performance metrics and usage trends for the 'AI Insights & Monitoring' section.
    """
    data = await service.get_ai_monitoring_data(current_user.get("organization_id"))
    return BaseResponse(data=data)


@router.get("/ai/logs", response_model=BaseResponse[list[AILog]])
async def get_ai_logs(
    limit: int = 50,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get recent AI activity logs for real-time monitoring.
    """
    data = await service.get_detailed_ai_logs(limit)
    return BaseResponse(data=data)


@router.get("/profile", response_model=BaseResponse[UserListItem])
async def get_admin_profile(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get the logged-in admin's profile data. Corresponds to the 'Profile' screen header.
    """
    data = await service.get_user_by_id(current_user["user_id"])
    return BaseResponse(data=data)


@router.patch("/profile", response_model=BaseResponse[bool])
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Update admin profile (Name, Email, Contact). Corresponds to the 'Edit Profile' screen.
    """
    success = await service.update_admin_profile(current_user["user_id"], data)
    return BaseResponse(data=success, message="Profile updated successfully")


@router.post("/change-password", response_model=BaseResponse[bool])
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Change admin password. Corresponds to the 'Change Password' screen.
    """
    success = await service.change_admin_password(current_user["user_id"], data)
    return BaseResponse(data=success, message="Password updated successfully")


@router.post("/logout", response_model=BaseResponse[bool])
async def logout(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
):
    """
    Invalidate the current session. Corresponds to the 'Confirm logging out!' modal.
    """
    # In a stateless JWT system, logout is usually handled by the frontend clearing the token.
    # However, you can implement a blacklist here if needed.
    return BaseResponse(data=True, message="Logged out successfully")


@router.get("/settings/content", response_model=BaseResponse[str])
async def get_settings_page_content(
    type: str, # privacy_policy, terms_conditions, about_us
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Fetch static content for settings pages. Corresponds to Settings Menu items.
    """
    content = await service.get_settings_content(type)
    return BaseResponse(data=content)


@router.post("/settings/content", response_model=BaseResponse[bool])
async def update_settings_page_content(
    data: SettingsContent,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Update static content for settings pages (Privacy, Terms, etc.). Corresponds to the 'Save' button.
    """
    success = await service.update_settings_content(data)
    return BaseResponse(data=success, message=f"{data.type} updated successfully")


# AUTH (Forgot Password) Endpoints - Usually public
@router.post("/auth/forgot-password", response_model=BaseResponse[None])
async def forgot_password(
    data: ForgotPasswordRequest,
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Request an OTP for password reset. Corresponds to 'Forgot Password' screen.
    """
    await service.forgot_password(data.email)
    return BaseResponse(data=None, message="OTP sent to your email")


@router.post("/auth/verify-otp", response_model=BaseResponse[bool])
async def verify_otp(
    data: VerifyOTPRequest,
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Verify the OTP sent to email. Corresponds to 'OTP Verification' screen.
    """
    success = await service.verify_otp(data)
    return BaseResponse(data=success, message="OTP verified successfully" if success else "Invalid OTP")


@router.post("/auth/reset-password", response_model=BaseResponse[bool])
async def reset_password(
    data: ResetPasswordRequest,
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Reset password using valid OTP. Final step of forgot password flow.
    """
    success = await service.reset_password(data)
    return BaseResponse(data=success, message="Password reset successful")


# INBOX (Messaging) Endpoints
@router.get("/chats", response_model=BaseResponse[list[ChatConversation]])
async def get_all_conversations(
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get all active conversations. Corresponds to the left panel of the 'Inbox' screen.
    """
    data = await service.get_conversations()
    return BaseResponse(data=data)


@router.get("/chats/{user_id}/messages", response_model=BaseResponse[list[ChatMessage]])
async def get_chat_messages(
    user_id: str,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Get message history for a specific user. Corresponds to the chat bubbles on the 'Inbox' screen.
    """
    data = await service.get_chat_history(user_id, current_user["user_id"])
    return BaseResponse(data=data)


@router.post("/chats/{user_id}/messages", response_model=BaseResponse[None])
async def send_message(
    user_id: str,
    text: str | None = None,
    image_url: str | None = None,
    current_user: dict = Depends(require_role(["admin", "super_admin"])),
    service: DashboardService = Depends(get_dashboard_service),
):
    """
    Send a message to a user. Supports both text and images.
    """
    await service.send_chat_message(current_user["user_id"], user_id, text, image_url)
    return BaseResponse(data=None, message="Message sent")
