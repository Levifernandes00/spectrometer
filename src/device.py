import json
import os
import sqlite3
from pathlib import Path

from supabase import create_client, Client

from config import get_app_dir, get_device_identifier

COMPANY_ID_ENV_VAR = "SUPABASE_COMPANY_ID"
DEFAULT_LOCAL_COMPANY_ID = "default"


def get_local_company_id(config: dict) -> str:
    """Company id for local SQLite writes (oxpecker shared schema)."""
    online_sync_cfg = config.get("online_sync") or {}
    config_value = str(online_sync_cfg.get("company_id") or "").strip()
    if config_value:
        return config_value
    env_value = os.environ.get(COMPANY_ID_ENV_VAR, "").strip()
    if env_value:
        return env_value
    return DEFAULT_LOCAL_COMPANY_ID


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


def get_company_id(config: dict, supabase: Client) -> str | None:
    """Resolve company_id from env, config, or the user's sole company membership."""
    env_value = os.environ.get(COMPANY_ID_ENV_VAR, "").strip()
    if env_value:
        return env_value

    online_sync_cfg = config.get("online_sync") or {}
    config_value = str(online_sync_cfg.get("company_id") or "").strip()
    if config_value:
        return config_value

    try:
        resp = (
            supabase.table("company_user")
            .select("company_id")
            .order("created_at")
            .execute()
        )
        company_ids = [
            str(row["company_id"]).strip()
            for row in (resp.data or [])
            if row.get("company_id")
        ]
    except Exception as exc:
        print(f"Online Sync: failed to load company memberships. Reason: {exc}")
        return None

    if len(company_ids) == 1:
        return company_ids[0]

    if not company_ids:
        print("Online Sync: no company memberships found for this user.")
        return None

    print(
        "Online Sync: user belongs to multiple companies. "
        "Set online_sync.company_id in config.json or SUPABASE_COMPANY_ID."
    )
    return None


def get_local_db(config: dict) -> sqlite3.Connection | None:
    db_path = config.get("database")
    if not db_path:
        return None
    path = Path(db_path)
    if not path.is_absolute():
        path = get_app_dir() / path
    return sqlite3.connect(str(path))


def find_device_by_identifier(
    supabase: Client,
    identifier: str,
    company_id: str,
) -> dict | None:
    resp = (
        supabase.table("device")
        .select("*")
        .eq("identifier", identifier)
        .eq("company_id", company_id)
        .execute()
    )
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    return None


def find_device_local(
    local_db: sqlite3.Connection,
    identifier: str,
    company_id: str = DEFAULT_LOCAL_COMPANY_ID,
) -> dict | None:
    cur = local_db.execute(
        "SELECT * FROM device WHERE identifier = ? AND company_id = ?",
        (identifier, company_id),
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
    company_id: str,
    category: str = "Spectrometer",
    connection_details: dict | None = None,
) -> dict:
    data = {
        "name": name,
        "place": place,
        "category": category,
        "identifier": identifier,
        "connection_details": connection_details or {},
        "company_id": company_id,
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
    company_id: str = DEFAULT_LOCAL_COMPANY_ID,
) -> dict:
    details = json.dumps(connection_details or {})
    cur = local_db.execute(
        """
        INSERT INTO device (name, identifier, place, category, connection_details, company_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, identifier, place, category, details, company_id),
    )
    local_db.commit()
    return {
        "id": cur.lastrowid,
        "name": name,
        "place": place,
        "category": category,
        "identifier": identifier,
        "company_id": company_id,
    }


def ensure_device_table(local_db: sqlite3.Connection) -> None:
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS device (
            id INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            name TEXT NOT NULL,
            place TEXT,
            category TEXT,
            connection_details TEXT NOT NULL,
            identifier TEXT NOT NULL,
            company_id TEXT NOT NULL DEFAULT 'default'
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
        company_id = get_company_id(config, supabase)
        if company_id:
            device = find_device_by_identifier(supabase, identifier, company_id)
            if device:
                return device
            return create_device_supabase(
                supabase, identifier, name, place, company_id, category, connection_details
            )

    local_db = get_local_db(config)
    if local_db:
        company_id = get_local_company_id(config)
        ensure_device_table(local_db)
        device = find_device_local(local_db, identifier, company_id)
        if device:
            return device
        device = create_device_local(
            local_db,
            identifier,
            name,
            place,
            category,
            connection_details,
            company_id,
        )
        return device

    return None
