"""
Integration test: full create_map → add_place → KML sync flow.
All external calls (Places API, Drive API) are mocked.
"""
import json
import pytest
import responses as resp_lib
from unittest.mock import MagicMock, patch

from travel.src.state import MapState
from travel.src.places import PlacesClient
from travel.src.kml import generate_kml
from travel.src.categorizer import categorize_from_types, get_color, needs_followup, FollowupQuestion

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


@pytest.fixture
def state(tmp_path):
    return MapState(maps_dir=str(tmp_path))


@pytest.fixture
def places_client():
    return PlacesClient(api_key="test-key")


def _mock_place_response(name, address, lat, lng, types):
    return {
        "places": [{
            "id": f"ChIJ_{name.replace(' ', '_')}",
            "displayName": {"text": name},
            "formattedAddress": address,
            "location": {"latitude": lat, "longitude": lng},
            "types": types,
        }]
    }


@resp_lib.activate
class TestCreateMapAndAddPlaces:
    def test_create_map_then_add_unambiguous_place(self, state, places_client):
        m = state.create_map("paris-trip", "Paris Trip")
        assert m["id"] == "paris-trip"
        assert m["places"] == []

        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Eiffel Tower", "Champ de Mars, Paris", 48.858, 2.294,
            ["tourist_attraction", "point_of_interest"],
        ))

        raw = places_client.search("Eiffel Tower Paris")
        cat = categorize_from_types(raw["types"])
        assert cat["category"] == "Do"
        assert needs_followup(cat) is None

        color = get_color(cat["category"], cat["subcategory"])
        place = {**raw, "category": cat["category"], "subcategory": cat["subcategory"],
                 "color": color, "description": "Iconic Paris landmark"}
        state.add_place("paris-trip", place)

        m = state.get_map("paris-trip")
        assert len(m["places"]) == 1
        assert m["places"][0]["name"] == "Eiffel Tower"
        assert m["places"][0]["color"] == "black"

    def test_add_ambiguous_place_triggers_followup(self, state, places_client):
        state.create_map("paris-trip", "Paris Trip")

        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Angelina", "226 Rue de Rivoli, Paris", 48.865, 2.333,
            ["bakery", "cafe", "establishment"],
        ))

        raw = places_client.search("Angelina Paris")
        cat = categorize_from_types(raw["types"])
        assert cat["category"] is None
        assert needs_followup(cat) == FollowupQuestion.EAT_DRINK_DO

        # Simulate user answering "Eat"
        cat["category"] = "Eat"
        assert needs_followup(cat) == FollowupQuestion.IS_DESSERT

        # Simulate user answering "yes, dessert"
        cat["subcategory"] = "dessert"
        assert needs_followup(cat) is None

        color = get_color(cat["category"], cat["subcategory"])
        assert color == "pink"

        place = {**raw, **cat, "color": color, "description": "Famous tea room"}
        state.add_place("paris-trip", place)
        m = state.get_map("paris-trip")
        assert m["places"][0]["color"] == "pink"
        assert m["places"][0]["subcategory"] == "dessert"

    def test_add_cafe_auto_categorizes_as_drink_coffee(self, state, places_client):
        state.create_map("paris-trip", "Paris Trip")

        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Café de Flore", "172 Bd Saint-Germain, Paris", 48.854, 2.333,
            ["cafe", "point_of_interest"],
        ))

        raw = places_client.search("Café de Flore Paris")
        cat = categorize_from_types(raw["types"])
        assert cat == {"category": "Drink", "subcategory": "coffee"}
        assert needs_followup(cat) is None

        color = get_color(cat["category"], cat["subcategory"])
        assert color == "brown"

    def test_kml_generated_after_adding_places(self, state, places_client):
        state.create_map("paris-trip", "Paris Trip")

        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Eiffel Tower", "Champ de Mars, Paris", 48.858, 2.294,
            ["tourist_attraction", "point_of_interest"],
        ))
        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Café de Flore", "172 Bd Saint-Germain, Paris", 48.854, 2.333,
            ["cafe", "point_of_interest"],
        ))

        for query, types, category, subcategory, desc in [
            ("Eiffel Tower Paris", ["tourist_attraction", "point_of_interest"], "Do", None, "Tower"),
            ("Café de Flore Paris", ["cafe", "point_of_interest"], "Drink", "coffee", "Café"),
        ]:
            raw = places_client.search(query)
            cat = {"category": category, "subcategory": subcategory}
            color = get_color(category, subcategory)
            place = {**raw, **cat, "color": color, "description": desc}
            state.add_place("paris-trip", place)

        m = state.get_map("paris-trip")
        kml = generate_kml(m)
        assert "Eiffel Tower" in kml
        assert "Café de Flore" in kml
        assert "do-black" in kml
        assert "drink-brown" in kml

    def test_manual_fallback_place_added_without_api(self, state, places_client):
        state.create_map("paris-trip", "Paris Trip")
        manual = places_client.build_manual_place(
            name="Le Comptoir du Relais",
            address="9 Carrefour de l'Odéon, Paris",
        )
        place = {**manual, "category": "Eat", "subcategory": None, "color": "blue", "description": "Bistro"}
        state.add_place("paris-trip", place)
        m = state.get_map("paris-trip")
        assert m["places"][0]["name"] == "Le Comptoir du Relais"

    def test_remove_place_from_map(self, state, places_client):
        state.create_map("paris-trip", "Paris Trip")
        resp_lib.add(resp_lib.POST, SEARCH_URL, json=_mock_place_response(
            "Eiffel Tower", "Champ de Mars, Paris", 48.858, 2.294,
            ["tourist_attraction"],
        ))
        raw = places_client.search("Eiffel Tower")
        place = {**raw, "category": "Do", "subcategory": None, "color": "black", "description": ""}
        state.add_place("paris-trip", place)
        state.remove_place("paris-trip", "Eiffel Tower")
        m = state.get_map("paris-trip")
        assert m["places"] == []


@pytest.mark.parametrize("types,expected_category,expected_sub", [
    (["restaurant", "food"], "Eat", None),
    (["cafe", "point_of_interest"], "Drink", "coffee"),
    (["bar", "establishment"], "Drink", "cocktails"),
    (["tourist_attraction", "point_of_interest"], "Do", None),
    (["museum"], "Do", None),
    (["park"], "Do", None),
    (["bakery", "cafe"], None, None),  # ambiguous
    ([], None, None),                 # ambiguous
])
def test_categorizer_parametrized(types, expected_category, expected_sub):
    result = categorize_from_types(types)
    assert result["category"] == expected_category
    assert result["subcategory"] == expected_sub
