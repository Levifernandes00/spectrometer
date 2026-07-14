import json
import os
import shutil
import sys
import uuid
from pathlib import Path

CONFIG_ENV_VAR = "SPECTROMETER_CONFIG"
CONFIG_FILENAME = "config.json"
CONFIG_TEMPLATE_FILENAME = "config.example.json"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_app_dir() -> Path:
    """Return the application directory (exe dir when frozen, repo root in dev)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_config_path() -> Path:
    configured = os.environ.get(CONFIG_ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return get_app_dir() / CONFIG_FILENAME


def _frozen_template_path() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / CONFIG_TEMPLATE_FILENAME
    return Path(__file__).resolve().parent.parent / CONFIG_TEMPLATE_FILENAME


def _ensure_config_exists(config_path: Path) -> None:
    if config_path.exists():
        return
    if not _is_frozen():
        return

    template_path = _frozen_template_path()
    if template_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, config_path)


def load_config() -> dict:
    config_path = get_config_path()
    _ensure_config_exists(config_path)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_device_identifier(config: dict) -> str:
    """
    Return device identifier from config.
    Set "identifier" in config.json to any name you choose (e.g. "SPECT-LAB-01").
    An empty string is allowed. If the key is missing, generates a placeholder and saves it.
    """
    if "identifier" in config:
        return str(config.get("identifier") or "").strip()
    identifier = f"spectrometer-{uuid.uuid4().hex[:8]}"
    config["identifier"] = identifier
    save_config(config)
    return identifier
