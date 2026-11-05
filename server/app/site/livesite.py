"""v0.459 ABHI ABHI WEBSITE (web Step 5, W6 live features; plan checkpoint "Clinic live queue + SMS reminders").

A website linked to its App Sahayak brain (v0.407 EK DIMAAG) gets the same real time the native apps have had since v0.409:
  * LIVE CHANNEL: /api/site-app/<site>/live = appmaker/live.py's SSE stream on the linked project, so every write from any
    path (the site, her console, the logic engine, a connector's answer, another server process) reaches the open pages,
    each event filtered by that list's own read rule (a customer hears only her own rows). The page script reads it with
    fetch() + the Authorization header (EventSource cannot send one) and re-draws only what changed: live order / ticket
    status, staff dashboards that update themselves, presence ("2 staff online") and typing in chat.
  * LIVE CHAT visitor <-> her team = appmaker/baat.py on the website: one thread per signed-in member, staff threads +
    unread at /admin/, her own replies only by her tap in the console (the agent never answers a customer on its own).
  * CLINIC QUEUE: today's tokens on a list of their own (`_queue`): a patient takes a token on the site (if she allows it) or
    reception adds a walk-in; staff press "Call next". A public board (TV in the waiting room / the site) shows ONLY the
    numbers - now serving, who is next, how many wait, the measured minutes per patient - never a name or a phone. A
    patient's own page shows her token, how many are ahead and the estimated wait. When a token comes within N of the front,
    ONE "your turn is near" goes out: her approved SMS / WhatsApp connector (trigger `queue`) and the patient's browser
    notification if she said yes. Numbers are given under the app's cross-process lock, so two receptionists never hand out
    the same token.
  * The public board stream needs no login (it carries no personal data), is capped per process and per address, and
    re-reads the queue at most once a second per site however many screens watch it."""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator

from sqlalchemy import select

from ..db import now, session
from . import webapp as W

IST = timezone(timedelta(hours=5, minutes=30))
QCOLL = "_queue"
DEFAULT = {"on": False, "label": "Queue", "self_take": True, "avg_min": 8, "near": 3, "open": True, "max_day": 300}
STATUSES = ("waiting", "called", "done", "skipped")
STATS = {"tokens": 0, "calls": 0, "near": 0, "boards": 0, "board_refused": 0}
BOARD_MAX = 3000
BOARD_PER_IP = 6
_BOARDS: dict[str, int] = {}
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


class QueueError(W.AppError):
    pass


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _bid(p) -> str:
    from ..appmaker import backend as BE
    return BE.bid(p)


def today() -> str:
    return now().astimezone(IST).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- settings (her switch)
def cfg(p) -> dict[str, Any]:
    from ..appmaker import backend as BE
    return {**DEFAULT, **(dict(BE.ensure(p).get("queue") or {}))}


def save_cfg(p, body: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import backend as BE
    q = cfg(p)
    for k in ("on", "self_take", "open"):
        if k in body:
            q[k] = bool(body.get(k))
    if "label" in body:
        q["label"] = re.sub(r"[\x00-\x1f<>]", "", str(body.get("label") or "Queue")).strip()[:40] or "Queue"
    for k, lo, hi in (("avg_min", 1, 120), ("near", 1, 20), ("max_day", 10, 2000)):
        if k in body:
            try:
                q[k] = max(lo, min(hi, int(body.get(k))))
            except (TypeError, ValueError):
                raise QueueError(f"{k}: ank likhiye.", 400)
    BE.patch_backend(p, set_={"queue": q})
    _CACHE.pop(_bid(p), None)
    return q


# ---------------------------------------------------------------- today's tokens
def _rows(p, day: str = "") -> list[tuple[Any, dict[str, Any]]]:
    day = day or today()
    with session() as s:
        xs = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == _bid(p), W.SiteAppRow.coll == QCOLL,
                                                  W.SiteAppRow.created_at >= now() - timedelta(hours=40))).all()
        for x in xs:
            s.expunge(x)
    out = [(x, _j(x.data, {})) for x in xs]
    out = [(x, d) for x, d in out if d.get("day") == day]
    out.sort(key=lambda t: int(t[1].get("token") or 0))
    return out


def _waiting(rows):
    return [(x, d) for x, d in rows if d.get("status") == "waiting"]


def _now_serving(rows) -> dict[str, Any] | None:
    called = [d for _, d in rows if d.get("status") == "called"]
    if not called:
        return None
    return max(called, key=lambda d: str(d.get("called_at") or ""))


