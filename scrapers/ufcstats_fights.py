from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper

UFCSTATS_ROOT = "http://ufcstats.com"


def _norm_stat_key(label: str) -> str:
    s = label.lower().strip().replace(".", "").replace("/", "_")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")


def _parse_control_seconds(txt: str) -> int | None:
    txt = txt.strip()
    if not txt or txt == "--":
        return None
    if ":" in txt:
        parts = [p.strip() for p in txt.split(":")]
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return None
    if txt.replace(".", "", 1).isdigit():
        try:
            return int(float(txt))
        except ValueError:
            return None
    return None


class UFCStatsFightsScraper(BaseScraper):
    base_url = UFCSTATS_ROOT

    @staticmethod
    def parse_fight_row_links(soup: BeautifulSoup, _event_url: str) -> list[dict[str, Any]]:
        fights: list[dict[str, Any]] = []
        for row in soup.select("tr.b-fight-details__table-row"):
            links = row.select("a.b-link_style_black")
            fighter_hrefs = [a.get("href", "") for a in links if "/fighter-details/" in a.get("href", "")]
            if len(fighter_hrefs) < 2:
                continue
            fight_link = row.select_one('a[href*="/fight-details/"]')
            if not fight_link:
                continue
            href = fight_link.get("href", "")
            slug = BaseScraper.slug_from_url(href, "fight-details") or href.rstrip("/").split("/")[-1]
            fa_slug = BaseScraper.slug_from_url(fighter_hrefs[0], "fighter-details")
            fb_slug = BaseScraper.slug_from_url(fighter_hrefs[1], "fighter-details")
            fa_name = links[0].get_text(strip=True) if links else ""
            fb_name = links[1].get_text(strip=True) if len(links) > 1 else ""
            if not all([slug, fa_slug, fb_slug]):
                continue
            col_texts = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            weight_class = col_texts[6] if len(col_texts) > 6 else None
            is_title = bool(re.search(r"title|championship", " ".join(col_texts).lower()))
            fights.append(
                {
                    "fight_id": slug,
                    "fight_url": urljoin(UFCSTATS_ROOT + "/", href.lstrip("/")),
                    "fighter_a_slug": fa_slug,
                    "fighter_b_slug": fb_slug,
                    "fighter_a_name": fa_name,
                    "fighter_b_name": fb_name,
                    "weight_class": weight_class,
                    "is_title_fight": is_title,
                }
            )
        return fights

    def parse_fight_detail(
        self, soup: BeautifulSoup, fight_id: str
    ) -> dict[str, Any]:
        """Parse winner, method, round, time, per-fighter totals from fight detail page."""
        out: dict[str, Any] = {
            "fight_id": fight_id,
            "winner_slug": None,
            "method": None,
            "round": None,
            "time_str": None,
            "fighters": [],
        }
        win_el = soup.select_one("i.b-fight-details__person-status_style_gray")
        if win_el:
            parent = win_el.find_parent("div", class_=re.compile("person"))
            if parent:
                name_a = parent.select_one("a")
                if name_a and name_a.get("href"):
                    out["winner_slug"] = BaseScraper.slug_from_url(
                        name_a["href"], "fighter-details"
                    )

        details = soup.select_one("div.b-fight-details__fight")
        if details:
            texts = [li.get_text(" ", strip=True) for li in details.select("li")]
            joined = " | ".join(texts)
            out["method"] = texts[0] if texts else None
            rm = re.search(r"Round:\s*(\d+)", joined, re.I)
            tm = re.search(r"Time:\s*([\d:]+)", joined, re.I)
            if rm:
                out["round"] = int(rm.group(1))
            if tm:
                out["time_str"] = tm.group(1)

        for person in soup.select("div.b-fight-details__person"):
            a = person.select_one('a[href*="/fighter-details/"]')
            if not a:
                continue
            slug = BaseScraper.slug_from_url(a["href"], "fighter-details")
            name = a.get_text(strip=True)
            is_winner = bool(person.select_one("i.b-fight-details__person-status_style_gray"))
            totals: dict[str, int | None] = {}
            section = person.find_next("div", class_=re.compile("fight-card"))
            if section:
                for row in section.select("div.b-fight-details__table-body tr"):
                    cells = [c.get_text(strip=True) for c in row.find_all("td")]
                    if len(cells) >= 2 and cells[0]:
                        key = cells[0].lower().replace(" ", "_")
                        try:
                            totals[key] = int(cells[1]) if cells[1].isdigit() else None
                        except (ValueError, TypeError):
                            totals[key] = None
            out["fighters"].append(
                {"fighter_slug": slug, "name": name, "is_winner": is_winner, "totals": totals}
            )

        # Fallback / enrich: parse all UFCStats fight stat tables into per-fighter totals
        table_fighters = UFCStatsFightsScraper._parse_all_stat_tables(soup)
        if len(out["fighters"]) < 2:
            out["fighters"] = table_fighters
        elif len(table_fighters) == 2:
            UFCStatsFightsScraper._merge_totals(out["fighters"], table_fighters)

        return out

    @staticmethod
    def _merge_totals(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> None:
        """Merge scraped table totals into primary list matched by fighter_slug."""
        by_slug = {x["fighter_slug"]: x.get("totals") or {} for x in secondary if x.get("fighter_slug")}
        for f in primary:
            slug = f.get("fighter_slug")
            if slug and slug in by_slug:
                f.setdefault("totals", {}).update(by_slug[slug])

    @staticmethod
    def _parse_all_stat_tables(soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Parse every b-fight-details__table on the page (totals, significant strikes, etc.)."""
        fighters: list[dict[str, Any]] = []
        header = soup.select_one("div.b-fight-details__persons")
        if not header:
            return fighters
        names = header.select('a[href*="/fighter-details/"]')
        for a in names[:2]:
            slug = BaseScraper.slug_from_url(a["href"], "fighter-details")
            fighters.append(
                {
                    "fighter_slug": slug,
                    "name": a.get_text(strip=True),
                    "is_winner": False,
                    "totals": {},
                }
            )
        if len(fighters) < 2:
            return fighters

        for table in soup.select("table.b-fight-details__table"):
            title_el = table.find_previous("p", class_=re.compile("b-fight-details__table-title"))
            section = _norm_stat_key(title_el.get_text(strip=True)) if title_el else "table"
            thead = table.select_one("thead")
            if not thead:
                continue
            ths = [th.get_text(strip=True) for th in thead.select("th")]
            if len(ths) < 3:
                continue
            # Map column index -> fighter index (skip first col = stat name)
            col_to_fidx: dict[int, int] = {}
            for col_idx in range(1, min(len(ths), 3)):
                h = ths[col_idx].lower()
                if fighters[0]["name"].lower() in h or fighters[0]["fighter_slug"] in h:
                    col_to_fidx[col_idx] = 0
                elif fighters[1]["name"].lower() in h or fighters[1]["fighter_slug"] in h:
                    col_to_fidx[col_idx] = 1
                else:
                    col_to_fidx[col_idx] = col_idx - 1

            for row in table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                label = cells[0].get_text(strip=True)
                if not label:
                    continue
                base_key = _norm_stat_key(label)
                low = label.lower()
                for col_idx in (1, 2):
                    if col_idx >= len(cells):
                        continue
                    fidx = col_to_fidx.get(col_idx, col_idx - 1)
                    if fidx not in (0, 1):
                        continue
                    txt = cells[col_idx].get_text(strip=True)
                    pref = f"{section}__" if section != "table" else ""
                    if "control" in low or "ctrl" in base_key:
                        sec = _parse_control_seconds(txt)
                        if sec is not None:
                            fighters[fidx]["totals"][pref + "control_time_seconds"] = sec
                            fighters[fidx]["totals"]["ctrl"] = sec
                        continue
                    nums = re.findall(r"\d+", txt)
                    if len(nums) >= 2 and ("of" in txt or "landed" in low or "/" in txt):
                        fighters[fidx]["totals"][pref + f"{base_key}_landed"] = int(nums[0])
                        fighters[fidx]["totals"][pref + f"{base_key}_attempted"] = int(nums[1])
                    elif len(nums) == 1:
                        try:
                            fighters[fidx]["totals"][pref + base_key] = int(nums[0])
                        except ValueError:
                            pass

        win_i = soup.select_one("i.b-fight-details__person-status_style_gray")
        if win_i:
            p = win_i.find_parent("div", class_=re.compile("person"))
            if p:
                wa = p.select_one('a[href*="/fighter-details/"]')
                if wa:
                    wslug = BaseScraper.slug_from_url(wa["href"], "fighter-details")
                    for f in fighters:
                        f["is_winner"] = f.get("fighter_slug") == wslug
        return fighters

    def run(self, event_url: str, *, fetch: bool = True) -> tuple[list[dict], list[dict]]:
        if not fetch:
            return [], []
        soup = self.fetch(event_url)
        card = self.parse_fight_row_links(soup, event_url)
        details: list[dict] = []
        for f in card:
            detail_soup = self.fetch(f["fight_url"])
            details.append(self.parse_fight_detail(detail_soup, f["fight_id"]))
        return card, details
