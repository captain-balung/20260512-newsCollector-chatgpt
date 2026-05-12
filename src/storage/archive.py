"""Archive a DailyEdition as JSON files on disk."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR


def archive_dir() -> Path:
    d = DATA_DIR / "archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_daily(edition: dict[str, Any]) -> Path:
    """Write daily JSON. Returns path of YYYY-MM-DD.json file."""
    date = edition["date"]
    path = archive_dir() / f"{date}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(edition, f, ensure_ascii=False, indent=2, default=str)

    # latest.json pointer
    latest = archive_dir() / "latest.json"
    with latest.open("w", encoding="utf-8") as f:
        json.dump(edition, f, ensure_ascii=False, indent=2, default=str)

    # index.json with summary list
    _update_index()
    return path


def _update_index() -> None:
    items = []
    for p in sorted(archive_dir().glob("*.json"), reverse=True):
        if p.name in ("index.json", "latest.json"):
            continue
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        items.append({
            "date": data.get("date"),
            "generated_at": data.get("generated_at"),
            "article_count": sum(len(s.get("articles", [])) for s in data.get("sections", [])),
        })
    with (archive_dir() / "index.json").open("w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.utcnow().isoformat(), "editions": items},
                  f, ensure_ascii=False, indent=2)


def read_daily(date: str) -> dict | None:
    p = archive_dir() / f"{date}.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_latest() -> dict | None:
    p = archive_dir() / "latest.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
