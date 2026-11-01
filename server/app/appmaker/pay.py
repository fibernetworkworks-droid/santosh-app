"""v0.419 PAISA (App Sahayak Pillar E, Phases 52-53): online payments in her native apps through HER own gateway.

  * HER KEYS, HER MONEY: she joins Razorpay / Cashfree / PhonePe PG in the console or her phone (typed in the app, never in
    chat), they are sealed on arrival (vault) and returned by NO route. The money goes from the customer to the gateway to
    HER bank account; Hoola never holds it.
  * PAID ONLY FROM THE GATEWAY: an order is marked paid ("Verified" + `_pay`) only from (a) a webhook whose signature
    verifies with her secret, or (b) a server-to-server status read with her keys (the pay page's check, the reconcile
    tick). The amount must equal what the server priced, else it is held as a MISMATCH for her eyes. The phone's word,
    a redirect or the checkout callback never mark anything paid.
  * CHECKOUT = the gateway's own: a short-lived pay page on her Hoola server (signed link, 30 min) opens Razorpay Checkout /
    Cashfree checkout / PhonePe's hosted page. The app opens it in the browser and hears "paid" over the live stream.
  * REFUNDS only by HER tap: full or part, never more than paid minus refunded, a fixed refund number recorded BEFORE the
    call (a timeout = `ambiguous`, checked with the same number - the gateway's idempotency - so it is never sent twice).
  * PAYMENT LINKS by her tap; SETTLEMENTS read-only; SUBSCRIPTIONS / UPI AutoPay: she makes a plan, the CUSTOMER subscribes
    in the app and authorises the mandate on the gateway's page (explicit consent, the page says the amount, how often,
    how many times, and that she can cancel any time); the customer or she cancels.
  * SPLIT PAYOUTS: only through the gateway's own product (Razorpay Route transfers / Cashfree Easy Split), only to vendor
    accounts she created there, only by a rule SHE approved (any change = approve again); the rest stays with her.
  * Stays out on purpose: wallets, holding customer money, lending, cards / UPI PINs (never typed anywhere in Hoola)."""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from ..paygate import gw as GW
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"started": 0, "paid": 0, "mismatch": 0, "webhooks": 0, "webhooks_bad": 0, "refunds": 0, "links": 0, "subs": 0,
         "transfers": 0, "reconciled": 0}
PAGE_MIN = 30
PERIODS = ("week", "month", "year")


class PayError(W.AppError):
    pass


class AppPayKeys(Base):
    __tablename__ = "app_pay_keys"
    app_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    gateway: Mapped[str] = mapped_column(String(16))
    sealed: Mapped[str] = mapped_column(Text)
    test: Mapped[int] = mapped_column(Integer, default=0)
    added: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppPayment(Base):
    __tablename__ = "app_payment"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="order")       # order | link | sub
    coll: Mapped[str] = mapped_column(String(40), default="")
    row_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    member: Mapped[str] = mapped_column(String(40), default="")
    gateway: Mapped[str] = mapped_column(String(16))
    gw_order: Mapped[str] = mapped_column(String(80), default="", index=True)
    payment_id: Mapped[str] = mapped_column(String(80), default="")
    amount: Mapped[int] = mapped_column(Integer)                          # paise
    status: Mapped[str] = mapped_column(String(12), default="created")   # created | paid | failed | mismatch
    refunded: Mapped[int] = mapped_column(Integer, default=0)
    label: Mapped[str] = mapped_column(String(200), default="")
    meta: Mapped[str] = mapped_column(Text, default="{}")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppRefund(Base):
    __tablename__ = "app_refund"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    payment: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="sending")  # sending | pending | done | failed | ambiguous
    gw_refund: Mapped[str] = mapped_column(String(80), default="")
    why: Mapped[str] = mapped_column(String(200), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AppSub(Base):
    __tablename__ = "app_sub"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(40), index=True)
    member: Mapped[str] = mapped_column(String(40), index=True)
    plan: Mapped[str] = mapped_column(String(40))
    gateway: Mapped[str] = mapped_column(String(16))
    sub_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    status: Mapped[str] = mapped_column(String(14), default="created")   # created | authenticated | activated | charged | halted | cancelled | completed
    charges: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_OK = False


def ensure_tables() -> None:
    global _OK
    if _OK:
        return
    from .. import db as _db
    if _db._engine is not None:
        for t in (AppPayKeys, AppPayment, AppRefund, AppSub):
            t.__table__.create(_db._engine, checkfirst=True)
        _OK = True


def _site(r: AppProject) -> str:
    return "app:" + r.id


def _j(s: Any, d: Any) -> Any:
    try:
        v = json.loads(s) if isinstance(s, str) and s else d
    except ValueError:
        return d
    return v if v is not None else d


def _rs(p: int) -> str:
    return f"Rs {p / 100:,.2f}".replace(".00", "")


