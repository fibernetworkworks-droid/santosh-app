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
    """The spec's names, or GSTN's own short names (lgnm / sts / rgdt...) when API Setu passes those through."""
    def g(*names):
        for n in names:
            v = data.get(n)
            if v not in (None, "", []):
                return v
        return ""
    status = str(g("status", "sts"))
    acts = g("natureBusinessActivities", "nba") or []
    return {"gstin": str(g("gstin")), "legal_name": str(g("legalName", "lgnm")),
            "trade_name": str(g("tradeName", "tradeNam")),
            "constitution": str(g("constitution", "ctb")), "status": status,
            "active": status.strip().lower() == "active",
            "registered_on": _iso(str(g("registrationDate", "rgdt"))),
            "cancelled_on": _iso(str(g("cancellationDate", "cxdt"))),
            "taxpayer_type": str(g("taxPayerType", "dty")),
            "centre_jurisdiction": str(g("centerJurisdiction", "ctj")),
            "state_jurisdiction": str(g("stateJurisdiction", "stj")),
            "activities": [str(a) for a in (acts if isinstance(acts, list) else [acts]) if a],
            "source": "API Setu (GSTN)"}


_REC_KEYS = ("gstin", "legalName", "lgnm", "tradeName", "tradeNam")
_WRAPS = ("data", "result", "results", "response", "taxpayer", "taxpayerDetails", "payload", "_list")


def record_in(data, depth: int = 0) -> dict:
    """The taxpayer record, whether bare (the spec) or wrapped one level or two in data / result / response / a list."""
    if isinstance(data, list):
        return record_in(data[0], depth + 1) if data and depth < 3 else {}
    if not isinstance(data, dict):
        return {}
    if any(data.get(k) for k in _REC_KEYS):
        return data
    if depth >= 3:
        return {}
    for k in _WRAPS:
        if k in data:
            got = record_in(data[k], depth + 1)
            if got:
                return got
    return {}


def shape_keys(data, prefix: str = "", depth: int = 0) -> list[str]:
    """Field names of a reply (nested as a.b) - never values."""
    out: list[str] = []
    if isinstance(data, list):
        return shape_keys(data[0], prefix + "[]", depth) if data else [prefix + "[]"] if prefix else []
    if not isinstance(data, dict):
        return []
    for k, v in list(data.items())[:20]:
        name = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, (dict, list)) and depth < 2 and v:
            out += shape_keys(v, name, depth + 1)
        else:
            out.append(name)
    return out[:30]


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
        data = {"_list": data} if isinstance(data, list) else {}
    rec = record_in(data)
    if r.status_code == 200 and rec:
        return rec if raw else _plain(rec)
    code = str(data.get("error") or data.get("errorCode") or data.get("code") or "").strip()
    said = str(data.get("errorDescription") or data.get("message") or data.get("msg") or "").strip()
    if r.status_code == 200:
        # v0.832 her live check: HTTP 200 with no record in the spec's shape - say what came back by its field names only
        code = code or "no_record"
        fields = ", ".join(shape_keys(data)) or "an empty body"
        raise ApiSetuError(code, f"API Setu accepted the keys (HTTP 200) but sent no taxpayer record for this GSTIN - the reply "
                                 f"held: {fields}" + (f" [API Setu said: {said[:160]}]" if said else ""), 200)
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
