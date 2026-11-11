"""Seekhe hue kaam (idea from Hermes Agent): when Hoola finishes a task that took several steps, it keeps the way it did
it as a named procedure (tools in order, what went wrong on the way). Next time a similar request comes, the procedure
goes into the prompt as a hint, so the job is done faster and with fewer wrong turns.

What is stored: the owner's request with digits masked (to match similar requests later), the tool names and their plain
labels, and short notes about failures. Never tool inputs or outputs. One owner's procedures are never used for another.
The owner sees every procedure (Profile > Seekhe hue kaam) and can switch one off or delete it. A procedure that keeps
failing switches itself off."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.procedures")
MIN_CALLS = 4          # a turn needs at least this many tool calls ...
MIN_TOOLS = 2          # ... using at least this many different tools, to be worth keeping
MAX_PER_OWNER = 200
MATCH_FLOOR = 0.55     # semantic score to use a procedure as a hint
SAME_FLOOR = 0.80      # this close = the same procedure (updated, not duplicated)
SKIP_TOOLS = {"remember", "forget", "memory_search", "employee", "procedures"}
STATS = {"learned": 0, "updated": 0, "hinted": 0}


class Procedure(Base):
    __tablename__ = "procedures"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(Text, default="")          # the request(s) it came from, digits masked
    steps: Mapped[str] = mapped_column(Text, default="[]")          # [{"tool", "label"}]
    watch_out: Mapped[str] = mapped_column(Text, default="[]")      # short notes about what failed on the way
    uses: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    fails: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _mask(text: str, n: int = 240) -> str:
    t = re.sub(r"\d{3,}", lambda m: "#" * len(m.group()), str(text or ""))
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", t)
    return re.sub(r"\s+", " ", t).strip()[:n]


def _request(text: str) -> str:
    """The owner's own words: without "[Automatic job ...]" style notes in front."""
    return re.sub(r"^(\s*\[[^\]]*\]\s*)+", "", str(text or "")).strip()


def _title(text: str) -> str:
    t = _mask(_request(text), 200)
    t = re.split(r"[\n.?!]", t)[0].strip(" ,")
    return (t[:1].upper() + t[1:])[:80] or "Task"


def _j(v: str, default):
    try:
        return json.loads(v) if v else default
    except Exception:
        return default


def view(p: Procedure) -> dict[str, Any]:
    return {"id": p.id, "title": p.title, "when": p.trigger.split("\n")[0][:200], "steps": _j(p.steps, []),
            "watch_out": _j(p.watch_out, []), "uses": p.uses, "wins": p.wins, "fails": p.fails, "active": p.active,
            "created_at": p.created_at.isoformat(), "used_at": p.used_at.isoformat() if p.used_at else None}


def _active(tenant: str) -> list[Procedure]:
    with session() as s:
        rows = s.scalars(select(Procedure).where(Procedure.tenant_id == tenant, Procedure.active.is_(True))).all()
        for r in rows:
            s.expunge(r)
        return list(rows)


def _match(tenant: str, text: str, floor: float) -> list[tuple[Procedure, float]]:
    from . import semantic
    rows = _active(tenant)
    if not rows or not (text or "").strip():
        return []
    by = {r.id: r for r in rows}
    ranked = semantic.rank(_mask(_request(text), 400), [(r.id, f"{r.title}. {r.trigger}") for r in rows], top=3, floor=floor)
    if not semantic.available():          # word overlap: demand more than half of the words
        # wave 11: and never LESS than the floor asked for - "the same procedure" (0.80) collapsed to 0.5 here, so a
        # different ask sharing half its words overwrote an existing procedure's steps
        ranked = [x for x in ranked if x[2] >= max(0.5, float(floor))]
    return [(by[i], score) for i, _, score in ranked]


# ---------------------------------------------------------------- using them
_STOPWORDS = {"haan", "han", "ha", "ji", "ok", "okay", "theek", "thik", "hai", "kar", "karo", "do", "de", "dijiye", "bhej",
              "bhejo", "aage", "badho", "chalo", "yes", "sure", "nahi", "mat", "ruko", "please", "plz", "the", "a", "to"}


