from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


class FighterBrief(BaseModel):
    fighter_id: str
    name: str


class FighterDetail(BaseModel):
    fighter_id: str
    name: str
    height_cm: float | None = None
    reach_cm: float | None = None
    weight_lbs: float | None = None
    stance: str | None = None
    dob: date | None = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    nc: int = 0


class EventSummary(BaseModel):
    event_id: str
    event_name: str
    date: date | None
    location: str | None = None
    is_upcoming: bool
    fight_count: int = 0


class EventDetail(EventSummary):
    fights: list["FightSummary"] = Field(default_factory=list)


class FightSummary(BaseModel):
    fight_id: str
    fighter_a: FighterBrief
    fighter_b: FighterBrief
    weight_class: str | None = None
    is_title_fight: bool = False


class TopFactor(BaseModel):
    feature: str
    impact: str
    favor: str


class FightPredictionResponse(BaseModel):
    fight_id: str
    fighter_a: dict[str, Any]
    fighter_b: dict[str, Any]
    top_factors: list[TopFactor] = Field(default_factory=list)
    predicted_method: str | None = None
    model_version: str
    generated_at: datetime


class ModelAccuracyPoint(BaseModel):
    period: str
    accuracy: float
    sample_size: int


class ModelAccuracyResponse(BaseModel):
    overall_accuracy: float | None
    roc_auc: float | None
    brier_score: float | None
    history: list[ModelAccuracyPoint] = Field(default_factory=list)


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class ModelFeaturesResponse(BaseModel):
    items: list[FeatureImportanceItem] = Field(default_factory=list)
