from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Query, joinedload

from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.repositories.base import BaseRepository


search_fields = (
    cast(Microcontroller.id, String),
    cast(Microcontroller.uuid, String),
    cast(Microcontroller.user_id, String),
    cast(Microcontroller.name, String),
    User.email,
    User.id,
)


class MicrocontrollerRepository(BaseRepository[Microcontroller]):
    model = Microcontroller

    ADMIN_UPDATE_FIELDS = {
        "name",
        "description",
        "software_version",
        "max_devices",
        "enabled",
        "user_id",
    }

    def get_by_uuid(self, uuid: UUID) -> Optional[Microcontroller]:
        return self.session.query(self.model).filter(self.model.uuid == uuid).first()

    def get_for_user(self, user_id: int) -> List[Microcontroller]:
        return (
            self.session.query(self.model).filter(self.model.user_id == user_id).all()
        )

    def get_for_user_by_uuid(
        self, uuid: UUID, user_id: int
    ) -> Optional[Microcontroller]:
        return (
            self.session.query(self.model)
            .filter(
                self.model.uuid == uuid,
                self.model.user_id == user_id,
            )
            .first()
        )

    def create(self, data: dict) -> Microcontroller:
        microcontroller = Microcontroller(**data)
        self.session.add(microcontroller)
        self.session.flush()
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
        self.session.flush()
        self.session.refresh(microcontroller)
        return microcontroller

    def delete_for_user(self, uuid: UUID, user_id: int) -> bool:
        microcontroller = self.get_for_user_by_uuid(uuid, user_id)
        if not microcontroller:
            return False
        self.session.delete(microcontroller)
        self.session.flush()
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

    def get_full_for_user(self, user_id: int):
        microcontrollers = (
            self.session.query(self.model)
            .filter(self.model.user_id == user_id)
            .options(
                joinedload(self.model.devices),
                joinedload(self.model.sensor_providers),
                joinedload(self.model.power_provider),
                joinedload(self.model.sensor_capabilities),
            )
            .all()
        )
        return microcontrollers

    def _with_full_options(self, query: Query) -> Query:
        return query.options(
            joinedload(self.model.devices),
            joinedload(self.model.sensor_providers),
            joinedload(self.model.power_provider),
            joinedload(self.model.sensor_capabilities),
            joinedload(self.model.user),
        )

    def list_full(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
    ) -> list[Microcontroller]:
        query = self._with_full_options(self._base_query())
        query = self._apply_filters(query, filters)

        if order_by is not None:
            query = query.order_by(order_by)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

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
            .options(
                joinedload(self.model.user),
                joinedload(self.model.devices),
                joinedload(self.model.sensor_providers),
                joinedload(self.model.power_provider),
                joinedload(self.model.sensor_capabilities),
            )
        )

        if search:
            query = self._apply_microcontroller_search(query, search)

        if order_by is not None:
            query = query.order_by(order_by)

        return query.offset(offset).limit(limit).all()

    def count_admin(self, *, search: str | None) -> int:
        query = self.session.query(self.model).outerjoin(User)

        if search:
            query = self._apply_microcontroller_search(query, search)

        return query.count()

    def get_full_by_id(self, id: int) -> Microcontroller | None:
        return (
            self.session.query(self.model)
            .filter(self.model.id == id)
            .options(
                joinedload(self.model.user),
                joinedload(self.model.devices),
                joinedload(self.model.sensor_providers),
                joinedload(self.model.power_provider),
                joinedload(self.model.sensor_capabilities),
            )
            .one_or_none()
        )

    def _apply_microcontroller_search(self, query, search: str):
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

        return query.filter(or_(*conditions))
