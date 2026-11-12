"""v0.446 DUKAAN PAISA (web Step 4 = W4 + the first of W5, docs/WEB_PLATFORM_PLAN.md): her website shop takes ONLINE
payments through HER OWN gateway account, on the same engine her apps use (`appmaker/pay.py`, v0.419 PAISA).

- online checkout: the order is made first (prices, stock, delivery, coupon - all on the server), then a gateway order for
  exactly that total; the customer pays on the gateway's own page. The order is PAID only from the gateway's verified
  webhook or a server-side status read with her keys, and only when the amount matches (a mismatch is never 'paid').
- an online order not paid within ABANDON_H hours is cancelled by itself (its stock and coupon go back); money arriving
  after that is never lost - the order is marked and she is told to refund or confirm.
- refunds only by her tap (the console), on the gateway's own refund API; the order history shows each one.
- coupons: her codes (the same store as her app's coupons), checked and applied by the server, once per customer
  (by mobile number) when the code says so; a cancel gives the use back.
- reviews: only a buyer whose order was DELIVERED can rate what was in it (1-5 + a line), once per product per order,
  by the order's private link; she can hide one (never edit it)."""
from __future__ import annotations

import json
import logging
import re
from datetime import timedelta
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import shop as SH

log = logging.getLogger("santosh.site")
ABANDON_H = 3
STATS = {"started": 0, "paid": 0, "late_paid": 0, "abandoned": 0, "refunds": 0, "reviews": 0, "coupons": 0}


class SiteShopReview(Base):
    __tablename__ = "site_shop_reviews"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rev"))
    site_id: Mapped[str] = mapped_column(String(40), index=True)
    slug: Mapped[str] = mapped_column(String(90), index=True)
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    stars: Mapped[int] = mapped_column(Integer, default=5)
    text: Mapped[str] = mapped_column(Text, default="")
    name: Mapped[str] = mapped_column(String(60), default="")                  # first name only
    status: Mapped[str] = mapped_column(String(10), default="shown")         # shown | hidden
    created_at = mapped_column(DateTime(timezone=True), default=now)


_OK = False


_LOCK = __import__("threading").Lock()


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    with _LOCK:                                    # v0.551 one thread sets up, the rest wait (it runs on every checkout)
        if not _OK:
            _ensure_tables()


def _ensure_tables() -> None:
    global _OK
    from .. import db as _db
    SH.ensure_tables()
    if _db._engine is not None:
        SiteShopReview.__table__.create(_db._engine, checkfirst=True)
        try:                                       # the order table gains discount / coupon / pay columns on old databases
            _db.add_missing_columns_for(_db._engine, SiteShopReview.__table__, SH.SiteShopOrder.__table__,   # v0.551 own tables only
                                        SH.SiteShopProduct.__table__)
        except Exception:                          # noqa: BLE001
            log.exception("shop columns")
        _OK = True


# ---------------------------------------------------------------- her gateway behind the site
def project_of(site_id: str):
    """The site's App Sahayak project (its gateway keys, coupons, GST) - or None."""
    from .models import Site
    from . import applink as AL
    with session() as s:
        r = s.get(Site, site_id)
        if r is None:
            return None
        s.expunge(r)
    return AL.project(r)


def online_on(site_id: str) -> bool:
    from ..appmaker import pay as PY
    p = project_of(site_id)
    try:
        return bool(p is not None and PY.on(p))
    except Exception:                              # noqa: BLE001
        return False


def connect(tenant: str, ref: str) -> dict[str, Any]:
    """Her console's 'Online payments' card: the site gets its project (to hold her sealed keys), then the app's own
    keys / status / refunds / settlements / links routes work on it."""
    from ..appmaker import pay as PY
    from . import applink as AL
    out = AL.link(tenant, ref)
    p = project_of(_site_id(tenant, ref))
    return {"app": out["app"], "number": out["number"], **PY.status(p)}


def _site_id(tenant: str, ref: str) -> str:
    from . import service as S
    with session() as s:
        return S._find(s, tenant, ref).id


