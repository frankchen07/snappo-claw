"""Unit tests for StageClassifier."""

import pytest
from crypto.src.stage_detector import StageClassifier


def _make_prices(n: int, start: float = 100.0, drift: float = 0.003) -> list[float]:
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + drift))
    return prices


def _make_volumes(n: int, base: float = 1_000_000.0) -> list[float]:
    return [base] * n


class TestStageClassifier:
    def test_returns_stage_1_when_insufficient_data(self):
        sc = StageClassifier()
        prices = _make_prices(100)
        result = sc.classify_stage(prices, _make_volumes(100), {"ma50": 100.0, "ma150": 99.0, "ma200": 98.0})
        assert result["stage"] == 1
        assert result["label"] == "Consolidation"

    def test_returns_stage_1_when_mas_missing(self):
        sc = StageClassifier()
        prices = _make_prices(300)
        result = sc.classify_stage(prices, _make_volumes(300), {"ma50": None, "ma150": None, "ma200": None})
        assert result["stage"] == 1

    def test_stage_2_uptrend(self):
        sc = StageClassifier()
        # Strong uptrend: price above all MAs, MAs stacked
        prices = _make_prices(300, start=50.0, drift=0.005)
        current = prices[-1]
        mas = {
            "ma10": current * 0.98,
            "ma50": current * 0.95,
            "ma150": current * 0.90,
            "ma200": current * 0.85,
        }
        result = sc.classify_stage(prices, _make_volumes(300), mas)
        assert result["stage"] == 2
        assert result["label"] == "Advancing"
        assert result["confidence"] >= 70

    def test_stage_4_decline(self):
        sc = StageClassifier()
        # Price below all MAs
        prices = _make_prices(300, start=200.0, drift=-0.004)
        current = prices[-1]
        mas = {
            "ma10": current * 1.10,
            "ma50": current * 1.15,
            "ma150": current * 1.20,
            "ma200": current * 1.25,
        }
        result = sc.classify_stage(prices, _make_volumes(300), mas)
        assert result["stage"] in (3, 4)  # declining prices may hit 3 or 4

    def test_confidence_in_valid_range(self):
        sc = StageClassifier()
        prices = _make_prices(300)
        result = sc.classify_stage(prices, _make_volumes(300), {
            "ma10": 105.0, "ma50": 103.0, "ma150": 100.0, "ma200": 98.0,
        })
        assert 0 <= result["confidence"] <= 100

    def test_stage_label_matches_stage_number(self):
        sc = StageClassifier()
        label_map = {1: "Consolidation", 2: "Advancing", 3: "Distribution", 4: "Decline"}
        prices = _make_prices(300)
        result = sc.classify_stage(prices, _make_volumes(300), {
            "ma10": 105.0, "ma50": 103.0, "ma150": 100.0, "ma200": 98.0,
        })
        assert result["label"] == label_map[result["stage"]]
