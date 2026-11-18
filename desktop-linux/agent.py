"""Hoola PC agent: the Linux cloud computer that belongs to Hoola (the coworker's own PC).

Speaks the SAME wire protocol as the Windows Santosh Desktop (server/app/pc/hub.py):
  dials out to the server over WebSocket, answers {"type": "info"}, runs {"type": "job"} messages,
  replies {"type": "result", "id", ok, data|error}. The PC operator (pc/operator.py) drives this
  PC exactly like her Windows PC - the vision loop cannot tell the difference.

The difference is what this PC IS: an Ubuntu container Hoola owns (Xvfb + openbox + Chromium).
So it gets extra actions the user's PC never offers:
  install    - apt-get / pip install packages (this is Hoola's own VM; no approval needed)
  run        - run a shell command inside the VM (the Claude-harness bash tool, same trust model)
  send_file  - v0.202 upload one of MY files to the server tagged direction "to_pc", so the USER'S
               personal PC can fetch it into her Santosh Inbox (the PC-to-PC file bridge; the server
               shows her a confirm card before it lands on her PC)

Browser intelligence goes over the Chrome DevTools Protocol (Chromium started lazily with
--remote-debugging-port=9222), NOT screen scraping: page_text / tabs / switch_tab / open_url
are exact. Screen + mouse + keyboard are Xvfb + xdotool + scrot, like the Anthropic reference
computer-use image.

State lives in /data (a Docker volume): identity.json (device_id + token), chrome profile
(logged-in sessions survive restarts), Downloads, installed.log.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import platform
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx

DATA = Path(os.environ.get("HOOLA_DATA", "/data"))
SERVER = os.environ.get("HOOLA_SERVER", "http://127.0.0.1:8077").strip().rstrip("/")
NAME = os.environ.get("HOOLA_PC_NAME", "Hoola PC")
DISPLAY = os.environ.get("DISPLAY", ":1")
CDP = "http://127.0.0.1:9222"
VERSION = "1.6.0"   # v0.885 HOOLA PC POOL: a locked folder per user, files to chat, background commands, installs that survive; v0.884.1 a blank tab at the deadline = no_page; v0.884 CHROME SAAF: India clock + language, portal-friendly Chrome, open_url says what went wrong
MAX_SEND = 50 * 1024 * 1024   # same upload cap as the Windows Santosh Desktop
DOWNLOADS = DATA / "Downloads"
PROFILE = DATA / "chrome"
SHOT_DIR = Path("/tmp")

# v0.884 CHROME SAAF (owner: "ON HOOLA PC CHROME NOT OPEN ALL WEBSITE CLEANLY IT STOPS IN BETWEEN"): her 13 Nov check -
# the server is in India (Bengaluru) but the browser ran on UTC with no language (sites saw a foreign browser, date
# fields off by 5.5 h), Chrome blocked portal pop-ups and asked about downloads, every open_url made a NEW tab that was
# never closed, and a page got 12 s. Government / legacy portals need all of it the other way round.
TZ_NAME = os.environ.get("TZ") or "Asia/Kolkata"
LANG = "en-IN"
ACCEPT_LANG = "en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7"
TAB_CAP = 6                       # open tabs kept; older ones are closed (memory)
OPEN_WAIT = 30                    # seconds a page gets by default (max 60)
POLICY = {   # Chrome enterprise policy (Hoola's own VM): what portals need, nothing that reaches her
    "DefaultPopupsSetting": 1,                 # portals open login / payment / print pages as pop-ups
    "PromptForDownloadLocation": False,
    "DownloadDirectory": str(DOWNLOADS),
    "DefaultNotificationsSetting": 2,          # no 'allow notifications?' bubble over the page
    "DefaultGeolocationSetting": 2,            # no 'know your location?' bubble either
    "PasswordManagerEnabled": False,           # Hoola never keeps passwords
    "TranslateEnabled": False,                 # no translate bar over Hindi / Marathi pages
    "BackgroundModeEnabled": False,
    "MetricsReportingEnabled": False,
}
POLICY_DIRS = ("/etc/opt/chrome/policies/managed", "/etc/chromium/policies/managed")

# v0.885 HOOLA PC POOL (owner: "EVERY HOOLA USER WILL HAS ITS OWN HOOLA PC ... Shared pool AND HUMAN IN LOOP"): one
# Hoola PC serves many users one after another, so each user gets her OWN folder (Chrome logins, Downloads, work
# files) under /data/profiles/<key>. /data/Downloads and /data/work are symlinks to the folder of the user being served
# right now (every old path keeps working). A user's folder is ENCRYPTED (openssl, her own secret that only the server
# holds) the moment the PC switches to someone else, and shell commands run as the unprivileged 'hoolawork' user who
# can reach the active folder only - never another user's folder, the PC's token or the encrypted archives.
PROFILES = DATA / "profiles"
WORK = DATA / "work"
WORKER = "hoolawork"
_KEY_RE = re.compile(r"^[a-f0-9]{8,40}$")
CUR: dict[str, str] = {"key": "", "secret": ""}
JOBS: dict[str, dict[str, Any]] = {}      # background commands of the user being served now
JOB_MAX = 6
JOB_HOURS = 2
CACHE_SKIP = ("Cache", "Code Cache", "GPUCache", "Service Worker/CacheStorage", "GrShaderCache", "ShaderCache")

for _d in (DATA, PROFILES):
    _d.mkdir(parents=True, exist_ok=True)
for _d in (DOWNLOADS, PROFILE):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:          # a symlink left pointing at a folder that is locked now: fixed by the next profile
        pass


class ActionError(Exception):
    pass


# ---------------- pairing + identity ----------------
def _identity() -> dict[str, str]:
    f = DATA / "identity.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            if d.get("device_id") and d.get("token"):
                return d
        except ValueError:
            pass
    return {}


def _save_identity(device_id: str, token: str) -> None:
    (DATA / "identity.json").write_text(json.dumps({"device_id": device_id, "token": token}))


def pair_once(code: str) -> str:
    """Exchange the 6-digit code from her app (Mera PC > pair) for this PC's own token."""
    r = httpx.post(SERVER + "/api/pc/pair", json={"code": code.strip(), "name": NAME,
                                                  "os": "Linux (Hoola PC)"}, timeout=20)
    if r.status_code >= 400:
        raise ActionError(f"pair failed: {r.text[:160]}")
    d = r.json()
    _save_identity(d["device_id"], d["token"])
    return d["device_id"]


# ---------------- xdotool / wmctrl helpers ----------------
def _x(*args: str, timeout: float = 15) -> str:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return (p.stdout or "").strip()


def _windows() -> list[str]:
    out = _x("wmctrl", "-l")
    titles = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            titles.append(parts[3])
    return titles


def _active_window() -> str:
    try:
        return _x("xdotool", "getactivewindow", "getwindowname", timeout=5)
    except Exception:
        return ""


# ---------------- Chrome over CDP (lazy) ----------------
_chrome_lock = threading.Lock()
_chrome: subprocess.Popen | None = None


def _browser_exe() -> str:
    """v1.2.0 real Google Chrome first (full codecs H.264/AAC/MP3 + the build sites are tested
    against - Debian's chromium has no proprietary codecs and that is most of the 'Chromium has
    issues' pain: videos black, some media sites broken). chromium stays as the fallback."""
    for e in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if subprocess.run(["which", e], capture_output=True).returncode == 0:
            return e
    return "chromium"


