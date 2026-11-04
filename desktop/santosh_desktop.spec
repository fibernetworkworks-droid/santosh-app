# -*- mode: python ; coding: utf-8 -*-
# Canonical Windows build for SantoshDesktop.exe (PyInstaller >= 6).
#   cd desktop
#   pip install -r requirements.txt pyinstaller
#   pyinstaller --noconfirm santosh_desktop.spec
# Output: dist/SantoshDesktop.exe  (onefile, no console window)
#
# Why the excludes: the desktop only takes screenshots (ImageGrab -> JPEG/PNG)
# and never decodes AVIF images. Newer Pillow Windows wheels ship a native
# PIL/_avif.cpXXX-win_amd64.pyd; bundling it made first-launch extraction slow
# and fragile (some antivirus products interfere with %TEMP%\_MEIxxxx
# extraction -> "Failed to extract PIL_.avif... decompression resulted in
# return code -1!"). Excluding it removes that failure point entirely and
# shrinks the exe.

from PyInstaller.utils.hooks import collect_submodules

import os

# v1.8.0 W2b: the PowerToys Run plugin payload (Community.PowerToys.Run.Plugin.Hoola.dll +
# plugin.json + Images) is built by build-desktop.yml BEFORE PyInstaller runs and staged at
# desktop/ptrun_payload/. It rides inside the exe (extracted to %TEMP%\_MEIxxxx\ptrun) so
# Hoola can install it itself to %LOCALAPPDATA%\...\PowerToys Run\Plugins\Hoola (pt_run.py).
# Dev machines without the payload build the exe exactly as before.
_ptrun = os.path.join(SPECPATH, "ptrun_payload")
datas = []
# v1.9.0 W3: the browser extension payload (manifest.json + background.js + popup/options +
# icons) is staged by build-desktop.yml at desktop/ext_payload/ and rides inside the exe
# (extracted to %TEMP%\_MEIxxxx\ext) so ext_install.py can copy it to
# %LOCALAPPDATA%\Hoola\chrome-extension for chrome://extensions 'Load unpacked'.
_ext = os.path.join(SPECPATH, "ext_payload")
if os.path.isdir(_ext):
    for _root, _dirs, _files in os.walk(_ext):
        for _f in _files:
            _p = os.path.join(_root, _f)
            _rel = os.path.relpath(_p, _ext)
            datas.append((_p, os.path.join("ext", os.path.dirname(_rel)) if os.path.dirname(_rel) else "ext"))
if os.path.isdir(os.path.join(_ptrun, "Images")):
    for _f in os.listdir(_ptrun):
        _p = os.path.join(_ptrun, _f)
        if os.path.isfile(_p):
            datas.append((_p, "ptrun"))
    for _f in os.listdir(os.path.join(_ptrun, "Images")):
        datas.append((os.path.join(_ptrun, "Images", _f), os.path.join("ptrun", "Images")))

a = Analysis(
    ["launcher.py"],
    pathex=[SPECPATH],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # carried over from the old CI command line (websockets 12 lazy-imports these)
        "websockets.asyncio.client",
        "websockets.legacy.client",
        # pypdf lazy-imports its submodules; collect them all (old CI: --collect-submodules pypdf)
        *collect_submodules("pypdf"),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PIL._avif",           # native AVIF codec (not used, ~1.5 MB, fragile to extract)
        "PIL.AvifImagePlugin", # AVIF plugin registration
        "pillow_avif",         # third-party pillow-avif-plugin, if installed on the build PC
        "PIL._imagingtk",      # not used (the app's UI is tkinter itself, not PIL-based)
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SantoshDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX-packed exes trip antivirus false positives; never enable
    upx_exclude=[],
    runtime_tmpdir=None,     # onefile: payload extracts to %TEMP%\_MEIxxxx at launch
    console=False,           # windowed app (Tk); matches the previously shipped exe
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
