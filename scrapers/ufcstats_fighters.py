from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper

UFCSTATS_ROOT = "http://ufcstats.com"


class UFCStatsFightersScraper(BaseScraper):
    base_url = UFCSTATS_ROOT

    @staticmethod
    def parse_profile(soup: BeautifulSoup, fighter_slug: str) -> dict[str, Any]:
        name_el = soup.select_one("span.b-content__title-highlight")
        name = name_el.get_text(strip=True) if name_el else fighter_slug
        record_text = ""
        title_parent = soup.select_one("span.b-content__title-highlight")
        if title_parent and title_parent.parent:
            record_text = title_parent.parent.get_text(" ", strip=True)
        wins = losses = draws = nc = 0
        m = re.search(
            r"(\d+)\s*-\s*(\d+)\s*-\s*(\d+)(?:\s*\((\d+)\s*NC\))?",
            record_text,
            re.I,
        )
        if m:
            wins, losses, draws = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if m.group(4):
                nc = int(m.group(4))

        height_cm = reach_cm = weight_lbs = None
        stance = dob = None
        for li in soup.select("ul.b-list__box-list li"):
            txt = li.get_text(" ", strip=True)
            low = txt.lower()
            if low.startswith("height:"):
                height_cm = UFCStatsFightersScraper._parse_height_cm(txt)
            elif low.startswith("reach:"):
                reach_cm = UFCStatsFightersScraper._parse_reach_cm(txt)
            elif low.startswith("weight:"):
                weight_lbs = UFCStatsFightersScraper._parse_weight_lbs(txt)
            elif low.startswith("stance:"):
                stance = txt.split(":", 1)[-1].strip() or None
            elif low.startswith("dob:"):
                dob = UFCStatsFightersScraper._parse_dob(txt)

        return {
            "fighter_id": fighter_slug,
            "name": name,
            "height_cm": height_cm,
            "reach_cm": reach_cm,
            "weight_lbs": weight_lbs,
            "stance": stance,
            "dob": dob,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "nc": nc,
        }

    @staticmethod
    def _parse_height_cm(s: str) -> float | None:
        m = re.search(r"(\d+)\s*'\s*(\d+)\"?", s)
        if not m:
            return None
        feet, inches = int(m.group(1)), int(m.group(2))
        return round((feet * 12 + inches) * 2.54, 1)

    @staticmethod
    def _parse_reach_cm(s: str) -> float | None:
        m = re.search(r"(\d+)\s*\"", s)
        if not m:
            return None
        return round(int(m.group(1)) * 2.54, 1)

    @staticmethod
    def _parse_weight_lbs(s: str) -> float | None:
        m = re.search(r"(\d+)\s*lbs?", s, re.I)
        return float(m.group(1)) if m else None

    @staticmethod
    def _parse_dob(s: str) -> date | None:
        part = s.split(":", 1)[-1].strip()
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(part, fmt).date()
            except ValueError:
                continue
        return None

    def run(self, fighter_url: str, fighter_slug: str, *, fetch: bool = True) -> dict[str, Any]:
        if not fetch:
            return {"fighter_id": fighter_slug, "name": fighter_slug}
        soup = self.fetch(fighter_url)
        return self.parse_profile(soup, fighter_slug)
