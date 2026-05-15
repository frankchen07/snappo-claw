import pytest
from travel.src.categorizer import (
    categorize_from_types,
    get_color,
    needs_followup,
    FollowupQuestion,
)


class TestCategorizeFromTypes:
    def test_restaurant_is_eat(self):
        result = categorize_from_types(["restaurant", "food", "point_of_interest"])
        assert result["category"] == "Eat"
        assert result["subcategory"] is None

    def test_meal_takeaway_is_eat(self):
        result = categorize_from_types(["meal_takeaway", "food"])
        assert result["category"] == "Eat"

    def test_cafe_alone_is_drink_coffee(self):
        result = categorize_from_types(["cafe", "point_of_interest"])
        assert result["category"] == "Drink"
        assert result["subcategory"] == "coffee"

    def test_bar_is_drink_cocktails(self):
        result = categorize_from_types(["bar", "point_of_interest"])
        assert result["category"] == "Drink"
        assert result["subcategory"] == "cocktails"

    def test_night_club_is_drink_cocktails(self):
        result = categorize_from_types(["night_club", "establishment"])
        assert result["category"] == "Drink"
        assert result["subcategory"] == "cocktails"

    def test_tourist_attraction_is_do(self):
        result = categorize_from_types(["tourist_attraction", "point_of_interest"])
        assert result["category"] == "Do"
        assert result["subcategory"] is None

    def test_museum_is_do(self):
        result = categorize_from_types(["museum", "point_of_interest"])
        assert result["category"] == "Do"

    def test_park_is_do(self):
        result = categorize_from_types(["park", "point_of_interest"])
        assert result["category"] == "Do"

    def test_bakery_alone_is_ambiguous(self):
        result = categorize_from_types(["bakery", "establishment"])
        assert result["category"] is None

    def test_bakery_plus_cafe_is_ambiguous(self):
        result = categorize_from_types(["bakery", "cafe", "establishment"])
        assert result["category"] is None

    def test_empty_types_is_ambiguous(self):
        result = categorize_from_types([])
        assert result["category"] is None

    def test_unknown_types_is_ambiguous(self):
        result = categorize_from_types(["establishment", "geocode"])
        assert result["category"] is None

    def test_shopping_mall_is_do(self):
        result = categorize_from_types(["shopping_mall", "point_of_interest"])
        assert result["category"] == "Do"


class TestGetColor:
    def test_eat_default_is_blue(self):
        assert get_color("Eat", None) == "blue"

    def test_eat_dessert_is_pink(self):
        assert get_color("Eat", "dessert") == "pink"

    def test_drink_coffee_is_brown(self):
        assert get_color("Drink", "coffee") == "brown"

    def test_drink_cocktails_is_purple(self):
        assert get_color("Drink", "cocktails") == "purple"

    def test_do_is_black(self):
        assert get_color("Do", None) == "black"

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            get_color("Unknown", None)


class TestNeedsFollowup:
    def test_ambiguous_needs_eat_drink_do(self):
        q = needs_followup({"category": None, "subcategory": None})
        assert q == FollowupQuestion.EAT_DRINK_DO

    def test_eat_no_subcategory_needs_dessert_question(self):
        q = needs_followup({"category": "Eat", "subcategory": None})
        assert q == FollowupQuestion.IS_DESSERT

    def test_drink_no_subcategory_needs_coffee_or_cocktails(self):
        q = needs_followup({"category": "Drink", "subcategory": None})
        assert q == FollowupQuestion.COFFEE_OR_COCKTAILS

    def test_fully_resolved_needs_no_followup(self):
        assert needs_followup({"category": "Eat", "subcategory": "dessert"}) is None
        assert needs_followup({"category": "Drink", "subcategory": "coffee"}) is None
        assert needs_followup({"category": "Drink", "subcategory": "cocktails"}) is None
        assert needs_followup({"category": "Do", "subcategory": None}) is None
