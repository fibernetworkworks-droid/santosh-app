"""G9 of docs/SUPPORT_GLOBAL_PLAN.md: watching every ticket until it is truly solved.

- Working hours: her week (per day, in HER time zone) and holidays, or 24/7. Every clock - first reply, every next
  reply, time at a stage, time to solve - counts only working time when she set hours; pauses for "waiting" stages
  still stop the clock.
- Solved only when the customer says so: a ticket that reaches a "solved" stage (or status) gets a "Did this fix it?"
  check. YES closes it (recorded as confirmed by the customer), NO sends it back to the stage it was at. No answer
  within her quiet period closes it, recorded that way. A customer who writes again on the same problem within her
  reopen window reopens it (counted, and she is told). A rating 1-5 is asked after closing when she wants ratings.
- The reminder ladder (her rules): before a deadline the ticket's owner is reminded, at the deadline again + her
  supervisor, past it by her chosen hours she is told with the list, then it repeats on her schedule until the ticket
  moves - never in her quiet hours, never more than her daily cap per ticket. Every reminder is recorded.
- The customer is kept informed: "still on it" with the real stage when nothing moved for her chosen hours.
- A morning list per person (their open, late and about-to-be-late tickets) and a stuck list with the reason.

Reminders reach the business app (push + the desk). A named person's own phone / Slack comes with queues and people
(G10); until then the reminder says whose it is.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger(__name__)

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DEFAULTS = {"hours_on": False, "week": {d: (["09:00", "18:00"] if d not in ("sun",) else []) for d in DAYS}, "holidays": [],
            "ladder_on": True, "before_h": 1.0, "boss_after_h": 4.0, "repeat_h": 4.0, "max_day": 6,
            "quiet": ["21:00", "08:00"], "supervisor": "", "update_h": 24.0, "confirm_days": 3.0, "reopen_days": 7.0,
            "confirm_on": True}
CONFIRM_KEYS = ("confirmed", "solved", "confirm", "resolved_check")
YES = re.compile(r"^\s*(yes|y|yeah|yep|ok|okay|done|fixed|working|works|it works|resolved|haan|ha|han|hanji|ho gaya|hogaya|theek|thik|"
                 r"sahi|si|sí|oui|ja|sim|да|نعم|हाँ|हां|हो गया|ठीक|होय)\b[\s!.]*", re.I)
NO = re.compile(r"^\s*(no|nope|nah|not yet|still|not working|nahi|nahin|na|abhi nahi|no funciona|non|nein|não|нет|لا|नहीं|नाही)\b", re.I)
CHECK_ASK = "Your request {n} was marked solved. Did this fix it? Reply YES or NO."


class WatchError(Exception):
    pass


class SevaReminder(Base):
    """One reminder, customer update or confirmation step that was sent (append-only)."""
    __tablename__ = "seva_reminders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("srm"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(30), default="")
    kind: Mapped[str] = mapped_column(String(20), default="")       # before | due | boss | repeat | update | check | closed_quiet | reopen
    deadline: Mapped[str] = mapped_column(String(40), default="")   # which deadline this was about (iso)
    to: Mapped[str] = mapped_column(String(120), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        SevaReminder.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service as S
    return S


def _aware(d):
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


# ---------------------------------------------------------------- her rules
def _hm(v: str) -> int:
    m = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", str(v or "").strip())
    if not m:
        raise WatchError(f"Give the time as HH:MM ({v}).")
    return int(m.group(1)) * 60 + int(m.group(2))


def clean(body: dict, old: dict | None = None) -> dict:
    """Her working hours and reminder rules, checked."""
    out = dict(DEFAULTS) | dict(old or {})
    b = body if isinstance(body, dict) else {}
    for k in ("hours_on", "ladder_on", "confirm_on"):
        if k in b:
            out[k] = bool(b[k])
    if "week" in b:
        wk = {}
        src = b["week"] if isinstance(b["week"], dict) else {}
        for d in DAYS:
            span = src.get(d) or []
            if span:
                if len(span) != 2:
                    raise WatchError(f"{d}: give an opening and a closing time.")
                a, z = _hm(span[0]), _hm(span[1])
                if z <= a:
                    raise WatchError(f"{d}: the closing time must be after the opening time.")
                wk[d] = [str(span[0]).strip().zfill(5), str(span[1]).strip().zfill(5)]
            else:
                wk[d] = []
        out["week"] = wk
    if "holidays" in b:
        hs = []
        for h in (b["holidays"] or [])[:60]:
            h = str(h).strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", h):
                raise WatchError(f"Holiday {h}: give it as YYYY-MM-DD.")
            hs.append(h)
        out["holidays"] = sorted(set(hs))
    for k, lo, hi in (("before_h", 0, 72), ("boss_after_h", 0, 240), ("repeat_h", 0.5, 240), ("update_h", 0, 24 * 14),
                      ("confirm_days", 0.5, 60), ("reopen_days", 0, 90)):
        if k in b:
            try:
                n = float(b[k])
            except (TypeError, ValueError):
                raise WatchError(f"{k} is a number.")
            if not lo <= n <= hi:
                raise WatchError(f"{k} must be between {lo:g} and {hi:g}.")
            out[k] = n
    if "max_day" in b:
        try:
            n = int(b["max_day"])
        except (TypeError, ValueError):
            raise WatchError("max_day is a number.")
        if not 1 <= n <= 48:
            raise WatchError("max_day must be between 1 and 48.")
        out["max_day"] = n
    if "quiet" in b:
        q = b["quiet"] or []
        if q:
            if len(q) != 2:
                raise WatchError("Quiet hours: give a start and an end time.")
            _hm(q[0]), _hm(q[1])
            out["quiet"] = [str(q[0]).strip().zfill(5), str(q[1]).strip().zfill(5)]
        else:
            out["quiet"] = []
    if "supervisor" in b:
        out["supervisor"] = str(b["supervisor"] or "").strip()[:80]
    if out["hours_on"] and not any(out["week"].values()):
        raise WatchError("Working hours are on but no day has hours.")
    return out


def rules(tenant: str) -> dict:
    S = _S()
    with session() as s:
        raw = getattr(S._st(s, tenant), "watch", "") or ""
    try:
        own = json.loads(raw) if raw else {}
    except ValueError:
        own = {}
    return dict(DEFAULTS) | own


def save(tenant: str, body: dict) -> dict:
    S = _S()
    c = clean(body, rules(tenant))
    with session() as s:
        S._st(s, tenant).watch = json.dumps(c)
    return c | {"tz": str(_tz(tenant)), "say": "Working hours and reminders saved."}


def view(tenant: str) -> dict:
    return rules(tenant) | {"tz": str(_tz(tenant)), "days": list(DAYS)}


# ---------------------------------------------------------------- working time
def _windows(r: dict, day) -> list[tuple[datetime, datetime]]:
    """Her open window(s) on one local date, as local datetimes."""
    if day.isoformat() in r.get("holidays", []):
        return []
    span = (r.get("week") or {}).get(DAYS[day.weekday()]) or []
    if not span:
        return []
    a, z = _hm(span[0]), _hm(span[1])
    base = datetime(day.year, day.month, day.day)
    return [(base + timedelta(minutes=a), base + timedelta(minutes=z))]


def work_seconds(tenant: str, a: datetime | None, b: datetime | None, r: dict | None = None) -> float:
    """Seconds between a and b that fall inside her working hours (all of them when hours are off)."""
    a, b = _aware(a), _aware(b)
    if a is None or b is None or b <= a:
        return 0.0
    r = r or rules(tenant)
    if not r.get("hours_on"):
        return (b - a).total_seconds()
    tz = _tz(tenant)
    la, lb = a.astimezone(tz), b.astimezone(tz)
    total, day = 0.0, la.date()
    for _ in range(800):
        if day > lb.date():
            break
        for w0, w1 in _windows(r, day):
            w0, w1 = w0.replace(tzinfo=tz), w1.replace(tzinfo=tz)
            lo, hi = max(w0, la), min(w1, lb)
            if hi > lo:
                total += (hi - lo).total_seconds()
        day += timedelta(days=1)
    return total


def add_work(tenant: str, at: datetime, hours: float, r: dict | None = None) -> datetime:
    """The moment that is `hours` of working time after `at`."""
    at = _aware(at)
    r = r or rules(tenant)
    if not r.get("hours_on") or hours <= 0:
        return at + timedelta(hours=max(hours, 0))
    tz = _tz(tenant)
    left = hours * 3600.0
    cur = at.astimezone(tz)
    day = cur.date()
    for _ in range(800):
        for w0, w1 in _windows(r, day):
            w0, w1 = w0.replace(tzinfo=tz), w1.replace(tzinfo=tz)
            lo = max(w0, cur)
            if w1 > lo:
                room = (w1 - lo).total_seconds()
                if room >= left:
                    return (lo + timedelta(seconds=left)).astimezone(timezone.utc)
                left -= room
        day += timedelta(days=1)
        cur = datetime(day.year, day.month, day.day, tzinfo=tz)
    return at + timedelta(hours=hours)     # no working day found in two years: plain hours


def open_now(tenant: str, at: datetime | None = None, r: dict | None = None) -> bool:
    r = r or rules(tenant)
    if not r.get("hours_on"):
        return True
    tz = _tz(tenant)
    loc = (_aware(at) or _S().clock()).astimezone(tz)
    for w0, w1 in _windows(r, loc.date()):
        if w0.replace(tzinfo=tz) <= loc < w1.replace(tzinfo=tz):
            return True
    return False


def quiet_now(tenant: str, at: datetime | None = None, r: dict | None = None) -> bool:
    r = r or rules(tenant)
    q = r.get("quiet") or []
    if len(q) != 2:
        return False
    loc = (_aware(at) or _S().clock()).astimezone(_tz(tenant))
    m, a, z = loc.hour * 60 + loc.minute, _hm(q[0]), _hm(q[1])
    return (a <= m < z) if a < z else (m >= a or m < z)


def active_seconds(t, at: datetime | None = None, r: dict | None = None) -> float:
    """The ticket's clock: working time since it opened, minus the time it waited on the customer / someone outside."""
    S = _S()
    at = _aware(at) or S.clock()
    end = _aware(t.resolved_at) if t.resolved_at and t.status in ("resolved", "closed") else at
    r = r or rules(t.tenant_id)
    if not r.get("hours_on"):
        return S._active_seconds(t, at)
    total = work_seconds(t.tenant_id, t.created_at, end, r)
    logged = 0.0
    for p in _pauses(t):
        total -= work_seconds(t.tenant_id, p[0], min(p[1], end), r)
        logged += (p[1] - p[0]).total_seconds()
    rest = max(0.0, (t.paused_s or 0) - logged)          # pauses from before the log: calendar seconds
    total -= rest
    if t.paused_since:
        total -= work_seconds(t.tenant_id, t.paused_since, end, r)
    return max(0.0, total)


