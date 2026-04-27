# Shopping List

Build a consolidated shopping list from a base recipe (typically a meal plan, but any recipe with linked sub-recipes works). Resolves linked recipes, scales them, merges and dedups ingredients, then groups by grocery-store section. Output is itself a RecipeMD document.

## Invocation

The user will typically say something like:

> Make a shopping list from `<file>` [for week of `<date>`]

Or pass a meal plan file directly.

## Output shape

A RecipeMD document with:

- **Title**: `Shopping list YYYY-MM-DD` (use the user-provided date or today's date).
- **No description, tags, yields, or instructions.**
- **Ingredient groups** = grocery-store sections (produce, meat & seafood, dairy, pantry/dry goods, spices, frozen, bakery, beverages, other). Skip any section that ends up empty.
- Each group's ingredients are the deduplicated, summed (where possible) shopping items.

Filename: `shopping-list-YYYY-MM-DD.md` unless the user specifies otherwise.

## Step 1: Parse the base recipe

```bash
python scripts/recipemd.py <input_file>
```

Use the JSON output as the structured starting point. Capture the flat `ingredients` and recurse into `ingredient_groups` to gather every ingredient at every depth into a working list. Each entry carries `name`, `amount` (optional), `link` (optional).

## Step 2: Resolve linked sub-recipes

Walk each ingredient that has a `link`. The `link` is either:

- **A local path** (e.g. `./pasta.md`, `recipes/pasta.md`) — needs filesystem access (Bash + Read).
- **A URL** — needs WebFetch or the extract workflow.

For each linked entry:

1. **Load the sub-recipe.**
   - Local path: read the file, parse via `scripts/recipemd.py`.
   - URL: follow `references/extract.md` to extract a RecipeMD document (in normal mode is fine; we only need the structured ingredient list, not the prose). Save as a temporary file or hold in memory.
2. **Scale it.** The base ingredient's `amount` is the scale factor for the linked recipe.
   - `*2* [pasta](./pasta.md)` → scale `pasta.md` by 2.
   - `*6 servings* [pasta](./pasta.md)` → ratio-scale `pasta.md` to 6 servings (use `--scale "6 servings"`).
   - `[pasta](./pasta.md)` (no amount) → load at 1× as written.
   ```bash
   python scripts/recipemd.py --scale "<amount>" <sub_recipe_file>
   ```
3. **Recurse.** The sub-recipe may itself contain linked recipes (e.g. a curry recipe linking to `./homemade-curry-paste.md`). Apply the same resolve-and-scale step on its ingredients before merging.
4. **Replace the linked entry** in the working list with the *expanded* ingredients of the scaled sub-recipe. Drop the original link entry — it's now represented by its components.

**Cycle protection:** track a set of resolved file paths/URLs. If a link points back to one already in the set, drop it with a warning rather than recursing.

**Degraded paths:**

- No filesystem access for a local link → tell the user the link can't be resolved without Bash/Read; ask them to paste the linked recipe inline, or skip with a warning.
- URL with no WebFetch and no Bash → same: ask the user.

## Step 3: Deduplicate

Multiple recipes will overlap. Merge similar entries:

- **Normalize names** for comparison: lowercase, trim whitespace, drop common prep modifiers (`chopped`, `diced`, `minced`, `sliced`, `grated`, `crushed`, `fresh`, `dried` when redundant, `whole`, `large`, `medium`, `small`, etc.). `"Parsley"`, `"chopped parsley"`, `"parsley, chopped"` all normalize to `"parsley"`.
- **Merge entries** that share a normalized name. For the merged entry, choose the most natural display name (typically the unmodified base, e.g. `"parsley"`).
- **Sum amounts when units match** (`200 g flour` + `300 g flour` → `500 g flour`).
- **Keep mixed units when they don't** (`1 bunch parsley` + `1 cup parsley, chopped` → display as `1 bunch + 1 cup parsley`). Don't try to convert across units (cup ↔ bunch, mL ↔ g, etc.) — surface the mix and let the shopper decide.
- **Items without amounts** (just a name) merge into a single entry with no amount.

When in doubt, prefer NOT merging — under-merging is annoying, over-merging silently hides ingredients.

## Step 4: Categorize into grocery-store sections

Assign each deduplicated ingredient to one of:

- **Produce** — fresh fruit, vegetables, herbs
- **Meat & Seafood** — fresh/frozen proteins
- **Dairy & Eggs** — milk, cheese, yogurt, butter, eggs
- **Pantry** — flour, sugar, rice, pasta, canned goods, oils, vinegars, condiments, broths
- **Spices** — dried spices, salt, pepper, dried herbs
- **Frozen** — frozen vegetables, ice, frozen meals (when distinct from frozen meat)
- **Bakery** — bread, tortillas, pastries
- **Beverages** — wine, juice, coffee, tea, soft drinks
- **Other** — anything that doesn't fit above; if the section ends up holding only one or two odd items, leave them here rather than inventing extra sections

Use judgment. The goal is "in the order the shopper walks the store," not perfect taxonomy. Skip empty sections in the output.

## Step 5: Compose the RecipeMD document

```markdown
# Shopping list YYYY-MM-DD

---

## Produce

- *2* yellow onions
- *1 bunch* parsley
- ...

## Pantry

- *500 g* flour
- ...

## Dairy & Eggs

- *1 dozen* eggs
- ...
```

Notes:

- Use the standard RecipeMD ingredient syntax (`*amount unit* name`) for every entry.
- For mixed-unit merges from Step 3, write `*1 bunch + 1 cup* parsley` or two separate entries — pick whichever is clearer for that specific item.
- For amount-less entries, just the name: `- salt`.
- The first thematic break (`---`) after the title is required by the format. Put it before the first `## Section` heading.
- No second thematic break, no instructions section.

## Step 6: Validate

```bash
python scripts/recipemd.py shopping-list-YYYY-MM-DD.md
```

Round-trip through the parser. Fix any errors and retry until exit 0. Then report success to the user with the file path.

## Reference example

`examples/shopping-list.md` is a worked example consolidating the week from `examples/meal-plan.md`. Note the format: title with date, no description / tags / yields / instructions, ingredient groups named after grocery sections, deduplicated quantities (whole milk consolidated across risotto + Bolognese into a single `*1.25 L*` entry), and a brief trailing note explaining the leftover sizing. Reproduce that shape.
