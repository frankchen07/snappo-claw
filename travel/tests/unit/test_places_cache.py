import json
import time
import pytest
from travel.src.places import PlacesCache, PlacesStats

_SAMPLE_PLACE = {
    "name": "Café de Flore",
    "address": "172 Bd Saint-Germain, Paris",
    "lat": 48.854,
    "lng": 2.333,
    "place_id": "ChIJtest",
    "types": ["cafe"],
}


class TestPlacesCache:
    def test_miss_returns_none(self, tmp_path):
        cache = PlacesCache(str(tmp_path / "cache.json"))
        assert cache.get("nonexistent|paris") is None

    def test_set_then_get_returns_place(self, tmp_path):
        cache = PlacesCache(str(tmp_path / "cache.json"))
        cache.set("café de flore|paris", _SAMPLE_PLACE)
        result = cache.get("café de flore|paris")
        assert result == _SAMPLE_PLACE

    def test_expired_entry_returns_none(self, tmp_path, monkeypatch):
        cache = PlacesCache(str(tmp_path / "cache.json"))
        # Write entry with old timestamp
        old_ts = time.time() - (31 * 24 * 3600)  # 31 days ago
        data = {"café de flore|paris": {"place": _SAMPLE_PLACE, "ts": old_ts}}
        (tmp_path / "cache.json").write_text(json.dumps(data))
        assert cache.get("café de flore|paris") is None

    def test_fresh_entry_not_expired(self, tmp_path):
        cache = PlacesCache(str(tmp_path / "cache.json"))
        cache.set("eiffel tower|paris", _SAMPLE_PLACE)
        # Should still be valid (just set, well within 30 days)
        assert cache.get("eiffel tower|paris") is not None

    def test_creates_parent_dir(self, tmp_path):
        cache = PlacesCache(str(tmp_path / "nested" / "dir" / "cache.json"))
        cache.set("key|", _SAMPLE_PLACE)
        assert (tmp_path / "nested" / "dir" / "cache.json").exists()

    def test_corrupt_file_returns_none(self, tmp_path):
        p = tmp_path / "cache.json"
        p.write_text("not valid json{{{")
        cache = PlacesCache(str(p))
        assert cache.get("any|key") is None


class TestPlacesStats:
    def test_initial_state(self, tmp_path):
        stats = PlacesStats(str(tmp_path / "stats.json"))
        d = stats.read()
        assert d["calls"] == 0
        assert d["cache_hits"] == 0

    def test_record_call_increments(self, tmp_path):
        stats = PlacesStats(str(tmp_path / "stats.json"))
        stats.record_call()
        stats.record_call()
        assert stats.read()["calls"] == 2

    def test_record_cache_hit_increments(self, tmp_path):
        stats = PlacesStats(str(tmp_path / "stats.json"))
        stats.record_cache_hit()
        assert stats.read()["cache_hits"] == 1

    def test_calls_and_hits_independent(self, tmp_path):
        stats = PlacesStats(str(tmp_path / "stats.json"))
        stats.record_call()
        stats.record_call()
        stats.record_cache_hit()
        d = stats.read()
        assert d["calls"] == 2
        assert d["cache_hits"] == 1

    def test_creates_parent_dir(self, tmp_path):
        stats = PlacesStats(str(tmp_path / "sub" / "stats.json"))
        stats.record_call()
        assert (tmp_path / "sub" / "stats.json").exists()
