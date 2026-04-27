import sys
from pathlib import Path

import pytest

EXTRACT_DIR = (
    Path(__file__).parent.parent
    / "plugins"
    / "recipemd"
    / "skills"
    / "recipemd"
    / "scripts"
)
sys.path.insert(0, str(EXTRACT_DIR))

from extract import _split_freetext_ingredient, build_recipe  # noqa: E402


def test_split_unit_and_name():
    ing = _split_freetext_ingredient("2 cups flour")
    assert ing.amount.factor == 2
    assert ing.amount.unit == "cups"
    assert ing.name == "flour"


def test_split_fraction_unit_name():
    ing = _split_freetext_ingredient("1/2 tsp salt")
    assert ing.amount.factor == 0.5
    assert ing.amount.unit == "tsp"
    assert ing.name == "salt"


def test_split_count_only():
    ing = _split_freetext_ingredient("3 eggs")
    assert ing.amount.factor == 3
    assert ing.amount.unit is None
    assert ing.name == "eggs"


def test_split_no_amount():
    ing = _split_freetext_ingredient("salt to taste")
    assert ing.amount is None
    assert ing.name == "salt to taste"


def test_split_vulgar_fraction():
    ing = _split_freetext_ingredient("½ cup butter")
    assert ing.amount.factor == pytest.approx(0.5)
    assert ing.amount.unit == "cup"
    assert ing.name == "butter"


def test_split_mixed_fraction():
    ing = _split_freetext_ingredient("1 1/2 cups water")
    assert ing.amount.factor == pytest.approx(1.5)
    assert ing.amount.unit == "cups"
    assert ing.name == "water"


def test_split_decimal_comma():
    ing = _split_freetext_ingredient("1,5 cups water")
    assert ing.amount.factor == pytest.approx(1.5)
    assert ing.amount.unit == "cups"


def test_split_empty_string():
    ing = _split_freetext_ingredient("")
    assert ing.name == ""
    assert ing.amount is None


def test_build_recipe_minimal():
    r = build_recipe(
        {
            "title": "Test Recipe",
            "description": "A short note.",
            "yields": "4 servings",
            "ingredients": ["2 cups flour", "1 tsp salt"],
            "instructions": "Mix and bake.",
        }
    )
    assert r.title == "Test Recipe"
    assert r.description == "A short note."
    assert len(r.yields) == 1
    assert r.yields[0].factor == 4
    assert r.yields[0].unit == "servings"
    assert len(r.ingredients) == 2
    assert r.instructions == "Mix and bake."


def test_build_recipe_groups():
    r = build_recipe(
        {
            "title": "Test",
            "ingredient_groups": [
                {"purpose": "Dough", "ingredients": ["2 cups flour"]},
                {"purpose": "Topping", "ingredients": ["1 cup cheese"]},
            ],
        }
    )
    assert len(r.ingredient_groups) == 2
    assert r.ingredient_groups[0].title == "Dough"
    assert r.ingredient_groups[0].ingredients[0].name == "flour"
    assert r.ingredient_groups[1].title == "Topping"


def test_build_recipe_tags_dedup():
    r = build_recipe(
        {
            "title": "T",
            "cuisine": "italian",
            "category": "pasta",
            "keywords": ["italian", "dinner", "pasta"],
        }
    )
    # cuisine+category first, then new keywords, dedup preserves order.
    assert r.tags == ["italian", "pasta", "dinner"]


def test_build_recipe_uses_instructions_list_when_no_block():
    r = build_recipe(
        {
            "title": "T",
            "instructions_list": ["Step one.", "Step two."],
        }
    )
    assert r.instructions == "Step one.\n\nStep two."
