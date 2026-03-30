import json
import pytest
from pathlib import Path

@pytest.fixture
def pdf_path():
    # Locates the file relative to the test file itself
    return Path(__file__).parent / "assets" / "giorgietti.pdf"

CONFIG_PATH = Path(__file__).parent / "test_config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_pdf_processing(pdf_path):
    with open(pdf_path, "rb") as f:
        content = f.read()
        print(content)
        assert content.startswith(b"%PDF")  # Basic check that it's a PDF