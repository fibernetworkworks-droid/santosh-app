"""v0.98 Bima Sahayak: Hoola as an insurance agent's coworker, end to end.

  1. Gets the job: "Ramesh ki LIC policy add karo", the insurer's renewal list (Excel / CSV), a policy PDF / photo,
     "Sunita ka claim karna hai", "Patil ji ko term plan chahiye".
  2. Does the work, step by step: client book (family, income, loans, goals), every policy (insurer, plan, number, mode,
     premium, cover, nominee), premium due / grace (15 / 30 days) / lapsed / revival window, needs analysis (life cover
     and health cover gaps by rules of thumb, IRDAI need analysis for savings plans), quote comparison she enters,
     proposal checklist, claim checklist with IRDAI timelines, birthdays.
  3. Checked against the rules and earlier work: grace and revival, free-look 30 days, GST exemption on individual life /
     health from 22 Sep 2025, Sec 126 (old 80D) only in the old regime, nominee missing, cover gaps vs what she sold
     before, claims crossing IRDAI timelines (escalate: insurer grievance -> Bima Bharosa -> Insurance Ombudsman).
  4. Ready as a card, a file or a draft: renewal reminder drafts, recommendation note, comparison table, claim document
     list, birthday wishes, the book as Excel.
  5. Waits for her Haan: sending a recommendation / any message to a client. Hoola never collects or pays a premium,
     never signs a proposal or fills a health declaration for the client, never promises a return the brochure doesn't
     guarantee.
  6. Delivers and learns: renewals paid move the due date; lapses and claims are logged; persistency and commission
     are tracked month by month.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import rules as R

log = logging.getLogger("santosh.insure")
_LOCK = threading.Lock()


class InsError(Exception):
    pass


class InsSettings(Base):
    __tablename__ = "ins_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_name: Mapped[str] = mapped_column(String(120), default="")
    agent_code: Mapped[str] = mapped_column(String(40), default="")
    remind_days: Mapped[int] = mapped_column(Integer, default=15)
    morning_time: Mapped[str] = mapped_column(String(5), default="09:15")
    last_morning: Mapped[str] = mapped_column(String(10), default="")


class InsClient(Base):
    __tablename__ = "ins_clients"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ic"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    dob: Mapped[str] = mapped_column(String(10), default="")
    gender: Mapped[str] = mapped_column(String(1), default="")
    city: Mapped[str] = mapped_column(String(60), default="")
    metro: Mapped[bool] = mapped_column(Boolean, default=False)
    income: Mapped[float] = mapped_column(Float, default=0.0)                  # yearly
    family: Mapped[str] = mapped_column(Text, default="[]")                    # [{name, relation, dob}]
    liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    goals: Mapped[float] = mapped_column(Float, default=0.0)
    savings: Mapped[float] = mapped_column(Float, default=0.0)
    whatsapp_ok: Mapped[bool] = mapped_column(Boolean, default=True)          # client agreed to messages
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InsPolicy(Base):
    __tablename__ = "ins_policies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ip"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(40), index=True)
    insurer: Mapped[str] = mapped_column(String(80), default="")
    plan: Mapped[str] = mapped_column(String(120), default="")
    ptype: Mapped[str] = mapped_column(String(12), default="other")
    number: Mapped[str] = mapped_column(String(40), default="", index=True)
    start: Mapped[str] = mapped_column(String(10), default="")
    term_years: Mapped[int] = mapped_column(Integer, default=0)
    ppt_years: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(12), default="yearly")
    premium: Mapped[float] = mapped_column(Float, default=0.0)
    cover: Mapped[float] = mapped_column(Float, default=0.0)
    next_due: Mapped[str] = mapped_column(String(10), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="inforce")        # inforce | lapsed | matured | surrendered | claimed | cancelled
    nominee: Mapped[str] = mapped_column(String(120), default="")
    commission_pct: Mapped[float] = mapped_column(Float, default=0.0)
    group: Mapped[bool] = mapped_column(Boolean, default=False)
    members: Mapped[str] = mapped_column(Text, default="[]")
    pay_link: Mapped[str] = mapped_column(String(300), default="")            # insurer's own payment page (she gives it)
    reminded_for: Mapped[str] = mapped_column(String(10), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InsClaim(Base):
    __tablename__ = "ins_claims"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("il"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    policy_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(24), default="other")
    event_on: Mapped[str] = mapped_column(String(10), default="")
    filed_on: Mapped[str] = mapped_column(String(10), default="")             # all documents with the insurer
    insurer_ref: Mapped[str] = mapped_column(String(60), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    docs: Mapped[str] = mapped_column(Text, default="{}")                     # {doc: true/false}
    status: Mapped[str] = mapped_column(String(12), default="open")           # open | filed | query | settled | rejected
    settled_amount: Mapped[float] = mapped_column(Float, default=0.0)
    log: Mapped[str] = mapped_column(Text, default="[]")


class InsAdvice(Base):
    """A needs analysis + recommendation (the IRDAI suitability record); goes to the client only on her Haan."""
    __tablename__ = "ins_advice"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ia"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str] = mapped_column(String(40), index=True)
    needs: Mapped[str] = mapped_column(Text, default="{}")
    options: Mapped[str] = mapped_column(Text, default="[]")
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="ready")          # ready | approved | sent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _rs(v) -> str:
    v = round(float(v or 0))
    s = str(abs(v))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if v < 0 else "") + "₹" + s


def _lakh(v) -> str:
    v = float(v or 0)
    if abs(v) >= 1e7:
        return f"₹{v / 1e7:g} cr"
    if abs(v) >= 1e5:
        return f"₹{round(v / 1e5, 2):g} lakh"
    return _rs(v)


def _f(v) -> float:
    from ..analyst.rules import clean_amount
    return abs(clean_amount(v))


def _date(v) -> date | None:
    from ..analyst.service import _date as d
    return d(v)


def _tz(tenant: str):
    from ..life import tz_of
    return tz_of(tenant)


def today(tenant: str) -> date:
    return datetime.now(_tz(tenant)).date()


def _plog(p: InsPolicy, what: str, by: str = "hoola") -> None:
    lg = _j(p.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "what": what[:300], "by": by})
    p.log = json.dumps(lg[-100:], ensure_ascii=False)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("insure publish failed")


def _st(s, tenant: str) -> InsSettings:
    r = s.get(InsSettings, tenant)
    if not r:
        r = InsSettings(tenant_id=tenant)
        s.add(r)
        s.flush()
    return r


def settings(tenant: str) -> dict:
    with session() as s:
        r = _st(s, tenant)
        return {"enabled": r.enabled, "agent_name": r.agent_name, "agent_code": r.agent_code, "remind_days": r.remind_days,
                "morning_time": r.morning_time}


def save_settings(tenant: str, **kw: Any) -> dict:
    with session() as s:
        r = _st(s, tenant)
        for k in ("agent_name", "agent_code"):
            if kw.get(k) is not None:
                setattr(r, k, str(kw[k]).strip()[:120])
        if kw.get("remind_days") is not None:
            r.remind_days = max(1, min(int(kw["remind_days"]), 60))
        if kw.get("morning_time"):
            r.morning_time = str(kw["morning_time"]).zfill(5)[:5]
        if "enabled" in kw:
            r.enabled = bool(kw["enabled"])
    return settings(tenant)


# ---------------------------------------------------------------- clients
def _client(s, tenant: str, ref: str) -> InsClient:
    ref = str(ref or "").strip()
    if not ref:
        raise InsError("Which customer? Give a name or phone.")
    c = s.get(InsClient, ref)
    if c and c.tenant_id == tenant:
        return c
    digits = re.sub(r"\D", "", ref)
    rows = s.scalars(select(InsClient).where(InsClient.tenant_id == tenant)).all()
    if len(digits) >= 10:
        for r in rows:
            if r.phone.endswith(digits[-10:]):
                return r
    hits = [r for r in rows if ref.lower() in r.name.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise InsError("Several customers have this name: " + ", ".join(f"{h.name} ({h.phone[-4:]})" for h in hits[:5]) + ". Give the phone.")
    raise InsError(f"Customer '{ref}' not found.")


def _client_view(c: InsClient, on: date) -> dict:
    dob = _date(c.dob)
    return {"id": c.id, "name": c.name, "phone": c.phone, "dob": c.dob, "age": R.age_on(dob, on), "gender": c.gender, "city": c.city,
            "metro": c.metro, "income": c.income, "family": _j(c.family, []), "liabilities": c.liabilities, "goals": c.goals,
            "savings": c.savings, "whatsapp_ok": c.whatsapp_ok, "notes": c.notes}


def save_client(tenant: str, name: str = "", client: str = "", phone: str = "", dob: str = "", gender: str = "", city: str = "",
                metro: bool | None = None, income=None, family: list | None = None, liabilities=None, goals=None, savings=None,
                whatsapp_ok: bool | None = None, notes: str = "") -> dict:
    with _LOCK, session() as s:
        c = _client(s, tenant, client) if client else None
        new = c is None
        if new:
            if not str(name).strip():
                raise InsError("The customer's name is required.")
            c = InsClient(tenant_id=tenant)
            s.add(c)
        if name:
            c.name = re.sub(r"\s+", " ", str(name)).strip()[:120]
        if phone:
            c.phone = re.sub(r"[^\d+]", "", str(phone))[:20]
        if dob:
            d = _date(dob)
            if not d:
                raise InsError(f"Could not understand the date of birth: {dob}")
            c.dob = d.isoformat()
        if gender:
            g = str(gender).strip().lower()
            c.gender = "F" if g.startswith(("f", "mahila", "w", "aurat")) else "M" if g.startswith(("m", "purush", "aadmi")) else ""
        if city:
            c.city = str(city)[:60]
            c.metro = str(city).strip().lower() in ("mumbai", "delhi", "new delhi", "kolkata", "chennai", "bengaluru", "bangalore",
                                                    "hyderabad", "pune", "ahmedabad", "gurugram", "noida", "thane", "navi mumbai")
        if metro is not None:
            c.metro = bool(metro)
        for k, v in (("income", income), ("liabilities", liabilities), ("goals", goals), ("savings", savings)):
            if v not in (None, ""):
                setattr(c, k, _f(v))
        if family is not None:
            c.family = json.dumps([{"name": str(m.get("name", ""))[:60], "relation": str(m.get("relation", ""))[:20],
                                    "dob": (_date(m.get("dob")).isoformat() if _date(m.get("dob")) else "")} for m in family if isinstance(m, dict)])
        if whatsapp_ok is not None:
            c.whatsapp_ok = bool(whatsapp_ok)
        if notes:
            c.notes = str(notes)[:2000]
        s.flush()
        v = _client_view(c, today(tenant))
    return {"client": v, "say": f"{'New customer' if new else 'Update'}: {v['name']}" + (f", {v['age']} years" if v["age"] else "") + "."}


def clients(tenant: str) -> list[dict]:
    on = today(tenant)
    with session() as s:
        return [_client_view(c, on) for c in s.scalars(select(InsClient).where(InsClient.tenant_id == tenant).order_by(InsClient.name)).all()]


# ---------------------------------------------------------------- policies
def _pview(p: InsPolicy, c: InsClient | None, on: date) -> dict:
    due = _date(p.next_due)
    st = R.premium_state(due, p.mode, p.ptype, on) if p.status in ("inforce", "lapsed") else {"state": p.status, "label": p.status}
    return {"id": p.id, "client_id": p.client_id, "client": c.name if c else "", "phone": c.phone if c else "", "insurer": p.insurer,
            "plan": p.plan, "type": p.ptype, "type_label": R.TYPES.get(p.ptype, p.ptype), "number": p.number, "start": p.start,
            "term_years": p.term_years, "ppt_years": p.ppt_years, "mode": p.mode, "premium": p.premium, "cover": p.cover,
            "next_due": p.next_due, "status": p.status, "premium_state": st, "nominee": p.nominee, "commission_pct": p.commission_pct,
            "group": p.group, "members": _j(p.members, []), "gst_pct": R.gst_on(p.ptype, p.group), "pay_link": p.pay_link,
            "log": _j(p.log, [])[-10:]}


def _ptype(v: str) -> str:
    t = str(v or "").lower()
    for k, words in (("term", ("term", "jeevan amar", "click 2 protect", "iprotect", "saral jeevan")), ("ulip", ("ulip", "unit linked", "wealth")),
                     ("pension", ("pension", "annuity", "retire")), ("topup", ("top-up", "top up", "topup", "super top")),
                     ("health", ("health", "mediclaim", "arogya", "family floater", "star", "care", "niva", "optima")),
                     ("pa", ("accident",)), ("critical", ("critical",)), ("motor", ("motor", "car", "bike", "two wheeler", "vehicle")),
                     ("home", ("home", "shop", "fire")), ("travel", ("travel",)),
                     ("endowment", ("endowment", "money back", "jeevan", "anand", "labh", "guaranteed", "savings"))):
        if t in R.TYPES and t == k:
            return k
        if any(w in t for w in words):
            return k
    return t if t in R.TYPES else "other"


def save_policy(tenant: str, client: str, insurer: str = "", plan: str = "", ptype: str = "", number: str = "", start: str = "",
                mode: str = "", premium=None, cover=None, next_due: str = "", term_years=None, ppt_years=None, nominee: str = "",
                commission_pct=None, group: bool | None = None, members: list | None = None, pay_link: str = "", policy: str = "",
                status: str = "", by: str = "owner") -> dict:
    if pay_link and not str(pay_link).startswith("https://"):
        raise InsError("Payment link sirf insurer ka https link ho.")
    on = today(tenant)
    with _LOCK, session() as s:
        if policy:
            p = s.get(InsPolicy, policy)
            if not p or p.tenant_id != tenant:
                p = s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant, InsPolicy.number == policy)).first()
            if not p:
                raise InsError("Policy not found.")
            c = s.get(InsClient, p.client_id)
            new = False
        else:
            c = _client(s, tenant, client)
            num = str(number or "").strip()
            p = s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant, InsPolicy.number == num)).first() if num else None
            new = p is None
            if new:
                p = InsPolicy(tenant_id=tenant, client_id=c.id)
                s.add(p)
        if insurer:
            p.insurer = str(insurer)[:80]
        if plan:
            p.plan = str(plan)[:120]
        if ptype or plan or new:
            p.ptype = _ptype(ptype or plan or p.ptype)
        if number:
            p.number = str(number).strip()[:40]
        if mode:
            p.mode = R.mode_of(mode)
        if premium not in (None, ""):
            p.premium = _f(premium)
        if cover not in (None, ""):
            p.cover = _f(cover)
        if term_years not in (None, ""):
            p.term_years = int(term_years)
        if ppt_years not in (None, ""):
            p.ppt_years = int(ppt_years)
        if nominee:
            p.nominee = str(nominee)[:120]
        if commission_pct not in (None, ""):
            p.commission_pct = float(commission_pct)
        if group is not None:
            p.group = bool(group)
        if members is not None:
            p.members = json.dumps([str(m)[:60] for m in members])
        if pay_link:
            p.pay_link = str(pay_link)[:300]
        if status in ("inforce", "lapsed", "matured", "surrendered", "claimed", "cancelled"):
            p.status = status
        sd = _date(start)
        if start and not sd:
            raise InsError(f"Could not understand the start date: {start}")
        if sd:
            p.start = sd.isoformat()
        nd = _date(next_due)
        if nd:
            p.next_due = nd.isoformat()
        elif new and p.start and p.mode != "single":
            # assume paid up to date: the due that is coming, or still inside grace
            p.next_due = R.next_due_after(_date(p.start), p.mode, on - timedelta(days=R.grace_days(p.mode))).isoformat()
        _plog(p, ("Policy jodi" if new else "Policy update") + f": {p.insurer} {p.plan} {p.number}", by)
        s.flush()
        v = _pview(p, c, on)
    warn = []
    if not v["nominee"]:
        warn.append("No nominee is recorded: ask the customer to name one (needed for a claim).")
    if v["premium_state"]["state"] in ("grace", "lapsed"):
        warn.append(v["premium_state"]["label"] + ".")
    say = f"{'Policy jodi' if new else 'Update'}: {v['client']} - {v['insurer']} {v['plan']} ({v['type_label']}), premium {_rs(v['premium'])} {v['mode']}, cover {_lakh(v['cover'])}."
    if v["next_due"]:
        say += f" Agla premium {v['next_due']}."
    if warn:
        say += " Dhyaan: " + " ".join(warn)
    return {"policy": v, "say": say}


def policies(tenant: str, client: str = "", state: str = "") -> list[dict]:
    on = today(tenant)
    with session() as s:
        q = select(InsPolicy).where(InsPolicy.tenant_id == tenant)
        if client:
            q = q.where(InsPolicy.client_id == _client(s, tenant, client).id)
        cs = {c.id: c for c in s.scalars(select(InsClient).where(InsClient.tenant_id == tenant)).all()}
        out = [_pview(p, cs.get(p.client_id), on) for p in s.scalars(q.order_by(InsPolicy.next_due)).all()]
    if state:
        out = [x for x in out if x["premium_state"]["state"] == state]
    return out


def premium_paid(tenant: str, policy: str, paid_on: str = "", by: str = "owner") -> dict:
    """The client paid the insurer (Hoola never takes the money): move the due date by one premium."""
    on = today(tenant)
    with _LOCK, session() as s:
        p = s.get(InsPolicy, policy) or s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant, InsPolicy.number == policy)).first()
        if not p or p.tenant_id != tenant:
            raise InsError("Policy not found.")
        k = R.MODES.get(p.mode, 12)
        due = _date(p.next_due)
        if not due or k == 0:
            raise InsError("This policy has no premium due.")
        p.next_due = R.add_months(due, k).isoformat()
        if p.status == "lapsed":
            p.status = "inforce"
        pd = _date(paid_on) or on
        _plog(p, f"Premium due {due.isoformat()} was paid on {pd.isoformat()} (by the customer to the insurer)", by)
        c = s.get(InsClient, p.client_id)
        v = _pview(p, c, on)
    return {"policy": v, "say": f"{v['client']} ka premium note: agla {v['next_due']}. Commission ~{_rs(v['premium'] * v['commission_pct'] / 100)}."}


_PH = {"client": ("customer name", "client name", "name", "policy holder", "policyholder", "proposer", "life assured"),
       "phone": ("mobile", "phone", "mobile no", "contact"), "number": ("policy no", "policy number", "policy no.", "policy"),
       "insurer": ("insurer", "company", "insurance company"), "plan": ("plan", "plan name", "product"),
       "premium": ("premium", "premium amount", "instalment premium", "inst. premium"), "mode": ("mode", "frequency", "payment mode"),
       "next_due": ("due date", "next due", "fup", "next due date", "renewal date"), "cover": ("sum assured", "sum insured", "cover"),
       "start": ("doc", "start date", "commencement", "date of commencement", "issue date"), "nominee": ("nominee",)}


def import_policies(tenant: str, file_id: str = "", data: bytes | None = None, name: str = "renewals.csv", insurer: str = "") -> dict:
    """The renewal / policy list from an insurer's agent portal (Excel / CSV export she downloads)."""
    from ..analyst.service import _rows
    if file_id:
        from ..analyst.service import _load_file
        name, data = _load_file(tenant, file_id)
    rows = _rows(name, data or b"")
    hi, cols = None, {}
    for i, r in enumerate(rows[:20]):
        h = [re.sub(r"\s+", " ", str(x or "").strip().lower()) for x in r]
        f = {}
        for j, x in enumerate(h):
            for k, ns in _PH.items():
                if x in ns and k not in f:
                    f[k] = j
        if {"client", "number"} <= set(f):
            hi, cols = i, f
            break
    if hi is None:
        raise InsError("The list needs a name column and a policy number column.")
    added, updated, errs = 0, 0, []
    for r in rows[hi + 1:]:
        g = lambda k: r[cols[k]] if k in cols and cols[k] < len(r) else None  # noqa: E731
        nm, num = str(g("client") or "").strip(), str(g("number") or "").strip()
        if not nm or not num:
            continue
        ph = re.sub(r"\D", "", str(g("phone") or ""))
        try:
            try:
                with session() as s:
                    _client(s, tenant, ph if len(ph) >= 10 else nm)
                cref = ph if len(ph) >= 10 else nm
            except InsError:
                cref = save_client(tenant, nm, phone=ph)["client"]["id"]
            res = save_policy(tenant, cref, insurer or str(g("insurer") or ""), str(g("plan") or ""), "", num, str(g("start") or ""),
                              str(g("mode") or ""), g("premium"), g("cover"), str(g("next_due") or ""), nominee=str(g("nominee") or ""))
            if "Update" in res["say"]:
                updated += 1
            else:
                added += 1
        except InsError as e:
            errs.append(f"{num}: {e}")
    return {"added": added, "updated": updated, "errors": errs[:30], "say": f"{added} new policies, {updated} updated." + (f" {len(errs)} had problems." if errs else "")}


