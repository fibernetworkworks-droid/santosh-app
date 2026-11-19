"""v0.999.25 HOOLA CREDITS - orders: start a purchase, settle it ONCE from the provider's word, renewals, refunds."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from ..db import now, session
from . import pay, plans as P, wallet as W

log = logging.getLogger("santosh.credits")


class CreditError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def token(order_id: str) -> str:
    """The pay page's own key for one order (opened in a browser where she is not signed in)."""
    from ..config import get_settings
    st = get_settings()
    key = f"credits:{st.secret_key or st.api_key or 'hoola-credits'}".encode()
    return hmac.new(key, order_id.encode(), hashlib.sha256).hexdigest()[:32]


def token_ok(order_id: str, t: str) -> bool:
    return bool(t) and hmac.compare_digest(token(order_id), t)


def _order_view(o: W.CreditOrder) -> dict[str, Any]:
    kind, item, region = P.parse_sku(o.sku)
    it = P.item_of(kind, item)
    return {"id": o.id, "sku": o.sku, "kind": kind, "item": item, "region": region, "name": it.get("name") or
            f"{it.get('credits', 0):,} credits", "employee": o.employee, "provider": o.provider, "status": o.status,
            "amount": o.amount / 100, "currency": o.currency, "granted": o.granted,
            "created": W._aware(o.created).isoformat() if o.created else None}


def overview(tenant: str, country: str = "") -> dict[str, Any]:
    region = P.region_of(country)
    W.ensure_table()
    with session() as s:
        orders = s.scalars(select(W.CreditOrder).where(W.CreditOrder.tenant_id == tenant)
                           .order_by(W.CreditOrder.created.desc()).limit(20)).all()
        ov = [_order_view(o) for o in orders]
    pool = pay.INDIA if region == "in" else pay.WORLD
    return {"wallet": W.view(tenant), "prices": P.catalogue(region), "packs": W.packs(tenant) if W.enabled() else [],
            "orders": ov, "providers": [p for p in pool if pay.ready(p)], "usd_per_credit": P.USD_PER_CREDIT}


def checkout(tenant: str, sku: str, provider: str = "", employee: str = "", buyer: dict[str, str] | None = None,
             base_url: str = "") -> dict[str, Any]:
    if not W.enabled():
        raise CreditError("Credits are not switched on on this server.", 409)
    try:
        kind, item, region = P.parse_sku(sku)
    except ValueError as e:
        raise CreditError(str(e))
    if kind == "pack":
        from ..employee import hire as H
        if employee not in H.CATALOG:
            raise CreditError("Pick the AI employee this package is for.")
    else:
        employee = ""
    amount, cur = P.price(kind, item, region)
    try:
        prov = pay.choose(region, provider)
    except pay.PayError as e:
        raise CreditError(str(e), e.code)
    W.ensure_table()
    with session() as s:
        o = W.CreditOrder(tenant_id=tenant, provider=prov, sku=sku, employee=employee, amount=P.minor(amount, cur),
                          currency=cur, status="pending")
        s.add(o)
        s.flush()
        oid = o.id
    k = token(oid)
    base = (base_url or "").rstrip("/")
    ret = f"{base}/pay/credits/{oid}?k={k}"
    try:
        got = pay.create(prov, oid, sku, P.minor(amount, cur), cur, {"id": tenant, **(buyer or {})}, ret)
    except pay.PayError as e:
        with session() as s:
            s.execute(update(W.CreditOrder).where(W.CreditOrder.id == oid).values(status="failed"))
        raise CreditError(str(e), e.code)
    with session() as s:
        s.execute(update(W.CreditOrder).where(W.CreditOrder.id == oid).values(
            provider_ref=got.get("provider_ref", ""), checkout=json.dumps(got.get("checkout") or {})))
    return {"order": oid, "provider": prov, "amount": amount, "currency": cur, "pay_url": ret,
            "redirect": got.get("redirect") or "", "checkout": got.get("checkout") or None}


def _find(s, order: str = "", provider_ref: str = "", payment_ref: str = "", sub_ref: str = "") -> W.CreditOrder | None:
    q = None
    if order:
        q = s.get(W.CreditOrder, order)
    if q is None and provider_ref:
        q = s.scalars(select(W.CreditOrder).where(W.CreditOrder.provider_ref == provider_ref)).first()
    if q is None and payment_ref:
        q = s.scalars(select(W.CreditOrder).where(W.CreditOrder.payment_ref == payment_ref)).first()
    if q is None and sub_ref:
        q = s.scalars(select(W.CreditOrder).where(W.CreditOrder.sub_ref == sub_ref)
                      .order_by(W.CreditOrder.created)).first()
    return q


def settle(order_id: str, payment_ref: str = "", sub_ref: str = "") -> bool:
    """The provider said PAID: give what was bought, exactly once (one conditional update claims the order)."""
    W.ensure_table()
    with session() as s:
        res = s.execute(update(W.CreditOrder).where(W.CreditOrder.id == order_id, W.CreditOrder.status == "pending")
                        .values(status="paid", paid_at=datetime.now(timezone.utc), payment_ref=payment_ref,
                                sub_ref=sub_ref))
        if res.rowcount != 1:
            return False
        o = s.get(W.CreditOrder, order_id)
        tenant, sku, employee = o.tenant_id, o.sku, o.employee
    kind, item, region = P.parse_sku(sku)
    c = W.grant(tenant, kind, item, region, order_id, employee=employee)
    with session() as s:
        s.execute(update(W.CreditOrder).where(W.CreditOrder.id == order_id).values(granted=c))
    W._tell(tenant, _paid_line(kind, item, region, c, employee))
    return True


