"""
Unit tests for cost-management features in cli.py:
- add_place(place_data=...) skips API call
- get_api_stats() returns correct shape
- cache is shared between categorize_place_query and add_place
"""
import os
import pytest
import responses as resp_lib
from unittest.mock import patch, MagicMock

import travel.cli as cli_module

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

_CAFE_PLACE = {
    "name": "Café de Flore",
    "address": "172 Bd Saint-Germain, 75006 Paris",
    "lat": 48.854,
    "lng": 2.333,
    "place_id": "ChIJtest",
    "types": ["cafe", "point_of_interest"],
}

_SEARCH_RESPONSE = {
    "places": [{
        "id": "ChIJtest",
        "displayName": {"text": "Café de Flore"},
        "formattedAddress": "172 Bd Saint-Germain, 75006 Paris",
        "location": {"latitude": 48.854, "longitude": 2.333},
        "types": ["cafe", "point_of_interest"],
    }]
}


@pytest.fixture(autouse=True)
def isolate_state(tmp_path, monkeypatch):
    """Reset module-level singletons to use tmp_path for each test."""
    from travel.src.state import MapState
    from travel.src.places import PlacesCache, PlacesStats

    maps_dir = str(tmp_path / "maps")
    cache_dir = str(tmp_path / "cache")
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    monkeypatch.setattr(cli_module, "_state", MapState(maps_dir=maps_dir))
    monkeypatch.setattr(cli_module, "_MAPS_DIR", maps_dir)
    monkeypatch.setattr(cli_module, "_CACHE_DIR", cache_dir)
    monkeypatch.setattr(
        cli_module, "_cache",
        PlacesCache(os.path.join(cache_dir, "places_cache.json"))
    )
    monkeypatch.setattr(
        cli_module, "_stats",
        PlacesStats(os.path.join(cache_dir, "api_stats.json"))
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_DRIVE_CREDENTIALS_JSON", "")

    cli_module._state.create_map("paris-trip", "Paris Trip")


class TestAddPlaceWithPlaceData:
    def test_place_data_skips_api(self):
        """Passing place_data should not make any HTTP calls."""
        with resp_lib.RequestsMock() as rsps:
            # No URLs registered — any HTTP call would raise ConnectionError
            result = cli_module.add_place(
                map_id="paris-trip",
                query="Café de Flore",
                category="Drink",
                subcategory="coffee",
                place_data=_CAFE_PLACE,
            )
        assert "error" not in result
        assert result["place"]["name"] == "Café de Flore"

    def test_place_data_overrides_query_lookup(self):
        """place_data takes precedence; API is never called even if key is set."""
        call_count = {"n": 0}

        original_search = cli_module.PlacesClient.search

        def mock_search(self, *args, **kwargs):
            call_count["n"] += 1
            return original_search(self, *args, **kwargs)

        with patch.object(cli_module.PlacesClient, "search", mock_search):
            cli_module.add_place(
                map_id="paris-trip",
                query="Café de Flore",
                category="Drink",
                subcategory="coffee",
                place_data=_CAFE_PLACE,
            )

        assert call_count["n"] == 0

    def test_no_place_data_still_calls_api(self):
        """Without place_data, add_place must call PlacesClient.search."""
        call_count = {"n": 0}
        original_search = cli_module.PlacesClient.search

        def mock_search(self, *args, **kwargs):
            call_count["n"] += 1
            return _CAFE_PLACE  # short-circuit actual HTTP

        with patch.object(cli_module.PlacesClient, "search", mock_search):
            result = cli_module.add_place(
                map_id="paris-trip",
                query="Café de Flore",
                category="Drink",
                subcategory="coffee",
                location_bias="Paris",
            )
        assert "error" not in result
        assert call_count["n"] == 1


class TestGetApiStats:
    def test_returns_expected_shape(self):
        stats = cli_module.get_api_stats()
        assert "api_calls" in stats
        assert "cache_hits" in stats
        assert "estimated_cost_usd" in stats

    def test_initial_stats_zero(self):
        stats = cli_module.get_api_stats()
        assert stats["api_calls"] == 0
        assert stats["cache_hits"] == 0
        assert stats["estimated_cost_usd"] == 0.0

    def test_cost_calculated_from_calls(self):
        cli_module._stats.record_call()
        cli_module._stats.record_call()
        stats = cli_module.get_api_stats()
        assert stats["api_calls"] == 2
        assert stats["estimated_cost_usd"] == pytest.approx(0.034, rel=1e-3)


class TestCategorizeAndAddSharedCache:
    def test_categorize_populates_cache(self):
        with resp_lib.RequestsMock() as rsps:
            rsps.add(resp_lib.POST, SEARCH_URL, json=_SEARCH_RESPONSE, status=200)
            result = cli_module.categorize_place_query("Café de Flore", location_bias="Paris")

        assert result["place"]["name"] == "Café de Flore"
        # Cache should now have the result (key from original args, not expanded query)
        key = "café de flore|paris"
        cached = cli_module._cache.get(key)
        assert cached is not None

    def test_add_with_place_data_makes_zero_api_calls(self):
        """Full flow: categorize (1 call) + add with place_data (0 calls) = 1 total."""
        with resp_lib.RequestsMock() as rsps:
            rsps.add(resp_lib.POST, SEARCH_URL, json=_SEARCH_RESPONSE, status=200)
            cat_result = cli_module.categorize_place_query(
                "Café de Flore", location_bias="Paris"
            )
            total_after_categorize = len(rsps.calls)

            # add_place with place_data — no new HTTP calls
            cli_module.add_place(
                map_id="paris-trip",
                query="Café de Flore",
                category=cat_result["category"],
                subcategory=cat_result["subcategory"],
                place_data=cat_result["place"],
            )
            total_after_add = len(rsps.calls)

        assert total_after_categorize == 1
        assert total_after_add == 1  # no additional call
