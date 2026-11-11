"""v0.827 API Setu GSTN Tax Payer lookup - the government's own, free GSTIN check (docs/research/accounts/06_apisetu_gstn.md).

Spec: https://cf-media.api-setu.in/specfiles/gstn.yaml (GSTN Tax Payer API 1.0.0). ONE call:
    GET https://apisetu.gov.in/gstn/v1/taxpayers/{gstin}   headers X-APISETU-CLIENTID + X-APISETU-APIKEY
200 = gstin, legalName, constitution, registrationDate (DD/MM/YYYY), status, taxPayerType, centerJurisdiction,
stateJurisdiction, cancellationDate, natureBusinessActivities[]; errors = {error, errorDescription} (400 / 401 / 404 / 5xx).

Keys: APISETU_CLIENT_ID + APISETU_API_KEY in the VPS .env ONLY (her API Setu partner account), never in chat, never in a reply.
A GSTIN that fails the check digit is refused before any call. Read-only: nothing is written anywhere by a lookup.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..config import get_settings
from .wb import clean

_transport: httpx.BaseTransport | None = None     # tests plug in httpx.MockTransport

PLAIN = {
    "invalid_authentication": "API Setu did not accept the keys - check APISETU_CLIENT_ID and APISETU_API_KEY in the VPS .env "
                              "(copy both again from your app in the API Setu partner portal)",
    "invalid_authorization": "API Setu accepted the keys, but your API Setu app is not allowed to use the GSTN Tax Payer API yet - "
                             "in the API Setu partner portal open your app and subscribe it to 'GSTN Tax Payer API' (or wait "
                             "for that subscription to be approved)",
    "record_not_found": "GSTN has no taxpayer with this GSTIN",
    "invalid parameter": "API Setu refused the GSTIN as a bad value",
    "missing parameter": "API Setu said a value was missing",
}


class ApiSetuError(Exception):
    def __init__(self, code: str, message: str, status: int = 0):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def keys() -> tuple[str, str]:
    st = get_settings()
    return clean(st.apisetu_client_id), clean(st.apisetu_api_key)


def configured() -> bool:
    cid, key = keys()
    return bool(cid and key)


OFFICIAL = "https://apisetu.gov.in/gstn/v1"


def base() -> str:
    """APISETU_GSTN_BASE if set; else the owner's data.gov.in relay worker (v0.828: the same worker forwards API Setu - NIC
    drops connections from cloud servers for both); else apisetu.gov.in itself."""
    st = get_settings()
    explicit = clean(st.apisetu_gstn_base)
    if explicit:
        return explicit.rstrip("/")
    relay = clean(getattr(st, "data_gov_in_base", "")).rstrip("/")
    if relay.startswith("https://"):
        return relay + "/gstn/v1"
    return OFFICIAL


def via_relay() -> bool:
    return not base().startswith("https://apisetu.gov.in/")


def _iso(d: str) -> str:
    try:
        return datetime.strptime((d or "").strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return ""


def _plain(data: dict[str, Any]) -> dict[str, Any]:
    status = str(data.get("status") or "")
    return {"gstin": str(data.get("gstin") or ""), "legal_name": str(data.get("legalName") or ""),
            "constitution": str(data.get("constitution") or ""), "status": status,
            "active": status.strip().lower() == "active",
            "registered_on": _iso(str(data.get("registrationDate") or "")),
            "cancelled_on": _iso(str(data.get("cancellationDate") or "")),
            "taxpayer_type": str(data.get("taxPayerType") or ""),
            "centre_jurisdiction": str(data.get("centerJurisdiction") or ""),
            "state_jurisdiction": str(data.get("stateJurisdiction") or ""),
            "activities": [str(a) for a in (data.get("natureBusinessActivities") or []) if a],
            "source": "API Setu (GSTN)"}


def taxpayer(gstin: str, *, raw: bool = False) -> dict[str, Any]:
    """One taxpayer's public GST record. Raises ApiSetuError with a plain line on every failure."""
    from ..appmaker.gst import valid_gstin
    g = (gstin or "").strip().upper()
    if not valid_gstin(g):
        raise ApiSetuError("bad_gstin", f"'{g[:20]}' is not a valid GSTIN (shape or check digit) - nothing was sent")
    cid, key = keys()
    if not (cid and key):
        raise ApiSetuError("not_configured", "API Setu is not set up on this server - the owner adds APISETU_CLIENT_ID and "
                                             "APISETU_API_KEY to the VPS .env (never in chat)")
    st = get_settings()
    try:
        with httpx.Client(timeout=float(st.apisetu_timeout_s or 20), transport=_transport, follow_redirects=False) as c:
            r = c.get(f"{base()}/taxpayers/{g}", headers={"X-APISETU-CLIENTID": cid, "X-APISETU-APIKEY": key,
                                                          "Accept": "application/json"})
    except httpx.HTTPError as e:
        why = f"({type(e).__name__})"
        if not via_relay() and isinstance(e, (httpx.TimeoutException, httpx.ConnectError)):
            why += (" - apisetu.gov.in answers elsewhere but drops this server, like data.gov.in does. Paste the updated "
                    "deploy/datagov-relay/worker.js into your Cloudflare relay worker and set DATA_GOV_IN_BASE (or "
                    "APISETU_GSTN_BASE=<worker>/gstn/v1) in the VPS .env")
        raise ApiSetuError("unreachable", f"API Setu could not be reached from this server {why}") from None
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if r.status_code == 200 and data.get("gstin"):
        return data if raw else _plain(data)
    code = str(data.get("error") or "").strip()
    said = str(data.get("errorDescription") or "").strip()
    if r.status_code == 404 and not code:
        code = "record_not_found" if data else "no_such_path"
    if r.status_code >= 500:
        code = code or "unavailable"
    no_path = (f"your relay worker ({base()}) does not forward API Setu yet - paste the updated deploy/datagov-relay/worker.js "
               "into it" if via_relay() else f"API Setu has no such address ({base()}) - check APISETU_GSTN_BASE")
    msg = PLAIN.get(code) or {"no_such_path": no_path,
                              "unavailable": "API Setu / GSTN is down or busy right now - try again later"}.get(code) \
        or f"API Setu answered HTTP {r.status_code}"
    if said and said.lower() not in msg.lower():
        msg += f" [API Setu said: {said[:160]}]"
    raise ApiSetuError(code or f"http_{r.status_code}", msg, r.status_code)