# ---------------------------------------------------------------- renewals
def renewals(tenant: str, days: int | None = None) -> dict:
    on = today(tenant)
    with session() as s:
        st = _st(s, tenant)
        days = days if days is not None else st.remind_days
    pol = [p for p in policies(tenant) if p["status"] in ("inforce", "lapsed")]
    due = [p for p in pol if p["premium_state"]["state"] == "due" and p["premium_state"]["days"] <= days]
    grace = [p for p in pol if p["premium_state"]["state"] == "grace"]
    lapsed = [p for p in pol if p["premium_state"]["state"] == "lapsed"]
    total = sum(p["premium"] for p in due + grace)
    comm = sum(p["premium"] * p["commission_pct"] / 100 for p in due + grace)
    say = (f"Next {days} days: {len(due)} premiums ({_rs(sum(p['premium'] for p in due))}); {len(grace)} in grace"
           + (f" (ends soonest: {min(grace, key=lambda x: x['premium_state']['days_left'])['client']})" if grace else "")
           + f"; lapsed {len(lapsed)}. Commission expected ~{_rs(comm)}.")
    return {"due": due, "grace": grace, "lapsed": lapsed, "premium_total": round(total), "commission": round(comm), "say": say}


def reminder_drafts(tenant: str, days: int | None = None) -> dict:
    """WhatsApp drafts for due / grace / lapsed premiums (she sends). Clients who said no to messages are skipped."""
    r = renewals(tenant, days)
    with session() as s:
        st = _st(s, tenant)
        agent = st.agent_name or "your insurance advisor"
        ok = {c.id: c.whatsapp_ok for c in s.scalars(select(InsClient).where(InsClient.tenant_id == tenant)).all()}
    out = []
    for p in r["due"] + r["grace"] + r["lapsed"]:
        if not ok.get(p["client_id"], True):
            continue
        ps = p["premium_state"]
        first = p["client"].split()[0] if p["client"] else ""
        if ps["state"] == "due":
            body = f"The {_rs(p['premium'])} premium for {p['insurer']} policy {p['number']} ({p['plan']}) is due on {ps['due']}."
        elif ps["state"] == "grace":
            body = (f"The {_rs(p['premium'])} premium for {p['insurer']} policy {p['number']} was due on {ps['due']}; the grace period "
                    f"ends on {ps['grace_end']}, after which the policy will lapse.")
        else:
            body = (f"{p['insurer']} policy {p['number']} has lapsed. It can be revived until {ps['revive_by']} (pending premium + interest, "
                    "sometimes a health declaration). Shall I help restart the cover?")
        pay = f" To pay: {p['pay_link']}" if p["pay_link"] else f" You can pay through the {p['insurer']} app / website / branch."
        out.append({"policy_id": p["id"], "client": p["client"], "to": p["phone"], "state": ps["state"],
                    "text": f"Hello {first}, {body}{pay} Let me know if you have any questions. - {agent}"})
    return {"drafts": out, "say": f"Reminder message drafts for {len(out)} customers (you send them; the customer pays the insurer directly)."}


