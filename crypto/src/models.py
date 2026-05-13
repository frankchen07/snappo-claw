"""Pydantic schemas for all trading analysis inputs and outputs."""

from typing import Literal
from pydantic import BaseModel, field_validator


class MarketTrend(BaseModel):
    direction: Literal["uptrend", "downtrend", "sideways"]
    strength: Literal["strong", "moderate", "weak"]


class SetupInfo(BaseModel):
    type: Literal["VCP", "breakout", "flat_base", "cup_and_handle", "none"]
    quality: int  # 1-10

    @field_validator("quality")
    @classmethod
    def quality_in_range(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("quality must be between 1 and 10")
        return v


class PriceLevel(BaseModel):
    price: float
    range: list[float] | None = None
    invalidation_reason: str | None = None


class Target(BaseModel):
    price: float
    rr_ratio: float


class PriceStructure(BaseModel):
    ma10: float | None = None
    ma50: float | None = None
    ma150: float | None = None
    ma200: float | None = None
    rs_value: float | None = None
    rs_interpretation: str | None = None  # "strong" | "weak" | "neutral"
    rs_trend: str | None = None           # "rising" | "falling" | "flat"
    support: list[float] = []
    resistance: list[float] = []


class RangeMetrics(BaseModel):
    closing_range_pct: float | None = None
    closing_range_class: str | None = None  # "buyers_winning" | "sellers_winning" | "balanced"
    atr_trend: str | None = None            # "expanding" | "contracting" | "stable"
    recent_atr: float | None = None
    prior_atr: float | None = None


class PatternInfo(BaseModel):
    primary: str   # "VCP" | "breakout" | "flat_base" | "cup_and_handle" | "none"
    quality: int


class StageInfo(BaseModel):
    stage: int    # 1-4
    label: str    # "Consolidation" | "Advancing" | "Distribution" | "Decline"
    confidence: int


class EcologicalFramework(BaseModel):
    price_structure: PriceStructure
    range_metrics: RangeMetrics
    pattern: PatternInfo
    stage: StageInfo
    expectations: str
    data_notes: list[str] = []


class AnalysisOutput(BaseModel):
    symbol: str
    timestamp: str
    market_trend: MarketTrend
    setup: SetupInfo
    entry_zone: dict
    stop_level: dict
    targets: list[dict]
    confidence_score: int  # 0-100
    key_signals: list[str]
    risk_reward: float
    disclaimer: str
    ecological_framework: EcologicalFramework | None = None

    @field_validator("confidence_score")
    @classmethod
    def confidence_in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        return v

    model_config = {"arbitrary_types_allowed": True}
