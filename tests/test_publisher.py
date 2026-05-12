"""Sanity check publisher writes expected files."""
from src.pipeline import collector, publisher
from scripts.run_pipeline import cmd_process


def test_publisher_emits_docs(tmp_path, monkeypatch, isolated_state):
    from src import config
    monkeypatch.setattr(publisher, "DOCS_DIR", isolated_state / "docs")
    items = collector.collect_from_fixture()
    edition = cmd_process(items_override=items)
    publisher.publish(edition)

    docs = isolated_state / "docs"
    assert (docs / "index.html").exists()
    assert (docs / "archive.html").exists()
    assert (docs / "sitemap.xml").exists()
    assert (docs / "feed.xml").exists()
    assert (docs / "search-index.json").exists()
    assert (docs / "archive" / edition["date"] / "index.html").exists()
    assert (docs / "archive" / edition["date"] / "data.json").exists()