def _cfg(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    return dict(BE.ensure(r).get("pay") or {})


def _keys(r: AppProject) -> tuple[str, dict[str, str], bool] | None:
    ensure_tables()
    with session() as s:
        k = s.get(AppPayKeys, r.id)
        if k is None:
            return None
        gw, sealed, test = k.gateway, k.sealed, bool(k.test)
    from ..bazar.security import vault
    try:
        return gw, json.loads(vault().open(sealed)), test
    except Exception:                                      # noqa: BLE001
        log.warning("pay keys could not be opened for %s", r.id)
        return None


def _client(r: AppProject):
    k = _keys(r)
    if k is None:
        raise PayError("Online payment band hai (dukaan ne gateway nahi joda).", 409)
    return GW.client(k[0], k[1], k[2]), k[0]


def on(r: AppProject) -> bool:
    return _keys(r) is not None


def _note(r: AppProject, text: str) -> None:
    try:
        from .android.service import _note as N
        N(r, text)
    except Exception:                                      # noqa: BLE001
        log.debug("pay note", exc_info=True)


def _base() -> str:
    from . import service as AS
    return (AS._settings().public_base_url or "").rstrip("/")


def _app_key(r: AppProject) -> str:
    return str(_j(r.android, {}).get("app_key") or "")


def webhook_url(r: AppProject) -> str:
    return f"{_base()}/api/app-api/{_app_key(r)}/pay/webhook"


# ---------------------------------------------------------------- her keys (typed in the app, sealed, never returned)
def set_keys(r: AppProject, gateway: str, creds: dict[str, Any], test: bool = False) -> dict[str, Any]:
    if gateway not in GW.GATEWAYS:
        raise PayError("Gateway: razorpay | cashfree | phonepe.", 400)
    c = {k: str(creds.get(k) or "").strip() for k in GW.KEY_FIELDS[gateway]}
    missing = [k for k, v in c.items() if not v and not (gateway == "phonepe" and k == "client_version")]
    if missing:
        raise PayError("Yeh bhi chahiye: " + ", ".join(missing), 400)
    if any(len(v) > 300 or re.search(r"\s", v) for v in c.values()):
        raise PayError("Chaabi mein space / bahut lambi value - dobara copy kijiye.", 400)
    try:
        chk = GW.client(gateway, c, test).check()          # a real read with her keys: wrong keys never get saved
    except GW.GwError as e:
        raise PayError(f"Gateway ne yeh chaabi nahi maani: {e}", 400)
    from ..bazar.security import vault
    ensure_tables()
    with session() as s:
        k = s.get(AppPayKeys, r.id)
        if k is None:
            k = AppPayKeys(app_id=r.id, gateway=gateway, sealed="")
            s.add(k)
        k.gateway, k.sealed, k.test, k.added = gateway, vault().seal(json.dumps(c)), 1 if (test or chk.get("test")) else 0, now()
    return status(r)


def forget_keys(r: AppProject) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        k = s.get(AppPayKeys, r.id)
        if k is not None:
            s.delete(k)
    return status(r)


def _view(p: AppPayment, refunds: list[AppRefund] | None = None) -> dict[str, Any]:
    out = {"id": p.id, "kind": p.kind, "coll": p.coll, "row": p.row_id, "gateway": p.gateway, "amount": p.amount,
           "amount_rs": _rs(p.amount), "status": p.status, "refunded": p.refunded, "label": p.label, "payment_id": p.payment_id,
           "created": p.created.isoformat() if p.created else "", "paid_at": p.paid_at.isoformat() if p.paid_at else ""}
    if refunds is not None:
        out["refunds"] = [{"id": f.id, "number": f.number, "amount": f.amount, "amount_rs": _rs(f.amount), "status": f.status,
                           "at": f.at.isoformat() if f.at else ""} for f in refunds]
    m = _j(p.meta, {})
    if m.get("url"):
        out["url"] = m["url"]
    if m.get("why"):
        out["why"] = m["why"]
    return out


def status(r: AppProject) -> dict[str, Any]:
    """Her payments page: gateway (never the keys), webhook address + how to set it, recent payments, plans, split rule."""
    k = _keys(r)
    cfg = _cfg(r)
    ensure_tables()
    with session() as s:
        ps = s.scalars(select(AppPayment).where(AppPayment.app_id == r.id).order_by(AppPayment.created.desc()).limit(60)).all()
        rf = s.scalars(select(AppRefund).where(AppRefund.payment.in_([p.id for p in ps] or ["-"]))).all()
        subs = s.scalars(select(AppSub).where(AppSub.app_id == r.id).order_by(AppSub.created.desc()).limit(60)).all()
        by: dict[str, list[AppRefund]] = {}
        for f in rf:
            by.setdefault(f.payment, []).append(f)
        pays = [_view(p, by.get(p.id, [])) for p in ps]
        sv = [{"id": x.id, "member": x.member, "plan": x.plan, "status": x.status, "charges": x.charges,
               "created": x.created.isoformat() if x.created else ""} for x in subs]
    paid = [p for p in pays if p["status"] == "paid"]
    out = {"on": k is not None, "gateway": k[0] if k else "", "test": bool(k and k[2]), "gateways": list(GW.GATEWAYS),
           "fields": {g: list(f) for g, f in GW.KEY_FIELDS.items()}, "can": sorted(GW.CAN.get(k[0], set())) if k else [],
           "webhook_url": webhook_url(r) if k else "", "dashboard": GW.DASHBOARD.get(k[0], "") if k else "",
           "webhook_how": _how(k[0]) if k else "",
           "payments": pays, "plans": [p for p in cfg.get("plans") or [] if not p.get("off")], "subs": sv,
           "split": cfg.get("split") or {}, "vendors": cfg.get("vendors") or [],
           "totals": {"paid": sum(p["amount"] for p in paid), "refunded": sum(p["refunded"] for p in paid),
                      "count": len(paid), "mismatch": sum(1 for p in pays if p["status"] == "mismatch")}}
    return out


def _how(gw: str) -> str:
    return {"razorpay": "Razorpay Dashboard > Account & Settings > Webhooks > Add: is address ko daaliye, wahi secret jo yahan diya, "
                        "events: payment.captured, payment.failed, order.paid, refund.processed, refund.failed, payment_link.paid, subscription.*",
            "cashfree": "Cashfree > Developers > Webhooks > Add: is address ko daaliye (Payment, Refund, Payment Link, Subscription events). "
                        "Signature aapke client secret se check hota hai.",
            "phonepe": "PhonePe Business > Developer settings > Webhook: is address ko daaliye aur wahi username / password jo yahan diya."}[gw]


# ---------------------------------------------------------------- the customer pays an order
def _row(r: AppProject, coll: str, row_id: str) -> tuple[W.SiteAppRow, dict[str, Any]]:
    with session() as s:
        x = s.get(W.SiteAppRow, row_id)
        if x is not None:
            s.expunge(x)
    if x is None or x.site_id != _site(r) or x.coll != coll:
        raise PayError("Yeh entry nahi mili.", 404)
    return x, _j(x.data, {})


def _customer(w: W.Who) -> dict[str, str]:
    m = w.m
    return {"id": m.id if m else "", "name": (m.name if m else "")[:100], "email": (m.email if m else "")[:120], "phone": ""}


def _sign(pid: str, exp: int) -> str:
    from ..site.webapp import _secret
    return hmac.new(_secret(), f"pay|{pid}|{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def page_token(pid: str, minutes: int = PAGE_MIN) -> str:
    exp = int(time.time()) + minutes * 60
    return f"{pid}.{exp}.{_sign(pid, exp)}"


def _from_token(tok: str) -> str:
    try:
        pid, exp, sig = str(tok).split(".")
        exp_i = int(exp)
    except ValueError:
        raise PayError("Link sahi nahi.", 404)
    if not hmac.compare_digest(sig, _sign(pid, exp_i)):
        raise PayError("Link sahi nahi.", 404)
    if exp_i < time.time():
        raise PayError("Yeh payment link purana ho gaya - app se dobara Pay dabaiye.", 410)
    return pid


def start(r: AppProject, w: W.Who, coll: str, row_id: str) -> dict[str, Any]:
    """POST /pay/c/<coll>/<id>/start: the customer's own unpaid order -> a gateway order for the SERVER's total -> pay page."""
    from . import backend as BE
    if w.m is None:
        raise PayError("Pehle login kijiye.", 401)
    if coll != BE.schema(r).get("order"):
        raise PayError("Is list ka online payment nahi.", 400)
    cl, gw = _client(r)
    x, d = _row(r, coll, row_id)
    if x.owner != w.m.id:
        raise PayError("Yeh entry nahi mili.", 404)
    if str(d.get("paid") or "No") == "Verified" or d.get("_pay"):
        raise PayError("Iska payment ho chuka hai.", 409)
    if str(d.get("status") or "") in ("Cancelled", "Rejected"):
        raise PayError("Yeh order cancel ho chuka hai.", 409)
    try:
        amount = GW.paise(d.get("total") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount < 100:
        raise PayError("Is order ki raqam abhi tay nahi (dukaan se poochhiye).", 409)
    W.rate(f"pay-start:{r.id}:{w.m.id}", 6, 600)
    ensure_tables()
    cut = now() - timedelta(minutes=PAGE_MIN - 5)
    with session() as s:                                  # the same order again within the window = the same payment
        old = s.scalars(select(AppPayment).where(AppPayment.app_id == r.id, AppPayment.row_id == row_id,
                                                 AppPayment.status == "created", AppPayment.created >= cut)).first()
        if old is not None and old.amount == amount and old.gateway == gw:
            return {"payment": old.id, "path": f"/api/app-api/{_app_key(r)}/pay/p/{page_token(old.id)}", "amount": amount}
    pid = new_id("pay")
    split = _split_parts(r, amount) if gw == "cashfree" else None
    try:
        made = cl.create_order(amount, pid, _customer(w), {"app": r.id, "row": row_id}, _return_url(r, pid), split)
    except GW.GwError as e:
        raise PayError(f"Payment shuru nahi hua: {e}", 502)
    with session() as s:
        s.add(AppPayment(id=pid, app_id=r.id, kind="order", coll=coll, row_id=row_id, member=w.m.id, gateway=gw,
                         gw_order=made["gw_order"], amount=amount, label=f"Order {row_id[-6:]}",
                         meta=json.dumps({"checkout": made["checkout"], "split": bool(split)})))
    STATS["started"] += 1
    return {"payment": pid, "path": f"/api/app-api/{_app_key(r)}/pay/p/{page_token(pid)}", "amount": amount}


def _return_url(r: AppProject, pid: str) -> str:
    return f"{_base()}/api/app-api/{_app_key(r)}/pay/p/{page_token(pid, 120)}?back=1"


# ---------------------------------------------------------------- the pay page (the gateway's own checkout)
def page(r: AppProject, tok: str) -> str:
    pid = _from_token(tok)
    with session() as s:
        p = s.get(AppPayment, pid)
        if p is not None:
            s.expunge(p)
    if p is None or p.app_id != r.id:
        raise PayError("Payment nahi mila.", 404)
    co = _j(p.meta, {}).get("checkout") or {}
    name = html.escape(r.name or "Shop")
    amt = _rs(p.amount)
    sub = p.kind == "sub"
    plan = _j(p.meta, {}).get("plan") or {}
    consent = ""
    if sub:
        every = {"week": "har hafte / every week", "month": "har mahine / every month", "year": "har saal / every year"}.get(plan.get("period"), "")
        consent = (f"<p class='c'><b>Automatic payment:</b> {html.escape(_rs(int(plan.get('amount') or 0)))} {every}, "
                   f"{int(plan.get('count') or 0)} times, from your account through {html.escape(p.gateway.title())} "
                   f"(UPI AutoPay / mandate). You approve it on the next screen, and you can cancel it any time in the app.</p>")
    state_url = f"/api/app-api/{_app_key(r)}/pay/s/{html.escape(tok)}"
    js_src = GW.CHECKOUT_JS.get(p.gateway, "")
    data = html.escape(json.dumps({"co": co, "name": r.name or "Shop", "desc": p.label}), quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pay {name}</title><style>body{{font:16px/1.5 system-ui,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#1d1d1f}}
h1{{font-size:22px;margin:0 0 4px}}.a{{font-size:32px;font-weight:600;margin:12px 0}}button{{width:100%;padding:14px;font-size:17px;border:0;
border-radius:12px;background:#4f46e5;color:#fff}}.m{{color:#555;font-size:14px}}.c{{background:#f4f4f6;padding:12px;border-radius:10px;font-size:14px}}
.ok{{color:#0a7d3c;font-weight:600}}.bad{{color:#b42318;font-weight:600}}</style>{f'<script src="{js_src}"></script>' if js_src else ''}</head>
<body><h1>{name}</h1><div class="m">{html.escape(p.label)}</div><div class="a">{amt}</div>{consent}
<p class="m">You pay on {html.escape(p.gateway.title())}'s own secure page. The shop gets the money in its bank account; this app never sees your card, UPI PIN or bank details.</p>
<button id="go">{'Approve AutoPay' if sub else 'Pay ' + amt}</button><p id="st" class="m" aria-live="polite"></p>
<div id="d" data-x="{data}" hidden></div>
<script>
var X=JSON.parse(document.getElementById('d').dataset.x),co=X.co,st=document.getElementById('st'),busy=0;
function check(){{fetch('{state_url}',{{cache:'no-store'}}).then(function(r){{return r.json()}}).then(function(j){{
 if(j.status==='paid'||j.status==='activated'||j.status==='authenticated'){{st.className='ok';st.textContent='Payment received and confirmed by the gateway. You can go back to the app.';document.getElementById('go').hidden=true;return}}
 if(j.status==='failed'){{st.className='bad';st.textContent='The payment did not go through. You can try again.';busy=0;return}}
 if(j.status==='mismatch'){{st.className='bad';st.textContent='The shop will check this payment.';return}}
 setTimeout(check,3000)}}).catch(function(){{setTimeout(check,5000)}})}}
document.getElementById('go').onclick=function(){{if(busy)return;busy=1;st.className='m';st.textContent='Opening the secure payment page...';
 if(co.gateway==='razorpay'){{var o={{key:co.key,name:X.name,description:X.desc,prefill:co.prefill||{{}},
   handler:function(){{st.textContent='Checking with the gateway...';check()}},modal:{{ondismiss:function(){{busy=0;st.textContent=''}}}}}};
   if(co.subscription_id)o.subscription_id=co.subscription_id;else{{o.order_id=co.order_id;o.amount=co.amount;o.currency=co.currency}}
   new Razorpay(o).open()}}
 else if(co.gateway==='cashfree'){{var c=Cashfree({{mode:co.mode}});
   if(co.subs_session)c.subscriptionsCheckout({{subsSessionId:co.subs_session,redirectTarget:'_self'}});
   else c.checkout({{paymentSessionId:co.session,redirectTarget:'_self'}})}}
 else if(co.gateway==='phonepe'&&co.redirect){{location.href=co.redirect}}}};
if(location.search.indexOf('back=1')>=0){{st.textContent='Checking with the gateway...';check()}}
</script></body></html>"""


PAGE_CSP = ("default-src 'none'; script-src 'unsafe-inline' https://checkout.razorpay.com https://sdk.cashfree.com; "
            "style-src 'unsafe-inline'; img-src https: data:; connect-src 'self' https://*.razorpay.com https://*.cashfree.com; "
            "frame-src https://*.razorpay.com https://*.cashfree.com; form-action https:; base-uri 'none'; frame-ancestors 'none'")


def page_state(r: AppProject, tok: str) -> dict[str, Any]:
    """The pay page asks how it went. If the webhook has not come yet, the SERVER asks the gateway (her keys), at most every 4 s."""
    pid = _from_token(tok)
    with session() as s:
        p = s.get(AppPayment, pid)
        if p is not None:
            s.expunge(p)
    if p is None or p.app_id != r.id:
        raise PayError("Payment nahi mila.", 404)
    if p.kind == "sub":
        with session() as s:
            sb = s.scalars(select(AppSub).where(AppSub.app_id == r.id, AppSub.sub_id == p.gw_order)).first()
            return {"status": sb.status if sb else "created"}
    if p.status == "created" and (p.checked is None or (now() - _aware(p.checked)).total_seconds() >= 4):
        _reconcile_one(r, p)
        with session() as s:
            p = s.get(AppPayment, pid)
            s.expunge(p)
    return {"status": p.status}


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _reconcile_one(r: AppProject, p: AppPayment) -> None:
    with session() as s:
        x = s.get(AppPayment, p.id)
        x.checked = now()
    try:
        cl, _gw = _client(r)
        st = cl.order_state(p.gw_order, p.id)
    except (GW.GwError, PayError) as e:
        log.info("pay reconcile %s: %s", p.id, e)
        return
    if st["state"] == "paid":
        STATS["reconciled"] += 1
        _paid(r, p.id, st.get("payment_id", ""), int(st.get("amount") or 0), st.get("method", ""), "status read")
    elif st["state"] == "failed":
        _set(p.id, status="failed")


def _set(pid: str, **kw: Any) -> None:
    with session() as s:
        x = s.get(AppPayment, pid)
        for k, v in kw.items():
            setattr(x, k, v)


def _paid(r: AppProject, pid: str, payment_id: str, amount: int, method: str, source: str) -> None:
    """THE one place a payment becomes paid - called only with what the gateway said (verified webhook / status read)."""
    from . import backend as BE
    from . import locks as LK
    with LK.app(r.id):
        with session() as s:
            p = s.get(AppPayment, pid)
            if p is None or p.status == "paid":
                return
            if amount != p.amount:
                p.status = "mismatch"
                p.payment_id = payment_id
                p.meta = json.dumps({**_j(p.meta, {}), "why": f"gateway said {_rs(amount)}, order was {_rs(p.amount)}"})
                STATS["mismatch"] += 1
                mismatch = True
            else:
                p.status, p.payment_id, p.paid_at = "paid", payment_id, now()
                mismatch = False
            kind, coll, row_id, gw, label, want = p.kind, p.coll, p.row_id, p.gateway, p.label, p.amount
        if mismatch:
            _note(r, f"Payment mein farak: {label} - gateway ne {_rs(amount)} bataya, order {_rs(want)} ka tha. "
                     "Order paid nahi maana; apne gateway dashboard mein dekhiye.")
            return
        STATS["paid"] += 1
        if kind == "order" and row_id:
            BE._merge(row_id, {"paid": "Verified", "_pay": {"gateway": gw, "payment_id": payment_id, "amount": amount,
                                                            "method": method, "at": now().isoformat(), "by": source}})
    if kind in ("order", "link"):
        _note(r, f"Online payment aaya: {label} - {_rs(amount)} ({gw.title()}, {payment_id}). Paisa aapke bank mein gateway se aayega.")
    if kind == "order":
        _transfers(r, pid, payment_id, amount)


# ---------------------------------------------------------------- webhooks (her gateway calls Hoola)
def webhook(r: AppProject, headers: dict[str, str], raw: bytes) -> dict[str, Any]:
    k = _keys(r)
    if k is None:
        raise PayError("Gateway nahi juda.", 404)
    cl = GW.client(k[0], k[1], k[2])
    h = {a.lower(): b for a, b in headers.items()}
    if not cl.verify(h, raw):
        STATS["webhooks_bad"] += 1
        log.warning("pay webhook with a bad signature for app %s", r.id)
        raise PayError("Signature galat.", 401)
    STATS["webhooks"] += 1
    done = 0
    for ev in cl.events(GW.body_json(raw)):
        try:
            done += _apply(r, ev)
        except Exception:                                  # noqa: BLE001 - one bad event never loses the others
            log.exception("pay webhook event")
    return {"ok": True, "applied": done}


def _by_order(r: AppProject, gw_order: str) -> AppPayment | None:
    if not gw_order:
        return None
    with session() as s:
        p = s.scalars(select(AppPayment).where(AppPayment.app_id == r.id, AppPayment.gw_order == gw_order)).first()
        if p is not None:
            s.expunge(p)
    return p


def _apply(r: AppProject, ev: dict[str, Any]) -> int:
    kind = ev.get("kind")
    if kind == "paid":
        p = _by_order(r, ev.get("gw_order", ""))
        if p is None:
            return 0
        _paid(r, p.id, ev.get("payment_id", ""), int(ev.get("amount") or 0), ev.get("method", ""), "webhook")
        return 1
    if kind == "failed":
        p = _by_order(r, ev.get("gw_order", ""))
        if p is not None and p.status == "created":
            _set(p.id, status="failed")
            return 1
        return 0
    if kind == "link_paid":
        with session() as s:
            p = s.scalars(select(AppPayment).where(AppPayment.app_id == r.id, AppPayment.kind == "link",
                                                   AppPayment.gw_order.in_([ev.get("link_id", ""), ev.get("ref", "")]))).first()
            pid = p.id if p else ""
        if pid:
            _paid(r, pid, ev.get("payment_id", ""), int(ev.get("amount") or 0), "link", "webhook")
            return 1
        return 0
    if kind == "refund":
        return _refund_event(r, ev)
    if kind == "sub":
        return _sub_event(r, ev)
    return 0


# ---------------------------------------------------------------- refunds (her tap only)
def refund(r: AppProject, pid: str, amount_rs: Any = None, why: str = "", her_tap: bool = False) -> dict[str, Any]:
    if not her_tap:
        raise PayError("Refund sirf aapke tap se hota hai.", 403)
    cl, gw = _client(r)
    if "refund" not in GW.CAN.get(gw, set()):
        raise PayError("Is gateway se refund Hoola se nahi.", 400)
    from . import locks as LK
    with LK.app(r.id):
        with session() as s:
            p = s.get(AppPayment, pid)
            if p is None or p.app_id != r.id:
                raise PayError("Payment nahi mila.", 404)
            if p.status != "paid":
                raise PayError("Sirf paid payment ka refund ho sakta hai.", 409)
            open_ = s.scalars(select(AppRefund).where(AppRefund.payment == pid, AppRefund.status.in_(("sending", "pending", "ambiguous")))).all()
            held = sum(f.amount for f in open_)
            left = p.amount - p.refunded - held
            try:
                amt = left if amount_rs in (None, "") else GW.paise(amount_rs)
            except (TypeError, ValueError):
                raise PayError("Raqam sahi nahi.", 400)
            if amt <= 0 or amt > left:
                raise PayError(f"Refund {_rs(left)} se zyada nahi ho sakta.", 400)
            n = s.query(AppRefund).filter(AppRefund.payment == pid).count() + 1
            f = AppRefund(id=new_id("rfd"), payment=pid, number=f"HR{pid[-10:]}{n:02d}", amount=amt, why=str(why or "")[:200])
            s.add(f)
            fid, number, payment_id, gw_order = f.id, f.number, p.payment_id, p.gw_order
    STATS["refunds"] += 1
    return _send_refund(r, cl, fid, number, payment_id, gw_order, amt)


def _send_refund(r: AppProject, cl, fid: str, number: str, payment_id: str, gw_order: str, amt: int) -> dict[str, Any]:
    try:
        got = cl.refund(payment_id, gw_order, amt, number)
    except GW.GwError as e:
        with session() as s:
            f = s.get(AppRefund, fid)
            f.status = "ambiguous" if e.ambiguous else "failed"
        if e.ambiguous:
            return {"ok": False, "refund": fid, "status": "ambiguous",
                    "say": "Gateway ne samay par jawab nahi diya - refund hua ya nahi, Hoola usi number se poochh kar batayega (dobara nahi bhejega)."}
        raise PayError(f"Refund nahi hua: {e}", 502)
    with session() as s:
        f = s.get(AppRefund, fid)
        f.gw_refund, f.status = got.get("refund_id", ""), got.get("status", "pending")
    if got.get("status") == "done":
        _refund_done(fid)
    return {"ok": True, "refund": fid, "number": number, "status": got.get("status", "pending"), "amount": amt,
            "say": f"Refund {_rs(amt)} gateway ko bheja ({number}). Bank tak 5-7 kaam ke din lag sakte hain."}


def _refund_done(fid: str) -> None:
    with session() as s:
        f = s.get(AppRefund, fid)
        if f is None or f.status == "counted":
            return
        p = s.get(AppPayment, f.payment)
        p.refunded = min(p.amount, p.refunded + f.amount)
        f.status = "counted"


def _refund_event(r: AppProject, ev: dict[str, Any]) -> int:
    with session() as s:
        f = None
        if ev.get("receipt"):
            f = s.scalars(select(AppRefund).where(AppRefund.number == ev["receipt"])).first()
        if f is None and ev.get("refund_id"):
            f = s.scalars(select(AppRefund).where(AppRefund.gw_refund == ev["refund_id"])).first()
        if f is None:
            return 0
        fid = f.id
        if ev.get("refund_id"):
            f.gw_refund = ev["refund_id"]
        if ev.get("status") == "failed" and f.status != "counted":
            f.status = "failed"
    if ev.get("status") == "done":
        _refund_done(fid)
    return 1


def refund_check(r: AppProject, fid: str) -> dict[str, Any]:
    """An ambiguous / pending refund: ask the gateway with the SAME number (never a second refund)."""
    cl, _gw = _client(r)
    with session() as s:
        f = s.get(AppRefund, fid)
        p = s.get(AppPayment, f.payment) if f else None
        if f is None or p is None or p.app_id != r.id:
            raise PayError("Refund nahi mila.", 404)
        number, payment_id, gw_order, st = f.number, p.payment_id, p.gw_order, f.status
    if st == "counted":
        return {"status": "done"}
    try:
        got = cl.refund_state(payment_id, gw_order, number)
    except GW.GwError as e:
        return {"status": st, "say": f"Gateway se pata nahi chala: {e}"}
    if got.get("status") == "done":
        with session() as s:
            s.get(AppRefund, fid).gw_refund = got.get("refund_id", "")
        _refund_done(fid)
        return {"status": "done"}
    if got.get("status") in ("pending", "failed"):
        with session() as s:
            s.get(AppRefund, fid).status = got["status"]
    return {"status": got.get("status", st)}


# ---------------------------------------------------------------- settlements, payment links
def settlements(r: AppProject) -> dict[str, Any]:
    cl, gw = _client(r)
    try:
        return {"gateway": gw, "settlements": cl.settlements()}
    except GW.GwError as e:
        raise PayError(str(e), e.code if e.code in (400, 401) else 502)


def link(r: AppProject, amount_rs: Any, purpose: str, name: str = "", phone: str = "", her_tap: bool = False,
         coll: str = "", row_id: str = "") -> dict[str, Any]:
    if not her_tap:
        raise PayError("Payment link sirf aapke tap se banta hai.", 403)
    cl, gw = _client(r)
    if "links" not in GW.CAN.get(gw, set()):
        raise PayError("Is gateway ke payment links Hoola se nahi.", 400)
    try:
        amount = GW.paise(amount_rs)
    except (TypeError, ValueError):
        raise PayError("Raqam sahi nahi.", 400)
    if amount < 100 or amount > 10_000_000:
        raise PayError("Raqam Rs 1 se Rs 1,00,000 ke beech.", 400)
    ph = re.sub(r"\D", "", str(phone or ""))[-10:]
    pid = new_id("pay")
    try:
        got = cl.link(amount, str(purpose or "Payment")[:200], {"name": str(name or "")[:80], "phone": ph}, pid)
    except GW.GwError as e:
        raise PayError(f"Link nahi bana: {e}", 502)
    ensure_tables()
    with session() as s:
        s.add(AppPayment(id=pid, app_id=r.id, kind="link", coll=coll, row_id=row_id, gateway=gw, gw_order=got.get("link_id") or pid,
                         amount=amount, label=str(purpose or "Payment link")[:200], meta=json.dumps({"url": got.get("url", "")})))
    STATS["links"] += 1
    return {"payment": pid, "url": got.get("url", ""), "amount": amount,
            "say": f"Link bana: {_rs(amount)}. Aap khud bhejiye (WhatsApp / SMS); paid hote hi yahan dikhega."}


# ---------------------------------------------------------------- subscriptions / UPI AutoPay (customer consent)
def add_plan(r: AppProject, name: str, amount_rs: Any, period: str, count: Any, her_tap: bool = False) -> dict[str, Any]:
    if not her_tap:
        raise PayError("Plan sirf aapke tap se banta hai.", 403)
    cl, gw = _client(r)
    if "subscriptions" not in GW.CAN.get(gw, set()):
        raise PayError("Is gateway ki subscriptions Hoola se nahi.", 400)
    if period not in PERIODS:
        raise PayError("Har: week | month | year.", 400)
    try:
        amount, n = GW.paise(amount_rs), int(count)
    except (TypeError, ValueError):
        raise PayError("Raqam / kitni baar sahi nahi.", 400)
    if amount < 100 or not (1 <= n <= 120):
        raise PayError("Raqam kam se kam Rs 1, baar 1-120.", 400)
    nm = re.sub(r"[\x00-\x1f]", " ", str(name or "")).strip()[:80] or "Plan"
    try:
        gw_plan = cl.plan(nm, amount, period)
    except GW.GwError as e:
        raise PayError(f"Plan nahi bana: {e}", 502)
    from . import backend as BE
    key = "pl_" + secrets.token_hex(4)

    def go(be):
        p = dict(be.get("pay") or {})
        p["plans"] = list(p.get("plans") or []) + [{"key": key, "name": nm, "amount": amount, "period": period, "count": n,
                                                    "gateway": gw, "gw_plan": gw_plan}]
        be["pay"] = p
    BE.patch_backend(r, fn=go)
    return status(r)


def drop_plan(r: AppProject, key: str) -> dict[str, Any]:
    """Hidden from new customers; running subscriptions are NOT touched (each customer / she cancels her own)."""
    from . import backend as BE

    def go(be):
        p = dict(be.get("pay") or {})
        p["plans"] = [dict(x, off=True) if x.get("key") == key else x for x in p.get("plans") or []]
        be["pay"] = p
    BE.patch_backend(r, fn=go)
    return status(r)


def plans(r: AppProject) -> dict[str, Any]:
    k = _keys(r)
    return {"on": k is not None, "plans": [{"key": p["key"], "name": p["name"], "amount": p["amount"], "amount_rs": _rs(p["amount"]),
                                            "period": p["period"], "count": p["count"]}
                                           for p in _cfg(r).get("plans") or [] if not p.get("off") and k and p.get("gateway") == k[0]]}


def subscribe(r: AppProject, w: W.Who, key: str) -> dict[str, Any]:
    if w.m is None:
        raise PayError("Pehle login kijiye.", 401)
    cl, gw = _client(r)
    pl = next((p for p in _cfg(r).get("plans") or [] if p.get("key") == key and not p.get("off") and p.get("gateway") == gw), None)
    if pl is None:
        raise PayError("Yeh plan ab nahi hai.", 404)
    W.rate(f"pay-sub:{r.id}:{w.m.id}", 3, 600)
    ensure_tables()
    with session() as s:
        live = s.scalars(select(AppSub).where(AppSub.app_id == r.id, AppSub.member == w.m.id, AppSub.plan == key,
                                              AppSub.status.in_(("authenticated", "activated", "charged")))).first()
        if live is not None:
            raise PayError("Yeh plan aapka pehle se chalu hai.", 409)
    sid = new_id("sub")
    try:
        got = cl.subscribe(pl["gw_plan"], int(pl["count"]), sid, _customer(w), _return_url(r, sid))
    except GW.GwError as e:
        raise PayError(f"Subscription shuru nahi hua: {e}", 502)
    with session() as s:
        s.add(AppSub(id=sid, app_id=r.id, member=w.m.id, plan=key, gateway=gw, sub_id=got["sub_id"]))
        s.add(AppPayment(id=sid, app_id=r.id, kind="sub", member=w.m.id, gateway=gw, gw_order=got["sub_id"], amount=pl["amount"],
                         label=pl["name"], meta=json.dumps({"checkout": got["checkout"], "plan": pl})))
    STATS["subs"] += 1
    return {"sub": sid, "path": f"/api/app-api/{_app_key(r)}/pay/p/{page_token(sid)}"}


def _sub_event(r: AppProject, ev: dict[str, Any]) -> int:
    with session() as s:
        sb = s.scalars(select(AppSub).where(AppSub.app_id == r.id, AppSub.sub_id == ev.get("sub_id", ""))).first()
        if sb is None:
            return 0
        st = str(ev.get("status") or "")
        if st == "charged":
            sb.charges += 1
            sb.status = "activated" if sb.status in ("created", "authenticated", "charged") else sb.status
        elif st in ("authenticated", "activated", "halted", "cancelled", "completed", "pending", "paused", "resumed"):
            sb.status = {"resumed": "activated", "paused": "halted"}.get(st, st)
        sb.updated = now()
        member, plan, charges, status_ = sb.member, sb.plan, sb.charges, sb.status
    if ev.get("status") == "charged" and ev.get("payment_id"):
        _note(r, f"AutoPay charge aaya: plan {plan}, {_rs(int(ev.get('amount') or 0))} (baar {charges}).")
    if status_ == "halted":
        _note(r, f"Ek subscription ruk gaya (plan {plan}): graahak ke mandate se paisa nahi kat paaya.")
    return 1


def my_subs(r: AppProject, w: W.Who) -> dict[str, Any]:
    if w.m is None:
        raise PayError("Pehle login kijiye.", 401)
    names = {p["key"]: p for p in _cfg(r).get("plans") or []}
    ensure_tables()
    with session() as s:
        xs = s.scalars(select(AppSub).where(AppSub.app_id == r.id, AppSub.member == w.m.id).order_by(AppSub.created.desc())).all()
        return {"subs": [{"id": x.id, "plan": names.get(x.plan, {}).get("name", x.plan),
                          "amount_rs": _rs(int(names.get(x.plan, {}).get("amount") or 0)), "period": names.get(x.plan, {}).get("period", ""),
                          "status": x.status, "charges": x.charges} for x in xs if x.status != "created" or
                         (now() - _aware(x.created)) < timedelta(hours=1)]}


def cancel_sub(r: AppProject, w: W.Who, sid: str) -> dict[str, Any]:
    """The customer cancels her own (her right, no questions) - or the owner cancels any."""
    with session() as s:
        sb = s.get(AppSub, sid)
        if sb is None or sb.app_id != r.id or not (w.owner or (w.m is not None and sb.member == w.m.id)):
            raise PayError("Subscription nahi mila.", 404)
        if sb.status in ("cancelled", "completed"):
            return {"ok": True, "status": sb.status}
        sub_id = sb.sub_id
    cl, _gw = _client(r)
    try:
        cl.cancel_sub(sub_id)
    except GW.GwError as e:
        raise PayError(f"Cancel nahi hua: {e}", 502)
    with session() as s:
        sb = s.get(AppSub, sid)
        sb.status, sb.updated = "cancelled", now()
    return {"ok": True, "status": "cancelled", "say": "AutoPay band. Aage koi paisa nahi katega."}


# ---------------------------------------------------------------- split payouts (her approved rule only)
def set_split(r: AppProject, vendors: list[dict[str, Any]], rules: list[dict[str, Any]], her_tap: bool = False) -> dict[str, Any]:
    if not her_tap:
        raise PayError("Payout rule sirf aapke tap se.", 403)
    _cl, gw = _client(r)
    if "split" not in GW.CAN.get(gw, set()):
        raise PayError("Is gateway ke split payouts Hoola se nahi.", 400)
    vs = []
    for v in vendors or []:
        acc = str(v.get("account") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-]{3,60}", acc):
            raise PayError("Vendor account id sahi nahi (jo gateway dashboard mein bana).", 400)
        vs.append({"key": str(v.get("key") or acc)[:40], "name": str(v.get("name") or acc)[:80], "account": acc})
    keys = {v["key"] for v in vs}
    rs, total = [], 0.0
    for x in rules or []:
        if x.get("vendor") not in keys:
            raise PayError("Rule mein anjaan vendor.", 400)
        pc = float(x.get("percent") or 0)
        if not (0 < pc <= 100):
            raise PayError("Percent 0-100.", 400)
        total += pc
        rs.append({"vendor": x["vendor"], "percent": round(pc, 2)})
    if total > 100:
        raise PayError("Sab vendors milakar 100% se zyada nahi.", 400)
    rule = {"vendors": vs, "rules": rs, "gateway": gw, "approved_at": now().isoformat()}
    rule["hash"] = hashlib.sha256(json.dumps({"v": vs, "r": rs, "g": gw}, sort_keys=True).encode()).hexdigest()[:16]
    from . import backend as BE

    def go(be):
        p = dict(be.get("pay") or {})
        p["split"], p["vendors"] = rule if rs else {}, vs
        be["pay"] = p
    BE.patch_backend(r, fn=go)
    return status(r)


def _split_parts(r: AppProject, amount: int) -> list[dict[str, Any]]:
    sp = _cfg(r).get("split") or {}
    k = _keys(r)
    if not sp.get("rules") or not k or sp.get("gateway") != k[0]:
        return []
    acc = {v["key"]: v["account"] for v in sp.get("vendors") or []}
    out = []
    for x in sp["rules"]:
        part = int(amount * float(x["percent"]) / 100)
        if part >= 100 and x["vendor"] in acc:
            out.append({"account": acc[x["vendor"]], "amount": part, "note": f"rule {sp.get('hash', '')}"})
    return out


def _transfers(r: AppProject, pid: str, payment_id: str, amount: int) -> None:
    k = _keys(r)
    if not k or k[0] != "razorpay":
        return                                             # Cashfree split already rode on the order
    parts = _split_parts(r, amount)
    if not parts:
        return
    with session() as s:
        p = s.get(AppPayment, pid)
        m = _j(p.meta, {})
        if m.get("transfers"):
            return                                         # never twice
        m["transfers"] = "sending"
        p.meta = json.dumps(m)
    try:
        ids = GW.client(k[0], k[1], k[2]).transfer(payment_id, parts)
        STATS["transfers"] += len(ids)
        res: Any = ids
    except GW.GwError as e:
        res = f"failed: {e}"
        _note(r, f"Vendor payout nahi gaya ({pid}): {e}. Razorpay dashboard > Route mein dekhiye.")
    with session() as s:
        p = s.get(AppPayment, pid)
        m = _j(p.meta, {})
        m["transfers"] = res
        p.meta = json.dumps(m)


# ---------------------------------------------------------------- the reconcile tick (webhook missing / late)
_LAST = [0.0]


def tick(force: bool = False) -> int:
    """Orders still 'created' 1-120 minutes after they started: ask the gateway (her keys). Every 2 minutes at most."""
    if not force and time.time() - _LAST[0] < 120:
        return 0
    _LAST[0] = time.time()
    ensure_tables()
    lo, hi = now() - timedelta(minutes=120), now() - timedelta(seconds=60)
    with session() as s:
        ps = s.scalars(select(AppPayment).where(AppPayment.kind == "order", AppPayment.status == "created",
                                                AppPayment.created >= lo, AppPayment.created <= hi).limit(200)).all()
        for p in ps:
            s.expunge(p)
    n = 0
    apps: dict[str, AppProject | None] = {}
    for p in ps:
        if p.app_id not in apps:
            with session() as s:
                a = s.get(AppProject, p.app_id)
                if a is not None:
                    s.expunge(a)
                apps[p.app_id] = a
        a = apps[p.app_id]
        if a is not None:
            _reconcile_one(a, p)
            n += 1
    with session() as s:                                   # ambiguous refunds: ask with the same number
        amb = s.scalars(select(AppRefund).where(AppRefund.status.in_(("ambiguous", "pending")),
                                                AppRefund.at >= now() - timedelta(days=10))).all()
        todo = [(f.id, f.payment) for f in amb]
    for fid, pid in todo:
        with session() as s:
            p = s.get(AppPayment, pid)
            app_id = p.app_id if p else ""
        a = apps.get(app_id)
        if a is None and app_id:
            with session() as s:
                a = s.get(AppProject, app_id)
                if a is not None:
                    s.expunge(a)
        if a is not None:
            try:
                refund_check(a, fid)
            except PayError:
                pass
    return n


# ---------------------------------------------------------------- what the app shows on a row
def row_info(r: AppProject, w: W.Who, coll: str, row_id: str) -> dict[str, Any]:
    """GET /pay/c/<coll>/<id>: can this person pay this order online now / is it paid (the app's Pay button)."""
    if w.m is None:
        raise PayError("Pehle login kijiye.", 401)
    x, d = _row(r, coll, row_id)
    if x.owner != w.m.id and not w.staff:
        raise PayError("Yeh entry nahi mili.", 404)
    paid = bool(d.get("_pay")) or str(d.get("paid") or "") == "Verified"
    return {"online": on(r), "paid": paid, "can_pay": on(r) and not paid and x.owner == w.m.id and
            str(d.get("status") or "") not in ("Cancelled", "Rejected") and float(d.get("total") or 0) >= 1}
