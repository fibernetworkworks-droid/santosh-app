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
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session
from .events import notify

log = logging.getLogger("santosh.kaam_followup")

STATE_WORD = {"done": "poora ho gaya", "failed": "ruk gaya, dikkat aayi", "stopped": "band kar diya gaya"}
_LOCK = threading.Lock()
_SENDING: set[int] = set()
STATS: dict[str, int] = {"enqueued": 0, "sent": 0, "fallback": 0, "skipped": 0, "postponed": 0, "dup": 0,
                         "wake": 0}

# v0.191 HARNESS-2 the wake budget (dsh maxConsecutiveWakes): a chat wakes at most AGENT_WAKE_MAX_CONSECUTIVE times
# without an intervening message of hers (the window ages out too). Her own words reset it (santosh calls wake_reset).
_WAKE_N: dict[str, tuple[int, float]] = {}


def wake_reset(conv: str) -> None:
    """She spoke in this chat again: the wake budget is whole."""
    if conv:
        _WAKE_N.pop(conv, None)


def _wake_allowed(conv: str, settings) -> bool:
    """The brain may be woken for this finished job: feature on, chat idle, budget left."""
    if not getattr(settings, "agent_wake_turns", True):
        return False
    import time as _t
    n, at = _WAKE_N.get(conv, (0, 0.0))
    win = float(getattr(settings, "agent_wake_window_min", 10) or 10) * 60.0
    if win and _t.time() - at > win:
        n = 0
    if n >= int(getattr(settings, "agent_wake_max_consecutive", 3) or 3):
        return False
    try:
        from .agent import santosh
        return not santosh.turn_running(conv)   # her turn holds the chat: the tick path postpones instead
    except Exception:
        return False


def _wake_spend(conv: str) -> None:
    import time as _t
    n, _at = _WAKE_N.get(conv, (0, 0.0))
    _WAKE_N[conv] = (n + 1, _t.time())


def _on() -> bool:
    return os.environ.get("KAAM_FOLLOWUP", "true").lower() not in ("0", "false", "off")


_table_ready = False


def ensure_table() -> None:
    """v0.190.1 P0 self-heal: on databases born before the model was registered with init_db, the
    kaam_followups table does not exist (create_all never saw the model - it only had lazy imports), and
    every query died 'no such table'. The first tick / enqueue after deploy creates it in place and the
    promise 'poora hote hi bata dungi' starts working on old servers too - no manual SQL, no restore."""
    global _table_ready
    if _table_ready:
        return
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        KaamFollowup.__table__.create(eng, checkfirst=True)
    _table_ready = True
    log.info("kaam_followups table ready (self-heal checked)")


