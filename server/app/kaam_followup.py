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
import time
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

STATE_WORD = {"done": "finished", "failed": "stopped, ran into a problem", "stopped": "was stopped"}
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


def enqueue(tenant: str, conv: str, job: dict[str, Any], dup_ok: bool = False) -> bool:
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
                return bool(dup_ok)     # v0.657 the caller may count "already on its way" as reported
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
    if r.kind == "research_watch" and r.state == "done":    # v0.480 R9: a watched topic CHANGED - a short message, from the diff
        rid = r.key.split(":", 1)[-1]
        return (f"[Santosh worker update, not the user] <research_change_due run=\"{rid}\">\nThe topic you were watching has changed ({r.title}): {r.detail}\n"
                f"First call the research_watch tool with action=result, run_id={rid} - it holds the digest of the change. Then write a SHORT message (3-8 lines): "
                f"what changed (what it was before -> what it is now, for which period), what is new, and what was not seen this time (write 'not seen this time', never 'changed'). Do not add reasons of your own. "
                f"Give new figures with their [n] source; give an old figure without [n], marked 'before'. End by asking: does she want the full report (research_status result) or should the watch be stopped.\n</research_change_due>")
    if r.kind == "research_run" and r.state == "done":     # v0.475 R4: the report is WRITTEN here, from the dossier
        rid = r.key.split(":", 1)[-1]
        return (f"[Santosh worker update, not the user] <research_report_due run=\"{rid}\">\nThe research is finished ({r.title}): {r.detail}\n"
                f"Now write her REPORT: first call the research_status tool with action=result, id={rid} - it holds the dossier. Write the report only from that dossier "
                f"(do not run research_run again): every number with its note's source [n] and date; what could not be confirmed goes "
                f"in a separate section 'Not confirmed', then the list of sources. Write in clear simple English. If she asked for something long or a file, "
                f"make a PDF / Word with the research_document tool (pass your final report as `report`) and give a summary + the file in the chat.\n</research_report_due>")
    if r.kind == "agent_team" and r.state in ("done", "failed"):
        # v0.722 JAWAB HI JAWAB: a background crew's deliverable (up to 24k chars, AgentTeam.result) never reached the chat -
        # the follow-up carried a 400-char snippet + "1-3 lines", so her question ("5 million dollar AI SaaS idea dhundo")
        # got a status survey of her whole desk and "the result should be in your chat above" instead of the answer
        tid = r.key.split(":", 1)[-1]
        return (f"[Santosh worker update, not the user] <team_result_due team=\"{tid}\">\nThe team she started: "
                f"{STATE_WORD.get(r.state, r.state)} ({r.label} {r.title}).".replace("( ", "(") + (f"\nDetails: {r.detail}" if r.detail else "") + f"\nFirst call the agent_status tool with action=check, id={tid} - it holds "
                f"the team's COMPLETE deliverables. Now write the ACTUAL ANSWER TO HER QUESTION right here in the chat from them - complete, "
                f"clear, in simple English (as much as the question needs; if she asked for three ideas, give all three, each with "
                f"the key points). This IS the answer for this chat: do not list other jobs / projects / cards, do not run kaam_status, "
                f"do not write 'the answer is above'. Do not add anything that is not in the deliverables; if something is unfinished, "
                f"say so in one line.\n</team_result_due>")
    head = f"{r.label} {r.title}".strip()
    digest = f"Job: {head}\nResult: {STATE_WORD.get(r.state, r.state)}"
    if r.detail:
        digest += f"\nDetails: {r.detail}"
    if r.link:
        digest += f"\nLink: {r.link}"
    return ("[Santosh worker update, not the user] The result of a background job has just come in:\n" + digest +
            "\n\nTell her this in your own voice in 1-3 short lines - what happened, what the real result is. Speak the way "
            "people talk on the phone: short sentences, a comma is a short pause, energy to match the result (a little "
            "pleased if it worked, slower and plainer if it is incomplete or wrong). If the result looks incomplete "
            "or wrong, or there is more work left than what was reported, check the real state with tools "
            "and give the right information (use the tools you can see; load others with tool_search). Say only what you know, "
            "add nothing of your own. Talk ONLY about THIS job - do not list other jobs / projects / cards. "
            "Write 'the result is above in the chat' only if it really is written above in this chat.")


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
        t0 = time.time()
        text = await santosh.run_turn(r.conversation_id, _wake_text(r), tenant_id=r.tenant_id, actor="wake",
                                      save_user=False)
        if not str(text or "").strip():
            return False
        if santosh.turn_failed_since(r.conversation_id, t0):
            # v0.657 PAKKA KAAM: the wake turn crashed / timed out / hit the budget and RETURNED its error line - that
            # is not the result. False = the honest canned line (with the result's link) goes out, never lost.
            STATS["wake_failed"] = STATS.get("wake_failed", 0) + 1
            return False
        _wake_spend(r.conversation_id)
        STATS["wake"] += 1
        try:   # the same quiet note into her live call, exactly like the one-shot line
            from . import kaamwatch
            # CALL PAR TEAM: a few full sentences (300 chars left one fragment of a 4-agent result on the call)
            kaamwatch._voice(r.tenant_id, r.conversation_id, " ".join(str(text).split())[:700])
        except Exception:
            log.debug("wake voice note failed", exc_info=True)
        return True
    except Exception:
        log.exception("wake turn failed")
        return False


