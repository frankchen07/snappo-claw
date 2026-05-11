"""Pydantic schemas for all trading analysis inputs and outputs."""

from typing import Literal
from pydantic import BaseModel, field_validator


class MarketTrend(BaseModel):
    direction: Literal["uptrend", "downtrend", "sideways"]
    strength: Literal["strong", "moderate", "weak"]


class SetupInfo(BaseModel):
    type: Literal["VCP", "breakout", "flat_base", "none"]
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

    @field_validator("confidence_score")
    @classmethod
    def confidence_in_range(cls, v: int) -> int:
        if not 0 <= v <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        return v

    model_config = {"arbitrary_types_allowed": True}
