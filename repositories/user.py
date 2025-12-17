from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import joinedload

from models.installation import Installation
from models.microcontroller import Microcontroller
from models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(self.model).filter(self.model.email == email).first()

    def activate_user(self, user: User) -> User:
        user.is_active = True
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        user.is_active = True
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_installations_details(self, user_id: int) -> Optional[User]:
        return (
            self.session.query(self.model)
            .options(
                joinedload(User.installations)
                .joinedload(Installation.microcontrollers)
                .joinedload(Microcontroller.devices),
                joinedload(User.installations)
                .joinedload(Installation.microcontrollers)
                .joinedload(Microcontroller.providers),
            )
            .filter(User.id == user_id)
            .first()
        )

    def get_all_with_installations_and_providers(self) -> List[User]:
        return (
            self.session.query(self.model)
            .options(
                joinedload(User.installations)
                .joinedload(Installation.microcontrollers)
                .joinedload(Microcontroller.providers)
            )
            .all()
        )
