# Spectrometer — Windows setup

This guide is for installing and running `spectrometer.exe` on a lab PC. It watches a folder for spectrometer PDF/TXT exports and writes parsed results into a shared SQLite `database.db` (used by oxpecker and other Arca apps).

## Requirements

- Windows 10 or later
- A permanent install folder (e.g. `C:\Arca\Spectrometer`)
- The spectrometer instrument export folder path (where PDF/TXT files appear)
- A writable path for the shared database (e.g. `C:\Arca\database.db`)
- The full `Spectrometer` release folder from the build (not just the exe alone)

## Quick install (recommended)

Open PowerShell, go to the folder containing the release files, and run:

```powershell
.\packaging\install_windows.ps1 `
  -InstallDir "C:\Arca\Spectrometer" `
  -SpectrometerFolder "C:\Spectrometer\Export" `
  -DatabasePath "C:\Arca\database.db"
```

This will:

1. Copy `spectrometer.exe` and dependencies into `C:\Arca\Spectrometer`
2. Create `config.json` with your paths
3. Add a **Startup shortcut** so the watcher starts automatically when you log in

Validate:

```powershell
C:\Arca\Spectrometer\spectrometer.exe --once
```

## Manual install

1. Unzip the release into a permanent folder, e.g. `C:\Arca\Spectrometer`.
2. Create or edit `config.json` next to `spectrometer.exe` (see example below).
3. Run once to validate:

   ```powershell
   cd C:\Arca\Spectrometer
   .\spectrometer.exe --once
   ```

4. For continuous watching (production), run without `--once`:

   ```powershell
   .\spectrometer.exe
   ```

If `config.json` is missing on first run, the app creates one from `config.example.json`. Edit the paths before relying on it in production.

## config.json fields

| Key | Example | Description |
|---|---|---|
| `folder` | `C:\Spectrometer\Export` | Folder where the spectrometer saves PDF/TXT files (use an absolute path) |
| `database` | `C:\Arca\database.db` | Shared SQLite database (must be writable by your user) |
| `identifier` | `LABORATORIO` | Stable device identifier stored in the database |
| `device.name` | `Spectrometer LAB-01` | Display name for this instrument |
| `device.place` | `LABORATÓRIO` | Location label |
| `websocket` | optional | Oxpecker WebSocket publish settings |
| `online_sync` | optional | Supabase credentials (omit for local-only mode) |

Example (also in `config.windows.example.json`):

```json
{
  "folder": "C:\\Spectrometer\\Export",
  "device": {
    "name": "Spectrometer LAB-01",
    "place": "LABORATÓRIO",
    "category": "Spectrometer"
  },
  "identifier": "SPECT-LAB-01",
  "database": "C:\\Arca\\database.db",
  "websocket": {
    "enabled": false,
    "url": "ws://192.168.1.50:9001",
    "open_timeout": 3
  }
}
```

## Auto-start on boot

The install script creates a shortcut in your Windows Startup folder automatically.

To do it manually:

1. Press `Win + R`, type `shell:startup`, press Enter.
2. Create a shortcut to `C:\Arca\Spectrometer\spectrometer.exe`.
3. Set **Start in** to `C:\Arca\Spectrometer`.
4. Sign out and back in (or reboot) to confirm the watcher starts.

## Verify it works

After `spectrometer.exe --once`, you should see output similar to:

```
Install dir: C:\Arca\Spectrometer
Config: C:\Arca\Spectrometer\config.json
Connected to local database: C:\Arca\database.db
Device: Spectrometer LAB-01 | identifier: SPECT-LAB-01
Processed 1 file(s)
Results inserted into database.
```

When running without `--once`, the console should show `Watching folder: ...` and stay open.

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `attempt to write a readonly database` | DB file or folder not writable | Check file permissions; avoid installing under `Program Files` without admin |
| `Configured folder does not exist` | Wrong `folder` path in config | Use absolute path; create the folder if needed |
| `Processed 0 file(s)` | Files already ingested for that date/time | Expected if re-running the same export; drop a new file to test |
| App closes immediately on boot | Shortcut missing **Start in** | Set Start in to the install folder |
| No chemistry in oxpecker | Wrong `database` path | Point to the same `database.db` other apps use |

## Files in the install folder

| File | Purpose |
|---|---|
| `spectrometer.exe` | Main application |
| `config.json` | Your settings (created by you or install script) |
| `config.example.json` | Template reference |
| `WINDOWS_SETUP.md` | This guide |
| `_internal/` | Bundled Python libraries (do not delete) |