def _canned(r: KaamFollowup) -> str:
    """The honest kaamwatch-style line, used when the model has no words (never leave her without the news)."""
    try:   # CALL PAR TEAM: her avatar's own forms ("shuru kar dungi")
        from .avatar.service import gendered, persona
        return gendered(_canned_raw(r), persona(r.tenant_id)[1])
    except Exception:
        return _canned_raw(r)


def _canned_raw(r: KaamFollowup) -> str:
    head = f"{r.label} {r.title}".strip()
    if r.state == "failed":
        return f"❌ {head}: stopped, ran into a problem." + (f" ({r.detail})" if r.detail else "") + \
            " Tell me if you want me to try again or take another route."
    if r.state == "stopped":
        return f"⏹ {head}: was stopped." + (f" ({r.detail})" if r.detail else "") + \
            " Whenever you want it, just say so and I will start it again."
    return f"✅ {head}: done." + (f" {r.detail}" if r.detail else "") + (f" {r.link}" if r.link else "")


_ONE_SHOT_SYSTEM = (   # v0.193 the delivery brief lives in ONE place so tests pin it
    "You are Hoola, an Indian AI coworker. The result of one of your owner's jobs has just come in. "
    "Tell her in 1-2 short lines of clear simple English: whether it finished, stopped, or was cancelled, and what the real "
    "result is. Write the way you would say it on the phone: short sentences, a comma is a short pause, "
    "energy to match the result (a little pleased if it worked, slower and plainer if it stopped or was cancelled). "
    "Say only the facts given below - add nothing of your own. If there is a link, write it clearly once. "
    "No emoji, no markdown, no symbols like ✅ ❌.")


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
           (f"\nDetails: {r.detail}" if r.detail else "") + (f"\nLink: {r.link}" if r.link else "")
    try:
        out = (await _ask(system, text, settings) or "").strip()
    except Exception as e:
        log.info("followup model call failed: %s", e)
        return ""
    return " ".join(out.split())[:600]


def _job_started(tenant: str, key: str):
    """When the job behind this report started (kaam_jobs), or None when it is not known."""
    if not tenant or not key:
        return None
    try:
        from .kaamwatch import KaamJob
        with session() as s:
            r = s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.key == key)).first()
            return _aware(r.started_at) if r is not None else None
    except Exception:
        log.debug("job start lookup failed", exc_info=True)
        return None


def _turn_began(conv: str, msg_id: int):
    """When the turn that wrote assistant message `msg_id` began = her last saved words before it (None if none)."""
    from .db import Message
    with session() as s:
        u = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "user",
                                            Message.id < msg_id).order_by(Message.id.desc()).limit(1)).first()
        return _aware(getattr(u, "created_at", None)) if u is not None else None


def _other_jobs_report(conv: str, key: str, at) -> bool:
    """v0.551 this reply WAS another finished job's own wake report (sent within two minutes after it was saved)."""
    if at is None:
        return False
    try:
        ensure_table()
        with session() as s:
            rows = s.scalars(select(KaamFollowup).where(KaamFollowup.conversation_id == conv,
                                                        KaamFollowup.status == "sent",
                                                        KaamFollowup.key != key,
                                                        KaamFollowup.sent_at >= at - timedelta(seconds=5),
                                                        KaamFollowup.sent_at <= at + timedelta(seconds=120))).all()
            return bool(rows)
    except Exception:
        log.debug("other-report check failed", exc_info=True)
        return False


