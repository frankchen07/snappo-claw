"""CoinGecko API client with rate limiting and cache fallback."""

import logging
import time
from typing import Any

import requests

from crypto.src.cache import FileCache

logger = logging.getLogger(__name__)

SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "ATOM": "cosmos",
    "FIL": "filecoin",
    "NEAR": "near",
    "SUI": "sui",
    "ARB": "arbitrum",
    "OP": "optimism",
    "STX": "blockstack",
    "ALEO": "aleo",
}

BASE_URL = "https://api.coingecko.com/api/v3"

# TTLs in seconds
TTL_MARKET_CHART = 6 * 3600   # 6 hours
TTL_MARKETS = 3600             # 1 hour
TTL_COIN_DETAILS = 24 * 3600  # 24 hours


class TokenBucket:
    def __init__(self, capacity: float, refill_per_minute: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_per_minute / 60.0
        self.last_refill = time.time()

    def acquire(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def wait_and_acquire(self, timeout: float = 10.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if self.acquire():
                return True
            time.sleep(0.5)
        return False


class CoinGeckoClient:
    def __init__(self, cache: FileCache, api_key: str | None = None):
        self.cache = cache
        self.api_key = api_key
        self.rate_limiter = TokenBucket(capacity=20, refill_per_minute=15)

    def _symbol_to_id(self, symbol: str) -> str:
        return SYMBOL_MAP.get(symbol.upper(), symbol.lower())

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["x-cg-demo-api-key"] = self.api_key
        return h

    def _get(self, url: str, params: dict | None = None) -> Any:
        self.rate_limiter.wait_and_acquire()
        resp = requests.get(url, params=params, headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_market_chart(self, symbol: str, days: int = 365) -> list[dict]:
        coin_id = self._symbol_to_id(symbol)
        cache_key = f"market_chart:{coin_id}:{days}"
        cached = self.cache.get(cache_key)
        if cached:
            data, is_fresh = cached
            if is_fresh:
                return data

        try:
            url = f"{BASE_URL}/coins/{coin_id}/market_chart"
            raw = self._get(url, params={"vs_currency": "usd", "days": days})
            prices = raw.get("prices", [])
            volumes = raw.get("total_volumes", [])
            result = [
                {"timestamp": p[0], "price": p[1], "volume": volumes[i][1] if i < len(volumes) else 0.0}
                for i, p in enumerate(prices)
            ]
            self.cache.set(cache_key, result, ttl_seconds=TTL_MARKET_CHART)
            return result
        except Exception as e:
            if cached:
                logger.warning(f"API error for {symbol}, returning stale cache: {e}")
                data, _ = cached
                return data
            logger.error(f"API error for {symbol} and no cache: {e}")
            raise

    def get_coins_markets(self, limit: int = 250) -> list[dict]:
        cache_key = "coins_markets"
        cached = self.cache.get(cache_key)
        if cached:
            data, is_fresh = cached
            if is_fresh:
                return data

        try:
            url = f"{BASE_URL}/coins/markets"
            result = self._get(url, params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "price_change_percentage": "7d",
            })
            self.cache.set(cache_key, result, ttl_seconds=TTL_MARKETS)
            return result
        except Exception as e:
            if cached:
                data, _ = cached
                return data
            raise

    def get_coin_details(self, symbol: str) -> dict:
        coin_id = self._symbol_to_id(symbol)
        cache_key = f"coin_details:{coin_id}"
        cached = self.cache.get(cache_key)
        if cached:
            data, is_fresh = cached
            if is_fresh:
                return data

        try:
            url = f"{BASE_URL}/coins/{coin_id}"
            result = self._get(url, params={"localization": "false", "tickers": "false"})
            self.cache.set(cache_key, result, ttl_seconds=TTL_COIN_DETAILS)
            return result
        except Exception as e:
            if cached:
                data, _ = cached
                return data
            raise
