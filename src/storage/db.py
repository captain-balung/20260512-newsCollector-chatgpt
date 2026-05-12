"""SQLite state store for dedup, embeddings, trends, runs."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from ..config import DATA_DIR

DB_PATH = DATA_DIR / "db" / "state.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url_hash         TEXT PRIMARY KEY,
    url              TEXT NOT NULL,
    title            TEXT NOT NULL,
    source_id        TEXT NOT NULL,
    section          TEXT,
    final_score      REAL,
    published_at     TEXT,
    fetched_at       TEXT NOT NULL,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_articles_section ON articles(section);

CREATE TABLE IF NOT EXISTS embeddings (
    url_hash    TEXT PRIMARY KEY,
    vector_json TEXT NOT NULL,
    model       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (url_hash) REFERENCES articles(url_hash)
);

CREATE TABLE IF NOT EXISTS trends (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    window_days  INTEGER NOT NULL,
    keyword      TEXT NOT NULL,
    occurrences  INTEGER NOT NULL,
    velocity     REAL NOT NULL,
    samples_json TEXT NOT NULL,
    UNIQUE (date, window_days, keyword)
);
CREATE INDEX IF NOT EXISTS idx_trends_date ON trends(date);

CREATE TABLE IF NOT EXISTS narratives (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_title  TEXT NOT NULL,
    arc_json      TEXT NOT NULL,
    implication   TEXT,
    started_at    TEXT NOT NULL,
    ended_at      TEXT NOT NULL,
    UNIQUE (thread_title, started_at)
);

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,
    metrics_json TEXT
);

CREATE TABLE IF NOT EXISTS source_candidates (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    suggested_at TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,
    reason       TEXT,
    score        REAL,
    status       TEXT NOT NULL DEFAULT 'pending'
);
"""


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


# ---------- Articles -----------------------------------------------------

def article_exists(url_hash: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM articles WHERE url_hash = ?", (url_hash,)
        ).fetchone()
        return row is not None


def save_article(article_dict: dict) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO articles
                (url_hash, url, title, source_id, section, final_score,
                 published_at, fetched_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_dict["url_hash"],
                article_dict["url"],
                article_dict["title"],
                article_dict["source_id"],
                article_dict.get("section"),
                article_dict.get("final_score"),
                article_dict.get("published_at"),
                article_dict["fetched_at"],
                json.dumps(article_dict, ensure_ascii=False, default=str),
            ),
        )


def recent_article_titles(since: datetime) -> list[tuple[str, str]]:
    """Return (url_hash, title) since timestamp."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT url_hash, title FROM articles WHERE fetched_at >= ?",
            (since.isoformat(),),
        ).fetchall()
        return [(r["url_hash"], r["title"]) for r in rows]


def articles_in_window(days: int) -> list[dict]:
    cutoff = _iso_days_ago(days)
    with connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM articles WHERE fetched_at >= ? ORDER BY fetched_at DESC",
            (cutoff,),
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]


# ---------- Embeddings ---------------------------------------------------

def save_embedding(url_hash: str, vector: list[float], model: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO embeddings (url_hash, vector_json, model, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (url_hash, json.dumps(vector), model, datetime.utcnow().isoformat()),
        )


def recent_embeddings(days: int) -> list[tuple[str, list[float]]]:
    cutoff = _iso_days_ago(days)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT e.url_hash, e.vector_json
            FROM embeddings e
            JOIN articles a ON a.url_hash = e.url_hash
            WHERE a.fetched_at >= ?
            """,
            (cutoff,),
        ).fetchall()
        return [(r["url_hash"], json.loads(r["vector_json"])) for r in rows]


# ---------- Trends -------------------------------------------------------

def save_trend(date: str, window_days: int, keyword: str, occurrences: int,
               velocity: float, samples: list[str]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO trends
                (date, window_days, keyword, occurrences, velocity, samples_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (date, window_days, keyword, occurrences, velocity,
             json.dumps(samples, ensure_ascii=False)),
        )


def previous_trend_occurrences(window_days: int, keyword: str, before_date: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT occurrences FROM trends
            WHERE window_days = ? AND keyword = ? AND date < ?
            ORDER BY date DESC LIMIT 1
            """,
            (window_days, keyword, before_date),
        ).fetchone()
        return int(row["occurrences"]) if row else 0


# ---------- Narratives ---------------------------------------------------

def save_narrative(thread_title: str, arc: list[str], implication: str,
                   started_at: str, ended_at: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO narratives
                (thread_title, arc_json, implication, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (thread_title, json.dumps(arc, ensure_ascii=False), implication,
             started_at, ended_at),
        )


# ---------- Runs ---------------------------------------------------------

def start_run() -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs (started_at, status) VALUES (?, ?)",
            (datetime.utcnow().isoformat(), "running"),
        )
        return cur.lastrowid


def finish_run(run_id: int, status: str, metrics: dict) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE runs SET finished_at = ?, status = ?, metrics_json = ?
            WHERE id = ?
            """,
            (datetime.utcnow().isoformat(), status,
             json.dumps(metrics, ensure_ascii=False, default=str), run_id),
        )


def last_successful_run_metrics() -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT metrics_json FROM runs WHERE status = 'success' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return json.loads(row["metrics_json"]) if row and row["metrics_json"] else None


# ---------- Source candidates (Phase 3) ----------------------------------

def add_source_candidate(url: str, reason: str, score: float) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO source_candidates (suggested_at, url, reason, score)
            VALUES (?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), url, reason, score),
        )


def pending_source_candidates() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM source_candidates WHERE status = 'pending' ORDER BY score DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- helpers ------------------------------------------------------

def _iso_days_ago(days: int) -> str:
    from datetime import timedelta
    return (datetime.utcnow() - timedelta(days=days)).isoformat()
