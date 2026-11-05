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


def _run(args: list[str], timeout: float = MAX_WAIT_S) -> dict[str, Any]:
    """One CLI call, one JSON envelope. FileNotFoundError -> AxUnavailable (binary gone), bad JSON -> AxError."""
    exe = _exe()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0   # never flash a console window
    try:
        r = subprocess.run([exe, *args], capture_output=True, timeout=max(2.0, timeout),
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
            "surfaces": [_cap(s, 20) for s in (d.get("surfaces") or [])][:8],
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
            "surfaces": [_cap(s, 20) for s in (d.get("surfaces") or [])][:8]}


def set_value(ref: str, text: str, timeout_ms: int = 6000) -> dict[str, Any]:
    """Write into a field BY REF. Privacy parity with page_type: the value never travels back - only
    whether the helper verified the readback."""
    ref = str(ref or "").strip()
    if not ref.startswith("@"):
        raise AxError("INVALID_ARGS", "ref must be a @snapshot:element ref from ax_snapshot / ax_find")
    if not text:
        raise AxError("INVALID_ARGS", "text khali hai")
    d = _run(["set-value", ref, str(text)[:4000], "--timeout-ms", str(max(2000, min(int(timeout_ms or 6000), 15000)))],
             timeout=min(MAX_WAIT_S, timeout_ms / 1000 + 8))
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
