# smart_common/schemas/user_schema.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict, EmailStr, Field

from smart_common.enums.user import UserRole
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.microcontroller_schema import MicrocontrollerResponse
from smart_common.schemas.provider_schema import ProviderResponse
from smart_common.schemas.user_profile_schema import UserProfileResponse

# ------------------------------------------------------------------
# BASE
# ------------------------------------------------------------------


class UserBase(APIModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plain-text password")


class UserLogin(APIModel):
    email: EmailStr
    password: str


class UserResponse(UserBase, ORMModel):
    id: int
    role: UserRole = Field(..., description="Assigned user role")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


class UserDetailsResponse(UserResponse):
    profile: Optional[UserProfileResponse] = None


class UserFullDetailsResponse(UserDetailsResponse):
    microcontrollers: Optional[List[MicrocontrollerResponse]] = None
    providers: Optional[List[ProviderResponse]] = None


class UserListQuery(APIModel):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    search: Optional[str] = Field(
        None,
        description="Global search (id, email, name, company, vat)",
        example="john",
    )


class AdminUserUpdate(APIModel):
    """
    Admin-only update.
    """

    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserSelfUpdate(APIModel):
    """
    Update own profile (SELF).
    """

    email: Optional[EmailStr] = None


class ChangePasswordRequest(APIModel):
    current_password: str = Field(
        ...,
        min_length=8,
        description="Existing password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password to replace the existing one",
    )


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class EmailTokenRequest(APIModel):
    token: str


class PasswordResetRequest(APIModel):
    email: EmailStr


class PasswordResetConfirm(APIModel):
    token: str
    new_password: str = Field(..., min_length=8)


class MessageResponse(APIModel):
    message: str


class AdminUserCreate(APIModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Plain-text password set by admin",
    )
    role: UserRole = Field(
        ...,
        description="Assigned user role",
    )
    is_active: bool = Field(
        True,
        description="Whether the account is active",
    )
