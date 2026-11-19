"""v0.999.26 HOOLA CREDITS - the wallet (owner: "FREE TIER WORKS ON NORMAL TIER ONLY. ALL OTHER WILL BE LOCKED ---
ONCE CREDIT PURCHASED --- USER CAN CHOOSE ANY TIER -- BASED ON CHOOSEN TIER USER CREDIT WILL DEDUCT. WE WILL KEEP AI
EMPLOYEE SECTION DIFFERENT PACKAGE PER EMPLOYEE" -> "PAYMENT WILL COME FROM ANY COUNTRY").

- Every model call's real cost (usage.record) becomes credits: $0.001 = 1 credit. Spent free first (60 a day, IST),
  then this month's plan credits, then top-ups. A buffer in memory, written with usage's own flush (every 30 s).
- Free = Normal only: her tier is locked to Normal while she has no paid credits (`unlocked`); a purchase opens every
  tier; when the paid credits are gone she is back on Normal.
- A turn is refused only when the free credits of the day AND the paid credits are both gone (`can_run`).
- AI employees: a package per employee (jobs a month). A turn in which an employee's tool runs is one job of that
  employee, and the model cost of that turn after the tool goes to the package, not to her chat credits.
- Low credits: one line a day in her home chat; the end of paid credits: one line. Nothing is ever moved to a cheaper
  tier by itself.
- Nothing here runs unless the owner turns credits on (CREDITS_ON); exempt tenants (CREDITS_EXEMPT) are never charged."""
from __future__ import annotations

import contextvars
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import plans as P

log = logging.getLogger("santosh.credits")
IST = timezone(timedelta(hours=5, minutes=30))


class CreditWallet(Base):
    __tablename__ = "credit_wallets"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    free_day: Mapped[str] = mapped_column(String(10), default="")
    free_used: Mapped[float] = mapped_column(Float, default=0.0)
    plan: Mapped[str] = mapped_column(String(16), default="")
    plan_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plan_left: Mapped[float] = mapped_column(Float, default=0.0)
    plan_grant: Mapped[float] = mapped_column(Float, default=0.0)
    topup_left: Mapped[float] = mapped_column(Float, default=0.0)
    topup_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ever_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    low_said: Mapped[str] = mapped_column(String(10), default="")
    out_said: Mapped[bool] = mapped_column(Boolean, default=False)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("cl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(16))          # spend | plan | topup | refund | pack | pack_job | adjust
    credits: Mapped[float] = mapped_column(Float, default=0.0)   # + added, - spent / taken back
    usd: Mapped[float] = mapped_column(Float, default=0.0)
    ref: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class CreditOrder(Base):
    __tablename__ = "credit_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("co"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(12))      # razorpay | cashfree | dodo | paddle
    sku: Mapped[str] = mapped_column(String(40))
    employee: Mapped[str] = mapped_column(String(40), default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)   # paise / cents
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(12), default="pending")   # pending | paid | failed | refunded
    provider_ref: Mapped[str] = mapped_column(String(80), default="", index=True)   # gateway order / session / txn
    payment_ref: Mapped[str] = mapped_column(String(80), default="", index=True)
    sub_ref: Mapped[str] = mapped_column(String(80), default="", index=True)       # a renewing subscription
    granted: Mapped[float] = mapped_column(Float, default=0.0)
    checkout: Mapped[str] = mapped_column(Text, default="")      # India: what the pay page opens (no secret in it)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployeePack(Base):
    __tablename__ = "credit_employee_packs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ep"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    employee: Mapped[str] = mapped_column(String(40), index=True)
    pack: Mapped[str] = mapped_column(String(16))
    jobs: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[int] = mapped_column(Integer, default=0)
    until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usd: Mapped[float] = mapped_column(Float, default=0.0)      # what its jobs really cost (for the owner)
    sub_ref: Mapped[str] = mapped_column(String(80), default="")


TABLES = (CreditWallet, CreditLedger, CreditOrder, EmployeePack)
_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in TABLES:
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ------------------------------------------------------------------ switches
def _st():
    from ..config import get_settings
    return get_settings()


