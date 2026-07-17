# pyright: reportMissingImports=false

import sqlite3
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import device
from db import (
    _ensure_tables_local,
    find_or_create_batch_local,
    insert_results_local,
)


def _fresh_db(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    device.ensure_device_table(conn)
    _ensure_tables_local(conn)
    return conn


def test_create_device_local_uses_integer_lastrowid(tmp_path):
    conn = _fresh_db(tmp_path)
    created = device.create_device_local(
        conn,
        identifier="SPECT-01",
        name="Spectrometer",
        place="LAB",
        company_id="default",
        connection_details={"folder": "/tmp"},
    )
    assert isinstance(created["id"], int)
    cur = conn.execute(
        "SELECT id, typeof(id), identifier, company_id FROM device WHERE id = ?",
        (created["id"],),
    )
    row = cur.fetchone()
    assert row is not None
    assert row[1] == "integer"
    assert row[2] == "SPECT-01"
    assert row[3] == "default"
    conn.close()


def test_find_or_create_batch_local_uses_iso_date_and_integer_id(tmp_path):
    conn = _fresh_db(tmp_path)
    batch = find_or_create_batch_local(conn, "260009", "08/01/2026", "default")
    assert isinstance(batch["id"], int)
    assert batch["date"] == "2026-01-08"
    again = find_or_create_batch_local(conn, "260009", "08/01/2026", "default")
    assert again["id"] == batch["id"]
    conn.close()


def test_insert_results_local_omits_id(tmp_path):
    conn = _fresh_db(tmp_path)
    device_row = device.create_device_local(
        conn, "SPECT-01", "Spectrometer", "LAB", company_id="default"
    )
    batch = find_or_create_batch_local(conn, "260009", "08/01/2026", "default")
    insert_results_local(
        conn,
        batch["id"],
        device_row["id"],
        [{"key": "C", "value": 0.12, "obs": None}],
        "2026-01-08T10:00:00",
    )
    cur = conn.execute(
        "SELECT id, typeof(id), key, batch_id, device_id FROM result"
    )
    row = cur.fetchone()
    assert row is not None
    assert row[1] == "integer"
    assert row[2] == "C"
    assert row[3] == batch["id"]
    assert row[4] == device_row["id"]
    conn.close()


def test_get_local_company_id_defaults_and_config(monkeypatch):
    monkeypatch.delenv("SUPABASE_COMPANY_ID", raising=False)
    assert device.get_local_company_id({}) == "default"
    assert (
        device.get_local_company_id({"online_sync": {"company_id": "co-1"}})
        == "co-1"
    )
