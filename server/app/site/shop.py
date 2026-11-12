"""v0.351 DUKAAN (web design Phase 7 step 1, owner: "START PHASE 3" - all features, first a real online shop).

A shop on any Hoola website: products with prices and stock, a cart, checkout, UPI payment to HER own UPI ID, orders she
manages, and a private tracking link for each customer.

Money rules (CLAUDE.md): money moves only by a person's own tap. The customer pays in THEIR UPI app (Hoola only shows her
UPI ID, the amount and the order number); "I have paid" + the UTR makes the order "payment told" and SHE confirms receipt
- Hoola never marks an order paid by itself. Cash on delivery only when she switched it on.

Trust rules: every price, total and stock figure comes from the server; a cart only says which product and how many. Stock
is checked and reduced inside one database transaction, so two buyers cannot both take the last piece; a cancelled order
puts its stock back. Public calls are rate limited per IP and per site. A customer sees only their own order, with the
secret token in their link.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import logging

from sqlalchemy import DateTime, Integer, String, Text, func, select, update
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

STATUSES = ("new", "payment_told", "confirmed", "packed", "shipped", "delivered", "cancelled")
NEXT = {"new": ("confirmed", "cancelled"), "payment_told": ("confirmed", "cancelled"), "confirmed": ("packed", "shipped", "cancelled"),
        "packed": ("shipped", "cancelled"), "shipped": ("delivered",), "delivered": (), "cancelled": ()}
WORDS = {"new": "New order", "payment_told": "Payment reported (check it)", "confirmed": "Confirmed", "packed": "Packed",
         "shipped": "Shipped", "delivered": "Delivered", "cancelled": "Cancelled"}
MAX_LINES, MAX_QTY, MAX_PRODUCTS, MAX_TOTAL_PAISE = 30, 99, 500, 5_00_000_00     # 5 lakh rupees an order
PIN = re.compile(r"^[1-9]\d{5}$")
UTR = re.compile(r"^[A-Za-z0-9]{6,22}$")


class ShopError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


class SiteShopProduct(Base):
    __tablename__ = "site_shop_products"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("prd"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    slug: Mapped[str] = mapped_column(String(90), index=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)              # paise
    unit: Mapped[str] = mapped_column(String(30), default="")           # "1 kg", "box of 12"
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)   # None = not counted
    active: Mapped[int] = mapped_column(Integer, default=1)
    photo: Mapped[str] = mapped_column(String(60), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    vendor: Mapped[str | None] = mapped_column(String(40), nullable=True)     # v0.452 a marketplace seller's product
    mod: Mapped[str | None] = mapped_column(String(10), nullable=True)        # v0.452 pending | ok | rejected (her OK)


class SiteShopOrder(Base):
    __tablename__ = "site_shop_orders"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ord"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(20), index=True)
    token: Mapped[str] = mapped_column(String(40), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(15), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    pincode: Mapped[str] = mapped_column(String(6), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[str] = mapped_column(Text, default="[]")
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    delivery: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(8), default="upi")
    status: Mapped[str] = mapped_column(String(16), default="new")
    utr: Mapped[str] = mapped_column(String(24), default="")
    history: Mapped[str] = mapped_column(Text, default="[]")
    ip_hash: Mapped[str] = mapped_column(String(24), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    discount: Mapped[int | None] = mapped_column(Integer, nullable=True)       # v0.446 paise off by her coupon
    coupon: Mapped[str | None] = mapped_column(String(20), nullable=True)      # v0.446 the code used
    pay_id: Mapped[str | None] = mapped_column(String(40), nullable=True)      # v0.446 her gateway payment (app_payment.id)
    inv_row: Mapped[str | None] = mapped_column(String(40), nullable=True)     # v0.452 the hidden app row that holds the GST numbers
    cid: Mapped[str | None] = mapped_column(String(40), nullable=True)         # v0.538 the checkout's own id: a retry = the same order


class SiteShopCounter(Base):
    """v0.542 the shop's next order number, handed out in ONE atomic step (count + 1 made every checkout of a crowd collide)."""
    __tablename__ = "site_shop_counter"
    site_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    n: Mapped[int] = mapped_column(Integer, default=0)


