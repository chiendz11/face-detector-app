from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
import sys
from typing import Any


APP_LOGGER_NAME = "app"


def configure_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.strip().upper(), logging.INFO)
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(numeric_level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(numeric_level)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
    }
    payload.update(
        {
            key: _json_safe(value)
            for key, value in fields.items()
            if value is not None
        }
    )
    logger.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, BaseException):
        return str(value)
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value
