from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import (
    FeatureImportanceItem,
    ModelAccuracyPoint,
    ModelAccuracyResponse,
    ModelFeaturesResponse,
)
from backend.services.model_service import feature_importance_from_disk, load_model_metadata

router = APIRouter()


@router.get("/model/accuracy", response_model=ModelAccuracyResponse)
def model_accuracy() -> ModelAccuracyResponse:
    meta = load_model_metadata()
    m = meta.get("metrics", {})
    hist_raw = meta.get("history", [])
    hist = [ModelAccuracyPoint(**h) for h in hist_raw] if hist_raw else []
    if not hist and m.get("accuracy") is not None:
        hist = [ModelAccuracyPoint(period="latest", accuracy=float(m["accuracy"]), sample_size=0)]
    return ModelAccuracyResponse(
        overall_accuracy=m.get("accuracy"),
        roc_auc=m.get("roc_auc"),
        brier_score=m.get("brier"),
        history=hist,
    )


@router.get("/model/features", response_model=ModelFeaturesResponse)
def model_features() -> ModelFeaturesResponse:
    raw = feature_importance_from_disk()
    items = [FeatureImportanceItem(feature=r["feature"], importance=r["importance"]) for r in raw]
    return ModelFeaturesResponse(items=items)
