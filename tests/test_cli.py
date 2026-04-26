import io
import json
from pathlib import Path

import pytest

from recipemd import main

TESTDATA = Path(__file__).parent / "testdata"
RECIPE = TESTDATA / "canonical" / "recipe.md"
TITLE_ONLY = TESTDATA / "canonical" / "title.md"
EMPTY_INVALID = TESTDATA / "canonical" / "empty.invalid.md"
FRONTMATTER_YAML = TESTDATA / "golden" / "frontmatter" / "yaml.md"


def _stdout_json(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def test_main_file_arg(capsys):
    assert main([str(TITLE_ONLY)]) == 0
    assert _stdout_json(capsys)["title"] == "The Most Useless Recipe"


def test_main_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(TITLE_ONLY.read_text()))
    assert main([]) == 0
    assert _stdout_json(capsys)["title"] == "The Most Useless Recipe"


def test_main_frontmatter_flag(capsys):
    assert main(["--frontmatter", str(FRONTMATTER_YAML)]) == 0
    out = _stdout_json(capsys)
    assert out["title"] == "Recipe"
    assert out["ingredients"] == [{"name": "salt", "amount": None, "link": None}]


def test_main_frontmatter_disabled_treats_fence_as_invalid_recipe(capsys):
    assert main([str(FRONTMATTER_YAML)]) == 1
    assert "error:" in capsys.readouterr().err


def test_main_invalid_recipe_returns_1(capsys):
    assert main([str(EMPTY_INVALID)]) == 1
    assert "error:" in capsys.readouterr().err


def test_main_scale_factor(capsys):
    assert main(["--scale", "2", str(RECIPE)]) == 0
    yields = {y["unit"]: y["factor"] for y in _stdout_json(capsys)["yields"]}
    assert yields == {"cups": "10", "ml": "40", "Tassen": "11"}


def test_main_scale_for_yield(capsys):
    # Recipe yields 5 cups → request 11 cups → ratio 11/5 = 2.2
    assert main(["--scale", "11 cups", str(RECIPE)]) == 0
    yields = {y["unit"]: y["factor"] for y in _stdout_json(capsys)["yields"]}
    assert yields == {"cups": "11", "ml": "44", "Tassen": "12.1"}


def test_main_scale_zero_rejected(capsys):
    assert main(["--scale", "0", str(RECIPE)]) == 1
    assert "non-zero" in capsys.readouterr().err


def test_main_scale_unmatched_unit_rejected(capsys):
    assert main(["--scale", "5 quarts", str(RECIPE)]) == 1
    assert "no matching yield unit" in capsys.readouterr().err


def test_main_indent_flag(capsys):
    assert main(["--indent", "0", str(TITLE_ONLY)]) == 0
    out = capsys.readouterr().out
    # indent=0 still produces newlines but no leading space per item
    assert "\n  " not in out
