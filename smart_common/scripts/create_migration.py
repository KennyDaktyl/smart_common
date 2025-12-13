#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
VERSIONS_PATH = PROJECT_ROOT / "alembic" / "versions"

load_dotenv(ENV_PATH, encoding="utf-8")

sys.path.insert(0, str(PROJECT_ROOT))

from smart_common.core.config import settings
from smart_common.core.db import Base

import models  # noqa: F401



def _list_version_files() -> set[Path]:
    if not VERSIONS_PATH.exists():
        return set()
    return {path for path in VERSIONS_PATH.iterdir() if path.suffix == ".py"}


def _has_schema_changes(engine: Engine) -> bool:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection=connection,
            opts={
                "compare_type": True,
                "compare_server_default": True,
            },
        )
        return bool(compare_metadata(context, Base.metadata))


def _build_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    safe_url = settings.DATABASE_URL.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", safe_url)
    return config


def _generate_message(override: str | None) -> str:
    if override:
        return override
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"auto migration {timestamp}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an Alembic revision only when models differ from the database schema."
    )
    parser.add_argument("-m", "--message", help="Migration message to embed in the revision header")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    engine = create_engine(settings.DATABASE_URL, future=True)

    try:
        logging.info("Checking models against database schema...")
        if not _has_schema_changes(engine):
            logging.info("No schema changes detected. Skipping revision generation.")
            return 0
    finally:
        engine.dispose()

    logging.info("Schema changes detected. Generating Alembic revision...")
    config = _build_config()
    before = _list_version_files()
    message = _generate_message(args.message)
    command.revision(config, message=message, autogenerate=True)
    after = _list_version_files()

    new_files = after - before
    if not new_files:
        logging.warning("Revision command completed but no new file was created.")
        return 1

    new_file = sorted(new_files)[-1]
    logging.info("Revision created at %s", new_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
