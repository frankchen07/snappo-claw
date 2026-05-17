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
from crypto.src.fetch import CoinGeckoClient, get_fallback_fetcher
from crypto.src.analysis import TrendAnalyzer, SetupDetector, VolumeAnalyzer, CANSLIMEvaluator, RangeAnalyzer
from crypto.src.stage_detector import StageClassifier
from crypto.src.narrative import ExpectationsNarrative
from crypto.src.ingest import DocumentIngester, FrameworkIndex
from crypto.src.models import (
    AnalysisOutput, MarketTrend, SetupInfo,
    EcologicalFramework, PriceStructure, RangeMetrics, PatternInfo, StageInfo,
)
from crypto.src.chart import ChartGenerator
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
    data_notes: list[str] = []

    try:
        history = client.get_market_chart(symbol, days=365)
        details = client.get_coin_details(symbol)
    except Exception as cg_err:
        fallback = get_fallback_fetcher(symbol)
        if fallback is None:
            raise
        _log("analyze_coin", symbol=symbol, status="coingecko_fallback", reason=str(cg_err))
        data_notes.append(f"CoinGecko unavailable — using fallback source ({cg_err.__class__.__name__})")
        history = fallback.get_market_chart(symbol, days=365)
        details = fallback.get_coin_details(symbol)
        if history:
            hist_prices = [row["price"] for row in history]
            details.setdefault("market_data", {}).setdefault("ath", {})["usd"] = max(hist_prices)

    prices = [row["price"] for row in history]
    volumes = [row["volume"] for row in history]

    # OHLC for range analysis / support-resistance
    try:
        ohlc = client.get_ohlc_30d(symbol)
    except Exception as e:
        fallback = get_fallback_fetcher(symbol)
        if fallback:
            try:
                ohlc = fallback.get_ohlc_30d(symbol)
            except Exception as fb_e:
                ohlc = []
                data_notes.append(f"OHLC unavailable ({fb_e.__class__.__name__}) — range metrics skipped")
        else:
            ohlc = []
            data_notes.append(f"OHLC unavailable ({e.__class__.__name__}) — range metrics skipped")

    # BTC prices for RS line baseline
    is_btc = symbol.upper() in ("BTC", "BITCOIN")
    if is_btc:
        btc_prices = prices
    else:
        try:
            btc_history = client.get_market_chart("BTC", days=365)
            btc_prices = [row["price"] for row in btc_history]
        except Exception as e:
            btc_prices = prices  # fallback: RS will be flat
            data_notes.append(f"BTC RS baseline unavailable — RS line flattened")

    ta = TrendAnalyzer()
    sd = SetupDetector()
    va = VolumeAnalyzer()
    ev = CANSLIMEvaluator()
    ra = RangeAnalyzer()
    sc = StageClassifier()
    en = ExpectationsNarrative()

    trend = ta.detect_trend(prices)
    setup = sd.classify(prices, volumes)
    canslim = ev.score(details, prices, volumes)
    mas = ta.moving_averages(prices)
    avg_vol = va.average_volume(volumes)
    current = prices[-1]

    # RS line
    if is_btc:
        rs = {"value": 1.0, "interpretation": "neutral", "trend": "flat", "ratios": [1.0] * min(90, len(prices))}
    else:
        rs = ta.rs_line(prices, btc_prices)

    # Support/resistance
    sr = ta.detect_support_resistance(ohlc, current) if ohlc else {"support": [], "resistance": []}

    # Range metrics
    if ohlc:
        cr = ra.analyze_closing_range(ohlc)
        closing_range_pct = cr["average_closing_range_pct"]
        closing_range_class = cr["classification"]
    else:
        closing_range_pct = None
        closing_range_class = "balanced"

    atr = ra.atr_trend(prices)
    stage_result = sc.classify_stage(prices, volumes, mas)

    # Narrative
    expectations = en.generate(
        stage=stage_result["stage"],
        stage_label=stage_result["label"],
        setup_type=setup["type"],
        rs_interpretation=rs["interpretation"],
        closing_range_class=closing_range_class,
        atr_trend=atr["trend"],
        support_levels=sr["support"],
        resistance_levels=sr["resistance"],
    )

    eco = EcologicalFramework(
        price_structure=PriceStructure(
            ma10=mas.get("ma10"),
            ma50=mas.get("ma50"),
            ma150=mas.get("ma150"),
            ma200=mas.get("ma200"),
            rs_value=rs["value"],
            rs_interpretation=rs["interpretation"],
            rs_trend=rs["trend"],
            support=sr["support"],
            resistance=sr["resistance"],
        ),
        range_metrics=RangeMetrics(
            closing_range_pct=closing_range_pct,
            closing_range_class=closing_range_class,
            atr_trend=atr["trend"],
            recent_atr=atr["recent_atr"],
            prior_atr=atr["prior_atr"],
        ),
        pattern=PatternInfo(primary=setup["type"], quality=setup["quality"]),
        stage=StageInfo(
            stage=stage_result["stage"],
            label=stage_result["label"],
            confidence=stage_result["confidence"],
        ),
        expectations=expectations,
        data_notes=data_notes,
    )

    confidence = int(min(100, canslim))
    entry_zone, stop_level, targets = _compute_entry_stop_targets(prices)
    risk = current - stop_level["price"]
    rr = (targets[0]["price"] - current) / risk if risk > 0 else 0.0

    key_signals = [
        f"Trend: {trend['direction']} ({trend['strength']}, {trend['criteria_met']}/8 criteria)",
        f"Setup: {setup['type']} (quality {setup['quality']}/10)",
        f"Stage: {stage_result['stage']} {stage_result['label']} (confidence {stage_result['confidence']}%)",
        f"RS vs BTC: {rs['value']} ({rs['interpretation']}, {rs['trend']})",
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
        ecological_framework=eco,
    )

    result = to_dict(output)
    elapsed = round((time.time() - t0) * 1000)
    _log("analyze_coin", symbol=symbol, elapsed_ms=elapsed, confidence=confidence,
         stage=stage_result["stage"], rs=rs["value"])
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


def generate_chart(symbol: str) -> str:
    """Generate a 3-panel PNG chart and return the file path."""
    cache = _cache()
    client = _client(cache)
    data_notes: list[str] = []

    history = client.get_market_chart(symbol, days=365)
    prices = [row["price"] for row in history]
    volumes = [row["volume"] for row in history]

    is_btc = symbol.upper() in ("BTC", "BITCOIN")
    if is_btc:
        btc_prices = prices
    else:
        try:
            btc_history = client.get_market_chart("BTC", days=365)
            btc_prices = [row["price"] for row in btc_history]
        except Exception:
            btc_prices = prices

    ta = TrendAnalyzer()
    mas = ta.moving_averages(prices)

    if is_btc:
        rs_ratios: list[float] = []
    else:
        rs = ta.rs_line(prices, btc_prices)
        rs_ratios = rs.get("ratios", [])

    try:
        ohlc = client.get_ohlc_30d(symbol)
    except Exception:
        ohlc = []

    sr = ta.detect_support_resistance(ohlc, prices[-1]) if ohlc else {"support": [], "resistance": []}

    sc = StageClassifier()
    stage_result = sc.classify_stage(prices, volumes, mas)

    cg = ChartGenerator()
    return cg.generate(
        symbol=symbol,
        prices=prices,
        volumes=volumes,
        moving_averages=mas,
        rs_line_values=rs_ratios,
        stage=stage_result["stage"],
        stage_label=stage_result["label"],
        support=sr["support"],
        resistance=sr["resistance"],
    )


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
