import json
from pathlib import Path

import pytest

from recipemd import (
    Amount,
    Ingredient,
    IngredientGroup,
    Recipe,
    RecipeMDError,
    __version__,
    parse,
    parse_amount,
)

TESTDATA = Path(__file__).parent / "testdata"

VALID = sorted(p for p in TESTDATA.rglob("*.md") if not p.name.endswith(".invalid.md"))
INVALID = sorted(TESTDATA.rglob("*.invalid.md"))


def _id(p: Path) -> str:
    return str(p.relative_to(TESTDATA))


def _kwargs(p: Path) -> dict:
    return {"frontmatter": True} if "frontmatter" in p.parts else {}


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize("md_path", VALID, ids=[_id(p) for p in VALID])
def test_golden_valid(md_path: Path):
    expected = json.loads(md_path.with_suffix(".json").read_text())
    assert parse(md_path.read_text(), **_kwargs(md_path)).to_dict() == expected


@pytest.mark.parametrize("md_path", INVALID, ids=[_id(p) for p in INVALID])
def test_golden_invalid(md_path: Path):
    with pytest.raises(RecipeMDError):
        parse(md_path.read_text(), **_kwargs(md_path))


def test_parse_amount_unitless():
    a = parse_amount("2.5")
    assert a.factor == 2.5
    assert a.unit is None


def test_parse_amount_with_unit():
    a = parse_amount("1.5 cups")
    assert a.factor == 1.5
    assert a.unit == "cups"


def test_parse_amount_unit_without_factor_raises():
    with pytest.raises(RecipeMDError):
        parse_amount("cups")


def test_amount_scale_mutates_factor():
    a = Amount(factor=4, unit="ml")
    a.scale(0.5)
    assert a.factor == 2


def test_ingredient_scale_handles_no_amount():
    ing = Ingredient(name="salt")
    ing.scale(2)
    assert ing.amount is None


def test_ingredient_group_scale_recurses():
    inner = Ingredient(name="x", amount=Amount(factor=10))
    group = IngredientGroup(
        title="g",
        ingredient_groups=[
            IngredientGroup(title="sub", ingredients=[inner]),
        ],
    )
    group.scale(0.1)
    assert inner.amount.factor == pytest.approx(1)


def test_recipe_scale_for_yield_matching_unit():
    r = Recipe(
        yields=[Amount(factor=4, unit="servings")],
        ingredients=[Ingredient(name="x", amount=Amount(factor=200, unit="g"))],
    )
    r.scale_for_yield(Amount(factor=6, unit="servings"))
    assert r.yields[0].factor == 6
    assert r.ingredients[0].amount.factor == pytest.approx(300)


def test_recipe_scale_for_yield_unitless_falls_back_to_factor():
    r = Recipe(
        yields=[Amount(factor=12, unit="cookies")],
        ingredients=[Ingredient(name="x", amount=Amount(factor=100))],
    )
    r.scale_for_yield(Amount(factor=2))
    assert r.yields[0].factor == 24
    assert r.ingredients[0].amount.factor == 200


def test_recipe_scale_for_yield_unmatched_unit_raises():
    r = Recipe(yields=[Amount(factor=4, unit="servings")])
    with pytest.raises(RecipeMDError, match="no matching yield"):
        r.scale_for_yield(Amount(factor=2, unit="quarts"))
