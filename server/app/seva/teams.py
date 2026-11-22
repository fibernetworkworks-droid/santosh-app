"""Teams, queues and rules (G10 of docs/SUPPORT_GLOBAL_PLAN.md).

- PEOPLE (`seva_agents`): her team in the support desk - role, languages, skills, shift (days, hours, time zone), how
  many open tickets they can hold, daily money-approval limit.
- QUEUES (`seva_queues`): Billing, Technical, Spanish, VIP... with members, languages, skills, round-robin or least-busy,
  an overflow queue. Inside a queue: people on shift now, with room, who speak the customer's language and have the
  skill; urgent and VIP first, then the longest waiting.
- ROUTING as data: category / language / country / VIP / channel / brand / words -> queue (first match wins).
- ONE RULE ENGINE (`seva_rules`): when an event happens (ticket created, status changed, stage moved) and its conditions
  hold - now or after a delay ("still open after 2 h") - its actions run once per ticket: queue, assign, priority,
  label, notify a person / role, reply with an approved saved reply, move stage, status.
- ROLES as permission lists (agent, supervisor, admin, finance, auditor, read-only + her own).
- APPROVAL CHAINS for money: amount bands per currency -> the roles that must say yes, in order; each step a person's
  tap on a one-time link bound to that request (or her own tap in the desk); daily limits per person, over the limit
  the step moves up to the next band's role and says why. Hoola still never moves money: approved = she pays.
- MACROS: an approved saved reply + label / stage / status / assignee in one click.
- CUSTOM FIELDS + SAVED VIEWS on tickets.
Honest limits: the desk has one sign-in (hers); her people approve through their links, they do not log in to the desk.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.seva.teams")


class TeamError(Exception):
    pass


class SevaAgent(Base):
    __tablename__ = "seva_agents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sag"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    phone: Mapped[str] = mapped_column(String(24), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(30), default="agent")
    langs: Mapped[str] = mapped_column(Text, default="[]")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    shift: Mapped[str] = mapped_column(Text, default="{}")            # {days: [0..6], start: "09:00", end: "18:00", tz}
    capacity: Mapped[int] = mapped_column(Integer, default=8)
    day_limit: Mapped[float] = mapped_column(Float, default=0.0)       # money approvals a day (0 = no limit of their own)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaQueue(Base):
    __tablename__ = "seva_queues"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sq"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(30), default="")
    name: Mapped[str] = mapped_column(String(80), default="")
    members: Mapped[str] = mapped_column(Text, default="[]")            # agent ids
    langs: Mapped[str] = mapped_column(Text, default="[]")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    strategy: Mapped[str] = mapped_column(String(12), default="least_busy")   # least_busy | round_robin
    overflow: Mapped[str] = mapped_column(String(30), default="")        # another queue's key
    rr: Mapped[int] = mapped_column(Integer, default=0)


class SevaTeamCfg(Base):
    __tablename__ = "seva_team_cfg"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    routes: Mapped[str] = mapped_column(Text, default="[]")            # [{if: {...}, queue}]
    roles: Mapped[str] = mapped_column(Text, default="{}")             # her own roles {name: [perms]}
    bands: Mapped[str] = mapped_column(Text, default="[]")             # [{currency, upto, steps: [role]}]
    fields: Mapped[str] = mapped_column(Text, default="[]")            # [{key, label, type, options}]
    views: Mapped[str] = mapped_column(Text, default="[]")             # [{name, filters}]
    currency: Mapped[str] = mapped_column(String(3), default="INR")


class SevaRule(Base):
    __tablename__ = "seva_rules"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("srl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    event: Mapped[str] = mapped_column(String(20), default="created")
    conditions: Mapped[str] = mapped_column(Text, default="[]")         # [{field, op, value}]
    actions: Mapped[str] = mapped_column(Text, default="[]")            # [{do, value}]
    delay_h: Mapped[float] = mapped_column(Float, default=0.0)
    on: Mapped[bool] = mapped_column(Boolean, default=True)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaRuleRun(Base):
    __tablename__ = "seva_rule_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("srr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    rule_id: Mapped[str] = mapped_column(String(40), index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(80), default="")             # event key: once per rule + ticket + event
    did: Mapped[str] = mapped_column(Text, default="[]")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaApprovalStep(Base):
    __tablename__ = "seva_approval_steps"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sas"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    exc_id: Mapped[str] = mapped_column(String(40), index=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[str] = mapped_column(String(30), default="")
    agent_id: Mapped[str] = mapped_column(String(40), default="")       # '' = her (the owner)
    why: Mapped[str] = mapped_column(Text, default="")                  # e.g. moved up: over Ravi's daily limit
    status: Mapped[str] = mapped_column(String(10), default="waiting")  # waiting | yes | no | skipped
    token_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    bound: Mapped[str] = mapped_column(String(64), default="")          # the request's hash when the step was made
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaAgent, SevaQueue, SevaTeamCfg, SevaRule, SevaRuleRun, SevaApprovalStep):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service
    return service


def _j(v, d):
    try:
        return json.loads(v) if v else d
    except Exception:   # noqa: BLE001
        return d


def _aware(d):
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def _clean(v, n=80) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _list(v, n=20) -> list[str]:
    if isinstance(v, str):
        v = v.split(",")
    return [x for x in (_clean(i, 40).lower() for i in (v or [])) if x][:n]


def _key(v) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(v or "").lower()).strip("_")[:30]


# ---------------------------------------------------------------- roles
PERMS = ("read", "reply", "note", "move", "take", "assign", "approve_money", "refunds", "rules", "team", "export", "settings")
ROLES = {
    "agent": ["read", "reply", "note", "move", "take"],
    "supervisor": ["read", "reply", "note", "move", "take", "assign", "approve_money", "rules", "export"],
    "admin": list(PERMS),
    "finance": ["read", "note", "approve_money", "refunds", "export"],
    "auditor": ["read", "export"],
    "readonly": ["read"],
}
ROLE_ORDER = ["readonly", "auditor", "agent", "finance", "supervisor", "admin", "owner"]


def _cfg(s, tenant: str) -> SevaTeamCfg:
    c = s.get(SevaTeamCfg, tenant)
    if c is None:
        c = SevaTeamCfg(tenant_id=tenant)
        s.add(c)
        s.flush()
    return c


def roles(tenant: str) -> dict[str, list[str]]:
    _ensure()
    with session() as s:
        own = _j(_cfg(s, tenant).roles, {})
    return ROLES | {k: [p for p in v if p in PERMS] for k, v in own.items()}


def save_role(tenant: str, name: str, perms: list[str]) -> dict:
    _ensure()
    k = _key(name)
    if not k or k in ROLES:
        raise TeamError("Give your own role a new name (the six built-in roles stay as they are).")
    bad = [p for p in perms or [] if p not in PERMS]
    if bad:
        raise TeamError("Unknown permission: " + ", ".join(bad))
    with session() as s:
        c = _cfg(s, tenant)
        r = _j(c.roles, {})
        r[k] = list(dict.fromkeys(perms or ["read"]))
        c.roles = json.dumps(r)
    return {"roles": roles(tenant), "say": f"Role {k} saved."}


def can(tenant: str, role: str, perm: str) -> bool:
    return role == "owner" or perm in roles(tenant).get(role, [])


# ---------------------------------------------------------------- people
def _agent_view(a: SevaAgent, tenant: str = "", at: datetime | None = None) -> dict:
    v = {"id": a.id, "name": a.name, "phone": a.phone, "email": a.email, "role": a.role, "langs": _j(a.langs, []),
         "skills": _j(a.skills, []), "shift": _j(a.shift, {}), "capacity": a.capacity, "day_limit": a.day_limit, "active": a.active}
    if tenant:
        v["on_shift"] = on_shift(v, at, tenant)
        v["open"] = load(tenant, a.name)
    return v


def _hm(v: str, d: str) -> str:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", str(v or "").strip())
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m and int(m.group(1)) < 24 and int(m.group(2)) < 60 else d


def save_agent(tenant: str, body: dict, aid: str = "") -> dict:
    _ensure()
    name = _clean(body.get("name"), 80)
    if not name:
        raise TeamError("Write the person's name.")
    role = _key(body.get("role") or "agent")
    if role not in roles(tenant):
        raise TeamError("Unknown role.")
    sh = body.get("shift") or {}
    tz = _clean(sh.get("tz"), 40)
    if tz:
        from zoneinfo import ZoneInfo
        try:
            ZoneInfo(tz)
        except Exception as e:   # noqa: BLE001
            raise TeamError(f"Unknown time zone: {tz}") from e
    shift = {"days": sorted({int(d) for d in (sh.get("days") if sh.get("days") is not None else [0, 1, 2, 3, 4, 5]) if 0 <= int(d) <= 6}),
             "start": _hm(sh.get("start"), "09:00"), "end": _hm(sh.get("end"), "18:00"), "tz": tz}
    if shift["start"] == shift["end"]:
        raise TeamError("The shift's start and end cannot be the same.")
    with session() as s:
        a = s.get(SevaAgent, aid) if aid else None
        if aid and (a is None or a.tenant_id != tenant):
            raise TeamError("This person was not found.")
        if a is None:
            a = SevaAgent(tenant_id=tenant)
            s.add(a)
        a.name, a.role = name, role
        a.phone, a.email = _clean(body.get("phone"), 24), _clean(body.get("email"), 160)
        a.langs, a.skills, a.shift = json.dumps(_list(body.get("langs"))), json.dumps(_list(body.get("skills"))), json.dumps(shift)
        a.capacity = max(1, min(200, int(body.get("capacity") or 8)))
        a.day_limit = max(0.0, float(body.get("day_limit") or 0))
        a.active = body.get("active") is not False
        s.flush()
        return _agent_view(a, tenant)


def agents(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return [_agent_view(a, tenant) for a in s.scalars(select(SevaAgent).where(SevaAgent.tenant_id == tenant)
                                                           .order_by(SevaAgent.created_at)).all()]


def remove_agent(tenant: str, aid: str) -> dict:
    _ensure()
    with session() as s:
        a = s.get(SevaAgent, aid)
        if a is None or a.tenant_id != tenant:
            raise TeamError("This person was not found.")
        a.active = False
        for q in s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant)).all():
            q.members = json.dumps([m for m in _j(q.members, []) if m != aid])
        name = a.name
    return {"say": f"{name} is off the team; their tickets stay with them until someone reassigns."}


def on_shift(agent: dict, at: datetime | None = None, tenant: str = "") -> bool:
    from zoneinfo import ZoneInfo
    sh = agent.get("shift") or {}
    at = _aware(at) or _S().clock()
    try:
        z = ZoneInfo(sh["tz"]) if sh.get("tz") else None
    except Exception:   # noqa: BLE001
        z = None
    loc = at.astimezone(z) if z else _S()._local(tenant or agent.get("tenant", ""), at)
    if not agent.get("active", True):
        return False
    hm = loc.strftime("%H:%M")
    start, end = sh.get("start", "09:00"), sh.get("end", "18:00")
    days = sh.get("days", [0, 1, 2, 3, 4, 5])
    if start < end:
        return loc.weekday() in days and start <= hm < end
    # a night shift that ends after midnight: it belongs to the day it started
    return (loc.weekday() in days and hm >= start) or ((loc.weekday() - 1) % 7 in days and hm < end)


def load(tenant: str, name: str) -> int:
    S = _S()
    with session() as s:
        return len(s.scalars(select(S.SevaTicket.id).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.assignee == name,
                                                           S.SevaTicket.status.in_(S.R.OPEN))).all())


# ---------------------------------------------------------------- queues
def _q_view(q: SevaQueue, people: dict | None = None) -> dict:
    return {"id": q.id, "key": q.key, "name": q.name, "members": _j(q.members, []), "langs": _j(q.langs, []), "skills": _j(q.skills, []),
            "strategy": q.strategy, "overflow": q.overflow,
            "member_names": [people[m]["name"] for m in _j(q.members, []) if people and m in people]}


def save_queue(tenant: str, body: dict) -> dict:
    _ensure()
    name = _clean(body.get("name"), 80)
    key = _key(body.get("key") or name)
    if not key:
        raise TeamError("Give the queue a name.")
    strat = body.get("strategy") or "least_busy"
    if strat not in ("least_busy", "round_robin"):
        raise TeamError("strategy: least_busy or round_robin")
    over = _key(body.get("overflow") or "")
    if over == key:
        raise TeamError("A queue cannot overflow into itself.")
    with session() as s:
        ids = {a.id for a in s.scalars(select(SevaAgent).where(SevaAgent.tenant_id == tenant, SevaAgent.active.is_(True))).all()}
        mem = [m for m in body.get("members") or [] if m in ids]
        q = s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant, SevaQueue.key == key)).first()
        if q is None:
            q = SevaQueue(tenant_id=tenant, key=key)
            s.add(q)
        q.name, q.members, q.strategy, q.overflow = name or key, json.dumps(mem), strat, over
        q.langs, q.skills = json.dumps(_list(body.get("langs"))), json.dumps(_list(body.get("skills")))
        s.flush()
        return _q_view(q)


def queues(tenant: str) -> list[dict]:
    _ensure()
    ppl = {a["id"]: a for a in agents(tenant)}
    with session() as s:
        return [_q_view(q, ppl) for q in s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant)).all()]


def remove_queue(tenant: str, key: str) -> dict:
    _ensure()
    with session() as s:
        q = s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant, SevaQueue.key == key)).first()
        if q is None:
            raise TeamError("This queue was not found.")
        s.delete(q)
    return {"say": "Queue removed; its tickets keep their person."}


# ---------------------------------------------------------------- routing
ROUTE_FIELDS = ("category", "language", "country", "vip", "channel", "brand", "words", "priority")


def _facts(tenant: str, t) -> dict:
    from . import handover as H
    custom = _j(getattr(t, "custom", "") or "", {})
    country = ""
    try:
        d = _S()._digits(t.customer)
        if d:
            from ..callcentre import countries as C
            country = (C.country_of("+" + d) or "").upper()
    except Exception:   # noqa: BLE001
        country = ""
    return {"category": t.category, "language": lang_of_ticket(t, custom), "country": country, "vip": bool(H.is_vip(tenant, t.customer)),
            "channel": t.channel, "brand": str(custom.get("brand") or "").lower(), "priority": t.priority, "text": (t.text or "").lower(),
            "status": t.status, "stage": t.stage or "", "assignee": t.assignee or "", "queue": getattr(t, "queue", "") or "",
            "labels": _j(getattr(t, "labels", "") or "", []), "custom": custom,
            "waiting_h": ((_S().clock() - _aware(t.awaiting_since)).total_seconds() / 3600) if t.awaiting_since else 0.0,
            "age_h": (_S().clock() - _aware(t.created_at)).total_seconds() / 3600}


_NAMES = {"hinglish": "hi", "hindi": "hi", "marathi": "mr", "english": "en"}


def lang_of_ticket(t, custom: dict | None = None) -> str:
    """The customer's language as a code: her custom field 'language' if set, else read from their own words (any
    language, the answer engine's reader), else the desk's language name."""
    custom = custom if custom is not None else _j(getattr(t, "custom", "") or "", {})
    if custom.get("language"):
        return str(custom["language"]).lower()[:10]
    try:
        from . import engine as E
        code = (E.lang_code(t.text or "") or "").lower()
        if code and not (code == "en" and _NAMES.get((t.lang or "").lower(), "en") != "en"):
            return code
    except Exception:   # noqa: BLE001
        pass
    return _NAMES.get((t.lang or "").lower(), (t.lang or "")[:10].lower())


def _lang_ok(want: str, have: list[str]) -> bool:
    if not have or not want:
        return True
    w = want[:2]
    return any(h[:2] == w or h == want for h in have)


def save_routes(tenant: str, routes: list[dict]) -> dict:
    _ensure()
    keys = {q["key"] for q in queues(tenant)}
    out = []
    for r in (routes or [])[:50]:
        cond = {k: v for k, v in (r.get("if") or {}).items() if k in ROUTE_FIELDS and v not in ("", None, [])}
        q = _key(r.get("queue"))
        if q not in keys:
            raise TeamError(f"Queue '{r.get('queue')}' does not exist.")
        if "vip" in cond:
            cond["vip"] = bool(cond["vip"])
        for k in ("category", "language", "country", "channel", "brand", "words", "priority"):
            if k in cond:
                cond[k] = _list(cond[k])
        out.append({"if": cond, "queue": q})
    with session() as s:
        _cfg(s, tenant).routes = json.dumps(out)
    return {"routes": out, "say": f"{len(out)} routing rule(s) saved. The first that matches wins."}


def routes(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return _j(_cfg(s, tenant).routes, [])


def _match_route(cond: dict, f: dict) -> bool:
    for k, v in cond.items():
        if k == "vip":
            if bool(v) != f["vip"]:
                return False
        elif k == "words":
            if not any(w in f["text"] for w in v):
                return False
        elif k == "language":
            if not any(f["language"][:2] == x[:2] for x in v):
                return False
        elif k == "country":
            if f["country"].lower() not in v:
                return False
        elif str(f.get(k, "")).lower() not in v:
            return False
    return True


def queue_for(tenant: str, t) -> str:
    f = _facts(tenant, t)
    for r in routes(tenant):
        if _match_route(r["if"], f):
            return r["queue"]
    return ""


def pick_person(tenant: str, qkey: str, t, at: datetime | None = None, seen: set | None = None) -> tuple[str, str, str]:
    """-> (queue key, person name, why). People on shift now, with room, who speak the language and have the skill;
    nobody = the overflow queue (once round); still nobody = the queue with nobody named (the queue board shows it)."""
    seen = seen or set()
    seen.add(qkey)
    with session() as s:
        q = s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant, SevaQueue.key == qkey)).first()
        if q is None:
            return "", "", "no such queue"
        mem, strat, over, rr = _j(q.members, []), q.strategy, q.overflow, q.rr
        need = _j(q.skills, [])
        ppl = [_agent_view(a) for a in s.scalars(select(SevaAgent).where(SevaAgent.tenant_id == tenant, SevaAgent.id.in_(mem))).all()]
    order = {m: i for i, m in enumerate(mem)}
    ppl.sort(key=lambda a: order.get(a["id"], 99))
    lang = lang_of_ticket(t)
    ok = []
    for a in ppl:
        if not a["active"] or a["role"] in ("readonly", "auditor") or not on_shift(a, at, tenant):
            continue
        if not _lang_ok(lang, a["langs"]):
            continue
        if need and not set(need) & set(a["skills"]):
            continue
        n = load(tenant, a["name"])
        if n >= a["capacity"]:
            continue
        ok.append((a, n))
    if ok:
        if strat == "round_robin":
            a = ok[rr % len(ok)][0]
            with session() as s:
                q = s.scalars(select(SevaQueue).where(SevaQueue.tenant_id == tenant, SevaQueue.key == qkey)).first()
                q.rr = rr + 1
            return qkey, a["name"], "round robin"
        a, n = min(ok, key=lambda x: x[1])
        return qkey, a["name"], f"least busy ({n} open)"
    if over and over not in seen:
        q2, who, why = pick_person(tenant, over, t, at, seen)
        if q2:                                       # it waits in the overflow queue even when nobody there is free yet
            return q2, who, f"overflow from {qkey}: " + why
    return qkey, "", "nobody on shift with room"


def route(tenant: str, ticket_id: str, by: str = "hoola") -> dict:
    """A new ticket: the queue by her routing, the person inside it. A ticket that already has a person keeps them."""
    _ensure()
    S = _S()
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        if t is None or t.assignee:
            return {}
        qk = queue_for(tenant, t)
        if not qk:
            return {}
        q, who, why = pick_person(tenant, qk, t)
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        t.queue = q
        if who:
            t.assignee = who
        S._add_note(t, by, f"Routed to queue {q}" + (f", given to {who} ({why})." if who else f" ({why})."))
    return {"queue": q, "assignee": who, "why": why}


def board(tenant: str) -> list[dict]:
    """Every queue: who is on shift and how full, and the waiting tickets - urgent and VIP first, then longest waiting."""
    _ensure()
    S = _S()
    from . import handover as H
    out = []
    ppl = {a["id"]: a for a in agents(tenant)}
    with session() as s:
        st = S._st(s, tenant)
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all()
        tix = [(t.queue or "", t.assignee, S._ticket_view(t, st), H.is_vip(tenant, t.customer), _aware(t.awaiting_since or t.created_at))
               for t in rows]
    for q in queues(tenant) + [{"key": "", "name": "Not in a queue", "members": []}]:
        mine = [x for x in tix if x[0] == q["key"]]
        mine.sort(key=lambda x: (x[2]["priority"] != "urgent", not x[3], x[4]))
        out.append({"key": q["key"], "name": q["name"],
                    "people": [{"name": ppl[m]["name"], "on_shift": ppl[m]["on_shift"], "open": ppl[m]["open"], "capacity": ppl[m]["capacity"]}
                               for m in q["members"] if m in ppl],
                    "waiting": [{"number": v["number"], "customer": v["customer"], "priority": v["priority"], "vip": vip,
                                 "assignee": who, "since": since.isoformat() if since else "", "text": v["text"][:120]}
                                for _, who, v, vip, since in mine]})
    return [b for b in out if b["key"] or b["waiting"]]


# ---------------------------------------------------------------- the rule engine
EVENTS = {"created": "A ticket is created", "status": "A ticket's status changes", "stage": "A ticket moves stage"}
OPS = ("is", "is_not", "in", "contains", "more_than", "less_than", "empty", "not_empty")
COND_FIELDS = ("category", "priority", "status", "channel", "language", "country", "vip", "queue", "stage", "assignee", "labels",
               "text", "waiting_h", "age_h", "custom")
ACTIONS = ("queue", "assign", "priority", "label", "notify", "reply", "stage", "status")


def _clean_rule(body: dict) -> dict:
    ev = body.get("event") or "created"
    if ev not in EVENTS:
        raise TeamError("event: " + " | ".join(EVENTS))
    conds = []
    for c in (body.get("conditions") or [])[:12]:
        f, op = str(c.get("field") or ""), str(c.get("op") or "is")
        if f.startswith("custom."):
            pass
        elif f not in COND_FIELDS:
            raise TeamError(f"Unknown condition field: {f}")
        if op not in OPS:
            raise TeamError(f"Unknown condition: {op}")
        conds.append({"field": f, "op": op, "value": c.get("value")})
    acts = []
    for a in (body.get("actions") or [])[:8]:
        d = str(a.get("do") or "")
        if d not in ACTIONS:
            raise TeamError(f"Unknown action: {d}")
        acts.append({"do": d, "value": _clean(a.get("value"), 200)})
    if not acts:
        raise TeamError("A rule needs at least one action.")
    delay = max(0.0, min(24 * 30, float(body.get("delay_h") or 0)))
    return {"name": _clean(body.get("name"), 120) or "Rule", "event": ev, "conditions": conds, "actions": acts, "delay_h": delay,
            "on": body.get("on") is not False}


def _rule_view(r: SevaRule) -> dict:
    return {"id": r.id, "name": r.name, "event": r.event, "conditions": _j(r.conditions, []), "actions": _j(r.actions, []),
            "delay_h": r.delay_h, "on": r.on, "runs": r.runs}


def save_rule(tenant: str, body: dict, rid: str = "") -> dict:
    _ensure()
    c = _clean_rule(body)
    with session() as s:
        r = s.get(SevaRule, rid) if rid else None
        if rid and (r is None or r.tenant_id != tenant):
            raise TeamError("This rule was not found.")
        if r is None:
            r = SevaRule(tenant_id=tenant)
            s.add(r)
        r.name, r.event, r.delay_h, r.on = c["name"], c["event"], c["delay_h"], c["on"]
        r.conditions, r.actions = json.dumps(c["conditions"]), json.dumps(c["actions"])
        s.flush()
        return _rule_view(r)


def rules_list(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return [_rule_view(r) for r in s.scalars(select(SevaRule).where(SevaRule.tenant_id == tenant).order_by(SevaRule.created_at)).all()]


def remove_rule(tenant: str, rid: str) -> dict:
    _ensure()
    with session() as s:
        r = s.get(SevaRule, rid)
        if r is None or r.tenant_id != tenant:
            raise TeamError("This rule was not found.")
        s.delete(r)
    return {"say": "Rule removed."}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def holds(cond: dict, f: dict) -> bool:
    field, op, val = cond["field"], cond["op"], cond.get("value")
    if field.startswith("custom."):
        have = f["custom"].get(field.split(".", 1)[1], "")
    else:
        have = f.get(field, "")
    if op == "empty":
        return have in ("", None, [], 0, False)
    if op == "not_empty":
        return have not in ("", None, [], 0, False)
    if op in ("more_than", "less_than"):
        return _num(have) > _num(val) if op == "more_than" else _num(have) < _num(val)
    if isinstance(have, bool):
        want = str(val).lower() in ("1", "true", "yes")
        return (have == want) if op != "is_not" else (have != want)
    vals = _list(val) if op == "in" else [str(val or "").lower()]
    if isinstance(have, list):
        hv = [str(x).lower() for x in have]
        hit = any(v in hv for v in vals)
    elif op == "contains":
        hit = str(val or "").lower() in str(have).lower()
    else:
        hit = str(have).lower() in vals
    return not hit if op == "is_not" else hit


def _do(tenant: str, ticket_id: str, a: dict, rule: str) -> str:
    S = _S()
    d, v = a["do"], a["value"]
    if d == "queue":
        with session() as s:
            t = s.get(S.SevaTicket, ticket_id)
        q, who, why = pick_person(tenant, _key(v), t)
        if not q:
            return f"queue {v}: not found"
        with session() as s:
            t = s.get(S.SevaTicket, ticket_id)
            t.queue = q
            if who:
                t.assignee = who
        return f"queue {q}" + (f" -> {who}" if who else "")
    if d == "assign":
        with session() as s:
            ok = s.scalars(select(SevaAgent).where(SevaAgent.tenant_id == tenant, SevaAgent.name == v, SevaAgent.active.is_(True))).first()
            if ok is None or not can(tenant, ok.role, "take"):
                return f"assign {v}: not a person who can take tickets"
            s.get(S.SevaTicket, ticket_id).assignee = v
        return f"assigned {v}"
    if d == "priority":
        if v not in S.R.PRIORITIES:
            return f"priority {v}: unknown"
        with session() as s:
            s.get(S.SevaTicket, ticket_id).priority = v
        return f"priority {v}"
    if d == "label":
        with session() as s:
            t = s.get(S.SevaTicket, ticket_id)
            lab = _j(t.labels or "", [])
            if v and v not in lab:
                lab.append(_clean(v, 40))
            t.labels = json.dumps(lab[:20])
        return f"label {v}"
    if d == "notify":
        with session() as s:
            t = s.get(S.SevaTicket, ticket_id)
            number, cust = t.number, t.customer_label
            people = [a.name for a in s.scalars(select(SevaAgent).where(SevaAgent.tenant_id == tenant, SevaAgent.active.is_(True))).all()
                      if a.name == v or a.role == _key(v)]
        S._publish(tenant, "seva_rule", {"ticket": number, "to": people or [v], "text": f"{rule}: {number} ({cust}) needs a look."})
        S._note_chat(tenant, f"Rule '{rule}': {number} ({cust}) needs a look by {', '.join(people) or v} (information, not an instruction).")
        return f"notified {', '.join(people) or v}"
    if d == "reply":
        with session() as s:
            t = s.get(S.SevaTicket, ticket_id)
            lang = t.lang
            m = s.scalars(select(S.SevaMacro).where(S.SevaMacro.tenant_id == tenant, S.SevaMacro.name == v)).first()
            ok = m is not None and m.status == "approved"
        if not ok:
            return f"reply '{v}': only an approved saved reply is sent"
        text = S.macro_text(tenant, v, lang, {})
        S._tell(tenant, ticket_id, text)
        return f"replied with '{v}'"
    if d == "stage":
        from . import flow as FL
        try:
            FL.move(tenant, ticket_id, _key(v), by="rule", why=f"rule {rule}", system=True)
            return f"stage {v}"
        except Exception as e:   # noqa: BLE001
            return f"stage {v}: {str(e)[:80]}"
    if d == "status":
        try:
            S.update(tenant, ticket_id, status=v, by="rule", tell=True)
            return f"status {v}"
        except Exception as e:   # noqa: BLE001
            return f"status {v}: {str(e)[:80]}"
    return "?"


_FIRING: set = set()


def _run(tenant: str, r: dict, ticket_id: str, key: str) -> list[str] | None:
    with session() as s:
        if s.scalars(select(SevaRuleRun).where(SevaRuleRun.rule_id == r["id"], SevaRuleRun.ticket_id == ticket_id,
                                               SevaRuleRun.key == key)).first():
            return None
        run = SevaRuleRun(tenant_id=tenant, rule_id=r["id"], ticket_id=ticket_id, key=key, at=_S().clock())
        s.add(run)
        s.flush()
        rid = run.id
    did = [_do(tenant, ticket_id, a, r["name"]) for a in r["actions"]]
    with session() as s:
        s.get(SevaRuleRun, rid).did = json.dumps(did)
        rr = s.get(SevaRule, r["id"])
        rr.runs = (rr.runs or 0) + 1
        t = s.get(_S().SevaTicket, ticket_id)
        _S()._add_note(t, "rule", f"Rule '{r['name']}': " + "; ".join(did))
    return did


def fire(tenant: str, event: str, ticket_id: str, key: str = "") -> list[dict]:
    """An event on a ticket: every rule for it with no delay whose conditions hold runs now (once per event key).
    Delayed rules are checked by `sweep` when their delay has passed."""
    _ensure()
    if (tenant, ticket_id) in _FIRING:            # a rule's own action never sets off more rules in the same moment
        return []
    S = _S()
    ran = []
    _FIRING.add((tenant, ticket_id))
    try:
        for r in rules_list(tenant):
            if not r["on"] or r["event"] != event or r["delay_h"]:
                continue
            with session() as s:
                t = s.get(S.SevaTicket, ticket_id)
                if t is None:
                    return ran
                f = _facts(tenant, t)
            if all(holds(c, f) for c in r["conditions"]):
                did = _run(tenant, r, ticket_id, f"{event}:{key}")
                if did is not None:
                    ran.append({"rule": r["name"], "did": did})
    finally:
        _FIRING.discard((tenant, ticket_id))
    return ran


def sweep(tenant: str, at: datetime | None = None) -> int:
    """Delayed rules: 'still open 2 hours after it was created' - checked against the ticket as it is NOW."""
    _ensure()
    S = _S()
    at = _aware(at) or S.clock()
    n = 0
    for r in rules_list(tenant):
        if not r["on"] or not r["delay_h"]:
            continue
        since = at - timedelta(hours=r["delay_h"])
        with session() as s:
            sel = select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant)
            if r["event"] == "created":
                sel = sel.where(S.SevaTicket.created_at <= since, S.SevaTicket.created_at >= since - timedelta(days=14))
            elif r["event"] == "stage":
                sel = sel.where(S.SevaTicket.stage_at.is_not(None), S.SevaTicket.stage_at <= since)
            else:
                sel = sel.where(S.SevaTicket.updated_at <= since, S.SevaTicket.updated_at >= since - timedelta(days=14))
            rows = [(t.id, _facts(tenant, t), (t.stage or "") + (_aware(t.stage_at).isoformat() if t.stage_at else "")
                     if r["event"] == "stage" else t.status) for t in s.scalars(sel.limit(500)).all()]
        for tid, f, k in rows:
            if all(holds(c, f) for c in r["conditions"]):
                if _run(tenant, r, tid, f"{r['event']}+{r['delay_h']}:{k}") is not None:
                    n += 1
    return n


def sweep_all() -> int:
    _ensure()
    with session() as s:
        tenants = sorted({r.tenant_id for r in s.scalars(select(SevaRule).where(SevaRule.on.is_(True), SevaRule.delay_h > 0)).all()})
    n = 0
    for t in tenants:
        try:
            n += sweep(t)
        except Exception:   # noqa: BLE001
            log.exception("seva rules sweep")
    return n


# ---------------------------------------------------------------- approval chains for money
def save_bands(tenant: str, bands: list[dict], currency: str = "") -> dict:
    _ensure()
    rs = roles(tenant)
    out = []
    for b in (bands or [])[:20]:
        cur = re.sub(r"[^A-Z]", "", str(b.get("currency") or "INR").upper())[:3] or "INR"
        upto = float(b.get("upto") or 0)
        steps = [_key(x) for x in (b.get("steps") or []) if _key(x)]
        if not steps:
            raise TeamError("Each amount band needs at least one role that says yes.")
        bad = [x for x in steps if x != "owner" and not can(tenant, x, "approve_money")]
        if bad:
            raise TeamError(f"Role(s) {', '.join(bad)} cannot approve money (give them approve_money first).")
        if any(x not in rs and x != "owner" for x in steps):
            raise TeamError("Unknown role in a band.")
        out.append({"currency": cur, "upto": upto, "steps": steps})
    out.sort(key=lambda b: (b["currency"], b["upto"] or 1e18))
    with session() as s:
        c = _cfg(s, tenant)
        c.bands = json.dumps(out)
        if currency:
            c.currency = re.sub(r"[^A-Z]", "", currency.upper())[:3] or c.currency
    return {"bands": out, "say": f"{len(out)} amount band(s) saved."}


def bands(tenant: str) -> dict:
    _ensure()
    with session() as s:
        c = _cfg(s, tenant)
        return {"bands": _j(c.bands, []), "currency": c.currency}


def chain_for(tenant: str, amount: float, currency: str = "") -> list[str]:
    b = bands(tenant)
    cur = (currency or b["currency"]).upper()
    mine = [x for x in b["bands"] if x["currency"] == cur]
    for x in mine:
        if not x["upto"] or amount <= x["upto"]:
            return list(x["steps"])
    return list(mine[-1]["steps"]) + ["owner"] if mine else []


def _approved_today(tenant: str, agent_id: str) -> float:
    S = _S()
    day0 = S.clock().replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        return sum(x.amount for x in s.scalars(select(SevaApprovalStep).where(
            SevaApprovalStep.tenant_id == tenant, SevaApprovalStep.agent_id == agent_id, SevaApprovalStep.status == "yes",
            SevaApprovalStep.decided_at >= day0)).all())


LADDER = ["supervisor", "finance", "admin", "owner"]


def _higher(role: str, chain_roles: list[str] | None = None) -> str:
    """The next role up when nobody in this one can take a money step (her own roles start at supervisor)."""
    return LADDER[LADDER.index(role) + 1] if role in LADDER[:-1] else ("supervisor" if role not in LADDER else "owner")


def _approver(tenant: str, role: str, amount: float, skip: set) -> tuple[str, str, str]:
    """-> (role, agent id or '' for her, why). Over a person's daily limit = the next role up, said."""
    why = ""
    while role != "owner":
        with session() as s:
            every = [(a.id, a.name, a.day_limit) for a in s.scalars(select(SevaAgent).where(
                SevaAgent.tenant_id == tenant, SevaAgent.role == role, SevaAgent.active.is_(True))).all()]
        ppl = [x for x in every if x[0] not in skip]
        for aid, name, lim in ppl:
            if not lim or _approved_today(tenant, aid) + amount <= lim:
                return role, aid, why
        nxt = _higher(role, [])
        reason = (f"no {role} has room under their daily limit" if ppl else
                  f"every {role} already said yes on an earlier step" if every else f"nobody has the role {role}")
        why = (why + "; " if why else "") + reason + f", moved up to {'you' if nxt == 'owner' else nxt}"
        role = nxt
    return "owner", "", why


