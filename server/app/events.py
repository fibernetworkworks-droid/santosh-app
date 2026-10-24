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

# never part of the chat's story (live-only noise) - still stored so a reconnect mid-turn catches up
LIVE_ONLY = {"typing", "step", "work", "log"}
# belong to the chat they were made in only (answers' sources, phone actions, list refreshes...): never copied to others
LOCAL_KINDS = LIVE_ONLY | {
    "message", "upload", "reminders", "routines", "lists", "email_sent", "hoola_update", "galla", "mshop", "office",
    "employee", "darzi_order", "phonedoc_open", "phonedoc_check", "device_action", "device_action_result", "home_device",
    "bt_request", "bazar_open", "bazar_link", "gyaan_sources", "memory_saved", "procedure", "open", "link",
    "call_receipt", "speaker", "voice", "biz_inbox", "biz_appointment", "propagent_listing", "chai_order",
}
# phone actions are done once, live (or through pending actions): never replayed as chat history
ACTIONS = {"device_action", "device_action_result", "home_device", "bt_request", "phonedoc_open", "bazar_open", "bazar_link"}
_ID_KEYS = ("id", "task_id", "session_id", "job_id", "deal_id", "ticket_id", "card_id", "project", "ref")
WAIT_STATUS = {"waiting", "pending", "needs_tap", "waiting_payment", "waiting_sign", "notice_waiting", "minutes_waiting",
               "awaiting", "needs_approval", "pending_tap", "ask"}
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


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._tsubs: dict[str, set[tuple[str, asyncio.Queue]]] = defaultdict(set)   # tenant -> (conv, queue)
        self._loops: dict[int, asyncio.AbstractEventLoop] = {}

    def publish(self, conversation_id: str, kind: str, payload: dict, campaign_id: str | None = None,
                call_id: str | None = None) -> dict:
        call = (call_id if call_id is not None else CALL.get()) or None
        with session() as s:
            ev = Event(conversation_id=conversation_id, campaign_id=campaign_id, kind=kind, payload=payload,
                       call_id=(call or None) and str(call)[:40])
            s.add(ev)
            s.flush()
            data = {"id": ev.id, "kind": kind, "campaign_id": campaign_id, "payload": payload,
                    "at": _utc(ev.created_at).isoformat(), "call": call, "conv": conversation_id}
        targets = list(self._subs.get(conversation_id, ()))
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
                    loop.call_soon_threadsafe(q.put_nowait, data)
                except RuntimeError:
                    pass  # that loop is closed
            else:
                q.put_nowait(data)
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

    def subscribe(self, conversation_id: str, tenant: str = "") -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
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


def _story(conversation_id: str, tenant: str, before: int = 0, scan: int = 6000):
    """Story events of a chat (newest first): its own non-live events + other chats' cards."""
    from . import convs
    with session() as s:
        cond = (Event.conversation_id == conversation_id) & (Event.kind.not_in(LIVE_ONLY | ACTIONS))
        others = [c for c in convs.ids(tenant) if c != conversation_id] if tenant else []
        if others:
            cond = or_(cond, (Event.conversation_id.in_(others)) & (Event.kind.not_in(LOCAL_KINDS)))
        q = select(Event).where(cond)
        if before:
            q = q.where(Event.id < before)
        rows = s.scalars(q.order_by(Event.id.desc()).limit(scan)).all()
        s.expunge_all()
        return rows


def _collapse(rows) -> list[dict]:
    """Newest-first rows -> items in story order: {key, first (Event), latest (Event)}."""
    items: dict[str, dict] = {}
    for e in rows:
        k = card_key(e.kind, e.payload, e.id)
        it = items.get(k)
        if it is None:
            items[k] = {"key": k, "first": e, "latest": e}
        else:
            it["first"] = e
    return sorted(items.values(), key=lambda it: it["first"].id)


def timeline(conversation_id: str, tenant: str, limit: int = 60, before: int = 0) -> dict[str, Any]:
    """The chat in order (see the module doc). `before` = load the page before that event id."""
    limit = max(10, min(int(limit or 60), 400))
    rows = _story(conversation_id, tenant, before)
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
            "conversation_id": conversation_id}


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
