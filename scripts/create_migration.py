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
    # fallback: script is inside smart_common/scripts/
    BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR))

# ======================================================
# STANDARD IMPORTS
# ======================================================
import argparse
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

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
# PROJECT IMPORTS (PAKIET!)
# ======================================================
import smart_common.models  # noqa: F401
from smart_common.core.config import settings
from smart_common.core.db import Base

# ======================================================
# INTERNALS
# ======================================================
def _has_schema_changes(engine) -> bool:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection=connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
            },
        )
        return bool(compare_metadata(context, Base.metadata))


def _generate_message(override: str | None) -> str:
    if override:
        return override
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"auto migration {ts}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--message")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    engine = create_engine(settings.DATABASE_URL, future=True)

    try:
        logging.info("Checking models against database schema...")
        if not _has_schema_changes(engine):
            logging.info("No schema changes detected.")
            return 0
    finally:
        engine.dispose()

    logging.info("Schema changes detected. Generating revision...")

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option(
        "sqlalchemy.url",
        settings.DATABASE_URL.replace("%", "%%"),
    )

    # 🔥 KLUCZOWE DLA SUBMODULE
    config.set_main_option(
        "script_location",
        str(ALEMBIC_DIR),
    )

    command.revision(
        config,
        message=_generate_message(args.message),
        autogenerate=True,
    )

    logging.info("Migration generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