def _token_hash(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def start_chain(tenant: str, exc_id: str) -> list[dict]:
    """A money request: the steps of her amount bands. No bands = her own tap only (as before)."""
    _ensure()
    S = _S()
    with session() as s:
        e = s.get(S.SevaException, exc_id)
        if e is None or e.kind not in S.R.MONEY_KINDS or not e.amount:
            return []
        amount, bound = e.amount, S._exc_hash(e)
    steps = chain_for(tenant, amount)
    if not steps:
        return []
    with session() as s:
        for i, role in enumerate(steps):
            s.add(SevaApprovalStep(tenant_id=tenant, exc_id=exc_id, n=i, role=role, bound=bound, amount=amount, at=S.clock()))
    _open_next(tenant, exc_id)
    return chain(tenant, exc_id)


def _open_next(tenant: str, exc_id: str) -> dict | None:
    """The next waiting step gets its person (limits checked now) and a one-time link."""
    S = _S()
    with session() as s:
        st = s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.exc_id == exc_id, SevaApprovalStep.status == "waiting")
                       .order_by(SevaApprovalStep.n)).first()
        if st is None:
            return None
        if st.token_hash:
            return {"id": st.id}
        used = {x.agent_id for x in s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.exc_id == exc_id,
                                                                             SevaApprovalStep.status == "yes")).all() if x.agent_id}
        sid, role, amount = st.id, st.role, st.amount
    role2, aid, why = _approver(tenant, role, amount, used)
    tok = secrets.token_urlsafe(24)
    with session() as s:
        st = s.get(SevaApprovalStep, sid)
        st.role, st.agent_id, st.why, st.token_hash = role2, aid, why[:400], _token_hash(tok)
    _LINKS[sid] = tok
    who = "you" if not aid else _agent_name(aid)
    S._publish(tenant, "seva_approval_step", {"exception": exc_id, "step": sid, "to": who, "why": why})
    return {"id": sid, "token": tok}


