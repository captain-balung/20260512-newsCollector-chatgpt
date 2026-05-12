"""Deduplicator (SRS §4.4, §4.5) — url_hash, title similarity, embedding similarity."""
from __future__ import annotations

import logging
import math
from typing import Iterable

from rapidfuzz import fuzz

from ..ai.client import AIClient
from ..config import get_settings
from ..models import Article
from ..storage import db

log = logging.getLogger(__name__)


def deduplicate(articles: list[Article]) -> tuple[list[Article], dict[str, int]]:
    """Return (kept, stats). Stats has counts for each dedup layer."""
    s = get_settings()
    cfg = s.scoring["dedup"]
    stats = {"by_url": 0, "by_title": 0, "by_embedding": 0, "by_db": 0}

    # Layer 0: drop if already in DB
    pre = []
    for a in articles:
        if cfg.get("url_hash") and db.article_exists(a.url_hash):
            stats["by_db"] += 1
            continue
        pre.append(a)

    # Layer 1: dedup within current batch by url_hash
    seen_urls: set[str] = set()
    layer1: list[Article] = []
    for a in pre:
        if a.url_hash in seen_urls:
            stats["by_url"] += 1
            continue
        seen_urls.add(a.url_hash)
        layer1.append(a)

    # Layer 2: title similarity
    title_thresh = float(cfg.get("title_similarity_threshold", 92))
    layer2: list[Article] = []
    for a in layer1:
        if any(_title_close(a, b, title_thresh) for b in layer2):
            stats["by_title"] += 1
            continue
        layer2.append(a)

    # Layer 3: embedding similarity
    emb_thresh = float(cfg.get("embedding_similarity_threshold", 0.88))
    ai = AIClient()
    kept: list[Article] = []
    kept_vecs: list[list[float]] = []
    # Also compare against recent DB embeddings (rolling 14d window)
    recent = db.recent_embeddings(days=14)

    for a in layer2:
        vec = ai.embed(a.title + " " + a.description[:400])
        a.embedding_id = a.url_hash
        # Compare with kept-in-batch
        dup = any(_cosine(vec, v) >= emb_thresh for v in kept_vecs)
        # Compare with DB
        if not dup:
            dup = any(_cosine(vec, v) >= emb_thresh for _, v in recent)
        if dup:
            stats["by_embedding"] += 1
            continue
        kept.append(a)
        kept_vecs.append(vec)
        db.save_embedding(a.url_hash, vec, model=ai.s.gemini_model_embed)

    log.info("dedup stats: %s; %d in → %d out", stats, len(articles), len(kept))
    return kept, stats


def _title_close(a: Article, b: Article, thresh: float) -> bool:
    return fuzz.token_set_ratio(a.title, b.title) >= thresh


def _cosine(u: Iterable[float], v: Iterable[float]) -> float:
    u_list, v_list = list(u), list(v)
    if len(u_list) != len(v_list) or not u_list:
        return 0.0
    dot = sum(x * y for x, y in zip(u_list, v_list))
    nu = math.sqrt(sum(x * x for x in u_list))
    nv = math.sqrt(sum(y * y for y in v_list))
    if nu == 0 or nv == 0:
        return 0.0
    return dot / (nu * nv)
