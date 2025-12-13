from __future__ import annotations

from smart_common.models.raspberry import Raspberry

from .base import BaseRepository


class RaspberryRepository(BaseRepository[Raspberry]):
    model = Raspberry
