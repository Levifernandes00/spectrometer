# Spectrometer Integration

Watches a spectrometer output folder, parses result files, and stores them in either Supabase (online sync) or a local SQLite database (offline fallback).

## Setup

Create the virtual environment with Homebrew/system Python, **not** Conda base Python (Conda can ship a `libsqlite3` that breaks `import sqlite3`):

```bash
/usr/local/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and adjust paths. Prefer the shared oxpecker DB:

```json
"database": "../database.db"
```

That path must be user-writable or SQLite will fail with `attempt to write a readonly database`.

```bash
python src/main.py --once
```

## Database backends

The app writes the same logical data (device, batch, results) but uses **one backend per run**:

1. **Supabase** — if `online_sync` URL/key plus email/password are set and `company_id` resolves.
2. **Local SQLite** — otherwise, using the path in `config["database"]` (shared `../database.db` with oxpecker).

Supabase and SQLite are not dual-written in the same execution.

## Schema: Supabase vs local SQLite

Local SQLite matches the **oxpecker shared schema** (lowercase tables, integer autoincrement IDs). Tables are created on startup if missing (`src/device.py`, `src/db.py`).

| Aspect | Supabase | Local SQLite (shared `database.db`) |
|---|---|---|
| Tables | `company_user`, `device`, `batch`, `result` | `device`, `batch`, `result` |
| IDs | integer (Postgres) | integer autoincrement (omit on insert) |
| `company_id` | required on `device` / `batch` | stored; defaults to `"default"` offline |
| `connection_details` | JSON object | JSON string (`TEXT`) |
| batch `date` | ISO `YYYY-MM-DD` | ISO `YYYY-MM-DD` |

Supabase tables are assumed to already exist in your project; this integration only reads/writes via the Supabase client.
