SPECTROMETER WINDOWS QUICK START
================================

Install (automated)
-------------------

From an elevated or normal PowerShell, after building or downloading the release zip:

  .\packaging\install_windows.ps1 `
    -InstallDir "C:\Arca\Spectrometer" `
    -SpectrometerFolder "C:\Spectrometer\Export" `
    -DatabasePath "C:\Arca\database.db"

This will:
- Copy spectrometer.exe into the install folder
- Write config.json with your paths
- Create a Startup shortcut so the watcher runs on login

Manual install
--------------

1) Unzip the release into a permanent folder, for example:
   C:\Arca\Spectrometer
   or
   %LOCALAPPDATA%\Spectrometer

2) Edit config.json (see packaging\config.windows.example.json for Windows paths):
   - folder: where the spectrometer drops PDF/TXT exports
   - database: absolute path to shared database.db (must be writable)
   - identifier, device.name, device.place

3) Run spectrometer.exe once to validate:
   spectrometer.exe --once

Start with Windows (Startup folder)
-----------------------------------

If you did not use install_windows.ps1:

1) Press Win + R and run:
   shell:startup

2) Create a shortcut to spectrometer.exe in that Startup folder.
   Set "Start in" to the install folder.

3) Reboot or sign out/in to verify automatic startup.

Build from source (Windows)
---------------------------

  .\packaging\build_windows.ps1

Output: dist\Spectrometer\spectrometer.exe

Test the build:

  dist\Spectrometer\spectrometer.exe --once

Notes
-----

- config.json must live next to spectrometer.exe.
- On first run, if config.json is missing, the app copies config.example.json.
- Use absolute paths for folder and database on Windows.
- For shared oxpecker DB, point database to the same database.db all apps use.
- For Online Sync, set online_sync.company_id when your Supabase user belongs
  to more than one company.
