"""G8 of docs/LANGGRAPH_TURN_PLAN.md - an approval card PARKS the turn graph (only when `chat_graph` and
`graph_card_park` are on; the old loop never imports this module).

Before G8 a tool that needed her tap returned "card created", the turn ended, her tap later ran the action OUTSIDE
the turn (the card's own route) and the job only went on if something else woke it. Now:

  1. A graph run whose tools made a card she must tap (a bazar confirm card - orders, payments, deletes, bulk and
     public changes of every connector that asks first - or an email draft / forward card) ends its answer as today
     (the model says "tap Send"), and then, instead of END, its thread PARKS: `finish` routes to `deliver` (the reply
     is told once, G5), `deliver` writes one `turn_card_parks` row per waiting card (card kind + id, the tool_use id,
     the tool, its argument hash, the chat's newest message id = the mark) and the `park` node calls LangGraph's
     official `interrupt()`. The checkpoint keeps the pending interrupt; the run's inbox row is `waiting_tap`; the
     delivery record's outcome is `waiting`.
  2. Her tap runs the action EXACTLY as before (the card's own route and code: bazar's claim-once conditional update,
     money only on her tap, nothing auto-approved). Only AFTER it ran does the card's code call `answered(kind, id,
     answer, result)`: the row is claimed `waiting -> answered` by one conditional UPDATE (a second call never wins),
     and the card's own chat line ("'X' is done.") is NOT written - the job's own turn tells it.
  3. `resume_due(thread)` (scheduled at once; the worker's `sweep` picks up one a restart cut) waits for the chat to
     be free, claims every answered row of the thread (`answered -> resuming`), and runs ONE ordinary turn of the chat
     (santosh.run_turn, actor "approved:card" = her tap's authority) whose history-only line says what she answered.
     That turn takes the chat's G2 ticket like any other (never two runs on one chat); its graph run resumes the
     parked thread with `Command(resume=...)`: the `park` node gets the answers, records them as G3 facts (done ->
     did, failed -> failed, declined -> skipped, unknown -> ambiguous), remembers a declined card's tool + arguments
     (the ledger runner refuses to run it again in that thread) and sends the job back to `model`. The model then
     continues the SAME job from that step; the result is delivered by that run's own G5 record, once.

Answers: done (the action ran; its result text), failed (it ran and failed), declined (she tapped Not now / Cancel:
nothing ran - the model is told not to try again unless she asks), unknown (the action began but a restart cut it -
bazar's 'interrupted'), expired (the card's own expiry, or `graph_card_park_ttl_h` without a tap) and replaced (the
model made a new card in its place). Expired / replaced never wake the model: the row is closed and, when nothing of
the thread is still waiting or answered, the parked thread is deleted (checkpoint + ledger) and its inbox row goes
`done` - the card's own expiry line is the one thing she sees, as today.

Two cards in one run: the run parks on ALL of them (one row each). Each answer resumes the thread once; the resume
line carries every answer claimed at that moment and names the cards still waiting; the resumed run, when it ends with
cards still waiting, parks again on those. So the job never waits for the slowest card, and no answer is told twice.

A restart while parked keeps the park (the checkpoint + the rows are on disk); a tap after it resumes the same thread.
A card made outside a graph run with a checkpoint (the old loop, a call's direct tools, a call's brain ask, a run whose
checkpointer could not open) is never parked: `answered()` finds no row and the card's code does what it always did.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.turnpark")

STATS = {"parked": 0, "cards": 0, "answered": 0, "lost_race": 0, "resumes": 0, "resumed_fresh": 0, "closed": 0,
         "expired": 0, "declined_guard": 0, "swept": 0}
WAITING, ANSWERED, RESUMING, RESUMED, CLOSED = "waiting", "answered", "resuming", "resumed", "closed"
ANSWERS = ("done", "failed", "declined", "unknown", "expired", "replaced")
WAKES = ("done", "failed", "declined", "unknown")          # answers that continue the job (a model run)
LINE_PREFIX = "[Card answered by her tap - not her words]"
FACT_EFFECT = {"done": "did", "failed": "failed", "declined": "skipped", "unknown": "ambiguous"}

# the parked thread a run of this chat resumes (set by resume_due around its run_turn; taken once by run_steps)
PARK_RUN: contextvars.ContextVar = contextvars.ContextVar("turnpark_run", default=None)

_ready_engine = None
_LOOP: list = []                                   # the server's event loop (a tap's thread schedules onto it)
_LOCKS: dict = defaultdict(asyncio.Lock)
_TASKS: set = set()


class TurnCardPark(Base):
    __tablename__ = "turn_card_parks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cp"))
    thread_id: Mapped[str] = mapped_column(String(160), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    tenant_id: Mapped[str] = mapped_column(String(64), default="")
    inbox_id: Mapped[str] = mapped_column(String(40), default="")
    card_kind: Mapped[str] = mapped_column(String(20), default="")          # bazar | email | studio (G9)
    card_id: Mapped[str] = mapped_column(String(64), index=True, default="")
    tool_use_id: Mapped[str] = mapped_column(String(120), default="")
    tool: Mapped[str] = mapped_column(String(120), default="")
    args_hash: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(12), default=WAITING, index=True)
    answer: Mapped[str] = mapped_column(String(12), default="")
    result: Mapped[str] = mapped_column(Text, default="")
    mark: Mapped[int] = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime(timezone=True), default=now)
    answered_at = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


def ensure_table() -> None:
    """Self-heal (the v0.190.1 rule): a database born before this model gets the table on first use."""
    global _ready_engine
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or eng is _ready_engine:
        return
    TurnCardPark.__table__.create(eng, checkfirst=True)
    _ready_engine = eng


def on(settings=None) -> bool:
    try:
        if settings is None:
            from ..config import get_settings
            settings = get_settings()
        return bool(getattr(settings, "chat_graph", False) and getattr(settings, "graph_card_park", False))
    except Exception:   # noqa: BLE001
        return False


def bind_loop() -> None:
    """Remember the server's loop (called from the loop: a park, the worker's sweep)."""
    try:
        lp = asyncio.get_running_loop()
    except RuntimeError:
        return
    if not _LOOP or _LOOP[0] is not lp:
        _LOOP[:] = [lp]


# ---------------------------------------------------------------- which tool results are cards she must tap

def card_of(tool: str, out: Any) -> dict | None:
    """{kind, id, title} when this tool result is a card waiting for her tap that this module can park on."""
    if not isinstance(out, dict):
        return None
    if out.get("needs_approval") and out.get("approval_id"):
        title = str(((out.get("card") or {}) if isinstance(out.get("card"), dict) else {}).get("title") or tool)
        return {"kind": "bazar", "id": str(out["approval_id"])[:64], "title": title[:200]}
    if tool in ("email_draft", "email_forward") and out.get("draft_id") \
            and str(out.get("status") or "") == "pending_approval":
        subj = str(out.get("subject") or "email")
        return {"kind": "email", "id": str(out["draft_id"])[:64], "title": ("Email: " + subj)[:200]}
    aid = out.get("waiting_owner")
    if isinstance(aid, str) and aid.startswith("sa") and "inr" in out:      # G9: a Video Studio / Create price card
        c = {"kind": "studio", "id": aid[:64], "title": f"Video Studio price card (Rs {out.get('inr')})"[:200]}
        if out.get("project"):
            c["project"] = str(out["project"])[:120]
        return c
    return None


def _studio_pending(card: dict) -> bool:
    """G9: a studio price card lives in its project's JSON (data/studio/<tenant>/projects), not in a table: the tenant
    comes from the run (turngraph._note_card) or the park row, the project from the tool result or the tenant's list."""
    from ..studio import service as ss
    aid = str(card.get("id") or "")
    tenant = str(card.get("tenant") or "")
    if not tenant:
        ensure_table()
        with session() as s:
            r = s.scalars(select(TurnCardPark).where(TurnCardPark.card_kind == "studio", TurnCardPark.card_id == aid)
                          .limit(1)).first()
            tenant = r.tenant_id if r is not None else ""
    if not tenant or not aid:
        return False
    st = ss.studio_sync(tenant)
    names = [card["project"]] if card.get("project") else [p["project"] for p in ss.listing(tenant, hidden=True)]
    for name in names:
        try:
            a = (st.load(name).get("approvals") or {}).get(aid)
        except Exception:   # noqa: BLE001 - a project that cannot be read holds no waiting card
            continue
        if a is not None:
            return str(a.get("status") or "") == "pending"
    return False


