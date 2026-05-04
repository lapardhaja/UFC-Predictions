from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models.db_models import Fight, FightParticipation, Fighter
from backend.models.schemas import FighterDetail

router = APIRouter()


@router.get("/fighters/{fighter_id}", response_model=FighterDetail)
def get_fighter(fighter_id: str, db: Session = Depends(get_db)) -> FighterDetail:
    f = db.query(Fighter).filter(Fighter.fighter_id == fighter_id).one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail={"error": "FIGHTER_NOT_FOUND", "message": fighter_id})
    return FighterDetail(
        fighter_id=f.fighter_id,
        name=f.name,
        height_cm=f.height_cm,
        reach_cm=f.reach_cm,
        weight_lbs=f.weight_lbs,
        stance=f.stance,
        dob=f.dob,
        wins=f.wins,
        losses=f.losses,
        draws=f.draws,
        nc=f.nc,
    )


@router.get("/fighters/search")
def search_fighters(q: str = Query(..., min_length=1), db: Session = Depends(get_db), limit: int = 10) -> list[dict]:
    rows = db.query(Fighter.fighter_id, Fighter.name).all()
    choices = {f"{name} ({fid})": fid for fid, name in rows}
    matches = process.extract(q, choices.keys(), scorer=fuzz.WRatio, limit=limit)
    return [{"fighter_id": choices[m[0]], "name": m[0].split(" (")[0], "score": m[1]} for m in matches]
