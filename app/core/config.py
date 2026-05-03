from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    APP_NAME: str = "Mabdel Backend API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    TRUSTED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = 20
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    PUBLIC_BACKEND_URL: str = "http://127.0.0.1:8000"

    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "mabdel_db"
    DATABASE_URL: str | None = None
    MONGODB_CONNECT_TIMEOUT_MS: int = 5000

    SECRET_KEY: str = "change-this-in-production"
    OAUTH_TOKEN_ENCRYPTION_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 10
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OAUTH_STATE_EXPIRE_MINUTES: int = 10

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str | None = None
    META_CLIENT_ID: str | None = None
    META_CLIENT_SECRET: str | None = None
    META_REDIRECT_URI: str | None = None
    LINKEDIN_CLIENT_ID: str | None = None
    LINKEDIN_CLIENT_SECRET: str | None = None
    LINKEDIN_REDIRECT_URI: str | None = None
    TWITTER_CLIENT_ID: str | None = None
    TWITTER_CLIENT_SECRET: str | None = None
    TWITTER_REDIRECT_URI: str | None = None
    WEBHOOK_SHARED_SECRET: str | None = None
    META_WEBHOOK_VERIFY_TOKEN: str | None = None
    FCM_SERVER_KEY: str | None = None
    PUSH_DELIVERY_SYNC: bool = True

    RESEND_API_KEY: str | None = None
    MAILTRAP_API_TOKEN: str | None = None
    MAIL_FROM: str = "hello@demomailtrap.co"
    MAIL_FROM_NAME: str = "Mabdel AI"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True

    OTP_EXPIRE_MINUTES: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5
    OTP_LENGTH: int = 4

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped[1:-1]
            return [origin.strip().strip('"').strip("'") for origin in stripped.split(",") if origin.strip()]
        return ["*"]

    @field_validator("TRUSTED_HOSTS", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped[1:-1]
            return [host.strip().strip('"').strip("'") for host in stripped.split(",") if host.strip()]
        return ["*"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return False

    @field_validator("SMTP_USE_TLS", mode="before")
    @classmethod
    def parse_smtp_tls_value(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return True

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str, info: ValidationInfo) -> str:
        environment = str(info.data.get("ENVIRONMENT", "development")).lower()
        if environment != "development" and value == "change-this-in-production":
            raise ValueError("SECRET_KEY must be changed outside development environment.")
        return value

    @field_validator("OAUTH_TOKEN_ENCRYPTION_KEY")
    @classmethod
    def validate_oauth_encryption_key(cls, value: str | None, info: ValidationInfo) -> str | None:
        environment = str(info.data.get("ENVIRONMENT", "development")).lower()
        if environment != "development" and not value:
            raise ValueError("OAUTH_TOKEN_ENCRYPTION_KEY must be set outside development environment.")
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: list[str], info: ValidationInfo) -> list[str]:
        environment = str(info.data.get("ENVIRONMENT", "development")).lower()
        if environment != "development" and "*" in value:
            raise ValueError("Wildcard CORS origins are not allowed outside development environment.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