def still_waiting(card: dict) -> bool:
    """Is this card still waiting for her tap right now (its own row says so)?"""
    try:
        if card.get("kind") == "bazar":
            from ..bazar.db import Approval
            with session() as s:
                a = s.get(Approval, card.get("id"))
                return a is not None and a.decision == "pending"
        if card.get("kind") == "email":
            from ..db import EmailDraft
            with session() as s:
                d = s.get(EmailDraft, card.get("id"))
                return d is not None and d.status == "pending"
        if card.get("kind") == "studio":
            return _studio_pending(card)
    except Exception:   # noqa: BLE001
        log.exception("card state check failed")
    return False


# ---------------------------------------------------------------- the park itself (the graph's deliver / park nodes)

def register(thread: str, conversation_id: str, tenant: str, inbox_id: str, cards: list[dict], mark: int) -> int:
    """One row per waiting card of a parked thread. Returns the rows written (0 = nothing to park on)."""
    ensure_table()
    n = 0
    with session() as s:
        for c in cards:
            dup = s.scalars(select(TurnCardPark).where(TurnCardPark.thread_id == thread,
                                                       TurnCardPark.card_kind == c["kind"],
                                                       TurnCardPark.card_id == c["id"],
                                                       TurnCardPark.status == WAITING).limit(1)).first()
            if dup is not None:
                dup.mark = int(mark or 0)
                n += 1
                continue
            s.add(TurnCardPark(thread_id=thread[:160], conversation_id=conversation_id, tenant_id=tenant or "",
                               inbox_id=(inbox_id or "")[:40], card_kind=c["kind"], card_id=c["id"],
                               tool_use_id=str(c.get("tool_use_id") or "")[:120], tool=str(c.get("tool") or "")[:120],
                               args_hash=str(c.get("args_hash") or "")[:64], title=str(c.get("title") or "")[:200],
                               mark=int(mark or 0)))
            n += 1
    if n:
        STATS["parked"] += 1
        STATS["cards"] += n
        bind_loop()
        if inbox_id:
            try:                                   # the turn row is honest: it waits for her tap
                from .. import turn_inbox
                turn_inbox.mark(inbox_id, "waiting_tap")
            except Exception:   # noqa: BLE001
                log.debug("inbox waiting mark failed", exc_info=True)
    return n


