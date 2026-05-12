"""Self evaluation (SRS Phase 3) — compute pipeline health & content quality scores."""
from __future__ import annotations

from datetime import datetime
from statistics import mean

from ..config import get_settings


def evaluate_edition(edition: dict, *, dedup_stats: dict | None = None,
                     run_metrics: dict | None = None) -> dict:
    s = get_settings()
    sections = edition.get("sections", [])
    arts = [a for sec in sections for a in sec.get("articles", [])]

    if not arts:
        return {
            "overall": 0.0,
            "graded_at": datetime.utcnow().isoformat(),
            "components": {"coverage": 0, "diversity": 0, "quality": 0},
            "warnings": ["no articles in edition"],
        }

    # Coverage: how many sections have ≥ min quota
    pmin = s.system["pipeline"]["per_section_min"]
    sections_ok = sum(1 for sec in sections if len(sec.get("articles", [])) >= pmin)
    coverage = sections_ok / len(sections)

    # Diversity: ratio of distinct sources
    sources = {a.get("source_name") for a in arts}
    diversity = min(1.0, len(sources) / max(4, len(arts) / 2))

    # Quality: average final_score / 10
    quality = mean(float(a.get("final_score", 0)) for a in arts) / 10

    # Insight density
    insight_rate = sum(1 for a in arts if a.get("insight")) / len(arts)

    overall = round(
        coverage * 0.35 + diversity * 0.20 + quality * 0.30 + insight_rate * 0.15, 3
    )

    warnings = []
    if coverage < 0.8:
        warnings.append("section coverage below 80%")
    if len(arts) < s.system["pipeline"]["min_articles_for_publish"]:
        warnings.append("fewer than min articles for publish")
    if dedup_stats and sum(dedup_stats.values()) > len(arts) * 3:
        warnings.append("dedup-heavy fetch — sources may be redundant")

    return {
        "overall": overall,
        "graded_at": datetime.utcnow().isoformat(),
        "components": {
            "coverage": round(coverage, 3),
            "diversity": round(diversity, 3),
            "quality": round(quality, 3),
            "insight_rate": round(insight_rate, 3),
        },
        "warnings": warnings,
        "dedup_stats": dedup_stats or {},
        "run_metrics": run_metrics or {},
    }