_LINKS: dict[str, str] = {}      # the newest link of each step, for her to share (in memory; a new one replaces it)


def _agent_name(aid: str) -> str:
    with session() as s:
        a = s.get(SevaAgent, aid)
        return a.name if a else ""


def new_link(tenant: str, step_id: str) -> str:
    _ensure()
    tok = secrets.token_urlsafe(24)
    with session() as s:
        st = s.get(SevaApprovalStep, step_id)
        if st is None or st.tenant_id != tenant or st.status != "waiting" or not st.agent_id:
            raise TeamError("This step is not waiting for a person.")
        st.token_hash = _token_hash(tok)
    _LINKS[step_id] = tok
    return tok


def chain(tenant: str, exc_id: str) -> list[dict]:
    _ensure()
    from ..config import get_settings
    base = (get_settings().public_base_url or "").rstrip("/")
    with session() as s:
        rows = s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.tenant_id == tenant, SevaApprovalStep.exc_id == exc_id)
                         .order_by(SevaApprovalStep.n)).all()
        out = []
        for st in rows:
            tok = _LINKS.get(st.id, "")
            out.append({"id": st.id, "n": st.n + 1, "role": st.role, "person": _agent_name(st.agent_id) if st.agent_id else
                        ("you" if st.token_hash or st.status != "waiting" else ""), "why": st.why, "status": st.status,
                        "note": st.note, "decided": _aware(st.decided_at).isoformat() if st.decided_at else "",
                        "link": f"{base}/support/approve/{tok}" if tok and st.status == "waiting" and st.agent_id else ""})
    return out