def parked_inbox(inbox_id: str | None) -> bool:
    """turn_inbox.run_owned: this inbox row's run parked on a card (the row stays `waiting_tap`, never `done`)."""
    if not inbox_id:
        return False
    try:
        ensure_table()
        with session() as s:
            return s.scalars(select(TurnCardPark.id).where(TurnCardPark.inbox_id == inbox_id,
                                                           TurnCardPark.status.in_((WAITING, ANSWERED, RESUMING)))
                             .limit(1)).first() is not None
    except Exception:   # noqa: BLE001
        return False


def rows(thread: str = "", conversation_id: str = "") -> list[dict]:
    """Tests / diagnostics."""
    ensure_table()
    q = select(TurnCardPark).order_by(TurnCardPark.created_at)
    if thread:
        q = q.where(TurnCardPark.thread_id == thread)
    if conversation_id:
        q = q.where(TurnCardPark.conversation_id == conversation_id)
    with session() as s:
        return [_view(r) for r in s.scalars(q).all()]


def _view(r: TurnCardPark) -> dict:
    return {"id": r.id, "thread": r.thread_id, "conv": r.conversation_id, "tenant": r.tenant_id, "inbox": r.inbox_id,
            "kind": r.card_kind, "card": r.card_id, "tool_use_id": r.tool_use_id, "tool": r.tool,
            "args_hash": r.args_hash, "title": r.title, "status": r.status, "answer": r.answer, "result": r.result,
            "mark": int(r.mark or 0)}


