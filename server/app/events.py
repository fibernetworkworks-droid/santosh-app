"""Live event bus: every event is stored (so a reconnecting phone can catch up) and pushed
to anyone currently listening on that conversation."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from sqlalchemy import select

from .db import Event, Message, session


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._loops: dict[int, asyncio.AbstractEventLoop] = {}

    def publish(self, conversation_id: str, kind: str, payload: dict, campaign_id: str | None = None) -> dict:
        with session() as s:
            ev = Event(conversation_id=conversation_id, campaign_id=campaign_id, kind=kind, payload=payload)
            s.add(ev)
            s.flush()
            data = {"id": ev.id, "kind": kind, "campaign_id": campaign_id, "payload": payload,
                    "at": ev.created_at.isoformat()}
        for q in list(self._subs.get(conversation_id, ())):
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
        return data

    def subscribe(self, conversation_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs[conversation_id].add(q)
        try:
            self._loops[id(q)] = asyncio.get_running_loop()
        except RuntimeError:
            pass
        return q

    def unsubscribe(self, conversation_id: str, q: asyncio.Queue) -> None:
        self._subs[conversation_id].discard(q)
        self._loops.pop(id(q), None)

    @staticmethod
    def backlog(conversation_id: str, after_id: int = 0, limit: int = 500) -> list[dict]:
        with session() as s:
            rows = s.scalars(select(Event).where(Event.conversation_id == conversation_id, Event.id > after_id)
                             .order_by(Event.id).limit(limit)).all()
            return [{"id": e.id, "kind": e.kind, "campaign_id": e.campaign_id, "payload": e.payload,
                     "at": e.created_at.isoformat()} for e in rows]


bus = EventBus()


def notify(conversation_id: str, text: str, campaign_id: str | None = None) -> None:
    """A message from Santosh produced by the background worker (not by a chat turn)."""
    with session() as s:
        s.add(Message(conversation_id=conversation_id, role="assistant", content=text, display=text,
                      in_history=False, delivered_to_agent=False))
    bus.publish(conversation_id, "message", {"role": "assistant", "text": text, "source": "worker"},
                campaign_id=campaign_id)
