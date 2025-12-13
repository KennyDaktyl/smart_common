from __future__ import annotations

from models.raspberry import Raspberry

from .base import BaseRepository


class RaspberryRepository(BaseRepository[Raspberry]):
    model = Raspberry
