"""G7 of docs/SUPPORT_GLOBAL_PLAN.md: handing a customer to a person, smoothly and honestly.

- WHEN (her rules, defaults on): the customer asks for a person; anger or distress; safety / legal / medical / fraud
  words; a money decision; a VIP customer; a topic set to "always a person"; two tries in a row Hoola could not answer;
  nothing in her knowledge answers it. She can turn each rule off except the ones about safety and money.
- TO WHOM: the person / team that owns the ticket's stage (her workflow, G8) or the ticket's assignee; queues and shifts
  come with G10.
- WHAT THE PERSON GETS - a hand-over packet, never "please read the thread": who the customer is (name, channel,
  language, country, their local time, open and past tickets), the problem in two lines, what Hoola checked and what it
  told the customer, how they feel, the deadline that applies, a suggested next step and a draft reply to edit.
- WHAT THE CUSTOMER IS TOLD, honestly: a person from the team has it; a time only from the real waiting time of past
  hand-overs (at least 3), never made up; when closed, the next opening time in the customer's own time zone; on a call,
  a call-back window (a live warm transfer needs the telephony bridge and is not built yet - said plainly).
- OUT OF HOURS: the ticket is made with the packet; an urgent one pages the owner at once.
- HAND-BACK: a person gives the chat back to Hoola with an instruction ("send the tracking link and close if they
  confirm"); Hoola follows it inside its rules. Every correction a person makes to a Hoola draft is kept; two on one
  topic in two weeks move that topic to "Hoola drafts, a person sends" until she sets it back.
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger(__name__)

RULES = {"asked": "The customer asks for a person", "angry": "Anger or distress", "safety": "Safety, legal, medical or fraud words",
         "money": "A refund, discount or waiver request", "vip": "A VIP customer", "topic": "A topic set to \"always a person\"",
         "failed": "Two tries in a row Hoola could not answer", "unknown": "Nothing in your knowledge answers it"}
FIXED = ("safety", "money")                  # never off: someone's safety, and only she decides about money
SENSITIVE = ("lawyer", "legal action", "court", "police", "consumer court", "fraud", "scam", "stolen", "hacked", "doctor",
             "hospital", "injury", "injured", "poison", "allergic", "bleeding", "fire", "accident", "vakil", "dhokha", "chori")
DEFAULTS = {"on": {k: True for k in RULES}, "vip": [], "words": [], "page_urgent": True, "callback_h": 2.0}


class HandoverError(Exception):
    pass


class SevaHandover(Base):
    """One hand-over of a customer to a person, with its packet."""
    __tablename__ = "seva_handovers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sho"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(30), default="")
    contact_id: Mapped[str] = mapped_column(String(40), default="")
    customer: Mapped[str] = mapped_column(String(200), default="", index=True)
    channel: Mapped[str] = mapped_column(String(12), default="")
    rule: Mapped[str] = mapped_column(String(20), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    to: Mapped[str] = mapped_column(String(120), default="")
    packet: Mapped[str] = mapped_column(Text, default="{}")
    told: Mapped[str] = mapped_column(Text, default="")                # what the customer was told
    status: Mapped[str] = mapped_column(String(12), default="waiting")  # waiting | taken | back | closed
    out_of_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    taken_by: Mapped[str] = mapped_column(String(80), default="")
    back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    back_note: Mapped[str] = mapped_column(Text, default="")


class SevaCorrection(Base):
    """A person changed Hoola's draft before sending it (append-only)."""
    __tablename__ = "seva_corrections"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("scx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    topic: Mapped[str] = mapped_column(String(20), default="")
    channel: Mapped[str] = mapped_column(String(12), default="")
    before: Mapped[str] = mapped_column(Text, default="")
    after: Mapped[str] = mapped_column(Text, default="")
    by: Mapped[str] = mapped_column(String(80), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def _ensure() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaHandover, SevaCorrection):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service as S
    return S


def _aware(d):
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- her rules
def rules(tenant: str) -> dict:
    S = _S()
    with session() as s:
        raw = getattr(S._st(s, tenant), "handover", "") or ""
    try:
        own = json.loads(raw) if raw else {}
    except ValueError:
        own = {}
    out = json.loads(json.dumps(DEFAULTS)) | {k: v for k, v in own.items() if k != "on"}
    out["on"] = DEFAULTS["on"] | (own.get("on") or {})
    for k in FIXED:
        out["on"][k] = True
    return out


def save(tenant: str, body: dict) -> dict:
    S = _S()
    b = body if isinstance(body, dict) else {}
    cur = rules(tenant)
    if isinstance(b.get("on"), dict):
        for k, v in b["on"].items():
            if k not in RULES:
                raise HandoverError(f"Unknown rule {k}.")
            if k in FIXED and not v:
                raise HandoverError(f"{RULES[k]} always goes to a person.")
            cur["on"][k] = bool(v)
    if "vip" in b:
        cur["vip"] = sorted({S._digits(x) for x in (b["vip"] or []) if len(S._digits(x)) >= 6})[:500]
    if "words" in b:
        cur["words"] = [str(w).strip().lower()[:40] for w in (b["words"] or []) if str(w).strip()][:60]
    if "page_urgent" in b:
        cur["page_urgent"] = bool(b["page_urgent"])
    if "callback_h" in b:
        try:
            n = float(b["callback_h"])
        except (TypeError, ValueError):
            raise HandoverError("The call-back window is a number of hours.")
        if not 0.5 <= n <= 48:
            raise HandoverError("The call-back window must be between 0.5 and 48 hours.")
        cur["callback_h"] = n
    with session() as s:
        S._st(s, tenant).handover = json.dumps(cur)
    return view(tenant) | {"say": "Hand-over rules saved."}


def view(tenant: str) -> dict:
    r = rules(tenant)
    return r | {"names": RULES, "fixed": list(FIXED)}


def is_vip(tenant: str, customer: str, r: dict | None = None) -> bool:
    r = r or rules(tenant)
    d = _S()._digits(customer)
    return bool(d) and any(d.endswith(v) or v.endswith(d) for v in r.get("vip", []) if v)


def sensitive(tenant: str, text: str, r: dict | None = None) -> bool:
    r = r or rules(tenant)
    low = " " + (text or "").lower() + " "
    return any(f" {w} " in low or f" {w}" in low for w in tuple(SENSITIVE) + tuple(r.get("words", [])))


def failed_twice(tenant: str, customer: str) -> bool:
    """The last two questions of this customer (within an hour) were ones Hoola could not answer."""
    S = _S()
    if not customer:
        return False
    since = S.clock() - timedelta(hours=1)
    with session() as s:
        rows = s.scalars(select(S.SevaQuestion).where(S.SevaQuestion.tenant_id == tenant, S.SevaQuestion.customer == customer,
                                                      S.SevaQuestion.at >= since).order_by(S.SevaQuestion.at.desc()).limit(2)).all()
        return len(rows) == 2 and all(r.outcome in ("unknown", "clarify") for r in rows)


# ---------------------------------------------------------------- honest times
def _people_tz(customer: str) -> str:
    try:
        from ..callcentre import countries as C
        d = _S()._digits(customer)
        if not d:
            return ""
        code = C.country_of("+" + d)
        return C.tz_of(code, "", "+" + d) if code else ""
    except Exception:   # noqa: BLE001
        return ""


def wait_estimate(tenant: str) -> float | None:
    """Median working hours from hand-over to a person taking it, over her last 20 - None with fewer than 3."""
    from . import watch as W
    _ensure()
    with session() as s:
        rows = s.scalars(select(SevaHandover).where(SevaHandover.tenant_id == tenant, SevaHandover.taken_at.is_not(None))
                         .order_by(SevaHandover.at.desc()).limit(20)).all()
        pairs = [(r.at, r.taken_at) for r in rows]
    if len(pairs) < 3:
        return None
    r = W.rules(tenant)
    return statistics.median(W.work_seconds(tenant, a, b, r) / 3600 for a, b in pairs)


def _say_h(h: float) -> str:
    if h < 1:
        m = max(5, int(round(h * 60 / 5.0)) * 5)
        return f"{m} minutes"
    if h < 24:
        n = round(h * 2) / 2
        return f"{n:g} hour" + ("" if n == 1 else "s")
    return f"{round(h / 24):g} day" + ("" if round(h / 24) == 1 else "s")


def next_open(tenant: str, at: datetime | None = None) -> datetime | None:
    from . import watch as W
    r = W.rules(tenant)
    at = _aware(at) or _S().clock()
    if not r.get("hours_on") or W.open_now(tenant, at, r):
        return None
    return W.add_work(tenant, at, 1 / 3600, r) - timedelta(seconds=1)


def _local(when: datetime, tz: str, tenant: str) -> str:
    from zoneinfo import ZoneInfo
    try:
        z = ZoneInfo(tz) if tz else None
    except Exception:   # noqa: BLE001
        z = None
    loc = when.astimezone(z) if z else _S()._local(tenant, when)
    return loc.strftime("%a %d %b, %H:%M") + ("" if z else "")


# ---------------------------------------------------------------- the packet
def _packet(tenant: str, t, reason: str, rule: str, feeling: str) -> dict:
    from . import flow as FL
    from . import watch as W
    S = _S()
    with session() as s:
        st = S._st(s, tenant)
        others = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == t.customer,
                                                      S.SevaTicket.id != t.id).order_by(S.SevaTicket.created_at.desc()).limit(8)).all()
        past = [{"number": o.number, "status": o.status, "text": S.mask(o.text)[:80]} for o in others]
        qs = s.scalars(select(S.SevaQuestion).where(S.SevaQuestion.tenant_id == tenant, S.SevaQuestion.customer == t.customer)
                       .order_by(S.SevaQuestion.at.desc()).limit(5)).all()
        checked = [{"asked": q.text[:160], "found": q.outcome} for q in reversed(qs)]
        dl, what = W.deadline_of(t, st, W.rules(tenant))
    notes = S._j(t.notes, [])
    told = [n["text"].replace("To the customer: ", "")[:240] for n in notes if n.get("public")][-3:]
    tz = _people_tz(t.customer)
    f, cur = FL.stage_of(t)
    nxt = [x["name"] for x in f["stages"] if cur and x["key"] in f["arrows"].get(cur["key"], [])] if f else []
    name = t.customer_label if t.customer_label and not t.customer_label.startswith("…") else ""
    who = FL.owner_name(cur["owner"]) if cur else "the support team"
    text = S.mask(t.text)
    two = text if len(text) <= 220 else text[:217].rsplit(" ", 1)[0] + "..."
    return {"customer": {"name": name or t.customer_label, "channel": t.channel, "language": t.lang,
                         "country_time_zone": tz, "their_time": _local(S.clock(), tz, tenant) if tz else "",
                         "vip": is_vip(tenant, t.customer)},
            "tickets": {"this": t.number, "others": past},
            "problem": two, "why_a_person": f"{RULES.get(rule, rule)}" + (f": {S.mask(reason)[:200]}" if reason else ""),
            "hoola_checked": checked, "hoola_told": told, "feeling": feeling,
            "deadline": {"when": _aware(dl).isoformat() if dl else "", "what": what},
            "stage": cur["name"] if cur else "", "next_step": (f"Move it to {nxt[0]} when done" if nxt else "Reply to the customer"),
            "draft": (f"Hello{' ' + name.split()[0] if name else ''}, this is {who} about your request {t.number}. "
                      "I have read everything you told us and I am looking at it now.")}


