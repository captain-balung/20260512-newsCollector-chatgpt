"""Normalize raw collector items into Article objects (SRS §2.3 Normalizer)."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from ..models import Article


def normalize(raw_items: list[dict[str, Any]]) -> list[Article]:
    out: list[Article] = []
    for it in raw_items:
        try:
            out.append(_one(it))
        except Exception:
            continue
    return out


def _one(it: dict[str, Any]) -> Article:
    url = (it.get("url") or "").strip()
    if not url:
        raise ValueError("missing url")
    canonical = _canonical(url)
    url_hash = it.get("url_hash") or hashlib.sha256(canonical.encode()).hexdigest()[:16]

    return Article(
        url=canonical,
        url_hash=url_hash,
        title=_norm_text(it.get("title", "")),
        description=_norm_text(it.get("description", "")),
        source_id=it["source_id"],
        source_name=it.get("source_name", it["source_id"]),
        source_confidence=float(it.get("source_confidence", 0.7)),
        fetched_at=_parse_dt(it.get("fetched_at")) or datetime.utcnow(),
        published_at=_parse_dt(it.get("published_at")),
        raw=it,
    )


def _canonical(url: str) -> str:
    u = url.strip().split("#")[0]
    if "?" in u:
        base, q = u.split("?", 1)
        keep = [p for p in q.split("&") if not p.startswith(("utm_", "fbclid=", "gclid="))]
        u = base + ("?" + "&".join(keep) if keep else "")
    return u.rstrip("/")


def _norm_text(s: str) -> str:
    return " ".join((s or "").split())


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None
