"""Her payment gateway, for refunds to the ORIGINAL payment. Decision (23 Oct 2026):

Default = she refunds herself. After her fingerprint Haan on the refund card, Hoola shows the exact amount, the payment
id and her gateway's dashboard page; she presses Refund there and tells Hoola the reference (or Hoola reads it back).

With her own gateway key joined in the app (sealed, never shown to the model):
- READ-ONLY status check: Razorpay GET /v1/payments/{payment_id}/refunds (Basic auth key_id:key_secret; refund status
  pending | processed | failed, acquirer_data.arn / rrn), Cashfree GET /pg/orders/{order_id}/refunds/{refund_id}
  (x-client-id / x-client-secret / x-api-version; refund_status SUCCESS | PENDING | ...; refund_arn). A refund she made in
  the dashboard is matched by our refund number (Razorpay `receipt`, Cashfree `refund_id`) and marked done with its ARN.
- SENDING through the API exists (Razorpay POST /v1/payments/{id}/refund {amount (paise), speed normal, receipt};
  Cashfree POST /pg/orders/{order_id}/refunds {refund_amount, refund_id, refund_speed STANDARD} with x-idempotency-key)
  but is OFF unless the server sets WAPSI_PG_EXECUTE=true, and even then it runs only from a SECOND fingerprint-signed
  tap of hers on an already approved refund (same refund number = idempotent at the gateway, never twice).
- PhonePe PG: dashboard steps only (no key joined here).
Sources: https://razorpay.com/docs/api/refunds/create-instant/ (normal refunds 5-7 working days; `receipt` acts as the
idempotency key), https://www.cashfree.com/docs/api-reference/payments/latest/refunds/create (refunds within 6 months,
x-api-version 2026-01-01, x-idempotency-key)."""
from __future__ import annotations

import os
from typing import Any

import httpx


class PgError(Exception):
    pass


_TRANSPORT: httpx.BaseTransport | None = None


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def execute_allowed() -> bool:
    return (os.environ.get("WAPSI_PG_EXECUTE") or "").lower() in ("1", "true", "yes")


DASHBOARD = {
    "razorpay": ("https://dashboard.razorpay.com/app/payments/{payment_id}", "Razorpay dashboard > Payments > yeh payment > Issue Refund"),
    "cashfree": ("https://merchant.cashfree.com/merchants/pg/transactions", "Cashfree > Payment Gateway > Transactions > order dhoondhiye > Refund"),
    "phonepe": ("https://business.phonepe.com/", "PhonePe Business dashboard > Transactions > yeh payment > Refund"),
    "paytm": ("https://dashboard.paytm.com/", "Paytm Business dashboard > Payments > yeh payment > Refund"),
}


def _base(gw: str) -> str:
    if gw == "razorpay":
        return (os.environ.get("WAPSI_RAZORPAY_BASE") or "https://api.razorpay.com").rstrip("/")
    return (os.environ.get("WAPSI_CASHFREE_BASE") or "https://api.cashfree.com").rstrip("/")


def _req(method: str, url: str, **kw) -> httpx.Response:
    try:
        with httpx.Client(timeout=30, transport=_TRANSPORT) as c:
            return c.request(method, url, **kw)
    except httpx.HTTPError as e:
        raise PgError(f"Gateway tak nahi pahunch paya ({e.__class__.__name__}).")


def _cf_headers(creds: dict) -> dict:
    return {"x-client-id": creds.get("key_id", ""), "x-client-secret": creds.get("key_secret", ""), "x-api-version": "2026-01-01",
            "Content-Type": "application/json"}


def prepare(gateway: str, payment_id: str, order_id: str, amount: float, number: str) -> dict[str, Any]:
    """What she needs to refund in her own dashboard: link, the exact amount, the ids, the reference to type."""
    gw = gateway if gateway in DASHBOARD else ""
    out = {"gateway": gw, "amount": round(amount, 2), "payment_id": payment_id, "order_id": order_id, "reference": number}
    if gw:
        url, steps = DASHBOARD[gw]
        out["dashboard"] = url.format(payment_id=payment_id or "")
        out["steps"] = [steps, f"Amount: ₹{amount:,.2f} (poora nahi, sirf itna)", f"Note / receipt mein likhiye: {number}",
                        "Refund ka reference (ARN / RRN / UTR) Hoola ko bataiye ya 'Jaanch karo' dabaiye"]
        if gw == "razorpay":
            out["api_request"] = {"POST": f"/v1/payments/{payment_id}/refund", "amount": int(round(amount * 100)), "speed": "normal", "receipt": number}
        if gw == "cashfree":
            out["api_request"] = {"POST": f"/pg/orders/{order_id}/refunds", "refund_amount": round(amount, 2), "refund_id": number,
                                  "refund_speed": "STANDARD"}
    return out


