"""v0.452 DUKAAN PLUS (web Step 4B = the rest of W4 + W5, docs/WEB_PLATFORM_PLAN.md) for her website shop.

1. GST tax invoice + credit note for WEBSITE orders on HER ONE series (Rule 46): an invoiced website order gets a hidden row
   on the site's app project (coll `_web_orders`), so `appmaker/gst.py` gives the number (the same INV/<FY>/0001 series as
   her app), `appmaker/receipt.py` draws the PDF, and the CA exports (registers, GSTR-1, Tally) see website sales too.
   A cancelled invoiced order gets its credit note (CN series) once.
2. Marketplace: sellers apply (public form) -> HER approval sets their commission + their gateway account (Razorpay Route
   linked account id; never a bank number) -> a private seller page (their products wait for her OK, their orders, what
   they earn) -> on a paid online order each approved seller's share (lines minus commission) goes as a gateway transfer,
   once. Cashfree / PhonePe transfers are not built (said on the card).
3. Courier: Shiprocket (her API user, sealed): her tap ships a confirmed order -> Shiprocket order + AWB + label; tracking
   read from Shiprocket; the order moves to shipped with the AWB on the customer's tracking page.
4. Cart reminders, opted-in only: a customer may tick "remind me" at checkout; a cart not ordered in 2 h shows on her list
   with a WhatsApp link SHE taps (nothing is sent by Hoola); the customer's own STOP link ends it; a later order closes it."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import urllib.parse
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import shop as SH

log = logging.getLogger("santosh.site")
WEB_COLL = "_web_orders"
CART_AFTER_H = 2
STATS = {"invoices": 0, "credit_notes": 0, "vendors": 0, "transfers": 0, "shipped": 0, "carts": 0}
_TRANSPORT: list[Any] = [None]                     # tests: httpx.MockTransport for Shiprocket


class SiteShopVendor(Base):
    __tablename__ = "site_shop_vendors"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ven"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    gstin: Mapped[str] = mapped_column(String(15), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")      # pending | approved | blocked
    commission: Mapped[int] = mapped_column(Integer, default=10)            # percent kept by her
    account: Mapped[str] = mapped_column(String(60), default="")            # gateway linked account id (her dashboard)
    token: Mapped[str] = mapped_column(String(40), index=True, default="")
    created_at = mapped_column(DateTime(timezone=True), default=now)


class SiteShopCart(Base):
    __tablename__ = "site_shop_carts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("crt"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    phone: Mapped[str] = mapped_column(String(15), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(10), default="open")         # open | ordered | reminded | stopped
    token: Mapped[str] = mapped_column(String(40), default="")
    consent_at = mapped_column(DateTime(timezone=True), default=now)
    updated_at = mapped_column(DateTime(timezone=True), default=now)


_OK = False


_LOCK = __import__("threading").Lock()


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    with _LOCK:                                    # v0.551 one thread sets up, the rest wait (a checkout calls it)
        if not _OK:
            _ensure_tables()


def _ensure_tables() -> None:
    global _OK
    from .. import db as _db
    SH.ensure_tables()
    if _db._engine is not None:
        SiteShopVendor.__table__.create(_db._engine, checkfirst=True)
        SiteShopCart.__table__.create(_db._engine, checkfirst=True)
        try:
            _db.add_missing_columns_for(_db._engine, SiteShopVendor.__table__, SiteShopCart.__table__,   # v0.551 own tables only
                                        SH.SiteShopProduct.__table__, SH.SiteShopOrder.__table__)
        except Exception:                          # noqa: BLE001
            log.exception("shop plus columns")
        _OK = True


def _site_id(tenant: str, ref: str) -> str:
    from . import service as S
    with session() as s:
        return S._find(s, tenant, ref).id


def _order(s, site_id: str, number: str) -> SH.SiteShopOrder:
    o = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id, SH.SiteShopOrder.number == number)).first()
    if o is None:
        raise SH.ShopError("Yeh order nahi mila.", 404)
    return o


def _project(site_id: str):
    from . import shoppay as SP
    return SP.project_of(site_id)


# ================================================================ 1. GST invoice / credit note on her one series
_FIELDS = [{"key": "name", "label": "Name", "type": "text"}, {"key": "address", "label": "Address", "type": "long_text"},
           {"key": "gstin", "label": "Buyer GSTIN", "type": "text"}, {"key": "items", "label": "Items", "type": "long_text", "admin_only": True},
           {"key": "total", "label": "Total", "type": "number", "admin_only": True}]
WEB_C = {"key": WEB_COLL, "label": "Website order", "fields": _FIELDS, "rules": {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"}}


def _shadow(p, o: SH.SiteShopOrder, gstin: str = "") -> str:
    """The order's hidden row on the app project (made once; the invoice / credit note numbers live on it)."""
    from ..appmaker import backend as BE
    from . import webapp as W
    with session() as s:
        x = s.get(SH.SiteShopOrder, o.id)
        if getattr(x, "inv_row", None):
            return x.inv_row
        items = json.loads(x.items or "[]")
        lines = "\n".join(f"{int(i['qty'])} x {i['title']} @ Rs {i['price'] / 100:.2f}" for i in items)
        d = {"name": x.name, "address": f"{x.address} {x.pincode}".strip(), "gstin": gstin, "items": lines,
             "total": round(x.total / 100, 2), "_delivery": round(x.delivery / 100, 2), "paid": "Verified" if x.utr else "",
             "utr": x.utr or "", "_web_order": x.number}
        if x.discount:
            d.update({"_discount": round(x.discount / 100, 2), "_coupon": x.coupon or "", "_subtotal": round(x.subtotal / 100, 2)})
        row = W.SiteAppRow(site_id=BE.bid(p), coll=WEB_COLL, owner="", data=json.dumps(d, ensure_ascii=False))
        s.add(row)
        s.flush()
        x.inv_row = row.id
        return row.id


