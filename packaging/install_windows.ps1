# Install spectrometer on Windows: copy build, write config.json, add Startup shortcut.
#
# Example:
#   .\packaging\install_windows.ps1 `
#     -InstallDir "C:\Arca\Spectrometer" `
#     -SpectrometerFolder "C:\Spectrometer\Export" `
#     -DatabasePath "C:\Arca\database.db"

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,

    [Parameter(Mandatory = $true)]
    [string]$SpectrometerFolder,

    [Parameter(Mandatory = $true)]
    [string]$DatabasePath,

    [string]$Identifier = "SPECT-LAB-01",
    [string]$DeviceName = "Spectrometer LAB-01",
    [string]$DevicePlace = "LABORATÓRIO",
    [string]$SourceDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $SourceDir) {
    $SourceDir = Join-Path $Root "dist\Spectrometer"
}

if (-not (Test-Path (Join-Path $SourceDir "spectrometer.exe"))) {
    throw "spectrometer.exe not found in SourceDir: $SourceDir. Run packaging\build_windows.ps1 first."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $SpectrometerFolder | Out-Null

Copy-Item -Path (Join-Path $SourceDir "*") -Destination $InstallDir -Recurse -Force

$DbDir = Split-Path -Parent $DatabasePath
if ($DbDir -and -not (Test-Path $DbDir)) {
    New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
}

$config = @{
    folder = $SpectrometerFolder
    device = @{
        name = $DeviceName
        place = $DevicePlace
        category = "Spectrometer"
    }
    identifier = $Identifier
    database = $DatabasePath
    websocket = @{
        enabled = $false
        url = "ws://127.0.0.1:9001"
        open_timeout = 3
    }
}

$configPath = Join-Path $InstallDir "config.json"
$config | ConvertTo-Json -Depth 5 | Set-Content -Path $configPath -Encoding UTF8

$Startup = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $Startup "Spectrometer.lnk"
$ExePath = Join-Path $InstallDir "spectrometer.exe"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Spectrometer folder watcher"
$Shortcut.Save()

Write-Host ""
Write-Host "Installed to: $InstallDir"
Write-Host "Config:       $configPath"
Write-Host "Watch folder: $SpectrometerFolder"
Write-Host "Database:     $DatabasePath"
Write-Host "Startup link: $ShortcutPath"
Write-Host ""
Write-Host "Validate: $ExePath --once"
