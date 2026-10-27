"""E-way bill clients behind one interface.

Default = `Manual`: Hoola builds the NIC bulk-upload JSON (same fields as the API) and the portal steps; she uploads it on
ewaybillgst.gov.in herself (login + OTP are hers) or lets the Computer Operator fill it (OTP / CAPTCHA confirm hers), then tells
Hoola the EWB number. `Gsp` = an authorised GST Suvidha Provider's e-way bill API with HER API user and HER GSP keys (typed only
in the app, sealed with the bazar vault). Every call here happens only after her tap on a `logistics_ewb` card (service.decide_ewb).
"""
from __future__ import annotations

import json
from typing import Any

import httpx

_TRANSPORT: httpx.BaseTransport | None = None


class EwbError(Exception):
    pass


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


def _http(method: str, url: str, **kw) -> httpx.Response:
    if not url.startswith("https://"):
        raise EwbError("GSP ka address https:// se shuru hona chahiye.")
    try:
        with httpx.Client(timeout=40, transport=_TRANSPORT) as c:
            return c.request(method, url, **kw)
    except httpx.HTTPError as e:
        raise EwbError(f"GSP tak nahi pahunch paya ({e.__class__.__name__}).")


BULK_VERSION = "1.0.0621"   # NIC bulk tool JSON version; if the portal asks for a newer one, its own Excel utility shows it


def bulk_json(bills: list[dict]) -> str:
    return json.dumps({"version": BULK_VERSION, "billLists": bills}, ensure_ascii=False, indent=1)


PORTAL_STEPS = {
    "generate": ["ewaybillgst.gov.in (ya ewaybill2.gst.gov.in) par apne GSTIN se login (OTP aapka)",
                 "e-Waybill > Bulk Generation > upar wali JSON file chuniye > Upload > Generate",
                 "Ya: e-Waybill > Generate New: wahi details bhariye (Part A + Part B gaadi no.)",
                 "Bana EWB number aur 'Valid Upto' Hoola ko bataiye (ya EWB ki PDF / photo bhejiye)"],
    "part_b": ["Portal > e-Waybill > Update Vehicle No: EWB number daaliye",
               "Nayi gaadi no., badalne ki wajah, kahan se (shehar + rajya) bhariye > Submit",
               "Hoola ko bataiye 'Part B update ho gaya'"],
    "extend": ["Portal > e-Waybill > Extend Validity (khatam hone se 8 ghante pehle se 8 ghante baad tak)",
               "EWB number, wajah, abhi kahan hai (PIN), baaki doori bhariye > Submit",
               "Naya 'Valid Upto' Hoola ko bataiye"],
    "consolidated": ["Portal > Consolidated EWB > Generate New: saare EWB number + gaadi no. daaliye",
                     "Bana CEWB number Hoola ko bataiye"],
}


class Client:
    name = "manual"
    needs: tuple[str, ...] = ()

    def __init__(self, creds: dict[str, Any] | None = None):
        self.creds = creds or {}

    def run(self, kind: str, payload: dict) -> dict:
        raise NotImplementedError


class Manual(Client):
    name = "manual"

    def run(self, kind: str, payload: dict) -> dict:
        return {"mode": "manual", "steps": PORTAL_STEPS.get(kind, []),
                "json": bulk_json([payload]) if kind == "generate" else json.dumps(payload, ensure_ascii=False, indent=1)}


class Gsp(Client):
    """NIC e-way bill API as passed through by her GSP (actions GENEWAYBILL / VEHEWB / EXTENDVALIDITY / GENCEWB).
    Paths and header names follow the NIC API v1.03 spec most GSPs expose; her GSP's own docs win (auth_path / api_path)."""
    name = "gsp"
    needs = ("base_url", "client_id", "client_secret", "gstin", "username", "password")
    ACTIONS = {"generate": "GENEWAYBILL", "part_b": "VEHEWB", "extend": "EXTENDVALIDITY", "consolidated": "GENCEWB"}

    def _base(self) -> str:
        return str(self.creds.get("base_url") or "").rstrip("/")

    def _headers(self) -> dict:
        c = self.creds
        return {"client_id": str(c.get("client_id", "")), "client_secret": str(c.get("client_secret", "")),
                "gstin": str(c.get("gstin", "")), "Content-Type": "application/json"}

    def _token(self) -> str:
        c = self.creds
        r = _http("POST", self._base() + (c.get("auth_path") or "/ewaybillapi/v1.03/auth"), headers=self._headers(),
                  json={"action": "ACCESSTOKEN", "username": c.get("username", ""), "password": c.get("password", "")})
        try:
            d = r.json()
        except ValueError:
            d = {}
        tok = d.get("authtoken") or (d.get("data") or {}).get("authtoken") if isinstance(d, dict) else ""
        if r.status_code >= 400 or not tok:
            raise EwbError("GSP ne login nahi diya: API user / password / GSP keys dekhiye (app mein).")
        return str(tok)

    def run(self, kind: str, payload: dict) -> dict:
        missing = [k for k in self.needs if not self.creds.get(k)]
        if missing:
            raise EwbError("GSP ki details adhuri: " + ", ".join(missing))
        tok = self._token()
        h = {**self._headers(), "authtoken": tok, "username": str(self.creds.get("username", ""))}
        r = _http("POST", self._base() + (self.creds.get("api_path") or "/ewaybillapi/v1.03/ewayapi"), headers=h,
                  json={"action": self.ACTIONS[kind], **payload})
        try:
            d = r.json()
        except ValueError:
            d = {}
        data = d.get("data") if isinstance(d, dict) and isinstance(d.get("data"), dict) else d
        if r.status_code >= 400 or not isinstance(data, dict) or str(d.get("status", "1")) in ("0", "false") or d.get("error"):
            err = (d.get("error") or {}) if isinstance(d, dict) else {}
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise EwbError("Portal ne mana kiya: " + str(msg or r.status_code)[:200])
        return {"mode": "gsp", "ewb_no": str(data.get("ewayBillNo") or data.get("cEwbNo") or ""),
                "ewb_date": str(data.get("ewayBillDate") or data.get("cEwbDate") or data.get("vehUpdDate") or ""),
                "valid_upto": str(data.get("validUpto") or ""), "raw": {k: data[k] for k in list(data)[:8]}}


PROVIDERS = {"manual": Manual, "gsp": Gsp}


def get(name: str, creds: dict | None = None) -> Client:
    return PROVIDERS.get(name or "manual", Manual)(creds)
