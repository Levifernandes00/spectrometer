# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: onedir build for spectrometer.exe (Windows production)."""

from pathlib import Path

block_cipher = None

project_root = Path(SPEC).resolve().parent.parent
src_dir = project_root / "src"

a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=[(str(project_root / "config.example.json"), ".")],
    hiddenimports=[
        "pypdf",
        "watchdog",
        "watchdog.observers",
        "watchdog.events",
        "websockets",
        "supabase",
        "httpx",
        "httpcore",
        "anyio",
        "h11",
        "h2",
        "hpack",
        "hyperframe",
        "certifi",
        "idna",
        "sniffio",
        "postgrest",
        "realtime",
        "storage3",
        "supabase_auth",
        "supabase_functions",
        "pydantic",
        "pydantic_core",
        "dotenv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="spectrometer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Spectrometer",
)