def start(site_id: str, order: dict[str, Any]) -> dict[str, Any]:
    """A gateway order for an online website order (the server's total), as a guest payment on her app engine."""
    from ..appmaker import pay as PY
    from ..appmaker.pay import AppPayment
    from ..paygate import gw as GW
    p = project_of(site_id)
    if p is None or not PY.on(p):
        raise SH.ShopError("Online payment is not turned on yet; pick UPI or Cash on delivery.", 409)
    cl, gw = PY._client(p)
    PY.ensure_tables()
    amount = int(order["total_paise"])
    pid = new_id("pay")
    cust = {"id": "guest", "name": order["name"][:100], "email": "", "phone": order["phone"]}
    try:
        made = cl.create_order(amount, pid, cust, {"site": site_id, "order": order["number"]}, PY._return_url(p, pid), None)
    except GW.GwError as e:
        raise SH.ShopError(f"The payment did not start: {e}", 502)
    with session() as s:
        s.add(AppPayment(id=pid, app_id=p.id, kind="site", coll="shop", row_id=order["id"], member="", gateway=gw,
                         gw_order=made["gw_order"], amount=amount, label=f"Website order {order['number']}",
                         meta=json.dumps({"checkout": made["checkout"], "site": site_id})))
        o = s.get(SH.SiteShopOrder, order["id"])
        o.pay_id = pid
    STATS["started"] += 1
    return {"payment": pid, "url": f"{PY._base()}/api/app-api/{PY._app_key(p)}/pay/p/{PY.page_token(pid)}", "amount": SH.rupees(amount)}


def again(site_id: str, number: str, token: str) -> dict[str, Any]:
    """The customer's private order link: pay again for an online order still waiting (same payment within its window)."""
    from ..appmaker import pay as PY
    from ..appmaker.pay import AppPayment
    ensure_tables()
    with session() as s:
        o = SH._mine(s, site_id, number, token)
        if o.method != "online" or o.status != "new":
            raise SH.ShopError("Online payment is no longer open for this order.", 409)
        oid, pid = o.id, o.pay_id or ""
        view = {"id": o.id, "number": o.number, "name": o.name, "phone": o.phone, "total_paise": o.total}
    p = project_of(site_id)
    if pid and p is not None:
        with session() as s:
            x = s.get(AppPayment, pid)
            if x is not None and x.status == "created" and now() - PY._aware(x.created) < timedelta(minutes=PY.PAGE_MIN - 5):
                return {"payment": pid, "url": f"{PY._base()}/api/app-api/{PY._app_key(p)}/pay/p/{PY.page_token(pid)}",
                        "amount": SH.rupees(x.amount)}
    return start(site_id, view)


def on_paid(order_id: str, payment_id: str, amount: int, gw: str, label: str) -> tuple[str, str]:
    """Called by pay._paid ONLY (verified webhook / status read, amount already matched). -> (site_id, what happened)."""
    ensure_tables()
    with session() as s:
        o = s.get(SH.SiteShopOrder, order_id)
        if o is None:
            return "", "missing"
        hist = json.loads(o.history or "[]")
        o.utr = (payment_id or "")[:24]
        if o.status == "new":
            o.status = "confirmed"
            hist.append({"at": SH._iso(), "to": "confirmed", "by": f"{gw} (payment verified)", "amount": SH.rupees(amount)})
            what = "confirmed"
            STATS["paid"] += 1
        else:                                       # it was cancelled meanwhile (abandoned) - the money is not lost
            hist.append({"at": SH._iso(), "note": f"Payment {SH.rupees(amount)} arrived when the order was '{o.status}' - a refund or "
                                                  "confirming it again is your decision.", "by": gw})
            what = "late"
            STATS["late_paid"] += 1
        o.history, o.updated_at = json.dumps(hist), now()
        return o.site_id, what