def step_by_token(tok: str) -> dict:
    _ensure()
    S = _S()
    with session() as s:
        st = s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.token_hash == _token_hash(str(tok or "")))).first()
        if st is None or st.status != "waiting":
            raise TeamError("This approval link is no longer valid.")
        if S.clock() - _aware(st.at) > timedelta(days=7):
            raise TeamError("This approval link has expired; ask for a new one.")
        e = s.get(S.SevaException, st.exc_id)
        if e is None or e.status != "pending":
            raise TeamError("This request has already been decided.")
        if S._exc_hash(e) != st.bound:
            raise TeamError("The request changed after the link was made; ask for a new one.")
        v = S._exc_view(e)
        return {"step": st.id, "tenant": st.tenant_id, "role": st.role, "person": _agent_name(st.agent_id),
                "request": {"number": v["number"], "kind": v["kind_label"], "amount": v["amount_text"], "customer": v["customer"],
                            "reason": v["reason"], "within": (v.get("check") or {}).get("within")}, "bound": st.bound}


def decide_step(tok: str, yes: bool, note: str = "") -> dict:
    """A person's tap on their own one-time link. The link is bound to the request as it was; a changed request needs a
    new link. The last yes = approved (she pays; Hoola never moves money). Any no = declined."""
    info = step_by_token(tok)
    S = _S()
    tenant, sid = info["tenant"], info["step"]
    if note and S._secret(note):
        raise TeamError("The note holds details that are not allowed.")
    with session() as s:
        st = s.get(SevaApprovalStep, sid)
        st.status, st.decided_at, st.note, st.token_hash = ("yes" if yes else "no"), S.clock(), S.mask(_clean(note, 400)), ""
        exc_id, who = st.exc_id, _agent_name(st.agent_id)
    _LINKS.pop(sid, None)
    if not yes:
        _finish(tenant, exc_id, False, f"declined by {who}" + (f": {note[:200]}" if note else ""))
        return {"say": "Declined. The request is closed."}
    nxt = _open_next(tenant, exc_id)
    if nxt is None:
        _finish(tenant, exc_id, True, f"approved through the chain (last: {who})")
        return {"say": "Approved. The owner pays it from her own bank or gateway; the customer is told."}
    return {"say": "Thank you. The request moves to the next person."}