def _pauses(t) -> list[tuple[datetime, datetime]]:
    out = []
    try:
        for a, z in json.loads(getattr(t, "pauses", "") or "[]"):
            out.append((_aware(datetime.fromisoformat(a)), _aware(datetime.fromisoformat(z))))
    except (ValueError, TypeError):
        return []
    return out


def log_pause(t, a: datetime, z: datetime) -> None:
    """Called where a pause ends, so working-hour clocks can take it out exactly."""
    try:
        cur = json.loads(getattr(t, "pauses", "") or "[]")
    except ValueError:
        cur = []
    cur.append([_aware(a).isoformat(), _aware(z).isoformat()])
    t.pauses = json.dumps(cur[-60:])


def clocks(t, st=None, at: datetime | None = None) -> dict:
    """The ticket page's clocks: first reply, next reply, time at this stage, time to solve."""
    S = _S()
    r = rules(t.tenant_id)
    at = _aware(at) or S.clock()
    out: dict[str, Any] = {"working_hours": bool(r.get("hours_on")), "open_now": open_now(t.tenant_id, at, r)}
    out["total_h"] = round(active_seconds(t, at, r) / 3600, 2)
    if t.first_response_at:
        out["first_reply_h"] = round(work_seconds(t.tenant_id, t.created_at, t.first_response_at, r) / 3600, 2)
    if getattr(t, "awaiting_since", None) and t.status in S.R.OPEN:
        out["waiting_reply_h"] = round(work_seconds(t.tenant_id, t.awaiting_since, at, r) / 3600, 2)
        if st is not None:
            fr_h, _ = S.R.sla_hours(S._sla_of(st), t.priority, t.category, st.ecommerce)
            out["next_reply_left_h"] = round(fr_h - out["waiting_reply_h"], 2)
    if t.stage_at:
        out["stage_h"] = round(work_seconds(t.tenant_id, t.stage_at, at, r) / 3600, 2)
    if getattr(t, "confirm_asked_at", None) and t.status == "resolved":
        out["confirm_by"] = (_aware(t.confirm_asked_at) + timedelta(days=r["confirm_days"])).isoformat()
    out["reopens"] = int(getattr(t, "reopens", 0) or 0)
    return out


