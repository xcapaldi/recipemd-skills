# recipemd-skills

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Agent Skills](https://img.shields.io/badge/agent--skills-compliant-blue)](https://agentskills.io/home)

A Claude plugin for working with recipes in the [RecipeMD](https://recipemd.org) format. Parse, scale, extract from URLs, plan meals, and consolidate shopping lists — all from one skill that works across Claude Code, Claude Cowork, and Claude Chat (with environment-dependent capabilities).

The skill conforms to the [Agent Skills specification](https://agentskills.io/home) and is validated against it on every commit.

This README is itself a valid RecipeMD document — drop it into the parser and it round-trips cleanly.

*Claude, RecipeMD, recipe, skill, plugin*

**1 plugin, 1 skill**

---

## Workflows

- parse / validate — `scripts/recipemd.py FILE`
- scale by factor or target yield — `scripts/recipemd.py --scale AMOUNT FILE`
- extract from URL or HTML — see `references/extract.md`
- plan weekly meals as a recipe-of-recipes — see `references/meal-plan.md`
- shopping list from a recipe or meal plan — see `references/shopping-list.md`

## Examples

- `examples/recipe.md` — thorough single recipe
- `examples/meal-plan.md` — week of meals as a recipe-of-recipes
- `examples/shopping-list.md` — consolidated grocery list

---

## What is RecipeMD?

[RecipeMD](https://recipemd.org/specification.html) is a Markdown-based format for writing recipes. A recipe file is plain Markdown with a defined structure:

```markdown
# Carbonara

A classic Roman pasta.

*Italian, pasta*

**2 servings**

---

- *200 g* spaghetti
- *100 g* guanciale
- *2* eggs
- *50 g* Pecorino Romano

---

Boil pasta. Render guanciale. Whisk eggs with cheese and pepper. Toss together off the heat.
```

Three sections divided by `---` thematic breaks:

| Section | Content |
|---|---|
| Preamble | H1 title, optional description, optional *tags* (italic), optional **yields** (bold) |
| Ingredients | Unordered lists; H2+ headings introduce named ingredient groups (which can nest) |
| Instructions | Free-form Markdown |

Amounts are wrapped in emphasis: `*2 tbsp*`. Numbers can be integers (`3`), decimals (`1.5`), fractions (`1/2`), improper fractions (`1 1/2`), or Unicode vulgar fractions (`½ ¼ ¾`).

## Install via skills CLI

The [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI installs skills from any Git repo. These skills have only been tested with Anthropic models.

```
npx skills@latest add xcapaldi/recipemd-skills/recipemd
```

## Install in Claude Code

Claude Code has a plugin system that pulls skills directly from a Git repo or marketplace. Full docs: <https://code.claude.com/docs/en/discover-plugins>.

Add this repo as a marketplace, then install the plugin:

```text
/plugin marketplace add xcapaldi/recipemd-skills
/plugin install recipemd
```

Once installed, ask anything RecipeMD-related ("parse this file", "extract a recipe from this URL", "plan vegetarian dinners for next week", "make a shopping list from `meal-plan.md`") and the skill will trigger.

## Install manually for Claude Chat or Cowork

Both Claude Chat and Cowork accept `.skill` bundles uploaded through their skills UI.

1. Grab the latest bundle from [Releases](https://github.com/xcapaldi/recipemd-skills/releases) — download `recipemd.skill`.
2. Open the skills panel in Claude Chat or Cowork and upload the `.skill` file.
3. Enable it for your conversation.

Build the bundle yourself if you'd rather:

```bash
cd plugins/recipemd/skills && zip -r recipemd.skill recipemd
```

## Capabilities by tool

The skill works in all three environments, but what it can *do* depends on which tools are available.

| Capability | Claude Code | Claude Cowork | Claude Chat |
|---|---|---|---|
| Parse / validate | ✅ runs `recipemd.py` | ✅ runs `recipemd.py` | ✅ runs `recipemd.py` |
| Scale | ✅ runs `recipemd.py --scale` | ✅ runs `recipemd.py --scale` | ✅ runs `recipemd.py --scale` |
| Extract from URL | ✅ runs `extract.py` (via uv/pipx) | WebFetch, or page access via Chrome extension | ✅ WebFetch |
| Read recipe files from disk | ✅ filesystem | ✅ when you grant the recipe directory | ❌ user pastes content inline |
| Build meal plans | ✅ scans collection | ✅ scans granted directory | ❌ user pastes recipe titles |
| Generate shopping list | ✅ resolves linked recipes recursively | ✅ resolves links in granted directory | ❌ links can't be resolved |

In short:

- **Claude Code** — full capability. The shell runs both bundled scripts directly, including `extract.py` (which pulls `recipe-scrapers` via uv/pipx). Best for batch work across many recipe files.
- **Claude Cowork** — runs the parser/scaler in its Python environment (only depends on `markdown-it-py`). Filesystem access (when you grant a recipe directory) lets meal-plan and shopping-list resolve linked recipes. URL extraction uses WebFetch or — better — the Chrome extension that lets Cowork read the page directly.
- **Claude Chat** — runs the parser/scaler in its Python environment as well. URL extraction uses WebFetch (best-effort scrape). Multi-file workflows degrade to "user pastes the recipes inline" since there's no filesystem access.

## Development

```bash
git clone https://github.com/xcapaldi/recipemd-skills
cd recipemd-skills
uv sync                        # install deps
uv run pytest                  # tests
uv run ruff check .            # lint
pre-commit install             # git hook
```

The skill source of truth lives at `plugins/recipemd/skills/recipemd/`. Tests cover the parser (`test_recipemd.py`), CLI (`test_cli.py`), and extract mapping (`test_extract.py`). The pre-commit hook validates the skill structure against the [Agent Skills specification](https://agentskills.io/home).

Releasing: tag `recipemd/v<version>` (e.g. `recipemd/v0.2.0`). The release workflow validates that `plugin.json` and `SKILL.md` versions match the tag, builds `recipemd.skill`, and creates a GitHub release.

## License

MIT — see [LICENSE](./LICENSE).