def enabled() -> bool:
    return bool(getattr(_st(), "credits_on", False))


def exempt(tenant: str) -> bool:
    ex = {x.strip() for x in str(getattr(_st(), "credits_exempt", "") or "").split(",") if x.strip()}
    return not tenant or tenant in ex


def active(tenant: str) -> bool:
    """Credits apply to this tenant now."""
    return enabled() and not exempt(tenant)


def _aware(d: datetime | None) -> datetime | None:
    if d is not None and d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def _today() -> str:
    return datetime.now(IST).date().isoformat()


# ------------------------------------------------------------------ the turn (AI-employee jobs)
# one dict per chat turn (set at the turn's start), so tools run side by side still mark the same turn
TURN: contextvars.ContextVar[dict | None] = contextvars.ContextVar("hoola_credit_turn", default=None)


def begin_turn() -> None:
    TURN.set({})


# ------------------------------------------------------------------ spending (buffer -> ledger)
_LOCK = threading.Lock()
_PEND: dict[str, float] = {}          # tenant -> credits not written yet
_PEND_USD: dict[str, float] = {}
_PACK_PEND: dict[tuple[str, str], float] = {}   # (tenant, employee) -> usd


def note(tenant: str, usd: float, feature: str = "") -> None:
    """usage.record calls this for every model call (never raises)."""
    try:
        if not usd or usd <= 0 or not active(tenant):
            return
        t = TURN.get()
        emp = (t or {}).get("employee")
        with _LOCK:
            if emp:
                k = (tenant, emp)
                _PACK_PEND[k] = _PACK_PEND.get(k, 0.0) + usd
                return
            _PEND[tenant] = _PEND.get(tenant, 0.0) + usd / P.USD_PER_CREDIT
            _PEND_USD[tenant] = _PEND_USD.get(tenant, 0.0) + usd
    except Exception:   # noqa: BLE001
        log.exception("credit note failed")


def _wallet(s, tenant: str) -> CreditWallet:
    w = s.get(CreditWallet, tenant)
    if w is None:
        w = CreditWallet(tenant_id=tenant, free_day=_today(), free_used=0.0)
        s.add(w)
        s.flush()
    if w.free_day != _today():
        w.free_day, w.free_used = _today(), 0.0
    t = datetime.now(timezone.utc)
    if w.plan_until is not None and _aware(w.plan_until) <= t and w.plan_left:
        s.add(CreditLedger(tenant_id=tenant, kind="adjust", credits=-w.plan_left, ref=w.plan or "", note="plan month ended"))
        w.plan_left = 0.0
    if w.topup_until is not None and _aware(w.topup_until) <= t and w.topup_left:
        s.add(CreditLedger(tenant_id=tenant, kind="adjust", credits=-w.topup_left, note="top-up credits older than 12 months"))
        w.topup_left = 0.0
    return w


def _free_daily() -> float:
    return float(getattr(_st(), "credits_free_daily", 60.0) or 0.0)


def _take(w: CreditWallet, credits: float) -> None:
    """Free of the day first, then the plan, then top-ups (top-ups may go a little below zero: the last call)."""
    left = credits
    f = max(0.0, _free_daily() - (w.free_used or 0.0))
    a = min(f, left)
    w.free_used = (w.free_used or 0.0) + a
    left -= a
    a = min(max(0.0, w.plan_left or 0.0), left)
    w.plan_left = (w.plan_left or 0.0) - a
    left -= a
    w.topup_left = (w.topup_left or 0.0) - left


def flush() -> None:
    """Write what was spent since the last flush (called by usage's own flush)."""
    with _LOCK:
        items, usds, packs = dict(_PEND), dict(_PEND_USD), dict(_PACK_PEND)
        _PEND.clear()
        _PEND_USD.clear()
        _PACK_PEND.clear()
    if not items and not packs:
        return
    try:
        ensure_table()
        said: list[tuple[str, str]] = []
        with session() as s:
            for tenant, c in items.items():
                w = _wallet(s, tenant)
                before = paid(w)
                _take(w, c)
                w.updated = now()
                s.add(CreditLedger(tenant_id=tenant, kind="spend", credits=-round(c, 4), usd=round(usds.get(tenant, 0.0), 8)))
                line = _low_line(w, before)
                if line:
                    said.append((tenant, line))
            for (tenant, emp), usd in packs.items():
                pk = _pack_row(s, tenant, emp)
                if pk is not None:
                    pk.usd = (pk.usd or 0.0) + usd
        for tenant in items:
            _UNLOCK_CACHE.pop(tenant, None)
        for tenant, line in said:
            _tell(tenant, line)
    except Exception:   # noqa: BLE001
        log.exception("credit flush failed")


