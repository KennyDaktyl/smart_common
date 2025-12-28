from __future__ import annotations

from smart_common.providers.adapters.factory import get_vendor_adapter_factory
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.schemas.wizard.goodwe import (
    GoodWeAuthStep,
    GoodWePowerStationStep,
    GoodWeFinalizeStep,
    GoodWeFinalSummary,
)
from smart_common.providers.wizard.base import WizardStep, WizardStepResult
from smart_common.providers.wizard.exceptions import WizardSessionStateError


# -------------------------------------------------
# STEP 1 – AUTH
# -------------------------------------------------
class GoodWeAuthWizardStep(WizardStep):
    name = "auth"
    schema = GoodWeAuthStep

    def process(self, payload, session_data):
        adapter = get_vendor_adapter_factory().create(
            ProviderVendor.GOODWE,
            credentials=payload.model_dump(),
            cache_key=payload.username,
        )

        # 🔥 TYLKO login + pobranie ID
        powerstation_id = adapter.get_powerstation_id()

        return WizardStepResult(
            next_step="powerstation",
            options={
                "powerstation_id": [
                    {
                        "value": powerstation_id,
                        "label": powerstation_id,
                    }
                ]
            },
            session_updates={
                "credentials": payload.model_dump(),
            },
        )


class GoodWePowerStationWizardStep(WizardStep):
    name = "powerstation"
    schema = GoodWePowerStationStep

    def process(self, payload, session_data):
        if "credentials" not in session_data:
            raise WizardSessionStateError("Missing credentials")

        return WizardStepResult(
            next_step="details",
            session_updates={
                "powerstation_id": payload.powerstation_id,
            },
            context_updates={
                "powerstation_id": payload.powerstation_id,
            },
        )


class GoodWeDetailsWizardStep(WizardStep):
    name = "details"
    schema = None  # 🔥 BRAK FORMULARZA

    def process(self, payload, session_data):
        credentials = session_data.get("credentials")
        powerstation_id = session_data.get("powerstation_id")

        if not credentials or not powerstation_id:
            raise WizardSessionStateError("Missing GoodWe session data")

        adapter = get_vendor_adapter_factory().create(
            ProviderVendor.GOODWE,
            credentials=credentials,
            cache_key=credentials["username"],
        )

        detail = adapter.get_powerstation_detail(powerstation_id)

        info = detail.get("info", {})
        kpi = detail.get("kpi", {})

        final_config = GoodWeFinalSummary(
            powerstation_id=info.get("powerstation_id"),
            station_name=info.get("stationname"),
            address=info.get("address"),
            capacity_kwp=info.get("capacity"),
            battery_capacity_kwh=info.get("battery_capacity"),
            powerstation_type=info.get("powerstation_type"),
            currency=kpi.get("currency"),
        ).model_dump()

        return WizardStepResult(
            is_complete=True,  # 🔥 KONIEC WIZARDA
            final_config=final_config,
        )


# -------------------------------------------------
# STEP 4 – FINALIZE (DUMMY – CONTRACT ONLY)
# -------------------------------------------------
class GoodWeFinalizeWizardStep(WizardStep):
    """
    Ten krok REALNIE się nie wykona, bo wizard kończy się w `details`.
    Zostaje tylko dla spójności kontraktu z resztą systemu.
    """

    name = "finalize"
    schema = GoodWeFinalizeStep

    def process(self, payload, session_data):
        raise WizardSessionStateError(
            "Finalize step should never be executed for GoodWe"
        )
