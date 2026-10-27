"""Copy of server/app/operator/display.py (the worker has its own venv), used by Santosh Browser too.

v0.74 Run the Computer Operator as a REAL browser window, not headless.

Headless Chromium tells every site it is "HeadlessChrome" and many Indian portals / banks (Akamai, Cloudflare) refuse it
outright, so every page looked "blocked". A server has no screen, so we give it a virtual one (Xvfb) and open a normal
Chrome / Chromium window on it. Nothing is faked: navigator.webdriver stays true, no automation-hiding flags; it is
simply the same browser a person would use.

  OPERATOR_BROWSER   auto (Google Chrome if installed, else Playwright's Chromium) | chrome | chromium
  OPERATOR_HEADLESS  false (default: real window on a virtual screen) | true (old behaviour)
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger("santosh.operator.display")

CHROME_PATHS = ("/opt/google/chrome/chrome", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable")
_lock = threading.Lock()
_xvfb: subprocess.Popen | None = None
_display = ""


def chrome_installed() -> bool:
    return any(Path(p).exists() for p in CHROME_PATHS)


def channel(choice: str) -> str:
    """'chrome' when Google Chrome should be used, '' for Playwright's own Chromium."""
    c = (choice or "auto").strip().lower()
    if c == "chromium":
        return ""
    if c == "chrome":
        return "chrome"
    return "chrome" if chrome_installed() else ""


def _lock_pid(lock: Path) -> int:
    try:
        return int(lock.read_text().strip() or 0)
    except (OSError, ValueError):
        return 0


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _is_xvfb(pid: int) -> bool:
    try:
        return "Xvfb" in Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="ignore")
    except OSError:
        return False


def virtual_display() -> str:
    """A DISPLAY for a real (headed) browser window: the server's own, or an Xvfb we start once. '' = none possible."""
    global _xvfb, _display
    if os.environ.get("DISPLAY"):
        return os.environ["DISPLAY"]
    with _lock:
        if _display and ((_xvfb is not None and _xvfb.poll() is None) or Path(f"/tmp/.X11-unix/X{_display[1:]}").exists()):
            return _display
        exe = shutil.which("Xvfb")
        if not exe:
            return ""
        for n in range(99, 120):
            lock, sock = Path(f"/tmp/.X{n}-lock"), Path(f"/tmp/.X11-unix/X{n}")
            if lock.exists() or sock.exists():
                pid = _lock_pid(lock)
                if pid and _is_xvfb(pid) and sock.exists():
                    _display = f":{n}"               # v0.88.1 a virtual screen already running (an earlier start): share it
                    log.info("using the running virtual screen %s for the browser", _display)
                    return _display
                if pid and _alive(pid):
                    continue                          # someone else's real X server
                for f in (lock, sock):                # stale: its process is gone (server restarted)
                    try:
                        f.unlink()
                    except OSError:
                        pass
                if lock.exists() or sock.exists():
                    continue
            p = subprocess.Popen([exe, f":{n}", "-screen", "0", "1366x900x24", "-nolisten", "tcp", "-ac"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            for _ in range(40):
                if Path(f"/tmp/.X11-unix/X{n}").exists():
                    _xvfb, _display = p, f":{n}"
                    log.info("virtual screen %s started for the Computer Operator", _display)
                    return _display
                if p.poll() is not None:
                    break
                time.sleep(0.1)
            p.kill()
        return ""


def launch_options(headless_setting: bool, browser_setting: str = "auto", executable: str = "") -> tuple[dict, str]:
    """Playwright launch kwargs (headless / channel / executable_path / env) + a one-line description."""
    opts: dict = {}
    what = []
    exe = executable or os.environ.get("OPERATOR_CHROMIUM", "")
    if exe:
        opts["executable_path"] = exe
        what.append(f"browser {exe}")
    else:
        ch = channel(browser_setting)
        if ch:
            opts["channel"] = ch
            what.append("Google Chrome")
        else:
            what.append("Chromium")
    headless = bool(headless_setting)
    if not headless:
        d = virtual_display()
        if d:
            opts["env"] = {**os.environ, "DISPLAY": d}
            what.append(f"real window on virtual screen {d}")
        else:
            headless = True
            what.append("headless (install Xvfb for a real window: sudo apt install -y xvfb)")
    else:
        what.append("headless")
    opts["headless"] = headless
    return opts, ", ".join(what)
