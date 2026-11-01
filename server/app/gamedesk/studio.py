"""v0.386 STUDIO PROJECT (Hoola Game Engine plan, Phase 2): a game that lives for weeks, months or 1,000 days.

A Studio Project wraps one Game Desk game (gamedesk/service.py keeps the code, the versions and the play link) and adds
what a real studio runs on:
- a TASK BOARD (todo -> working -> review -> done, plus blocked / dropped): every task is ONE small change, built by
  the same pipeline as Phase 1 (code -> guard -> headless play -> Web export -> Hoola plays it); a task that builds
  waits for HER OK; her "wapas" sends it back and the version before it is live again;
- MILESTONES (Prototype -> First playable -> Alpha -> Beta -> Release) with progress counted in code;
- a DECISIONS LOG (what was chosen and why) that Hoola reads before planning and answers "why is X like this?" from;
- a NIGHTLY BUILD: the live version's code is built and played again from scratch with no model call; a failure or a
  big fps drop names the tasks since the last good night;
- a MORNING SUMMARY in her chat (yesterday, waiting for her, stuck, last night, today, milestone %), written in code.

Precision rules (in code, not in a prompt): one task builds at a time; a new task never starts while another waits
for her OK (so "wapas" always undoes exactly one task); a failed task never replaces the live version; every version
records the task it came from and its code fingerprint. Nothing is published and no money is spent; GitHub only by
her tap on the usual card (gamedesk/github.py)."""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import crew as C
from . import service as G

log = logging.getLogger("santosh.gamedesk")

MILESTONES = [{"key": "proto", "name": "Prototype", "target": ""}, {"key": "playable", "name": "First playable", "target": ""},
              {"key": "alpha", "name": "Alpha", "target": ""}, {"key": "beta", "name": "Beta", "target": ""},
              {"key": "release", "name": "Release", "target": ""}]
TASK_STATES = ("todo", "working", "review", "done", "blocked", "dropped")
KINDS = ("feature", "content", "polish", "fix", "test")
OPEN = ("todo", "working", "review", "blocked")
MAX_TASKS = 2000
MAX_STUDIOS = 20
NIGHT_HOURS = (1, 5)          # local time window for the nightly build
FPS_DROP = 0.25               # a nightly fps drop of more than 25 % vs the last good night is reported


class StudioError(G.GameError):
    pass


class GameStudio(Base):
    __tablename__ = "game_studios"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(120), default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    game_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    milestones: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(12), default="active")      # active | paused | archived
    auto: Mapped[bool] = mapped_column(Boolean, default=True)              # after her OK, start the next task alone
    nightly_on: Mapped[bool] = mapped_column(Boolean, default=True)
    summary_on: Mapped[bool] = mapped_column(Boolean, default=True)
    summary_hour: Mapped[int] = mapped_column(Integer, default=9)
    last_summary: Mapped[str] = mapped_column(String(10), default="")      # local date of the last morning summary
    nightly: Mapped[list] = mapped_column(JSON, default=list)              # last 30 nightly results
    gates: Mapped[list | None] = mapped_column(JSON, nullable=True)        # v0.406 milestone gate checks (advisory)
    qa: Mapped[list | None] = mapped_column(JSON, nullable=True)           # v0.415 QA farm reports (last 12)
    platform: Mapped[dict | None] = mapped_column(JSON, nullable=True)     # v0.415 {package (never changes), version_code}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GameTask(Base):
    __tablename__ = "game_tasks"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(12), default="feature")
    milestone: Mapped[str] = mapped_column(String(24), default="proto")
    priority: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(String(12), default="todo")
    source: Mapped[str] = mapped_column(String(12), default="her")          # her | hoola | nightly
    version: Mapped[int] = mapped_column(Integer, default=0)                # the game version this task made
    base: Mapped[int] = mapped_column(Integer, default=0)                   # the live version it was built on
    notes: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    tries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # v0.406 Hoola Game Crew: who does it, how "done" is checked, and the lead's review
    role: Mapped[str] = mapped_column(String(32), default="")
    criteria: Mapped[list | None] = mapped_column(JSON, nullable=True)
    review: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class GameDecision(Base):
    __tablename__ = "game_decisions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    why: Mapped[str] = mapped_column(Text, default="")
    task: Mapped[str] = mapped_column(String(16), default="")
    by: Mapped[str] = mapped_column(String(12), default="her")               # her | hoola
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()
_NIGHT_LOCK = threading.Lock()


