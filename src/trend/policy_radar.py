"""Taiwan policy radar — detect policy-relevant articles for highlight in Portal."""
from __future__ import annotations

from ..models import Article

TW_POLICY_KEYWORDS = [
    "國科會", "教育部", "經濟部", "數位發展部", "NCC", "監管", "補助",
    "立法院", "原住民族", "TWNIC", "TSMC", "台積電",
    "policy", "regulation", "subsidy", "taiwan",
]


def flag_taiwan_policy(articles: list[Article]) -> list[Article]:
    """Returns articles classified as policy-relevant; also bumps their final_score by 0.5."""
    flagged: list[Article] = []
    for a in articles:
        haystack = (a.title + " " + a.description + " " + (a.summary or "")).lower()
        if any(kw.lower() in haystack for kw in TW_POLICY_KEYWORDS):
            a.final_score = round(a.final_score + 0.5, 3)
            flagged.append(a)
    return flagged
