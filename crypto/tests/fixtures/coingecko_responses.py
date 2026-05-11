"""Mock CoinGecko API responses for testing."""

import time


def make_price_history(days: int = 365, base_price: float = 50000.0) -> dict:
    """Generate a realistic-looking price history for testing."""
    now = int(time.time() * 1000)
    ms_per_day = 86400 * 1000
    prices = []
    volumes = []
    price = base_price
    for i in range(days, 0, -1):
        ts = now - i * ms_per_day
        # Mild uptrend with noise
        price = price * (1 + 0.001 + (i % 7 - 3) * 0.002)
        prices.append([ts, price])
        volumes.append([ts, price * 1000 + (i % 10) * 10000])
    return {"prices": prices, "total_volumes": volumes}


def make_uptrend_price_history(days: int = 365) -> dict:
    """Strong uptrend that satisfies Minervini trend template."""
    now = int(time.time() * 1000)
    ms_per_day = 86400 * 1000
    prices = []
    volumes = []
    # Start low, trend strongly upward
    price = 20000.0
    for i in range(days, 0, -1):
        ts = now - i * ms_per_day
        price = price * 1.003  # ~3x over 365 days
        prices.append([ts, price])
        volumes.append([ts, price * 500])
    return {"prices": prices, "total_volumes": volumes}


def make_downtrend_price_history(days: int = 365) -> dict:
    """Persistent downtrend."""
    now = int(time.time() * 1000)
    ms_per_day = 86400 * 1000
    prices = []
    volumes = []
    price = 60000.0
    for i in range(days, 0, -1):
        ts = now - i * ms_per_day
        price = price * 0.998  # declining
        prices.append([ts, price])
        volumes.append([ts, price * 500])
    return {"prices": prices, "total_volumes": volumes}


COIN_DETAILS_BTC = {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "market_cap_rank": 1,
    "market_data": {
        "current_price": {"usd": 65000.0},
        "ath": {"usd": 73000.0},
        "atl": {"usd": 3200.0},
        "high_52_weeks": {"usd": 73000.0},
        "low_52_weeks": {"usd": 38000.0},
        "total_volume": {"usd": 35_000_000_000},
        "market_cap": {"usd": 1_280_000_000_000},
    },
}

COIN_DETAILS_ETH = {
    "id": "ethereum",
    "symbol": "eth",
    "name": "Ethereum",
    "market_cap_rank": 2,
    "market_data": {
        "current_price": {"usd": 3500.0},
        "ath": {"usd": 4878.0},
        "atl": {"usd": 0.43},
        "high_52_weeks": {"usd": 4000.0},
        "low_52_weeks": {"usd": 1800.0},
        "total_volume": {"usd": 18_000_000_000},
        "market_cap": {"usd": 421_000_000_000},
    },
}

MARKETS_RESPONSE = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 65000.0,
        "market_cap": 1_280_000_000_000,
        "market_cap_rank": 1,
        "total_volume": 35_000_000_000,
        "price_change_percentage_24h": 2.5,
        "price_change_percentage_7d_in_currency": 8.0,
    },
    {
        "id": "ethereum",
        "symbol": "eth",
        "name": "Ethereum",
        "current_price": 3500.0,
        "market_cap": 421_000_000_000,
        "market_cap_rank": 2,
        "total_volume": 18_000_000_000,
        "price_change_percentage_24h": 1.8,
        "price_change_percentage_7d_in_currency": 5.0,
    },
]
