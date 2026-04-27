---
name: recipemd
description: Read, write, scale, extract, and plan with RecipeMD recipes — a Markdown-based recipe format
license: MIT
allowed-tools: Bash, Read, Write, WebFetch
metadata:
    author: Xavier Capaldi
    version: 0.1.0
---

# RecipeMD

Tools for working with [RecipeMD](https://recipemd.org) — a Markdown-based recipe format. The full format spec is in `references/REFERENCE.md`; read it whenever writing or fixing a RecipeMD document.

## Capabilities

| Task | Path |
|---|---|
| **Parse / validate** a RecipeMD file → JSON | `scripts/recipemd.py <file>` |
| **Scale** a recipe by a factor or to a target yield | `scripts/recipemd.py --scale <amount> <file>` |
| **Extract** a recipe from a URL or page content | read `references/extract.md` and follow that workflow |
| **Plan** weekly meals as a recipe-of-recipes | read `references/meal-plan.md` and follow that workflow |
| **Shopping list** — consolidate ingredients from a recipe (or meal plan), resolve linked sub-recipes, dedup, group by store section | read `references/shopping-list.md` and follow that workflow |

Pick the row that matches the user's request. For parse/scale, run the script directly. For extract/meal-plan, read the corresponding reference file first — it contains the step-by-step workflow.

## Parse / validate

```bash
python scripts/recipemd.py <file>             # plain Python
uv run python scripts/recipemd.py <file>      # with dependency lock
```

- Exit 0 + JSON on stdout → valid. Print or use the parsed structure.
- Exit 1 + `error: ...` on stderr → invalid. Read the error, identify the structural problem, fix the document, re-run. Repeat until exit 0.

Useful flags:

- `--frontmatter` — strip a leading YAML (`---`) or TOML (`+++`) frontmatter block before parsing.
- `--indent N` — JSON indent (default 2).

## Scale

```bash
python scripts/recipemd.py --scale 2 <file>            # double everything
python scripts/recipemd.py --scale 0.5 <file>          # halve everything
python scripts/recipemd.py --scale "6 servings" <file> # ratio-scale to target yield
```

`--scale FACTOR` (bare number) multiplies all yields and ingredient amounts. `--scale "N unit"` finds a yield with matching unit and applies the corresponding ratio. Unmatched unit → error. Zero factor → error.

## Conventions

- **Single source of truth for quantities is the structured ingredient list.** When generating or rewriting recipe body text (description, instructions), avoid absolute quantity references that duplicate the ingredient list — they break under scaling. See `references/extract.md` § "Inline quantities in body text" for the rewrite rules.
- **`scripts/recipemd.py` is the validator.** Any RecipeMD output you produce should round-trip through it before you report success.

## Examples

`examples/` holds reference outputs you can use as targets:

- `examples/recipe.md` — a thorough single recipe (preamble + tags + multi-yield + ingredient groups + linked sub-recipe + multi-paragraph instructions).
- `examples/meal-plan.md` — a week's meal plan as a recipe-of-recipes.
- `examples/shopping-list.md` — the consolidated grocery list derived from that meal plan.