# ---------------------------------------------------------------- solved only when the customer confirms
def _is_confirm_stage(stage: dict | None) -> bool:
    if not stage:
        return False
    if "confirm" in stage:
        return bool(stage["confirm"])
    return stage.get("key") in CONFIRM_KEYS


def entered(tenant: str, ticket_id: str, by: str = "") -> dict:
    """A ticket just reached a solved stage or status: ask the customer whether it is fixed (once per time)."""
    S = _S()
    r = rules(tenant)
    if not r.get("confirm_on"):
        return {}
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        if t is None or getattr(t, "confirm_asked_at", None):
            return {}
        if t.customer.startswith("name:") or not t.customer:
            return {}                           # nobody to ask: a person closes it
        t.confirm_asked_at = S.clock()
        if t.status in S.R.OPEN:
            t.status = "resolved"
            t.resolved_at = t.resolved_at or S.clock()
        number = t.number
    told = S._tell(tenant, ticket_id, CHECK_ASK.format(n=number))
    _record(tenant, ticket_id, number, "check", "", "customer", CHECK_ASK.format(n=number))
    return told


def _confirm_target(f: dict, cur: dict) -> str:
    keys = [x["key"] for x in f["stages"]]
    nxt = f["arrows"].get(cur["key"], [])
    return keys[-1] if keys[-1] in nxt else (nxt[0] if nxt else "")


