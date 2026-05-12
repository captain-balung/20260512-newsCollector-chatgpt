from datetime import datetime, timezone

from src.models import Article
from src.pipeline.deduplicator import deduplicate


def _make(url, title, desc=""):
    return Article(
        url=url, url_hash=str(abs(hash(url)))[:16],
        title=title, description=desc,
        source_id="t", source_name="T", source_confidence=0.9,
        fetched_at=datetime.now(timezone.utc), published_at=None, raw={"tier": 1},
    )


def test_dedup_by_url():
    a = _make("https://a.com/x", "Same article")
    b = _make("https://a.com/x", "Same article")  # same url_hash via same url
    kept, stats = deduplicate([a, b])
    assert len(kept) == 1


def test_dedup_by_title_similarity():
    a = _make("https://a.com/x", "OpenAI 釋出 GPT 新版本 強化長上下文推理")
    b = _make("https://b.com/y", "OpenAI 釋出 GPT 新版本 - 強化長上下文推理 (轉載)")
    kept, stats = deduplicate([a, b])
    assert len(kept) == 1
    assert stats["by_title"] + stats["by_embedding"] >= 1
