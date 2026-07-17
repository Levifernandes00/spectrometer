"""Database operations for batch and result tables."""

from datetime import datetime

from supabase import Client

from device import DEFAULT_LOCAL_COMPANY_ID


def _ensure_tables_local(local_db) -> None:
    """Create oxpecker-compatible batch and result tables if they don't exist."""
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS batch (
            id INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            day_order INTEGER,
            product_id INTEGER,
            company_id TEXT NOT NULL DEFAULT 'default'
        )
    """)
    local_db.execute("""
        CREATE TABLE IF NOT EXISTS result (
            id INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            "key" TEXT NOT NULL,
            value NUMERIC,
            datetime TEXT,
            obs TEXT,
            batch_id INTEGER,
            device_id INTEGER
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
    """Convert DD/MM/YYYY to ISO date (YYYY-MM-DD) for Supabase / shared SQLite."""
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return datetime.now().strftime("%Y-%m-%d")


def find_or_create_batch_supabase(
    supabase: Client,
    name: str,
    date_str: str,
    company_id: str,
) -> dict:
    """Find batch by name+date+company or create in Supabase."""
    date_iso = _date_to_iso_date(date_str)
    resp = (
        supabase.table("batch")
        .select("*")
        .eq("name", name)
        .eq("date", date_iso)
        .eq("company_id", company_id)
        .execute()
    )
    if resp.data and len(resp.data) > 0:
        return resp.data[0]
    data = {"name": name, "date": date_iso, "company_id": company_id}
    resp = supabase.table("batch").insert(data).execute()
    return resp.data[0]


def find_or_create_batch_local(
    local_db,
    name: str,
    date_str: str,
    company_id: str = DEFAULT_LOCAL_COMPANY_ID,
) -> dict:
    """Find batch by name+date+company or create in local DB (oxpecker schema)."""
    date_iso = _date_to_iso_date(date_str)
    cur = local_db.execute(
        "SELECT * FROM batch WHERE name = ? AND date = ? AND company_id = ?",
        (name, date_iso, company_id),
    )
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    cur = local_db.execute(
        """
        INSERT INTO batch (date, name, day_order, product_id, company_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (date_iso, name, None, None, company_id),
    )
    local_db.commit()
    return {
        "id": cur.lastrowid,
        "date": date_iso,
        "name": name,
        "company_id": company_id,
    }


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
    device_id: int,
    datetime_iso: str,
) -> bool:
    """Return True if any result exists for this device at this datetime."""
    cur = local_db.execute(
        "SELECT 1 FROM result WHERE device_id = ? AND datetime = ? LIMIT 1",
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
    batch_id: int,
    device_id: int,
    results: list[dict],
    datetime_iso: str,
) -> None:
    """Insert multiple results into local DB (oxpecker schema)."""
    for r in results:
        local_db.execute(
            """
            INSERT INTO result ("key", value, datetime, obs, batch_id, device_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (r["key"], r["value"], datetime_iso, r.get("obs"), batch_id, device_id),
        )
    local_db.commit()