def invoice_pdf(site_id: str, number: str, doc: str = "", gstin: str = "") -> tuple[bytes, str]:
    """Her (or the buyer's, by the private link) tax invoice / credit note PDF. Needs her GSTIN on the site's app."""
    from ..appmaker import gst as G
    from ..appmaker import receipt as RC
    from . import webapp as W
    ensure_tables()
    p = _project(site_id)
    if p is None or not G.on(p):
        raise SH.ShopError("GST bill ke liye pehle apna GSTIN daaliye (Shop tab > GST).", 409)
    with session() as s:
        o = _order(s, site_id, number)
        if o.status in ("new", "payment_told") and not o.utr:
            raise SH.ShopError("Invoice payment / pakka hone ke baad banta hai.", 409)
        s.expunge(o)
    rid = _shadow(p, o, gstin)
    with session() as s:
        row = s.get(W.SiteAppRow, rid)
        s.expunge(row)
    d = json.loads(row.data or "{}")
    if not d.get("_inv_no"):
        G.number_for(p, rid)
        STATS["invoices"] += 1
        with session() as s:
            row = s.get(W.SiteAppRow, rid)
            s.expunge(row)
        d = json.loads(row.data or "{}")
    if doc == "credit" and not d.get("_cn_no"):
        raise SH.ShopError("Is order ka credit note nahi bana (order radd nahi hua).", 404)
    out = RC.pdf(p, WEB_C, row, d, "" if doc == "credit" else "invoice")
    no = d.get("_cn_no") if doc == "credit" else d.get("_inv_no")
    return out, str(no or "invoice").replace("/", "-")


def credit_on_cancel(site_id: str, number: str, reason: str = "Order cancelled") -> str:
    """Called when an order is cancelled: an INVOICED order gets its credit note once (none if never invoiced)."""
    from ..appmaker import gst as G
    with session() as s:
        o = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id, SH.SiteShopOrder.number == number)).first()
        rid = getattr(o, "inv_row", None) if o is not None else None
    p = _project(site_id)
    if not rid or p is None:
        return ""
    got = G.credit_for(p, rid, reason)
    if got:
        STATS["credit_notes"] += 1
        return got[0]
    return ""


