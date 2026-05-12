"""Source expansion candidates (SRS Phase 3).

We DO NOT auto-add sources to config/sources.yaml. Instead we surface
candidate URLs (e.g. from Hacker News outlinks pointing to AI-related domains
not yet in our list) in the DB for human review.
"""
from __future__ import annotations

import logging
from collections import Counter
from urllib.parse import urlparse

from ..config import get_settings
from ..models import Article
from ..storage import db

log = logging.getLogger(__name__)


def suggest_new_sources(articles: list[Article]) -> list[dict]:
    """Look for domains showing up repeatedly outside our existing source list."""
    s = get_settings()
    known_hosts = set()
    for src in s.sources.get("sources", []):
        try:
            known_hosts.add(urlparse(src["url"]).netloc.lower())
        except Exception:
            continue

    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for a in articles:
        host = urlparse(a.url).netloc.lower()
        if not host or host in known_hosts:
            continue
        counts[host] += 1
        samples.setdefault(host, []).append(a.title)

    suggestions = []
    for host, n in counts.most_common(10):
        if n < 2:
            continue
        candidate_url = f"https://{host}/feed"
        score = min(10.0, n * 1.5)
        suggestions.append({
            "host": host,
            "url": candidate_url,
            "count": n,
            "score": score,
            "reason": f"{n} articles from {host} in last batch; sample: "
                      + " · ".join(samples[host][:2]),
        })
        db.add_source_candidate(url=candidate_url, reason=suggestions[-1]["reason"], score=score)
    return suggestions