def mark_reminded(tenant: str, policy: str) -> dict:
    with session() as s:
        p = s.get(InsPolicy, policy)
        if not p or p.tenant_id != tenant:
            raise InsError("Policy not found.")
        p.reminded_for = p.next_due
        _plog(p, f"Reminded (due {p.next_due})", "owner")
    return {"say": "Noted."}


def mark_lapsed(tenant: str) -> int:
    """Policies past grace become lapsed (morning job)."""
    on = today(tenant)
    n = 0
    with session() as s:
        for p in s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant, InsPolicy.status == "inforce")).all():
            st = R.premium_state(_date(p.next_due), p.mode, p.ptype, on)
            if st["state"] in ("lapsed", "lapsed_final"):
                p.status = "lapsed"
                _plog(p, f"Grace ended: lapsed (due {p.next_due})")
                n += 1
    return n


# ---------------------------------------------------------------- needs analysis + recommendation (her Haan to send)
def needs(tenant: str, client: str) -> dict:
    on = today(tenant)
    with session() as s:
        c = _client(s, tenant, client)
        cv = _client_view(c, on)
        pols = [_pview(p, c, on) for p in s.scalars(select(InsPolicy).where(InsPolicy.client_id == c.id, InsPolicy.status == "inforce")).all()]
    life_existing = sum(p["cover"] for p in pols if p["type"] in R.LIFE)
    health_existing = sum(p["cover"] for p in pols if p["type"] in ("health", "topup"))
    fam = cv["family"]
    members = 1 + sum(1 for m in fam if m.get("relation", "").lower() in ("wife", "husband", "patni", "pati", "spouse", "son", "daughter",
                                                                         "beta", "beti", "child", "father", "mother", "papa", "maa"))
    ages = [R.age_on(_date(m.get("dob")), on) for m in fam if m.get("dob")] + ([cv["age"]] if cv["age"] else [])
    life = R.life_cover_need(cv["income"], cv["age"], cv["liabilities"], cv["goals"], life_existing, cv["savings"]) if cv["income"] else None
    health = R.health_cover_need(members, cv["metro"], max([a for a in ages if a is not None], default=None), health_existing)
    gaps = []
    if life and life["gap"] > 0:
        gaps.append(f"Term life cover is short: needs ~{_lakh(life['need'])}, has {_lakh(life_existing)} (gap {_lakh(life['gap'])}).")
    if not cv["income"]:
        gaps.append("Yearly income is not known: tell me to work out the life cover.")
    if health["gap"] > 0:
        gaps.append(f"Health cover is short: for {members} people it needs ~{_lakh(health['need'])}, has {_lakh(health_existing)}.")
    if not any(p["type"] == "pa" for p in pols) and cv["income"]:
        gaps.append("No personal accident cover (cheap and important for the earning member).")
    no_nominee = [p["number"] for p in pols if not p["nominee"]]
    if no_nominee:
        gaps.append(f"No nominee: {', '.join(no_nominee)}.")
    return {"client": cv, "life": life, "health": health, "policies": len(pols), "gaps": gaps,
            "say": f"{cv['name']}: " + (" ".join(gaps) if gaps else "cover looks fine.") + " (An estimate by rule of thumb: the final decision is the customer's.)"}


