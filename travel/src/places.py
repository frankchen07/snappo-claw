import json
import time
import requests
from pathlib import Path

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
])

_CACHE_TTL = 30 * 24 * 3600  # 30 days


class PlacesError(Exception):
    pass


class PlacesCache:
    def __init__(self, cache_path: str):
        self._path = Path(cache_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return {}

    def get(self, key: str) -> dict | None:
        data = self._load()
        entry = data.get(key)
        if entry and time.time() - entry["ts"] < _CACHE_TTL:
            return entry["place"]
        return None

    def set(self, key: str, place: dict) -> None:
        data = self._load()
        data[key] = {"place": place, "ts": time.time()}
        self._path.write_text(json.dumps(data, indent=2))


class PlacesStats:
    def __init__(self, stats_path: str):
        self._path = Path(stats_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self._path.exists():
            return {"calls": 0, "cache_hits": 0}
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return {"calls": 0, "cache_hits": 0}

    def record_call(self) -> None:
        d = self._load()
        d["calls"] = d.get("calls", 0) + 1
        self._path.write_text(json.dumps(d, indent=2))

    def record_cache_hit(self) -> None:
        d = self._load()
        d["cache_hits"] = d.get("cache_hits", 0) + 1
        self._path.write_text(json.dumps(d, indent=2))

    def read(self) -> dict:
        return self._load()


class PlacesClient:
    def __init__(
        self,
        api_key: str,
        cache: PlacesCache | None = None,
        stats: PlacesStats | None = None,
    ):
        self._api_key = api_key
        self._cache = cache
        self._stats = stats

    def _cache_key(self, query: str, location_bias: str | None) -> str:
        return f"{query.lower().strip()}|{(location_bias or '').lower().strip()}"

    def search(self, query: str, location_bias: str | None = None) -> dict:
        if self._cache is not None:
            key = self._cache_key(query, location_bias)
            cached = self._cache.get(key)
            if cached is not None:
                if self._stats is not None:
                    self._stats.record_cache_hit()
                return cached

        result = self._fetch(query, location_bias)

        if self._cache is not None:
            self._cache.set(self._cache_key(query, location_bias), result)
        if self._stats is not None:
            self._stats.record_call()

        return result

    def _fetch(self, query: str, location_bias: str | None) -> dict:
        body: dict = {"textQuery": query}

        if location_bias and location_bias.lower() not in query.lower():
            body["textQuery"] = f"{query} {location_bias}"

        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(SEARCH_URL, json=body, headers=headers, timeout=10)
        except requests.RequestException as e:
            raise PlacesError(f"Request failed: {e}") from e

        if not response.ok:
            data = response.json()
            msg = data.get("error", {}).get("message", response.text)
            raise PlacesError(f"API error {response.status_code}: {msg}")

        data = response.json()
        places = data.get("places", [])
        if not places:
            raise PlacesError(f"No results found for '{query}'")

        p = places[0]
        return {
            "name": p["displayName"]["text"],
            "address": p.get("formattedAddress", ""),
            "lat": p["location"]["latitude"],
            "lng": p["location"]["longitude"],
            "place_id": p.get("id"),
            "types": p.get("types", []),
        }

    def build_manual_place(self, name: str, address: str) -> dict:
        return {
            "name": name,
            "address": address,
            "lat": None,
            "lng": None,
            "place_id": None,
            "types": [],
        }
