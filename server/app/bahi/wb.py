"""The WhiteBooks GSP client (docs/research/accounts/04_whitebooks_api.md - built to the OpenAPI specs in their Developer Hub, NOT
their prose guides, which describe an OAuth / bearer API the live server does not have).

The contract this module keeps:
- every call carries the `client_id` / `client_secret` HEADERS of its product (gst | einv | ewb) and the `email` QUERY parameter;
- the base is the sandbox or production host from WHITEBOOKS_ENV;
- **success is `status_cd == "1"` - the HTTP status is 200 even on failure**, so we never branch on it;
- a refusal comes back as WbError with a stable `code` (WB_ERR_xxxx / the GSTN / NIC code / ours) and a plain-English message;
- passwords / OTPs never reach a log line (the e-way bill password rides a QUERY string - `safe_url` scrubs it);
- every call is metered (they bill per call): a per-tenant daily cap and a per-minute guard REFUSE before the call, never queue;
- `shape()` records a reply's structure with NO values, so the sandbox check can pin the real response shapes the spec omits.
Keys live only in the VPS .env (config.py `whitebooks_*`); nothing here returns them.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from ..config import get_settings

log = logging.getLogger("bahi.wb")

HOSTS = {"sandbox": "https://apisandbox.whitebooks.in", "production": "https://api.whitebooks.in"}
PRODUCTS = ("gst", "einv", "ewb")
SECRET_PARAMS = ("password", "otp", "evcotp", "client_secret")
SANDBOX_OTP = "575757"          # the spec's own sandbox OTP - never used against production
TRANSPORT: httpx.BaseTransport | None = None   # tests inject httpx.MockTransport here

PLAIN = {
    "WB_ERR_9001": "WhiteBooks did not accept the keys, or the account is not active. Check the WHITEBOOKS_* lines in the server's .env.",
    "WB_ERR_9000": "WhiteBooks had an unexpected error. Try again in a few minutes; if it repeats, their support has to look.",
    "not_configured": "WhiteBooks is not set up on the server yet.",
    "cap": "Today's WhiteBooks call limit for this account is used up (they charge per call). It resets at midnight.",
    "rate": "Too many WhiteBooks calls this minute - try again in a minute.",
    "bad_reply": "WhiteBooks sent a reply Hoola could not read.",
    "network": "Could not reach WhiteBooks just now.",
    "2150": "This invoice already has an IRN (duplicate). Hoola fetches the existing one instead of making another.",
    "2174": "This IRN has an active e-way bill - cancel the e-way bill first.",
}


class WbError(Exception):
    def __init__(self, code: str, message: str = "", *, product: str = "", op: str = "", detail: str = ""):
        self.code = str(code or "error")
        self.message = message or PLAIN.get(self.code, "WhiteBooks refused the request.")
        self.product, self.op, self.detail = product, op, detail
        super().__init__(f"{self.code}: {self.message}")

    def view(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "message": self.message, "detail": self.detail[:300], "op": self.op}


# ------------------------------------------------------------------ configuration
def env() -> str:
    e = str(get_settings().whitebooks_env or "sandbox").strip().lower()
    return e if e in HOSTS else "sandbox"


def base() -> str:
    return HOSTS[env()]


def clean(v: Any) -> str:
    """A pasted .env value as WhiteBooks expects it: no surrounding spaces / tabs / Windows line ends, no wrapping quotes that
    survived the .env reader (v0.814: her first wb_check was refused on every product - a stray character is one cause)."""
    s = str(v or "").strip().strip("\r\n\t ")
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        s = s[1:-1].strip()
    return s


def email() -> str:
    return clean(get_settings().whitebooks_email)


def keys(product: str) -> tuple[str, str]:
    st = get_settings()
    cid = clean(getattr(st, f"whitebooks_{product}_client_id", ""))
    sec = clean(getattr(st, f"whitebooks_{product}_client_secret", ""))
    if not (cid and sec):                     # one pair for all three products is allowed
        cid, sec = clean(st.whitebooks_gst_client_id), clean(st.whitebooks_gst_client_secret)
    return cid, sec


_INVALID = re.compile(r"invalid credentials|account is not active", re.I)


def configured(product: str = "gst") -> bool:
    cid, sec = keys(product)
    return bool(email() and cid and sec)


def status() -> dict[str, Any]:
    """What the desk may show: which products are set up - never a key, never the email."""
    st = get_settings()
    return {"env": env(), "base": base(), "email_set": bool(email()),
            "products": {p: configured(p) for p in PRODUCTS},
            "own_pair": {p: bool(getattr(st, f"whitebooks_{p}_client_id", "")) for p in PRODUCTS},
            "daily_cap": int(st.whitebooks_daily_calls or 0), "per_minute": int(st.whitebooks_per_minute or 0)}


def env_lines() -> list[str]:
    """The .env line NAMES the owner sets (values never)."""
    return ["WHITEBOOKS_ENV=sandbox", "WHITEBOOKS_EMAIL=...", "WHITEBOOKS_GST_CLIENT_ID=...", "WHITEBOOKS_GST_CLIENT_SECRET=...",
            "WHITEBOOKS_EINV_CLIENT_ID=... (optional)", "WHITEBOOKS_EINV_CLIENT_SECRET=... (optional)",
            "WHITEBOOKS_EWB_CLIENT_ID=... (optional)", "WHITEBOOKS_EWB_CLIENT_SECRET=... (optional)"]


# ------------------------------------------------------------------ guards + meter
_MINUTE: dict[str, deque] = {}
_LOCK = threading.Lock()


def _today_start() -> datetime:
    ist = timezone(timedelta(hours=5, minutes=30))
    n = datetime.now(ist)
    return n.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def calls_today(tenant: str) -> int:
    from sqlalchemy import func, select

    from ..db import session
    from .models import AccWbCall, ensure_tables
    ensure_tables()
    with session() as s:
        return int(s.scalar(select(func.count()).select_from(AccWbCall).where(
            AccWbCall.tenant_id == tenant, AccWbCall.at >= _today_start())) or 0)


def _guard(tenant: str, product: str, op: str) -> None:
    st = get_settings()
    cap = int(st.whitebooks_daily_calls or 0)
    if cap and calls_today(tenant) >= cap:
        raise WbError("cap", product=product, op=op)
    per = int(st.whitebooks_per_minute or 0)
    if per:
        with _LOCK:
            q = _MINUTE.setdefault(tenant, deque())
            t = time.monotonic()
            while q and t - q[0] > 60:
                q.popleft()
            if len(q) >= per:
                raise WbError("rate", product=product, op=op)
            q.append(t)


def _meter(tenant: str, product: str, op: str, ok: bool, code: str, ms: int) -> None:
    try:
        from ..db import session
        from .models import AccWbCall, ensure_tables
        ensure_tables()
        with session() as s:
            s.add(AccWbCall(tenant_id=tenant, product=product, op=op[:60], ok=ok, code=code[:40], ms=ms))
            s.commit()
    except Exception:   # noqa: BLE001 - the meter never breaks a call
        log.exception("wb meter failed")


def safe_url(url: str, query: dict[str, Any] | None = None) -> str:
    q = {k: ("***" if k.lower() in SECRET_PARAMS else v) for k, v in (query or {}).items()}
    return url + ("?" + urlencode(q) if q else "")


# ------------------------------------------------------------------ the call
_CODE = re.compile(r"\b(WB_ERR_\d+)\b")


def _code_of(env_: dict[str, Any]) -> str:
    err = env_.get("error") if isinstance(env_.get("error"), dict) else {}
    for c in (err.get("error_cd"), err.get("code"), env_.get("errorCode"), env_.get("error_cd")):
        if c:
            return str(c)
    desc = str(env_.get("status_desc") or "")
    m = _CODE.search(desc)
    if m:
        return m.group(1)
    return "WB_ERR_9001" if _INVALID.search(desc) else "refused"     # the e-way bill login says it without the code


_ERRS: dict[str, Any] | None = None


def known_error(code: str) -> str:
    """The GST / e-invoice system's own words for a code, from WhiteBooks' published error lists (bahi/wb_errors.json):
    'Invalid GSTIN', 'OTP is either expired or incorrect', an e-invoice code's message + its fix. '' when unknown."""
    global _ERRS
    if _ERRS is None:
        try:
            import json
            from pathlib import Path
            _ERRS = json.loads((Path(__file__).resolve().parent / "wb_errors.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _ERRS = {}
    c = str(code or "").strip()
    g = (_ERRS.get("gst") or {}).get(c)
    if g:
        return f"GST system: {g}."
    e = (_ERRS.get("einv") or {}).get(c)
    if e and e.get("message"):
        fix = e.get("fix") or ""
        return f"e-invoice system: {e['message']}." + (f" {fix}" if fix else "")
    return ""


def _message_of(env_: dict[str, Any], code: str) -> str:
    if code in PLAIN:
        return PLAIN[code]
    k = known_error(code)
    if k:
        return k[:400]
    err = env_.get("error") if isinstance(env_.get("error"), dict) else {}
    for m in (err.get("message"), err.get("desc"), env_.get("message"), env_.get("status_desc")):
        if m:
            return re.sub(r"^\s*WB_ERR_\d+\s*:\s*", "", str(m))[:300]
    return "WhiteBooks refused the request."


def _note_of(env_: dict[str, Any]) -> str:
    """WhiteBooks' own words from a refusal: every short scalar in the envelope and its error block (codes, descriptions) - the reply
    holds no keys or taxpayer data on a refusal. Used when our plain message is generic."""
    bits: list[str] = []
    def walk(d: Any, pre: str, depth: int) -> None:
        if not isinstance(d, dict) or depth > 2:
            return
        for k, v in list(d.items())[:12]:
            if k == "data":
                continue
            if isinstance(v, (str, int, float)) and str(v).strip():
                bits.append(f"{pre}{k}={str(v)[:120]}")
            elif isinstance(v, dict):
                walk(v, f"{pre}{k}.", depth + 1)
    walk(env_, "", 0)
    return "; ".join(bits)[:400]


def call(tenant: str, product: str, method: str, path: str, *, query: dict[str, Any] | None = None,
         headers: dict[str, Any] | None = None, body: Any = None, op: str = "", auth: bool = True) -> dict[str, Any]:
    """One WhiteBooks call. Returns the reply envelope (`status_cd == "1"`) or raises WbError. `auth=False` only for the root ping."""
    if product not in PRODUCTS:
        raise WbError("bad_product", f"Unknown WhiteBooks product '{product}'.")
    op = op or f"{method} {path}"
    st = get_settings()
    if auth and not configured(product):
        raise WbError("not_configured", product=product, op=op)
    if auth:
        _guard(tenant, product, op)
    cid, sec = keys(product)
    q = dict(query or {})
    h: dict[str, str] = {"Accept": "application/json"}
    if auth:
        q = {"email": email(), **q}
        h.update({"client_id": cid, "client_secret": sec})
    for k, v in (headers or {}).items():
        if v is not None and v != "":
            h[k] = str(v)
    url = base() + path
    t0 = time.monotonic()
    code, ok = "", False
    try:
        with httpx.Client(transport=TRANSPORT, timeout=float(st.whitebooks_timeout_s or 30)) as c:
            r = c.request(method.upper(), url, params=q, headers=h, json=body if body is not None else None)
        try:
            env_ = r.json()
        except ValueError:
            code = "bad_reply"
            raise WbError("bad_reply", product=product, op=op, detail=f"HTTP {r.status_code}: {r.text[:200]}")
        if not isinstance(env_, dict):
            code = "bad_reply"
            raise WbError("bad_reply", product=product, op=op)
        if not auth:
            ok = r.status_code < 400
            return env_
        if str(env_.get("status_cd")) == "1":
            ok = True
            return env_
        code = _code_of(env_)
        raise WbError(code, _message_of(env_, code), product=product, op=op, detail=_note_of(env_))
    except httpx.HTTPError as e:
        code = "network"
        raise WbError("network", product=product, op=op, detail=type(e).__name__)
    finally:
        ms = int((time.monotonic() - t0) * 1000)
        log.info("wb %s %s -> %s (%d ms)", product, safe_url(url, q), "ok" if ok else (code or "error"), ms)
        if auth:
            _meter(tenant, product, op, ok, code or ("ok" if ok else "error"), ms)


def data_of(env_: dict[str, Any]) -> Any:
    """The useful part of a reply. WhiteBooks returns `data` either as an object or as a JSON string."""
    d = env_.get("data")
    if isinstance(d, str):
        import json
        try:
            return json.loads(d)
        except ValueError:
            return d
    return d


def shape(v: Any, depth: int = 0) -> Any:
    """The structure of a reply with NO values: dict -> {key: shape}, list -> [shape of first], scalars -> their type name."""
    if depth > 6:
        return "..."
    if isinstance(v, dict):
        return {str(k): shape(x, depth + 1) for k, x in list(v.items())[:60]}
    if isinstance(v, list):
        return [shape(v[0], depth + 1)] if v else []
    if v is None:
        return "null"
    return type(v).__name__


def _ip() -> str:
    return str(get_settings().whitebooks_ip_address or "127.0.0.1")


# ------------------------------------------------------------------ primitives A0 / A1 use
def ping() -> dict[str, Any]:
    """The gateway root ('I-HUB is up and running!') - no keys, no meter."""
    return call("__wbping__", "gst", "GET", "/", auth=False, op="ping")


def public_search(tenant: str, gstin: str) -> dict[str, Any]:
    """A GSTIN's public record - no taxpayer OTP needed."""
    return call(tenant, "gst", "GET", "/public/search", query={"gstin": gstin.strip().upper()}, op="public/search")


def rettrack(tenant: str, gstin: str, fy: str, typ: str = "") -> dict[str, Any]:
    """Which returns a GSTIN has filed in a financial year (YYYY-YY) - no OTP. Drives the 'supplier has not filed' watch."""
    q = {"gstin": gstin.strip().upper(), "fy": fy}
    if typ:
        q["type"] = typ
    return call(tenant, "gst", "GET", "/public/rettrack", query=q, op="public/rettrack")


def _gst_headers(gst_username: str, state_cd: str, txn: str = "", ip: str = "") -> dict[str, str]:
    h = {"gst_username": gst_username, "state_cd": state_cd, "ip_address": ip or _ip()}
    if txn:
        h["txn"] = txn
    return h


def find_txn(env_: dict[str, Any]) -> str:
    """The OTP request's transaction id - the spec gives no response example, so look where GSTN puts it."""
    for holder in (env_, env_.get("header") if isinstance(env_.get("header"), dict) else {}, data_of(env_)):
        if isinstance(holder, dict):
            for k in ("txn", "Txn", "TXN", "transaction_id"):
                if holder.get(k):
                    return str(holder[k])
    return ""


def otp_request(tenant: str, gst_username: str, state_cd: str, ip: str = "") -> dict[str, Any]:
    """Ask the GST system to send the login OTP to HER registered mobile / email (her tap starts this - A1)."""
    return call(tenant, "gst", "GET", "/authentication/otprequest", headers=_gst_headers(gst_username, state_cd, ip=ip),
                op="auth/otprequest")


def auth_token(tenant: str, gst_username: str, state_cd: str, txn: str, otp: str, ip: str = "") -> dict[str, Any]:
    """Exchange her OTP for the session WhiteBooks holds. The OTP is passed straight through - never stored, never logged."""
    return call(tenant, "gst", "GET", "/authentication/authtoken", query={"otp": otp},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="auth/authtoken")


def refresh(tenant: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    return call(tenant, "gst", "GET", "/authentication/refreshtoken", headers=_gst_headers(gst_username, state_cd, txn, ip),
                op="auth/refreshtoken")


def ledger_balance(tenant: str, gstin: str, retperiod: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    """Cash + credit ledger balance for a period (MMYYYY) - a harmless read used to prove the session works."""
    return call(tenant, "gst", "GET", "/ledgers/bal", query={"gstin": gstin, "retperiod": retperiod},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="ledgers/bal")


def einv_auth(tenant: str, gstin: str, username: str, password: str, ip: str = "", irp: str = "") -> dict[str, Any]:
    return call(tenant, "einv", "GET", "/einvoice/authenticate", query={"irp": irp} if irp else None,
                headers={"username": username, "password": password, "ip_address": ip or _ip(), "gstin": gstin}, op="einv/authenticate")


def ewb_auth(tenant: str, gstin: str, username: str, password: str, ip: str = "", irp: str = "") -> dict[str, Any]:
    q = {"username": username, "password": password}
    if irp:
        q["irp"] = irp
    return call(tenant, "ewb", "GET", "/ewaybillapi/v1.03/authenticate", query=q,
                headers={"ip_address": ip or _ip(), "gstin": gstin}, op="ewb/authenticate")


# ------------------------------------------------------------------ A2: 2B + IMS (reads are harmless; ims_save changes her portal and only runs on her tap)
def gstr2b_all(tenant: str, gstin: str, rtnprd: str, gst_username: str, state_cd: str, txn: str, filenum: int = 0, ip: str = "") -> dict[str, Any]:
    q = {"gstin": gstin, "rtnprd": rtnprd}
    if filenum:
        q["filenum"] = filenum
    return call(tenant, "gst", "GET", "/gstr2b/all", query=q, headers=_gst_headers(gst_username, state_cd, txn, ip), op="gstr2b/all")


def ims_invoices(tenant: str, gstin: str, section: str, gst_username: str, state_cd: str, txn: str, status: str = "", ip: str = "") -> dict[str, Any]:
    q = {"gstin": gstin, "section": section}
    if status:
        q["status"] = status
    return call(tenant, "gst", "GET", "/ims/invoices", query=q, headers=_gst_headers(gst_username, state_cd, txn, ip), op="ims/invoices")


def ims_save(tenant: str, gstin: str, ret_period: str, body: dict[str, Any], gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    h = _gst_headers(gst_username, state_cd, txn, ip) | {"gstin": gstin, "ret_period": ret_period}
    return call(tenant, "gst", "PUT", "/ims/save", headers=h, body=body, op="ims/save")


def ims_status(tenant: str, gstin: str, int_tran_id: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    return call(tenant, "gst", "GET", "/ims/status", query={"gstin": gstin, "int_tran_id": int_tran_id},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="ims/status")


def gen2b(tenant: str, gstin: str, ret_period: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    h = _gst_headers(gst_username, state_cd, txn, ip) | {"gstin": gstin, "ret_period": ret_period}
    return call(tenant, "gst", "PUT", "/gstr2b/gen2b", headers=h, op="gstr2b/gen2b")


def get2b(tenant: str, gstin: str, int_tran_id: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    return call(tenant, "gst", "GET", "/gstr2b/get2b", query={"gstin": gstin, "int_tran_id": int_tran_id},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="gstr2b/get2b")


def logout(tenant: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    """End the GST session at WhiteBooks. A GSP account allows only a few open sessions per user (AUTH403 'Maximum session allowed'),
    so every walk that opens one must close it."""
    return call(tenant, "gst", "GET", "/authentication/logout", headers=_gst_headers(gst_username, state_cd, txn, ip), op="auth/logout")


# ------------------------------------------------------------------ A3: GSTR-1 (retsave is a DRAFT on the portal; the EVC file call is gated by BAHI_FILING)
def gstr1_retsave(tenant: str, gstin: str, ret_period: str, body: dict[str, Any], gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    h = _gst_headers(gst_username, state_cd, txn, ip) | {"gstin": gstin, "ret_period": ret_period}
    return call(tenant, "gst", "PUT", "/gstr1/retsave", headers=h, body=body, op="gstr1/retsave")


def gstr1_retsum(tenant: str, gstin: str, retperiod: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    return call(tenant, "gst", "GET", "/gstr1/retsum", query={"gstin": gstin, "retperiod": retperiod},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="gstr1/retsum")


def gstr1_validatehsnsum(tenant: str, gstin: str, retperiod: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    return call(tenant, "gst", "GET", "/gstr1/validatehsnsum", query={"gstin": gstin, "retperiod": retperiod},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="gstr1/validatehsnsum")


def otp_for_evc(tenant: str, gstin: str, pan: str, form_type: str, gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    """Sends the EVC OTP to the authorised signatory's registered mobile. The OTP itself never comes back here."""
    return call(tenant, "gst", "GET", "/authentication/otpforevc", query={"gstin": gstin, "pan": pan, "form_type": form_type},
                headers=_gst_headers(gst_username, state_cd, txn, ip), op="auth/otpforevc")


def gstr1_evcfile(tenant: str, gstin: str, ret_period: str, pan: str, evcotp: str, content: dict[str, Any], gst_username: str, state_cd: str, txn: str, ip: str = "") -> dict[str, Any]:
    h = _gst_headers(gst_username, state_cd, txn, ip) | {"gstin": gstin, "ret_period": ret_period}
    return call(tenant, "gst", "POST", "/gstr1/retevcfile", query={"pan": pan, "evcotp": evcotp}, headers=h, body={"content": content}, op="gstr1/retevcfile")


# ------------------------------------------------------------------ A4: GSTR-3B (save and offset change her portal ledgers; the EVC file call is gated by BAHI_FILING)
def _g3(tenant, path, op, gstin, rp, user, state, txn, method="GET", body=None, query=None, ip=""):
    h = _gst_headers(user, state, txn, ip)
    if method != "GET":
        h = h | {"gstin": gstin, "ret_period": rp}
        q = query
    else:
        q = {"gstin": gstin, "retperiod": rp} | (query or {})
    return call(tenant, "gst", method, path, query=q, headers=h, body=body, op=op)


def gstr3b_autoliab(tenant, gstin, rp, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/autoliab", "gstr3b/autoliab", gstin, rp, user, state, txn, ip=ip)


def gstr3b_retsum(tenant, gstin, rp, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/retsum", "gstr3b/retsum", gstin, rp, user, state, txn, ip=ip)


def gstr3b_syscalcintrst(tenant, gstin, rp, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/syscalcintrst", "gstr3b/syscalcintrst", gstin, rp, user, state, txn, ip=ip)


def gstr3b_retsave(tenant, gstin, rp, body, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/retsave", "gstr3b/retsave", gstin, rp, user, state, txn, method="PUT", body=body, ip=ip)


def gstr3b_retoffset(tenant, gstin, rp, body, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/retoffset", "gstr3b/retoffset", gstin, rp, user, state, txn, method="PUT", body=body, ip=ip)


def gstr3b_evcfile(tenant, gstin, rp, pan, evcotp, content, user, state, txn, ip=""):
    return _g3(tenant, "/gstr3b/retevcfile", "gstr3b/retevcfile", gstin, rp, user, state, txn, method="POST", body={"content": content},
               query={"pan": pan, "evcotp": evcotp}, ip=ip)


# ------------------------------------------------------------------ A5: e-invoice (IRP) + e-way bill. Every call carries the IRP session token in the `auth-token` header.
def _einv_h(gstin: str, username: str, token: str, ip: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ip_address": ip or _ip(), "gstin": gstin, "username": username, "auth-token": token, **(extra or {})}


def einv_generate(tenant, gstin, username, token, payload, irp="", ip=""):
    return call(tenant, "einv", "POST", "/einvoice/type/GENERATE/version/V1_03", query={"irp": irp} if irp else None,
                headers=_einv_h(gstin, username, token, ip), body=payload, op="einv/generate")


def einv_cancel(tenant, gstin, username, token, irn, reason, remark, irp="", ip=""):
    return call(tenant, "einv", "POST", "/einvoice/type/CANCEL/version/V1_03", query={"irp": irp} if irp else None,
                headers=_einv_h(gstin, username, token, ip), body={"Irn": irn, "CnlRsn": reason, "CnlRem": remark[:100]}, op="einv/cancel")


def einv_by_doc(tenant, gstin, username, token, doc_type, doc_no, doc_date_dmy, irp="", ip=""):
    q = {"param1": doc_type}
    if irp:
        q["irp"] = irp
    return call(tenant, "einv", "GET", "/einvoice/type/GETIRNBYDOCDETAILS/version/V1_03", query=q,
                headers=_einv_h(gstin, username, token, ip, {"docnum": doc_no, "docdate": doc_date_dmy}), op="einv/getirnbydoc")


def einv_gstin_details(tenant, gstin, username, token, party_gstin, irp="", ip=""):
    q = {"param1": party_gstin} | ({"irp": irp} if irp else {})
    return call(tenant, "einv", "GET", "/einvoice/type/GSTNDETAILS/version/V1_03", query=q, headers=_einv_h(gstin, username, token, ip), op="einv/gstndetails")


def einv_ewb_by_irn(tenant, gstin, username, token, body, irp="", ip=""):
    return call(tenant, "einv", "POST", "/einvoice/type/GENERATE_EWAYBILL/version/V1_03", query={"irp": irp} if irp else None,
                headers=_einv_h(gstin, username, token, ip), body=body, op="einv/generate_ewb")


def ewb_cancel(tenant, gstin, username, ewb_no, reason_code, remark, ip=""):
    """Cancel an e-way bill (within 24 h of generation). Path from the spec's `.../ewayapi/canewb` - NOT VERIFIED."""
    return call(tenant, "ewb", "POST", "/ewaybillapi/v1.03/ewayapi/canewb", headers={"ip_address": ip or _ip(), "gstin": gstin, "username": username},
                body={"ewbNo": int(ewb_no), "cancelRsnCode": int(reason_code), "cancelRmrk": remark[:50]}, op="ewb/cancel")
