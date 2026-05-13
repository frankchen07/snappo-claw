"""RED: End-to-end pipeline integration tests."""

from unittest.mock import MagicMock, patch

import pytest

from tests.fixtures.coingecko_responses import (
    COIN_DETAILS_BTC,
    MARKETS_RESPONSE,
    make_uptrend_price_history,
    make_ohlc_30d,
)


@pytest.fixture
def tmp_crypto_dirs(tmp_path):
    cache_dir = tmp_path / "cache"
    knowledge_dir = tmp_path / "knowledge"
    cache_dir.mkdir()
    knowledge_dir.mkdir()
    (knowledge_dir / "raw").mkdir()
    (knowledge_dir / "processed").mkdir()
    return {"cache": str(cache_dir), "knowledge": str(knowledge_dir)}


def _mock_coingecko(tmp_dirs):
    """Patch CoinGecko calls with test data."""
    history = make_uptrend_price_history(365)

    ohlc = make_ohlc_30d()

    def fake_get(url, *args, **kwargs):
        m = MagicMock()
        m.status_code = 200
        m.raise_for_status = lambda: None
        if "market_chart" in url:
            m.json.return_value = history
        elif "/ohlc" in url:
            m.json.return_value = ohlc
        elif "markets" in url:
            m.json.return_value = MARKETS_RESPONSE
        else:
            m.json.return_value = COIN_DETAILS_BTC
        return m

    return fake_get


def test_analyze_coin_returns_valid_output(tmp_crypto_dirs):
    from crypto.src.cache import FileCache
    from crypto.src.fetch import CoinGeckoClient
    from crypto.src.analysis import TrendAnalyzer, SetupDetector, CANSLIMEvaluator, VolumeAnalyzer
    from crypto.src.models import AnalysisOutput

    cache = FileCache(cache_dir=tmp_crypto_dirs["cache"])
    client = CoinGeckoClient(cache=cache)

    with patch("requests.get", side_effect=_mock_coingecko(tmp_crypto_dirs)):
        history = client.get_market_chart("BTC", days=365)
        details = client.get_coin_details("BTC")

    prices = [row["price"] for row in history]
    volumes = [row["volume"] for row in history]

    ta = TrendAnalyzer()
    sd = SetupDetector()
    va = VolumeAnalyzer()
    ev = CANSLIMEvaluator()

    trend = ta.detect_trend(prices)
    setup = sd.classify(prices, volumes)
    canslim = ev.score(details, prices, volumes)
    avg_vol = va.average_volume(volumes)
    current_price = prices[-1]

    output = AnalysisOutput(
        symbol="BTC",
        timestamp="2026-05-10T12:00:00Z",
        market_trend={"direction": trend["direction"], "strength": trend["strength"]},
        setup={"type": setup["type"], "quality": setup["quality"]},
        entry_zone={"price": current_price, "range": [current_price * 0.97, current_price * 1.01]},
        stop_level={"price": current_price * 0.92, "invalidation_reason": "Below 50MA"},
        targets=[{"price": current_price * 1.15, "rr_ratio": 2.0}],
        confidence_score=min(100, int(canslim)),
        key_signals=[f"Trend: {trend['direction']}", f"Setup: {setup['type']}"],
        risk_reward=2.0,
        disclaimer="Not financial advice.",
    )

    assert output.symbol == "BTC"
    assert output.market_trend.direction in ("uptrend", "downtrend", "sideways")
    assert 0 <= output.confidence_score <= 100
    assert output.disclaimer == "Not financial advice."


def test_analyze_coin_cli_function(tmp_crypto_dirs):
    import os
    os.environ["CRYPTO_CACHE_DIR"] = tmp_crypto_dirs["cache"]
    os.environ["CRYPTO_KNOWLEDGE_DIR"] = tmp_crypto_dirs["knowledge"]

    with patch("requests.get", side_effect=_mock_coingecko(tmp_crypto_dirs)):
        from crypto.cli import analyze_coin
        result = analyze_coin("BTC")

    assert isinstance(result, dict)
    assert result["symbol"] == "BTC"
    assert "market_trend" in result
    assert "setup" in result
    assert "confidence_score" in result
    assert result["disclaimer"] == "Not financial advice."

    eco = result.get("ecological_framework")
    assert eco is not None, "ecological_framework must be present"
    assert eco["stage"]["stage"] in (1, 2, 3, 4)
    assert eco["stage"]["label"] in ("Consolidation", "Advancing", "Distribution", "Decline")
    assert isinstance(eco["expectations"], str) and len(eco["expectations"]) > 10
    assert eco["price_structure"]["rs_value"] == 1.0  # BTC vs BTC is always 1.0