# ================================================================ 2. marketplace
def apply_vendor(site_id: str, body: dict[str, Any], ip: str = "") -> dict[str, Any]:
    ensure_tables()
    SH._rate(f"vendor:{hashlib.sha256((ip + site_id).encode()).hexdigest()[:20]}", 3, 86400)
    name = SH._tidy(body.get("name"), 120)
    phone = re.sub(r"\D", "", str(body.get("phone") or ""))[-10:]
    if not name or len(phone) != 10 or phone[0] not in "6789":
        raise SH.ShopError("Naam aur 10 ankon ka mobile chahiye.")
    gstin = str(body.get("gstin") or "").strip().upper()
    if gstin:
        from ..appmaker import gst as G
        if not G.valid_gstin(gstin):
            raise SH.ShopError("GSTIN sahi nahi lagta.")
    with session() as s:
        if s.scalars(select(SiteShopVendor).where(SiteShopVendor.site_id == site_id, SiteShopVendor.phone == phone)).first():
            raise SH.ShopError("Is number se pehle hi arzi aa chuki hai.", 409)
        s.add(SiteShopVendor(site_id=site_id, name=name, phone=phone, email=SH._tidy(body.get("email"), 160), gstin=gstin,
                             about=SH._tidy(body.get("about"), 600)))
    STATS["vendors"] += 1
    return {"ok": True, "say": "Arzi mil gayi. Dukaan ki maalkin dekhkar jawab dengi."}


def _vview(v: SiteShopVendor, with_token: bool = False) -> dict[str, Any]:
    out = {"id": v.id, "name": v.name, "phone": v.phone, "email": v.email, "gstin": v.gstin, "about": v.about, "status": v.status,
           "commission": v.commission, "account": v.account, "since": v.created_at.isoformat() if v.created_at else ""}
    if with_token:
        out["portal"] = v.token
    return out


def vendors(tenant: str, ref: str) -> dict[str, Any]:
    site_id = _site_id(tenant, ref)
    ensure_tables()
    with session() as s:
        vs = [_vview(v, True) for v in s.scalars(select(SiteShopVendor).where(SiteShopVendor.site_id == site_id)
                                                .order_by(SiteShopVendor.created_at.desc())).all()]
        pend = [{"slug": p.slug, "title": p.title, "price": SH.rupees(p.price), "vendor": p.vendor}
                for p in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id,
                                                                    SH.SiteShopProduct.mod == "pending")).all()]
    return {"vendors": vs, "pending_products": pend}


def set_vendor(tenant: str, ref: str, vid: str, body: dict[str, Any]) -> dict[str, Any]:
    """HER tap: approve / block, commission %, the seller's gateway linked account (Razorpay Route `acc_...`)."""
    site_id = _site_id(tenant, ref)
    with session() as s:
        v = s.get(SiteShopVendor, vid)
        if v is None or v.site_id != site_id:
            raise SH.ShopError("Seller nahi mila.", 404)
        if "commission" in body:
            try:
                c = int(body["commission"])
            except (TypeError, ValueError):
                raise SH.ShopError("Commission 0-90 %.")
            if not 0 <= c <= 90:
                raise SH.ShopError("Commission 0-90 %.")
            v.commission = c
        if "account" in body:
            acc = str(body.get("account") or "").strip()
            if acc and not re.fullmatch(r"acc_[A-Za-z0-9]{6,40}", acc):
                raise SH.ShopError("Razorpay Route ka linked account id (acc_...) daaliye; bank number kabhi nahi.")
            v.account = acc
        st = str(body.get("status") or "")
        if st in ("approved", "blocked", "pending"):
            v.status = st
            if st == "approved" and not v.token:
                v.token = secrets.token_urlsafe(24)
            if st == "blocked":                      # a blocked seller's products leave the shop at once
                for p in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id,
                                                                    SH.SiteShopProduct.vendor == v.id)).all():
                    p.active = 0
        return _vview(v, True)


def approve_product(tenant: str, ref: str, slug: str, ok: bool = True) -> dict[str, Any]:
    """Catalogue moderation: a seller's product goes on sale only after HER OK."""
    site_id = _site_id(tenant, ref)
    with session() as s:
        p = s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id, SH.SiteShopProduct.slug == slug)).first()
        if p is None:
            raise SH.ShopError("Product nahi mila.", 404)
        p.mod = "ok" if ok else "rejected"
        p.active = 1 if ok else 0
    return {"ok": True, "slug": slug, "on_sale": ok}


