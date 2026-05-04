from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from ml.age_util import age_years_on_date, reference_date_for_prediction


def load_bundle(path: Path | None = None) -> dict[str, Any]:
    path = path or Path(__file__).resolve().parent / "models" / "production.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Model not found at {path}; run ml/train.py first.")
    return joblib.load(path)


def fight_row_by_id(db: Session, fight_id: str) -> dict[str, Any] | None:
    q = text(
        """
        SELECT f.id AS fight_db_id, f.fight_id, e.date AS fight_date, e.is_upcoming AS event_is_upcoming, f.weight_class, f.is_title_fight,
               f.winner_fighter_id, pa.fighter_id AS fa_id, pb.fighter_id AS fb_id,
               fa.fighter_id AS fa_slug, fb.fighter_id AS fb_slug,
                fa.name AS fa_name, fb.name AS fb_name
        FROM fights f
        JOIN events e ON e.id = f.event_id
        JOIN fight_participations pa ON pa.fight_id = f.id AND pa.is_fighter_a = 1
        JOIN fight_participations pb ON pb.fight_id = f.id AND pb.is_fighter_a = 0
        JOIN fighters fa ON fa.id = pa.fighter_id
        JOIN fighters fb ON fb.id = pb.fighter_id
        WHERE f.fight_id = :fid
        """
    )
    row = db.execute(q, {"fid": fight_id}).mappings().first()
    return dict(row) if row else None


