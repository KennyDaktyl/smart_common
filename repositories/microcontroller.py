from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Query, selectinload

from smart_common.models.microcontroller import Microcontroller
from smart_common.models.provider import Provider
from smart_common.models.user import User
from smart_common.providers.enums import ProviderType
from smart_common.repositories.base import BaseRepository


search_fields = (
    cast(Microcontroller.id, String),
    cast(Microcontroller.uuid, String),
    cast(Microcontroller.user_id, String),
    cast(Microcontroller.name, String),
    User.email,
)


class MicrocontrollerRepository(BaseRepository[Microcontroller]):
    model = Microcontroller
    default_order_by = Microcontroller.id.asc()

    ADMIN_UPDATE_FIELDS = {
        "name",
        "description",
        "software_version",
        "max_devices",
        "enabled",
        "user_id",
    }

    # =====================================================
    # EAGER LOADING – SINGLE SOURCE OF TRUTH
    # =====================================================

    def _full_options(self) -> list:
        return [
            selectinload(Microcontroller.user),
            selectinload(Microcontroller.devices),
            selectinload(Microcontroller.power_provider),
            selectinload(Microcontroller.sensor_capabilities),
        ]

    # =====================================================
    # BASIC GETTERS
    # =====================================================

    def get_by_uuid(self, uuid: UUID) -> Optional[Microcontroller]:
        return (
            self.session.query(self.model).filter(self.model.uuid == uuid).one_or_none()
        )

    def get_for_user(self, user_id: int) -> List[Microcontroller]:
        microcontrollers = (
            self.session.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.id.asc())
            .options(*self._full_options())
            .all()
        )

        providers = (
            self.session.query(Provider)
            .filter(
                Provider.user_id == user_id,
                Provider.provider_type == ProviderType.API,
                Provider.enabled.is_(True),
            )
            .all()
        )

        for mc in microcontrollers:
            mc.__dict__["available_api_providers"] = providers

        return microcontrollers

    def get_for_user_by_uuid(
        self, uuid: UUID, user_id: int
    ) -> Optional[Microcontroller]:
        return (
            self.session.query(self.model)
            .filter(
                self.model.uuid == uuid,
                self.model.user_id == user_id,
            )
            .options(*self._full_options())
            .one_or_none()
        )

    def get_full_by_id(self, microcontroller_id: int) -> Optional[Microcontroller]:
        return (
            self.session.query(self.model)
            .filter(self.model.id == microcontroller_id)
            .options(*self._full_options())
            .one_or_none()
        )

    # =====================================================
    # CREATE / UPDATE / DELETE
    # =====================================================

    def create(self, data: dict) -> Microcontroller:
        microcontroller = Microcontroller(**data)
        self.session.add(microcontroller)
        self.session.commit()
        self.session.refresh(microcontroller)
        return microcontroller

    def update_for_user(
        self, uuid: UUID, user_id: int, data: dict
    ) -> Optional[Microcontroller]:
        microcontroller = self.get_for_user_by_uuid(uuid, user_id)
        if not microcontroller:
            return None

        for key, value in data.items():
            setattr(microcontroller, key, value)

        self.session.commit()
        self.session.refresh(microcontroller)
        return microcontroller

    def delete_for_user(self, uuid: UUID, user_id: int) -> bool:
        microcontroller = self.get_for_user_by_uuid(uuid, user_id)
        if not microcontroller:
            return False

        self.session.delete(microcontroller)
        self.session.commit()
        return True

    def delete_by_id(self, microcontroller_id: int) -> None:
        microcontroller = self.get_by_id(microcontroller_id)
        if not microcontroller:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Microcontroller not found",
            )

        self.session.delete(microcontroller)
        self.session.commit()

    # =====================================================
    # ADMIN LISTING
    # =====================================================

    def list_admin(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
        order_by: Any | None = None,
    ) -> list[Microcontroller]:
        query = (
            self.session.query(self.model)
            .outerjoin(User)
            .options(*self._full_options())
        )

        if search:
            query = self._apply_microcontroller_search(query, search)

        if order_by is not None:
            query = query.order_by(order_by)
        elif self.default_order_by is not None:
            query = query.order_by(self.default_order_by)

        return query.offset(offset).limit(limit).all()

    def count_admin(self, *, search: str | None) -> int:
        query = self.session.query(self.model).outerjoin(User)

        if search:
            query = self._apply_microcontroller_search(query, search)

        return query.count()

    # =====================================================
    # SEARCH
    # =====================================================

    def _apply_microcontroller_search(self, query: Query, search: str) -> Query:
        conditions = []

        if search.isdigit():
            value = int(search)
            conditions.append(self.model.id == value)
            conditions.append(self.model.user_id == value)

        try:
            uuid = UUID(search)
            conditions.append(self.model.uuid == uuid)
        except ValueError:
            pass

        conditions.append(User.email.ilike(f"%{search}%"))
        conditions.append(self.model.name.ilike(f"%{search}%"))

        return query.filter(or_(*conditions))

    def set_power_provider_for_user(
        self,
        *,
        microcontroller_uuid: UUID,
        user_id: int,
        provider_uuid: UUID | None,
    ) -> Microcontroller | None:
        microcontroller = self.get_for_user_by_uuid(
            uuid=microcontroller_uuid,
            user_id=user_id,
        )

        if not microcontroller:
            return None

        if provider_uuid is None:
            microcontroller.power_provider_id = None
            self.session.commit()
            self.session.refresh(microcontroller)
            return microcontroller

        provider = (
            self.session.query(Provider)
            .filter(
                Provider.uuid == provider_uuid,
                Provider.user_id == user_id,
                Provider.enabled.is_(True),
            )
            .one_or_none()
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider not found or not available",
            )

        microcontroller.power_provider_id = provider.id

        self.session.commit()
        self.session.refresh(microcontroller)
        return microcontroller
