"""Topic / keyword trend tracking (SRS §6.3)."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Iterable

from ..config import get_settings
from ..models import TrendTopic
from ..storage import db

# Very simple keyword extraction — splits CJK + word chars, lowercases.
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-]+|[一-龥]{2,}")

STOPWORDS_EN = {
    "the", "and", "for", "with", "from", "this", "that", "are", "was",
    "have", "has", "but", "you", "our", "your", "their", "more", "less",
    "than", "into", "about", "also", "than", "while", "where", "after",
    "before", "what", "which", "when", "ai", "model", "data", "use",
    "using", "based",
}
STOPWORDS_TW = {"今天", "我們", "他們", "以及", "可以", "因為", "但是", "現在",
                "未來", "本週", "目前", "新聞", "報導", "表示", "宣布"}


def compute_trends(*, today: str | None = None) -> list[TrendTopic]:
    s = get_settings()
    today = today or datetime.utcnow().date().isoformat()
    windows = s.system["trend"]["windows_days"]
    min_recur = s.system["trend"]["min_recurrence"]
    top_n = s.system["trend"]["top_topics"]

    all_topics: list[TrendTopic] = []
    for w in windows:
        articles = db.articles_in_window(days=w)
        tokens = _tokens_from(articles)
        counter = Counter(tokens)
        for keyword, count in counter.most_common(top_n * 3):
            if count < min_recur:
                continue
            prev = db.previous_trend_occurrences(window_days=w, keyword=keyword, before_date=today)
            velocity = (count - prev) / max(1, prev) if prev else float(count)
            samples = [a["title"] for a in articles
                       if keyword.lower() in (a.get("title", "").lower())][:3]
            t = TrendTopic(keyword=keyword, window_days=w,
                           occurrences=count, velocity=round(velocity, 3),
                           samples=samples)
            all_topics.append(t)
            db.save_trend(date=today, window_days=w, keyword=keyword,
                          occurrences=count, velocity=t.velocity, samples=samples)
        # Limit per window
    # Sort: higher velocity first within window, but mix windows interleaved
    all_topics.sort(key=lambda t: (-t.velocity, -t.occurrences))
    return all_topics[: top_n * len(windows)]


def _tokens_from(articles: Iterable[dict]) -> list[str]:
    out: list[str] = []
    for a in articles:
        text = " ".join([
            a.get("title", "") or "",
            a.get("summary", "") or "",
            " ".join(a.get("tags", []) or []),
        ])
        for m in TOKEN_RE.findall(text):
            m_lower = m.lower()
            if m_lower in STOPWORDS_EN or m in STOPWORDS_TW:
                continue
            if len(m_lower) < 3 and not _is_cjk(m_lower):
                continue
            out.append(m if _is_cjk(m) else m_lower)
    return out


def _is_cjk(s: str) -> bool:
    return any("一" <= c <= "鿿" for c in s)
