from __future__ import annotations

from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper


class TapologyUpcomingScraper(BaseScraper):
    """Optional upcoming discovery; Tapology is JS-heavy — best-effort static parse."""

    base_url = "https://www.tapology.com"

    FIGHTCENTER = "https://www.tapology.com/fightcenter"

    @staticmethod
    def parse_upcoming_cards(soup: BeautifulSoup) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        # Minimal structure for tests / placeholder when HTML differs
        for a in soup.select("a[href*='/fightcenter/events/']"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            slug = href.rstrip("/").split("/")[-1] if href else ""
            if not title or not slug:
                continue
            events.append(
                {
                    "external_id": f"tapology-{slug}",
                    "event_name": title,
                    "date": None,
                    "fights": [],
                }
            )
        return events

    @staticmethod
    def _parse_date(s: str) -> date | None:
        for fmt in ("%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def run(self, *, fetch: bool = True) -> list[dict[str, Any]]:
        if not fetch:
            return []
        soup = self.fetch(self.FIGHTCENTER)
        return self.parse_upcoming_cards(soup)
