from datetime import datetime, timezone

from src.models import Article
from src.pipeline.scorer import filter_publishable, score


def _make(title, conf=0.9, desc=""):
    return Article(
        url="https://example.com/x" + title,
        url_hash=("x" + title)[:16].ljust(16, "0"),
        title=title,
        description=desc,
        source_id="t", source_name="T", source_confidence=conf,
        fetched_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
        raw={"tier": 1},
    )


def test_score_assigns_final_score_in_range():
    arts = [_make("OpenAI 推出 GPT-5", desc="Major model launch")]
    score(arts)
    assert 0 <= arts[0].final_score <= 14  # tier bonus can push above 10


def test_filter_publishable_drops_below_threshold():
    arts = [_make("low impact", conf=0.3, desc="meh")]
    score(arts)
    assert filter_publishable(arts) == []
