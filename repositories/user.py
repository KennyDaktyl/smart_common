from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm import selectinload, joinedload

from smart_common.core.security import hash_password
from smart_common.enums.user import UserRole
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.models.user_profile import UserProfile
from smart_common.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    model = User

    ADMIN_EDITABLE_FIELDS = {"email", "role", "is_active"}
    SELF_EDITABLE_FIELDS = {"email"}

    searchable_fields = {
        "email": User.email,
        "is_active": User.is_active,
        "role": User.role,
    }

    search_fields = {
        "id": User.id,
        "email": User.email,
        "first_name": UserProfile.first_name,
        "last_name": UserProfile.last_name,
        "company_name": UserProfile.company_name,
        "company_vat": UserProfile.company_vat,
    }

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def get_profile(self, user: User) -> Optional[UserProfile]:
        return (
            self.session.query(UserProfile)
            .filter(UserProfile.user_id == user.id)
            .first()
        )

    def activate_user(self, user: User) -> User:
        user.is_active = True
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        logger.info("Activated user id=%s email=%s", user.id, user.email)
        return user

    def deactivate_user(self, user: User) -> User:
        updated_user = self.partial_update(
            user,
            data={"is_active": False},
            allowed_fields={"is_active"},
        )
        logger.info("Deactivated user id=%s email=%s", user.id, user.email)
        return updated_user

    def update_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        logger.info("Password updated for user id=%s", user.id)
        return user

    def get_me_details(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .options(
                joinedload(User.profile),
                # selectinload(User.microcontrollers).selectinload(
                #     Microcontroller.devices
                # ),
                # selectinload(User.microcontrollers).selectinload(
                #     Microcontroller.sensor_providers
                # ),
                # selectinload(User.microcontrollers).selectinload(
                #     Microcontroller.power_provider
                # ),
            )
            .filter(User.id == user_id)
            .first()
        )

    def get_user_details(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .options(
                joinedload(User.profile),
                selectinload(User.microcontrollers).selectinload(
                    Microcontroller.devices
                ),
                selectinload(User.microcontrollers).selectinload(
                    Microcontroller.power_provider
                ),
            )
            .filter(User.id == user_id)
            .first()
        )

    def upsert_profile(
        self,
        user: User,
        data: dict,
    ) -> UserProfile:
        if user.profile is None:
            user.profile = UserProfile(user_id=user.id, **data)
        else:
            for key, value in data.items():
                setattr(user.profile, key, value)

        self.session.add(user.profile)
        self.session.commit()
        self.session.refresh(user.profile)
        logger.info(
            "Profile upserted for user id=%s fields=%s",
            user.id,
            data,
        )
        return user.profile

    def update_user_admin(
        self,
        user: User,
        data: dict[str, Any],
    ) -> User:
        updated_user = self.partial_update(
            user,
            data=data,
            allowed_fields=self.ADMIN_EDITABLE_FIELDS,
        )
        logger.info("Admin updated user id=%s fields=%s", user.id, data)
        return updated_user

    def update_user_self(
        self,
        user: User,
        data: dict[str, Any],
    ) -> User:
        updated_user = self.partial_update(
            user,
            data=data,
            allowed_fields=self.SELF_EDITABLE_FIELDS,
        )
        logger.info("User updated self id=%s fields=%s", user.id, data)
        return updated_user

    def list_admin(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
        order_by,
    ) -> list[User]:
        base_query = (
            self.session.query(User)
            .outerjoin(UserProfile)
            .options(joinedload(User.profile))
        )

        results = self.list_with_search(
            limit=limit,
            offset=offset,
            search=search,
            search_fields=self.search_fields,
            order_by=order_by,
            base_query=base_query,
        )
        logger.info(
            "Admin listed users limit=%s offset=%s search=%s returned=%s",
            limit,
            offset,
            search,
            len(results),
        )
        return results

    def count_admin(self, *, search: str | None) -> int:
        base_query = self.session.query(User).outerjoin(UserProfile)

        return self.count_with_search(
            search=search,
            search_fields=self.search_fields,
            base_query=base_query,
        )

    def create_user_admin(
        self,
        *,
        email: str,
        password: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        logger.info(
            "Admin created user id=%s email=%s role=%s active=%s",
            user.id,
            user.email,
            user.role,
            user.is_active,
        )

        return user
