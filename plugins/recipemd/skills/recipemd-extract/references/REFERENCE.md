# RecipeMD Specification

This document describes the RecipeMD format (compatible with v2.4.0), refined from the [original specification](https://recipemd.org/specification.html). RecipeMD is a Markdown-based format for structuring recipes. All documents must conform to [CommonMark](https://commonmark.org).

## Example

```markdown
# Pico de Gallo

A fresh, chunky salsa that goes with everything.

*mexican, side, vegan*

**6 Servings, 350g**

---

- *4* roma tomatoes
- *1/2* white onion
- *1 bunch* cilantro
- *.5* limes
- jalapeño
- *1/4 tsp* salt

---

Dice tomatoes and onion. Finely chop cilantro. Mince jalapeño, removing
seeds for less heat. Combine in a bowl, squeeze lime over top and season
with salt. Let rest 10 minutes before serving.
```

## Data Types

### Recipe

A recipe contains:

- **Title** (required): first-level heading
- **Description** (optional): one or more paragraphs after the title
- **Tags** (optional, at most once): a paragraph consisting entirely of italicized text, containing a comma-separated list of strings (e.g. `*sauce, side, vegan*`)
- **Yields** (optional, at most once): a paragraph consisting entirely of bold text, containing a comma-separated list of amounts (e.g. `**6 Servings, 350g**`)
- A horizontal rule (`---`)
- **Ingredients** (required): zero or more ungrouped ingredients and zero or more ingredient groups
- A horizontal rule — may be omitted when there are no instructions
- **Instructions** (optional): everything after the second horizontal rule

Tags and yields may appear in either order.

When splitting comma-separated lists, a comma directly between two ASCII digits is not treated as a separator. This allows decimal commas in amounts (e.g. `**1,5 liters**`).

### Amount

An amount is a numeric value with an optional unit. The number may be expressed as:

- Integer: `3`
- Decimal (using `.` or `,`): `1.5`, `1,5`
- Proper fraction: `3/4`
- Improper fraction: `1 1/2`
- Unicode vulgar fraction: `½`, `1 ½`

The unit is everything following the number. If no number is present, the amount is empty.

### Ingredient

An ingredient has:

- An optional amount, written in italics at the start of the list item
- A name, which is all remaining text in the list item
- An optional link to a sub-recipe: if the name consists solely of an [inline link](https://spec.commonmark.org/0.28/#inline-link), the link text becomes the ingredient name and the link destination references a recipe for that ingredient

Examples:

```markdown
- *1.5* avocado
- *.5 teaspoon* salt
- lemon juice
- *200g* [salsa](salsa.md)
```

### Ingredient Group

An ingredient group organizes related ingredients under a heading. It contains:

- A title, specified as a heading (h2–h6)
- Zero or more ingredients (list items following the heading; items from all consecutive lists are collected)
- Zero or more child ingredient groups

A group is considered a child of a preceding group when its heading level is lower (e.g. `###` is a child of `##`). Groups at the same or higher heading level are siblings.

Example:

```markdown
## Sauce

- *2* tomatoes
- *1 clove* garlic

### Spice Mix

- *1 tsp* cumin
- *0.5 tsp* paprika

## Filling

- *200g* chicken
```
