# pyright: reportMissingImports=false

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from parser import _extract_furnace, parse_file


LIVARNA_HEADER = """
Peč 2
 ANALIZA KEMIJSKE SESTAVE
 Datum in ura:
 2026-03-09   10:48:44
 Peč:
 Material:
 EN-GJMW 400-05
"""


def test_extract_furnace_from_title_line():
    assert _extract_furnace(LIVARNA_HEADER) == "2"


def test_extract_furnace_from_same_line_label():
    text = "Peč: 3\nMaterial: EN-GJMW 400-05"
    assert _extract_furnace(text) == "3"


def test_extract_furnace_from_next_line_label():
    text = "Peč:\n4\nMaterial: EN-GJMW 400-05"
    assert _extract_furnace(text) == "4"


def test_extract_furnace_returns_none_when_absent():
    assert _extract_furnace("Material: GJS 400\nNr. Colata: 260009") is None


def test_parse_livarna_pdf_includes_furnace():
    parsed = parse_file(TESTS_DIR / "livarna.pdf")
    assert parsed is not None
    assert parsed.furnace == "2"
