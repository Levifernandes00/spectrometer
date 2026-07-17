# Spectrometer Integration

Watches a spectrometer output folder, parses result files, and stores them in either Supabase (online sync) or a local SQLite database (offline fallback).

## Development setup (macOS/Linux)

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
python src/main.py --once   # validate
python src/main.py          # run watcher
```

## Windows production deployment

### Build the exe

On a Windows machine (or via GitHub Actions):

```powershell
.\packaging\build_windows.ps1
```

Output: `dist\Spectrometer\spectrometer.exe` (onedir bundle — ship the whole folder).

CI: push a tag `v*` or run the **Build Spectrometer Windows EXE** workflow manually. Download the artifact from GitHub Actions.

### Install on a lab PC

```powershell
.\packaging\install_windows.ps1 `
  -InstallDir "C:\Arca\Spectrometer" `
  -SpectrometerFolder "C:\Spectrometer\Export" `
  -DatabasePath "C:\Arca\database.db"
```

This writes `config.json`, copies the exe, and adds a **Startup folder shortcut** so the watcher starts on login.

**Operator guide:** [`packaging/WINDOWS_SETUP.md`](packaging/WINDOWS_SETUP.md)

See also [`packaging/WINDOWS_README.txt`](packaging/WINDOWS_README.txt) and [`packaging/config.windows.example.json`](packaging/config.windows.example.json) for path examples.

### Windows path guidance

| Setting | Example | Notes |
|---|---|---|
| `folder` | `C:\Spectrometer\Export` | Absolute path to instrument output |
| `database` | `C:\Arca\database.db` | Absolute path to shared oxpecker DB |
| Install dir | `C:\Arca\Spectrometer` | Keep exe + config.json together |

First run without `config.json`: the exe auto-creates it from bundled `config.example.json`. Edit paths before production use, or use `install_windows.ps1`.

## Database backends

The app writes the same logical data (device, batch, results) but uses **one backend per run**:

1. **Supabase** — if `online_sync` URL/key plus email/password are set and `company_id` resolves.
2. **Local SQLite** — otherwise, using the path in `config["database"]` (shared `database.db` with oxpecker).

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

Result rows include oxpecker-compatible `obs` JSON with fusion, material, furnace (Peč), date, and hour when parsed from PDFs.

Supabase tables are assumed to already exist in your project; this integration only reads/writes via the Supabase client.
