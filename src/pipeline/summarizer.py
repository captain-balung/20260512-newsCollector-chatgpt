"""Summarize + Insight + Classify each article via AIClient (SRS §5)."""
from __future__ import annotations

import logging

from ..ai.client import AIClient
from ..config import get_settings
from ..models import Article

log = logging.getLogger(__name__)


def enrich(articles: list[Article]) -> list[Article]:
    """Mutate articles in-place with summary / insight / classification."""
    ai = AIClient()
    s = get_settings()
    valid_sections = set(s.section_ids)

    for a in articles:
        try:
            s_out = ai.summarize(title=a.title, url=a.url, description=a.description)
            a.title = s_out.get("title", a.title) or a.title
            a.summary = s_out.get("summary", "")
            a.importance = s_out.get("importance", "medium")
            a.tags = (s_out.get("tags") or [])[:5]

            i_out = ai.insight(title=a.title, summary=a.summary)
            a.insight = i_out.get("insight", "")
            a.perspective = i_out.get("perspective")
            a.market_impact = i_out.get("market_impact")

            c_out = ai.classify(title=a.title, summary=a.summary)
            sec = c_out.get("section")
            a.section = sec if sec in valid_sections else "giants_market"
        except Exception as e:  # noqa: BLE001
            log.warning("enrich failed for %s: %s", a.url, e)
            a.summary = a.summary or a.description[:200]
            a.section = a.section or "giants_market"
    return articles


def organise_into_sections(articles: list[Article]) -> list[dict]:
    """Group ranked articles into the 6 SRS §7 sections, respecting per-section quotas."""
    s = get_settings()
    pmin = s.system["pipeline"]["per_section_min"]
    pmax = s.system["pipeline"]["per_section_max"]

    by_section: dict[str, list[Article]] = {sid: [] for sid in s.section_ids}
    for a in sorted(articles, key=lambda x: x.final_score, reverse=True):
        sec = a.section or "giants_market"
        if sec not in by_section:
            sec = "giants_market"
        if len(by_section[sec]) < pmax:
            by_section[sec].append(a)

    # Backfill under-filled sections from overflow pool (best scores first)
    overflow = sorted(
        [a for a in articles if a not in sum(by_section.values(), [])],
        key=lambda x: x.final_score, reverse=True,
    )
    for sid, items in by_section.items():
        while len(items) < pmin and overflow:
            items.append(overflow.pop(0))

    out = []
    for sid in s.section_ids:
        meta = s.section_map[sid]
        out.append({
            "id": sid,
            "icon": meta["icon"],
            "label": meta["label"],
            "articles": [_article_dict(a) for a in by_section[sid]],
        })
    return out


def _article_dict(a: Article) -> dict:
    return {
        "title": a.title,
        "summary": a.summary,
        "insight": a.insight,
        "perspective": a.perspective,
        "importance": a.importance,
        "market_impact": a.market_impact,
        "source_url": a.url,
        "source_name": a.source_name,
        "confidence_score": a.source_confidence,
        "final_score": a.final_score,
        "scores": a.scores.model_dump(),
        "tags": a.tags,
        "embedding_id": a.embedding_id,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "section": a.section,
        "url_hash": a.url_hash,
    }
