"""v0.407 ABHI ABHI (App Sahayak Pillar C, Phase 49): real time for every native app - live lists, live order status,
instant chat, presence ("rider online") and typing - instead of the 10-second / pull-to-refresh view.

How it works (one design for 1 or 4 server worker processes, SQLite or Postgres):
  * THE JOURNAL IS THE FEED. v0.390's journal already records EVERY write to an app's rows, from every path (the app, her
    Hoola, the logic engine, stock / coupons / khata, her own database's outside edits), in the SAME transaction as the
    write. So nothing new can be missed: one tailer thread per process reads the journal's new entries a few times a second
    (one query per process, however many phones are connected) and fans each entry out to the open streams of that app.
    A write made by ANOTHER worker process arrives the same way - no extra broker to run on her VPS.
  * EVERY EVENT IS FILTERED PER PERSON with the list's own read rule (`W._can_read`, the rule the list endpoint uses): a
    customer only ever hears about her own rows of an "own" list; staff hear everything; internal lists ("_audit"...) never.
    Chat messages reach only that thread's customer and staff.
  * NOTHING IS LOST ON A RECONNECT: each event carries the journal id (SSE `id:`). The phone reconnects with
    Last-Event-ID and the missed events are replayed from the journal; too many missed = one `reset` (the phone reloads its
    lists). The offline outbox on the phone stays the only source of truth for her writes - live is read-only.
  * JOURNAL IDS CAN COMMIT OUT OF ORDER on Postgres (id 12 committed before id 11): a gap is remembered and asked for again
    for a few seconds, so a late commit is still delivered.
  * PRESENCE + TYPING are short-lived signals in a small table (`app_live_signal`) that the same tailer reads, so they work
    across processes too. An open stream IS presence (refreshed every 20 s, expires 45 s after the phone goes). Customers see
    only whether staff are online (first name); staff see everyone. Typing is scoped to one chat thread.
  * LIMITS in code: a sign-in is needed (no anonymous streams), at most 3 streams per account, LIVE_MAX_PER_APP per app and
    LIVE_MAX_TOTAL per process (over = 429 and the phone keeps its normal refresh), a token signed out elsewhere ends the
    stream within a minute, each stream lives 10 minutes then reconnects (fresh auth check, no stuck sockets)."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, AsyncIterator

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now, session
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"streams": 0, "events": 0, "replayed": 0, "resets": 0, "refused": 0, "signals": 0, "late_commits": 0}

TICK = 0.35                 # seconds between journal reads while anything is connected
HEARTBEAT = 15              # a comment line so proxies keep the socket open
STREAM_SECONDS = 600        # then the phone reconnects (fresh token check)
AUTH_EVERY = 60             # a token signed out elsewhere ends the stream within this
HERE_EVERY = 20             # presence refresh
HERE_TTL = 45               # presence lasts this long without a refresh
TYPING_TTL = 6
REPLAY_MAX = 300            # more missed than this = one reset
GAP_WAIT = 5.0              # how long a missing journal id is asked for again
MAX_PER_MEMBER = 3
LIVE_MAX_PER_APP = 500
LIVE_MAX_TOTAL = 3000
QUEUE = 400                 # a stream that falls this far behind gets a reset instead
CHAT = "_chat"
OWNER = "owner"             # her own console / phone (Hoola login) as a live viewer


class LiveSignal(Base):
    """Short-lived signals (presence / typing), read by every process's tailer. Pruned after a few minutes."""
    __tablename__ = "app_live_signal"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    member: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(60), default="")
    staff: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(10))               # here | gone | typing
    scope: Mapped[str] = mapped_column(String(40), default="")   # here/gone: the stream id; typing: the chat thread
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    data: Mapped[str | None] = mapped_column(Text, nullable=True)   # v0.412 NAKSHA LIVE: a rider's position + who may see it


_OK = False


def ensure_table() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        LiveSignal.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _first(name: str) -> str:
    return (str(name or "").strip().split(" ") or [""])[0][:30]


