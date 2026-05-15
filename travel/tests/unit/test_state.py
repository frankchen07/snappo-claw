import json
import pytest
from travel.src.state import MapState


@pytest.fixture
def state(tmp_path):
    return MapState(maps_dir=str(tmp_path))


@pytest.fixture
def place():
    return {
        "name": "Café de Flore",
        "address": "172 Bd Saint-Germain, 75006 Paris",
        "lat": 48.854,
        "lng": 2.333,
        "place_id": "ChIJtest123",
        "category": "Drink",
        "subcategory": "coffee",
        "description": "Iconic Paris café",
        "color": "brown",
    }


class TestCreateMap:
    def test_creates_json_file(self, state, tmp_path):
        state.create_map("paris-trip", "Paris Trip")
        assert (tmp_path / "paris-trip.json").exists()

    def test_returns_map_dict(self, state):
        m = state.create_map("paris-trip", "Paris Trip")
        assert m["id"] == "paris-trip"
        assert m["name"] == "Paris Trip"
        assert m["places"] == []
        assert m["drive_file_id"] is None

    def test_duplicate_id_raises(self, state):
        state.create_map("paris-trip", "Paris Trip")
        with pytest.raises(ValueError, match="already exists"):
            state.create_map("paris-trip", "Paris Trip 2")

    def test_has_default_layers(self, state):
        m = state.create_map("paris-trip", "Paris Trip")
        assert set(m["layers"]) == {"Eat", "Drink", "Do"}


class TestGetMap:
    def test_returns_existing_map(self, state):
        state.create_map("paris-trip", "Paris Trip")
        m = state.get_map("paris-trip")
        assert m["id"] == "paris-trip"

    def test_missing_map_raises(self, state):
        with pytest.raises(KeyError):
            state.get_map("nonexistent")


class TestListMaps:
    def test_empty_initially(self, state):
        assert state.list_maps() == []

    def test_lists_created_maps(self, state):
        state.create_map("paris-trip", "Paris Trip")
        state.create_map("tokyo-trip", "Tokyo Trip")
        ids = [m["id"] for m in state.list_maps()]
        assert set(ids) == {"paris-trip", "tokyo-trip"}


class TestAddPlace:
    def test_adds_place_to_map(self, state, place):
        state.create_map("paris-trip", "Paris Trip")
        state.add_place("paris-trip", place)
        m = state.get_map("paris-trip")
        assert len(m["places"]) == 1
        assert m["places"][0]["name"] == "Café de Flore"

    def test_place_has_added_at(self, state, place):
        state.create_map("paris-trip", "Paris Trip")
        state.add_place("paris-trip", place)
        m = state.get_map("paris-trip")
        assert "added_at" in m["places"][0]

    def test_add_to_nonexistent_map_raises(self, state, place):
        with pytest.raises(KeyError):
            state.add_place("nonexistent", place)

    def test_persists_to_disk(self, state, tmp_path, place):
        state.create_map("paris-trip", "Paris Trip")
        state.add_place("paris-trip", place)
        raw = json.loads((tmp_path / "paris-trip.json").read_text())
        assert len(raw["places"]) == 1


class TestRemovePlace:
    def test_removes_place_by_name(self, state, place):
        state.create_map("paris-trip", "Paris Trip")
        state.add_place("paris-trip", place)
        state.remove_place("paris-trip", "Café de Flore")
        m = state.get_map("paris-trip")
        assert m["places"] == []

    def test_remove_nonexistent_place_raises(self, state):
        state.create_map("paris-trip", "Paris Trip")
        with pytest.raises(ValueError, match="not found"):
            state.remove_place("paris-trip", "Does Not Exist")


class TestSetDriveFileId:
    def test_updates_drive_file_id(self, state):
        state.create_map("paris-trip", "Paris Trip")
        state.set_drive_file_id("paris-trip", "abc123")
        m = state.get_map("paris-trip")
        assert m["drive_file_id"] == "abc123"
