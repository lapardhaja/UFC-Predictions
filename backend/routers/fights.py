from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models.db_models import Fight, FightParticipation
from backend.services.prediction_service import get_prediction_for_fight

router = APIRouter()


@router.get("/fights/{fight_id}")
def fight_detail(fight_id: str, db: Session = Depends(get_db)) -> dict:
    f = (
        db.query(Fight)
        .options(joinedload(Fight.participations).joinedload(FightParticipation.fighter))
        .filter(Fight.fight_id == fight_id)
        .one_or_none()
    )
    if not f:
        raise HTTPException(status_code=404, detail={"error": "FIGHT_NOT_FOUND", "message": fight_id})
    try:
        pred = get_prediction_for_fight(db, fight_id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=400, detail={"error": code, "message": fight_id}) from exc
    parts = sorted(f.participations, key=lambda p: not p.is_fighter_a)
    card: dict = {"fight_id": f.fight_id}
    if len(parts) == 2:
        card.update(
            {
                "fighter_a": {"fighter_id": parts[0].fighter.fighter_id, "name": parts[0].fighter.name},
                "fighter_b": {"fighter_id": parts[1].fighter.fighter_id, "name": parts[1].fighter.name},
                "weight_class": f.weight_class,
                "is_title_fight": f.is_title_fight,
            }
        )
    return {"fight": card, "prediction": pred}
