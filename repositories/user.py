from __future__ import annotations

from models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User
