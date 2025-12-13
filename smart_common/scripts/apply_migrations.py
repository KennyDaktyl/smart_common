#!/usr/bin/env python3
from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"

load_dotenv(ENV_PATH, encoding="utf-8")

sys.path.insert(0, str(PROJECT_ROOT))

from smart_common.core.config import settings


def _build_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    sql_url = settings.DATABASE_URL.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", sql_url)
    return config


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info("Applying Alembic migrations to %s", settings.DATABASE_URL)

    config = _build_config()
    command.upgrade(config, "head")

    logging.info("Migrations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
