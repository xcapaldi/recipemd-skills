# Export to Open Knowledge Format (OKF)

Optionally convert a RecipeMD recipe — or a whole collection — into an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF) bundle: markdown files with a YAML frontmatter block, linked together with normal markdown links. This makes recipe knowledge consumable by other AI agents/tools that speak OKF, without giving up RecipeMD as the canonical authoring format.

This is an **export-only, optional** capability. RecipeMD stays the source of truth; OKF is a derived view generated on request.

## Invocation

The user will typically say something like:

> Export this recipe as OKF
> Convert my recipe collection in `./recipes/` to an OKF bundle

## Step 1: Single recipe vs. collection

- **Single file** → single-document mode, prints one OKF document.
- **Directory of recipe files** → bundle mode, produces an `index.md` plus one OKF document per recipe.

## Step 2: Convert

Single document, to stdout:

```bash
uv run scripts/okf.py <file>
```

Bundle, to a directory:

```bash
uv run scripts/okf.py --bundle <recipes_dir> --out <out_dir> \
    --collection-title "My Recipes" --collection-description "..."
```

`--collection-title` / `--collection-description` are optional; the title defaults to the input directory name. Pass `--resource <url>` in single-document mode to record where an extracted recipe came from.

## Mapping: RecipeMD → OKF

| RecipeMD | OKF |
|---|---|
| — | `type: Recipe` (frontmatter, always set — the one field OKF requires) |
| Title | `title` (frontmatter) |
| Description, first sentence | `description` (frontmatter) — OKF's `description` is meant to be one summary sentence |
| Description, full text (if longer than one sentence) | `# Notes` section in the body |
| Tags | `tags` (frontmatter) |
| Yields | `yields` (frontmatter, custom field — not part of the core spec but allowed since producers may add extra fields) |
| Source URL (if known) | `resource` (frontmatter) |
| Ingredients / ingredient groups | `# Ingredients` section in the body, with nested groups as `##`, `###`, … |
| Instructions | `# Instructions` section in the body |

Linked sub-recipe ingredients (`[Fresh egg pasta](./fresh-egg-pasta.md)`) keep their relative link target unchanged. In bundle mode, every recipe is written under `<out_dir>/recipes/` using its **original filename**, so links between recipes that were already valid in the source collection stay valid in the bundle without rewriting.

A collection's `index.md` follows the spec's reserved-filename rule for directory listings: **no frontmatter**, just a `# <title>` heading, an optional description paragraph, and a `# Recipes` section with one bullet per recipe — `* [Title](./recipes/file.md) - <short description>` — matching the spec's example index format exactly.

## Step 3: Validate

`scripts/okf.py` is a one-way converter — there is no OKF→RecipeMD round trip and no separate validator. Confirm success by checking the script's exit code (0 = success, non-zero + `error: ...` on stderr = failure) and spot-checking the output against the mapping table above.

## Reference example

`examples/okf/` is the bundle produced by running `scripts/okf.py --bundle` over `examples/` recipe files. See `examples/okf/index.md` and `examples/okf/recipes/recipe.md` for the expected shape.
