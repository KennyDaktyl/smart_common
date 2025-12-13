from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from smart_common.models import Installation, Provider
from .base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider

    def list_for_user(self, db: Session, user_id: int) -> List[Provider]:
        return (
            db.query(self.model)
            .join(Installation)
            .filter(Installation.user_id == user_id)
            .all()
        )

    def get_for_user(self, db: Session, provider_id: int, user_id: int) -> Optional[Provider]:
        return (
            db.query(self.model)
            .join(Installation)
            .filter(self.model.id == provider_id, Installation.user_id == user_id)
            .first()
        )
