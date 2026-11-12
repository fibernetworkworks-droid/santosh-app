"""v0.833 BAHI A1 - connect her GSTIN through the GSP and check suppliers with no OTP.

Connect walk: start(gstin, gst_username) asks the GST system to send HER an OTP (her tap) -> verify(otp) exchanges it for the session
WhiteBooks holds -> refresh() keeps it alive -> disconnect() forgets it here. The OTP is passed straight through: never stored, never
logged, never returned. No portal password is asked for. Nothing here files or pays. State lives in acc_gst_conn (txn + dates only).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import session
from . import register as REG
from . import wb
from .models import AccGstConn, ensure_tables

_GSTIN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]$")
SESSION_HOURS = 6        # GSTN API sessions lapse; the desk asks for a refresh / new OTP after this (WhiteBooks gives the exact time on the token)


class ConnectError(Exception):
    pass


def _iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def _check(gstin: str) -> str:
    from ..appmaker.gst import valid_gstin
    g = (gstin or "").strip().upper()
    if not (_GSTIN.match(g) and valid_gstin(g)):
        raise ConnectError("That is not a valid GSTIN (shape or check digit) - nothing was sent.")
    return g


def _row(s, tenant: str, gstin: str) -> AccGstConn | None:
    return s.scalars(select(AccGstConn).where(AccGstConn.tenant_id == tenant, AccGstConn.gstin == gstin)).first()


def _view(r: AccGstConn) -> dict[str, Any]:
    live = r.status == "connected" and bool(r.enabled_until) and r.enabled_until > _iso()
    st = "connected" if live else ("lapsed" if r.status == "connected" else r.status)
    return {"gstin": r.gstin, "state_cd": r.state_cd, "status": st, "gst_username": r.gst_username,
            "enabled_until": r.enabled_until, "last_refresh": r.last_refresh}     # never the txn, never an OTP


def status(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [_view(r) for r in s.scalars(select(AccGstConn).where(AccGstConn.tenant_id == tenant)).all()]


def start(tenant: str, gstin: str, gst_username: str, ip: str = "") -> dict[str, Any]:
    g = _check(gstin)
    user = wb.clean(gst_username)
    if not user:
        raise ConnectError("Type your GST portal username (the one you log in with). Your password is never asked for.")
    ensure_tables()
    try:
        env_ = wb.otp_request(tenant, user, g[:2], ip=ip)
    except wb.WbError as e:
        raise ConnectError(e.message) from None
    txn = wb.find_txn(env_)
    if not txn:
        raise ConnectError("The GST system answered but sent no transaction id - nothing is connected. Try once more.")
    with session() as s:
        r = _row(s, tenant, g)
        if r is None:
            r = AccGstConn(tenant_id=tenant, gstin=g)
            s.add(r)
        r.state_cd, r.gst_username, r.txn, r.status = g[:2], user[:60], txn[:120], "otp_sent"
        REG._event(s, tenant, "connect_otp", g, after={"username": user[:60]}, actor="owner")
        s.commit()
        return {"gstin": g, "status": "otp_sent", "message": "The GST portal has sent an OTP to your registered mobile / email. Type it here."}


def verify(tenant: str, gstin: str, otp: str, ip: str = "") -> dict[str, Any]:
    g = _check(gstin)
    otp = re.sub(r"\D", "", otp or "")
    if not 4 <= len(otp) <= 8:
        raise ConnectError("Type the OTP the GST portal sent you (digits only).")
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None or r.status not in ("otp_sent", "connected", "lapsed") or not r.txn:
            raise ConnectError("Ask for an OTP first.")
        user, txn = r.gst_username, r.txn
    try:
        env_ = wb.auth_token(tenant, user, g[:2], txn, otp, ip=ip)
    except wb.WbError as e:
        raise ConnectError(e.message) from None
    new_txn = wb.find_txn(env_) or txn
    with session() as s:
        r = _row(s, tenant, g)
        r.txn, r.status = new_txn[:120], "connected"
        r.last_refresh = _iso()
        r.enabled_until = _iso(datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS))
        REG._event(s, tenant, "connected", g, actor="owner")
        s.commit()
        return _view(r)


def refresh(tenant: str, gstin: str, ip: str = "") -> dict[str, Any]:
    g = _check(gstin)
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None or not r.txn or r.status != "connected":
            raise ConnectError("Not connected - ask for an OTP first.")
        user, txn = r.gst_username, r.txn
    try:
        env_ = wb.refresh(tenant, user, g[:2], txn, ip=ip)
    except wb.WbError as e:
        with session() as s:
            r = _row(s, tenant, g)
            r.status = "lapsed"
            s.commit()
        raise ConnectError(e.message + " Ask for a new OTP.") from None
    with session() as s:
        r = _row(s, tenant, g)
        r.txn = (wb.find_txn(env_) or txn)[:120]
        r.last_refresh = _iso()
        r.enabled_until = _iso(datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS))
        s.commit()
        return _view(r)


def disconnect(tenant: str, gstin: str) -> dict[str, Any]:
    g = _check(gstin)
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is not None:
            r.txn, r.status, r.enabled_until = "", "new", ""
            REG._event(s, tenant, "disconnected", g, actor="owner")
            s.commit()
    return {"gstin": g, "status": "new",
            "message": "Forgotten here. To cut access at the source too, open the GST portal > My Profile > Manage API Access and switch it off."}


# ------------------------------------------------------------------ supplier checks (no OTP)
def _fy(today: datetime | None = None) -> list[str]:
    t = today or datetime.now()
    y = t.year if t.month >= 4 else t.year - 1
    return [f"{y}-{str(y + 1)[2:]}", f"{y - 1}-{str(y)[2:]}"]


def supplier_check(tenant: str, gstin: str, *, filing: bool = True) -> dict[str, Any]:
    """Is this supplier's GSTIN active, and did they file? Free official answer first (API Setu), WhiteBooks public search as the
    second, filing track from WhiteBooks. Every part says where it came from and what it could NOT find - no guessing."""
    from . import apisetu
    g = _check(gstin)
    out: dict[str, Any] = {"gstin": g, "status": "unknown", "legal_name": "", "source": "", "filing": None, "notes": []}
    if apisetu.configured():
        try:
            rec = apisetu.taxpayer(g)
            out.update(status=("active" if rec["active"] else (rec["status"].lower() or "unknown")), legal_name=rec["legal_name"],
                       trade_name=rec.get("trade_name", ""), registered_on=rec["registered_on"], cancelled_on=rec["cancelled_on"],
                       source=rec["source"])
        except apisetu.ApiSetuError as e:
            out["notes"].append(f"API Setu: {e.message}")
    if not out["source"] and wb.configured("gst"):
        try:
            d = wb.data_of(wb.public_search(tenant, g)) or {}
            d = d if isinstance(d, dict) else {}
            sts = str(d.get("sts") or d.get("status") or "")
            out.update(status=sts.lower() or "unknown", legal_name=str(d.get("lgnm") or d.get("legalName") or ""), source="WhiteBooks (GSTN)")
        except wb.WbError as e:
            out["notes"].append(f"WhiteBooks search: {e.message}")
    if filing and wb.configured("gst"):
        last = ""
        for fy in _fy():
            try:
                d = wb.data_of(wb.rettrack(tenant, g, fy, "R1"))
                out["filing"] = {"fy": fy, "returns": _returns(d)}
                break
            except wb.WbError as e:
                last = e.message
        if out["filing"] is None:
            out["notes"].append(f"Filing track not available: {last or 'not set up'} - so Hoola cannot say whether this supplier filed.")
    elif filing:
        out["notes"].append("Filing track needs the WhiteBooks GST keys.")
    if not out["source"]:
        out["notes"].append("No official source answered - status is unknown, not 'fine'.")
    return out


def _returns(d: Any) -> list[dict[str, str]]:
    """Whatever list of filings the reply holds, reduced to period / form / date / status. Shape is pinned by wb_check."""
    rows = d.get("EFiledlist") if isinstance(d, dict) and "EFiledlist" in d else d
    if isinstance(rows, dict):
        rows = next((v for v in rows.values() if isinstance(v, list)), [])
    out = []
    for x in (rows if isinstance(rows, list) else [])[:40]:
        if isinstance(x, dict):
            out.append({"period": str(x.get("ret_prd") or x.get("retperiod") or ""), "form": str(x.get("rtntype") or x.get("return_type") or ""),
                        "filed_on": str(x.get("dof") or x.get("filing_date") or ""), "status": str(x.get("status") or x.get("sts") or "")})
    return out
