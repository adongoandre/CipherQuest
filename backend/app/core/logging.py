"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = str(value)
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install a single structured stream handler on the root logger."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers when reload/uvicorn re-imports this module.
    for handler in list(root.handlers):
        if getattr(handler, "_cipherquest", False):
            root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._cipherquest = True  # type: ignore[attr-defined]
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