def _chrome_up() -> None:
    global _chrome
    with _chrome_lock:
        try:   # v0.884 a Chrome already answering (started by this agent or by a 'check' run) is used as it is
            httpx.get(CDP + "/json/version", timeout=2)
            return
        except Exception:
            pass
        _write_policy()
        _seed_prefs(PROFILE)                 # v0.885 this user's downloads go to her Downloads
        # --no-sandbox: the container runs as root - Chrome refuses to start without it
        # (Debian's chromium wrapper adds it silently for root, Google Chrome does not).
        flags = ["--remote-debugging-port=9222", f"--user-data-dir={PROFILE}", "--no-first-run",
                 "--no-default-browser-check", "--disable-session-crashed-bubble", "--start-maximized",
                 "--window-position=0,0", "--window-size=1280,760", "--disable-dev-shm-usage",
                 "--disable-crash-reporter", "--force-device-scale-factor=1", "--password-store=basic",
                 "--no-sandbox",
                 # v0.884 an Indian browser, and work never slowed in a tab that is not in front
                 f"--lang={LANG}", f"--accept-lang={ACCEPT_LANG}", "--disable-popup-blocking",
                 "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                 "--disable-backgrounding-occluded-windows"]
        exe = _browser_exe()
        # v1.3.1: a recreated container has a NEW hostname, but the volume's profile carries the OLD
        # container's SingletonLock - Chrome refuses to boot on it ("The profile appears to be in use
        # by another Google Chrome process ... on another computer") and headless there is no dialog
        # to unlock it. NOTHING is alive here (the CDP check above just failed and the agent is the
        # only chrome supervisor in this container), so the stale locks are safe to clear. A lock from
        # THIS hostname with a dead PID is cleared by Chrome itself.
        for f in ("SingletonLock", "SingletonSocket", "SingletonCookie", "SingletonCookie-1"):
            try:
                (PROFILE / f).unlink()
            except OSError:
                pass
        # stderr to a file, not DEVNULL (v1.3.0 lesson: a chrome that will not boot was INVISIBLE -
        # the selftest could only say 'CDP ready nahi hua'; now the real error is in /tmp/chrome_err.log)
        _chrome = subprocess.Popen([exe, *flags], env={**os.environ, "DISPLAY": DISPLAY, "TZ": TZ_NAME,
                                                         "LANGUAGE": "en_IN:en"},
                                   stdout=subprocess.DEVNULL,
                                   stderr=open("/tmp/chrome_err.log", "ab"))
    for _ in range(90):          # up to ~45s for first paint (real Chrome on a big profile is slower
        try:                     # than 15s on its first boot - dbus/machine-id noise + profile work)
            httpx.get(CDP + "/json/version", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise ActionError("Chrome nahi khula (CDP ready nahi hua) - /tmp/chrome_err.log par dekho")


def _targets() -> list[dict[str, Any]]:
    r = httpx.get(CDP + "/json", timeout=5)
    return [t for t in r.json() if t.get("type") == "page"]


def _active_target() -> dict[str, Any]:
    ts = _targets()
    if not ts:
        raise ActionError("Koi page khula nahi hai")
    act = _active_window()
    for t in ts:
        if act and t.get("title") == act:
            return t
    return ts[0]


def _cdp_eval(t: dict[str, Any], expr: str, timeout: float = 15) -> Any:
    """One Runtime.evaluate over the page's WebSocket debugger."""
    import websockets

    async def go() -> Any:
        async with websockets.connect(t["webSocketDebuggerUrl"], max_size=16 * 1024 * 1024, open_timeout=10) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                      "params": {"expression": expr, "returnByValue": True,
                                                 "awaitPromise": True}}))
            end = time.time() + timeout
            while time.time() < end:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(1, end - time.time()))
                msg = json.loads(raw)
                if msg.get("id") == 1:
                    return msg.get("result", {}).get("result", {}).get("value")
        return None

    return asyncio.run(go())


def _write_policy() -> None:
    """v0.884 Chrome's own policy file (pop-ups allowed, downloads straight into /data/Downloads, no bubbles).
    Read by Chrome when it starts; a failure only means the old behaviour."""
    for d in POLICY_DIRS:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
            (Path(d) / "hoola.json").write_text(json.dumps(POLICY, indent=1))
        except OSError:
            pass


def _cdp_call(ws_url: str, method: str, params: dict[str, Any] | None = None, timeout: float = 15) -> Any:
    """One CDP command on a page; returns its result (or raises ActionError)."""
    import websockets

    async def go() -> Any:
        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024, open_timeout=10) as ws:
            await ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
            end = time.time() + timeout
            while time.time() < end:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(1, end - time.time())))
                if msg.get("id") == 1:
                    if "error" in msg:
                        raise ActionError(f"{method}: {msg['error'].get('message', '')}"[:200])
                    return msg.get("result")
        raise ActionError(f"{method}: no answer in {int(timeout)}s")

    return asyncio.run(go())


def _host(url: str) -> str:
    from urllib.parse import urlparse
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


_ERR = re.compile(r"\b(?:NET::)?ERR_[A-Z_]+\b")
_CERT = re.compile(r"NET::ERR_CERT|ERR_CERT_|ERR_SSL_|privacy error|connection is not private", re.I)
_BLOCK = re.compile(r"access denied|you don.t have permission to access|request blocked|request rejected|"
                    r"error 1020|\bforbidden\b|not authorized to access", re.I)
_BOTCHECK = re.compile(r"just a moment|checking your browser|attention required|verify you are human|"
                       r"are you a robot|ddos protection", re.I)
_CRASH = re.compile(r"aw, snap|he's dead, jim|status_access_violation|sbox_fatal", re.I)

STATE_JS = ("(() => ({ready: document.readyState, href: location.href, title: document.title, "
            "text: (document.body ? document.body.innerText : '').slice(0, 1500)}))()")


def _state(t: dict[str, Any] | None) -> dict[str, Any]:
    if t is None:
        return {"error": "gone"}
    try:
        v = _cdp_eval(t, STATE_JS, timeout=6)
        return v if isinstance(v, dict) else {"error": "empty"}
    except Exception as e:
        return {"error": type(e).__name__}


def classify(st: dict[str, Any]) -> str:
    """'' = the page is fine; else one word for what stopped it (pure, tested): certificate / net:<ERR_...> /
    blocked / bot_check / crashed / no_answer / slow."""
    if not st or st.get("error"):
        return "no_answer"
    href = str(st.get("href") or "")
    title = str(st.get("title") or "")
    text = str(st.get("text") or "")
    both = title + "\n" + text
    if href.startswith("chrome-error://"):
        if _CERT.search(both):
            return "certificate"
        m = _ERR.search(both)
        return "net:" + (m.group(0).replace("NET::", "") if m else "ERR_FAILED")
    if _CRASH.search(both[:600]):
        return "crashed"
    if _BOTCHECK.search(title) or (len(text) < 400 and _BOTCHECK.search(text)):
        return "bot_check"
    if _BLOCK.search(title) or (len(text) < 600 and _BLOCK.search(text)):
        return "blocked"
    if st.get("ready") != "complete":
        return "slow"
    return ""


HINTS = {
    "certificate": "The site's security certificate is broken or expired, so Chrome stopped on its warning page. "
                   "Hoola does not click past security warnings: tell her plainly (old government portals often "
                   "have this) and offer to do it on HER PC (pc_do), where she decides.",
    "blocked": "The site REFUSES this cloud computer's internet address (some government / bank sites block cloud "
               "servers). Retrying will not help. Tell her plainly and offer to do it on HER PC (pc_do) instead.",
    "bot_check": "A 'checking your browser' page is showing. Take a screenshot; if it wants a tick / puzzle, ask her "
                 "(ask_user). Do not open the site again.",
    "crashed": "The tab crashed; it was reloaded once. If it is still blank, take a screenshot and open the page again.",
    "no_page": "The site sent NOTHING (the tab stayed blank) - it most likely refuses cloud servers, as "
               "parivahan.gov.in does. Retrying will not help. Tell her plainly and offer to do it on HER PC (pc_do).",
    "no_answer": "The tab did not answer. Take a screenshot to see what is on screen.",
    "slow": "The page is still loading. Use wait_for with a word you expect on it, or take a screenshot - do NOT open "
            "it again (that restarts the load).",
}


def hint_for(problem: str) -> str:
    if problem.startswith("net:"):
        return (f"The site did not open ({problem[4:]}), tried twice. It may be down right now or it blocks cloud "
                "servers. Tell her plainly and offer to do it on HER PC (pc_do) or later. Do not keep retrying.")
    return HINTS.get(problem, "")


def _trim_tabs(keep: str) -> int:
    """v0.884 at most TAB_CAP tabs: every open_url used to make a new tab and none was ever closed."""
    closed = 0
    try:
        ts = _targets()
    except Exception:
        return 0
    extra = [t for t in ts if t.get("id") != keep]
    while len(extra) + 1 > TAB_CAP:
        t = extra.pop()                                   # /json lists the newest first: close from the end
        try:
            httpx.get(CDP + f"/json/close/{t['id']}", timeout=5)
            closed += 1
        except Exception:
            break
    return closed


# ---------------- v0.842 exact mode (agent-desktop over AT-SPI) ----------------
# axtree.py is the SAME file the Windows Hoola Desktop ships (a test keeps the two copies identical). No control
# switch here: this is Hoola's own VM. A missing helper / accessibility bus = a clear error, pixel mode goes on.
AX_ACTIONS = {"ax_status", "ax_apps", "ax_snapshot", "ax_text", "ax_find", "ax_click", "ax_set_value", "ax_press",
              "ax_launch", "ax_wait", "ax_get", "ax_is", "ax_act", "ax_select", "ax_type", "ax_scroll", "ax_displays",
              "ax_window_shot", "ax_surfaces", "ax_open_surface", "ax_notifications", "ax_notification_dismiss",
              "ax_notification_action", "ax_clipboard", "ax_close_app", "ax_batch"}


