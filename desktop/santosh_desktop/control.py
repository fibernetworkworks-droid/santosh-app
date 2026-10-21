"""Santosh can use this PC like a person: see the screen, open apps, click, type, press keys, scroll.

Off by default. The PC owner turns on "Hoola ko PC chalane dein" in Santosh Desktop; while Santosh is working a
banner shows on the PC and the owner can stop it any time (Rokiye button, or throw the mouse into the top-left
corner: pyautogui's fail-safe). Santosh types Aadhaar / PAN / any number the owner gave (v0.81, her decision); passwords, OTPs, PINs and card
numbers stay hers, and it asks on the phone before anything that sends, submits, deletes, pays or installs.
"""
from __future__ import annotations

import base64
import io
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

MAX_WIDTH = 1280
_dpi_done = False

BLOCKED_KEYS = {("win", "l")}                                  # locking the PC would end the session for the owner


class ControlError(Exception):
    pass


def _dpi_aware() -> None:
    """Make screenshots and mouse use the same (physical) pixels on scaled Windows displays."""
    global _dpi_done
    if _dpi_done or sys.platform != "win32":
        return
    _dpi_done = True
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _gui():
    _dpi_aware()
    try:
        import pyautogui
    except Exception as e:  # not installed / no display
        raise ControlError(f"PC control is not available on this computer ({type(e).__name__})")
    pyautogui.FAILSAFE = True      # mouse to the top-left corner stops everything
    pyautogui.PAUSE = 0.08
    return pyautogui


class Control:
    def __init__(self) -> None:
        self.scale = 1.0           # screen pixels per screenshot pixel
        self.on_activity = None    # set by the window app: shows the "Hoola is using this PC" banner

    def _touch(self, what: str) -> None:
        if self.on_activity:
            try:
                self.on_activity(what)
            except Exception:
                pass

    # ---------------- seeing ----------------
    def screen(self, max_width: int = MAX_WIDTH) -> dict[str, Any]:
        _dpi_aware()
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=False)
        except Exception as e:
            raise ControlError(f"Screenshot failed: {type(e).__name__}: {e}")
        w, h = img.size
        if w > max_width:
            self.scale = w / max_width
            img = img.resize((max_width, round(h / self.scale)))
        else:
            self.scale = 1.0
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=60, optimize=True)
        out = {"image_b64": base64.b64encode(buf.getvalue()).decode(), "width": img.size[0], "height": img.size[1],
               "screen": [w, h]}
        out.update(self.windows())
        return out

    def windows(self) -> dict[str, Any]:
        try:
            import pygetwindow as gw
            act = gw.getActiveWindow()
            titles = [t for t in gw.getAllTitles() if t.strip()][:30]
            return {"active_window": act.title if act else "", "windows": titles}
        except Exception:
            return {"active_window": "", "windows": []}

    # ---------------- doing ----------------
    def _xy(self, x: Any, y: Any) -> tuple[int, int]:
        try:
            return round(float(x) * self.scale), round(float(y) * self.scale)
        except (TypeError, ValueError):
            raise ControlError("x and y must be numbers (pixels on the last screenshot)")

    def act(self, op: str, x: Any = None, y: Any = None, text: str = "", keys: str = "", amount: int = 0,
            to_x: Any = None, to_y: Any = None) -> dict[str, Any]:
        op = (op or "").lower()
        if op in ("key", "hotkey") and tuple(p.strip().lower() for p in re.split(r"[+ ]+", keys or "") if p.strip()) in BLOCKED_KEYS:
            raise ControlError("That key combination is not allowed")
        g = _gui()
        self._touch(op)
        if op in ("click", "double_click", "right_click", "move"):
            px, py = self._xy(x, y)
            if op == "click":
                g.click(px, py)
            elif op == "double_click":
                g.doubleClick(px, py)
            elif op == "right_click":
                g.rightClick(px, py)
            else:
                g.moveTo(px, py, duration=0.15)
        elif op == "drag":
            px, py = self._xy(x, y)
            qx, qy = self._xy(to_x, to_y)
            g.moveTo(px, py)
            g.dragTo(qx, qy, duration=0.4, button="left")
        elif op == "type":
            if not text:
                raise ControlError("Nothing to type")
            if text.isascii():
                g.write(text, interval=0.012)
            else:   # Hindi / Marathi text: paste through the clipboard
                self._paste(text)
        elif op in ("key", "hotkey"):
            parts = [p.strip().lower() for p in re.split(r"[+ ]+", keys or "") if p.strip()]
            if not parts:
                raise ControlError("Which keys?")
            if tuple(parts) in BLOCKED_KEYS:
                raise ControlError("That key combination is not allowed")
            if len(parts) == 1:
                g.press(parts[0])
            else:
                g.hotkey(*parts)
        elif op == "scroll":
            if x is not None and y is not None:
                g.moveTo(*self._xy(x, y))
            g.scroll(int(amount or -5) * 100)
        elif op == "wait":
            time.sleep(max(0.2, min(float(amount or 2), 10)))
        else:
            raise ControlError(f"Unknown control op '{op}'")
        time.sleep(0.35)
        return {"ok": True, "op": op}

    def _paste(self, text: str) -> None:
        g = _gui()
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception as e:
            raise ControlError(f"Could not type this text: {e}")
        g.hotkey("ctrl", "v")

    # ---------------- apps ----------------
    @staticmethod
    def _start_menu() -> list[Path]:
        dirs = []
        for base in (os.environ.get("ProgramData", r"C:\ProgramData"), os.environ.get("APPDATA", "")):
            if base:
                dirs.append(Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        out = []
        for d in dirs:
            if d.exists():
                out += [p for p in d.rglob("*.lnk") if "uninstall" not in p.name.lower()]
        return out

    def apps(self) -> dict[str, Any]:
        names = sorted({p.stem for p in self._start_menu()}, key=str.lower)
        return {"apps": names[:400], "count": len(names), **self.windows()}

    def open_app(self, name: str = "") -> dict[str, Any]:
        q = (name or "").strip().lower()
        if not q:
            raise ControlError("Which app?")
        self._touch("open " + name)
        found = [p for p in self._start_menu() if q == p.stem.lower()] or \
                [p for p in self._start_menu() if q in p.stem.lower()]
        if not found:
            aliases = {"notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe", "paint": "mspaint.exe",
                       "explorer": "explorer.exe", "file explorer": "explorer.exe", "cmd": None, "powershell": None}
            exe = aliases.get(q)
            if exe and sys.platform == "win32":
                os.startfile(exe)  # type: ignore[attr-defined]
                time.sleep(1.5)
                return {"opened": name}
            raise ControlError(f"'{name}' app not found on this PC. Use list_apps to see installed apps.")
        target = sorted(found, key=lambda p: len(p.stem))[0]
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            raise ControlError("Opening apps is supported on Windows")
        time.sleep(2.0)
        return {"opened": target.stem}

    def focus(self, title: str = "") -> dict[str, Any]:
        try:
            import pygetwindow as gw
        except Exception:
            raise ControlError("Window control not available")
        wins = [w for w in gw.getAllWindows() if title.lower() in (w.title or "").lower() and w.title.strip()]
        if not wins:
            raise ControlError(f"No open window matches '{title}'")
        w = wins[0]
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
        except Exception:
            pass
        time.sleep(0.5)
        return {"focused": w.title}