# ---------------------------------------------------------------- start / take / hand back
def start(tenant: str, customer: str, channel: str = "whatsapp", reason: str = "", rule: str = "", text: str = "",
          contact_id: str = "", name: str = "", ref: str = "", by: str = "hoola") -> dict:
    """Hand this customer to a person: a ticket (theirs, or a new one), the packet, an honest line for the customer."""
    _ensure()
    from . import engine as E
    from . import flow as FL
    from . import watch as W
    S = _S()
    rule = rule if rule in RULES else ("asked" if not rule else rule)
    t = None
    with session() as s:
        if ref:
            t = S._find_ticket(s, tenant, ref)
        elif customer:
            t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == customer,
                                                     S.SevaTicket.status.in_(S.R.OPEN)).order_by(S.SevaTicket.updated_at.desc())).first()
        tid = t.id if t is not None else ""
        if t is not None:
            customer = customer or t.customer
            if channel in ("", "other"):
                channel = t.channel
    if not tid:
        words = S._clean(text or reason, 3000) or "The customer asked to talk to a person."
        ch = channel if channel in S.TICKET_CHANNELS else "other"
        tid = S.new_ticket(tenant, words, ch, customer, name, "", by=by)["ticket"]["id"]
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        u = E.understand(tenant, t.text + " " + (text or ""))
        feeling = "upset" if u["angry"] else "worried" if u["safety"] or u["priority"] == "urgent" else "calm"
        urgent = t.priority == "urgent" or u["safety"] or rule == "safety"
        if urgent and t.priority != "urgent":
            t.priority = "urgent"
        packet = _packet(tenant, t, reason, rule, feeling)
        f, cur = FL.stage_of(t)
        to = t.assignee or (FL.owner_name(cur["owner"]) if cur and cur["owner"] != "hoola" else "the support team")
        number, cust, lang = t.number, t.customer, t.lang
        S._add_note(t, by, f"Handed to a person ({RULES.get(rule, rule)}). {S.mask(reason)[:300]}")
    ooh = next_open(tenant)
    tz = _people_tz(cust)
    team = to if not to.startswith("the ") else to[4:]
    team = team[0].upper() + team[1:] if team else "Our team"
    if channel == "phone":
        h = rules(tenant)["callback_h"]
        start_at = ooh or S.clock()
        end = W.add_work(tenant, start_at, h)
        line = (f"I have passed this to {to}. A person will call you back between {_local(start_at, tz, tenant)} and "
                f"{_local(end, tz, tenant)}. Your request number is {number}.")
    elif ooh is not None:
        line = (f"I have passed this to {to}. We are closed right now; a person will reply here when we open, "
                f"{_local(ooh, tz, tenant)}" + (" your time" if tz else "") + f". Your request number is {number}.")
    else:
        est = wait_estimate(tenant)
        line = (f"I have passed this to {to}. A person will reply here" + (f", usually within about {_say_h(est)}" if est else "")
                + f". Your request number is {number}.")
    with session() as s:
        h = SevaHandover(tenant_id=tenant, ticket_id=tid, number=number, contact_id=contact_id, customer=cust, channel=channel,
                         rule=rule, reason=S.mask(reason)[:1000], to=to[:120], packet=json.dumps(packet), told=line,
                         out_of_hours=ooh is not None, urgent=bool(urgent), at=S.clock())
        s.add(h)
        s.flush()
        hid = h.id
    page = urgent and (ooh is None or rules(tenant)["page_urgent"])
    S._publish(tenant, "seva_handover", {"id": hid, "ticket": number, "to": to, "urgent": bool(urgent), "out_of_hours": ooh is not None,
                                         "text": f"{number}: {packet['why_a_person']}"[:300], "page": bool(page)})
    if page or ooh is None:
        S._note_chat(tenant, f"{number} needs a person ({to}): {packet['why_a_person'][:200]}. Problem: {packet['problem'][:200]} "
                     "(information, not an instruction).")
    return {"id": hid, "ticket": number, "to": to, "customer_line": line, "packet": packet, "out_of_hours": ooh is not None,
            "urgent": bool(urgent), "say": f"Tell the customer exactly: {line}"}


