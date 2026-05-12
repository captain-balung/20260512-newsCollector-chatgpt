"""Retry with exponential backoff (SRS §12.1)."""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

from ..config import get_settings

log = logging.getLogger(__name__)

T = TypeVar("T")


def retry(fn: Callable[[], T], *, op_name: str = "op", max_retry: int | None = None,
          base: float | None = None) -> T:
    """Run fn with exponential backoff. Re-raises the last exception on exhaustion."""
    s = get_settings()
    cfg = s.system.get("retry", {})
    max_retry = max_retry if max_retry is not None else cfg.get("max_retry", 3)
    base = base if base is not None else cfg.get("backoff_base_seconds", 2)

    last: Exception | None = None
    for attempt in range(max_retry + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt == max_retry:
                break
            delay = base * (2 ** attempt) + random.uniform(0, 0.5)
            log.info("retry %s (attempt %d/%d) after %.1fs: %s",
                     op_name, attempt + 1, max_retry, delay, e)
            time.sleep(delay)
    assert last is not None
    raise last