def _vendor_by_token(s, site_id: str, token: str) -> SiteShopVendor:
    v = s.scalars(select(SiteShopVendor).where(SiteShopVendor.site_id == site_id, SiteShopVendor.token == token)).first() if token else None
    if v is None or v.status != "approved":
        raise SH.ShopError("Yeh seller link nahi chalta.", 404)
    return v


def vendor_portal(site_id: str, token: str) -> dict[str, Any]:
    """The seller's own page: their products (with moderation state), their order lines, what they earn after commission."""
    ensure_tables()
    with session() as s:
        v = _vendor_by_token(s, site_id, token)
        prods = s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id, SH.SiteShopProduct.vendor == v.id)).all()
        mine = {p.slug for p in prods}
        lines, gross = [], 0
        for o in s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id).order_by(SH.SiteShopOrder.created_at.desc())
                           .limit(500)).all():
            for x in json.loads(o.items or "[]"):
                if x["slug"] in mine:
                    lines.append({"order": o.number, "status": SH.WORDS.get(o.status, o.status), "title": x["title"], "qty": x["qty"],
                                  "amount": SH.rupees(x["amount"]), "pincode": o.pincode})   # never the buyer's phone / address
                    if o.status not in ("new", "cancelled", "payment_told"):
                        gross += int(x["amount"])
        return {"vendor": {"name": v.name, "commission": v.commission, "payouts": bool(v.account)},
                "products": [{"slug": p.slug, "title": p.title, "price": SH.rupees(p.price), "unit": p.unit, "stock": p.stock,
                              "state": p.mod or "ok", "on_sale": bool(p.active)} for p in prods],
                "orders": lines, "sales": SH.rupees(gross), "earn": SH.rupees(gross - gross * v.commission // 100)}


def vendor_add_product(site_id: str, token: str, body: dict[str, Any]) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        v = _vendor_by_token(s, site_id, token)
        vid = v.id
    title = SH._tidy(body.get("title"), 120)
    if not title:
        raise SH.ShopError("Product ka naam chahiye.")
    slug = SH._slug(title)
    with session() as s:
        if s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == site_id, SH.SiteShopProduct.slug == slug)).first():
            raise SH.ShopError("Is naam ka product pehle se hai.", 409)
        price = SH.paise(body.get("price"))
        if price <= 0:
            raise SH.ShopError("Daam sahi nahi.")
        stock = body.get("stock")
        s.add(SH.SiteShopProduct(site_id=site_id, slug=slug, title=title, price=price, unit=SH._tidy(body.get("unit"), 30),
                                 stock=int(stock) if str(stock or "").isdigit() else None, active=0, vendor=vid, mod="pending"))
    return {"ok": True, "slug": slug, "say": "Product bhej diya; maalkin ke OK ke baad dukaan mein dikhega."}


def vendor_transfers(p, pid: str, payment_id: str, order_id: str) -> int:
    """On a PAID website order: each approved seller with a linked account gets (their lines - commission), once."""
    from ..appmaker import pay as PY
    from ..appmaker.pay import AppPayment
    from ..paygate import gw as GW
    k = PY._keys(p)
    if not k or k[0] != "razorpay":
        return 0                                     # Route transfers are Razorpay's; others not built
    with session() as s:
        o = s.get(SH.SiteShopOrder, order_id)
        if o is None:
            return 0
        items = json.loads(o.items or "[]")
        slugs = [x["slug"] for x in items]
        prods = {pr.slug: pr.vendor for pr in s.scalars(select(SH.SiteShopProduct).where(SH.SiteShopProduct.site_id == o.site_id,
                                                                                         SH.SiteShopProduct.slug.in_(slugs))).all()}
        vs = {v.id: v for v in s.scalars(select(SiteShopVendor).where(SiteShopVendor.site_id == o.site_id,
                                                                      SiteShopVendor.status == "approved")).all()}
        share: dict[str, int] = {}
        for x in items:
            vid = prods.get(x["slug"])
            v = vs.get(vid or "")
            if v is not None and v.account:
                share[v.account] = share.get(v.account, 0) + int(x["amount"]) * (100 - v.commission) // 100
        parts = [{"account": a, "amount": amt, "note": f"order {o.number}"} for a, amt in share.items() if amt >= 100]
    if not parts:
        return 0
    with session() as s:
        x = s.get(AppPayment, pid)
        m = json.loads(x.meta or "{}")
        if m.get("transfers"):
            return 0                                 # never twice
        m["transfers"] = "sending"
        x.meta = json.dumps(m)
    try:
        ids = GW.client(k[0], k[1], k[2]).transfer(payment_id, parts)
        res: Any = ids
        STATS["transfers"] += len(ids)
    except GW.GwError as e:
        res = f"failed: {e}"
        PY._note(p, f"Seller payout nahi gaya (order {order_id}): {e}. Razorpay dashboard > Route mein dekhiye.")
    with session() as s:
        x = s.get(AppPayment, pid)
        m = json.loads(x.meta or "{}")
        m["transfers"] = res
        x.meta = json.dumps(m)
    return len(parts)