def ensure_tables() -> None:
    from .. import db as _db
    G.ensure_table()
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in (GameStudio, GameTask, GameDecision):
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _utc(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _clean(v: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


# ---------------------------------------------------------------- loading
def _studio(s, tenant: str, ref: str) -> GameStudio:
    ensure_tables()
    r = s.get(GameStudio, ref)
    if r is None:
        r = s.scalars(select(GameStudio).where(GameStudio.tenant_id == tenant, GameStudio.number == str(ref or "").upper())).first()
    if r is None or r.tenant_id != tenant:
        raise StudioError("Yeh studio project nahi mila.")
    return r


def _task(s, tenant: str, ref: str, studio_id: str = "") -> GameTask:
    t = s.get(GameTask, ref)
    if t is None and studio_id:
        t = s.scalars(select(GameTask).where(GameTask.studio_id == studio_id, GameTask.number == str(ref or "").upper())).first()
    if t is None or t.tenant_id != tenant:
        raise StudioError("Yeh task nahi mila.")
    return t


def _tasks(s, sid: str) -> list[GameTask]:
    return list(s.scalars(select(GameTask).where(GameTask.studio_id == sid).order_by(GameTask.created_at)).all())


def _game(tenant: str, gid: str) -> G.GameProject | None:
    try:
        return G._get(tenant, gid)
    except G.GameError:
        return None


# ---------------------------------------------------------------- views
def task_view(t: GameTask) -> dict[str, Any]:
    role = t.role or C.pick_role(t.title, t.detail, t.kind)
    r = C.ROLES.get(role) or {}
    crit = list(t.criteria or [])
    return {"id": t.id, "number": t.number, "title": t.title, "detail": t.detail, "kind": t.kind, "milestone": t.milestone,
            "priority": t.priority, "status": t.status, "source": t.source, "version": t.version, "base": t.base,
            "notes": t.notes, "error": t.error, "tries": t.tries,
            "role": role, "role_name": r.get("name", ""), "role_mode": r.get("mode", "builds"),
            "reviewer": C.reviewer(role), "criteria": crit, "verdict": C.verdict(crit), "review": t.review or {},
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None}


def progress(milestones: list[dict], tasks: list[GameTask]) -> list[dict[str, Any]]:
    out = []
    for m in milestones:
        mine = [t for t in tasks if t.milestone == m["key"] and t.status != "dropped"]
        done = sum(1 for t in mine if t.status == "done")
        out.append({**m, "total": len(mine), "done": done, "pct": round(100 * done / len(mine)) if mine else 0})
    return out


def current_milestone(prog: list[dict]) -> str:
    for m in prog:
        if m["total"] and m["done"] < m["total"]:
            return m["key"]
    return next((m["key"] for m in prog if not m["total"]), prog[-1]["key"] if prog else "")


def view(r: GameStudio, full: bool = False) -> dict[str, Any]:
    with session() as s:
        tasks = _tasks(s, r.id)
        for t in tasks:
            s.expunge(t)
        decs = list(s.scalars(select(GameDecision).where(GameDecision.studio_id == r.id)
                              .order_by(GameDecision.at.desc()).limit(200 if full else 5)).all())
        for d in decs:
            s.expunge(d)
    g = _game(r.tenant_id, r.game_id)
    gv = G.view(g) if g else {}
    prog = progress(r.milestones or MILESTONES, tasks)
    counts = {k: sum(1 for t in tasks if t.status == k) for k in TASK_STATES}
    d: dict[str, Any] = {
        "id": r.id, "number": r.number, "title": r.title, "goal": r.goal, "status": r.status, "auto": r.auto,
        "nightly_on": r.nightly_on, "summary_on": r.summary_on, "summary_hour": r.summary_hour,
        "milestones": prog, "milestone": current_milestone(prog), "counts": counts,
        "game": {k: gv.get(k) for k in ("id", "number", "title", "status", "say", "stage", "pct", "error", "play_url",
                                        "version", "design", "shots", "numbers")} if gv else {},
        "night": (r.nightly or [])[-1] if r.nightly else {},
        "bible": _bible_line(r),
        "assets": _assets_line(r),
        "qa": _qa_line(r),
        "created_at": r.created_at.isoformat() if r.created_at else None}
    live_src = ((G._good(g) or [{}])[-1].get("src", "")) if g else ""
    if full:
        d["tasks"] = [task_view(t) for t in tasks]
        for tv in d["tasks"]:                          # evidence older than the code (a later change / restore)
            tv["evidence_old"] = bool(tv["status"] == "review" and live_src and any(
                (c.get("evidence") or {}).get("src") not in (None, "", live_src) for c in tv["criteria"]))
        d["crew"] = {"count": len(C.ROLES), "busy": sorted({t.role for t in tasks if t.role and t.status in OPEN}),
                     "teams": [{"key": k, "name": v["name"]} for k, v in C.TEAMS.items()]}
        d["gates"] = list(reversed((r.gates or [])[-10:]))
        d["decisions"] = [{"id": x.id, "text": x.text, "why": x.why, "task": x.task, "by": x.by,
                           "at": x.at.isoformat() if x.at else None} for x in decs]
        d["nightly"] = list(reversed((r.nightly or [])[-14:]))
        d["versions"] = versions(r.tenant_id, r.game_id, tasks)
    else:
        d["next"] = [task_view(t) for t in _ordered([t for t in tasks if t.status == "todo"], r.milestones or MILESTONES)[:3]]
        d["review"] = [task_view(t) for t in tasks if t.status == "review"]
    return d


def _bible_line(r: GameStudio) -> dict[str, Any]:
    """v0.395 the Game Bible in one line for the board: version, version inside the game, counts, problems."""
    try:
        from . import bible as B
        with session() as s:
            b = B._row(s, r.tenant_id, r.id, make=False)
            if b is None:
                return {"version": 0}
            data = b.data or B.empty()
            c = B.check(data)
            return {"version": b.version or 0, "applied": b.applied or 0, "draft": bool(b.draft),
                    "counts": {k: len(v or []) for k, v in (data.get("entities") or {}).items() if v},
                    "errors": len(c["errors"]), "warnings": len(c["warnings"])}
    except Exception:                                   # noqa: BLE001
        log.exception("bible line")
        return {"version": 0}


def _qa_line(r: GameStudio) -> dict[str, Any]:
    try:
        from . import qa as Q
        return Q.summary_line(r)
    except Exception:                                   # noqa: BLE001
        return {}


def _assets_line(r: GameStudio) -> dict[str, Any]:
    """v0.415 the asset store in one line for the board."""
    try:
        from . import assets as A
        A.ensure_table()
        with session() as s:
            rows = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == r.id)).all()
            return {"count": len(rows), "in_game": sum(1 for a in rows if a.approved),
                    "waiting_ok": sum(1 for a in rows if a.status == "draft"),
                    "priced": round(sum(a.cost_inr for a in rows if a.status == "priced"), 2)}
    except Exception:                                   # noqa: BLE001
        log.exception("assets line")
        return {"count": 0}


def versions(tenant: str, gid: str, tasks: list[GameTask] | None = None) -> list[dict[str, Any]]:
    g = _game(tenant, gid)
    if g is None:
        return []
    by_id = {t.id: t for t in (tasks or [])}
    live = (G._good(g) or [{}])[-1].get("n")
    out = []
    for v in reversed(g.versions or []):
        t = by_id.get(v.get("task") or "")
        out.append({"n": v.get("n"), "at": v.get("at"), "ok": bool(v.get("ok")), "rejected": bool(v.get("rejected")),
                    "live": v.get("n") == live, "words": (v.get("words") or "")[:200], "notes": (v.get("notes") or "")[:300],
                    "task": t.number if t else "", "task_title": t.title if t else "", "src": v.get("src", ""),
                    "bible": v.get("bible", 0),
                    "numbers": v.get("numbers") or {}})
    return out[:60]


def _ordered(todo: list[GameTask], milestones: list[dict]) -> list[GameTask]:
    order = {m["key"]: i for i, m in enumerate(milestones)}
    return sorted(todo, key=lambda t: (order.get(t.milestone, 99), t.priority or 2, _utc(t.created_at) or now()))


# ---------------------------------------------------------------- projects
def create(tenant: str, conv: str, title: str = "", goal: str = "", game: str = "", brief: str = "",
           orientation: str = "portrait", actor: str = "owner") -> dict[str, Any]:
    """A long project around an existing game (game = G-0001) or a new one (brief -> Phase 1's design doc first)."""
    ensure_tables()
    goal = _clean(goal, 1500)
    with session() as s:
        mine = s.scalars(select(GameStudio).where(GameStudio.tenant_id == tenant, GameStudio.status != "archived")).all()
        if len(mine) >= MAX_STUDIOS:
            raise StudioError(f"{MAX_STUDIOS} studio projects pehle se chal rahe hain; ek archive kijiye.")
        n = len(s.scalars(select(GameStudio.id).where(GameStudio.tenant_id == tenant)).all())
        taken = {x.game_id for x in mine}
    if game:
        g = G._get(tenant, game)
        if g.id in taken:
            raise StudioError(f"{g.number} pehle se ek studio project mein hai.")
    else:
        brief = _clean(brief or goal, 2000)
        if len(brief) < 8:
            raise StudioError("Kaunsa game? Purana game chuniye (G-0001) ya 2-3 line mein naye game ka idea likhiye.")
        gv = G.start(tenant, conv, brief, orientation, actor)
        g = G._get(tenant, gv["id"])
    r = GameStudio(tenant_id=tenant, conversation_id=conv or g.conversation_id or "", number=f"S-{n + 1:04d}",
                   title=_clean(title, 120) or g.title or g.brief[:60], goal=goal or g.brief[:1500], game_id=g.id,
                   milestones=[dict(m) for m in MILESTONES])
    with session() as s:
        s.add(r)
        s.flush()
        s.expunge(r)
    _decide(r, f"Project shuru: {r.title}", f"Lakshya: {r.goal[:300]}", by="her")
    return view(r, full=True)


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _studio(s, tenant, ref)
        s.expunge(r)
    return view(r, full=True)


