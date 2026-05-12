"""Gemini wrapper with mock mode. All AI calls go through this module."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any

from jinja2 import Template

from ..config import get_settings
from ..cost.budget import BudgetGuard

log = logging.getLogger(__name__)


@dataclass
class AIResponse:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""


class AIClient:
    """Single interface for all LLM/embedding tasks. Toggles real vs mock by settings.use_mock."""

    def __init__(self) -> None:
        self.s = get_settings()
        self.budget = BudgetGuard()
        self._client = None
        if not self.s.use_mock and self.s.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.s.gemini_api_key)
                self._client = genai
            except ImportError:
                log.warning("google-generativeai not installed; falling back to mock")
                self.s.use_mock = True

    # ------------- public API --------------------------------------------

    def summarize(self, *, title: str, url: str, description: str) -> dict:
        if self.s.use_mock or not self._client:
            return _mock_summary(title, description)
        prompt = _render(self.s.prompts["summarize"],
                         title=title, url=url, description=description)
        raw = self._call_pro(prompt)
        return _safe_json(raw, fallback=_mock_summary(title, description))

    def insight(self, *, title: str, summary: str) -> dict:
        if self.s.use_mock or not self._client:
            return _mock_insight(title, summary)
        prompt = _render(self.s.prompts["insight"], title=title, summary=summary)
        raw = self._call_pro(prompt)
        return _safe_json(raw, fallback=_mock_insight(title, summary))

    def classify(self, *, title: str, summary: str) -> dict:
        if self.s.use_mock or not self._client:
            return {"section": _mock_section(title + " " + summary)}
        prompt = _render(self.s.prompts["classify"], title=title, summary=summary)
        raw = self._call_fast(prompt)
        return _safe_json(raw, fallback={"section": _mock_section(title + " " + summary)})

    def narrative(self, *, timeline: str) -> dict:
        if self.s.use_mock or not self._client:
            return _mock_narrative(timeline)
        prompt = _render(self.s.prompts["narrative"], timeline=timeline)
        raw = self._call_pro(prompt)
        return _safe_json(raw, fallback=_mock_narrative(timeline))

    def embed(self, text: str) -> list[float]:
        """Returns a list[float]. In mock mode, a deterministic hash-based pseudo-embedding."""
        if self.s.use_mock or not self._client:
            return _mock_embed(text)
        try:
            self.budget.charge(tokens=_approx_tokens(text), kind="embed")
            res = self._client.embed_content(
                model=self.s.gemini_model_embed,
                content=text,
            )
            return list(res["embedding"])  # type: ignore[index]
        except Exception as e:  # noqa: BLE001
            log.warning("embed failed (%s), using mock", e)
            return _mock_embed(text)

    # ------------- internal ----------------------------------------------

    def _call_pro(self, prompt: str) -> str:
        return self._call(prompt, model=self.s.gemini_model_pro, kind="pro")

    def _call_fast(self, prompt: str) -> str:
        return self._call(prompt, model=self.s.gemini_model_fast, kind="fast")

    def _call(self, prompt: str, *, model: str, kind: str) -> str:
        if self.s.use_mock or not self._client:
            return _mock_llm(prompt)
        if not self.budget.allow(tokens=_approx_tokens(prompt), kind=kind):
            log.warning("budget exceeded — falling back to mock for %s", kind)
            return _mock_llm(prompt)
        try:
            m = self._client.GenerativeModel(
                model,
                system_instruction=self.s.prompts.get("system_preamble", ""),
            )
            resp = m.generate_content(prompt)
            text = (resp.text or "").strip()
            self.budget.charge(
                tokens=_approx_tokens(prompt) + _approx_tokens(text), kind=kind
            )
            return text
        except Exception as e:  # noqa: BLE001
            log.warning("LLM call failed (%s), using mock", e)
            return _mock_llm(prompt)


# ============================================================================
# Helpers
# ============================================================================

def _render(template_str: str, **vars: Any) -> str:
    return Template(template_str).render(**vars)


def _approx_tokens(s: str) -> int:
    # Roughly 1 token per 4 chars for English, 1 per 1.5 for CJK. Use middle ground.
    return max(1, len(s) // 3)


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _safe_json(text: str, *, fallback: dict) -> dict:
    if not text:
        return fallback
    m = _JSON_BLOCK.search(text)
    if not m:
        return fallback
    try:
        return json.loads(m.group(0))
    except Exception:
        return fallback


# ----------- Mock helpers ----------------------------------------------------

def _mock_llm(prompt: str) -> str:
    """Return a stub JSON guess based on prompt content so the pipeline runs end-to-end."""
    if "schema_version" in prompt or "thread_title" in prompt:
        return json.dumps(_mock_narrative(prompt), ensure_ascii=False)
    if "section" in prompt and "giants_market" in prompt:
        return json.dumps({"section": _mock_section(prompt)}, ensure_ascii=False)
    if "perspective" in prompt:
        return json.dumps(_mock_insight("", prompt), ensure_ascii=False)
    return json.dumps(_mock_summary("", prompt), ensure_ascii=False)


def _mock_summary(title: str, description: str) -> dict:
    hint = (title + " " + description).strip()[:60]
    return {
        "title": (title or "AI 重點新聞")[:24],
        "summary": (
            f"摘要(mock):{hint}。"
            "本則為自動產生的 mock summary,僅供 pipeline 驗證使用。"
            "請設定 USE_MOCK=0 並提供 Gemini API Key 取得真實摘要。"
        ),
        "importance": "medium",
        "tags": _mock_tags(hint),
    }


def _mock_insight(title: str, summary: str) -> dict:
    haystack = (title + " " + summary).lower()
    if any(k in haystack for k in ["taiwan", "台灣", "國科會", "tsmc"]):
        perspective = "台灣政策分析"
    elif any(k in haystack for k in ["edu", "school", "teacher", "教育", "課程"]):
        perspective = "教育科技分析"
    elif any(k in haystack for k in ["stock", "earnings", "ipo", "股", "市值"]):
        perspective = "金融市場分析"
    elif any(k in haystack for k in ["open", "weights", "github", "framework"]):
        perspective = "AI 生態分析"
    else:
        perspective = "媒體設計分析"
    return {
        "perspective": perspective,
        "insight": (
            f"({perspective} · mock)此事件反映 AI 產業結構性變化,"
            "建議追蹤後續模型釋出節奏與政策回應。"
        ),
        "market_impact": "可觀察短期模型供應與資料中心採購信號",
    }


def _mock_section(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["openai", "anthropic", "google", "巨頭", "earnings"]):
        return "giants_market"
    if any(k in t for k in ["agent", "tool", "ide", "sdk", "framework", "github"]):
        return "dev_tools_agent"
    if any(k in t for k in ["image", "video", "audio", "music", "generative"]):
        return "generative_media"
    if any(k in t for k in ["edu", "school", "teacher", "教育", "課程"]):
        return "edu_tech"
    if any(k in t for k in ["weights", "open source", "llama", "deepseek", "kernel"]):
        return "infra_open_source"
    if any(k in t for k in ["regulation", "law", "ethic", "監管", "倫理"]):
        return "law_ethics_society"
    return "giants_market"


def _mock_narrative(timeline: str) -> dict:
    return {
        "thread_title": "AI 生態整合中(mock)",
        "arc": ["新模型發表", "開發者工具跟進", "監管討論浮現"],
        "implication": "預期 6 個月內影響台灣 AI 採購與教育試點佈局(mock)。",
    }


def _mock_tags(hint: str) -> list[str]:
    out = []
    for kw, tag in [
        ("openai", "openai"), ("anthropic", "anthropic"), ("google", "google"),
        ("agent", "agents"), ("opensource", "open-source"), ("台灣", "taiwan"),
        ("edu", "education"),
    ]:
        if kw in hint.lower() and tag not in out:
            out.append(tag)
    return out[:5] or ["ai"]


def _mock_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic 64-dim pseudo-embedding from md5; unit-normalised."""
    h = hashlib.md5(text.encode("utf-8")).digest()
    vec = [(b - 127.5) / 127.5 for b in h]
    # extend to dim
    while len(vec) < dim:
        h = hashlib.md5(h).digest()
        vec.extend((b - 127.5) / 127.5 for b in h)
    vec = vec[:dim]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
