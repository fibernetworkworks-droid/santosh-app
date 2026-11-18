"""v0.838 BAHI A3 - GSTR-1, checked before the 11th and saved as a DRAFT on the portal on her tap. Filing needs her EVC OTP and the
BAHI_FILING switch (off by default); nothing here files on its own.

Builds on the GST Sahayak engine (it already writes the portal JSON from itemised bills, with HSN and rates) and adds what it lacked:
a check against the one register (invoices other engines hold that GSTR-1 would miss, B2B shown as B2C, wrong GSTIN, a rate that is not a
slab in force on the invoice date, a month already locked), the save to the portal bound to a plan hash, and the EVC walk (gated).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import session
from . import connect as CN
from . import register as REG
from . import rules as RU
from . import wb
from .models import AccDoc, ensure_tables


class Gstr1Error(Exception):
    pass


def _gp():
    from ..gstp import service as GP
    return GP


def _norm(n: str) -> str:
    import re
    s = re.sub(r"[^A-Z0-9]", "", str(n or "").upper())
    return re.sub(r"(?<![0-9])0+(?=\d)", "", s)


def _ym(period: str) -> str:
    import re
    p = (period or "").strip()
    if re.fullmatch(r"\d{6}", p):
        p = f"{p[2:]}-{p[:2]}"
    if not re.fullmatch(r"\d{4}-\d{2}", p):
        raise Gstr1Error("Month as YYYY-MM.")
    return p


def _mmyyyy(ym: str) -> str:
    return ym[5:] + ym[:4]


def prepare(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    """GSTR-1 JSON for the month (GST Sahayak engine) + the pre-11th checks against the register. Nothing leaves Hoola."""
    from ..appmaker.gst import valid_gstin
    GP = _gp()
    g, ym = gstin.strip().upper(), _ym(period)
    if not valid_gstin(g):
        raise Gstr1Error("That is not a valid GSTIN (shape or check digit).")
    try:
        res = GP.prepare_gstr1(tenant, g, ym)
    except GP.GstError as e:
        raise Gstr1Error(str(e)) from None
    ret = res["return"]
    checks: list[dict[str, str]] = [{"kind": "engine", "text": c} for c in ret.get("checks", [])]
    ensure_tables()
    with session() as s:
        if REG.locked(s, tenant, g, ym):
            checks.append({"kind": "locked", "text": f"{ym} is locked in the register - changes to it are held as amendments, so re-check before saving."})
        reg = [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "out", AccDoc.period == ym,
                                                         AccDoc.status != "gone")).all() if d.gstin in (g, "")]
        from ..gstp.service import GstDoc
        c = GP._client(s, tenant, g)
        gp_docs = s.scalars(select(GstDoc).where(GstDoc.tenant_id == tenant, GstDoc.client_id == c.id, GstDoc.direction == "out",
                                                 GstDoc.period == ym)).all()
        have = {_norm(d.number): d for d in gp_docs}
        slabs = set(RU.slabs_on(f"{ym}-15") or [])
        for d in reg:
            hit = have.get(_norm(d.number))
            if d.source != "gst_sahayak" and hit is None:
                checks.append({"kind": "missing", "text": f"Invoice {d.number} ({d.doc_date}, {d.party_name or 'customer'}, tax Rs {round(d.tax or d.igst + d.cgst + d.sgst, 2):g}) "
                               f"is in your {REG.SOURCES.get(d.source, d.source)} records but not in the GSTR-1 data - it would be left out."})
            if hit is not None and d.party_gstin and not hit.party_gstin:
                checks.append({"kind": "b2b_as_b2c", "text": f"Invoice {d.number}: the customer has GSTIN {d.party_gstin} in the register but the bill carries none - it would go as B2C."})
        for d in gp_docs:
            if d.party_gstin and not valid_gstin(d.party_gstin):
                checks.append({"kind": "bad_gstin", "text": f"Invoice {d.number}: customer GSTIN {d.party_gstin} fails the check digit - the portal will reject it."})
            if slabs:
                for it in json.loads(d.items or "[]"):
                    rt = float(it.get("rate") or 0)
                    if rt not in slabs and d.kind not in ("exp",):
                        checks.append({"kind": "rate", "text": f"Invoice {d.number}: rate {rt:g}% is not a GST slab in force on {d.doc_date or ym} ({', '.join(f'{x:g}' for x in sorted(slabs))}) - check the rate or HSN."})
                        break
    return {"gstin": g, "period": ym, "return_id": ret["id"], "summary": ret["summary"], "checks": checks,
            "plan_hash": plan_hash(tenant, g, ym), "say": res.get("say", "")}


def _json(tenant: str, g: str, ym: str) -> dict[str, Any]:
    GP = _gp()
    from ..gstp.service import GstReturn
    with session() as s:
        c = GP._client(s, tenant, g)
        r = s.scalars(select(GstReturn).where(GstReturn.tenant_id == tenant, GstReturn.client_id == c.id, GstReturn.period == ym,
                                              GstReturn.kind == "gstr1")).first()
        if r is None or not r.portal_json:
            raise Gstr1Error("Prepare GSTR-1 for this month first.")
        j = json.loads(r.portal_json)
    j.pop("version", None)
    j.pop("hash", None)                       # the offline tool's keys; the API body is the plain return
    j.setdefault("gstin", g)
    j.setdefault("fp", _mmyyyy(ym))
    j.setdefault("gt", 0)                     # aggregate turnover: unknown here - NOT VERIFIED what the portal does with 0
    j.setdefault("cur_gt", 0)
    return j


def plan_hash(tenant: str, g: str, ym: str) -> str:
    try:
        return hashlib.sha256(json.dumps(_json(tenant, g, ym), sort_keys=True).encode()).hexdigest()[:20]
    except Gstr1Error:
        return ""


def _save_event(tenant: str, what: str, g: str, ym: str, after: Any = "") -> None:
    ensure_tables()
    with session() as s:
        REG._event(s, tenant, what, f"{g}:{ym}", after=after, actor="owner")
        s.commit()


def save_draft(tenant: str, gstin: str, period: str, plan: str, confirm: bool) -> dict[str, Any]:
    """PUT the prepared return to the portal as a DRAFT (retsave). Needs her confirm + the plan hash of exactly this JSON.
    Saving is not filing: the return stays unfiled until her EVC OTP on the filing step."""
    if confirm is not True:
        raise Gstr1Error("This puts a draft on your GST portal - it needs your confirmation.")
    g, ym = gstin.strip().upper(), _ym(period)
    body = _json(tenant, g, ym)
    if plan != plan_hash(tenant, g, ym):
        raise Gstr1Error("The return changed since you looked at it - review it again.")
    try:
        user, state, txn = CN.session_for(tenant, g)
        env_ = wb.gstr1_retsave(tenant, g, _mmyyyy(ym), body, user, state, txn)
        out: dict[str, Any] = {"saved": True, "reference": _ref(env_), "validate_hsn": "", "portal_summary_fields": []}
        try:
            out["validate_hsn"] = _words(wb.data_of(wb.gstr1_validatehsnsum(tenant, g, _mmyyyy(ym), user, state, txn)))
            out["portal_summary_fields"] = _fields(wb.data_of(wb.gstr1_retsum(tenant, g, _mmyyyy(ym), user, state, txn)))
        except wb.WbError as e:
            out["validate_hsn"] = f"not read: {e.message}"
    except (CN.ConnectError, wb.WbError) as e:
        raise Gstr1Error(getattr(e, "message", None) or str(e)) from None
    _save_event(tenant, "gstr1_saved", g, ym, {"reference": out["reference"]})
    return out


def _ref(env_: Any) -> str:
    from .itc import _find
    return _find(env_, "reference_id") or _find(env_, "refid") or _find(env_, "int_tran_id")


def _words(d: Any) -> str:
    from .itc import _words as w
    return w(d)


def _fields(d: Any) -> list[str]:
    from .connect import _returns  # noqa: F401  (kept import-light)
    from .apisetu import shape_keys
    return shape_keys(d)


# ------------------------------------------------------------------ filing (gated; her EVC OTP; NOT VERIFIED)
def _filing_on() -> None:
    if not get_settings().bahi_filing:
        raise Gstr1Error("Filing from Hoola is switched off on this server (BAHI_FILING). Save the draft here and file it on the GST portal, or ask the owner to switch it on.")


def request_evc_otp(tenant: str, gstin: str, pan: str) -> dict[str, Any]:
    _filing_on()
    g = gstin.strip().upper()
    pan = (pan or "").strip().upper()
    if len(pan) != 10:
        raise Gstr1Error("Type the PAN of the authorised signatory (10 characters).")
    try:
        user, state, txn = CN.session_for(tenant, g)
        wb.otp_for_evc(tenant, g, pan, "R1", user, state, txn)
    except (CN.ConnectError, wb.WbError) as e:
        raise Gstr1Error(getattr(e, "message", None) or str(e)) from None
    return {"sent": True, "message": "The GST portal sent an OTP to the signatory's registered mobile."}


def file_evc(tenant: str, gstin: str, period: str, pan: str, otp: str, plan: str, confirm: bool) -> dict[str, Any]:
    """File GSTR-1 with her EVC OTP. Needs BAHI_FILING, her confirm, the plan hash of the JSON she reviewed, and a saved draft whose
    summary the portal returns. The OTP is passed straight through and never stored."""
    _filing_on()
    if confirm is not True:
        raise Gstr1Error("Filing is final - it needs your confirmation.")
    g, ym = gstin.strip().upper(), _ym(period)
    import re
    otp = re.sub(r"\D", "", otp or "")
    if not 4 <= len(otp) <= 8:
        raise Gstr1Error("Type the OTP the GST portal sent to the signatory (digits only).")
    if plan != plan_hash(tenant, g, ym):
        raise Gstr1Error("The return changed since you looked at it - review it again.")
    try:
        user, state, txn = CN.session_for(tenant, g)
        summ = wb.data_of(wb.gstr1_retsum(tenant, g, _mmyyyy(ym), user, state, txn))
        if not isinstance(summ, dict) or not summ:
            raise Gstr1Error("The portal has no saved draft summary for this month - save the draft first.")
        env_ = wb.gstr1_evcfile(tenant, g, _mmyyyy(ym), pan.strip().upper(), otp, summ, user, state, txn)
    except (CN.ConnectError, wb.WbError) as e:
        raise Gstr1Error(getattr(e, "message", None) or str(e)) from None
    _save_event(tenant, "gstr1_filed", g, ym, {"status": _words(wb.data_of(env_))})
    return {"filed": True, "portal_status": _words(wb.data_of(env_)), "reference": _ref(env_),
            "next": "Check the status on the portal and record the ARN in GST Sahayak. GSTR-1A is for corrections after this and before GSTR-3B."}