def studios(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(GameStudio).where(GameStudio.tenant_id == tenant, GameStudio.status != "archived")
                         .order_by(GameStudio.updated_at.desc())).all()
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def settings(tenant: str, ref: str, **kw) -> dict[str, Any]:
    with session() as s:
        r = _studio(s, tenant, ref)
        if kw.get("title"):
            r.title = _clean(kw["title"], 120)
        if kw.get("goal"):
            r.goal = _clean(kw["goal"], 1500)
        for k in ("auto", "nightly_on", "summary_on"):
            if kw.get(k) is not None:
                setattr(r, k, bool(kw[k]))
        if kw.get("summary_hour") is not None:
            r.summary_hour = max(5, min(12, int(kw["summary_hour"])))
        if kw.get("status") in ("active", "paused", "archived"):
            r.status = kw["status"]
        if isinstance(kw.get("milestones"), list):
            have = {m["key"]: dict(m) for m in (r.milestones or MILESTONES)}
            for m in kw["milestones"]:
                if isinstance(m, dict) and m.get("key") in have:
                    if m.get("name"):
                        have[m["key"]]["name"] = _clean(m["name"], 40)
                    if "target" in m:
                        tg = _clean(m.get("target"), 10)
                        have[m["key"]]["target"] = tg if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tg) else ""
            r.milestones = list(have.values())
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    return view(r, full=True)


# ---------------------------------------------------------------- tasks
def _number(s, sid: str) -> str:
    n = len(s.scalars(select(GameTask.id).where(GameTask.studio_id == sid)).all())
    if n >= MAX_TASKS:
        raise StudioError("Is project mein bahut task ho gaye; purane band kijiye ya naya project banaiye.")
    return f"T-{n + 1:04d}"


def add_task(tenant: str, ref: str, title: str, detail: str = "", milestone: str = "", kind: str = "feature",
             priority: int = 2, source: str = "her", role: str = "", criteria: list | None = None) -> dict[str, Any]:
    title = _clean(title, 200)
    if len(title) < 3:
        raise StudioError("Task ek line mein likhiye (kya badalna / jodna hai).")
    why = G.problem(f"{title} {detail}")
    if why:
        raise StudioError(why)
    with session() as s:
        r = _studio(s, tenant, ref)
        keys = [m["key"] for m in (r.milestones or MILESTONES)]
        if milestone not in keys:
            prog = progress(r.milestones or MILESTONES, _tasks(s, r.id))
            milestone = current_milestone(prog) or keys[0]
        t = GameTask(tenant_id=tenant, studio_id=r.id, number=_number(s, r.id), title=title, detail=_clean(detail, 2000),
                     milestone=milestone, kind=kind if kind in KINDS else "feature",
                     priority=max(1, min(3, int(priority or 2))), source=source if source in ("her", "hoola", "nightly") else "her")
        t.role = role if role in C.ROLES else C.pick_role(title, detail, t.kind)
        t.criteria = C.criteria_for(t.role, criteria)
        s.add(t)
        r.updated_at = now()
        s.flush()
        s.expunge(t)
    return task_view(t)


def plan(tenant: str, ref: str, words: str = "", team: str = "") -> dict[str, Any]:
    """Hoola (the producer) proposes the next small tasks from the design, the goal, the board and her decisions.
    They land in To do; she can drop or edit any; nothing is built until a task starts."""
    from .. import usage
    with session() as s:
        r = _studio(s, tenant, ref)
        tasks = _tasks(s, r.id)
        decs = s.scalars(select(GameDecision).where(GameDecision.studio_id == r.id).order_by(GameDecision.at)).all()
        dec_lines = [f"{d.text} ({d.why})" if d.why else d.text for d in decs]
        try:                                            # v0.395 the Game Bible is the source of truth for every task
            from . import bible as B
            bb = B._row(s, tenant, r.id, make=False)
            if bb is not None and bb.version:
                dec_lines.append("GAME BIBLE (names / numbers live here; tasks change the Bible or read it): "
                                 + B._summary(bb.data or B.empty())[:6000])
        except Exception:                               # noqa: BLE001
            pass
        s.expunge(r)
        tv = [task_view(t) for t in tasks]
    if sum(1 for t in tv if t["status"] == "todo") >= 40:
        raise StudioError("To do mein 40 task pehle se hain; pehle unhe poora / band kijiye.")
    g = _game(tenant, r.game_id)
    if team and team not in C.TEAMS:
        raise StudioError("team = " + ", ".join(C.TEAMS))
    keys = C.TEAMS[team]["roles"] if team else [k for k, v in C.ROLES.items() if v["tier"] != C.E or k.startswith("godot")]
    roles = [C.ROLES[k] for k in keys]
    with usage.scope(tenant, "game"):
        items = G.ai.plan_tasks((g.design if g else "") or r.goal, r.goal, r.milestones or MILESTONES, tv, dec_lines,
                                _clean(words, 1500), roles=roles)
    made = []
    for i in items:
        role = str(i.get("role") or "")
        if team and role not in keys:                  # a team plan only uses the team's roles
            role = C.pick_role(str(i.get("title") or ""), str(i.get("detail") or ""), str(i.get("kind") or "feature"))
            role = role if role in keys else keys[0]
        try:
            made.append(add_task(tenant, r.id, i.get("title", ""), i.get("detail", ""), str(i.get("milestone") or ""),
                                 str(i.get("kind") or "feature"), int(i.get("priority") or 2) if str(i.get("priority") or "2").isdigit() else 2,
                                 source="hoola", role=role,
                                 criteria=i.get("criteria") if isinstance(i.get("criteria"), list) else None))
        except StudioError:
            continue
    if not made:
        raise StudioError("Hoola koi naya task nahi bana paya; apne shabdon mein ek task likhiye.")
    return {"made": made, "studio": get(tenant, r.id)}


def _busy_task(s, sid: str) -> GameTask | None:
    return s.scalars(select(GameTask).where(GameTask.studio_id == sid, GameTask.status.in_(("working", "review")))).first()


