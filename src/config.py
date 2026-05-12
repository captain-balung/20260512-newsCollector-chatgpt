"""Configuration loader. Reads .env + config/*.yaml into a single Settings object."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"


class Settings:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env", override=False)
        self.use_mock: bool = os.getenv("USE_MOCK", "1") == "1"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.timezone: str = os.getenv("TIMEZONE", "Asia/Taipei")

        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model_fast: str = os.getenv("GEMINI_MODEL_FAST", "gemini-2.0-flash-exp")
        self.gemini_model_pro: str = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-pro")
        self.gemini_model_embed: str = os.getenv("GEMINI_MODEL_EMBED", "text-embedding-004")

        self.email_provider: str = os.getenv("EMAIL_PROVIDER", "smtp")
        self.smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user: str = os.getenv("SMTP_USER", "")
        self.smtp_password: str = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from: str = os.getenv("SMTP_FROM", "Daily AI Insights <noreply@example.com>")
        self.email_to: list[str] = [
            x.strip() for x in os.getenv("EMAIL_TO", "").split(",") if x.strip()
        ]

        self.publish_target: str = os.getenv("PUBLISH_TARGET", "docs")
        self.site_base_url: str = os.getenv("SITE_BASE_URL", "https://example.github.io/daily-ai-insights").rstrip("/")
        # Derived path prefix (e.g. "/20260512-newsCollector-chatgpt" for project Pages).
        # Empty for root-domain hosting (https://user.github.io/).
        from urllib.parse import urlparse
        self.site_path_prefix: str = urlparse(self.site_base_url).path.rstrip("/")

        self.daily_token_budget: int | None = _int_or_none(os.getenv("DAILY_TOKEN_BUDGET"))
        self.monthly_token_budget: int | None = _int_or_none(os.getenv("MONTHLY_TOKEN_BUDGET"))
        self.alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")

        # YAML configs
        self.sources: dict[str, Any] = _load_yaml(CONFIG_DIR / "sources.yaml")
        self.scoring: dict[str, Any] = _load_yaml(CONFIG_DIR / "scoring.yaml")
        self.prompts: dict[str, Any] = _load_yaml(CONFIG_DIR / "prompts.yaml")
        self.system: dict[str, Any] = _load_yaml(CONFIG_DIR / "settings.yaml")

    @property
    def section_ids(self) -> list[str]:
        return [s["id"] for s in self.system["sections"]]

    @property
    def section_map(self) -> dict[str, dict[str, str]]:
        return {s["id"]: s for s in self.system["sections"]}


def _int_or_none(v: str | None) -> int | None:
    if v is None or v.strip() == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