# ================================================================ 3. courier: Shiprocket (her API user)
SR = "https://apiv2.shiprocket.in/v1/external"


def _sr_cfg(site_id: str) -> dict[str, Any]:
    p = _project(site_id)
    if p is None:
        return {}
    from ..appmaker import backend as BE
    return dict((BE._j(p.backend, {}) or {}).get("courier") or {})


def set_courier(tenant: str, ref: str, body: dict[str, Any]) -> dict[str, Any]:
    """Her Shiprocket API user (email + password typed in the console), pickup nickname, default parcel. Sealed; checked
    with one real login first - a wrong one is never saved."""
    from ..appmaker import backend as BE
    from ..bazar.security import vault
    from . import applink as AL
    AL.link(tenant, ref)
    site_id = _site_id(tenant, ref)
    p = _project(site_id)
    email, pw = str(body.get("email") or "").strip(), str(body.get("password") or "")
    pickup = SH._tidy(body.get("pickup"), 60) or "Primary"
    if not email or not pw:
        raise SH.ShopError("Shiprocket API user ka email aur password chahiye (Settings > API > Add new API user).")
    _sr_login(email, pw)
    weight = max(0.05, min(30.0, float(body.get("weight") or 0.5)))
    box = {k: max(1, min(150, int(body.get(k) or d))) for k, d in (("length", 20), ("breadth", 15), ("height", 10))}
    cfg = {"provider": "shiprocket", "sealed": vault().seal(json.dumps({"email": email, "password": pw})), "pickup": pickup,
           "weight": weight, **box, "added": now().isoformat()}

    def go(be):
        be["courier"] = cfg
    BE.patch_backend(p, fn=go)
    return courier_view(site_id)


def courier_view(site_id: str) -> dict[str, Any]:
    c = _sr_cfg(site_id)
    return {"on": bool(c.get("sealed")), "provider": c.get("provider", ""), "pickup": c.get("pickup", ""),
            "weight": c.get("weight"), "box": [c.get("length"), c.get("breadth"), c.get("height")] if c else []}


def _http() -> httpx.Client:
    return httpx.Client(timeout=25, transport=_TRANSPORT[0]) if _TRANSPORT[0] else httpx.Client(timeout=25)


def _sr_login(email: str, pw: str) -> str:
    try:
        with _http() as h:
            r = h.post(f"{SR}/auth/login", json={"email": email, "password": pw})
        tok = (r.json() or {}).get("token") if r.status_code == 200 else ""
    except (httpx.HTTPError, ValueError):
        tok = ""
    if not tok:
        raise SH.ShopError("Shiprocket ne login nahi maana (API user ka email / password dekhiye).", 400)
    return tok


def _sr_token(site_id: str) -> str:
    from ..bazar.security import vault
    c = _sr_cfg(site_id)
    if not c.get("sealed"):
        raise SH.ShopError("Pehle Shiprocket jodiye (Shop tab > Courier).", 409)
    k = json.loads(vault().open(c["sealed"]))
    return _sr_login(k["email"], k["password"])