def _finish(tenant: str, exc_id: str, yes: bool, note: str) -> None:
    S = _S()
    S._settle(tenant, exc_id, yes, note=note, amount=None, by="chain")


def owner_decided(tenant: str, exc_id: str) -> None:
    """Her own tap in the desk decides the whole request: waiting steps are closed."""
    _ensure()
    with session() as s:
        for st in s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.exc_id == exc_id, SevaApprovalStep.status == "waiting")).all():
            st.status, st.token_hash, st.note = "skipped", "", "the owner decided"
            _LINKS.pop(st.id, None)


def waiting_on_chain(tenant: str, exc_id: str) -> bool:
    _ensure()
    with session() as s:
        return s.scalars(select(SevaApprovalStep).where(SevaApprovalStep.exc_id == exc_id, SevaApprovalStep.status == "waiting",
                                                        SevaApprovalStep.agent_id != "")).first() is not None


# ---------------------------------------------------------------- macros with actions, custom fields, saved views
def set_macro_actions(tenant: str, macro_id: str, actions: dict) -> dict:
    S = _S()
    keep = {k: _clean(v, 60) for k, v in (actions or {}).items() if k in ("label", "stage", "status", "assign") and v}
    if keep.get("status") and keep["status"] not in S.R.STATUSES:
        raise TeamError("Unknown status.")
    with session() as s:
        m = s.get(S.SevaMacro, macro_id)
        if m is None or m.tenant_id != tenant:
            raise TeamError("This saved reply was not found.")
        m.actions = json.dumps(keep)
        name = m.name
    return {"say": f"'{name}' now also does: " + (", ".join(f"{k} {v}" for k, v in keep.items()) or "nothing else")}


