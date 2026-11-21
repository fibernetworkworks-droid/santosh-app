"""G8 of docs/SUPPORT_GLOBAL_PLAN.md: HER ticket workflow, and always knowing where a ticket is.

- Workflows are hers: they start from her industry pack (G0) and she changes them on the Workflow page - stages (name,
  owner, time limit, the customer is told or not, waiting on someone outside, fields that must be filled before leaving),
  the arrows between them, and which ticket categories use which workflow.
- A ticket is ALWAYS at one stage with one owner and one next deadline. It moves only along her arrows; Hoola moves a
  ticket only out of a stage she gave to Hoola; a stage's required fields must be filled before it is left; every move is
  recorded (who, when, from, to, why) and the customer is told when she ticked it for that stage.
- "Where is my request?" on any channel is answered from the REAL stage, owner team and next deadline (customer_line),
  never a guess. She can ask which tickets are stuck at a stage (stuck()).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

STATUSES = ("new", "open", "pending", "on_hold", "resolved", "closed")
OWNER_KINDS = ("hoola", "team", "supervisor", "approver", "finance", "field", "engineering")
DEFAULT = {"key": "request", "name": "Request", "categories": [], "stages": [
    {"key": "new", "name": "New", "owner": "hoola", "hours": 2, "customer_told": False, "needs": [], "waiting": False},
    {"key": "working", "name": "Being worked on", "owner": "team", "hours": 48, "customer_told": True, "needs": [], "waiting": False},
    {"key": "solved", "name": "Solved", "owner": "team", "hours": 72, "customer_told": True, "needs": [], "waiting": False},
    {"key": "closed", "name": "Closed", "owner": "team", "hours": 0, "customer_told": False, "needs": [], "waiting": False}],
    "arrows": {"new": ["working", "solved"], "working": ["solved"], "solved": ["closed", "working"], "closed": []}}


class FlowError(Exception):
    pass


class SevaFlow(Base):
    """One workflow of hers."""
    __tablename__ = "seva_flows"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sfl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(30), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    body: Mapped[str] = mapped_column(Text, default="{}")            # stages, arrows, categories
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaStageMove(Base):
    """One move of one ticket (append-only)."""
    __tablename__ = "seva_stage_moves"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ssm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), index=True)
    flow: Mapped[str] = mapped_column(String(30), default="")
    from_stage: Mapped[str] = mapped_column(String(30), default="")
    to_stage: Mapped[str] = mapped_column(String(30), default="")
    by: Mapped[str] = mapped_column(String(80), default="")
    why: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaFlow, SevaStageMove):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service as S
    return S


def _aware(d):
    from datetime import timezone
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- checking a workflow
def _owner_ok(o: str) -> bool:
    o = str(o or "")
    if o in OWNER_KINDS:
        return True
    kind, _, name = o.partition(":")
    return kind in ("person", "queue") and bool(name.strip())


def clean_flow(f: dict) -> dict:
    """A workflow checked and tidied: stage keys unique, owners known, arrows between real stages, every stage reachable
    from the first, the last stage ends."""
    if not isinstance(f, dict):
        raise FlowError("A workflow is a set of stages and arrows.")
    import re
    key = re.sub(r"[^a-z0-9_]", "", str(f.get("key") or "").lower())[:30]
    name = str(f.get("name") or key).strip()[:80]
    if not key or not name:
        raise FlowError("Give the workflow a name.")
    stages, seen = [], set()
    for s in (f.get("stages") or [])[:20]:
        k = re.sub(r"[^a-z0-9_]", "", str(s.get("key") or s.get("name") or "").lower().replace(" ", "_"))[:30]
        n = str(s.get("name") or "").strip()[:60]
        if not k or not n:
            raise FlowError("Every stage needs a name.")
        if k in seen:
            raise FlowError(f"Two stages are called {n}.")
        seen.add(k)
        if not _owner_ok(s.get("owner")):
            raise FlowError(f"{n}: the owner must be Hoola, a role ({', '.join(OWNER_KINDS[1:])}), person:<name> or queue:<name>.")
        try:
            hours = max(0.0, min(24 * 90, float(s.get("hours") or 0)))
        except (TypeError, ValueError):
            raise FlowError(f"{n}: the time limit is a number of hours.")
        st = s.get("status") if s.get("status") in STATUSES else ""
        stages.append({"key": k, "name": n, "owner": str(s.get("owner")), "hours": hours, "customer_told": bool(s.get("customer_told")),
                       "needs": [str(x).strip()[:40] for x in (s.get("needs") or []) if str(x).strip()][:6],
                       "waiting": bool(s.get("waiting")), "status": st,
                       "confirm": bool(s["confirm"]) if "confirm" in s else k in ("confirmed", "solved", "confirm")})
    if len(stages) < 2:
        raise FlowError("A workflow needs at least two stages.")
    keys = [s["key"] for s in stages]
    arrows = {}
    for k in keys:
        tos = [t for t in ((f.get("arrows") or {}).get(k) or []) if t in keys and t != k]
        arrows[k] = list(dict.fromkeys(tos))
    if arrows[keys[-1]]:
        raise FlowError(f"The last stage ({stages[-1]['name']}) must end: no arrows out of it.")
    seen, todo = set(), [keys[0]]
    while todo:
        k = todo.pop()
        if k not in seen:
            seen.add(k)
            todo += arrows[k]
    lost = [s["name"] for s in stages if s["key"] not in seen]
    if lost:
        raise FlowError("These stages cannot be reached from the first: " + ", ".join(lost))
    cats = [str(c)[:20] for c in (f.get("categories") or []) if str(c).strip()][:30]
    return {"key": key, "name": name, "stages": stages, "arrows": arrows, "categories": cats}


def status_of(flow: dict, stage: str) -> str:
    """The ticket status a stage means (her own, else: first = new, waiting = pending, last = closed, else open)."""
    keys = [s["key"] for s in flow["stages"]]
    s = next((x for x in flow["stages"] if x["key"] == stage), None)
    if s is None:
        return "open"
    if s.get("status"):
        return s["status"]
    if stage == keys[0]:
        return "new"
    if stage == keys[-1]:
        return "closed"
    if s.get("waiting"):
        return "pending"
    return "open"


# ---------------------------------------------------------------- her workflows
def _install(tenant: str) -> None:
    """First read: her pack's workflows (G0) or the default one."""
    with session() as s:
        if s.scalars(select(SevaFlow).where(SevaFlow.tenant_id == tenant)).first() is not None:
            return
    from . import profile as PF
    st = PF.get(tenant)
    flows = []
    if st:
        try:
            flows = PF.pack(st["pack"])["flows"]
        except PF.ProfileError:
            flows = []
    flows = flows or [DEFAULT]
    cats = list(PF.categories(tenant)) if st else []
    with session() as s:
        for i, f in enumerate(flows):
            body = dict(f)
            if i == 0 and "categories" not in body:
                body["categories"] = []
            body.setdefault("categories", [c for c in cats if c == f["key"]])
            c = clean_flow(body | {"key": f["key"], "name": f["name"]})
            s.add(SevaFlow(tenant_id=tenant, key=c["key"], name=c["name"], body=json.dumps(c)))


