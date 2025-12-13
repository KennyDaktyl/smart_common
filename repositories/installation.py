from __future__ import annotations

from models.installation import Installation

from .base import BaseRepository


class InstallationRepository(BaseRepository[Installation]):
    model = Installation