def start_task(tenant: str, ref: str, task: str = "") -> dict[str, Any]:
    """Build one task (the given one, or the next in order). One at a time; never while one waits for her OK."""
    with session() as s:
        r = _studio(s, tenant, ref)
        if r.status != "active":
            raise StudioError("Project ruka hua hai; pehle 'chalu karo' boliye.")
        b = _busy_task(s, r.id)
        if b is not None:
            raise StudioError(f"{b.number} ({b.title[:50]}) " + ("abhi ban raha hai." if b.status == "working" else
                              "aapke OK ka intezaar kar raha hai: pehle OK ya wapas kijiye."))
        if task:
            t = _task(s, tenant, task, r.id)
            if t.studio_id != r.id or t.status not in ("todo", "blocked"):
                raise StudioError(f"{t.number} '{t.status}' hai; sirf To do / ruka hua task shuru hota hai.")
        else:
            todo = _ordered([x for x in _tasks(s, r.id) if x.status == "todo"], r.milestones or MILESTONES)
            if not todo:
                raise StudioError("To do khaali hai: task likhiye ya 'aage ka plan banao' boliye.")
            t = todo[0]
        g = _game(tenant, r.game_id)
        if g is None:
            raise StudioError("Is project ka game nahi mila.")
        if not G._good(g):
            raise StudioError("Pehle game ka pehla version banne dijiye (design OK karke 'Build it').")
        role = t.role or C.pick_role(t.title, t.detail, t.kind)
        crit = "; ".join(c["text"] for c in (t.criteria or []) if c.get("by") != "test")
        words = (f"[{t.number}] {t.title}" + (f". {t.detail}" if t.detail else "") + f" || {C.lens(role)}"
                 + (f" || Done when: {crit}" if crit else ""))
        tid, gid = t.id, g.id
    if not C.builds(role):                              # v0.406 a writing role: a written result, no build
        with session() as s:
            t = s.get(GameTask, tid)
            t.status, t.error, t.tries, t.updated_at = "working", "", (t.tries or 0) + 1, now()
            s.flush()
            s.expunge(t)
        if os.environ.get("GAME_WORKER", "true").lower() in ("0", "false", "off"):
            pass                                        # tests call write_task themselves
        else:
            G._POOL.submit(_write_safe, tenant, tid)
        return task_view(t)
    G.change(tenant, gid, words[:1500], task=tid)       # raises GameError (busy / day limit) before the task moves
    with session() as s:
        t = s.get(GameTask, tid)
        t.status, t.error, t.tries, t.base = "working", "", (t.tries or 0) + 1, (G._good(g) or [{}])[-1].get("n", 0)
        t.updated_at = now()
        s.flush()
        s.expunge(t)
    return task_view(t)


def after_build(tenant: str, task_id: str, ver: dict | None, err: str = "") -> None:
    """Called by gamedesk.service when a task's build ends: review (built and played fine) / blocked / back to To do."""
    with session() as s:
        t = s.get(GameTask, task_id)
        if t is None or t.tenant_id != tenant or t.status != "working":
            return
        if ver and ver.get("ok"):
            t.status, t.version, t.notes, t.error = "review", int(ver.get("n") or 0), (ver.get("notes") or "")[:1500], ""
            ev = {"version": int(ver.get("n") or 0), "src": ver.get("src", ""), "by": "hoola playtest",
                  "shots": list(ver.get("shots") or [])[:3], "at": now().isoformat()}
            t.criteria = [({**c, "status": "covered", "evidence": ev} if c.get("by") == "test" else
                           {**c, "status": "untested", "evidence": {}}) for c in (t.criteria or [])]
        elif err == "cancelled":
            t.status, t.error = "todo", ""
        else:
            t.status, t.error = "blocked", (err or "build nahi chala")[:600]
            if ver:
                t.version = int(ver.get("n") or 0)
        t.updated_at = now()
        sid = t.studio_id
    with session() as s:
        r = s.get(GameStudio, sid)
        if r is not None:
            r.updated_at = now()
    if ver and ver.get("ok") and _auto_review():
        try:
            review_task(tenant, sid, task_id)
        except Exception:                               # noqa: BLE001 - a review never breaks the build result
            log.exception("crew review %s", task_id)


def _auto_review() -> bool:
    """The lead's review after each build: on with Claude configured (GAME_CREW_REVIEW=off turns it off)."""
    v = os.environ.get("GAME_CREW_REVIEW", "auto").lower()
    if v in ("0", "off", "false"):
        return False
    from ..config import get_settings
    return v in ("1", "on", "true") or bool(get_settings().anthropic_api_key)


REVIEW = """You are the {lead} of a small game studio, reviewing one finished task by your {role}. Judge ONLY what you
can see: the screenshots from Hoola's own playtest and the code change. For each acceptance criterion numbered below
say "covered" (you can see it is true), "failed" (you can see it is false) or "untested" (you cannot tell from this).
Never mark a criterion covered from the code alone when it is about what the player sees. Then up to 4 short findings a
lead would raise (bugs, rule breaks, risks), most important first. OUTPUT only JSON:
{{"criteria": [{{"i": 0, "status": "covered|failed|untested", "why": "short"}}], "findings": ["..."], "summary": "one line"}}"""


def _diff(g: G.GameProject, base: int, n: int) -> str:
    import difflib
    a = G._vdir(g, base) / "proj" if base else None
    b = G._vdir(g, n) / "proj"
    out = []
    for p in sorted(b.glob("*.gd")):
        if p.name in ("hoola_probe.gd", "hoola_bible.gd"):
            continue
        old = (a / p.name).read_text(encoding="utf-8").splitlines() if a and (a / p.name).is_file() else []
        out += list(difflib.unified_diff(old, p.read_text(encoding="utf-8").splitlines(), f"v{base}/{p.name}",
                                         f"v{n}/{p.name}", lineterm="", n=2))
    return "\n".join(out)[:14000] or "(no code change)"


