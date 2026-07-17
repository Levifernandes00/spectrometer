# Build spectrometer.exe for Windows (PyInstaller onedir).
# Run from the spectrometer repo root in PowerShell:
#   .\packaging\build_windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Venv = Join-Path $Root ".venv-build"
$Python = Join-Path $Venv "Scripts\python.exe"
$Pip = Join-Path $Venv "Scripts\pip.exe"

if (-not (Test-Path $Python)) {
    python -m venv $Venv
}

& $Pip install --upgrade pip
& $Pip install -r requirements-build.txt
& $Python -m PyInstaller packaging\spectrometer.spec --noconfirm --clean

$OutDir = Join-Path $Root "dist\Spectrometer"
if (-not (Test-Path (Join-Path $OutDir "spectrometer.exe"))) {
    throw "Build failed: dist\Spectrometer\spectrometer.exe not found"
}

Copy-Item -Path (Join-Path $Root "config.example.json") -Destination $OutDir -Force
Copy-Item -Path (Join-Path $Root "packaging\WINDOWS_README.txt") -Destination $OutDir -Force

Write-Host ""
Write-Host "Build complete: $OutDir"
Write-Host "Test: dist\Spectrometer\spectrometer.exe --once"