def _paid_line(kind: str, item: str, region: str, c: float, employee: str) -> str:
    if kind == "pack":
        p = P.PACKS[item]
        return f"Payment received: {p['name']} package for this AI employee - {p['jobs']} jobs this month."
    extra = " Every quality tier is open now." if kind in ("plan", "topup") else ""
    return f"Payment received: {c:,.0f} credits added.{extra}"


def renewed(sub_ref: str, payment_ref: str) -> bool:
    """A subscription took its next month's money (Dodo / Paddle): give the month again, once per payment."""
    if not sub_ref or not payment_ref:
        return False
    W.ensure_table()
    with session() as s:
        if s.scalars(select(W.CreditOrder).where(W.CreditOrder.payment_ref == payment_ref)).first() is not None:
            return False
        first = _find(s, sub_ref=sub_ref)
        if first is None:
            return False
        o = W.CreditOrder(tenant_id=first.tenant_id, provider=first.provider, sku=first.sku, employee=first.employee,
                          amount=first.amount, currency=first.currency, status="paid", provider_ref=payment_ref,
                          payment_ref=payment_ref, sub_ref=sub_ref, paid_at=datetime.now(timezone.utc))
        s.add(o)
        s.flush()
        oid, tenant, sku, emp = o.id, o.tenant_id, o.sku, o.employee
    kind, item, region = P.parse_sku(sku)
    c = W.grant(tenant, kind, item, region, oid, employee=emp, renewal=True)
    with session() as s:
        s.execute(update(W.CreditOrder).where(W.CreditOrder.id == oid).values(granted=c))
    return True


def refunded(provider_ref: str = "", payment_ref: str = "", order: str = "") -> bool:
    W.ensure_table()
    with session() as s:
        o = _find(s, order=order, provider_ref=provider_ref, payment_ref=payment_ref)
        if o is None:
            return False
        res = s.execute(update(W.CreditOrder).where(W.CreditOrder.id == o.id, W.CreditOrder.status == "paid")
                        .values(status="refunded"))
        if res.rowcount != 1:
            return False
        tenant, sku, granted, oid, emp = o.tenant_id, o.sku, o.granted, o.id, o.employee
    kind, _item, _region = P.parse_sku(sku)
    if kind == "pack":
        with session() as s:
            r = W._pack_row(s, tenant, emp)
            if r is not None:
                r.until = datetime.now(timezone.utc)
        return True
    W.take_back(tenant, kind, granted or 0.0, oid)
    return True


def webhook(provider: str, headers: dict[str, str], raw: bytes) -> dict[str, Any]:
    if provider not in pay.PROVIDERS:
        raise CreditError("Unknown payment service.", 404)
    evs = pay.verify_and_read(provider, headers, raw)
    if not evs:
        return {"ok": False, "done": 0}
    done = 0
    for e in evs:
        try:
            if e["kind"] == "paid":
                with session() as s:
                    o = _find(s, order=e.get("order", ""), provider_ref=e.get("provider_ref", ""))
                    oid = o.id if o is not None and o.provider == provider else ""
                if oid:
                    done += bool(settle(oid, e.get("payment_ref", ""), e.get("sub_ref", "")))
            elif e["kind"] == "failed":
                with session() as s:
                    o = _find(s, order=e.get("order", ""), provider_ref=e.get("provider_ref", ""))
                    if o is not None and o.status == "pending":
                        o.status = "failed"
                        done += 1
            elif e["kind"] == "renewed":
                done += bool(renewed(e.get("sub_ref", ""), e.get("payment_ref", "")))
            elif e["kind"] == "refund":
                done += bool(refunded(e.get("provider_ref", ""), e.get("payment_ref", ""), e.get("order", "")))
            elif e["kind"] == "cancelled":
                done += 1        # the plan simply is not renewed; what she has stays until its month ends
        except Exception:   # noqa: BLE001
            log.exception("credit webhook event failed")
    return {"ok": True, "done": done}


def check(order_id: str, payment_ref: str = "") -> dict[str, Any]:
    """Her return page asks: read the provider's own record (never the browser's word) and settle if paid."""
    W.ensure_table()
    with session() as s:
        o = s.get(W.CreditOrder, order_id)
        if o is None:
            raise CreditError("No such order.", 404)
        prov, ref, pref, status = o.provider, o.provider_ref, o.payment_ref or payment_ref, o.status
    if status == "pending":
        try:
            st = pay.state(prov, ref, pref)
        except Exception:   # noqa: BLE001 - the provider not answering = still pending, never paid
            log.warning("credit order %s: %s did not answer the status read", order_id, prov)
            st = {"state": "pending"}
        if st.get("state") == "paid":
            settle(order_id, st.get("payment_ref", ""), st.get("sub_ref", ""))
        elif st.get("state") == "failed":
            with session() as s:
                s.execute(update(W.CreditOrder).where(W.CreditOrder.id == order_id, W.CreditOrder.status == "pending")
                          .values(status="failed"))
    with session() as s:
        return _order_view(s.get(W.CreditOrder, order_id))


def order_checkout(order_id: str) -> dict[str, Any]:
    """What the pay page needs to open the provider's checkout again (India: the checkout data)."""
    with session() as s:
        o = s.get(W.CreditOrder, order_id)
        if o is None:
            raise CreditError("No such order.", 404)
        try:
            co = json.loads(o.checkout or "{}")
        except ValueError:
            co = {}
        return {"provider": o.provider, "provider_ref": o.provider_ref, "amount": o.amount, "currency": o.currency,
                "status": o.status, "sku": o.sku, "checkout": co}