def _answered_since(conv: str, since, key: str = "", tenant: str = "") -> bool:
    """v0.260: did a REAL reply land in this chat after the job finished? Then the turn she was watching already
    told her, and waking the brain for a second report is the duplicate she saw on 29 Oct ("Competitor job poora ho
    gaya" under a full answer). _recent_said below only matched the TITLE's words against the reply, so it missed
    every paraphrase - and missed completely when the reply came out in another language, which is exactly what
    happened. This check is about WHEN, not about words, so it holds in any language.
    """
    if since is None:
        return False
    try:
        from .db import Message
        cut = _aware(since) - timedelta(seconds=5)       # the reply may be saved a moment before the row
        with session() as s:
            rows = s.scalars(select(Message).where(Message.conversation_id == conv, Message.role == "assistant")
                             .order_by(Message.id.desc()).limit(6)).all()
        for m in rows:
            at = _aware(getattr(m, "created_at", None))
            if not at or at < cut:
                continue
            if getattr(m, "in_history", True) is False:
                continue                                  # progress lines / notes are not an answer
            text = (m.display or (m.content if isinstance(m.content, str) else "") or "").strip()
            if text[:1] in set("\u25b6\U0001f504\u2705\u274c\u23f9\u23f3\u26a0"):
                continue                                  # a status chip is not an answer either
            if len(text) >= 40:                           # a real reply, not a one-word ack
                # v0.552 NATIJA PAKKA: a reply is THIS job's report only when its turn ran the job (began before
                # the job started) and it is not another job's own wake report. Before, ANY reply after the
                # finish counted, so a job that finished while she asked about something else was never told.
                if key and _other_jobs_report(conv, key, at):
                    continue
                started = _job_started(tenant, key)
                if started is not None:
                    began = _turn_began(conv, m.id)
                    if began is None or began > started + timedelta(seconds=5):
                        continue                          # she asked something else after the job began
                return True
    except Exception:
        log.debug("answered-since check failed", exc_info=True)
    return False


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
        rows = s.scalars(select(KaamFollowup).where(KaamFollowup.status == "pending", KaamFollowup.tries < _MAX_TRIES)
                         .order_by(KaamFollowup.created_at).limit(8)).all()
        rows = [{c: getattr(r, c) for c in ("id", "tenant_id", "conversation_id", "tries")} for r in rows]
    from .config import get_settings
    settings = get_settings()
    for row in rows:
        conv = row["conversation_id"]
        if row["id"] in _SENDING:
            # v0.657 PAKKA KAAM: checked FIRST - the turn holding the chat may be this row's OWN wake turn; counting
            # that as "her turn is busy" posted the dry canned line in the middle of the real report (told twice)
            continue
        if conv and _turn_running(conv):
            with session() as s:
                r = s.get(KaamFollowup, row["id"])
                if r and r.status == "pending":
                    r.tries += 1
                    age = (now() - (_aware(r.created_at) or now())).total_seconds()
                    # v0.552 NATIJA PAKKA: wait for her turn up to KAAM_FOLLOWUP_WAIT_S (5 min), not 5 ticks (~50 s):
                    # an ordinary multi-tool turn used to get a dry line dropped into its middle and the real report
                    # never came. A truly long turn still gets the honest line - the news is never lost.
                    if age >= _wait_s() or r.tries >= _MAX_TRIES - 1:
                        r.status, r.sent_at = "sent", now()
                        line = _canned(r)
                        notify(conv, line)
                        STATS["fallback"] += 1
                        try:   # CALL PAR TEAM: a live call hears it too (it went to the chat only)
                            from . import kaamwatch
                            kaamwatch._voice(r.tenant_id, conv, line[:700])
                        except Exception:
                            log.debug("fallback voice note failed", exc_info=True)
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
_MAX_TRIES = 60          # v0.552 postpones count here too (every ~10 s), so the cap sits above the 5-minute wait


def _wait_s() -> int:
    try:
        return max(30, int(os.environ.get("KAAM_FOLLOWUP_WAIT_S", "300")))
    except ValueError:
        return 300


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
            conv, tenant, title, key = r.conversation_id, r.tenant_id, r.title, r.key
            r.tries += 1
        if not conv:
            with session() as s:
                r2 = s.get(KaamFollowup, fid)
                if r2:
                    r2.status, r2.sent_at = "skipped", now()
            return
        if _recent_said(conv, title) or _answered_since(conv, getattr(r, "created_at", None), key=key, tenant=tenant):
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
                # v0.553 GHANTI: the wake turn is the NORMAL path, and it returned before the ring below - so a
                # finished job almost never rang her phone. It rings here too (same gates: quiet hours, daily cap,
                # never over a live call).
                _ring(conv, snapshot.key, snapshot.state, title, settings)
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
        _ring(conv, r3.key, r3.state, title, settings)
        STATS["sent"] += 1
    except Exception:
        log.exception("kaam followup send failed")


def _ring(conv: str, key: str, state: str, title: str, settings) -> None:
    """v0.211 NO live call? the SERVER may ring her phone for this news: kind=voice_ring data push, gated in
    push.on_event (quiet hours, daily budget, never while a call is live); v0.219 the phone's native side learned
    the kind and the setting flipped ON - 'if we dont give call it never reply on its own'. v0.553: ONE helper for
    both report paths (the wake turn and the one-shot line)."""
    try:
        if settings.voice_ring:
            from . import push as _push
            _push.on_event(conv, {"kind": "voice_ring", "id": key, "at": "",
                                  "payload": {"reason": f"kaam {state}: {title}"[:80], "ref": key, "conv": conv}})
            STATS["ring"] = STATS.get("ring", 0) + 1
    except Exception:
        log.debug("voice ring skipped", exc_info=True)


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
