"""Win+R se 'hoola' likhkar Hoola Desktop kholna (HKCU App Paths alias - current user only, no admin).

v1.7.0 W2a of the Platforms plan (owner: 'W2 - LAUNCHER --- START A WORK'): Windows ka apna App Paths
mechanism - HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\hoola.exe ka default value
SantoshDesktop.exe ki poori path point karta hai, to Windows khud Win+R 'hoola' ko us exe tak pahuncha
deta hai (Start menu / Run dono isi se chalte hain). User-level key: no admin, kisi doosre user ko chhoot
nahi, Run-key nahi, kuch auto-start nahi hota - sirf ek alias. autostart.py ka twin module (same style:
lazy winreg import, sys.platform guards, chhota surface).
"""
from __future__ import annotations

import sys
from pathlib import PureWindowsPath

KEY = r"Software\Microsoft\Windows\CurrentVersion\App Paths\hoola.exe"
COMMAND = "hoola"


def _exe() -> str:
    return sys.executable          # frozen: SantoshDesktop.exe khud


def supported() -> bool:
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            winreg.QueryValueEx(k, "")
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> dict:
    """Alias jodo / hatao. Jawab wahi dict jo chat mein dikh sakti hai (Hinglish message ke saath)."""
    if sys.platform != "win32":
        return {"ok": False, "on": False, "supported": False,
                "message": "Yeh alias sirf Windows PC par banta hai."}
    if on and not getattr(sys, "frozen", False):
        return {"ok": False, "on": False, "supported": False,
                "message": "Dev mode mein alias nahi banta - yeh installed SantoshDesktop.exe ke saath banta hai."}
    import winreg
    if on:
        exe = _exe()
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}"')
            winreg.SetValueEx(k, "Path", 0, winreg.REG_SZ, str(PureWindowsPath(exe).parent))
        return {"ok": True, "on": True, "supported": True, "command": COMMAND, "exe": exe,
                "message": "Ab Win+R dabakar 'hoola' likhne se Hoola Desktop khul jaayega."}
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, KEY)
        return {"ok": True, "on": False, "supported": True,
                "message": "Win+R wala 'hoola' alias hata diya."}
    except OSError:
        return {"ok": True, "on": False, "supported": True,
                "message": "Alias pehle se nahi tha - kuch badla nahi."}
