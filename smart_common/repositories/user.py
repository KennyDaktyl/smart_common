from __future__ import annotations

from smart_common.models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
