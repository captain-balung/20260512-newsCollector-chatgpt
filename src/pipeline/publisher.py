"""Publisher (SRS §2.3, §9, §16 publish.yml). Writes docs/ for GitHub Pages + indexes."""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import DOCS_DIR, TEMPLATES_DIR, get_settings
from ..storage import archive

log = logging.getLogger(__name__)


def publish(edition: dict) -> dict[str, Path]:
    """Idempotent publish: write JSON archive, render Portal pages, copy assets."""
    s = get_settings()
    written: dict[str, Path] = {}

    archive.write_daily(edition)
    written["archive_json"] = (s := get_settings()) and (Path(s.system["site"]["title"]) and None)  # no-op for type
    written["archive_json"] = (Path(_docs_archive(edition["date"])) / "data.json")
    _docs_archive(edition["date"]).mkdir(parents=True, exist_ok=True)
    _docs_archive(edition["date"]).joinpath("data.json").write_text(
        json.dumps(edition, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    _render_portal(edition)
    _write_search_index()
    _copy_assets()
    _write_sitemap()
    _write_robots()
    _write_rss()

    return written


# ---- internal --------------------------------------------------------------

def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR / "portal")),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _render_portal(edition: dict) -> None:
    s = get_settings()
    env = _env()
    site = s.system["site"]
    base = s.site_base_url
    prefix = s.site_path_prefix
    common = dict(site=site, site_base_url=base, path_prefix=prefix,
                  sections=s.system["sections"])

    # 1) Today's article page under docs/archive/<date>/index.html
    art_dir = _docs_archive(edition["date"])
    art_dir.mkdir(parents=True, exist_ok=True)
    art_dir.joinpath("index.html").write_text(
        env.get_template("article.html").render(
            edition=edition, now=datetime.utcnow(), **common),
        encoding="utf-8",
    )

    # 2) Update homepage with latest edition
    editions = _list_editions()
    DOCS_DIR.joinpath("index.html").write_text(
        env.get_template("index.html").render(
            edition=edition, editions=editions[:30],
            now=datetime.utcnow(), **common),
        encoding="utf-8",
    )

    # 3) Archive list page
    DOCS_DIR.joinpath("archive.html").write_text(
        env.get_template("archive.html").render(
            editions=editions, now=datetime.utcnow(), **common),
        encoding="utf-8",
    )

    # 4) 404
    DOCS_DIR.joinpath("404.html").write_text(
        env.get_template("404.html").render(
            site=site, site_base_url=base, path_prefix=prefix),
        encoding="utf-8",
    )


def _write_search_index() -> None:
    """Aggregate every published article into a flat searchable JSON for client-side search."""
    items = []
    for ed_dir in sorted(DOCS_DIR.joinpath("archive").glob("*/"), reverse=True):
        data_path = ed_dir / "data.json"
        if not data_path.exists():
            continue
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        date = data.get("date")
        for sec in data.get("sections", []):
            for a in sec.get("articles", []):
                items.append({
                    "date": date,
                    "title": a.get("title"),
                    "summary": a.get("summary"),
                    "insight": a.get("insight"),
                    "tags": a.get("tags", []),
                    "section": sec.get("id"),
                    "section_label": sec.get("label"),
                    "source_url": a.get("source_url"),
                    "source_name": a.get("source_name"),
                    "url_hash": a.get("url_hash"),
                    "permalink": f"{get_settings().site_path_prefix}/archive/{date}/#{a.get('url_hash')}",
                })
    DOCS_DIR.joinpath("search-index.json").write_text(
        json.dumps({"updated_at": datetime.utcnow().isoformat(), "items": items},
                   ensure_ascii=False),
        encoding="utf-8",
    )


def _copy_assets() -> None:
    src = TEMPLATES_DIR / "portal" / "assets"
    dst = DOCS_DIR / "assets"
    if src.exists():
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)


def _write_sitemap() -> None:
    s = get_settings()
    base = s.site_base_url
    editions = _list_editions()
    urls = [base + "/", base + "/archive.html"] + [
        f"{base}/archive/{e['date']}/" for e in editions
    ]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = datetime.utcnow().date().isoformat()
    for u in urls:
        body.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    body.append("</urlset>")
    DOCS_DIR.joinpath("sitemap.xml").write_text("\n".join(body), encoding="utf-8")


def _write_robots() -> None:
    s = get_settings()
    DOCS_DIR.joinpath("robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {s.site_base_url}/sitemap.xml\n",
        encoding="utf-8",
    )


def _write_rss() -> None:
    s = get_settings()
    editions = _list_editions()[:30]
    items = []
    for e in editions:
        items.append(
            f"  <item>"
            f"<title>{s.system['site']['title']} {e['date']}</title>"
            f"<link>{s.site_base_url}/archive/{e['date']}/</link>"
            f"<guid>{s.site_base_url}/archive/{e['date']}/</guid>"
            f"<description>{e.get('article_count',0)} articles</description>"
            f"</item>"
        )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{s.system['site']['title']}</title>
    <link>{s.site_base_url}</link>
    <description>{s.system['site']['subtitle']}</description>
{chr(10).join(items)}
  </channel>
</rss>"""
    DOCS_DIR.joinpath("feed.xml").write_text(body, encoding="utf-8")


def _list_editions() -> list[dict]:
    out = []
    for ed_dir in sorted(DOCS_DIR.joinpath("archive").glob("*/"), reverse=True):
        data_path = ed_dir / "data.json"
        if not data_path.exists():
            continue
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({
            "date": data.get("date"),
            "generated_at": data.get("generated_at"),
            "article_count": sum(len(s.get("articles", [])) for s in data.get("sections", [])),
            "url": f"archive/{data.get('date')}/",
        })
    return out


def _docs_archive(date: str) -> Path:
    return DOCS_DIR / "archive" / date