_TABLES_OK = False
_TABLES_LOCK = __import__("threading").Lock()


class _ShopTables:
    """v0.551 only the shop's own tables for the missing-column check (the whole database is ~900 tables)."""
    sorted_tables = (SiteShopProduct.__table__, SiteShopOrder.__table__, SiteShopCounter.__table__)


def ensure_tables() -> None:
    global _TABLES_OK
    if _TABLES_OK:
        return
    with _TABLES_LOCK:                              # v0.551 one thread sets up; the others wait for it, never repeat it
        if _TABLES_OK:
            return
        _ensure_tables()


def _ensure_tables() -> None:
    global _TABLES_OK
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None:
        SiteShopProduct.__table__.create(eng, checkfirst=True)
        SiteShopOrder.__table__.create(eng, checkfirst=True)
        SiteShopCounter.__table__.create(eng, checkfirst=True)
        try:                                            # v0.446 discount / coupon / pay_id on older databases
            _db.add_missing_columns_for(eng, *_ShopTables.sorted_tables)  # v0.551 was every table (~900) - minutes under a rush
        except Exception:                               # noqa: BLE001
            pass
        from sqlalchemy import text as _t               # v0.538 one number and one checkout id per order, enforced by the db
        for sql in ("CREATE UNIQUE INDEX IF NOT EXISTS ux_shop_order_num ON site_shop_orders (site_id, number)",
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_shop_order_cid ON site_shop_orders (site_id, cid)"):
            try:
                with eng.begin() as c:
                    c.execute(_t(sql))
            except Exception:                           # noqa: BLE001 - old duplicate numbers: the retry below still helps
                log.warning("shop index not made: %s", sql[:60])
        _TABLES_OK = True


# ---------------------------------------------------------------- money as text
def paise(v: Any) -> int:
    """'₹1,250.50' / 1250.5 / '1250' -> 125050 paise. Raises on nonsense or a negative amount."""
    s = re.sub(r"[₹,\s]|rs\.?|inr", "", str(v if v is not None else "").lower())
    m = re.fullmatch(r"(\d{1,7})(?:\.(\d{1,2}))?", s)
    if not m:
        raise ShopError(f"The price was not understood: {str(v)[:20]}")
    return int(m.group(1)) * 100 + int((m.group(2) or "0").ljust(2, "0"))


def rupees(p: int) -> str:
    r, ps = divmod(int(p), 100)
    s = f"{r:,}"
    if r >= 1000:                                   # Indian grouping: 1,25,000
        head, tail = str(r)[:-3], str(r)[-3:]
        s = (re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head) + "," + tail) if head else tail
    return f"₹{s}" + (f".{ps:02d}" if ps else "")


def _slug(s: Any, n: int = 90) -> str:
    return re.sub(r"[^a-z0-9/]+", "-", str(s or "").lower()).strip("-/")[:n]


def _tidy(s: Any, n: int) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()[:n]


# ---------------------------------------------------------------- her products and settings
def settings_of(facts: dict[str, Any]) -> dict[str, Any]:
    s = facts.get("shop") if isinstance(facts.get("shop"), dict) else {}
    return {"on": bool(s.get("on")), "cod": bool(s.get("cod")), "pickup": bool(s.get("pickup")),
            "delivery": int(s.get("delivery") or 0), "free_above": int(s.get("free_above") or 0),
            "min_order": int(s.get("min_order") or 0), "pincodes": [p for p in s.get("pincodes") or [] if PIN.match(str(p))][:500]}


