import xml.etree.ElementTree as ET
import pytest
from travel.src.kml import generate_kml

NS = "http://www.opengis.net/kml/2.2"


def parse(kml_str: str) -> ET.Element:
    return ET.fromstring(kml_str)


@pytest.fixture
def empty_map():
    return {
        "id": "paris-trip",
        "name": "Paris Trip",
        "places": [],
        "layers": {"Eat": [], "Drink": [], "Do": []},
    }


@pytest.fixture
def map_with_places():
    return {
        "id": "paris-trip",
        "name": "Paris Trip",
        "places": [
            {
                "name": "Café de Flore",
                "address": "172 Bd Saint-Germain, Paris",
                "lat": 48.854,
                "lng": 2.333,
                "category": "Drink",
                "subcategory": "coffee",
                "description": "Iconic Paris café",
                "color": "brown",
            },
            {
                "name": "Ladurée",
                "address": "75 Av. des Champs-Élysées, Paris",
                "lat": 48.872,
                "lng": 2.304,
                "category": "Eat",
                "subcategory": "dessert",
                "description": "Famous macarons",
                "color": "pink",
            },
            {
                "name": "Eiffel Tower",
                "address": "Champ de Mars, Paris",
                "lat": 48.858,
                "lng": 2.294,
                "category": "Do",
                "subcategory": None,
                "description": "Iconic landmark",
                "color": "black",
            },
        ],
        "layers": {"Eat": [], "Drink": [], "Do": []},
    }


class TestKmlStructure:
    def test_returns_string(self, empty_map):
        result = generate_kml(empty_map)
        assert isinstance(result, str)

    def test_valid_xml(self, empty_map):
        result = generate_kml(empty_map)
        ET.fromstring(result)  # raises if invalid

    def test_has_kml_root(self, empty_map):
        root = parse(generate_kml(empty_map))
        assert root.tag == f"{{{NS}}}kml"

    def test_document_name_matches_map(self, empty_map):
        root = parse(generate_kml(empty_map))
        doc = root.find(f"{{{NS}}}Document")
        name = doc.find(f"{{{NS}}}name").text
        assert name == "Paris Trip"

    def test_three_layer_folders(self, empty_map):
        root = parse(generate_kml(empty_map))
        doc = root.find(f"{{{NS}}}Document")
        folders = doc.findall(f"{{{NS}}}Folder")
        names = [f.find(f"{{{NS}}}name").text for f in folders]
        assert set(names) == {"Eat", "Drink", "Do"}

    def test_has_style_definitions(self, empty_map):
        root = parse(generate_kml(empty_map))
        doc = root.find(f"{{{NS}}}Document")
        styles = doc.findall(f"{{{NS}}}Style")
        style_ids = {s.get("id") for s in styles}
        assert "eat-blue" in style_ids
        assert "eat-pink" in style_ids
        assert "drink-brown" in style_ids
        assert "drink-purple" in style_ids
        assert "do-black" in style_ids


class TestKmlPlacemarks:
    def test_places_in_correct_folders(self, map_with_places):
        root = parse(generate_kml(map_with_places))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}

        drink_marks = folders["Drink"].findall(f"{{{NS}}}Placemark")
        assert len(drink_marks) == 1
        assert drink_marks[0].find(f"{{{NS}}}name").text == "Café de Flore"

        eat_marks = folders["Eat"].findall(f"{{{NS}}}Placemark")
        assert len(eat_marks) == 1
        assert eat_marks[0].find(f"{{{NS}}}name").text == "Ladurée"

        do_marks = folders["Do"].findall(f"{{{NS}}}Placemark")
        assert len(do_marks) == 1
        assert do_marks[0].find(f"{{{NS}}}name").text == "Eiffel Tower"

    def test_placemark_has_coordinates(self, map_with_places):
        root = parse(generate_kml(map_with_places))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}
        pm = folders["Drink"].findall(f"{{{NS}}}Placemark")[0]
        point = pm.find(f"{{{NS}}}Point")
        coords = point.find(f"{{{NS}}}coordinates").text.strip()
        assert "2.333" in coords
        assert "48.854" in coords

    def test_placemark_has_description(self, map_with_places):
        root = parse(generate_kml(map_with_places))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}
        pm = folders["Drink"].findall(f"{{{NS}}}Placemark")[0]
        desc = pm.find(f"{{{NS}}}description").text
        assert "Iconic Paris café" in desc

    def test_placemark_references_style(self, map_with_places):
        root = parse(generate_kml(map_with_places))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}
        pm = folders["Drink"].findall(f"{{{NS}}}Placemark")[0]
        style_url = pm.find(f"{{{NS}}}styleUrl").text
        assert style_url == "#drink-brown"

        pm_eat = folders["Eat"].findall(f"{{{NS}}}Placemark")[0]
        assert pm_eat.find(f"{{{NS}}}styleUrl").text == "#eat-pink"


class TestKmlAddressFallback:
    def test_manual_place_emits_address_element(self):
        map_data = {
            "id": "test",
            "name": "Test Map",
            "places": [
                {
                    "name": "Secret Bar",
                    "address": "12 Rue XYZ, 75001 Paris",
                    "lat": None,
                    "lng": None,
                    "category": "Drink",
                    "subcategory": "cocktails",
                    "description": "",
                    "color": "purple",
                }
            ],
        }
        root = parse(generate_kml(map_data))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}
        pm = folders["Drink"].findall(f"{{{NS}}}Placemark")[0]
        # Should have <address>, NOT <Point>
        assert pm.find(f"{{{NS}}}Point") is None
        addr = pm.find(f"{{{NS}}}address")
        assert addr is not None
        assert "75001" in addr.text

    def test_normal_place_still_uses_point(self):
        map_data = {
            "id": "test",
            "name": "Test Map",
            "places": [
                {
                    "name": "Eiffel Tower",
                    "address": "Champ de Mars, Paris",
                    "lat": 48.858,
                    "lng": 2.294,
                    "category": "Do",
                    "subcategory": None,
                    "description": "",
                    "color": "black",
                }
            ],
        }
        root = parse(generate_kml(map_data))
        doc = root.find(f"{{{NS}}}Document")
        folders = {f.find(f"{{{NS}}}name").text: f for f in doc.findall(f"{{{NS}}}Folder")}
        pm = folders["Do"].findall(f"{{{NS}}}Placemark")[0]
        assert pm.find(f"{{{NS}}}Point") is not None
        assert pm.find(f"{{{NS}}}address") is None