def flows(tenant: str) -> list[dict]:
    _ensure()
    _install(tenant)
    with session() as s:
        rows = s.scalars(select(SevaFlow).where(SevaFlow.tenant_id == tenant, SevaFlow.active.is_(True))
                         .order_by(SevaFlow.updated_at)).all()
        return [json.loads(r.body) | {"version": r.version} for r in rows]


def flow(tenant: str, key: str) -> dict:
    for f in flows(tenant):
        if f["key"] == key:
            return f
    raise FlowError("No such workflow.")


def save(tenant: str, body: dict, by: str = "owner") -> dict:
    """Her change to a workflow (or a new one). A stage that tickets are still at cannot be removed."""
    _ensure()
    _install(tenant)
    c = clean_flow(body)
    S = _S()
    with session() as s:
        r = s.scalars(select(SevaFlow).where(SevaFlow.tenant_id == tenant, SevaFlow.key == c["key"])).first()
        if r is not None:
            gone = {x["key"] for x in json.loads(r.body)["stages"]} - {x["key"] for x in c["stages"]}
            if gone:
                held = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.flow == c["key"],
                                                            S.SevaTicket.stage.in_(gone),
                                                            S.SevaTicket.status.in_(S.R.OPEN))).all()
                if held:
                    raise FlowError(f"{len(held)} open ticket(s) are still at a stage you removed ({', '.join(sorted(gone))}). "
                                    "Move them first.")
            r.body, r.name, r.version, r.updated_at, r.active = json.dumps(c), c["name"], r.version + 1, now(), True
        else:
            s.add(SevaFlow(tenant_id=tenant, key=c["key"], name=c["name"], body=json.dumps(c)))
    return flow(tenant, c["key"]) | {"say": f"Workflow {c['name']} saved."}


def remove(tenant: str, key: str) -> dict:
    S = _S()
    with session() as s:
        n = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.flow == key,
                                                 S.SevaTicket.status.in_(S.R.OPEN))).all()
        if n:
            raise FlowError(f"{len(n)} open ticket(s) use this workflow.")
        r = s.scalars(select(SevaFlow).where(SevaFlow.tenant_id == tenant, SevaFlow.key == key)).first()
        if r is None:
            raise FlowError("No such workflow.")
        r.active = False
    if not flows(tenant):
        raise FlowError("Keep at least one workflow.")
    return {"removed": key, "say": "Workflow removed."}


