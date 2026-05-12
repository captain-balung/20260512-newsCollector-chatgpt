"""Scoring engine (SRS §4.1, §4.2, §4.3). Heuristic-based; AI scoring layered on top."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import get_settings
from ..models import Article, Scores

log = logging.getLogger(__name__)


def score(articles: list[Article]) -> list[Article]:
    s = get_settings()
    weights = s.scoring["weights"]
    boosts = s.scoring.get("keyword_boosts", {})
    tier_bonus = s.sources.get("tier_defaults", {})

    for a in articles:
        sc = Scores(
            relevance=_relevance(a, boosts),
            novelty=_novelty(a),
            impact=_impact(a, boosts),
            taiwan_related=_keyword_hits(a, boosts.get("taiwan_related", [])),
            market_signal=_keyword_hits(a, boosts.get("market_signal", [])),
        )
        # Tier bonus applies multiplicatively to final
        bonus = float(tier_bonus.get(a.raw.get("tier") or 2, {}).get("weight_bonus", 1.0))
        a.scores = sc
        a.final_score = round(
            (
                sc.relevance * weights["relevance"]
                + sc.novelty * weights["novelty"]
                + sc.impact * weights["impact"]
                + sc.taiwan_related * weights["taiwan_related"]
                + sc.market_signal * weights["market_signal"]
            ) * bonus,
            3,
        )
    return articles


def filter_publishable(articles: list[Article]) -> list[Article]:
    s = get_settings()
    th = s.scoring["thresholds"]
    return [
        a for a in articles
        if a.final_score >= float(th["final_score_min"])
        and a.source_confidence >= float(th["source_confidence_min"])
    ]


# ---- per-axis heuristics ---------------------------------------------------

def _relevance(a: Article, boosts: dict) -> float:
    """0-10. Mix of source tier confidence + keyword density."""
    base = a.source_confidence * 10.0  # 0..10
    haystack = (a.title + " " + a.description).lower()
    hits = sum(1 for kw in boosts.get("high_impact", []) if kw.lower() in haystack)
    return min(10.0, base + min(hits * 1.5, 3.0))


def _novelty(a: Article) -> float:
    """0-10. Newer = higher; demoted if very long-form or very short."""
    if not a.published_at:
        return 6.0
    age_h = max(0.0, (datetime.now(timezone.utc) - a.published_at).total_seconds() / 3600)
    # 100% at age 0, decays to 50% at 36h, near-zero after 96h
    score = 10.0 * max(0.0, 1.0 - age_h / 96.0)
    return round(score, 2)


def _impact(a: Article, boosts: dict) -> float:
    """0-10. Keyword hits + length signal."""
    haystack = (a.title + " " + a.description).lower()
    keys = boosts.get("high_impact", [])
    hits = sum(1 for kw in keys if kw.lower() in haystack)
    desc_len = len(a.description)
    length_bonus = 1.0 if 200 <= desc_len <= 1500 else 0.0
    return min(10.0, 5.0 + hits * 1.5 + length_bonus)


def _keyword_hits(a: Article, words: list[str]) -> float:
    """0-10 based on raw keyword matches."""
    if not words:
        return 0.0
    haystack = (a.title + " " + a.description).lower()
    hits = sum(1 for w in words if w.lower() in haystack)
    return min(10.0, hits * 3.0)
