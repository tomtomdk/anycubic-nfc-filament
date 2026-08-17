# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("anycubic_nfc_app/templates", "anycubic_nfc_app/templates"),
        ("anycubic_nfc_app/static", "anycubic_nfc_app/static"),
    ],
    hiddenimports=[
        "engineio.async_drivers.threading",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["eventlet", "gevent", "tkinter"],
    noarchive=False,
    optimize=1,
)
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
    icon="anycubic_nfc_app/static/images/spooltag-icon.ico",
    codesign_identity=None,
    entitlements_file=None,
)