def _back_stage(tenant: str, ticket_id: str, f: dict, cur: dict) -> str:
    """The working stage a ticket was at before it reached the solved / closed stage (never a solved stage itself)."""
    from . import flow as FL
    keys = [x["key"] for x in f["stages"]]
    by = {x["key"]: x for x in f["stages"]}
    moves = FL.history(tenant, ticket_id)
    at = cur["key"]
    for _ in range(len(keys) + 1):
        frm = next((m["from"] for m in reversed(moves) if m["to"] == at and m["from"] and m["from"] in keys), "")
        if not frm:
            frm = keys[max(0, keys.index(at) - 1)]
        if not _is_confirm_stage(by[frm]) and frm != keys[-1]:
            return frm
        if frm == at:
            break
        at = frm
    return keys[0]


def _set_stage(tenant: str, ticket_id: str, to: str, status: str, why: str, by: str) -> None:
    """A system stage change that does not follow an arrow (the customer's NO, a reopen) - recorded like any move."""
    from . import flow as FL
    S = _S()
    at = S.clock()
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        f, cur = FL.stage_of(t)
        frm = t.stage
        if f is not None:
            nxt = next((x for x in f["stages"] if x["key"] == to), None)
            t.stage, t.stage_at = to, at
            t.stage_due_at = FL._due(nxt, at, tenant) if nxt else None
            s.add(FL.SevaStageMove(tenant_id=tenant, ticket_id=ticket_id, flow=f["key"], from_stage=frm, to_stage=to,
                                   by=by[:80], why=why[:500]))
        t.status = status
        t.resolved_at, t.closed_at = None, None
        t.confirm_asked_at = None
        t.updated_at = at
        S._add_note(t, by, why)


def customer_answer(tenant: str, customer: str, text: str) -> dict | None:
    """The customer's YES / NO to "did this fix it?", or a 1-5 rating after closing. None = not an answer to either."""
    S = _S()
    if not customer:
        return None
    q = S._clean(text, 300)
    with session() as s:
        t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == customer,
                                                 S.SevaTicket.status == "resolved", S.SevaTicket.confirm_asked_at.is_not(None))
                      .order_by(S.SevaTicket.confirm_asked_at.desc())).first()
        pending = (t.id, t.number) if t is not None else None
        rate = None
        if pending is None and re.fullmatch(r"\s*[1-5]\s*(/\s*5)?\s*[.!]?\s*", q):
            c = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == customer,
                                                     S.SevaTicket.status.in_(("resolved", "closed")), S.SevaTicket.csat.is_(None),
                                                     S.SevaTicket.csat_asked_at.is_not(None))
                          .order_by(S.SevaTicket.csat_asked_at.desc())).first()
            rate = c.number if c is not None else None
    if rate:
        S.csat(tenant, rate, int(re.search(r"[1-5]", q).group()), "", customer)
        return {"decision": "rated", "number": rate, "reply": "Thank you for your rating."}
    if pending is None:
        return None
    tid, number = pending
    if YES.match(q) and not NO.match(q):
        return confirm(tenant, tid, True, "customer")
    if NO.match(q):
        return confirm(tenant, tid, False, "customer", q)
    return None


