import logging
from typing import Callable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from smart_common.models.microcontroller import Microcontroller
from smart_common.models.provider import Provider, ProviderCredential
from smart_common.providers.enums import ProviderType, ProviderVendor

# ---- provider config schemas ----
from smart_common.repositories.microcontroller import MicrocontrollerRepository
from smart_common.repositories.provider import ProviderRepository
from smart_common.core.security import encrypt_secret
from smart_common.repositories.provider_credentials import ProviderCredentialRepository
from smart_common.providers.registry import PROVIDER_DEFINITIONS, resolve_sensor_type


class ProviderService:
    def __init__(
        self,
        provider_repo_factory: Callable[[Session], ProviderRepository],
        microcontroller_repo_factory: Optional[
            Callable[[Session], MicrocontrollerRepository]
        ],
    ):
        self._provider_repo_factory = provider_repo_factory
        self._microcontroller_repo_factory = microcontroller_repo_factory
        self.logger = logging.getLogger(__name__)

    # ---------- repositories ----------

    def _repo(self, db: Session) -> ProviderRepository:
        return self._provider_repo_factory(db)

    def _microcontroller_repo(self, db: Session) -> MicrocontrollerRepository:
        if not self._microcontroller_repo_factory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Microcontroller repository is not configured",
            )
        return self._microcontroller_repo_factory(db)

    # ---------- guards ----------

    def _ensure_microcontroller(
        self, db: Session, user_id: int, mc_uuid: UUID
    ) -> Microcontroller:
        microcontroller = self._microcontroller_repo(db).get_for_user_by_uuid(
            mc_uuid, user_id
        )
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )
        return microcontroller

    def _ensure_provider(self, db: Session, user_id: int, provider_id: int) -> Provider:
        provider = self._repo(db).get_for_user(provider_id, user_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        return provider

    def _ensure_provider_by_uuid(
        self,
        db: Session,
        user_id: int,
        provider_uuid: UUID,
    ) -> Provider:
        provider = self._repo(db).get_for_user_by_uuid(provider_uuid, user_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        return provider

    def _ensure_provider_for_microcontroller(
        self,
        db: Session,
        user_id: int,
        provider_id: int,
        microcontroller_id: int,
    ) -> Provider:
        provider = self._ensure_provider(db, user_id, provider_id)
        if provider.microcontroller_id != microcontroller_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found",
            )
        return provider

    # ---------- CONFIG VALIDATION (TU JEST KLUCZ) ----------

    def _resolve_vendor(self, vendor: ProviderVendor | str | None) -> ProviderVendor:
        if vendor is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider vendor is required",
            )

        try:
            return ProviderVendor(vendor)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid provider vendor: {vendor}",
            )

    def _resolve_definition(self, vendor: ProviderVendor) -> dict:
        meta = PROVIDER_DEFINITIONS.get(vendor)
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported provider vendor: {vendor.value}",
            )
        return meta

    def _validate_config(self, meta: dict, config: dict) -> dict:
        schema = meta.get("config_schema")
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider config schema is not defined",
            )
        return schema.model_validate(config or {}).model_dump()

    def _validate_credentials(self, meta: dict, credentials: dict | None) -> dict | None:
        schema = meta.get("credentials_schema")
        if not schema:
            return None

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider credentials are required for this vendor",
            )

        return schema.model_validate(credentials).model_dump()

    def _ensure_sensor_supported(
        self,
        microcontroller: Microcontroller,
        vendor: ProviderVendor,
    ) -> None:
        sensor_type = resolve_sensor_type(vendor)
        if not sensor_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Sensor providers must use a sensor vendor",
            )

        assigned = set(microcontroller.assigned_sensors)
        if sensor_type not in assigned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Sensor provider is not supported by the selected microcontroller"
                ),
            )

    def _validate_external_id(self, external_id: str | None) -> str:
        if not external_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider external_id is required",
            )
        return str(external_id).strip()

    def _derive_external_id(
        self,
        vendor: ProviderVendor,
        payload: dict,
        config: dict,
    ) -> str:
        if vendor == ProviderVendor.HUAWEI:
            device_id = config.get("device_id") or payload.get("external_id")
            if not device_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Huawei provider requires device_id in config",
                )
            return self._validate_external_id(device_id)

        return self._validate_external_id(payload.get("external_id"))

    def _ensure_unique_provider(
        self,
        db: Session,
        user_id: int,
        vendor: ProviderVendor,
        external_id: str,
    ) -> None:
        existing = self._repo(db).get_for_user_vendor_external(
            user_id=user_id,
            vendor=vendor,
            external_id=external_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider with this vendor and external_id already exists",
            )

    # ---------- queries ----------

    def list_for_microcontroller(
        self,
        db: Session,
        user_id: int,
        mc_uuid: UUID,
    ) -> list[Provider]:
        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)
        return (
            db.query(Provider)
            .filter(
                Provider.microcontroller_id == microcontroller.id,
                Provider.provider_type == ProviderType.SENSOR,
            )
            .all()
        )

    def list_api_for_user(self, db: Session, user_id: int) -> list[Provider]:
        return (
            db.query(Provider)
            .filter(
                Provider.user_id == user_id,
                Provider.provider_type == ProviderType.API,
            )
            .all()
        )

    # ---------- commands ----------

    def create_for_microcontroller(
        self,
        db: Session,
        user_id: int,
        mc_uuid: UUID,
        payload: dict,
    ) -> Provider:
        microcontroller = self._ensure_microcontroller(db, user_id, mc_uuid)

        vendor = self._resolve_vendor(payload.get("vendor"))
        meta = self._resolve_definition(vendor)
        if meta["provider_type"] != ProviderType.SENSOR:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only SENSOR providers can be attached to a microcontroller",
            )

        self._ensure_sensor_supported(microcontroller, vendor)

        provider = self._create_provider(
            db=db,
            payload=payload,
            vendor=vendor,
            meta=meta,
            user_id=microcontroller.user_id,
            microcontroller_id=microcontroller.id,
        )
        return provider

    def create_for_user(
        self,
        db: Session,
        user_id: int,
        payload: dict,
    ) -> Provider:
        vendor = self._resolve_vendor(payload.get("vendor"))
        meta = self._resolve_definition(vendor)
        if meta["provider_type"] != ProviderType.API:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only API providers can be created at user scope",
            )

        provider = self._create_provider(
            db=db,
            payload=payload,
            vendor=vendor,
            meta=meta,
            user_id=user_id,
            microcontroller_id=None,
        )
        return provider

    def update(
        self,
        db: Session,
        user_id: int,
        provider_id: int,
        payload: dict,
    ) -> Provider:
        provider = self._ensure_provider(db, user_id, provider_id)

        allowed_fields = {
            "name",
            "unit",
            "value_min",
            "value_max",
            "enabled",
            "config",
        }

        changes = {
            k: v for k, v in payload.items() if k in allowed_fields and v is not None
        }

        if not changes:
            return provider

        if "value_min" in changes or "value_max" in changes:
            new_min = changes.get("value_min", provider.value_min)
            new_max = changes.get("value_max", provider.value_max)

            if new_min >= new_max:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="value_min must be lower than value_max",
                )

        if "config" in changes:
            meta = self._resolve_definition(provider.vendor)
            changes["config"] = self._validate_config(meta, changes["config"])

        if changes.get("enabled") is True and not self._is_provider_attached(db, provider):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider must be attached to a microcontroller before enabling",
            )

        for attr, value in changes.items():
            setattr(provider, attr, value)

        db.commit()
        db.refresh(provider)
        self.logger.info(
            "Provider updated",
            extra={
                "provider_id": provider.id,
                "user_id": user_id,
                "updated_fields": list(changes.keys()),
            },
        )
        return provider

    def update_for_microcontroller(
        self,
        db: Session,
        user_id: int,
        microcontroller_id: int,
        provider_id: int,
        payload: dict,
    ) -> Provider:
        provider = self._ensure_provider_for_microcontroller(
            db,
            user_id,
            provider_id,
            microcontroller_id,
        )
        return self.update(db, user_id, provider.id, payload)

    def set_enabled(
        self,
        db: Session,
        user_id: int,
        provider_id: int,
        enabled: bool,
    ) -> Provider:
        provider = self._ensure_provider(db, user_id, provider_id)
        if enabled and not self._is_provider_attached(db, provider):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider must be attached to a microcontroller before enabling",
            )
        provider.enabled = enabled
        db.commit()
        db.refresh(provider)
        self.logger.info(
            "Provider status changed",
            extra={
                "provider_id": provider.id,
                "user_id": user_id,
                "enabled": enabled,
            },
        )
        return provider

    def set_enabled_for_microcontroller(
        self,
        db: Session,
        user_id: int,
        microcontroller_id: int,
        provider_id: int,
        enabled: bool,
    ) -> Provider:
        provider = self._ensure_provider_for_microcontroller(
            db,
            user_id,
            provider_id,
            microcontroller_id,
        )
        return self.set_enabled(db, user_id, provider.id, enabled)

    def _is_provider_attached(self, db: Session, provider: Provider) -> bool:
        return (
            db.query(Microcontroller)
            .filter(Microcontroller.power_provider_id == provider.id)
            .first()
            is not None
        )

    def get_provider(
        self,
        db: Session,
        user_id: int,
        provider_id: int,
    ) -> Provider:
        return self._ensure_provider(db, user_id, provider_id)

    def get_provider_by_uuid(
        self,
        db: Session,
        user_id: int,
        provider_uuid: UUID,
    ) -> Provider:
        return self._ensure_provider_by_uuid(db, user_id, provider_uuid)

    def delete_by_uuid(self, db: Session, user_id: int, provider_uuid: UUID) -> bool:
        provider = self._repo(db).get_for_user_by_uuid(provider_uuid, user_id)
        if not provider:
            return False
        self._repo(db).delete(provider)
        db.commit()
        self.logger.info(
            "Provider deleted",
            extra={"provider_id": provider.id, "user_id": user_id},
        )
        return True

    def update_by_uuid(
        self,
        db: Session,
        user_id: int,
        provider_uuid: UUID,
        payload: dict,
    ) -> Provider:
        provider = self._ensure_provider_by_uuid(db, user_id, provider_uuid)
        return self.update(db, user_id, provider.id, payload)

    def set_enabled_by_uuid(
        self,
        db: Session,
        user_id: int,
        provider_uuid: UUID,
        enabled: bool,
    ) -> Provider:
        provider = self._ensure_provider_by_uuid(db, user_id, provider_uuid)
        return self.set_enabled(db, user_id, provider.id, enabled)

    def _store_credentials(
        self,
        db: Session,
        provider_id: int,
        credentials: dict,
    ) -> None:
        cred_repo = ProviderCredentialRepository(db)

        def _encrypt_optional(value: str | None) -> str | None:
            return encrypt_secret(value) if value is not None else None

        cred_repo.create(
            ProviderCredential(
                provider_id=provider_id,
                login=_encrypt_optional(credentials.get("username")),
                password=_encrypt_optional(credentials.get("password")),
                token=_encrypt_optional(credentials.get("token")),
                refresh_token=_encrypt_optional(credentials.get("refresh_token")),
            )
        )

    def _create_provider(
        self,
        db: Session,
        payload: dict,
        vendor: ProviderVendor,
        meta: dict,
        *,
        user_id: int,
        microcontroller_id: int | None,
    ) -> Provider:
        payload_type = payload.get("provider_type")
        if payload_type and payload_type != meta["provider_type"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provider type does not match vendor definition",
            )

        config = payload.get("config") or {}
        credentials = payload.get("credentials")
        external_id = self._derive_external_id(vendor, payload, config)
        self._ensure_unique_provider(db, user_id, vendor, external_id)

        value_min = payload.get("value_min")
        value_max = payload.get("value_max")

        if value_min is None or value_max is None:
            raise HTTPException(
                status_code=422,
                detail="Both value_min and value_max must be provided",
            )

        if value_min >= value_max:
            raise HTTPException(
                status_code=422,
                detail="value_min must be lower than value_max",
            )

        payload["vendor"] = vendor
        payload["provider_type"] = meta["provider_type"]
        payload["config"] = self._validate_config(meta, config)
        payload["user_id"] = user_id
        payload["microcontroller_id"] = microcontroller_id
        payload["external_id"] = external_id
        # Providers are enabled only when explicitly attached to a microcontroller.
        payload["enabled"] = False
        validated_credentials = self._validate_credentials(meta, credentials)
        payload.pop("credentials", None)

        provider = Provider(**payload)

        self._repo(db).create(provider)
        db.flush()

        if validated_credentials:
            self._store_credentials(db, provider.id, validated_credentials)

        db.commit()
        db.refresh(provider)
        self.logger.info(
            "Provider created",
            extra={
                "provider_id": provider.id,
                "user_id": user_id,
                "vendor": vendor.value if vendor else None,
                "provider_type": provider.provider_type.value,
            },
        )
        return provider
