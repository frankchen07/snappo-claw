"""CANSLIM + Minervini trend template + VCP analysis engine."""

import statistics
from typing import Any


def _moving_average(prices: list[float], period: int) -> float | None:
    if len(prices) < period:
        return None
    return statistics.mean(prices[-period:])


def _slope(values: list[float]) -> float:
    """Linear regression slope (simple rise/run over the series)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


class TrendAnalyzer:
    def moving_averages(self, prices: list[float]) -> dict[str, float | None]:
        return {
            "ma10": _moving_average(prices, 10),
            "ma50": _moving_average(prices, 50),
            "ma150": _moving_average(prices, 150),
            "ma200": _moving_average(prices, 200),
        }

    def detect_trend(self, prices: list[float]) -> dict[str, Any]:
        if len(prices) < 200:
            return {"direction": "sideways", "strength": "weak", "criteria_met": 0}

        mas = self.moving_averages(prices)
        ma50 = mas["ma50"]
        ma150 = mas["ma150"]
        ma200 = mas["ma200"]
        current = prices[-1]
        high_52w = max(prices[-365:]) if len(prices) >= 365 else max(prices)
        low_52w = min(prices[-365:]) if len(prices) >= 365 else min(prices)

        criteria = [
            current > ma150,                             # 1
            ma150 > ma200,                               # 2
            _slope(prices[-30:]) > 0,                   # 3 — 200MA trending up proxy
            ma50 > ma150,                                # 4
            ma50 > ma200,                                # 5
            current > ma50,                              # 6
            current >= high_52w * 0.75,                 # 7 — within 25% of 52w high
            current >= low_52w * 1.30,                  # 8 — 30% above 52w low
        ]
        met = sum(1 for c in criteria if c)
        ma200_slope = _slope(prices[-30:])

        if met >= 6 and criteria[0] and criteria[1]:
            direction = "uptrend"
            strength = "strong" if (met == 8 and ma200_slope > 0) else "moderate"
        elif not criteria[0] and not criteria[1] and not criteria[5]:
            direction = "downtrend"
            strength = "strong" if met <= 2 else "moderate"
        else:
            direction = "sideways"
            strength = "moderate" if met >= 4 else "weak"

        return {"direction": direction, "strength": strength, "criteria_met": met}

    def rs_line(self, coin_prices: list[float], btc_prices: list[float], window: int = 90) -> dict:
        """Relative strength vs BTC over a rolling window."""
        n = min(len(coin_prices), len(btc_prices), window)
        if n < 2:
            return {"value": 1.0, "interpretation": "neutral", "trend": "flat", "ratios": []}

        coin = coin_prices[-n:]
        btc = btc_prices[-n:]

        if coin[0] == 0 or btc[0] == 0:
            return {"value": 1.0, "interpretation": "neutral", "trend": "flat", "ratios": []}

        ratios = [(coin[i] / coin[0]) / (btc[i] / btc[0]) for i in range(n)]
        current = ratios[-1]
        slope = _slope(ratios[-20:]) if len(ratios) >= 20 else _slope(ratios)

        interpretation = "strong" if current > 1.1 else "weak" if current < 0.9 else "neutral"
        trend = "rising" if slope > 0.001 else "falling" if slope < -0.001 else "flat"

        return {"value": round(current, 3), "interpretation": interpretation, "trend": trend, "ratios": ratios}

    def detect_support_resistance(self, ohlc: list[dict], current_price: float) -> dict:
        """Detect swing pivot support/resistance from recent OHLC data."""
        if len(ohlc) < 5:
            return {"support": [], "resistance": []}

        highs = [row["high"] for row in ohlc]
        lows = [row["low"] for row in ohlc]

        swing_highs, swing_lows = [], []
        for i in range(2, len(ohlc) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])

        resistance = sorted(h for h in swing_highs if h > current_price)[:2]
        support = sorted((l for l in swing_lows if l < current_price), reverse=True)[:2]

        return {
            "support": [round(s, 2) for s in support],
            "resistance": [round(r, 2) for r in resistance],
        }


class VolumeAnalyzer:
    def average_volume(self, volumes: list[float], days: int = 20) -> float:
        if not volumes:
            return 0.0
        window = volumes[-days:] if len(volumes) >= days else volumes
        return statistics.mean(window)

    def is_breakout_volume(self, recent_vol: float, avg_vol: float) -> bool:
        return avg_vol > 0 and recent_vol >= avg_vol * 1.5


class RangeAnalyzer:
    def closing_range_percent(self, ohlc: list[dict]) -> list[float]:
        """Per-candle (close - low) / (high - low) * 100."""
        result = []
        for row in ohlc:
            rng = row["high"] - row["low"]
            result.append((row["close"] - row["low"]) / rng * 100 if rng > 0 else 50.0)
        return result

    def analyze_closing_range(self, ohlc: list[dict], period: int = 14) -> dict:
        """Average closing range % over the period, with buyer/seller classification."""
        window = ohlc[-period:] if len(ohlc) >= period else ohlc
        crp = self.closing_range_percent(window)
        avg = statistics.mean(crp) if crp else 50.0
        classification = "buyers_winning" if avg > 60 else "sellers_winning" if avg < 40 else "balanced"
        return {"average_closing_range_pct": round(avg, 1), "classification": classification}

    def atr_trend(self, prices: list[float]) -> dict:
        """Compare recent 7d ATR vs prior 7d ATR: expanding / contracting / stable."""
        if len(prices) < 15:
            return {"trend": "stable", "recent_atr": 0.0, "prior_atr": 0.0}

        def _atr(p: list[float]) -> float:
            ranges = [abs(p[i] - p[i-1]) for i in range(1, len(p))]
            return statistics.mean(ranges) if ranges else 0.0

        recent_atr = _atr(prices[-8:])
        prior_atr = _atr(prices[-15:-7])

        if prior_atr > 0:
            ratio = recent_atr / prior_atr
            trend = "expanding" if ratio > 1.15 else "contracting" if ratio < 0.85 else "stable"
        else:
            trend = "stable"

        return {"trend": trend, "recent_atr": round(recent_atr, 2), "prior_atr": round(prior_atr, 2)}


class SetupDetector:
    def _atr(self, prices: list[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 0.0
        ranges = [abs(prices[i] - prices[i - 1]) for i in range(-period, 0)]
        return statistics.mean(ranges)

    def _detect_vcp(self, prices: list[float], volumes: list[float]) -> dict:
        if len(prices) < 40:
            return {"detected": False}
        window = prices[-40:]
        vols = volumes[-40:] if len(volumes) >= 40 else volumes

        third = len(window) // 3
        vol1 = statistics.stdev(window[:third]) if third > 1 else 0
        vol2 = statistics.stdev(window[third:2*third]) if third > 1 else 0
        vol3 = statistics.stdev(window[2*third:]) if third > 1 else 0

        contracting = vol1 > vol2 > vol3 and vol3 < vol1 * 0.6
        recent_price_surge = prices[-1] > max(prices[-20:-5]) * 0.99
        avg_vol = statistics.mean(vols[:-5]) if len(vols) > 5 else 1
        vol_breakout = vols[-1] >= avg_vol * 1.4 if avg_vol > 0 else False

        if contracting and recent_price_surge:
            return {"detected": True, "quality": 7 if vol_breakout else 5}
        return {"detected": False}

    def _detect_flat_base(self, prices: list[float]) -> dict:
        if len(prices) < 35:
            return {"detected": False}
        window = prices[-35:]
        high = max(window)
        low = min(window)
        pct_range = (high - low) / low if low > 0 else 1.0
        if pct_range <= 0.12:
            return {"detected": True, "quality": 6}
        return {"detected": False}

    def _detect_breakout(self, prices: list[float], volumes: list[float]) -> dict:
        if len(prices) < 25 or len(volumes) < 25:
            return {"detected": False}
        recent_high = max(prices[-25:-5])
        current = prices[-1]
        avg_vol = statistics.mean(volumes[-25:-5]) if len(volumes) >= 25 else 1
        recent_vol = volumes[-1] if volumes else 0
        if current > recent_high and recent_vol >= avg_vol * 1.3:
            return {"detected": True, "quality": 7}
        return {"detected": False}

    def _detect_cup_and_handle(self, prices: list[float], volumes: list[float]) -> dict:
        """30+ day U-shape followed by 5-15 day tight handle in upper third."""
        if len(prices) < 45:
            return {"detected": False}

        cup_window = prices[-45:-10]
        handle_window = prices[-10:]

        cup_start = cup_window[0]
        cup_end = cup_window[-1]
        cup_low = min(cup_window)
        mid = len(cup_window) // 2
        cup_mid = statistics.mean(cup_window[max(0, mid-2):min(len(cup_window), mid+3)])

        cup_depth = (min(cup_start, cup_end) - cup_low) / cup_low if cup_low > 0 else 0
        is_u_shape = cup_mid < cup_start * 0.93 and cup_mid < cup_end * 0.93 and cup_depth > 0.08

        if not is_u_shape:
            return {"detected": False}

        handle_high = max(handle_window)
        handle_low = min(handle_window)
        handle_range_pct = (handle_high - handle_low) / handle_low if handle_low > 0 else 1.0

        full_top = max(cup_start, cup_end)
        upper_third_bottom = cup_low + (full_top - cup_low) * 0.67
        handle_in_upper_third = handle_low >= upper_third_bottom

        if handle_range_pct <= 0.10 and handle_in_upper_third:
            return {"detected": True, "quality": 7}
        return {"detected": False}

    def classify(self, prices: list[float], volumes: list[float]) -> dict:
        vcp = self._detect_vcp(prices, volumes)
        if vcp["detected"]:
            return {"type": "VCP", "quality": vcp["quality"]}

        breakout = self._detect_breakout(prices, volumes)
        if breakout["detected"]:
            return {"type": "breakout", "quality": breakout["quality"]}

        flat = self._detect_flat_base(prices)
        if flat["detected"]:
            return {"type": "flat_base", "quality": flat["quality"]}

        cup_handle = self._detect_cup_and_handle(prices, volumes)
        if cup_handle["detected"]:
            return {"type": "cup_and_handle", "quality": cup_handle["quality"]}

        return {"type": "none", "quality": 3}


class CANSLIMEvaluator:
    """Crypto-adapted CANSLIM scoring. Returns 0-100."""

    def score(self, coin_details: dict, prices: list[float], volumes: list[float]) -> float:
        scores = []

        # C — current momentum (90-day ROC)
        if len(prices) >= 90:
            roc_90 = (prices[-1] - prices[-90]) / prices[-90] * 100
            scores.append(min(25, max(0, 12.5 + roc_90 * 0.1)))
        else:
            scores.append(10)

        # A — annual trend (1Y ROC)
        if len(prices) >= 250:
            roc_1y = (prices[-1] - prices[-250]) / prices[-250] * 100
            scores.append(min(15, max(0, 7.5 + roc_1y * 0.03)))
        else:
            scores.append(7)

        # N — proximity to ATH / new high
        md = coin_details.get("market_data", {})
        ath = md.get("ath", {}).get("usd") or md.get("high_52_weeks", {}).get("usd")
        current = prices[-1] if prices else 0
        if ath and ath > 0:
            pct_from_ath = (ath - current) / ath
            n_score = max(0, 15 * (1 - pct_from_ath * 2))
        else:
            n_score = 7
        scores.append(n_score)

        # S — supply/demand (relative volume vs 20-day avg)
        va = VolumeAnalyzer()
        avg_vol = va.average_volume(volumes, days=20)
        if avg_vol > 0 and volumes:
            rel_vol = volumes[-1] / avg_vol
            s_score = min(15, max(0, rel_vol * 7.5))
        else:
            s_score = 5
        scores.append(s_score)

        # L — market cap rank (leader = top 20)
        rank = coin_details.get("market_cap_rank", 999)
        if rank and rank <= 5:
            scores.append(10)
        elif rank and rank <= 20:
            scores.append(7)
        elif rank and rank <= 50:
            scores.append(4)
        else:
            scores.append(1)

        # M — market direction proxy (50MA vs 200MA)
        if len(prices) >= 200:
            ma50 = _moving_average(prices, 50)
            ma200 = _moving_average(prices, 200)
            scores.append(10 if (ma50 and ma200 and ma50 > ma200) else 3)
        else:
            scores.append(5)

        # I — volume trend (institutional proxy: rising volume in uptrend)
        if len(volumes) >= 30:
            early_vol = statistics.mean(volumes[-30:-15])
            late_vol = statistics.mean(volumes[-15:])
            scores.append(10 if late_vol > early_vol else 3)
        else:
            scores.append(5)

        return min(100, sum(scores))
