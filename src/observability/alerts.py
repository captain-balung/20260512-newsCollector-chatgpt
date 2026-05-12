"""Alerting (SRS §11.3). Posts to webhook if configured; otherwise logs."""
from __future__ import annotations

import json
import logging
from typing import Iterable

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)


def check_alerts(*, edition: dict | None, email_ok: bool, pipeline_errors: Iterable[str],
                 publish_ok: bool) -> list[str]:
    s = get_settings()
    fired: list[str] = []

    min_arts = s.system["pipeline"]["min_articles_for_publish"]
    if edition is None:
        fired.append("AI generation failed — no edition produced")
    else:
        total = sum(len(sec.get("articles", [])) for sec in edition.get("sections", []))
        if total < min_arts:
            fired.append(f"Article count below minimum: {total} < {min_arts}")
    if not email_ok:
        fired.append("Email delivery failed")
    if not publish_ok:
        fired.append("GitHub publish failed")
    errs = [e for e in pipeline_errors if e]
    if errs:
        fired.append("Pipeline errors: " + "; ".join(errs[:3]))

    if fired:
        _dispatch(fired)
    return fired


def _dispatch(messages: list[str]) -> None:
    s = get_settings()
    text = "🚨 Daily AI Insights alert:\n- " + "\n- ".join(messages)
    if not s.alert_webhook_url:
        log.warning(text)
        return
    try:
        with httpx.Client(timeout=10) as c:
            c.post(s.alert_webhook_url,
                   json={"text": text},
                   headers={"Content-Type": "application/json"})
    except Exception as e:  # noqa: BLE001
        log.warning("alert webhook failed: %s; payload=%s", e, json.dumps(messages))
