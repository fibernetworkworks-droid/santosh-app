"""v0.999.166 open banking: one interface, a licensed partner per region behind it (plan D4).

Hoola is not a regulated account-information provider. It reaches a bank through a partner that holds the licence, under
the owner's contract with that partner. Every partner here:
  start(...)   -> {url, ext_ref}       she opens the url, signs in at HER bank's own page and approves read-only access
  status(...)  -> {status, accounts, expires_at, token}
  fetch(...)   -> {rows, cursor}       bank lines as {day, amount (+ in / - out), narration, ref, currency}
  revoke(...)                           ends the consent at the partner
No bank password, PIN or OTP ever passes through Hoola. Partner keys live only in the VPS .env (config.py); a partner is
offered only when its keys are set AND its name is in OPEN_BANKING_ACK (the owner read and signed its terms).

The request and answer shapes are written from each partner's public API reference; none has answered a live call from
this server yet (NOT VERIFIED). Every network call goes through one seam, `_http`, so tests run with no network."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable

import httpx

# Which partner serves which country (plan D4). A country not here is served by bank files, statement mail and upload.
REGIONS: dict[str, list[str]] = {
    "setu_aa": ["IN"],
    "gocardless": ["GB", "IE", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "PT", "FI", "SE", "DK", "NO", "PL", "CZ", "SK", "SI", "HU",
                   "RO", "BG", "HR", "GR", "CY", "MT", "LU", "LT", "LV", "EE", "IS", "LI"],
    "plaid": ["US", "CA"],
}
# Named in the plan for later; not built (said as such on the page).
LATER: dict[str, tuple[str, list[str]]] = {
    "basiq": ("Basiq (Consumer Data Right)", ["AU"]),
    "belvo": ("Belvo", ["BR", "MX", "CO"]),
    "lean": ("Lean Technologies", ["AE", "SA"]),
    "mono": ("Mono", ["NG"]),
    "stitch": ("Stitch", ["ZA"]),
}
NAMES = {"setu_aa": "Account Aggregator (through Setu)", "gocardless": "GoCardless Bank Account Data", "plaid": "Plaid"}
NEEDS = {"setu_aa": "mobile", "gocardless": "bank", "plaid": ""}     # what she gives before the bank page: her mobile / her bank


class BankLinkError(ValueError):
    pass


_http: Callable[..., httpx.Response] | None = None     # tests replace this: (method, url, **kw) -> httpx.Response


def _call(method: str, url: str, **kw: Any) -> httpx.Response:
    if _http is not None:
        return _http(method, url, **kw)
    with httpx.Client(timeout=30) as c:
        return c.request(method, url, **kw)


def _json(r: httpx.Response, what: str) -> dict[str, Any]:
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400:
        msg = ""
        if isinstance(data, dict):
            err = data.get("error")
            msg = str(data.get("error_message") or data.get("detail") or data.get("summary") or data.get("errorMsg")
                      or (err.get("message") if isinstance(err, dict) else err) or "")
        raise BankLinkError(f"{what}: the partner answered {r.status_code}{(' - ' + msg[:200]) if msg else ''}.")
    return data if isinstance(data, dict) else {"_list": data}


def _cfg():
    from ...config import get_settings
    return get_settings()


def _ack() -> set[str]:
    return {x.strip().lower() for x in str(_cfg().open_banking_ack or "").split(",") if x.strip()}


def keys_set(partner: str) -> bool:
    c = _cfg()
    return {"setu_aa": bool(c.setu_aa_client_id and c.setu_aa_client_secret and c.setu_aa_product_instance),
            "gocardless": bool(c.gocardless_secret_id and c.gocardless_secret_key),
            "plaid": bool(c.plaid_client_id and c.plaid_secret)}.get(partner, False)


def available(partner: str) -> bool:
    return partner in PARTNERS and keys_set(partner) and partner in _ack()


def for_country(cc: str) -> dict[str, Any]:
    """The open-banking route of one country: which partner, and whether this server can use it today."""
    cc = (cc or "").upper()
    for p, ccs in REGIONS.items():
        if cc in ccs:
            if available(p):
                state, why = "ready", ""
            elif not keys_set(p):
                state, why = "not_set_up", f"{NAMES[p]} is not set up on this server yet (the owner signs up with it and adds its keys)."
            else:
                state, why = "terms", f"{NAMES[p]} keys are set, but its terms are not marked as read (OPEN_BANKING_ACK)."
            return {"partner": p, "name": NAMES[p], "state": state, "why": why, "needs": NEEDS[p]}
    for p, (name, ccs) in LATER.items():
        if cc in ccs:
            return {"partner": p, "name": name, "state": "later", "needs": "",
                    "why": f"{name} is the planned partner for this country; it is not built yet. Bank files, statement mail and upload work today."}
    return {"partner": "", "name": "", "state": "none", "needs": "",
            "why": "No bank-connection partner covers this country yet. Bank files, statement mail and upload work everywhere."}


def _amt(v: Any) -> Decimal:
    try:
        return Decimal(str(v).replace(",", "").strip() or "0")
    except Exception:   # noqa: BLE001
        return Decimal("0")


def _iso(d: str) -> str:
    d = str(d or "")[:10]
    try:
        return date.fromisoformat(d).isoformat()
    except ValueError:
        return ""


# ---------------------------------------------------------------- GoCardless Bank Account Data (UK + EU/EEA)

class GoCardless:
    base = "https://bankaccountdata.gocardless.com/api/v2"
    _tok: tuple[float, str] = (0.0, "")

    def _token(self) -> str:
        import time
        if self._tok[1] and time.time() < self._tok[0]:
            return self._tok[1]
        c = _cfg()
        d = _json(_call("POST", f"{self.base}/token/new/", json={"secret_id": c.gocardless_secret_id, "secret_key": c.gocardless_secret_key}),
                  "GoCardless sign-in")
        GoCardless._tok = (time.time() + int(d.get("access_expires") or 3600) - 60, str(d.get("access") or ""))
        return GoCardless._tok[1]

    def _h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}", "accept": "application/json"}

    def banks(self, cc: str, q: str = "") -> list[dict[str, str]]:
        d = _json(_call("GET", f"{self.base}/institutions/", params={"country": cc.lower()}, headers=self._h()), "Bank list")
        rows = d.get("_list") or d.get("results") or []
        q = (q or "").lower()
        return [{"id": str(b.get("id")), "name": str(b.get("name"))} for b in rows if not q or q in str(b.get("name", "")).lower()][:60]

    def start(self, cc: str, bank: str, back: str, state: str, mobile: str = "") -> dict[str, Any]:
        if not bank:
            raise BankLinkError("Pick your bank first.")
        ag = _json(_call("POST", f"{self.base}/agreements/enduser/", headers=self._h(), json={
            "institution_id": bank, "max_historical_days": 90, "access_valid_for_days": 90,
            "access_scope": ["balances", "details", "transactions"]}), "Consent")
        rq = _json(_call("POST", f"{self.base}/requisitions/", headers=self._h(), json={
            "redirect": back, "institution_id": bank, "reference": state, "agreement": ag.get("id"), "user_language": "EN"}), "Bank link")
        return {"url": str(rq.get("link") or ""), "ext_ref": str(rq.get("id") or ""), "institution": bank,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()}

    def status(self, link: dict[str, Any]) -> dict[str, Any]:
        d = _json(_call("GET", f"{self.base}/requisitions/{link['ext_ref']}/", headers=self._h()), "Bank link")
        st = {"LN": "active", "EX": "expired", "RJ": "failed", "SU": "revoked"}.get(str(d.get("status")), "pending")
        accts = []
        if st == "active":
            for a in d.get("accounts") or []:
                det = _json(_call("GET", f"{self.base}/accounts/{a}/details/", headers=self._h()), "Account").get("account") or {}
                iban = str(det.get("iban") or det.get("bban") or "")
                accts.append({"ext_id": str(a), "name": str(det.get("name") or det.get("product") or "Bank account")[:80],
                              "masked": ("..." + iban[-4:]) if iban else "", "currency": str(det.get("currency") or "")})
        return {"status": st, "accounts": accts}

    def fetch(self, link: dict[str, Any], ext_id: str, since: str) -> dict[str, Any]:
        d = _json(_call("GET", f"{self.base}/accounts/{ext_id}/transactions/", headers=self._h(), params={"date_from": since}),
                  "Bank lines")
        rows = []
        for t in ((d.get("transactions") or {}).get("booked") or []):
            amt = t.get("transactionAmount") or {}
            nar = " ".join(str(x) for x in (t.get("creditorName") or t.get("debtorName"), t.get("remittanceInformationUnstructured"))
                           if x)
            rows.append({"day": _iso(t.get("bookingDate") or t.get("valueDate")), "amount": _amt(amt.get("amount")),
                         "narration": nar or str(t.get("additionalInformation") or ""), "currency": str(amt.get("currency") or ""),
                         "ref": str(t.get("transactionId") or t.get("internalTransactionId") or "")})
        return {"rows": rows, "cursor": ""}

    def revoke(self, link: dict[str, Any]) -> None:
        _call("DELETE", f"{self.base}/requisitions/{link['ext_ref']}/", headers=self._h())


# ---------------------------------------------------------------- Plaid (US + Canada), Hosted Link

class Plaid:
    def _base(self) -> str:
        return "https://production.plaid.com" if str(_cfg().plaid_env).lower() == "production" else "https://sandbox.plaid.com"

    def _p(self, path: str, body: dict[str, Any], what: str) -> dict[str, Any]:
        c = _cfg()
        return _json(_call("POST", self._base() + path, json={"client_id": c.plaid_client_id, "secret": c.plaid_secret, **body}), what)

    def start(self, cc: str, bank: str, back: str, state: str, mobile: str = "") -> dict[str, Any]:
        d = self._p("/link/token/create", {"user": {"client_user_id": state}, "client_name": "Hoola", "products": ["transactions"],
                                            "country_codes": [cc.upper()], "language": "en",
                                            "hosted_link": {"completion_redirect_uri": back}}, "Bank link")
        return {"url": str(d.get("hosted_link_url") or ""), "ext_ref": str(d.get("link_token") or ""), "institution": "",
                "expires_at": ""}

    def status(self, link: dict[str, Any]) -> dict[str, Any]:
        if link.get("token"):
            return {"status": "active", "accounts": link.get("accounts") or []}
        d = self._p("/link/token/get", {"link_token": link["ext_ref"]}, "Bank link")
        pub = ""
        for sess in d.get("link_sessions") or []:
            for r in ((sess.get("results") or {}).get("item_add_results") or []):
                pub = pub or str(r.get("public_token") or "")
        if not pub:
            return {"status": "pending", "accounts": []}
        tok = str(self._p("/item/public_token/exchange", {"public_token": pub}, "Bank link").get("access_token") or "")
        acc = self._p("/accounts/get", {"access_token": tok}, "Accounts")
        accts = [{"ext_id": str(a.get("account_id")), "name": str(a.get("name") or "Bank account")[:80],
                  "masked": ("..." + str(a.get("mask"))) if a.get("mask") else "",
                  "currency": str((a.get("balances") or {}).get("iso_currency_code") or "")} for a in acc.get("accounts") or []]
        inst = str((acc.get("item") or {}).get("institution_name") or (acc.get("item") or {}).get("institution_id") or "")
        return {"status": "active", "accounts": accts, "token": tok, "institution": inst}

    def fetch(self, link: dict[str, Any], ext_id: str, since: str) -> dict[str, Any]:
        cursor, rows = link.get("cursor") or "", []
        for _ in range(20):
            d = self._p("/transactions/sync", {"access_token": link["token"], **({"cursor": cursor} if cursor else {})}, "Bank lines")
            for t in d.get("added") or []:
                if ext_id and str(t.get("account_id")) != ext_id:
                    continue
                # Plaid: a positive amount is money OUT of the account
                rows.append({"day": _iso(t.get("date")), "amount": -_amt(t.get("amount")), "narration": str(t.get("name") or "")[:200],
                             "currency": str(t.get("iso_currency_code") or ""), "ref": str(t.get("transaction_id") or "")})
            cursor = str(d.get("next_cursor") or cursor)
            if not d.get("has_more"):
                break
        return {"rows": rows, "cursor": cursor}

    def revoke(self, link: dict[str, Any]) -> None:
        if link.get("token"):
            self._p("/item/remove", {"access_token": link["token"]}, "Disconnect")


# ---------------------------------------------------------------- Setu Account Aggregator (India)

class SetuAA:
    def _h(self) -> dict[str, str]:
        c = _cfg()
        return {"x-client-id": c.setu_aa_client_id, "x-client-secret": c.setu_aa_client_secret,
                "x-product-instance-id": c.setu_aa_product_instance, "Content-Type": "application/json"}

    def _b(self) -> str:
        return str(_cfg().setu_aa_base or "https://fiu-sandbox.setu.co").rstrip("/")

    def start(self, cc: str, bank: str, back: str, state: str, mobile: str = "") -> dict[str, Any]:
        mob = "".join(ch for ch in str(mobile or "") if ch.isdigit())[-10:]
        if len(mob) != 10:
            raise BankLinkError("Type the 10-digit mobile number your bank account uses. The Account Aggregator sends you its own code.")
        today = date.today()
        d = _json(_call("POST", f"{self._b()}/v2/consents", headers=self._h(), json={
            "consentDuration": {"unit": "MONTH", "value": "12"}, "vua": mob, "redirectUrl": back,
            "dataRange": {"from": (today - timedelta(days=365)).isoformat() + "T00:00:00Z", "to": today.isoformat() + "T23:59:59Z"},
            "context": [{"key": "accounttype", "value": "SAVINGS"}]}), "Consent")
        return {"url": str(d.get("url") or ""), "ext_ref": str(d.get("id") or ""), "institution": "",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()}

    def status(self, link: dict[str, Any]) -> dict[str, Any]:
        d = _json(_call("GET", f"{self._b()}/v2/consents/{link['ext_ref']}", headers=self._h()), "Consent")
        st = {"ACTIVE": "active", "EXPIRED": "expired", "REJECTED": "failed", "REVOKED": "revoked", "PAUSED": "revoked"}.get(
            str(d.get("status") or "").upper(), "pending")
        accts = [{"ext_id": str(a.get("linkRefNumber") or a.get("maskedAccNumber") or ""),
                  "name": f"{a.get('fipId') or 'Bank'} {a.get('accType') or ''}".strip()[:80],
                  "masked": "..." + str(a.get("maskedAccNumber") or "")[-4:] if a.get("maskedAccNumber") else "", "currency": "INR"}
                 for a in d.get("accountsLinked") or []]
        return {"status": st, "accounts": accts}

    def fetch(self, link: dict[str, Any], ext_id: str, since: str) -> dict[str, Any]:
        today = date.today()
        s = _json(_call("POST", f"{self._b()}/v2/sessions", headers=self._h(), json={
            "consentId": link["ext_ref"], "format": "json",
            "dataRange": {"from": since + "T00:00:00Z", "to": today.isoformat() + "T23:59:59Z"}}), "Data fetch")
        sid = str(s.get("id") or "")
        d = _json(_call("GET", f"{self._b()}/v2/sessions/{sid}", headers=self._h()), "Data fetch")
        if str(d.get("status") or "").upper() not in ("COMPLETED", "PARTIAL"):
            return {"rows": [], "cursor": "", "pending": True}
        rows = []
        for fip in d.get("fips") or []:
            for a in fip.get("accounts") or []:
                if ext_id and str(a.get("linkRefNumber") or a.get("maskedAccNumber") or "") != ext_id:
                    continue
                txs = (((a.get("data") or {}).get("account") or {}).get("transactions") or {}).get("transaction") or []
                for t in txs:
                    sign = 1 if str(t.get("type") or "").upper() == "CREDIT" else -1
                    rows.append({"day": _iso(t.get("valueDate") or t.get("transactionTimestamp")), "amount": sign * _amt(t.get("amount")),
                                 "narration": str(t.get("narration") or "")[:200], "currency": "INR",
                                 "ref": str(t.get("txnId") or t.get("reference") or "")})
        return {"rows": rows, "cursor": ""}

    def revoke(self, link: dict[str, Any]) -> None:
        _call("POST", f"{self._b()}/v2/consents/{link['ext_ref']}/revoke", headers=self._h())


PARTNERS: dict[str, Any] = {"setu_aa": SetuAA(), "gocardless": GoCardless(), "plaid": Plaid()}


def partner(name: str):
    if name not in PARTNERS:
        raise BankLinkError("No such bank-connection partner.")
    if not available(name):
        raise BankLinkError(for_country(REGIONS[name][0])["why"])
    return PARTNERS[name]


def dumps(x: Any) -> str:
    return json.dumps(x, default=str)
