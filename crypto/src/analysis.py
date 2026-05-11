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
            current > ma150,                                      # 1
            ma150 > ma200,                                        # 2
            _slope(prices[-30:]) > 0,                            # 3 — 200MA trending up proxy
            ma50 > ma150,                                         # 4
            ma50 > ma200,                                         # 5
            current > ma50,                                       # 6
            current >= high_52w * 0.75,                          # 7 — within 25% of 52w high
            current >= low_52w * 1.30,                           # 8 — 30% above 52w low
        ]
        met = sum(1 for c in criteria if c)
        ma200_slope = _slope(prices[-30:])

        if met >= 6 and criteria[0] and criteria[1]:
            direction = "uptrend"
            if met == 8 and ma200_slope > 0:
                strength = "strong"
            elif met >= 6:
                strength = "moderate"
            else:
                strength = "weak"
        elif not criteria[0] and not criteria[1] and not criteria[5]:
            direction = "downtrend"
            strength = "strong" if met <= 2 else "moderate"
        else:
            direction = "sideways"
            strength = "moderate" if met >= 4 else "weak"

        return {"direction": direction, "strength": strength, "criteria_met": met}


class VolumeAnalyzer:
    def average_volume(self, volumes: list[float], days: int = 20) -> float:
        if not volumes:
            return 0.0
        window = volumes[-days:] if len(volumes) >= days else volumes
        return statistics.mean(window)

    def is_breakout_volume(self, recent_vol: float, avg_vol: float) -> bool:
        return avg_vol > 0 and recent_vol >= avg_vol * 1.5


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

        # Compute rolling volatility in thirds
        third = len(window) // 3
        vol1 = statistics.stdev(window[:third]) if third > 1 else 0
        vol2 = statistics.stdev(window[third:2*third]) if third > 1 else 0
        vol3 = statistics.stdev(window[2*third:]) if third > 1 else 0

        contracting = vol1 > vol2 > vol3 and vol3 < vol1 * 0.6
        recent_price_surge = prices[-1] > max(prices[-20:-5]) * 0.99
        avg_vol = statistics.mean(vols[:-5]) if len(vols) > 5 else 1
        vol_breakout = vols[-1] >= avg_vol * 1.4 if avg_vol > 0 else False

        if contracting and recent_price_surge:
            quality = 7 if vol_breakout else 5
            return {"detected": True, "quality": quality}
        return {"detected": False}

    def _detect_flat_base(self, prices: list[float]) -> dict:
        if len(prices) < 35:
            return {"detected": False}
        window = prices[-35:]
        high = max(window)
        low = min(window)
        pct_range = (high - low) / low if low > 0 else 1.0
        if pct_range <= 0.12:  # within 12% range
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

        # M — market direction proxy (BTC trend via 50MA vs 200MA)
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
