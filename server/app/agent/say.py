"""v0.187 chhote sach, turant: between the steps of a turn the phone shows one short human line about what the
last tool REALLY returned ("12 naye mails aaye", "video taiyar — drive.google.com"). Rule-based from the tool
result itself: no model call (a model call here would be exactly the delay we are killing), never a guess —
when no true fact can be read out of the result, there is no line. Numbers and hosts only; the args-brief
masking rules stay in charge of anything sensitive, and no line is ever longer than one breath."""
from __future__ import annotations

import re

_DONE_WORDS = {"done", "ok", "true", "success", "saved", "sent", "created", "updated", "ready", "completed", "completed"}
_URL_KEYS = ("url", "link", "preview_url", "file_url", "share_url", "download_url")
_URL_RE = re.compile(r"^https?://")
_LIST_KEYS = ("items", "results", "mails", "threads", "messages", "files", "rows", "orders", "videos", "shots", "tasks")
_COUNT_KEYS = ("count", "total", "found", "n")


def _host(u: str) -> str:
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1) if m else ""


def _fmt_n(n: int) -> str:
    return str(n)


def line_for(label: str, tool: str, out: object) -> str:
    """One true Hinglish line about `out` (the tool's result), or '' when nothing true can be said."""
    label = " ".join(str(label or "").split())
    tool = str(tool or "").lower()
    if isinstance(out, dict):
        if out.get("error"):
            return ""                      # errors are the step chip's job; the line never repeats them
        n = 0
        for k in _COUNT_KEYS:
            v = out.get(k)
            if isinstance(v, (int, float)) and v >= 0:
                n = int(v)
                break
        if not n:
            for k in _LIST_KEYS:
                v = out.get(k)
                if isinstance(v, list):
                    n = len(v)
                    break
        for k in _URL_KEYS:
            v = out.get(k)
            if isinstance(v, str) and _URL_RE.match(v):
                u = v.split("?")[0].rstrip("/")
                h = _host(u)
                if n:
                    return f"{label}: {_fmt_n(n)} mile — {h}" if h else f"{label}: {_fmt_n(n)} mile"
                return f"{label} taiyar — {h}" if h else ""
        if n:
            if "mail" in tool or "mail" in label.lower():
                return f"{_fmt_n(n)} mails mile"
            if "search" in tool or "web" in tool:
                return f"{_fmt_n(n)} results mile"
            if "thread" in tool:
                return f"{_fmt_n(n)} threads mile"
            if "file" in tool or "photo" in tool or "attachment" in tool:
                return f"{_fmt_n(n)} files mili"
            return f"{label}: {_fmt_n(n)}"
        st = str(out.get("status") or out.get("state") or "").lower().strip()
        if st in _DONE_WORDS or out.get("ok") is True:
            return f"{label} ho gaya"
        return ""
    if isinstance(out, str):
        s = out.strip()
        if _URL_RE.match(s):
            h = _host(s.split("?")[0])
            return f"{label} taiyar — {h}" if h else ""
    return ""
