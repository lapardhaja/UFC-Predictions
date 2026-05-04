from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.config import get_settings


def load_model_metadata() -> dict[str, Any]:
    path = get_settings().model_dir / "metadata.json"
    if not path.exists():
        return {"overall_accuracy": None, "roc_auc": None, "brier_score": None, "history": []}
    return json.loads(path.read_text(encoding="utf-8"))


def feature_importance_from_disk() -> list[dict[str, Any]]:
    """If training saved importance — else empty."""
    p = get_settings().model_dir / "feature_importance.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))
