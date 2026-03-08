from __future__ import annotations

from typing import Optional

from pydantic import Field

from smart_common.schemas.base import APIModel, ORMModel


class UserProfileBase(APIModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=32)

    company_name: Optional[str] = Field(None, max_length=255)
    company_vat: Optional[str] = Field(None, max_length=64)
    company_address: Optional[str] = Field(None, max_length=512)
    energy_price_amount: Optional[float] = Field(None, gt=0)
    energy_price_currency: Optional[str] = Field(None, max_length=8)
    energy_price_unit: Optional[str] = Field(None, max_length=16)


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase, ORMModel):
    id: int

    model_config = {
        "from_attributes": True,
        "extra": "forbid",
    }