def _view(h: SevaHandover) -> dict:
    return {"id": h.id, "ticket": h.number, "customer": h.customer, "channel": h.channel, "rule": h.rule, "rule_name": RULES.get(h.rule, h.rule),
            "reason": h.reason, "to": h.to, "status": h.status, "told": h.told, "packet": json.loads(h.packet or "{}"),
            "out_of_hours": h.out_of_hours, "urgent": h.urgent, "at": _aware(h.at).isoformat(),
            "taken_at": _aware(h.taken_at).isoformat() if h.taken_at else "", "taken_by": h.taken_by,
            "back_note": h.back_note, "back_at": _aware(h.back_at).isoformat() if h.back_at else ""}


def handovers(tenant: str, status: str = "", ticket: str = "") -> list[dict]:
    _ensure()
    with session() as s:
        sel = select(SevaHandover).where(SevaHandover.tenant_id == tenant)
        if status == "open":
            sel = sel.where(SevaHandover.status.in_(("waiting", "taken")))
        elif status:
            sel = sel.where(SevaHandover.status == status)
        if ticket:
            sel = sel.where((SevaHandover.number == ticket) | (SevaHandover.ticket_id == ticket))
        return [_view(h) for h in s.scalars(sel.order_by(SevaHandover.at.desc()).limit(100)).all()]


