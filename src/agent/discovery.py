"""Autonomous topic discovery (SRS Phase 3).

Looks at the long-tail of recent articles + emerging trend keywords and surfaces
topics that the current source list under-covers. Output is fed back to the human
operator (via Portal "intelligence" panel) rather than auto-applied.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from ..storage import db
from ..trend.topics import _is_cjk, _tokens_from


def discover_emerging_topics(*, max_candidates: int = 5,
                              window_days: int = 14) -> list[dict]:
    """Compare 14d topic frequency with 90d baseline; surface fast-rising terms."""
    today = datetime.utcnow().date().isoformat()
    recent = db.articles_in_window(days=window_days)
    baseline = db.articles_in_window(days=90)

    recent_counts = Counter(_tokens_from(recent))
    baseline_counts = Counter(_tokens_from(baseline))

    suggestions: list[dict] = []
    for kw, count in recent_counts.most_common(120):
        if count < 3:
            continue
        baseline_rate = baseline_counts.get(kw, 0) / max(1, len(baseline))
        recent_rate = count / max(1, len(recent))
        if baseline_rate == 0:
            growth = float(recent_rate * 100)
        else:
            growth = recent_rate / baseline_rate
        if growth < 3.0:
            continue
        suggestions.append({
            "keyword": kw,
            "occurrences_recent": count,
            "growth_ratio": round(growth, 2),
            "is_cjk": _is_cjk(kw),
            "discovered_at": today,
        })
    suggestions.sort(key=lambda x: -x["growth_ratio"])
    return suggestions[:max_candidates]
