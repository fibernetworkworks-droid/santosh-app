"""v0.187 kaam ka natija, Hoola ki awaaz mein: when a watched background job finishes (or fails), she does not
get a dry "✅ ho gaya" line any more - ONE short message in Hoola's own words carries the actual result,
written by a tiny one-shot model call (cheap brain, no tools, a second or two) and sent through the normal
notify path (Message + SSE + FCM push) plus a quiet note into her live call. The model here NEVER runs tools
and NEVER sees more than the job's own state line - it is a voice, not a brain.

Why: every one of the ~32 task families already posted a canned kaamwatch line, but it carried no result and
the chat brain never followed up - so "jab result aaye to batana" never really happened (the voice call's
late-result loop was the only working one). Now the promise is true everywhere.

Safety: the digest passed to the model is the job's own public status line (kaamwatch._tidy already masks long
numbers); no tool inputs, no file contents, no secrets. If the model fails or says nothing, the honest canned
line goes out instead - she is never left without the news. Multi-tenant: every row carries tenant_id and the
conversation it belongs to; nothing is ever sent to another chat."""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session
from .events import notify

log = logging.getLogger("santosh.kaam_followup")

STATE_WORD = {"done": "poora ho gaya", "failed": "ruk gaya, dikkat aayi"}
_LOCK = threading.Lock()
_SENDING: set[int] = set()
STATS: dict[str, int] = {"enqueued": 0, "sent": 0, "fallback": 0, "skipped": 0, "postponed": 0, "dup": 0}


def _on() -> bool:
    return os.environ.get("KAAM_FOLLOWUP", "true").lower() not in ("0", "false", "off")


class KaamFollowup(Base):
    __tablename__ = "kaam_followups"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    key: Mapped[str] = mapped_column(String(120), index=True)          # kind:job id (same key as kaam_jobs)
    kind: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    state: Mapped[str] = mapped_column(String(16), default="done")     # done | failed
    detail: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | sent | skipped
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def enqueue(tenant: str, conv: str, job: dict[str, Any]) -> bool:
    """Queue one result report for a finished/failed job (deduped per job key + state). False = not queued."""
    if not _on() or not tenant or not conv:
        return False
    st = job.get("state")
    if st not in ("done", "failed"):
        return False
    key = str(job.get("key") or "")
    if not key:
        return False
    try:
        with _LOCK, session() as s:
            cut = now() - timedelta(minutes=10)
            dup = s.scalars(select(KaamFollowup).where(KaamFollowup.tenant_id == tenant, KaamFollowup.key == key,
                                                       KaamFollowup.state == st,
                                                       KaamFollowup.status.in_(("pending", "sent")),
                                                       KaamFollowup.created_at >= cut)).first()
            if dup:
                return False
            s.add(KaamFollowup(tenant_id=tenant, conversation_id=conv, key=key, kind=str(job.get("kind") or "")[:40],
                               label=str(job.get("label") or "")[:80], title=str(job.get("title") or "")[:200],
                               state=st, detail=str(job.get("detail") or "")[:400], link=str(job.get("link") or "")[:300]))
        STATS["enqueued"] += 1
        return True
    except Exception:
        log.exception("kaam followup enqueue failed")
        return False


def _canned(r: KaamFollowup) -> str:
    """The honest kaamwatch-style line, used when the model has no words (never leave her without the news)."""
    head = f"{r.label} {r.title}".strip()
    if r.state == "failed":
        return f"❌ {head}: ruk gaya, dikkat aayi." + (f" ({r.detail})" if r.detail else "") + \
            " Bataiye to dobara koshish karun ya doosra raasta lun."
    return f"✅ {head}: ho gaya." + (f" {r.detail}" if r.detail else "") + (f" {r.link}" if r.link else "")


async def _model_line(r: KaamFollowup, settings) -> str:
    """One tiny one-shot call (cheap brain first, no tools): the result in Hoola's own words, 1-2 lines."""
    from .agent.pakka import _ask
    system = ("Tum Hoola ho, ek Bharatiya AI coworker. Tumhari malik ke ek kaam ka natija abhi aaya hai. "
              "Usko 1-2 chhoti Hinglish lines mein batao: kya poora hua ya ruk gaya, asli natija kya hai. "
              "Sirf wahi fact bolo jo neeche diya hai - kuch apne aap se jodna mat. Link ho to ek baar saaf likho. "
              "Koi emoji nahi, koi markdown nahi, koi ✅ ❌ jaise symbol nahi.")
    text = f"Kaam: {r.label} {r.title}\nNatija: {STATE_WORD.get(r.state, r.state)}" + \
           (f"\nVivaran: {r.detail}" if r.detail else "") + (f"\nLink: {r.link}" if r.link else "")
    try:
        out = (await _ask(system, text, settings) or "").strip()
    except Exception as e:
        log.info("followup model call failed: %s", e)
        return ""
    return " ".join(out.split())[:600]


