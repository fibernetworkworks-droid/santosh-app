"""v0.999.25 HOOLA CREDITS - money in from every country (owner: "GO Dodo Payments, Paddle, RAZORPAY, CASHFREE").

India (rupees, GST included): Razorpay or Cashfree - Newtika's OWN accounts (HOOLA_RAZORPAY_* / HOOLA_CASHFREE_* in
the VPS .env), the same clients the website shops use (paygate/gw.py).
Every other country (dollars): Dodo Payments or Paddle as merchant of record - they sell, add and pay each country's
tax and pay Newtika out. Their products / prices are made once in their dashboards and named here by SKU
(DODO_PRODUCTS / PADDLE_PRICES, JSON).

An order is PAID only from the provider: a signed webhook, or a server read of the provider's own record. The browser's
return page never counts. Each order gives its credits once (the paid row is claimed by one conditional update).

Shapes from the providers' own docs, read 19 Nov 2026 (docs.dodopayments.com, developer.paddle.com). NOT VERIFIED with
a live payment."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from . import plans as P

log = logging.getLogger("santosh.credits")
PROVIDERS = ("razorpay", "cashfree", "dodo", "paddle")
INDIA = ("razorpay", "cashfree")
WORLD = ("dodo", "paddle")

_TRANSPORT: httpx.BaseTransport | None = None


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t
    from ..paygate import gw
    gw.set_transport(t)


class PayError(Exception):
    def __init__(self, msg: str, code: int = 502):
        super().__init__(msg)
        self.code = code


def _st():
    from ..config import get_settings
    return get_settings()


def _req(method: str, url: str, **kw) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
            r = c.request(method, url, **kw)
    except httpx.HTTPError as e:
        raise PayError(f"The payment service did not answer ({type(e).__name__}).")
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.status_code >= 400:
        raise PayError(f"The payment service refused ({r.status_code}).", 502)
    return d if isinstance(d, dict) else {"items": d}


# ------------------------------------------------------------------ which provider
def ready(provider: str) -> bool:
    st = _st()
    return {
        "razorpay": bool(st.hoola_razorpay_key_id and st.hoola_razorpay_key_secret),
        "cashfree": bool(st.hoola_cashfree_client_id and st.hoola_cashfree_client_secret),
        "dodo": bool(st.dodo_api_key),
        "paddle": bool(st.paddle_api_key),
    }.get(provider, False)


def choose(region: str, asked: str = "") -> str:
    """Her pick if it serves her region and is set up, else the owner's default, else the other one."""
    st = _st()
    pool = INDIA if region == "in" else WORLD
    default = (st.credits_india_gateway if region == "in" else st.credits_world_gateway) or pool[0]
    for p in ([asked] if asked else []) + [default] + list(pool):
        if p in pool and ready(p):
            return p
    raise PayError("Payments are not set up yet for your country.", 503)


def _ids(field: str) -> dict[str, str]:
    try:
        d = json.loads(str(getattr(_st(), field, "") or "") or "{}")
        return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except ValueError:
        return {}


# ------------------------------------------------------------------ India: Razorpay / Cashfree (paygate clients)
def _india_client(provider: str):
    from ..paygate import gw
    st = _st()
    if provider == "razorpay":
        return gw.client("razorpay", {"key_id": st.hoola_razorpay_key_id, "key_secret": st.hoola_razorpay_key_secret,
                                      "webhook_secret": st.hoola_razorpay_webhook_secret})
    return gw.client("cashfree", {"client_id": st.hoola_cashfree_client_id, "client_secret": st.hoola_cashfree_client_secret})


# ------------------------------------------------------------------ Dodo Payments
def _dodo_base() -> str:
    k = str(_st().dodo_api_key or "")
    return "https://test.dodopayments.com" if k.startswith("dodo_test_") else "https://live.dodopayments.com"


def _dodo_h() -> dict[str, str]:
    return {"Authorization": f"Bearer {_st().dodo_api_key}"}


