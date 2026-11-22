"""v0.999.111 ULTIMATE PC PLAN P1 (rest) - page engine 2 on HER PC, through the Hoola extension in her Chrome.

On her Windows PC the page tools used to read Chrome through Windows' accessibility tree (UIA): no page components
(shadow DOM), no same-page frames, a click that never moved the mouse, no hover, no drag, no date boxes. The Hoola
extension (desktop/ext/hoola-extension, already paired with her 6-digit code) now opens its own socket here and runs the
SAME engine as Hoola PC (pagekit.js is generated from desktop-linux/pagekit.py) in the tab she has in front:

    extension  --wss /api/pc/ext-ws (first message: its paired spc_ token)-->  this module
    operator._pc(page_*) on her PC  ->  extlink.handle()  ->  {"op": "js" | "mouse" | "tab"}  ->  the extension

The refs, the checks and the decisions stay HERE (like agent.py on Hoola PC); the extension only runs one function of
pagekit.js in the page (its own isolated world - the page's scripts cannot touch it) or moves the real mouse through
chrome.debugger (Chrome shows its 'started debugging this browser' bar while it does). A password box is refused, what
is typed never comes back, the page's text is data. No extension = the old accessibility path, as before."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from . import pagekit as PK

log = logging.getLogger("santosh.pc.extlink")

CALL_TIMEOUT = 25.0
ACTIONS = ("page_elements", "page_click", "page_type", "page_select", "page_fill_form", "page_text", "page_hover",
           "page_drag")
PW_REFUSED = ("PASSWORD box: Hoola never types a password itself (not even one written on the page). Call ask_login - "
              "she types it into a private form and the system enters it - or finish with done(success=false) saying the "
              "sign-in is hers.")


class ExtError(RuntimeError):
    pass


@dataclass
class Link:
    tenant: str
    device_id: str
    send: Any                                   # async fn(dict)
    since: float = field(default_factory=time.time)
    last: float = field(default_factory=time.time)
    pending: dict = field(default_factory=dict)
    browser: str = ""
    refs: dict = field(default_factory=dict)    # ref -> {path, role, name, ty, drag}


LINKS: dict[str, Link] = {}                     # tenant -> the newest live extension of hers


def ready(tenant: str) -> bool:
    lk = LINKS.get(tenant)
    return bool(lk) and time.time() - lk.last < 75


def status(tenant: str) -> dict[str, Any]:
    lk = LINKS.get(tenant)
    return {"connected": ready(tenant), "device_id": lk.device_id if lk else "", "browser": lk.browser if lk else ""}


def _day_first(tenant: str) -> bool:
    try:
        from ..life import get_profile
        tz = str(get_profile(tenant).timezone or "")
    except Exception:   # noqa: BLE001
        tz = ""
    month_first = ("America/", "Asia/Manila", "Africa/Johannesburg", "Asia/Tokyo")
    day_first_americas = ("America/Toronto", "America/Vancouver", "America/Sao_Paulo", "America/Mexico_City",
                          "America/Argentina", "America/Bogota", "America/Lima", "America/Santiago")
    if tz.startswith(day_first_americas):
        return True
    return not tz.startswith(month_first)


# ---------------------------------------------------------------- the socket
async def call(tenant: str, msg: dict, timeout: float = CALL_TIMEOUT) -> Any:
    lk = LINKS.get(tenant)
    if lk is None or not ready(tenant):
        raise ExtError("the Hoola extension in her browser is not connected")
    rid = secrets.token_hex(6)
    fut = asyncio.get_running_loop().create_future()
    lk.pending[rid] = fut
    try:
        await lk.send({"id": rid, **msg})
        got = await asyncio.wait_for(fut, timeout)
    except asyncio.TimeoutError as e:
        raise ExtError(f"her browser did not answer in {int(timeout)} s") from e
    finally:
        lk.pending.pop(rid, None)
    if not got.get("ok"):
        raise ExtError(str(got.get("error") or "the browser refused")[:300])
    return got.get("result")


def receive(tenant: str, msg: dict) -> None:
    lk = LINKS.get(tenant)
    if lk is None:
        return
    lk.last = time.time()
    fut = lk.pending.get(str(msg.get("id") or ""))
    if fut is not None and not fut.done():
        fut.set_result(msg)


async def _js(tenant: str, fn: str, args: dict | None = None, timeout: float = CALL_TIMEOUT) -> Any:
    return await call(tenant, {"op": "js", "fn": fn, "args": args or {}}, timeout)


async def _mouse(tenant: str, events: list[dict]) -> None:
    await call(tenant, {"op": "mouse", "events": events})


# ---------------------------------------------------------------- the engine (the same decisions as agent.py)
async def _snap(tenant: str) -> dict | None:
    try:
        return await _js(tenant, "snap", timeout=15)
    except ExtError:
        return None


async def _changed(tenant: str, before: dict | None, wait: float = 0.6) -> str:
    await asyncio.sleep(wait)
    return PK.diff_line(PK.diff(before, await _snap(tenant)))


def _ref(lk: Link, ref: Any) -> dict:
    try:
        it = lk.refs.get(int(ref or 0))
    except (TypeError, ValueError):
        it = None
    if not it:
        raise ExtError(f"ref {ref} is gone - run page_elements again first (the page changed)")
    return it


async def _on(tenant: str, lk: Link, it: dict, fn: str, extra: dict | None = None) -> dict:
    r = await _js(tenant, fn, {"path": it["path"], "role": it["role"], "name": it["name"], **(extra or {})}) or {}
    if r.get("newpath"):
        it["path"] = r["newpath"]
    return r


async def _aim(tenant: str, lk: Link, ref: Any) -> tuple[dict, dict]:
    it = _ref(lk, ref)
    p = await _on(tenant, lk, it, "point")
    if not p.get("ok"):
        raise ExtError(f"ref {ref} is gone from the page ({it.get('role')} '{str(it.get('name', ''))[:40]}') - run "
                       "page_elements again")
    return it, p


def _press(x: int, y: int, press: bool = True) -> list[dict]:
    ev = [{"type": "mouseMoved", "x": x, "y": y, "button": "none"}]
    if press:
        ev += [{"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
               {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1}]
    return ev


async def _type(tenant: str, lk: Link, it: dict, text: str, clear: bool = True) -> dict:
    txt = str(text or "")[:4000]
    ty = it.get("ty") or ""
    iso = PK.field_value(txt, ty, _day_first(tenant)) if ty in PK.DATE_TYPES else ""
    if ty in PK.DATE_TYPES and not iso:
        return {"ok": False, "err": f"'{txt[:30]}' is not a date / time this {ty} box can take"}
    if ty == "password":
        return {"ok": False, "err": "password"}
    return await _on(tenant, lk, it, "type", {"txt": txt, "clr": bool(clear), "iso": iso})


async def handle(tenant: str, action: str, a: dict | None) -> dict[str, Any]:
    """One page action on her PC through the extension; the same answers the Hoola PC agent gives."""
    a = dict(a or {})
    lk = LINKS.get(tenant)
    if lk is None:
        raise ExtError("the Hoola extension in her browser is not connected")
    if action == "page_elements":
        r = await _js(tenant, "elements") or {}
        els = list(r.get("elements") or [])[:max(1, min(int(a.get("max_items") or 60), 200))]
        lk.refs, out = {}, []
        for i, e in enumerate(els, 1):
            lk.refs[i] = {"path": e.get("path") or [], "role": e.get("role") or "", "name": e.get("name") or "",
                          "ty": e.get("ty") or "", "drag": bool(e.get("drag"))}
            item = {"ref": i, "role": e.get("role"), "name": e.get("name")}
            for k_in, k_out in (("ph", "placeholder"), ("ty", "type"), ("where", "where")):
                if e.get(k_in):
                    item[k_out] = e[k_in]
            if e.get("disabled"):
                item["disabled"] = True
            if e.get("drag"):
                item["draggable"] = True
            out.append(item)
        return {"title": r.get("title", ""), "url": r.get("url", ""), "count": len(out), "elements": out,
                "blocked_frames": r.get("blocked_frames", 0), "engine": "extension"}
    if action == "page_text":
        n = max(500, min(int(a.get("max_chars") or 6000), 20000))
        tab = await call(tenant, {"op": "tab"}) or {}
        text = await _js(tenant, "text", timeout=20) or ""
        return {"title": tab.get("title", ""), "url": tab.get("url", ""), "text": str(text)[:n]}
    if action == "page_click":
        before = await _snap(tenant)
        it, p = await _aim(tenant, lk, a.get("ref"))
        if p.get("disabled"):
            raise ExtError(f"element {a.get('ref')} is disabled (greyed out) - something else must be done first")
        if p.get("covered"):
            return {"clicked": False, "covered_by": p.get("cover") or "something", "moved": bool(p.get("moved"))}
        if p.get("x") is None:
            await _on(tenant, lk, it, "click")
        else:
            await _mouse(tenant, _press(int(p["x"]), int(p["y"])))
        tab = await call(tenant, {"op": "tab"}) or {}
        return {"clicked": True, "title": tab.get("title", ""), "url": tab.get("url", ""), "moved": bool(p.get("moved")),
                "navigated": bool(before) and before.get("url") != tab.get("url"),
                "change": await _changed(tenant, before)}
    if action == "page_hover":
        before = await _snap(tenant)
        _it, p = await _aim(tenant, lk, a.get("ref"))
        if p.get("x") is None:
            raise ExtError(f"element {a.get('ref')} has no size on screen - it cannot be pointed at")
        await _mouse(tenant, _press(int(p["x"]), int(p["y"]), press=False))
        return {"hovered": True, "covered_by": p.get("cover") if p.get("covered") else "",
                "change": await _changed(tenant, before)}
    if action == "page_drag":
        before = await _snap(tenant)
        src, dst = _ref(lk, a.get("ref")), _ref(lk, a.get("to_ref"))
        if src.get("drag"):
            r = await _js(tenant, "drag", {"src": src, "dst": dst}) or {}
            if not r.get("ok"):
                raise ExtError(f"drag failed ({r.get('err', '?')}) - run page_elements again")
            how = "drag events"
        else:
            _a, p1 = await _aim(tenant, lk, a.get("ref"))
            _b, p2 = await _aim(tenant, lk, a.get("to_ref"))
            if p1.get("x") is None or p2.get("x") is None:
                raise ExtError("one of the two elements has no size on screen")
            x1, y1, x2, y2 = int(p1["x"]), int(p1["y"]), int(p2["x"]), int(p2["y"])
            ev = [{"type": "mouseMoved", "x": x1, "y": y1, "button": "none"},
                  {"type": "mousePressed", "x": x1, "y": y1, "button": "left", "clickCount": 1}]
            ev += [{"type": "mouseMoved", "x": x1 + (x2 - x1) * i // 8, "y": y1 + (y2 - y1) * i // 8,
                    "button": "left", "buttons": 1} for i in range(1, 9)]
            ev.append({"type": "mouseReleased", "x": x2, "y": y2, "button": "left", "clickCount": 1})
            await _mouse(tenant, ev)
            how = "mouse"
        return {"dragged": True, "how": how, "change": await _changed(tenant, before),
                "note": "refs may have changed - run page_elements again before the next step"}
    if action == "page_type":
        before = await _snap(tenant)
        r = await _type(tenant, lk, _ref(lk, a.get("ref")), a.get("text", ""), bool(a.get("clear", True)))
        if r.get("err") == "password":
            raise ExtError(PW_REFUSED)
        if not r.get("ok"):
            raise ExtError(f"type failed ({r.get('err', '?')}) - run page_elements again")
        return {"typed": True, "length": r.get("length"), "matches": r.get("matches"), "as_date": bool(r.get("as_date")),
                "change": await _changed(tenant, before, 0.3)}
    if action == "page_select":
        before = await _snap(tenant)
        r = await _on(tenant, lk, _ref(lk, a.get("ref")), "select", {"val": str(a.get("value") or "")})
        if not r.get("ok"):
            raise ExtError(f"select failed ({r.get('err', '?')})"
                           + (f" - options: {', '.join((r.get('options') or [])[:12])}" if r.get("options") else ""))
        return {"selected": r.get("picked"), "change": await _changed(tenant, before, 0.3)}
    if action == "page_fill_form":
        items = a.get("entries")
        if not isinstance(items, list) or not items:
            raise ExtError("entries needed: [{'ref': 2, 'text': '...'}, ...]")
        before = await _snap(tenant)
        out = []
        for e in items[:20]:
            try:
                ref = int(e.get("ref") or 0)
                it = _ref(lk, ref)
                r = await _type(tenant, lk, it, str(e.get("text") or ""))
            except (ExtError, TypeError, ValueError, AttributeError) as ex:
                out.append({"ref": e.get("ref") if isinstance(e, dict) else None, "ok": False, "err": str(ex)[:120]})
                continue
            if r.get("err") == "password":
                r["err"] = PW_REFUSED
            out.append({"ref": ref, "ok": bool(r.get("ok")), "length": r.get("length"), "matches": r.get("matches"),
                        **({"err": r["err"]} if r.get("err") else {})})
        return {"filled": sum(1 for x in out if x.get("ok")), "total": len(out), "results": out,
                "change": await _changed(tenant, before, 0.3)}
    raise ExtError(f"Unknown action: {action}")


# ---------------------------------------------------------------- the route
def mount(app) -> None:
    @app.websocket("/api/pc/ext-ws")
    async def ext_ws(ws: WebSocket):
        await ws.accept()
        try:
            hello = json.loads(await asyncio.wait_for(ws.receive_text(), 15))
        except Exception:   # noqa: BLE001
            await ws.close(code=4401)
            return
        from . import service as pcs
        dev = pcs.device_for_token(str(hello.get("token") or ""))
        if dev is None:
            await ws.send_text(json.dumps({"type": "refused", "why": "not paired (or removed) - pair it again"}))
            await ws.close(code=4401)
            return

        async def send(msg: dict) -> None:
            await ws.send_text(json.dumps(msg))
        lk = Link(tenant=dev.tenant_id, device_id=dev.id, send=send, browser=str(hello.get("browser") or "")[:60])
        old = LINKS.get(dev.tenant_id)
        LINKS[dev.tenant_id] = lk
        if old is not None:
            for f in old.pending.values():
                if not f.done():
                    f.set_exception(ExtError("her browser connected again"))
        log.info("pc ext link %s tenant %s (%s)", dev.id, dev.tenant_id, lk.browser or "browser")
        await ws.send_text(json.dumps({"type": "ready", "version": 1}))
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if msg.get("type") == "ping":
                    lk.last = time.time()
                    await ws.send_text(json.dumps({"type": "pong"}))
                    continue
                receive(dev.tenant_id, msg)
        except WebSocketDisconnect:
            pass
        except Exception:   # noqa: BLE001
            log.debug("ext link dropped", exc_info=True)
        finally:
            if LINKS.get(dev.tenant_id) is lk:
                LINKS.pop(dev.tenant_id, None)
            for f in lk.pending.values():
                if not f.done():
                    f.set_exception(ExtError("her browser went away"))
