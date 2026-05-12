from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.helpers import utc_now
from Dashboard.app.repositories.dashboard_repository import DashboardRepository
from Dashboard.app.schemas.dashboard_schemas import (
    DashboardSummary, 
    DashboardStatItem, 
    ChartDataPoint, 
    GrowthMetrics
)


class DashboardService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.repository = DashboardRepository(db)

    async def get_admin_summary(self, organization_id: str) -> DashboardSummary:
        user_stats = await self.repository.get_user_counts(organization_id)
        ai_stats = await self.repository.get_ai_usage_stats(organization_id)
        revenue = await self.repository.get_revenue_stats(organization_id)

        stats = [
            DashboardStatItem(
                label="Total Users",
                value=user_stats["total"],
                description="Total members in your organization"
            ),
            DashboardStatItem(
                label="Active Users (24h)",
                value=user_stats["active_24h"],
                description="Users active in the last 24 hours"
            ),
            DashboardStatItem(
                label="AI Commands",
                value=sum(s["total"] for s in ai_stats.values()),
                description="Total AI interactions"
            ),
            DashboardStatItem(
                label="Organization Revenue",
                value=f"${revenue['total_revenue'] / 100:.2f}",
                description="Total paid invoices"
            )
        ]

        return DashboardSummary(stats=stats)

    async def get_super_admin_summary(self) -> DashboardSummary:
        user_stats = await self.repository.get_user_counts()
        org_count = await self.repository.db.users.distinct("organization_id")
        ai_stats = await self.repository.get_ai_usage_stats()
        revenue = await self.repository.get_revenue_stats()

        stats = [
            DashboardStatItem(
                label="Total Organizations",
                value=len([o for o in org_count if o]),
                description="Total businesses on platform"
            ),
            DashboardStatItem(
                label="Total Platform Users",
                value=user_stats["total"],
                description="Total users across all organizations"
            ),
            DashboardStatItem(
                label="Global AI Usage",
                value=sum(s["total"] for s in ai_stats.values()),
                description="Total AI interactions platform-wide"
            ),
            DashboardStatItem(
                label="Platform Revenue",
                value=f"${revenue['total_revenue'] / 100:.2f}",
                description="Total revenue across all tenants"
            )
        ]

        return DashboardSummary(stats=stats)

    async def get_growth_metrics(self, collection: str, organization_id: str | None = None) -> GrowthMetrics:
        raw_data = await self.repository.get_growth_data(collection, organization_id=organization_id)
        chart_data = [ChartDataPoint(label=d["_id"], value=d["count"]) for d in raw_data]
        
        total = sum(d["count"] for d in raw_data)
        # Simple growth rate calculation (comparing last 7 days vs previous 7 days)
        # This is a placeholder for more complex logic
        growth_rate = 15.5  # Mock value
        
        return GrowthMetrics(
            chart_data=chart_data,
            total_count=total,
            growth_rate=growth_rate
        )

    async def get_paginated_users(
        self, 
        organization_id: str | None = None, 
        limit: int = 10, 
        offset: int = 0, 
        search: str | None = None,
        status: str | None = None
    ) -> PaginatedResponse[UserListItem]:
        filters = {}
        if organization_id:
            filters["organization_id"] = organization_id
        if status:
            filters["status"] = status
        
        items, total = await self.repository.get_users_paginated(organization_id, limit, offset, search, status)
        user_items = [
            UserListItem(
                id=str(item["_id"]),
                full_name=item.get("full_name", "Unknown"),
                email=item.get("email", ""),
                phone_no=item.get("phone_no"),
                joined_date=item.get("created_at", utc_now()),
                status=item.get("status", "active")
            )
            for item in items
        ]
        return PaginatedResponse(items=user_items, total=total, limit=limit, offset=offset)

    async def get_user_by_id(self, user_id: str) -> UserListItem:
        item = await self.repository.db.users.find_one({"_id": ObjectId(user_id)})
        if not item:
            from app.core.exceptions import AppException
            raise AppException(status_code=404, code="USER_NOT_FOUND", message="User not found")
            
        return UserListItem(
            id=str(item["_id"]),
            full_name=item.get("full_name", "Unknown"),
            email=item.get("email", ""),
            phone_no=item.get("phone_no"),
            joined_date=item.get("created_at", utc_now()),
            status=item.get("status", "active")
        )

    async def toggle_user_status(self, user_id: str, status: str) -> bool:
        return await self.repository.update_user_status(user_id, status)

    async def get_earnings_summary(self, organization_id: str | None = None) -> EarningsSummary:
        stats = await self.repository.get_earnings_stats(organization_id)
        return EarningsSummary(
            today=stats["today"],
            this_month=stats["this_month"],
            total_revenue=stats["total"]
        )

    async def get_paginated_transactions(
        self, organization_id: str | None = None, limit: int = 10, offset: int = 0
    ) -> PaginatedResponse[TransactionListItem]:
        items, total = await self.repository.get_transactions_paginated(organization_id, limit, offset)
        trx_items = [
            TransactionListItem(
                id=str(item["_id"]),
                full_name=item.get("user_name", "Unknown User"),
                trx_id=item.get("transaction_id", f"#{str(item['_id'])[:8]}"),
                plan_name=item.get("plan_name", "Subscription"),
                price=item.get("total_amount", 0) / 100,
                date=item.get("created_at", utc_now()),
                status=item.get("status", "completed")
            )
            for item in items
        ]
        return PaginatedResponse(items=trx_items, total=total, limit=limit, offset=offset)

    async def get_transaction_details(self, trx_id: str) -> TransactionDetails:
        item = await self.repository.get_transaction_by_id(trx_id)
        if not item:
            from app.core.exceptions import AppException
            raise AppException(status_code=404, code="TRANSACTION_NOT_FOUND", message="Transaction not found")
        
        return TransactionDetails(
            transaction_id=item.get("transaction_id", str(item["_id"])),
            plan_name=item.get("plan_name", "Subscription"),
            date=item.get("created_at", utc_now()),
            user_name=item.get("user_name", "Unknown User"),
            account_number=item.get("account_number", "**** **** **** 000"),
            email=item.get("user_email", ""),
            amount=item.get("total_amount", 0) / 100
        )

    async def get_subscription_plans(self) -> list[SubscriptionPlan]:
        plans = await self.repository.get_plans()
        return [
            SubscriptionPlan(
                id=str(p["_id"]),
                name=p["name"],
                price=p["price"],
                interval=p["interval"],
                features=p["features"],
                is_active=p.get("is_active", True)
            ) for p in plans
        ]

    async def create_subscription_plan(self, data: SubscriptionPlanCreate) -> str:
        plan_dict = data.model_dump()
        plan_dict["is_active"] = True
        plan_dict["created_at"] = utc_now()
        return await self.repository.create_plan(plan_dict)

    async def handle_stripe_webhook(self, event: dict[str, Any]):
        """
        Processes Stripe webhook events.
        """
        event_type = event.get("type")
        if event_type == "checkout.session.completed":
            session = event.get("data", {}).get("object", {})
            await self.repository.process_stripe_payment(session)
        # Add other event types here if needed (e.g. subscription deleted)

    async def get_ai_monitoring_data(self, organization_id: str | None = None) -> AIStats:
        stats = await self.repository.get_ai_performance_stats(organization_id)
        return AIStats(
            total_requests=stats["total"],
            success_rate=stats["success_rate"],
            avg_response_time=stats["avg_time"],
            total_tokens_used=stats["total_tokens"],
            task_distribution=stats["task_distribution"],
            error_breakdown=stats["error_breakdown"],
            usage_trend=stats.get("usage_trend", [])
        )

    async def get_detailed_ai_logs(self, limit: int = 50) -> list[AILog]:
        logs = await self.repository.get_recent_ai_logs(limit)
        return [
            AILog(
                id=str(l["_id"]),
                user_id=l.get("user_id", "System"),
                action=l.get("action", "General AI Request"),
                status=l.get("status", "unknown"),
                tokens_used=l.get("tokens_used", 0),
                timestamp=l.get("timestamp", utc_now())
            ) for l in logs
        ]

    async def get_paginated_user_reports(
        self, limit: int = 10, offset: int = 0
    ) -> PaginatedResponse[UserReportListItem]:
        items, total = await self.repository.get_user_reports_paginated(limit, offset)
        report_items = [
            UserReportListItem(
                id=str(item["_id"]),
                report_from=item.get("report_from_name", "Anonymous"),
                report_from_image=item.get("report_from_image"),
                reason=item.get("reason", "No reason provided"),
                report_to=item.get("report_to_name", "Unknown"),
                report_to_image=item.get("report_to_image"),
                date_time=item.get("created_at", utc_now())
            )
            for item in items
        ]
        return PaginatedResponse(items=report_items, total=total, limit=limit, offset=offset)

    async def update_admin_profile(self, user_id: str, data: ProfileUpdateRequest) -> bool:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return True
        return await self.repository.update_user_profile(user_id, update_data)

    async def change_admin_password(self, user_id: str, data: ChangePasswordRequest) -> bool:
        from app.core.security import verify_password, hash_password
        from app.core.exceptions import AppException
        from bson import ObjectId
        
        user = await self.repository.db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not verify_password(data.current_password, user.get("hashed_password", "")):
            raise AppException(status_code=400, code="INVALID_PASSWORD", message="Current password is incorrect")
        
        new_hashed = hash_password(data.new_password)
        return await self.repository.update_user_password(user_id, new_hashed)

    async def forgot_password(self, email: str):
        import random
        from app.core.exceptions import AppException
        
        user = await self.repository.db.users.find_one({"email": email})
        if not user:
            raise AppException(status_code=404, code="USER_NOT_FOUND", message="Email not registered")
        
        otp = f"{random.randint(1000, 9999)}"
        await self.repository.save_otp(email, otp)
        # In production, call your email service here:
        # await self.email_service.send_otp(email, otp)
        print(f"DEBUG: OTP for {email} is {otp}") 

    async def verify_otp(self, data: VerifyOTPRequest) -> bool:
        return await self.repository.verify_otp(data.email, data.otp)

    async def reset_password(self, data: ResetPasswordRequest) -> bool:
        from app.core.security import hash_password
        from app.core.exceptions import AppException
        
        if not await self.repository.verify_otp(data.email, data.otp):
            raise AppException(status_code=400, code="INVALID_OTP", message="Invalid or expired OTP")
        
        user = await self.repository.db.users.find_one({"email": email})
        hashed = hash_password(data.new_password)
        return await self.repository.update_user_password(str(user["_id"]), hashed)

    async def get_settings_content(self, content_type: str) -> str:
        return await self.repository.get_settings_content(content_type)

    async def update_settings_content(self, data: SettingsContent) -> bool:
        return await self.repository.update_settings_content(data.type, data.content)

    async def get_conversations(self) -> list[ChatConversation]:
        chats = await self.repository.get_all_chats()
        return [ChatConversation(
            id=str(c["_id"]),
            user_name=c.get("user_name", "Unknown"),
            avatar_url=c.get("avatar_url"),
            last_message=c.get("last_message", ""),
            timestamp=c.get("last_timestamp", utc_now()),
            unread_count=c.get("unread_count", 0)
        ) for c in chats]

    async def get_chat_history(self, user_id: str, admin_id: str) -> list[ChatMessage]:
        messages = await self.repository.get_chat_messages(user_id)
        return [ChatMessage(
            id=str(m["_id"]),
            sender_id=str(m["sender_id"]),
            receiver_id=str(m["receiver_id"]),
            message=m.get("message"),
            image_url=m.get("image_url"),
            timestamp=m.get("timestamp", utc_now()),
            is_me=(str(m["sender_id"]) == admin_id)
        ) for m in messages]

    async def send_chat_message(self, admin_id: str, user_id: str, text: str | None = None, image_url: str | None = None):
        msg = {
            "sender_id": admin_id,
            "receiver_id": user_id,
            "message": text,
            "image_url": image_url,
            "timestamp": utc_now()
        }
        await self.repository.save_message(msg)