def pick(tenant: str, category: str) -> dict:
    fs = flows(tenant)
    for f in fs:
        if category in f.get("categories", []) or f["key"] == category:
            return f
    return fs[0]


# ---------------------------------------------------------------- tickets at stages
def _due(stage: dict, at: datetime, tenant: str = "") -> datetime | None:
    """The stage's deadline: its hours counted in HER working hours when she set them (G9, seva/watch.py)."""
    if not stage.get("hours"):
        return None
    if tenant:
        try:
            from . import watch as W
            return W.add_work(tenant, at, stage["hours"])
        except Exception:   # noqa: BLE001
            pass
    return at + timedelta(hours=stage["hours"])


def start(tenant: str, ticket_id: str, by: str = "hoola") -> None:
    """A new ticket enters its workflow at the first stage."""
    S = _S()
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        if t is None or t.flow:
            return
        f = pick(tenant, t.category)
        st0 = f["stages"][0]
        at = S.clock()
        t.flow, t.stage, t.stage_at, t.stage_due_at = f["key"], st0["key"], at, _due(st0, at, tenant)
        s.add(SevaStageMove(tenant_id=tenant, ticket_id=t.id, flow=f["key"], from_stage="", to_stage=st0["key"], by=by[:80],
                            why="opened"))


def stage_of(t) -> tuple[dict | None, dict | None]:
    if not getattr(t, "flow", ""):
        return None, None
    try:
        f = flow(t.tenant_id, t.flow)
    except FlowError:
        return None, None
    return f, next((x for x in f["stages"] if x["key"] == t.stage), None)


def owner_name(o: str) -> str:
    from . import profile as PF
    if ":" in str(o):
        kind, name = o.split(":", 1)
        return name.strip() if kind == "person" else f"the {name.strip()} team"
    return {"team": "the support team"}.get(o, PF.OWNERS.get(o, o).lower() if o != "hoola" else "Hoola")


def move(tenant: str, ref: str, to: str, by: str = "owner", why: str = "", fields: dict | None = None,
         system: bool = False) -> dict:
    """Move a ticket along HER arrows. Hoola may move it only out of a stage she gave to Hoola. `system` = the
    customer's own answer to "did this fix it?" (G9), which may close a stage that is not Hoola's."""
    S = _S()
    with session() as s:
        t = S._find_ticket(s, tenant, ref)
        if not t.flow:
            raise FlowError("This ticket has no workflow yet.")
        tid = t.id
    f, cur = stage_of(t)
    if f is None or cur is None:
        raise FlowError("This ticket's workflow or stage is gone; pick a stage again.")
    if to not in f["arrows"].get(cur["key"], []):
        names = {x["key"]: x["name"] for x in f["stages"]}
        nxt = ", ".join(names[k] for k in f["arrows"].get(cur["key"], [])) or "none (it is the last stage)"
        raise FlowError(f"From {cur['name']} it can go to: {nxt}.")
    if not system and by.startswith(("hoola", "customer:")) and cur["owner"] != "hoola":
        raise FlowError(f"{cur['name']} belongs to {owner_name(cur['owner'])}; Hoola does not move it.")
    have = dict(S._j(t.fields, {}) if getattr(t, "fields", "") else {})
    for k, v in (fields or {}).items():
        if str(v).strip():
            have[str(k)[:40]] = S._clean(v, 300)
    missing = [n for n in cur.get("needs", []) if not str(have.get(n, "")).strip()]
    if missing and not system:
        raise FlowError(f"Fill before leaving {cur['name']}: {', '.join(missing)}.")
    nxt = next(x for x in f["stages"] if x["key"] == to)
    at = S.clock()
    status = status_of(f, to)
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        t.stage, t.stage_at, t.stage_due_at, t.updated_at = to, at, _due(nxt, at, tenant), at
        t.fields = S._dump(have)
        if status != t.status:
            if status == "pending" and not t.paused_since:
                t.paused_since = at
            if t.status == "pending" and status != "pending" and t.paused_since:
                t.paused_s += (at - _aware(t.paused_since)).total_seconds()
                from . import watch as W
                W.log_pause(t, t.paused_since, at)
                t.paused_since = None
            if status in ("resolved", "closed") and not t.resolved_at:
                t.resolved_at = at
            if status == "closed":
                t.closed_at = at
            t.status = status
        s.add(SevaStageMove(tenant_id=tenant, ticket_id=tid, flow=f["key"], from_stage=cur["key"], to_stage=to, by=by[:80],
                            why=S._clean(why, 500)))
        S._add_note(t, by, f"Moved from {cur['name']} to {nxt['name']}." + (f" {S._clean(why, 300)}" if why else ""))
        number = t.number
    told = {}
    from . import watch as W
    checking = nxt.get("confirm") and not system and status != "closed" and W.rules(tenant).get("confirm_on")
    if nxt.get("customer_told") and not checking:
        told = S._tell(tenant, tid, customer_line(tenant, number))
    if checking:
        told = W.entered(tenant, tid, by) or told
    elif status == "closed" and not system:
        W._after_close(tenant, tid)
    return S.ticket(tenant, number) | {"told": told, "say": f"{number} is now at {nxt['name']}."}


