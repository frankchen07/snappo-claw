"""RED: File cache TTL tests."""

import json
import os
import time

import pytest
from freezegun import freeze_time


@pytest.fixture
def cache(tmp_path):
    from crypto.src.cache import FileCache
    return FileCache(cache_dir=str(tmp_path))


def test_get_missing_key_returns_none(cache):
    result = cache.get("nonexistent")
    assert result is None


def test_set_and_get_fresh(cache):
    cache.set("btc_price", {"price": 65000}, ttl_seconds=3600)
    result = cache.get("btc_price")
    assert result is not None
    data, is_fresh = result
    assert data["price"] == 65000
    assert is_fresh is True


def test_get_expired_returns_stale(cache, tmp_path):
    with freeze_time("2026-05-10 12:00:00"):
        cache.set("old_data", {"price": 50000}, ttl_seconds=60)
    with freeze_time("2026-05-10 12:02:00"):  # 2 min later, TTL=60s
        result = cache.get("old_data")
    assert result is not None
    data, is_fresh = result
    assert data["price"] == 50000
    assert is_fresh is False


def test_set_writes_json_to_disk(cache, tmp_path):
    cache.set("test_key", {"foo": "bar"}, ttl_seconds=300)
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    content = json.loads(files[0].read_text())
    assert content["data"]["foo"] == "bar"
    assert "cached_at" in content


def test_invalidate_removes_entry(cache):
    cache.set("to_delete", {"x": 1}, ttl_seconds=3600)
    assert cache.get("to_delete") is not None
    cache.invalidate("to_delete")
    assert cache.get("to_delete") is None


def test_manifest_lists_all_keys(cache):
    cache.set("key1", {"a": 1}, ttl_seconds=3600)
    cache.set("key2", {"b": 2}, ttl_seconds=60)
    manifest = cache.manifest()
    assert "key1" in manifest
    assert "key2" in manifest


def test_key_sanitized_for_filesystem(cache):
    cache.set("coins/bitcoin/market_chart", {"p": 1}, ttl_seconds=100)
    result = cache.get("coins/bitcoin/market_chart")
    assert result is not None
    data, _ = result
    assert data["p"] == 1
