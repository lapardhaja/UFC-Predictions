from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.models.db_models import Event, Fight, FightParticipation, Fighter
from scrapers.tapology_upcoming import TapologyUpcomingScraper
from scrapers.ufcstats_events import UFCStatsEventsScraper
from scrapers.ufcstats_fights import UFCStatsFightsScraper
from scrapers.ufcstats_fighters import UFCStatsFightersScraper

logger = logging.getLogger(__name__)


def _get_or_create_fighter(db: Session, slug: str, name: str) -> Fighter:
    f = db.query(Fighter).filter(Fighter.fighter_id == slug).one_or_none()
    if f:
        if name and f.name != name:
            f.name = name
        return f
    row = Fighter(fighter_id=slug, name=name or slug)
    db.add(row)
    db.flush()
    return row


def _map_totals(totals: dict[str, Any]) -> dict[str, Any]:
    def pick(*keys: str) -> int | None:
        for k in keys:
            if k in totals and totals[k] is not None:
                try:
                    return int(totals[k])  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    continue
        return None

    def parse_control(val: Any) -> int | None:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip()
        if ":" in s:
            parts = s.split(":")
            try:
                if len(parts) == 2:
                    m, sec = int(parts[0]), int(parts[1])
                    return m * 60 + sec
                if len(parts) == 3:
                    h, m, sec = int(parts[0]), int(parts[1]), int(parts[2])
                    return h * 3600 + m * 60 + sec
            except (ValueError, IndexError):
                return None
        if s.isdigit():
            return int(s)
        return None

    sig_l = pick("sig_str_landed", "significant_strikes_landed")
    sig_a = pick("sig_str_attempted", "significant_strikes_attempted")
    td_l = pick("td_landed", "takedowns_landed")
    td_a = pick("td_attempted", "takedowns_attempted")
    sub_a = pick("sub_att", "submission_attempts")
    kd = pick("kd", "knockdowns")
    raw_ctrl = None
    for k in ("ctrl", "control_time", "control_time_seconds"):
        if k in totals and totals[k] is not None:
            raw_ctrl = totals[k]
            break
    ctrl = parse_control(raw_ctrl)
    tsl = pick("total_str_landed", "total_strikes_landed")
    tsa = pick("total_str_attempted", "total_strikes_attempted")
    return {
        "sig_strikes_landed": sig_l,
        "sig_strikes_attempted": sig_a,
        "total_strikes_landed": tsl,
        "total_strikes_attempted": tsa,
        "takedowns_landed": td_l,
        "takedowns_attempted": td_a,
        "submission_attempts": sub_a,
        "knockdowns": kd,
        "control_time_seconds": ctrl,
    }


