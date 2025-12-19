from sqlalchemy import and_
from smart_common.models.device_auto_config import DeviceAutoConfig
from smart_common.repositories.base import BaseRepository


class DeviceAutoConfigRepository(BaseRepository[DeviceAutoConfig]):
    model = DeviceAutoConfig

    # ---------------------------------------------------------
    # Queries
    # ---------------------------------------------------------

    def get_for_device(
        self,
        *,
        user_id: int,
        device_id: int,
        microcontroller_id: int,
    ) -> DeviceAutoConfig | None:
        return (
            self.session.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.device_id == device_id,
                    self.model.microcontroller_id == microcontroller_id,
                )
            )
            .one_or_none()
        )

    # ---------------------------------------------------------
    # Commands
    # ---------------------------------------------------------

    def create_config(
        self,
        *,
        user_id: int,
        device_id: int,
        microcontroller_id: int,
        config: dict,
        enabled: bool = True,
    ) -> DeviceAutoConfig:
        entity = DeviceAutoConfig(
            user_id=user_id,
            device_id=device_id,
            microcontroller_id=microcontroller_id,
            config=config,
            enabled=enabled,
        )
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update_config(
        self,
        entity: DeviceAutoConfig,
        *,
        config: dict | None = None,
        enabled: bool | None = None,
    ) -> DeviceAutoConfig:
        if config is not None:
            entity.config = config

        if enabled is not None:
            entity.enabled = enabled

        self.session.commit()
        self.session.refresh(entity)
        return entity

    def set_enabled(
        self,
        entity: DeviceAutoConfig,
        *,
        enabled: bool,
    ) -> DeviceAutoConfig:
        entity.enabled = enabled
        self.session.commit()
        self.session.refresh(entity)
        return entity