def _ax_handle(action: str, a: dict[str, Any]) -> dict[str, Any]:
    import axtree as X
    if not X.available():
        raise ActionError("Exact mode needs the agent-desktop helper in this Hoola PC image (rebuild with vps-ops "
                          "pc_deploy). Pixel mode still works.")
    s = lambda k, n=80: str(a.get(k) or "")[:n]   # noqa: E731
    try:
        if action == "ax_status":
            return X.status()
        if action == "ax_apps":
            out = X.list_apps()
            out.update(X.windows())
            return out
        if action == "ax_snapshot":
            return X.snapshot(s("app", 60), s("window_id", 80), bool(a.get("skeleton")), s("root", 48), s("surface", 20),
                              int(a.get("timeout_ms") or 6000))
        if action == "ax_text":
            return X.read(s("app", 60), s("surface", 20), max_chars=int(a.get("max_chars") or 6000))
        if action == "ax_find":
            return X.find(s("app", 60), s("role", 24), s("name"), s("text"), bool(a.get("exact")))
        if action == "ax_click":
            return X.click(s("ref", 48))
        if action == "ax_set_value":
            return X.set_value(s("ref", 48), str(a.get("text") or "")[:4000])
        if action == "ax_press":
            keys = s("keys", 40).lower().replace(" ", "")
            if keys in ("super+l", "win+l", "ctrl+alt+delete", "ctrl+alt+backspace"):
                raise ActionError("that shortcut is not allowed")
            return X.press(keys, s("app", 60))
        if action == "ax_launch":
            return X.launch(s("name", 200))
        if action == "ax_wait":
            return X.wait(s("app", 60), s("text"), s("window"), int(a.get("seconds") or 10))
        if action == "ax_get":
            return X.get(s("ref", 48), s("property", 16) or "text")
        if action == "ax_is":
            return X.is_state(s("ref", 48), s("state", 16) or "visible")
        if action == "ax_act":
            return X.act(s("op", 16), s("ref", 48))
        if action == "ax_select":
            return X.select(s("ref", 48), s("value", 200))
        if action == "ax_type":
            return X.type_text(s("ref", 48), str(a.get("text") or "")[:4000], int(a.get("interval_ms") or 0))
        if action == "ax_scroll":
            return X.scroll(s("ref", 48), s("direction", 8) or "down", int(a.get("amount") or 3))
        if action == "ax_displays":
            return X.displays()
        if action == "ax_window_shot":
            return X.window_shot(s("app", 60), s("window_id", 80))
        if action == "ax_surfaces":
            return X.surfaces(s("app", 60))
        if action == "ax_open_surface":
            return X.open_surface(s("surface", 24))
        if action == "ax_notifications":
            return X.notifications(s("app", 60), s("text"), int(a.get("limit") or 10))
        if action == "ax_notification_dismiss":
            return X.dismiss_notification(int(a.get("index") or 1), s("expected_app", 60), s("expected_title", 120))
        if action == "ax_notification_action":
            return X.notification_action(int(a.get("index") or 1), s("action", 40), s("expected_app", 60),
                                         s("expected_title", 120))
        if action == "ax_clipboard":
            op = s("op", 8) or "get"
            if op == "set":
                return X.clipboard_set(str(a.get("text") or ""))
            return X.clipboard_clear() if op == "clear" else X.clipboard_get()
        if action == "ax_close_app":
            if "agent" in s("app", 60).lower():
                raise ActionError("Hoola never closes its own agent")
            return X.close_app(s("app", 60))
        if action == "ax_batch":
            return X.batch(list(a.get("steps") or []))
    except X.AxError as e:
        raise ActionError(str(e))
    except X.AxUnavailable as e:
        raise ActionError(str(e))
    raise ActionError(f"Unknown action {action}")


# ---------------- v0.885 the pool: one locked folder per user ----------------
def _worker() -> tuple[int, int] | None:
    """(uid, gid) of the unprivileged shell user, or None (tests / an old image without it: commands run as before)."""
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return None
    try:
        import pwd
        w = pwd.getpwnam(WORKER)
        return w.pw_uid, w.pw_gid
    except (KeyError, ImportError):
        return None


def _real(p: Path) -> Path:
    try:
        return p.resolve()
    except OSError:
        return p


def allowed(path: str | Path) -> bool:
    """A file action may touch this path: never another user's folder, an encrypted archive or the PC's token."""
    r = _real(Path(path))
    root = _real(PROFILES)
    if r.name == "identity.json" or r.name.endswith(".tar.enc"):
        return False
    try:
        rel = r.relative_to(root)
    except ValueError:
        return True
    return bool(CUR["key"]) and bool(rel.parts) and rel.parts[0] == CUR["key"]


def _guard(path: str | Path) -> None:
    if not allowed(path):
        raise ActionError("Yeh folder kisi aur user ka hai - Hoola PC par har user apne folder tak hi pahunchta hai.")


def _point(link: Path, target: Path) -> None:
    """Make /data/Downloads (or /data/work) point at the active user's folder."""
    target.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    elif link.exists():            # a real folder (old layout) that was not moved: keep it under a dated name
        link.rename(link.with_name(link.name + ".old-" + time.strftime("%Y%m%d%H%M%S")))
    link.symlink_to(target)


def _walls() -> None:
    """File permissions that make the folders private (root only; tests skip it)."""
    w = _worker()
    if w is None:
        return
    uid, gid = w
    for f, mode in ((DATA, 0o711), (PROFILES, 0o711), (DATA / "identity.json", 0o600)):
        try:
            os.chmod(f, mode)
        except OSError:
            pass
    for c in PROFILES.iterdir():
        try:
            if c.name == CUR["key"]:
                os.chmod(c, 0o711)
                (c / "chrome").mkdir(exist_ok=True)
                os.chmod(c / "chrome", 0o700)            # cookies / logins: Chrome (root) only
                for sub in ("Downloads", "files"):
                    (c / sub).mkdir(exist_ok=True)
                    os.chown(c / sub, uid, gid)
                    os.chmod(c / sub, 0o775)
            else:
                os.chmod(c, 0o700)
        except OSError:
            pass


def _stop_chrome() -> None:
    """Close Chrome (it holds the old user's profile open) and wait until it is really gone."""
    global _chrome
    with _chrome_lock:
        try:   # a clean close first: Chrome writes the user's cookies / logins to disk only on a real shutdown
            ws = httpx.get(CDP + "/json/version", timeout=2).json().get("webSocketDebuggerUrl", "")
            if ws:
                try:
                    _cdp_call(ws, "Browser.close", {}, timeout=5)
                except Exception:
                    pass                       # the socket drops as Chrome closes - that is the success case
                for _ in range(30):
                    time.sleep(0.5)
                    try:
                        httpx.get(CDP + "/json/version", timeout=1)
                    except Exception:
                        break
                if _chrome is not None:
                    try:
                        _chrome.wait(timeout=10)
                    except Exception:
                        pass
        except Exception:
            pass
        if _chrome is not None:
            try:
                _chrome.terminate()
                _chrome.wait(timeout=8)
            except Exception:
                try:
                    _chrome.kill()
                except Exception:
                    pass
            _chrome = None
        subprocess.run(["pkill", "-f", "--", "--remote-debugging-port=9222"], capture_output=True)
        for _ in range(20):
            try:
                httpx.get(CDP + "/json/version", timeout=1)
                time.sleep(0.5)
            except Exception:
                return


