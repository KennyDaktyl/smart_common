from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import joinedload

from smart_common.models.installation import Installation
from smart_common.models.providers import Provider
from smart_common.models.raspberry import Raspberry

from .base import BaseRepository


class RaspberryRepository(BaseRepository[Raspberry]):
    model = Raspberry

    def get_by_uuid(self, uuid: UUID) -> Optional[Raspberry]:
        return (
            self.session.query(self.model)
            .filter(self.model.uuid == uuid)
            .first()
        )

    def get_for_user(self, user_id: int) -> List[Raspberry]:
        return (
            self.session.query(self.model)
            .filter(self.model.user_id == user_id)
            .all()
        )

    def get_for_user_by_uuid(self, uuid: UUID, user_id: int) -> Optional[Raspberry]:
        return (
            self.session.query(self.model)
            .filter(self.model.uuid == uuid, self.model.user_id == user_id)
            .first()
        )

    def create(self, data: dict) -> Raspberry:
        raspberry = Raspberry(**data)
        self.session.add(raspberry)
        self.session.flush()
        self.session.refresh(raspberry)
        return raspberry

    def update_for_user(self, uuid: UUID, user_id: int, data: dict) -> Optional[Raspberry]:
        raspberry = self.get_for_user_by_uuid(uuid, user_id)
        if not raspberry:
            return None
        for key, value in data.items():
            setattr(raspberry, key, value)
        self.session.flush()
        self.session.refresh(raspberry)
        return raspberry

    def delete_for_user(self, uuid: UUID, user_id: int) -> bool:
        raspberry = self.get_for_user_by_uuid(uuid, user_id)
        if not raspberry:
            return False
        self.session.delete(raspberry)
        self.session.flush()
        return True

    def get_full_for_user(self, user_id: int):
        raspberries = (
            self.session.query(self.model)
            .filter(self.model.user_id == user_id)
            .options(
                joinedload(self.model.devices),
                joinedload(self.model.provider).joinedload(Provider.raspberries),
            )
            .all()
        )

        installations = (
            self.session.query(Installation)
            .filter(Installation.user_id == user_id)
            .options(joinedload(Installation.providers))
            .all()
        )

        return raspberries, installations
