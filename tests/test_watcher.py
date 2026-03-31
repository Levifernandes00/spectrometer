# pyright: reportMissingImports=false

import sys
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileMovedEvent


TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from watcher import SpectrometerEventHandler, is_supported_file


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
