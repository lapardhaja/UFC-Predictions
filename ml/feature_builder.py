from __future__ import annotations

import math
import random
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import SessionLocal


def _age_years(dob: date | None, as_of: date) -> float | None:
    if dob is None:
        return None
    return (as_of - dob).days / 365.25


def _safe_div(a: float, b: float) -> float:
    if b == 0 or math.isnan(b):
        return 0.0
    return a / b


def _career_stats_before(df: pd.DataFrame) -> dict[str, float]:
    """df rows are past fights for one fighter, sorted by date ascending."""
    if df.empty:
        return {
            "win_rate": 0.0,
            "finish_rate": 0.0,
            "sig_strike_accuracy": 0.0,
            "sig_strike_defense": 0.0,
            "takedown_accuracy": 0.0,
            "takedown_defense": 0.0,
            "submission_avg_per_15min": 0.0,
            "avg_knockdowns_per_15min": 0.0,
            "avg_control_per_15min": 0.0,
            "total_fights": 0.0,
        }
    wins = (df["result"] == "W").sum()
    losses = (df["result"] == "L").sum()
    n = len(df)
    ko_w = (df["method_win"] == "KO").sum() if "method_win" in df.columns else 0
    sub_w = (df["method_win"] == "SUB").sum() if "method_win" in df.columns else 0

    sig_l = df["sig_strikes_landed"].fillna(0)
    sig_a = df["sig_strikes_attempted"].replace(0, np.nan)
    opp_sig_l = df["opp_sig_strikes_landed"].fillna(0)
    opp_sig_a = df["opp_sig_strikes_attempted"].replace(0, np.nan)
    td_l = df["takedowns_landed"].fillna(0)
    td_a = df["takedowns_attempted"].replace(0, np.nan)
    opp_td_l = df["opp_takedowns_landed"].fillna(0)
    opp_td_a = df["opp_takedowns_attempted"].replace(0, np.nan)

    fight_min = df["fight_minutes"].replace(0, np.nan)
    sub = df["submission_attempts"].fillna(0)
    kd = df["knockdowns"].fillna(0)
    ctrl = df["control_time_seconds"].fillna(0) / 60.0

    scale = 15.0 / fight_min

    return {
        "win_rate": wins / n if n else 0.0,
        "finish_rate": (ko_w + sub_w) / max(wins, 1) if wins else 0.0,
        "sig_strike_accuracy": float(np.nanmean(_safe_div_series(sig_l, sig_a))),
        "sig_strike_defense": float(1.0 - np.nanmean(_safe_div_series(opp_sig_l, opp_sig_a))),
        "takedown_accuracy": float(np.nanmean(_safe_div_series(td_l, td_a))),
        "takedown_defense": float(1.0 - np.nanmean(_safe_div_series(opp_td_l, opp_td_a))),
        "submission_avg_per_15min": float(np.nanmean(sub * scale)),
        "avg_knockdowns_per_15min": float(np.nanmean(kd * scale)),
        "avg_control_per_15min": float(np.nanmean(ctrl * scale)),
        "total_fights": float(n),
    }


