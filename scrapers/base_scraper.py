from __future__ import annotations

import random
import re
import time
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from backend.config import get_settings


DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) rv:121.0) Gecko/20100101 Firefox/121.0",
]


class BaseScraper(ABC):
    base_url: str = ""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.settings = get_settings()

    def _sleep_rate_limit(self) -> None:
        lo, hi = self.settings.scrape_delay_min, self.settings.scrape_delay_max
        time.sleep(random.uniform(lo, hi))

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": random.choice(DEFAULT_USER_AGENTS)}

    def fetch(self, url: str, *, retries: int = 4) -> BeautifulSoup:
        last_exc: Exception | None = None
        backoff = 2.0
        for attempt in range(retries):
            self._sleep_rate_limit()
            try:
                resp = self.session.get(url, headers=self._headers(), timeout=60)
                if resp.status_code in (429, 503):
                    time.sleep(backoff + random.uniform(0, 1))
                    backoff *= 2
                    continue
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(backoff + random.uniform(0, 1))
                backoff *= 2
        raise RuntimeError(f"Failed to fetch {url}: {last_exc}")

    @staticmethod
    def slug_from_url(href: str, segment: str) -> str | None:
        """Extract slug after /segment/ in path."""
        path = urlparse(href).path.strip("/").split("/")
        try:
            idx = path.index(segment.rstrip("/").split("/")[-1])
            return path[idx + 1] if idx + 1 < len(path) else None
        except ValueError:
            m = re.search(rf"/{re.escape(segment)}/([^/?#]+)", href)
            return m.group(1) if m else None

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def absolute_url(self, href: str) -> str:
        return urljoin(self.base_url, href)