def _close_user_apps() -> int:
    """Every window of the previous user goes (LibreOffice, a PDF viewer...): its files must not show to the next."""
    pids: set[int] = set()
    try:
        out = subprocess.run(["wmctrl", "-lp"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) not in (0, os.getpid()):
                pids.add(int(parts[2]))
    except Exception:
        pass
    for pid in pids:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    _stop_chrome()
    for j in list(JOBS.values()):             # the old user's background commands stop too
        _kill_job(j)
    JOBS.clear()
    return len(pids)


def _lock_profile(key: str, secret: str) -> bool:
    """Encrypt the folder of a user who is not being served any more, then delete the readable copy."""
    d = PROFILES / key
    if not key or not secret or not d.is_dir():
        return False
    arc = PROFILES / (key + ".tar.enc")
    tmp = PROFILES / (key + ".tar.enc.tmp")
    excl = [f"--exclude={key}/chrome/*/{c}" for c in CACHE_SKIP] + [f"--exclude={key}/chrome/{c}" for c in CACHE_SKIP]
    try:
        tar = subprocess.Popen(["tar", "-C", str(PROFILES), *excl, "-cf", "-", key], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
        enc = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-salt",
                              "-pass", "env:HOOLA_PK", "-out", str(tmp)], stdin=tar.stdout,
                             env={**os.environ, "HOOLA_PK": secret}, capture_output=True, timeout=600)
        tar.stdout.close()
        tar.wait(timeout=60)
        if tar.returncode == 0 and enc.returncode == 0 and tmp.exists():
            tmp.replace(arc)
            os.chmod(arc, 0o600)
            import shutil
            shutil.rmtree(d, ignore_errors=True)
            return True
    except Exception as e:
        print(f"profile lock failed: {e}", flush=True)
    tmp.unlink(missing_ok=True)
    try:
        os.chmod(d, 0o700)            # could not encrypt: at least nobody but root reads it
    except OSError:
        pass
    return False


def _unlock_profile(key: str, secret: str) -> str:
    """'' fresh / 'kept' (a readable copy is still there) / 'opened' (decrypted from its archive)."""
    d = PROFILES / key
    if d.is_dir():
        return "kept"
    arc = PROFILES / (key + ".tar.enc")
    if not arc.exists():
        d.mkdir(parents=True, exist_ok=True)
        return ""
    dec = subprocess.Popen(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-pass",
                            "env:HOOLA_PK", "-in", str(arc)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={**os.environ, "HOOLA_PK": secret})
    tar = subprocess.run(["tar", "-C", str(PROFILES), "-xf", "-"], stdin=dec.stdout, capture_output=True, timeout=600)
    dec.stdout.close()
    dec.wait(timeout=60)
    if dec.returncode != 0 or tar.returncode != 0 or not d.is_dir():
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        raise ActionError("Is user ka folder khul nahi paya (chabi mel nahi khayi) - kuch nahi badla.")
    arc.unlink(missing_ok=True)       # the readable copy is the only copy while she is served
    return "opened"


def _migrate_home(key: str) -> bool:
    """The PC's first user (before the pool) kept her Chrome logins in /data/chrome and files in /data/Downloads:
    they move into HER folder once, so nothing she was logged into is lost."""
    d = PROFILES / key
    moved = False
    if (DATA / "chrome").is_dir() and not (DATA / "chrome").is_symlink() and not (d / "chrome").exists():
        d.mkdir(parents=True, exist_ok=True)
        (DATA / "chrome").rename(d / "chrome")
        moved = True
    old = DATA / "Downloads"
    if old.is_dir() and not old.is_symlink() and not (d / "Downloads").exists():
        d.mkdir(parents=True, exist_ok=True)
        old.rename(d / "Downloads")
        moved = True
    return moved


def _seed_prefs(profile: Path) -> None:
    """Chrome's own download setting for this profile (the policy file says the same for every profile)."""
    f = profile / "Default" / "Preferences"
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        d = json.loads(f.read_text()) if f.exists() else {}
        dl = d.setdefault("download", {})
        dl.update({"default_directory": str(DOWNLOADS), "prompt_for_download": False, "directory_upgrade": True})
        d.setdefault("savefile", {})["default_directory"] = str(DOWNLOADS)
        f.write_text(json.dumps(d))
    except (OSError, ValueError):
        pass


def use_profile(key: str, secret: str = "", home: bool = False) -> dict[str, Any]:
    """Switch this PC to one user's folder. Same user again = nothing happens (fast)."""
    global PROFILE
    key = str(key or "").strip().lower()
    if key and not _KEY_RE.match(key):
        raise ActionError("bad profile key")
    if key and len(str(secret or "")) < 24:
        raise ActionError("profile secret missing")
    if key == CUR["key"] and (not key or (PROFILES / key).is_dir()):
        return {"profile": key or "home", "switched": False}
    how = ""
    if key:                              # open HER folder first: a wrong key changes nothing at all
        if home and (DATA / "chrome").is_dir() and not (PROFILES / key / "chrome").exists():
            _stop_chrome()               # Chrome must not hold the old profile open while it moves
            _migrate_home(key)
        how = _unlock_profile(key, secret)
    closed = _close_user_apps()
    old, old_secret = CUR["key"], CUR["secret"]
    locked = _lock_profile(old, old_secret) if old and old != key else False
    if key:
        base = PROFILES / key
        PROFILE = base / "chrome"
        PROFILE.mkdir(parents=True, exist_ok=True)
        _point(DOWNLOADS, base / "Downloads")
        _point(WORK, base / "files")
    else:
        PROFILE = DATA / "chrome"
        PROFILE.mkdir(parents=True, exist_ok=True)
    CUR["key"], CUR["secret"] = key, (secret if key else "")
    _walls()
    return {"profile": key or "home", "switched": True, "locked_previous": locked, "opened": how,
            "windows_closed": closed}


# ---------------- v0.885 long commands in the background ----------------
def _kill_job(j: dict[str, Any]) -> None:
    p = j.get("proc")
    if p is not None and p.poll() is None:
        try:
            os.killpg(p.pid, 9)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def _run_env() -> dict[str, str]:
    return {**os.environ, "DISPLAY": DISPLAY, "HOME": str(WORK), "TZ": TZ_NAME}


def _as_worker() -> dict[str, Any]:
    w = _worker()
    return {"user": w[0], "group": w[1], "extra_groups": []} if w else {}


