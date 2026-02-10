from __future__ import annotations

import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Format logs as structured JSON for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "path"):
            payload["path"] = record.path
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    """Create or reuse a configured JSON logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