def ingest_event_page(db: Session, event_url: str, *, fetch_fights: bool = True) -> int:
    """Scrape one UFCStats event URL and persist fights + participations. Returns fight count."""
    ev_scraper = UFCStatsEventsScraper()
    fight_scraper = UFCStatsFightsScraper()
    fighter_scraper = UFCStatsFightersScraper()

    soup = ev_scraper.fetch(event_url)
    title = soup.select_one("h2.b-content__title span")
    name = title.get_text(strip=True) if title else "Unknown Event"
    slug = event_url.rstrip("/").split("/")[-1]

    date_el = soup.select_one("li.b-list__box-list-item")
    event_date: date | None = None
    if date_el:
        event_date = UFCStatsEventsScraper._parse_date(date_el.get_text(strip=True))

    loc_el = None
    for li in soup.select("li.b-list__box-list-item"):
        if "location" in li.get_text().lower():
            loc_el = li
            break
    location = None
    if loc_el:
        location = loc_el.get_text(" ", strip=True).split(":", 1)[-1].strip()

    event = db.query(Event).filter(Event.event_id == slug).one_or_none()
    if not event:
        event = Event(
            event_id=slug,
            event_name=name,
            date=event_date,
            location=location,
            is_upcoming=False,
        )
        db.add(event)
        db.flush()
    else:
        event.event_name = name
        event.date = event_date or event.date
        event.location = location or event.location

    card, details = fight_scraper.run(event_url, fetch=fetch_fights)
    count = 0
    for row, detail in zip(card, details):
        fa = _get_or_create_fighter(db, row["fighter_a_slug"], row["fighter_a_name"])
        fb = _get_or_create_fighter(db, row["fighter_b_slug"], row["fighter_b_name"])

        for slug in (row["fighter_a_slug"], row["fighter_b_slug"]):
            furl = f"{UFCStatsFightersScraper.base_url}/fighter-details/{slug}"
            prof = fighter_scraper.run(furl, slug, fetch=fetch_fights)
            fx = db.query(Fighter).filter(Fighter.fighter_id == slug).one()
            for k in ("height_cm", "reach_cm", "weight_lbs", "stance", "dob", "wins", "losses", "draws", "nc"):
                if prof.get(k) is not None:
                    setattr(fx, k, prof[k])

        winner_id = None
        ws = detail.get("winner_slug")
        if ws:
            wf = db.query(Fighter).filter(Fighter.fighter_id == ws).one_or_none()
            if wf:
                winner_id = wf.id

        fight = db.query(Fight).filter(Fight.fight_id == row["fight_id"]).one_or_none()
        if not fight:
            fight = Fight(
                fight_id=row["fight_id"],
                event_id=event.id,
                winner_fighter_id=winner_id,
                method=detail.get("method"),
                round=detail.get("round"),
                time_str=detail.get("time_str"),
                weight_class=row.get("weight_class"),
                is_title_fight=bool(row.get("is_title_fight")),
            )
            db.add(fight)
            db.flush()
        else:
            fight.winner_fighter_id = winner_id
            fight.method = detail.get("method")
            fight.round = detail.get("round")
            fight.time_str = detail.get("time_str")
            fight.weight_class = row.get("weight_class")
            fight.is_title_fight = bool(row.get("is_title_fight"))

        db.query(FightParticipation).filter(FightParticipation.fight_id == fight.id).delete()
        fighers_detail = detail.get("fighters") or []
        by_slug = {x["fighter_slug"]: x for x in fighers_detail if x.get("fighter_slug")}

        def participation(fighter: Fighter, is_a: bool) -> FightParticipation:
            d = by_slug.get(fighter.fighter_id, {})
            raw_totals = d.get("totals") or {}
            stats = _map_totals(raw_totals)
            stats_json = json.dumps(raw_totals, ensure_ascii=False) if raw_totals else None
            return FightParticipation(
                fight_id=fight.id,
                fighter_id=fighter.id,
                is_fighter_a=is_a,
                stats_json=stats_json,
                sig_strikes_landed=stats["sig_strikes_landed"],
                sig_strikes_attempted=stats["sig_strikes_attempted"],
                total_strikes_landed=stats["total_strikes_landed"],
                total_strikes_attempted=stats["total_strikes_attempted"],
                takedowns_landed=stats["takedowns_landed"],
                takedowns_attempted=stats["takedowns_attempted"],
                submission_attempts=stats["submission_attempts"],
                knockdowns=stats["knockdowns"],
                control_time_seconds=stats["control_time_seconds"],
            )

        db.add(participation(fa, True))
        db.add(participation(fb, False))
        count += 1

    db.commit()
    return count


def refresh_upcoming_from_tapology(db: Session, *, fetch: bool = True) -> int:
    scraper = TapologyUpcomingScraper()
    items = scraper.run(fetch=fetch)
    n = 0
    for ev in items:
        eid = ev["external_id"]
        ex = db.query(Event).filter(Event.event_id == eid).one_or_none()
        if not ex:
            ex = Event(
                event_id=eid,
                event_name=ev["event_name"],
                date=ev.get("date"),
                location=None,
                is_upcoming=True,
            )
            db.add(ex)
            n += 1
        else:
            ex.is_upcoming = True
            ex.event_name = ev["event_name"]
    db.commit()
    return n


def run_incremental_events(db: Session, *, max_pages: int = 1, fetch: bool = True) -> int:
    """Fetch first N pages of completed events and ingest new URLs only."""
    scraper = UFCStatsEventsScraper()
    total = 0
    if not fetch:
        return 0
    for i, soup in enumerate(scraper.fetch_all_completed_pages()):
        if i >= max_pages:
            break
        links = scraper.discover_event_links(soup)
        for url in links:
            slug = url.rstrip("/").split("/")[-1]
            if db.query(Event).filter(Event.event_id == slug).count():
                continue
            try:
                total += ingest_event_page(db, url, fetch_fights=fetch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("ingest failed %s: %s", url, exc)
    return total