def dodo_verify(headers: dict[str, str], raw: bytes, tolerance: int = 300) -> bool:
    """Standard Webhooks: HMAC-SHA256 of '{id}.{timestamp}.{body}', key = base64 of the secret after 'whsec_'."""
    sec = str(_st().dodo_webhook_secret or "")
    wid, ts, sig = headers.get("webhook-id", ""), headers.get("webhook-timestamp", ""), headers.get("webhook-signature", "")
    if not sec or not wid or not ts or not sig:
        return False
    try:
        if abs(time.time() - int(ts)) > tolerance:
            return False
        key = base64.b64decode(sec[6:] if sec.startswith("whsec_") else sec)
    except (ValueError, TypeError):
        return False
    want = base64.b64encode(hmac.new(key, f"{wid}.{ts}.".encode() + raw, hashlib.sha256).digest()).decode()
    for part in sig.split():
        v = part.split(",", 1)
        if len(v) == 2 and v[0] == "v1" and hmac.compare_digest(v[1], want):
            return True
    return False


def dodo_events(body: dict[str, Any]) -> list[dict[str, Any]]:
    t, d = str(body.get("type") or ""), body.get("data") or {}
    meta = d.get("metadata") or {}
    base = {"order": str(meta.get("hoola_order") or ""), "payment_ref": str(d.get("payment_id") or ""),
            "sub_ref": str(d.get("subscription_id") or "")}
    kind = {"payment.succeeded": "paid", "payment.failed": "failed", "subscription.renewed": "renewed",
            "subscription.cancelled": "cancelled", "subscription.on_hold": "cancelled", "subscription.expired": "cancelled",
            "refund.succeeded": "refund"}.get(t)
    return [{**base, "kind": kind}] if kind else []


# ------------------------------------------------------------------ Paddle Billing
def _paddle_base() -> str:
    k = str(_st().paddle_api_key or "")
    return "https://sandbox-api.paddle.com" if "_sdbx_" in k else "https://api.paddle.com"


def _paddle_h() -> dict[str, str]:
    return {"Authorization": f"Bearer {_st().paddle_api_key}", "Content-Type": "application/json"}


def paddle_verify(headers: dict[str, str], raw: bytes, tolerance: int = 300) -> bool:
    """Paddle-Signature: ts=<unix>;h1=<hex HMAC-SHA256 of 'ts:body' with the endpoint secret as it is>."""
    sec = str(_st().paddle_webhook_secret or "")
    h = headers.get("paddle-signature", "")
    if not sec or not h:
        return False
    parts = [p.split("=", 1) for p in h.split(";") if "=" in p]
    ts = next((v for k, v in parts if k.strip() == "ts"), "")
    sigs = [v for k, v in parts if k.strip() == "h1"]
    try:
        if not ts or abs(time.time() - int(ts)) > tolerance:
            return False
    except ValueError:
        return False
    want = hmac.new(sec.encode(), ts.encode() + b":" + raw, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(s, want) for s in sigs)


def paddle_events(body: dict[str, Any]) -> list[dict[str, Any]]:
    t, d = str(body.get("event_type") or ""), body.get("data") or {}
    cd = d.get("custom_data") or {}
    if t == "transaction.completed":
        kind = "renewed" if (d.get("origin") == "subscription_recurring") else "paid"
        return [{"kind": kind, "order": str(cd.get("hoola_order") or ""), "provider_ref": str(d.get("id") or ""),
                 "payment_ref": str(d.get("id") or ""), "sub_ref": str(d.get("subscription_id") or "")}]
    if t == "transaction.payment_failed":
        return [{"kind": "failed", "order": str(cd.get("hoola_order") or ""), "provider_ref": str(d.get("id") or "")}]
    if t in ("subscription.canceled", "subscription.past_due", "subscription.paused"):
        return [{"kind": "cancelled", "order": "", "sub_ref": str(d.get("id") or "")}]
    if t in ("adjustment.created", "adjustment.updated") and d.get("action") == "refund" and d.get("status") == "approved":
        return [{"kind": "refund", "order": "", "provider_ref": str(d.get("transaction_id") or ""),
                 "payment_ref": str(d.get("transaction_id") or "")}]
    return []


