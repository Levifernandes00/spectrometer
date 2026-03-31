# pyright: reportMissingImports=false

from pathlib import Path
import json
import sys

import pytest

TESTS_DIR = Path(__file__).parent
ASSETS_DIR = TESTS_DIR / "assets"
EXPECTED_PATH = TESTS_DIR / "expected_assets.json"

# Import parser module from spectrometer/src without requiring package install.
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from parser import parse_file


def load_expected() -> dict:
    with open(EXPECTED_PATH, encoding="utf-8") as f:
        return json.load(f)


def discover_assets() -> list[Path]:
    return sorted(
        p for p in ASSETS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".pdf", ".txt")
    )


def test_expected_fixture_matches_assets_folder():
    expected = load_expected()
    asset_names = {p.name for p in discover_assets()}
    expected_names = set(expected.keys())
    assert asset_names == expected_names


@pytest.mark.parametrize("asset_path", discover_assets(), ids=lambda p: p.name)
def test_asset_parsing_matches_expected_properties(asset_path: Path):
    expected = load_expected()[asset_path.name]
    parsed = parse_file(asset_path)

    assert parsed is not None, f"Parser returned None for {asset_path.name}"
    assert parsed.batch == expected["batch"]
    assert parsed.date == expected["date"]
    assert parsed.time == expected["time"]
    assert parsed.results == expected["results"]