def paid(w: CreditWallet) -> float:
    return max(0.0, w.plan_left or 0.0) + max(0.0, w.topup_left or 0.0)


def _low_line(w: CreditWallet, before: float) -> str:
    now_paid = paid(w)
    if before > 0 and now_paid <= 0 and not w.out_said:
        w.out_said = True
        return ("Your paid Hoola credits are used up. Chats now run on Normal with your free credits "
                f"({int(_free_daily())} a day) until you buy more credits.")
    grant = max(w.plan_grant or 0.0, 1000.0)
    if 0 < now_paid < 0.1 * grant and before >= 0.1 * grant and w.low_said != _today():
        w.low_said = _today()
        return (f"Your Hoola credits are running low: {int(now_paid):,} left. Buy more credits, or pick a cheaper tier "
                "in the Quality menu.")
    return ""


def _tell(tenant: str, text: str) -> None:
    try:
        from ..events import notify
        from ..net.service import home_conv
        conv = home_conv(tenant)
        if conv:
            notify(conv, text)
    except Exception:   # noqa: BLE001
        log.exception("credit line failed")


# ------------------------------------------------------------------ reading
def _pending(tenant: str) -> float:
    with _LOCK:
        return _PEND.get(tenant, 0.0)


def view(tenant: str) -> dict[str, Any]:
    if not enabled():
        return {"on": False}
    if exempt(tenant):
        return {"on": True, "exempt": True, "unlocked": True, "can_run": True}
    ensure_table()
    with session() as s:
        w = _wallet(s, tenant)
        spent = _pending(tenant)
        free_left = max(0.0, _free_daily() - (w.free_used or 0.0))
        a = min(free_left, spent)
        free_left -= a
        spent -= a
        plan_left = max(0.0, (w.plan_left or 0.0) - spent)
        spent = max(0.0, spent - (w.plan_left or 0.0))
        top_left = max(0.0, (w.topup_left or 0.0) - spent)
        out = {"on": True, "exempt": False, "free_daily": _free_daily(), "free_left": round(free_left, 1),
               "plan": w.plan, "plan_name": P.PLANS.get(w.plan, {}).get("name", ""),
               "plan_until": _aware(w.plan_until).isoformat() if w.plan_until else None,
               "plan_left": round(plan_left, 1), "topup_left": round(top_left, 1),
               "paid_left": round(plan_left + top_left, 1), "ever_paid": bool(w.ever_paid)}
    out["unlocked"] = out["paid_left"] > 0
    out["can_run"] = out["unlocked"] or out["free_left"] > 0
    return out


_UNLOCK_CACHE: dict[str, tuple[float, bool]] = {}


def unlocked(tenant: str) -> bool:
    """Every tier open (she has paid credits), or credits are off / she is exempt. Read at most every 5 s a tenant."""
    if not active(tenant):
        return True
    import time as _t
    hit = _UNLOCK_CACHE.get(tenant)
    if hit and _t.monotonic() - hit[0] < 5:
        return hit[1]
    try:
        v = bool(view(tenant).get("unlocked"))
    except Exception:   # noqa: BLE001
        log.exception("credit unlocked check failed")
        return True
    _UNLOCK_CACHE[tenant] = (_t.monotonic(), v)
    return v


def can_run(tenant: str) -> bool:
    if not active(tenant):
        return True
    try:
        return bool(view(tenant).get("can_run"))
    except Exception:   # noqa: BLE001
        log.exception("credit can_run check failed")
        return True


