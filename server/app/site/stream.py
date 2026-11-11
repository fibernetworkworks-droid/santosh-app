"""v0.664 ASLI SAMAY: the website is built in front of her.

Every section Opus writes is streamed (same prompt, same model, same tokens) and the half-written HTML / CSS is pulled
out of the arriving JSON into a small live buffer per section ("slot"). The Web Studio reads the slots over one live
connection and grows each section inside the real page as the words arrive. Nothing here is saved: the finished
section is checked and stored exactly as before, then `finish` hands the checked HTML to the screen.

Slots live in memory AND (v0.808 E7) in a small file per site under <SITE_DIR>/_live/ (written at most once a second
while words stream, at once when a section finishes / the looks change / the slots clear): a restart or a second worker
reads the file back, so the live view she was watching is still there (the build itself resumes as before). Each
change bumps the site's sequence number, so a reader asks "what changed since N" and waits on a condition instead of
polling.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.site.stream")

_COND = threading.Condition()
_SITES: dict[str, dict[str, Any]] = {}
_TL = threading.local()
FEED_EVERY_S = 0.2        # at most ~5 screen updates a second per section (the model sends far more pieces)
KEEP_S = 3600             # a site's slots are forgotten an hour after the last change
MAX_SLOTS = 400
SAVE_EVERY_S = 1.0        # v0.808 E7: the on-disk copy while words stream (finish / looks / clear write at once)


def _file(site_id: str) -> Path:
    d = Path(os.environ.get("SITE_DIR", "data/sites")) / "_live"
    d.mkdir(parents=True, exist_ok=True)
    return d / (re.sub(r"[^\w-]", "_", site_id)[:80] + ".json")


def _persist(st: dict[str, Any], force: bool = False) -> None:
    now = time.time()
    if not force and now - st.get("_saved", 0.0) < SAVE_EVERY_S:
        return
    st["_saved"] = now
    try:
        f = _file(st["id"])
        tmp = f.with_name(f"{f.name}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps({k: st[k] for k in ("seq", "slots", "looks", "touched", "done")}, ensure_ascii=False))
        tmp.replace(f)
    except Exception:                         # the live view on disk is a convenience; never break a build for it
        log.debug("live slots not saved", exc_info=True)


def _load(site_id: str) -> dict[str, Any] | None:
    """After a restart (or in another worker): the slots she was watching, read back from disk."""
    try:
        f = _file(site_id)
        if not f.exists():
            return None
        d = json.loads(f.read_text())
    except Exception:
        return None
    if time.time() - float(d.get("touched") or 0) > KEEP_S:
        return None
    st = {"id": site_id, "seq": int(d.get("seq") or 0), "slots": d.get("slots") or {}, "looks": d.get("looks") or [],
          "touched": float(d.get("touched") or time.time()), "done": int(d.get("done") or 0), "restored": True,
          "_saved": time.time()}
    for sl in st["slots"].values():           # a section that was being written when the server stopped
        if sl.get("state") in ("think", "write"):
            sl["stale"] = True
    _SITES[site_id] = st
    return st


def _get(site_id: str) -> dict[str, Any] | None:
    return _SITES.get(site_id) or _load(site_id)


def _site(site_id: str) -> dict[str, Any]:
    st = _get(site_id)
    if st is None:
        st = _SITES[site_id] = {"id": site_id, "seq": 0, "slots": {}, "looks": [], "touched": time.time(), "done": 0}
    return st


def _bump(st: dict[str, Any], slot: dict[str, Any] | None = None, force: bool = False) -> None:
    st["seq"] += 1
    st["touched"] = time.time()
    if slot is not None:
        slot["v"] = st["seq"]
        slot.pop("stale", None)
    _persist(st, force or slot is None or (slot is not None and slot.get("state") in ("done", "error")))
    _COND.notify_all()


def _sweep() -> None:
    now = time.time()
    for k in [k for k, v in _SITES.items() if now - v["touched"] > KEEP_S]:
        _SITES.pop(k, None)
        try:
            _file(k).unlink()
        except OSError:
            pass


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
        slot = (_get(cur[0]) or {}).get("slots", {}).get(cur[1])
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
        st = _get(site_id)
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
        return list((_get(site_id) or {}).get("looks") or [])


def done_count(site_id: str) -> int:
    with _COND:
        return int((_get(site_id) or {}).get("done", 0))


def clear(site_id: str) -> None:
    with _COND:
        st = _get(site_id)
        if st:
            st["slots"].clear()
            st["looks"] = []
            _bump(st)


# ---------------------------------------------------------------- the reader's side (the Studio)
def snapshot(site_id: str, since: int = 0) -> dict[str, Any]:
    with _COND:
        st = _get(site_id)
        if not st:
            return {"seq": 0, "slots": [], "looks": []}
        slots = [dict(s) for s in st["slots"].values() if s.get("v", 0) > since]
        return {"seq": st["seq"], "slots": sorted(slots, key=lambda s: s["at"]),
                "looks": [{"label": x.get("label", ""), "style": x.get("style", "")} for x in st["looks"]]}


def wait(site_id: str, since: int, timeout: float = 15.0) -> dict[str, Any]:
    end = time.time() + timeout
    with _COND:
        while (_get(site_id) or {}).get("seq", 0) <= since:
            left = end - time.time()
            if left <= 0:
                break
            _COND.wait(left)
    return snapshot(site_id, since)


def dumps(ev: dict[str, Any]) -> str:
    return json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