def recommend(tenant: str, client: str, options: list[dict], note: str = "", conv: str = "") -> dict:
    """Options she got from insurers (premium, cover, insurer, plan, csr, features): compared and saved as the suitability
    record. It reaches the client only after her Haan."""
    n = needs(tenant, client)
    rows = []
    for o in options or []:
        prem, cov = _f(o.get("premium")), _f(o.get("cover"))
        if not prem or not cov:
            continue
        pt = _ptype(o.get("type") or o.get("plan") or "")
        rows.append({"insurer": str(o.get("insurer", ""))[:60], "plan": str(o.get("plan", ""))[:80], "type": pt, "premium": prem, "cover": cov,
                     "per_lakh": round(prem / (cov / 1e5), 2), "csr": o.get("csr"), "features": str(o.get("features", ""))[:300],
                     "gst_pct": R.gst_on(pt), "guaranteed": bool(o.get("guaranteed"))})
    if not rows:
        raise InsError("At least one option is needed (insurer, plan, premium, cover).")
    rows.sort(key=lambda r: (r["per_lakh"], -(float(r["csr"] or 0))))
    savings_plan = any(r["type"] in R.SAVINGS for r in rows)
    with session() as s:
        c = _client(s, tenant, client)
        a = InsAdvice(tenant_id=tenant, client_id=c.id, needs=json.dumps({k: n[k] for k in ("life", "health", "gaps")}, ensure_ascii=False),
                      options=json.dumps(rows, ensure_ascii=False), note=str(note)[:2000])
        s.add(a)
        s.flush()
        aid = a.id
    say = (f"{len(rows)} options for {n['client']['name']}: cheapest per lakh of cover is {rows[0]['insurer']} {rows[0]['plan']} "
           f"({_rs(rows[0]['per_lakh'])} / lakh).")
    if savings_plan:
        say += " This is a savings plan: the need analysis is recorded as IRDAI requires; show the benefit illustration to the customer."
    say += " Your approval comes before anything is sent to the customer."
    _publish(tenant, "ins_advice", {"advice_id": aid, "client": n["client"]["name"]}, conv)
    return {"advice_id": aid, "options": rows, "needs": n, "say": say}


