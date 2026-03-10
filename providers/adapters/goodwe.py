from __future__ import annotations

import json
import logging

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from smart_common.enums.unit import PowerUnit
from smart_common.enums.provider_telemetry import (
    ProviderTelemetryCapability,
    TelemetryAggregationMode,
    TelemetryChartType,
)
from smart_common.schemas.normalized_measurement import (
    NormalizedMeasurement,
    NormalizedMetric,
)
from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.enums import (
    ProviderKind,
    ProviderPowerSource,
    ProviderType,
    ProviderVendor,
)
from smart_common.providers.exceptions import ProviderError, ProviderFetchError
from smart_common.providers.provider_config.goodwe import goodwe_integration_settings

logger = logging.getLogger(__name__)

EXTRA_ENERGY_GRID_STATUS = -1
IMPORT_ENERGY_GRID_STATUS = 1
BATTERY_SOC_METRIC_KEY = "battery_soc"
GRID_POWER_METRIC_KEY = "grid_power"


class GoodWeProviderAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.GOODWE
    kind = ProviderKind.POWER

    SEMS_VER = "v2.1.0"

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------

    def __init__(
        self,
        username: str,
        password: str,
        *,
        provider_id: int,
        provider_external_id: str,
        provider_power_source: ProviderPowerSource,
        provider_has_power_meter: bool = False,
        provider_has_energy_storage: bool = False,
    ) -> None:
        super().__init__(
            base_url="https://www.semsportal.com",
            timeout=goodwe_integration_settings.GOODWE_TIMEOUT,
            max_retries=goodwe_integration_settings.GOODWE_MAX_RETRIES,
        )

        self.username = username
        self.password = password
        self.provider_id = provider_id
        self.provider_external_id = provider_external_id
        self.provider_power_source = provider_power_source
        self.provider_has_power_meter = provider_has_power_meter
        self.provider_has_energy_storage = provider_has_energy_storage

        self._login_base_url = "https://www.semsportal.com"
        self._api_base_url: str | None = None

        self._logged_in = False
        self._token_ctx: dict[str, Any] | None = None

        self._external_id: str | None = provider_external_id
        self._powerstation_ids: list[str] | None = None

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        self._authenticate()

    def _authenticate(self) -> None:

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0",
            "Token": json.dumps(
                {
                    "client": "web",
                    "language": "zh_CN",
                    "version": self.SEMS_VER,
                },
                separators=(",", ":"),
            ),
        }

        body = {
            "account": self.username,
            "pwd": self.password,
        }

        old_base_url = self.base_url
        try:
            self.base_url = self._login_base_url
            response = self._request(
                "POST",
                "/api/v2/Common/CrossLogin",
                json_data=body,
                headers=headers,
            )
        finally:
            self.base_url = old_base_url

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderFetchError(
                message="Invalid JSON from GoodWe login",
                details={"body": response.text},
            ) from exc

        if payload.get("code") != 0:
            raise ProviderError(
                message=payload.get("msg", "GoodWe login failed"),
                details={"response": payload},
            )

        data = payload.get("data")
        api_base = payload.get("api")

        if not isinstance(data, dict) or not api_base:
            raise ProviderError(
                message="Incomplete login payload from GoodWe",
                details={"response": payload},
            )

        self._api_base_url = api_base.rstrip("/")
        self.base_url = self._api_base_url

        self._token_ctx = {
            "uid": data["uid"],
            "timestamp": data["timestamp"],
            "token": data["token"],
            "client": "web",
            "language": data.get("language", "zh_CN"),
            "ver": self.SEMS_VER,
        }

        self._logged_in = True

        logger.info("[GOODWE LOGIN OK]", extra={"uid": data["uid"]})

    # ------------------------------------------------------------------
    # TOKEN
    # ------------------------------------------------------------------

    def _token_header(self) -> str:
        if not self._token_ctx:
            raise ProviderError(message="GoodWe adapter not authenticated")

        return json.dumps(self._token_ctx, separators=(",", ":"))

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: Mapping[str, Any]) -> Any:
        self._authenticate()

        if not self._api_base_url:
            raise ProviderError(message="GoodWe API base URL not set")

        body = dict(payload)

        response = self._request(
            "POST",
            path,
            json_data=body,
            headers={
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0",
                "Token": self._token_header(),
            },
        )

        data = response.json()
        if data.get("code") not in (0, "0", None):
            raise ProviderError(
                message=data.get("msg", "GoodWe API error"),
                details={
                    "code": data.get("code"),
                    "response": data,
                    "path": path,
                },
            )

        return data.get("data")

    # ------------------------------------------------------------------
    # DOMAIN
    # ------------------------------------------------------------------

    def get_powerstation_ids(self) -> list[str]:
        if self._powerstation_ids is not None:
            return self._powerstation_ids

        data = self._post(
            "/PowerStation/GetPowerStationIdByOwner",
            {},
        )

        ids = self._collect_powerstation_ids(data)
        if not ids:
            raise ProviderError(
                message="No PowerStation IDs returned by GoodWe",
                details={"data": data},
            )

        self._powerstation_ids = list(dict.fromkeys(ids))
        self._external_id = self._powerstation_ids[0]
        return self._powerstation_ids

    def _get_powerflow_payload(self, power_station_id: str) -> Mapping[str, Any] | None:
        snapshot = self._get_powerflow_snapshot(power_station_id)
        if snapshot is None:
            return None

        powerflow = snapshot.get("powerflow")
        if not isinstance(powerflow, Mapping):
            return None

        return powerflow

    def _get_powerflow_snapshot(self, power_station_id: str) -> Mapping[str, Any] | None:
        data = self._post(
            "/v2/PowerStation/GetPowerflow",
            {"PowerStationId": power_station_id},
        )

        if not isinstance(data, dict):
            return None

        if not data.get("hasPowerflow", False):
            return None

        powerflow = data.get("powerflow")
        if not isinstance(powerflow, dict):
            return None

        return data

    @staticmethod
    def _resolve_power_source(
        power_source_hint: ProviderPowerSource,
    ) -> ProviderPowerSource:
        if isinstance(power_source_hint, ProviderPowerSource):
            return power_source_hint
        raise ProviderError("Provider power_source not configured")

    @staticmethod
    def _safe_watt(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None

            if cleaned.endswith("W"):
                cleaned = cleaned[:-1].strip()

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    @classmethod
    def _prune_none(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            cleaned: dict[str, Any] = {}
            for key, nested_value in value.items():
                pruned_value = cls._prune_none(nested_value)
                if pruned_value is not None:
                    cleaned[str(key)] = pruned_value
            return cleaned or None

        if isinstance(value, list):
            cleaned_list = [cls._prune_none(item) for item in value]
            compacted = [item for item in cleaned_list if item is not None]
            return compacted or None

        return value

    def _build_metadata(
        self,
        snapshot: Mapping[str, Any],
        *,
        power_station_id: str,
    ) -> dict[str, Any]:
        powerflow = snapshot.get("powerflow")
        powerflow_map: Mapping[str, Any] = (
            powerflow if isinstance(powerflow, Mapping) else {}
        )

        extra_data: dict[str, Any] = {
            "powerstation_id": power_station_id,
            "flags": {
                "has_genset": snapshot.get("hasGenset"),
                "has_micro_grid": snapshot.get("hasMicroGrid"),
                "has_more_inverter": snapshot.get("hasMoreInverter"),
                "has_powerflow": snapshot.get("hasPowerflow"),
                "has_grid_load": snapshot.get("hasGridLoad"),
                "is_stored": snapshot.get("isStored"),
                "is_parallel_inverters": snapshot.get("isParallelInventers"),
                "is_mixed_parallel_inverters": snapshot.get(
                    "isMixedParallelInventers"
                ),
                "is_ev_charge": snapshot.get("isEvCharge"),
                "is_third_party_ems": snapshot.get("is3rdEms"),
            },
            "powerflow": {
                "pv_w": self._safe_watt(powerflow_map.get("pv")),
                "grid_w": self._safe_watt(powerflow_map.get("grid")),
                "load_w": self._safe_watt(powerflow_map.get("load")),
                "battery_w": self._safe_watt(powerflow_map.get("bettery")),
                "genset_w": self._safe_watt(powerflow_map.get("genset")),
                "micro_grid_w": self._safe_watt(powerflow_map.get("microGrid")),
                "soc": powerflow_map.get("soc"),
                "soc_text": powerflow_map.get("socText"),
                "status": {
                    "pv": powerflow_map.get("pvStatus"),
                    "battery": powerflow_map.get("betteryStatus"),
                    "battery_text": powerflow_map.get("betteryStatusStr"),
                    "load": powerflow_map.get("loadStatus"),
                    "grid": powerflow_map.get("gridStatus"),
                    "genset": powerflow_map.get("gensetStatus"),
                    "grid_genset": powerflow_map.get("gridGensetStatus"),
                    "micro_grid": powerflow_map.get("microGridStatus"),
                },
                "has_equipment": powerflow_map.get("hasEquipment"),
                "is_homekit": powerflow_map.get("isHomKit"),
                "is_bpu_inverter_no_battery": powerflow_map.get(
                    "isBpuAndInverterNoBattery"
                ),
                "is_multi_battery": powerflow_map.get("isMoreBettery"),
            },
        }

        ev_charge = snapshot.get("evCharge")
        if isinstance(ev_charge, Mapping):
            extra_data["ev_charge"] = dict(ev_charge)

        cleaned = self._prune_none(extra_data)
        if isinstance(cleaned, Mapping):
            return dict(cleaned)

        return {"powerstation_id": power_station_id}

    @staticmethod
    def _extract_signed_grid_power(powerflow: Mapping[str, Any]) -> Optional[float]:
        grid_w = GoodWeProviderAdapter._safe_watt(powerflow.get("grid"))
        if grid_w is None:
            return None

        load_status = powerflow.get("loadStatus")

        if load_status == EXTRA_ENERGY_GRID_STATUS:
            # eksport do sieci -> wartość dodatnia
            return float(grid_w)

        if load_status == IMPORT_ENERGY_GRID_STATUS:
            # pobór z sieci -> wartość ujemna
            return -float(grid_w)

        return None

    @staticmethod
    def _extract_pv_power(powerflow: Mapping[str, Any]) -> Optional[float]:
        pv_w = GoodWeProviderAdapter._safe_watt(powerflow.get("pv"))
        if pv_w is None:
            return None
        return float(pv_w)

    def _build_extra_metrics(
        self,
        powerflow: Mapping[str, Any],
    ) -> list[NormalizedMetric]:
        metrics: list[NormalizedMetric] = []

        battery_soc = self._safe_watt(powerflow.get("soc"))
        if self.provider_has_energy_storage and battery_soc is not None:
            metrics.append(
                NormalizedMetric(
                    key=BATTERY_SOC_METRIC_KEY,
                    value=battery_soc,
                    unit=PowerUnit.PERCENT.value,
                    label="Battery SOC",
                    chart_type=TelemetryChartType.LINE,
                    aggregation_mode=TelemetryAggregationMode.RAW,
                    capability_tag=ProviderTelemetryCapability.ENERGY_STORAGE,
                )
            )

        grid_power = self._extract_signed_grid_power(powerflow)
        if self.provider_has_power_meter and grid_power is not None:
            metrics.append(
                NormalizedMetric(
                    key=GRID_POWER_METRIC_KEY,
                    value=grid_power,
                    unit=PowerUnit.WATT.value,
                    label="Grid power",
                    chart_type=TelemetryChartType.BAR,
                    aggregation_mode=TelemetryAggregationMode.HOURLY_INTEGRAL,
                    capability_tag=ProviderTelemetryCapability.POWER_METER,
                )
            )

        return metrics

    def get_current_export_power(self, power_station_id: str) -> Optional[float]:
        powerflow = self._get_powerflow_payload(power_station_id)
        if powerflow is None:
            return None
        return self._extract_signed_grid_power(powerflow)

    def get_current_power_by_provider_type(
        self,
        power_station_id: str,
        *,
        power_source: ProviderPowerSource,
    ) -> Optional[float]:
        powerflow = self._get_powerflow_payload(power_station_id)
        if powerflow is None:
            return None

        resolved_power_source = self._resolve_power_source(power_source)
        if resolved_power_source == ProviderPowerSource.INVERTER:
            return self._extract_pv_power(powerflow)

        return self._extract_signed_grid_power(powerflow)

    def get_current_power(self, device_id: str) -> Optional[float]:
        return self.get_current_power_by_provider_type(
            device_id,
            power_source=self.provider_power_source,
        )

    def fetch_measurement(self) -> NormalizedMeasurement:
        if not self._external_id:
            self.get_powerstation_ids()

        snapshot = self._get_powerflow_snapshot(self._external_id)
        if snapshot is None:
            raise ProviderError(
                message="GoodWe powerflow snapshot unavailable",
                details={"powerstation_id": self._external_id},
            )

        powerflow = snapshot.get("powerflow")
        powerflow_map: Mapping[str, Any] = (
            powerflow if isinstance(powerflow, Mapping) else {}
        )

        resolved_power_source = self._resolve_power_source(self.provider_power_source)

        logger.info(
            "GoodWe resolved power source",
            extra={"power_source": self.provider_power_source.value},
        )

        if resolved_power_source == ProviderPowerSource.INVERTER:
            value = self._extract_pv_power(powerflow_map)
            measurement_source = "pv"
        else:
            value = self._extract_signed_grid_power(powerflow_map)
            measurement_source = "grid"

        if value is None:
            raise ProviderError(
                message="GoodWe power value missing for selected source",
                details={
                    "powerstation_id": self._external_id,
                    "power_source": resolved_power_source.value,
                },
            )

        metadata = self._build_metadata(
            snapshot,
            power_station_id=self._external_id,
        )
        metadata["measurement_source"] = measurement_source
        metadata["power_source"] = resolved_power_source.value

        logger.info(
            "GoodWe measurement source selected",
            extra={
                "powerstation_id": self._external_id,
                "power_source": resolved_power_source.value,
                "value": value,
                "metadata_keys": sorted(metadata.keys()),
            },
        )

        return NormalizedMeasurement(
            provider_id=self.provider_id,
            value=value,
            unit=PowerUnit.WATT.value,
            measured_at=datetime.now(timezone.utc),
            metadata=metadata,
            extra_metrics=self._build_extra_metrics(powerflow_map),
        )

    # ------------------------------------------------------------------
    # REQUIRED BY BASE
    # ------------------------------------------------------------------

    def list_stations(self) -> list[Mapping[str, Any]]:
        return [
            {"station_id": sid, "external_id": sid}
            for sid in self.get_powerstation_ids()
        ]

    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        return [{"device_id": station_code, "external_id": station_code}]

    # ------------------------------------------------------------------
    # UTILS
    # ------------------------------------------------------------------

    def _collect_powerstation_ids(self, payload: Any) -> list[str]:
        ids: list[str] = []

        if isinstance(payload, str):
            return [payload]

        if isinstance(payload, Mapping):
            for k, v in payload.items():
                if "powerstation" in k.lower() and "id" in k.lower():
                    if isinstance(v, str):
                        ids.append(v)
                    elif isinstance(v, (list, Mapping)):
                        ids.extend(self._collect_powerstation_ids(v))
                elif isinstance(v, (list, Mapping)):
                    ids.extend(self._collect_powerstation_ids(v))

        elif isinstance(payload, list):
            for item in payload:
                ids.extend(self._collect_powerstation_ids(item))

        return ids
