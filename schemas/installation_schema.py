from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from schemas.base import APIModel, ORMModel


class InstallationBase(APIModel):
    """Fields shared by installation create/update payloads."""

    name: str = Field(..., description="Name of the installation")
    station_code: str = Field(..., description="Unique station identifier")
    station_addr: Optional[str] = Field(None, description="Physical address")


class InstallationCreate(InstallationBase):
    user_id: int = Field(..., description="Owner user id")


class InstallationUpdate(APIModel):
    name: Optional[str] = None
    station_code: Optional[str] = None
    station_addr: Optional[str] = None


class InstallationOut(InstallationBase, ORMModel):
    id: int
    user_id: int


class InstallationList(ORMModel):
    installations: List[InstallationOut] = []