def approve_advice(tenant: str, advice_id: str, approve: bool = True) -> dict:
    with session() as s:
        a = s.get(InsAdvice, advice_id)
        if not a or a.tenant_id != tenant:
            raise InsError("Advice record not found.")
        if not approve:
            a.status = "ready"
            return {"say": "Roka."}
        a.status = "approved"
        c = s.get(InsClient, a.client_id)
        st = _st(s, tenant)
        rows = _j(a.options, [])
        needs_ = _j(a.needs, {})
    lines = [f"{i}. {r['insurer']} {r['plan']}: cover {_lakh(r['cover'])}, premium {_rs(r['premium'])}"
             + (f", claim settlement {r['csr']}%" if r.get("csr") else "") + (f" ({r['features']})" if r["features"] else "")
             for i, r in enumerate(rows[:4], 1)]
    text = (f"Hello {c.name.split()[0]}, based on your needs: " + " ".join(needs_.get("gaps", [])[:2]) + "\n" + "\n".join(lines)
            + "\nThere is no GST on individual life / health premiums now. If you do not like the policy within 30 days of getting it (free-look), you can return it. "
            "Please fill in the proposal form and health details yourself, truthfully. - " + (st.agent_name or "your advisor"))
    return {"draft": text, "to": c.phone, "say": "Approved: message draft ready for the customer (you send it)."}


