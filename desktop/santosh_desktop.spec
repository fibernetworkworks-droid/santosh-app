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

a = Analysis(
    ["launcher.py"],
    pathex=[SPECPATH],
    binaries=[],
    datas=[],
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
