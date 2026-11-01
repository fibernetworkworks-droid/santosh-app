"""v0.417 PAISA (App Sahayak Pillar E): HER payment gateway - Razorpay, Cashfree PG, PhonePe PG - through each one's own
official server API (no SDK on Hoola's side, no scraping). Hoola never holds money: the customer pays the gateway on the
gateway's own checkout, the money settles to HER bank account, and Hoola only creates orders / refunds / links with HER
keys and reads back what the gateway says.

The rule every caller relies on: a payment is PAID only when the GATEWAY says so - a webhook whose signature verifies
with her secret, or a server-to-server status read with her keys. Never the phone's word, never a redirect URL.

Documented shapes this follows (said plainly: no live merchant account has answered this code yet):
  Razorpay  https://razorpay.com/docs/api/ - Basic key_id:key_secret; POST /v1/orders {amount paise, currency, receipt};
            GET /v1/orders/{id}/payments; webhook X-Razorpay-Signature = hex HMAC-SHA256(raw body, webhook secret);
            POST /v1/payments/{id}/refund {amount, speed normal, receipt}; GET /v1/settlements; POST /v1/payment_links;
            POST /v1/plans + /v1/subscriptions (+ /cancel); Route: POST /v1/payments/{id}/transfers.
  Cashfree  https://www.cashfree.com/docs/api-reference/payments/ - x-client-id / x-client-secret / x-api-version;
            POST /pg/orders -> payment_session_id; GET /pg/orders/{id}/payments; webhook x-webhook-signature =
            base64 HMAC-SHA256(x-webhook-timestamp + raw body, client secret); POST /pg/orders/{id}/refunds
            (x-idempotency-key); POST /pg/settlements; POST /pg/links; plans + subscriptions; order_splits (Easy Split).
  PhonePe   https://developer.phonepe.com/v1/reference/ (Standard Checkout v2) - OAuth client_credentials -> O-Bearer;
            POST /checkout/v2/pay -> redirectUrl; GET /checkout/v2/order/{merchantOrderId}/status; POST
            /payments/v2/refund; webhook Authorization = sha256(username:password). No links / plans / settlements here."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx

_TRANSPORT: httpx.BaseTransport | None = None


def set_transport(t: httpx.BaseTransport | None) -> None:
    """Tests replace the network with a recorded / fake gateway."""
    global _TRANSPORT
    _TRANSPORT = t


class GwError(Exception):
    def __init__(self, msg: str, code: int = 502, ambiguous: bool = False):
        super().__init__(msg)
        self.code, self.ambiguous = code, ambiguous


GATEWAYS = ("razorpay", "cashfree", "phonepe")
KEY_FIELDS = {
    "razorpay": ("key_id", "key_secret", "webhook_secret"),
    "cashfree": ("client_id", "client_secret"),
    "phonepe": ("client_id", "client_secret", "client_version", "webhook_user", "webhook_password"),
}
CAN = {   # what each gateway does through Hoola
    "razorpay": {"refund", "settlements", "links", "subscriptions", "split"},
    "cashfree": {"refund", "settlements", "links", "subscriptions", "split"},
    "phonepe": {"refund"},
}
CHECKOUT_JS = {"razorpay": "https://checkout.razorpay.com/v1/checkout.js", "cashfree": "https://sdk.cashfree.com/js/v3/cashfree.js"}
DASHBOARD = {"razorpay": "https://dashboard.razorpay.com/app/webhooks", "cashfree": "https://merchant.cashfree.com/merchants/pg/developers/webhooks",
             "phonepe": "https://business.phonepe.com/"}


def _req(method: str, url: str, **kw) -> httpx.Response:
    try:
        with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
            return c.request(method, url, **kw)
    except httpx.TimeoutException:
        raise GwError("Gateway ne samay par jawab nahi diya.", 504, ambiguous=True)   # it MAY have happened
    except httpx.HTTPError as e:
        raise GwError(f"Gateway tak nahi pahunch paaye ({type(e).__name__}).", 502)


def _json(r: httpx.Response) -> dict[str, Any]:
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.status_code >= 400:
        msg = ""
        if isinstance(d, dict):
            e = d.get("error")
            msg = (e.get("description") if isinstance(e, dict) else "") or d.get("message") or ""
        raise GwError(f"Gateway ne mana kiya ({r.status_code}){': ' + str(msg)[:200] if msg else ''}.",
                      401 if r.status_code in (401, 403) else 502)
    return d if isinstance(d, dict) else {"items": d}


def paise(rupees: Any) -> int:
    return int(round(float(rupees) * 100))


# ---------------------------------------------------------------- Razorpay
class Razorpay:
    name = "razorpay"

    def __init__(self, keys: dict[str, str], test: bool = False):
        self.k = keys
        self.base = (os.environ.get("PAY_RAZORPAY_BASE") or "https://api.razorpay.com").rstrip("/")
        self.test = test or str(keys.get("key_id", "")).startswith("rzp_test_")

    def _call(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        return _json(_req(method, self.base + path, auth=(self.k["key_id"], self.k["key_secret"]), json=body))

    def check(self) -> dict[str, Any]:
        self._call("GET", "/v1/orders?count=1")              # a read that needs both keys
        return {"ok": True, "test": self.test}

    def create_order(self, amount: int, receipt: str, customer: dict, notes: dict, return_url: str,
                     split: list[dict] | None = None) -> dict[str, Any]:
        d = self._call("POST", "/v1/orders", {"amount": amount, "currency": "INR", "receipt": receipt[:40],
                                              "notes": {k: str(v)[:250] for k, v in notes.items()}})
        return {"gw_order": d["id"], "checkout": {"gateway": "razorpay", "key": self.k["key_id"], "order_id": d["id"],
                                                    "amount": amount, "currency": "INR",
                                                    "prefill": {"name": customer.get("name", ""), "email": customer.get("email", ""),
                                                                "contact": customer.get("phone", "")}}}

    def order_state(self, gw_order: str, receipt: str = "") -> dict[str, Any]:
        d = self._call("GET", f"/v1/orders/{gw_order}/payments")
        items = d.get("items") or []
        ok = [p for p in items if p.get("status") == "captured"]
        if ok:
            p = ok[0]
            return {"state": "paid", "payment_id": p["id"], "amount": int(p.get("amount") or 0), "method": p.get("method", "")}
        if items and all(p.get("status") == "failed" for p in items):
            return {"state": "failed", "payment_id": items[-1].get("id", ""), "amount": 0}
        return {"state": "pending"}

    def verify(self, headers: dict[str, str], raw: bytes) -> bool:
        sec = self.k.get("webhook_secret") or ""
        sig = headers.get("x-razorpay-signature") or ""
        if not sec or not sig:
            return False
        return hmac.compare_digest(hmac.new(sec.encode(), raw, hashlib.sha256).hexdigest(), sig)

    def events(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        ev, p = str(body.get("event") or ""), body.get("payload") or {}
        pay = ((p.get("payment") or {}).get("entity")) or {}
        out: list[dict[str, Any]] = []
        if ev in ("payment.captured", "order.paid"):
            out.append({"kind": "paid", "gw_order": pay.get("order_id") or ((p.get("order") or {}).get("entity") or {}).get("id", ""),
                        "payment_id": pay.get("id", ""), "amount": int(pay.get("amount") or 0), "method": pay.get("method", "")})
        elif ev == "payment.failed":
            out.append({"kind": "failed", "gw_order": pay.get("order_id", ""), "payment_id": pay.get("id", "")})
        elif ev in ("refund.processed", "refund.failed"):
            rf = ((p.get("refund") or {}).get("entity")) or {}
            out.append({"kind": "refund", "refund_id": rf.get("id", ""), "receipt": rf.get("receipt") or "",
                        "payment_id": rf.get("payment_id", ""), "status": "done" if ev == "refund.processed" else "failed"})
        elif ev == "payment_link.paid":
            lk = ((p.get("payment_link") or {}).get("entity")) or {}
            out.append({"kind": "link_paid", "link_id": lk.get("id", ""), "ref": lk.get("reference_id", ""),
                        "payment_id": pay.get("id", ""), "amount": int(pay.get("amount") or lk.get("amount_paid") or 0)})
        elif ev.startswith("subscription."):
            sb = ((p.get("subscription") or {}).get("entity")) or {}
            out.append({"kind": "sub", "sub_id": sb.get("id", ""), "status": ev.split(".", 1)[1],
                        "payment_id": pay.get("id", ""), "amount": int(pay.get("amount") or 0)})
        return out

    def refund(self, payment_id: str, gw_order: str, amount: int, number: str) -> dict[str, Any]:
        d = self._call("POST", f"/v1/payments/{payment_id}/refund", {"amount": amount, "speed": "normal", "receipt": number})
        return {"refund_id": d.get("id", ""), "status": "done" if d.get("status") == "processed" else "pending"}

    def refund_state(self, payment_id: str, gw_order: str, number: str) -> dict[str, Any]:
        d = self._call("GET", f"/v1/payments/{payment_id}/refunds")
        for f in d.get("items") or []:
            if f.get("receipt") == number:
                st = f.get("status")
                return {"refund_id": f.get("id", ""), "status": "done" if st == "processed" else ("failed" if st == "failed" else "pending")}
        return {"status": "unknown"}

    def settlements(self) -> list[dict[str, Any]]:
        d = self._call("GET", "/v1/settlements?count=20")
        return [{"id": x.get("id"), "amount": int(x.get("amount") or 0), "fees": int(x.get("fees") or 0), "tax": int(x.get("tax") or 0),
                 "status": x.get("status"), "utr": x.get("utr") or "", "at": x.get("created_at")} for x in d.get("items") or []]

    def link(self, amount: int, purpose: str, customer: dict, ref: str) -> dict[str, Any]:
        d = self._call("POST", "/v1/payment_links", {
            "amount": amount, "currency": "INR", "description": purpose[:2048], "reference_id": ref[:40],
            "customer": {k: v for k, v in {"name": customer.get("name"), "contact": customer.get("phone"),
                                           "email": customer.get("email")}.items() if v},
            "notify": {"sms": False, "email": False}, "reminder_enable": False})
        return {"link_id": d.get("id", ""), "url": d.get("short_url", "")}

    def plan(self, name: str, amount: int, period: str) -> str:
        per = {"week": "weekly", "month": "monthly", "year": "yearly", "day": "daily"}[period]
        d = self._call("POST", "/v1/plans", {"period": per, "interval": 1, "item": {"name": name[:100], "amount": amount, "currency": "INR"}})
        return d["id"]

    def subscribe(self, plan_id: str, count: int, ref: str, customer: dict, return_url: str) -> dict[str, Any]:
        d = self._call("POST", "/v1/subscriptions", {"plan_id": plan_id, "total_count": count, "customer_notify": 0,
                                                     "notes": {"hoola_ref": ref}})
        return {"sub_id": d["id"], "checkout": {"gateway": "razorpay", "key": self.k["key_id"], "subscription_id": d["id"],
                                                 "prefill": {"name": customer.get("name", ""), "email": customer.get("email", ""),
                                                             "contact": customer.get("phone", "")}}}

    def cancel_sub(self, sub_id: str) -> None:
        self._call("POST", f"/v1/subscriptions/{sub_id}/cancel", {"cancel_at_cycle_end": 0})

    def transfer(self, payment_id: str, parts: list[dict[str, Any]]) -> list[str]:
        d = self._call("POST", f"/v1/payments/{payment_id}/transfers", {"transfers": [
            {"account": p["account"], "amount": p["amount"], "currency": "INR", "notes": {"hoola": p.get("note", "")[:250]}}
            for p in parts]})
        return [t.get("id", "") for t in d.get("items") or []]


# ---------------------------------------------------------------- Cashfree
class Cashfree:
    name = "cashfree"

    def __init__(self, keys: dict[str, str], test: bool = False):
        self.k = keys
        self.test = test or str(keys.get("client_id", "")).upper().startswith("TEST")
        default = "https://sandbox.cashfree.com" if self.test else "https://api.cashfree.com"
        self.base = (os.environ.get("PAY_CASHFREE_BASE") or default).rstrip("/")
        self.ver = os.environ.get("PAY_CASHFREE_VERSION") or "2025-01-01"

    def _h(self, idem: str = "") -> dict[str, str]:
        h = {"x-client-id": self.k["client_id"], "x-client-secret": self.k["client_secret"], "x-api-version": self.ver}
        if idem:
            h["x-idempotency-key"] = idem
        return h

    def _call(self, method: str, path: str, body: dict | None = None, idem: str = "") -> dict[str, Any]:
        return _json(_req(method, self.base + path, headers=self._h(idem), json=body))

    def check(self) -> dict[str, Any]:
        try:
            self._call("GET", "/pg/orders/hoola-key-check")
        except GwError as e:
            if e.code == 401:
                raise
        return {"ok": True, "test": self.test}

    def create_order(self, amount: int, receipt: str, customer: dict, notes: dict, return_url: str,
                     split: list[dict] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "order_id": receipt[:45], "order_amount": round(amount / 100, 2), "order_currency": "INR",
            "customer_details": {"customer_id": (customer.get("id") or "guest")[:50], "customer_phone": customer.get("phone") or "9999999999",
                                 "customer_name": customer.get("name", "")[:100], "customer_email": customer.get("email") or None},
            "order_meta": {"return_url": return_url}, "order_tags": {k: str(v)[:250] for k, v in list(notes.items())[:10]}}
        body["customer_details"] = {k: v for k, v in body["customer_details"].items() if v}
        if split:
            body["order_splits"] = [{"vendor_id": p["account"], "amount": round(p["amount"] / 100, 2)} for p in split]
        d = self._call("POST", "/pg/orders", body, idem=receipt)
        return {"gw_order": d.get("order_id") or receipt, "checkout": {"gateway": "cashfree", "session": d.get("payment_session_id", ""),
                                                                         "mode": "sandbox" if self.test else "production"}}

    def order_state(self, gw_order: str, receipt: str = "") -> dict[str, Any]:
        d = self._call("GET", f"/pg/orders/{gw_order}/payments")
        items = d.get("items") if "items" in d else d
        items = items if isinstance(items, list) else []
        ok = [p for p in items if p.get("payment_status") == "SUCCESS"]
        if ok:
            p = ok[0]
            return {"state": "paid", "payment_id": str(p.get("cf_payment_id", "")), "amount": paise(p.get("payment_amount") or 0),
                    "method": str(p.get("payment_group", ""))}
        if items and all(p.get("payment_status") in ("FAILED", "USER_DROPPED", "CANCELLED") for p in items):
            return {"state": "failed", "payment_id": str(items[-1].get("cf_payment_id", "")), "amount": 0}
        return {"state": "pending"}

    def verify(self, headers: dict[str, str], raw: bytes) -> bool:
        sig, ts = headers.get("x-webhook-signature") or "", headers.get("x-webhook-timestamp") or ""
        if not sig or not ts:
            return False
        mac = base64.b64encode(hmac.new(self.k["client_secret"].encode(), ts.encode() + raw, hashlib.sha256).digest()).decode()
        return hmac.compare_digest(mac, sig)

    def events(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        t, d = str(body.get("type") or ""), body.get("data") or {}
        order, pay = d.get("order") or {}, d.get("payment") or {}
        if t.startswith("PAYMENT_SUCCESS"):
            return [{"kind": "paid", "gw_order": order.get("order_id", ""), "payment_id": str(pay.get("cf_payment_id", "")),
                     "amount": paise(pay.get("payment_amount") or 0), "method": str(pay.get("payment_group", ""))}]
        if t.startswith("PAYMENT_FAILED") or t.startswith("PAYMENT_USER_DROPPED"):
            return [{"kind": "failed", "gw_order": order.get("order_id", ""), "payment_id": str(pay.get("cf_payment_id", ""))}]
        if t.startswith("REFUND"):
            rf = d.get("refund") or {}
            st = str(rf.get("refund_status") or "")
            return [{"kind": "refund", "refund_id": str(rf.get("cf_refund_id", "")), "receipt": rf.get("refund_id", ""),
                     "gw_order": rf.get("order_id", ""), "status": "done" if st == "SUCCESS" else ("failed" if st in ("CANCELLED", "FAILED") else "pending")}]
        if t.startswith("PAYMENT_LINK"):
            return [{"kind": "link_paid", "link_id": d.get("link_id", ""), "ref": d.get("link_id", ""),
                     "payment_id": str((d.get("order") or {}).get("transaction_id", "")), "amount": paise(d.get("link_amount_paid") or 0)}] \
                if str(d.get("link_status")) == "PAID" else []
        if t.startswith("SUBSCRIPTION"):
            s = d.get("subscription_details") or d
            st = str(s.get("subscription_status") or "").lower()
            mp = {"active": "activated", "cancelled": "cancelled", "on_hold": "halted", "completed": "completed"}
            return [{"kind": "sub", "sub_id": s.get("subscription_id", ""), "status": mp.get(st, st or "pending"),
                     "payment_id": str((d.get("payment_details") or {}).get("cf_payment_id", "")),
                     "amount": paise((d.get("payment_details") or {}).get("payment_amount") or 0)}]
        return []

    def refund(self, payment_id: str, gw_order: str, amount: int, number: str) -> dict[str, Any]:
        d = self._call("POST", f"/pg/orders/{gw_order}/refunds", {"refund_amount": round(amount / 100, 2), "refund_id": number,
                                                                   "refund_speed": "STANDARD"}, idem=number)
        st = str(d.get("refund_status") or "")
        return {"refund_id": str(d.get("cf_refund_id", "")), "status": "done" if st == "SUCCESS" else "pending"}

    def refund_state(self, payment_id: str, gw_order: str, number: str) -> dict[str, Any]:
        d = self._call("GET", f"/pg/orders/{gw_order}/refunds/{number}")
        st = str(d.get("refund_status") or "")
        return {"refund_id": str(d.get("cf_refund_id", "")), "status": "done" if st == "SUCCESS" else ("failed" if st in ("CANCELLED", "FAILED") else "pending")}

    def settlements(self) -> list[dict[str, Any]]:
        end = time.strftime("%Y-%m-%dT23:59:59Z", time.gmtime())
        start = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() - 30 * 86400))
        d = self._call("POST", "/pg/settlements", {"pagination": {"limit": 20}, "filters": {"start_date": start, "end_date": end}})
        return [{"id": str(x.get("cf_settlement_id", "")), "amount": paise(x.get("amount_settled") or 0),
                 "fees": paise(x.get("service_charge") or 0), "tax": paise(x.get("service_tax") or 0),
                 "status": x.get("status"), "utr": x.get("settlement_utr") or "", "at": x.get("settlement_date")}
                for x in d.get("data") or []]

    def link(self, amount: int, purpose: str, customer: dict, ref: str) -> dict[str, Any]:
        d = self._call("POST", "/pg/links", {"link_id": ref[:50], "link_amount": round(amount / 100, 2), "link_currency": "INR",
                                             "link_purpose": purpose[:500],
                                             "customer_details": {k: v for k, v in {"customer_phone": customer.get("phone") or "9999999999",
                                                                                     "customer_name": customer.get("name"),
                                                                                     "customer_email": customer.get("email")}.items() if v},
                                             "link_notify": {"send_sms": False, "send_email": False}}, idem=ref)
        return {"link_id": d.get("link_id", ref), "url": d.get("link_url", "")}

    def plan(self, name: str, amount: int, period: str) -> str:
        pid = "hoola_" + hashlib.sha1(f"{name}{amount}{period}{time.time()}".encode()).hexdigest()[:16]
        self._call("POST", "/pg/plans", {"plan_id": pid, "plan_name": name[:100], "plan_type": "PERIODIC", "plan_currency": "INR",
                                         "plan_recurring_amount": round(amount / 100, 2), "plan_max_amount": round(amount / 100, 2),
                                         "plan_intervals": 1, "plan_interval_type": period.upper()})
        return pid

    def subscribe(self, plan_id: str, count: int, ref: str, customer: dict, return_url: str) -> dict[str, Any]:
        d = self._call("POST", "/pg/subscriptions", {
            "subscription_id": ref[:50],
            "customer_details": {k: v for k, v in {"customer_phone": customer.get("phone") or "9999999999",
                                                    "customer_name": customer.get("name"), "customer_email": customer.get("email") or "na@example.com"}.items() if v},
            "plan_details": {"plan_id": plan_id}, "subscription_meta": {"return_url": return_url}}, idem=ref)
        return {"sub_id": d.get("subscription_id", ref), "checkout": {"gateway": "cashfree", "subs_session": d.get("subscription_session_id", ""),
                                                                        "mode": "sandbox" if self.test else "production"}}

    def cancel_sub(self, sub_id: str) -> None:
        self._call("POST", f"/pg/subscriptions/{sub_id}/manage", {"subscription_id": sub_id, "action": "CANCEL"})

    def transfer(self, payment_id: str, parts: list[dict[str, Any]]) -> list[str]:
        return []                                     # Easy Split rides on the order itself (order_splits)


# ---------------------------------------------------------------- PhonePe PG (Standard Checkout v2)
class PhonePe:
    name = "phonepe"
    _tok: dict[str, tuple[str, float]] = {}

    def __init__(self, keys: dict[str, str], test: bool = False):
        self.k = keys
        self.test = test
        self.base = (os.environ.get("PAY_PHONEPE_BASE") or
                     ("https://api-preprod.phonepe.com/apis/pg-sandbox" if test else "https://api.phonepe.com/apis/pg")).rstrip("/")
        self.auth = (os.environ.get("PAY_PHONEPE_AUTH") or
                     ("https://api-preprod.phonepe.com/apis/pg-sandbox" if test else "https://api.phonepe.com/apis/identity-manager")).rstrip("/")

    def _token(self) -> str:
        hit = self._tok.get(self.k["client_id"])
        if hit and hit[1] > time.time() + 60:
            return hit[0]
        d = _json(_req("POST", self.auth + "/v1/oauth/token", data={
            "client_id": self.k["client_id"], "client_version": self.k.get("client_version") or "1",
            "client_secret": self.k["client_secret"], "grant_type": "client_credentials"}))
        tok = d.get("access_token", "")
        if not tok:
            raise GwError("PhonePe ne token nahi diya.", 401)
        self._tok[self.k["client_id"]] = (tok, float(d.get("expires_at") or (time.time() + 600)))
        return tok

    def _call(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        return _json(_req(method, self.base + path, headers={"Authorization": "O-Bearer " + self._token()}, json=body))

    def check(self) -> dict[str, Any]:
        self._token()
        return {"ok": True, "test": self.test}

    def create_order(self, amount: int, receipt: str, customer: dict, notes: dict, return_url: str,
                     split: list[dict] | None = None) -> dict[str, Any]:
        d = self._call("POST", "/checkout/v2/pay", {"merchantOrderId": receipt[:63], "amount": amount, "expireAfter": 1800,
                                                   "paymentFlow": {"type": "PG_CHECKOUT", "merchantUrls": {"redirectUrl": return_url}}})
        return {"gw_order": receipt[:63], "checkout": {"gateway": "phonepe", "redirect": d.get("redirectUrl", "")}}

    def order_state(self, gw_order: str, receipt: str = "") -> dict[str, Any]:
        d = self._call("GET", f"/checkout/v2/order/{gw_order}/status")
        st = str(d.get("state") or "")
        det = (d.get("paymentDetails") or [{}])[-1] if d.get("paymentDetails") else {}
        if st == "COMPLETED":
            return {"state": "paid", "payment_id": det.get("transactionId", gw_order), "amount": int(d.get("amount") or 0),
                    "method": det.get("paymentMode", "")}
        if st == "FAILED":
            return {"state": "failed", "payment_id": det.get("transactionId", ""), "amount": 0}
        return {"state": "pending"}

    def verify(self, headers: dict[str, str], raw: bytes) -> bool:
        want = hashlib.sha256(f"{self.k.get('webhook_user', '')}:{self.k.get('webhook_password', '')}".encode()).hexdigest()
        got = (headers.get("authorization") or "").strip()
        return bool(self.k.get("webhook_user")) and hmac.compare_digest(want, got)

    def events(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        ev, p = str(body.get("event") or ""), body.get("payload") or {}
        if ev == "checkout.order.completed":
            return [{"kind": "paid", "gw_order": p.get("merchantOrderId", ""), "payment_id": ((p.get("paymentDetails") or [{}])[-1]).get("transactionId", ""),
                     "amount": int(p.get("amount") or 0), "method": ""}]
        if ev == "checkout.order.failed":
            return [{"kind": "failed", "gw_order": p.get("merchantOrderId", ""), "payment_id": ""}]
        if ev.startswith("pg.refund."):
            return [{"kind": "refund", "refund_id": p.get("refundId", ""), "receipt": p.get("merchantRefundId", ""),
                     "status": "done" if p.get("state") == "COMPLETED" else ("failed" if p.get("state") == "FAILED" else "pending")}]
        return []

    def refund(self, payment_id: str, gw_order: str, amount: int, number: str) -> dict[str, Any]:
        d = self._call("POST", "/payments/v2/refund", {"merchantRefundId": number, "originalMerchantOrderId": gw_order, "amount": amount})
        return {"refund_id": d.get("refundId", ""), "status": "done" if d.get("state") == "COMPLETED" else "pending"}

    def refund_state(self, payment_id: str, gw_order: str, number: str) -> dict[str, Any]:
        d = self._call("GET", f"/payments/v2/refund/{number}/status")
        st = d.get("state")
        return {"refund_id": d.get("refundId", ""), "status": "done" if st == "COMPLETED" else ("failed" if st == "FAILED" else "pending")}

    def settlements(self) -> list[dict[str, Any]]:
        raise GwError("PhonePe settlements Hoola se nahi dikhte - PhonePe Business dashboard dekhiye.", 400)

    def link(self, *a, **k):
        raise GwError("PhonePe payment links Hoola se nahi banate.", 400)

    def plan(self, *a, **k):
        raise GwError("PhonePe subscriptions Hoola se nahi banate.", 400)

    subscribe = plan
    cancel_sub = plan

    def transfer(self, payment_id: str, parts: list[dict[str, Any]]) -> list[str]:
        raise GwError("PhonePe split payouts Hoola se nahi.", 400)


def client(gateway: str, keys: dict[str, str], test: bool = False):
    if gateway == "razorpay":
        return Razorpay(keys, test)
    if gateway == "cashfree":
        return Cashfree(keys, test)
    if gateway == "phonepe":
        return PhonePe(keys, test)
    raise GwError("Gateway: razorpay | cashfree | phonepe.", 400)


def body_json(raw: bytes) -> dict[str, Any]:
    try:
        d = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return {}
    return d if isinstance(d, dict) else {}
