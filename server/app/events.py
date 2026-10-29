"""Live event bus: every event is stored (so a reconnecting phone can catch up) and pushed
to anyone currently listening on that conversation.

v0.158 the chat she reads is one story:
- cards (approvals, app / website boards, every Sahayak card) from ANY of her chats reach the chat she has open, live
  and on reload (they used to land in whichever chat a job started in, or the newest chat the console made);
- ``timeline`` gives a chat in order: messages and each card ONCE at the moment it first appeared, in its latest
  state, newest page last, older pages on request (the old replay sent the OLDEST 500 events and then skipped the rest);
- every event made by a tool a voice call ran carries that call's id (``call``), so the call shows only its own cards.
"""
from __future__ import annotations

import asyncio
import contextvars
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select

from .db import Event, Message, session

# the live voice call whose tool is running now (set by voice.Call.run_tool; copied into tasks / to_thread)
CALL: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_call", default="")

# v0.161 a reply as it is being written: sent to open streams only, NEVER stored (the final `message` is the record)
# v0.171 `think`: the model's reasoning as it thinks (Claude thinking / GLM reasoning), same live-only discipline
STREAM_KINDS = {"reply_start", "delta", "delta_reset", "reply_end", "think", "say"}
# never part of the chat's story (live-only noise) - still stored so a reconnect mid-turn catches up (except STREAM_KINDS)
LIVE_ONLY = {"typing", "step", "work", "log"} | STREAM_KINDS
# belong to the chat they were made in only (answers' sources, phone actions, list refreshes...): never copied to others
LOCAL_KINDS = LIVE_ONLY | {
    "message", "upload", "reminders", "routines", "lists", "email_sent", "email_new", "email_snooze", "hoola_update",
    "galla", "mshop", "office",
    "employee", "darzi_order", "phonedoc_open", "phonedoc_check", "device_action", "device_action_result", "home_device",
    "bt_request", "bazar_open", "bazar_link", "gyaan_sources", "memory_saved", "procedure", "open", "link",
    "call_receipt", "speaker", "voice", "biz_inbox", "biz_appointment", "propagent_listing", "chai_order",
}
# phone actions are done once, live (or through pending actions): never replayed as chat history
ACTIONS = {"device_action", "device_action_result", "home_device", "bt_request", "phonedoc_open", "bazar_open", "bazar_link"}
_ID_KEYS = ("id", "task_id", "session_id", "job_id", "deal_id", "ticket_id", "card_id", "project", "ref")
WAIT_STATUS = {"waiting", "pending", "needs_tap", "waiting_payment", "waiting_sign", "notice_waiting", "minutes_waiting",
               "awaiting", "needs_approval", "pending_tap", "ask", "blocked"}   # v0.187: a goal blocked on her
# card kinds that always wait for her when they are open (no status field of their own)
TAP_KINDS = {"bazar_approval", "employee_ask", "operator_ask", "studio_approval", "ask_form", "pg_write"}


def card_key(kind: str, payload: Any, event_id: int) -> str:
    """One card = one key (kind + its own id). Messages and id-less events never merge."""
    if kind == "message" or not isinstance(payload, dict):
        return f"e:{event_id}"
    for k in _ID_KEYS:
        v = payload.get(k)
        if isinstance(v, (str, int)) and str(v):
            return f"{kind}:{k}:{v}"
    return f"e:{event_id}"


def needs_her(kind: str, payload: Any) -> bool:
    """Is this card waiting for her answer / tap right now (by its own latest state)?"""
    if not isinstance(payload, dict):
        return False
    st = str(payload.get("status") or payload.get("state") or "").lower()
    if st in WAIT_STATUS:
        return True
    if kind in TAP_KINDS:
        if payload.get("decided") or payload.get("answered") or st in ("approved", "rejected", "done", "expired",
                                                                        "cancelled", "answered", "decided", "failed"):
            return False
        return st in ("", "open")
    return False