def release_unpaid(hours: int = ABANDON_H) -> int:
    """Worker: an online order with no payment after `hours` is cancelled; its stock + coupon go back (never a paid one)."""
    ensure_tables()
    cut = now() - timedelta(hours=hours)
    with session() as s:
        rows = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.method == "online", SH.SiteShopOrder.status == "new",
                                                        SH.SiteShopOrder.created_at < cut).limit(200)).all()
        todo = [(o.site_id, o.number) for o in rows]
    n = 0
    for site_id, number in todo:
        try:
            cancel(site_id, number, "payment did not arrive")
            n += 1
        except Exception:                           # noqa: BLE001
            log.exception("release unpaid %s", number)
    STATS["abandoned"] += n
    return n


def cancel(site_id: str, number: str, why: str) -> dict[str, Any]:
    out = SH.set_status(site_id, number, "cancelled")
    with session() as s:
        o = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id, SH.SiteShopOrder.number == number)).first()
        hist = json.loads(o.history or "[]")
        if hist:
            hist[-1]["why"] = why
        o.history = json.dumps(hist)
    return out                                      # set_status already gave the coupon use back


# ---------------------------------------------------------------- refunds (her tap)
def refund(tenant: str, ref: str, number: str, amount_rs: Any = None, why: str = "") -> dict[str, Any]:
    from ..appmaker import pay as PY
    site_id = _site_id(tenant, ref)
    ensure_tables()
    with session() as s:
        o = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id, SH.SiteShopOrder.number == number)).first()
        if o is None:
            raise SH.ShopError("This order was not found.", 404)
        pid = o.pay_id or ""
    p = project_of(site_id)
    if not pid or p is None:
        raise SH.ShopError("This order has no online payment (you refund UPI / COD yourself).", 409)
    out = PY.refund(p, pid, amount_rs, why or f"Order {number}", her_tap=True)
    with session() as s:
        o = s.scalars(select(SH.SiteShopOrder).where(SH.SiteShopOrder.site_id == site_id, SH.SiteShopOrder.number == number)).first()
        o.history = json.dumps(json.loads(o.history or "[]") + [{"at": SH._iso(), "note": f"Refund {out.get('amount') or ''} "
                                                                  f"({out.get('status') or 'bheja'})", "by": "owner"}])
    STATS["refunds"] += 1
    return out


# ---------------------------------------------------------------- coupons on the website (her app's coupon store)
def _guest(phone: str):
    class _G:                                       # coupon rules count a customer by mobile number on the website
        id = "ph:" + phone
        m = None
        owner = False
        staff = False
    return _G()


def coupon_check(site_id: str, code: str, items: Any) -> dict[str, Any]:
    from ..appmaker import coupon as CP
    p = project_of(site_id)
    code = re.sub(r"\s+", "", str(code or "")).upper()
    sub = _subtotal(site_id, items)
    if p is None or not code:
        return {"ok": False, "why": "This code does not work.", "subtotal": SH.rupees(sub), "discount": SH.rupees(0), "total": SH.rupees(sub)}
    c = CP._all(p).get(code) if CP.CODE.match(code) else None
    why = CP._why(c, sub / 100, "")
    if why:
        return {"ok": False, "why": why, "subtotal": SH.rupees(sub), "discount": SH.rupees(0), "total": SH.rupees(sub)}
    d = int(round(CP.discount_of(c, sub / 100) * 100))
    return {"ok": True, "code": code, "subtotal": SH.rupees(sub), "discount": SH.rupees(d), "total": SH.rupees(sub - d)}


def coupon_apply(site_id: str, code: str, subtotal_paise: int, phone: str) -> tuple[int, str, str]:
    """At order time: (discount paise, code used, note when it did not apply). A failing code never loses the order."""
    from ..appmaker import coupon as CP
    code = re.sub(r"\s+", "", str(code or "")).upper()
    p = project_of(site_id)
    if not code or p is None:
        return 0, "", ""
    d, extra = CP.apply(p, code, subtotal_paise / 100, _guest(phone))
    if extra.get("coupon_note"):
        return 0, "", extra["coupon_note"]
    STATS["coupons"] += 1
    return min(subtotal_paise, int(round(d * 100))), code, ""


