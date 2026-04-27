# Meal Plan

Build a weekly meal plan as a RecipeMD document whose ingredients are links to existing recipes.

> **Status:** placeholder. Workflow not yet specified — flesh out when the user starts using this.

## Concept

A meal plan is a special RecipeMD document where:

- The **title** is the plan's name (e.g. "Week of 2026-04-27").
- The **description** captures any narrative (theme, dietary constraints).
- **Ingredient groups** correspond to days or meals (e.g. `## Monday`, `## Tuesday`).
- Each **ingredient** is a *linked* recipe — `[recipe title](./path/to/recipe.md)` — with no amount.
- **Instructions** can hold the cooking schedule, prep notes, or shopping order.

Because each ingredient is a link, downstream tooling (a future flatten capability) can resolve the linked recipes, gather their ingredients, and produce a consolidated grocery list.

## Workflow (sketch)

1. Ask the user for the week (or scope) and any constraints (dietary, time, leftovers).
2. Identify candidate recipes from the user's collection (filesystem if available; otherwise ask).
3. Compose the plan: assign recipes to days/meals as ingredient groups.
4. Write the plan as a RecipeMD file.
5. Validate with `scripts/recipemd.py <plan_file>`.

## Dependencies

- Filesystem access to read the user's recipe collection (Bash + Read in Claude Code).
- Without filesystem access, the workflow degrades to "user pastes recipe titles inline".