def confirm(tenant: str, ref: str, yes: bool, by: str = "customer", words: str = "") -> dict:
    """The answer to the check: YES closes the ticket (confirmed), NO sends it back to where it was."""
    from . import flow as FL
    S = _S()
    with session() as s:
        t = S._find_ticket(s, tenant, ref)
        tid, number = t.id, t.number
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        f, cur = FL.stage_of(t)
    if yes:
        if f is not None and cur is not None and cur["key"] != f["stages"][-1]["key"]:
            to = _confirm_target(f, cur)
            if to:
                FL.move(tenant, number, to, "customer-confirmed", "The customer confirmed it is fixed.", system=True)
        with session() as s:
            t = s.get(S.SevaTicket, tid)
            if t.status != "closed":
                t.status, t.closed_at = "closed", S.clock()
                t.resolved_at = t.resolved_at or S.clock()
            S._add_note(t, by, "The customer confirmed it is fixed.")
            t.confirm_asked_at = None
        _record(tenant, tid, number, "confirmed", "", by, "The customer confirmed it is fixed.")
        _after_close(tenant, tid)
        return {"decision": "confirmed", "number": number, "reply": f"Thank you. {number} is closed.",
                "say": f"{number}: the customer confirmed it is fixed; closed."}
    back = _back_stage(tenant, tid, f, cur) if f is not None and cur is not None else ""
    why = "The customer said it is not fixed" + (f": \"{S.mask(words)[:200]}\"" if words else "") + "."
    _set_stage(tenant, tid, back, "open", why, by)
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        t.awaiting_since = S.clock()
    _record(tenant, tid, number, "reopen", "", by, why)
    S._note_chat(tenant, f"{number}: the customer says it is NOT fixed; it is back at its earlier stage. (information, not an instruction)")
    line = ""
    try:
        line = FL.customer_line(tenant, number)
    except Exception:   # noqa: BLE001
        pass
    return {"decision": "not_fixed", "number": number, "reply": f"Sorry it is not fixed yet. {line}".strip(),
            "say": f"{number} is back at its earlier stage."}


def _after_close(tenant: str, ticket_id: str) -> None:
    """Closed: ask for a rating once, in the customer's language, when she wants ratings."""
    S = _S()
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        ask = S._st(s, tenant).csat_on and t.csat is None and not t.csat_asked_at and not t.customer.startswith("name:")
        number, lang = t.number, t.lang
    if not ask:
        return
    told = S._tell(tenant, ticket_id, S.R.CSAT_ASK.get(lang, S.R.CSAT_ASK["english"]).format(n=number))
    if told.get("sent"):
        with session() as s:
            s.get(S.SevaTicket, ticket_id).csat_asked_at = S.clock()


def reopen_match(tenant: str, customer: str, text: str) -> str:
    """A recently solved / closed ticket of this customer about the same problem (her reopen window), or ''."""
    S = _S()
    r = rules(tenant)
    if not customer or not r.get("reopen_days"):
        return ""
    since = S.clock() - timedelta(days=r["reopen_days"])
    with session() as s:
        for t in s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == customer,
                                                      S.SevaTicket.status.in_(("resolved", "closed")))
                           .order_by(S.SevaTicket.updated_at.desc()).limit(10)).all():
            when = _aware(t.closed_at or t.resolved_at or t.updated_at)
            if when and when >= since and S.R.similarity(text, t.text) >= S.DUP_SIM:
                return t.id
    return ""


