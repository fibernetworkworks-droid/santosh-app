"""v0.863 R3s (docs/HOOLA_APP_REDESIGN_PLAN.md): ONE answer to "how did the newest ask in this chat end?".

Before: the chat list knew only `busy` (the turn lock), Work read the job tracker, the notification read the event,
the chat read the stream - four places that could disagree ("Done" on one, still spinning on another). This reader
looks at the stores that already exist (nothing new is written) and gives every surface the same record:

  status     queued | working | needs_you | done | partial | stuck | stopped | failed      (or "" = nothing asked yet)
  needs_you  True when a card / question / job in THIS chat waits for her answer
  line       one plain English line for a list row or a notification
  made       what the newest ask produced (pages, files, pictures, sites) - title + kind, at most 4
  at         when that state began (ISO)

Order of truth (first that holds wins): a card or a job waiting on her -> needs_you; the turn lock held or a running
turn-inbox row or a running tracked job -> working; an accepted inbox row not started -> queued; a failed inbox row ->
failed; the chat task log's outcome for her newest ask (done / partial / stuck / stopped; talk = done); her newest
message answered -> done. `brief()` is the cheap form for list rows (no card scan); `result()` is the full one.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from .db import Message, session

log = logging.getLogger("santosh.turnresult")

STATUSES = ("queued", "working", "needs_you", "done", "partial", "stuck", "stopped", "failed")
LINE = {"queued": "Waiting to start", "working": "Working on it", "needs_you": "Needs your answer",
        "done": "Done", "partial": "Partly done", "stuck": "Got stuck", "stopped": "Stopped", "failed": "Did not finish"}
MADE_KINDS = {"artifact": "page", "pc_file": "file", "file": "file", "image": "picture", "creation": "picture",
              "site": "site", "website": "site", "video_job": "video", "doc": "document"}


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime | None) -> str:
    d = _utc(d)
    return d.isoformat() if d else ""


def _plain(t: str, n: int = 110) -> str:
    t = re.sub(r"```.*?```", " ", str(t or ""), flags=re.S)
    t = re.sub(r"[#*_`>|~\[\]]", "", t)
    t = re.sub(r"\(https?://[^)]*\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    first = re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0]
    t = first if 12 <= len(first) <= n else t
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _last_her(conv: str) -> Message | None:
    with session() as s:
        return s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "user",
                                               Message.display.is_not(None), Message.display != "")
                         .order_by(Message.id.desc()).limit(1)).first()


def _reply_after(conv: str, after_id: int) -> Message | None:
    with session() as s:
        return s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant",
                                               Message.id > after_id, Message.display.is_not(None),
                                               Message.display != "")
                         .order_by(Message.id.desc()).limit(1)).first()


def _busy(conv: str) -> bool:
    try:
        from .chats import _busy as busy
        return busy(conv)
    except Exception:
        return False


def _inbox(conv: str):
    try:
        from .turn_inbox import TurnInbox, ensure_table
        ensure_table()
        with session() as s:
            return s.scalars(select(TurnInbox).where(TurnInbox.conversation_id == conv)
                             .order_by(TurnInbox.created_at.desc()).limit(1)).first()
    except Exception:
        return None


def _jobs(conv: str) -> list[Any]:
    try:
        from .kaamwatch import KaamJob
        with session() as s:
            return list(s.scalars(select(KaamJob).where(KaamJob.conversation_id == conv,
                                                        KaamJob.state.in_(("working", "waiting")))
                                  .order_by(KaamJob.updated_at.desc()).limit(5)).all())
    except Exception:
        return []


def _task(conv: str, since: datetime | None):
    try:
        from .agent.pakka import TaskRun
        with session() as s:
            q = select(TaskRun).where(TaskRun.conversation_id == conv)
            if since is not None:
                q = q.where(TaskRun.created_at >= since)
            return s.scalars(q.order_by(TaskRun.created_at.desc()).limit(1)).first()
    except Exception:
        return None


def _made(conv: str, after: datetime | None) -> list[dict[str, str]]:
    if after is None:
        return []
    try:
        from .db import Event
        with session() as s:
            rows = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind.in_(list(MADE_KINDS)),
                                                 Event.created_at >= after)
                             .order_by(Event.id).limit(40)).all()
            out: list[dict[str, str]] = []
            seen: set[str] = set()
            for e in rows:
                p = e.payload if isinstance(e.payload, dict) else {}
                key = str(p.get("id") or p.get("file_id") or p.get("artifact_id") or e.id)
                if key in seen:
                    continue
                seen.add(key)
                title = str(p.get("title") or p.get("name") or p.get("filename") or MADE_KINDS[e.kind]).strip()[:80]
                out.append({"kind": MADE_KINDS[e.kind], "title": title, "id": key})
            return out[-4:]
    except Exception:
        return []


def _waiting_card(tenant: str, conv: str) -> dict[str, Any] | None:
    try:
        from .events import CARD_STALE_H, waiting_cards
        ws = waiting_cards(tenant, 3, max_age_h=CARD_STALE_H, conversation_id=conv)
        return ws[0] if ws else None
    except Exception:
        return None


def result(tenant: str, conv: str, cards: bool = True) -> dict[str, Any]:
    """The record for one chat. `cards=False` skips the card scan (cheap, for list rows)."""
    out: dict[str, Any] = {"status": "", "needs_you": False, "line": "", "made": [], "at": ""}
    her = _last_her(conv)
    since = _utc(her.created_at) if her is not None else None

    if cards:
        card = _waiting_card(tenant, conv)
        if card:
            out.update(status="needs_you", needs_you=True, line=card.get("title") or LINE["needs_you"], at=card.get("at", ""))
            out["made"] = _made(conv, since)
            return out
    jobs = _jobs(conv)
    waiting = [j for j in jobs if j.state == "waiting"]
    if waiting:
        j = waiting[0]
        out.update(status="needs_you", needs_you=True, line=(j.title or j.label or LINE["needs_you"])[:110],
                   at=_iso(j.updated_at))
        return out
    inbox = _inbox(conv)
    ib_status = getattr(inbox, "status", "") if inbox is not None else ""
    if _busy(conv) or ib_status == "running" or any(j.state == "working" for j in jobs):
        running = next((j for j in jobs if j.state == "working"), None)
        line = (running.title or running.label) if running is not None else LINE["working"]
        out.update(status="working", line=str(line)[:110], at=_iso(getattr(inbox, "updated_at", None) or since))
        return out
    if ib_status == "accepted":
        out.update(status="queued", line=LINE["queued"], at=_iso(inbox.created_at))
        return out
    if ib_status == "failed" and (since is None or (_utc(inbox.updated_at) or since) >= since):
        out.update(status="failed", line="Did not finish - ask again", at=_iso(inbox.updated_at))
        return out
    if her is None:
        return out
    reply = _reply_after(conv, her.id)
    task = _task(conv, since)
    outcome = (getattr(task, "outcome", "") or "") if task is not None else ""
    status = {"done": "done", "talk": "done", "partial": "partial", "stuck": "stuck", "stopped": "stopped"}.get(outcome, "")
    if not status:
        if ib_status == "stopped":
            status = "stopped"
        elif reply is not None:
            status = "done"
        else:
            return out   # her ask has no answer yet and nothing is running: say nothing rather than guess
    line = _plain(reply.display) if reply is not None and status == "done" else LINE[status]
    if status in ("partial", "stuck") and task is not None and (task.left or "").strip():
        line = f"{LINE[status]}: {_plain(task.left, 90)}"
    out.update(status=status, line=line or LINE[status],
               at=_iso((reply.created_at if reply is not None else None) or (task.created_at if task else None)))
    out["made"] = _made(conv, since)
    return out


def brief(tenant: str, conv: str) -> dict[str, Any]:
    """The list-row form: status, needs_you, line (no card scan, no made list)."""
    try:
        r = result(tenant, conv, cards=False)
        return {"status": r["status"], "needs_you": r["needs_you"], "line": r["line"]}
    except Exception:
        log.exception("turn result for %s failed", conv)
        return {"status": "", "needs_you": False, "line": ""}
