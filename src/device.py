import json
import os
import sqlite3
import uuid
from pathlib import Path

from supabase import create_client, Client

from config import get_device_identifier


def get_supabase(config: dict) -> Client | None:
    online_sync_cfg = config.get("online_sync") or {}
    url = os.environ.get("SUPABASE_URL") or online_sync_cfg.get("url")
    key = os.environ.get("SUPABASE_KEY") or online_sync_cfg.get("key")
    email = os.environ.get("SUPABASE_EMAIL") or online_sync_cfg.get("email")
    password = os.environ.get("SUPABASE_PASSWORD") or online_sync_cfg.get("password")

    if not url or not key:
        return None

    # Optional Supabase mode: require user credentials to enable cloud sync.
    if not email or not str(email).strip() or not password or not str(password).strip():
        print("Online Sync credentials missing (email/password); running in local-only mode.")
        return None

    try:
        supabase = create_client(url, key)
        supabase.auth.sign_in_with_password(
            {"email": str(email).strip(), "password": str(password)}
        )
        return supabase
    except Exception as exc:
        print(f"Online Sync auth failed; running in local-only mode. Reason: {exc}")
        return None


def get_local_db(config: dict) -> sqlite3.Connection | None:
    db_path = config.get("database")
    if not db_path:
        return None
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).parent.parent / path
    return sqlite3.connect(str(path))


def find_device_by_identifier(supabase: Client, identifier: str) -> dict | None:
    resp = supabase.table("device").select("*").eq("identifier", identifier).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return None


def find_device_local(local_db: sqlite3.Connection, identifier: str) -> dict | None:
    cur = local_db.execute(
        "SELECT * FROM Device WHERE identifier = ?", (identifier,)
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def create_device_supabase(
    supabase: Client,
    identifier: str,
    name: str,
    place: str,
    category: str = "Spectrometer",
    connection_details: dict | None = None,
) -> dict:
    data = {
        "name": name,
        "place": place,
        "category": category,
        "identifier": identifier,
        "connection_details": connection_details or {},
    }
    resp = supabase.table("device").insert(data).execute()
    return resp.data[0]


def create_device_local(
    local_db: sqlite3.Connection,
    identifier: str,
    name: str,
    place: str,
    category: str = "Spectrometer",
    connection_details: dict | None = None,
) -> dict:
    device_id = str(uuid.uuid4())
    details = json.dumps(connection_details or {})
    local_db.execute(
        """
        INSERT INTO Device (id, name, place, category, identifier, connection_details)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (device_id, name, place, category, identifier, details),
    )
    local_db.commit()
    return {"id": device_id, "name": name, "place": place, "category": category, "identifier": identifier}


def ensure_device_table(local_db: sqlite3.Connection) -> None:
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS Device (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            place TEXT NOT NULL,
            category TEXT NOT NULL,
            identifier TEXT,
            connection_details TEXT
        )
    """)
    local_db.commit()


def find_or_create_device(config: dict) -> dict | None:
    """
    Find device by identifier. If not found, create it and save identifier to config.
    Returns device dict or None if neither Supabase nor local DB is available.
    """
    identifier = get_device_identifier(config)
    device_cfg = config.get("device", {})
    name = device_cfg.get("name", "Spectrometer")
    place = device_cfg.get("place", "LABORATÓRIO")
    category = device_cfg.get("category", device_cfg.get("instrument", "Spectrometer"))
    folder = config.get("folder")
    connection_details = {"folder": folder} if folder else {}

    supabase = get_supabase(config)
    if supabase:
        device = find_device_by_identifier(supabase, identifier)
        if device:
            return device
        device = create_device_supabase(
            supabase, identifier, name, place, category, connection_details
        )
        return device

    local_db = get_local_db(config)
    if local_db:
        ensure_device_table(local_db)
        device = find_device_local(local_db, identifier)
        if device:
            return device
        device = create_device_local(
            local_db, identifier, name, place, category, connection_details
        )
        return device

    return None