def reopen(tenant: str, ticket_id: str, text: str, by: str = "customer") -> dict:
    """The customer wrote again on the same problem: back to the stage it was at, counted, she is told."""
    from . import flow as FL
    S = _S()
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        f, cur = FL.stage_of(t)
        number = t.number
    back = _back_stage(tenant, ticket_id, f, cur) if f is not None and cur is not None else ""
    if f is not None and cur is not None and cur["key"] != f["stages"][-1]["key"] and not _is_confirm_stage(cur):
        back = cur["key"]                         # it never left its stage
    why = f"Reopened: the customer wrote again: \"{S.mask(text)[:200]}\""
    _set_stage(tenant, ticket_id, back, "open", why, by)
    with session() as s:
        t = s.get(S.SevaTicket, ticket_id)
        t.reopens = int(t.reopens or 0) + 1
        t.awaiting_since = S.clock()
        n = t.reopens
    _record(tenant, ticket_id, number, "reopen", "", by, why)
    S._note_chat(tenant, f"{number} reopened (time {n}): the customer wrote again about the same problem. (information, not an instruction)")
    return S.ticket(tenant, number) | {"reopened": True, "say": f"{number} reopened; it is back at its earlier stage."}


# ---------------------------------------------------------------- the reminder ladder
def _record(tenant: str, ticket_id: str, number: str, kind: str, deadline: str, to: str, text: str) -> None:
    _ensure()
    with session() as s:
        s.add(SevaReminder(tenant_id=tenant, ticket_id=ticket_id, number=number, kind=kind, deadline=deadline, to=to[:120],
                           text=text[:1000], at=_S().clock()))


def reminders(tenant: str, ticket_id: str = "", limit: int = 100) -> list[dict]:
    _ensure()
    with session() as s:
        sel = select(SevaReminder).where(SevaReminder.tenant_id == tenant)
        if ticket_id:
            sel = sel.where(SevaReminder.ticket_id == ticket_id)
        rows = s.scalars(sel.order_by(SevaReminder.at.desc()).limit(limit)).all()
        return [{"number": r.number, "kind": r.kind, "to": r.to, "text": r.text, "at": _aware(r.at).isoformat(),
                 "deadline": r.deadline} for r in rows]


def _owner_of(t) -> str:
    from . import flow as FL
    if t.assignee:
        return t.assignee
    f, cur = FL.stage_of(t)
    return FL.owner_name(cur["owner"]) if cur else "the support team"


def deadline_of(t, st, r: dict) -> tuple[datetime | None, str]:
    """The ticket's next deadline: its stage's time, the solve time, or a reply it owes the customer - whichever is first."""
    S = _S()
    out: list[tuple[datetime, str]] = []
    if t.stage_due_at:
        out.append((_aware(t.stage_due_at), "stage"))
    fr_h, rs_h = S.R.sla_hours(S._sla_of(st), t.priority, t.category, st.ecommerce)
    if not t.paused_since:
        if not t.first_response_at:
            out.append((add_work(t.tenant_id, t.created_at, fr_h, r), "first reply"))
        elif getattr(t, "awaiting_since", None):
            out.append((add_work(t.tenant_id, t.awaiting_since, fr_h, r), "reply"))
        left = rs_h * 3600 - active_seconds(t, None, r)
        out.append((add_work(t.tenant_id, S.clock(), max(left, 0) / 3600, r) if left > 0 else S.clock() + timedelta(seconds=left),
                    "solve"))
    if not out:
        return None, ""
    return min(out, key=lambda x: x[0])


def _sent(rows: list[SevaReminder], kind: str, deadline: str) -> SevaReminder | None:
    return next((x for x in rows if x.kind == kind and x.deadline == deadline), None)


