"""v0.649 SACH MEIN ROKO: "cancel this task" really cancels it - on a call, the phone chat and the console chat.

Owner (7 Nov 2026): "IF I TELL ON VOICE CANCLE THIS TASK.... IT SAYS I HAVE CANCLED IT ... STILL WHEN I HAVE COME BACK ON
VOICE IT TELL ... I AM WORKING ON THAT".

Why it happened (read from the code): there was NO cancel tool - only the chat's Stop button (`santosh.stop`) and a few
per-kind stops nobody on a call could reach. Her "cancel karo" went to the brain as a new ask on the SAME conversation,
so it waited behind the very job it should stop; the brain had nothing to run and said "cancel kar diya" anyway; the job
tracker, the long-job plan and the restart inbox all still said "running", so the next call said "kaam chal raha hai".

Now:
  * `wants_stop(text)` spots a stop ask in code (Hinglish + English, a short sentence, never a reminder / meeting / light
    / the call itself). `santosh._run_turn` asks `cancel()` BEFORE taking the conversation lock, so the stop never
    queues behind the job.
  * `cancel()` finds what is running for her in EVERY conversation (chats and call records): running turns (a call's
    santosh_kaam job, a chat job, a long-job round) and tracked jobs (website, app, browser job, research, long job...).
    Her words pick one ("website wala"); bare "cancel karo" = the newest one; "sab" = all. Words that name something
    that is not running -> nothing is touched (the brain handles it: a draft, a booking...).
  * For each one it calls the REAL stop (the turn's Stop, the kind's own stop) and writes the truth everywhere: the job
    row -> stopped + "cancelled" (kaamwatch keeps it stopped even if a late event arrives, and never announces it), its
    pending result report -> skipped, the restart inbox -> stopped (a restart never re-runs it), the long job -> stopped.
  * The reply is built from what really stopped - never "cancel kar diya" for something that was not stopped.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from .db import session

log = logging.getLogger("santosh.kaamstop")
STATS: dict[str, int] = {"asked": 0, "stopped": 0, "nothing": 0, "unmatched": 0}
_RECENT: dict[str, float] = {}        # conversation -> when a job there was cancelled (late news of it is dropped)
RECENT_S = 1800

_VERB = re.compile(r"\b(cancel|cancle|cansel|kancel|cancell?\s*kar\w*|roko|rok\s*do|rok\s*de|rok\s*dijiye|rok\s*dena|"
                   r"ruk\s*jao|ruko|band\s*kar\w*|band\s*kijiye|band\s*karo|stop|rehne\s*do|rahne\s*do|mat\s*karo|"
                   r"chhod\s*do|chod\s*do|chhodo|abort|nahi\s*karna)\b", re.I)
# a stop of something that is not a job: those go to their own tools / the call itself
_NOT_JOB = re.compile(r"\b(reminder|alarm|timer|meeting|event|appointment|booking|order|subscription|routine|"
                      r"light|lights|bulb|fan|pankha|ac|tv|geyser|music|gaana|gana|song|awaaz|volume|call|phone|"
                      r"baat|recording|notification|draft)\b", re.I)
_FILLER = {
    "yeh", "ye", "yah", "wo", "woh", "vo", "voh", "is", "us", "isko", "usko", "ise", "use", "iska", "uska", "kaam",
    "kam", "task", "job", "work", "wala", "wali", "wale", "ko", "please", "plz", "pls", "abhi", "turant", "jaldi", "na",
    "bhai", "ji", "hoola", "santosh", "mera", "meri", "mere", "jo", "maine", "mai", "main", "diya", "diye", "tha", "thi",
    "the", "bola", "kaha", "this", "that", "it", "the", "a", "an", "my", "karo", "kar", "do", "de", "dijiye", "dena",
    "please", "now", "right", "and", "aur", "bhi", "hi", "hai", "ho", "raha", "rahi", "chal", "chalu", "wapas", "sab",
    "saare", "sare", "sabhi", "all", "everything", "every", "pura", "poora", "puri", "poori", "ek", "second", "dekho",
    "okay", "ok", "acha", "achha", "theek", "thik", "haan", "han", "nahi", "mat", "band", "stop", "cancel", "roko",
    "rok", "ruk", "jao", "rehne", "rahne", "chhod", "chod", "chhodo", "abort", "kijiye", "karna", "cancle", "cansel",
}
_ALL = re.compile(r"\b(sab|saare|sare|sabhi|all|everything)\b", re.I)


def wants_stop(text: str) -> bool:
    """A short ask to stop / cancel work (not a reminder, a meeting, a device or the call)."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t or t.startswith(("[", "(")) or len(t.split()) > 14:
        return False
    return bool(_VERB.search(t)) and not _NOT_JOB.search(t)


def _content(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Zऀ-ॿ]+", str(text or "").lower())
    return [w for w in words if len(w) >= 3 and w not in _FILLER and not _VERB.fullmatch(w)]


def _utc(d: datetime | None) -> datetime:
    if d is None:
        return datetime.now(timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _her_convs(tenant: str) -> set[str]:
    from .db import Conversation
    with session() as s:
        return set(s.scalars(select(Conversation.id).where(Conversation.tenant_id == tenant)).all())


def _running_turns(tenant: str, skip: str = "") -> list[dict[str, Any]]:
    """Her conversations where a turn is working right now, with what she asked for it (the restart inbox row)."""
    from .agent import santosh
    locked = [c for c, lk in list(santosh._locks.items()) if c != skip and lk.locked()]
    if not locked:
        return []
    mine = _her_convs(tenant)
    out = []
    for c in locked:
        if c not in mine:
            continue
        # a turn whose ask is unknown ranks BELOW every named job (bare "cancel karo" means the job she can name)
        what, at = "", datetime(2000, 1, 1, tzinfo=timezone.utc)
        try:
            from . import turn_inbox
            turn_inbox.ensure_table()
            with session() as s:
                r = s.scalars(select(turn_inbox.TurnInbox).where(turn_inbox.TurnInbox.conversation_id == c,
                                                                 turn_inbox.TurnInbox.status.in_(("accepted", "running")))
                              .order_by(turn_inbox.TurnInbox.created_at.desc())).first()
                if r is not None:
                    what, at = r.text or "", _utc(r.created_at)
        except Exception:
            log.debug("inbox read failed", exc_info=True)
        out.append({"type": "turn", "conversation_id": c, "title": re.sub(r"\s+", " ", what).strip()[:140] or "work in progress",
                    "label": "Kaam", "at": at})
    return out


def _tracked(tenant: str) -> list[dict[str, Any]]:
    from .kaamwatch import KaamJob
    cut = datetime.now(timezone.utc) - timedelta(days=2)
    with session() as s:
        rows = s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.state.in_(("working", "waiting")),
                                               KaamJob.updated_at >= cut).order_by(KaamJob.updated_at.desc())).all()
        return [{"type": "job", "key": r.key, "kind": r.kind, "label": r.label, "title": r.title or r.label,
                 "conversation_id": r.conversation_id or "", "at": _utc(r.updated_at)} for r in rows]


def _pc_tasks(tenant: str, have: set[str]) -> list[dict[str, Any]]:
    """v0.836 DESKTOP TEAM: every task working on one of her PCs (or Hoola's own PCs) right now, even when its
    watch row was never written - so 'band karo' reaches the PC itself, not only the list."""
    try:
        from .pc import operator as pcop
        ops = pcop.running_all(tenant)
    except Exception:
        return []
    out = []
    for o in ops:
        key = f"browser:{o.id}"
        if key in have:
            continue
        where = o.device_name or ("Hoola PC" if o.kind else "your PC")
        what = re.sub(r"\s+", " ", o.task).strip()[:100]
        out.append({"type": "job", "key": key, "kind": "browser", "label": "PC job",
                    "title": f"{where}: {what}",
                    "conversation_id": o.conv or "", "at": datetime.fromtimestamp(o.created, timezone.utc)})
    return out


def running(tenant: str, skip_turn: str = "") -> list[dict[str, Any]]:
    """Everything she could cancel now, newest first."""
    items = _tracked(tenant)
    items += _pc_tasks(tenant, {x["key"] for x in items})
    items += _running_turns(tenant, skip_turn)
    items.sort(key=lambda x: x["at"], reverse=True)
    return items


def _pick(items: list[dict[str, Any]], words: str) -> tuple[list[dict[str, Any]], str]:
    if not items:
        return [], "nothing"
    if _ALL.search(words or ""):
        return items, "all"
    want = _content(words)
    if want:
        def hits(x: dict[str, Any]) -> bool:
            blob = (x["title"] + " " + x["label"] + " " + x.get("kind", "")).lower()
            toks = _content(blob)
            return any(w in blob or any(w in t or t in w for t in toks) for w in want)
        hit = [x for x in items if hits(x)]
        return (hit, "named") if hit else ([], "unmatched")
    return [items[0]], "newest"


def _native_stop(tenant: str, kind: str, jid: str, conv: str) -> bool:
    """The kind's own stop, where it has one. False = nothing to call (the row + turn stop still hold)."""
    try:
        if kind == "goal":
            from .agent import goal as _goal
            _goal.mark_stopped(conv)
            return True
        if kind == "site_board":
            from .site import service as S
            S.stop(tenant, jid)
            return True
        if kind in ("app_board", "app_android", "app_ios"):
            from .appmaker import service as A
            A.stop(tenant, jid)
            return True
        if kind == "browser" and jid.startswith("pcop_"):   # v0.836 a task on one of her PCs really stops there
            from .pc import operator as pcop
            return bool(pcop.stop(tenant, jid))
        if kind == "operator_task":
            from .operator import service as O
            O.cancel(tenant, jid)
            return True
        if kind == "agent_team":   # CALL PAR TEAM: "agents band karo" really stops a background crew
            from .agent import team as _team
            return _team.stop_team(tenant, jid)
        if kind == "research_run":
            from .research import runner as R
            R.stop(tenant, jid)
            return True
    except Exception:
        log.warning("native stop for %s:%s failed", kind, jid, exc_info=True)
    return False


def _mark_row(tenant: str, key: str) -> None:
    from .kaamwatch import KaamJob, _MEM
    with session() as s:
        for r in s.scalars(select(KaamJob).where(KaamJob.tenant_id == tenant, KaamJob.key == key)).all():
            r.state, r.status, r.told = "stopped", "cancelled", "stopped"
            r.updated_at = r.moved_at = datetime.now(timezone.utc)
    try:
        if tenant in _MEM and key in _MEM[tenant]:
            _MEM[tenant][key]["state"] = "stopped"
    except Exception:
        pass
    try:
        from . import kaam_followup as F
        F.ensure_table()
        with session() as s:
            for r in s.scalars(select(F.KaamFollowup).where(F.KaamFollowup.tenant_id == tenant, F.KaamFollowup.key == key,
                                                            F.KaamFollowup.status == "pending")).all():
                r.status = "skipped"
    except Exception:
        log.debug("followup skip failed", exc_info=True)


def _stop_turn(conv: str) -> None:
    from .agent import santosh
    santosh.stop(conv)                     # the Stop button: running model / tool call ends, the long job stops
    try:
        from . import turn_inbox
        turn_inbox.ensure_table()
        with session() as s:
            for r in s.scalars(select(turn_inbox.TurnInbox).where(turn_inbox.TurnInbox.conversation_id == conv,
                                                                  turn_inbox.TurnInbox.status.in_(("accepted", "running")))).all():
                r.status = "stopped"       # a server restart never re-runs a cancelled job
    except Exception:
        log.debug("inbox stop failed", exc_info=True)


def recently_cancelled(conv: str) -> bool:
    """A job in this conversation was cancelled in the last half hour (its late news must not be spoken / told)."""
    t = _RECENT.get(conv or "")
    return bool(t and time.monotonic() - t < RECENT_S)


def cancel(tenant: str, words: str = "", here: str = "", skip_turn: str = "") -> dict[str, Any]:
    """Stop what she means. `skip_turn` = a conversation whose running turn must NOT be stopped (the tool's own turn)."""
    STATS["asked"] += 1
    items = running(tenant, skip_turn)
    picked, how = _pick(items, words)
    if not picked:
        STATS["nothing" if how == "nothing" else "unmatched"] += 1
        return {"stopped": [], "how": how, "left": [x["title"] for x in items][:5],
                "say": ("Nothing is running right now that I could stop." if how == "nothing" else "")}
    done, partial = [], []
    turns_done: set[str] = set()
    job_convs = {x.get("conversation_id") for x in picked if x["type"] == "job"}
    for x in picked:
        conv = x.get("conversation_id") or ""
        if x["type"] == "turn":
            if conv and conv not in turns_done:
                _stop_turn(conv)
                turns_done.add(conv)
            if conv not in job_convs:           # the turn driving a named job is that job: say its name once
                done.append(x["title"])
        else:
            jid = x["key"].split(":", 1)[1] if ":" in x["key"] else x["key"]
            _mark_row(tenant, x["key"])          # first: its own "stopped" event then finds it cancelled (no second line)
            native = _native_stop(tenant, x["kind"], jid, conv)
            if conv and conv not in turns_done:
                from .agent import santosh
                if santosh.turn_running(conv) and conv != skip_turn:
                    _stop_turn(conv)
                    turns_done.add(conv)
            # no own stop = the row and the turn are stopped, but a worker / outside build may still finish: said plainly
            (done if native else partial).append(f"{x['label']} {x['title']}".strip())
        if conv:
            _RECENT[conv] = time.monotonic()
    if here:
        _RECENT[here] = time.monotonic()
    STATS["stopped"] += len(picked)
    left = [x["title"] for x in items if x not in picked][:3]
    names = "; ".join(done + partial)
    say = f"Okay, stopped: {names}."
    if partial:
        say += (" The part of it that was already running may finish on its own; I will not do anything more on it "
                "and will not report back on it.")
    try:   # wave 13: her avatar's own forms ("nahi karungi" for a female avatar)
        from .avatar.service import gendered, persona
        say = gendered(say, persona(tenant)[1])
    except Exception:
        pass
    if left:
        say += " Still running: " + "; ".join(left) + "."
    log.info("kaam cancelled for %s (%s): %s", tenant, how, names)
    return {"stopped": done + partial, "how": how, "left": left, "say": say}
