"""v0.314 HIRE AN EMPLOYEE: the owner picks an AI employee in the Employee Hub (web console or app); only then does its
desk appear on her surfaces and its 24/7 jobs run. SEO Specialist is the first one; the rest of the catalogue shows as
"coming" so she sees where Hoola is going.

States: hired -> paused -> hired (resume) ; hired / paused -> left. Letting go stops every job at once and keeps the
history read-only (nothing is deleted). One row per (tenant, employee key)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session


class HireError(Exception):
    pass


class HiredEmployee(Base):
    __tablename__ = "hired_employees"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("he"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(10), default="hired")          # hired | paused | left
    trust: Mapped[str] = mapped_column(String(10), default="seekh")           # seekh | saathi | bharosa
    settings: Mapped[str] = mapped_column(Text, default="{}")
    hired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_table() -> None:
    """Self-heal (the table is also created by db.init_db): once per database engine."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        HiredEmployee.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


TRUST = ("seekh", "saathi", "bharosa")

# The catalogue. `live` employees can be hired today; the others show as "coming".
CATALOG: dict[str, dict[str, Any]] = {
    "seo": {
        "name": "SEO Specialist", "live": True, "icon": "search",
        "pitch": "Gets your business found on Google and in AI answers. Works 24/7 on your website and Google profile.",
        "does": ["Full audit of your website every week (up to 500 pages) with a fix list",
                 "Watches your site every hour: down, blocked from Google, pages dropped",
                 "Reads your Search Console and Google Analytics: clicks, searches, leads from Google",
                 "Core Web Vitals (speed) on mobile",
                 "A 90-day plan you approve, worked as a weekly board",
                 "Weekly note and a monthly PDF report with charts"],
        "needs": ["Your website address", "Google sign-in for Search Console (and Analytics, if you use it)"],
        "never": ["Buy links or fake reviews", "Publish anything on your site or Google profile without your OK",
                  "Make mass AI pages or doorway pages", "Promise a ranking"],
    },
    "social": {"name": "Social Media Manager", "live": False, "icon": "share",
               "pitch": "Plans, writes and schedules your Instagram, Facebook and WhatsApp status posts."},
    "accounts": {"name": "Accounts Assistant", "live": False, "icon": "receipt",
                 "pitch": "Bills, GST returns, payments due and the monthly books."},
    "telecaller": {"name": "Telecaller", "live": False, "icon": "phone",
                   "pitch": "Calls your leads and customers with a script, notes every answer."},
    "support": {"name": "Customer Support", "live": False, "icon": "chat",
                "pitch": "Answers customer questions on WhatsApp and email from your own FAQ."},
}


def _row(s, tenant: str, key: str) -> HiredEmployee | None:
    return s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant, HiredEmployee.key == key)
                     .order_by(HiredEmployee.hired_at.desc())).first()


def _view(r: HiredEmployee | None) -> dict[str, Any]:
    if r is None:
        return {"status": "none"}
    try:
        st = json.loads(r.settings or "{}")
    except ValueError:
        st = {}
    return {"status": r.status, "trust": r.trust, "hired_at": r.hired_at.isoformat() if r.hired_at else "",
            "left_at": r.left_at.isoformat() if r.left_at else "", "settings": st}


def status(tenant: str, key: str) -> str:
    """'none' | 'hired' | 'paused' | 'left'."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        return r.status if r else "none"


def is_hired(tenant: str, key: str) -> bool:
    """Hired and working (paused counts as hired for the desk, not for the 24/7 jobs: see is_working)."""
    return status(tenant, key) in ("hired", "paused")


def is_working(tenant: str, key: str) -> bool:
    return status(tenant, key) == "hired"


def hired_keys(tenant: str) -> dict[str, str]:
    """{key: status} for every employee she has hired and not let go (the surfaces use this to show desks)."""
    ensure_table()
    out: dict[str, str] = {}
    with session() as s:
        for r in s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant)
                           .order_by(HiredEmployee.hired_at)).all():
            if r.status in ("hired", "paused"):
                out[r.key] = r.status
            else:
                out.pop(r.key, None)
    return out


def working_tenants(key: str) -> list[str]:
    """Every tenant whose `key` employee is hired and not paused (the 24/7 scheduler walks these)."""
    ensure_table()
    with session() as s:
        return sorted({r.tenant_id for r in s.scalars(select(HiredEmployee).where(HiredEmployee.key == key,
                                                                                  HiredEmployee.status == "hired")).all()})


def catalog(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    out = []
    with session() as s:
        for key, c in CATALOG.items():
            out.append({"key": key, **c, **_view(_row(s, tenant, key))})
    return out


def hire(tenant: str, key: str, trust: str = "seekh") -> dict[str, Any]:
    c = CATALOG.get(key)
    if c is None:
        raise HireError("Aisa koi employee nahi.")
    if not c.get("live"):
        raise HireError(f"{c['name']} abhi taiyaar ho raha hai; jald aayega.")
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is not None and r.status in ("hired", "paused"):
            r.status = "hired"
            return {"key": key, **_view(r), "already": True}
        r = HiredEmployee(tenant_id=tenant, key=key, status="hired",
                          trust=trust if trust in TRUST else "seekh", settings="{}")
        s.add(r)
        s.flush()
        return {"key": key, **_view(r)}


def _set(tenant: str, key: str, status_: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        r.status = status_
        if status_ == "left":
            r.left_at = now()
        return {"key": key, **_view(r)}


def pause(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "paused")


def resume(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "hired")


def leave(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "left")


def settings(tenant: str, key: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        return _view(_row(s, tenant, key)).get("settings", {})


def save_settings(tenant: str, key: str, **kw: Any) -> dict[str, Any]:
    """Merge keys into the employee's settings (trust is its own column)."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        st = _view(r)["settings"]
        trust = kw.pop("trust", None)
        if trust in TRUST:
            r.trust = trust
        st.update({k: v for k, v in kw.items() if v is not None})
        r.settings = json.dumps(st, ensure_ascii=False)
        return _view(r)