def run_macro(tenant: str, ref: str, macro_id: str, by: str = "owner") -> dict:
    """One click: the approved reply in the customer's language + its label / stage / status / person."""
    S = _S()
    with session() as s:
        m = s.get(S.SevaMacro, macro_id)
        if m is None or m.tenant_id != tenant:
            raise TeamError("This saved reply was not found.")
        if m.status != "approved":
            raise TeamError("Approve the saved reply first; only approved replies go to customers.")
        t = S._find_ticket(s, tenant, ref)
        tid, lang, name, acts = t.id, t.lang, m.name, _j(getattr(m, "actions", "") or "", {})
        m.uses = (m.uses or 0) + 1
    text = S.macro_text(tenant, name, lang, {})
    told = S._tell(tenant, tid, text, first=True, sender=by if by != "owner" else "")
    did = []
    for k in ("label", "assign", "stage", "status"):
        if acts.get(k):
            did.append(_do(tenant, tid, {"do": k, "value": acts[k]}, f"saved reply {name}"))
    return {"told": told, "did": did, "say": f"Sent '{name}'" + (" and " + "; ".join(did) if did else "") + "."}


FIELD_TYPES = ("text", "number", "date", "choice")


def save_fields(tenant: str, fields: list[dict]) -> dict:
    _ensure()
    out = []
    for f in (fields or [])[:30]:
        k = _key(f.get("key") or f.get("label"))
        ty = f.get("type") or "text"
        if not k or ty not in FIELD_TYPES:
            raise TeamError("Each field needs a name and a type (text, number, date, choice).")
        opts = _list(f.get("options"), 30) if ty == "choice" else []
        if ty == "choice" and not opts:
            raise TeamError(f"The choice field '{k}' needs its options.")
        out.append({"key": k, "label": _clean(f.get("label") or k, 60), "type": ty, "options": opts})
    with session() as s:
        _cfg(s, tenant).fields = json.dumps(out)
    return {"fields": out, "say": f"{len(out)} custom field(s) saved."}


