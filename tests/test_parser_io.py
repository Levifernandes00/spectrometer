# pyright: reportMissingImports=false

import errno
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from parser import _read_bytes_with_retry, find_files


def test_read_bytes_with_retry_recovers_from_permission_error(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_bytes(b"hello")

    attempts = {"count": 0}
    original_read_bytes = Path.read_bytes

    def flaky_read_bytes(self):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError(errno.EACCES, "permission denied")
        return original_read_bytes(self)

    with patch.object(Path, "read_bytes", flaky_read_bytes):
        data = _read_bytes_with_retry(target, retries=5, delay=0)

    assert data == b"hello"
    assert attempts["count"] == 3


def test_read_bytes_with_retry_returns_none_after_exhausting_retries(tmp_path, capsys):
    target = tmp_path / "locked.txt"
    target.write_bytes(b"hello")

    def always_denied(self):
        raise PermissionError(errno.EACCES, "permission denied")

    with patch.object(Path, "read_bytes", always_denied):
        data = _read_bytes_with_retry(target, retries=2, delay=0)

    assert data is None
    captured = capsys.readouterr()
    assert "could not read" in captured.out
    assert "locked.txt" in captured.out


def test_find_files_skips_unreadable_directories(tmp_path, monkeypatch, capsys):
    readable = tmp_path / "ok"
    blocked = tmp_path / "blocked"
    readable.mkdir()
    blocked.mkdir()
    (readable / "good.pdf").write_text("pdf", encoding="utf-8")

    real_walk = __import__("os").walk

    def walk_with_permission_error(folder, onerror=None):
        for root, dirs, files in real_walk(folder):
            if Path(root) == blocked and onerror is not None:
                onerror(PermissionError(errno.EACCES, "permission denied", str(blocked)))
                dirs.clear()
                continue
            yield root, dirs, files

    monkeypatch.setattr("parser.os.walk", walk_with_permission_error)

    files = find_files(tmp_path)

    assert files == [readable / "good.pdf"]
    captured = capsys.readouterr()
    assert "skipping unreadable path" in captured.out
