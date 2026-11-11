"""`python -m app.bahi.wbcheck` - the WhiteBooks contract check (vps-ops `wb_check`).

The specs document every request but NO success reply, so before anything touches her GSTIN this walks the calls the employee will
use and RECORDS the shape of each real reply (keys and types only - never a value) to data/bahi/wb_shapes.json. Each step prints
PASS / FAIL / SKIP with a plain line. Never prints a key, a password or an OTP.

SANDBOX (WHITEBOOKS_ENV=sandbox): ping -> GSTIN search -> filing track -> OTP request -> auth token with the spec's sandbox OTP ->
refresh -> ledger balance -> e-invoice login -> e-way bill login (each needs the sandbox identities from the Hub's Credentials page:
WHITEBOOKS_SANDBOX_GSTIN / _GST_USERNAME / _EINV_USERNAME / _EINV_PASSWORD / _EWB_USERNAME / _EWB_PASSWORD).
PRODUCTION: the ping only - no taxpayer call, no OTP, ever, from a check.
"""
from __future__ import annotations

import json
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
            steps.append({"step": name, "result": "FAIL", "line": f"{e.code}: {e.message}"})
            return None
        shapes[name] = {"envelope": wb.shape({k: v for k, v in env_.items() if k != "data"}), "data": wb.shape(wb.data_of(env_))}
        steps.append({"step": name, "result": "PASS", "line": "reply shape recorded"})
        return env_

    step("ping", wb.ping, product="")
    gstin = st.whitebooks_sandbox_gstin.strip().upper() if wb.env() == "sandbox" else ""   # production: no test GSTIN, so the
                                                                                            # public steps SKIP too
    step("public_search", lambda: wb.public_search(TENANT, gstin), need=[("whitebooks_sandbox_gstin", gstin)])
    step("rettrack", lambda: wb.rettrack(TENANT, gstin, _fy(today)), need=[("whitebooks_sandbox_gstin", gstin)])
    if wb.env() != "sandbox":
        steps.append({"step": "taxpayer_calls", "result": "SKIP", "line": "production: a check never makes taxpayer calls or asks for an OTP"})
    else:
        user = st.whitebooks_sandbox_gst_username
        state = gstin[:2]
        otp_env = step("otp_request", lambda: wb.otp_request(TENANT, user, state),
                       need=[("whitebooks_sandbox_gstin", gstin), ("whitebooks_sandbox_gst_username", user)])
        txn = wb.find_txn(otp_env) if otp_env else ""
        if otp_env and not txn:
            steps.append({"step": "txn", "result": "FAIL", "line": "no transaction id found in the OTP reply - see the recorded shape"})
        if txn:
            step("auth_token", lambda: wb.auth_token(TENANT, user, state, txn, wb.SANDBOX_OTP))
            step("refresh", lambda: wb.refresh(TENANT, user, state, txn))
            per = f"{today.month:02d}{today.year}"
            step("ledger_balance", lambda: wb.ledger_balance(TENANT, gstin, per, user, state, txn))
        eu, ep = st.whitebooks_sandbox_einv_username, st.whitebooks_sandbox_einv_password
        step("einv_auth", lambda: wb.einv_auth(TENANT, gstin, eu, ep), product="einv",
             need=[("whitebooks_sandbox_gstin", gstin), ("whitebooks_sandbox_einv_username", eu), ("whitebooks_sandbox_einv_password", ep)])
        wu, wp = st.whitebooks_sandbox_ewb_username, st.whitebooks_sandbox_ewb_password
        step("ewb_auth", lambda: wb.ewb_auth(TENANT, gstin, wu, wp), product="ewb",
             need=[("whitebooks_sandbox_gstin", gstin), ("whitebooks_sandbox_ewb_username", wu), ("whitebooks_sandbox_ewb_password", wp)])
    res = {"env": wb.env(), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "steps": steps,
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
    for s in res["steps"]:
        print(f"  {s['result']:<4}  {s['step']:<16} {s['line']}")
    print(f"{res['passed']} passed, {res['failed']} failed, {res['skipped']} skipped. Shapes: {shapes_path()}")
    if not wb.configured("gst"):
        print("Set in the server's .env (names only - never paste the values in chat):")
        for line in wb.env_lines():
            print("  " + line)
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
