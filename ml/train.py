from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

try:
    from lightgbm import LGBMClassifier
except ImportError:
    LGBMClassifier = None  # type: ignore[misc, assignment]

from ml.feature_builder import assert_no_leakage_columns, build_feature_matrix
from ml.split_config import resolve_time_masks


@dataclass
class TrainArtifacts:
    version: str
    feature_names: list[str]
    train_end: str
    val_end: str
    metrics: dict[str, float]
    metrics_train: dict[str, float] = field(default_factory=dict)
    metrics_val: dict[str, float] = field(default_factory=dict)
    metrics_test: dict[str, float] = field(default_factory=dict)
    split: dict[str, Any] = field(default_factory=dict)
    hyperparams: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)


def build_estimator(random_state: int = 42, overrides: dict[str, Any] | None = None) -> Pipeline:
    """Voting ensemble; `overrides` may contain xgb_*, lgb_*, lr_C, vote_* weights."""
    o = dict(overrides or {})

    xgb = XGBClassifier(
        n_estimators=int(o.get("xgb_n_estimators", 200)),
        max_depth=int(o.get("xgb_max_depth", 5)),
        learning_rate=float(o.get("xgb_learning_rate", 0.08)),
        subsample=float(o.get("xgb_subsample", 0.85)),
        colsample_bytree=float(o.get("xgb_colsample_bytree", 0.8)),
        min_child_weight=float(o.get("xgb_min_child_weight", 2)),
        reg_alpha=float(o.get("xgb_reg_alpha", 0.0)),
        reg_lambda=float(o.get("xgb_reg_lambda", 1.0)),
        random_state=random_state,
        n_jobs=-1,
        eval_metric="logloss",
    )
    estimators: list[tuple[str, Any]] = [("xgb", xgb)]
    weights: list[float] = [float(o.get("vote_xgb", 0.55))]

    if LGBMClassifier is not None:
        estimators.append(
            (
                "lgb",
                LGBMClassifier(
                    n_estimators=int(o.get("lgb_n_estimators", 200)),
                    max_depth=int(o.get("lgb_max_depth", -1)),
                    num_leaves=int(o.get("lgb_num_leaves", 31)),
                    learning_rate=float(o.get("lgb_learning_rate", 0.08)),
                    subsample=float(o.get("lgb_subsample", 0.85)),
                    colsample_bytree=float(o.get("lgb_colsample_bytree", 0.8)),
                    min_child_samples=int(o.get("lgb_min_child_samples", 20)),
                    reg_alpha=float(o.get("lgb_reg_alpha", 0.0)),
                    reg_lambda=float(o.get("lgb_reg_lambda", 0.0)),
                    random_state=random_state,
                    n_jobs=-1,
                    verbose=-1,
                ),
            )
        )
        weights.append(float(o.get("vote_lgb", 0.30)))
    estimators.append(
        (
            "lr",
            LogisticRegression(
                max_iter=2000,
                random_state=random_state,
                class_weight="balanced",
                C=float(o.get("lr_C", 1.0)),
                solver="lbfgs",
            ),
        )
    )
    weights.append(float(o.get("vote_lr", 0.20 if len(weights) == 2 else 0.15)))
    s = sum(weights)
    weights = [w / s for w in weights]

    vote = VotingClassifier(estimators=estimators, voting="soft", weights=weights)
    return Pipeline([("scale", StandardScaler()), ("clf", vote)])


def _split_metrics(model: Any, X: pd.DataFrame, y: np.ndarray) -> dict[str, float]:
    if len(y) == 0 or X.empty:
        return {"accuracy": float("nan"), "brier": float("nan"), "roc_auc": float("nan"), "n": 0.0}
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    out: dict[str, float] = {
        "accuracy": float(accuracy_score(y, pred)),
        "brier": float(brier_score_loss(y, proba)),
        "n": float(len(y)),
    }
    try:
        out["roc_auc"] = float(roc_auc_score(y, proba)) if len(np.unique(y)) > 1 else float("nan")
    except ValueError:
        out["roc_auc"] = float("nan")
    return out


