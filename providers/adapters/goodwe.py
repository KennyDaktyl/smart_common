from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from smart_common.providers.adapters.base import BaseProviderAdapter
from smart_common.providers.enums import ProviderKind, ProviderType, ProviderVendor
from smart_common.providers.exceptions import ProviderError, ProviderFetchError
from smart_common.providers.provider_config.goodwe import goodwe_integration_settings

logger = logging.getLogger(__name__)


class GoodWeProviderAdapter(BaseProviderAdapter):
    provider_type = ProviderType.API
    vendor = ProviderVendor.GOODWE
    kind = ProviderKind.POWER

    SEMS_VER = "v2.1.0"

    def __init__(self, username: str, password: str) -> None:
        super().__init__(
            base_url="https://www.semsportal.com",
            timeout=goodwe_integration_settings.GOODWE_TIMEOUT,
            max_retries=goodwe_integration_settings.GOODWE_MAX_RETRIES,
        )
        self.username = username
        self.password = password

        self._logged_in: bool = False
        self._token_ctx: dict[str, Any] | None = None
        self._powerstation_id: str | None = None
        self._external_id: str | None = None
        self._powerstation_ids: list[str] | None = None

    # ------------------------------------------------------------------
    # PUBLIC API (used by wizard / services)
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """Public auth entrypoint"""
        self._authenticate()

    def get_powerstation_id(self) -> str:
        """
        Step 1 domain method:
        returns GoodWe PowerStationId for logged-in user
        """
        self._authenticate()

        if self._external_id:
            return self._external_id

        station_ids = self.get_powerstation_ids()
        if not station_ids:
            raise ProviderError(
                message="Missing PowerStation identifiers from GoodWe",
            )

        station_id = station_ids[0]
        self._external_id = station_id
        return station_id

    def get_powerstation_ids(self) -> list[str]:
        """Return all available PowerStation IDs for the user."""
        if self._powerstation_ids is not None:
            return self._powerstation_ids

        response = self._post(
            "/PowerStation/GetPowerStationIdByOwner",
            payload={},
        )

        ids = self._collect_powerstation_ids(response)

        if not ids:
            raise ProviderError(
                message="GoodWe returned no PowerStation identifiers",
                details={"data": response},
            )

        unique_ids = list(dict.fromkeys(ids))
        self._powerstation_ids = unique_ids
        self._external_id = unique_ids[0]

        return unique_ids

    def get_powerstation_detail(self, powerstation_id: str) -> dict[str, Any]:
        if not self._token_ctx:
            raise ProviderError(message="GoodWe adapter not authenticated")

        headers = {
            "Content-Type": "application/json",
            "Token": json.dumps(
                {
                    "uid": self._token_ctx["uid"],
                    "timestamp": self._token_ctx["timestamp"],
                    "token": self._token_ctx["token"],
                    "client": "web",
                    "version": "v2.1.0",
                    "language": "zh_CN",
                },
                separators=(",", ":"),
            ),
            "User-Agent": "PostmanRuntime/7.51.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        payload = {"PowerStationId": powerstation_id}
        import requests

        response = requests.post(
            "https://eu.semsportal.com/api/v3/PowerStation/GetPlantDetailByPowerstationId",
            headers=headers,
            json=payload,
            timeout=10,
        )

        logger.info("GoodWe RAW status=%s", response.status_code)
        logger.info("GoodWe RAW response=%s", response.text)

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ProviderError(
                message="Invalid plant detail payload from GoodWe",
                details={"response": data},
            )

        return data

    def get_current_power(self, power_station_id: str) -> float:
        """
        Current power in **W**
        """

        if not self._token_ctx:
            self._authenticate()

        headers = {
            "Content-Type": "application/json",
            "Token": json.dumps(
                {
                    "uid": self._token_ctx["uid"],
                    "timestamp": self._token_ctx["timestamp"],
                    "token": self._token_ctx["token"],
                    "client": "web",
                    "version": "v2.1.0",
                    "language": "zh_CN",
                },
                separators=(",", ":"),
            ),
            "User-Agent": "PostmanRuntime/7.51.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        data = self._post(
            "/api/v2/PowerStation/GetPowerflow",
            headers=headers,
            payload={"PowerStationId": power_station_id},
        )

        powerflow = data.get("powerflow")
        if not powerflow:
            raise ProviderError(message="Missing powerflow data in GoodWe GetPowerflow")

        power_str = powerflow.get("pv")
        if power_str is None:
            raise ProviderError(message="Missing power value in GoodWe GetPowerflow")

        power = power_str.replace("W", "0")
        return float(power)

    # ------------------------------------------------------------------
    # REQUIRED BY BASE
    # ------------------------------------------------------------------

    def list_stations(self) -> list[Mapping[str, Any]]:
        return [
            {
                "station_id": station_id,
                "external_id": station_id,
            }
            for station_id in self.get_powerstation_ids()
        ]

    def list_devices(self, station_code: str) -> list[Mapping[str, Any]]:
        return [
            {
                "device_id": station_code,
                "external_id": station_code,
            }
        ]

    def _collect_powerstation_ids(self, payload: Any) -> list[str]:
        ids: list[str] = []

        if isinstance(payload, str):
            ids.append(payload)
            return ids

        if isinstance(payload, Mapping):
            for key, value in payload.items():
                key_lower = key.lower()
                if "powerstation" in key_lower and "id" in key_lower:
                    if isinstance(value, str):
                        ids.append(value)
                        continue
                    if isinstance(value, list):
                        for entry in value:
                            ids.extend(self._collect_powerstation_ids(entry))
                        continue
                    if isinstance(value, Mapping):
                        ids.extend(self._collect_powerstation_ids(value))
                        continue
                if isinstance(value, (Mapping, list)):
                    ids.extend(self._collect_powerstation_ids(value))
        elif isinstance(payload, list):
            for entry in payload:
                ids.extend(self._collect_powerstation_ids(entry))

        return ids

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        if self._logged_in:
            return

        response = self._request(
            "POST",
            "/api/v2/Common/CrossLogin",
            json_data={
                "account": self.username,
                "pwd": self.password,
                "agreement_agreement": 0,
                "is_local": False,
            },
            headers={
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
            },
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderFetchError(
                "Invalid JSON from GoodWe login",
                details={"body": response.text},
            ) from exc

        if payload.get("code") != 0:
            raise ProviderError(
                message=payload.get("msg", "GoodWe login failed"),
                details={"response": payload},
            )

        data = payload["data"]

        api_base = payload.get("api")
        if not api_base:
            raise ProviderError(message="Missing API base URL from GoodWe")

        self.base_url = api_base.rstrip("/")

        self._token_ctx = {
            "uid": data["uid"],
            "timestamp": data["timestamp"],
            "token": data["token"],
            "client": "web",
            "language": data.get("language", "zh_CN"),
            "ver": self.SEMS_VER,
        }

        self._logged_in = True
        logger.info("[GOODWE LOGIN OK] uid=%s", data["uid"])

    def _token_header(self) -> str:
        if not self._token_ctx:
            raise ProviderError(message="GoodWe adapter not authenticated")
        return json.dumps(self._token_ctx, separators=(",", ":"))

    def _post(self, path: str, payload: Mapping[str, Any]) -> Any:
        self._authenticate()

        body = dict(payload)

        if path.startswith("/api/v2") or path.startswith("/PowerStation"):
            body["ver"] = self.SEMS_VER

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

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderFetchError(
                message="Invalid JSON from GoodWe API",
                details={"body": response.text},
            ) from exc

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
