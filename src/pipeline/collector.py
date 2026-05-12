"""Collector — fetch articles from configured sources (SRS §3, §16 fetch.yml)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from ..config import DATA_DIR, get_settings
from ..recovery.retry import retry

log = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "cache"
USER_AGENT = "DailyAIInsightsBot/2.0 (+https://github.com/captain-balung/daily-ai-insights)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def collect_all() -> list[dict[str, Any]]:
    """Fetch from every enabled source. Returns list of raw items (not yet normalised)."""
    s = get_settings()
    items: list[dict[str, Any]] = []
    for src in s.sources.get("sources", []):
        if not src.get("enabled", True):
            continue
        try:
            fetched = _fetch_one(src)
            log.info("collected %d items from %s", len(fetched), src["id"])
            items.extend(fetched)
        except Exception as e:  # noqa: BLE001
            log.warning("source %s failed: %s — using cache if available", src["id"], e)
            cached = _load_cache(src["id"])
            if cached:
                items.extend(cached)
    return items


def _fetch_one(src: dict) -> list[dict[str, Any]]:
    handler = {
        "rss": _fetch_rss,
        "hn_api": _fetch_hn,
        "github_trending": _fetch_github_trending,
    }.get(src["type"])
    if handler is None:
        log.warning("unknown source type %s", src["type"])
        return []
    items = retry(lambda: handler(src), op_name=f"fetch:{src['id']}")
    _save_cache(src["id"], items)
    return items


def _fetch_rss(src: dict) -> list[dict[str, Any]]:
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(src["url"], follow_redirects=True)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
    limit = _limit_for_tier(src["tier"])
    out = []
    for e in parsed.entries[:limit]:
        url = e.get("link") or ""
        if not url:
            continue
        out.append(_make_item(
            src=src,
            url=url,
            title=_text(e.get("title", "")),
            description=_text(e.get("summary", "") or e.get("description", "")),
            published_at=_parse_pub(e),
        ))
    return out


def _fetch_hn(src: dict) -> list[dict[str, Any]]:
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as c:
        ids = c.get(src["url"]).json()[:30]
        out = []
        for i in ids:
            item = c.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json()
            if not item or item.get("type") != "story":
                continue
            title = item.get("title", "")
            url = item.get("url") or f"https://news.ycombinator.com/item?id={i}"
            if not _is_ai_relevant(title):
                continue
            out.append(_make_item(
                src=src,
                url=url,
                title=title,
                description=item.get("text", ""),
                published_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
            ))
            if len(out) >= _limit_for_tier(src["tier"]):
                break
    return out


def _fetch_github_trending(src: dict) -> list[dict[str, Any]]:
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(src["url"], follow_redirects=True)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    out = []
    for article in soup.select("article.Box-row")[: _limit_for_tier(src["tier"])]:
        a = article.select_one("h2 a")
        if not a:
            continue
        repo = a.get_text(strip=True).replace("\n", "").replace(" ", "")
        url = "https://github.com" + a["href"]
        desc_el = article.select_one("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        if not _is_ai_relevant(repo + " " + desc):
            continue
        out.append(_make_item(
            src=src, url=url, title=f"GitHub Trending: {repo}",
            description=desc, published_at=datetime.now(timezone.utc),
        ))
    return out


# ---------------- helpers ---------------------------------------------------

def _make_item(*, src: dict, url: str, title: str, description: str,
               published_at: datetime | None) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc)
    url_hash = hashlib.sha256(_canonical_url(url).encode()).hexdigest()[:16]
    return {
        "url": url,
        "url_hash": url_hash,
        "title": title.strip(),
        "description": description.strip(),
        "source_id": src["id"],
        "source_name": src["name"],
        "source_confidence": src.get("confidence", 0.7),
        "tier": src["tier"],
        "published_at": published_at.isoformat() if published_at else None,
        "fetched_at": fetched_at.isoformat(),
    }


def _canonical_url(url: str) -> str:
    return url.split("#")[0].split("?utm_")[0].rstrip("/")


def _text(s: str) -> str:
    if not s:
        return ""
    return BeautifulSoup(s, "lxml").get_text(" ", strip=True)


def _parse_pub(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _is_ai_relevant(text: str) -> bool:
    t = text.lower()
    keywords = ["ai", "llm", "gpt", "claude", "gemini", "llama", "anthropic",
                "openai", "agent", "ml ", "neural", "transformer", "diffusion",
                "rag", "embedding", "model"]
    return any(k in t for k in keywords)


def _limit_for_tier(tier: int) -> int:
    s = get_settings()
    return int(s.sources.get("tier_defaults", {}).get(tier, {}).get("fetch_limit", 20))


def _save_cache(source_id: str, items: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{source_id}.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2)
    )


def _load_cache(source_id: str) -> list[dict] | None:
    p = CACHE_DIR / f"{source_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


# ----- offline fixture: used by tests + first-run smoke when no network -----

def collect_from_fixture(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or (Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "sample_items.json")
    if not p.exists():
        return []
    return json.loads(p.read_text())
