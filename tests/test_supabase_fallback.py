# pyright: reportMissingImports=false

import sys
from pathlib import Path


TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import device


def _clear_supabase_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_EMAIL", raising=False)
    monkeypatch.delenv("SUPABASE_PASSWORD", raising=False)


def test_get_supabase_missing_password_returns_none(monkeypatch):
    _clear_supabase_env(monkeypatch)

    calls = {"count": 0}

    def _fake_create_client(url: str, key: str):
        calls["count"] += 1
        return object()

    monkeypatch.setattr(device, "create_client", _fake_create_client)

    cfg = {
        "online_sync": {
            "url": "https://example.supabase.co",
            "key": "anon-key",
            "email": "user@example.com",
            "password": "",
        }
    }
    assert device.get_supabase(cfg) is None
    assert calls["count"] == 0


def test_get_supabase_failed_auth_returns_none(monkeypatch):
    _clear_supabase_env(monkeypatch)

    class _Auth:
        def sign_in_with_password(self, data: dict):
            raise RuntimeError("invalid credentials")

    class _Client:
        auth = _Auth()

    monkeypatch.setattr(device, "create_client", lambda url, key: _Client())

    cfg = {
        "online_sync": {
            "url": "https://example.supabase.co",
            "key": "anon-key",
            "email": "user@example.com",
            "password": "bad-password",
        }
    }
    assert device.get_supabase(cfg) is None


def test_get_supabase_valid_auth_returns_client(monkeypatch):
    _clear_supabase_env(monkeypatch)

    class _Auth:
        def __init__(self):
            self.calls = []

        def sign_in_with_password(self, data: dict):
            self.calls.append(data)
            return {"ok": True}

    class _Client:
        def __init__(self):
            self.auth = _Auth()

    client = _Client()
    monkeypatch.setattr(device, "create_client", lambda url, key: client)

    cfg = {
        "online_sync": {
            "url": "https://example.supabase.co",
            "key": "anon-key",
            "email": "user@example.com",
            "password": "good-password",
        }
    }

    result = device.get_supabase(cfg)
    assert result is client
    assert client.auth.calls == [
        {"email": "user@example.com", "password": "good-password"}
    ]