def _safe_div_series(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num.astype(float) / den.astype(float)
    return out.replace([np.inf, -np.inf], np.nan)


def load_fights_dataframe(db: Session) -> pd.DataFrame:
    q = text(
        """
        SELECT
          f.id AS fight_db_id,
          f.fight_id,
          e.date AS fight_date,
          f.weight_class,
          f.is_title_fight,
          f.method,
          f.winner_fighter_id,
          pa.fighter_id AS fa_id,
          pb.fighter_id AS fb_id,
          pa.sig_strikes_landed AS fa_sig_l, pa.sig_strikes_attempted AS fa_sig_a,
          pa.takedowns_landed AS fa_td_l, pa.takedowns_attempted AS fa_td_a,
          pa.submission_attempts AS fa_sub, pa.knockdowns AS fa_kd,
          pa.control_time_seconds AS fa_ctrl,
          pb.sig_strikes_landed AS fb_sig_l, pb.sig_strikes_attempted AS fb_sig_a,
          pb.takedowns_landed AS fb_td_l, pb.takedowns_attempted AS fb_td_a,
          pb.submission_attempts AS fb_sub, pb.knockdowns AS fb_kd,
          pb.control_time_seconds AS fb_ctrl
        FROM fights f
        JOIN events e ON e.id = f.event_id
        JOIN fight_participations pa ON pa.fight_id = f.id AND pa.is_fighter_a = 1
        JOIN fight_participations pb ON pb.fight_id = f.id AND pb.is_fighter_a = 0
        WHERE e.date IS NOT NULL AND f.winner_fighter_id IS NOT NULL
        ORDER BY e.date ASC, f.id ASC
        """
    )
    rows = db.execute(q).mappings().all()
    return pd.DataFrame(rows)


def load_fighter_attrs(db: Session) -> pd.DataFrame:
    q = text(
        """
        SELECT id AS fighter_pk, fighter_id, height_cm, reach_cm, dob, stance
        FROM fighters
        """
    )
    return pd.DataFrame(db.execute(q).mappings().all())


def build_per_fighter_history(df: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Long format: each row one fighter's perspective in a fight."""
    records: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r["fight_date"]).date()
        wa = r["winner_fighter_id"]
        wa_na = wa is None or (isinstance(wa, float) and math.isnan(wa)) or pd.isna(wa)
        res_a = "D" if wa_na else ("W" if int(wa) == int(r["fa_id"]) else "L")
        res_b = "D" if wa_na else ("W" if int(wa) == int(r["fb_id"]) else "L")
        won_a = not wa_na and int(wa) == int(r["fa_id"])
        won_b = not wa_na and int(wa) == int(r["fb_id"])
        records.append(
            {
                "fighter_pk": int(r["fa_id"]),
                "fight_date": d,
                "fight_db_id": int(r["fight_db_id"]),
                "result": res_a,
                "method_win": _method_bucket(r, won_a),
                "sig_strikes_landed": r["fa_sig_l"],
                "sig_strikes_attempted": r["fa_sig_a"],
                "opp_sig_strikes_landed": r["fb_sig_l"],
                "opp_sig_strikes_attempted": r["fb_sig_a"],
                "takedowns_landed": r["fa_td_l"],
                "takedowns_attempted": r["fa_td_a"],
                "opp_takedowns_landed": r["fb_td_l"],
                "opp_takedowns_attempted": r["fb_td_a"],
                "submission_attempts": r["fa_sub"],
                "knockdowns": r["fa_kd"],
                "control_time_seconds": r["fa_ctrl"],
                "fight_minutes": 15.0,
            }
        )
        records.append(
            {
                "fighter_pk": int(r["fb_id"]),
                "fight_date": d,
                "fight_db_id": int(r["fight_db_id"]),
                "result": res_b,
                "method_win": _method_bucket(r, won_b),
                "sig_strikes_landed": r["fb_sig_l"],
                "sig_strikes_attempted": r["fb_sig_a"],
                "opp_sig_strikes_landed": r["fa_sig_l"],
                "opp_sig_strikes_attempted": r["fa_sig_a"],
                "takedowns_landed": r["fb_td_l"],
                "takedowns_attempted": r["fb_td_a"],
                "opp_takedowns_landed": r["fa_td_l"],
                "opp_takedowns_attempted": r["fa_td_a"],
                "submission_attempts": r["fb_sub"],
                "knockdowns": r["fb_kd"],
                "control_time_seconds": r["fb_ctrl"],
                "fight_minutes": 15.0,
            }
        )
    hist = pd.DataFrame(records)
    if hist.empty:
        return {}
    hist["fight_date"] = pd.to_datetime(hist["fight_date"])
    by_f: dict[int, pd.DataFrame] = {}
    for fid, g in hist.groupby("fighter_pk"):
        by_f[int(fid)] = g.sort_values("fight_date")
    return by_f


def _method_bucket(r: pd.Series, won: bool) -> str:
    if not won or r["winner_fighter_id"] is None or (isinstance(r["winner_fighter_id"], float) and math.isnan(r["winner_fighter_id"])):
        return "NONE"
    m = str(r.get("method") or "").lower()
    if "ko" in m or "tko" in m:
        return "KO"
    if "sub" in m:
        return "SUB"
    return "DEC"


def _recent_form(g: pd.DataFrame, n: int) -> tuple[int, int]:
    tail = g.tail(n)
    w = (tail["result"] == "W").sum()
    l = (tail["result"] == "L").sum()
    return int(w), int(l)


def _streak(g: pd.DataFrame) -> int:
    if g.empty:
        return 0
    last = None
    streak = 0
    for res in g["result"].iloc[::-1]:
        if res not in ("W", "L"):
            continue
        if last is None:
            last = res
            streak = 1 if res == "W" else -1
        elif res == last:
            streak += 1 if res == "W" else -1
        else:
            break
    return streak


def build_feature_matrix(
    db: Session | None = None,
) -> tuple[pd.DataFrame, np.ndarray, list[str], pd.Series]:
    """Returns X, y (fighter_a wins 0/1), feature_names, fight_date (for time splits only)."""
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        random.seed(42)
        np.random.seed(42)
        df = load_fights_dataframe(db)
        attrs = load_fighter_attrs(db)
        if not attrs.empty and "dob" in attrs.columns:
            attrs["dob"] = pd.to_datetime(attrs["dob"], errors="coerce").dt.date
        if df.empty:
            return pd.DataFrame(), np.array([]), [], pd.Series(dtype="datetime64[ns]")
        hist_by_f = build_per_fighter_history(df)
        pk_to = attrs.set_index("fighter_pk").to_dict("index")

        X_rows: list[dict[str, float]] = []
        y: list[int] = []
        fight_dates: list[pd.Timestamp] = []

        for _, r in df.iterrows():
            fd = pd.to_datetime(r["fight_date"]).normalize()
            fa, fb = int(r["fa_id"]), int(r["fb_id"])
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

            as_of_d = fd.date() if isinstance(fd, pd.Timestamp) else fd

            ha = pk_to.get(fa, {})
            hb = pk_to.get(fb, {})
            age_a = _age_years(ha.get("dob"), as_of_d) if ha.get("dob") is not None else None
            age_b = _age_years(hb.get("dob"), as_of_d) if hb.get("dob") is not None else None
            h_a = float(ha.get("height_cm") or 0) or 0.0
            h_b = float(hb.get("height_cm") or 0) or 0.0
            r_a = float(ha.get("reach_cm") or 0) or 0.0
            r_b = float(hb.get("reach_cm") or 0) or 0.0

            last_a = past_a["fight_date"].max() if not past_a.empty else pd.NaT
            last_b = past_b["fight_date"].max() if not past_b.empty else pd.NaT
            days_a = (fd - last_a).days if pd.notna(last_a) else 365.0
            days_b = (fd - last_b).days if pd.notna(last_b) else 365.0

            flip = random.random() < 0.5
            if flip:
                left, right = cb, ca
                rw3, rl3, rw5, rl5 = b_w3, b_l3, b_w5, b_l5
                lw3, ll3, lw5, ll5 = a_w3, a_l3, a_w5, a_l5
                streak_l = _streak(past_b)
                streak_r = _streak(past_a)
                hd = h_b - h_a
                rd = r_b - r_a
                ad = (age_b or 0) - (age_a or 0)
                dlay = float(days_b - days_a)
                label = int(r["winner_fighter_id"] == fb) if r["winner_fighter_id"] else 0
            else:
                left, right = ca, cb
                lw3, ll3, lw5, ll5 = a_w3, a_l3, a_w5, a_l5
                rw3, rl3, rw5, rl5 = b_w3, b_l3, b_w5, b_l5
                streak_l = _streak(past_a)
                streak_r = _streak(past_b)
                hd = h_a - h_b
                rd = r_a - r_b
                ad = (age_a or 0) - (age_b or 0)
                dlay = float(days_a - days_b)
                label = int(r["winner_fighter_id"] == fa) if r["winner_fighter_id"] else 0

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
                "is_title_fight": float(r["is_title_fight"] or 0),
            }
            X_rows.append(row)
            y.append(label)
            fight_dates.append(fd)

        X = pd.DataFrame(X_rows)
        feature_names = list(X.columns)
        return X, np.array(y, dtype=np.int64), feature_names, pd.Series(fight_dates, name="fight_date")
    finally:
        if own_db and db is not None:
            db.close()


def assert_no_leakage_columns(features: list[str]) -> None:
    joined = " ".join(features).lower()
    for token in ("winner", "post_fight", "fight_result"):
        assert token not in joined
