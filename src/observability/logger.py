"""Structured logging (SRS §11.2). JSON line logs go to data/state/pipeline.log."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from ..config import DATA_DIR, get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure() -> None:
    s = get_settings()
    log_dir = DATA_DIR / "state"
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, s.log_level.upper(), logging.INFO))

    # Stream (human readable)
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s"))
    root.addHandler(stream)

    # File (JSON for ingestion)
    file_h = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
    file_h.setFormatter(JsonFormatter())
    root.addHandler(file_h)
