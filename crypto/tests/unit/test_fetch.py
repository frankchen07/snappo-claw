"""RED: CoinGecko fetch + rate limiting tests."""

from unittest.mock import MagicMock, patch

import pytest

from tests.fixtures.coingecko_responses import (
    COIN_DETAILS_BTC,
    MARKETS_RESPONSE,
    make_uptrend_price_history,
)


@pytest.fixture
def mock_cache(tmp_path):
    from crypto.src.cache import FileCache
    return FileCache(cache_dir=str(tmp_path))


@pytest.fixture
def client(mock_cache):
    from crypto.src.fetch import CoinGeckoClient
    return CoinGeckoClient(cache=mock_cache)


def test_get_market_chart_returns_price_list(client):
    history = make_uptrend_price_history(365)
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: history,
            raise_for_status=lambda: None,
        )
        result = client.get_market_chart("BTC", days=365)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "timestamp" in result[0]
    assert "price" in result[0]
    assert "volume" in result[0]


def test_get_market_chart_uses_cache_on_second_call(client):
    history = make_uptrend_price_history(365)
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: history,
            raise_for_status=lambda: None,
        )
        client.get_market_chart("BTC", days=365)
        client.get_market_chart("BTC", days=365)
    assert mock_get.call_count == 1  # second call served from cache


def test_get_coins_markets_returns_list(client):
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MARKETS_RESPONSE,
            raise_for_status=lambda: None,
        )
        result = client.get_coins_markets()
    assert isinstance(result, list)
    assert result[0]["symbol"] == "btc"


def test_get_coin_details_returns_dict(client):
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: COIN_DETAILS_BTC,
            raise_for_status=lambda: None,
        )
        result = client.get_coin_details("BTC")
    assert result["id"] == "bitcoin"
    assert result["market_data"]["current_price"]["usd"] == 65000.0


def test_api_failure_returns_stale_with_warning(client, mock_cache):
    from tests.fixtures.coingecko_responses import make_uptrend_price_history
    # Pre-seed cache with stale data
    history = make_uptrend_price_history(10)
    parsed = [
        {"timestamp": p[0], "price": p[1], "volume": v[1]}
        for p, v in zip(history["prices"], history["total_volumes"])
    ]
    mock_cache.set("market_chart:bitcoin:365", parsed, ttl_seconds=1)

    import time
    time.sleep(1.1)  # expire the cache

    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        result = client.get_market_chart("BTC", days=365)

    assert result is not None  # returns stale, doesn't raise


def test_symbol_to_id_mapping(client):
    assert client._symbol_to_id("BTC") == "bitcoin"
    assert client._symbol_to_id("ETH") == "ethereum"
    assert client._symbol_to_id("SOL") == "solana"
    assert client._symbol_to_id("UNKNOWN") == "unknown"  # lowercase fallback
