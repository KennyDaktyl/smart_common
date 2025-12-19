from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import joinedload

from smart_common.models.installation import Installation
from smart_common.models.microcontroller import Microcontroller
from smart_common.repositories.base import BaseRepository


class MicrocontrollerRepository(BaseRepository[Microcontroller]):
    model = Microcontroller

    def get_by_uuid(self, uuid: UUID) -> Optional[Microcontroller]:
        return self.session.query(self.model).filter(self.model.uuid == uuid).first()

    def get_for_user(self, user_id: int) -> List[Microcontroller]:
        return (
            self.session.query(self.model)
            .join(self.model.installation)
            .filter(Installation.user_id == user_id)
            .all()
        )

    def get_for_user_by_uuid(self, uuid: UUID, user_id: int) -> Optional[Microcontroller]:
        return (
            self.session.query(self.model)
            .join(self.model.installation)
            .filter(
                self.model.uuid == uuid,
                Installation.user_id == user_id,
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

    def update_for_user(self, uuid: UUID, user_id: int, data: dict) -> Optional[Microcontroller]:
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

    def get_full_for_user(self, user_id: int):
        microcontrollers = (
            self.session.query(self.model)
            .join(self.model.installation)
            .filter(Installation.user_id == user_id)
            .options(
                joinedload(self.model.devices),
                joinedload(self.model.providers),
            )
            .all()
        )

        installations = (
            self.session.query(Installation)
            .filter(Installation.user_id == user_id)
            .options(joinedload(Installation.microcontrollers))
            .all()
        )

        return microcontrollers, installations