def review_task(tenant: str, ref: str, task: str) -> dict[str, Any]:
    """The task's lead reviews it: screenshots + the code change against the criteria. Only screen criteria can be
    set by the review (test = Hoola's playtest, her = only her); the verdict is counted in code."""
    import json as _json
    from .. import usage
    with session() as s:
        r = _studio(s, tenant, ref)
        t = _task(s, tenant, task, r.id)
        if t.status != "review" or not t.version:
            raise StudioError(f"{t.number} review ke layak nahi ('{t.status}').")
        s.expunge(t)
        s.expunge(r)
    g = _game(tenant, r.game_id)
    role = t.role or C.pick_role(t.title, t.detail, t.kind)
    lead = C.reviewer(role)
    crit = list(t.criteria or [])
    shots = []
    if g is not None:
        for name in ((next((v for v in g.versions or [] if v.get("n") == t.version), {}) or {}).get("shots") or [])[:3]:
            p = G._vdir(g, t.version) / "shots" / name
            if p.is_file():
                shots.append(p.read_bytes())
    text = (f"Task {t.number}: {t.title}\n{t.detail}\nBuilder's notes: {t.notes}\n\nAcceptance criteria:\n"
            + "\n".join(f"{i}. [{c.get('by')}] {c.get('text')}" for i, c in enumerate(crit))
            + f"\n\nCode change:\n{_diff(g, t.base, t.version) if g else '(no game)'}")
    with usage.scope(tenant, "game"):
        raw = G.ai.ask_with_images(REVIEW.format(lead=C.ROLES.get(lead, {}).get("name", "lead"),
                                                 role=C.ROLES.get(role, {}).get("name", "builder")), text, shots)
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        res = _json.loads(m.group(0)) if m else {}
    except ValueError:
        res = {}
    ev = {"version": t.version, "src": ((next((v for v in (g.versions if g else []) or [] if v.get("n") == t.version), {}) or {}).get("src", "")),
          "by": lead, "shots": len(shots), "at": now().isoformat()}
    for item in res.get("criteria") or []:
        try:
            i = int(item.get("i"))
        except (TypeError, ValueError):
            continue
        st = str(item.get("status") or "")
        if 0 <= i < len(crit) and crit[i].get("by") == "screen" and st in ("covered", "failed", "untested"):
            if st == "covered" and not shots:
                st = "untested"                          # nothing seen = not covered
            crit[i] = {**crit[i], "status": st, "evidence": {**ev, "why": str(item.get("why") or "")[:200]} if st != "untested" else {}}
    rev = {"by": lead, "by_name": C.ROLES.get(lead, {}).get("name", ""), "at": now().isoformat(), "version": t.version,
           "shots_seen": len(shots), "summary": str(res.get("summary") or "")[:300],
           "findings": [str(x)[:300] for x in (res.get("findings") or [])][:4]}
    with session() as s:
        row = s.get(GameTask, t.id)
        row.criteria, row.review, row.updated_at = crit, rev, now()
        s.flush()
        s.expunge(row)
    return task_view(row)


def write_task(tenant: str, task_id: str) -> None:
    """A writing role's task (spec, checklist, store text, sound list, Unity / Unreal plan): one model call with the
    role's lens, the design and the Game Bible; the result waits for her OK. Nothing in the game changes."""
    from .. import usage
    with session() as s:
        t = s.get(GameTask, task_id)
        if t is None or t.tenant_id != tenant or t.status != "working":
            return
        r = s.get(GameStudio, t.studio_id)
        s.expunge(t)
        s.expunge(r)
    g = _game(tenant, r.game_id)
    bible_txt = ""
    try:
        from . import bible as B
        with session() as s:
            bb = B._row(s, tenant, r.id, make=False)
            bible_txt = B._summary(bb.data) if bb is not None and bb.version else ""
    except Exception:                                   # noqa: BLE001
        pass
    role = t.role or C.pick_role(t.title, t.detail, t.kind)
    system = (C.lens(role) + " Write the result of this task for the studio owner: clear headings, short lines, real "
              "numbers only from the material given (never invented), what is still open at the end. Markdown, max 600 words.")
    prompt = (f"Game: {r.title}\nGoal: {r.goal}\n\nDesign doc:\n{(g.design if g else '')[:6000]}\n\nGame Bible:\n{bible_txt[:8000]}"
              f"\n\nTask {t.number}: {t.title}\n{t.detail}\n\nIt is done when:\n"
              + "\n".join(f"- {c['text']}" for c in (t.criteria or [])))
    try:
        with usage.scope(tenant, "game"):
            out = G.ai.ask(system, prompt, max_tokens=3000).strip()
        status, err = ("review", "") if out else ("blocked", "khaali jawab aaya")
    except Exception as e:                              # noqa: BLE001
        out, status, err = "", "blocked", f"likh nahi paya: {type(e).__name__}"
    with session() as s:
        row = s.get(GameTask, task_id)
        if row is not None and row.status == "working":
            row.status, row.notes, row.error, row.updated_at = status, out[:12000], err, now()


def _write_safe(tenant: str, task_id: str) -> None:
    try:
        write_task(tenant, task_id)
    except Exception:                                   # noqa: BLE001
        log.exception("crew write %s", task_id)


def approve_task(tenant: str, ref: str, task: str, note: str = "") -> dict[str, Any]:
    note = _clean(note, 600)
    with session() as s:
        r = _studio(s, tenant, ref)
        t = _task(s, tenant, task, r.id)
        if t.status != "review":
            raise StudioError(f"{t.number} OK ke liye taiyaar nahi ('{t.status}').")
        t.status, t.done_at, t.updated_at = "done", now(), now()
        t.criteria = [({**c, "status": "covered", "evidence": {"by": "her", "at": now().isoformat(), "version": t.version}}
                       if c.get("by") == "her" and c.get("status") != "failed" else c) for c in (t.criteria or [])]
        num, title, auto = t.number, t.title, r.auto
        s.expunge(r)
    if note:
        _decide(r, f"{num} OK: {title}", note, task=num, by="her")
    nxt = None
    if auto:
        try:
            nxt = start_task(tenant, r.id)
        except G.GameError:
            nxt = None
    return {"done": num, "next": nxt, "studio": get(tenant, r.id)}


def reject_task(tenant: str, ref: str, task: str, note: str = "") -> dict[str, Any]:
    """'Wapas': the task's version stops being live (the one before it plays again) and the task returns to To do
    with her words added, so the next try knows what was wrong."""
    note = _clean(note, 800)
    with session() as s:
        r = _studio(s, tenant, ref)
        t = _task(s, tenant, task, r.id)
        if t.status not in ("review", "done"):
            raise StudioError(f"{t.number} wapas nahi ho sakta ('{t.status}').")
        if t.status == "done":
            newer = s.scalars(select(GameTask).where(GameTask.studio_id == r.id, GameTask.version > t.version,
                                                     GameTask.status.in_(("done", "review")))).first()
            if newer is not None:
                raise StudioError(f"{t.number} ke baad {newer.number} bana hai; seedha wapas nahi hoga. Ek naya task "
                                  "likhiye jo ise theek kare, ya 'version N wapas lao' boliye.")
        if t.version:
            G.reject_version(tenant, r.game_id, t.version)
        t.criteria = [{**c, "status": "untested", "evidence": {}} for c in (t.criteria or [])]
        t.review = {}
        t.status, t.done_at, t.updated_at = "todo", None, now()
        if note:
            t.detail = _clean(f"{t.detail} | Pichhli baar galat: {note}", 2000)
        num, title = t.number, t.title
        s.expunge(r)
    _decide(r, f"{num} wapas: {title}", note or "aapne wapas bheja", task=num, by="her")
    return get(tenant, r.id)


