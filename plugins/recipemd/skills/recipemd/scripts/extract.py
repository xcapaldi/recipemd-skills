#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "recipe-scrapers",
# ]
# ///
"""Extract a recipe from a URL and emit canonical RecipeMD-shaped JSON.

Output:

    {
      "recipe":   { ... matches Recipe.to_dict() ... },
      "metadata": { "image": ..., "host": ..., "canonical_url": ..., "author": ... }
    }

The recipe section is shaped per the RecipeMD parser's JSON schema with
structured Ingredient/IngredientGroup/Amount entries. The metadata section
carries side-channel info that does not fit in Recipe but the SKILL.md uses
for normal-mode embedding (image, source attribution).

Usage:
    uv run scripts/extract.py <url>
    uv run scripts/extract.py --raw <url>      # emit raw scraper JSON instead
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# scripts/extract.py and scripts/recipemd.py (symlink) live in the same dir.
sys.path.insert(0, str(Path(__file__).parent))

from recipemd import (  # noqa: E402
    Amount,
    Ingredient,
    IngredientGroup,
    Recipe,
    RecipeMDError,
    parse_amount,
)

_AMOUNT_PREFIX = re.compile(
    r"""^(
        \d+\s+\d+\s*/\s*\d+        # mixed:    1 1/2
      | \d+\s*/\s*\d+              # fraction: 1/2
      | \d+\s+[¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]    # mixed vulgar: 1 ½
      | \d+(?:[.,]\d+)?            # decimal/integer: 1.5  1,5  3
      | [¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]            # bare vulgar: ½
    )(?:\s+(.*))?$""",
    re.VERBOSE,
)


def _split_freetext_ingredient(s: str) -> Ingredient:
    """Best-effort split of a free-text ingredient string into Amount + name.

    - "2 cups flour"   -> Amount(2, "cups"), name="flour"
    - "1/2 tsp salt"   -> Amount(0.5, "tsp"), name="salt"
    - "3 eggs"         -> Amount(3),         name="eggs"
    - "salt to taste"  -> Amount=None,       name="salt to taste"
    - "1 large onion"  -> Amount(1, "large"), name="onion"   # heuristic miss

    Last case is wrong-but-valid RecipeMD; Claude can refine.
    """
    s = (s or "").strip()
    if not s:
        return Ingredient(name="")
    m = _AMOUNT_PREFIX.match(s)
    if not m:
        return Ingredient(name=s)
    amount_text, remainder = m.group(1), (m.group(2) or "").strip()
    try:
        amt = parse_amount(amount_text)
    except RecipeMDError:
        return Ingredient(name=s)
    if amt.factor == 0 and amt.unit is None:
        return Ingredient(name=s)
    if not remainder:
        return Ingredient(amount=amt)
    parts = remainder.split(None, 1)
    if len(parts) == 1:
        return Ingredient(amount=Amount(factor=amt.factor), name=parts[0])
    unit_word, name_rest = parts
    return Ingredient(
        amount=Amount(factor=amt.factor, unit=unit_word),
        name=name_rest.strip(),
    )


def _parse_yields(value: object) -> list[Amount]:
    if not isinstance(value, str):
        return []
    out: list[Amount] = []
    for raw in value.split(","):
        part = raw.strip()
        if not part:
            continue
        try:
            out.append(parse_amount(part))
        except RecipeMDError:
            continue
    return out


def _collect_tags(scraper: dict) -> list[str]:
    tags: list[str] = []
    for key in ("cuisine", "category"):
        v = scraper.get(key)
        if isinstance(v, str) and v.strip():
            tags.append(v.strip())
    keywords = scraper.get("keywords")
    if isinstance(keywords, list):
        tags.extend(k.strip() for k in keywords if isinstance(k, str) and k.strip())
    elif isinstance(keywords, str):
        tags.extend(k.strip() for k in keywords.split(",") if k.strip())
    return list(dict.fromkeys(tags))


def _instructions(scraper: dict) -> str | None:
    text = scraper.get("instructions")
    if isinstance(text, str) and text.strip():
        return text.strip()
    steps = scraper.get("instructions_list")
    if isinstance(steps, list):
        cleaned = [s.strip() for s in steps if isinstance(s, str) and s.strip()]
        return "\n\n".join(cleaned) or None
    return None


def build_recipe(scraper: dict) -> Recipe:
    recipe = Recipe()
    recipe.title = (scraper.get("title") or "").strip()
    desc = scraper.get("description")
    if isinstance(desc, str) and desc.strip():
        recipe.description = desc.strip()
    recipe.yields = _parse_yields(scraper.get("yields"))
    recipe.tags = _collect_tags(scraper)

    for s in scraper.get("ingredients") or []:
        if isinstance(s, str):
            recipe.ingredients.append(_split_freetext_ingredient(s))

    for grp in scraper.get("ingredient_groups") or []:
        if not isinstance(grp, dict):
            continue
        title = (grp.get("purpose") or "").strip()
        if not title:
            continue
        ings = [
            _split_freetext_ingredient(s)
            for s in grp.get("ingredients") or []
            if isinstance(s, str)
        ]
        recipe.ingredient_groups.append(IngredientGroup(title=title, ingredients=ings))

    recipe.instructions = _instructions(scraper)
    return recipe


def _metadata(scraper: dict) -> dict:
    image = scraper.get("image")
    if isinstance(image, list):
        image = next((i for i in image if isinstance(i, str) and i), None)
    return {
        "image": image if isinstance(image, str) else None,
        "host": scraper.get("host"),
        "canonical_url": scraper.get("canonical_url"),
        "author": scraper.get("author"),
    }


def scrape(url: str) -> dict:
    try:
        from recipe_scrapers import scrape_me
    except ImportError:
        print(
            "recipe-scrapers is not available; run via uv: "
            "uv run scripts/extract.py <url>",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        scraper = scrape_me(url)
    except Exception as exc:  # noqa: BLE001 — surface any scraper failure
        print(f"Failed to scrape {url}: {exc}", file=sys.stderr)
        sys.exit(1)
    return scraper.to_json()


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Extract a recipe from a URL and emit canonical RecipeMD-shaped JSON.\n"
            "Errors are written to stderr; exit code is non-zero on failure."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("url", help="Recipe page URL to scrape")
    p.add_argument(
        "--raw",
        action="store_true",
        help="emit raw recipe-scrapers JSON instead of the canonical shape",
    )
    args = p.parse_args()

    raw = scrape(args.url)
    if args.raw:
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return
    output = {"recipe": build_recipe(raw).to_dict(), "metadata": _metadata(raw)}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
