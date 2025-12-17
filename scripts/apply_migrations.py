#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from alembic import command
from alembic.config import Config

ENV_PATH = ".env"
ALEMBIC_INI_PATH = "alembic.ini"

load_dotenv(ENV_PATH, encoding="utf-8")

from core.config import settings


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info("Applying Alembic migrations to %s", settings.DATABASE_URL)

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option(
        "sqlalchemy.url",
        settings.DATABASE_URL.replace("%", "%%"),
    )

    command.upgrade(config, "head")
    logging.info("Migrations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
