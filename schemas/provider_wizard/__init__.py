from __future__ import annotations

from pydantic import Field

from smart_common.providers.enums import ProviderVendor
from smart_common.schemas.base import APIModel


class WizardRuntimeResponse(APIModel):
    vendor: ProviderVendor
    step: str | None
    schema_definition: dict | None = Field(alias="schema")
    options: dict
    context: dict
    is_complete: bool
    final_config: dict | None = None
