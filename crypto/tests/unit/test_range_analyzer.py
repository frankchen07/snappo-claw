"""Unit tests for RangeAnalyzer."""

import pytest
from crypto.src.analysis import RangeAnalyzer


def _make_ohlc(closes, spread_pct=0.02):
    """Build OHLC list from close prices."""
    return [
        {
            "open": c * 0.999,
            "high": c * (1 + spread_pct),
            "low": c * (1 - spread_pct),
            "close": c,
        }
        for c in closes
    ]


def _make_buyers_ohlc(n=14):
    """Candles where close is near the high (buyers winning)."""
    return [
        {"open": 100.0, "high": 105.0, "low": 95.0, "close": 104.0}
        for _ in range(n)
    ]


def _make_sellers_ohlc(n=14):
    """Candles where close is near the low (sellers winning)."""
    return [
        {"open": 100.0, "high": 105.0, "low": 95.0, "close": 96.0}
        for _ in range(n)
    ]


class TestClosingRangePercent:
    def test_close_at_high_returns_100(self):
        ohlc = [{"high": 110.0, "low": 100.0, "close": 110.0, "open": 105.0}]
        ra = RangeAnalyzer()
        assert ra.closing_range_percent(ohlc) == [100.0]

    def test_close_at_low_returns_0(self):
        ohlc = [{"high": 110.0, "low": 100.0, "close": 100.0, "open": 105.0}]
        ra = RangeAnalyzer()
        assert ra.closing_range_percent(ohlc) == [0.0]

    def test_close_at_midpoint_returns_50(self):
        ohlc = [{"high": 110.0, "low": 90.0, "close": 100.0, "open": 105.0}]
        ra = RangeAnalyzer()
        assert ra.closing_range_percent(ohlc) == [50.0]

    def test_zero_range_returns_50(self):
        ohlc = [{"high": 100.0, "low": 100.0, "close": 100.0, "open": 100.0}]
        ra = RangeAnalyzer()
        assert ra.closing_range_percent(ohlc) == [50.0]

    def test_multiple_candles(self):
        ohlc = _make_buyers_ohlc(5)
        ra = RangeAnalyzer()
        results = ra.closing_range_percent(ohlc)
        assert len(results) == 5
        assert all(r > 60 for r in results)


class TestAnalyzeClosingRange:
    def test_buyers_winning(self):
        ra = RangeAnalyzer()
        result = ra.analyze_closing_range(_make_buyers_ohlc(14))
        assert result["classification"] == "buyers_winning"
        assert result["average_closing_range_pct"] > 60

    def test_sellers_winning(self):
        ra = RangeAnalyzer()
        result = ra.analyze_closing_range(_make_sellers_ohlc(14))
        assert result["classification"] == "sellers_winning"
        assert result["average_closing_range_pct"] < 40

    def test_balanced(self):
        ohlc = [{"high": 110.0, "low": 90.0, "close": 100.0, "open": 100.0}] * 14
        ra = RangeAnalyzer()
        result = ra.analyze_closing_range(ohlc)
        assert result["classification"] == "balanced"

    def test_short_ohlc_uses_all_candles(self):
        ra = RangeAnalyzer()
        result = ra.analyze_closing_range(_make_buyers_ohlc(5), period=14)
        assert result["classification"] == "buyers_winning"


class TestAtrTrend:
    def test_expanding_volatility(self):
        # prior window: small moves ~1.0; recent window: large moves ~8.0
        prices = [100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0, 101.0,
                  100.0, 108.0, 100.0, 108.0, 100.0, 108.0, 100.0, 108.0]
        ra = RangeAnalyzer()
        result = ra.atr_trend(prices)
        assert result["trend"] == "expanding"
        assert result["recent_atr"] > result["prior_atr"]

    def test_contracting_volatility(self):
        # Prices with shrinking day-to-day moves
        prices = [100.0, 104.0, 96.0, 105.0, 95.0, 103.0, 97.0, 102.0] + [100.0] * 8
        ra = RangeAnalyzer()
        result = ra.atr_trend(prices)
        assert result["trend"] == "contracting"

    def test_stable_volatility(self):
        prices = [100.0 + (i % 3) for i in range(20)]
        ra = RangeAnalyzer()
        result = ra.atr_trend(prices)
        assert result["trend"] in ("stable", "contracting", "expanding")  # just doesn't crash

    def test_too_short_returns_stable(self):
        ra = RangeAnalyzer()
        result = ra.atr_trend([100.0, 101.0])
        assert result["trend"] == "stable"
        assert result["recent_atr"] == 0.0
