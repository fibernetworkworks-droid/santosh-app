"""PowerToys Run plugin 'hoola' install/uninstall (user-level, no admin) - the W2b launcher door.

W2b of the Platforms plan (owner: 'W2b - PowerToys Run plugin'): PowerToys Run plugins are
folders under %LOCALAPPDATA%\\Microsoft\\PowerToys\\PowerToys Run\\Plugins\\<Name> holding
plugin.json + the plugin DLL (Microsoft's own third-party plugin guide installs exactly this
way). Hoola ships its plugin INSIDE SantoshDesktop.exe (PyInstaller datas, ptrun_payload
built by CI) and copies it here on her word - same user-level, no-admin discipline as
app_paths.py (W2a) and autostart.py: kisi doosre user ko chhoot nahi, machine-wide folder
nahi, kuch auto-start nahi. PowerToys na ho to actions.py wahi Ctrl+Alt+H hotkey door
(quickkey.py) on karta hai - yeh module sirf bata deta hai ki PowerToys hai ya nahi.

Upgrades = the same install again (the old folder is replaced whole, like the community
plugin installers do); uninstall deletes only Hoola's own folder.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

PLUGIN_NAME = "Hoola"
ID = "162E72D3C1D7464E865293A276993A7B"          # plugin.json / Main.PluginID - never changes
ACTION_KEYWORD = "hoola"


def plugins_root() -> Path:
    """PowerToys Run's per-user plugin folder (Microsoft's documented community-plugin location)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Microsoft" / "PowerToys" / "PowerToys Run" / "Plugins"


def plugin_dir() -> Path:
    return plugins_root() / PLUGIN_NAME


def supported() -> bool:
    return sys.platform == "win32"


def power_toys_present() -> bool:
    """Per-user install (%LOCALAPPDATA%\\PowerToys), machine install (Program Files), or the
    Run plugins root itself (PowerToys ran at least once)."""
    if sys.platform != "win32":
        return False
    la = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    checks = [Path(la) / "PowerToys" / "PowerToys.exe", Path(pf) / "PowerToys" / "PowerToys.exe"]
    if la:
        checks.append(Path(la) / "Microsoft" / "PowerToys" / "PowerToys Run" / "Plugins")
    return any(c.exists() for c in checks if str(c))


def installed() -> bool:
    d = plugin_dir() / "plugin.json"
    if not d.is_file():
        return False
    try:
        meta = json.loads(d.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return bool(meta.get("ExecuteFileName")) and (plugin_dir() / meta["ExecuteFileName"]).is_file()


def _payload(source_dir: str | None) -> Path | None:
    """The bundled plugin payload: PyInstaller extracts datas to sys._MEIPASS (frozen); the
    dev tree keeps it beside the module only if someone built it there. Tests pass an explicit
    source_dir."""
    if source_dir:
        p = Path(source_dir)
        return p if (p / "plugin.json").is_file() else None
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
    else:
        base = Path(__file__).parent
    p = base / "ptrun"
    return p if (p / "plugin.json").is_file() else None


def set_enabled(on: bool, source_dir: str | None = None) -> dict:
    """Plugin jodo / hatao. Jawab wahi dict jo chat mein dikh sakti hai (Hinglish message ke saath).
    PowerToys na hone par install ki jagah hotkey door ka ishara - actions.py use on karta hai."""
    if not supported():
        return {"ok": False, "pt_present": False, "plugin": False, "supported": False,
                "message": "PowerToys Run plugin sirf Windows PC par lagta hai."}
    pt = power_toys_present()
    if on:
        if not pt:
            return {"ok": True, "pt_present": False, "plugin": False, "supported": True,
                    "message": "PowerToys is PC par nahi hai - Hoola wahi kaam Ctrl+Alt+H hotkey se karti hai."}
        out = install(source_dir)
        out["pt_present"] = True
        return out
    out = uninstall()
    out["pt_present"] = pt
    return out


def install(source_dir: str | None = None) -> dict:
    """Copy the bundled plugin folder into PowerToys Run's per-user plugins folder (whole-folder
    replace = upgrade). Nothing outside Hoola's own folder is touched."""
    src = _payload(source_dir)
    if src is None:
        return {"ok": False, "plugin": False, "supported": True,
                "message": "Plugin ki files is SantoshDesktop build mein nahi mili - naya exe install kijiye."}
    try:
        meta = json.loads((src / "plugin.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return {"ok": False, "plugin": False, "supported": True,
                "message": f"Plugin ki plugin.json padh nahi paaya: {type(e).__name__}"}
    dll = str(meta.get("ExecuteFileName") or "")
    if not dll or not (src / dll).is_file():
        return {"ok": False, "plugin": False, "supported": True,
                "message": "Plugin ki DLL is build mein nahi mili - naya exe install kijiye."}
    dest = plugin_dir()
    try:
        if dest.exists():
            shutil.rmtree(dest)                 # upgrade: the old copy goes whole
        dest.mkdir(parents=True)
        shutil.copy2(src / "plugin.json", dest / "plugin.json")
        shutil.copy2(src / dll, dest / dll)
        if (src / "Images").is_dir():
            shutil.copytree(src / "Images", dest / "Images", dirs_exist_ok=True)
    except OSError as e:
        return {"ok": False, "plugin": False, "supported": True,
                "message": f"Plugin copy nahi ho paya: {type(e).__name__}: {e}"}
    return {"ok": True, "plugin": True, "supported": True, "dir": str(dest), "keyword": ACTION_KEYWORD,
            "message": "PowerToys Run mein 'hoola' lag gaya - Alt+Space dabakar 'hoola' likhiye "
                       "(PowerToys ko ek baar restart kijiye taaki wo naya plugin dekhe)."}


def uninstall() -> dict:
    """Delete only Hoola's own plugin folder; 'pehle se nahi tha' stays a calm no-op (app_paths undo style)."""
    dest = plugin_dir()
    if not dest.exists():
        return {"ok": True, "plugin": False, "supported": True,
                "message": "Plugin pehle se nahi laga tha - kuch badla nahi."}
    try:
        shutil.rmtree(dest)
    except OSError as e:
        return {"ok": False, "plugin": True, "supported": True,
                "message": f"Plugin hata nahi paaya: {type(e).__name__}: {e}"}
    return {"ok": True, "plugin": False, "supported": True,
            "message": "PowerToys Run wala 'hoola' plugin hata diya."}
