# Extract Recipe

Extract a recipe from a URL and convert it to [RecipeMD](https://recipemd.org) format.

Two modes:

- **normal** — copy verbatim with image and a source attribution block
- **cleanroom** — rewrite description and instructions in neutral tone to avoid attribution issues; ingredients (factual data) are kept as-is

## Invocation

The user will typically say something like:

> Extract the recipe at `<url>` [in cleanroom mode]

Default is **normal** unless the user explicitly requests cleanroom.

## Step 1: Detect runtime

This skill has two extraction paths. Choose based on tool availability:

- **Scripted path (Step 2A)** — preferred. Requires Bash and one of `uv`, `pipx`, or a Python with `recipe-scrapers` installed.
- **Manual path (Step 2B)** — fallback. Used when Bash isn't available (e.g., Claude Chat or Cowork) or no Python runner is on PATH.

Probe by attempting to run a runner — for example:

```bash
command -v uv || command -v pipx || command -v python3
```

If Bash is unavailable or none of those resolve, take the manual path.

## Step 2A: Scripted extraction

Run the bundled scraper. Pick whichever runner is available:

```bash
uv run scripts/extract.py <url>          # auto-installs deps
pipx run scripts/extract.py <url>        # auto-installs deps
python scripts/extract.py <url>          # requires: pip install recipe-scrapers
```

On success the script prints a JSON object to **stdout**. On failure it writes a human-readable message to **stderr** and exits non-zero. If the script fails for any reason, fall back to **Step 2B** and tell the user.

The output is shaped as:

```json
{
  "recipe":   { /* canonical RecipeMD shape — same as recipemd parser output */ },
  "metadata": {
    "image": "...", "host": "...", "canonical_url": "...", "author": "..."
  }
}
```

`recipe` matches the schema produced by the `recipemd` parser: `title`, `description`, `yields` (list of `{factor, unit}`), `tags`, `ingredients` (list of `{name, amount, link}`), `ingredient_groups` (nested), `instructions`. Use it as the structured starting point for the document.

`metadata` carries fields that don't fit in `recipe` but the modes below use (image embedding, source attribution).

**Note**: the script uses a heuristic to split free-text ingredient strings (`"2 cups flour"` → `Amount(2, "cups")` + `name="flour"`). It gets common cases right; phrases like `"1 large onion"` may be mis-split (`"large"` treated as unit). When that happens, refine the ingredient before writing — the canonical shape lets you spot-check easily.

Pass `--raw` to bypass the mapping and get the raw recipe-scrapers JSON instead (useful if you want to do all the structuring yourself).

## Step 2B: Manual extraction (fallback)

When the scripted path is unavailable:

1. Use the **WebFetch** tool to retrieve the page.
2. Look for structured data first — most recipe sites embed JSON-LD with `@type: "Recipe"` in a `<script type="application/ld+json">` block. That gives the cleanest source for `name`, `description`, `recipeIngredient`, `recipeInstructions`, `recipeYield`, `image`, `author`, etc.
3. If no JSON-LD is present, infer the same fields from the rendered HTML/text (heading, ingredient list, step list).
4. **Tell the user explicitly** that you are extracting manually and the result may contain errors — fields may be missed, lists may be merged, or formatting may drift.

## Step 3: Convert to RecipeMD

Use the scraped/inferred data and the RecipeMD specification in `references/REFERENCE.md` to produce a valid RecipeMD document.

### Normal mode

- Keep title, description, ingredients, and instructions **verbatim**.
- If `image` is present, embed it immediately after the title:
  ```markdown
  ![Recipe photo](<image_url>)
  ```
- Add a source blockquote in the description:
  ```markdown
  > **Source:** [<title>](<canonical_url>) via <host>
  ```
- After writing the file, **warn the user**:
  > Attribution: This recipe was copied verbatim from `<canonical_url>`. Make sure you have the right to store and share this content before distributing it.

### Cleanroom mode

The goal is a clean, independent document conveying the same culinary information without copying the original author's expression.

- Keep the **title** as-is (titles are not copyrightable).
- **Rewrite the description** in a neutral, factual, third-person tone. Remove personal anecdotes, first-person voice, brand references, and phrasing that echoes the source. Describe what the dish is and why someone would make it.
- Keep **ingredients and amounts exactly as scraped** — quantities and ingredient names are factual.
- **Rewrite the instructions** in clear, neutral imperative language ("Dice the onion." not "I like to dice my onion really finely!"). Each step conveys the cooking action only.
- Do **not** include the source image.
- Do **not** include a source attribution block.
- If the user has provided an existing recipe collection and asks for tone matching, you may align with their patterns.

### Inline quantities in body text (applies to both modes)

If the description or instructions reference an absolute quantity that is also captured in the structured ingredients list, **rewrite the inline reference to be relative or generic**. The structured ingredient list is the single source of truth for quantities; inline duplicates become inconsistent the moment the user scales the recipe.

| Replace | With |
|---|---|
| "add 2 cups flour" | "add the flour" or "add half the flour" |
| "whisk in 3 eggs" | "whisk in the eggs" or "whisk in 1/3 of the eggs" |
| "sprinkle 1 tsp cinnamon" | "sprinkle the cinnamon" |

Use **generic** ("the flour") when the step calls for the full ingredient amount, **fractional** ("half the flour", "a third of the eggs") when only part is used. Keep absolute quantities only when they refer to something *not* in the ingredient list (oven temperatures, timing, container sizes — e.g. "bake at 180°C for 25 minutes in a 9-inch pan" stays verbatim).

This is the one acceptable deviation from "verbatim" in normal mode — preserves correctness under scaling without changing the recipe's voice.

## Step 4: Write output file

Derive a filename from the title: lowercase, spaces replaced with hyphens, non-alphanumeric characters stripped, `.md` extension. Example: `pico-de-gallo.md`.

Write the RecipeMD content to that file in the current working directory unless the user specifies a path.

## Step 5: Validate

Run the bundled RecipeMD parser to confirm the output is structurally valid:

```bash
python scripts/recipemd.py <output_file>
```

(Prefer `uv run python scripts/recipemd.py <output_file>` if `uv` is available — it ensures `markdown-it-py` is on the path.)

Expected outcomes:

- **Exit 0 + JSON on stdout** → valid. Report success to the user.
- **Exit 1 + `error: ...` on stderr** → invalid. Read the error, identify the structural problem in the document, fix it, re-run validation. Repeat until exit 0.

If running scripts isn't possible (manual path with no Bash), tell the user that automatic validation could not run and recommend they re-run this skill in a Claude Code session, or paste the document into a session where the parser is available.

## Reference example

`examples/recipe.md` shows what a thorough RecipeMD document looks like when produced by this workflow: full preamble (description, tags, multi-yield), two ingredient groups, a linked sub-recipe ingredient (`[Fresh egg pasta](./fresh-egg-pasta.md)`), and multi-paragraph instructions. Use it as a target shape when in doubt about formatting choices.
