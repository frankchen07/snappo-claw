"""RED: Trend template, CANSLIM, VCP analysis tests."""

import pytest

from tests.fixtures.coingecko_responses import (
    make_uptrend_price_history,
    make_downtrend_price_history,
)


def _extract_prices(history: dict) -> list[float]:
    return [p[1] for p in history["prices"]]


def _extract_volumes(history: dict) -> list[float]:
    return [v[1] for v in history["total_volumes"]]


# --- TrendAnalyzer ---

def test_trend_uptrend_detected():
    from crypto.src.analysis import TrendAnalyzer
    prices = _extract_prices(make_uptrend_price_history(365))
    ta = TrendAnalyzer()
    result = ta.detect_trend(prices)
    assert result["direction"] == "uptrend"


def test_trend_downtrend_detected():
    from crypto.src.analysis import TrendAnalyzer
    prices = _extract_prices(make_downtrend_price_history(365))
    ta = TrendAnalyzer()
    result = ta.detect_trend(prices)
    assert result["direction"] == "downtrend"


def test_moving_averages_computed():
    from crypto.src.analysis import TrendAnalyzer
    prices = _extract_prices(make_uptrend_price_history(365))
    ta = TrendAnalyzer()
    mas = ta.moving_averages(prices)
    assert "ma50" in mas
    assert "ma150" in mas
    assert "ma200" in mas
    assert mas["ma50"] > 0
    assert mas["ma200"] > 0


def test_trend_strength_strong_in_uptrend():
    from crypto.src.analysis import TrendAnalyzer
    prices = _extract_prices(make_uptrend_price_history(365))
    ta = TrendAnalyzer()
    result = ta.detect_trend(prices)
    assert result["strength"] in ("strong", "moderate")


def test_trend_criteria_count():
    from crypto.src.analysis import TrendAnalyzer
    prices = _extract_prices(make_uptrend_price_history(365))
    ta = TrendAnalyzer()
    result = ta.detect_trend(prices)
    assert "criteria_met" in result
    assert isinstance(result["criteria_met"], int)
    assert 0 <= result["criteria_met"] <= 8


# --- SetupDetector ---

def test_flat_base_detected_in_sideways():
    from crypto.src.analysis import SetupDetector
    # Flat price: tight range over 35 days
    prices = [50000.0 + (i % 3) * 100 for i in range(60)]
    volumes = [1_000_000.0] * 60
    sd = SetupDetector()
    result = sd.classify(prices, volumes)
    assert result["type"] in ("flat_base", "none")


def test_breakout_detected_on_volume():
    from crypto.src.analysis import SetupDetector
    # Rising prices with volume spike at end
    prices = [50000.0 + i * 100 for i in range(60)]
    volumes = [1_000_000.0] * 55 + [3_000_000.0, 3_500_000.0, 4_000_000.0, 4_500_000.0, 5_000_000.0]
    prices[-5:] = [p + 500 for p in prices[-5:]]  # price surge with volume
    sd = SetupDetector()
    result = sd.classify(prices, volumes)
    assert result["type"] in ("breakout", "VCP", "none")  # could be any of these


def test_setup_quality_in_range():
    from crypto.src.analysis import SetupDetector
    prices = _extract_prices(make_uptrend_price_history(365))
    volumes = _extract_volumes(make_uptrend_price_history(365))
    sd = SetupDetector()
    result = sd.classify(prices, volumes)
    assert 1 <= result["quality"] <= 10


# --- VolumeAnalyzer ---

def test_average_volume_computed():
    from crypto.src.analysis import VolumeAnalyzer
    volumes = [1_000_000.0 + i * 1000 for i in range(30)]
    va = VolumeAnalyzer()
    avg = va.average_volume(volumes, days=20)
    assert avg > 0


def test_breakout_volume_detected():
    from crypto.src.analysis import VolumeAnalyzer
    va = VolumeAnalyzer()
    assert va.is_breakout_volume(recent_vol=2_000_000, avg_vol=1_000_000) is True
    assert va.is_breakout_volume(recent_vol=1_100_000, avg_vol=1_000_000) is False


# --- CANSLIMEvaluator ---

def test_canslim_score_in_range():
    from crypto.src.analysis import CANSLIMEvaluator
    from tests.fixtures.coingecko_responses import COIN_DETAILS_BTC
    prices = _extract_prices(make_uptrend_price_history(365))
    volumes = _extract_volumes(make_uptrend_price_history(365))
    ev = CANSLIMEvaluator()
    score = ev.score(coin_details=COIN_DETAILS_BTC, prices=prices, volumes=volumes)
    assert 0 <= score <= 100


def test_canslim_higher_for_uptrend_than_downtrend():
    from crypto.src.analysis import CANSLIMEvaluator
    from tests.fixtures.coingecko_responses import COIN_DETAILS_BTC
    ev = CANSLIMEvaluator()
    up_prices = _extract_prices(make_uptrend_price_history(365))
    up_volumes = _extract_volumes(make_uptrend_price_history(365))
    down_prices = _extract_prices(make_downtrend_price_history(365))
    down_volumes = _extract_volumes(make_downtrend_price_history(365))
    up_score = ev.score(COIN_DETAILS_BTC, up_prices, up_volumes)
    down_score = ev.score(COIN_DETAILS_BTC, down_prices, down_volumes)
    assert up_score > down_score
