# pyright: reportMissingImports=false

import sys
from pathlib import Path


TESTS_DIR = Path(__file__).parent
SRC_DIR = TESTS_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

import device
from db import find_or_create_batch_supabase


class _Query:
    def __init__(self, table_name: str, store: dict):
        self.table_name = table_name
        self.store = store
        self.filters: list[tuple[str, object]] = []

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column: str, value: object):
        self.filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def insert(self, data):
        self.store.setdefault("inserts", []).append((self.table_name, data))
        return self

    def execute(self):
        if self.table_name == "company_user":
            return type("Resp", (), {"data": self.store.get("memberships", [])})()

        if self.table_name == "device" and self.store.get("existing_device"):
            return type("Resp", (), {"data": [self.store["existing_device"]]})()

        if self.table_name == "batch" and self.store.get("existing_batch"):
            batch = self.store["existing_batch"]
            if all(batch.get(col) == val for col, val in self.filters):
                return type("Resp", (), {"data": [batch]})()
            return type("Resp", (), {"data": []})()

        inserts = self.store.get("inserts", [])
        if inserts and inserts[-1][0] == self.table_name:
            payload = inserts[-1][1]
            if isinstance(payload, list):
                payload = payload[0]
            return type("Resp", (), {"data": [payload]})()

        return type("Resp", (), {"data": []})()


class _Client:
    def __init__(self, store: dict | None = None):
        self.store = store or {}

    def table(self, name: str):
        return _Query(name, self.store)


def test_get_company_id_uses_config_value(monkeypatch):
    monkeypatch.delenv("SUPABASE_COMPANY_ID", raising=False)
    cfg = {"online_sync": {"company_id": "company-from-config"}}
    assert device.get_company_id(cfg, _Client()) == "company-from-config"


def test_get_company_id_uses_env_override(monkeypatch):
    monkeypatch.setenv("SUPABASE_COMPANY_ID", "company-from-env")
    cfg = {"online_sync": {"company_id": "company-from-config"}}
    assert device.get_company_id(cfg, _Client()) == "company-from-env"


def test_get_company_id_auto_picks_single_membership(monkeypatch):
    monkeypatch.delenv("SUPABASE_COMPANY_ID", raising=False)
    client = _Client({"memberships": [{"company_id": "only-company"}]})
    assert device.get_company_id({}, client) == "only-company"


def test_get_company_id_returns_none_for_multiple_memberships(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_COMPANY_ID", raising=False)
    client = _Client(
        {
            "memberships": [
                {"company_id": "company-a"},
                {"company_id": "company-b"},
            ]
        }
    )
    assert device.get_company_id({}, client) is None
    captured = capsys.readouterr()
    assert "multiple companies" in captured.out


def test_create_device_supabase_includes_company_id():
    client = _Client()
    device.create_device_supabase(
        client,
        identifier="SPECT-01",
        name="Spectrometer",
        place="LAB",
        company_id="company-1",
        connection_details={"folder": "/tmp"},
    )
    table_name, payload = client.store["inserts"][-1]
    assert table_name == "device"
    assert payload["company_id"] == "company-1"
    assert payload["identifier"] == "SPECT-01"


def test_find_or_create_batch_supabase_includes_company_id():
    client = _Client()
    batch = find_or_create_batch_supabase(
        client,
        name="260009",
        date_str="08/01/2026",
        company_id="company-1",
    )
    table_name, payload = client.store["inserts"][-1]
    assert table_name == "batch"
    assert payload["company_id"] == "company-1"
    assert payload["name"] == "260009"
    assert batch["company_id"] == "company-1"
