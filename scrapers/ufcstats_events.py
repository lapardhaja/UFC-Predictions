from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterator

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper


UFCSTATS_ROOT = "http://ufcstats.com"


class UFCStatsEventsScraper(BaseScraper):
    base_url = UFCSTATS_ROOT

    COMPLETED_URL = f"{UFCSTATS_ROOT}/statistics/events/completed"
    UPCOMING_URL = f"{UFCSTATS_ROOT}/statistics/events/upcoming"

    @staticmethod
    def parse_event_rows(soup: BeautifulSoup, *, upcoming: bool) -> list[dict]:
        rows: list[dict] = []
        for a in soup.select("a.b-link.b-link_style_black"):
            href = a.get("href") or ""
            if "/event-details/" not in href:
                continue
            slug = BaseScraper.slug_from_url(href, "event-details") or href.rstrip("/").split("/")[-1]
            name = a.get_text(strip=True)
            if not name or not slug:
                continue
            parent_row = a.find_parent("tr")
            loc = date_s = None
            if parent_row:
                cells = parent_row.find_all("td")
                if len(cells) >= 2:
                    date_s = cells[0].get_text(strip=True)
                if len(cells) >= 3:
                    loc = cells[1].get_text(strip=True)
            parsed_date = UFCStatsEventsScraper._parse_date(date_s) if date_s else None
            rows.append(
                {
                    "event_id": slug,
                    "event_name": name,
                    "date": parsed_date,
                    "location": loc,
                    "is_upcoming": upcoming,
                }
            )
        return rows

    @staticmethod
    def _parse_date(s: str) -> date | None:
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        m = re.search(r"(\w+\s+\d{1,2},\s+\d{4})", s)
        if m:
            return UFCStatsEventsScraper._parse_date(m.group(1))
        return None

    def discover_event_links(self, soup: BeautifulSoup) -> list[str]:
        links: list[str] = []
        for a in soup.select("a.b-link"):
            href = a.get("href") or ""
            if "/event-details/" in href:
                links.append(self.absolute_url(href))
        return list(dict.fromkeys(links))

    def fetch_all_completed_pages(self) -> Iterator[BeautifulSoup]:
        url = self.COMPLETED_URL
        seen: set[str] = set()
        while url and url not in seen:
            seen.add(url)
            soup = self.fetch(url)
            yield soup
            next_link = None
            for a in soup.select("a.b-link"):
                t = a.get_text(strip=True).lower()
                if t == "next":
                    next_link = self.absolute_url(a["href"])
                    break
            url = next_link or ""

    def run(self, *, upcoming: bool = False, fetch: bool = True) -> list[dict]:
        if not fetch:
            return []
        url = self.UPCOMING_URL if upcoming else self.COMPLETED_URL
        soup = self.fetch(url)
        return self.parse_event_rows(soup, upcoming=upcoming)
