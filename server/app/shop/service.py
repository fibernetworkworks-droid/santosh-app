"""Order karo: one place that turns "Blinkit se 2 litre doodh aur bread mangwa do" into a finished order up to the
payment, which she makes herself.

Route per site:
  1. the company's official MCP (Swiggy food / Instamart, Zomato, Zepto) when she has linked it in Bazar: the agent
     uses those tools; placing the order is a confirm card and the UPI payment is hers.
  2. otherwise the Computer Operator in its own real Chrome with her saved logins: search, compare, choose, cart,
     address, slot, coupon, then STOP at payment; she presses pay in the live view (or approves the UPI request in her
     own app). The job is learned as a recipe, so the next order on that site is quick.
Every order is kept (`ShopOrder`) with its status, so "mera order kahan hai" has an answer.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import sites as S

log = logging.getLogger("santosh.shop")


class ShopError(Exception):
    pass


class ShopOrder(Base):
    __tablename__ = "shop_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("so"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    site: Mapped[str] = mapped_column(String(40), default="")
    route: Mapped[str] = mapped_column(String(16), default="operator")   # operator | mcp
    what: Mapped[str] = mapped_column(Text, default="")                  # her words / the items
    status: Mapped[str] = mapped_column(String(24), default="working")   # working | waiting_payment | placed | failed | cancelled
    task_id: Mapped[str] = mapped_column(String(40), default="")         # Computer Operator job
    summary: Mapped[str] = mapped_column(Text, default="")
    order_ref: Mapped[str] = mapped_column(String(80), default="")
    total: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


RULES = """
ORDER RULES (Hoola's own, on top of the operator rules):
- Goal: the order is READY TO PAY with exactly what she asked: right items, sizes / variants, quantities, her saved
  delivery address, the delivery slot / date she wants. Then ask_owner(kind='payment', ref=<the pay / place-order
  button>, reason='<site>: <items x qty> = Rs <total incl. delivery / fees>, delivery <date / slot>, address <short>').
  She presses it herself; then read the confirmation and finish with the order id, total and delivery date as proof.
- Choosing: follow her words first (brand, size, budget, veg / non-veg, rating). Otherwise pick the best value: rating
  4+ with many reviews, a known seller / Assured / fulfilled, in stock, earliest delivery, within budget. Never pick a
  sponsored result just because it is first. If nothing fits her budget or wish, ask_owner(kind='choice') with the
  best 2-3 options and prices instead of guessing.
- Quantities and cart: empty anything old in the cart that she did not ask for only after ask_owner(kind='approve');
  check the cart total before going to payment.
- No paid extras she did not ask for (insurance, protection plans, tips, donations, subscriptions, priority delivery).
  Apply a visible coupon / bank-free offer that needs nothing from her.
- Login: if the site wants a login, use her mobile / email from her messages; the OTP comes from her phone
  (ask_owner kind='otp'). Her logins stay saved for next time.
- Address: choose her saved address that matches what she said ("ghar", "office"); if there is none or it's unclear,
  ask_owner(kind='question'). Never invent an address.
- Cash on delivery / UPI / card: she chooses on the payment page. Never type card numbers, UPI PIN or CVV.
- If the site refuses the server or keeps failing: finish with what you found (product, price, link) so she can
  order on her phone in one tap.
"""


def _view(o: ShopOrder) -> dict[str, Any]:
    s = S.SITES.get(o.site, {})
    return {"id": o.id, "site": o.site, "site_name": s.get("name", o.site), "route": o.route, "what": o.what[:300],
            "status": o.status, "task_id": o.task_id, "summary": o.summary[:600], "order_ref": o.order_ref,
            "total": o.total, "created_at": o.created_at.isoformat(), "updated_at": o.updated_at.isoformat()}


def _mcp_ready(tenant: str, pack: str) -> bool:
    if not pack:
        return False
    try:
        from ..agent import mcp_live
        return any(x.get("pack_id") == pack and x.get("status") == "ready" and x.get("tools")
                   for x in mcp_live.snapshot(tenant))
    except Exception:
        return False


def plan(tenant: str, what: str, site: str = "", compare: list[str] | None = None) -> dict[str, Any]:
    """Which site and which route."""
    site = (site or "").strip().lower() or S.find(what)
    if site and site not in S.SITES:
        site = S.find(site) or ""
    kind = S.SITES[site]["kind"] if site else S.guess_kind(what)
    chosen = site or S.KIND_DEFAULT.get(kind, ["amazon"])[0]
    others = [c for c in (compare or []) if c in S.SITES and c != chosen][:2]
    pack = S.SITES[chosen].get("mcp", "")
    return {"site": chosen, "kind": kind, "named": bool(site), "compare": others,
            "route": "mcp" if _mcp_ready(tenant, pack) else "operator", "mcp_pack": pack}


def _job_text(what: str, p: dict[str, Any], budget: str, when: str, address: str, notes: str) -> tuple[str, str]:
    """(task shown on her card and used for recipes, guidance for the operator)."""
    s = S.SITES[p["site"]]
    lines = [f"Order on {s['name']}: {what}"]
    if budget:
        lines.append(f"Budget: {budget}")
    if when:
        lines.append(f"Delivery / slot / date wanted: {when}")
    if address:
        lines.append(f"Deliver to her saved address: {address}")
    if notes:
        lines.append(f"Her other wishes: {notes}")
    if p["compare"]:
        names = ", ".join(f"{S.SITES[c]['name']} ({S.search_url(c, S.query_of(what, p['site']))})" for c in p["compare"])
        lines.append(f"FIRST compare the same item(s) on {names}: open each search page, note price + delivery for the "
                     f"best match; then order where the total is lowest for the same thing (say which and why).")
    task = "\n".join(lines)
    guide = f"How on {s['name']} ({s['web']}): {s['play']}\n" + RULES.strip()
    return task, guide


def order(tenant: str, what: str, conversation_id: str = "", site: str = "", budget: str = "", when: str = "",
          address: str = "", notes: str = "", compare: list[str] | None = None, created_by: str = "owner") -> dict[str, Any]:
    what = re.sub(r"\s+", " ", what or "").strip()
    if len(what) < 3:
        raise ShopError("Kya mangwana / book karna hai? Item, quantity aur site (agar pata ho) bataiye.")
    p = plan(tenant, what, site, compare)
    s = S.SITES[p["site"]]
    if p["route"] == "mcp":
        with session() as db:
            o = ShopOrder(tenant_id=tenant, site=p["site"], route="mcp", what=what[:1000])
            db.add(o)
            db.flush()
            v = _view(o)
        return {**v, "next": (
            f"Use {s['name']}'s official tools (Bazar pack {p['mcp_pack']}, the mcp_ tools of that server): find the "
            "address first, search, add to the cart with the right quantity, check the cart and payment options, then "
            "the place-order tool (it becomes a confirm card for her). For UPI it returns a pending payment: open its "
            "UPI link on her phone with open_on_phone (she pays in her UPI app), check the payment status, then "
            "confirm the order and tell her the order id and ETA. Never pick a payment method or pay for her."),
            "plan": p}
    from ..operator import service as ops
    job, guide = _job_text(what, p, budget, when, address, notes)
    try:
        t = ops.start(tenant, job, S.search_url(p["site"], S.query_of(what, p["site"])), [], conversation_id, created_by=created_by,
                      guide=guide)
    except ops.OperatorJobError as e:
        raise ShopError(str(e)) from None
    with session() as db:
        o = ShopOrder(tenant_id=tenant, site=p["site"], route="operator", what=what[:1000], task_id=t["id"])
        db.add(o)
        db.flush()
        v = _view(o)
    return {**v, "plan": p, "say": (f"{s['name']} par order taiyaar kar raha hoon: item chun ke cart, address aur slot tak "
                                    "le jaunga. Payment ke waqt aapko card aayega, pay aap khud karengi.")}


_REF = re.compile(r"\b(?:order|booking|pnr)\s*(?:id|no\.?|number|#)?\s*[:#-]?\s*([A-Z0-9-]*\d[A-Z0-9-]{4,30})", re.I)
_TOTAL = re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*\d(?:\.\d{1,2})?|\d)", re.I)


def _sync(o: ShopOrder) -> None:
    """Bring an operator-run order up to date from its job (lazy, on read)."""
    if o.route != "operator" or not o.task_id or o.status in ("placed", "cancelled"):
        return
    from ..operator import service as ops
    try:
        t = ops.get(o.tenant_id, o.task_id)
    except Exception:
        return
    pend = t.get("pending") or {}
    text = " ".join([t.get("summary") or ""] + [str(x) for x in (t.get("proof") or [])])
    if pend and (pend.get("kind") == "payment" or "payment" in str(pend.get("reason", "")).lower()):
        o.status = "waiting_payment"
        o.summary = str(pend.get("reason") or "")[:600]
    elif t.get("status") == "done":
        m = _REF.search(text)
        o.status = "placed" if m or re.search(r"order (?:placed|confirmed)|booked|booking confirmed", text, re.I) else "failed"
        o.order_ref = (m.group(1) if m else o.order_ref)[:80]
        o.summary = (t.get("summary") or "")[:600]
    elif t.get("status") in ("failed", "stopped"):
        o.status, o.summary = "failed", (t.get("summary") or t.get("error") or "")[:600]
    elif t.get("status") == "cancelled":
        o.status = "cancelled"
    mt = _TOTAL.search(text + " " + str(pend.get("reason", "")))
    if mt and not o.total:
        o.total = "₹" + mt.group(1)


def orders(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    with session() as db:
        rows = db.scalars(select(ShopOrder).where(ShopOrder.tenant_id == tenant)
                          .order_by(ShopOrder.created_at.desc()).limit(limit)).all()
        for r in rows:
            _sync(r)
        return [_view(r) for r in rows]


def mark(tenant: str, oid: str, status: str = "", order_ref: str = "", total: str = "", summary: str = "") -> dict[str, Any]:
    """The agent (MCP route) or the app records what happened."""
    with session() as db:
        o = db.get(ShopOrder, oid)
        if o is None or o.tenant_id != tenant:
            raise ShopError("Yeh order nahi mila.")
        if status in ("working", "waiting_payment", "placed", "failed", "cancelled"):
            o.status = status
        if order_ref:
            o.order_ref = order_ref[:80]
        if total:
            o.total = total[:40]
        if summary:
            o.summary = summary[:600]
        return _view(o)
