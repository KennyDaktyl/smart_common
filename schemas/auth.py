from datetime import datetime

from pydantic import ConfigDict, EmailStr, Field

from smart_common.enums.user import UserRole
from smart_common.schemas.base import APIModel, ORMModel


class LoginRequest(APIModel):
    email: EmailStr = Field(
        ...,
        description="Email address assigned to the Smart Energy account",
        example="client@example.com",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password in plain text",
        example="S3curePassw0rd!",
    )


class RefreshTokenRequest(APIModel):
    refresh_token: str = Field(
        ...,
        description="Valid refresh token received during login",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )


class TokenResponse(APIModel):
    access_token: str = Field(
        ...,
        description="JWT access token for Authorization header",
        example="eyJraWQiOiIyMDIyMjA...",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token used to request new access tokens",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
    token_type: str = Field(
        "bearer",
        description="Token type prefix used in Authorization headers",
        example="bearer",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "access_token": "eyJleHAiOiIxNjQwMDAwMDAwIiwic3ViIjoiMSJ9",
                "refresh_token": "eyJleHAiOiIxNzQwMDAwMDAwIiwic3ViIjoiMSJ9",
                "token_type": "bearer",
            }
        },
    )


class CurrentUserResponse(ORMModel):
    id: int = Field(..., description="Internal user identifier", example=123)
    email: EmailStr = Field(
        ...,
        description="Email address associated with the account",
        example="client@example.com",
    )
    role: UserRole = Field(
        ...,
        description="Role assigned to the user",
        example=UserRole.CLIENT.value,
    )
    is_active: bool = Field(
        ...,
        description="Indicates whether the user has completed activation",
        example=True,
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp (UTC)",
        example="2024-01-01T12:00:00Z",
    )

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": 123,
                "email": "client@example.com",
                "role": UserRole.CLIENT.value,
                "is_active": True,
                "created_at": "2024-01-01T12:00:00Z",
            }
        },
    )


class EmailTokenRequest(APIModel):
    token: str = Field(
        ...,
        description="Action token received over email",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )


class PasswordResetRequest(APIModel):
    email: EmailStr = Field(
        ...,
        description="Email associated with the account that requires reset",
        example="client@example.com",
    )


class PasswordResetConfirm(APIModel):
    token: str = Field(
        ...,
        description="Password reset token issued via email",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password for the account",
        example="NewS3curePass!",
    )


class MessageResponse(APIModel):
    message: str = Field(..., example="Operation completed successfully")
    token: str | None = Field(
        None,
        description="Optional token returned when the operation produces one (e.g. password reset)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
