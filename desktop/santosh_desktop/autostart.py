"""Start Santosh Desktop when the user signs in to Windows (current user only, no admin)."""
from __future__ import annotations

import sys

KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "SantoshDesktop"


def _cmd() -> str:
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return f'"{exe}" --background'
    return f'"{exe}" -m santosh_desktop --background'


def supported() -> bool:
    return sys.platform == "win32"


def enabled() -> bool:
    if not supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            winreg.QueryValueEx(k, NAME)
            return True
    except OSError:
        return False


def set_enabled(on: bool) -> None:
    if not supported():
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, _cmd())
        else:
            try:
                winreg.DeleteValue(k, NAME)
            except OSError:
                pass
