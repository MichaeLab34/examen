"""Structured runtime logging helpers for containerized services."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        message = record.getMessage()
        try:
            event = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            event = None
        if isinstance(event, dict):
            payload.update(event)
        else:
            payload["message"] = message
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_json_logger(name: str, *, level: int = logging.INFO) -> logging.Logger:
    """Return an idempotently configured JSON logger writing to container stderr."""

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(getattr(handler, "decrochage_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        handler.decrochage_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger
