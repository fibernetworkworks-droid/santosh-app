"""v0.999.47 SAVED SIGN-INS - her portal logins kept for the next time (Dots 'Save to Passwords', Grok Bot Vault).

Owner (20 Nov 2026), item 1 of "DO THIS FOR HOOLA": a site that logged her out should not need her password again.

- Saved only when she ticks 'Save for next time' on the private sign-in form (never by Hoola on its own).
- Sealed with the same key as her ID locker (Fernet). The user name is shown masked, the password never leaves the server
  except into the PC's field.
- Reusing one needs her tap ('Use saved sign-in') - like Dots, a saved login is not used without her confirmation.
- Never for bank / card / payment / UPI sites (those sign-ins are always hers).
- Keyed by the site's host (gst.gov.in, services.gst.gov.in -> gst.gov.in) else the site name she was asked for.
- She sees the list and deletes any of them (Hoola Computer page).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.pc")


class PcLogin(Base):
    __tablename__ = "pc_logins"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pcl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(120), index=True)          # the key: host or the site's name
    label: Mapped[str] = mapped_column(String(120), default="")         # what she was shown ('GST portal')
    user_sealed: Mapped[str] = mapped_column(Text, default="")
    pw_sealed: Mapped[str] = mapped_column(Text, default="")
    user_masked: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    PcLogin.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


MONEY_SITE = re.compile(r"\b(bank|banking|netbanking|net\s*banking|credit\s*card|debit\s*card|card|upi|paytm|phonepe|"
                        r"gpay|google\s*pay|razorpay|payment|wallet|sbi|hdfc|icici|axis|kotak|pnb|yes\s*bank|"
                        r"demat|zerodha|groww|upstox|broker)\b", re.I)


def key_of(site: str, url: str = "") -> str:
    host = ""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        host = ""
    if host:
        parts = [p for p in host.split(".") if p]
        if host.startswith("www."):
            parts = parts[1:]
        # keep the registrable part: gst.gov.in, irctc.co.in, incometax.gov.in
        if len(parts) >= 3 and parts[-2] in ("gov", "co", "nic", "org", "ac", "net", "edu") and len(parts[-1]) == 2:
            return ".".join(parts[-3:])
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    return re.sub(r"[^a-z0-9]+", " ", str(site or "").lower()).strip()[:120]


def money_site(site: str, url: str = "") -> bool:
    return bool(MONEY_SITE.search(f"{site} {url}"))


def _mask(user: str) -> str:
    u = str(user or "")
    if not u:
        return ""
    if "@" in u:
        name, dom = u.split("@", 1)
        return (name[:1] + "***@" + dom)[:80]
    return (u[:2] + "***" + u[-2:] if len(u) > 5 else u[:1] + "***")[:80]


def view(r: PcLogin) -> dict[str, Any]:
    return {"id": r.id, "site": r.site, "label": r.label or r.site, "user": r.user_masked,
            "saved": r.created_at.isoformat() if r.created_at else "", "used": r.used_at.isoformat() if r.used_at else ""}


def find(tenant: str, key: str) -> dict[str, Any] | None:
    if not key:
        return None
    ensure_table()
    with session() as s:
        r = s.execute(select(PcLogin).where(PcLogin.tenant_id == tenant, PcLogin.site == key)
                      .order_by(PcLogin.created_at.desc())).scalars().first()
        return view(r) if r else None


def save(tenant: str, key: str, label: str, user: str, pw: str) -> dict[str, Any]:
    from ..idvault import _seal
    if not key or not pw:
        raise ValueError("Nothing to save.")
    if money_site(label, key):
        raise ValueError("Bank, card and payment sign-ins are never saved.")
    ensure_table()
    with session() as s:
        r = s.execute(select(PcLogin).where(PcLogin.tenant_id == tenant, PcLogin.site == key)).scalars().first()
        if r is None:
            r = PcLogin(tenant_id=tenant, site=key)
            s.add(r)
        r.label = str(label or key)[:120]
        r.user_sealed, r.pw_sealed = (_seal(user) if user else ""), _seal(pw)
        r.user_masked = _mask(user)
        r.created_at = now()
        s.flush()
        log.info("pc saved sign-in for %s (tenant %s)", key, tenant)
        return view(r)


def open_(tenant: str, lid: str) -> tuple[str, str]:
    """The real user name + password, for the PC's field only (never returned to the model or a client)."""
    from ..idvault import _open
    ensure_table()
    with session() as s:
        r = s.get(PcLogin, lid)
        if r is None or r.tenant_id != tenant:
            raise ValueError("That saved sign-in is gone.")
        r.used_at = now()
        return (_open(r.user_sealed) if r.user_sealed else ""), _open(r.pw_sealed)


def list_(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.execute(select(PcLogin).where(PcLogin.tenant_id == tenant).order_by(PcLogin.site)).scalars().all()
        return [view(r) for r in rows]


def delete(tenant: str, lid: str) -> bool:
    ensure_table()
    with session() as s:
        r = s.get(PcLogin, lid)
        if r is None or r.tenant_id != tenant:
            return False
        s.delete(r)
        return True
