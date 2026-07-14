# pyright: reportMissingImports=false

import sys
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileMovedEvent


TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from watcher import SpectrometerEventHandler, handle_folder_change, is_supported_file


def test_is_supported_file():
    assert is_supported_file("sample.pdf") is True
    assert is_supported_file("sample.txt") is True
    assert is_supported_file("sample.csv") is False
    


def test_event_handler_calls_callback_for_supported_files():
    seen = []

    def callback(path: Path):
        seen.append(path.name)

    handler = SpectrometerEventHandler(callback)
    handler.on_created(FileCreatedEvent("/tmp/new_file.pdf"))
    handler.on_created(FileCreatedEvent("/tmp/new_file.txt"))
    handler.on_created(FileCreatedEvent("/tmp/new_file.csv"))

    assert seen == ["new_file.pdf", "new_file.txt"]


def test_event_handler_uses_destination_path_on_move():
    seen = []

    def callback(path: Path):
        seen.append(path.name)

    handler = SpectrometerEventHandler(callback)
    handler.on_moved(FileMovedEvent("/tmp/tmp.part", "/tmp/final.pdf"))

    assert seen == ["final.pdf"]


def test_handle_folder_change_catches_os_error(monkeypatch, capsys):
    def raise_permission_error(*_args, **_kwargs):
        raise PermissionError(13, "permission denied")

    monkeypatch.setattr("watcher.process_folder", raise_permission_error)

    handle_folder_change({"folder": "/tmp"}, Path("/tmp/test.pdf"))

    captured = capsys.readouterr()
    assert "Error processing" in captured.out
    assert "test.pdf" in captured.out


def test_handle_folder_change_catches_unexpected_error(monkeypatch, capsys):
    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("watcher.process_folder", raise_runtime_error)

    handle_folder_change({"folder": "/tmp"}, Path("/tmp/test.pdf"))

    captured = capsys.readouterr()
    assert "Unexpected error processing" in captured.out
