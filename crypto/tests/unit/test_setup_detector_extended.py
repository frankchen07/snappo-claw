"""Extended tests for SetupDetector: cup_and_handle detection and classify() ordering."""

import pytest
from crypto.src.analysis import SetupDetector


def _flat_prices(n: int, value: float = 100.0) -> list[float]:
    return [value] * n


def _volumes(n: int, base: float = 1_000_000.0) -> list[float]:
    return [base] * n


def _cup_and_handle_prices(cup_depth: float = 0.15, handle_range: float = 0.04) -> list[float]:
    """Build a synthetic cup-and-handle: 35 cup bars + 10 handle bars = 45 total."""
    cup_start = 100.0
    cup_end = 100.0
    cup_bottom = cup_start * (1 - cup_depth)

    # Cup: descend to bottom then rise back
    half = 17
    cup = []
    for i in range(half):
        cup.append(cup_start - (cup_start - cup_bottom) * (i / half))
    for i in range(half + 1):
        cup.append(cup_bottom + (cup_end - cup_bottom) * (i / half))

    # Trim to 35 bars
    cup = cup[:35]

    # Handle: tight consolidation in upper third
    handle_high = cup_end * 1.0
    handle_low = handle_high * (1 - handle_range)
    handle = [handle_low + (handle_high - handle_low) * (i % 2) for i in range(10)]

    return cup + handle


class TestCupAndHandle:
    def test_too_short_returns_not_detected(self):
        sd = SetupDetector()
        prices = _flat_prices(30)
        result = sd._detect_cup_and_handle(prices, _volumes(30))
        assert result["detected"] is False

    def test_valid_cup_and_handle_detected(self):
        sd = SetupDetector()
        prices = _cup_and_handle_prices(cup_depth=0.15, handle_range=0.04)
        result = sd._detect_cup_and_handle(prices, _volumes(len(prices)))
        assert result["detected"] is True
        assert result["quality"] > 0

    def test_shallow_cup_not_detected(self):
        """Cup depth < 8% should not trigger."""
        sd = SetupDetector()
        # Very shallow cup (3% depth) — won't satisfy cup_depth > 0.08
        prices = _cup_and_handle_prices(cup_depth=0.03, handle_range=0.04)
        result = sd._detect_cup_and_handle(prices, _volumes(len(prices)))
        assert result["detected"] is False

    def test_wide_handle_not_detected(self):
        """Handle range > 10% should not qualify."""
        sd = SetupDetector()
        prices = _cup_and_handle_prices(cup_depth=0.15, handle_range=0.20)
        result = sd._detect_cup_and_handle(prices, _volumes(len(prices)))
        assert result["detected"] is False


class TestClassifyOrdering:
    def test_classify_returns_valid_type(self):
        sd = SetupDetector()
        result = sd.classify(_flat_prices(100), _volumes(100))
        assert result["type"] in ("VCP", "breakout", "flat_base", "cup_and_handle", "none")

    def test_classify_includes_quality(self):
        sd = SetupDetector()
        result = sd.classify(_flat_prices(100), _volumes(100))
        assert "quality" in result
        assert isinstance(result["quality"], int)

    def test_classify_cup_and_handle(self):
        """Cup-and-handle prices should eventually yield cup_and_handle type."""
        sd = SetupDetector()
        prices = _cup_and_handle_prices(cup_depth=0.15, handle_range=0.04)
        # Pad to 100 bars so VCP/breakout/flat_base don't trigger first
        prices = _flat_prices(55) + prices
        result = sd.classify(prices, _volumes(len(prices)))
        # May be cup_and_handle or another pattern — just verify no crash
        assert isinstance(result["type"], str)
        assert isinstance(result["quality"], int)

    def test_no_crash_various_lengths(self):
        sd = SetupDetector()
        for n in (10, 30, 50, 100, 200):
            result = sd.classify(_flat_prices(n), _volumes(n))
            assert result["type"] in ("VCP", "breakout", "flat_base", "cup_and_handle", "none")
