from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.models.db_models import Fight, Fighter
from ml.predict import load_bundle, predict_fight


def heuristic_prediction(fight: Fight, fa: Fighter, fb: Fighter) -> dict[str, Any]:
    """Fallback when model artifact is missing."""
    score_a = (fa.wins or 0) + 0.01 * (fa.reach_cm or 0)
    score_b = (fb.wins or 0) + 0.01 * (fb.reach_cm or 0)
    tot = score_a + score_b + 1e-6
    p_a = float(score_a / tot)
    p_b = 1.0 - p_a

    def tier(p: float) -> str:
        d = abs(p - 0.5)
        return "High" if d >= 0.15 else "Medium" if d >= 0.08 else "Low"

    return {
        "fight_id": fight.fight_id,
        "fighter_a": {"name": fa.name, "win_probability": round(p_a, 4), "confidence": tier(p_a)},
        "fighter_b": {"name": fb.name, "win_probability": round(p_b, 4), "confidence": tier(p_b)},
        "top_factors": [
            {"feature": "record_proxy", "impact": "+0.0", "favor": fa.name if p_a >= p_b else fb.name},
        ],
        "predicted_method": "Decision",
        "model_version": "heuristic-v0",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


def get_prediction_for_fight(db: Session, fight_id: str) -> dict[str, Any]:
    try:
        load_bundle()
        return predict_fight(db, fight_id)
    except FileNotFoundError:
        pass
    fight = db.query(Fight).filter(Fight.fight_id == fight_id).one_or_none()
    if not fight:
        raise ValueError("FIGHT_NOT_FOUND")
    parts = fight.participations
    if len(parts) != 2:
        raise ValueError("FIGHT_INCOMPLETE")
    fa = next(p.fighter for p in parts if p.is_fighter_a)
    fb = next(p.fighter for p in parts if not p.is_fighter_a)
    return heuristic_prediction(fight, fa, fb)