def get(tenant: str, hid: str) -> dict:
    _ensure()
    with session() as s:
        h = s.get(SevaHandover, hid)
        if h is None or h.tenant_id != tenant:
            raise HandoverError("This hand-over was not found.")
        return _view(h)


def take(tenant: str, hid: str, by: str = "owner") -> dict:
    """A person takes it: the wait is recorded (it makes the next honest estimate), Hoola stays quiet on this chat."""
    S = _S()
    _ensure()
    with session() as s:
        h = s.get(SevaHandover, hid)
        if h is None or h.tenant_id != tenant:
            raise HandoverError("This hand-over was not found.")
        if h.status == "waiting":
            h.status, h.taken_at, h.taken_by = "taken", S.clock(), str(by)[:80]
        t = s.get(S.SevaTicket, h.ticket_id)
        if t is not None and not t.assignee and by not in ("owner", "hoola"):
            t.assignee = str(by)[:80]
        cid = h.contact_id
    if cid:
        try:
            from ..employee import inbox
            inbox.set_human(tenant, cid, True)
        except Exception:   # noqa: BLE001
            log.exception("handover take: set_human")
    return get(tenant, hid) | {"say": "It is yours; Hoola stays quiet on this chat until you hand it back."}


def replied(tenant: str, contact_id: str, by: str = "owner") -> None:
    """A person replied in the inbox: any waiting hand-over of this customer counts as taken."""
    _ensure()
    with session() as s:
        ids = [h.id for h in s.scalars(select(SevaHandover).where(SevaHandover.tenant_id == tenant, SevaHandover.contact_id == contact_id,
                                                                  SevaHandover.status == "waiting")).all()]
    for i in ids:
        take(tenant, i, by)


