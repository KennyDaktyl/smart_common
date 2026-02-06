from __future__ import annotations

import json
import logging

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from smart_common.enums.unit import PowerUnit
from smart_common.providers.adapters.utils import _parse_watt
from smart_common.schemas.normalized_measurement import NormalizedMeasurement
from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.exceptions import ProviderError, ProviderFetchError
from smart_common.providers.provider_config.goodwe import goodwe_integration_settings

logger = logging.getLogger(__name__)

EXTRA_ENERGY_GRID_STATUS = -1
IMPORT_ENERGY_GRID_STATUS = 1


class GoodWeProviderAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.GOODWE
    kind = ProviderKind.POWER

    SEMS_VER = "v2.1.0"

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------

    def __init__(self, username: str, password: str) -> None:
        super().__init__(
            base_url="https://www.semsportal.com",
            timeout=goodwe_integration_settings.GOODWE_TIMEOUT,
            max_retries=goodwe_integration_settings.GOODWE_MAX_RETRIES,
        )

        self.username = username
        self.password = password

        self._login_base_url = "https://www.semsportal.com"
        self._api_base_url: str | None = None

        self._logged_in = False
        self._token_ctx: dict[str, Any] | None = None

        self._external_id: str | None = None
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

    def get_current_export_power(self, power_station_id: str) -> Optional[float]:
        data = self._post(
            "/v2/PowerStation/GetPowerflow",
            {"PowerStationId": power_station_id},
        )

        if not isinstance(data, dict):
            return None

        powerflow = data.get("powerflow")
        if not isinstance(powerflow, dict):
            return None

        if not data.get("hasPowerflow", False):
            return None

        grid_w = _parse_watt(powerflow.get("grid"))
        load_status = powerflow.get("loadStatus")

        if load_status == EXTRA_ENERGY_GRID_STATUS:
            # eksport → wartość ujemna
            return float(grid_w)

        if load_status == IMPORT_ENERGY_GRID_STATUS:
            # pobór → wartość dodatnia
            return -float(grid_w)

        # status nieznany
        return None

    def get_current_power(self, device_id: str) -> Optional[float]:
        return self.get_current_export_power(device_id)

    def fetch_measurement(self) -> NormalizedMeasurement:
        if not self._external_id:
            self.get_powerstation_ids()

        value = self.get_current_power(self._external_id)

        return NormalizedMeasurement(
            provider_id=getattr(self, "provider_id", 0),
            value=value,
            unit=PowerUnit.WATT.value,
            measured_at=datetime.now(timezone.utc),
            metadata={"powerstation_id": self._external_id},
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
