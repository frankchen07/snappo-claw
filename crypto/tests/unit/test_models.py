"""RED: Pydantic schema validation tests."""

import pytest
from pydantic import ValidationError


def test_analysis_output_requires_all_fields():
    from crypto.src.models import AnalysisOutput
    with pytest.raises(ValidationError):
        AnalysisOutput()


def test_analysis_output_disclaimer_always_set():
    from crypto.src.models import AnalysisOutput, MarketTrend, SetupInfo
    output = AnalysisOutput(
        symbol="BTC",
        timestamp="2026-05-10T00:00:00Z",
        market_trend=MarketTrend(direction="uptrend", strength="strong"),
        setup=SetupInfo(type="VCP", quality=8),
        entry_zone={"price": 65000.0, "range": [63000.0, 66000.0]},
        stop_level={"price": 60000.0, "invalidation_reason": "Below 50MA"},
        targets=[{"price": 75000.0, "rr_ratio": 2.0}],
        confidence_score=75,
        key_signals=["Price above all MAs", "Volume breakout"],
        risk_reward=2.0,
        disclaimer="Not financial advice.",
    )
    assert output.disclaimer == "Not financial advice."
    assert output.symbol == "BTC"


def test_market_trend_rejects_invalid_direction():
    from crypto.src.models import MarketTrend
    with pytest.raises(ValidationError):
        MarketTrend(direction="moon", strength="strong")


def test_market_trend_rejects_invalid_strength():
    from crypto.src.models import MarketTrend
    with pytest.raises(ValidationError):
        MarketTrend(direction="uptrend", strength="ultra")


def test_setup_info_quality_bounds():
    from crypto.src.models import SetupInfo
    with pytest.raises(ValidationError):
        SetupInfo(type="VCP", quality=11)
    with pytest.raises(ValidationError):
        SetupInfo(type="VCP", quality=0)


def test_setup_info_valid_types():
    from crypto.src.models import SetupInfo
    for t in ["VCP", "breakout", "flat_base", "none"]:
        s = SetupInfo(type=t, quality=5)
        assert s.type == t


def test_confidence_score_bounds():
    from crypto.src.models import AnalysisOutput, MarketTrend, SetupInfo
    base = dict(
        symbol="BTC",
        timestamp="2026-05-10T00:00:00Z",
        market_trend=MarketTrend(direction="uptrend", strength="strong"),
        setup=SetupInfo(type="none", quality=1),
        entry_zone={"price": 1.0, "range": [0.9, 1.1]},
        stop_level={"price": 0.8, "invalidation_reason": "test"},
        targets=[{"price": 1.5, "rr_ratio": 2.5}],
        key_signals=[],
        risk_reward=2.5,
        disclaimer="Not financial advice.",
    )
    with pytest.raises(ValidationError):
        AnalysisOutput(**base, confidence_score=101)
    with pytest.raises(ValidationError):
        AnalysisOutput(**base, confidence_score=-1)
    ok = AnalysisOutput(**base, confidence_score=50)
    assert ok.confidence_score == 50
