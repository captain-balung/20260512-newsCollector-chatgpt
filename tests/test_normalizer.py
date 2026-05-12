from src.pipeline.normalizer import normalize


def test_normalize_preserves_required_fields():
    raw = [{
        "url": "https://example.com/a?utm_source=foo#x",
        "title": "  hello   world  ",
        "description": "<p>desc</p>",
        "source_id": "x", "source_name": "X", "source_confidence": 0.8,
        "tier": 1,
        "fetched_at": "2026-05-12T01:00:00+00:00",
        "published_at": "2026-05-12T00:00:00Z",
    }]
    out = normalize(raw)
    assert len(out) == 1
    a = out[0]
    assert a.url.endswith("/a")
    assert a.title == "hello world"
    assert a.source_confidence == 0.8


def test_normalize_skips_invalid():
    out = normalize([{"title": "missing url"}])
    assert out == []
