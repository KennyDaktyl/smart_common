from __future__ import annotations

from typing import List, Optional

from smart_common.models.installation import Installation
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.provider import Provider
from smart_common.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider

    def list_for_user(self, user_id: int) -> List[Provider]:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .join(Microcontroller.installation)
            .filter(Installation.user_id == user_id)
            .all()
        )

    def get_for_user(self, provider_id: int, user_id: int) -> Optional[Provider]:
        return (
            self.session.query(self.model)
            .join(self.model.microcontroller)
            .join(Microcontroller.installation)
            .filter(
                self.model.id == provider_id,
                Installation.user_id == user_id,
            )
            .first()
        )