def fields(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return _j(_cfg(s, tenant).fields, [])


def set_custom(tenant: str, ref: str, values: dict) -> dict:
    S = _S()
    defs = {f["key"]: f for f in fields(tenant)}
    clean = {}
    for k, v in (values or {}).items():
        f = defs.get(k)
        if f is None:
            raise TeamError(f"Unknown field: {k}")
        v = _clean(v, 200)
        if v and f["type"] == "number":
            try:
                float(v)
            except ValueError as e:
                raise TeamError(f"{f['label']} must be a number.") from e
        if v and f["type"] == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise TeamError(f"{f['label']} must be a date (YYYY-MM-DD).")
        if v and f["type"] == "choice" and v.lower() not in f["options"]:
            raise TeamError(f"{f['label']}: one of " + ", ".join(f["options"]))
        if S._secret(v):
            raise TeamError("This holds details like an OTP / PIN / card.")
        clean[k] = v
    with session() as s:
        t = S._find_ticket(s, tenant, ref)
        cur = _j(t.custom or "", {})
        cur.update(clean)
        t.custom = json.dumps({k: v for k, v in cur.items() if v})
        return {"custom": _j(t.custom, {})}


VIEW_FILTERS = ("queue", "status", "priority", "assignee", "label", "category", "channel")


def save_view(tenant: str, name: str, filters: dict) -> dict:
    _ensure()
    n = _clean(name, 60)
    if not n:
        raise TeamError("Name the view.")
    fl = {k: _clean(v, 60) for k, v in (filters or {}).items() if v and (k in VIEW_FILTERS or k.startswith("custom."))}
    with session() as s:
        c = _cfg(s, tenant)
        vs = [v for v in _j(c.views, []) if v["name"] != n]
        vs.append({"name": n, "filters": fl})
        c.views = json.dumps(vs[-30:])
    return {"views": views(tenant), "say": f"View '{n}' saved."}


def views(tenant: str) -> list[dict]:
    _ensure()
    with session() as s:
        return _j(_cfg(s, tenant).views, [])


def remove_view(tenant: str, name: str) -> dict:
    _ensure()
    with session() as s:
        c = _cfg(s, tenant)
        c.views = json.dumps([v for v in _j(c.views, []) if v["name"] != name])
    return {"views": views(tenant)}


def view_tickets(tenant: str, name: str) -> dict:
    S = _S()
    v = next((x for x in views(tenant) if x["name"] == name), None)
    if v is None:
        raise TeamError("This view was not found.")
    fl = v["filters"]
    with session() as s:
        st = S._st(s, tenant)
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant).order_by(S.SevaTicket.updated_at.desc()).limit(500)).all()
        out = []
        for t in rows:
            ok = True
            for k, want in fl.items():
                if k == "status" and want == "open":
                    ok = t.status in S.R.OPEN
                elif k == "label":
                    ok = want.lower() in [x.lower() for x in _j(t.labels or "", [])]
                elif k.startswith("custom."):
                    ok = str(_j(t.custom or "", {}).get(k.split(".", 1)[1], "")).lower() == want.lower()
                elif k == "queue":
                    ok = (t.queue or "") == want
                else:
                    ok = str(getattr(t, k, "") or "").lower() == want.lower()
                if not ok:
                    break
            if ok:
                out.append(S._ticket_view(t, st))
    return {"view": v, "tickets": out[:200]}


# ---------------------------------------------------------------- one page for the desk
def overview(tenant: str) -> dict:
    from . import flow as FL
    return {"people": agents(tenant), "queues": queues(tenant), "routes": routes(tenant), "rules": rules_list(tenant),
            "roles": roles(tenant), "builtin_roles": list(ROLES), "perms": list(PERMS), "bands": bands(tenant),
            "fields": fields(tenant), "views": views(tenant), "board": board(tenant), "events": EVENTS, "ops": list(OPS),
            "cond_fields": list(COND_FIELDS), "actions": list(ACTIONS), "route_fields": list(ROUTE_FIELDS),
            "stages": sorted({x["key"] for f in FL.flows(tenant) for x in f.get("stages", [])}),
            "macros": [{"id": m["id"], "name": m["name"], "status": m["status"], "actions": m.get("actions", {})} for m in _S().macros(tenant)],
            "not_built": ["Sign-ins to the desk for each person (her people approve money on their own one-time links)",
                          "Rules on a customer's new message (rules run on ticket created / status / stage, now or after a delay)"]}