def build_row_for_fight(db: Session, fight_id: str, *, flip: bool | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    bundle = load_bundle()
    feature_names: list[str] = list(bundle["feature_names"])

    df = load_fights_dataframe(db)
    attrs = load_fighter_attrs(db)
    if not attrs.empty and "dob" in attrs.columns:
        attrs["dob"] = pd.to_datetime(attrs["dob"], errors="coerce").dt.date
    hist_by_f = build_per_fighter_history(df)
    pk_to = attrs.set_index("fighter_pk").to_dict("index")

    fr = fight_row_by_id(db, fight_id)
    if not fr:
        raise ValueError(f"Fight not found: {fight_id}")
    fd = pd.to_datetime(fr["fight_date"]).normalize()
    fa, fb = int(fr["fa_id"]), int(fr["fb_id"])

    g_a = hist_by_f.get(fa, pd.DataFrame())
    g_b = hist_by_f.get(fb, pd.DataFrame())
    past_a = g_a[g_a["fight_date"] < fd]
    past_b = g_b[g_b["fight_date"] < fd]

    ca = _career_stats_before(past_a)
    cb = _career_stats_before(past_b)
    a_w3, a_l3 = _recent_form(past_a, 3)
    b_w3, b_l3 = _recent_form(past_b, 3)
    a_w5, a_l5 = _recent_form(past_a, 5)
    b_w5, b_l5 = _recent_form(past_b, 5)

    as_of_d = reference_date_for_prediction(fr.get("fight_date"))
    ha = pk_to.get(fa, {})
    hb = pk_to.get(fb, {})
    age_a = age_years_on_date(ha.get("dob"), as_of_d) if ha.get("dob") else None
    age_b = age_years_on_date(hb.get("dob"), as_of_d) if hb.get("dob") else None
    h_a = float(ha.get("height_cm") or 0) or 0.0
    h_b = float(hb.get("height_cm") or 0) or 0.0
    r_a = float(ha.get("reach_cm") or 0) or 0.0
    r_b = float(hb.get("reach_cm") or 0) or 0.0

    last_a = past_a["fight_date"].max() if not past_a.empty else pd.NaT
    last_b = past_b["fight_date"].max() if not past_b.empty else pd.NaT
    days_a = (fd - last_a).days if pd.notna(last_a) else 365.0
    days_b = (fd - last_b).days if pd.notna(last_b) else 365.0

    use_flip = flip if flip is not None else False
    if use_flip:
        left, right = cb, ca
        lw3, ll3, lw5, ll5 = b_w3, b_l3, b_w5, b_l5
        rw3, rl3, rw5, rl5 = a_w3, a_l3, a_w5, a_l5
        streak_l, streak_r = _streak(past_b), _streak(past_a)
        hd, rd = h_b - h_a, r_b - r_a
        ad = (age_b or 0) - (age_a or 0)
        dlay = float(days_b - days_a)
    else:
        left, right = ca, cb
        lw3, ll3, lw5, ll5 = a_w3, a_l3, a_w5, a_l5
        rw3, rl3, rw5, rl5 = b_w3, b_l3, b_w5, b_l5
        streak_l, streak_r = _streak(past_a), _streak(past_b)
        hd, rd = h_a - h_b, r_a - r_b
        ad = (age_a or 0) - (age_b or 0)
        dlay = float(days_a - days_b)

    row = {
        "win_rate_diff": left["win_rate"] - right["win_rate"],
        "finish_rate_diff": left["finish_rate"] - right["finish_rate"],
        "sig_acc_diff": left["sig_strike_accuracy"] - right["sig_strike_accuracy"],
        "sig_def_diff": left["sig_strike_defense"] - right["sig_strike_defense"],
        "td_acc_diff": left["takedown_accuracy"] - right["takedown_accuracy"],
        "td_def_diff": left["takedown_defense"] - right["takedown_defense"],
        "sub_per15_diff": left["submission_avg_per_15min"] - right["submission_avg_per_15min"],
        "kd_per15_diff": left["avg_knockdowns_per_15min"] - right["avg_knockdowns_per_15min"],
        "ctrl_per15_diff": left["avg_control_per_15min"] - right["avg_control_per_15min"],
        "experience_diff": left["total_fights"] - right["total_fights"],
        "wins_last3_diff": float(lw3 - rw3),
        "losses_last3_diff": float(ll3 - rl3),
        "wins_last5_diff": float(lw5 - rw5),
        "losses_last5_diff": float(ll5 - rl5),
        "height_diff_cm": hd,
        "reach_diff_cm": rd,
        "age_diff_years": ad,
        "streak_diff": float(streak_l - streak_r),
        "layoff_days_diff": dlay,
        "is_title_fight": float(fr["is_title_fight"] or 0),
    }
    X = pd.DataFrame([{k: row.get(k, 0.0) for k in feature_names}])
    meta = {
        "flip": use_flip,
        "fa_name": fr["fa_name"],
        "fb_name": fr["fb_name"],
        "fa_slug": fr["fa_slug"],
        "fb_slug": fr["fb_slug"],
    }
    return X, meta


def confidence_tier(p: float) -> str:
    d = abs(p - 0.5)
    if d >= 0.2:
        return "High"
    if d >= 0.1:
        return "Medium"
    return "Low"


def predict_fight(db: Session, fight_id: str) -> dict[str, Any]:
    bundle = load_bundle()
    model = bundle["model"]
    X0, meta0 = build_row_for_fight(db, fight_id, flip=False)
    p0 = float(model.predict_proba(X0)[0, 1])
    X1, meta1 = build_row_for_fight(db, fight_id, flip=True)
    p1 = float(model.predict_proba(X1)[0, 1])
    # Average symmetric predictions: P(A wins) ≈ (p0 + (1-p1)) / 2
    p_a = (p0 + (1.0 - p1)) / 2.0
    p_b = 1.0 - p_a

    top = top_factors(model, X0, list(X0.columns))
    method = "Decision"
    if p_a > 0.55 or p_b > 0.55:
        method = "KO/TKO" if max(p_a, p_b) > 0.65 else "Decision"

    return {
        "fight_id": fight_id,
        "fighter_a": {
            "name": meta0["fa_name"],
            "win_probability": round(p_a, 4),
            "confidence": confidence_tier(p_a),
        },
        "fighter_b": {
            "name": meta0["fb_name"],
            "win_probability": round(p_b, 4),
            "confidence": confidence_tier(p_b),
        },
        "top_factors": top,
        "predicted_method": method,
        "model_version": bundle.get("version", "unknown"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def top_factors(model: Any, X: pd.DataFrame, names: list[str], k: int = 3) -> list[dict[str, str]]:
    """Approximate global importance via permutation on this row (cheap)."""
    base = float(model.predict_proba(X)[0, 1])
    impacts: list[tuple[str, float]] = []
    for col in names:
        Xp = X.copy()
        Xp[col] = 0.0
        new_p = float(model.predict_proba(Xp)[0, 1])
        impacts.append((col, new_p - base))
    impacts.sort(key=lambda x: abs(x[1]), reverse=True)
    out: list[dict[str, str]] = []
    for feat, imp in impacts[:k]:
        out.append(
            {
                "feature": feat,
                "impact": f"{imp:+.3f}",
                "favor": "Fighter A" if imp > 0 else "Fighter B",
            }
        )
    return out