def status(gateway: str, creds: dict, payment_id: str, order_id: str, number: str) -> dict[str, Any]:
    """Read-only: has a refund with our number been made at her gateway? {found, state done|pending|failed, ref, amount}."""
    if gateway == "razorpay":
        if not payment_id:
            raise PgError("Razorpay payment id chahiye (pay_...).")
        r = _req("GET", f"{_base('razorpay')}/v1/payments/{payment_id}/refunds", auth=(creds.get("key_id", ""), creds.get("key_secret", "")))
        if r.status_code in (401, 403):
            raise PgError("Razorpay ne key mana ki (galat ya band).")
        if r.status_code >= 400:
            raise PgError(f"Razorpay: {r.status_code}")
        for it in (r.json() or {}).get("items") or []:
            if it.get("receipt") == number:
                st = {"processed": "done", "failed": "failed"}.get(str(it.get("status")), "pending")
                ad = it.get("acquirer_data") or {}
                return {"found": True, "state": st, "ref": str(ad.get("arn") or ad.get("rrn") or ad.get("utr") or it.get("id") or ""),
                        "amount": (it.get("amount") or 0) / 100, "gateway_id": it.get("id", "")}
        return {"found": False}
    if gateway == "cashfree":
        if not order_id:
            raise PgError("Cashfree order id chahiye.")
        r = _req("GET", f"{_base('cashfree')}/pg/orders/{order_id}/refunds/{number}", headers=_cf_headers(creds))
        if r.status_code == 404:
            return {"found": False}
        if r.status_code >= 400:
            raise PgError(f"Cashfree: {r.status_code}")
        d = r.json() or {}
        st = {"SUCCESS": "done", "CANCELLED": "failed", "REJECTED": "failed"}.get(str(d.get("refund_status")), "pending")
        return {"found": True, "state": st, "ref": str(d.get("refund_arn") or d.get("cf_refund_id") or ""), "amount": float(d.get("refund_amount") or 0),
                "gateway_id": str(d.get("cf_refund_id") or "")}
    raise PgError("Is gateway ki jaanch API se nahi hoti: dashboard mein dekhiye.")


def send(gateway: str, creds: dict, payment_id: str, order_id: str, amount: float, number: str) -> dict[str, Any]:
    """Only called from her second fingerprint tap on an approved refund, and only when WAPSI_PG_EXECUTE is on."""
    if not execute_allowed():
        raise PgError("Gateway se seedha refund is server par band hai: dashboard se kijiye.")
    if amount <= 0:
        raise PgError("Rakam galat.")
    if gateway == "razorpay":
        r = _req("POST", f"{_base('razorpay')}/v1/payments/{payment_id}/refund", auth=(creds.get("key_id", ""), creds.get("key_secret", "")),
                 json={"amount": int(round(amount * 100)), "speed": "normal", "receipt": number, "notes": {"hoola": number}})
        d = r.json() if r.content else {}
        if r.status_code >= 400:
            raise PgError("Razorpay: " + str(((d or {}).get("error") or {}).get("description") or r.status_code)[:200])
        st = {"processed": "done", "failed": "failed"}.get(str(d.get("status")), "pending")
        ad = d.get("acquirer_data") or {}
        return {"state": st, "ref": str(ad.get("arn") or ad.get("rrn") or d.get("id") or ""), "gateway_id": d.get("id", "")}
    if gateway == "cashfree":
        h = _cf_headers(creds) | {"x-idempotency-key": number}
        r = _req("POST", f"{_base('cashfree')}/pg/orders/{order_id}/refunds", headers=h,
                 json={"refund_amount": round(amount, 2), "refund_id": number, "refund_note": f"Hoola {number}"[:100], "refund_speed": "STANDARD"})
        d = r.json() if r.content else {}
        if r.status_code >= 400:
            raise PgError("Cashfree: " + str((d or {}).get("message") or r.status_code)[:200])
        st = {"SUCCESS": "done"}.get(str(d.get("refund_status")), "pending")
        return {"state": st, "ref": str(d.get("refund_arn") or d.get("cf_refund_id") or ""), "gateway_id": str(d.get("cf_refund_id") or "")}
    raise PgError("Is gateway se API refund nahi: dashboard se kijiye.")
