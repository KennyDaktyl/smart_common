from __future__ import annotations

from typing import Any, Mapping

from smart_common.providers.adapters.factory import get_vendor_adapter_factory
from smart_common.providers.adapters.huawei import HuaweiProviderAdapter
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import WizardStep, WizardStepResult
from smart_common.providers.wizard.exceptions import WizardSessionStateError
from smart_common.providers.schemas.wizard.huawei import (
    HuaweiAuthForm,
    HuaweiStationForm,
    HuaweiDeviceSelectForm,
    HuaweiDetailsForm,
    HuaweiDetailsSummary,
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _resolve_adapter(session_data: Mapping[str, Any]) -> HuaweiProviderAdapter:
    credentials = session_data.get("credentials")
    if not credentials:
        raise WizardSessionStateError("Missing Huawei credentials in wizard session")

    username = credentials.get("username")
    if not isinstance(username, str):
        raise WizardSessionStateError("Missing username in wizard session credentials")

    overrides = session_data.get("adapter_overrides") or {}

    return get_vendor_adapter_factory().create(
        ProviderVendor.HUAWEI,
        credentials=credentials,
        cache_key=username,
        overrides=overrides,
    )


# ------------------------------------------------------------
# Step: AUTH
# ------------------------------------------------------------

class HuaweiAuthWizardStep(WizardStep):
    name = "auth"
    schema = HuaweiAuthForm

    def process(
        self,
        payload: HuaweiAuthForm,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        adapter = get_vendor_adapter_factory().create(
            ProviderVendor.HUAWEI,
            credentials={"username": payload.username, "password": payload.password},
            cache_key=payload.username,
        )

        stations = adapter.list_stations()
        options = {
            "stations": [
                {"value": s["station_code"], "label": s["name"]}
                for s in stations
            ]
        }

        return WizardStepResult(
            next_step="station",
            options=options,
            session_updates={
                "credentials": {
                    "username": payload.username,
                    "password": payload.password,
                }
            },
        )


# ------------------------------------------------------------
# Step: STATION
# ------------------------------------------------------------

class HuaweiStationWizardStep(WizardStep):
    name = "station"
    schema = HuaweiStationForm

    def process(
        self,
        payload: HuaweiStationForm,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        adapter = _resolve_adapter(session_data)
        devices = adapter.list_devices(payload.station_code)

        options = {
            "devices": [
                {"value": d["device_id"], "label": d["name"]}
                for d in devices
            ]
        }

        return WizardStepResult(
            next_step="device",
            options=options,
            session_updates={
                "station_code": payload.station_code,
                "devices": {d["device_id"]: d for d in devices},
            },
            context_updates={
                "station_code": payload.station_code,
            },
        )


# ------------------------------------------------------------
# Step: DEVICE (select + summary)
# ------------------------------------------------------------

class HuaweiDeviceWizardStep(WizardStep):
    name = "device"
    schema = HuaweiDeviceSelectForm

    def process(
        self,
        payload: HuaweiDeviceSelectForm,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        devices: dict[int, dict] = session_data.get("devices", {})
        device = devices.get(payload.device_id)

        if not device:
            raise WizardSessionStateError("Selected Huawei device not found")

        station_code = session_data.get("station_code")
        if not station_code:
            raise WizardSessionStateError("Missing station_code in session")

        details = HuaweiDetailsSummary(
            station_code=station_code,
            inverter_id=device["device_id"],
            name=device.get("name"),
            model=device.get("model"),
            inv_type=device.get("inv_type"),
            latitude=device.get("latitude"),
            longitude=device.get("longitude"),
            software_version=device.get("software_version"),
            optimizer_count=device.get("optimizer_count"),
        ).model_dump()

        return WizardStepResult(
            next_step="details",
            options=details,
            session_updates={
                "details": details,
            },
            context_updates={
                "station_code": station_code,
            },
        )


# ------------------------------------------------------------
# Step: DETAILS (editable form)
# ------------------------------------------------------------

class HuaweiDetailsWizardStep(WizardStep):
    name = "details"
    schema = HuaweiDetailsForm

    def process(
        self,
        payload: HuaweiDetailsForm,
        session_data: Mapping[str, Any],
    ) -> WizardStepResult:
        details = session_data.get("details")
        if not details:
            raise WizardSessionStateError("Missing Huawei details in wizard session")

        final_config = {
            **details,
            **payload.model_dump(),
        }

        return WizardStepResult(
            is_complete=True,
            final_config=final_config,
        )
