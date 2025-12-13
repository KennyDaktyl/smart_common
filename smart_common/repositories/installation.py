from __future__ import annotations

from typing import List, Optional

from smart_common.models.installation import Installation

from .base import BaseRepository


class InstallationRepository(BaseRepository[Installation]):
    model = Installation

    def get_by_user(self, user_id: int) -> List[Installation]:
        return (
            self.session.query(self.model)
            .filter(self.model.user_id == user_id)
            .all()
        )

    def get_by_station_code(self, station_code: str) -> Optional[Installation]:
        return (
            self.session.query(self.model)
            .filter(self.model.station_code == station_code)
            .first()
        )

    def get_for_user_by_id(self, installation_id: int, user_id: int) -> Optional[Installation]:
        return (
            self.session.query(self.model)
            .filter(self.model.id == installation_id, self.model.user_id == user_id)
            .first()
        )

    def update_for_user(self, installation_id: int, user_id: int, data: dict) -> Optional[Installation]:
        installation = self.get_for_user_by_id(installation_id, user_id)
        if not installation:
            return None
        for key, value in data.items():
            setattr(installation, key, value)
        self.session.flush()
        self.session.refresh(installation)
        return installation

    def delete_for_user(self, installation_id: int, user_id: int) -> bool:
        installation = self.get_for_user_by_id(installation_id, user_id)
        if not installation:
            return False
        self.session.delete(installation)
        self.session.flush()
        return True
