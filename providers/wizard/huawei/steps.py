from __future__ import annotations

from typing import Any, Mapping

from smart_common.providers.adapters.factory import get_vendor_adapter_factory
from smart_common.providers.adapters.huawei import HuaweiProviderAdapter
from smart_common.providers.enums import ProviderVendor
from smart_common.providers.wizard.base import WizardStep, WizardStepResult
from smart_common.providers.wizard.exceptions import WizardSessionStateError
from smart_common.providers.schemas.wizard.huawei import (
    HuaweiAuthStep as HuaweiAuthStepSchema,
    HuaweiDeviceStep as HuaweiDeviceStepSchema,
    HuaweiStationStep as HuaweiStationStepSchema,
)


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


class HuaweiAuthWizardStep(WizardStep):
    name = "auth"
    schema = HuaweiAuthStepSchema

    def process(
        self,
        payload: HuaweiAuthStepSchema,
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
                {"value": station["station_code"], "label": station["name"]}
                for station in stations
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


class HuaweiStationWizardStep(WizardStep):
    name = "station"
    schema = HuaweiStationStepSchema

    def process(self, payload, session_data):
        adapter = _resolve_adapter(session_data)
        devices = adapter.list_devices(payload.station_code)

        options = {
            "devices": [{"value": d["device_id"], "label": d["name"]} for d in devices]
        }

        return WizardStepResult(
            next_step="device",
            options=options,
            session_updates={
                "station_code": payload.station_code,
                "devices": {d["device_id"]: d for d in devices},  # 🔥
            },
            context_updates={"station_code": payload.station_code},
        )


class HuaweiDeviceWizardStep(WizardStep):
    name = "device"
    schema = HuaweiDeviceStepSchema

    def process(self, payload, session_data):
        devices: dict = session_data.get("devices", {})
        device = devices.get(payload.device_id)

        if not device:
            raise WizardSessionStateError("Selected Huawei device not found in session")

        station_code = session_data.get("station_code")
        if not station_code:
            raise WizardSessionStateError("Missing station_code")

        final_config = {
            "station_code": station_code,
            "inverter_id": device["device_id"],
            "name": device["name"],
            "model": device.get("model"),
            "inv_type": device.get("inv_type"),
            "latitude": device.get("latitude"),
            "longitude": device.get("longitude"),
            "software_version": device.get("software_version"),
            "optimizer_count": device.get("optimizer_count"),
            "max_power_kw": 10.0,
            "min_power_kw": 0.0,
        }

        return WizardStepResult(
            is_complete=True,
            final_config=final_config,
            session_updates={"device_id": device["device_id"]},
        )
