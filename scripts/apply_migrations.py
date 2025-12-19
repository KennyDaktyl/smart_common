#!/usr/bin/env python3
from __future__ import annotations

# ======================================================
# BOOTSTRAP PYTHONPATH (SUBMODULE SAFE)
# ======================================================
import sys
import os
from pathlib import Path

SMART_COMMON_PATH = os.getenv("SMART_COMMON_PATH")

if SMART_COMMON_PATH:
    BASE_DIR = Path(SMART_COMMON_PATH).resolve()
else:
    # fallback: script inside smart_common/scripts/
    BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR))

# ======================================================
# STANDARD IMPORTS
# ======================================================
import logging
from dotenv import load_dotenv

from alembic import command
from alembic.config import Config

# ======================================================
# PATHS
# ======================================================
ENV_PATH = BASE_DIR / ".env"
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
ALEMBIC_DIR = BASE_DIR / "alembic"

# ======================================================
# ENV
# ======================================================
load_dotenv(ENV_PATH, encoding="utf-8")

# ======================================================
# PROJECT IMPORTS
# ======================================================
from smart_common.core.config import settings


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info(
        "Applying Alembic migrations to %s",
        settings.DATABASE_URL,
    )

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option(
        "sqlalchemy.url",
        settings.DATABASE_URL.replace("%", "%%"),
    )

    config.set_main_option(
        "script_location",
        str(ALEMBIC_DIR),
    )

    command.upgrade(config, "head")

    logging.info("Migrations applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
