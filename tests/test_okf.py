from pathlib import Path

from okf import (
    build_bundle,
    recipe_to_body,
    recipe_to_frontmatter,
    recipe_to_okf_doc,
)
from recipemd import Amount, Ingredient, IngredientGroup, Recipe, parse


def test_frontmatter_minimal_fields_only():
    recipe = Recipe(title="Toast")
    fm = recipe_to_frontmatter(recipe)
    assert fm == {"type": "Recipe", "title": "Toast"}


def test_frontmatter_includes_optional_fields():
    recipe = Recipe(
        title="Pico de Gallo",
        description="A fresh salsa.",
        tags=["mexican", "vegan"],
        yields=[Amount(6, "Servings"), Amount(350, "g")],
    )
    fm = recipe_to_frontmatter(recipe, resource="https://example.com/pico")
    assert fm["description"] == "A fresh salsa."
    assert fm["tags"] == ["mexican", "vegan"]
    assert fm["yields"] == ["6 Servings", "350 g"]
    assert fm["resource"] == "https://example.com/pico"


def test_body_renders_flat_ingredients_and_instructions():
    recipe = Recipe(
        title="Toast",
        ingredients=[
            Ingredient(name="bread", amount=Amount(2, "slices")),
            Ingredient(name="butter"),
        ],
        instructions="Toast the bread. Spread butter.",
    )
    body = recipe_to_body(recipe)
    assert "## Ingredients" in body
    assert "- *2 slices* bread" in body
    assert "- butter" in body
    assert "## Instructions" in body
    assert "Toast the bread." in body


def test_body_renders_linked_ingredient():
    recipe = Recipe(
        title="Lasagna",
        ingredients=[
            Ingredient(name="Tomato sauce", amount=Amount(2), link="./sauce.md")
        ],
    )
    body = recipe_to_body(recipe)
    assert "- *2* [Tomato sauce](./sauce.md)" in body


def test_body_renders_nested_groups_with_increasing_heading_depth():
    recipe = Recipe(
        title="Layered",
        ingredient_groups=[
            IngredientGroup(
                title="Sauce",
                ingredients=[Ingredient(name="tomatoes", amount=Amount(2))],
                ingredient_groups=[
                    IngredientGroup(
                        title="Spice Mix",
                        ingredients=[Ingredient(name="cumin", amount=Amount(1, "tsp"))],
                    )
                ],
            )
        ],
    )
    body = recipe_to_body(recipe)
    lines = body.splitlines()
    assert "### Sauce" in lines
    assert "#### Spice Mix" in lines
    assert lines.index("### Sauce") < lines.index("#### Spice Mix")


def test_body_omits_instructions_section_when_absent():
    recipe = Recipe(title="Toast", ingredients=[Ingredient(name="bread")])
    body = recipe_to_body(recipe)
    assert "## Instructions" not in body


def test_doc_has_frontmatter_fences_and_blank_separator():
    recipe = Recipe(title="Toast", ingredients=[Ingredient(name="bread")])
    doc = recipe_to_okf_doc(recipe)
    assert doc.startswith("---\n")
    assert 'type: "Recipe"' in doc
    assert "\n---\n\n## Ingredients" in doc


def test_doc_round_trips_real_example():
    example = (
        Path(__file__).parent.parent
        / "plugins"
        / "recipemd"
        / "skills"
        / "recipemd"
        / "examples"
        / "recipe.md"
    )
    recipe = parse(example.read_text())
    doc = recipe_to_okf_doc(recipe)
    assert 'title: "Spaghetti Bolognese"' in doc
    assert "### Sauce" in doc
    assert "### Pasta and finish" in doc
    assert "[Fresh egg pasta](./fresh-egg-pasta.md)" in doc


def test_build_bundle_writes_index_and_recipes(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "toast.md").write_text(
        "# Toast\n\n---\n\n- *2 slices* bread\n\n---\n\nToast it.\n"
    )
    (src / "jam.md").write_text("# Jam\n\n---\n\n- *1 jar* jam\n")

    out = tmp_path / "out"
    build_bundle(src, out, title="Breakfast", description="Quick bites")

    index = (out / "index.md").read_text()
    assert 'type: "Recipe Collection"' in index
    assert 'title: "Breakfast"' in index
    assert "[Toast](./recipes/toast.md)" in index
    assert "[Jam](./recipes/jam.md)" in index

    assert (out / "recipes" / "toast.md").exists()
    assert (out / "recipes" / "jam.md").exists()


def test_build_bundle_default_title_from_dirname(tmp_path: Path):
    src = tmp_path / "weeknight-meals"
    src.mkdir()
    (src / "toast.md").write_text("# Toast\n\n---\n\n- bread\n")

    out = tmp_path / "out"
    build_bundle(src, out)

    index = (out / "index.md").read_text()
    assert 'title: "Weeknight Meals"' in index
