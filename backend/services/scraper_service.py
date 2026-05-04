from __future__ import annotations

import logging
from pathlib import Path
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


def trigger_retrain(*, hyperparams_json: Path | None = None) -> dict[str, Any]:
    import json
    from pathlib import Path

    from ml import train as train_mod

    hp = None
    if hyperparams_json is not None and Path(hyperparams_json).exists():
        data = json.loads(Path(hyperparams_json).read_text(encoding="utf-8"))
        hp = data.get("best_params")
    meta = train_mod.train(hyperparams=hp)
    return {
        "status": "ok",
        "metrics": meta.metrics,
        "metrics_val": meta.metrics_val,
        "metrics_test": meta.metrics_test,
        "version": meta.version,
        "used_tuned_hyperparams": hp is not None,
    }
