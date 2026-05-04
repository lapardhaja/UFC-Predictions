from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, classification_report, roc_auc_score

from ml.feature_builder import build_feature_matrix


def load_bundle(path: Path | None = None) -> dict[str, Any]:
    path = path or Path(__file__).resolve().parent / "models" / "production.pkl"
    if not path.exists():
        raise FileNotFoundError(path)
    return joblib.load(path)


def evaluate_holdout(year_start: int = 2024) -> dict[str, float]:
    X, y, _, fight_dates = build_feature_matrix()
    if X.empty:
        return {"accuracy": 0.0, "n": 0.0}
    mask = pd.to_datetime(fight_dates).dt.year >= year_start
    if not mask.any():
        mask = pd.Series([True] * len(X), index=X.index)
    Xh, yh = X.loc[mask], y[mask.values]
    bundle = load_bundle()
    model = bundle["model"]
    proba = model.predict_proba(Xh)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(yh, pred)),
        "brier": float(brier_score_loss(yh, proba)),
        "roc_auc": float(roc_auc_score(yh, proba)) if len(np.unique(yh)) > 1 else 0.0,
        "n": float(len(yh)),
    }


def print_report() -> None:
    bundle = load_bundle()
    X, y, _, _ = build_feature_matrix()
    model = bundle["model"]
    pred = model.predict(X)
    print(classification_report(y, pred, digits=3))


if __name__ == "__main__":
    print(evaluate_holdout())