# ---------------- the actions ----------------
class Actions:
    def __init__(self) -> None:
        self.log = print
        self._els: dict[int, str] = {}          # v1.3.0 semantic refs: ref -> CSS selector of the element
        self._els_src: str = ""                 # title+url the refs were taken from (staleness check)

    def info(self) -> dict[str, Any]:
        return {"type": "info", "name": NAME, "os": f"Linux {platform.release()} (Hoola PC)",
                "version": VERSION, "kind": "hoola_pc",
                "folders": [{"path": str(DATA), "label": "Hoola PC"}],
                "tally": {}, "indexed": 0, "inbox": str(DOWNLOADS), "paused": False, "control": True}

    def handle(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if action in AX_ACTIONS:                  # v0.842 exact mode: the same ax_* the Windows PC answers
            return _ax_handle(action, args or {})
        fn = getattr(self, "do_" + action, None)
        if fn is None:
            raise ActionError(f"Unknown action {action}")
        try:
            return fn(**(args or {}))
        except ActionError:
            raise
        except TypeError as e:
            raise ActionError(f"Bad request: {e}")
        except Exception as e:
            raise ActionError(f"{type(e).__name__}: {e}"[:300])

    # ---- screen + control (xdotool) ----
    def do_screen(self, max_width: int = 1280, monitor: str = "primary", **_) -> dict[str, Any]:
        p = SHOT_DIR / "hoola_pc_shot.png"
        _x("scrot", "-o", str(p), timeout=20)
        from PIL import Image
        img = Image.open(p).convert("RGB")
        w, h = img.size
        mw = max(320, min(int(max_width or 1280), 1920))
        if w > mw:
            img = img.resize((mw, round(h * mw / w)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=72)
        return {"image_b64": base64.b64encode(buf.getvalue()).decode(), "width": img.size[0],
                "height": img.size[1], "monitor": "primary", "active_window": _active_window(),
                "windows": _windows()[:12]}

    def do_control(self, op: str = "", x: Any = None, y: Any = None, text: str = "", keys: str = "",
                   amount: int = 0, to_x: Any = None, to_y: Any = None, **_) -> dict[str, Any]:
        op = str(op or "")
        if op in ("click", "right_click", "double_click"):
            xi, yi = int(x or 0), int(y or 0)
            if op == "right_click":
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "3")
            elif op == "double_click":
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "--repeat", "2", "--delay", "60", "1")
            else:
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "1")
            return {"ok": True}
        if op == "type":
            text = str(text or "")[:4000]
            if not text:
                return {"ok": True}
            _x("xdotool", "type", "--clearmodifiers", "--delay", "10", "--", text, timeout=120)
            return {"ok": True}
        if op == "key":
            k = str(keys or "").strip()
            if not k:
                return {"ok": True}
            mapped = {"enter": "Return", "esc": "Escape", "win": "super", "del": "Delete"}.get(k.lower(), k)
            _x("xdotool", "key", "--", mapped)
            return {"ok": True}
        if op == "scroll":
            xi, yi = int(x or 640), int(y or 400)
            steps = max(1, min(abs(int(amount or -5)) * 2, 30))
            btn = "4" if int(amount or -5) > 0 else "5"          # 4 = up, 5 = down
            _x("xdotool", "mousemove", str(xi), str(yi), "click", "--repeat", str(steps), "--delay", "30", btn)
            return {"ok": True}
        if op == "drag":
            _x("xdotool", "mousemove", str(int(x or 0)), str(int(y or 0)), "mousedown", "1")
            _x("xdotool", "mousemove", "--sync", str(int(to_x or 0)), str(int(to_y or 0)))
            _x("xdotool", "mouseup", "1")
            return {"ok": True}
        raise ActionError(f"Unknown control op {op}")

    # ---- apps / windows ----
    _APPS = {"chrome": "@browser", "chromium": "@browser", "browser": "@browser", "files": "xdg-open",
             "calculator": "gnome-calculator", "text editor": "gedit", "editor": "gedit",
             "terminal": None, "cmd": None}

    def do_apps(self, **_) -> dict[str, Any]:
        apps = ["Chrome (Google Chrome)", "Files", "Text Editor (gedit)", "Calculator",
                "LibreOffice / anything installed via the install action"]
        return {"apps": apps, "windows": _windows()[:20]}

    def do_open_app(self, name: str = "", **_) -> dict[str, Any]:
        name = str(name or "").strip()
        low = name.lower()
        cmd = self._APPS.get(low)
        if cmd == "@browser":
            cmd = _browser_exe()          # v1.2.0 google-chrome when present, chromium otherwise
        if cmd is None and low in self._APPS:
            raise ActionError("Terminal yahan nahi khulta - run action use kijiye (yeh Hoola ka apna VM hai).")
        if cmd is None:
            for cand in (low, low.replace(" ", "-"), low.replace(" ", "_")):
                if subprocess.run(["which", cand], capture_output=True).returncode == 0:
                    cmd = cand
                    break
        if cmd is None:
            raise ActionError(f"{name} install nahi hai. Pehle install action se install kijiye.")
        args = [cmd, str(DATA)] if cmd == "xdg-open" else [cmd]
        subprocess.Popen(args, env={**os.environ, "DISPLAY": DISPLAY},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        return {"opened": name}

    def do_focus(self, title: str = "", **_) -> dict[str, Any]:
        t = str(title or "")
        if subprocess.run(["wmctrl", "-a", t], capture_output=True, env={**os.environ, "DISPLAY": DISPLAY}).returncode != 0:
            raise ActionError(f"'{t}' naam ki koi window nahi mili")
        return {"focused": _active_window() or t}

    def do_window(self, op: str = "", title: str = "", **_) -> dict[str, Any]:
        op = str(op or "").lower()
        env = {**os.environ, "DISPLAY": DISPLAY}
        t = str(title or "")
        if op == "close":
            subprocess.run(["wmctrl", "-c", t], capture_output=True, env=env)
        elif op == "minimize":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["xdotool", "getactivewindow", "windowminimize"], capture_output=True, env=env)
        elif op == "maximize":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["wmctrl", "-r", t, "-b", "add,maximized_vert,maximized_horz"], capture_output=True, env=env)
        elif op == "restore":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["wmctrl", "-r", t, "-b", "remove,maximized_vert,maximized_horz"], capture_output=True, env=env)
        else:
            raise ActionError("op must be minimize, maximize, restore or close")
        return {"window": _active_window() or t}

    # ---- browser intelligence over CDP ----
    def do_open_url(self, url: str = "", wait: int = OPEN_WAIT, new_tab: bool = False, **_) -> dict[str, Any]:
        """v0.884 open a site and SAY what happened: the same site's tab is reused (no endless tabs), a page gets up
        to `wait` s (30, max 60), a timeout is retried once, a crashed tab reloaded once, and a page that did not
        open comes back with problem + hint instead of a silent 'still loading'."""
        url = str(url or "").strip()
        if url.lower().startswith("file://"):      # v0.885 a local file: only the active user's own
            from urllib.parse import unquote, urlparse
            _guard(unquote(urlparse(url).path))
        elif not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        limit = max(5, min(int(wait or OPEN_WAIT), 60))
        t0 = time.time()
        _chrome_up()
        host = _host(url)
        tid = ""
        if not new_tab and host:
            try:
                same = next((t for t in _targets() if _host(t.get("url") or "") == host), None)
            except Exception:
                same = None
            if same is not None:
                try:
                    _cdp_call(same["webSocketDebuggerUrl"], "Page.navigate", {"url": url}, timeout=10)
                    tid = same["id"]
                except Exception:
                    tid = ""
        if not tid:
            r = httpx.put(CDP + f"/json/new?{url}", timeout=10)   # PUT is required on newer Chromium
            if r.status_code >= 400:
                r = httpx.put(CDP + "/json/new", params={"url": url}, timeout=10)
            tid = r.json().get("id", "")
        _trim_tabs(tid)
        notes = []
        st, problem = self._settle(tid, t0 + limit)
        if problem.startswith("net:") and time.time() - t0 < 75:
            self._reload(tid)                   # one more try: old portals often time out once, then answer
            st, problem = self._settle(tid, time.time() + min(limit, 30))
            notes.append("retried once")
        if problem == "bot_check":              # those pages usually clear themselves in a few seconds
            st, problem = self._settle(tid, time.time() + 15, accept_bot=False)
        if problem == "crashed":
            self._reload(tid)
            st, problem = self._settle(tid, time.time() + limit)
            notes.append("crashed tab reloaded")
        try:
            httpx.get(CDP + f"/json/activate/{tid}", timeout=5)
        except Exception:
            pass
        out = {"opened": url, "in": "Chrome (Hoola PC)", "title": str(st.get("title") or ""),
               "url": str(st.get("href") or url), "loaded": not problem, "seconds": round(time.time() - t0, 1)}
        if problem:
            out["problem"] = problem
            out["hint"] = hint_for(problem)
        if notes:
            out["note"] = "; ".join(notes)
        return out

    def _target(self, tid: str) -> dict[str, Any] | None:
        try:
            return next((x for x in _targets() if x.get("id") == tid), None)
        except Exception:
            return None

    def _reload(self, tid: str) -> None:
        t = self._target(tid)
        if t is not None:
            try:
                _cdp_call(t["webSocketDebuggerUrl"], "Page.reload", {"ignoreCache": True}, timeout=10)
            except Exception:
                pass
            time.sleep(0.5)

    def _settle(self, tid: str, deadline: float, accept_bot: bool = True) -> tuple[dict[str, Any], str]:
        """Poll the tab until it is complete, shows an error / block page, or the deadline passes."""
        time.sleep(0.8)
        while True:
            st = _state(self._target(tid))
            problem = classify(st)
            href = str(st.get("href") or "")
            final = problem in ("", "certificate", "blocked", "crashed") or problem.startswith("net:")
            if final and not (problem == "" and href in ("", "about:blank")):
                return st, problem
            if problem == "bot_check" and accept_bot:
                return st, problem
            if time.time() >= deadline:
                if problem == "" and href in ("", "about:blank"):
                    problem = "no_page"         # v0.884.1 the site sent nothing at all (her parivahan.gov.in check)
                return st, problem
            time.sleep(0.8)

    def do_check(self, urls: list | str | None = None, **_) -> dict[str, Any]:
        """v0.884 open each site in the real Chrome and say how it went (the 'does Chrome open everything' test)."""
        if isinstance(urls, str):
            urls = [u for u in re.split(r"[\s,]+", urls) if u]
        rows = []
        for u in list(urls or [])[:20]:
            try:
                r = self.do_open_url(u, wait=40)
                rows.append({"url": u, "ok": r.get("loaded"), "problem": r.get("problem", ""),
                             "title": str(r.get("title", ""))[:60], "seconds": r.get("seconds"),
                             "note": r.get("note", "")})
            except Exception as e:
                rows.append({"url": u, "ok": False, "problem": f"{type(e).__name__}: {e}"[:120]})
        return {"sites": rows, "tz": TZ_NAME, "lang": LANG, "version": VERSION}

    def do_page_text(self, max_chars: int = 6000, **_) -> dict[str, Any]:
        _chrome_up()
        t = _active_target()
        n = max(500, min(int(max_chars or 6000), 20000))
        text = _cdp_eval(t, "document.body ? document.body.innerText : ''", timeout=20) or ""
        return {"title": t.get("title", ""), "url": t.get("url", ""), "text": str(text)[:n]}

    # ---- v1.3.0 SEMANTIC BROWSER (CDP): act on elements by ref, never by guessed pixels ----
    # The root cause of 'browser operations not smooth' was pixel clicking: a JPEG screenshot -> the model
    # guesses X,Y -> xdotool clicks. Every step was a vision round trip and a miss on layout shift / DPI.
    # Here the PAGE tells us its real elements (one cheap exact step) and the browser itself clicks/types
    # the element the model named - the click cannot miss, and page_fill_form does a whole form in ONE step.

    _JS_ELEMENTS = r"""
(() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const nm = el => { let t = el.getAttribute('aria-label') || el.getAttribute('title') || el.placeholder || '';
    if (!t && el.value && ['INPUT','SELECT','TEXTAREA','BUTTON'].includes(el.tagName) && el.type !== 'password') t = String(el.value);
    if (!t && el.labels && el.labels[0]) t = el.labels[0].textContent;
    if (!t && el.tagName === 'IMG') t = el.alt || '';
    if (!t) t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    return (t || '').trim().slice(0, 90); };
  const path = el => { if (el.id) return '#' + CSS.escape(el.id);
    const parts = []; let e = el;
    while (e && e.nodeType === 1 && parts.length < 7) {
      if (e.id) { parts.unshift('#' + CSS.escape(e.id)); break; }
      let s = e.tagName.toLowerCase(); const p = e.parentElement;
      if (p) { const sib = Array.from(p.children).filter(c => c.tagName === e.tagName);
        if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(e) + 1) + ')'; }
      parts.unshift(s); e = p; }
    return parts.join(' > '); };
  const nodes = document.querySelectorAll('a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"], [role="checkbox"], [role="radio"], [role="combobox"], [role="menuitem"], [onclick]');
  const seen = new Set(); const out = [];
  for (const el of nodes) {
    if (out.length >= 300) break;
    if (!vis(el)) continue;
    const tag = el.tagName.toLowerCase(); const ty = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['hidden','file'].includes(ty)) continue;
    const role = tag === 'input' ? ({checkbox:'checkbox', radio:'radio', button:'button', submit:'button', reset:'button'}[ty] || 'input')
                                 : (el.getAttribute('role') || (tag === 'a' ? 'link' : tag));
    const name = nm(el);
    const key = role + '|' + name + '|' + (el.disabled ? 'd' : 'e');
    if (seen.has(key) && !['input','textarea','select'].includes(role)) continue;
    seen.add(key);
    out.push({role, name, path: path(el), disabled: !!el.disabled,
              ph: (el.placeholder || '').slice(0, 60), ty: ty || undefined});
  }
  return {title: document.title, url: location.href, elements: out};
})()
"""

    def do_page_elements(self, max_items: int = 60, **_) -> dict[str, Any]:
        _chrome_up()
        t = _active_target()
        r = _cdp_eval(t, self._JS_ELEMENTS, timeout=25) or {}
        els = list(r.get("elements") or [])[:max(1, min(int(max_items or 60), 200))]
        out = []
        self._els = {}
        for i, e in enumerate(els, 1):
            self._els[i] = e.get("path") or ""
            item = {"ref": i, "role": e.get("role"), "name": e.get("name")}
            if e.get("ph"): item["placeholder"] = e["ph"]
            if e.get("ty"): item["type"] = e["ty"]
            if e.get("disabled"): item["disabled"] = True
            out.append(item)
        self._els_src = f"{r.get('title', '')}|{r.get('url', '')}"
        return {"title": r.get("title", ""), "url": r.get("url", ""), "count": len(out), "elements": out}

    def _ref_sel(self, ref: int) -> str:
        sel = self._els.get(int(ref or 0))
        if not sel:
            raise ActionError(f"ref {ref} gaya - pehle page_elements dobara chalao (page badla ya naya session)")
        return sel

    def _js_on_ref(self, sel: str, body: str) -> Any:
        """Run body(el) inside a IIFE after resolving sel; body returns a plain object."""
        t = _active_target()
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};" + body + "})()")
        return _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}

    def do_page_click(self, ref: int, **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        r = self._js_on_ref(sel, """ el.scrollIntoView({block:'center'}); el.focus();
            const before = location.href; el.click();
            return {ok:true, was: before, now: location.href, title: document.title}; """)
        if not r.get("ok"):
            raise ActionError(f"click nahi hua ({r.get('err', '?')}) - page_elements dobara chalao")
        t = _active_target()
        return {"clicked": True, "title": t.get("title", ""), "url": t.get("url", ""),
                "navigated": r.get("was") != r.get("now")}

    _JS_TYPE = r""" el.scrollIntoView({block:'center'}); el.focus();
        if (el.disabled || el.readOnly) return {ok:false, err:'disabled'};
        if (CLR) { if (el.select) try { el.select(); } catch(e) {}
          let okDel = false; try { okDel = document.execCommand('delete'); } catch(e) {}
          if (!okDel && el.value !== undefined) { try { el.value = ''; } catch(e) {} } }
        let ok = false; try { ok = document.execCommand('insertText', false, TXT); } catch(e) {}
        if (!ok || (el.value || '') === '') {
          const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          const d = Object.getOwnPropertyDescriptor(proto, 'value');
          if (d && d.set) { d.set.call(el, (el.value || '') + TXT);
            el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }
        }
        const v = el.value || '';
        return {ok:true, length:v.length, matches: v === TXT || v.endsWith(TXT)};"""

    def do_page_type(self, ref: int, text: str = "", clear: bool = True, **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        txt = str(text or "")[:4000]
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};"
              " const TXT = " + json.dumps(txt) + "; const CLR = " + json.dumps(bool(clear)) + ";"
              + self._JS_TYPE + "})()")
        t = _active_target()
        r = _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}
        if not r.get("ok"):
            raise ActionError(f"type nahi hua ({r.get('err', '?')}) - page_elements dobara chalao")
        return {"typed": True, "length": r.get("length"), "matches": r.get("matches"),
                "note": "value kabhi wapas nahi aati (sirf length + match)"}

    def do_page_select(self, ref: int, value: str = "", **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};"
              " const VAL = " + json.dumps(str(value or "")) + ";"
              r""" if (el.tagName === 'SELECT') { el.focus();
                for (const o of el.options) { if (o.value === VAL || o.text.trim() === VAL ||
                    o.text.trim().toLowerCase() === VAL.toLowerCase()) { el.value = o.value;
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return {ok:true, picked:o.text.trim()}; } }
                return {ok:false, err:'option', options: Array.from(el.options).slice(0,30).map(o=>o.text.trim())}; }
              el.focus();
              const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
              if (d && d.set) { d.set.call(el, VAL); el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true})); }
              return {ok:true, picked:VAL}; })()""")
        t = _active_target()
        r = _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}
        if not r.get("ok"):
            raise ActionError(f"select nahi hua ({r.get('err', '?')})"
                              + (f" - options: {', '.join((r.get('options') or [])[:12])}" if r.get("options") else ""))
        return {"selected": r.get("picked")}

    def do_page_fill_form(self, entries: list | dict | None = None, **_) -> dict[str, Any]:
        """Many fields in ONE step: entries = [{'ref': 2, 'text': '...'}, ...]. Each field types with the
        same execCommand + events path as page_type; results come back per entry (text never echoed)."""
        _chrome_up()
        items = entries.get("entries") if isinstance(entries, dict) else entries
        if not isinstance(items, list) or not items:
            raise ActionError("entries chahiye: [{'ref': 2, 'text': '...'}, ...]")
        out = []
        for it in items[:20]:
            try:
                ref = int(it.get("ref") or 0)
                sel = self._ref_sel(ref)
            except (ActionError, TypeError, ValueError) as e:
                out.append({"ref": it.get("ref"), "ok": False, "err": str(e)[:120]})
                continue
            txt = str(it.get("text") or "")[:4000]
            js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
                  " if (!el) return {ok:false, err:'gone'};"
                  " const TXT = " + json.dumps(txt) + "; const CLR = true;" + self._JS_TYPE + "})()")
            try:
                r = _cdp_eval(_active_target(), js, timeout=25) or {"ok": False}
            except Exception as e:
                r = {"ok": False, "err": str(e)[:120]}
            out.append({"ref": ref, "ok": bool(r.get("ok")), "length": r.get("length"),
                        "matches": r.get("matches"), **({"err": r["err"]} if r.get("err") else {})})
        return {"filled": sum(1 for x in out if x.get("ok")), "total": len(out), "results": out}

    def do_wait_for(self, text: str = "", seconds: int = 15, **_) -> dict[str, Any]:
        """Wait until a text really appears on the page (polls innerText over CDP; max 20s)."""
        _chrome_up()
        want = str(text or "").strip()
        if not want:
            raise ActionError("Kis text ka intezaar?")
        end = time.time() + max(2, min(int(seconds or 15), 20))
        while time.time() < end:
            t = _active_target()
            body = str(_cdp_eval(t, "document.body ? document.body.innerText : ''", timeout=10) or "")
            if want.lower() in body.lower():
                return {"found": True, "title": t.get("title", "")}
            time.sleep(1.0)
        return {"found": False, "note": f"'{want[:60]}' {int(seconds or 15)}s mein nahi dikha"}

    def do_tabs(self, **_) -> dict[str, Any]:
        _chrome_up()
        ts = _targets()
        act = _active_window()
        tabs = [{"index": i + 1, "title": (t.get("title") or "")[:120],
                 "active": (t.get("title") == act) or (i == 0 and not act)} for i, t in enumerate(ts)]
        return {"tabs": tabs, "count": len(tabs)}

    def do_switch_tab(self, tab: str = "", index: int = 0, **_) -> dict[str, Any]:
        _chrome_up()
        ts = _targets()
        pick = None
        if index and 1 <= int(index) <= len(ts):
            pick = ts[int(index) - 1]
        else:
            q = str(tab or "").lower()
            pick = next((t for t in ts if q in (t.get("title") or "").lower()), None)
        if pick is None:
            raise ActionError("Waisa koi tab nahi khula")
        httpx.get(CDP + f"/json/activate/{pick['id']}", timeout=5)
        subprocess.run(["wmctrl", "-a", (pick.get("title") or "")[:80]], capture_output=True,
                       env={**os.environ, "DISPLAY": DISPLAY})
        return {"switched": (pick.get("title") or "")[:80], "title": pick.get("title", "")}

    def do_downloads(self, minutes: int = 15, **_) -> dict[str, Any]:
        mins = max(1, min(int(minutes or 15), 240))
        cutoff = time.time() - mins * 60
        files = []
        cand = sorted(DOWNLOADS.iterdir(), key=lambda c: c.stat().st_mtime if c.exists() else 0, reverse=True)[:20]
        for c in cand:
            if not c.is_file() or c.name.startswith("."):
                continue
            st = c.stat()
            if st.st_mtime < cutoff:
                break
            files.append({"name": c.name, "size_text": f"{st.st_size // 1024} KB", "partial": c.suffix == ".crdownload"})
        return {"files": files, "folder": str(DOWNLOADS)}

    # ---- files (same surface as Santosh Desktop, over /data) ----
    def do_status(self, **_) -> dict[str, Any]:
        i = self.info()
        i.pop("type", None)
        return i

    def do_list(self, path: str = "", **_) -> dict[str, Any]:
        p = Path(path or str(WORK if CUR["key"] else DATA))
        _guard(p)
        if not p.is_dir():
            raise ActionError("Yeh folder nahi hai")
        entries = []
        for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:300]:
            if c.name.startswith(".") or not allowed(c):
                continue
            try:
                st = c.stat()
            except OSError:
                continue
            entries.append({"name": c.name, "path": str(c), "dir": c.is_dir(), "size": st.st_size if c.is_file() else None,
                            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
        return {"path": str(p), "entries": entries}

    def do_read(self, path: str = "", max_chars: int = 12000, **_) -> dict[str, Any]:
        p = Path(path)
        _guard(p)
        if not p.is_file():
            raise ActionError("File nahi mili")
        n = max(500, min(int(max_chars or 12000), 40000))
        try:
            text = p.read_text(errors="ignore")[:n]
        except Exception as e:
            raise ActionError(f"Padh nahi paya: {e}")
        return {"path": str(p), "name": p.name, "text": text}

    def do_save_file(self, file_id: str = "", name: str = "", url: str = "", **_) -> dict[str, Any]:
        stem = Path(name or file_id or "file").stem
        ext = Path(name or file_id or "file").suffix
        dest = DOWNLOADS / (stem + ext)
        n = 1
        while dest.exists():                     # v0.202 never overwrite (Windows desktop parity)
            dest = DOWNLOADS / f"{stem} ({n}){ext}"
            n += 1
        with httpx.stream("GET", SERVER + (url or f"/api/pc/fetch/{file_id}"), timeout=300) as r:
            if r.status_code >= 400:
                raise ActionError(f"Download failed ({r.status_code})")
            with dest.open("wb") as out:
                for chunk in r.iter_bytes():
                    out.write(chunk)
        return {"saved_path": str(dest), "name": dest.name,
                "message": f"{dest.name} Hoola PC ke Downloads mein save ho gayi."}

    def do_send_file(self, path: str = "", **_) -> dict[str, Any]:
        """v0.202 the PC-to-PC bridge: hand one of MY files to the server so the USER'S personal PC can
        fetch it (her desktop saves it into her Santosh Inbox after she approves the confirm card the
        operator raised). Tagged direction "to_pc": only her paired desktop can fetch it - a phone
        download link can never pick it up. Same shape as the Windows desktop's do_send_file."""
        p = Path(path)
        if not p.is_absolute():
            p = (WORK if CUR["key"] else DATA) / p
        _guard(p)
        if not p.is_file():
            raise ActionError("File nahi mili")
        size = p.stat().st_size
        if size > MAX_SEND:
            raise ActionError(f"{p.name} is {size // (1024 * 1024)} MB; the limit is 50 MB.")
        token = _identity().get("token", "")
        with p.open("rb") as fh:
            r = httpx.post(SERVER + "/api/pc/files", headers={"Authorization": f"Bearer {token}"},
                           files={"file": (p.name, fh, "application/octet-stream")},
                           data={"path": str(p), "direction": "to_pc"}, timeout=300)
        if r.status_code >= 400:
            raise ActionError(f"Upload failed ({r.status_code}): {r.text[:160]}")
        return r.json()

    # ---- THE COWORKER SURFACE: install software + run commands (Hoola's own VM) ----
    def do_install(self, packages: str = "", pip: bool = False, **_) -> dict[str, Any]:
        pkgs = str(packages or "").strip()
        if not pkgs:
            raise ActionError("Batayiye kya install karna hai")
        if any(ch in pkgs for ch in ";|&`$>\n"):
            raise ActionError("Ek baar mein sirf package naam (koi shell nahi). Alag-alag naam dijiye.")
        names = pkgs.split()
        if pip:
            cmd = ["pip", "install", "--quiet", "--no-input", *names]
        else:
            subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=240)
            cmd = ["apt-get", "install", "-y", *names]
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=480, env=env)
        except subprocess.TimeoutExpired:
            raise ActionError("Install ne 8 minute mein jawab nahi diya (network dheema hai). Dobara koshish kijiye.")
        tail = ((p.stdout or "") + (p.stderr or ""))[-1500:]
        line = f"{time.strftime('%m-%d %H:%M')} {'pip' if pip else 'apt'} {pkgs} rc={p.returncode}"
        with (DATA / "installed.log").open("a") as fh:
            fh.write(line + "\n")
        if p.returncode != 0:
            raise ActionError(f"Install fail (rc={p.returncode}): {tail[-400:]}")
        return {"installed": names, "pip": bool(pip), "note": tail[-400:] or "installed"}

    def do_run(self, command: str = "", timeout: int = 60, background: bool = False, **_) -> dict[str, Any]:
        """One shell command in the active user's work folder, as the unprivileged worker user (v0.885). background
        = it keeps running (up to 2 hours) and run_status reads its output - for long conversions / downloads."""
        cmd = str(command or "").strip()
        if not cmd:
            raise ActionError("Kaunsa command?")
        cwd = str(WORK if CUR["key"] else DATA)
        if background:
            self._reap()
            live = [j for j in JOBS.values() if j["proc"].poll() is None]
            if len(live) >= JOB_MAX:
                raise ActionError(f"{JOB_MAX} commands pehle se chal rahe hain - run_status se dekhiye ya intezaar kijiye.")
            jid = "job" + str(int(time.time() * 1000))[-8:]
            logdir = Path(cwd) / ".jobs"
            logdir.mkdir(parents=True, exist_ok=True)
            logf = logdir / f"{jid}.log"
            fh = logf.open("ab")
            w = _worker()
            if w:
                try:
                    os.chown(logdir, *w)
                    os.chown(logf, *w)
                except OSError:
                    pass
            proc = subprocess.Popen(["bash", "-c", cmd], stdout=fh, stderr=subprocess.STDOUT, cwd=cwd,
                                    env=_run_env(), start_new_session=True, **_as_worker())
            JOBS[jid] = {"proc": proc, "log": logf, "started": time.time(), "cmd": cmd[:200]}
            return {"job": jid, "running": True, "cwd": cwd,
                    "note": "Running in the background (max 2 hours). Call run_status with this job id to see output."}
        limit = max(5, min(int(timeout or 60), 180))
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=limit,
                               env=_run_env(), cwd=cwd, **_as_worker())
        except subprocess.TimeoutExpired:
            raise ActionError(f"Command {limit}s mein ruk gaya (timeout). Lambe kaam ke liye background=true.")
        return {"exit": p.returncode, "stdout": (p.stdout or "")[-6000:],
                "stderr": (p.stderr or "")[-1500:], "cwd": cwd}

    def _reap(self) -> None:
        for jid, j in list(JOBS.items()):
            if j["proc"].poll() is None and time.time() - j["started"] > JOB_HOURS * 3600:
                _kill_job(j)
                j["killed"] = True

    def do_run_status(self, job: str = "", max_chars: int = 4000, **_) -> dict[str, Any]:
        self._reap()
        if not job:
            return {"jobs": [{"job": k, "running": v["proc"].poll() is None, "cmd": v["cmd"],
                              "seconds": int(time.time() - v["started"])} for k, v in JOBS.items()]}
        j = JOBS.get(str(job))
        if j is None:
            raise ActionError("Yeh job nahi mila (PC badla ya restart hua).")
        rc = j["proc"].poll()
        try:
            data = j["log"].read_bytes()[-max(500, min(int(max_chars or 4000), 20000)):]
        except OSError:
            data = b""
        return {"job": job, "running": rc is None, "exit": rc, "seconds": int(time.time() - j["started"]),
                "output": data.decode("utf-8", "replace"), "stopped_after_2h": bool(j.get("killed"))}

    def do_run_stop(self, job: str = "", **_) -> dict[str, Any]:
        j = JOBS.get(str(job))
        if j is None:
            raise ActionError("Yeh job nahi mila.")
        _kill_job(j)
        return {"job": job, "stopped": True}

    # ---- v0.885 the pool ----
    def do_profile(self, key: str = "", secret: str = "", home: bool = False, **_) -> dict[str, Any]:
        """The server tells this PC whose folder to use before every task (one user at a time)."""
        return use_profile(key, secret, bool(home))