def train(
    *,
    train_cutoff: date | None = date(2022, 1, 1),
    val_cutoff: date | None = date(2024, 1, 1),
    auto_split: bool = False,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    hyperparams: dict[str, Any] | None = None,
    calibrate: bool = True,
    model_dir: Path | None = None,
    random_state: int = 42,
    version: str = "v1.1.0",
) -> TrainArtifacts:
    """
    Time-based train / val / test (no random shuffle across dates).
    Default: cutoffs 2022-01-01 (val start) and 2024-01-01 (test start); use --auto-split for 70/15/15 chronological.
    """
    model_dir = model_dir or Path(__file__).resolve().parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    X, y, feature_names, fight_dates = build_feature_matrix()
    if len(y) < 30:
        raise RuntimeError("Not enough labeled fights to train; ingest historical data first.")

    assert_no_leakage_columns(feature_names)

    m_train, m_val, m_test, split_summary = resolve_time_masks(
        fight_dates,
        train_cutoff=train_cutoff,
        val_cutoff=val_cutoff,
        auto_split=auto_split,
        train_frac=train_frac,
        val_frac=val_frac,
    )
    X_train, y_train = X.loc[m_train], y[m_train]
    X_val, y_val = X.loc[m_val], y[m_val]
    X_test, y_test = X.loc[m_test], y[m_test]

    if X_train.empty:
        raise RuntimeError("Train split is empty; widen date range or use --auto-split.")

    hp = dict(hyperparams or {})
    base = build_estimator(random_state, hp)

    if calibrate and len(y_val) >= 10:
        cal = CalibratedClassifierCV(base, method="isotonic", cv=min(3, max(2, len(y_train) // 20)))
        cal.fit(pd.concat([X_train, X_val]), np.concatenate([y_train, y_val]))
    elif calibrate:
        cal = CalibratedClassifierCV(
            base, method="sigmoid", cv=TimeSeriesSplit(n_splits=min(3, max(2, len(y_train) // 15)))
        )
        cal.fit(X_train, y_train)
    else:
        base.fit(X_train, y_train)
        cal = base

    metrics_train = _split_metrics(cal, X_train, y_train)

    metrics_train = _split_metrics(cal, X_train, y_train)
    metrics_val = _split_metrics(cal, X_val, y_val)
    metrics_test = _split_metrics(cal, X_test, y_test)

    # Primary headline metrics = held-out test when available
    if len(y_test) > 0 and not X_test.empty:
        headline = metrics_test
    elif len(y_val) > 0:
        headline = metrics_val
    else:
        headline = metrics_train

    metrics = {
        "accuracy": headline.get("accuracy", float("nan")),
        "brier": headline.get("brier", float("nan")),
        "roc_auc": headline.get("roc_auc", float("nan")),
    }

    bundle = {
        "model": cal,
        "feature_names": feature_names,
        "version": version,
        "train_cutoff": split_summary.train_cutoff.isoformat(),
        "val_cutoff": split_summary.val_cutoff.isoformat(),
        "split": split_summary.to_dict(),
        "hyperparams": hp,
        "metrics_train": metrics_train,
        "metrics_val": metrics_val,
        "metrics_test": metrics_test,
    }
    joblib.dump(bundle, model_dir / "production.pkl")

    try:
        est = cal.calibrated_classifiers_[0].estimator if hasattr(cal, "calibrated_classifiers_") else cal
        vote = est.named_steps["clf"]
        xgb_est = vote.named_estimators_["xgb"]
        imp = getattr(xgb_est, "feature_importances_", None)
        if imp is not None and len(imp) == len(feature_names):
            ranked = sorted(
                [{"feature": n, "importance": float(i)} for n, i in zip(feature_names, imp)],
                key=lambda x: x["importance"],
                reverse=True,
            )
            (model_dir / "feature_importance.json").write_text(
                json.dumps(ranked[:40], indent=2), encoding="utf-8"
            )
    except (AttributeError, KeyError, IndexError, TypeError):
        pass

    meta = TrainArtifacts(
        version=version,
        feature_names=feature_names,
        train_end=split_summary.train_cutoff.isoformat(),
        val_end=split_summary.val_cutoff.isoformat(),
        metrics=metrics,
        metrics_train=metrics_train,
        metrics_val=metrics_val,
        metrics_test=metrics_test,
        split=split_summary.to_dict(),
        hyperparams=hp,
    )
    meta_dict = asdict(meta)
    meta_dict["history"] = [
        {
            "period": "train",
            "accuracy": metrics_train.get("accuracy"),
            "roc_auc": metrics_train.get("roc_auc"),
            "brier": metrics_train.get("brier"),
            "sample_size": int(metrics_train.get("n", 0)),
        },
        {
            "period": "validation",
            "accuracy": metrics_val.get("accuracy"),
            "roc_auc": metrics_val.get("roc_auc"),
            "brier": metrics_val.get("brier"),
            "sample_size": int(metrics_val.get("n", 0)),
        },
        {
            "period": "test_holdout",
            "accuracy": metrics_test.get("accuracy"),
            "roc_auc": metrics_test.get("roc_auc"),
            "brier": metrics_test.get("brier"),
            "sample_size": int(metrics_test.get("n", 0)),
        },
    ]
    (model_dir / "metadata.json").write_text(json.dumps(meta_dict, indent=2, default=str), encoding="utf-8")
    return meta


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    p = argparse.ArgumentParser(description="Train calibrated UFC fight model (time-based splits).")
    p.add_argument("--auto-split", action="store_true", help="Chronological 70%%/15%%/15%% instead of date cutoffs")
    p.add_argument("--train-frac", type=float, default=0.70)
    p.add_argument("--val-frac", type=float, default=0.15)
    p.add_argument("--train-cutoff", type=str, default="2022-01-01", help="First day of validation window (ISO)")
    p.add_argument("--val-cutoff", type=str, default="2024-01-01", help="First day of test holdout (ISO)")
    p.add_argument("--hyperparams-json", type=Path, help="JSON dict from ml.hyperparameter_tune")
    p.add_argument("--no-calibrate", action="store_true", help="Skip isotonic calibration (debug)")
    p.add_argument("--model-dir", type=Path, default=None)
    args = p.parse_args()

    hp: dict[str, Any] | None = None
    if args.hyperparams_json and args.hyperparams_json.exists():
        hp = json.loads(args.hyperparams_json.read_text(encoding="utf-8"))

    train(
        train_cutoff=None if args.auto_split else _parse_date(args.train_cutoff),
        val_cutoff=None if args.auto_split else _parse_date(args.val_cutoff),
        auto_split=args.auto_split,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        hyperparams=hp,
        calibrate=not args.no_calibrate,
        model_dir=args.model_dir,
    )


if __name__ == "__main__":
    main()