# ---------------------------------------------------------------- her tap (called by the card's own code)

def answered(kind: str, card_id: str, answer: str, result: str = "") -> bool:
    """The card's own code ran her answer (or the card expired). True = a parked graph run waits for this card: it
    resumes and tells the result itself, so the caller must NOT write its own chat line. False = today's behaviour."""
    if not card_id or answer not in ANSWERS or not on():
        return False
    try:
        ensure_table()
        with session() as s:
            r = s.scalars(select(TurnCardPark).where(TurnCardPark.card_kind == kind, TurnCardPark.card_id == card_id,
                                                     TurnCardPark.status == WAITING)
                          .order_by(TurnCardPark.created_at.desc()).limit(1)).first()
            if r is None:
                return False
            rid, thread = r.id, r.thread_id
        new = ANSWERED if answer in WAKES else CLOSED
        with session() as s:            # claim once: exactly one answer wins the row
            won = s.execute(update(TurnCardPark).where(TurnCardPark.id == rid, TurnCardPark.status == WAITING)
                            .values(status=new, answer=answer, result=str(result or "")[:3000],
                                    answered_at=now(), updated_at=now())).rowcount
        if won != 1:
            STATS["lost_race"] += 1
            return False
        STATS["answered"] += 1
        if new == CLOSED:
            STATS["expired" if answer == "expired" else "closed"] += 1
            _kick(_close_if_idle(thread))
            return answer != "replaced"         # expired: the card's own line is said; nothing else needed
        _kick(resume_due(thread))
        return True
    except Exception:   # noqa: BLE001 - a park that cannot be answered never breaks her tap (today's line is said)
        log.exception("card park answer failed")
        return False


def _kick(coro) -> None:
    """Run the coroutine on the server's loop - from the loop itself, or from a tap's worker thread."""
    try:
        lp = asyncio.get_running_loop()
    except RuntimeError:
        lp = None
    if lp is not None:
        t = lp.create_task(coro)
        _TASKS.add(t)
        t.add_done_callback(_TASKS.discard)
        return
    target = _LOOP[0] if _LOOP else None
    if target is not None and not target.is_closed():
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, target)
            _TASKS.add(fut)
            fut.add_done_callback(_TASKS.discard)
            return
        except RuntimeError:
            pass
    coro.close()                     # no loop here: the worker's sweep resumes it (the row says answered)


# ---------------------------------------------------------------- the resume (one ordinary turn of the chat)

def _line(answers: list[dict], waiting: list[dict]) -> str:
    parts = [LINE_PREFIX]
    for a in answers:
        t = a.get("title") or a.get("tool") or "the card"
        res = " ".join(str(a.get("result") or "").split())[:900]
        ans = a.get("answer")
        if ans == "done":
            parts.append(f"She tapped Approve / Send on '{t}' and it RAN: {res or 'done'}. Continue the same job from "
                         "this step. Tell her the real result in one short line, then do what is left.")
        elif ans == "failed":
            parts.append(f"She tapped Approve / Send on '{t}', but it FAILED: {res or 'no reason given'}. Tell her "
                         "plainly that it did not go through and why; do not say it is done. Retry only with a NEW "
                         "card if that is clearly right.")
        elif ans == "declined":
            parts.append(f"She tapped Not now / Cancel on '{t}' - nothing was done. Do NOT do it again and do not "
                         "make a new card for it unless she asks. Say in one short line that it was not done, and "
                         "carry on with the rest of the job if anything is left.")
        else:
            parts.append(f"She tapped Approve on '{t}', but the server stopped while it was running - it MAY or may "
                         "not have gone through. Do not repeat it; tell her to check, and check yourself if a tool "
                         "can.")
    if waiting:
        parts.append("Still waiting for her tap: " + "; ".join(f"'{w.get('title') or w.get('tool')}'"
                                                               for w in waiting[:6]) + ".")
    return " ".join(parts)