def _utc(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _row(e: Event, payload: Any = None, updated: datetime | None = None) -> dict[str, Any]:
    out = {"id": e.id, "kind": e.kind, "campaign_id": e.campaign_id, "payload": e.payload if payload is None else payload,
           "at": _utc(e.created_at).isoformat(), "call": e.call_id or None, "conv": e.conversation_id}
    if updated is not None:
        out["updated_at"] = _utc(updated).isoformat()
    return out


Q_MAX = 400   # v0.208.1 a stream queue holds minutes of bursts, not forever: the SSE client replays the
              # missed events from the DB (backlog), so dropping the OLDEST on a full queue loses nothing.


def _push(q: asyncio.Queue, data: dict) -> None:
    """v0.208.1 put_nowait with drop-oldest. The old unbounded Queue grew without limit whenever a
    consumer stalled or died without unsubscribe (a dead SSE stream leaked EVERY later publish -
    the ~100 MB/min climb behind the voice drops)."""
    try:
        q.put_nowait(data)
    except asyncio.QueueFull:
        try:
            q.get_nowait()   # drop the oldest - the newest state is what a live stream needs
            q.put_nowait(data)
            q._hoola_drops = getattr(q, "_hoola_drops", 0) + 1   # grows only when nobody reads
        except (asyncio.QueueEmpty, asyncio.QueueFull):
            pass


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._tsubs: dict[str, set[tuple[str, asyncio.Queue]]] = defaultdict(set)   # tenant -> (conv, queue)
        self._all: dict[str, set[asyncio.Queue]] = defaultdict(set)                 # v0.162 tenant -> account streams
        self._loops: dict[int, asyncio.AbstractEventLoop] = {}

    def publish(self, conversation_id: str, kind: str, payload: dict, campaign_id: str | None = None,
                call_id: str | None = None, ephemeral: bool = False) -> dict:
        """v0.187 `ephemeral` (the turn's ack line): fanned out to this chat's open streams only - no Event row,
        no chat-list touch, no FCM push, no job watch. It is a word of comfort, not part of the chat's story;
        a reload never shows it and the real reply replaces it."""
        call = (call_id if call_id is not None else CALL.get()) or None
        if ephemeral:
            data = {"id": 0, "kind": kind, "campaign_id": campaign_id, "payload": payload,
                    "at": datetime.now(timezone.utc).isoformat(), "call": call, "conv": conversation_id,
                    "live": True}
            for q in list(self._subs.get(conversation_id, ())) + self._account(conversation_id):
                loop = self._loops.get(id(q))
                try:
                    running = asyncio.get_running_loop()
                except RuntimeError:
                    running = None
                try:
                    if loop is not None and loop is not running:
                        loop.call_soon_threadsafe(_push, q, data)
                    else:
                        _push(q, data)
                except RuntimeError:
                    pass  # that loop is closed
            return data
        with session() as s:
            ev = Event(conversation_id=conversation_id, campaign_id=campaign_id, kind=kind, payload=payload,
                       call_id=(call or None) and str(call)[:40])
            s.add(ev)
            s.flush()
            data = {"id": ev.id, "kind": kind, "campaign_id": campaign_id, "payload": payload,
                    "at": _utc(ev.created_at).isoformat(), "call": call, "conv": conversation_id}
            if kind == "message":   # v0.162 the chat list orders by the latest message
                from .chats import touch
                touch(s, conversation_id)
        targets = list(self._subs.get(conversation_id, ()))
        targets += [q for q in self._account(conversation_id) if q not in targets]
        if kind not in LOCAL_KINDS and self._tsubs:
            try:   # v0.158 the card also reaches her other open chats (phone on one chat, console on another)
                from . import convs
                tenant = convs.tenant_of(conversation_id)
                for c, q in list(self._tsubs.get(tenant, ())):
                    if c != conversation_id and q not in targets:
                        targets.append(q)
            except Exception:
                pass
        for q in targets:
            loop = self._loops.get(id(q))
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            if loop is not None and loop is not running:
                # published from a worker thread (e.g. Bazar tools run in a thread): hand over safely
                try:
                    loop.call_soon_threadsafe(_push, q, data)
                except RuntimeError:
                    pass  # that loop is closed
            else:
                _push(q, data)
        try:   # also to the phone through Firebase, for when the app is closed or the screen is locked
            from . import push
            push.on_event(conversation_id, data)
        except Exception:
            pass
        try:   # v0.136 Hoola watches every long job as it moves and tells her (chat + live call)
            from . import kaamwatch
            kaamwatch.observe(conversation_id, kind, payload)
        except Exception:
            pass
        return data

    def publish_live(self, conversation_id: str, kind: str, payload: dict) -> dict:
        """v0.161 a STREAM_KINDS event: to this chat's open streams only. No database row, no push, no job watch;
        id 0 so a stream sends it without an SSE id (Last-Event-ID never moves on it)."""
        assert kind in STREAM_KINDS, kind
        data = {"id": 0, "kind": kind, "payload": payload, "at": datetime.now(timezone.utc).isoformat(),
                "call": CALL.get() or None, "conv": conversation_id, "live": True}
        for q in list(self._subs.get(conversation_id, ())) + self._account(conversation_id):
            loop = self._loops.get(id(q))
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None
            try:
                if loop is not None and loop is not running:
                    loop.call_soon_threadsafe(_push, q, data)
                else:
                    _push(q, data)
            except RuntimeError:
                pass  # that loop is closed
        return data

    def sweep(self) -> int:
        """v0.208.1 dead-queue GC: a queue whose consumer never reads is removed once it has missed
        enough publishes (drop counter), and any queue whose event loop is closed goes immediately.
        Returns how many queues were pruned (the janitor logs it)."""
        def dead(q: asyncio.Queue) -> bool:
            loop = self._loops.get(id(q))
            if loop is not None and loop.is_closed():
                return True
            return getattr(q, "_hoola_drops", 0) >= 800
        gone = 0
        for reg in (self._subs, self._all):
            for key in list(reg):
                alive = {q for q in reg.get(key, ()) if not dead(q)}
                gone += len(reg.get(key, ())) - len(alive)
                if alive:
                    reg[key] = alive
                else:
                    reg.pop(key, None)
        for tenant in list(self._tsubs):
            alive = {(c, q) for (c, q) in self._tsubs.get(tenant, ()) if not dead(q)}
            gone += len(self._tsubs.get(tenant, ())) - len(alive)
            if alive:
                self._tsubs[tenant] = alive
            else:
                self._tsubs.pop(tenant, None)
        keep = {id(q) for qs in self._subs.values() for q in qs} | \
               {id(q) for qs in self._all.values() for q in qs} | \
               {id(q) for pairs in self._tsubs.values() for _, q in pairs}
        for iq in list(self._loops):
            if iq not in keep:
                self._loops.pop(iq, None)
        return gone

    def _account(self, conversation_id: str) -> list[asyncio.Queue]:
        """v0.162 queues of her account-wide streams (every event of every chat of hers)."""
        if not self._all:
            return []
        try:
            from . import convs
            return list(self._all.get(convs.tenant_of(conversation_id), ()))
        except Exception:
            return []

    def subscribe_account(self, tenant: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=Q_MAX)
        self._all[tenant].add(q)
        try:
            self._loops[id(q)] = asyncio.get_running_loop()
        except RuntimeError:
            pass
        return q

    def unsubscribe_account(self, tenant: str, q: asyncio.Queue) -> None:
        self._all[tenant].discard(q)
        if not self._all[tenant]:
            self._all.pop(tenant, None)
        self._loops.pop(id(q), None)

    @staticmethod
    def backlog_account(tenant: str, after_id: int = 0, limit: int = 500) -> list[dict]:
        """Events of all her chats after `after_id`, oldest first (STREAM_KINDS are never stored)."""
        from . import convs
        ids = convs.ids(tenant)
        if not ids:
            return []
        with session() as s:
            rows = s.scalars(select(Event).where(Event.conversation_id.in_(ids), Event.id > after_id)
                             .order_by(Event.id).limit(limit)).all()
            return [_row(e) for e in rows]

    @staticmethod
    def last_account_id(tenant: str) -> int:
        from . import convs
        ids = convs.ids(tenant)
        if not ids:
            return 0
        with session() as s:
            return int(s.scalar(select(func.max(Event.id)).where(Event.conversation_id.in_(ids))) or 0)

    def subscribe(self, conversation_id: str, tenant: str = "") -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=Q_MAX)
        self._subs[conversation_id].add(q)
        if tenant:
            self._tsubs[tenant].add((conversation_id, q))
        try:
            self._loops[id(q)] = asyncio.get_running_loop()
        except RuntimeError:
            pass
        return q

    def unsubscribe(self, conversation_id: str, q: asyncio.Queue) -> None:
        self._subs[conversation_id].discard(q)
        for t in list(self._tsubs):
            self._tsubs[t].discard((conversation_id, q))
            if not self._tsubs[t]:
                self._tsubs.pop(t, None)
        self._loops.pop(id(q), None)

    @staticmethod
    def backlog(conversation_id: str, after_id: int = 0, limit: int = 500, tenant: str = "") -> list[dict]:
        """Events after `after_id`, oldest first: this chat's, plus (with `tenant`) cards from her other chats."""
        with session() as s:
            cond = Event.conversation_id == conversation_id
            if tenant:
                from . import convs
                others = [c for c in convs.ids(tenant) if c != conversation_id]
                if others:
                    cond = or_(cond, (Event.conversation_id.in_(others)) & (Event.kind.not_in(LOCAL_KINDS)))
            rows = s.scalars(select(Event).where(cond, Event.id > after_id).order_by(Event.id).limit(limit)).all()
            return [_row(e) for e in rows]

    @staticmethod
    def last_id(conversation_id: str, tenant: str = "") -> int:
        with session() as s:
            ids = [conversation_id]
            if tenant:
                from . import convs
                ids = list({conversation_id, *convs.ids(tenant)})
            return int(s.scalar(select(func.max(Event.id)).where(Event.conversation_id.in_(ids))) or 0)


