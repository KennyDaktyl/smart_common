import logging
import sys
import os
from datetime import datetime, timezone

from smart_common.core.config import settings
from smart_common.smart_logging.custom_rotating_handler import (
    AdvancedRotatingFileHandler,
)
from smart_common.smart_logging.formatter import ExtraFormatter


def setup_logging():
    from pathlib import Path

    log_dir = Path(settings.LOG_DIR)

    if not log_dir.is_absolute():
        log_dir = (Path.cwd() / log_dir).resolve()

    log_dir.mkdir(parents=True, exist_ok=True)

    LOG_DIR = str(log_dir)

    FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    DATEFMT = "%Y-%m-%d %H:%M:%S"

    formatter = ExtraFormatter(FORMAT, datefmt=DATEFMT)

    file_handler = AdvancedRotatingFileHandler(
        base_log_dir=LOG_DIR,
        filename="service.log",
        retention_days=365,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # =========================
    # ROOT LOGGER (APLIKACJA)
    # =========================
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # =========================
    # UVICORN LOGGERS → FILE
    # =========================

    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_access = logging.getLogger("uvicorn.access")

    uvicorn_error.handlers.clear()
    uvicorn_access.handlers.clear()

    uvicorn_error.addHandler(file_handler)
    uvicorn_access.addHandler(file_handler)

    uvicorn_error.setLevel(logging.INFO)
    uvicorn_access.setLevel(logging.INFO)

    uvicorn_error.propagate = False
    uvicorn_access.propagate = False

    # =========================
    # STARTUP LOG
    # =========================
    root.info("🚀 Logging initialized")
    root.info("Logs directory: %s", LOG_DIR)
    root.info(
        "Logger start time UTC: %s",
        datetime.now(timezone.utc).isoformat(),
    )