def history(tenant: str, ticket_id: str) -> list[dict]:
    _ensure()
    with session() as s:
        rows = s.scalars(select(SevaStageMove).where(SevaStageMove.tenant_id == tenant, SevaStageMove.ticket_id == ticket_id)
                         .order_by(SevaStageMove.at)).all()
        return [{"from": r.from_stage, "to": r.to_stage, "by": r.by, "why": r.why, "at": _aware(r.at).isoformat()} for r in rows]


def _when(tenant: str, d) -> str:
    S = _S()
    loc = S._local(tenant, d)
    return loc.strftime("%a %d %b, %H:%M")


def customer_line(tenant: str, number: str) -> str:
    """What the customer is told about where their request is - only the real stage, owner and deadline."""
    S = _S()
    with session() as s:
        t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.number == number)).first()
        if t is None:
            return ""
        f, cur = stage_of(t)
        if cur is None:
            return S.R.status_line(t.status, t.number, t.lang, t.merged_into)
        keys = [x["key"] for x in f["stages"]]
        i = keys.index(cur["key"]) + 1
        line = f"Your request {t.number} is at step {i} of {len(keys)}: {cur['name']}."
        if cur["key"] != keys[-1]:
            line += f" With {owner_name(cur['owner'])}."
            if t.stage_due_at:
                line += f" Next step expected by {_when(tenant, t.stage_due_at)}."
        if t.customer_line:
            line += f" {t.customer_line}"
        return line


def view(t) -> dict | None:
    """The ticket page's stage block."""
    f, cur = stage_of(t)
    if cur is None:
        return None
    names = {x["key"]: x["name"] for x in f["stages"]}
    due = _aware(t.stage_due_at)
    return {"flow": f["key"], "flow_name": f["name"], "stage": cur["key"], "stage_name": cur["name"],
            "owner": cur["owner"], "owner_name": owner_name(cur["owner"]), "needs": cur.get("needs", []),
            "since": _aware(t.stage_at).isoformat() if t.stage_at else "", "due": due.isoformat() if due else "",
            "late": bool(due and due < now() and t.status in ("new", "open", "pending", "on_hold")),
            "next": [{"key": k, "name": names[k]} for k in f["arrows"].get(cur["key"], [])],
            "stages": [{"key": x["key"], "name": x["name"]} for x in f["stages"]],
            "fields": json.loads(t.fields or "{}") if getattr(t, "fields", "") else {}}


def board(tenant: str) -> list[dict]:
    """Per workflow, per stage: open tickets and how many are past the stage's time."""
    S = _S()
    out = []
    with session() as s:
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all()
        by: dict[tuple[str, str], list] = {}
        for t in rows:
            by.setdefault((t.flow, t.stage), []).append(t)
        for f in flows(tenant):
            st = []
            for x in f["stages"]:
                ts = by.get((f["key"], x["key"]), [])
                late = [t for t in ts if t.stage_due_at and _aware(t.stage_due_at) < now()]
                st.append({"key": x["key"], "name": x["name"], "owner_name": owner_name(x["owner"]), "open": len(ts),
                           "late": len(late), "tickets": [t.number for t in ts][:30]})
            out.append({"key": f["key"], "name": f["name"], "stages": st})
    return out


def stuck(tenant: str, stage: str = "", older_h: float = 0) -> list[dict]:
    """Open tickets past their stage's time (or longer than older_h at a stage)."""
    S = _S()
    out = []
    with session() as s:
        for t in s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all():
            if not t.flow or (stage and t.stage != stage):
                continue
            since = _aware(t.stage_at)
            age = (now() - since).total_seconds() / 3600 if since else 0
            late = bool(t.stage_due_at and _aware(t.stage_due_at) < now())
            if (older_h and age >= older_h) or (not older_h and late):
                f, cur = stage_of(t)
                out.append({"number": t.number, "customer": t.customer_label, "flow": t.flow, "stage": cur["name"] if cur else t.stage,
                            "hours_at_stage": round(age, 1), "owner": owner_name(cur["owner"]) if cur else ""})
    out.sort(key=lambda x: -x["hours_at_stage"])
    return out
