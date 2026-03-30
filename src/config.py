import json
import uuid
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_device_identifier(config: dict) -> str:
    """
    Return device identifier from config.
    Set "identifier" in config.json to any name you choose (e.g. "SPECT-LAB-01").
    If not set, generates a placeholder and saves it; you can edit config.json to change it.
    """
    identifier = config.get("identifier")
    if identifier and str(identifier).strip():
        return str(identifier).strip()
    identifier = f"spectrometer-{uuid.uuid4().hex[:8]}"
    config["identifier"] = identifier
    save_config(config)
    return identifier