def edit_task(tenant: str, ref: str, task: str, **kw) -> dict[str, Any]:
    with session() as s:
        r = _studio(s, tenant, ref)
        t = _task(s, tenant, task, r.id)
        if kw.get("status") == "dropped":
            if t.status in ("working", "review"):
                raise StudioError(f"{t.number} abhi '{t.status}' hai; pehle rokiye / wapas kijiye.")
            t.status = "dropped"
        elif kw.get("status") == "todo" and t.status in ("dropped", "blocked"):
            t.status = "todo"
        if t.status in ("todo", "blocked"):
            if kw.get("title"):
                t.title = _clean(kw["title"], 200)
            if kw.get("detail") is not None and kw.get("detail") != "":
                t.detail = _clean(kw["detail"], 2000)
            if kw.get("milestone") in [m["key"] for m in (r.milestones or MILESTONES)]:
                t.milestone = kw["milestone"]
            if kw.get("priority"):
                t.priority = max(1, min(3, int(kw["priority"])))
        t.updated_at = now()
        s.flush()
        s.expunge(t)
    return task_view(t)


def restore(tenant: str, ref: str, n: int) -> dict[str, Any]:
    with session() as s:
        r = _studio(s, tenant, ref)
        b = _busy_task(s, r.id)
        if b is not None:
            raise StudioError(f"{b.number} '{b.status}' hai; pehle use poora kijiye.")
        s.expunge(r)
    G.restore(tenant, r.game_id, int(n))
    _decide(r, f"Version {int(n)} wapas laya", "aapke kehne par", by="her")
    return get(tenant, r.id)


# ---------------------------------------------------------------- decisions
def _decide(r: GameStudio, text: str, why: str = "", task: str = "", by: str = "her") -> None:
    with session() as s:
        s.add(GameDecision(tenant_id=r.tenant_id, studio_id=r.id, text=_clean(text, 600), why=_clean(why, 1000),
                           task=task, by=by))


def decide(tenant: str, ref: str, text: str, why: str = "") -> dict[str, Any]:
    text = _clean(text, 600)
    if len(text) < 3:
        raise StudioError("Faisla ek line mein likhiye.")
    with session() as s:
        r = _studio(s, tenant, ref)
        s.expunge(r)
    _decide(r, text, why, by="her")
    return get(tenant, r.id)


_WORD = re.compile(r"[a-z0-9ऀ-ॿ]{3,}")


def why(tenant: str, ref: str, q: str) -> dict[str, Any]:
    """Her 'why is X like this?' -> the decisions and finished tasks that mention it (newest first). The answer is
    read from these; if nothing matches, Hoola says so instead of guessing."""
    words = set(_WORD.findall((q or "").lower())) - {"why", "kyun", "kyon", "hai", "the", "and", "kya", "this", "itna", "itni"}
    with session() as s:
        r = _studio(s, tenant, ref)
        decs = s.scalars(select(GameDecision).where(GameDecision.studio_id == r.id)).all()
        tasks = [t for t in _tasks(s, r.id) if t.status in ("done", "review")]
        hits = []
        for d in decs:
            sc = len(words & set(_WORD.findall(f"{d.text} {d.why}".lower())))
            if sc:
                hits.append((sc, _utc(d.at), {"type": "decision", "text": d.text, "why": d.why, "task": d.task, "by": d.by,
                                              "at": d.at.isoformat() if d.at else None}))
        for t in tasks:
            sc = len(words & set(_WORD.findall(f"{t.title} {t.detail} {t.notes}".lower())))
            if sc:
                hits.append((sc, _utc(t.done_at or t.updated_at), {"type": "task", "text": f"{t.number} {t.title}",
                                                                   "why": t.detail[:300], "notes": t.notes[:300],
                                                                   "at": (t.done_at or t.updated_at).isoformat()}))
    hits.sort(key=lambda h: (-h[0], -(h[1].timestamp() if h[1] else 0)))
    return {"question": q, "found": [h[2] for h in hits[:8]],
            "note": "" if hits else "Is baare mein koi faisla / task log mein nahi hai; andaza mat lagaiye, use bataiye."}


# ---------------------------------------------------------------- nightly build
def nightly(tenant: str, ref: str) -> dict[str, Any]:
    """The live version's code built and played again FROM SCRATCH (no model call): proves the project still builds,
    compares fps with the last good night and names the tasks since then when something broke."""
    import shutil
    import tempfile
    from . import engine, playtest, template
    with session() as s:
        r = _studio(s, tenant, ref)
        s.expunge(r)
    g = _game(tenant, r.game_id)
    good = G._good(g) if g else []
    if not good:
        raise StudioError("Abhi koi chalne wala version nahi.")
    live = good[-1]
    if not G.health()["ready"]:
        raise StudioError("Server par Godot taiyaar nahi; raat ka build nahi chala.")
    src = G._vdir(g, live["n"]) / "proj"
    res: dict[str, Any] = {"at": now().isoformat(), "version": live["n"], "ok": False, "errors": [], "suspects": []}
    t0 = time.time()
    with _NIGHT_LOCK, tempfile.TemporaryDirectory(prefix="hoola-night-") as d:
        job = __import__("pathlib").Path(d)
        shutil.copytree(src, job / "proj")
        res["src"] = G._src_hash(job / "proj")
        res["same_code"] = bool(live.get("src")) and res["src"] == live.get("src")
        sm = engine.smoke(job)
        res["errors"] = list(sm.get("errors") or [])[:6]
        if sm.get("ok"):
            ex = engine.export_web(job)
            res["errors"] = list(ex.get("errors") or [])[:6]
            if ex.get("ok"):
                pl = playtest.run(job / "build", job / "shots", g.orientation if g.orientation in template.SIZES else "portrait")
                res["errors"] = list(pl.get("errors") or [])[:6]
                res["ok"] = bool(pl.get("ok"))
                res["fps"] = pl.get("fps")
                res["load_s"] = pl.get("load_s")
                if res["ok"] and os.environ.get("GAME_QA_NIGHTLY", "on").lower() not in ("0", "off", "false"):
                    try:                                # v0.415 the QA farm plays the same fresh build every night
                        from . import qa as Q
                        q = Q.farm(tenant, r.id, proj=job / "proj", version=live["n"])
                        res["qa"] = {"verdict": q.get("verdict"), "filed": len(q.get("filed") or []), "fixed": q.get("fixed")}
                    except Exception as e:              # noqa: BLE001
                        log.exception("nightly qa")
                        res["qa"] = {"verdict": "NOT ASSESSED", "error": type(e).__name__}
    res["seconds"] = round(time.time() - t0, 1)
    prev_ok = next((x for x in reversed(r.nightly or []) if x.get("ok")), None)
    warn = []
    if res["ok"] and prev_ok and prev_ok.get("fps") and res.get("fps") and res["fps"] < prev_ok["fps"] * (1 - FPS_DROP):
        warn.append(f"fps {prev_ok['fps']} -> {res['fps']}")
    if (not res["ok"] or warn):
        since = int((prev_ok or {}).get("version") or 0)
        with session() as s:
            res["suspects"] = [f"{t.number} {t.title[:60]}" for t in _tasks(s, r.id)
                               if t.status in ("done", "review") and t.version > since][:6]
    res["warnings"] = warn
    with session() as s:
        row = s.get(GameStudio, r.id)
        row.nightly = ((row.nightly or []) + [res])[-30:]
    if not res["ok"]:
        try:
            add_task(tenant, r.id, f"Raat ka build theek karo (version {live['n']})",
                     "Nightly build fail: " + "; ".join(res["errors"][:3]) + (
                         f". Shayad inse: {', '.join(res['suspects'][:3])}" if res["suspects"] else ""),
                     kind="fix", priority=1, source="nightly")
        except StudioError:
            pass
    return res


