from enum import Enum


class FollowupQuestion(Enum):
    EAT_DRINK_DO = "eat_drink_do"
    IS_DESSERT = "is_dessert"
    COFFEE_OR_COCKTAILS = "coffee_or_cocktails"


_EAT_TYPES = {"restaurant", "meal_takeaway", "meal_delivery", "food"}
_DRINK_COFFEE_TYPES = {"cafe"}
_DRINK_COCKTAILS_TYPES = {"bar", "night_club", "liquor_store"}
_DO_TYPES = {"tourist_attraction", "museum", "park", "amusement_park", "shopping_mall", "store", "art_gallery", "zoo", "aquarium", "stadium", "movie_theater"}
_AMBIGUOUS_TYPES = {"bakery"}  # could be Eat or Drink depending on context

_COLOR_MAP = {
    ("Eat", None): "blue",
    ("Eat", "dessert"): "pink",
    ("Drink", "coffee"): "brown",
    ("Drink", "cocktails"): "purple",
    ("Do", None): "black",
}

_STYLE_ID_MAP = {
    "blue": "eat-blue",
    "pink": "eat-pink",
    "brown": "drink-brown",
    "purple": "drink-purple",
    "black": "do-black",
}


def categorize_from_types(types: list[str]) -> dict:
    type_set = set(types)

    has_eat = bool(type_set & _EAT_TYPES)
    has_coffee = bool(type_set & _DRINK_COFFEE_TYPES)
    has_cocktails = bool(type_set & _DRINK_COCKTAILS_TYPES)
    has_do = bool(type_set & _DO_TYPES)
    has_bakery = "bakery" in type_set

    # Unambiguous drink — bar/night_club with no food signals
    if has_cocktails and not has_eat:
        return {"category": "Drink", "subcategory": "cocktails"}

    # Café alone (no bakery, no restaurant) → coffee
    if has_coffee and not has_eat and not has_bakery:
        return {"category": "Drink", "subcategory": "coffee"}

    # Unambiguous food
    if has_eat and not has_coffee and not has_bakery:
        return {"category": "Eat", "subcategory": None}

    # Do (tourist attractions etc.)
    if has_do and not has_eat and not has_coffee and not has_cocktails and not has_bakery:
        return {"category": "Do", "subcategory": None}

    return {"category": None, "subcategory": None}


def get_color(category: str, subcategory: str | None) -> str:
    key = (category, subcategory)
    if key not in _COLOR_MAP:
        raise ValueError(f"Unknown category/subcategory combination: {key}")
    return _COLOR_MAP[key]


def get_style_id(color: str) -> str:
    return _STYLE_ID_MAP[color]


def needs_followup(categorization: dict) -> FollowupQuestion | None:
    category = categorization["category"]
    subcategory = categorization["subcategory"]

    if category is None:
        return FollowupQuestion.EAT_DRINK_DO
    if category == "Eat" and subcategory is None:
        return FollowupQuestion.IS_DESSERT
    if category == "Drink" and subcategory is None:
        return FollowupQuestion.COFFEE_OR_COCKTAILS
    return None
