"""Database operations for batch and result tables."""

import uuid
from datetime import datetime

from supabase import Client


def _ensure_tables_local(local_db) -> None:
    """Create batch and result tables if they don't exist."""
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS Batch (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            product_id TEXT
        )
    """)
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS Result (
            id TEXT PRIMARY KEY,
            key TEXT NOT NULL,
            value REAL NOT NULL,
            datetime TEXT NOT NULL,
            obs TEXT,
            batch_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES Batch(id),
            FOREIGN KEY (device_id) REFERENCES Device(id)
        )
    """)
    local_db.commit()


def _date_to_iso(date_str: str, time_str: str) -> str:
    """Convert DD/MM/YYYY and HH:MM:SS to ISO datetime."""
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return datetime.now().isoformat()


def _date_to_iso_date(date_str: str) -> str:
    """Convert DD/MM/YYYY to ISO date (YYYY-MM-DD) for Supabase."""
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")


def find_or_create_batch_supabase(
    supabase: Client,
    name: str,
    date_str: str,
) -> dict:
    """Find batch by name+date or create in Supabase."""
    date_iso = _date_to_iso_date(date_str)
    resp = supabase.table("batch").select("*").eq("name", name).eq("date", date_iso).execute()
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    data = {"name": name, "date": date_iso}
    resp = supabase.table("batch").insert(data).execute()
    return resp.data[0]


def find_or_create_batch_local(
    local_db,
    name: str,
    date_str: str,
) -> dict:
    """Find batch by name+date or create in local DB."""
    cur = local_db.execute(
        "SELECT * FROM Batch WHERE name = ? AND date = ?",
        (name, date_str),
    )
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    batch_id = str(uuid.uuid4())
    local_db.execute(
        "INSERT INTO Batch (id, date, name, product_id) VALUES (?, ?, ?, ?)",
        (batch_id, date_str, name, None),
    )
    local_db.commit()
    return {"id": batch_id, "date": date_str, "name": name}


def has_results_for_device_datetime_supabase(
    supabase: Client,
    device_id: int,
    datetime_iso: str,
) -> bool:
    """Return True if any result exists for this device at this datetime."""
    resp = (
        supabase.table("result")
        .select("id")
        .eq("device_id", device_id)
        .eq("datetime", datetime_iso)
        .limit(1)
        .execute()
    )
    return bool(resp.data and len(resp.data) > 0)


def has_results_for_device_datetime_local(
    local_db,
    device_id: str,
    datetime_iso: str,
) -> bool:
    """Return True if any result exists for this device at this datetime."""
    cur = local_db.execute(
        "SELECT 1 FROM Result WHERE device_id = ? AND datetime = ? LIMIT 1",
        (device_id, datetime_iso),
    )
    return cur.fetchone() is not None


def insert_results_supabase(
    supabase: Client,
    batch_id: int,
    device_id: int,
    results: list[dict],
    datetime_iso: str,
) -> None:
    """Insert multiple results into Supabase."""
    rows = [
        {
            "key": r["key"],
            "value": r["value"],
            "datetime": datetime_iso,
            "obs": r.get("obs"),
            "batch_id": batch_id,
            "device_id": device_id,
        }
        for r in results
    ]
    supabase.table("result").insert(rows).execute()


def insert_results_local(
    local_db,
    batch_id: str,
    device_id: str,
    results: list[dict],
    datetime_iso: str,
) -> None:
    """Insert multiple results into local DB."""
    for r in results:
        rid = str(uuid.uuid4())
        local_db.execute(
            """
            INSERT INTO Result (id, key, value, datetime, obs, batch_id, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (rid, r["key"], r["value"], datetime_iso, r.get("obs"), batch_id, device_id),
        )
    local_db.commit()
