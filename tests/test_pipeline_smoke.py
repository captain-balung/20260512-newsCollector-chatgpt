"""End-to-end smoke test using fixture items + mock AI. Validates JSON schema shape."""
import json
from datetime import datetime

from src.pipeline import collector
from scripts.run_pipeline import cmd_process


REQUIRED_TOP_LEVEL = {"schema_version", "generated_at", "pipeline_version", "date",
                      "dashboard", "sections"}


def test_smoke_runs_end_to_end_with_fixture():
    items = collector.collect_from_fixture()
    assert items, "fixture must not be empty"
    edition = cmd_process(items_override=items)

    assert REQUIRED_TOP_LEVEL.issubset(edition.keys())
    assert edition["date"]
    # at least one section non-empty
    assert any(sec.get("articles") for sec in edition["sections"])

    # Per-article required keys (subset of SRS §10.2)
    for sec in edition["sections"]:
        for a in sec.get("articles", []):
            assert {"title", "summary", "source_url", "source_name",
                    "confidence_score", "final_score"}.issubset(a.keys())

    # Schema serialisable
    json.dumps(edition, default=str)
