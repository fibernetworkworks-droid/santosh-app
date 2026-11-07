"""v0.664 ASLI SAMAY: the website is built in front of her.

Every section Opus writes is streamed (same prompt, same model, same tokens) and the half-written HTML / CSS is pulled
out of the arriving JSON into a small live buffer per section ("slot"). The Web Studio reads the slots over one live
connection and grows each section inside the real page as the words arrive. Nothing here is saved: the finished
section is checked and stored exactly as before, then `finish` hands the checked HTML to the screen.

Slots live in memory (one server process; a restart only loses what was on screen). Each change bumps the site's
sequence number, so a reader asks "what changed since N" and waits on a condition instead of polling.
"""
from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from typing import Any

_COND = threading.Condition()
_SITES: dict[str, dict[str, Any]] = {}
_TL = threading.local()
FEED_EVERY_S = 0.2        # at most ~5 screen updates a second per section (the model sends far more pieces)
KEEP_S = 3600             # a site's slots are forgotten an hour after the last change
MAX_SLOTS = 400


def _site(site_id: str) -> dict[str, Any]:
    st = _SITES.get(site_id)
    if st is None:
        st = _SITES[site_id] = {"seq": 0, "slots": {}, "looks": [], "touched": time.time(), "done": 0}
    return st


def _bump(st: dict[str, Any], slot: dict[str, Any] | None = None) -> None:
    st["seq"] += 1
    st["touched"] = time.time()
    if slot is not None:
        slot["v"] = st["seq"]
    _COND.notify_all()


def _sweep() -> None:
    now = time.time()
    for k in [k for k, v in _SITES.items() if now - v["touched"] > KEEP_S]:
        _SITES.pop(k, None)


# ---------------------------------------------------------------- the half-written JSON
def _json_string_from(text: str, i: int) -> tuple[str, bool]:
    """Decode a JSON string that starts at text[i] (just after its opening quote) as far as it has arrived.
    Returns (value so far, closed)."""
    out: list[str] = []
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            return "".join(out), True
        if c == "\\":
            if i + 1 >= n:
                break
            e = text[i + 1]
            if e == "u":
                if i + 6 > n:
                    break
                try:
                    out.append(chr(int(text[i + 2:i + 6], 16)))
                except ValueError:
                    pass
                i += 6
                continue
            out.append({"n": "\n", "t": "\t", "r": "", "b": "", "f": "", '"': '"', "\\": "\\", "/": "/"}.get(e, e))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out), False


def partial(text: str, field: str) -> str:
    """The value of "field" in a JSON object that is still arriving ("" until its key has arrived)."""
    import re
    m = re.search(r'"' + re.escape(field) + r'"\s*:\s*"', text or "")
    if not m:
        return ""
    return _json_string_from(text, m.end())[0]


# ---------------------------------------------------------------- the writer's side (build threads)
@contextmanager
def watch(site_id: str, key: str, label: str, page: str = "home", look: int = -1, kind: str = "build"):
    """Around one Opus call that writes a section: the model's words go to this slot while it writes."""
    begin(site_id, key, label, page, look, kind)
    prev = getattr(_TL, "cur", None)
    _TL.cur = (site_id, key)
    _TL.last = 0.0
    try:
        yield
    except BaseException:
        finish(site_id, key, ok=False)
        raise
    finally:
        _TL.cur = prev


def current() -> tuple[str, str] | None:
    return getattr(_TL, "cur", None)


def begin(site_id: str, key: str, label: str, page: str = "home", look: int = -1, kind: str = "build") -> None:
    with _COND:
        _sweep()
        st = _site(site_id)
        if len(st["slots"]) >= MAX_SLOTS and key not in st["slots"]:
            old = min(st["slots"].values(), key=lambda s: s.get("v", 0))
            st["slots"].pop(old["key"], None)
        slot = {"key": key, "label": label[:120], "page": page, "look": look, "kind": kind, "state": "think",
                "html": "", "css": "", "at": time.time(), "end": None, "chars": 0}
        st["slots"][key] = slot
        _bump(st, slot)


def reset() -> None:
    """A retry of the same call: what the failed try wrote goes away."""
    cur = current()
    if not cur:
        return
    with _COND:
        slot = _SITES.get(cur[0], {}).get("slots", {}).get(cur[1])
        if slot and slot["state"] in ("think", "write"):
            slot.update(html="", css="", state="think", chars=0)
            _bump(_SITES[cur[0]], slot)


def feed(text: str, force: bool = False) -> None:
    """The model's answer so far (the whole text, not a piece). Throttled; the last piece always goes out (force)."""
    cur = current()
    if not cur:
        return
    now = time.time()
    if not force and now - getattr(_TL, "last", 0.0) < FEED_EVERY_S:
        return
    _TL.last = now
    html, css = partial(text, "html"), partial(text, "css")
    with _COND:
        slot = _SITES.get(cur[0], {}).get("slots", {}).get(cur[1])
        if not slot or slot["state"] not in ("think", "write"):
            return
        if html == slot["html"] and css == slot["css"]:
            return
        slot.update(html=html, css=css, state="write" if html else "think", chars=len(text))
        _bump(_SITES[cur[0]], slot)


def finish(site_id: str, key: str, ok: bool = True, html: str | None = None, css: str | None = None) -> None:
    """The section is written and checked (ok) or failed: the screen gets the checked HTML, never the raw draft."""
    with _COND:
        st = _SITES.get(site_id)
        slot = st and st["slots"].get(key)
        if not slot:
            return
        if html is not None:
            slot["html"] = html
        if css is not None:
            slot["css"] = css
        slot.update(state="done" if ok else "error", end=time.time())
        if ok:
            st["done"] += 1
        _bump(st, slot)


def set_looks(site_id: str, looks: list[dict[str, Any]]) -> None:
    """The three looks being written now (label, tokens, which home sections): their canvases are drawn from this."""
    with _COND:
        st = _site(site_id)
        st["looks"] = looks
        _bump(st)


def looks(site_id: str) -> list[dict[str, Any]]:
    with _COND:
        return list(_SITES.get(site_id, {}).get("looks") or [])


def done_count(site_id: str) -> int:
    with _COND:
        return int(_SITES.get(site_id, {}).get("done", 0))


def clear(site_id: str) -> None:
    with _COND:
        st = _SITES.get(site_id)
        if st:
            st["slots"].clear()
            st["looks"] = []
            _bump(st)


# ---------------------------------------------------------------- the reader's side (the Studio)
def snapshot(site_id: str, since: int = 0) -> dict[str, Any]:
    with _COND:
        st = _SITES.get(site_id)
        if not st:
            return {"seq": 0, "slots": [], "looks": []}
        slots = [dict(s) for s in st["slots"].values() if s.get("v", 0) > since]
        return {"seq": st["seq"], "slots": sorted(slots, key=lambda s: s["at"]),
                "looks": [{"label": x.get("label", ""), "style": x.get("style", "")} for x in st["looks"]]}


def wait(site_id: str, since: int, timeout: float = 15.0) -> dict[str, Any]:
    end = time.time() + timeout
    with _COND:
        while _SITES.get(site_id, {}).get("seq", 0) <= since:
            left = end - time.time()
            if left <= 0:
                break
            _COND.wait(left)
    return snapshot(site_id, since)


def dumps(ev: dict[str, Any]) -> str:
    return json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