def replied_key(tenant: str, customer: str, by: str = "owner") -> None:
    """A person replied from the desk on a messaging app: the waiting hand-over of this customer counts as taken."""
    _ensure()
    with session() as s:
        ids = [h.id for h in s.scalars(select(SevaHandover).where(SevaHandover.tenant_id == tenant, SevaHandover.customer == customer,
                                                                  SevaHandover.status == "waiting")).all()]
    for i in ids:
        take(tenant, i, by)


def hand_back(tenant: str, hid: str, note: str = "", by: str = "owner") -> dict:
    """The person gives the chat back to Hoola, with an instruction Hoola follows inside its rules."""
    S = _S()
    note = S._clean(note, 600)
    if note and S._secret(note):
        raise HandoverError("This holds details that are not allowed.")
    _ensure()
    with session() as s:
        h = s.get(SevaHandover, hid)
        if h is None or h.tenant_id != tenant:
            raise HandoverError("This hand-over was not found.")
        if h.status == "waiting":
            h.taken_at, h.taken_by = S.clock(), str(by)[:80]
        h.status, h.back_at, h.back_note = "back", S.clock(), note
        cid, tid = h.contact_id, h.ticket_id
        t = s.get(S.SevaTicket, tid)
        if t is not None:
            S._add_note(t, by, "Handed back to Hoola" + (f": {note}" if note else "."))
    if cid:
        try:
            from ..employee import inbox
            inbox.set_human(tenant, cid, False)
        except Exception:   # noqa: BLE001
            log.exception("handover back: set_human")
    return get(tenant, hid) | {"say": "Hoola has the chat again" + (" and will follow your note." if note else ".")}