bus = EventBus()


def _story(conversation_id: str, tenant: str, before: int = 0, scan: int = 6000,
           steps: bool = False):
    """Story events of a chat (newest first): its own non-live events + other chats' cards.
    v0.171 `steps` also keeps the `step` events (the console's transcript shows what each turn did, like Claude's
    chat does; the phone timeline stays as it was — it never asked)."""
    from . import chats, convs
    hide = chats.story_filter(conversation_id)     # v0.162 Edit / Dobara versions that are not shown now
    noise = LIVE_ONLY - {"step"} if steps else LIVE_ONLY
    with session() as s:
        cond = (Event.conversation_id == conversation_id) & (Event.kind.not_in(noise | ACTIONS))
        others = [c for c in convs.ids(tenant) if c != conversation_id] if tenant else []
        if others:
            cond = or_(cond, (Event.conversation_id.in_(others)) & (Event.kind.not_in(LOCAL_KINDS)))
        q = select(Event).where(cond)
        if hide is not None:
            q = q.where(hide)
        if before:
            q = q.where(Event.id < before)
        rows = s.scalars(q.order_by(Event.id.desc()).limit(scan)).all()
        s.expunge_all()
        return rows


def _collapse(rows) -> list[dict]:
    """Newest-first rows -> items in story order: {key, first (Event), latest (Event)}."""
    items: dict[str, dict] = {}
    for e in rows:
        if e.kind == "message" and isinstance(e.payload, dict) and (e.payload.get("replaced_by") or e.payload.get("taken_back")):
            continue          # v0.161 a reply she retried: kept as a branch, not part of the story
            # v0.173 a message she took back while queued: it never reached the model, it leaves the chat too
        k = card_key(e.kind, e.payload, e.id)
        it = items.get(k)
        if it is None:
            items[k] = {"key": k, "first": e, "latest": e}
        else:
            it["first"] = e
            # v0.179 `latest` keeps the card's NEWEST state: a resolved ask card must not fall back to its original
            # "waiting" state on reload, and a finished job must not look running again (rows come newest-first, so
            # older rows never overwrite). One v0.171 exception stays: a step that already ended keeps its end state
            # even when a later event of the same step says "running" again (an echo never hides how the call ended).
            step_end_hidden = (e.kind == "step" and isinstance(e.payload, dict) and e.payload.get("state") != "running"
                               and isinstance(it["latest"].payload, dict) and it["latest"].payload.get("state") == "running")
            if e.id > it["latest"].id or step_end_hidden:
                it["latest"] = e
    return sorted(items.values(), key=lambda it: it["first"].id)


