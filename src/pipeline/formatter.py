"""Formatter — produces HTML, JSON, Markdown from a DailyEdition (SRS §2.3, §10)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import DOCS_DIR, TEMPLATES_DIR, get_settings


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader([str(TEMPLATES_DIR / "portal"), str(TEMPLATES_DIR / "email")]),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def to_json(edition: dict) -> str:
    return json.dumps(edition, ensure_ascii=False, indent=2, default=str)


def to_markdown(edition: dict) -> str:
    s = get_settings()
    lines: list[str] = []
    lines.append(f"# {s.system['site']['title']} — {edition['date']}")
    lines.append("")
    lines.append(f"_Generated at {edition['generated_at']}_")
    lines.append("")

    dash = edition.get("dashboard") or {}
    if dash:
        lines.append("## 今日 AI 看板")
        for card in dash.get("cards", []):
            lines.append(f"- **{card['label']}**:{card['value']}")
        lines.append("")

    for sec in edition.get("sections", []):
        lines.append(f"## {sec['icon']} {sec['label']}")
        lines.append("")
        for a in sec.get("articles", []):
            lines.append(f"### [{a['title']}]({a['source_url']})")
            lines.append(f"*{a['source_name']} · score {a['final_score']} · {a.get('importance','')}*")
            lines.append("")
            lines.append(a.get("summary", ""))
            if a.get("insight"):
                lines.append("")
                lines.append(f"> **{a.get('perspective','觀點')}** — {a['insight']}")
            if a.get("market_impact"):
                lines.append("")
                lines.append(f"_市場影響:{a['market_impact']}_")
            lines.append("")

    trends = edition.get("trends") or []
    if trends:
        lines.append("## 趨勢雷達")
        for t in trends[:8]:
            lines.append(f"- `{t['window_days']}d` **{t['keyword']}** × {t['occurrences']}")
        lines.append("")

    narratives = edition.get("narratives") or []
    if narratives:
        lines.append("## 敘事追蹤")
        for n in narratives:
            lines.append(f"### {n['thread_title']}")
            for step in n.get("arc", []):
                lines.append(f"- {step}")
            if n.get("implication"):
                lines.append(f"\n_{n['implication']}_")
            lines.append("")

    return "\n".join(lines)


def to_portal_html(edition: dict) -> str:
    env = _env()
    tpl = env.get_template("article.html")
    s = get_settings()
    return tpl.render(
        edition=edition,
        site=s.system["site"],
        site_base_url=s.site_base_url,
        sections=s.system["sections"],
        now=datetime.utcnow(),
    )


def to_email_html(edition: dict) -> str:
    env = _env()
    tpl = env.get_template("email_html.html")
    s = get_settings()
    return tpl.render(
        edition=edition,
        site=s.system["site"],
        site_base_url=s.site_base_url,
    )


def to_email_plain(edition: dict) -> str:
    env = _env()
    tpl = env.get_template("email_plain.txt")
    return tpl.render(edition=edition, md=to_markdown(edition))


def write_outputs(edition: dict, *, output_dir: Path | None = None) -> dict[str, Path]:
    """Write JSON / Markdown / HTML alongside daily archive."""
    out_dir = output_dir or DOCS_DIR / "archive" / edition["date"]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    paths["json"] = out_dir / "data.json"
    paths["json"].write_text(to_json(edition), encoding="utf-8")

    paths["md"] = out_dir / "edition.md"
    paths["md"].write_text(to_markdown(edition), encoding="utf-8")

    paths["html"] = out_dir / "index.html"
    paths["html"].write_text(to_portal_html(edition), encoding="utf-8")

    return paths