def out_text() -> str:
    return (f"You have used today's {int(_free_daily())} free credits. They come back tomorrow - or buy credits "
            "(Settings > Credits) to keep going now.")


def ledger(tenant: str, n: int = 50) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(CreditLedger).where(CreditLedger.tenant_id == tenant)
                         .order_by(CreditLedger.created.desc()).limit(max(1, min(200, n)))).all()
        return [{"kind": r.kind, "credits": round(r.credits, 2), "ref": r.ref, "note": r.note,
                 "at": _aware(r.created).isoformat() if r.created else None} for r in rows]


# ------------------------------------------------------------------ grants (only from a confirmed payment)
def grant(tenant: str, kind: str, item: str, region: str, ref: str, employee: str = "", renewal: bool = False) -> float:
    """Give what a confirmed payment bought. Returns the credits added (0 for an employee package)."""
    ensure_table()
    t = datetime.now(timezone.utc)
    with session() as s:
        w = _wallet(s, tenant)
        if kind == "plan":
            p = P.PLANS[item]
            c = float(p["credits"][region])
            keep = 0.0
            if p.get("carry") and (w.plan_left or 0) > 0:
                keep = min(w.plan_left, c)              # Pro / Max: up to one month carries over
            start = _aware(w.plan_until) if (w.plan_until and _aware(w.plan_until) > t and w.plan == item) else t
            w.plan, w.plan_until = item, start + timedelta(days=P.PLAN_DAYS)
            w.plan_left, w.plan_grant = c + keep, c
            s.add(CreditLedger(tenant_id=tenant, kind="plan", credits=c, ref=ref,
                               note=f"{p['name']} plan{' renewed' if renewal else ''}"))
        elif kind == "topup":
            c = float(P.TOPUPS[item]["credits"])
            w.topup_left = max(0.0, w.topup_left or 0.0) + c
            w.topup_until = t + timedelta(days=P.TOPUP_DAYS)
            s.add(CreditLedger(tenant_id=tenant, kind="topup", credits=c, ref=ref, note=f"{c:,.0f} credits"))
        elif kind == "pack":
            c = 0.0
            pk = P.PACKS[item]
            row = _pack_row(s, tenant, employee)
            if row is None:
                row = EmployeePack(tenant_id=tenant, employee=employee)
                s.add(row)
            base = _aware(row.until) if (row.until and _aware(row.until) > t and row.pack == item) else t
            row.pack, row.jobs, row.used, row.until = item, int(pk["jobs"]), 0, base + timedelta(days=P.PLAN_DAYS)
            s.add(CreditLedger(tenant_id=tenant, kind="pack", credits=0.0, ref=ref,
                               note=f"{pk['name']} package for {employee}: {pk['jobs']} jobs"))
        else:
            raise ValueError(kind)
        w.ever_paid, w.out_said, w.updated = True, False, now()
    _UNLOCK_CACHE.pop(tenant, None)
    return c


def take_back(tenant: str, kind: str, credits: float, ref: str) -> float:
    """A refund: take back what is still there of what the order gave (never below zero)."""
    ensure_table()
    with session() as s:
        w = _wallet(s, tenant)
        if kind == "plan":
            a = min(max(0.0, w.plan_left or 0.0), credits)
            w.plan_left -= a
            if w.plan_left <= 0:
                w.plan_until = datetime.now(timezone.utc)
        else:
            a = min(max(0.0, w.topup_left or 0.0), credits)
            w.topup_left -= a
        s.add(CreditLedger(tenant_id=tenant, kind="refund", credits=-a, ref=ref, note="refunded"))
    _UNLOCK_CACHE.pop(tenant, None)
    return a


# ------------------------------------------------------------------ AI-employee packages
def _pack_row(s, tenant: str, employee: str) -> EmployeePack | None:
    return s.scalars(select(EmployeePack).where(EmployeePack.tenant_id == tenant, EmployeePack.employee == employee)).first()


