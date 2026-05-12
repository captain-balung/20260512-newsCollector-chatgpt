"""Narrative threading (SRS §6.2) — group articles into multi-day storylines."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

from ..ai.client import AIClient
from ..models import Narrative
from ..storage import db


def build_narratives(*, top_n: int = 3, window_days: int = 7) -> list[Narrative]:
    """Cluster recent articles by embedding similarity and ask LLM to narrate the arc."""
    articles = db.articles_in_window(days=window_days)
    if len(articles) < 4:
        return []

    embeddings = dict(db.recent_embeddings(days=window_days))
    clusters = _cluster_by_embedding(articles, embeddings, threshold=0.78)
    # Sort clusters by size, keep top_n with >= 3 items
    clusters = sorted([c for c in clusters if len(c) >= 3], key=len, reverse=True)[:top_n]

    ai = AIClient()
    out: list[Narrative] = []
    for cluster in clusters:
        cluster_sorted = sorted(
            cluster,
            key=lambda a: a.get("published_at") or a.get("fetched_at") or "",
        )
        timeline = "\n".join(
            f"- {(a.get('published_at') or a.get('fetched_at'))[:10]} · {a.get('title')}"
            for a in cluster_sorted
        )
        parsed = ai.narrative(timeline=timeline)
        if not parsed:
            continue
        narr = Narrative(
            thread_title=parsed.get("thread_title", "敘事追蹤")[:24],
            arc=list(parsed.get("arc") or [])[:8],
            implication=parsed.get("implication", "")[:240],
            started_at=datetime.fromisoformat(_get_dt(cluster_sorted[0])),
            ended_at=datetime.fromisoformat(_get_dt(cluster_sorted[-1])),
        )
        out.append(narr)
        db.save_narrative(narr.thread_title, narr.arc, narr.implication,
                          narr.started_at.isoformat(), narr.ended_at.isoformat())
    return out


def _cluster_by_embedding(articles: list[dict], embeddings: dict[str, list[float]],
                          threshold: float) -> list[list[dict]]:
    clusters: list[list[dict]] = []
    cluster_centroids: list[list[float]] = []
    for a in articles:
        vec = embeddings.get(a.get("url_hash"))
        if not vec:
            continue
        placed = False
        for i, centroid in enumerate(cluster_centroids):
            if _cosine(vec, centroid) >= threshold:
                clusters[i].append(a)
                cluster_centroids[i] = _avg(cluster_centroids[i], vec, len(clusters[i]))
                placed = True
                break
        if not placed:
            clusters.append([a])
            cluster_centroids.append(vec[:])
    return clusters


def _cosine(u: list[float], v: list[float]) -> float:
    if len(u) != len(v):
        return 0.0
    dot = sum(x * y for x, y in zip(u, v))
    nu = math.sqrt(sum(x * x for x in u))
    nv = math.sqrt(sum(y * y for y in v))
    return dot / (nu * nv) if nu and nv else 0.0


def _avg(centroid: list[float], new_vec: list[float], n: int) -> list[float]:
    return [(c * (n - 1) + nv) / n for c, nv in zip(centroid, new_vec)]


def _get_dt(article: dict) -> str:
    return article.get("published_at") or article.get("fetched_at") or datetime.utcnow().isoformat()
