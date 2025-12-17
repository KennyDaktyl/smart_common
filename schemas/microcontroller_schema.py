from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from enums.microcontroller import MicrocontrollerType
from schemas.base import APIModel, ORMModel


class MicrocontrollerBase(APIModel):
    """Shared fields for microcontroller payloads."""

    name: str = Field(..., description="Friendly microcontroller name")
    description: Optional[str] = Field(None, description="Optional description")
    software_version: Optional[str] = Field(None, description="Installed firmware version")
    max_devices: int = Field(1, ge=1, description="Maximum number of devices")
    enabled: bool = Field(True, description="Is the microcontroller active?")


class MicrocontrollerCreate(MicrocontrollerBase):
    installation_id: int = Field(..., description="Installation the controller belongs to")
    type: MicrocontrollerType = Field(..., description="Hardware type identifier")


class MicrocontrollerUpdate(APIModel):
    name: Optional[str] = None
    description: Optional[str] = None
    software_version: Optional[str] = None
    max_devices: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None


class MicrocontrollerOut(MicrocontrollerBase, ORMModel):
    id: int
    uuid: UUID
    installation_id: int
    type: MicrocontrollerType
    created_at: datetime
    updated_at: datetime


class MicrocontrollerList(ORMModel):
    microcontrollers: List[MicrocontrollerOut] = []
