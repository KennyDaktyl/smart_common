#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

# -------------------------------------------------
# USTALAMY ROOT PROJEKTU = katalog z alembic.ini
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)  # <<< KLUCZOWE

sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / ".env"
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"

load_dotenv(ENV_PATH, encoding="utf-8")

from smart_common.core.config import settings
import smart_common.models  # noqa: F401


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
