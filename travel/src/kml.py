from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from .categorizer import get_style_id

_ICON_URLS = {
    "eat-blue":    "https://maps.google.com/mapfiles/kml/paddle/blu-circle.png",
    "eat-pink":    "https://maps.google.com/mapfiles/kml/paddle/pink-circle.png",
    "drink-brown": "https://maps.google.com/mapfiles/kml/paddle/orange-circle.png",
    "drink-purple":"https://maps.google.com/mapfiles/kml/paddle/purple-circle.png",
    "do-black":    "https://maps.google.com/mapfiles/kml/paddle/wht-circle.png",
}

_STYLES = [
    ("eat-blue",     "ff0000ff"),
    ("eat-pink",     "ffff69b4"),
    ("drink-brown",  "ff7b3f00"),
    ("drink-purple", "ff800080"),
    ("do-black",     "ff000000"),
]

NS = "http://www.opengis.net/kml/2.2"


def _add_style(doc: Element, style_id: str, color_abgr: str) -> None:
    style = SubElement(doc, f"{{{NS}}}Style", id=style_id)
    icon_style = SubElement(style, f"{{{NS}}}IconStyle")
    color_el = SubElement(icon_style, f"{{{NS}}}color")
    color_el.text = color_abgr
    scale_el = SubElement(icon_style, f"{{{NS}}}scale")
    scale_el.text = "1.2"
    icon = SubElement(icon_style, f"{{{NS}}}Icon")
    href = SubElement(icon, f"{{{NS}}}href")
    href.text = _ICON_URLS.get(style_id, "")


def generate_kml(map_data: dict) -> str:
    kml = Element(f"{{{NS}}}kml")
    doc = SubElement(kml, f"{{{NS}}}Document")

    name_el = SubElement(doc, f"{{{NS}}}name")
    name_el.text = map_data["name"]

    for style_id, color_abgr in _STYLES:
        _add_style(doc, style_id, color_abgr)

    # Group places by category
    by_layer: dict[str, list] = {"Eat": [], "Drink": [], "Do": []}
    for place in map_data.get("places", []):
        layer = place.get("category", "Do")
        if layer in by_layer:
            by_layer[layer].append(place)

    for layer_name in ["Eat", "Drink", "Do"]:
        folder = SubElement(doc, f"{{{NS}}}Folder")
        fn = SubElement(folder, f"{{{NS}}}name")
        fn.text = layer_name

        for place in by_layer[layer_name]:
            pm = SubElement(folder, f"{{{NS}}}Placemark")

            pname = SubElement(pm, f"{{{NS}}}name")
            pname.text = place["name"]

            pdesc = SubElement(pm, f"{{{NS}}}description")
            lines = [place.get("description") or "", place.get("address") or ""]
            pdesc.text = "\n".join(l for l in lines if l)

            color = place.get("color", "black")
            style_id = get_style_id(color)
            style_url = SubElement(pm, f"{{{NS}}}styleUrl")
            style_url.text = f"#{style_id}"

            lat = place.get("lat")
            lng = place.get("lng")
            if lat is not None and lng is not None:
                point = SubElement(pm, f"{{{NS}}}Point")
                coords = SubElement(point, f"{{{NS}}}coordinates")
                coords.text = f"{lng},{lat},0"
            else:
                addr_el = SubElement(pm, f"{{{NS}}}address")
                addr_el.text = place.get("address", "")

    raw = tostring(kml, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    # Remove the extra XML declaration minidom adds (KML already implies version)
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)
