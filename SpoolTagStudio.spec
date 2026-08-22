# -*- mode: python ; coding: utf-8 -*-

import sys

platform_hiddenimports = ["engineio.async_drivers.threading"]
platform_excludes = ["eventlet", "gevent", "tkinter"]
if sys.platform == "win32":
    platform_hiddenimports.extend([
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
    ])
elif sys.platform.startswith("linux"):
    platform_hiddenimports.extend([
        "webview.platforms.gtk",
        "gi",
        "gi.repository.Gdk",
        "gi.repository.Gio",
        "gi.repository.GLib",
        "gi.repository.Gtk",
    ])
    platform_excludes.extend([
        "IPython",
        "jedi",
        "matplotlib",
        "numpy",
        "pandas",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "pytest",
        "qtpy",
    ])

app_icon = "anycubic_nfc_app/static/images/spooltag-icon.ico" if sys.platform == "win32" else None


a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("anycubic_nfc_app/templates", "anycubic_nfc_app/templates"),
        ("anycubic_nfc_app/static", "anycubic_nfc_app/static"),
    ],
    hiddenimports=platform_hiddenimports,
    hookspath=[],
    hooksconfig={
        "gi": {
            "icons": ["Adwaita"],
            "themes": ["Adwaita"],
            "languages": ["en"],
        },
    },
    runtime_hooks=[],
    excludes=platform_excludes,
    noarchive=False,
    optimize=1,
)
if sys.platform.startswith("linux"):
    a.binaries = [
        binary for binary in a.binaries
        if binary[0] not in {"libgcc_s.so.1", "libstdc++.so.6"}
    ]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SpoolTagStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=app_icon,
    codesign_identity=None,
    entitlements_file=None,
)
