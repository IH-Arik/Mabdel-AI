from __future__ import annotations
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_mongo_database
from Dashboard.app.services.dashboard_service import DashboardService

def get_dashboard_service(db: AsyncIOMotorDatabase = Depends(get_mongo_database)) -> DashboardService:
    return DashboardService(db)
