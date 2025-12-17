from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from enums.user import UserRole
from schemas.base import APIModel, ORMModel


class UserBase(APIModel):
    email: EmailStr
    role: UserRole = Field(UserRole.CLIENT, description="Assigned user role")
    is_active: bool = Field(True, description="Active flag for the account")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plain-text password")


class UserUpdate(APIModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserOut(UserBase, ORMModel):
    id: int
    created_at: datetime


class UserList(ORMModel):
    users: List[UserOut] = []


class UserLogin(APIModel):
    email: EmailStr
    password: str


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
    new_password: str


class MessageResponse(APIModel):
    message: str