def proposal_checklist(ptype: str, age: int | None = None, cover: float = 0.0) -> dict:
    t = _ptype(ptype)
    docs = list(R.PROPOSAL_DOCS["common"])
    if t in ("term", "endowment", "ulip", "pension"):
        docs += R.PROPOSAL_DOCS["term"]
    if t in ("health", "topup", "critical"):
        docs += R.PROPOSAL_DOCS["health"]
    if t == "motor":
        docs = R.PROPOSAL_DOCS["common"][:3] + R.PROPOSAL_DOCS["motor"]
    if t in R.SAVINGS:
        docs += R.PROPOSAL_DOCS["savings"]
    tips = [f"Free-look {R.FREE_LOOK_DAYS} days: return the policy if you do not like it.", "Give the Customer Information Sheet (CIS) to the customer."]
    if age and age >= 45 and t in ("term", "health"):
        tips.append("Age 45+: a medical test may be needed; declare any existing illness.")
    return {"type": t, "documents": docs, "tips": tips, "never": list(R.NEVER)}


# ---------------------------------------------------------------- claims
def start_claim(tenant: str, policy: str, kind: str, event_on: str = "", amount=None, by: str = "owner") -> dict:
    k = kind if kind in R.CLAIM_DOCS else ("health_reimbursement" if "health" in kind or "hospital" in kind else
                                           "death" if "death" in kind or "maut" in kind else "motor" if "motor" in kind or "gaadi" in kind else "other")
    with _LOCK, session() as s:
        p = s.get(InsPolicy, policy) or s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant, InsPolicy.number == policy)).first()
        if not p or p.tenant_id != tenant:
            raise InsError("Policy not found.")
        cl = InsClaim(tenant_id=tenant, policy_id=p.id, kind=k, event_on=(_date(event_on) or today(tenant)).isoformat(),
                      amount=_f(amount) if amount else 0.0, docs=json.dumps({d: False for d in R.CLAIM_DOCS[k]}, ensure_ascii=False))
        s.add(cl)
        _plog(p, f"Claim started ({k})", by)
        s.flush()
        cid = cl.id
        c = s.get(InsClient, p.client_id)
        insurer, num = p.insurer, p.number
    t = {"death": "Settled in 15 days without an investigation, 45 days with one; late payment carries interest (bank rate + 2%).",
         "health_cashless": "Cashless approval within 1 hour, discharge within 3 hours (IRDAI).",
         "health_reimbursement": "Should be settled within 15 days of all documents being submitted.",
         "motor": "A surveyor will inspect; tell the insurer before repairing the vehicle.", "other": "Tell the insurer at once."}[k]
    return {"claim_id": cid, "documents": R.CLAIM_DOCS[k],
            "say": f"{c.name}'s {insurer} claim ({num}) started. Tell the insurer at once. Documents: {', '.join(R.CLAIM_DOCS[k])}. {t}"}


