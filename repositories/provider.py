from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from smart_common.models.provider import Provider
from smart_common.providers.enums import ProviderVendor
from smart_common.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider

    def list_for_user(self, user_id: int) -> list[Provider]:
        return self.list(filters={"user_id": user_id})

    def get_for_user(self, provider_id: int, user_id: int) -> Optional[Provider]:
        return (
            self.session.query(self.model)
            .filter(
                self.model.id == provider_id,
                self.model.user_id == user_id,
            )
            .first()
        )

    def get_for_user_by_uuid(
        self,
        provider_uuid: UUID,
        user_id: int,
    ) -> Optional[Provider]:
        return (
            self.session.query(self.model)
            .filter(
                self.model.uuid == provider_uuid,
                self.model.user_id == user_id,
            )
            .first()
        )

    def get_for_user_vendor_external(
        self,
        user_id: int,
        vendor: ProviderVendor,
        external_id: str,
    ) -> Optional[Provider]:
        return (
            self.session.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.vendor == vendor,
                self.model.external_id == external_id,
            )
            .first()
        )

    def exists_user_provider_with_external_id(
        self,
        *,
        user_id: int,
        vendor: ProviderVendor,
        external_id: str,
    ) -> bool:
        query = (
            self.session.query(self.model.id)
            .filter(
                self.model.user_id == user_id,
                self.model.vendor == vendor,
                self.model.external_id == external_id,
                self.model.microcontroller_id.is_(None),
            )
            .limit(1)
        )
        return self.session.query(query.exists()).scalar()
