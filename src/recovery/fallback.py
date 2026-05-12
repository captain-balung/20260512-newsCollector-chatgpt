"""Fallback strategy (SRS §12.2)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..config import DATA_DIR
from ..storage import archive, db

log = logging.getLogger(__name__)


def previous_successful_edition() -> dict | None:
    """Reuse yesterday's edition payload (with a retitled date) when today's pipeline fails."""
    metrics = db.last_successful_run_metrics()
    if not metrics:
        log.info("no prior successful run found for fallback")
    latest = archive.read_latest()
    if not latest:
        return None
    log.warning("falling back to previous edition dated %s", latest.get("date"))
    return latest


def cached_collector_items(source_id: str) -> list[dict] | None:
    p: Path = DATA_DIR / "cache" / f"{source_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def emergency_edition_stub(date: str | None = None) -> dict:
    """Last-ditch placeholder if everything is broken — keeps publish step working."""
    date = date or datetime.utcnow().date().isoformat()
    return {
        "schema_version": "2.0",
        "generated_at": datetime.utcnow().isoformat(),
        "pipeline_version": "fallback",
        "date": date,
        "dashboard": {
            "cards": [
                {"label": "狀態", "value": "Pipeline 降級 (fallback)"},
                {"label": "說明", "value": "今日資料蒐集異常,顯示上次成功版本"},
            ]
        },
        "sections": [],
        "trends": [],
        "narratives": [],
        "metrics": {"fallback": True},
    }
