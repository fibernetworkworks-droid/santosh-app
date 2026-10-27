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
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MAX_WIDTH = 1280
_dpi_done = False

# v1.4 browsers whose running process makes open_url land inside them (a new tab in HER browser, not whatever
# Windows calls the 'default' today)
_BROWSER_EXES = (("chrome", "Chrome"), ("msedge", "Edge"), ("brave", "Brave"), ("firefox", "Firefox"))

BLOCKED_KEYS = {("win", "l")}                                  # locking the PC would end the session for the owner

# names the PC must never open for Hoola even if the model finds a direct path (mirror of the server list)
BLOCKED_APP_WORDS = re.compile(r"\b(cmd|command prompt|powershell|windows terminal|terminal|regedit|registry|wsl|bash|"
                              r"task scheduler|group policy|gpedit|diskpart|format)\b", re.I)

# v1.3 the part of Windows behind the taskbar: AppUserModelIDs of Start-menu apps (normal + Store/UWP), cached
_uwp_cache: tuple[float, dict[str, str]] = (0.0, {})


def _uwp_apps() -> dict[str, str]:
    """Friendly name -> AppUserModelID for every app Windows knows (Start menu, Microsoft Store, preinstalled).
    Uses PowerShell's Get-StartApps once per 10 minutes and caches it; empty on non-Windows or when it fails."""
    global _uwp_cache
    t, cache = _uwp_cache
    if time.time() - t < 600:
        return cache
    out: dict[str, str] = {}
    if sys.platform == "win32":
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-StartApps | "
                                "ForEach-Object { '$($PSItem.Name)`t$($PSItem.AppID)' }"],
                               capture_output=True, timeout=15)
            for line in r.stdout.decode("utf-8", "ignore").splitlines():
                name, _, appid = line.partition("\t")
                name, appid = name.strip(), appid.strip()
                if name and appid and "!" in appid:      # real launchable apps (not control-panel entries)
                    out.setdefault(name.lower(), appid)
        except Exception:
            pass
    _uwp_cache = (time.time(), out)
    return out