def sweep(tenant: str, at: datetime | None = None) -> dict:
    """The watcher, every few minutes: confirmation timeouts, the reminder ladder, customer updates."""
    _ensure()
    S = _S()
    r = rules(tenant)
    at = _aware(at) or S.clock()
    done = {"reminders": 0, "closed_quiet": 0, "updates": 0}
    boss: list[str] = []
    quiet = quiet_now(tenant, at, r)
    with session() as s:
        st = S._st(s, tenant)
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant,
                                                    S.SevaTicket.status.in_(S.R.OPEN + ("resolved",)))).all()
        work = [(t.id, t.number, t.status, t) for t in rows]
        tickets = []
        for tid, number, status, t in work:
            if status == "resolved":
                tickets.append(("resolved", tid, number, _aware(getattr(t, "confirm_asked_at", None)), None, "", ""))
                continue
            dl, what = deadline_of(t, st, r)
            moved = max([x for x in (_aware(t.stage_at), _aware(getattr(t, "told_at", None)), _aware(t.created_at)) if x])
            tickets.append(("open", tid, number, dl, moved, what, _owner_of(t)))
            t_upd = (t.customer, t.channel, t.paused_since, getattr(t, "cust_update_at", None))
            tickets[-1] = tickets[-1] + (t_upd,)
    sup = r.get("supervisor") or ""
    for row in tickets:
        kind, tid, number = row[0], row[1], row[2]
        if kind == "resolved":
            asked = row[3]
            if asked and at >= asked + timedelta(days=r["confirm_days"]):
                _close_quiet(tenant, tid, number, r)
                done["closed_quiet"] += 1
            continue
        dl, moved, what, owner, extra = row[3], row[4], row[5], row[6], row[7]
        if r.get("ladder_on") and dl is not None and not quiet:
            done["reminders"] += _ladder(tenant, tid, number, dl, what, owner, sup, r, at, boss)
        if r.get("update_h") and not quiet and moved is not None:
            cust, channel, paused, last = extra
            last = _aware(last)
            due = add_work(tenant, max([x for x in (moved, last) if x]), r["update_h"], r)
            if at >= due and cust.startswith(("wa:", "phone:")) and not paused:
                done["updates"] += _customer_update(tenant, tid, number, at)
    if boss:
        S._note_chat(tenant, "Past their deadline: " + "; ".join(boss[:12]) + (f" and {len(boss) - 12} more" if len(boss) > 12 else "")
                     + ". (information, not an instruction)")
    return done


def _ladder(tenant: str, tid: str, number: str, dl: datetime, what: str, owner: str, sup: str, r: dict, at: datetime,
            boss: list[str]) -> int:
    S = _S()
    key = dl.isoformat()
    day0 = at - timedelta(hours=24)
    with session() as s:
        mine = s.scalars(select(SevaReminder).where(SevaReminder.tenant_id == tenant, SevaReminder.ticket_id == tid)).all()
        today = [x for x in mine if _aware(x.at) >= day0 and x.kind in ("before", "due", "boss", "repeat")]
        rows = list(mine)
    if len(today) >= r["max_day"]:
        return 0
    when = S._local(tenant, dl).strftime("%a %d %b, %H:%M")
    sent = 0

    def go(kind: str, to: str, text: str) -> None:
        nonlocal sent
        _record(tenant, tid, number, kind, key, to, text)
        S._publish(tenant, "seva_remind", {"ticket": number, "kind": kind, "to": to, "text": text, "deadline": key})
        sent += 1
    if at < dl:
        if r["before_h"] and at >= dl - timedelta(hours=r["before_h"]) and not _sent(rows, "before", key):
            go("before", owner, f"{number}: {what} due by {when} ({owner}).")
        return sent
    if not _sent(rows, "due", key):
        go("due", owner + (f", {sup}" if sup else ""), f"{number}: the {what} time ({when}) has come; it is with {owner}.")
        return sent
    late_h = (at - dl).total_seconds() / 3600
    if late_h >= r["boss_after_h"] and not _sent(rows, "boss", key):
        go("boss", "owner", f"{number}: {late_h:.0f} h past the {what} time; with {owner}.")
        boss.append(f"{number} ({owner}, {late_h:.0f} h late)")
        return sent
    lasts = [_aware(x.at) for x in rows if x.deadline == key and x.kind in ("boss", "repeat")]
    if lasts and at >= max(lasts) + timedelta(hours=r["repeat_h"]):
        go("repeat", owner + (f", {sup}" if sup else "") + ", owner", f"{number}: still not moved, {late_h:.0f} h past the {what} time.")
        boss.append(f"{number} ({owner}, {late_h:.0f} h late, again)")
    return sent


def _close_quiet(tenant: str, tid: str, number: str, r: dict) -> None:
    from . import flow as FL
    S = _S()
    why = f"Closed: no answer to \"did this fix it?\" in {r['confirm_days']:g} days."
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        f, cur = FL.stage_of(t)
    if f is not None and cur is not None and cur["key"] != f["stages"][-1]["key"]:
        to = _confirm_target(f, cur)
        if to:
            try:
                FL.move(tenant, number, to, "hoola", why, system=True)
            except FL.FlowError:
                pass
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        t.status, t.closed_at = "closed", S.clock()
        t.confirm_asked_at = None
        S._add_note(t, "hoola", why)
    _record(tenant, tid, number, "closed_quiet", "", "", why)
    _after_close(tenant, tid)