def _too_short(text: str) -> bool:
    """wave 11: a bare yes / no / carry-on ("Haan bhej do", "theek hai", "aage badho") is not a job to learn from or to
    match: the yes-turn runs the tools, so a procedure titled "Haan bhej do" was learned and then hinted on every later
    yes (score 0.79 against "haan theek hai")."""
    t = _request(text or "").lower()
    words = [w for w in re.findall(r"[a-z\u0900-\u097f]+", t) if w not in _STOPWORDS]
    if len(words) < 3:
        return True
    try:
        from . import approval_words
        return bool(approval_words.is_pure_approval(t))
    except Exception:   # noqa: BLE001
        return False


def hint(tenant: str, user_text: str, limit: int = 2) -> tuple[str, list[str]]:
    """Prompt block with the best matching procedures, and their ids (to score them after the turn)."""
    if _too_short(user_text):
        return "", []
    found = _match(tenant, user_text, MATCH_FLOOR)[:limit]
    if not found:
        return "", []
    lines = ["\n\nLearned tasks (you did this kind of work this way before; for help only, change it if needed, "
             "and always follow what the user said just now):"]
    for p, _ in found:
        steps = " -> ".join(s.get("label") or s.get("tool") for s in _j(p.steps, []))
        lines.append(f"- {p.title}: {steps}")
        for w in _j(p.watch_out, [])[:3]:
            lines.append(f"  watch out: {w}")
    STATS["hinted"] += len(found)
    return "\n".join(lines), [p.id for p, _ in found]


# ---------------------------------------------------------------- learning
def after_turn(tenant: str, user_text: str, calls: list[dict[str, Any]], used: list[str], ok: bool,
               actor: str = "owner") -> dict[str, Any] | None:
    """Called once per finished agent turn. calls = [{"tool", "ok", "error"}] in order. Returns what was learned."""
    try:
        return _after_turn(tenant, user_text, calls, used, ok, actor)
    except Exception:
        log.exception("procedure learning failed")
        return None


def _after_turn(tenant, user_text, calls, used, ok, actor):
    with session() as s:
        for pid in used:                                  # score the hints that were in the prompt
            p = s.get(Procedure, pid)
            if p is None or p.tenant_id != tenant:
                continue
            p.uses += 1
            p.used_at = now()
            if ok:
                p.wins += 1
            else:
                p.fails += 1
                if p.fails >= 3 and p.fails > p.wins:
                    p.active = False                      # keeps failing: switched off, the owner can turn it on again
    if not ok or actor not in ("owner", "routine") or _too_short(user_text):
        return None
    real = [c for c in calls if c.get("tool") not in SKIP_TOOLS and not str(c.get("tool", "")).startswith("biz_")]
    good = [c for c in real if c.get("ok")]
    if len(real) < MIN_CALLS or len({c["tool"] for c in good}) < MIN_TOOLS or len(good) < len(real) / 2:
        return None
    from .agent.tools import TOOL_LABELS

    def label_for(tool: str) -> str:
        from . import lang as _lang
        return _lang.label(tool)
    steps, seen = [], set()
    for c in good:                                         # each tool once, in the order it first worked
        if c["tool"] in seen:
            continue
        seen.add(c["tool"])
        steps.append({"tool": c["tool"], "label": label_for(c["tool"])})
    watch = []
    for c in real:
        if not c.get("ok") and c.get("error"):
            w = f"{label_for(c['tool'])}: {_mask(c['error'], 120)}"
            if w not in watch:
                watch.append(w)
    trigger = _mask(_request(user_text), 240)
    same = _match(tenant, user_text, SAME_FLOOR)
    if same:
        with session() as s:
            p = s.get(Procedure, same[0][0].id)
            if not p.edited:
                p.steps = json.dumps(steps, ensure_ascii=False)
            old = _j(p.watch_out, [])
            p.watch_out = json.dumps((old + [w for w in watch if w not in old])[-5:], ensure_ascii=False)
            if trigger and trigger not in p.trigger and p.trigger.count("\n") < 4:
                p.trigger = p.trigger + "\n" + trigger
            STATS["updated"] += 1
            return {"updated": p.id, "title": p.title}
    with session() as s:
        n = s.scalar(select(func.count()).select_from(Procedure).where(Procedure.tenant_id == tenant)) or 0
        if n >= MAX_PER_OWNER:                             # make room: drop the least useful one
            worst = s.scalars(select(Procedure).where(Procedure.tenant_id == tenant)
                              .order_by(Procedure.wins, Procedure.uses, Procedure.created_at)).first()
            if worst is not None:
                s.delete(worst)
        p = Procedure(tenant_id=tenant, title=_title(user_text), trigger=trigger,
                      steps=json.dumps(steps, ensure_ascii=False), watch_out=json.dumps(watch[:5], ensure_ascii=False))
        s.add(p)
        s.flush()
        STATS["learned"] += 1
        return {"learned": p.id, "title": p.title}