def ship(tenant: str, ref: str, number: str) -> dict[str, Any]:
    """HER tap on a confirmed order: Shiprocket order -> AWB -> label; the order moves to shipped with its AWB."""
    site_id = _site_id(tenant, ref)
    c = _sr_cfg(site_id)
    tok = _sr_token(site_id)
    with session() as s:
        o = _order(s, site_id, number)
        if o.status not in ("confirmed", "packed"):
            raise SH.ShopError("Sirf pakka / pack hua order bhej sakte hain.", 409)
        if (json.loads(o.history or "[]") and any(h.get("awb") for h in json.loads(o.history or "[]"))):
            raise SH.ShopError("Yeh order pehle hi courier ko diya ja chuka hai.", 409)
        items = json.loads(o.items or "[]")
        body = {"order_id": o.number, "order_date": (o.created_at or now()).strftime("%Y-%m-%d %H:%M"), "pickup_location": c["pickup"],
                "billing_customer_name": o.name, "billing_last_name": "", "billing_address": o.address[:190], "billing_city": "",
                "billing_pincode": o.pincode, "billing_state": "", "billing_country": "India", "billing_email": "",
                "billing_phone": o.phone, "shipping_is_billing": True,
                "order_items": [{"name": x["title"][:100], "sku": x["slug"][:40], "units": int(x["qty"]), "selling_price": round(x["price"] / 100, 2)}
                                for x in items],
                "payment_method": "COD" if o.method == "cod" else "Prepaid", "sub_total": round(o.total / 100, 2),
                "length": c["length"], "breadth": c["breadth"], "height": c["height"], "weight": c["weight"]}
    hdr = {"Authorization": f"Bearer {tok}"}
    try:
        with _http() as h:
            r1 = h.post(f"{SR}/orders/create/adhoc", json=body, headers=hdr)
            d1 = r1.json() if r1.status_code == 200 else {}
            sid_ = d1.get("shipment_id")
            if not sid_:
                raise SH.ShopError(f"Shiprocket ne order nahi liya: {str(d1.get('message') or r1.text)[:160]}", 502)
            r2 = h.post(f"{SR}/courier/assign/awb", json={"shipment_id": sid_}, headers=hdr)
            d2 = (r2.json() or {}).get("response", {}).get("data", {}) if r2.status_code == 200 else {}
            awb = str(d2.get("awb_code") or "")
            if not awb:
                raise SH.ShopError("AWB nahi mila (Shiprocket wallet / pincode service dekhiye).", 502)
            r3 = h.post(f"{SR}/courier/generate/label", json={"shipment_id": [sid_]}, headers=hdr)
            label = str((r3.json() or {}).get("label_url") or "") if r3.status_code == 200 else ""
    except httpx.HTTPError as e:
        raise SH.ShopError(f"Shiprocket tak nahi pahunche: {type(e).__name__}", 502)
    with session() as s:
        o = _order(s, site_id, number)
        o.status, o.updated_at = "shipped", now()
        o.history = json.dumps(json.loads(o.history or "[]") + [{"at": SH._iso(), "to": "shipped", "by": "shiprocket", "awb": awb,
                                                                  "courier": str(d2.get("courier_name") or ""), "shipment": sid_}])
    STATS["shipped"] += 1
    return {"awb": awb, "courier": d2.get("courier_name", ""), "label": label, "shipment": sid_, "status": "shipped"}


def track(site_id: str, number: str, token: str) -> dict[str, Any]:
    """The customer's tracking (private link): Shiprocket's own status for the AWB, never cached guesses."""
    with session() as s:
        o = SH._mine(s, site_id, number, token)
        awb = next((h.get("awb") for h in json.loads(o.history or "[]") if h.get("awb")), "")
    if not awb:
        return {"awb": "", "status": ""}
    try:
        tok = _sr_token(site_id)
        with _http() as h:
            r = h.get(f"{SR}/courier/track/awb/{urllib.parse.quote(awb)}", headers={"Authorization": f"Bearer {tok}"})
        td = ((r.json() or {}).get("tracking_data") or {}) if r.status_code == 200 else {}
        acts = td.get("shipment_track_activities") or []
        return {"awb": awb, "status": str((td.get("shipment_track") or [{}])[0].get("current_status") or ""),
                "events": [{"at": a.get("date", ""), "what": a.get("activity", ""), "where": a.get("location", "")} for a in acts[:20]]}
    except SH.ShopError:
        return {"awb": awb, "status": ""}
    except (httpx.HTTPError, ValueError):
        return {"awb": awb, "status": ""}