def _measured(rows, q) -> int:
    """Minutes per patient from today's own calls (median gap of the last 10), else her setting."""
    ts = sorted(str(d.get("called_at")) for _, d in rows if d.get("called_at"))[-11:]
    gaps = []
    for a, b in zip(ts, ts[1:]):
        try:
            g = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60
        except ValueError:
            continue
        if 0.2 <= g <= 180:
            gaps.append(g)
    if len(gaps) >= 3:
        gaps.sort()
        return max(1, round(gaps[len(gaps) // 2]))
    return int(q.get("avg_min") or 8)


def board(p) -> dict[str, Any]:
    """The public view: numbers only - never a name, never a phone."""
    q = cfg(p)
    if not q.get("on"):
        return {"on": False, "label": q["label"]}
    rows = _rows(p)
    wt = _waiting(rows)
    cur = _now_serving(rows)
    return {"on": True, "open": bool(q.get("open")), "label": q["label"], "day": today(),
            "now": int(cur["token"]) if cur else None, "next": [int(d["token"]) for _, d in wt[:8]], "waiting": len(wt),
            "min_each": _measured(rows, q), "self_take": bool(q.get("self_take")), "done": sum(1 for _, d in rows if d.get("status") == "done")}


def board_cached(p) -> dict[str, Any]:
    site = _bid(p)
    hit = _CACHE.get(site)
    if hit and time.monotonic() - hit[0] < 1.0:
        return hit[1]
    b = board(p)
    _CACHE[site] = (time.monotonic(), b)
    return b


def _mine_view(p, rows, d: dict[str, Any] | None) -> dict[str, Any]:
    if d is None:
        return {"token": None}
    q = cfg(p)
    wt = [int(x[1]["token"]) for x in _waiting(rows)]
    ahead = wt.index(int(d["token"])) if d.get("status") == "waiting" and int(d["token"]) in wt else 0
    cur = _now_serving(rows)
    return {"token": int(d["token"]), "status": d.get("status"), "ahead": ahead, "est_min": ahead * _measured(rows, q),
            "now": int(cur["token"]) if cur else None, "label": q["label"]}


def mine(p, w: W.Who) -> dict[str, Any]:
    if w.m is None:
        raise QueueError("Pehle login kijiye.", 401)
    rows = _rows(p)
    d = next((d for x, d in reversed(rows) if x.owner == w.m.id and d.get("status") in ("waiting", "called")), None) \
        or next((d for x, d in reversed(rows) if x.owner == w.m.id), None)
    return _mine_view(p, rows, d)


def _phone(v: Any) -> str:
    digits = re.sub(r"\D", "", str(v or ""))[-10:]
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else ""


def _insert(p, owner: str, name: str, phone: str, by: str) -> dict[str, Any]:
    from ..appmaker import locks as LK
    q = cfg(p)
    if not q.get("on"):
        raise QueueError("Queue abhi band hai.", 409)
    day = today()
    with LK.app(p.id):                                       # one number, one person - across every server process
        rows = _rows(p, day)
        if owner and any(x.owner == owner and d.get("status") in ("waiting", "called") for x, d in rows):
            return {"again": True}
        if len(rows) >= int(q.get("max_day") or 300):
            raise QueueError("Aaj ke token poore ho gaye.", 409)
        n = max([int(d.get("token") or 0) for _, d in rows] + [0]) + 1
        d = {"token": n, "name": name[:60], "phone": phone, "status": "waiting", "day": day, "by": by, "at": now().isoformat()}
        with session() as s:
            s.add(W.SiteAppRow(site_id=_bid(p), coll=QCOLL, owner=owner or "", data=json.dumps(d, ensure_ascii=False)))
    STATS["tokens"] += 1
    _CACHE.pop(_bid(p), None)
    near(p)
    return d


def take(p, w: W.Who, body: dict[str, Any]) -> dict[str, Any]:
    """A signed-in patient takes today's token herself (only when she - the owner - allowed it and the queue is open)."""
    if w.m is None:
        raise QueueError("Token lene ke liye pehle login kijiye.", 401)
    q = cfg(p)
    if not q.get("on"):
        raise QueueError("Queue abhi band hai.", 409)
    if not q.get("self_take"):
        raise QueueError("Token reception par milta hai.", 403)
    if not q.get("open"):
        raise QueueError("Aaj ki queue band ho gayi.", 409)
    W.rate(f"queue-take:{_bid(p)}:{w.m.id}", 5, 3600)
    name = (w.m.name or (w.m.email or "").split("@")[0] or "Patient").strip()
    _insert(p, w.m.id, name, _phone(body.get("phone")) or _phone(getattr(w.m, "phone", "")), "self")
    return mine(p, w)


def add(p, w: W.Who, body: dict[str, Any]) -> dict[str, Any]:
    """Reception (staff / her): a walk-in."""
    if not w.staff:
        raise QueueError("Sirf staff.", 403)
    name = re.sub(r"[\x00-\x1f<>]", "", str(body.get("name") or "")).strip()
    if not name:
        raise QueueError("Naam likhiye.", 400)
    raw = str(body.get("phone") or "").strip()
    ph = _phone(raw)
    if raw and not ph:
        raise QueueError("Mobile number 10 ank ka (6-9 se shuru).", 400)
    d = _insert(p, "", name, ph, "staff")
    return {**staff_view(p, w), "added": d.get("token")}


def call_next(p, w: W.Who, n: int | None = None) -> dict[str, Any]:
    """Staff: the patient now being seen is done; the next waiting token (or token n) is called."""
    if not w.staff:
        raise QueueError("Sirf staff.", 403)
    from ..appmaker import locks as LK
    with LK.app(p.id):
        rows = _rows(p)
        wt = _waiting(rows)
        target = next(((x, d) for x, d in wt if int(d["token"]) == int(n)), None) if n else (wt[0] if wt else None)
        if n and target is None:
            raise QueueError(f"Token {n} queue mein nahi (ya pehle bulaya ja chuka).", 404)
        t = now().isoformat()
        with session() as s:
            for x, d in rows:
                if d.get("status") == "called":
                    row = s.get(W.SiteAppRow, x.id)
                    dd = _j(row.data, {})
                    dd.update(status="done", done_at=t)
                    row.data = json.dumps(dd, ensure_ascii=False)
            if target is not None:
                row = s.get(W.SiteAppRow, target[0].id)
                dd = _j(row.data, {})
                dd.update(status="called", called_at=t, called_by=(w.m.id if w.m else "owner"))
                row.data = json.dumps(dd, ensure_ascii=False)
    STATS["calls"] += 1
    _CACHE.pop(_bid(p), None)
    if target is not None and target[0].owner:
        _push(p, [target[0].owner], f"{cfg(p)['label']}: token {target[1]['token']}", "Aapki baari aa gayi - andar aaiye.")
    near(p)
    return staff_view(p, w)


def mark(p, w: W.Who, n: int, status: str) -> dict[str, Any]:
    """Staff: a token done / skipped (did not come) / back to waiting."""
    if not w.staff:
        raise QueueError("Sirf staff.", 403)
    if status not in ("done", "skipped", "waiting"):
        raise QueueError("Status: done | skipped | waiting.", 400)
    hit = next(((x, d) for x, d in _rows(p) if int(d.get("token") or 0) == int(n)), None)
    if hit is None:
        raise QueueError("Token nahi mila.", 404)
    with session() as s:
        row = s.get(W.SiteAppRow, hit[0].id)
        dd = _j(row.data, {})
        dd["status"] = status
        if status == "waiting":
            dd.pop("called_at", None)
        row.data = json.dumps(dd, ensure_ascii=False)
    _CACHE.pop(_bid(p), None)
    near(p)
    return staff_view(p, w)


def staff_view(p, w: W.Who) -> dict[str, Any]:
    if not w.staff:
        raise QueueError("Sirf staff.", 403)
    rows = _rows(p)
    return {"settings": cfg(p), "board": board(p),
            "tokens": [{"token": int(d["token"]), "name": d.get("name", ""), "phone": d.get("phone", ""), "status": d.get("status"),
                        "by": d.get("by", ""), "near_sent": bool(d.get("near_sent")), "at": d.get("at", "")} for _, d in rows]}


def near(p) -> int:
    """The front N waiting tokens that were never told: ONE 'your turn is near' each (her SMS / WhatsApp connector with
    trigger 'queue' + the patient's browser notification if she said yes)."""
    q = cfg(p)
    if not q.get("on"):
        return 0
    rows = _rows(p)
    todo = [x for x, d in _waiting(rows)[: int(q.get("near") or 3)] if not d.get("near_sent")]
    if not todo:
        return 0
    with session() as s:
        for x in todo:
            row = s.get(W.SiteAppRow, x.id)
            dd = _j(row.data, {})
            dd["near_sent"] = True
            row.data = json.dumps(dd, ensure_ascii=False)
    from ..appmaker import connect as CN
    for x in todo:
        d = _j(x.data, {})
        if d.get("phone"):
            CN.fire(p, QCOLL, x.id, "queue")
        if x.owner:
            _push(p, [x.owner], f"{q['label']}: token {d.get('token')}", "Aapki baari paas hai - kripya taiyaar rahiye.")
        STATS["near"] += 1
    return len(todo)


def _push(p, members: list[str], title: str, body: str) -> None:
    from . import webpush as WP
    WP.later(_bid(p), members, title, body, "/", "queue")


# ---------------------------------------------------------------- the public board stream (TV / site), numbers only
def board_admit(ip: str) -> None:
    if sum(_BOARDS.values()) >= BOARD_MAX or _BOARDS.get(ip, 0) >= BOARD_PER_IP:
        STATS["board_refused"] += 1
        raise QueueError("Abhi bahut screens judi hain.", 429)


async def board_stream(p, ip: str, gone=None, seconds: float = 600, every: float = 1.0) -> AsyncIterator[str]:
    _BOARDS[ip] = _BOARDS.get(ip, 0) + 1
    STATS["boards"] += 1
    last, beat, t0 = "", time.monotonic(), time.monotonic()
    try:
        yield "retry: 3000\n\n"
        while time.monotonic() - t0 < seconds:
            if gone is not None and await gone():
                break
            b = await asyncio.to_thread(board_cached, p)
            txt = json.dumps(b, ensure_ascii=False, sort_keys=True)
            if txt != last:
                last, beat = txt, time.monotonic()
                yield f"event: board\ndata: {txt}\n\n"
            elif time.monotonic() - beat >= 15:
                beat = time.monotonic()
                yield ": ping\n\n"
            await asyncio.sleep(every)
        yield "event: bye\ndata: {}\n\n"
    finally:
        _BOARDS[ip] = max(0, _BOARDS.get(ip, 1) - 1)
        if not _BOARDS[ip]:
            _BOARDS.pop(ip, None)


BOARD_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>__LABEL__ - live queue</title><style>
:root{color-scheme:light dark;--bg:#fff;--ink:#14121a;--mut:#5d5a66;--line:#e6e4ea;--acc:#5b3fd6}
@media (prefers-color-scheme:dark){:root{--bg:#121117;--ink:#f3f2f6;--mut:#b4b1bd;--line:#2b2934;--acc:#a996ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;
min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 16px;text-align:center}
h1{font-size:clamp(20px,3vw,32px);font-weight:600;margin:0 0 8px}.lab{color:var(--mut);font-size:clamp(14px,2vw,20px)}
.now{font-size:clamp(96px,22vw,260px);font-weight:700;line-height:1;margin:8px 0 4px;color:var(--acc);font-variant-numeric:tabular-nums}
.next{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin:20px 0}.next span{border:1px solid var(--line);border-radius:12px;
padding:10px 18px;font-size:clamp(22px,4vw,40px);font-weight:600;font-variant-numeric:tabular-nums}.meta{color:var(--mut);font-size:clamp(14px,2vw,20px)}
.off{color:var(--mut)}@media (prefers-reduced-motion:no-preference){.now.flash{animation:f 1.2s ease-out}@keyframes f{0%{opacity:.2}100%{opacity:1}}}
</style></head><body><h1>__LABEL__</h1><div class="lab">Now serving · ab baari</div><div class="now" id="n" aria-live="assertive">-</div>
<div class="lab">Next · agla</div><div class="next" id="x"></div><div class="meta" id="m"></div><noscript>Turn on JavaScript for the live board.</noscript>
<script>(function(){var u=__URL__,n=document.getElementById('n'),x=document.getElementById('x'),m=document.getElementById('m'),last=null;
function draw(b){if(!b.on){n.textContent='-';x.innerHTML='';m.textContent='Queue is closed.';m.className='meta off';return}
var v=b.now==null?'-':String(b.now);if(v!==last){n.textContent=v;n.classList.remove('flash');void n.offsetWidth;n.classList.add('flash');last=v}
x.innerHTML='';(b.next||[]).forEach(function(t){var s=document.createElement('span');s.textContent=t;x.appendChild(s)});
m.className='meta';m.textContent=b.waiting+' waiting · about '+b.min_each+' min each'+(b.open?'':' · no new tokens today')}
function go(){var es=new EventSource(u);es.addEventListener('board',function(e){try{draw(JSON.parse(e.data))}catch(_){}});
es.addEventListener('bye',function(){es.close();setTimeout(go,500)});es.onerror=function(){es.close();setTimeout(go,4000)}}go()})();</script></body></html>"""


def board_page(site_id: str, label: str) -> str:
    safe = re.sub(r"[<>&\"']", "", label or "Queue")[:40] or "Queue"
    return BOARD_PAGE.replace("__LABEL__", safe).replace("__URL__", json.dumps(f"/api/site-app/{site_id}/queue/live"))


# ---------------------------------------------------------------- the website's live login check (old site logins too)
def still(site_id: str, p, token: str, member: str) -> bool:
    from . import applink as AL
    w = AL._who(site_id, p, token)
    return w.m is not None and w.m.id == member