def clean_settings(raw: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    out = dict(old)
    for k in ("on", "cod", "pickup"):
        if k in raw:
            out[k] = bool(raw[k])
    for k in ("delivery", "free_above", "min_order"):
        if k in raw and raw[k] not in (None, ""):
            out[k] = paise(raw[k])
    if "pincodes" in raw:
        pins = raw["pincodes"] if isinstance(raw["pincodes"], list) else re.split(r"[,\s]+", str(raw["pincodes"] or ""))
        out["pincodes"] = sorted({str(p).strip() for p in pins if PIN.match(str(p).strip())})[:500]
    return out


def upsert_products(site_id: str, items: list[dict[str, Any]]) -> dict[str, int]:
    """Add or change products by title / slug: {title, price, stock?, unit?, active?, photo?}. Returns counts."""
    ensure_tables()
    added = changed = 0
    with session() as s:
        have = {p.slug: p for p in s.scalars(select(SiteShopProduct).where(SiteShopProduct.site_id == site_id)).all()}
        for it in items[:max_products()]:
            if not isinstance(it, dict):
                continue
            title = _tidy(it.get("title"), 120)
            slug = _slug(it.get("slug") or title)
            if not slug:
                continue
            p = have.get(slug)
            if p is None:
                if not title or it.get("price") in (None, ""):
                    continue
                if len(have) >= max_products():
                    raise ShopError(f"A shop can have up to {max_products()} products.")
                p = SiteShopProduct(site_id=site_id, slug=slug, title=title, price=paise(it["price"]))
                s.add(p)
                have[slug] = p
                added += 1
            else:
                changed += 1
                if title:
                    p.title = title
                if it.get("price") not in (None, ""):
                    p.price = paise(it["price"])
            if "stock" in it:
                st = it["stock"]
                p.stock = None if st in (None, "", "unlimited") else max(0, int(st))
            if it.get("unit") is not None:
                p.unit = _tidy(it.get("unit"), 30)
            if "active" in it:
                p.active = 1 if it["active"] else 0
            if it.get("photo") is not None:
                p.photo = _tidy(it.get("photo"), 60)
            p.updated_at = now()
    return {"added": added, "changed": changed}


PRICE_FIELD = re.compile(r"price|rate|mrp|cost|daam|keemat|fees?", re.I)


def from_collections(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """v0.315 list items that carry a price become products (slug = the item's page address)."""
    out = []
    for c in plan.get("collections") or []:
        pf = next((f["key"] for f in c.get("fields", []) if PRICE_FIELD.search(f["key"]) or PRICE_FIELD.search(f.get("label", ""))), "")
        if not pf:
            continue
        for it in c.get("items", []):
            v = (it.get("data") or {}).get(pf, "")
            m = re.search(r"\d[\d,]*(?:\.\d{1,2})?", str(v))
            if m:
                unit = re.sub(r"^[\s/]+", "", str(v)[m.end():]).strip()[:30]
                out.append({"slug": f"{c['key']}/{it['slug']}", "title": it["title"], "price": m.group(0), "unit": unit})
    return out


def products(site_id: str, active_only: bool = True) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(SiteShopProduct).where(SiteShopProduct.site_id == site_id)
        if active_only:
            q = q.where(SiteShopProduct.active == 1)
        rows = s.scalars(q.order_by(SiteShopProduct.title)).all()
        return [{"slug": p.slug, "title": p.title, "price": p.price, "price_text": rupees(p.price), "unit": p.unit,
                 "stock": p.stock, "in_stock": p.stock is None or p.stock > 0, "active": bool(p.active), "photo": p.photo}
                for p in rows]


# ---------------------------------------------------------------- the public side: an order from her website
_RATE: dict[str, list[float]] = {}


def _rate(key: str, n: int, per: int) -> None:
    from .webapp import AppError, rate
    try:
        rate("shop:" + key, n, per)
    except AppError as e:
        raise ShopError(str(e), 429)


def _number(s, site_id: str, attempt: int = 0) -> str:
    """Fallback only (the unique index fired after the counter's number): count + 1 + attempt inside the open checkout."""
    n = s.scalar(select(func.count()).select_from(SiteShopOrder).where(SiteShopOrder.site_id == site_id)) or 0
    return f"O-{1001 + n + attempt}"


def next_number(site_id: str) -> str:
    """The next order number from the shop's counter, in its OWN short transaction, taken BEFORE the checkout writes
    anything (on SQLite a second writer inside an open write would wait on itself). Committed at once, so no other
    checkout waits on this one and two never get the same number; a number a refused checkout took is simply not used
    - an order number is not a tax invoice number (those have their own gap-free series). The unique index
    (site_id, number) stays as the last guard."""
    ensure_tables()
    from sqlalchemy.exc import IntegrityError
    for _ in range(5):
        try:
            with session() as c:
                got = c.execute(update(SiteShopCounter).where(SiteShopCounter.site_id == site_id)
                                .values(n=SiteShopCounter.n + 1).returning(SiteShopCounter.n)).scalar()
                if got is None:                       # the shop's first order since v0.542: start after what it already has
                    have = c.scalar(select(func.count()).select_from(SiteShopOrder).where(SiteShopOrder.site_id == site_id)) or 0
                    c.add(SiteShopCounter(site_id=site_id, n=have + 1))
                    c.flush()
                    got = have + 1
            return f"O-{1000 + got}"
        except IntegrityError:                         # two first orders created the counter at once: read it again
            continue
    return ""


def _st():
    from ..config import get_settings
    return get_settings()


def max_products() -> int:
    return max(MAX_PRODUCTS, int(getattr(_st(), "site_shop_max_products", 20000) or MAX_PRODUCTS))


class _SameCheckout(Exception):
    pass


def _again(site_id: str, cid: str, cfg: dict[str, Any]) -> dict[str, Any] | None:
    """v0.538 the same checkout sent twice (a slow network, a double tap): the first order, never a second one."""
    if not cid:
        return None
    with session() as s:
        o = s.scalar(select(SiteShopOrder).where(SiteShopOrder.site_id == site_id, SiteShopOrder.cid == cid))
        if o is None:
            return None
        out = {**public_view(o), "again": True}
        total, method = o.total, o.method
    if method == "upi" and cfg.get("upi"):
        from . import live as LV
        link = LV.upi_link(cfg["upi"], cfg.get("shop_name") or "Shop", f"{total / 100:.2f}", f"Order {out['number']}")
        out["pay"] = {"vpa": cfg["upi"], "link": link, "qr": LV.qr_data_uri(link), "amount": rupees(total)}
    return out


log = logging.getLogger("santosh.site.shop")


def place(site_id: str, tenant_id: str, cfg: dict[str, Any], body: dict[str, Any], ip: str = "") -> dict[str, Any]:
    try:
        return _place(site_id, tenant_id, cfg, body, ip)
    except _SameCheckout:                                 # v0.538 a twin of this checkout landed first: that one order
        got = _again(site_id, re.sub(r"[^A-Za-z0-9_-]", "", str(body.get("cid") or ""))[:40], cfg)
        if got is None:
            raise ShopError("The order could not be placed right now; tap once more.", 503)
        return got


def _place(site_id: str, tenant_id: str, cfg: dict[str, Any], body: dict[str, Any], ip: str = "") -> dict[str, Any]:
    """A visitor's checkout. Everything money-related is computed HERE from her products; returns the order and how to pay."""
    ensure_tables()
    if not cfg.get("on"):
        raise ShopError("Online orders are turned off on this website right now.", 403)
    if str(body.get("website") or "").strip():                         # honeypot
        raise ShopError("The order could not be placed.")
    iph = hashlib.sha256(f"{ip}|{site_id}".encode()).hexdigest()[:24]
    cid = re.sub(r"[^A-Za-z0-9_-]", "", str(body.get("cid") or ""))[:40]
    seen = _again(site_id, cid, cfg)
    if seen is not None:
        return seen
    _rate(f"order:{iph}", int(getattr(_st(), "site_shop_ip_cap", 12) or 12), 600)
    _rate(f"order-site:{site_id}", int(getattr(_st(), "site_shop_day_cap", 300) or 300), 86400)
    name = _tidy(body.get("name"), 120)
    phone = re.sub(r"\D", "", str(body.get("phone") or ""))[-10:]
    method = str(body.get("method") or "upi")
    pickup = bool(body.get("pickup")) and cfg.get("pickup")
    address = _tidy(body.get("address"), 600)
    pin = str(body.get("pincode") or "").strip()
    if not name or len(phone) != 10 or phone[0] not in "6789":
        raise ShopError("A name and a valid 10-digit mobile number are needed.")
    if not pickup:
        if len(address) < 10 or not PIN.match(pin):
            raise ShopError("The full address and a 6-digit pincode are needed.")
        if cfg.get("pincodes") and pin not in cfg["pincodes"]:
            raise ShopError("There is no delivery to this pincode right now.")
    if method not in ("upi", "cod", "online") or (method == "cod" and not cfg.get("cod")) or \
            (method == "online" and not cfg.get("online")):
        raise ShopError("Pick a payment method.")
    if method == "upi" and not cfg.get("upi"):
        raise ShopError("The shop's UPI ID is not set yet; pick Cash on delivery or call the shop.")
    want: dict[str, int] = {}
    for line in (body.get("items") if isinstance(body.get("items"), list) else [])[:MAX_LINES]:
        if not isinstance(line, dict):
            continue
        sg, q = _slug(line.get("slug")), line.get("qty")
        try:
            q = int(q)
        except (TypeError, ValueError):
            continue
        if sg and 0 < q <= MAX_QTY:
            want[sg] = min(MAX_QTY, want.get(sg, 0) + q)
    if not want:
        raise ShopError("The cart is empty.")
    first_number = next_number(site_id)            # v0.542 before this checkout writes anything (one atomic step)
    with session() as s:
        prods = {p.slug: p for p in s.scalars(select(SiteShopProduct).where(
            SiteShopProduct.site_id == site_id, SiteShopProduct.slug.in_(list(want)), SiteShopProduct.active == 1)).all()}
        lines, sub = [], 0
        for sg, q in want.items():
            p = prods.get(sg)
            if p is None:
                raise ShopError("One item in the cart is no longer in the shop; look at the cart again.", 409)
            if p.stock is not None and p.stock < q:
                raise ShopError(f"{p.title}: only {p.stock} left.", 409)
            lines.append({"slug": sg, "title": p.title, "unit": p.unit, "qty": q, "price": p.price, "amount": p.price * q})
            sub += p.price * q
        if cfg.get("min_order") and sub < cfg["min_order"]:
            raise ShopError(f"The minimum order is {rupees(cfg['min_order'])}.")
        off, code, cnote = 0, "", ""
        if str(body.get("coupon") or "").strip():          # v0.446 her code, applied by the server (never trusted from the page)
            from . import shoppay as SP
            off, code, cnote = SP.coupon_apply(site_id, str(body.get("coupon")), sub, phone)
        goods = sub - off
        delivery = 0 if pickup or (cfg.get("free_above") and goods >= cfg["free_above"]) else int(cfg.get("delivery") or 0)
        total = goods + delivery
        if total > MAX_TOTAL_PAISE:
            raise ShopError("An order this large cannot be placed online; call the shop.")
        for sg, q in want.items():     # one conditional UPDATE each: two buyers can never both take the last piece
            if prods[sg].stock is None:
                continue
            res = s.execute(update(SiteShopProduct).where(SiteShopProduct.id == prods[sg].id, SiteShopProduct.stock >= q)
                            .values(stock=SiteShopProduct.stock - q).execution_options(synchronize_session=False))
            if res.rowcount != 1:
                if code:
                    from . import shoppay as SP
                    SP.give_back(site_id, code, phone)
                raise ShopError(f"{prods[sg].title}: just sold out; look at the cart again.", 409)
        o = SiteShopOrder(site_id=site_id, tenant_id=tenant_id, number="", token=secrets.token_urlsafe(16), cid=cid or None,
                          name=name, phone=phone, address="Pickup from the shop" if pickup else address,
                          pincode="" if pickup else pin, note=_tidy(body.get("note"), 400), items=json.dumps(lines, ensure_ascii=False),
                          subtotal=sub, delivery=delivery, total=total, method=method, ip_hash=iph,
                          discount=off or None, coupon=code or None,
                          history=json.dumps([{"at": _iso(), "to": "new"}] + ([{"at": _iso(), "note": cnote}] if cnote else [])))
        from sqlalchemy.exc import IntegrityError
        for attempt in range(60):                     # v0.538 two checkouts at once never share an order number
            o.number = first_number if attempt == 0 and first_number else _number(s, site_id, attempt)
            try:
                with s.begin_nested():
                    s.add(o)
                    s.flush()
                break
            except IntegrityError:
                if cid and s.scalar(select(func.count()).select_from(SiteShopOrder).where(
                        SiteShopOrder.site_id == site_id, SiteShopOrder.cid == cid)):
                    if code:
                        from . import shoppay as SP
                        SP.give_back(site_id, code, phone)
                    raise _SameCheckout()               # the other copy won: this one's stock goes back (rollback)
        else:
            raise ShopError("The order could not be placed right now; tap once more.", 503)
        out = public_view(o)
        start_view = {"id": o.id, "number": o.number, "name": name, "phone": phone, "total_paise": total}
    if cnote:
        out["coupon_note"] = cnote
    try:                                                  # v0.452 a real order closes this number's reminder cart
        from . import shopplus as SPL
        SPL.ordered(site_id, phone)
    except Exception:                                     # noqa: BLE001
        pass
    if method == "online":                                # v0.446 her own gateway; PAID only from its verified answer
        from . import shoppay as SP
        try:
            out["online"] = SP.start(site_id, start_view)
        except ShopError as e:
            out["online"] = {"error": str(e)}
    if method == "upi":
        from . import live as LV
        link = LV.upi_link(cfg["upi"], cfg.get("shop_name") or "Shop", f"{total / 100:.2f}", f"Order {out['number']}")
        out["pay"] = {"vpa": cfg["upi"], "link": link, "qr": LV.qr_data_uri(link), "amount": rupees(total)}
    return out


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_view(o: SiteShopOrder) -> dict[str, Any]:
    """What the customer sees of THEIR order (never other orders, never her notes)."""
    return {"number": o.number, "token": o.token, "status": o.status, "status_text": WORDS.get(o.status, o.status),
            "items": [{k: x[k] for k in ("slug", "title", "unit", "qty")} | {"amount": rupees(x["amount"])} for x in json.loads(o.items or "[]")],
            "subtotal": rupees(o.subtotal), "delivery": rupees(o.delivery), "total": rupees(o.total), "method": o.method,
            "utr_told": bool(o.utr) and o.method != "online", "discount": rupees(o.discount or 0) if o.discount else "",
            "coupon": o.coupon or "", "paid_online": o.method == "online" and o.status not in ("new", "cancelled")}


def _mine(s, site_id: str, number: str, token: str) -> SiteShopOrder:
    o = s.scalars(select(SiteShopOrder).where(SiteShopOrder.site_id == site_id, SiteShopOrder.number == number)).first()
    if o is None or not token or not secrets.compare_digest(o.token, str(token)):
        raise ShopError("Order not found.", 404)
    return o


def track(site_id: str, number: str, token: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        return public_view(_mine(s, site_id, number, token))


def tell_paid(site_id: str, number: str, token: str, utr: str, ip: str = "") -> dict[str, Any]:
    """The customer says they paid by UPI (with the UTR). She still confirms receipt herself."""
    ensure_tables()
    _rate(f"paid:{ip}", 10, 600)
    utr = re.sub(r"\s", "", str(utr or ""))
    if not UTR.match(utr):
        raise ShopError("The UTR / UPI reference number is not right (it is in the payment details of your UPI app).")
    with session() as s:
        o = _mine(s, site_id, number, token)
        if o.method != "upi" or o.status not in ("new", "payment_told"):
            raise ShopError("This cannot be done on this order.", 409)
        o.utr, o.status, o.updated_at = utr, "payment_told", now()
        o.history = json.dumps(json.loads(o.history or "[]") + [{"at": _iso(), "to": "payment_told", "utr": utr}])
        return public_view(o)


# ---------------------------------------------------------------- her side
def owner_view(o: SiteShopOrder) -> dict[str, Any]:
    return {**public_view(o), "id": o.id, "pay_id": getattr(o, "pay_id", None) or "", "name": o.name, "phone": o.phone,
            "address": o.address, "pincode": o.pincode,
            "note": o.note, "utr": o.utr, "next": list(NEXT.get(o.status, ())), "created": o.created_at.isoformat() if o.created_at else "",
            "history": json.loads(o.history or "[]")}


def orders(site_id: str, status: str = "", limit: int = 200) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(SiteShopOrder).where(SiteShopOrder.site_id == site_id)
        if status:
            q = q.where(SiteShopOrder.status == status)
        return [owner_view(o) for o in s.scalars(q.order_by(SiteShopOrder.created_at.desc()).limit(limit)).all()]


def set_status(site_id: str, number: str, to: str) -> dict[str, Any]:
    """HER move of an order (confirm / packed / shipped / delivered / cancel). A cancel returns its stock."""
    ensure_tables()
    with session() as s:
        o = s.scalars(select(SiteShopOrder).where(SiteShopOrder.site_id == site_id, SiteShopOrder.number == number)).first()
        if o is None:
            raise ShopError("This order was not found.", 404)
        if to not in NEXT.get(o.status, ()):
            raise ShopError(f"'{WORDS.get(o.status)}' cannot go to '{WORDS.get(to, to)}'.", 409)
        if to == "cancelled":
            for x in json.loads(o.items or "[]"):
                p = s.scalars(select(SiteShopProduct).where(SiteShopProduct.site_id == site_id, SiteShopProduct.slug == x["slug"])).first()
                if p is not None and p.stock is not None:
                    s.execute(update(SiteShopProduct).where(SiteShopProduct.id == p.id)
                              .values(stock=SiteShopProduct.stock + int(x["qty"])).execution_options(synchronize_session=False))
        o.status, o.updated_at = to, now()
        o.history = json.dumps(json.loads(o.history or "[]") + [{"at": _iso(), "to": to}])
        view, code, phone = owner_view(o), (getattr(o, "coupon", None) or ""), o.phone
    if to == "cancelled" and code:                     # v0.446 the coupon use goes back with a cancel
        from . import shoppay as SP
        SP.give_back(site_id, code, phone)
    if to == "cancelled":                              # v0.452 an INVOICED order gets its GST credit note, once
        from . import shopplus as SPL
        cn = SPL.credit_on_cancel(site_id, number)
        if cn:
            view["credit_note"] = cn
    return view


def summary(site_id: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(SiteShopOrder).where(SiteShopOrder.site_id == site_id)).all()
        day = datetime.now(timezone.utc) - timedelta(days=1)
        live = [o for o in rows if o.status not in ("cancelled",)]
        return {"orders": len(rows), "open": sum(1 for o in rows if o.status in ("new", "payment_told", "confirmed", "packed")),
                "to_check": sum(1 for o in rows if o.status == "payment_told"),
                "today": sum(1 for o in rows if o.created_at and o.created_at.replace(tzinfo=o.created_at.tzinfo or timezone.utc) >= day),
                "sales": rupees(sum(o.total for o in live if o.status in ("confirmed", "packed", "shipped", "delivered")))}