def resume_value(answers: list[dict], waiting: list[dict]) -> dict:
    keep = ("id", "kind", "card", "tool_use_id", "tool", "args_hash", "title", "answer", "result")
    return {"answers": [{k: a.get(k) for k in keep} for a in answers],
            "waiting": [{k: w.get(k) for k in ("kind", "card", "title")} for w in waiting]}


async def resume_due(thread: str) -> bool:
    """Resume a parked thread with every answer claimed now. True = a turn ran for it."""
    from . import santosh as S
    from . import turnrun
    ensure_table()
    with session() as s:
        r0 = s.scalars(select(TurnCardPark).where(TurnCardPark.thread_id == thread).limit(1)).first()
        if r0 is None:
            return False
        conv, tenant = r0.conversation_id, r0.tenant_id
    async with _LOCKS[(conv, id(asyncio.get_running_loop()))]:   # one resume of a chat's parks at a time
        for _ in range(int(3600 / 0.25)):       # wait for the chat to be free (her own turn, a job round...)
            if not (turnrun.busy(conv) or S._locks[conv].locked()):
                break
            await asyncio.sleep(0.25)
        with session() as s:
            got = s.scalars(select(TurnCardPark).where(TurnCardPark.thread_id == thread,
                                                       TurnCardPark.status == ANSWERED)
                            .order_by(TurnCardPark.answered_at)).all()
            ids = [r.id for r in got]
        if not ids:
            return False
        with session() as s:
            won = s.execute(update(TurnCardPark).where(TurnCardPark.id.in_(ids), TurnCardPark.status == ANSWERED)
                            .values(status=RESUMING, updated_at=now())).rowcount
        if not won:                             # another resume took them: it tells them
            return False
        with session() as s:
            answers = [_view(r) for r in s.scalars(select(TurnCardPark).where(TurnCardPark.id.in_(ids),
                                                                              TurnCardPark.status == RESUMING)).all()]
            waiting = [_view(r) for r in s.scalars(select(TurnCardPark).where(TurnCardPark.thread_id == thread,
                                                                              TurnCardPark.status == WAITING)).all()]
        value = resume_value(answers, waiting)
        STATS["resumes"] += 1
        tok = PARK_RUN.set((conv, thread, value))
        try:
            await S.run_turn(conv, _line(answers, waiting), tenant_id=tenant, actor="approved:card")
        except Exception:   # noqa: BLE001 - run_turn's own guard already said it in her chat
            log.exception("card park resume turn failed")
        finally:
            try:
                PARK_RUN.reset(tok)
            except ValueError:
                PARK_RUN.set(None)
            with session() as s:
                s.execute(update(TurnCardPark).where(TurnCardPark.id.in_([a["id"] for a in answers]),
                                                     TurnCardPark.status == RESUMING)
                          .values(status=RESUMED, updated_at=now()))
        return True


def take(conversation_id: str):
    """turngraph.run_steps: (thread, value) of the park this run resumes, once; another chat's turn never takes it."""
    v = PARK_RUN.get()
    if not v or v[0] != conversation_id:
        return None
    PARK_RUN.set(None)
    return v[1], v[2]


