from __future__ import annotations

from typing import Any, Mapping

from smart_common.providers.adapters.factory import get_vendor_adapter_factory
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.schemas.wizard.goodwe import (
    GoodWeAuthStep,
    GoodWeDetailsForm,
    GoodWeDetailsSummary,
    GoodWePowerStationStep,
)
from smart_common.providers.wizard.base import WizardStep, WizardStepResult
from smart_common.providers.wizard.exceptions import WizardSessionStateError


class GoodWeAuthWizardStep(WizardStep):
    name = "auth"
    schema = GoodWeAuthStep

    def process(
        self,
        payload: GoodWeAuthStep,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        credentials = payload.model_dump()
        adapter = get_vendor_adapter_factory().create(
            ProviderVendor.GOODWE,
            credentials=credentials,
            cache_key=payload.username,
        )

        station_ids = adapter.get_powerstation_ids()
        options = {
            "powerstation_id": [
                {"value": station_id, "label": station_id} for station_id in station_ids
            ]
        }

        return WizardStepResult(
            next_step="powerstation",
            options=options,
            session_updates={"credentials": credentials},
        )


class GoodWePowerStationWizardStep(WizardStep):
    name = "powerstation"
    schema = GoodWePowerStationStep

    def process(
        self,
        payload: GoodWePowerStationStep,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        if "credentials" not in session_data:
            raise WizardSessionStateError("Missing credentials")

        credentials = session_data["credentials"]
        powerstation_id = payload.powerstation_id

        adapter = get_vendor_adapter_factory().create(
            ProviderVendor.GOODWE,
            credentials=credentials,
            cache_key=credentials["username"],
        )

        raw = adapter.get_powerstation_detail(powerstation_id)

        data = raw.get("data", {})
        info: dict[str, Any] = data.get("info", {})
        kpi: dict[str, Any] = data.get("kpi", {})

        details = GoodWeDetailsSummary(
            powerstation_id=powerstation_id,
            station_name=info.get("stationname"),
            address=info.get("address"),
            capacity_kw=info.get("capacity"),
            battery_capacity_kwh=info.get("battery_capacity"),
            powerstation_type=info.get("powerstation_type"),
            currency=kpi.get("currency"),
        ).model_dump()

        return WizardStepResult(
            next_step="details",
            options=details,
            session_updates={
                "powerstation_id": powerstation_id,
                "details": details,
            },
            context_updates={
                "powerstation_id": powerstation_id,
            },
        )


class GoodWeDetailsWizardStep(WizardStep):
    name = "details"
    schema = GoodWeDetailsForm

    def process(
        self,
        payload: GoodWeDetailsForm,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        details = session_data.get("details")
        if not details:
            raise WizardSessionStateError("Missing GoodWe details")

        final_config = {
            **details,
            **payload.model_dump(),
        }

        return WizardStepResult(
            is_complete=True,
            final_config=final_config,
        )
