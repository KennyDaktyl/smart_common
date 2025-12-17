#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

ENV_PATH = ".env"
ALEMBIC_INI_PATH = "alembic.ini"
VERSIONS_PATH = "alembic/versions"

load_dotenv(ENV_PATH, encoding="utf-8")

import models  # noqa: F401
from core.config import settings
from core.db import Base


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

    command.revision(
        config,
        message=_generate_message(args.message),
        autogenerate=True,
    )

    logging.info("Migration generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
