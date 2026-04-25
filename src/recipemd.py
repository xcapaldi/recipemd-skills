"""RecipeMD parser and writer."""

from __future__ import annotations

from dataclasses import dataclass, field

__version__ = "0.1.0"


class RecipeMDError(ValueError):
    pass


@dataclass
class Amount:
    factor: str
    unit: str | None = None


@dataclass
class Yield:
    factor: str
    unit: str | None = None


@dataclass
class Ingredient:
    name: str
    amount: Amount | None = None
    link: str | None = None


@dataclass
class IngredientGroup:
    title: str
    ingredients: list[Ingredient] = field(default_factory=list)
    ingredient_groups: list[IngredientGroup] = field(default_factory=list)


@dataclass
class Recipe:
    title: str = ""
    description: str | None = None
    yields: list[Yield] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)
    ingredient_groups: list[IngredientGroup] = field(default_factory=list)
    instructions: str | None = None

    def to_dict(self) -> dict:
        return {}


def parse(text: str) -> Recipe:
    return Recipe()
