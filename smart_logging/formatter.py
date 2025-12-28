# smart_common/smart_logging/formatter.py
import logging
import json

STANDARD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


class ExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)

        extras = {k: v for k, v in record.__dict__.items() if k not in STANDARD_ATTRS}

        if not extras:
            return base

        try:
            extras_str = json.dumps(extras, ensure_ascii=False)
        except Exception:
            extras_str = str(extras)

        return f"{base} | extra={extras_str}"
