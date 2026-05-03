from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    full_name: str
    email: EmailStr
    password_hash: str
    is_verified: bool = False
    auth_provider: str = "email"
    created_at: datetime
    updated_at: datetime
