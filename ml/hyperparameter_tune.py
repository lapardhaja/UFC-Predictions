"""Optuna hyperparameter search — optimizes on validation set only (test untouched until final train)."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score

from ml.feature_builder import build_feature_matrix
from ml.split_config import resolve_time_masks
from ml.train import LGBMClassifier, build_estimator


def _objective(
    trial: optuna.Trial,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    random_state: int,
    use_lgb: bool,
) -> float:
    o: dict[str, Any] = {
        "xgb_n_estimators": trial.suggest_int("xgb_n_estimators", 100, 500, step=50),
        "xgb_max_depth": trial.suggest_int("xgb_max_depth", 3, 8),
        "xgb_learning_rate": trial.suggest_float("xgb_learning_rate", 0.02, 0.2, log=True),
        "xgb_subsample": trial.suggest_float("xgb_subsample", 0.6, 1.0),
        "xgb_colsample_bytree": trial.suggest_float("xgb_colsample_bytree", 0.5, 1.0),
        "xgb_min_child_weight": trial.suggest_float("xgb_min_child_weight", 1.0, 8.0),
        "xgb_reg_alpha": trial.suggest_float("xgb_reg_alpha", 1e-8, 5.0, log=True),
        "xgb_reg_lambda": trial.suggest_float("xgb_reg_lambda", 1e-8, 5.0, log=True),
        "lr_C": trial.suggest_float("lr_C", 0.05, 5.0, log=True),
    }
    if use_lgb:
        o["lgb_n_estimators"] = trial.suggest_int("lgb_n_estimators", 100, 400, step=50)
        o["lgb_num_leaves"] = trial.suggest_int("lgb_num_leaves", 15, 63)
        o["lgb_learning_rate"] = trial.suggest_float("lgb_learning_rate", 0.02, 0.2, log=True)
        o["lgb_subsample"] = trial.suggest_float("lgb_subsample", 0.6, 1.0)
        o["lgb_colsample_bytree"] = trial.suggest_float("lgb_colsample_bytree", 0.5, 1.0)
        o["lgb_min_child_samples"] = trial.suggest_int("lgb_min_child_samples", 5, 80)
        o["lgb_reg_alpha"] = trial.suggest_float("lgb_reg_alpha", 1e-8, 2.0, log=True)
        o["lgb_reg_lambda"] = trial.suggest_float("lgb_reg_lambda", 1e-8, 2.0, log=True)
        w1 = trial.suggest_float("vote_xgb", 0.35, 0.65)
        w2 = trial.suggest_float("vote_lgb", 0.2, 0.45)
        w3 = max(0.05, 1.0 - w1 - w2)
        s = w1 + w2 + w3
        o["vote_xgb"], o["vote_lgb"], o["vote_lr"] = w1 / s, w2 / s, w3 / s
    else:
        w1 = trial.suggest_float("vote_xgb", 0.55, 0.85)
        o["vote_xgb"] = w1
        o["vote_lr"] = 1.0 - w1

    clf = build_estimator(random_state, o)
    clf.fit(X_train, y_train)
    proba = clf.predict_proba(X_val)[:, 1]
    brier = brier_score_loss(y_val, proba)
    acc = accuracy_score(y_val, (proba >= 0.5).astype(int))
    try:
        auc = roc_auc_score(y_val, proba) if len(np.unique(y_val)) > 1 else 0.5
    except ValueError:
        auc = 0.5
    return float(brier - 0.05 * auc - 0.02 * acc)


def run_study(
    *,
    n_trials: int = 50,
    train_cutoff: date | None = date(2022, 1, 1),
    val_cutoff: date | None = date(2024, 1, 1),
    auto_split: bool = False,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    random_state: int = 42,
    use_lgb: bool = True,
    output_path: Path | None = None,
) -> dict[str, Any]:
    if not use_lgb or LGBMClassifier is None:
        use_lgb = False

    X, y, _, fight_dates = build_feature_matrix()
    if len(y) < 80:
        raise RuntimeError("Need more labeled fights for stable HPO (suggest >= 80).")

    m_train, m_val, _, split_summary = resolve_time_masks(
        fight_dates,
        train_cutoff=train_cutoff,
        val_cutoff=val_cutoff,
        auto_split=auto_split,
        train_frac=train_frac,
        val_frac=val_frac,
    )
    X_train, y_train = X.loc[m_train], y[m_train]
    X_val, y_val = X.loc[m_val], y[m_val]
    if len(y_val) < 15:
        raise RuntimeError("Validation split too small for HPO; use --auto-split or wider date windows.")

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=random_state))
    study.optimize(
        lambda tr: _objective(tr, X_train, y_train, X_val, y_val, random_state, use_lgb),
        n_trials=n_trials,
        show_progress_bar=True,
    )
    best = study.best_params
    out = {
        "best_params": best,
        "best_value": study.best_value,
        "n_trials": n_trials,
        "split": split_summary.to_dict(),
        "note": "Tune on val only; run ml.train with --hyperparams-json for final fit+calibration+test.",
    }
    path = output_path or Path(__file__).resolve().parent / "models" / "best_hyperparams.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return out


def main() -> None:
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    p = argparse.ArgumentParser(description="Optuna HPO on validation set (time-safe splits).")
    p.add_argument("--trials", type=int, default=50)
    p.add_argument("--auto-split", action="store_true")
    p.add_argument("--train-frac", type=float, default=0.70)
    p.add_argument("--val-frac", type=float, default=0.15)
    p.add_argument("--train-cutoff", type=str, default="2022-01-01")
    p.add_argument("--val-cutoff", type=str, default="2024-01-01")
    p.add_argument("--no-lgb", action="store_true", help="XGB + LR only (faster)")
    p.add_argument("-o", "--output", type=Path, default=None)
    args = p.parse_args()

    tc = None if args.auto_split else date.fromisoformat(args.train_cutoff)
    vc = None if args.auto_split else date.fromisoformat(args.val_cutoff)
    out = run_study(
        n_trials=args.trials,
        train_cutoff=tc,
        val_cutoff=vc,
        auto_split=args.auto_split,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        use_lgb=not args.no_lgb,
        output_path=args.output,
    )
    print(json.dumps(out["best_params"], indent=2))


if __name__ == "__main__":
    main()
