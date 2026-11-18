"""Semantic desktop control through the OS accessibility tree (v1.6.0): the DESKTOP twin of the v1.5.0
semantic browser.

agent-desktop (vercel-labs, Apache-2.0, https://github.com/vercel-labs/agent-desktop) reads an app's UI the
way Windows itself sees it (UIA): one `snapshot` lists every button / field / link with a ref like
@s8f3k2p9:e12, and actions land on the ref - no pixel guessing, no focus steal (headless by default), and
every action reports whether it was delivered and verified. Hoola uses it so Excel, Word, TallyPrime's UI,
File Explorer dialogs and any other desktop app work like page_elements / page_click / page_type already
work in Chrome.

The helper binary (`agent-desktop.exe`, ~1.7 MB) ships BESIDE SantoshDesktop.exe - build-desktop.yml
downloads the official release archive and puts it next to the PyInstaller output. Search order:
HOOLA_AGENT_DESKTOP env var > beside the exe (frozen) > beside this module (source runs) > PATH.
When it is missing everything here raises AxUnavailable and the PC falls back to the pixel lane it
always had - nothing else in the app depends on this module being usable.

Every CLI call is one process that prints ONE JSON envelope ({ok, data | error{code, disposition}}).
Refs belong to their snapshot and are re-identified before an action lands; identical twin controls are
REFUSED (AMBIGUOUS_TARGET) instead of clicked by luck, and the CLI refuses dangerous shortcuts
(alt+f4, win+l...) on its own - the same direction as our own BLOCKED_KEYS.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any

STATE_ROOT = os.path.join(os.path.expanduser("~"), ".agent-desktop")   # the CLI's own snapshot store
MAX_WAIT_S = 25            # longest any single CLI call may run (wait caps below this)
MAX_TREE_ITEMS = 120       # flat element cap for one snapshot sent to the model
MAX_TEXT_CHARS = 6000      # ax_text cap (page_text parity)


class AxError(Exception):
    """A structured refusal / failure from the helper (carries the envelope's own fields)."""

    def __init__(self, code: str, message: str, suggestion: str = "", retry_safe: bool = True,
                 delivery: str = "not_delivered"):
        super().__init__(message or code)
        self.code, self.message, self.suggestion = code, message, suggestion
        self.retry_safe, self.delivery = retry_safe, delivery

    def __str__(self) -> str:      # the ActionError text the server shows the model
        s = f"{self.code}: {self.message}"
        if self.suggestion:
            s += f" ({self.suggestion})"
        return s[:300]


class AxUnavailable(Exception):
    """The helper binary is not installed / not runnable - pixel mode keeps working."""


def _exe() -> str:
    """Path of the agent-desktop helper: env > beside the exe > beside this file > PATH."""
    cand = os.environ.get("HOOLA_AGENT_DESKTOP", "").strip()
    if cand and os.path.isfile(cand):
        return cand
    bases = []
    if getattr(sys, "frozen", False):                    # PyInstaller onefile: beside SantoshDesktop.exe
        bases.append(os.path.dirname(sys.executable))
    bases.append(os.path.dirname(os.path.abspath(__file__)))
    name = "agent-desktop.exe" if sys.platform == "win32" else "agent-desktop"
    for b in bases:
        p = os.path.join(b, name)
        if os.path.isfile(p):
            return p
    found = shutil.which(name)
    if found:
        return found
    raise AxUnavailable("agent-desktop helper nahi mila (agent-desktop.exe SantoshDesktop.exe ke bagal mein hona chahiye)")


def available() -> bool:
    try:
        _exe()
        return True
    except AxUnavailable:
        return False


def _run(args: list[str], timeout: float = MAX_WAIT_S, stdin: str | None = None) -> Any:
    """One CLI call, one JSON envelope. FileNotFoundError -> AxUnavailable (binary gone), bad JSON -> AxError.
    v1.10.0: `stdin` = text handed over a pipe (agent-desktop 1.2 --stdin), so what Hoola types - an Aadhaar or
    PAN from her ID locker included - never sits on the process command line where other programs can read it."""
    exe = _exe()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0   # never flash a console window
    try:
        r = subprocess.run([exe, *args], capture_output=True, timeout=max(2.0, timeout),
                           input=(stdin.encode("utf-8") if stdin is not None else None),
                           creationflags=flags if sys.platform == "win32" else 0)
    except FileNotFoundError as e:
        raise AxUnavailable(f"agent-desktop helper chal nahi paya: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise AxError("TIMEOUT", f"helper {timeout:.0f}s mein jawab nahi de gaya ({' '.join(args[:2])[:60]})") from e
    try:
        env = json.loads(r.stdout.decode("utf-8", "ignore"))
    except ValueError as e:
        raise AxError("INTERNAL", f"helper ka jawab JSON nahi tha ({(r.stderr or b'')[:120]!r})") from e
    if env.get("ok"):
        return env.get("data") or {}
    err = env.get("error") or {}
    disp = err.get("disposition") or {}
    raise AxError(str(err.get("code") or "INTERNAL"), str(err.get("message") or "helper error"),
                  str(err.get("suggestion") or ""), disp.get("retry") == "safe",
                  str(disp.get("delivery") or "not_delivered"))


_STATES = ("checked", "selected", "expanded", "collapsed", "disabled", "focused", "pressed", "readonly", "offscreen")


def _cap(s: Any, n: int = 80) -> str:
    return str(s or "").strip()[:n]


def _walk(node: dict[str, Any], out: list[dict[str, Any]], depth: int = 0) -> None:
    """Flatten the accessibility tree into the elements the model can act on (page_elements shape)."""
    if len(out) >= MAX_TREE_ITEMS or depth > 24 or not isinstance(node, dict):
        return
    ref = node.get("ref_id")
    if ref:
        row = {"ref": ref, "role": _cap(node.get("role"), 24), "name": _cap(node.get("name"), 90)}
        if node.get("value"):
            row["value"] = _cap(node.get("value"), 60)
        if node.get("description"):
            row["desc"] = _cap(node.get("description"), 60)
        if "disabled" in node and node.get("disabled"):
            row["disabled"] = True
        st = [x for x in (node.get("states") or []) if x in _STATES]   # v1.10.0 checked / selected / expanded ...
        if st:
            row["states"] = st[:5]
        out.append(row)
    for ch in node.get("children") or []:
        _walk(ch, out, depth + 1)
        if len(out) >= MAX_TREE_ITEMS:
            return


def _lines(node: dict[str, Any], out: list[str], depth: int = 0) -> None:
    """Every named node as an indented line - the 'read the screen' view (ax_text)."""
    if len(out) > 400 or depth > 24 or not isinstance(node, dict):
        return
    name = _cap(node.get("name"), 100)
    if name:
        out.append("  " * min(depth, 6) + f"{node.get('role', '?')}: {name}")
    for ch in node.get("children") or []:
        _lines(ch, out, depth + 1)
        if len(out) > 400:
            return


# ---------------- status / inventory ----------------
def status() -> dict[str, Any]:
    d = _run(["status"], timeout=15)
    perm = (d.get("permissions") or {}).get("accessibility") or {}
    return {"available": True, "platform": d.get("platform"), "helper": _exe(),
            "accessibility": perm.get("state") or "unknown",
            "suggestion": _cap(perm.get("suggestion"), 160)}


def list_apps() -> dict[str, Any]:
    d = _run(["list-apps", "--timeout-ms", "8000"], timeout=15)
    apps = [{"name": _cap(a.get("name") or a.get("process"), 60), "pid": a.get("pid")}
            for a in (d.get("apps") or d if isinstance(d, list) else d.get("apps") or [])[:60]
            if isinstance(a, dict)]
    return {"apps": apps, "count": len(apps)}


def windows() -> dict[str, Any]:
    d = _run(["list-windows", "--timeout-ms", "8000"], timeout=15)
    wins = d.get("windows") if isinstance(d, dict) else d
    out = [{"id": _cap(w.get("id"), 24), "title": _cap(w.get("title"), 90), "app": _cap(w.get("app") or w.get("process"), 40)}
           for w in (wins or []) if isinstance(w, dict)][:40]
    return {"windows": out, "count": len(out)}


# ---------------- observe ----------------
def snapshot(app: str = "", window_id: str = "", skeleton: bool = False, root: str = "",
             surface: str = "", timeout_ms: int = 6000) -> dict[str, Any]:
    """Interactive elements of one app as flat refs (page_elements for the desktop). app='' reads the
    focused window (--surface focused)."""
    args = ["snapshot", "-i", "--compact", "--timeout-ms", str(max(1500, min(int(timeout_ms or 6000), 20000)))]
    if app:
        args += ["--app", app[:60]]
    elif surface in ("window", "focused", ""):
        args += ["--surface", "focused"]
    else:                                    # menus / sheets / alerts are their own surfaces
        args += ["--surface", surface[:20]]
    if window_id:
        args += ["--window-id", window_id[:24]]
    if skeleton:
        args.append("--skeleton")
    if root:
        args += ["--root", root[:40]]
    d = _run(args, timeout=min(MAX_WAIT_S, timeout_ms / 1000 + 8))
    els: list[dict[str, Any]] = []
    _walk(d.get("tree") or {}, els)
    win = d.get("window") or {}
    return {"snapshot_id": d.get("snapshot_id"), "window": _cap(win.get("title"), 90), "app": _cap(d.get("app"), 60),
            "complete": d.get("complete", True), "identity_unproven": bool(d.get("identity_unproven")),
            "truncated": bool(d.get("truncated")), "count": len(els), "elements": els,
            "surfaces": _surfaces(d),
            "note": ("refs not proven unique (window read incomplete) - re-snapshot with a longer timeout"
                     if d.get("identity_unproven") else "")}


def read(app: str = "", surface: str = "", timeout_ms: int = 6000, max_chars: int = MAX_TEXT_CHARS) -> dict[str, Any]:
    """The whole visible text of a desktop app (page_text for the desktop): roles + names, depth-first."""
    args = ["snapshot", "--compact", "--timeout-ms", str(max(1500, min(int(timeout_ms or 6000), 20000)))]
    if app:
        args += ["--app", app[:60]]
    elif surface in ("window", "focused", ""):
        args += ["--surface", "focused"]
    else:
        args += ["--surface", surface[:20]]
    d = _run(args, timeout=min(MAX_WAIT_S, timeout_ms / 1000 + 8))
    lines: list[str] = []
    _lines(d.get("tree") or {}, lines)
    win = d.get("window") or {}
    return {"app": _cap(d.get("app"), 60) or _cap(app, 60), "window": _cap(win.get("title"), 90),
            "text": "\n".join(lines)[:max(500, min(int(max_chars or MAX_TEXT_CHARS), 12000))],
            "complete": d.get("complete", True)}


def find(app: str = "", role: str = "", name: str = "", text: str = "", exact: bool = False) -> dict[str, Any]:
    args = ["find", "--timeout-ms", "8000"]
    if app:
        args += ["--app", app[:60]]
    if role:
        args += ["--role", role[:24]]
    if name:
        args += ["--name", name[:80]]
    if text:
        args += ["--text", text[:80]]
    if exact:
        args.append("--exact")
    if not (role or name or text):
        raise AxError("INVALID_ARGS", "find needs role, name or text")
    d = _run(args, timeout=15)
    matches = d.get("matches") if isinstance(d, dict) else d
    out = [{"ref": _cap(m.get("ref_id") or m.get("ref"), 40), "role": _cap(m.get("role"), 24),
            "name": _cap(m.get("name"), 90), "value": _cap(m.get("value"), 60)}
           for m in (matches or []) if isinstance(m, dict)][:MAX_TREE_ITEMS]
    return {"count": len(out), "matches": out}


# ---------------- act ----------------
def click(ref: str, timeout_ms: int = 6000) -> dict[str, Any]:
    ref = str(ref or "").strip()
    if not ref.startswith("@"):
        raise AxError("INVALID_ARGS", "ref must be a @snapshot:element ref from ax_snapshot / ax_find")
    d = _run(["click", ref, "--timeout-ms", str(max(2000, min(int(timeout_ms or 6000), 15000)))],
             timeout=min(MAX_WAIT_S, timeout_ms / 1000 + 8))
    disp = d.get("disposition") or {}
    return {"ref": ref, "clicked": True, "delivery": disp.get("delivery") or "delivered_unverified",
            "verified": disp.get("delivery") == "delivered_verified",
            "surfaces": _surfaces(d)}


def _surfaces(d: Any) -> list[str]:
    """v1.10.0 the surfaces a click opened, as words ('menu: File', 'sheet: Save As'). agent-desktop 1.1+ sends
    objects {id, type, title}; the old code printed their Python repr cut at 20 chars ("{'id': 'w-1.1-org-gn")."""
    out = []
    for x in ((d or {}).get("surfaces") or [])[:8]:
        if isinstance(x, dict):
            t = _cap(x.get("type") or x.get("kind") or "surface", 16)
            title = _cap(x.get("title") or x.get("name"), 40)
            out.append(f"{t}: {title}" if title else t)
        else:
            out.append(_cap(x, 40))
    return out


def set_value(ref: str, text: str, timeout_ms: int = 6000) -> dict[str, Any]:
    """Write into a field BY REF. Privacy parity with page_type: the value never travels back - only
    whether the helper verified the readback."""
    ref = str(ref or "").strip()
    if not ref.startswith("@"):
        raise AxError("INVALID_ARGS", "ref must be a @snapshot:element ref from ax_snapshot / ax_find")
    if not text:
        raise AxError("INVALID_ARGS", "text khali hai")
    d = _run(["set-value", ref, "--stdin", "--timeout-ms", str(max(2000, min(int(timeout_ms or 6000), 15000)))],
             timeout=min(MAX_WAIT_S, timeout_ms / 1000 + 8), stdin=str(text)[:4000])
    disp = d.get("disposition") or {}
    return {"ref": ref, "length": len(str(text)), "delivery": disp.get("delivery") or "delivered_unverified",
            "verified": disp.get("delivery") == "delivered_verified"}


def press(keys: str, app: str = "") -> dict[str, Any]:
    keys = str(keys or "").strip()[:40]
    if not keys:
        raise AxError("INVALID_ARGS", "which keys?")
    args = ["press", keys]
    if app:
        args += ["--app", app[:60]]
    d = _run(args, timeout=15)
    disp = d.get("disposition") or {}
    return {"pressed": keys, "delivery": disp.get("delivery") or "delivered_unverified"}


def launch(app: str, timeout_ms: int = 20000) -> dict[str, Any]:
    if not app:
        raise AxError("INVALID_ARGS", "which app?")
    d = _run(["launch", app[:200], "--timeout", str(max(5000, min(int(timeout_ms or 20000), 30000)))],
             timeout=min(45, timeout_ms / 1000 + 10))
    return {"launched": _cap(d.get("name") or d.get("app") or app, 80)}


def wait(app: str = "", text: str = "", window: str = "", seconds: int = 10) -> dict[str, Any]:
    secs = max(1, min(int(seconds or 10), 20))
    args = ["wait", str(secs * 1000)]
    if text:
        args += ["--text", text[:80]]
    if window:
        args += ["--window", window[:80]]
    if app and (text or window):
        args += ["--app", app[:60]]
    if not (text or window):
        raise AxError("INVALID_ARGS", "wait needs text or window")
    d = _run(args, timeout=secs + 10)
    return {"found": bool(d.get("matched", d.get("found", True))), "waited": secs}



# ---------------- v1.10.0 AGENT-DESKTOP FULL: every headless command worth having ----------------
# Owner: "GO AGENT-DESKTOP FULL". Everything below stays HEADLESS (no focus steal, no cursor moves): the
# commands that need --headed (focus, double-click, triple-click, hover, mouse-*, key-down/up) are left out on
# purpose - the pixel lane (control.py) already does physical input behind the same switch and orange bar.
def _ref(ref: Any) -> str:
    ref = str(ref or "").strip()
    if not ref.startswith("@") or len(ref) > 48:
        raise AxError("INVALID_ARGS", "ref must be a @snapshot:element ref from ax_snapshot / ax_find")
    return ref


def _tms(v: Any, lo: int = 2000, hi: int = 15000, default: int = 6000) -> int:
    try:
        return max(lo, min(int(v or default), hi))
    except (TypeError, ValueError):
        return default


def _delivery(d: Any) -> dict[str, Any]:
    disp = (d or {}).get("disposition") or {}
    return {"delivery": disp.get("delivery") or "delivered_unverified", "verified": disp.get("delivery") == "delivered_verified"}


GET_PROPS = ("text", "value", "title", "bounds", "role", "states")
IS_STATES = ("visible", "enabled", "checked", "focused", "expanded", "selected")
REF_ACTIONS = ("check", "uncheck", "toggle", "expand", "collapse", "clear", "scroll-to", "right-click")


def get(ref: str, prop: str = "text") -> dict[str, Any]:
    prop = str(prop or "text").strip().lower()
    if prop not in GET_PROPS:
        raise AxError("INVALID_ARGS", f"property must be one of {', '.join(GET_PROPS)}")
    d = _run(["get", _ref(ref), "--property", prop], timeout=15)
    v = d.get("value")
    if isinstance(v, str):
        v = v[:2000]
    return {"ref": ref, "property": prop, "value": v}


def is_state(ref: str, state: str = "visible") -> dict[str, Any]:
    state = str(state or "visible").strip().lower()
    if state not in IS_STATES:
        raise AxError("INVALID_ARGS", f"state must be one of {', '.join(IS_STATES)}")
    d = _run(["is", _ref(ref), "--property", state], timeout=15)
    val = d.get("value", d.get("result", d.get(state)))
    return {"ref": ref, "state": state, "value": bool(val)}


def act(op: str, ref: str, timeout_ms: int = 6000) -> dict[str, Any]:
    """One semantic action on an element: check / uncheck / toggle / expand / collapse / clear / scroll-to /
    right-click (a context menu opened semantically)."""
    op = str(op or "").strip().lower().replace("_", "-")
    if op not in REF_ACTIONS:
        raise AxError("INVALID_ARGS", f"op must be one of {', '.join(REF_ACTIONS)}")
    t = _tms(timeout_ms)
    d = _run([op, _ref(ref), "--timeout-ms", str(t)], timeout=min(MAX_WAIT_S, t / 1000 + 8))
    return {"ref": ref, "op": op, **_delivery(d), "surfaces": _surfaces(d)}


def select(ref: str, value: str, timeout_ms: int = 6000) -> dict[str, Any]:
    value = str(value or "").strip()
    if not value:
        raise AxError("INVALID_ARGS", "which option?")
    t = _tms(timeout_ms)
    d = _run(["select", _ref(ref), value[:200], "--timeout-ms", str(t)], timeout=min(MAX_WAIT_S, t / 1000 + 8))
    return {"ref": ref, "selected": value[:200], **_delivery(d)}


def type_text(ref: str, text: str, interval_ms: int = 0, timeout_ms: int = 0) -> dict[str, Any]:
    """Insert text into a field the way a keyboard would (fields that ignore set-value: search boxes, Tally's
    entry lines). Over a pipe (--stdin), never on the command line; only the length comes back."""
    if not text:
        raise AxError("INVALID_ARGS", "text khali hai")
    text = str(text)[:4000]
    args = ["type", _ref(ref), "--stdin"]
    if interval_ms:
        args += ["--interval-ms", str(max(1, min(int(interval_ms), 200)))]
    secs = 8 + len(text) * (max(1, int(interval_ms or 0)) / 1000 + 0.03)
    d = _run(args, timeout=min(90, secs), stdin=text)
    return {"ref": ref, "length": len(text), **_delivery(d)}


def scroll(ref: str, direction: str = "down", amount: int = 3) -> dict[str, Any]:
    direction = str(direction or "down").lower()
    if direction not in ("up", "down", "left", "right"):
        raise AxError("INVALID_ARGS", "direction must be up / down / left / right")
    n = max(1, min(int(amount or 3), 20))
    d = _run(["scroll", _ref(ref), "--direction", direction, "--amount", str(n)], timeout=15)
    return {"ref": ref, "scrolled": direction, "amount": n, **_delivery(d)}


def close_app(app: str) -> dict[str, Any]:
    """Quit an app GRACEFULLY (its own 'save changes?' prompt can appear). --force is never sent."""
    app = str(app or "").strip()
    if not app:
        raise AxError("INVALID_ARGS", "which app?")
    d = _run(["close-app", app[:60]], timeout=20)
    return {"app": _cap(d.get("app") or app, 60), **_delivery(d),
            "closed": ((d.get("details") or {}).get("evidence") == "process_instance_exited")}


def displays() -> dict[str, Any]:
    d = _run(["list-displays"], timeout=15)
    rows = d if isinstance(d, list) else (d.get("displays") or [])
    out = [{"index": i, "primary": bool(x.get("is_primary")), "scale": x.get("scale"),
            "width": int((x.get("bounds") or {}).get("width") or 0), "height": int((x.get("bounds") or {}).get("height") or 0)}
           for i, x in enumerate(rows) if isinstance(x, dict)][:8]
    return {"displays": out, "count": len(out)}


def window_shot(app: str = "", window_id: str = "", max_width: int = 1280) -> dict[str, Any]:
    """A picture of ONE app window (not the whole desktop) as a JPEG, base64 - like screen() but tight."""
    import base64
    import io
    import tempfile
    if not (app or window_id):
        raise AxError("INVALID_ARGS", "which app or window?")
    fd, path = tempfile.mkstemp(prefix="hoola_win_", suffix=".png")
    os.close(fd)
    os.unlink(path)                              # the helper writes a NEW file only
    try:
        args = ["screenshot"] + (["--window-id", str(window_id)[:80]] if window_id else ["--app", str(app)[:60]]) + [path]
        d = _run(args, timeout=20)
        from PIL import Image
        img = Image.open(d.get("path") or path).convert("RGB")
        if img.width > max_width:
            img = img.resize((max_width, int(img.height * max_width / img.width)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=70)
        return {"image_b64": base64.b64encode(buf.getvalue()).decode(), "width": img.width, "height": img.height,
                "app": _cap(app, 60)}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


SYSTEM_SURFACES = ("start-menu", "taskbar", "system-tray", "system-tray-overflow", "action-center", "quick-settings")


def surfaces(app: str) -> dict[str, Any]:
    d = _run(["list-surfaces", "--app", str(app or "")[:60]], timeout=15)
    out = [{"type": _cap(x.get("type"), 16), "title": _cap(x.get("title"), 60), "id": _cap(x.get("id"), 80)}
           for x in (d.get("surfaces") or []) if isinstance(x, dict)][:12]
    return {"app": _cap(app, 60), "surfaces": out, "count": len(out)}


def open_surface(surface: str) -> dict[str, Any]:
    surface = str(surface or "").strip().lower()
    if surface not in SYSTEM_SURFACES:
        raise AxError("INVALID_ARGS", f"surface must be one of {', '.join(SYSTEM_SURFACES)}")
    d = _run(["open-system-surface", "--surface", surface], timeout=20)
    win = d.get("window") or {}
    return {"opened": surface, "window_id": _cap(win.get("id") if isinstance(win, dict) else win, 80),
            "title": _cap(win.get("title") if isinstance(win, dict) else "", 60)}


def notifications(app: str = "", text: str = "", limit: int = 10) -> dict[str, Any]:
    args = ["list-notifications", "--limit", str(max(1, min(int(limit or 10), 30)))]
    if app:
        args += ["--app", str(app)[:60]]
    if text:
        args += ["--text", str(text)[:80]]
    d = _run(args, timeout=15)
    rows = d if isinstance(d, list) else (d.get("notifications") or [])
    out = []
    for i, n in enumerate(rows):
        if not isinstance(n, dict):
            continue
        out.append({"index": int(n.get("index") or i + 1), "app": _cap(n.get("app") or n.get("app_name"), 40),
                    "title": _cap(n.get("title"), 80), "body": _cap(n.get("body") or n.get("text"), 200),
                    "actions": [_cap(a.get("name") if isinstance(a, dict) else a, 30) for a in (n.get("actions") or [])][:6]})
    return {"notifications": out[:30], "count": len(out)}


def dismiss_notification(index: int, expected_app: str = "", expected_title: str = "") -> dict[str, Any]:
    if not (expected_app or expected_title):
        raise AxError("INVALID_ARGS", "say which notification: expected_app or expected_title (from ax_notifications)")
    args = ["dismiss-notification", str(max(1, int(index or 1)))]
    if expected_app:
        args += ["--expected-app", str(expected_app)[:60]]
    if expected_title:
        args += ["--expected-title", str(expected_title)[:120]]
    d = _run(args, timeout=15)
    return {"dismissed": int(index), **_delivery(d)}


def notification_action(index: int, action: str, expected_app: str = "", expected_title: str = "") -> dict[str, Any]:
    if not action:
        raise AxError("INVALID_ARGS", "which button (Reply / Open ...)?")
    if not (expected_app or expected_title):
        raise AxError("INVALID_ARGS", "say which notification: expected_app or expected_title (from ax_notifications)")
    args = ["notification-action", str(max(1, int(index or 1))), str(action)[:40]]
    if expected_app:
        args += ["--expected-app", str(expected_app)[:60]]
    if expected_title:
        args += ["--expected-title", str(expected_title)[:120]]
    d = _run(args, timeout=20)
    return {"index": int(index), "action": str(action)[:40], **_delivery(d)}


def clipboard_get() -> dict[str, Any]:
    d = _run(["clipboard-get"], timeout=15)
    return {"type": _cap(d.get("type"), 16), "text": str(d.get("text") or "")[:6000]}


def clipboard_set(text: str) -> dict[str, Any]:
    text = str(text or "")[:10000]
    if not text:
        raise AxError("INVALID_ARGS", "text khali hai")
    d = _run(["clipboard-set", "--stdin"], timeout=15, stdin=text)
    return {"length": len(text), **_delivery(d)}


def clipboard_clear() -> dict[str, Any]:
    d = _run(["clipboard-clear"], timeout=15)
    return {"cleared": True, **_delivery(d)}


# batch: a FEW safe steps in one call. Text-writing steps are NOT allowed here (a batch carries its JSON on the
# command line - an ID-locker number must ride --stdin through ax_set_value / ax_type instead), and neither are
# press / launch / close-app / notification actions (each of those is its own decision).
BATCH_OK = {"click", "check", "uncheck", "toggle", "expand", "collapse", "select", "scroll", "scroll-to", "clear",
            "get", "is", "find", "wait"}
BATCH_MAX = 8


def batch(steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(steps, list) or not steps:
        raise AxError("INVALID_ARGS", "steps: a list of {command, args}")
    if len(steps) > BATCH_MAX:
        raise AxError("INVALID_ARGS", f"at most {BATCH_MAX} steps in one batch")
    clean = []
    for i, st in enumerate(steps):
        cmd = str((st or {}).get("command") or "").strip().lower().replace("_", "-")
        args = (st or {}).get("args") or {}
        if cmd not in BATCH_OK or not isinstance(args, dict):
            raise AxError("INVALID_ARGS", f"step {i + 1}: '{cmd}' is not allowed in a batch ({', '.join(sorted(BATCH_OK))})")
        safe = {}
        for k, v in args.items():
            if k in ("text", "value") and cmd not in ("select", "find", "wait"):
                raise AxError("INVALID_ARGS", f"step {i + 1}: write text with ax_set_value / ax_type, not in a batch")
            if isinstance(v, (str, int, float, bool)):
                safe[str(k)[:24]] = v if not isinstance(v, str) else v[:200]
        if cmd == "wait":
            safe["ms"] = max(50, min(int(safe.get("ms") or 300), 5000))
        clean.append({"command": cmd, "args": safe})
    d = _run(["batch", json.dumps(clean), "--stop-on-error", "--timeout-ms", "30000"], timeout=MAX_WAIT_S + 10)
    res = []
    for r in (d.get("results") or [])[:BATCH_MAX]:
        if not isinstance(r, dict):
            continue
        err = r.get("error") or {}
        res.append({"command": r.get("command"), "ok": not err,
                    "error": (f"{err.get('code')}: {_cap(err.get('message'), 120)}" if err else ""),
                    "value": (r.get("data") or {}).get("value") if isinstance(r.get("data"), dict) else None})
    return {"completed": int(d.get("completed_entries") or 0), "not_started": int(d.get("not_started_entries") or 0),
            "results": res}
