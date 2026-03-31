"""Optional WebSocket publisher for Oxpecker integration."""

import asyncio
import json

import websockets


def _websocket_config(config: dict) -> dict:
    ws_cfg = config.get("websocket")
    return ws_cfg if isinstance(ws_cfg, dict) else {}


def websocket_enabled(config: dict) -> bool:
    ws_cfg = _websocket_config(config)
    return bool(ws_cfg.get("enabled"))


def get_material(config: dict, parsed_material: str | None = None) -> str:
    parsed = str(parsed_material).strip() if parsed_material is not None else ""
    if parsed:
        return parsed

    ws_cfg = _websocket_config(config)
    material = ws_cfg.get("material", config.get("material", "unknown"))
    material_str = str(material).strip() if material is not None else ""
    return material_str or "unknown"


def build_batch_material_payload(batch: str, material: str) -> dict:
    # Oxpecker expects "fusion" + "material" on websocket input.
    return {"fusion": batch, "material": material}


async def _send_json(url: str, payload: dict, open_timeout: float) -> None:
    async with websockets.connect(url, open_timeout=open_timeout) as ws:
        await ws.send(json.dumps(payload))


def publish_batch_material(config: dict, batch: str, material: str | None = None) -> bool:
    """
    Publish minimal payload to WebSocket server.
    Returns True when sent, False when disabled/misconfigured/failed.
    """
    if not websocket_enabled(config):
        return False

    ws_cfg = _websocket_config(config)
    url = str(ws_cfg.get("url", "")).strip()
    if not url:
        print("WebSocket enabled but no URL configured; skipping publish.")
        return False

    open_timeout = float(ws_cfg.get("open_timeout", 3))
    payload = build_batch_material_payload(
        batch=batch,
        material=get_material(config, parsed_material=material),
    )

    try:
        asyncio.run(_send_json(url, payload, open_timeout))
        return True
    except Exception as exc:
        print(f"WebSocket publish failed: {exc}")
        return False
