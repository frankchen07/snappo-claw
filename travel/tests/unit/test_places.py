import pytest
import responses as resp_lib
from travel.src.places import PlacesClient, PlacesError


API_KEY = "test-api-key"
SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


@pytest.fixture
def client():
    return PlacesClient(api_key=API_KEY)


@resp_lib.activate
class TestSearchPlace:
    def test_returns_place_dict(self, client):
        resp_lib.add(
            resp_lib.POST,
            SEARCH_URL,
            json={
                "places": [
                    {
                        "id": "ChIJtest",
                        "displayName": {"text": "Café de Flore"},
                        "formattedAddress": "172 Bd Saint-Germain, 75006 Paris",
                        "location": {"latitude": 48.854, "longitude": 2.333},
                        "types": ["cafe", "point_of_interest"],
                    }
                ]
            },
            status=200,
        )
        place = client.search("Café de Flore Paris")
        assert place["name"] == "Café de Flore"
        assert place["address"] == "172 Bd Saint-Germain, 75006 Paris"
        assert place["lat"] == 48.854
        assert place["lng"] == 2.333
        assert place["place_id"] == "ChIJtest"
        assert "cafe" in place["types"]

    def test_sends_api_key_header(self, client):
        resp_lib.add(
            resp_lib.POST,
            SEARCH_URL,
            json={"places": [
                {
                    "id": "ChIJtest",
                    "displayName": {"text": "X"},
                    "formattedAddress": "Addr",
                    "location": {"latitude": 1.0, "longitude": 2.0},
                    "types": ["restaurant"],
                }
            ]},
            status=200,
        )
        client.search("test query")
        assert resp_lib.calls[0].request.headers["X-Goog-Api-Key"] == API_KEY

    def test_location_bias_sent_in_body(self, client):
        import json
        resp_lib.add(
            resp_lib.POST,
            SEARCH_URL,
            json={"places": [
                {
                    "id": "ChIJtest",
                    "displayName": {"text": "X"},
                    "formattedAddress": "Addr",
                    "location": {"latitude": 1.0, "longitude": 2.0},
                    "types": [],
                }
            ]},
            status=200,
        )
        client.search("test", location_bias="Paris")
        body = json.loads(resp_lib.calls[0].request.body)
        assert "locationBias" in body

    def test_no_results_raises(self, client):
        resp_lib.add(resp_lib.POST, SEARCH_URL, json={"places": []}, status=200)
        with pytest.raises(PlacesError, match="No results"):
            client.search("nonexistent place xyz")

    def test_api_error_raises(self, client):
        resp_lib.add(resp_lib.POST, SEARCH_URL, json={"error": {"message": "Invalid key"}}, status=400)
        with pytest.raises(PlacesError, match="API error"):
            client.search("anything")

    def test_manual_fallback_accepted(self, client):
        place = client.build_manual_place(
            name="Le Comptoir",
            address="9 Carrefour de l'Odéon, 75006 Paris",
        )
        assert place["name"] == "Le Comptoir"
        assert place["place_id"] is None
        assert place["types"] == []


_SEARCH_RESPONSE = {
    "places": [
        {
            "id": "ChIJcache",
            "displayName": {"text": "Café de Flore"},
            "formattedAddress": "172 Bd Saint-Germain, 75006 Paris",
            "location": {"latitude": 48.854, "longitude": 2.333},
            "types": ["cafe"],
        }
    ]
}


class TestPlacesClientCache:
    def test_cache_miss_calls_api(self, tmp_path):
        from travel.src.places import PlacesCache, PlacesStats
        cache = PlacesCache(str(tmp_path / "cache.json"))
        stats = PlacesStats(str(tmp_path / "stats.json"))
        client = PlacesClient(api_key=API_KEY, cache=cache, stats=stats)

        with resp_lib.RequestsMock() as rsps:
            rsps.add(resp_lib.POST, SEARCH_URL, json=_SEARCH_RESPONSE, status=200)
            place = client.search("Café de Flore", location_bias="Paris")

        assert place["name"] == "Café de Flore"
        assert stats.read()["calls"] == 1
        assert stats.read()["cache_hits"] == 0

    def test_cache_miss_stores_result(self, tmp_path):
        from travel.src.places import PlacesCache, PlacesStats
        cache = PlacesCache(str(tmp_path / "cache.json"))
        stats = PlacesStats(str(tmp_path / "stats.json"))
        client = PlacesClient(api_key=API_KEY, cache=cache, stats=stats)

        with resp_lib.RequestsMock() as rsps:
            rsps.add(resp_lib.POST, SEARCH_URL, json=_SEARCH_RESPONSE, status=200)
            client.search("Café de Flore", location_bias="Paris")

        # key is built from original args, not the expanded textQuery
        key = "café de flore|paris"
        assert cache.get(key) is not None

    def test_cache_hit_skips_api(self, tmp_path):
        from travel.src.places import PlacesCache, PlacesStats
        cache = PlacesCache(str(tmp_path / "cache.json"))
        stats = PlacesStats(str(tmp_path / "stats.json"))
        # Pre-populate cache with the key derived from original args
        key = "café de flore|paris"
        cached_place = {
            "name": "Café de Flore", "address": "172 Bd Saint-Germain",
            "lat": 48.854, "lng": 2.333, "place_id": "ChIJcache", "types": ["cafe"],
        }
        cache.set(key, cached_place)

        client = PlacesClient(api_key=API_KEY, cache=cache, stats=stats)
        # No HTTP mock — if API is called, it will raise ConnectionError
        place = client.search("Café de Flore", location_bias="Paris")

        assert place["name"] == "Café de Flore"
        assert stats.read()["cache_hits"] == 1
        assert stats.read()["calls"] == 0

    def test_no_cache_still_works(self):
        client = PlacesClient(api_key=API_KEY)  # no cache/stats args
        with resp_lib.RequestsMock() as rsps:
            rsps.add(resp_lib.POST, SEARCH_URL, json=_SEARCH_RESPONSE, status=200)
            place = client.search("Café de Flore")
        assert place["name"] == "Café de Flore"