def back_note(tenant: str, contact_id: str) -> str:
    """For the business inbox prompt: the latest instruction a person gave when handing this chat back (7 days)."""
    if not contact_id:
        return ""
    _ensure()
    S = _S()
    with session() as s:
        h = s.scalars(select(SevaHandover).where(SevaHandover.tenant_id == tenant, SevaHandover.contact_id == contact_id,
                                                 SevaHandover.status == "back").order_by(SevaHandover.back_at.desc())).first()
        if h is None or not h.back_note or _aware(h.back_at) < S.clock() - timedelta(days=7):
            return ""
        return (f"A person from the team ({h.taken_by or 'the team'}) handed this chat back to you about {h.number} with this "
                f"instruction: \"{h.back_note}\". Follow it inside your rules (never a promise or a payment it does not name).")


# ---------------------------------------------------------------- corrections lower trust
def correction(tenant: str, topic: str, channel: str, before: str, after: str, by: str = "") -> dict:
    """A person changed Hoola's draft. Two on one topic in 14 days: the topic moves to 'Hoola drafts, a person sends'."""
    from . import engine as E
    S = _S()
    if S.R.norm(before) == S.R.norm(after):
        return {}
    _ensure()
    with session() as s:
        s.add(SevaCorrection(tenant_id=tenant, topic=topic or "*", channel=channel or "*", before=S.mask(before)[:3000],
                             after=S.mask(after)[:3000], by=by[:80], at=S.clock()))
    since = S.clock() - timedelta(days=14)
    with session() as s:
        n = len(s.scalars(select(SevaCorrection.id).where(SevaCorrection.tenant_id == tenant, SevaCorrection.topic == (topic or "*"),
                                                          SevaCorrection.at >= since)).all())
    lowered = False
    if n >= 2 and topic and E.trust_level(tenant, topic, "*") == "answer":
        E.set_trust(tenant, "draft", topic, "*")
        lowered = True
        S._note_chat(tenant, f"Your team corrected Hoola's answers on '{topic}' {n} times in two weeks, so Hoola now drafts those and a "
                     "person sends them. Fix the answer in Knowledge, then set it back in Channels & settings.")
    return {"corrections": n, "lowered": lowered}


def corrections(tenant: str, limit: int = 50) -> list[dict]:
    _ensure()
    with session() as s:
        rows = s.scalars(select(SevaCorrection).where(SevaCorrection.tenant_id == tenant).order_by(SevaCorrection.at.desc()).limit(limit)).all()
        return [{"topic": r.topic, "channel": r.channel, "before": r.before, "after": r.after, "by": r.by, "at": _aware(r.at).isoformat()}
                for r in rows]


def overview(tenant: str) -> dict:
    est = wait_estimate(tenant)
    return {"open": handovers(tenant, "open"), "wait_h": est, "wait_text": _say_h(est) if est else "",
            "rules": view(tenant), "corrections": corrections(tenant, 10)}