class KaamFollowup(Base):
    __tablename__ = "kaam_followups"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    key: Mapped[str] = mapped_column(String(120), index=True)          # kind:job id (same key as kaam_jobs)
    kind: Mapped[str] = mapped_column(String(40), default="")
    label: Mapped[str] = mapped_column(String(80), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    state: Mapped[str] = mapped_column(String(16), default="done")     # done | failed | stopped
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
    """Queue one result report for a finished/failed/stopped job (deduped per job key + state). False = not queued.
    v0.189: stopped jobs report too - she told Hoola to Rokiye a kaam, or the system stopped it; the news is still
    hers, in Hoola's own words, not a dry ⏹ line."""
    if not _on() or not tenant or not conv:
        return False
    ensure_table()          # v0.190.1 P0 self-heal: first touch after deploy creates the table on old DBs
    st = job.get("state")
    if st not in ("done", "failed", "stopped"):
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


def _wake_text(r: KaamFollowup) -> str:
    """The wake turn's 'user' words: the job's own public status line + the instruction. The admission router reads
    these words too, so the tools the result talks about (mail, sheet, video...) are loaded for the follow-up."""
    head = f"{r.label} {r.title}".strip()
    digest = f"Kaam: {head}\nNatija: {STATE_WORD.get(r.state, r.state)}"
    if r.detail:
        digest += f"\nVivaran: {r.detail}"
    if r.link:
        digest += f"\nLink: {r.link}"
    return ("[Santosh worker update, not the user] Ek background kaam ka natija abhi aaya hai:\n" + digest +
            "\n\nIsko apni awaaz mein 1-3 chhoti lines mein batao - kya hua, asli natija kya hai. Bole jaise phone "
            "par bolte hain: chhote vaakya, comma ka matlab chhota pause, aur energy natije ke hisaab se (sahi nikla "
            "to thodi khushi awaaz mein, adhura ya galat to dheemi aur seedhi). Agar natija adhura "
            "ya galat lag raha hai, ya usme jo bataya gaya usse zyada kaam baaki hai, to tools se haalat check kar ke "
            "sahi jaankari do (jo tools dikhe unse; jo nahi dikhe tool_search se lao). Jo pata hai wahi bolo, kuch "
            "apne aap se mat jodo.")


async def _wake_turn(r: KaamFollowup, settings) -> bool:
    """Wake the REAL brain for this finished job (tools allowed, actor='wake'): Hoola reads the result, may check
    the truth with tools, and reports in her own words through the normal message path (SSE + FCM push).
    False/exception = fall back to the v0.187 one-shot line - the news is never lost."""
    from .agent import eventlog
    eventlog.log_event(r.tenant_id, r.conversation_id, "wake",
                       {"line": f"{r.label} {r.title} {STATE_WORD.get(r.state, r.state)}", "job": r.key,
                        "mode": "wake_turn"})
    try:
        from .agent import santosh
        text = await santosh.run_turn(r.conversation_id, _wake_text(r), tenant_id=r.tenant_id, actor="wake",
                                      save_user=False)
        if not str(text or "").strip():
            return False
        _wake_spend(r.conversation_id)
        STATS["wake"] += 1
        try:   # the same quiet note into her live call, exactly like the one-shot line
            from . import kaamwatch
            kaamwatch._voice(r.tenant_id, r.conversation_id, " ".join(str(text).split())[:300])
        except Exception:
            log.debug("wake voice note failed", exc_info=True)
        return True
    except Exception:
        log.exception("wake turn failed")
        return False


def _canned(r: KaamFollowup) -> str:
    """The honest kaamwatch-style line, used when the model has no words (never leave her without the news)."""
    head = f"{r.label} {r.title}".strip()
    if r.state == "failed":
        return f"❌ {head}: ruk gaya, dikkat aayi." + (f" ({r.detail})" if r.detail else "") + \
            " Bataiye to dobara koshish karun ya doosra raasta lun."
    if r.state == "stopped":
        return f"⏹ {head}: band kar diya gaya." + (f" ({r.detail})" if r.detail else "") + \
            " Jab chahiye, bas bol dena - phir shuru kar dunga."
    return f"✅ {head}: ho gaya." + (f" {r.detail}" if r.detail else "") + (f" {r.link}" if r.link else "")


_ONE_SHOT_SYSTEM = (   # v0.193 the delivery brief lives in ONE place so tests pin it
    "Tum Hoola ho, ek Bharatiya AI coworker. Tumhari malik ke ek kaam ka natija abhi aaya hai. "
    "Usko 1-2 chhoti Hinglish lines mein batao: kya poora hua, ruk gaya, ya band kar diya gaya, asli "
    "natija kya hai. Jaise phone par bolti hai waise likho: chhote vaakya, comma ka matlab chhota pause, "
    "energy natije ke hisaab se (sahi nikla to thodi khushi, ruk gaya ya band hua to dheemi aur seedhi "
    "awaaz). Sirf wahi fact bolo jo neeche diya hai - kuch apne aap se jodna mat. Link ho to ek "
    "baar saaf likho. Koi emoji nahi, koi markdown nahi, koi ✅ ❌ jaise symbol nahi.")


def _spoken(line: str) -> str:
    """The chat line as SHE would hear it in a live call: symbols out, the flat 'title: state' colon becomes a
    spoken comma. The chat keeps the original line as it is."""
    out = re.sub(r"[✅❌⏹▶🔄⚠⏳]\s*", "", str(line or "")).strip()
    out = out.replace(": ", ", ", 1)
    return out


async def _model_line(r: KaamFollowup, settings) -> str:
    """One tiny one-shot call (cheap brain first, no tools): the result in Hoola's own words, 1-2 lines."""
    from .agent.pakka import _ask
    system = _ONE_SHOT_SYSTEM
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
    ensure_table()          # v0.190.1 P0 self-heal (see enqueue)
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
        with session() as s:   # v0.191 a fresh copy for the wake decision (the row may age while we work)
            rr = s.get(KaamFollowup, fid)
            snapshot = None if rr is None else KaamFollowup(
                id=rr.id, tenant_id=rr.tenant_id, conversation_id=rr.conversation_id, key=rr.key, kind=rr.kind,
                label=rr.label, title=rr.title, state=rr.state, detail=rr.detail, link=rr.link,
                status=rr.status, tries=rr.tries, created_at=rr.created_at, sent_at=rr.sent_at)
        if snapshot is not None and _wake_allowed(conv, settings):
            if await _wake_turn(snapshot, settings):
                with session() as s:
                    r2 = s.get(KaamFollowup, fid)
                    if r2 is not None and r2.status == "pending":
                        r2.status, r2.sent_at = "sent", now()
                return                   # the wake turn already told her (and the call) in Hoola's own words
            log.info("wake turn declined for %s; the one-shot line goes instead", fid)
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
        try:   # the same quiet note into her live call(s), like every kaamwatch line - spoken shaped (v0.193)
            from . import kaamwatch
            kaamwatch._voice(tenant, conv, _spoken(line))
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
