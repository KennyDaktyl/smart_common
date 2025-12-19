from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict, EmailStr, Field

from smart_common.enums.user import UserRole
from smart_common.schemas.base import APIModel, ORMModel
from smart_common.schemas.installations import InstallationResponse
from smart_common.schemas.user_profile_schema import UserProfileResponse


# ------------------------------------------------------------------
# BASE
# ------------------------------------------------------------------

class UserBase(APIModel):
    email: EmailStr


# ------------------------------------------------------------------
# INPUT SCHEMAS
# ------------------------------------------------------------------

class UserCreate(UserBase):
    """
    Schema used ONLY for user registration.

    Security rules:
    - role is ALWAYS set server-side
    - is_active is ALWAYS False on creation
    """
    password: str = Field(..., min_length=8, description="Plain-text password")


class UserUpdate(APIModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class UserLogin(APIModel):
    email: EmailStr
    password: str


# ------------------------------------------------------------------
# OUTPUT SCHEMAS
# ------------------------------------------------------------------

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
    installations: List[InstallationResponse] = Field(
        default_factory=list,
        description="Installations owned by the user",
    )
    profile: Optional[UserProfileResponse] = None


class UserListQuery(APIModel):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class AdminUserUpdate(APIModel):
    """
    Admin-only update.
    """
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserUpdate(APIModel):
    """
    Update own profile (SELF).
    """
    email: Optional[EmailStr] = None
    
# ------------------------------------------------------------------
# AUTH / TOKENS
# ------------------------------------------------------------------

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
