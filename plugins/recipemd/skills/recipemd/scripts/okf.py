#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown-it-py",
# ]
# ///
"""Convert RecipeMD documents to Open Knowledge Format (OKF) documents/bundles.

OKF (https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)
represents knowledge as plain markdown files with a YAML frontmatter block
(only `type` is mandatory) followed by a free-form markdown body. Bundles are
directories of such files linked together with normal markdown links, with an
optional `index.md` per directory.

Two modes:

    uv run scripts/okf.py <file>                     # single document -> stdout
    uv run scripts/okf.py --bundle <dir> --out <out> # directory of recipes -> bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# scripts/okf.py and scripts/recipemd.py (symlink) live in the same dir.
sys.path.insert(0, str(Path(__file__).parent))

from recipemd import (  # noqa: E402
    Amount,
    Ingredient,
    IngredientGroup,
    Recipe,
    RecipeMDError,
    parse,
)

OKF_RECIPE_TYPE = "Recipe"
OKF_COLLECTION_TYPE = "Recipe Collection"


def _yaml_str(s: str) -> str:
    """Double-quoted YAML scalar. JSON's escaping rules are a valid subset of
    YAML's for double-quoted scalars, so json.dumps gives us a safe encoder.
    """
    import json

    return json.dumps(s, ensure_ascii=False)


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(_yaml_str(i) for i in items) + "]"


def _yaml_frontmatter(fields: dict[str, str | list[str]]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}: {_yaml_list(value)}")
        else:
            lines.append(f"{key}: {_yaml_str(value)}")
    lines.append("---")
    return "\n".join(lines)


def _amount_str(amount: Amount) -> str:
    d = amount.to_dict()
    factor, unit = d["factor"], d["unit"]
    return f"{factor} {unit}" if unit else factor


def _render_ingredient(ing: Ingredient) -> str:
    prefix = f"*{_amount_str(ing.amount)}* " if ing.amount else ""
    name = f"[{ing.name}]({ing.link})" if ing.link else ing.name
    return f"- {prefix}{name}"


def _render_groups(groups: list[IngredientGroup], depth: int) -> list[str]:
    lines: list[str] = []
    for group in groups:
        lines.append(f"{'#' * depth} {group.title}")
        lines.append("")
        lines.extend(_render_ingredient(i) for i in group.ingredients)
        if group.ingredients:
            lines.append("")
        lines.extend(_render_groups(group.ingredient_groups, depth + 1))
    return lines


def recipe_to_frontmatter(
    recipe: Recipe, *, resource: str | None = None
) -> dict[str, str | list[str]]:
    fields: dict[str, str | list[str]] = {
        "type": OKF_RECIPE_TYPE,
        "title": recipe.title,
    }
    if recipe.description:
        fields["description"] = recipe.description
    if recipe.tags:
        fields["tags"] = list(recipe.tags)
    if recipe.yields:
        fields["yields"] = [_amount_str(y) for y in recipe.yields]
    if resource:
        fields["resource"] = resource
    return fields


def recipe_to_body(recipe: Recipe) -> str:
    lines = ["## Ingredients", ""]
    lines.extend(_render_ingredient(i) for i in recipe.ingredients)
    if recipe.ingredients:
        lines.append("")
    lines.extend(_render_groups(recipe.ingredient_groups, depth=3))
    if recipe.instructions:
        lines.append("## Instructions")
        lines.append("")
        lines.append(recipe.instructions)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def recipe_to_okf_doc(recipe: Recipe, *, resource: str | None = None) -> str:
    frontmatter = _yaml_frontmatter(recipe_to_frontmatter(recipe, resource=resource))
    body = recipe_to_body(recipe)
    return f"{frontmatter}\n\n{body}"


def _default_collection_title(dir_path: Path) -> str:
    return dir_path.name.replace("-", " ").replace("_", " ").title() or "Recipes"


def build_bundle(
    input_dir: Path,
    out_dir: Path,
    *,
    title: str | None = None,
    description: str | None = None,
    frontmatter: bool = False,
) -> None:
    files = sorted(input_dir.glob("*.md"))
    if not files:
        raise RecipeMDError(f"no .md files found in {input_dir}")

    recipes_dir = out_dir / "recipes"
    recipes_dir.mkdir(parents=True, exist_ok=True)

    links: list[str] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        try:
            recipe = parse(text, frontmatter=frontmatter)
        except RecipeMDError as e:
            raise RecipeMDError(f"{file}: {e}") from e
        doc = recipe_to_okf_doc(recipe)
        (recipes_dir / file.name).write_text(doc, encoding="utf-8")
        links.append(f"- [{recipe.title}](./recipes/{file.name})")

    index_fields: dict[str, str | list[str]] = {
        "type": OKF_COLLECTION_TYPE,
        "title": title or _default_collection_title(input_dir),
    }
    if description:
        index_fields["description"] = description
    index_body = "## Recipes\n\n" + "\n".join(links) + "\n"
    index_doc = f"{_yaml_frontmatter(index_fields)}\n\n{index_body}"
    (out_dir / "index.md").write_text(index_doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Convert RecipeMD documents to Open Knowledge Format (OKF)."
    )
    p.add_argument(
        "file", nargs="?", help="path to a RecipeMD .md file (default: stdin)"
    )
    p.add_argument(
        "--bundle",
        metavar="DIR",
        help="convert every *.md file in DIR into an OKF bundle",
    )
    p.add_argument(
        "--out",
        metavar="DIR",
        default="okf",
        help="output directory for --bundle (default: okf)",
    )
    p.add_argument("--collection-title", help="title for the bundle's index.md")
    p.add_argument(
        "--collection-description", help="description for the bundle's index.md"
    )
    p.add_argument("--resource", help="source URL to record as the resource field")
    p.add_argument(
        "--frontmatter",
        action="store_true",
        help="strip existing YAML/TOML frontmatter before parsing",
    )
    args = p.parse_args(argv)

    if args.bundle:
        try:
            build_bundle(
                Path(args.bundle),
                Path(args.out),
                title=args.collection_title,
                description=args.collection_description,
                frontmatter=args.frontmatter,
            )
        except RecipeMDError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"wrote OKF bundle to {args.out}")
        return 0

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    try:
        recipe = parse(text, frontmatter=args.frontmatter)
    except RecipeMDError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(recipe_to_okf_doc(recipe, resource=args.resource), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