def pack_view(tenant: str, employee: str) -> dict[str, Any] | None:
    ensure_table()
    with session() as s:
        r = _pack_row(s, tenant, employee)
        if r is None:
            return None
        live = bool(r.until and _aware(r.until) > datetime.now(timezone.utc))
        return {"employee": employee, "pack": r.pack, "name": P.PACKS.get(r.pack, {}).get("name", r.pack),
                "jobs": r.jobs, "used": r.used, "left": max(0, r.jobs - r.used) if live else 0, "active": live,
                "until": _aware(r.until).isoformat() if r.until else None, "tier": P.PACKS.get(r.pack, {}).get("tier", "")}


def packs(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        keys = [r.employee for r in s.scalars(select(EmployeePack).where(EmployeePack.tenant_id == tenant)).all()]
    return [v for v in (pack_view(tenant, k) for k in keys) if v]


def needs_pack(tenant: str, employee: str) -> bool:
    """Hiring / running this employee needs a package that is still live."""
    if not active(tenant) or not bool(getattr(_st(), "credits_employee_packs", True)):
        return False
    v = pack_view(tenant, employee)
    return not (v and v["active"])


def employee_job(tenant: str, employee: str) -> str:
    """An employee's tool is about to run in this turn: count one job (once a turn). '' = go ahead, else why not."""
    if not active(tenant) or not bool(getattr(_st(), "credits_employee_packs", True)):
        return ""
    t = TURN.get()
    if t is not None and employee in t.get("jobs", set()):
        t["employee"] = employee
        return ""
    ensure_table()
    with session() as s:
        r = _pack_row(s, tenant, employee)
        if r is None or not r.until or _aware(r.until) <= datetime.now(timezone.utc):
            return f"This AI employee needs its package first (Settings > Credits > AI employees)."
        if r.used >= r.jobs:
            return (f"This AI employee's package has used all {r.jobs} jobs for this month. Buy the package again "
                    "to add a month, or wait for the next month.")
        r.used += 1
        s.add(CreditLedger(tenant_id=tenant, kind="pack_job", credits=0.0, ref=employee, note=f"job {r.used} of {r.jobs}"))
    if t is not None:
        t.setdefault("jobs", set()).add(employee)
        t["employee"] = employee
    return ""


def pack_tier(tenant: str, employee: str) -> str:
    v = pack_view(tenant, employee) if active(tenant) else None
    return (v or {}).get("tier", "") if v and v.get("active") else ""


# which AI employee a tool belongs to (the employee's own key = its tool for most; the rest named here)
EMP_TOOLS = {"cad_part": "cad", "film_desk": "film", "film_desk_dekho": "film", "game_desk": "game_dev",
             "game_net": "netcode_dev", "game_physics": "physics_dev", "game_audio": "audio_dev",
             "game_haptics": "haptics_dev", "game_xr": "xr_dev", "game_sim": "sim_dev", "game_world": "procgen_dev",
             "game_vfx": "vfx_td", "game_twin": "twin_arch", "software_architect": "architect", "guru": "tutor",
             "guru_dekho": "tutor", "daftar": "school_office", "daftar_dekho": "school_office",
             "pathyakram": "curriculum", "pathyakram_dekho": "curriculum", "shodh": "research", "shodh_dekho": "research",
             "shiksha": "school_register", "shiksha_dekho": "school_register", "prayog": "lab"}


def employee_of(tool: str) -> str:
    try:
        from ..employee import hire as H
    except Exception:   # noqa: BLE001
        return ""
    if tool.startswith("leads_"):
        return "leads"
    k = EMP_TOOLS.get(tool) or (tool[:-6] if tool.endswith("_dekho") else tool)
    c = H.CATALOG.get(k)
    return k if c and c.get("live") else ""


def tool_gate(tenant: str, tool: str) -> str:
    """Before a tool runs: a HIRED employee's tool is a job of its package ('' = go ahead, else why not). An employee
    she has not hired keeps working as before (some tools were always open to everyone) - on her chat credits."""
    if not active(tenant):
        return ""
    emp = employee_of(tool)
    if not emp:
        return ""
    try:
        from ..employee import hire as H
        if not H.is_hired(tenant, emp):
            return ""
    except Exception:   # noqa: BLE001
        return ""
    return employee_job(tenant, emp)
