import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from smart_common.core.config import settings
from smart_common.smart_logging.custom_rotating_handler import (
    AdvancedRotatingFileHandler,
)
from smart_common.smart_logging.formatter import ExtraFormatter


def setup_logging():
    # === GUARD: konfigurujemy logging tylko raz ===
    if getattr(setup_logging, "_configured", False):
        return
    setup_logging._configured = True

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
    # ROOT LOGGER
    # =========================
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # =========================
    # UVICORN → PROPAGATE DO ROOT
    # =========================
    logging.getLogger("uvicorn.error").propagate = True
    logging.getLogger("uvicorn.access").propagate = True

    # =========================
    # STARTUP LOG
    # =========================
    root.info("🚀 Logging initialized")
    root.info("Logs directory: %s", LOG_DIR)
    root.info(
        "Logger start time UTC: %s",
        datetime.now(timezone.utc).isoformat(),
    )
