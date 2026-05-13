"""Minervini Stage 1-4 classification."""

import statistics
from typing import Any


def _slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def _rolling_ma(prices: list[float], period: int, samples: int = 10) -> list[float]:
    """Sample evenly spaced MA values over the price series for slope calculation."""
    result = []
    step = max(1, (len(prices) - period) // samples)
    for i in range(period, len(prices), step):
        result.append(statistics.mean(prices[i - period:i]))
    return result


class StageClassifier:
    def classify_stage(
        self,
        prices: list[float],
        volumes: list[float],
        moving_averages: dict[str, float | None],
    ) -> dict[str, Any]:
        """
        Classify Minervini market stage 1-4.
        Stage 1: Consolidation/basing
        Stage 2: Advancing
        Stage 3: Distribution/topping
        Stage 4: Decline
        """
        if len(prices) < 200:
            return {"stage": 1, "label": "Consolidation", "confidence": 30}

        ma50 = moving_averages.get("ma50")
        ma150 = moving_averages.get("ma150")
        ma200 = moving_averages.get("ma200")
        current = prices[-1]

        if not all([ma50, ma150, ma200]):
            return {"stage": 1, "label": "Consolidation", "confidence": 20}

        ma200_series = _rolling_ma(prices, 200)
        ma50_series = _rolling_ma(prices, 50)
        ma200_slope = _slope(ma200_series) if len(ma200_series) >= 2 else 0.0
        ma50_slope = _slope(ma50_series) if len(ma50_series) >= 2 else 0.0

        price_above_all = current > ma50 and current > ma150 and current > ma200
        price_below_all = current < ma50 and current < ma150 and current < ma200
        ma_stacked = ma50 > ma150 > ma200
        near_200ma = abs(current - ma200) / ma200 < 0.05

        avg_recent_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else 0
        avg_prior_vol = statistics.mean(volumes[-40:-20]) if len(volumes) >= 40 else avg_recent_vol
        rising_volume = avg_recent_vol > avg_prior_vol * 1.1 if avg_prior_vol > 0 else False

        lower_highs = lower_lows = False
        if len(prices) >= 20:
            recent_highs = [max(prices[i:i+5]) for i in range(len(prices)-20, len(prices)-5, 5)]
            recent_lows = [min(prices[i:i+5]) for i in range(len(prices)-20, len(prices)-5, 5)]
            if len(recent_highs) >= 2:
                lower_highs = all(recent_highs[i] > recent_highs[i+1] for i in range(len(recent_highs)-1))
            if len(recent_lows) >= 2:
                lower_lows = all(recent_lows[i] > recent_lows[i+1] for i in range(len(recent_lows)-1))

        # Stage 2: advancing
        if price_above_all and ma_stacked and ma200_slope >= 0:
            conf = 80
            if ma50_slope > 0 and rising_volume:
                conf = 90
            return {"stage": 2, "label": "Advancing", "confidence": conf}

        # Stage 4: decline
        if price_below_all and (lower_highs or lower_lows):
            conf = 75
            if lower_highs and lower_lows:
                conf = 85
            return {"stage": 4, "label": "Decline", "confidence": conf}

        # Stage 3: distribution (above 200MA but losing uptrend structure)
        if current > ma200 and ma50_slope < 0:
            return {"stage": 3, "label": "Distribution", "confidence": 65}

        # Stage 1: consolidation default
        conf = 75 if near_200ma else 60
        return {"stage": 1, "label": "Consolidation", "confidence": conf}