# ------------------------------------------------------------------ one call for every provider
def create(provider: str, order_id: str, sku: str, amount_minor: int, currency: str, buyer: dict[str, str],
           return_url: str) -> dict[str, Any]:
    """Start a payment. Returns {provider_ref, redirect?, checkout?}."""
    if provider in INDIA:
        c = _india_client(provider)
        d = c.create_order(amount_minor, order_id, {"id": buyer.get("id", ""), "name": buyer.get("name", ""),
                                                     "email": buyer.get("email", ""), "phone": buyer.get("phone", "")},
                           {"hoola_order": order_id, "sku": sku}, return_url)
        return {"provider_ref": d["gw_order"], "checkout": d["checkout"]}
    if provider == "dodo":
        pid = _ids("dodo_products").get(sku)
        if not pid:
            raise PayError("This item is not set up in Dodo Payments yet (DODO_PRODUCTS).", 503)
        cust = {"email": buyer.get("email") or "", "name": buyer.get("name") or "Hoola user"}
        d = _req("POST", _dodo_base() + "/checkouts", headers=_dodo_h(),
                 json={"product_cart": [{"product_id": pid, "quantity": 1}], "customer": cust,
                       "return_url": return_url, "metadata": {"hoola_order": order_id, "sku": sku}})
        if not d.get("checkout_url"):
            raise PayError("Dodo Payments gave no checkout link.")
        return {"provider_ref": str(d.get("session_id") or ""), "redirect": d["checkout_url"]}
    if provider == "paddle":
        pid = _ids("paddle_prices").get(sku)
        if not pid:
            raise PayError("This item is not set up in Paddle yet (PADDLE_PRICES).", 503)
        d = _req("POST", _paddle_base() + "/transactions", headers=_paddle_h(),
                 json={"items": [{"price_id": pid, "quantity": 1}], "custom_data": {"hoola_order": order_id, "sku": sku}})
        data = d.get("data") or {}
        url = ((data.get("checkout") or {}).get("url")) or ""
        if not url:
            raise PayError("Paddle gave no checkout link (set a default payment link in Paddle).")
        return {"provider_ref": str(data.get("id") or ""), "redirect": url}
    raise PayError("Unknown payment service.", 400)


def state(provider: str, provider_ref: str, payment_ref: str = "") -> dict[str, Any]:
    """The provider's own record of a payment: {'state': paid|failed|pending, 'payment_ref'}."""
    if provider in INDIA:
        d = _india_client(provider).order_state(provider_ref)
        return {"state": d.get("state", "pending"), "payment_ref": str(d.get("payment_id") or "")}
    if provider == "dodo":
        if not payment_ref:
            return {"state": "pending"}
        d = _req("GET", _dodo_base() + f"/payments/{payment_ref}", headers=_dodo_h())
        st = str(d.get("status") or "").lower()
        return {"state": "paid" if st == "succeeded" else "failed" if st in ("failed", "cancelled") else "pending",
                "payment_ref": payment_ref, "sub_ref": str(d.get("subscription_id") or "")}
    if provider == "paddle":
        d = (_req("GET", _paddle_base() + f"/transactions/{provider_ref}", headers=_paddle_h()).get("data") or {})
        st = str(d.get("status") or "")
        return {"state": "paid" if st in ("completed", "paid") else "pending", "payment_ref": provider_ref,
                "sub_ref": str(d.get("subscription_id") or "")}
    return {"state": "pending"}


def verify_and_read(provider: str, headers: dict[str, str], raw: bytes) -> list[dict[str, Any]]:
    """A webhook: [] when the signature is wrong (nothing is believed); else the events in one shape."""
    h = {k.lower(): v for k, v in headers.items()}
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        return []
    if provider in INDIA:
        c = _india_client(provider)
        if not c.verify(h, raw):
            return []
        out = []
        for e in c.events(body):
            if e.get("kind") in ("paid", "failed"):
                out.append({"kind": e["kind"], "order": "", "provider_ref": str(e.get("gw_order") or ""),
                            "payment_ref": str(e.get("payment_id") or "")})
            elif e.get("kind") == "refund" and e.get("status") == "done":
                out.append({"kind": "refund", "order": "", "payment_ref": str(e.get("payment_id") or ""),
                            "provider_ref": str(e.get("gw_order") or "")})
        return out
    if provider == "dodo":
        return dodo_events(body) if dodo_verify(h, raw) else []
    if provider == "paddle":
        return paddle_events(body) if paddle_verify(h, raw) else []
    return []
