"""Token budget guard (SRS §14). Keeps an in-process tally; persisted in run metrics."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from ..config import DATA_DIR, get_settings

log = logging.getLogger(__name__)

STATE_FILE = DATA_DIR / "state" / "budget.json"


class BudgetGuard:
    """Tracks per-day and per-month token usage and enforces caps."""

    def __init__(self) -> None:
        self.s = get_settings()
        self._daily_used = 0
        self._monthly_used = 0
        self._by_kind: dict[str, int] = {}
        self._load()

    # ---- public ----------------------------------------------------------

    def allow(self, *, tokens: int, kind: str) -> bool:
        return self._within_caps(tokens)

    def charge(self, *, tokens: int, kind: str) -> None:
        self._daily_used += tokens
        self._monthly_used += tokens
        self._by_kind[kind] = self._by_kind.get(kind, 0) + tokens
        self._save()

    def snapshot(self) -> dict:
        return {
            "daily_used": self._daily_used,
            "monthly_used": self._monthly_used,
            "daily_budget": self.s.daily_token_budget,
            "monthly_budget": self.s.monthly_token_budget,
            "by_kind": dict(self._by_kind),
        }

    # ---- internal --------------------------------------------------------

    def _within_caps(self, tokens: int) -> bool:
        if self.s.daily_token_budget and self._daily_used + tokens > self.s.daily_token_budget:
            log.warning("daily token budget exceeded (%d/%d)",
                        self._daily_used + tokens, self.s.daily_token_budget)
            return False
        if self.s.monthly_token_budget and self._monthly_used + tokens > self.s.monthly_token_budget:
            log.warning("monthly token budget exceeded")
            return False
        return True

    def _load(self) -> None:
        if not STATE_FILE.exists():
            return
        import json
        try:
            data = json.loads(STATE_FILE.read_text())
        except Exception:
            return
        today = datetime.utcnow().date().isoformat()
        month = today[:7]
        if data.get("day") == today:
            self._daily_used = data.get("daily_used", 0)
        if data.get("month") == month:
            self._monthly_used = data.get("monthly_used", 0)
            self._by_kind = data.get("by_kind", {})

    def _save(self) -> None:
        import json
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        today = datetime.utcnow().date().isoformat()
        STATE_FILE.write_text(json.dumps({
            "day": today,
            "month": today[:7],
            "daily_used": self._daily_used,
            "monthly_used": self._monthly_used,
            "by_kind": self._by_kind,
        }, ensure_ascii=False))
