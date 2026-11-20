"""v0.999.60 HOOLA WALLET (owner: "WALLET FOR AI --- USER WILL PUT SOME MONEY THERE AND AI WILL MAKE TRANSACTION VIA THAT ---
WITH APPROVAL FROM USER -- ORDERING DAILY NEED, BILL PAYMENTS, FOOD ORDER" + "ENTIRE WORLD" -> design
claude.ai/artifact/6saoWTun5YqusMghbLzYgn -> "GO BUILD ALL").

What it is: Hoola's spending rules, the approval card and the ledger for everything Hoola buys for her.
- Hoola NEVER holds money. A loaded balance needs a licensed partner in her country (RBI PPI in India, e-money /
  card issuing elsewhere); until `WALLET_PARTNER` names one, the wallet runs in "pay each time" mode (her own UPI or
  card at the shop's checkout). Every route says which.
- Every payment needs her approval on her UNLOCKED PHONE (Hoola's rule: money never moves without her tap; payments
  need an unlocked phone). The console only sends the request to her phone.
- Limits are checked twice: when Hoola asks, and again at the moment she approves.
- Never, whatever the chat says: paying a person, loans / investments / crypto / betting / gift cards, or paying
  because a website / mail / message told it to (the request must come from her own words).
- After she approves, Hoola is woken in that chat to finish the order; the payment row records the result.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.wallet")

REGIONS = {"IN": ("INR", "₹", "India"), "US": ("USD", "$", "United States"), "GB": ("GBP", "£", "United Kingdom"),
           "EU": ("EUR", "€", "Europe"), "AE": ("AED", "AED ", "UAE"), "SG": ("SGD", "S$", "Singapore")}
CATEGORIES = ["groceries", "food", "bills", "recharge", "shopping", "travel"]
CAT_LABEL = {"groceries": "Groceries and daily needs", "food": "Food orders", "bills": "Bills", "recharge": "Mobile recharges",
             "shopping": "Shopping", "travel": "Travel"}
NEVER = re.compile(r"\b(send money to|transfer to|pay (?:him|her|them)|loan|emi|invest(?:ment)?|mutual fund|stocks?|shares|crypto|bitcoin|"
                   r"bet(?:ting)?|casino|lottery|gift ?cards?|wallet top.?up|upi to)\b", re.I)
EXPIRE_MIN = 10


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    region: Mapped[str] = mapped_column(String(4), default="IN")
    mode: Mapped[str] = mapped_column(String(12), default="each")          # each | balance (partner only)
    monthly: Mapped[int] = mapped_column(Integer, default=1_000_000)       # minor units (paise / cents)
    per_buy: Mapped[int] = mapped_column(Integer, default=200_000)
    per_day: Mapped[int] = mapped_column(Integer, default=300_000)
    cats: Mapped[str] = mapped_column(Text, default="")                    # json {cat: {on, limit}}
    known_only: Mapped[bool] = mapped_column(Boolean, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[int] = mapped_column(Integer, default=0)               # only with a partner (their number)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WalletPayment(Base):
    __tablename__ = "wallet_payments"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), default="")
    shop: Mapped[str] = mapped_column(String(120), default="")
    shop_host: Mapped[str] = mapped_column(String(120), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(4), default="INR")
    category: Mapped[str] = mapped_column(String(20), default="groceries")
    status: Mapped[str] = mapped_column(String(16), default="waiting")     # waiting|approved|paid|declined|stopped|expired|failed|refunded
    reason: Mapped[str] = mapped_column(String(300), default="")
    method: Mapped[str] = mapped_column(String(40), default="")
    new_shop: Mapped[bool] = mapped_column(Boolean, default=False)
    bill_id: Mapped[str] = mapped_column(String(40), default="")
    order_ref: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WalletBill(Base):
    __tablename__ = "wallet_bills"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wbl"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")            # 'Electricity · MSEDCL'
    kind: Mapped[str] = mapped_column(String(20), default="electricity")
    site: Mapped[str] = mapped_column(String(200), default="")            # where Hoola pays it
    account_masked: Mapped[str] = mapped_column(String(40), default="")
    account_sealed: Mapped[str] = mapped_column(Text, default="")
    due: Mapped[str] = mapped_column(String(10), default="")              # YYYY-MM-DD
    amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="upcoming")   # upcoming | due | paid
    remind: Mapped[bool] = mapped_column(Boolean, default=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_TABLE_OK: set[int] = set()


def ensure_table() -> None:
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _TABLE_OK:
        return
    for t in (WalletAccount, WalletPayment, WalletBill):
        t.__table__.create(bind=eng, checkfirst=True)
    _TABLE_OK.add(id(eng))


class WalletError(Exception):
    pass


def _aware(d: datetime | None) -> datetime | None:
    return d if d is None or d.tzinfo else d.replace(tzinfo=timezone.utc)


def partner() -> str:
    """The licensed partner that holds wallet balances here ('' = none yet: pay each time only)."""
    from .config import get_settings
    return str(getattr(get_settings(), "wallet_partner", "") or "").strip()


def _cats(a: WalletAccount) -> dict[str, dict[str, Any]]:
    try:
        c = json.loads(a.cats or "{}")
    except Exception:
        c = {}
    base = {"groceries": {"on": True, "limit": 400_000}, "food": {"on": True, "limit": 150_000}, "bills": {"on": True, "limit": 400_000},
            "recharge": {"on": True, "limit": 100_000}, "shopping": {"on": False, "limit": 300_000}, "travel": {"on": False, "limit": 500_000}}
    for k, v in (c or {}).items():
        if k in base and isinstance(v, dict):
            base[k] = {"on": bool(v.get("on", base[k]["on"])), "limit": max(0, int(v.get("limit", base[k]["limit"])))}
    return base


def _acct(s, tenant: str, make: bool = False) -> WalletAccount | None:
    a = s.get(WalletAccount, tenant)
    if a is None and make:
        a = WalletAccount(tenant_id=tenant, cats=json.dumps(_cats(WalletAccount())))
        s.add(a)
        s.flush()
    return a


def _host(u: str) -> str:
    from urllib.parse import urlparse
    try:
        h = (urlparse(u if "://" in u else "https://" + u).hostname or "").lower()
    except Exception:
        h = ""
    return h[4:] if h.startswith("www.") else h


def _spent(s, tenant: str, since: datetime, cat: str = "") -> int:
    q = select(WalletPayment).where(WalletPayment.tenant_id == tenant, WalletPayment.status.in_(("approved", "paid")))
    tot = 0
    for p in s.execute(q).scalars().all():
        if (_aware(p.decided_at) or _aware(p.created_at)) >= since and (not cat or p.category == cat):
            tot += p.amount
    return tot


def _month_start() -> datetime:
    n = datetime.now(timezone.utc)
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _day_start() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)


def money(minor: int, region: str = "IN") -> str:
    sym = REGIONS.get(region, REGIONS["IN"])[1]
    v = minor / 100
    if region == "IN":
        whole, _, frac = f"{v:.2f}".partition(".")
        n = whole[-3:]
        rest = whole[:-3]
        while rest:
            n = rest[-2:] + "," + n
            rest = rest[:-2]
        s = n + ("" if frac == "00" else "." + frac)
        return f"{sym} {s}"
    return f"{sym}{v:,.2f}"


def check(s, a: WalletAccount, tenant: str, category: str, amount: int, title: str) -> str:
    """'' = within her rules, else the plain reason it is not allowed (Hoola does not ask her for it)."""
    if a.paused:
        return "You paused all spending."
    if NEVER.search(title or "") or category not in CATEGORIES:
        return "Hoola Wallet never pays people, loans, investments, crypto, betting or gift cards."
    c = _cats(a).get(category, {"on": False, "limit": 0})
    if not c["on"]:
        return f"{CAT_LABEL.get(category, category)} is switched off in your limits."
    if amount <= 0:
        return "There is no amount to pay."
    if amount > a.per_buy:
        return f"Over your per-payment limit of {money(a.per_buy, a.region)}."
    day = _spent(s, tenant, _day_start())
    if day + amount > a.per_day:
        return f"Over your daily limit of {money(a.per_day, a.region)}."
    month = _spent(s, tenant, _month_start())
    if month + amount > a.monthly:
        return f"Over your monthly limit of {money(a.monthly, a.region)} ({money(max(0, a.monthly - month), a.region)} left)."
    cm = _spent(s, tenant, _month_start(), category)
    if cm + amount > c["limit"]:
        return f"Over your {CAT_LABEL[category].lower()} limit of {money(c['limit'], a.region)} this month."
    return ""


# ------------------------------------------------------------------------------------------------ views
def view_payment(p: WalletPayment, region: str = "IN") -> dict[str, Any]:
    try:
        items = json.loads(p.items or "[]")
    except Exception:
        items = []
    exp = _aware(p.expires_at)
    if p.status == "waiting" and exp and exp < datetime.now(timezone.utc):
        status = "expired"
    else:
        status = p.status
    return {"id": p.id, "shop": p.shop, "shop_host": p.shop_host, "title": p.title, "items": items, "amount": p.amount,
            "amount_text": money(p.amount, region), "currency": p.currency, "category": p.category, "status": status,
            "reason": p.reason, "method": p.method, "new_shop": p.new_shop, "order_ref": p.order_ref, "bill_id": p.bill_id,
            "conversation_id": p.conversation_id,
            "created": _aware(p.created_at).isoformat() if p.created_at else "",
            "expires": exp.isoformat() if exp else "", "decided": _aware(p.decided_at).isoformat() if p.decided_at else "",
            "paid": _aware(p.paid_at).isoformat() if p.paid_at else ""}


def view_bill(b: WalletBill, region: str = "IN") -> dict[str, Any]:
    return {"id": b.id, "name": b.name, "kind": b.kind, "site": b.site, "account": b.account_masked, "due": b.due,
            "amount": b.amount, "amount_text": money(b.amount, region) if b.amount else "", "status": b.status, "remind": b.remind,
            "paid": _aware(b.paid_at).isoformat() if b.paid_at else ""}


def overview(tenant: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        a = _acct(s, tenant)
        if a is None:
            return {"exists": False, "partner": partner(), "regions": {k: {"currency": v[0], "symbol": v[1], "name": v[2]} for k, v in REGIONS.items()},
                    "categories": CAT_LABEL}
        _expire(s, tenant)
        month = _spent(s, tenant, _month_start())
        by = {c: _spent(s, tenant, _month_start(), c) for c in CATEGORIES}
        rows = s.execute(select(WalletPayment).where(WalletPayment.tenant_id == tenant).order_by(WalletPayment.created_at.desc()).limit(200)).scalars().all()
        bills = s.execute(select(WalletBill).where(WalletBill.tenant_id == tenant).order_by(WalletBill.due)).scalars().all()
        cats = _cats(a)
        return {"exists": True, "partner": partner(), "region": a.region, "currency": REGIONS.get(a.region, REGIONS["IN"])[0],
                "symbol": REGIONS.get(a.region, REGIONS["IN"])[1], "mode": a.mode, "paused": a.paused,
                "balance": a.balance if partner() and a.mode == "balance" else None,
                "limits": {"monthly": a.monthly, "per_buy": a.per_buy, "per_day": a.per_day, "known_only": a.known_only, "cats": cats},
                "spent": {"month": month, "left": max(0, a.monthly - month), "by": by},
                "text": {"month": money(month, a.region), "left": money(max(0, a.monthly - month), a.region), "monthly": money(a.monthly, a.region),
                         "per_buy": money(a.per_buy, a.region), "per_day": money(a.per_day, a.region),
                         "by": {c: money(by[c], a.region) for c in CATEGORIES}, "cat_limit": {c: money(cats[c]["limit"], a.region) for c in CATEGORIES}},
                "payments": [view_payment(p, a.region) for p in rows], "bills": [view_bill(b, a.region) for b in bills],
                "regions": {k: {"currency": v[0], "symbol": v[1], "name": v[2]} for k, v in REGIONS.items()}, "categories": CAT_LABEL}


def _expire(s, tenant: str) -> None:
    n = datetime.now(timezone.utc)
    for p in s.execute(select(WalletPayment).where(WalletPayment.tenant_id == tenant, WalletPayment.status == "waiting")).scalars().all():
        if _aware(p.expires_at) and _aware(p.expires_at) < n:
            p.status, p.reason = "expired", "Not approved within 10 minutes."


# ------------------------------------------------------------------------------------------------ actions
def setup(tenant: str, region: str, mode: str, monthly: int, cats: list[str]) -> dict[str, Any]:
    ensure_table()
    if region not in REGIONS:
        raise WalletError("That country is not supported yet.")
    if mode == "balance" and not partner():
        raise WalletError("A wallet balance needs a licensed payment partner in your country, and none is connected yet. "
                          "Choose 'Pay each time' for now.")
    with session() as s:
        a = _acct(s, tenant, make=True)
        a.region, a.mode = region, ("balance" if mode == "balance" else "each")
        a.monthly = max(0, int(monthly))
        a.per_buy = min(a.per_buy, a.monthly) if a.monthly else a.per_buy
        c = _cats(a)
        for k in CATEGORIES:
            c[k]["on"] = k in (cats or [])
        a.cats = json.dumps(c)
        a.updated_at = now()
    return overview(tenant)


def set_limits(tenant: str, body: dict[str, Any]) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        a = _acct(s, tenant, make=True)
        for k in ("monthly", "per_buy", "per_day"):
            if k in body:
                setattr(a, k, max(0, int(body[k])))
        if "known_only" in body:
            a.known_only = bool(body["known_only"])
        if "paused" in body:
            a.paused = bool(body["paused"])
        if isinstance(body.get("cats"), dict):
            c = _cats(a)
            for k, v in body["cats"].items():
                if k in c and isinstance(v, dict):
                    if "on" in v:
                        c[k]["on"] = bool(v["on"])
                    if "limit" in v:
                        c[k]["limit"] = max(0, int(v["limit"]))
            a.cats = json.dumps(c)
        a.updated_at = now()
        if body.get("paused"):
            for p in s.execute(select(WalletPayment).where(WalletPayment.tenant_id == tenant, WalletPayment.status == "waiting")).scalars().all():
                p.status, p.reason, p.decided_at = "stopped", "You paused all spending.", now()
    return overview(tenant)


def request(tenant: str, conv: str, shop: str, url: str, title: str, items: list[dict[str, Any]], amount: int,
            category: str, bill_id: str = "") -> dict[str, Any]:
    """Hoola asks to pay. Inside her rules = a waiting card on her phone; outside = recorded as stopped (never asked)."""
    ensure_table()
    with session() as s:
        a = _acct(s, tenant)
        if a is None:
            raise WalletError("Hoola Wallet is not set up yet. Open Hoola Wallet once and set your limits.")
        _expire(s, tenant)
        host = _host(url) if url else ""
        clean = []
        for it in (items or [])[:40]:
            try:
                clean.append({"name": str(it.get("name", ""))[:120], "qty": int(it.get("qty") or 1), "amount": max(0, int(it.get("amount") or 0))})
            except Exception:
                continue
        why = check(s, a, tenant, category, int(amount), f"{title} {shop}")
        known = bool(host) and s.execute(select(WalletPayment).where(WalletPayment.tenant_id == tenant, WalletPayment.shop_host == host,
                                                                      WalletPayment.status == "paid")).first() is not None
        p = WalletPayment(tenant_id=tenant, conversation_id=conv or "", shop=shop[:120], shop_host=host, title=title[:200],
                          items=json.dumps(clean), amount=int(amount), currency=REGIONS.get(a.region, REGIONS["IN"])[0],
                          category=category, bill_id=bill_id, new_shop=bool(a.known_only and host and not known),
                          status="stopped" if why else "waiting", reason=why,
                          expires_at=None if why else datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN))
        s.add(p)
        s.flush()
        out = view_payment(p, a.region)
    if not why:
        _announce(conv, out)
    log.info("wallet request %s %s %s %s -> %s", out["id"], category, out["amount_text"], shop, out["status"])
    return out


def _announce(conv: str, p: dict[str, Any]) -> None:
    try:
        from .events import bus
        if conv:
            bus.publish(conv, "wallet_pay", {**p, "card": "wallet_pay"})
    except Exception:
        log.exception("wallet card publish failed")


def approval_card(tenant: str, pid: str) -> dict[str, Any] | None:
    """What her fingerprint signs (approvekey kind 'wallet'): the payment as it is NOW."""
    ensure_table()
    with session() as s:
        p = s.get(WalletPayment, pid)
        if p is None or p.tenant_id != tenant:
            return None
        a = _acct(s, tenant)
        v = view_payment(p, a.region if a else "IN")
    if v["status"] != "waiting":
        return None
    return {"title": f"Pay {v['shop']}" if v["shop"] else "Hoola Wallet payment", "payee": v["shop"], "amount": v["amount_text"],
            "items": [f"{i.get('name', '')} x{i.get('qty', 1)}" for i in v["items"]][:20], "for": v["title"]}


def decide(tenant: str, pid: str, approve: bool, unlocked: bool, proof: dict[str, Any] | None = None) -> dict[str, Any]:
    """Her answer. Approving needs her fingerprint signature from a linked phone (approvekey); a phone not linked for
    fingerprint approvals must at least be unlocked by her (the app unlocks first). Limits are checked again."""
    ensure_table()
    if approve:
        from . import approvekey as ak
        if ak.active_on(tenant):
            try:
                ak.verify(tenant, "wallet", pid, proof)
            except ak.ApproveError as e:
                raise WalletError(str(e))
        elif not unlocked:
            raise WalletError("Approve on your phone: payments need your unlocked phone.")
    with session() as s:
        p = s.get(WalletPayment, pid)
        if p is None or p.tenant_id != tenant:
            raise WalletError("Not found.")
        _expire(s, tenant)
        if p.status != "waiting":
            raise WalletError(f"This payment is already {p.status}.")
        a = _acct(s, tenant)
        if not approve:
            p.status, p.reason, p.decided_at = "declined", "You said no.", now()
            out = view_payment(p, a.region if a else "IN")
            approved = False
        else:
            why = check(s, a, tenant, p.category, p.amount, f"{p.title} {p.shop}") if a else "No wallet."
            if why:
                p.status, p.reason, p.decided_at = "stopped", why, now()
                out = view_payment(p, a.region if a else "IN")
                approved = False
            else:
                p.status, p.decided_at, p.method = "approved", now(), ("wallet" if a.mode == "balance" else "pay each time")
                out = view_payment(p, a.region)
                approved = True
        conv = p.conversation_id
    try:
        from .events import bus
        if conv:
            bus.publish(conv, "wallet_pay", {**out, "card": "wallet_pay"})
    except Exception:
        pass
    if approved and conv:
        _wake(tenant, conv, out)
    log.info("wallet %s %s", pid, out["status"])
    return out


def _wake(tenant: str, conv: str, p: dict[str, Any]) -> None:
    """She approved: Hoola is woken in that chat to finish the order (the PC pays at the shop's checkout)."""
    text = (f"[Hoola Wallet] She approved payment {p['id']}: {p['amount_text']} to {p['shop']} for \"{p['title']}\". "
            f"Finish this order now (the checkout is on the Hoola PC). Pay exactly {p['amount_text']} and nothing else; if the shop's "
            f"total is different, stop and ask her again with a new hoola_wallet request. When the shop confirms, call hoola_wallet "
            f"action=paid with payment_id={p['id']} and the order number; if it fails, action=failed with the reason.")
    try:
        import asyncio

        from . import turn_inbox
        ti = turn_inbox.accept(tenant, conv, text, False, "", "", actor="wallet")
        coro = turn_inbox.run_owned(ti, conv, text, tenant, False, save_user=False, actor="wallet")
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            from .operator import service as _op
            if _op.MAIN_LOOP is None:
                coro.close()
                raise RuntimeError("no main loop")
            asyncio.run_coroutine_threadsafe(coro, _op.MAIN_LOOP)
    except Exception:
        log.exception("wallet wake failed for %s", p.get("id"))


def finish(tenant: str, pid: str, ok: bool, order_ref: str = "", reason: str = "") -> dict[str, Any]:
    ensure_table()
    with session() as s:
        p = s.get(WalletPayment, pid)
        if p is None or p.tenant_id != tenant:
            raise WalletError("Not found.")
        if p.status != "approved":
            raise WalletError("Only an approved payment can be marked paid or failed.")
        p.status = "paid" if ok else "failed"
        p.order_ref, p.reason = str(order_ref or "")[:120], str(reason or "")[:300]
        p.paid_at = now() if ok else None
        if ok and p.bill_id:
            b = s.get(WalletBill, p.bill_id)
            if b is not None and b.tenant_id == tenant:
                b.status, b.paid_at = "paid", now()
        a = _acct(s, tenant)
        return view_payment(p, a.region if a else "IN")


def add_bill(tenant: str, name: str, kind: str, site: str, account: str, due: str, amount: int) -> dict[str, Any]:
    from .idvault import _seal
    ensure_table()
    with session() as s:
        if _acct(s, tenant) is None:
            raise WalletError("Set up Hoola Wallet first.")
        acc = re.sub(r"\s+", "", str(account or ""))
        b = WalletBill(tenant_id=tenant, name=name[:120], kind=kind[:20] or "other", site=site[:200],
                       account_masked=("••" + acc[-4:]) if acc else "", account_sealed=_seal(acc) if acc else "",
                       due=due[:10], amount=max(0, int(amount or 0)), status="due" if amount else "upcoming")
        s.add(b)
        s.flush()
        return view_bill(b)


def delete_bill(tenant: str, bid: str) -> bool:
    ensure_table()
    with session() as s:
        b = s.get(WalletBill, bid)
        if b is None or b.tenant_id != tenant:
            return False
        s.delete(b)
        return True


def pay_bill(tenant: str, conv: str, bid: str) -> dict[str, Any]:
    with session() as s:
        b = s.get(WalletBill, bid)
        if b is None or b.tenant_id != tenant:
            raise WalletError("Not found.")
        if not b.amount:
            raise WalletError("This bill has no amount yet.")
        name, site, amount = b.name, b.site, b.amount
    return request(tenant, conv, name, site, f"Bill: {name}", [], amount, "bills", bill_id=bid)


# ------------------------------------------------------------------------------------------------ routes
class SetupIn(BaseModel):
    region: str = "IN"
    mode: str = "each"
    monthly: int = Field(default=1_000_000, ge=0)
    cats: list[str] = Field(default_factory=lambda: ["groceries", "food", "bills", "recharge"])


class DecideIn(BaseModel):
    approve: bool
    proof: dict | None = None      # her fingerprint signature (approvekey kind 'wallet')


class BillIn(BaseModel):
    name: str = Field(max_length=120)
    kind: str = Field(default="other", max_length=20)
    site: str = Field(default="", max_length=200)
    account: str = Field(default="", max_length=60)
    due: str = Field(default="", max_length=10)
    amount: int = Field(default=0, ge=0)

    def __repr__(self) -> str:
        return f"BillIn(name={self.name!r})"


def mount(app, current_tenant, require_key) -> None:
    r = APIRouter()

    def _e(e: WalletError) -> HTTPException:
        return HTTPException(404 if str(e) == "Not found." else 409, str(e))

    @r.get("/api/wallet", dependencies=[Depends(require_key)])
    def w_get(tenant: str = Depends(current_tenant)):
        return overview(tenant)

    @r.post("/api/wallet/setup", dependencies=[Depends(require_key)])
    def w_setup(body: SetupIn, tenant: str = Depends(current_tenant)):
        try:
            return setup(tenant, body.region, body.mode, body.monthly, body.cats)
        except WalletError as e:
            raise _e(e)

    @r.put("/api/wallet/limits", dependencies=[Depends(require_key)])
    def w_limits(body: dict, tenant: str = Depends(current_tenant)):
        return set_limits(tenant, body or {})

    @r.post("/api/wallet/payments/{pid}/decide", dependencies=[Depends(require_key)])
    def w_decide(pid: str, body: DecideIn, request: Request, tenant: str = Depends(current_tenant)):
        unlocked = request.headers.get("x-hoola-unlocked", "") == "1"
        try:
            return decide(tenant, pid, body.approve, unlocked, body.proof)
        except WalletError as e:
            if str(e) in ("fingerprint_needed", "fingerprint_invalid"):
                raise HTTPException(428, "Approve with your fingerprint on your phone." if str(e) == "fingerprint_needed"
                                    else "The fingerprint check did not match this payment. Try again on your phone.")
            raise _e(e)

    @r.post("/api/wallet/payments/{pid}/to-phone", dependencies=[Depends(require_key)])
    def w_to_phone(pid: str, tenant: str = Depends(current_tenant)):
        """The console's button: the approval goes to her phone as a notification."""
        ensure_table()
        with session() as s:
            p = s.get(WalletPayment, pid)
            if p is None or p.tenant_id != tenant:
                raise HTTPException(404, "Not found.")
            a = _acct(s, tenant)
            v = view_payment(p, a.region if a else "IN")
        if v["status"] != "waiting":
            raise HTTPException(409, f"This payment is already {v['status']}.")
        from . import convs
        _announce(v["conversation_id"] or convs.current_or_new(tenant), {**v, "to_phone": True})   # the push goes with the event
        return {"ok": True}

    @r.post("/api/wallet/bills", dependencies=[Depends(require_key)])
    def w_bill_add(body: BillIn, tenant: str = Depends(current_tenant)):
        try:
            return add_bill(tenant, body.name, body.kind, body.site, body.account, body.due, body.amount)
        except WalletError as e:
            raise _e(e)

    @r.delete("/api/wallet/bills/{bid}", dependencies=[Depends(require_key)])
    def w_bill_del(bid: str, tenant: str = Depends(current_tenant)):
        return {"ok": delete_bill(tenant, bid)}

    @r.post("/api/wallet/bills/{bid}/pay", dependencies=[Depends(require_key)])
    def w_bill_pay(bid: str, tenant: str = Depends(current_tenant)):
        from . import convs
        try:
            return pay_bill(tenant, convs.current_or_new(tenant), bid)
        except WalletError as e:
            raise _e(e)

    @r.post("/api/wallet/add-money", dependencies=[Depends(require_key)])
    def w_add(tenant: str = Depends(current_tenant)):
        if not partner():
            raise HTTPException(409, "Adding money needs a licensed payment partner in your country, and none is connected yet. "
                                     "For now Hoola pays each time with your own UPI or card, after your approval.")
        raise HTTPException(501, "The partner's top-up is not connected yet.")

    app.include_router(r)
