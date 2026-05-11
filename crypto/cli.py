"""Agent-facing entry point for crypto trading analysis."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from crypto.src.cache import FileCache
from crypto.src.fetch import CoinGeckoClient
from crypto.src.analysis import TrendAnalyzer, SetupDetector, VolumeAnalyzer, CANSLIMEvaluator
from crypto.src.ingest import DocumentIngester, FrameworkIndex
from crypto.src.models import AnalysisOutput, MarketTrend, SetupInfo
from crypto.src.format import to_dict

_WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # workspace/
_OPENCLAW_ROOT = os.path.dirname(_WORKSPACE_ROOT)                               # .openclaw/

_CACHE_DIR = os.environ.get("CRYPTO_CACHE_DIR", os.path.join(_OPENCLAW_ROOT, "cache", "crypto"))
_KNOWLEDGE_DIR = os.environ.get("CRYPTO_KNOWLEDGE_DIR", os.path.join(_WORKSPACE_ROOT, "crypto", "knowledge"))
_LOG_PATH = os.path.join(_WORKSPACE_ROOT, "crypto", "logs", "crypto.log")

os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)

_log_handler = logging.FileHandler(_LOG_PATH)
_log_handler.setFormatter(logging.Formatter('%(message)s'))
_logger = logging.getLogger("crypto")
_logger.setLevel(logging.INFO)
_logger.addHandler(_log_handler)


def _log(fn: str, symbol: str | None = None, **kwargs) -> None:
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "function": fn}
    if symbol:
        entry["symbol"] = symbol
    entry.update(kwargs)
    _logger.info(json.dumps(entry))


def _cache() -> FileCache:
    return FileCache(cache_dir=_CACHE_DIR)


def _client(cache: FileCache) -> CoinGeckoClient:
    api_key = os.environ.get("COINGECKO_API_KEY") or None
    return CoinGeckoClient(cache=cache, api_key=api_key)


def _compute_entry_stop_targets(prices: list[float]) -> tuple[dict, dict, list[dict]]:
    current = prices[-1]
    ma50_data = prices[-50:] if len(prices) >= 50 else prices
    ma50 = sum(ma50_data) / len(ma50_data)
    stop_price = round(ma50 * 0.97, 2)
    risk = current - stop_price
    entry_zone = {
        "price": round(current, 2),
        "range": [round(current * 0.97, 2), round(current * 1.01, 2)],
    }
    stop_level = {
        "price": stop_price,
        "invalidation_reason": "Close below 50MA",
    }
    targets = [
        {"price": round(current + risk * 2, 2), "rr_ratio": 2.0},
        {"price": round(current + risk * 3, 2), "rr_ratio": 3.0},
    ]
    return entry_zone, stop_level, targets


def analyze_coin(symbol: str, confidence_threshold: int = 0) -> dict:
    """Analyze a single coin using Minervini + CANSLIM methodology."""
    t0 = time.time()
    cache = _cache()
    client = _client(cache)

    history = client.get_market_chart(symbol, days=365)
    details = client.get_coin_details(symbol)

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
    current = prices[-1]

    confidence = int(min(100, canslim))
    entry_zone, stop_level, targets = _compute_entry_stop_targets(prices)
    risk = current - stop_level["price"]
    rr = (targets[0]["price"] - current) / risk if risk > 0 else 0.0

    key_signals = [
        f"Trend: {trend['direction']} ({trend['strength']}, {trend['criteria_met']}/8 criteria)",
        f"Setup: {setup['type']} (quality {setup['quality']}/10)",
        f"Volume: {volumes[-1]:,.0f} vs avg {avg_vol:,.0f}",
        f"CANSLIM score: {canslim:.0f}/100",
    ]

    output = AnalysisOutput(
        symbol=symbol.upper(),
        timestamp=datetime.now(timezone.utc).isoformat(),
        market_trend=MarketTrend(direction=trend["direction"], strength=trend["strength"]),
        setup=SetupInfo(type=setup["type"], quality=setup["quality"]),
        entry_zone=entry_zone,
        stop_level=stop_level,
        targets=targets,
        confidence_score=confidence,
        key_signals=key_signals,
        risk_reward=round(rr, 2),
        disclaimer="Not financial advice.",
    )

    result = to_dict(output)
    elapsed = round((time.time() - t0) * 1000)
    _log("analyze_coin", symbol=symbol, elapsed_ms=elapsed, confidence=confidence)
    return result


def scan_watchlist(symbols: list[str]) -> list[dict]:
    """Analyze multiple coins."""
    results = []
    for sym in symbols:
        try:
            results.append(analyze_coin(sym))
        except Exception as e:
            _log("scan_watchlist", symbol=sym, status="error", error=str(e))
            results.append({"symbol": sym, "error": str(e)})
    return results


def search_knowledge(query: str, limit: int = 5) -> list[dict]:
    """Search ingested trading frameworks."""
    index = FrameworkIndex(knowledge_dir=_KNOWLEDGE_DIR)
    results = index.search(query, limit=limit)
    _log("search_knowledge", query=query, results=len(results))
    return results


def ingest_new_documents() -> dict:
    """Scan knowledge/raw/ and ingest new documents."""
    ingester = DocumentIngester(knowledge_dir=_KNOWLEDGE_DIR)
    result = ingester.ingest_all()
    _log("ingest_new_documents", **result)
    return result


def health_check() -> dict:
    """Check system status."""
    cache = _cache()
    manifest = cache.manifest()
    stale = sum(1 for v in manifest.values() if not v["is_fresh"])
    fresh = len(manifest) - stale
    return {
        "cache_status": {"total_entries": len(manifest), "fresh": fresh, "stale": stale},
        "knowledge_dir": _KNOWLEDGE_DIR,
        "cache_dir": _CACHE_DIR,
    }