# ---------------------------------------------------------------- milestone gate (advisory, never blocks her)
GATE = """You are the studio's {who}. A milestone gate check is in front of you with FACTS counted by Hoola (below).
Write 2-4 short lines from your seat: what is solid, what worries you, what to do next. Use only these facts; never
invent a number. If the facts say NOT ASSESSED, say what is missing to judge it."""


def gate(tenant: str, ref: str, milestone: str = "") -> dict[str, Any]:
    """Can this milestone be called done? Facts and the verdict are counted in code (PASS / CONCERNS / FAIL / NOT
    ASSESSED); the creative director, technical director and producer each add a short view when Claude is set up.
    It advises - nothing moves without her."""
    from .. import usage
    with session() as s:
        r = _studio(s, tenant, ref)
        tasks = _tasks(s, r.id)
        for t in tasks:
            s.expunge(t)
        s.expunge(r)
    prog = progress(r.milestones or MILESTONES, tasks)
    milestone = milestone or current_milestone(prog)
    m = next((x for x in prog if x["key"] == milestone), None)
    if m is None:
        raise StudioError("milestone = " + ", ".join(x["key"] for x in prog))
    mine = [t for t in tasks if t.milestone == milestone and t.status != "dropped"]
    crit = [c for t in mine for c in (t.criteria or [])]
    covered = sum(1 for c in crit if c.get("status") == "covered")
    night = (r.nightly or [])[-1] if r.nightly else {}
    facts = {"milestone": m["name"], "tasks": len(mine), "done": sum(1 for t in mine if t.status == "done"),
             "open": sum(1 for t in mine if t.status in ("todo", "working", "review")),
             "blocked": [f"{t.number} {t.title[:50]}" for t in mine if t.status == "blocked"],
             "criteria": len(crit), "criteria_covered": covered,
             "criteria_failed": sum(1 for c in crit if c.get("status") == "failed"),
             "nightly": ("not run yet" if not night else "skipped: " + str(night.get("skipped")) if night.get("skipped")
                         else "passed" if night.get("ok") else "FAILED"),
             "target": m.get("target") or ""}
    bib: dict[str, Any] = {}
    try:
        from . import bible as B
        v = B.view(tenant, r.id)
        sim = B.simulate(v["data"], 100) if v["version"] else {"verdict": "NOT ASSESSED"}
        bib = {"version": v["version"], "errors": len(v["check"]["errors"]), "sim": sim.get("verdict"),
               "sim_flags": (sim.get("flags") or [])[:4]}
    except Exception:                                   # noqa: BLE001
        bib = {"version": 0}
    facts["bible"] = bib
    qa_last = (r.qa or [{}])[-1] if r.qa else {}
    try:
        from . import qa as Q
        qline = Q.summary_line(r)
    except Exception:                                   # noqa: BLE001
        qline = {}
    facts["qa"] = {"verdict": qa_last.get("verdict") or "not run", "version": qa_last.get("version"),
                   "open_bugs": qline.get("open", 0), "crash_bugs": qline.get("crash_open", 0)}
    blockers, concerns, missing = [], [], []
    if not mine:
        missing.append("no tasks in this milestone")
    if facts["blocked"]:
        blockers.append(f"{len(facts['blocked'])} task(s) stuck: " + ", ".join(facts["blocked"][:3]))
    if facts["criteria_failed"]:
        blockers.append(f"{facts['criteria_failed']} acceptance criteria failed")
    if night and not night.get("skipped") and not night.get("ok"):
        blockers.append("last nightly build failed")
    if bib.get("errors"):
        blockers.append(f"Game Bible has {bib['errors']} error(s)")
    if facts["qa"]["crash_bugs"]:
        blockers.append(f"{facts['qa']['crash_bugs']} crash / blocker bug(s) open")
    if facts["qa"]["verdict"] == "FAIL":
        blockers.append("the last QA farm run failed")
    if facts["qa"]["verdict"] in ("not run", "NOT ASSESSED"):
        concerns.append("the QA bots have not checked this game yet" if facts["qa"]["verdict"] == "not run" else "the last QA run could not assess the game")
    elif facts["qa"]["verdict"] == "CONCERNS":
        concerns.append("the last QA farm run raised concerns")
    if facts["open"]:
        concerns.append(f"{facts['open']} task(s) still open")
    if crit and covered < len(crit):
        concerns.append(f"{len(crit) - covered} of {len(crit)} acceptance criteria not yet covered")
    if not night or night.get("skipped"):
        concerns.append("no nightly build has checked this game yet" if not night else f"nightly skipped ({night.get('skipped')})")
    if bib.get("sim_flags"):
        concerns.append("balance: " + "; ".join(bib["sim_flags"][:2]))
    verdict = "NOT ASSESSED" if missing else "FAIL" if blockers else "CONCERNS" if concerns else "PASS"
    views: dict[str, str] = {}
    if _auto_review() and verdict != "NOT ASSESSED":
        import json as _json
        for who in ("creative_director", "technical_director", "producer"):
            try:
                with usage.scope(tenant, "game"):
                    views[who] = G.ai.ask(GATE.format(who=C.ROLES[who]["name"]), _json.dumps(
                        {"facts": facts, "verdict": verdict, "blockers": blockers, "concerns": concerns}), max_tokens=500).strip()[:800]
            except Exception:                           # noqa: BLE001
                continue
    res = {"at": now().isoformat(), "milestone": milestone, "name": m["name"], "verdict": verdict, "facts": facts,
           "blockers": blockers, "concerns": concerns, "missing": missing, "views": views,
           "note": "Advice only: you decide when a milestone is done."}
    with session() as s:
        row = s.get(GameStudio, r.id)
        row.gates = ((row.gates or []) + [res])[-20:]
    _decide(r, f"Gate {m['name']}: {verdict}", "; ".join(blockers + concerns + missing)[:600], by="hoola")
    return res