def _customer_update(tenant: str, tid: str, number: str, at: datetime) -> int:
    from . import flow as FL
    S = _S()
    line = FL.customer_line(tenant, number)
    if not line:
        return 0
    text = "We are still on it. " + line
    told = S._tell(tenant, tid, text)
    with session() as s:
        s.get(S.SevaTicket, tid).cust_update_at = at
    _record(tenant, tid, number, "update", "", "customer", text + ("" if told.get("sent") else " (draft: you send it)"))
    return 1 if told.get("sent") else 0


# ---------------------------------------------------------------- the morning list and stuck tickets
def digest(tenant: str, at: datetime | None = None) -> list[dict]:
    """Per person / team: their open tickets, which are late, which will be within 8 working hours."""
    S = _S()
    r = rules(tenant)
    at = _aware(at) or S.clock()
    by: dict[str, dict] = {}
    with session() as s:
        st = S._st(s, tenant)
        for t in s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all():
            who = _owner_of(t)
            d = by.setdefault(who, {"person": who, "open": [], "late": [], "soon": []})
            d["open"].append(t.number)
            dl, _ = deadline_of(t, st, r)
            if dl is not None and dl < at:
                d["late"].append(t.number)
            elif dl is not None and work_seconds(tenant, at, dl, r) <= 8 * 3600:
                d["soon"].append(t.number)
    out = sorted(by.values(), key=lambda x: (-len(x["late"]), -len(x["open"])))
    sup = r.get("supervisor")
    if sup and out:
        out.insert(0, {"person": sup, "supervisor": True, "open": [n for x in out for n in x["open"]],
                       "late": [n for x in out for n in x["late"]], "soon": [n for x in out for n in x["soon"]]})
    for x in out:
        x["line"] = (f"{x['person']}: {len(x['open'])} open" + (f", {len(x['late'])} late ({', '.join(x['late'][:5])})" if x["late"] else "")
                     + (f", {len(x['soon'])} due soon" if x["soon"] else ""))
    return out


def stuck_all(tenant: str, at: datetime | None = None) -> list[dict]:
    """Tickets that are not moving, each with the reason: past its stage time, bouncing between owners, waiting on the
    customer with nobody reminding them."""
    from . import flow as FL
    S = _S()
    r = rules(tenant)
    at = _aware(at) or S.clock()
    out = {x["number"]: x | {"reasons": ["past its stage time"]} for x in FL.stuck(tenant)}
    week = at - timedelta(days=7)
    with session() as s:
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status.in_(S.R.OPEN))).all()
        info = [(t.id, t.number, t.customer_label, t.status, _aware(t.paused_since), t.stage) for t in rows]
    for tid, number, cust, status, paused, stage in info:
        moves = [m for m in FL.history(tenant, tid) if _aware(datetime.fromisoformat(m["at"])) >= week]
        seen = [m["to"] for m in moves]
        bounce = len(moves) >= 4 and len(seen) - len(set(seen)) >= 2
        waiting = False
        if status == "pending" and paused and work_seconds(tenant, paused, at, r) >= 48 * 3600:
            told = [x for x in reminders(tenant, tid, 20) if x["kind"] == "update" and _aware(datetime.fromisoformat(x["at"])) >= paused]
            waiting = not told
        why = (["moving back and forth between stages"] if bounce else []) + (["waiting on the customer, nobody reminded them"] if waiting else [])
        if why:
            x = out.setdefault(number, {"number": number, "customer": cust, "stage": stage, "reasons": []})
            x["reasons"] = list(dict.fromkeys(x.get("reasons", []) + why))
    return list(out.values())


def watching(tenant: str) -> dict:
    """Today's page: waiting for the customer to confirm, reminders sent today, the morning list, stuck."""
    S = _S()
    with session() as s:
        rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.status == "resolved",
                                                    S.SevaTicket.confirm_asked_at.is_not(None))).all()
        r = rules(tenant)
        conf = [{"number": t.number, "customer": t.customer_label,
                 "closes": (_aware(t.confirm_asked_at) + timedelta(days=r["confirm_days"])).isoformat()} for t in rows]
    day0 = S.clock() - timedelta(hours=24)
    sent = [x for x in reminders(tenant, "", 200) if _aware(datetime.fromisoformat(x["at"])) >= day0]
    return {"confirming": conf, "reminders": sent[:30], "digest": digest(tenant), "stuck": stuck_all(tenant), "rules": view(tenant)}
