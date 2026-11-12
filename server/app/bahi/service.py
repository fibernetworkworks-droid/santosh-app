"""The GST & Accounts desk, A0: what the console page shows - honestly, including what is not built yet."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import session
from . import register as REG
from . import rules as RU
from . import wb, wbcheck
from .models import AccGstConn, ensure_tables

PHASES = [
    {"id": "A0", "name": "Foundation", "what": "One register of every document, rules as data, period locks, the WhiteBooks pipe checked on sandbox", "state": "built"},
    {"id": "A1", "name": "Connect your GSTIN", "what": "Enable API access + your OTP, supplier GSTIN and filing checks", "state": "built"},
    {"id": "A2", "name": "Monthly credit (ITC) loop", "what": "IMS accept / reject / pending with reasons, recompute 2B", "state": "built"},
    {"id": "A3", "name": "GSTR-1 / 1A", "what": "GSTR-1 checked before the 11th and saved as a draft on your tap; filing on your EVC OTP stays off until the owner switches it on. GSTR-1A not built yet", "state": "built"},
    {"id": "A4", "name": "GSTR-3B + challan", "what": "Prepared with the least-cash set-off, compared with the portal, saved and set off on your tap; you create and pay the challan yourself; filing off until the owner enables it", "state": "built"},
    {"id": "A5", "name": "e-invoice + e-way bill", "what": "IRN and e-way bills from any Hoola invoice, 30-day window watched", "state": "next"},
    {"id": "A6", "name": "Bills in, checked", "what": "WhatsApp / email / photo bills become checked purchase entries", "state": "planned"},
    {"id": "A7", "name": "Bank + UPI reconciliation", "what": "Every bank line matched with a reason", "state": "planned"},
    {"id": "A8", "name": "Payables, receivables, TDS", "what": "MSME 15 / 45 days, Rule 37, TDS on payments", "state": "planned"},
    {"id": "A9", "name": "Your book + the CA pack", "what": "Tally / Zoho export, the monthly pack for your CA", "state": "planned"},
    {"id": "A10", "name": "Month-end + year-end", "what": "Close checklist, MIS, GSTR-9 draft, deadline watchers", "state": "planned"},
]


def _conns(tenant: str) -> list[dict[str, Any]]:
    from . import connect as CN
    return CN.status(tenant)       # never a password / token / txn


def _scheme_and_flags(tenant: str) -> tuple[str, bool, bool]:
    """What her calendar should include, read from the engines she already uses (no question asked in A0)."""
    scheme, employer, tds = "monthly", False, False
    try:
        from ..gstp.service import GstClient
        with session() as s:
            c = s.scalars(select(GstClient).where(GstClient.tenant_id == tenant, GstClient.active.is_(True))).first()
            if c is not None and c.scheme in ("monthly", "qrmp"):
                scheme = c.scheme
    except Exception:   # noqa: BLE001
        pass
    try:
        from ..payroll import service as P
        with session() as s:
            employer = s.scalars(select(P.PayEmployee).where(P.PayEmployee.tenant_id == tenant)).first() is not None
    except Exception:   # noqa: BLE001
        pass
    return scheme, employer, tds


def overview(tenant: str, today: date | None = None) -> dict[str, Any]:
    from ..employee import hire
    today = today or date.today()
    period = f"{today.year:04d}-{today.month:02d}"
    prev = REG.months_back(2, today)[1]
    scheme, employer, tds = _scheme_and_flags(tenant)
    calls = 0
    try:
        calls = wb.calls_today(tenant)
    except Exception:   # noqa: BLE001
        pass
    last = wbcheck.last()
    return {
        "enabled": bool(get_settings().bahi_enabled),
        "employee": {"key": "accounts", "status": hire.status(tenant, "accounts")},
        "period": period, "prev_period": prev,
        "this_month": REG.summary(tenant, period), "last_month": REG.summary(tenant, prev),
        # the work for LAST month's period falls due this month - that is what she must act on now
        "dues": RU.dues_for(prev, scheme=scheme, employer=employer, tds=tds, today=today),
        "scheme": scheme,
        "whitebooks": {**wb.status(), "calls_today": calls, "env_lines": wb.env_lines(),
                       "last_check": ({k: last.get(k) for k in ("env", "at", "passed", "failed", "skipped", "steps")} if last else None)},
        "connections": _conns(tenant),
        "rules": RU.freshness(today),
        "sources": REG.SOURCES,
        "events": REG.events(tenant, 12),
        "phases": PHASES,
        "filing": bool(get_settings().bahi_filing),
    }