# ---------------------------------------------------------------- morning summary
def summary(tenant: str, ref: str) -> str:
    """The producer's morning note, written in code from the board (no model call, no numbers that are not real)."""
    with session() as s:
        r = _studio(s, tenant, ref)
        tasks = _tasks(s, r.id)
        for t in tasks:
            s.expunge(t)
        s.expunge(r)
    day = now() - timedelta(hours=24)
    done = [t for t in tasks if t.status == "done" and t.done_at and _utc(t.done_at) >= day]
    review = [t for t in tasks if t.status == "review"]
    blocked = [t for t in tasks if t.status == "blocked"]
    working = [t for t in tasks if t.status == "working"]
    todo = _ordered([t for t in tasks if t.status == "todo"], r.milestones or MILESTONES)
    prog = progress(r.milestones or MILESTONES, tasks)
    cur = next((m for m in prog if m["total"] and m["done"] < m["total"]), None) or \
        next((m for m in reversed(prog) if m["total"]), None)          # never a milestone with no tasks ("0/0")
    lines = [f"{r.number} {r.title}: subah ki report"]
    lines.append(f"Kal: {len(done)} kaam poore" + (f" ({', '.join(t.number + ' ' + t.title[:40] for t in done[:3])})" if done else "") + ".")
    if review:
        lines.append(f"Aapke OK ke liye: {', '.join(t.number + ' ' + t.title[:40] for t in review[:3])}.")
    if working:
        lines.append(f"Ban raha hai: {working[0].number} {working[0].title[:50]}.")
    if blocked:
        lines.append(f"Ruka hua: {', '.join(t.number + ' ' + t.title[:40] for t in blocked[:3])}.")
    n = (r.nightly or [])[-1] if r.nightly else None
    fresh = bool(n and _utc(datetime.fromisoformat(n["at"])) >= day)
    if r.nightly_on and not fresh and _game(tenant, r.game_id) is not None:
        lines.append("Raat ka build: kal raat jaancha NAHI gaya (isliye 'sab theek' nahi keh sakte).")
    if fresh and n.get("skipped"):
        lines.append(f"Raat ka build: NAHI chala - {n['skipped']}.")
    elif fresh:
        if n.get("ok"):
            lines.append(f"Raat ka build: chala (version {n['version']}"
                         + (f", {n['fps']} fps" if n.get("fps") else "") + (f", {n['load_s']} s mein khula" if n.get("load_s") else "")
                         + ")" + (f"; dhyan: {', '.join(n.get('warnings') or [])}" if n.get("warnings") else "") + ".")
        else:
            lines.append("Raat ka build: FAIL - " + "; ".join((n.get("errors") or ["?"])[:2])[:200]
                         + (f". Shayad: {', '.join(n.get('suspects')[:2])}" if n.get("suspects") else "") + ".")
    q = (r.qa or [{}])[-1] if r.qa else None
    if q and q.get("at") and _utc(datetime.fromisoformat(q["at"])) >= day:
        lines.append(f"QA bots: {q.get('verdict')}" + (f", {len(q.get('filed') or [])} bug(s) mile" if q.get("filed") else "")
                     + (f", theek hue: {', '.join(q['fixed'][:3])}" if q.get("fixed") else "") + ".")
    if todo:
        lines.append(f"Aaj: {', '.join(t.number + ' ' + t.title[:40] for t in todo[:3])}.")
    if cur:
        lines.append(f"Milestone {cur['name']}: {cur['done']}/{cur['total']} ({cur['pct']}%)"
                     + (f", lakshya {cur['target']}" if cur.get("target") else "") + ".")
    return "\n".join(lines)


# ---------------------------------------------------------------- background (worker)
_LAST_TICK = 0.0


def jobs(force: bool = False) -> dict[str, int]:
    """Every few minutes from the worker: morning summaries at her hour, nightly builds in the night window, and an
    'auto' project whose board is idle picks its next task. Cheap when nothing is due."""
    global _LAST_TICK
    out = {"summaries": 0, "nightly": 0, "started": 0}
    if not force and time.time() - _LAST_TICK < 240:
        return out
    _LAST_TICK = time.time()
    ensure_tables()
    from ..employee import hire
    from ..events import notify
    with session() as s:
        rows = s.scalars(select(GameStudio).where(GameStudio.status == "active")).all()
        for r in rows:
            s.expunge(r)
    for r in rows:
        try:
            if not hire.is_working(r.tenant_id, "game_dev"):
                continue
            try:                                        # v0.415 finished 3D Studio models become asset versions
                from . import assets as A
                A.collect_models(r.tenant_id)
            except Exception:                           # noqa: BLE001
                log.exception("collect models")
            local = _local(r.tenant_id)
            with session() as s:
                tasks = _tasks(s, r.id)
                active = any(_utc(t.updated_at) and _utc(t.updated_at) > now() - timedelta(days=14) for t in tasks)
                st = {t.status for t in tasks}
            if r.summary_on and tasks and local.hour >= r.summary_hour and r.last_summary != local.date().isoformat() and active:
                with session() as s:
                    s.get(GameStudio, r.id).last_summary = local.date().isoformat()
                conv = r.conversation_id
                if not conv:
                    from ..net.service import home_conv
                    conv = home_conv(r.tenant_id)
                notify(conv, summary(r.tenant_id, r.id))
                out["summaries"] += 1
            last = (r.nightly or [])[-1] if r.nightly else None
            last_at = _utc(datetime.fromisoformat(last["at"])) if last else None
            if (r.nightly_on and active and NIGHT_HOURS[0] <= local.hour < NIGHT_HOURS[1]
                    and (last_at is None or now() - last_at > timedelta(hours=20)) and "working" not in st):
                G._POOL.submit(_night_safe, r.tenant_id, r.id)
                out["nightly"] += 1
            if r.auto and "todo" in st and not ({"working", "review"} & st):
                g = _game(r.tenant_id, r.game_id)
                if g is not None and G._good(g) and g.status not in G.BUSY:
                    start_task(r.tenant_id, r.id)
                    out["started"] += 1
        except G.GameError as e:
            log.info("studio %s: %s", r.number, e)
        except Exception:                               # noqa: BLE001
            log.exception("studio job %s", r.id)
    return out


def _local(tenant: str) -> datetime:
    from ..life import tz_of
    return now().astimezone(tz_of(tenant))


def _night_safe(tenant: str, sid: str) -> None:
    try:
        res = nightly(tenant, sid)
        if not res.get("ok"):
            log.info("studio nightly %s failed: %s", sid, res.get("errors"))
    except Exception as e:                              # noqa: BLE001 - recorded, never silent (v0.406 NOT ASSESSED)
        log.info("studio nightly %s: %s", sid, e)
        skipped(sid, str(e)[:200])


def skipped(sid: str, why: str) -> None:
    """A nightly that could not run is a record too: the morning report and the gate say it was NOT checked."""
    with session() as s:
        row = s.get(GameStudio, sid)
        if row is not None:
            row.nightly = ((row.nightly or []) + [{"at": now().isoformat(), "ok": None, "skipped": why, "errors": [],
                                                   "suspects": []}])[-30:]