def update_claim(tenant: str, claim_id: str, have: list[str] | None = None, status: str = "", insurer_ref: str = "", filed_on: str = "",
                 settled_amount=None, note: str = "") -> dict:
    with session() as s:
        cl = s.get(InsClaim, claim_id)
        if not cl or cl.tenant_id != tenant:
            raise InsError("Claim not found.")
        docs = _j(cl.docs, {})
        for h in have or []:
            for d in docs:
                if h.lower() in d.lower():
                    docs[d] = True
        cl.docs = json.dumps(docs, ensure_ascii=False)
        if insurer_ref:
            cl.insurer_ref = str(insurer_ref)[:60]
        fd = _date(filed_on)
        if fd:
            cl.filed_on = fd.isoformat()
            cl.status = "filed"
        if status in ("open", "filed", "query", "settled", "rejected"):
            cl.status = status
        if settled_amount not in (None, ""):
            cl.settled_amount = _f(settled_amount)
        lg = _j(cl.log, [])
        if note:
            lg.append({"at": now().isoformat(timespec="seconds"), "what": note[:300]})
        cl.log = json.dumps(lg[-50:], ensure_ascii=False)
        missing = [d for d, ok in docs.items() if not ok]
        st = cl.status
    return {"missing": missing, "status": st, "say": ("Pending documents: " + ", ".join(missing)) if missing else "All documents are complete."}


def claims(tenant: str, open_only: bool = True) -> list[dict]:
    on = today(tenant)
    with session() as s:
        q = select(InsClaim).where(InsClaim.tenant_id == tenant)
        if open_only:
            q = q.where(InsClaim.status.in_(("open", "filed", "query")))
        pols = {p.id: p for p in s.scalars(select(InsPolicy).where(InsPolicy.tenant_id == tenant)).all()}
        cs = {c.id: c for c in s.scalars(select(InsClient).where(InsClient.tenant_id == tenant)).all()}
        out = []
        for cl in s.scalars(q).all():
            p = pols.get(cl.policy_id)
            days_limit = {"death": 15, "health_reimbursement": 15}.get(cl.kind)
            fd = _date(cl.filed_on)
            overdue = bool(fd and days_limit and cl.status == "filed" and (on - fd).days > (45 if cl.kind == "death" else days_limit))
            out.append({"id": cl.id, "kind": cl.kind, "client": cs[p.client_id].name if p and p.client_id in cs else "", "insurer": p.insurer if p else "",
                        "policy": p.number if p else "", "status": cl.status, "filed_on": cl.filed_on, "insurer_ref": cl.insurer_ref,
                        "missing": [d for d, ok in _j(cl.docs, {}).items() if not ok], "overdue": overdue,
                        "escalate": ("The insurer's grievance cell, then Bima Bharosa (IRDAI) and the Insurance Ombudsman." if overdue else "")})
        return out


