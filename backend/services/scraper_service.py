from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from scrapers.scraper_runner import ingest_event_page, refresh_upcoming_from_tapology, run_incremental_events

logger = logging.getLogger(__name__)


def trigger_refresh_events(db: Session, *, fetch: bool = True) -> dict[str, Any]:
    n = refresh_upcoming_from_tapology(db, fetch=fetch)
    return {"upcoming_events_upserted": n}


def trigger_incremental_scrape(db: Session, *, max_pages: int = 1, fetch: bool = True) -> dict[str, Any]:
    n = run_incremental_events(db, max_pages=max_pages, fetch=fetch)
    return {"fights_ingested_estimate": n}


def trigger_retrain() -> dict[str, Any]:
    from ml import train as train_mod

    meta = train_mod.train()
    return {"status": "ok", "metrics": meta.metrics, "version": meta.version}