# ---------------------------------------------------------------- the owner's controls
class ProcedureError(Exception):
    pass


def listing(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(Procedure).where(Procedure.tenant_id == tenant)
                         .order_by(Procedure.active.desc(), Procedure.wins.desc(), Procedure.created_at.desc())).all()
        return [view(p) for p in rows]


def update(tenant: str, pid: str, active: bool | None = None, title: str | None = None,
           steps: list[str] | None = None) -> dict[str, Any]:
    with session() as s:
        p = s.get(Procedure, pid)
        if p is None or p.tenant_id != tenant:
            raise ProcedureError("This learned task was not found.")
        if active is not None:
            p.active = bool(active)
            if active:
                p.fails = 0
        if title is not None:
            t = re.sub(r"\s+", " ", str(title)).strip()[:80]
            if not t:
                raise ProcedureError("The name cannot be empty.")
            p.title = t
        if steps is not None:                              # the owner rewrote the steps in her own words
            clean = [re.sub(r"\s+", " ", str(x)).strip()[:120] for x in steps if str(x).strip()][:12]
            if not clean:
                raise ProcedureError("Write at least one step.")
            p.steps = json.dumps([{"tool": "", "label": x} for x in clean], ensure_ascii=False)
            p.edited = True
        return view(p)


def record_run(tenant: str, pid: str, ok: bool, undo_win: bool = False) -> dict[str, Any]:
    """v0.745 her own verdict after a real run from the Video Learner: worked = a win, wrong = a fail.
    v0.785 undo_win: the run was already counted as a win by the operator's own finish and she says it was wrong."""
    with session() as s:
        p = s.get(Procedure, pid)
        if p is None or p.tenant_id != tenant:
            raise ProcedureError("This learned task was not found.")
        if undo_win:
            p.wins = max(0, int(p.wins or 0) - 1)
        else:
            p.uses += 1
        if ok:
            p.wins += 1
        else:
            p.fails += 1
        return view(p)


def delete(tenant: str, pid: str) -> None:
    with session() as s:
        p = s.get(Procedure, pid)
        if p is None or p.tenant_id != tenant:
            raise ProcedureError("This learned task was not found.")
        s.delete(p)


def forget_all(tenant: str) -> int:
    with session() as s:
        rows = s.scalars(select(Procedure).where(Procedure.tenant_id == tenant)).all()
        for r in rows:
            s.delete(r)
        return len(rows)


def save_video(tenant: str, title: str, trigger: str, steps: list[dict[str, Any]],
               watch_out: list[str] | None = None) -> dict[str, Any]:
    """v0.713 SEEKH MANCH: a way of working learned by WATCHING a video (seekh.py), kept exactly like a
    learned procedure so hint() offers it on the next similar ask. Unproven by definition: wins come only
    from real runs (after_turn scores them like any other procedure)."""
    clean = [s for s in (steps or []) if isinstance(s, dict) and str(s.get("label") or "").strip()][:12]
    if not clean:
        raise ProcedureError("No step worth saving was found in the video.")
    with session() as s:
        n = s.scalar(select(func.count()).select_from(Procedure).where(Procedure.tenant_id == tenant)) or 0
        if n >= MAX_PER_OWNER:                             # make room: drop the least useful one
            worst = s.scalars(select(Procedure).where(Procedure.tenant_id == tenant)
                              .order_by(Procedure.wins, Procedure.uses, Procedure.created_at)).first()
            if worst is not None:
                s.delete(worst)
        p = Procedure(tenant_id=tenant, title=_title(title or "Task learned from a video"),
                      trigger=_mask(_request(trigger), 240),
                      steps=json.dumps(clean, ensure_ascii=False),
                      watch_out=json.dumps([str(w)[:200] for w in (watch_out or [])[:8]], ensure_ascii=False))
        s.add(p)
        s.flush()
        STATS["learned"] += 1
        return view(p)
