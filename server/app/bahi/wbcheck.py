"""`python -m app.bahi.wbcheck` - the WhiteBooks contract check (vps-ops `wb_check`).

The specs document every request but NO success reply, so before anything touches her GSTIN this walks the calls the employee will
use and RECORDS the shape of each real reply (keys and types only - never a value) to data/bahi/wb_shapes.json. Each step prints
PASS / FAIL / SKIP with a plain line. Never prints a key, a password or an OTP.

SANDBOX (WHITEBOOKS_ENV=sandbox): ping -> GSTIN search -> filing track -> OTP request -> auth token with the spec's sandbox OTP ->
refresh -> ledger balance -> e-invoice login -> e-way bill login (each needs the sandbox identities from the Hub's Credentials page:
WHITEBOOKS_SANDBOX_GSTIN (e-invoice / e-way bill) / _GST_GSTIN (GST, else the same) / _GST_USERNAME / _EINV_USERNAME / _EINV_PASSWORD / _EWB_USERNAME / _EWB_PASSWORD).
PRODUCTION: the ping only - no taxpayer call, no OTP, ever, from a check.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from . import wb

TENANT = "__wbcheck__"


def shapes_path() -> Path:
    return Path("data") / "bahi" / "wb_shapes.json"


def _fy(today: date) -> str:
    y = today.year if today.month >= 4 else today.year - 1
    return f"{y}-{str(y + 1)[2:]}"


_SETTINGS = (("WHITEBOOKS_EMAIL", "whitebooks_email", "email"),
             ("WHITEBOOKS_GST_CLIENT_ID", "whitebooks_gst_client_id", "id"), ("WHITEBOOKS_GST_CLIENT_SECRET", "whitebooks_gst_client_secret", "secret"),
             ("WHITEBOOKS_EINV_CLIENT_ID", "whitebooks_einv_client_id", "id"), ("WHITEBOOKS_EINV_CLIENT_SECRET", "whitebooks_einv_client_secret", "secret"),
             ("WHITEBOOKS_EWB_CLIENT_ID", "whitebooks_ewb_client_id", "id"), ("WHITEBOOKS_EWB_CLIENT_SECRET", "whitebooks_ewb_client_secret", "secret"),
             ("WHITEBOOKS_SANDBOX_GSTIN", "whitebooks_sandbox_gstin", "gstin"),
             ("WHITEBOOKS_SANDBOX_GST_GSTIN", "whitebooks_sandbox_gst_gstin", "gstin"),
             ("WHITEBOOKS_SANDBOX_EINV_PASSWORD", "whitebooks_sandbox_einv_password", "secret"),
             ("WHITEBOOKS_SANDBOX_EWB_PASSWORD", "whitebooks_sandbox_ewb_password", "secret"))
_GSTIN = re.compile(r"^\d{2}[A-Z0-9]{13}$")


def paste_check() -> list[dict[str, Any]]:
    """How each pasted value LOOKS - never the value itself. Catches the usual paste mistakes: dots copied from a hidden field
    (the Hub shows a secret as dots until the eye / copy button is used), spaces or a Windows line end, quotes kept by hand, the
    GST key pasted into the e-invoice line. For a client id only its leading letters are shown (the Hub prints them on screen,
    e.g. GSTS...); for a secret / password only its length."""
    st = get_settings()
    out: list[dict[str, Any]] = []
    for name, attr, kind in _SETTINGS:
        raw = str(getattr(st, attr, "") or "")
        if not raw:
            continue
        v = wb.clean(raw)
        notes: list[str] = []
        if v != raw:
            notes.append("had spaces, quotes or a line end around it (Hoola now removes them)")
        if any(ord(c) > 126 for c in v):
            notes.append("has non-keyboard characters - probably the hidden dots were copied, use the Hub's copy button")
        if any(c.isspace() for c in v):
            notes.append("has a space inside it")
        if kind == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            notes.append("does not look like an email address")
        if kind == "gstin" and not _GSTIN.match(v.upper()):
            notes.append("is not 15 characters like 27AAGCB1286Q005")
        if kind == "id":
            lead = re.match(r"[A-Za-z]*", v).group(0)[:6]
            notes.insert(0, f"starts '{lead}', {len(v)} characters")
        elif kind == "secret":
            notes.insert(0, f"{len(v)} characters")
        out.append({"name": name, "ok": not any("probably" in n or "inside" in n or "does not" in n or "is not" in n for n in notes),
                    "line": "; ".join(notes) or "looks fine"})
    ids = {r["name"]: r["line"].split(",")[0] for r in out if r["name"].endswith("_CLIENT_ID")}
    g = ids.get("WHITEBOOKS_GST_CLIENT_ID")
    for k in ("WHITEBOOKS_EINV_CLIENT_ID", "WHITEBOOKS_EWB_CLIENT_ID"):
        if g and ids.get(k) == g and not g.endswith("''"):
            for r in out:
                if r["name"] == k:
                    r["line"] += " - same start as the GST key: is the GST key pasted here? Each product tab has its own key"
    return out


def run(today: date | None = None) -> dict[str, Any]:
    st = get_settings()
    today = today or date.today()
    steps: list[dict[str, Any]] = []
    shapes: dict[str, Any] = {}

    def step(name: str, fn, *, need: list[tuple[str, Any]] | None = None, product: str = "gst"):
        missing = [k for k, v in (need or []) if not v]
        if missing:
            steps.append({"step": name, "result": "SKIP", "line": "not set in .env: " + ", ".join(m.upper() for m in missing)})
            return None
        if product and not wb.configured(product):
            steps.append({"step": name, "result": "SKIP", "line": f"WhiteBooks {product} keys not set"})
            return None
        try:
            env_ = fn()
        except wb.WbError as e:
            extra = e.detail if e.detail and e.detail[:60] not in e.message else ""        # WhiteBooks' own words when ours are generic
            steps.append({"step": name, "result": "FAIL", "line": f"{e.code}: {e.message}" + (f" [WhiteBooks said: {extra[:200]}]" if extra else "")})
            return None
        shapes[name] = {"envelope": wb.shape({k: v for k, v in env_.items() if k != "data"}), "data": wb.shape(wb.data_of(env_))}
        steps.append({"step": name, "result": "PASS", "line": "reply shape recorded"})
        return env_

    step("ping", wb.ping, product="")
    gstin = wb.clean(st.whitebooks_sandbox_gstin).upper() if wb.env() == "sandbox" else ""   # production: no test GSTIN, so the
                                                                                            # public steps SKIP too
    # v0.826: GST (returns) has its OWN test GSTIN (WhiteBooks support gave 27AAGCB1286QKZL with its username); the e-invoice /
    # e-way bill one (their shared PDF) stays for those two. Empty GST line = the shared one, as before.
    ggstin = (wb.clean(st.whitebooks_sandbox_gst_gstin).upper() if wb.env() == "sandbox" else "") or gstin
    gneed = [("whitebooks_sandbox_gst_gstin", ggstin)]
    step("public_search", lambda: wb.public_search(TENANT, ggstin), need=gneed)
    def _ret():
        err = None
        for fy in (_fy(today), _fy(date(today.year - 1, today.month, 1))):     # this FY may have no data yet - try last year too
            try:
                return wb.rettrack(TENANT, ggstin, fy, "R1")
            except wb.WbError as e:
                err = e
        raise err
    step("rettrack", _ret, need=gneed)
    if wb.env() != "sandbox":
        steps.append({"step": "taxpayer_calls", "result": "SKIP", "line": "production: a check never makes taxpayer calls or asks for an OTP"})
    else:
        user = wb.clean(st.whitebooks_sandbox_gst_username)
        state = ggstin[:2]
        otp_env = step("otp_request", lambda: wb.otp_request(TENANT, user, state),
                       need=[("whitebooks_sandbox_gst_gstin", ggstin), ("whitebooks_sandbox_gst_username", user)])
        txn = wb.find_txn(otp_env) if otp_env else ""
        if otp_env and not txn:
            steps.append({"step": "txn", "result": "FAIL", "line": "no transaction id found in the OTP reply - see the recorded shape"})
        if txn:
            step("auth_token", lambda: wb.auth_token(TENANT, user, state, txn, wb.SANDBOX_OTP))
            step("refresh", lambda: wb.refresh(TENANT, user, state, txn))
            per = f"{today.month:02d}{today.year}"
            step("ledger_balance", lambda: wb.ledger_balance(TENANT, ggstin, per, user, state, txn))
            # A2 reads (harmless): the shapes of 2B and IMS are pinned here; the IMS write is NOT in a check because it changes the portal
            prev = date(today.year - 1, 12, 1) if today.month == 1 else date(today.year, today.month - 1, 1)
            rp = f"{prev.month:02d}{prev.year}"
            step("gstr2b_all", lambda: wb.gstr2b_all(TENANT, ggstin, rp, user, state, txn))
            step("ims_invoices", lambda: wb.ims_invoices(TENANT, ggstin, "b2b", user, state, txn))
        eu, ep = wb.clean(st.whitebooks_sandbox_einv_username), wb.clean(st.whitebooks_sandbox_einv_password)
        step("einv_auth", lambda: wb.einv_auth(TENANT, gstin, eu, ep), product="einv",
             need=[("whitebooks_sandbox_gstin", gstin), ("whitebooks_sandbox_einv_username", eu), ("whitebooks_sandbox_einv_password", ep)])
        wu, wp = wb.clean(st.whitebooks_sandbox_ewb_username), wb.clean(st.whitebooks_sandbox_ewb_password)
        step("ewb_auth", lambda: wb.ewb_auth(TENANT, gstin, wu, wp), product="ewb",
             need=[("whitebooks_sandbox_gstin", gstin), ("whitebooks_sandbox_ewb_username", wu), ("whitebooks_sandbox_ewb_password", wp)])
    res = {"paste": paste_check(), "env": wb.env(), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "steps": steps,
           "passed": sum(1 for s in steps if s["result"] == "PASS"), "failed": sum(1 for s in steps if s["result"] == "FAIL"),
           "skipped": sum(1 for s in steps if s["result"] == "SKIP"), "shapes": shapes}
    try:
        p = shapes_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    return res


def last() -> dict[str, Any] | None:
    """The last check's result (steps + shapes, no values) for the desk."""
    try:
        return json.loads(shapes_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main() -> int:
    res = run()
    print(f"WhiteBooks contract check - {res['env']}")
    print("  How the pasted values look (never the values):")
    for r in res["paste"]:
        print(f"    {'ok ' if r['ok'] else 'FIX'}  {r['name']:<34} {r['line']}")
    for s in res["steps"]:
        print(f"  {s['result']:<4}  {s['step']:<16} {s['line']}")
    print(f"{res['passed']} passed, {res['failed']} failed, {res['skipped']} skipped. Shapes: {shapes_path()}")
    refused = [s for s in res["steps"] if s["result"] == "FAIL" and s["line"].startswith("WB_ERR_9001")]
    if refused and all(r["ok"] for r in res["paste"]):
        print("Every value looks well pasted, so WhiteBooks itself is refusing this account: in the Developer Hub the products may"
              " still be 'not subscribed' / not active for the sandbox. Ask WhiteBooks support (Get Support in the Hub) to activate"
              " sandbox API access for GST, e-Invoice and e-Way Bill on your developer account, then run wb_check again.")
    if any(s["step"] == "otp_request" and s["result"] == "FAIL" and re.search(r"user ?name", s["line"], re.I)
           for s in res["steps"]):
        print("The GST sandbox does not know the name in WHITEBOOKS_SANDBOX_GST_USERNAME, so the OTP login (and the token, refresh"
              " and ledger after it) cannot run. A username given for the public taxpayer search is not a login - GSTIN search"
              " needs no username at all. Ask WhiteBooks support for the GST sandbox LOGIN: its gst_username and the GSTIN it"
              " belongs to (put them in WHITEBOOKS_SANDBOX_GST_USERNAME / WHITEBOOKS_SANDBOX_GST_GSTIN), then run wb_check again.")
    if not wb.configured("gst"):
        print("Set in the server's .env (names only - never paste the values in chat):")
        for line in wb.env_lines():
            print("  " + line)
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
