"""Shared pytest fixtures — isolate DB / cache / docs to a temp dir per test session."""
import os
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("USE_MOCK", "1")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Redirect DATA_DIR / DOCS_DIR to tmp so tests don't pollute repo."""
    from src import config

    tmp_data = tmp_path / "data"
    tmp_docs = tmp_path / "docs"
    (tmp_data / "cache").mkdir(parents=True)
    (tmp_data / "db").mkdir(parents=True)
    (tmp_data / "state").mkdir(parents=True)
    (tmp_data / "archive").mkdir(parents=True)
    tmp_docs.mkdir(parents=True)

    monkeypatch.setattr(config, "DATA_DIR", tmp_data)
    monkeypatch.setattr(config, "DOCS_DIR", tmp_docs)
    # ensure modules that closed over the old path are refreshed
    from src.storage import db as storage_db
    monkeypatch.setattr(storage_db, "DB_PATH", tmp_data / "db" / "state.sqlite")
    storage_db.init_db()
    yield tmp_path
    # cleanup is automatic via tmp_path