def timeline(conversation_id: str, tenant: str, limit: int = 60, before: int = 0, steps: bool = False,
             own: bool = False) -> dict[str, Any]:
    """The chat in order (see the module doc). `before` = load the page before that event id.
    v0.171 `steps=True` (the console): tool-call step events ride along, args and all.
    v0.227.4 `own=True` (the console, many chats side by side): only THIS chat's events, never her other chats'
    cards (the phone keeps the v0.158 one-chat rule)."""
    limit = max(10, min(int(limit or 60), 400))
    rows = _story(conversation_id, "" if own else tenant, before, steps=steps)
    items = _collapse(rows)
    page, older = items[-limit:], items[:-limit]
    # cards that started before this page but still wait for her: kept, at their own place (just above the page)
    extra = [it for it in older if needs_her(it["latest"].kind, it["latest"].payload)][-20:] if not before else []
    out = [_row(it["first"], it["latest"].payload, it["latest"].created_at) for it in extra + page]
    for o, it in zip(out, extra + page):
        o["key"] = it["key"]
        if it["latest"].call_id and not o.get("call"):
            o["call"] = it["latest"].call_id
    return {"events": out, "has_more": bool(older) or len(rows) >= 6000,
            "before": page[0]["first"].id if page else 0,
            "last_event_id": bus.last_id(conversation_id, tenant) if not before else 0,
            "conversation_id": conversation_id, "branches": _branches(conversation_id)}


