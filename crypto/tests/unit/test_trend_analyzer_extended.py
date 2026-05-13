"""Extended tests for TrendAnalyzer additions: ma10, rs_line, detect_support_resistance."""

import pytest
from crypto.src.analysis import TrendAnalyzer


def _prices(n: int = 200, start: float = 100.0, drift: float = 0.002) -> list[float]:
    p = [start]
    for _ in range(n - 1):
        p.append(p[-1] * (1 + drift))
    return p


class TestMovingAveragesWithMA10:
    def test_ma10_present_in_output(self):
        ta = TrendAnalyzer()
        result = ta.moving_averages(_prices(50))
        assert "ma10" in result

    def test_ma10_is_none_when_insufficient_data(self):
        ta = TrendAnalyzer()
        result = ta.moving_averages(_prices(5))
        assert result["ma10"] is None

    def test_ma10_computed_correctly(self):
        prices = list(range(1, 21))  # 1..20
        ta = TrendAnalyzer()
        result = ta.moving_averages(prices)
        # Last 10 of [1..20] is [11..20], mean = 15.5
        assert result["ma10"] == pytest.approx(15.5)


class TestRsLine:
    def test_btc_vs_itself_is_1(self):
        ta = TrendAnalyzer()
        prices = _prices(100)
        result = ta.rs_line(prices, prices)
        assert result["value"] == pytest.approx(1.0)
        assert result["interpretation"] == "neutral"

    def test_outperforming_coin_is_strong(self):
        ta = TrendAnalyzer()
        # Coin goes up fast, BTC flat
        coin = _prices(100, drift=0.01)
        btc = _prices(100, drift=0.001)
        result = ta.rs_line(coin, btc)
        assert result["interpretation"] == "strong"
        assert result["value"] > 1.0

    def test_underperforming_coin_is_weak(self):
        ta = TrendAnalyzer()
        coin = _prices(100, drift=0.0005)
        btc = _prices(100, drift=0.008)
        result = ta.rs_line(coin, btc)
        assert result["interpretation"] == "weak"
        assert result["value"] < 1.0

    def test_too_short_returns_neutral(self):
        ta = TrendAnalyzer()
        result = ta.rs_line([100.0], [100.0])
        assert result["interpretation"] == "neutral"
        assert result["value"] == 1.0

    def test_returns_ratios_list(self):
        ta = TrendAnalyzer()
        prices = _prices(50)
        result = ta.rs_line(prices, prices)
        assert "ratios" in result
        assert len(result["ratios"]) > 0


class TestDetectSupportResistance:
    def _make_ohlc(self, prices):
        return [
            {
                "open": p * 0.999,
                "high": p * 1.01,
                "low": p * 0.99,
                "close": p,
            }
            for p in prices
        ]

    def test_returns_support_and_resistance_keys(self):
        ta = TrendAnalyzer()
        ohlc = self._make_ohlc([100.0] * 10)
        result = ta.detect_support_resistance(ohlc, 100.0)
        assert "support" in result
        assert "resistance" in result

    def test_too_short_returns_empty(self):
        ta = TrendAnalyzer()
        result = ta.detect_support_resistance([], 100.0)
        assert result["support"] == []
        assert result["resistance"] == []

    def test_resistance_above_current_price(self):
        ta = TrendAnalyzer()
        # Create a clear swing high above current price
        prices = [100, 100, 120, 100, 100, 100, 100, 100, 100, 100]
        ohlc = self._make_ohlc(prices)
        result = ta.detect_support_resistance(ohlc, 100.0)
        for r in result["resistance"]:
            assert r > 100.0

    def test_support_below_current_price(self):
        ta = TrendAnalyzer()
        prices = [100, 100, 80, 100, 100, 100, 100, 100, 100, 100]
        ohlc = self._make_ohlc(prices)
        result = ta.detect_support_resistance(ohlc, 100.0)
        for s in result["support"]:
            assert s < 100.0