# ---------------- the bridge (same protocol as the Windows desktop) ----------------
def _ws_url(server: str) -> str:
    s = server.rstrip("/")
    scheme = "ws://" if not s.startswith("https://") else "wss://"
    return scheme + s.split("://", 1)[1] + "/api/pc/ws"


async def _connect(url: str, token: str):
    import websockets
    headers = {"Authorization": f"Bearer {token}"}
    try:
        from websockets.asyncio.client import connect  # websockets >= 13
        return await connect(url, additional_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30, open_timeout=20)
    except ImportError:
        return await websockets.connect(url, extra_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30)


class Bridge:
    def __init__(self, actions: Actions) -> None:
        self.actions = actions
        self.ws: Any = None

    async def _send(self, msg: dict[str, Any]) -> None:
        if self.ws is not None:
            await self.ws.send(json.dumps(msg, ensure_ascii=False, default=str))

    async def run_forever(self) -> None:
        delay = 1.0
        while True:
            if not _identity():
                code_file = DATA / "pair_code"
                code = code_file.read_text().strip() if code_file.exists() else ""
                if len(code) == 6 and code.isdigit():
                    try:
                        device_id = await asyncio.to_thread(pair_once, code)
                        code_file.unlink()
                        print(f"PAIRED: {device_id}", flush=True)
                    except Exception as e:
                        print(f"pair failed: {e}", flush=True)
                        await asyncio.sleep(5)
                    continue
                print("waiting for pair code: docker exec hoola-pc sh -c 'echo 123456 > /data/pair_code'", flush=True)
                await asyncio.sleep(3)
                continue
            ident = _identity()
            try:
                self.ws = await _connect(_ws_url(SERVER), ident["token"])
                print("connected: Hoola PC is online", flush=True)
                delay = 1.0
                await self._send(self.actions.info())
                async for raw in self.ws:
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    t = msg.get("type")
                    if t == "hello":
                        await self._send(self.actions.info())
                    elif t == "ping":
                        await self._send({"type": "pong"})
                    elif t == "job":
                        asyncio.create_task(self._job(msg))
            except Exception as e:
                code = getattr(getattr(e, "rcvd", None), "code", None) or getattr(e, "code", None)
                if code in (4401, 4403):
                    print("unpaired by the server; waiting for a new pair code", flush=True)
                    (DATA / "identity.json").unlink(missing_ok=True)
                    continue
                print(f"connection toota, {int(delay)}s mein dobara… ({type(e).__name__})", flush=True)
            finally:
                self.ws = None
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _job(self, msg: dict[str, Any]) -> None:
        jid, action, args = msg.get("id"), str(msg.get("action") or ""), msg.get("args") or {}
        t0 = time.time()
        try:
            data = await asyncio.to_thread(self.actions.handle, action, args)
            reply = {"type": "result", "id": jid, "ok": True, "data": data}
        except ActionError as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": str(e)[:300]}
        except Exception as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        print(f"job {action} -> {'ok' if reply.get('ok') else str(reply.get('error', ''))[:80]} ({time.time() - t0:.1f}s)", flush=True)
        try:
            await self._send(reply)
        except Exception:
            pass


