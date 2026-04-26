import json
from pathlib import Path

import pytest

from recipemd import RecipeMDError, __version__, parse

TESTDATA = Path(__file__).parent / "testdata"

VALID = sorted(p for p in TESTDATA.rglob("*.md") if not p.name.endswith(".invalid.md"))
INVALID = sorted(TESTDATA.rglob("*.invalid.md"))


def _id(p: Path) -> str:
    return str(p.relative_to(TESTDATA))


def _kwargs(p: Path) -> dict:
    return {"frontmatter": True} if "frontmatter" in p.parts else {}


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize("md_path", VALID, ids=[_id(p) for p in VALID])
def test_golden_valid(md_path: Path):
    expected = json.loads(md_path.with_suffix(".json").read_text())
    assert parse(md_path.read_text(), **_kwargs(md_path)).to_dict() == expected


@pytest.mark.parametrize("md_path", INVALID, ids=[_id(p) for p in INVALID])
def test_golden_invalid(md_path: Path):
    with pytest.raises(RecipeMDError):
        parse(md_path.read_text(), **_kwargs(md_path))