def _virtual_screen() -> tuple[int, int, int, int]:
    """(left, top, width, height) of the WHOLE desktop across all monitors (primary when unknown)."""
    if sys.platform == "win32":
        try:
            import ctypes
            sm = ctypes.windll.user32.GetSystemMetrics
            x0, y0, w, h = sm(76), sm(77), sm(78), sm(79)   # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CX/CY
            if w > 0 and h > 0:
                return int(x0), int(y0), int(w), int(h)
        except Exception:
            pass
    try:
        from PIL import ImageGrab
        w, h = ImageGrab.grab().size
        return 0, 0, w, h
    except Exception:
        return 0, 0, 0, 0


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
        self.origin = (0, 0)       # v1.3 screen position of the screenshot's top-left corner (monitors left of the primary are negative)
        self.on_activity = None    # set by the window app: shows the "Hoola is using this PC" banner
        self._br_cache: tuple[float, str | None] = (0.0, None)   # v1.4 running-browser check (tasklist is slow; cached 30 s)

    def _touch(self, what: str) -> None:
        if self.on_activity:
            try:
                self.on_activity(what)
            except Exception:
                pass

    # ---------------- seeing ----------------
    def screen(self, max_width: int = MAX_WIDTH, monitor: str = "primary") -> dict[str, Any]:
        """v1.3 monitor="all" = every monitor stitched into one picture (a second screen is no longer blind).
        self.scale + self.origin turn screenshot pixels back into screen pixels for THIS capture; the server keeps
        the model's screenshots and the live-view frames on the same monitor and width, so a click always maps with
        the capture the model just looked at (the v0.91.1 rule)."""
        _dpi_aware()
        whole = (str(monitor or "primary").lower() == "all")
        bbox = None
        if whole:
            x0, y0, vw, vh = _virtual_screen()
            if vw > 0 and vh > 0:
                bbox = (x0, y0, x0 + vw, y0 + vh)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=whole, bbox=bbox)
        except Exception as e:
            raise ControlError(f"Screenshot failed: {type(e).__name__}: {e}")
        w, h = img.size
        if whole:
            self.origin = (bbox[0], bbox[1]) if bbox else (0, 0)
        else:
            self.origin = (0, 0)
        if w > max_width:
            self.scale = w / max_width
            img = img.resize((max_width, round(h / self.scale)))
        else:
            self.scale = 1.0
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=80, optimize=True)   # v1.3 was 60: invoice digits stay readable
        out = {"image_b64": base64.b64encode(buf.getvalue()).decode(), "width": img.size[0], "height": img.size[1],
               "screen": [w, h], "monitor": "all" if whole else "primary", "origin": list(self.origin)}
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
            return (self.origin[0] + round(float(x) * self.scale),
                    self.origin[1] + round(float(y) * self.scale))
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
            # v1.3 long or mixed-language text goes through the clipboard (instant, no dropped keys);
            # the user's own clipboard is saved and put back. Short plain text still types key by key
            # (no clipboard side effects for OTP-style one-liners).
            if not text.isascii() or len(text) > 24:
                self._paste(text)
            else:
                g.write(text, interval=0.012)
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
        except Exception as e:
            # no clipboard: type it out instead (slower, but it lands)
            if text.isascii():
                g.write(text, interval=0.012)
                return
            raise ControlError(f"Could not type this text: {e}")
        saved = ""
        try:
            saved = pyperclip.paste() or ""
        except Exception:
            pass
        pyperclip.copy(text)
        g.hotkey("ctrl", "v")
        time.sleep(0.15)
        try:                          # her own copied text goes back after the paste
            pyperclip.copy(saved)
        except Exception:
            pass

    # ---------------- windows (v1.3: minimise / maximise / restore / close by title) ----------------
    def window_op(self, op: str = "", title: str = "") -> dict[str, Any]:
        try:
            import pygetwindow as gw
        except Exception:
            raise ControlError("Window control not available")
        op = (op or "").lower()
        if op not in ("minimize", "maximize", "restore", "close"):
            raise ControlError("op must be minimize, maximize, restore or close")
        wins = [w for w in gw.getAllWindows() if title.lower() in (w.title or "").lower() and w.title.strip()]
        if not wins:
            raise ControlError(f"No open window matches '{title}'")
        w = wins[0]
        self._touch(f"window {op}: {w.title[:60]}")
        try:
            getattr(w, {"minimize": "minimize", "maximize": "maximize",
                        "restore": "restore", "close": "close"}[op])()
        except Exception as e:
            raise ControlError(f"Could not {op} the window: {type(e).__name__}")
        time.sleep(0.5)
        return {"window": w.title, "op": op}

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
        if BLOCKED_APP_WORDS.search(q):
            raise ControlError("Santosh doesn't open command-line or system tools")
        self._touch("open " + name)
        found = [p for p in self._start_menu() if q == p.stem.lower()] or \
                [p for p in self._start_menu() if q in p.stem.lower()]
        if not found:
            aliases = {"notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe", "paint": "mspaint.exe",
                       "explorer": "explorer.exe", "file explorer": "explorer.exe", "cmd": None, "powershell": None}
            exe = aliases.get(q)
            if exe is None and sys.platform == "win32":
                # v1.3 Microsoft Store / UWP apps (Mail, Calculator, Teams, Photos...) by their real name
                uwp = _uwp_apps()
                appid = uwp.get(q) or next((v for k, v in uwp.items() if q in k), "")
                if appid:
                    os.startfile("shell:appsFolder\\" + appid)  # type: ignore[attr-defined]
                    time.sleep(2.0)
                    return {"opened": name}
                # v1.3 a full path to an installed program the Start menu missed ('C:\...\app.exe')
                if q.endswith(".exe") and "\\" in q:
                    p = Path(os.path.expandvars(q))
                    if p.is_file() and not BLOCKED_APP_WORDS.search(str(p)):
                        os.startfile(str(p))  # type: ignore[attr-defined]
                        time.sleep(2.0)
                        return {"opened": p.stem}
            if exe and sys.platform == "win32":
                os.startfile(exe)  # type: ignore[attr-defined]
                time.sleep(1.5)
                return {"opened": name}
            raise ControlError(f"'{name}' app not found on this PC. Use list_apps to see installed apps.")
        target = sorted(found, key=lambda p: len(p.stem))[0]
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", str(target.stem)])
        else:
            raise ControlError("Opening apps is supported on Windows")
        time.sleep(2.0)
        return {"opened": target.stem}

    def _running_browser(self) -> str | None:
        """v1.4 A browser with a window open right now (Chrome / Edge / Brave / Firefox), else None.
        tasklist runs once and is cached 30 s — this runs on every open_url."""
        if sys.platform != "win32":
            return None
        t, name = self._br_cache
        if time.time() - t < 30:
            return name
        name = None
        try:
            r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, timeout=12)
            procs = r.stdout.decode("utf-8", "ignore").lower()
            for exe, label in _BROWSER_EXES:
                if f'"{exe}.exe"' in procs:
                    name = label
                    break
        except Exception:
            name = None
        self._br_cache = (time.time(), name)
        return name

    def _focus_browser(self, label: str) -> bool:
        """v1.4 Bring the named browser's window to the front (True when one was found and focused)."""
        try:
            import pygetwindow as gw
        except Exception:
            return False
        try:
            wins = [w for w in gw.getAllWindows()
                    if label.lower() in (w.title or "").lower() and w.title.strip()]
        except Exception:
            return False
        if not wins:
            return False
        w = wins[0]
        try:
            if w.isMinimized:
                w.restore()
            w.activate()
        except Exception:
            pass
        time.sleep(0.5)
        return True

    def _wait_title_change(self, before: str, seconds: float = 8.0) -> str:
        """v1.4 Page-load signal without DevTools: the browser window title IS the active tab's title, so wait
        until it changes (page loaded) and then holds steady for two polls. Returns the settled title ('' = unknown)."""
        end = time.time() + max(1.0, seconds)
        last, same = "", 0
        while time.time() < end:
            time.sleep(0.4)
            try:
                import pygetwindow as gw
                act = gw.getActiveWindow()
                title = (act.title if act else "") or ""
            except Exception:
                return ""
            if title and title != before:
                if title == last:
                    same += 1
                    if same >= 2:
                        return title        # loaded and stable
                else:
                    last, same = title, 1
        return last

    def open_url(self, url: str = "") -> dict[str, Any]:
        """v1.4 Open a website in the browser she is ALREADY using (new tab in Chrome/Edge/Brave/Firefox) and wait
        for the page to load. Falls back to her default browser when none is running. http(s) only."""
        u = (url or "").strip()
        if not u:
            raise ControlError("Which site?")
        if "\\" in u or u.lower().endswith(".exe"):
            raise ControlError("That is not a website")
        # a leading scheme must already be http(s); only a scheme-less address gets https:// in front
        m = re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", u)
        if m and m.group(0)[:-1].lower() not in ("http", "https"):
            raise ControlError("Only http(s) websites open here")
        if not m:
            u = "https://" + u
        if urlparse(u).scheme.lower() not in ("http", "https") or not urlparse(u).netloc:
            raise ControlError("Only http(s) websites open here")
        self._touch("open " + u[:80])
        if sys.platform == "win32":
            label = self._running_browser()
            if label and self._focus_browser(label):
                try:
                    import pygetwindow as gw
                    act = gw.getActiveWindow()
                    before = (act.title if act else "") or ""
                except Exception:
                    before = ""
                g = _gui()
                g.hotkey("ctrl", "l")        # address bar of the running browser
                time.sleep(0.15)
                self._paste(u)               # clipboard: exact, instant, any language
                time.sleep(0.15)
                g.press("enter")
                title = self._wait_title_change(before, 8.0)
                return {"opened": u[:200], "in": f"{label} (new tab)", "title": title[:200], "loaded": bool(title)}
            os.startfile(u)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", u])
        else:
            subprocess.Popen(["xdg-open", u])
        time.sleep(1.5)
        return {"opened": u[:200], "in": "default browser", "title": "", "loaded": False}

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
