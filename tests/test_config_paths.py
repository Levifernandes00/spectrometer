# pyright: reportMissingImports=false

import importlib
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))


def _reload_config():
    if "config" in sys.modules:
        del sys.modules["config"]
    return importlib.import_module("config")


def test_get_config_path_uses_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom.json"
    monkeypatch.setenv("SPECTROMETER_CONFIG", str(override))
    cfg = _reload_config()
    assert cfg.get_config_path() == override.resolve()


def test_get_config_path_frozen_uses_executable_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECTROMETER_CONFIG", raising=False)
    exe = tmp_path / "bin" / "spectrometer.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    cfg = _reload_config()
    assert cfg.get_config_path() == exe.parent / "config.json"


def test_get_config_path_dev_uses_repo_config(monkeypatch):
    monkeypatch.delenv("SPECTROMETER_CONFIG", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    cfg = _reload_config()
    assert cfg.get_config_path() == cfg.get_app_dir() / "config.json"


def test_get_app_dir_frozen_uses_executable_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECTROMETER_CONFIG", raising=False)
    exe = tmp_path / "bin" / "spectrometer.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    cfg = _reload_config()
    assert cfg.get_app_dir() == exe.parent


def test_get_local_db_frozen_uses_executable_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECTROMETER_CONFIG", raising=False)
    exe = tmp_path / "bin" / "spectrometer.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    if "config" in sys.modules:
        del sys.modules["config"]
    if "device" in sys.modules:
        del sys.modules["device"]
    device = importlib.import_module("device")

    conn = device.get_local_db({"database": "spectrometer.db"})
    assert conn is not None
    conn.close()
    assert (exe.parent / "spectrometer.db").exists()
