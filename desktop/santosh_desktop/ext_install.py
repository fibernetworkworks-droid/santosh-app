"""The Hoola browser extension install/uninstall (user-level, no admin) - the W3 'send page' door.

W3 of the Platforms plan (owner: 'W3 (web extension)'): an MV3 Chromium extension (Chrome / Edge /
Brave) that sends the page she is reading - link, title, her selection - into the Hoola conversation
through the W3 quick-ask lane. Chrome/Edge allow off-store extensions only as 'Load unpacked' from a
STABLE folder (developer-mode, her own click - the honest path the community plugins also take), so
Hoola ships the extension INSIDE SantoshDesktop.exe (PyInstaller datas, ext_payload built by CI)
and copies it to %LOCALAPPDATA%\\Hoola\\chrome-extension on her word - the folder she selects once
in chrome://extensions. Upgrades = the same install again (whole-folder replace, Chrome picks the
new files on the extension's reload); uninstall deletes only Hoola's own folder.

This module NEVER touches browser policies, never writes registry, never auto-starts anything -
the pt_run.py / app_paths.py / autostart.py discipline: kisi doosre user ko chhoot nahi.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

EXT_DIR_NAME = "chrome-extension"


def install_root() -> Path:
    """Hoola's own user-level folder (the stable path she selects in chrome://extensions once)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Hoola" / EXT_DIR_NAME


def supported() -> bool:
    return sys.platform == "win32"


def open_folder() -> None:
    """Reveal the installed folder in Explorer - 'Load unpacked' needs it selected by hand."""
    d = install_root()
    if d.is_dir() and sys.platform == "win32":
        os.startfile(str(d))  # noqa: S606 - explorer at her own folder, her own click


def installed() -> bool:
    d = install_root()
    try:
        meta = json.loads((d / "manifest.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return bool(meta.get("version")) and (d / "background.js").is_file()


def _payload(source_dir: str | None) -> Path | None:
    """The bundled extension payload: PyInstaller extracts datas to sys._MEIPASS/ext (frozen);
    the dev tree keeps desktop/ext/hoola-extension beside the module for tests / dev runs."""
    if source_dir:
        p = Path(source_dir)
        return p if (p / "manifest.json").is_file() else None
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
    else:
        base = Path(__file__).parent
    p = base / "ext"
    return p if (p / "manifest.json").is_file() else None


def set_enabled(on: bool, source_dir: str | None = None) -> dict:
    """Files lagao / hatao. Jawab wahi dict jo chat mein dikh sakti hai (Hinglish message ke saath)."""
    if not supported():
        return {"ok": False, "supported": False,
                "message": "Browser extension abhi Windows installer ke saath lagti hai (Chrome / Edge)."}
    if on:
        return install(source_dir)
    return uninstall()


def install(source_dir: str | None = None) -> dict:
    """Copy the bundled extension folder to Hoola's own stable folder (whole-folder replace =
    upgrade). Nothing outside Hoola's own folder is touched."""
    src = _payload(source_dir)
    if src is None:
        return {"ok": False, "supported": True,
                "message": "Extension ki files is SantoshDesktop build mein nahi mili - naya exe install kijiye."}
    try:
        meta = json.loads((src / "manifest.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return {"ok": False, "supported": True,
                "message": f"Extension ka manifest.json padh nahi paaya: {type(e).__name__}"}
    if int(meta.get("manifest_version", 0)) != 3:
        return {"ok": False, "supported": True,
                "message": "Extension ka manifest MV3 nahi hai - naya exe install kijiye."}
    if not (src / "background.js").is_file():
        return {"ok": False, "supported": True,
                "message": "Extension ka background.js is build mein nahi mila - naya exe install kijiye."}
    dest = install_root()
    try:
        if dest.exists():
            shutil.rmtree(dest)                 # upgrade: the old copy goes whole
        dest.mkdir(parents=True)
        for item in src.iterdir():
            if item.is_dir():
                shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest / item.name)
    except OSError as e:
        return {"ok": False, "supported": True,
                "message": f"Extension copy nahi ho payi: {type(e).__name__}: {e}"}
    return {"ok": True, "supported": True, "dir": str(dest), "version": meta.get("version", ""),
            "message": "Extension ki files lag gayi hain - chrome://extensions kholiye, Developer mode "
                       "on kijiye, 'Load unpacked' se yeh folder chuniye: " + str(dest)}


def uninstall() -> dict:
    """Delete only Hoola's own extension folder; 'pehle se nahi thi' stays a calm no-op.
    Browser se 'Remove' uska apna kaam hai (Chrome khud us folder ko chhod deta hai)."""
    dest = install_root()
    if not dest.exists():
        return {"ok": True, "supported": True,
                "message": "Extension pehle se nahi lagi thi - kuch badla nahi."}
    try:
        shutil.rmtree(dest)
    except OSError as e:
        return {"ok": False, "supported": True,
                "message": f"Extension folder delete nahi hua: {type(e).__name__}: {e}"}
    return {"ok": True, "supported": True,
            "message": "Extension ki files hata di (browser mein bhi 'Remove' kar dijiye)."}