def _branches(conversation_id: str) -> list[dict]:
    from . import chats
    return chats.info(conversation_id)


def head(conversation_id: str, tenant: str, n: int = 40) -> dict[str, Any]:
    """What the newest part of the chat must contain, for the app's self-check: the story ids in order."""
    items = _collapse(_story(conversation_id, tenant, scan=1500))[-max(5, min(n, 120)):]
    return {"ids": [it["first"].id for it in items], "keys": [it["key"] for it in items],
            "last_event_id": bus.last_id(conversation_id, tenant)}


def waiting_cards(tenant: str, limit: int = 40) -> list[dict[str, Any]]:
    """Cards in ANY of her chats whose latest state waits for her (newest first)."""
    from . import convs
    conv = convs.current(tenant)
    if not conv:
        return []
    items = _collapse(_story(conv, tenant, scan=4000))
    now = datetime.now(timezone.utc)
    out = []
    for it in reversed(items):
        e = it["latest"]
        if needs_her(e.kind, e.payload):
            age = (now - _utc(it["first"].created_at)).total_seconds() / 3600
            out.append({"id": it["first"].id, "kind": e.kind, "key": it["key"], "age_h": round(age, 1),
                        "title": str((e.payload or {}).get("title") or (e.payload or {}).get("what") or
                                     (e.payload or {}).get("reason") or e.kind)[:80]})
            if len(out) >= limit:
                break
    return out


def notify(conversation_id: str, text: str, campaign_id: str | None = None) -> None:
    """A message from Santosh produced by the background worker (not by a chat turn)."""
    with session() as s:
        s.add(Message(conversation_id=conversation_id, role="assistant", content=text, display=text,
                      in_history=False, delivered_to_agent=False))
    bus.publish(conversation_id, "message", {"role": "assistant", "text": text, "source": "worker"},
                campaign_id=campaign_id)
