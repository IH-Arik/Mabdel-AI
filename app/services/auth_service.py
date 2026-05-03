from __future__ import annotations

from datetime import timedelta

from starlette import status

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token_for_storage,
    verify_password,
)
from app.repositories.auth_repository import AuthRepository
from app.repositories.token_repository import TokenRepository
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendOTPRequest,
    TokenResponse,
    UserResponse,
    VerifyOTPRequest,
)
from app.services.otp_service import OTPService
from app.utils.helpers import serialize_mongo_document, utc_now


class AuthService:
    def __init__(self, auth_repository: AuthRepository, otp_service: OTPService, token_repository: TokenRepository) -> None:
        self.auth_repository = auth_repository
        self.otp_service = otp_service
        self.token_repository = token_repository

    async def register_user(self, payload: RegisterRequest) -> MessageResponse:
        existing_user = await self.auth_repository.get_user_by_email(payload.email)
        if existing_user:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email already exists.",
            )

        password_hash = hash_password(payload.password)
        await self.auth_repository.create_user(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=password_hash,
        )

        await self.otp_service.issue_otp(email=payload.email, purpose="signup")
        return MessageResponse(message="Registration successful. OTP sent to your email.")

    async def login_user(self, payload: LoginRequest) -> TokenResponse:
        user = await self.auth_repository.get_user_by_email(payload.email)
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
            )

        if not user.get("is_verified", False):
            raise AppException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="EMAIL_NOT_VERIFIED",
                message="Please verify your account before logging in.",
            )

        user_id = str(user["_id"])
        access_token = create_access_token(user_id=user_id, email=user["email"])
        refresh_token = create_refresh_token(user_id=user_id, email=user["email"])

        refresh_expires_at = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repository.create_refresh_token(
            user_id=user_id,
            token_hash=hash_token_for_storage(refresh_token),
            expires_at=refresh_expires_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=self._user_to_response(user),
        )

    async def send_otp(self, payload: SendOTPRequest) -> MessageResponse:
        user = await self.auth_repository.get_user_by_email(payload.email)

        if payload.purpose == "signup":
            if not user:
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code="USER_NOT_FOUND",
                    message="No user found for this email.",
                )
            if user.get("is_verified"):
                raise AppException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="USER_ALREADY_VERIFIED",
                    message="User is already verified.",
                )

        if payload.purpose == "forgot_password" and not user:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="USER_NOT_FOUND",
                message="No user found for this email.",
            )

        await self.otp_service.issue_otp(email=payload.email, purpose=payload.purpose)
        return MessageResponse(message="OTP sent successfully.")

    async def resend_otp(self, payload: SendOTPRequest) -> MessageResponse:
        return await self.send_otp(payload)

    async def verify_otp(self, payload: VerifyOTPRequest) -> MessageResponse:
        await self.otp_service.verify_otp(email=payload.email, purpose=payload.purpose, code=payload.code)

        if payload.purpose == "signup":
            await self.auth_repository.mark_user_verified(payload.email)
            return MessageResponse(message="Account verified successfully.")

        reset_token = create_password_reset_token(payload.email)
        return MessageResponse(message="OTP verified successfully.", reset_token=reset_token)

    async def forgot_password(self, payload: ForgotPasswordRequest) -> MessageResponse:
        user = await self.auth_repository.get_user_by_email(payload.email)
        if not user:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="USER_NOT_FOUND",
                message="No user found for this email.",
            )

        await self.otp_service.issue_otp(email=payload.email, purpose="forgot_password")
        return MessageResponse(message="Password reset OTP sent successfully.")

    async def reset_password(self, payload: ResetPasswordRequest) -> MessageResponse:
        claims = decode_token(payload.reset_token)
        if claims.get("type") != "password_reset":
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_RESET_TOKEN",
                message="Invalid reset token type.",
            )
        if claims.get("sub") != payload.email:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_RESET_TOKEN",
                message="Reset token does not match the email.",
            )

        user = await self.auth_repository.get_user_by_email(payload.email)
        if not user:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="USER_NOT_FOUND",
                message="No user found for this email.",
            )

        await self.auth_repository.update_user_password(
            email=payload.email,
            password_hash=hash_password(payload.new_password),
        )
        await self.token_repository.revoke_all_user_tokens(str(user["_id"]))
        return MessageResponse(message="Password updated successfully.")

    async def refresh_access_token(self, payload: RefreshTokenRequest) -> TokenResponse:
        claims = decode_token(payload.refresh_token)
        if claims.get("type") != "refresh":
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_REFRESH_TOKEN",
                message="Invalid refresh token type.",
            )

        stored_token = await self.token_repository.get_valid_refresh_token(
            hash_token_for_storage(payload.refresh_token)
        )
        if not stored_token:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_REFRESH_TOKEN",
                message="Refresh token is invalid or revoked.",
            )

        user_id = claims.get("sub")
        user = await self.auth_repository.get_user_by_id(user_id)
        if not user:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_REFRESH_TOKEN",
                message="User not found for refresh token.",
            )

        await self.token_repository.revoke_refresh_token(str(stored_token["_id"]))

        new_access = create_access_token(user_id=str(user["_id"]), email=user["email"])
        new_refresh = create_refresh_token(user_id=str(user["_id"]), email=user["email"])
        refresh_expires_at = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repository.create_refresh_token(
            user_id=str(user["_id"]),
            token_hash=hash_token_for_storage(new_refresh),
            expires_at=refresh_expires_at,
        )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            user=self._user_to_response(user),
        )

    async def google_login(self, _: GoogleLoginRequest) -> MessageResponse:
        # TODO: Validate Google ID token and create/login user by provider ID.
        raise AppException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            code="GOOGLE_LOGIN_NOT_IMPLEMENTED",
            message="Google login is not implemented yet.",
        )

    async def get_current_user(self, access_token: str) -> UserResponse:
        claims = decode_token(access_token)
        if claims.get("type") != "access":
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_ACCESS_TOKEN",
                message="Invalid access token type.",
            )

        user = await self.auth_repository.get_user_by_id(claims.get("sub", ""))
        if not user:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="USER_NOT_FOUND",
                message="User for this token no longer exists.",
            )
        return self._user_to_response(user)

    async def logout(self, access_token: str) -> MessageResponse:
        claims = decode_token(access_token)
        user_id = claims.get("sub", "")
        await self.token_repository.revoke_all_user_tokens(user_id)
        return MessageResponse(message="Logged out successfully.")

    @staticmethod
    def _user_to_response(user: dict) -> UserResponse:
        safe_user = serialize_mongo_document(user) or {}
        return UserResponse(
            id=safe_user["_id"],
            full_name=safe_user["full_name"],
            email=safe_user["email"],
            is_verified=bool(safe_user.get("is_verified", False)),
            auth_provider=safe_user.get("auth_provider", "email"),
            avatar_url=safe_user.get("avatar_url"),
            language_preference=safe_user.get("language_preference", "EN"),
            created_at=safe_user["created_at"],
        )
