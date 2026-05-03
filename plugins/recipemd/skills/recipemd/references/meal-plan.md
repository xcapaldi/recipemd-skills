# Meal Plan

Build a meal plan as a RecipeMD document whose ingredients are links to existing recipes. Each linked ingredient can carry a scaling factor or target yield, so the same plan can be fed straight into the **shopping-list** workflow to generate a grocery list.

## Invocation

The user will typically say something like:

> Plan meals for the week of `<date>`
> Make me a meal plan for next week, vegetarian, dinner only
> Build a weekly menu from my recipes in `./recipes/`

## Output shape

A RecipeMD document where:

- **Title**: `Week of YYYY-MM-DD`, `Meal plan YYYY-MM-DD`, or whatever the user requests.
- **Description** (optional): theme, scope, constraints — e.g. "Vegetarian dinners, 4 servings each, low-carb."
- **Tags** (optional): plan-level tags such as `*weekly, vegetarian*`.
- **No yields** (a plan doesn't yield a single quantity).
- **Ingredient groups** are organized hierarchically:
  - One-meal-per-day plan → one top-level group per day: `## Monday`, `## Tuesday`, ….
  - Multi-meal plan → one top-level group per day, with nested sub-groups per meal:

    ```markdown
    ## Monday

    ### Breakfast

    - *4* [Overnight Oats](./overnight-oats.md)

    ### Dinner

    - *4 servings* [Mushroom Risotto](./mushroom-risotto.md)
    ```

    Use nested groups (`### Breakfast`, `### Lunch`, `### Dinner`) — *not* flat day-meal headings like `## Monday — Dinner`. Nesting maps cleanly onto RecipeMD's `ingredient_groups` tree and lets the shopping-list workflow walk the structure naturally.
- **Each ingredient** is a single linked recipe:
  - `[Recipe Title](./path/to/recipe.md)` — load 1× as written.
  - `*<factor>* [Recipe Title](./path/to/recipe.md)` — scale the recipe by a bare factor (e.g. `*2*` doubles).
  - `*<n unit>* [Recipe Title](./path/to/recipe.md)` — scale to a target yield (e.g. `*6 servings*` for ratio scaling against the recipe's yield).
- **Instructions** (optional): prep schedule, batching notes, shopping reminder.

Filename: `meal-plan-YYYY-MM-DD.md` unless the user specifies otherwise.

## Step 1: Gather requirements

Ask the user for any of the following that aren't already clear:

- **Scope**: which dates? (week starting <date>, weekend, single day, etc.)
- **Meals per day**: dinner only, breakfast/lunch/dinner, etc.
- **Servings target**: how many people / portions per meal. Used to compute scaling factors.
- **Dietary constraints**: vegetarian, vegan, gluten-free, low-carb, allergies.
- **Time constraints**: quick weeknight meals, more time on weekends.
- **Variety preferences**: rotate proteins, avoid repeating cuisines.
- **Leftover handling**: cook double Monday → eat Tuesday lunch?
- **Recipe source**: existing collection (where?) or freeform / extract from URLs / suggest new?

Don't pepper the user with questions — pick the missing essentials, ask once, then proceed with sensible defaults for the rest.

## Step 2: Identify candidate recipes

Choose a path based on tool availability and what the user supplies.

### Path A — User has a recipe collection (filesystem)

Requires Bash and Read.

```bash
find <recipes_dir> -name '*.md' -type f
```

For each file, parse with `scripts/recipemd.py <file>` to read the structured fields. Useful for filtering:

- **`title`** for display.
- **`tags`** for dietary / cuisine / time filters (e.g. only recipes tagged `vegetarian`).
- **`yields`** for sizing decisions (a recipe that yields 4 with a target of 6 needs scaling 1.5×).

Build a candidate list: `[(title, path, tags, yields), ...]`.

### Path B — No collection, user wants suggestions

If the user says "just suggest things" (no files):

- Generate recipe titles + brief descriptions inline.
- Optionally chain into the **extract** workflow (`references/extract.md`) for each suggestion that maps to a known URL — write each to a file so the plan can link to it.
- Or keep the plan free-floating with link targets like `[Pasta Pomodoro](./pasta-pomodoro.md)` even though the file doesn't exist yet, and tell the user the recipes still need to be authored before the shopping-list workflow can resolve them.

### Path C — No filesystem access (chat / cowork)

Ask the user to paste recipe titles and any associated paths/URLs. Treat the resulting list as Path A's candidate list, but recognize the shopping-list workflow won't be able to resolve links automatically without filesystem/web access either.

## Step 3: Select and assign

For each meal slot in the scope:

1. **Filter** candidates by the user's constraints (tags, time, dietary).
2. **Pick** one recipe. Default rules:
   - Don't repeat a recipe within the plan unless the user wants leftovers.
   - Spread variety: alternate proteins, cuisines, cooking methods across the week.
   - Match time constraints to the day (quick weeknights, longer weekends if signaled).
3. **Determine the scaling factor** from the recipe's `yields` and the user's serving target:
   - Recipe yields 4, user wants 4 → no scale (`[Recipe](path.md)`).
   - Recipe yields 4, user wants 6 → scale 1.5 (`*1.5* [Recipe](path.md)`) or use target yield (`*6 servings* [Recipe](path.md)`); prefer target-yield form when units match because it survives recipe edits.
   - Recipe has no `yields` → no scale, optionally tell the user the recipe doesn't declare a yield so portions are best-effort.
4. **Leftovers**: if a recipe is meant to span two slots, assign it to both with the same link (the shopping-list workflow will dedup the resolved ingredients automatically — but make sure the scaling factor reflects the *total* servings needed, e.g. `*8 servings*` if you're feeding 4 across two meals).

## Step 4: Compose the document

```markdown
# Week of 2026-04-27

A vegetarian dinner plan for 4. Quick weeknight meals, more time Sunday.

*vegetarian, weekly*

---

## Monday

- *4 servings* [Mushroom Risotto](./mushroom-risotto.md)

## Tuesday

- *4 servings* [Roasted Veg Tacos](./veg-tacos.md)

## Wednesday

- *4 servings* [Lentil Soup](./lentil-soup.md)

## Thursday

- *4 servings* [Spinach Lasagna](./spinach-lasagna.md)

## Friday

- *4 servings* [Pizza Margherita](./pizza-margherita.md)

## Saturday

- *4 servings* [Chickpea Curry](./chickpea-curry.md)

## Sunday

- *8 servings* [Mushroom Wellington](./mushroom-wellington.md)

---

Sunday's wellington intentionally over-yields — leftover slices for Monday lunch.
Run the shopping-list workflow on this file to consolidate the week's groceries.
```

Notes:

- The first thematic break (`---`) separates the preamble (description, tags) from the ingredients, as required by RecipeMD.
- The second thematic break (`---`) before the instructions paragraph is optional; include it when there's prep/leftover narrative.
- Use relative paths (`./recipe.md` or `recipes/recipe.md`) so the plan moves cleanly with its recipe collection.

## Step 5: Write the file

Filename default: `meal-plan-YYYY-MM-DD.md` (using the start date of the scope, or today's date for an unscoped "this week" plan). Lowercase, hyphens, `.md` extension. Write to the user's chosen directory or the current working directory.

## Step 6: Validate

```bash
uv run scripts/recipemd.py <plan_file>
```

Round-trip through the parser. Fix any structural errors and retry until exit 0.

## Step 7: Hand off to shopping-list (optional)

After confirming the plan validates, offer the user:

> Want me to generate a shopping list from this plan?

If yes, switch to `references/shopping-list.md` and pass the plan file as the input. The shopping-list workflow will resolve every linked recipe, scale them by the factors you set in Step 3, dedup, and group by grocery section.

## Dependencies

- **Filesystem access** (Bash + Read) is needed to scan the user's collection (Path A) and to write the plan file. Without it, fall back to Path C — the resulting plan still validates, but linked recipes can't be resolved automatically.
- **WebFetch / extract workflow** is only needed if the user asks to populate the collection from URLs as part of planning.

## Reference example

`examples/meal-plan.md` is a worked example: a 7-day vegetarian-leaning plan for 4, with Sunday's recipe scaled to 6 servings to leave leftovers. Each day is an ingredient group containing a single linked recipe with a `*N servings*` target-yield prefix. See it for filename conventions, the preamble shape, and how to use the optional instructions paragraph for prep/leftover notes.
