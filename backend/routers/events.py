from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models.db_models import Event, Fight, FightParticipation
from backend.models.schemas import EventDetail, EventSummary, FightSummary, FighterBrief

router = APIRouter()


@router.get("/events/upcoming", response_model=list[EventSummary])
def upcoming_events(db: Session = Depends(get_db)) -> list[EventSummary]:
    q = (
        db.query(Event)
        .filter(Event.is_upcoming.is_(True))
        .order_by(Event.date.asc().nulls_last())
    )
    out: list[EventSummary] = []
    for e in q.all():
        n = db.query(func.count(Fight.id)).filter(Fight.event_id == e.id).scalar() or 0
        out.append(
            EventSummary(
                event_id=e.event_id,
                event_name=e.event_name,
                date=e.date,
                location=e.location,
                is_upcoming=e.is_upcoming,
                fight_count=int(n),
            )
        )
    return out


@router.get("/events/{event_id}", response_model=EventDetail)
def event_detail(event_id: str, db: Session = Depends(get_db)) -> EventDetail:
    e = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail={"error": "EVENT_NOT_FOUND", "message": event_id})
    fights = (
        db.query(Fight)
        .options(joinedload(Fight.participations).joinedload(FightParticipation.fighter))
        .filter(Fight.event_id == e.id)
        .all()
    )
    summaries: list[FightSummary] = []
    for f in fights:
        parts = sorted(f.participations, key=lambda p: not p.is_fighter_a)
        if len(parts) != 2:
            continue
        fa, fb = parts[0].fighter, parts[1].fighter
        summaries.append(
            FightSummary(
                fight_id=f.fight_id,
                fighter_a=FighterBrief(fighter_id=fa.fighter_id, name=fa.name),
                fighter_b=FighterBrief(fighter_id=fb.fighter_id, name=fb.name),
                weight_class=f.weight_class,
                is_title_fight=bool(f.is_title_fight),
            )
        )
    n = len(summaries)
    return EventDetail(
        event_id=e.event_id,
        event_name=e.event_name,
        date=e.date,
        location=e.location,
        is_upcoming=e.is_upcoming,
        fight_count=n,
        fights=summaries,
    )