def thread_over(thread: str) -> None:
    """The parked thread reached END (or could not be resumed): nothing of it waits any more. Waiting rows are closed
    (the card still works, as a plain card), the inbox row is honest again."""
    try:
        ensure_table()
        with session() as s:
            rs = s.scalars(select(TurnCardPark).where(TurnCardPark.thread_id == thread)).all()
            inbox = {r.inbox_id for r in rs if r.inbox_id}
            for r in rs:
                if r.status == WAITING:
                    r.status, r.answer = CLOSED, r.answer or "ended"
        for iid in inbox:
            from .. import turn_inbox
            turn_inbox.mark(iid, "done")
    except Exception:   # noqa: BLE001
        log.exception("card park thread end failed")


async def _close_if_idle(thread: str) -> None:
    """An expired / replaced card: when nothing of its thread waits or is answered any more, the parked thread goes."""
    try:
        with session() as s:
            busy = s.scalars(select(TurnCardPark.id).where(TurnCardPark.thread_id == thread,
                                                           TurnCardPark.status.in_((WAITING, ANSWERED, RESUMING)))
                             .limit(1)).first()
        if busy is not None:
            return
        from ..config import get_settings
        from . import turngraph
        await turngraph.forget_threads(get_settings(), [thread])
        thread_over(thread)
    except Exception:   # noqa: BLE001
        log.exception("card park close failed")


# ---------------------------------------------------------------- the worker's sweep

async def sweep(settings=None) -> int:
    """(1) an answered card whose resume a restart cut is resumed; (2) a card she never tapped within
    `graph_card_park_ttl_h` closes the park (the card itself is untouched); (3) a card decided by another path that
    never told us (no hook) is treated like its own answer."""
    if settings is None:
        from ..config import get_settings
        settings = get_settings()
    if not on(settings):
        return 0
    bind_loop()
    ensure_table()
    n = 0
    stale = now() - timedelta(seconds=60)
    with session() as s:
        # a resume that began but whose process died (resuming, old) goes back to answered once
        s.execute(update(TurnCardPark).where(TurnCardPark.status == RESUMING, TurnCardPark.updated_at < now() -
                                             timedelta(minutes=30)).values(status=ANSWERED))
        due = sorted({r.thread_id for r in s.scalars(select(TurnCardPark).where(
            TurnCardPark.status == ANSWERED, TurnCardPark.answered_at < stale)).all()})
        ttl = float(getattr(settings, "graph_card_park_ttl_h", 26.0) or 0)
        old = s.scalars(select(TurnCardPark).where(TurnCardPark.status == WAITING,
                                                   TurnCardPark.created_at < now() - timedelta(hours=ttl))).all() \
            if ttl > 0 else []
        old = [(r.card_kind, r.card_id) for r in old]
        live = [(r.card_kind, r.card_id, r.title) for r in s.scalars(select(TurnCardPark).where(
            TurnCardPark.status == WAITING)).all()]
    for th in due:
        _kick(resume_due(th))
        n += 1
    for kind, cid in old:
        if answered(kind, cid, "expired", "no tap within the park's time limit"):
            n += 1
    for kind, cid, title in live:               # decided elsewhere (no hook): a card no longer waiting is closed
        if (kind, cid) in old:
            continue
        if not still_waiting({"kind": kind, "id": cid}):
            answered(kind, cid, "replaced", "decided outside the park")
            n += 1
    STATS["swept"] += n
    return n


def forget_old(days: int = 7) -> int:
    ensure_table()
    with session() as s:
        res = s.execute(TurnCardPark.__table__.delete().where(
            TurnCardPark.status.in_((RESUMED, CLOSED)), TurnCardPark.updated_at < now() - timedelta(days=days)))
        return int(getattr(res, "rowcount", 0) or 0)


def declined_guard(declined: list) -> Any:
    """The ledger runner's check: a tool_use with the same tool + arguments as a card she declined is refused."""
    keys = {(str(d.get("tool") or ""), str(d.get("args_hash") or "")) for d in declined or [] if d}

    def check(name: str, ahash: str) -> str:
        if (name, ahash) in keys:
            STATS["declined_guard"] += 1
            return (f"She tapped Not now on this exact {name} card earlier in this job - it is NOT done again. "
                    "Do not retry it unless she asks for it now.")
        return ""
    return check
