#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# ======================================================
# BOOTSTRAP
# ======================================================
BASE_DIR = Path(__file__).resolve().parents[1]  # smart_common
PROJECT_DIR = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

# ======================================================
# IMPORTS
# ======================================================
import argparse
import logging
from datetime import datetime, timezone

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ======================================================
# PATHS
# ======================================================
ENV_PATH = BASE_DIR / ".env"
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
ALEMBIC_DIR = BASE_DIR / "alembic"

load_dotenv(ENV_PATH)

# ======================================================
# PROJECT IMPORTS
# ======================================================
import smart_common.models  # noqa
from smart_common.core.config import settings
from smart_common.core.db import Base


# ======================================================
# HELPERS
# ======================================================
def has_schema_changes(engine) -> bool:
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            connection=conn,
            opts={"compare_type": True, "compare_server_default": True},
        )
        return bool(compare_metadata(ctx, Base.metadata))


def db_is_at_head(engine, config: Config) -> bool:
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        current = ctx.get_current_revision()

    return current == head


def message(msg: str | None) -> str:
    if msg:
        return msg
    ts = datetime.now(timezone.utc).isoformat()
    return f"auto migration {ts}"


# ======================================================
# MAIN
# ======================================================
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--message")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    engine = create_engine(settings.DATABASE_URL, future=True)

    try:
        if not has_schema_changes(engine):
            logging.info("No schema changes detected.")
            return 0
    finally:
        engine.dispose()

    config = Config(str(ALEMBIC_INI_PATH))

    # 🔥 MUSI BYĆ PRZED ScriptDirectory
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option(
        "sqlalchemy.url",
        settings.DATABASE_URL.replace("%", "%%"),
    )

    if not db_is_at_head(engine, config):
        logging.error("DB not at HEAD. Run migrations first.")
        return 1

    command.revision(
        config,
        autogenerate=True,
        message=message(args.message),
    )

    logging.info("Migration created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