def replay_installs(log_path: Path | None = None, dry: bool = False) -> list[str]:
    """v0.885 software Hoola installed before lives in installed.log; a rebuilt image does not have it any more.
    Missing apt / pip packages from SUCCESSFUL installs are put back once at boot (in the background)."""
    f = log_path or (DATA / "installed.log")
    apt: list[str] = []
    pipn: list[str] = []
    try:
        lines = f.read_text().splitlines()
    except OSError:
        return []
    for line in lines:
        m = re.match(r"^\S+ \S+ (apt|pip) (.+) rc=0$", line.strip())
        if not m:
            continue
        for n in m.group(2).split():
            if re.match(r"^[A-Za-z0-9][A-Za-z0-9.+_=<>~-]*$", n):
                (apt if m.group(1) == "apt" else pipn).append(n)
    apt = list(dict.fromkeys(apt))
    pipn = list(dict.fromkeys(pipn))
    if dry:
        return apt + ["pip:" + n for n in pipn]
    miss_apt = [n for n in apt if subprocess.run(["dpkg", "-s", n], capture_output=True).returncode != 0]
    miss_pip = [n for n in pipn if subprocess.run(["pip", "show", re.split(r"[=<>~]", n)[0]],
                                                  capture_output=True).returncode != 0]
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    if miss_apt:
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=300)
        subprocess.run(["apt-get", "install", "-y", *miss_apt], capture_output=True, timeout=1800, env=env)
    if miss_pip:
        subprocess.run(["pip", "install", "--quiet", "--no-input", *miss_pip], capture_output=True, timeout=1800)
    if miss_apt or miss_pip:
        print(f"reinstalled after rebuild: {' '.join(miss_apt + miss_pip)}", flush=True)
    return miss_apt + miss_pip


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":   # v0.884: docker exec hoola-pc python /app/agent.py check <urls>
        global PROFILE
        try:
            httpx.get(CDP + "/json/version", timeout=2)
            own = False                     # a Chrome is already up (serving a user): use it, never stop it
        except Exception:
            own = True                      # v0.885 nobody's folder: a throwaway profile, closed afterwards
            PROFILE = Path("/tmp/hoola-check-profile")
            PROFILE.mkdir(parents=True, exist_ok=True)
        try:
            res = Actions().do_check(sys.argv[2:] or ["https://www.google.com"])
        finally:
            if own:
                _stop_chrome()
        for r in res["sites"]:
            print(f"{'OK  ' if r.get('ok') else 'FAIL'} {r.get('seconds', '-'):>5}s {r['url']}  "
                  f"{r.get('problem') or ''} {r.get('note') or ''} | {r.get('title') or ''}", flush=True)
        return
    print(f"Hoola PC agent {VERSION} -> {SERVER} (display {DISPLAY})", flush=True)
    for c in PROFILES.iterdir() if PROFILES.is_dir() else []:   # v0.885 left readable by a restart: root only
        try:
            if c.is_dir():
                os.chmod(c, 0o700)
        except OSError:
            pass
    threading.Thread(target=replay_installs, daemon=True).start()
    asyncio.run(Bridge(Actions()).run_forever())


if __name__ == "__main__":
    main()
