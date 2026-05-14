"""Structured JSON logging.

One JSON object per line on stderr. Standard fields: ``timestamp`` (UTC,
ISO-8601), ``level``, ``logger``, ``message``. Anything passed via the
``extra={"foo": ...}`` arg of a logging call lands at the top level of the
record, so downstream tooling can pivot on it (e.g. ``request_id``,
``duration_ms``, ``model``).

Never log child free-text answers or secrets — callers are responsible. The
formatter does not redact; it just structures.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

_RESERVED_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_ATTRS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging(level: str = "INFO") -> None:
    """Idempotently install the JSON formatter on the root logger.

    Safe to call repeatedly (tests/imports); the existing JSON handler is
    reused so we do not double-emit.
    """
    root = logging.getLogger()
    root.setLevel(level)
    for existing in root.handlers:
        if getattr(existing, "_ela_json", False):
            existing.setLevel(level)
            return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonLogFormatter())
    handler.setLevel(level)
    handler._ela_json = True  # type: ignore[attr-defined]
    root.addHandler(handler)
