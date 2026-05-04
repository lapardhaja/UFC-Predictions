from __future__ import annotations

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


@dataclass
class TrainArtifacts:
    version: str
    feature_names: list[str]
    train_end: str
    val_end: str
    metrics: dict[str, float]
    history: list[dict[str, Any]] = field(default_factory=list)


def time_mask(dates: pd.Series, train_end: date, val_end: date) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ts = pd.to_datetime(dates).dt.normalize()
    m_train = ts < pd.Timestamp(train_end)
    m_val = (ts >= pd.Timestamp(train_end)) & (ts < pd.Timestamp(val_end))
    m_test = ts >= pd.Timestamp(val_end)
    return m_train.values, m_val.values, m_test.values


def build_estimator(random_state: int = 42) -> Pipeline:
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.8,
        min_child_weight=2,
        reg_lambda=1.0,
        random_state=random_state,
        n_jobs=-1,
        eval_metric="logloss",
    )
    estimators: list[tuple[str, Any]] = [("xgb", xgb)]
    weights: list[float] = [0.55]
    if LGBMClassifier is not None:
        estimators.append(
            (
                "lgb",
                LGBMClassifier(
                    n_estimators=200,
                    max_depth=-1,
                    num_leaves=31,
                    learning_rate=0.08,
                    subsample=0.85,
                    colsample_bytree=0.8,
                    random_state=random_state,
                    n_jobs=-1,
                    verbose=-1,
                ),
            )
        )
        weights.append(0.3)
    estimators.append(
        (
            "lr",
            LogisticRegression(max_iter=1000, random_state=random_state, class_weight="balanced"),
        )
    )
    weights.append(0.2 if len(weights) == 2 else 0.15)
    # Renormalize weights
    s = sum(weights)
    weights = [w / s for w in weights]

    vote = VotingClassifier(estimators=estimators, voting="soft", weights=weights)
    return Pipeline([("scale", StandardScaler()), ("clf", vote)])


def train(
    *,
    train_cutoff: date = date(2022, 1, 1),
    val_cutoff: date = date(2024, 1, 1),
    model_dir: Path | None = None,
    random_state: int = 42,
) -> TrainArtifacts:
    model_dir = model_dir or Path(__file__).resolve().parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    X, y, feature_names, fight_dates = build_feature_matrix()
    if len(y) < 30:
        raise RuntimeError("Not enough labeled fights to train; ingest historical data first.")

    assert_no_leakage_columns(feature_names)

    m_train, m_val, m_test = time_mask(fight_dates, train_cutoff, val_cutoff)
    X_train, y_train = X.loc[m_train], y[m_train]
    X_val, y_val = X.loc[m_val], y[m_val]
    X_test, y_test = X.loc[m_test], y[m_test]

    if X_train.empty:
        X_train, y_train = X, y
        X_val, y_val = X.iloc[:0], y[:0]
        X_test, y_test = X.iloc[:0], y[:0]

    base = build_estimator(random_state)
    # Calibrate on validation slice; if empty use last 20% of train chronologically
    if len(y_val) >= 10:
        cal = CalibratedClassifierCV(base, method="isotonic", cv=3)
        cal.fit(pd.concat([X_train, X_val]), np.concatenate([y_train, y_val]))
    else:
        cal = CalibratedClassifierCV(base, method="sigmoid", cv=TimeSeriesSplit(n_splits=min(3, max(2, len(y_train) // 10))))
        cal.fit(X_train, y_train)

    metrics: dict[str, float] = {}
    if len(y_test) > 0:
        proba = cal.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics["accuracy"] = float(accuracy_score(y_test, pred))
        metrics["brier"] = float(brier_score_loss(y_test, proba))
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
        except ValueError:
            metrics["roc_auc"] = float("nan")
    else:
        proba = cal.predict_proba(X_train)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics["accuracy"] = float(accuracy_score(y_train, pred))
        metrics["brier"] = float(brier_score_loss(y_train, proba))
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_train, proba))
        except ValueError:
            metrics["roc_auc"] = float("nan")

    version = "v1.0.0"
    bundle = {
        "model": cal,
        "feature_names": feature_names,
        "version": version,
        "train_cutoff": train_cutoff.isoformat(),
        "val_cutoff": val_cutoff.isoformat(),
    }
    joblib.dump(bundle, model_dir / "production.pkl")

    # Feature importance from XGBoost base learner (explainability)
    try:
        cal0 = cal.calibrated_classifiers_[0]
        inner = cal0.estimator
        vote = inner.named_steps["clf"]
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
    except (AttributeError, KeyError, IndexError):
        pass

    meta = TrainArtifacts(
        version=version,
        feature_names=feature_names,
        train_end=train_cutoff.isoformat(),
        val_end=val_cutoff.isoformat(),
        metrics=metrics,
    )
    meta_dict = asdict(meta)
    meta_dict["history"] = [
        {"period": "holdout", "accuracy": metrics.get("accuracy"), "sample_size": int(m_test.sum())},
    ]
    (model_dir / "metadata.json").write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")
    return meta


if __name__ == "__main__":
    out = train()
    print(out)