# ---------------------------------------------------------------- book, greetings, morning
def birthdays(tenant: str, days: int = 7) -> dict:
    on = today(tenant)
    out = []
    with session() as s:
        agent = _st(s, tenant).agent_name or "your advisor"
        for c in s.scalars(select(InsClient).where(InsClient.tenant_id == tenant)).all():
            d = _date(c.dob)
            if not d:
                continue
            try:
                nxt = d.replace(year=on.year)
            except ValueError:
                nxt = date(on.year, 3, 1)
            if nxt < on:
                nxt = nxt.replace(year=on.year + 1)
            if (nxt - on).days <= days and c.whatsapp_ok:
                out.append({"client": c.name, "to": c.phone, "on": nxt.isoformat(),
                            "text": f"Happy birthday {c.name.split()[0]}! Wishing you and your family good health and safety. - {agent}"})
    return {"birthdays": out}


def book(tenant: str) -> dict:
    pol = policies(tenant)
    infor = [p for p in pol if p["status"] == "inforce"]
    yearly = sum(p["premium"] * (12 / R.MODES[p["mode"]] if R.MODES.get(p["mode"]) else 0) for p in infor)
    by_type: dict[str, int] = {}
    for p in infor:
        by_type[p["type_label"]] = by_type.get(p["type_label"], 0) + 1
    lapsed = [p for p in pol if p["status"] == "lapsed" or p["premium_state"]["state"] == "lapsed"]
    persist = round(len(infor) * 100 / (len(infor) + len(lapsed)), 1) if (infor or lapsed) else None
    return {"policies": len(pol), "inforce": len(infor), "lapsed": len(lapsed), "yearly_premium": round(yearly),
            "yearly_commission": round(sum(p["premium"] * (12 / R.MODES[p["mode"]] if R.MODES.get(p["mode"]) else 0) * p["commission_pct"] / 100 for p in infor)),
            "by_type": by_type, "persistency_pct": persist,
            "say": f"{len(infor)} active policies, yearly premium {_lakh(yearly)}, lapsed {len(lapsed)}" + (f", persistency {persist}%." if persist is not None else ".")}


def book_file(tenant: str, conv: str = "") -> dict:
    import openpyxl
    from .. import chatfiles
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Policies"
    ws.append(["Client", "Phone", "Insurer", "Plan", "Type", "Policy no", "Mode", "Premium", "Cover", "Next due", "Status", "Nominee"])
    for p in policies(tenant):
        ws.append([p["client"], p["phone"], p["insurer"], p["plan"], p["type_label"], p["number"], p["mode"], p["premium"], p["cover"],
                   p["next_due"], p["premium_state"].get("label", p["status"]), p["nominee"]])
    bio = io.BytesIO()
    wb.save(bio)
    f = chatfiles.store(tenant, "Insurance_book.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    _publish(tenant, "pc_file", {**f, "source": "insure", "title": "Insurance book"}, conv)
    return {"file": f, "say": "Poori policy book Excel mein."}


def due_mornings() -> list[str]:
    from ..life import tz_of
    out = []
    with session() as s:
        for r in s.scalars(select(InsSettings).where(InsSettings.enabled.is_(True))).all():
            if not s.scalars(select(InsPolicy.id).where(InsPolicy.tenant_id == r.tenant_id).limit(1)).first():
                continue
            local = datetime.now(tz_of(r.tenant_id))
            d = local.date().isoformat()
            try:
                hh, mm = [int(x) for x in (r.morning_time or "09:15").split(":")]
            except ValueError:
                hh, mm = 9, 15
            late = (local.hour * 60 + local.minute) - (hh * 60 + mm)
            if r.last_morning != d and 0 <= late <= 180:
                r.last_morning = d
                out.append(r.tenant_id)
    return out


def send_morning(tenant: str) -> dict:
    from ..events import notify
    from ..net.service import home_conv
    mark_lapsed(tenant)
    r = renewals(tenant, 7)
    b = birthdays(tenant, 0)["birthdays"]
    cl = [c for c in claims(tenant) if c["overdue"] or c["missing"]]
    parts = []
    if r["due"] or r["grace"]:
        parts.append(f"{len(r['due'])} premiums due this week, {len(r['grace'])} in grace")
    if b:
        parts.append("Birthday today: " + ", ".join(x["client"] for x in b))
    if cl:
        parts.append(f"{len(cl)} claims with work pending")
    if not parts:
        return {"text": ""}
    text = "Bima: " + "; ".join(parts) + "."
    conv = home_conv(tenant)
    try:
        notify(conv, text)
    except Exception:
        pass
    _publish(tenant, "ins_day", {"text": text}, conv)
    return {"text": text}
