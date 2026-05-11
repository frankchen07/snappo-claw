"""RED: Output formatting tests."""

import json
import pytest


@pytest.fixture
def sample_analysis():
    from crypto.src.models import AnalysisOutput, MarketTrend, SetupInfo
    return AnalysisOutput(
        symbol="BTC",
        timestamp="2026-05-10T12:00:00Z",
        market_trend=MarketTrend(direction="uptrend", strength="strong"),
        setup=SetupInfo(type="VCP", quality=8),
        entry_zone={"price": 65000.0, "range": [63000.0, 66500.0]},
        stop_level={"price": 60000.0, "invalidation_reason": "Close below 50MA"},
        targets=[
            {"price": 72000.0, "rr_ratio": 1.4},
            {"price": 80000.0, "rr_ratio": 3.0},
        ],
        confidence_score=78,
        key_signals=["Price > all MAs", "Volume breakout 2.3x avg", "Near 52w high"],
        risk_reward=2.1,
        disclaimer="Not financial advice.",
    )


def test_to_dict_returns_all_fields(sample_analysis):
    from crypto.src.format import to_dict
    d = to_dict(sample_analysis)
    assert d["symbol"] == "BTC"
    assert d["confidence_score"] == 78
    assert d["disclaimer"] == "Not financial advice."
    assert "market_trend" in d
    assert "setup" in d
    assert "entry_zone" in d
    assert "stop_level" in d
    assert "targets" in d


def test_to_json_is_valid_json(sample_analysis):
    from crypto.src.format import to_json
    result = to_json(sample_analysis)
    parsed = json.loads(result)
    assert parsed["symbol"] == "BTC"


def test_to_markdown_contains_key_sections(sample_analysis):
    from crypto.src.format import to_markdown
    md = to_markdown(sample_analysis)
    assert "BTC" in md
    assert "uptrend" in md.lower()
    assert "VCP" in md
    assert "Not financial advice" in md
    assert "65000" in md or "65,000" in md


def test_to_markdown_includes_disclaimer(sample_analysis):
    from crypto.src.format import to_markdown
    md = to_markdown(sample_analysis)
    assert "Not financial advice" in md