# ================================================================ 4. cart reminders (opted-in, SHE sends)
def hold_cart(site_id: str, body: dict[str, Any], ip: str = "") -> dict[str, Any]:
    """The customer ticked "remind me": only then is the cart kept (phone + items), with a STOP link."""
    ensure_tables()
    if body.get("consent") is not True:
        raise SH.ShopError("Yaad dilane ke liye haan (tick) zaroori hai.")
    SH._rate(f"cart:{hashlib.sha256((ip + site_id).encode()).hexdigest()[:20]}", 10, 3600)
    phone = re.sub(r"\D", "", str(body.get("phone") or ""))[-10:]
    if len(phone) != 10 or phone[0] not in "6789":
        raise SH.ShopError("10 ankon ka mobile chahiye.")
    items = [{"slug": SH._slug(x.get("slug")), "qty": int(x.get("qty") or 1)} for x in (body.get("items") or [])[:SH.MAX_LINES]
             if isinstance(x, dict) and SH._slug(x.get("slug"))]
    if not items:
        raise SH.ShopError("Cart khaali hai.")
    with session() as s:
        c = s.scalars(select(SiteShopCart).where(SiteShopCart.site_id == site_id, SiteShopCart.phone == phone)).first()
        if c is not None and c.status == "stopped":
            raise SH.ShopError("Aapne yaad dilana band kiya tha.", 409)
        if c is None:
            c = SiteShopCart(site_id=site_id, phone=phone, token=secrets.token_urlsafe(16))
            s.add(c)
        c.name, c.items, c.status, c.consent_at, c.updated_at = SH._tidy(body.get("name"), 120), json.dumps(items), "open", now(), now()
        tok = c.token
    STATS["carts"] += 1
    return {"ok": True, "stop": tok}


