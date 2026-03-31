# pyright: reportMissingImports=false

import sys
from pathlib import Path
import queue
import socket
import threading
import time
import json
import asyncio

import websockets

TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from websocket_publisher import (
    build_batch_material_payload,
    get_material,
    publish_batch_material,
)


def test_build_batch_material_payload():
    payload = build_batch_material_payload("260009", "EN-GJMW 400-05")
    assert payload == {"fusion": "260009", "material": "EN-GJMW 400-05"}


def test_get_material_fallback_unknown():
    assert get_material({}) == "unknown"


def test_get_material_prefers_parsed_value():
    cfg = {"material": "CONFIG-MATERIAL"}
    assert get_material(cfg, parsed_material="EN-GJMW 400-05") == "EN-GJMW 400-05"


def test_publish_disabled_returns_false():
    cfg = {"websocket": {"enabled": False, "url": "ws://127.0.0.1:8765"}}
    assert publish_batch_material(cfg, "260009") is False


def test_publish_enabled_missing_url_returns_false():
    cfg = {"websocket": {"enabled": True}}
    assert publish_batch_material(cfg, "260009") is False


def test_publish_non_fatal_on_send_failure(monkeypatch):
    import websocket_publisher as wp

    async def _raise_send(url: str, payload: dict, open_timeout: float) -> None:
        raise RuntimeError("cannot connect")

    monkeypatch.setattr(wp, "_send_json", _raise_send)
    cfg = {
        "material": "EN-GJMW 400-05",
        "websocket": {"enabled": True, "url": "ws://127.0.0.1:8765"},
    }
    assert publish_batch_material(cfg, "260009", "EN-GJMW 400-05") is False


def test_publish_success(monkeypatch):
    import websocket_publisher as wp

    seen = {}

    async def _ok_send(url: str, payload: dict, open_timeout: float) -> None:
        seen["url"] = url
        seen["payload"] = payload
        seen["open_timeout"] = open_timeout

    monkeypatch.setattr(wp, "_send_json", _ok_send)
    cfg = {
        "material": "EN-GJMW 400-05",
        "websocket": {
            "enabled": True,
            "url": "ws://127.0.0.1:8765",
            "open_timeout": 5,
        },
    }
    assert publish_batch_material(cfg, "260009", "EN-GJMW 400-05") is True
    assert seen["url"] == "ws://127.0.0.1:8765"
    assert seen["payload"] == {"fusion": "260009", "material": "EN-GJMW 400-05"}
    assert seen["open_timeout"] == 5.0


def test_publish_loopback_same_machine():
    received: queue.Queue[str] = queue.Queue()
    stop_event = threading.Event()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()

    async def handler(ws):
        message = await ws.recv()
        received.put(message)

    async def server_main():
        async with websockets.serve(handler, "127.0.0.1", port):
            while not stop_event.is_set():
                await asyncio.sleep(0.05)

    def run_server():
        asyncio.run(server_main())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.2)

    cfg = {
        "material": "EN-GJMW 400-05",
        "websocket": {
            "enabled": True,
            "url": f"ws://127.0.0.1:{port}",
            "open_timeout": 3,
        },
    }
    sent = publish_batch_material(cfg, "260009", "EN-GJMW 400-05")
    assert sent is True

    raw = received.get(timeout=3)
    assert json.loads(raw) == {"fusion": "260009", "material": "EN-GJMW 400-05"}

    stop_event.set()
    thread.join(timeout=2)


def test_publish_uses_unknown_when_material_missing(monkeypatch):
    import websocket_publisher as wp

    seen = {}

    async def _ok_send(url: str, payload: dict, open_timeout: float) -> None:
        seen["payload"] = payload

    monkeypatch.setattr(wp, "_send_json", _ok_send)
    cfg = {"websocket": {"enabled": True, "url": "ws://127.0.0.1:8765"}}
    assert publish_batch_material(cfg, "260009", "") is True
    assert seen["payload"] == {"fusion": "260009", "material": "unknown"}