def _aware(t: datetime | None) -> datetime:
    if t is None:
        return now()
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- one open stream
class Sub:
    def __init__(self, r: AppProject, w: W.Who, colls: set[str] | None, loop: asyncio.AbstractEventLoop):
        self.r, self.w, self.colls, self.loop = r, w, colls, loop
        self.site = _site(r)
        self.sid = uuid.uuid4().hex[:16]
        self.q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE)
        self.behind = False

    @property
    def member(self) -> str:
        return OWNER if self.w.owner else self.w.id

    def put(self, ev: dict[str, Any]) -> None:
        """Called from the tailer thread."""
        def go():
            if self.behind:
                return
            try:
                self.q.put_nowait(ev)
            except asyncio.QueueFull:
                self.behind = True
                try:
                    while True:
                        self.q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                self.q.put_nowait({"type": "reset", "why": "behind"})
                STATS["resets"] += 1
        try:
            self.loop.call_soon_threadsafe(go)
        except RuntimeError:            # its loop is gone (server stopping)
            pass


# ---------------------------------------------------------------- what one journal entry means to one person
_SCHEMA: dict[str, tuple[float, dict[str, Any]]] = {}


def _schema(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    hit = _SCHEMA.get(r.id)
    if hit and time.monotonic() - hit[0] < 10:
        return hit[1]
    with session() as s:                                   # the app's settings as they are NOW (a list added a minute ago)
        fresh = s.get(AppProject, r.id)
        if fresh is not None:
            s.expunge(fresh)
    sch = BE.schema(fresh or r)
    _SCHEMA[r.id] = (time.monotonic(), sch)
    return sch


def _row_view(c: dict[str, Any], row_id: str, data: dict[str, Any], owner: str, created: str, w: W.Who) -> dict[str, Any]:
    """The same fields the list endpoint shows (W.row_view) - nothing internal ('_' keys) leaves."""
    return {"id": row_id, **{f["key"]: data.get(f["key"], "") for f in c["fields"]}, "created": created,
            "mine": bool(w.id) and owner == w.id}


def event_for(sub: Sub, j: Any, sch: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """A journal entry -> the event this person may see, or None. j has id, row_id, coll, op, owner, after, created."""
    w = sub.w
    if j.coll == CHAT:
        if j.op != "insert":
            return None                                    # read marks are not news
        if not (w.staff or (w.id and j.owner == w.id)):
            return None
        try:
            d = json.loads(j.after or "{}")
        except ValueError:
            return None
        return {"type": "chat", "seq": j.id, "id": j.row_id, "thread": j.owner, "staff": bool(d.get("staff")),
                "name": str(d.get("name") or "")[:60], "text": str(d.get("text") or "")[:1000], "at": j.created}
    if str(j.coll).startswith("_"):
        return None
    if sub.colls is not None and j.coll not in sub.colls:
        return None
    sch = sch or _schema(sub.r)
    c = next((x for x in sch.get("collections") or [] if x.get("key") == j.coll), None)
    if c is None:
        return None
    how = ""
    if not W._can_read(c, w, SimpleNamespace(owner=j.owner or "")):
        if w.m is None or (w.m.role or "") != "partner" or j.op == "delete":
            return None
        try:                                               # v0.435 PARIVAAR: a partner's own work only, limited view
            d0 = json.loads(j.after or "{}")
        except ValueError:
            return None
        from . import family as FA
        how = FA.sees(sub.r, w, j.coll, j.row_id, d0)
        if not how:
            return None
    ev = {"type": "row", "seq": j.id, "coll": j.coll, "op": j.op, "id": j.row_id}
    if j.op != "delete":
        try:
            d = json.loads(j.after or "{}")
        except ValueError:
            d = {}
        ev["row"] = _row_view(c, j.row_id, d, j.owner or "", j.created or "", w)
        if how:
            from . import family as FA
            ev["row"] = FA.limit_live(sub.r, c, ev["row"], how)
        if "status" in d:
            ev["status"] = str(d.get("status") or "")
    return ev


def signal_event(sub: Sub, sig: Any, online: bool | None = None) -> dict[str, Any] | None:
    """A presence / typing signal -> the event this person may see. Customers see staff only; nobody sees themselves."""
    w = sub.w
    if sig.kind == "pos":                                  # v0.412 NAKSHA LIVE: a rider on shift moved
        return pos_event(sub, sig)
    if sig.member == sub.member and sig.kind != "typing":
        return None
    if sig.kind == "typing":
        if sig.member == sub.member:
            return None
        if sig.staff:                                      # staff typing in a customer's thread -> that customer only
            if not (w.staff or (w.id and w.id == sig.scope)):
                return None
        elif not w.staff:                                  # a customer typing -> staff only
            return None
        return {"type": "typing", "thread": sig.scope, "name": sig.name, "staff": bool(sig.staff)}
    if not w.staff and not sig.staff:
        return None
    ev = {"type": "presence", "name": sig.name, "staff": bool(sig.staff), "online": bool(online)}
    if w.staff:
        ev["member"] = sig.member
    else:
        ev["member"] = "staff:" + (sig.member if sig.member == OWNER else sig.member[-6:])
    return ev


def pos_event(sub: Sub, sig: Any) -> dict[str, Any] | None:
    """v0.412 a rider's position: staff / the owner see every rider on shift; a customer ONLY the rider bringing HER order,
    only while it is on its way (the list the server wrote into the signal when the rider sent it), never anyone else."""
    try:
        d = json.loads(sig.data or "{}")
    except ValueError:
        return None
    w = sub.w
    base = {"type": "pos", "name": sig.name, "off": bool(d.get("off"))}
    if not base["off"]:
        base.update({"lat": d.get("lat"), "lng": d.get("lng"), "at": d.get("at", ""), "speed": d.get("speed")})
    if w.staff:
        return {**base, "member": sig.member, "orders": sorted((d.get("orders") or {}).keys())}
    mine = {k: v for k, v in (d.get("orders") or {}).items() if w.id and v.get("to") == w.id}
    if not mine:
        return None
    return {**base, "member": "rider", "orders": {k: {"eta_min": v.get("eta_min"), "km": v.get("km")} for k, v in mine.items()}}


# ---------------------------------------------------------------- the per-process tailer
class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.subs: dict[str, set[Sub]] = {}
        self.cur_j: int | None = None
        self.cur_s: int | None = None
        self.gaps: dict[int, float] = {}
        self.here: dict[str, dict[str, dict[str, Any]]] = {}   # site -> member -> {name, staff, conns: {sid: until}}
        self.thread: threading.Thread | None = None
        self.stop = threading.Event()
        self.last_prune = 0.0

    # -- who is connected
    def count(self, site: str = "", member: str = "") -> int:
        with self.lock:
            if not site:
                return sum(len(v) for v in self.subs.values())
            subs = self.subs.get(site, set())
            return sum(1 for s in subs if s.member == member) if member else len(subs)

    def add(self, sub: Sub) -> None:
        with self.lock:
            self.subs.setdefault(sub.site, set()).add(sub)
        self._start()

    def remove(self, sub: Sub) -> None:
        with self.lock:
            got = self.subs.get(sub.site)
            if got is not None:
                got.discard(sub)
                if not got:
                    self.subs.pop(sub.site, None)

    def _start(self) -> None:
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return
            self.stop.clear()
            self.thread = threading.Thread(target=self._run, name="app-live", daemon=True)
            self.thread.start()

    def _run(self) -> None:
        while not self.stop.is_set():
            try:
                if self.count():
                    self.tick()
                else:
                    self.cur_j = self.cur_s = None         # nobody listening: start fresh at the end next time
                    self.gaps.clear()
                    self.here.clear()
            except Exception:                              # noqa: BLE001 - the tailer never dies on one bad read
                log.exception("app live tick")
            self.stop.wait(TICK)

    # -- one read of the journal + the signals
    def tick(self) -> None:
        from .backup import AppJournal, ensure_table as ensure_journal
        ensure_journal()
        ensure_table()
        with self.lock:
            sites = list(self.subs)
        if not sites:
            return
        t = time.monotonic()
        with session() as s:
            if self.cur_j is None:
                self.cur_j = int(s.scalar(select(AppJournal.id).order_by(AppJournal.id.desc()).limit(1)) or 0)
            if self.cur_s is None:
                self.cur_s = int(s.scalar(select(LiveSignal.id).order_by(LiveSignal.id.desc()).limit(1)) or 0)
            new = s.scalars(select(AppJournal).where(AppJournal.id > self.cur_j).order_by(AppJournal.id.asc()).limit(500)).all()
            late = []
            if self.gaps:
                late = s.scalars(select(AppJournal).where(AppJournal.id.in_(list(self.gaps)))).all()
            sigs = s.scalars(select(LiveSignal).where(LiveSignal.id > self.cur_s).order_by(LiveSignal.id.asc()).limit(500)).all()
            for x in list(new) + list(late) + list(sigs):
                s.expunge(x)
        for x in late:                                     # an id that committed after a higher one
            self.gaps.pop(x.id, None)
            STATS["late_commits"] += 1
        expect = self.cur_j + 1
        for x in new:
            for missing in range(expect, x.id):            # a hole: an earlier transaction has not committed yet
                if len(self.gaps) < 2000:
                    self.gaps.setdefault(missing, t)
            expect = x.id + 1
            self.cur_j = x.id
        for gid, since in list(self.gaps.items()):
            if t - since > GAP_WAIT:                       # rolled back (or a skipped sequence number): stop asking
                self.gaps.pop(gid, None)
        site_set = set(sites)
        for x in sorted(list(new) + list(late), key=lambda e: e.id):
            if x.site_id in site_set:
                self.fan(x)
        for sg in sigs:
            self.cur_s = sg.id
            if sg.site_id in site_set:
                self.signal(sg)
        self.expire()
        if time.monotonic() - self.last_prune > 120:
            self.last_prune = time.monotonic()
            prune()

    def fan(self, j: Any) -> None:
        with self.lock:
            subs = list(self.subs.get(j.site_id, ()))
        sch_cache: dict[str, dict[str, Any]] = {}
        for sub in subs:
            try:
                if sub.r.id not in sch_cache and j.coll != CHAT:
                    sch_cache[sub.r.id] = _schema(sub.r)
                ev = event_for(sub, j, sch_cache.get(sub.r.id))
            except Exception:                              # noqa: BLE001
                log.debug("live event", exc_info=True)
                continue
            if ev is not None:
                STATS["events"] += 1
                sub.put(ev)

    def signal(self, sg: Any) -> None:
        if sg.kind == "pos":                               # v0.412 positions are never presence
            if time.time() - _aware(sg.at).timestamp() <= 120:
                self._send(sg.site_id, sg, None)
            return
        if sg.kind == "typing":
            if time.time() - _aware(sg.at).timestamp() > TYPING_TTL:
                return
            self._send(sg.site_id, sg, None)
            return
        people = self.here.setdefault(sg.site_id, {})
        p = people.setdefault(sg.member, {"name": sg.name, "staff": sg.staff, "conns": {}})
        was = bool(p["conns"])
        if sg.kind == "here":
            p["conns"][sg.scope] = _aware(sg.at).timestamp() + HERE_TTL
        else:
            p["conns"].pop(sg.scope, None)
        if bool(p["conns"]) != was:
            self._send(sg.site_id, sg, bool(p["conns"]))

    def expire(self) -> None:
        t = time.time()
        for site, people in list(self.here.items()):
            for member, p in list(people.items()):
                had = bool(p["conns"])
                p["conns"] = {k: u for k, u in p["conns"].items() if u > t}
                if had and not p["conns"]:
                    self._send(site, SimpleNamespace(member=member, name=p["name"], staff=p["staff"], kind="gone", scope=""), False)
                if not p["conns"]:
                    people.pop(member, None)

    def _send(self, site: str, sg: Any, online: bool | None) -> None:
        with self.lock:
            subs = list(self.subs.get(site, ()))
        for sub in subs:
            ev = signal_event(sub, sg, online)
            if ev is not None:
                sub.put(ev)


HUB = Hub()


# ---------------------------------------------------------------- signals (any process)
def _write_signal(site: str, member: str, name: str, staff: bool, kind: str, scope: str = "", data: Any = None) -> None:
    ensure_table()
    with session() as s:
        s.add(LiveSignal(site_id=site, member=member[:40], name=_first(name), staff=1 if staff else 0, kind=kind, scope=scope[:40],
                         data=json.dumps(data, ensure_ascii=False) if data is not None else None))
    STATS["signals"] += 1


def prune() -> None:
    """Signals older than a few minutes are history: removed."""
    ensure_table()
    from sqlalchemy import delete
    try:
        with session() as s:
            s.execute(delete(LiveSignal).where(LiveSignal.at < now() - timedelta(minutes=5)))
    except Exception:                                      # noqa: BLE001
        log.debug("live prune", exc_info=True)


def _me(w: W.Who) -> tuple[str, str, bool]:
    if w.owner:
        return OWNER, "Shop", True
    return w.id, (w.m.name if w.m else "") or (w.m.email.split("@")[0] if w.m and w.m.email else ""), w.staff


def typing(r: AppProject, w: W.Who, thread: str = "") -> dict[str, Any]:
    """POST /live/typing: a customer types in her thread (to staff); staff type in a customer's thread (to that customer)."""
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    member, name, staff = _me(w)
    if not staff:
        thread = w.id                                       # a customer can only ever type in her own thread
    elif not str(thread or "").strip():
        raise W.AppError("Kis baatcheet mein?", 400)
    try:
        W.rate(f"live-typing:{_site(r)}:{member}", 1, 2)   # one signal every 2 s is enough for "typing..."
    except W.AppError:
        return {"ok": True, "quiet": True}                 # a fast typist: the last signal still shows
    _write_signal(_site(r), member, name, staff, "typing", str(thread))
    return {"ok": True}


def online(r: AppProject, w: W.Who) -> dict[str, Any]:
    """GET /live/presence: who is online now (customers: staff only), from the signals table (every process)."""
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    ensure_table()
    site, cut = _site(r), now() - timedelta(seconds=HERE_TTL)
    with session() as s:
        sigs = s.scalars(select(LiveSignal).where(LiveSignal.site_id == site, LiveSignal.kind.in_(("here", "gone")),
                                                  LiveSignal.at >= cut).order_by(LiveSignal.id.asc())).all()
        for x in sigs:
            s.expunge(x)
    conns: dict[str, dict[str, Any]] = {}
    for x in sigs:
        p = conns.setdefault(x.member, {"sig": x, "on": set()})
        p["sig"] = x
        (p["on"].add if x.kind == "here" else p["on"].discard)(x.scope)
    me = OWNER if w.owner else w.id
    sub = SimpleNamespace(w=w, member=me)
    out = []
    for member, p in conns.items():
        if not p["on"] or member == me:
            continue
        ev = signal_event(sub, p["sig"], True)
        if ev is not None:
            out.append({k: v for k, v in ev.items() if k != "type"})
    return {"online": out}


# ---------------------------------------------------------------- the stream itself
def admit(r: AppProject, w: W.Who) -> None:
    """Refuses a stream BEFORE it opens (401 / 429 as plain JSON)."""
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    site, me = _site(r), (OWNER if w.owner else w.id)
    if HUB.count(site, me) >= MAX_PER_MEMBER or HUB.count(site) >= LIVE_MAX_PER_APP or HUB.count() >= LIVE_MAX_TOTAL:
        STATS["refused"] += 1
        raise W.AppError("Abhi bahut log jude hain; app apne aap taaza hota rahega.", 429)


def _sse(ev: dict[str, Any]) -> str:
    seq = ev.pop("seq", None)
    head = f"id: j{seq}\n" if seq else ""
    return f"{head}event: {ev.get('type', 'message')}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"


def replay(sub: Sub, last: str) -> tuple[list[dict[str, Any]], int, bool]:
    """Events missed since Last-Event-ID 'j<id>': (events, the newest journal id looked at, reset?)."""
    from .backup import AppJournal, ensure_table as ensure_journal
    ensure_journal()
    raw = str(last or "").strip()
    if not raw.startswith("j"):
        return [], 0, False
    try:
        since = int(raw[1:])
    except ValueError:
        return [], 0, False
    if since < 0:
        return [], 0, False
    with session() as s:
        got = s.scalars(select(AppJournal).where(AppJournal.site_id == sub.site, AppJournal.id > since)
                        .order_by(AppJournal.id.asc()).limit(REPLAY_MAX + 1)).all()
        for x in got:
            s.expunge(x)
    if len(got) > REPLAY_MAX:
        STATS["resets"] += 1
        return [], got[-1].id, True
    sch = _schema(sub.r)
    out = []
    for x in got:
        ev = event_for(sub, x, sch)
        if ev is not None:
            out.append(ev)
    STATS["replayed"] += len(out)
    return out, (got[-1].id if got else since), False


async def stream(r: AppProject, w: W.Who, token: str, colls: str = "", last: str = "",
                 gone=None, seconds: float | None = None, check=None) -> AsyncIterator[str]:
    """The SSE body. `gone` = an async callable that says the phone hung up (request.is_disconnected). `check` (v0.456) =
    a callable that says the login is still good - a website's own rule (its old site-signed logins, ended sessions)."""
    want = {c.strip() for c in str(colls or "").split(",") if c.strip()} or None
    sub = Sub(r, w, want, asyncio.get_running_loop())
    member, name, staff = _me(w)
    HUB.add(sub)
    STATS["streams"] += 1
    life = STREAM_SECONDS if seconds is None else seconds
    t0 = time.monotonic()
    try:
        await asyncio.to_thread(_write_signal, sub.site, member, name, staff, "here", sub.sid)
        yield f"retry: 3000\nevent: hello\ndata: {json.dumps({'type': 'hello', 'stream': sub.sid, 'tick': TICK})}\n\n"
        done = 0
        if last:
            evs, done, reset = await asyncio.to_thread(replay, sub, last)
            if reset:
                yield _sse({"type": "reset", "why": "missed"})
            for ev in evs:
                yield _sse(ev)
        beat = here = auth = time.monotonic()
        while time.monotonic() - t0 < life:
            if gone is not None and await gone():
                break
            try:
                ev = await asyncio.wait_for(sub.q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                ev = None
            tnow = time.monotonic()
            if ev is not None:
                if ev.get("seq") and done and ev["seq"] <= done:
                    continue                               # already sent by the replay
                if ev.get("type") == "reset":
                    sub.behind = False
                yield _sse(ev)
                beat = tnow
            elif tnow - beat >= HEARTBEAT:
                yield ": ping\n\n"
                beat = tnow
            if tnow - here >= HERE_EVERY:
                here = tnow
                await asyncio.to_thread(_write_signal, sub.site, member, name, staff, "here", sub.sid)
            if not w.owner and tnow - auth >= AUTH_EVERY:
                auth = tnow
                ok = await asyncio.to_thread(check) if check is not None else await asyncio.to_thread(_still_signed_in, r, token, w.id)
                if not ok:
                    yield _sse({"type": "bye", "why": "login"})
                    break
        else:
            yield _sse({"type": "bye", "why": "again"})   # 10 minutes: the phone reconnects with Last-Event-ID
    finally:
        HUB.remove(sub)
        try:
            await asyncio.to_thread(_write_signal, sub.site, member, name, staff, "gone", sub.sid)
        except Exception:                                  # noqa: BLE001
            log.debug("live gone", exc_info=True)


def _still_signed_in(r: AppProject, token: str, member: str) -> bool:
    m = W.member_of(_site(r), token)
    return m is not None and m.id == member


def status() -> dict[str, Any]:
    return {"connected": HUB.count(), "apps": len(HUB.subs), "stats": dict(STATS)}
