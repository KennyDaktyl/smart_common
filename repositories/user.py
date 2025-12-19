from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import selectinload

from smart_common.models.installation import Installation
from smart_common.models.microcontroller import Microcontroller
from smart_common.models.user import User
from smart_common.models.user_profile import UserProfile
from smart_common.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    ADMIN_EDITABLE_FIELDS = {"email", "role", "is_active"}
    SELF_EDITABLE_FIELDS = {"email"}
    
    searchable_fields = {
        "email": User.email,
        "is_active": User.is_active,
        "role": User.role,
    }

    # -----------------------------
    # BASIC
    # -----------------------------
    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    # -----------------------------
    # INSTALLATIONS (średnie)
    # -----------------------------
    def get_with_installations(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .options(
                selectinload(User.installations),
            )
            .filter(User.id == user_id)
            .first()
        )

    # -----------------------------
    # FULL DETAILS (ciężkie)
    # -----------------------------
    def get_with_installations_details(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .options(
                selectinload(User.installations)
                .selectinload(Installation.microcontrollers)
                .selectinload(Microcontroller.devices),
                selectinload(User.installations)
                .selectinload(Installation.microcontrollers)
                .selectinload(Microcontroller.providers),
            )
            .filter(User.id == user_id)
            .first()
        )

    def get_with_profile(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .outerjoin(User.profile)
            .filter(User.id == user_id)
            .first()
        )

    def upsert_profile(
        self,
        user: User,
        data: dict,
    ) -> UserProfile:
        if user.profile is None:
            user.profile = UserProfile(**data)
        else:
            for key, value in data.items():
                setattr(user.profile, key, value)

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user.profile)
        return user.profile
    
    def update_user_admin(
        self,
        user: User,
        data: dict[str, Any],
    ) -> User:
        return self.partial_update(
            user,
            data=data,
            allowed_fields=self.ADMIN_EDITABLE_FIELDS,
        )

    def update_user_self(
        self,
        user: User,
        data: dict[str, Any],
    ) -> User:
        return self.partial_update(
            user,
            data=data,
            allowed_fields=self.SELF_EDITABLE_FIELDS,
        )

    def deactivate_user(self, user: User) -> User:
        return self.partial_update(
            user,
            data={"is_active": False},
            allowed_fields={"is_active"},
        )