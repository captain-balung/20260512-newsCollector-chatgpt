"""CLI entry point for the daily pipeline.

Usage:
  python -m scripts.run_pipeline all       # everything end-to-end
  python -m scripts.run_pipeline fetch     # only fetch sources -> data/cache
  python -m scripts.run_pipeline process   # fetch (or use cache) + AI -> data/archive
  python -m scripts.run_pipeline publish   # publish today's archive -> docs/ + email
  python -m scripts.run_pipeline smoke     # offline smoke with tests/fixtures
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent.discovery import discover_emerging_topics  # noqa: E402
from src.agent.evaluator import evaluate_edition  # noqa: E402
from src.agent.source_expander import suggest_new_sources  # noqa: E402
from src.config import DATA_DIR, get_settings  # noqa: E402
from src.emailer.sender import send_daily  # noqa: E402
from src.observability.alerts import check_alerts  # noqa: E402
from src.observability.logger import configure as configure_logging  # noqa: E402
from src.observability.metrics import Metrics  # noqa: E402
from src.pipeline import (collector, deduplicator, formatter, normalizer,  # noqa: E402
                          publisher, scorer, summarizer)
from src.recovery.fallback import emergency_edition_stub  # noqa: E402
from src.storage import archive, db  # noqa: E402
from src.trend.narrative import build_narratives  # noqa: E402
from src.trend.policy_radar import flag_taiwan_policy  # noqa: E402
from src.trend.topics import compute_trends  # noqa: E402

log = logging.getLogger("dai.pipeline")

PIPELINE_VERSION = "2.0.0"


def cmd_fetch() -> None:
    items = collector.collect_all()
    out = DATA_DIR / "cache" / "_combined.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2))
    log.info("fetched %d items -> %s", len(items), out)


def cmd_process(*, items_override: list[dict] | None = None) -> dict:
    s = get_settings()
    db.init_db()
    metrics = Metrics()
    run_id = db.start_run()
    errors: list[str] = []

    try:
        metrics.timer_start("fetch")
        raw = items_override if items_override is not None else collector.collect_all()
        metrics.timer_stop("fetch")
        metrics.inc("articles_fetched", len(raw))

        articles = normalizer.normalize(raw)

        metrics.timer_start("dedup")
        deduped, dedup_stats = deduplicator.deduplicate(articles)
        metrics.timer_stop("dedup")
        metrics.gauge("dedup_drop_total", sum(dedup_stats.values()))

        metrics.timer_start("score")
        scorer.score(deduped)
        flag_taiwan_policy(deduped)
        publishable = scorer.filter_publishable(deduped)
        metrics.timer_stop("score")
        metrics.inc("articles_filtered", len(publishable))

        metrics.timer_start("ai_enrich")
        summarizer.enrich(publishable)
        metrics.timer_stop("ai_enrich")

        # persist enriched articles before sectioning
        for a in publishable:
            db.save_article({
                **a.model_dump(),
                "fetched_at": a.fetched_at.isoformat(),
                "published_at": a.published_at.isoformat() if a.published_at else None,
            })

        sections = summarizer.organise_into_sections(publishable)

        # Phase 2
        trends = [t.model_dump() for t in compute_trends()]
        narratives = [n.model_dump() for n in build_narratives()]

        # Phase 3
        discovery = discover_emerging_topics()
        suggested_sources = suggest_new_sources(publishable)

        edition = _build_edition(
            sections=sections,
            trends=trends,
            narratives=narratives,
            discovery=discovery,
            suggested_sources=suggested_sources,
            metrics_snapshot=metrics.snapshot(),
        )

        # Self-evaluation
        evaluation = evaluate_edition(edition, dedup_stats=dedup_stats,
                                      run_metrics=metrics.snapshot())
        edition["evaluation"] = evaluation
        metrics.gauge("eval_overall", float(evaluation.get("overall", 0)))

        archive.write_daily(edition)
        log.info("edition written (%d articles, eval=%.2f)",
                 sum(len(s.get('articles', [])) for s in sections),
                 evaluation.get("overall", 0))
        db.finish_run(run_id, "success", metrics.snapshot())
        return edition
    except Exception as e:  # noqa: BLE001
        log.exception("process failed: %s", e)
        errors.append(str(e))
        db.finish_run(run_id, "failed", {"error": str(e), **metrics.snapshot()})
        return emergency_edition_stub()


def cmd_publish() -> None:
    s = get_settings()
    today = datetime.utcnow().date().isoformat()
    edition = archive.read_daily(today) or archive.read_latest()
    if not edition:
        log.error("no edition to publish")
        check_alerts(edition=None, email_ok=False,
                     pipeline_errors=["no edition file"], publish_ok=False)
        return

    publish_ok = True
    email_ok = True
    try:
        publisher.publish(edition)
    except Exception as e:  # noqa: BLE001
        log.exception("publish failed")
        publish_ok = False

    try:
        html = formatter.to_email_html(edition)
        plain = formatter.to_email_plain(edition)
        subject = f"[{s.system['site']['title']}] {edition['date']} 今日 AI 情報"
        res = send_daily(subject, html=html, plain=plain)
        email_ok = res.ok
    except Exception as e:  # noqa: BLE001
        log.exception("email failed")
        email_ok = False

    check_alerts(edition=edition, email_ok=email_ok,
                 pipeline_errors=[], publish_ok=publish_ok)


def cmd_smoke() -> None:
    items = collector.collect_from_fixture()
    if not items:
        log.error("no fixture items found")
        sys.exit(1)
    edition = cmd_process(items_override=items)
    cmd_publish()
    print(json.dumps({
        "date": edition.get("date"),
        "sections": [
            {"id": sec["id"], "count": len(sec["articles"])}
            for sec in edition.get("sections", [])
        ],
        "trends": len(edition.get("trends", [])),
        "narratives": len(edition.get("narratives", [])),
        "evaluation": edition.get("evaluation", {}).get("overall"),
    }, ensure_ascii=False, indent=2))


def cmd_all() -> None:
    cmd_fetch()
    cmd_process()
    cmd_publish()


# ---- helpers ---------------------------------------------------------------

def _build_edition(*, sections: list[dict], trends: list[dict], narratives: list[dict],
                   discovery: Iterable[dict], suggested_sources: Iterable[dict],
                   metrics_snapshot: dict) -> dict:
    total = sum(len(s.get("articles", [])) for s in sections)
    sources = {a["source_name"] for sec in sections for a in sec.get("articles", [])}
    high_imp = sum(1 for sec in sections for a in sec.get("articles", [])
                   if a.get("importance") in {"high", "critical"})

    return {
        "schema_version": "2.0",
        "generated_at": datetime.utcnow().isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "date": datetime.utcnow().date().isoformat(),
        "dashboard": {
            "cards": [
                {"label": "今日新聞", "value": str(total)},
                {"label": "來源數", "value": str(len(sources))},
                {"label": "高影響事件", "value": str(high_imp)},
                {"label": "趨勢主題", "value": str(len(trends))},
            ]
        },
        "sections": sections,
        "trends": trends,
        "narratives": narratives,
        "intelligence": {
            "emerging_topics": list(discovery),
            "suggested_sources": list(suggested_sources),
        },
        "metrics": metrics_snapshot,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command",
                        choices=["all", "fetch", "process", "publish", "smoke"])
    args = parser.parse_args()
    configure_logging()
    {
        "all": cmd_all,
        "fetch": cmd_fetch,
        "process": cmd_process,
        "publish": cmd_publish,
        "smoke": cmd_smoke,
    }[args.command]()


if __name__ == "__main__":
    main()
