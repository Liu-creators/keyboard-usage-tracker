# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

# Keep PyInstaller from recursively collecting every optional backend/module.
hiddenimports = [
    "pynput.keyboard._darwin",
    "pynput.keyboard._base",
    "pynput._util.darwin",
    "rumps.rumps",
]
icon_path = str(Path("KeyboardUsageTracker.icns").resolve())

a = Analysis(
    ["keyboard_menu_app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="KeyboardUsageTracker",
          console=False, debug=False, bootloader_ignore_signals=False,
          strip=False, upx=True, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True,
               upx_exclude=[], name="KeyboardUsageTracker")
app = BUNDLE(coll, name="KeyboardUsageTracker.app", icon=icon_path,
             bundle_identifier="com.keyboardusagetracker.app")
