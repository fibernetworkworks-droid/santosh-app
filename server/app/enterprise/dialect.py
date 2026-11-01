"""How each enterprise system really wants to be written to - the part that is NOT generic OData.

v0.382 found this by reading the vendors' own documentation instead of assuming "OData is OData". Every claim
below carries the page it came from, because each one is a write that silently FAILS without it:

SAP (SAP Gateway / S4HANA, OData v2 and v4)
  - `If-Match` is REQUIRED on PUT/PATCH/MERGE wherever the entity has an ETag, which S/4HANA's released APIs
    generally do. No If-Match -> 428 Precondition Required. Stale -> 412 Precondition Failed.
    help.sap.com .../bea0e62beca343fca78ded10f2937658.html (ETag Handling)
    help.sap.com .../8a/3fc9607e1d4c2b9235948334d1ac5f (Conditional Handling: the 428 / 412 codes)
    v4 APIs say it flatly: "the If-Match header must be set for all Update operations".
  - The ETag is on the GET of THAT ENTITY: v2 in the `ETag` response header, v4 in the `etag` header or the
    `@odata.etag` property of the payload.
  - `X-CSRF-Token` is REQUIRED on every modifying request, fetched with `X-CSRF-Token: Fetch` on a GET. Missing
    -> 403. It is bound to the SECURITY SESSION, so the fetch and the write must share cookies - which is why
    this module holds one httpx.Client open instead of opening one per call.
    help.sap.com .../b35c22518bc72214e10000000a44176d.html
  - There is no documented exemption for OAuth/bearer: SAP's own examples fetch the CSRF token WHILE sending a
    bearer token. So we always try, and simply carry on if the server does not issue one.
  - SAP documents a real idempotent-create mechanism: `RequestID` (a 32-char client GUID, stable across
    retries) + `RepeatabilityCreation`, answered by `RepeatabilityResult: accepted`, which guarantees the
    server state reflects a SINGLE execution. help.sap.com .../09f82651c294256ee10000000a445394.html
    It is opt-in per customer system (a background job in SPRO), and returns 412 when off - so we send it,
    read the answer, and record what that endpoint actually supports rather than assuming.

PTC Windchill (Windchill REST Services, OData v4)
  - `CSRF_NONCE` is REQUIRED on POST / PUT / PATCH / DELETE. Fetch `GET <base>/PTC/GetCSRFToken()`, which
    returns `NonceKey` and `NonceValue`; the header NAME is the NonceKey it gives back, so we read it rather
    than hard-code it. support.ptc.com .../WCCG_RESTAccessExamplesFetchNONCE.html
  - An object must be RESERVED (checked out) before a PATCH and unreserved afterwards; ChangeMgmt exposes
    `Reserve` and `UndoReservation` as bound actions.
    support.ptc.com .../example_changemgmt_modify_change_request.html
    This is the dangerous one: a half-finished run that reserved and never released leaves HER change object
    locked to our user, blocking her own engineers. So `writing()` below always releases in a finally, and a
    failed reserve means we never PATCH at all.
  - No ETag / If-Match is documented anywhere for Windchill OData, and PTC states "all aspects of OData
    standard are not currently supported". Concurrency there is the reservation lock, not a conditional
    request. So we PROBE for an ETag and use it if the server sends one, and never require it.
  - Reads default to 25 rows a page; `Prefer: odata.maxpagesize=<n>` raises it, capped at 2000 by the server.
    support.ptc.com .../WCCG_RESTAPIsODataPreferHeader.html

Salesforce
  - Its own REST needs neither CSRF nor If-Match; it is a different animal and gets no concurrency token here.

NOT VERIFIED against a live server (said plainly rather than left to look settled): no customer SAP, Windchill
or Salesforce tenant has ever answered this code. The header and flow shapes come from the vendors' docs; the
exact bound-action path for Windchill Reserve, and whether a given SAP system has the idempotency job
scheduled, can only be confirmed against a real endpoint. Everything here fails CLOSED - a token we cannot
fetch, a reserve we cannot take, an ETag we cannot read on a system that demands one, all stop the write.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("santosh.enterprise.dialect")

MAX_PAGE = 2000             # Windchill's own ceiling; asking for more is silently restricted to it


# A TABLE, not an if-chain. A new system is a row here.
#   csrf     : None | "sap" | "ptc"   - how a modifying request is authorised
#   etag     : "required" | "probe" | "none"
#   reserve  : the OData namespace for Reserve / UndoReservation, or "" for none
#   idem     : "sap" | ""             - a vendor-documented idempotent create
#   page     : send Prefer: odata.maxpagesize
DIALECTS: dict[str, dict[str, Any]] = {
    "sap":        {"csrf": "sap", "etag": "required", "reserve": "",              "idem": "sap", "page": False},
    "windchill":  {"csrf": "ptc", "etag": "probe",    "reserve": "PTC.ChangeMgmt", "idem": "",   "page": True},
    "salesforce": {"csrf": None,  "etag": "none",     "reserve": "",              "idem": "",    "page": False},
    "oracle":     {"csrf": None,  "etag": "probe",    "reserve": "",              "idem": "",    "page": False},
    "teamcenter": {"csrf": None,  "etag": "probe",    "reserve": "",              "idem": "",    "page": False},
}
DEFAULT: dict[str, Any] = {"csrf": None, "etag": "probe", "reserve": "", "idem": "", "page": False}


def of(system: str) -> dict[str, Any]:
    return DIALECTS.get(system or "", DEFAULT)


class DialectError(Exception):
    """A write that must not be attempted: no CSRF token, no ETag where one is demanded, no reservation."""


class Call:
    """One HTTP conversation with her endpoint.

    It exists because a SAP CSRF token is bound to the security session: fetching it on one connection and
    writing on another is the single most common way this integration fails. So the cookie jar, the token and
    the writes all live on one client, opened for a run and closed after it.
    """

    def __init__(self, ep: Any, timeout: int = 60):
        import httpx
        self.ep = ep
        self.system = getattr(ep, "system", "") or ""
        self.d = of(self.system)
        self._token: tuple[str, str] | None = None      # (header name, value)
        self._idem_support: str = "unknown"             # unknown | accepted | unsupported
        self._c = httpx.Client(timeout=timeout, follow_redirects=False)

    # -------------------------------------------------------------- plumbing
    def close(self) -> None:
        try:
            self._c.close()
        except Exception:
            pass

    def __enter__(self) -> "Call":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _auth(self) -> dict[str, str]:
        from ..bazar.security import vault
        h: dict[str, str] = {}
        if getattr(self.ep, "auth_enc", ""):
            secret = vault().open(self.ep.auth_enc)
            kind = getattr(self.ep, "auth_kind", "bearer")
            if kind == "bearer":
                h["Authorization"] = "Bearer " + secret
            elif kind == "basic":
                h["Authorization"] = "Basic " + secret
            else:
                h[getattr(self.ep, "header_name", "") or "X-API-Key"] = secret
        return h

    def _url(self, path: str) -> str:
        return str(self.ep.base_url).rstrip("/") + "/" + str(path).lstrip("/")

    def raw(self, method: str, path: str, body: Any = None, params: dict | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, Any, Any]:
        """The one place an HTTP request is made. Returns (status, parsed body, response) - the response too,
        because an ETag and a CSRF token live in the HEADERS and every caller above needs them."""
        h = {"Accept": "application/json"}
        h.update(self._auth())
        if body is not None:
            h["Content-Type"] = "application/json"      # was missing entirely before v0.382
        if headers:
            h.update(headers)
        res = self._c.request(method, self._url(path), json=body, params=params, headers=h)
        try:
            data: Any = res.json()
        except ValueError:
            data = {"text": res.text[:4000]}
        return res.status_code, data, res

    def get(self, path: str, params: dict | None = None, page: int = 0) -> tuple[int, Any]:
        """A read. On a system that pages small by default, ask for a real page size."""
        headers = {}
        if page and self.d["page"]:
            headers["Prefer"] = f"odata.maxpagesize={max(1, min(int(page), MAX_PAGE))}"
        code, data, _ = self.raw("GET", path, params=params, headers=headers or None)
        return code, data

    # -------------------------------------------------------------- concurrency token
    def token(self, root: str = "") -> tuple[str, str] | None:
        """Fetch the CSRF / nonce token for this session, once. None = this system does not use one."""
        kind = self.d["csrf"]
        if kind is None:
            return None
        if self._token is not None:
            return self._token
        if kind == "sap":
            # a NON-modifying request carrying X-CSRF-Token: Fetch; the token comes back in the same header
            code, _data, res = self.raw("GET", root or "$metadata", headers={"X-CSRF-Token": "Fetch"})
            tok = res.headers.get("x-csrf-token") or res.headers.get("X-CSRF-Token") or ""
            if tok and tok.lower() != "required":
                self._token = ("X-CSRF-Token", tok)
                return self._token
            raise DialectError(
                f"SAP ne CSRF token nahi diya (HTTP {code}). Iske bina koi write nahi bhejenge - "
                "SAP use 403 kar deta hai. Address aur credential jaanch lijiye.")
        if kind == "ptc":
            # GET <base>/PTC/GetCSRFToken() -> {"NonceKey": "CSRF_NONCE", "NonceValue": "..."}
            code, data, _res = self.raw("GET", "PTC/GetCSRFToken()")
            if code < 300 and isinstance(data, dict):
                name = str(data.get("NonceKey") or "CSRF_NONCE")
                val = str(data.get("NonceValue") or "")
                if val:
                    self._token = (name, val)
                    return self._token
            raise DialectError(
                f"Windchill ne CSRF nonce nahi diya (HTTP {code}). Iske bina Windchill har write mana kar "
                "deta hai, to hum bhejenge hi nahi.")
        return None

    def _write_headers(self, root: str = "") -> dict[str, str]:
        t = self.token(root)
        return {t[0]: t[1]} if t else {}

    def retoken(self) -> None:
        """A failed response carries no valid token, so a 403 means fetch a fresh one and try once more."""
        self._token = None

    # -------------------------------------------------------------- concurrency: the ETag
    def etag(self, item_path: str) -> str | None:
        """Read the current ETag of THAT entity. v2 puts it in the `ETag` header, v4 in the `etag` header or
        the `@odata.etag` property. A parent's ETag is not documented as acceptable, so we never substitute."""
        code, data, res = self.raw("GET", item_path)
        if code >= 300:
            return None
        tag = res.headers.get("etag") or res.headers.get("ETag") or ""
        if not tag and isinstance(data, dict):
            tag = str(data.get("@odata.etag") or data.get("@odata.etag".lower()) or "")
        return tag or None

    # -------------------------------------------------------------- the write itself
    def create(self, collection: str, body: dict[str, Any], idem_key: str = "",
               root: str = "") -> tuple[int, Any, dict[str, Any]]:
        """POST. Where the vendor documents an idempotent create, use it: that is the only thing that makes an
        ambiguous timeout safe, and it beats our own key, which only protects a RESUME."""
        h = self._write_headers(root)
        note: dict[str, Any] = {}
        if self.d["idem"] == "sap" and idem_key:
            h["RequestID"] = _guid32(idem_key)
            h["RepeatabilityCreation"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
            note["idempotent_bheja"] = True
        code, data, res = self.raw("POST", collection, body=body, headers=h)
        if code == 403 and self.d["csrf"]:
            self.retoken()
            h.update(self._write_headers(root))
            code, data, res = self.raw("POST", collection, body=body, headers=h)
        rr = (res.headers.get("repeatabilityresult") or res.headers.get("RepeatabilityResult") or "").lower()
        if rr:
            note["repeatability"] = rr
            self._idem_support = "accepted" if rr == "accepted" else "unsupported"
        elif note.get("idempotent_bheja"):
            # SAP returns 412 when the idempotency job is not scheduled on that system
            self._idem_support = "unsupported" if code == 412 else self._idem_support
            note["repeatability"] = "jawab nahi mila"
        return code, data, note

    def update(self, item_path: str, body: dict[str, Any], root: str = "") -> tuple[int, Any, dict[str, Any]]:
        """PATCH - partial by design. Never PUT: PUT resets every field we did not send to its default.

        On a system that demands an ETag we read it first and send If-Match. 428 means we sent none, 412 means
        somebody else changed the row between our read and our write - and a 412 is NEVER blind-retried,
        because the row we planned against is not the row that is there now."""
        h = self._write_headers(root)
        note: dict[str, Any] = {}
        want = self.d["etag"]
        if want in ("required", "probe"):
            tag = self.etag(item_path)
            if tag:
                h["If-Match"] = tag
                note["if_match"] = True
            elif want == "required":
                raise DialectError(
                    f"{self.system} ko If-Match (ETag) chahiye aur row padhe bina woh nahi milta. "
                    "Bina ETag SAP 428 deta hai, to yeh row chhod rahe hain - galat likhne se behtar hai.")
        code, data, res = self.raw("PATCH", item_path, body=body, headers=h)
        if code == 403 and self.d["csrf"]:
            self.retoken()
            h.update(self._write_headers(root))
            code, data, res = self.raw("PATCH", item_path, body=body, headers=h)
        if code == 428:
            note["kyon"] = "If-Match bheja nahi gaya (428)."
        elif code == 412:
            note["kyon"] = "Beech mein kisi ne yeh record badal diya (412). Dobara padhkar nayi jhalak chahiye."
            note["dobara_na_bhejo"] = True
        return code, data, note

    # -------------------------------------------------------------- Windchill's reservation
    def reserve(self, item_path: str, root: str = "") -> bool:
        ns = self.d["reserve"]
        if not ns:
            return False
        code, data, _ = self.raw("POST", f"{item_path}/{ns}.Reserve", body={},
                                 headers=self._write_headers(root))
        if code >= 300:
            raise DialectError(
                f"{self.system} mein yeh object reserve (check out) nahi hua (HTTP {code}): "
                + json.dumps(data, default=str)[:200]
                + " - reserve ke bina Windchill badlav leta hi nahi, to bhej nahi rahe.")
        return True

    def unreserve(self, item_path: str, root: str = "") -> None:
        """Always called in a finally. A reservation we took and never gave back locks HER object against her
        own engineers, so a failure here is logged loudly and never swallowed silently."""
        ns = self.d["reserve"]
        if not ns:
            return
        try:
            code, data, _ = self.raw("POST", f"{item_path}/{ns}.UndoReservation", body={},
                                     headers=self._write_headers(root))
            if code >= 300:
                log.error("UNRESERVE FAILED system=%s path=%s code=%s body=%s - object may stay locked",
                          self.system, item_path, code, json.dumps(data, default=str)[:300])
        except Exception as ex:                                   # noqa: BLE001 - must never mask the write
            log.error("UNRESERVE ERROR system=%s path=%s %s", self.system, item_path, ex)

    def writing(self, item_path: str, root: str = ""):
        """`with call.writing(path):` - reserve if this system needs it, and ALWAYS release."""
        return _Reserved(self, item_path, root)

    def support(self) -> dict[str, Any]:
        """What this endpoint turned out to actually support - recorded, not assumed."""
        return {"system": self.system, "csrf": self.d["csrf"] or "nahi chahiye",
                "etag": self.d["etag"], "reserve": bool(self.d["reserve"]),
                "idempotent_create": self._idem_support}


class _Reserved:
    def __init__(self, call: Call, path: str, root: str):
        self.call, self.path, self.root, self.took = call, path, root, False

    def __enter__(self) -> "_Reserved":
        self.took = self.call.reserve(self.path, self.root)
        return self

    def __exit__(self, *_: Any) -> None:
        if self.took:
            self.call.unreserve(self.path, self.root)


def _guid32(seed: str) -> str:
    """SAP wants "a 32 character GUID string… globally unique for all time" for RequestID, and it must be the
    SAME on a retry or it is not idempotent. Our row's idem hash is already 32 stable hex characters; anything
    shorter is padded deterministically from it rather than randomly."""
    s = "".join(ch for ch in (seed or "") if ch in "0123456789abcdefABCDEF").lower()
    if len(s) >= 32:
        return s[:32]
    return (s + uuid.uuid5(uuid.NAMESPACE_OID, seed or "hoola").hex)[:32]