def give_back(site_id: str, code: str, phone: str) -> None:
    from ..appmaker import coupon as CP
    p = project_of(site_id)
    if p is not None and code:
        try:
            CP.give_back(p, code, "ph:" + phone)
        except Exception:                           # noqa: BLE001
            log.exception("coupon give back")


def _subtotal(site_id: str, items: Any) -> int:
    want: dict[str, int] = {}
    for line in (items if isinstance(items, list) else [])[:SH.MAX_LINES]:
        if isinstance(line, dict):
            try:
                q = int(line.get("qty"))
            except (TypeError, ValueError):
                continue
            if 0 < q <= SH.MAX_QTY:
                want[SH._slug(line.get("slug"))] = q
    prices = {p["slug"]: p["price"] for p in SH.products(site_id)}
    return sum(prices.get(sg, 0) * q for sg, q in want.items())


# ---------------------------------------------------------------- reviews (verified buyers only)
def review(site_id: str, number: str, token: str, slug: str, stars: Any, text: str = "") -> dict[str, Any]:
    ensure_tables()
    try:
        st = int(stars)
    except (TypeError, ValueError):
        st = 0
    if not 1 <= st <= 5:
        raise SH.ShopError("Pick 1 to 5 stars.")
    slug = SH._slug(slug)
    with session() as s:
        o = SH._mine(s, site_id, number, token)
        if o.status != "delivered":
            raise SH.ShopError("A review can be given only after the item is delivered.", 409)
        if slug not in {x["slug"] for x in json.loads(o.items or "[]")}:
            raise SH.ShopError("This item was not in this order.", 400)
        if s.scalars(select(SiteShopReview).where(SiteShopReview.order_id == o.id, SiteShopReview.slug == slug)).first():
            raise SH.ShopError("A review has already been given for this item.", 409)
        first = (o.name or "").split(" ")[0][:40]
        s.add(SiteShopReview(site_id=site_id, slug=slug, order_id=o.id, stars=st, text=SH._tidy(text, 600), name=first))
    STATS["reviews"] += 1
    return {"ok": True, "say": "Thank you. Your review is posted."}


def reviews(site_id: str, slug: str = "") -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        q = select(SiteShopReview).where(SiteShopReview.site_id == site_id, SiteShopReview.status == "shown")
        if slug:
            q = q.where(SiteShopReview.slug == SH._slug(slug))
        rows = s.scalars(q.order_by(SiteShopReview.created_at.desc()).limit(500)).all()
        by: dict[str, list[int]] = {}
        for x in rows:
            by.setdefault(x.slug, []).append(x.stars)
        return {"summary": {k: {"avg": round(sum(v) / len(v), 1), "count": len(v)} for k, v in by.items()},
                "reviews": [{"id": x.id, "slug": x.slug, "stars": x.stars, "text": x.text, "name": x.name, "verified": True,
                             "at": x.created_at.isoformat() if x.created_at else ""} for x in rows[:60]]}


def owner_reviews(tenant: str, ref: str) -> list[dict[str, Any]]:
    site_id = _site_id(tenant, ref)
    ensure_tables()
    with session() as s:
        return [{"id": x.id, "slug": x.slug, "stars": x.stars, "text": x.text, "name": x.name, "status": x.status,
                 "at": x.created_at.isoformat() if x.created_at else ""}
                for x in s.scalars(select(SiteShopReview).where(SiteShopReview.site_id == site_id)
                                   .order_by(SiteShopReview.created_at.desc()).limit(300)).all()]


def hide_review(tenant: str, ref: str, rid: str, hide: bool = True) -> dict[str, Any]:
    """Her moderation: hide / show a review. Never edits a buyer's words."""
    site_id = _site_id(tenant, ref)
    with session() as s:
        x = s.get(SiteShopReview, rid)
        if x is None or x.site_id != site_id:
            raise SH.ShopError("Review not found.", 404)
        x.status = "hidden" if hide else "shown"
    return {"ok": True, "status": "hidden" if hide else "shown"}
