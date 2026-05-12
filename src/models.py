"""Shared Pydantic models matching SRS §10 Data Schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Importance = Literal["low", "medium", "high", "critical"]


class Scores(BaseModel):
    relevance: float = 0.0
    novelty: float = 0.0
    impact: float = 0.0
    taiwan_related: float = 0.0
    market_signal: float = 0.0


class Article(BaseModel):
    """Internal representation of one news item — superset of SRS §10.2 Article Schema."""

    url: str
    url_hash: str
    title: str
    description: str = ""
    source_id: str
    source_name: str
    source_confidence: float
    fetched_at: datetime
    published_at: datetime | None = None

    # AI-enriched fields
    summary: str = ""
    insight: str = ""
    perspective: str | None = None
    importance: Importance | None = None
    market_impact: str | None = None
    tags: list[str] = Field(default_factory=list)
    section: str | None = None
    embedding_id: str | None = None

    # Scoring
    scores: Scores = Field(default_factory=Scores)
    final_score: float = 0.0

    # Raw payload for debugging
    raw: dict[str, Any] = Field(default_factory=dict)


class TrendTopic(BaseModel):
    keyword: str
    window_days: int
    occurrences: int
    velocity: float = 0.0
    samples: list[str] = Field(default_factory=list)


class Narrative(BaseModel):
    thread_title: str
    arc: list[str]
    implication: str
    started_at: datetime
    ended_at: datetime


class DashboardCard(BaseModel):
    label: str
    value: str
    trend: Literal["up", "down", "flat"] | None = None


class DailyEdition(BaseModel):
    """Top-level daily output, written to JSON archive (SRS §10.1)."""

    schema_version: str = "2.0"
    generated_at: datetime
    pipeline_version: str
    date: str  # YYYY-MM-DD
    dashboard: dict[str, Any] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    trends: list[TrendTopic] = Field(default_factory=list)
    narratives: list[Narrative] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