def stop_cart(site_id: str, token: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(select(SiteShopCart).where(SiteShopCart.site_id == site_id, SiteShopCart.token == token)).first()
        if c is None:
            raise SH.ShopError("Link nahi chala.", 404)
        c.status, c.items = "stopped", "[]"
    return {"ok": True, "say": "Theek hai, ab yaad nahi dilayenge."}


def ordered(site_id: str, phone: str) -> None:
    """A real order from this number closes its cart (no reminder for something already bought)."""
    ensure_tables()
    with session() as s:
        for c in s.scalars(select(SiteShopCart).where(SiteShopCart.site_id == site_id, SiteShopCart.phone == phone,
                                                      SiteShopCart.status.in_(("open", "reminded")))).all():
            c.status, c.items = "ordered", "[]"


def carts(tenant: str, ref: str) -> dict[str, Any]:
    """Her list: opted-in carts older than CART_AFTER_H hours, each with a WhatsApp link SHE taps (Hoola sends nothing)."""
    from . import service as S
    site_id = _site_id(tenant, ref)
    ensure_tables()
    r = S._load(site_id)
    shop_name = (S._j(r.facts, {}) or {}).get("name") or r.name or "Shop"
    titles = {p["slug"]: p["title"] for p in SH.products(site_id)}
    cut = now() - timedelta(hours=CART_AFTER_H)
    with session() as s:
        rows = s.scalars(select(SiteShopCart).where(SiteShopCart.site_id == site_id, SiteShopCart.status == "open",
                                                    SiteShopCart.updated_at < cut).order_by(SiteShopCart.updated_at.desc()).limit(100)).all()
        out = []
        for c in rows:
            what = ", ".join(titles.get(x["slug"], x["slug"]) for x in json.loads(c.items or "[]"))[:200]
            msg = f"Namaste {c.name or ''}! {shop_name} se: aapke cart mein {what} rakha hai. Order karna ho to website par poora kar lijiye. Na chahiye to STOP likhiye."
            out.append({"id": c.id, "name": c.name, "phone": c.phone[:2] + "******" + c.phone[-2:], "items": what,
                        "wa": "https://wa.me/91" + c.phone + "?text=" + urllib.parse.quote(msg)})
    return {"carts": out, "note": "Sirf unke cart jinhone 'yaad dilana' tick kiya. Link aap dabati hain; Hoola khud kuch nahi bhejta."}


def mark_reminded(tenant: str, ref: str, cid: str) -> dict[str, Any]:
    site_id = _site_id(tenant, ref)
    with session() as s:
        c = s.get(SiteShopCart, cid)
        if c is None or c.site_id != site_id:
            raise SH.ShopError("Cart nahi mila.", 404)
        c.status, c.updated_at = "reminded", now()
    return {"ok": True}


# the seller page: an apply form, or (with ?k=<private link>) the seller's own dashboard. Every value set as TEXT.
SELLER_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sell with us</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:20px;color:#1d1d1f}
h1{font-size:24px}h2{font-size:18px;margin-top:24px}label{display:block;margin:8px 0}input,textarea{width:100%;padding:10px;border:1px solid #bbb;
border-radius:8px;font:inherit;box-sizing:border-box}button{padding:12px 18px;border:0;border-radius:10px;background:#4f46e5;color:#fff;font:inherit}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left}.m{color:#555}
.ok{color:#0a7d3c}.bad{color:#b42318}</style></head><body><main id="app"><h1>Sell with us</h1></main>
<script>
var API='__API__',k=new URLSearchParams(location.search).get('k'),app=document.getElementById('app');
function el(t,txt){var e=document.createElement(t);if(txt!=null)e.textContent=txt;return e}
function req(m,p,b){return fetch(API+p,{method:m,headers:b?{'Content-Type':'application/json'}:{},body:b?JSON.stringify(b):undefined})
 .then(function(r){return r.json().then(function(j){if(!r.ok||j.ok===false)throw new Error(j.error||'Error');return j})})}
function form(fields,label,send){var f=el('form');fields.forEach(function(x){var l=el('label',x[1]);var i=el(x[2]==='area'?'textarea':'input');
 i.name=x[0];if(x[2]&&x[2]!=='area')i.type=x[2];if(x[3])i.required=true;l.appendChild(i);f.appendChild(l)});
 var b=el('button',label);f.appendChild(b);var m=el('p');m.setAttribute('role','status');f.appendChild(m);
 f.onsubmit=function(e){e.preventDefault();var d={};new FormData(f).forEach(function(v,n){d[n]=v});b.disabled=true;
  send(d).then(function(j){m.className='ok';m.textContent=j.say||'Done';f.reset()}).catch(function(er){m.className='bad';m.textContent=er.message}).then(function(){b.disabled=false})};
 return f}
if(!k){app.appendChild(el('p','Apply to sell your products in this shop. The owner reviews every seller and every product first.'));
 app.appendChild(form([['name','Your / business name','text',1],['phone','Mobile (10 digits)','tel',1],['email','Email','email'],
  ['gstin','GSTIN (optional)','text'],['about','What do you sell?','area']],'Apply',function(d){return req('POST','/vendor/apply',d)}))}
else{req('GET','/vendor/'+encodeURIComponent(k)).then(function(j){
 app.appendChild(el('p',j.vendor.name+' - commission '+j.vendor.commission+'% - payouts '+(j.vendor.payouts?'on (through the gateway)':'not set up yet')));
 app.appendChild(el('p','Sales: '+j.sales+' - you earn: '+j.earn));
 app.appendChild(el('h2','Your products'));var t=el('table');j.products.forEach(function(p){var r=el('tr');
  [p.title,p.price,p.unit||'',p.state==='pending'?'waiting for the owner':(p.on_sale?'on sale':'off')].forEach(function(v){r.appendChild(el('td',v))});t.appendChild(r)});
 app.appendChild(t);app.appendChild(el('h2','Add a product'));
 app.appendChild(form([['title','Name','text',1],['price','Price (Rs)','number',1],['unit','Unit (1 kg, box of 12)','text'],['stock','Stock','number']],
  'Send for approval',function(d){return req('POST','/vendor/'+encodeURIComponent(k)+'/product',d)}));
 app.appendChild(el('h2','Your orders'));var o=el('table');j.orders.forEach(function(x){var r=el('tr');
  [x.order,x.title+' x '+x.qty,x.amount,x.status,x.pincode].forEach(function(v){r.appendChild(el('td',v))});o.appendChild(r)});app.appendChild(o);
}).catch(function(er){app.appendChild(el('p',er.message))})}
</script></body></html>"""
