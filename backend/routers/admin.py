from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.services import scraper_service

router = APIRouter()


def verify_admin(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = f"Bearer {settings.admin_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": "Invalid admin key"})


@router.post("/admin/refresh-events")
def refresh_events(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    return scraper_service.trigger_refresh_events(db, fetch=True)


@router.post("/admin/retrain")
def retrain(_: None = Depends(verify_admin)) -> dict:
    return scraper_service.trigger_retrain()
