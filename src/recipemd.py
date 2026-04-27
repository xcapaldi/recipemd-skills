"""RecipeMD parser."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from markdown_it.token import Token

__version__ = "0.1.0"


class RecipeMDError(ValueError):
    pass


@dataclass
class Amount:
    factor: float
    unit: str | None = None

    def to_dict(self) -> dict:
        return {"factor": _format_factor(self.factor), "unit": self.unit}

    def scale(self, factor: float) -> None:
        self.factor *= factor


@dataclass
class Ingredient:
    name: str
    amount: Amount | None = None
    link: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "amount": self.amount.to_dict() if self.amount else None,
            "link": self.link,
        }

    def scale(self, factor: float) -> None:
        if self.amount is not None:
            self.amount.scale(factor)


@dataclass
class IngredientGroup:
    title: str
    ingredients: list[Ingredient] = field(default_factory=list)
    ingredient_groups: list[IngredientGroup] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "ingredient_groups": [g.to_dict() for g in self.ingredient_groups],
        }

    def scale(self, factor: float) -> None:
        for ing in self.ingredients:
            ing.scale(factor)
        for sub in self.ingredient_groups:
            sub.scale(factor)


@dataclass
class Recipe:
    title: str = ""
    description: str | None = None
    yields: list[Amount] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)
    ingredient_groups: list[IngredientGroup] = field(default_factory=list)
    instructions: str | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "yields": [y.to_dict() for y in self.yields],
            "tags": list(self.tags),
            "ingredients": [i.to_dict() for i in self.ingredients],
            "ingredient_groups": [g.to_dict() for g in self.ingredient_groups],
            "instructions": self.instructions,
        }

    def scale(self, factor: float) -> None:
        for y in self.yields:
            y.scale(factor)
        for ing in self.ingredients:
            ing.scale(factor)
        for g in self.ingredient_groups:
            g.scale(factor)

    def scale_for_yield(self, desired: Amount) -> None:
        for y in self.yields:
            if y.unit is None and desired.unit is None:
                self.scale(desired.factor / y.factor)
                return
            if y.unit is not None and desired.unit == y.unit:
                self.scale(desired.factor / y.factor)
                return
        if desired.unit is None:
            self.scale(desired.factor)
            return
        raise RecipeMDError(f"no matching yield unit: {desired.unit!r}")


def _format_factor(f: float, rounding: int = 3) -> str:
    if rounding < 0:
        return repr(f)
    rounded = round(f, rounding)
    s = f"{rounded:.{rounding}f}"
    if rounding > 0:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _strip_frontmatter(text: str) -> str:
    if len(text) < 3:
        return text
    if text.startswith("---"):
        fence = "---"
    elif text.startswith("+++"):
        fence = "+++"
    else:
        return text
    nl = text.find("\n")
    if nl < 0:
        return text
    if text[:nl].strip() != fence:
        return text
    rest = text[nl + 1 :]
    while rest:
        line_end = rest.find("\n")
        line = rest if line_end < 0 else rest[:line_end]
        if line.strip() == fence:
            return "" if line_end < 0 else rest[line_end + 1 :]
        if line_end < 0:
            break
        rest = rest[line_end + 1 :]
    return text


_VULGAR_FRACTIONS = {
    "¼": 1 / 4, "½": 1 / 2, "¾": 3 / 4,
    "⅐": 1 / 7, "⅑": 1 / 9, "⅒": 1 / 10,
    "⅓": 1 / 3, "⅔": 2 / 3,
    "⅕": 1 / 5, "⅖": 2 / 5, "⅗": 3 / 5, "⅘": 4 / 5,
    "⅙": 1 / 6, "⅚": 5 / 6,
    "⅛": 1 / 8, "⅜": 3 / 8, "⅝": 5 / 8, "⅞": 7 / 8,
}  # fmt: skip


def _try_improper_fraction(s: str) -> tuple[float | None, str]:
    """Match 'a b/c' (e.g. '1 1/2')."""
    m = re.match(r"^(\d+)\s+(\d+)\s*/\s*(\d+)", s)
    if not m:
        return None, s
    whole, num, denom = float(m.group(1)), float(m.group(2)), float(m.group(3))
    if denom == 0:
        return None, s
    return whole + num / denom, s[m.end() :]


def _try_improper_vulgar(s: str) -> tuple[float | None, str]:
    """Match 'a ½' (whole number followed by a vulgar fraction)."""
    m = re.match(r"^(\d+)\s+", s)
    if not m:
        return None, s
    rest = s[m.end() :]
    if not rest or rest[0] not in _VULGAR_FRACTIONS:
        return None, s
    return float(m.group(1)) + _VULGAR_FRACTIONS[rest[0]], rest[1:]


def _try_proper_fraction(s: str) -> tuple[float | None, str]:
    """Match 'a/b' (e.g. '1/2')."""
    m = re.match(r"^(\d+)\s*/\s*(\d+)", s)
    if not m:
        return None, s
    num, denom = float(m.group(1)), float(m.group(2))
    if denom == 0:
        return None, s
    return num / denom, s[m.end() :]


def _try_vulgar_alone(s: str) -> tuple[float | None, str]:
    if not s or s[0] not in _VULGAR_FRACTIONS:
        return None, s
    return _VULGAR_FRACTIONS[s[0]], s[1:]


def _try_decimal(s: str) -> tuple[float | None, str]:
    """Match 'a.b', 'a,b', or '.b' (decimal-comma supported)."""
    m = re.match(r"^(\d*)[.,](\d+)", s)
    if not m:
        return None, s
    int_part = m.group(1) or "0"
    return float(f"{int_part}.{m.group(2)}"), s[m.end() :]


def _try_integer(s: str) -> tuple[float | None, str]:
    m = re.match(r"^(\d+)", s)
    if not m:
        return None, s
    return float(m.group(1)), s[m.end() :]


_AMOUNT_PARSERS = (
    _try_improper_fraction,
    _try_improper_vulgar,
    _try_proper_fraction,
    _try_vulgar_alone,
    _try_decimal,
    _try_integer,
)


def parse_amount(s: str) -> Amount:
    s = s.lstrip()
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:].lstrip()

    factor: float | None = None
    remaining = s
    for try_parse in _AMOUNT_PARSERS:
        factor, remaining = try_parse(s)
        if factor is not None:
            break

    unit = remaining.strip() or None
    if factor is None:
        if unit:
            raise RecipeMDError(f"unit without value: {s!r}")
        return Amount(factor=0.0)
    return Amount(factor=-factor if negative else factor, unit=unit)


def _split_list(s: str) -> list[str]:
    """Split on commas, but skip decimal-commas (digit,digit)."""
    parts: list[str] = []
    start = 0
    search = 0
    while True:
        idx = s.find(",", search)
        if idx == -1:
            break
        if 0 < idx < len(s) - 1 and s[idx - 1].isdigit() and s[idx + 1].isdigit():
            search = idx + 1
            continue
        chunk = s[start:idx].strip()
        if chunk:
            parts.append(chunk)
        start = idx + 1
        search = start
    final = s[start:].strip()
    if final:
        parts.append(final)
    return parts


def _parse_tags(s: str) -> list[str]:
    return _split_list(s)


def _parse_yields(s: str) -> list[Amount]:
    return [parse_amount(item) for item in _split_list(s)]


def _is_only_emphasis(inline: Token, kind: str) -> tuple[str, bool]:
    """If inline contains exactly one ``em``/``strong`` span and nothing else at
    the top level (ignoring empty text nodes), return (inner_text, True).
    Otherwise (\"\", False).
    """
    children = [
        c for c in (inline.children or [])
        if not (c.type == "text" and not c.content.strip())
    ]
    if len(children) < 2:
        return "", False
    open_tag, close_tag = f"{kind}_open", f"{kind}_close"
    if children[0].type != open_tag or children[-1].type != close_tag:
        return "", False

    level = 0
    for idx, child in enumerate(children):
        if child.type.endswith("_open"):
            level += 1
        elif child.type.endswith("_close"):
            level -= 1
        if level == 0 and idx < len(children) - 1:
            return "", False

    parts = [c.content for c in children[1:-1] if c.type in ("text", "code_inline")]
    return "".join(parts).strip(), True


def _inline_plain_text(token: Token) -> str:
    """Extract plain text from a markdown-it-py inline token: concatenate text
    and code-span content verbatim, recurse through emphasis/link wrappers
    without inserting separators, and trim the final result once.
    """
    if not token.children:
        return token.content.strip()
    stack: list[list[str]] = [[]]
    for child in token.children:
        t = child.type
        if t in ("text", "code_inline"):
            stack[-1].append(child.content)
        elif t.endswith("_open"):
            stack.append([])
        elif t.endswith("_close"):
            inner = "".join(stack.pop()).strip()
            stack[-1].append(inner)
        elif t in ("softbreak", "hardbreak"):
            stack[-1].append(" ")
        elif child.content:
            stack[-1].append(child.content)
    return "".join(stack[0]).strip()


def _find_block_close(tokens: list[Token], open_idx: int) -> int:
    open_tok = tokens[open_idx]
    close_type = open_tok.type[: -len("_open")] + "_close"
    target_lvl = open_tok.level
    for j in range(open_idx + 1, len(tokens)):
        if tokens[j].type == close_type and tokens[j].level == target_lvl:
            return j
    return -1


def _collect_item_blocks(
    tokens: list[Token], item_open_idx: int
) -> tuple[int, list[tuple[int, int]]]:
    """Return ``(item_close_idx, [(open_idx, close_idx), ...])`` for the direct
    child blocks of the list item starting at ``item_open_idx``. Single-token
    blocks (code_block, fence, hr, html_block) use the same idx for open/close.
    """
    item_lvl = tokens[item_open_idx].level
    inner_lvl = item_lvl + 1
    blocks: list[tuple[int, int]] = []
    i = item_open_idx + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "list_item_close" and tok.level == item_lvl:
            return i, blocks
        if tok.level == inner_lvl:
            if tok.type.endswith("_open"):
                close_idx = _find_block_close(tokens, i)
                blocks.append((i, close_idx))
                i = close_idx + 1
                continue
            blocks.append((i, i))
        i += 1
    return i, blocks


def _filter_padding(children: list[Token]) -> list[Token]:
    return [c for c in children if not (c.type == "text" and not c.content.strip())]


def _extract_amount(inline: Token) -> tuple[Amount | None, list[Token]]:
    """If the inline starts with a single em span, parse it as an [Amount] and
    return (amount, children_after_em). Otherwise return (None, filtered_children).
    """
    children = _filter_padding(inline.children or [])
    if not children or children[0].type != "em_open":
        return None, children
    depth = 0
    close_at = -1
    for k, c in enumerate(children):
        if c.type == "em_open":
            depth += 1
        elif c.type == "em_close":
            depth -= 1
            if depth == 0:
                close_at = k
                break
    if close_at < 1:
        return None, children
    inner_text = "".join(
        c.content for c in children[1:close_at]
        if c.type in ("text", "code_inline")
    ).strip()
    return parse_amount(inner_text), children[close_at + 1 :]


def _find_single_link(children: list[Token]) -> tuple[str, str] | None:
    """If ``children`` consist of exactly one link surrounded only by whitespace
    text, return ``(link_text, href)``. Otherwise None.
    """
    href: str | None = None
    inside = False
    text_parts: list[str] = []
    for c in children:
        if c.type == "link_open":
            if href is not None:
                return None
            href = c.attrs.get("href", "")
            inside = True
        elif c.type == "link_close":
            inside = False
        elif inside:
            if c.type == "text":
                text_parts.append(c.content)
        elif c.type == "text":
            if c.content.strip():
                return None
        else:
            return None
    if href is None:
        return None
    return "".join(text_parts).strip(), href


def _inline_sequence_text(children: list[Token]) -> str:
    """Render a sequence of inline children back to text, preserving emphasis
    markers (``*x*``, ``**x**``) and link syntax (``[t](u)``).
    """
    parts: list[str] = []
    i = 0
    while i < len(children):
        c = children[i]
        t = c.type
        if t in ("text", "code_inline"):
            parts.append(c.content)
        elif t in ("softbreak", "hardbreak"):
            parts.append("\n")
        elif t.endswith("_open"):
            tag = t[: -len("_open")]
            close_at = -1
            depth = 0
            for k in range(i, len(children)):
                if children[k].type == t:
                    depth += 1
                elif children[k].type == tag + "_close":
                    depth -= 1
                    if depth == 0:
                        close_at = k
                        break
            if close_at < 0:
                i += 1
                continue
            inner_plain = "".join(
                cc.content for cc in children[i + 1 : close_at]
                if cc.type in ("text", "code_inline")
            ).strip()
            if tag == "em":
                parts.append(f"*{inner_plain}*")
            elif tag == "strong":
                parts.append(f"**{inner_plain}**")
            elif tag == "link":
                parts.append(f"[{inner_plain}]({c.attrs.get('href', '')})")
            else:
                parts.append(inner_plain)
            i = close_at + 1
            continue
        i += 1
    return "".join(parts)


_LIST_ITEM_INDENT = "  "


def _block_separator(
    prev_end_line: int, curr_start_line: int, source_lines: list[str]
) -> str:
    if curr_start_line <= prev_end_line:
        return "\n"
    blank_idx = prev_end_line
    blank = source_lines[blank_idx] if 0 <= blank_idx < len(source_lines) else ""
    return "\n" + blank + "\n" + _LIST_ITEM_INDENT


def _block_raw(tokens: list[Token], open_idx: int, source_lines: list[str]) -> str:
    tok = tokens[open_idx]
    if tok.type == "paragraph_open":
        return tokens[open_idx + 1].content
    if tok.map is None:
        return tok.content
    start, end = tok.map
    return "\n".join(source_lines[start:end]).rstrip("\n")


def _parse_ingredient_item(
    tokens: list[Token], item_open_idx: int, source_lines: list[str]
) -> tuple[int, Ingredient]:
    item_close_idx, blocks = _collect_item_blocks(tokens, item_open_idx)
    if not blocks:
        raise RecipeMDError("ingredient must have a name")

    first_open_idx, _ = blocks[0]
    first_open = tokens[first_open_idx]
    is_only_block = len(blocks) == 1

    amount: Amount | None = None
    link: str | None = None
    name = ""

    if first_open.type == "paragraph_open":
        inline = tokens[first_open_idx + 1]
        amount, after_amount = _extract_amount(inline)
        link_pair = _find_single_link(after_amount)
        if is_only_block and link_pair is not None:
            name, link = link_pair
        elif amount is not None:
            name = _inline_sequence_text(after_amount).strip()
        else:
            name = inline.content.strip()
    else:
        name = _block_raw(tokens, first_open_idx, source_lines)

    prev_open_idx = first_open_idx
    for next_open_idx, _ in blocks[1:]:
        prev_end = tokens[prev_open_idx].map[1] if tokens[prev_open_idx].map else 0
        curr_start = tokens[next_open_idx].map[0] if tokens[next_open_idx].map else 0
        sep = _block_separator(prev_end, curr_start, source_lines)
        name += sep + _block_raw(tokens, next_open_idx, source_lines)
        prev_open_idx = next_open_idx

    name = name.strip()
    if not name:
        raise RecipeMDError("ingredient must have a name")

    return item_close_idx + 1, Ingredient(name=name, amount=amount, link=link)


def _parse_ingredient_list(
    tokens: list[Token], list_open_idx: int, source_lines: list[str]
) -> tuple[int, list[Ingredient]]:
    list_lvl = tokens[list_open_idx].level
    close_type = tokens[list_open_idx].type[: -len("_open")] + "_close"
    ingredients: list[Ingredient] = []
    i = list_open_idx + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == close_type and tok.level == list_lvl:
            return i + 1, ingredients
        if tok.type == "list_item_open" and tok.level == list_lvl + 1:
            i, ing = _parse_ingredient_item(tokens, i, source_lines)
            ingredients.append(ing)
            continue
        i += 1
    return i, ingredients


def _parse_ingredient_groups(
    tokens: list[Token],
    start_idx: int,
    parent_level: int,
    source_lines: list[str],
) -> tuple[int, list[IngredientGroup]]:
    groups: list[IngredientGroup] = []
    i = start_idx
    while i < len(tokens):
        tok = tokens[i]
        if tok.type != "heading_open":
            break
        lvl = int(tok.tag[1:])
        if lvl <= parent_level:
            break
        title = _inline_plain_text(tokens[i + 1])
        i += 3  # heading_open, inline, heading_close
        group = IngredientGroup(title=title)
        while i < len(tokens) and tokens[i].type in (
            "bullet_list_open",
            "ordered_list_open",
        ):
            i, ings = _parse_ingredient_list(tokens, i, source_lines)
            group.ingredients.extend(ings)
        i, subgroups = _parse_ingredient_groups(tokens, i, lvl, source_lines)
        group.ingredient_groups.extend(subgroups)
        groups.append(group)
    return i, groups


def parse(text: str, *, frontmatter: bool = False) -> Recipe:
    # Lazy so dataclasses + parse_amount stay usable without markdown-it-py installed.
    from markdown_it import MarkdownIt

    if frontmatter:
        text = _strip_frontmatter(text)

    tokens = MarkdownIt("commonmark").parse(text)
    recipe = Recipe()

    if not tokens:
        raise RecipeMDError("recipe must have a title")

    if tokens[0].type != "heading_open":
        raise RecipeMDError(f"expected level 1 heading, got {tokens[0].type}")
    if tokens[0].tag != "h1":
        raise RecipeMDError(f"expected level 1 heading, got {tokens[0].tag}")
    if len(tokens) < 3 or tokens[1].type != "inline":
        raise RecipeMDError("missing title text")

    recipe.title = _inline_plain_text(tokens[1])
    desc_start_line = tokens[0].map[1]
    i = 3

    tags_found = yields_found = tags_yields_mode = False
    excluded_lines: set[int] = set()
    hr_idx: int | None = None

    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "hr":
            hr_idx = i
            break
        if tok.type == "paragraph_open" and i + 2 < len(tokens):
            inline = tokens[i + 1]
            tags_text, is_em = _is_only_emphasis(inline, "em")
            if is_em:
                if tags_found:
                    raise RecipeMDError("tags already set")
                recipe.tags = _parse_tags(tags_text)
                tags_found = tags_yields_mode = True
                excluded_lines.update(range(*tok.map))
                i += 3
                continue
            yields_text, is_strong = _is_only_emphasis(inline, "strong")
            if is_strong:
                if yields_found:
                    raise RecipeMDError("yields already set")
                recipe.yields = _parse_yields(yields_text)
                yields_found = tags_yields_mode = True
                excluded_lines.update(range(*tok.map))
                i += 3
                continue
            if tags_yields_mode:
                raise RecipeMDError("unexpected content in tags/yields section")
            i += 3
            continue
        i += 1

    if hr_idx is None:
        raise RecipeMDError("missing thematic break divider")

    desc_end_line = tokens[hr_idx].map[0]
    source_lines = text.split("\n")
    if desc_end_line > desc_start_line:
        kept = [
            source_lines[ln]
            for ln in range(desc_start_line, desc_end_line)
            if ln not in excluded_lines
        ]
        desc = "\n".join(kept).strip("\n")
        if desc:
            recipe.description = desc

    i = hr_idx + 1

    while i < len(tokens) and tokens[i].type in (
        "bullet_list_open",
        "ordered_list_open",
    ):
        i, ings = _parse_ingredient_list(tokens, i, source_lines)
        recipe.ingredients.extend(ings)

    i, groups = _parse_ingredient_groups(tokens, i, 0, source_lines)
    recipe.ingredient_groups.extend(groups)

    if i < len(tokens):
        if tokens[i].type != "hr":
            raise RecipeMDError("paragraph not valid in ingredients section")
        instr_start_line = tokens[i].map[1]
        instructions = "\n".join(source_lines[instr_start_line:]).strip("\n")
        if instructions:
            recipe.instructions = instructions

    return recipe


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Parse a RecipeMD document into JSON.")
    p.add_argument("file", nargs="?", help="path to .md file (default: stdin)")
    p.add_argument(
        "--frontmatter", action="store_true", help="strip YAML/TOML frontmatter"
    )
    p.add_argument(
        "--scale",
        metavar="AMOUNT",
        help='scale by a factor ("2", "0.5") or to a target yield ("6 servings")',
    )
    p.add_argument("--indent", type=int, default=2, help="JSON indent (default: 2)")
    args = p.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    try:
        recipe = parse(text, frontmatter=args.frontmatter)
    except RecipeMDError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.scale is not None:
        try:
            scale_amount = parse_amount(args.scale)
        except RecipeMDError as e:
            print(f"error: invalid --scale value: {e}", file=sys.stderr)
            return 1
        if scale_amount.factor == 0:
            print("error: --scale value must be non-zero", file=sys.stderr)
            return 1
        try:
            if scale_amount.unit is None:
                recipe.scale(scale_amount.factor)
            else:
                recipe.scale_for_yield(scale_amount)
        except RecipeMDError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    print(json.dumps(recipe.to_dict(), indent=args.indent, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