def _recent_said(conv: str, title: str) -> bool:
    """The turn's own reply or the job's service already told her this a moment ago: don't say it twice."""
    import re
    try:
        from .db import Message
        cut = now() - timedelta(seconds=300)
        with session() as s:
            rows = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant")
                             .order_by(Message.id.desc()).limit(4)).all()
        words = [w for w in re.split(r"[\s·]+", (title or "").lower()) if len(w) >= 3][:3]
        if not words:
            return False
        for m in rows:
            at = _aware(getattr(m, "created_at", None))
            if at and at < cut:
                continue
            text = (m.display or (m.content if isinstance(m.content, str) else "") or "").lower()
            if text[:1] in set("▶🔄✅❌⏹⏳⚠"):
                continue
            if all(w in text for w in words[:2]):
                return True
    except Exception:
        log.debug("followup dup check failed", exc_info=True)
    return False


def _turn_running(conv: str) -> bool:
    try:
        from .agent import santosh
        lk = santosh._locks.get(conv)
        return bool(lk and lk.locked())
    except Exception:
        return False


async def tick() -> int:
    """The worker slot (every ~10 s): send pending result reports. A report whose chat has a turn running is
    postponed (her words must not interleave); after a few postpones the canned line goes out anyway."""
    if not _on():
        return 0
    out = 0
    with session() as s:
        rows = s.scalars(select(KaamFollowup).where(KaamFollowup.status == "pending", KaamFollowup.tries < 5)
                         .order_by(KaamFollowup.created_at).limit(8)).all()
        rows = [{c: getattr(r, c) for c in ("id", "tenant_id", "conversation_id", "tries")} for r in rows]
    from .config import get_settings
    settings = get_settings()
    for row in rows:
        conv = row["conversation_id"]
        if conv and _turn_running(conv):
            with session() as s:
                r = s.get(KaamFollowup, row["id"])
                if r and r.status == "pending":
                    r.tries += 1
                    if r.tries >= 5:            # never lose the news: the canned line goes out now
                        r.status, r.sent_at = "sent", now()
                        notify(conv, _canned(r))
                        STATS["fallback"] += 1
            STATS["postponed"] += 1
            continue
        if row["id"] in _SENDING:
            continue
        _SENDING.add(row["id"])
        t = asyncio.ensure_future(_send(row["id"], settings))
        _task_row[t] = row["id"]
        _BG.add(t)
        t.add_done_callback(_bg_done)
        out += 1
    return out


_BG: set = set()
_task_row: dict = {}


def _bg_done(t) -> None:
    """Keep the task referenced until it finishes and free the in-flight slot (the santosh._bg pattern)."""
    _BG.discard(t)
    _SENDING.discard(_task_row.pop(t, ""))
    if not t.cancelled() and t.exception():
        log.exception("kaam followup send task failed")


async def _send(fid: str, settings) -> None:
    try:
        with session() as s:
            r = s.get(KaamFollowup, fid)
            if r is None or r.status != "pending":
                return
            conv, tenant, title = r.conversation_id, r.tenant_id, r.title
            r.tries += 1
        if not conv:
            with session() as s:
                r2 = s.get(KaamFollowup, fid)
                if r2:
                    r2.status, r2.sent_at = "skipped", now()
            return
        if _recent_said(conv, title):
            with session() as s:
                r2 = s.get(KaamFollowup, fid)
                if r2:
                    r2.status, r2.sent_at = "skipped", now()
            STATS["dup"] += 1
            return
        line = ""
        try:
            with session() as s:
                rr = s.get(KaamFollowup, fid)
                if rr is not None:
                    line = await _model_line(rr, settings)
        except Exception:
            log.exception("followup model line failed")
        with session() as s:
            r3 = s.get(KaamFollowup, fid)
            if r3 is None or r3.status != "pending":
                return
            if not line:
                line = _canned(r3)
                STATS["fallback"] += 1
            r3.status, r3.sent_at = "sent", now()
        try:
            notify(conv, line)
        except Exception:
            log.exception("followup notify failed")
            return
        try:   # the same quiet note into her live call(s), like every kaamwatch line
            from . import kaamwatch
            kaamwatch._voice(tenant, conv, line)
        except Exception:
            log.debug("followup voice note failed", exc_info=True)
        STATS["sent"] += 1
    except Exception:
        log.exception("kaam followup send failed")


def pending(tenant: str) -> list[dict[str, Any]]:
    """Diagnostics: what is queued right now."""
    with session() as s:
        rows = s.scalars(select(KaamFollowup).where(KaamFollowup.tenant_id == tenant, KaamFollowup.status == "pending")
                         .order_by(KaamFollowup.created_at).limit(20)).all()
        return [{"id": r.id, "key": r.key, "title": r.title, "state": r.state, "tries": r.tries,
                 "created_at": (_aware(r.created_at) or now()).isoformat()} for r in rows]


def forget_old(days: int = 7) -> int:
    cut = now() - timedelta(days=days)
    with session() as s:
        rows = s.scalars(select(KaamFollowup).where(KaamFollowup.created_at < cut)).all()
        for r in rows:
            s.delete(r)
        return len(rows)
