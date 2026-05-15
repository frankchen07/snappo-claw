"""
Travel Maps CLI — agent-facing entry point.

Import from workspace root:
    from travel.cli import create_map, add_place, list_maps, get_map, remove_place

All functions return plain dicts. Drive sync is attempted automatically;
if credentials are missing a warning key is included but state is still saved.
"""
import os
import sys

# Allow running from workspace root or travel/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../..", ".env"))

from travel.src.state import MapState
from travel.src.places import PlacesClient, PlacesCache, PlacesStats, PlacesError
from travel.src.kml import generate_kml
from travel.src.categorizer import categorize_from_types, get_color, needs_followup, FollowupQuestion

_MAPS_DIR = os.path.join(os.path.dirname(__file__), "maps")
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

_state = MapState(maps_dir=_MAPS_DIR)
_cache = PlacesCache(os.path.join(_CACHE_DIR, "places_cache.json"))
_stats = PlacesStats(os.path.join(_CACHE_DIR, "api_stats.json"))


def _make_places_client() -> PlacesClient:
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return PlacesClient(api_key=api_key, cache=_cache, stats=_stats)


def _get_drive_client():
    creds = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON")
    if not creds:
        return None
    try:
        from travel.src.drive import DriveClient
        return DriveClient(credentials_path=creds)
    except Exception:
        return None


def _sync_to_drive(map_data: dict) -> dict:
    drive = _get_drive_client()
    if drive is None:
        return {"warning": "Drive not configured — map saved locally only"}

    kml = generate_kml(map_data)
    filename = f"{map_data['id']}.kml"

    try:
        if map_data.get("drive_file_id"):
            drive.update_kml(map_data["drive_file_id"], kml)
        else:
            file_id = drive.upload_kml(filename, kml)
            map_data = _state.set_drive_file_id(map_data["id"], file_id)
    except Exception as e:
        return {"warning": f"Drive sync failed: {e}"}

    return {}


def create_map(map_id: str, name: str) -> dict:
    """Create a new travel map with default Eat/Drink/Do layers.

    Args:
        map_id: URL-safe identifier, e.g. "paris-trip"
        name:   Human-readable name, e.g. "Paris Trip"

    Returns dict with keys: id, name, map_url (or warning if Drive not set up)
    """
    m = _state.create_map(map_id, name)
    extras = _sync_to_drive(m)
    m = _state.get_map(map_id)
    return {**m, **extras}


def add_place(
    map_id: str,
    query: str,
    category: str,
    subcategory: str | None = None,
    description: str | None = None,
    location_bias: str | None = None,
    manual_address: str | None = None,
    place_data: dict | None = None,
) -> dict:
    """Look up a place and add it to a map layer.

    The agent must resolve category/subcategory before calling this function
    (ask follow-up questions using categorize_place_query first if needed).

    Args:
        map_id:         Target map ID
        query:          Place name/query for Places API search
        category:       "Eat", "Drink", or "Do"
        subcategory:    "dessert" | "coffee" | "cocktails" | None
        description:    Optional note about the place
        location_bias:  City or region hint for Places API, e.g. "Paris"
        manual_address: If provided, skip Places API and use this address directly
        place_data:     Pre-fetched place dict from categorize_place_query; avoids
                        a second API call when the agent already resolved the place.

    Returns dict with the added place data + updated map_url
    """
    if place_data:
        raw = place_data
    elif manual_address:
        places_client = _make_places_client()
        raw = places_client.build_manual_place(name=query, address=manual_address)
    else:
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
        if not api_key:
            return {"error": "GOOGLE_MAPS_API_KEY not set"}
        places_client = _make_places_client()
        try:
            raw = places_client.search(query, location_bias=location_bias)
        except PlacesError as e:
            return {"error": str(e)}

    color = get_color(category, subcategory)
    place = {
        **raw,
        "category": category,
        "subcategory": subcategory,
        "description": description or "",
        "color": color,
    }

    m = _state.add_place(map_id, place)
    extras = _sync_to_drive(m)
    m = _state.get_map(map_id)
    return {"place": place, "map": m, **extras}


def categorize_place_query(query: str, location_bias: str | None = None) -> dict:
    """Look up a place and return its auto-detected category + any required follow-up.

    Use this before add_place when you're not sure what category a place falls into.
    The agent should ask the user the follow-up question if one is returned.
    Pass result["place"] as place_data to add_place to avoid a second API call.

    Returns:
        {
          "place": {...},           # raw place data from Places API
          "category": str | None,
          "subcategory": str | None,
          "followup": "eat_drink_do" | "is_dessert" | "coffee_or_cocktails" | None,
          "followup_question": str | None,   # human-readable question to ask
        }
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}

    client = _make_places_client()
    try:
        raw = client.search(query, location_bias=location_bias)
    except PlacesError as e:
        return {"error": str(e)}

    cat = categorize_from_types(raw.get("types", []))
    followup = needs_followup(cat)

    _QUESTIONS = {
        FollowupQuestion.EAT_DRINK_DO: "Is this for Eat, Drink, or Do?",
        FollowupQuestion.IS_DESSERT: "Is this a dessert spot?",
        FollowupQuestion.COFFEE_OR_COCKTAILS: "Coffee/tea or cocktails/beer?",
    }

    return {
        "place": raw,
        "category": cat["category"],
        "subcategory": cat["subcategory"],
        "followup": followup.value if followup else None,
        "followup_question": _QUESTIONS.get(followup) if followup else None,
    }


def list_maps() -> list[dict]:
    """List all travel maps with their place counts and URLs."""
    maps = _state.list_maps()
    return [
        {
            "id": m["id"],
            "name": m["name"],
            "place_count": len(m.get("places", [])),
            "map_url": m.get("map_url"),
            "created_at": m.get("created_at"),
        }
        for m in maps
    ]


def get_map(map_id: str) -> dict:
    """Get full map data including all places."""
    return _state.get_map(map_id)


def remove_place(map_id: str, place_name: str) -> dict:
    """Remove a place from a map by exact name, then sync KML to Drive."""
    try:
        m = _state.remove_place(map_id, place_name)
    except (KeyError, ValueError) as e:
        return {"error": str(e)}
    extras = _sync_to_drive(m)
    m = _state.get_map(map_id)
    return {"map": m, **extras}


def get_api_stats() -> dict:
    """Return Places API call counts and estimated cost.

    Returns:
        {
          "api_calls": int,            # actual HTTP calls made
          "cache_hits": int,           # calls served from cache
          "estimated_cost_usd": float, # api_calls × $0.017
        }
    """
    data = _stats.read()
    calls = data.get("calls", 0)
    hits = data.get("cache_hits", 0)
    return {
        "api_calls": calls,
        "cache_hits": hits,
        "estimated_cost_usd": round(calls * 0.017, 4),
    }
