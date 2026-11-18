"""v0.840 BAHI A4 - GSTR-3B and the payment plan. Hoola prepares (GST Sahayak engine: tables, least-cash set-off, interest, late fee), brings
her A2 credit decisions into that preparation, compares with the portal's own figures, and - each on her confirm bound to a plan hash -
saves the draft, applies the set-off, and (only if BAHI_FILING is on) files on her EVC OTP.

NOT built: generating the PMT-06 challan (it needs her bank and address choices) - Hoola tells her the exact cash to pay and she creates the
challan on the GST portal; no money moves from here, ever. NOT VERIFIED on a live portal: the retsave / retoffset bodies, the portal summary
layout, the ledger ids, the EVC call.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlalchemy import delete, select

from ..config import get_settings
from ..db import session
from . import connect as CN
from . import register as REG
from . import wb
from .models import AccTwoB, ensure_tables

HEADS = ("igst", "cgst", "sgst", "cess")


class Gstr3bError(Exception):
    pass


def _ym(period: str) -> str:
    p = (period or "").strip()
    if re.fullmatch(r"\d{6}", p):
        p = f"{p[2:]}-{p[:2]}"
    if not re.fullmatch(r"\d{4}-\d{2}", p):
        raise Gstr3bError("Month as YYYY-MM.")
    return p


def _mm(ym: str) -> str:
    return ym[5:] + ym[:4]


def _gp():
    from ..gstp import service as GP
    return GP


def _bring_2b(tenant: str, g: str, ym: str) -> int:
    """Her A2 work (the 2B she pulled + her accept / pending / reject) becomes the credit this 3B can use: GST Sahayak's 2B rows for the
    month are replaced by hers. Returns how many rows. Nothing happens if she has not pulled a 2B."""
    GP = _gp()
    from ..gstp.service import Gst2B
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == _mm(ym))).all()
        if not rows:
            return 0
        c = GP._client(s, tenant, g)
        s.execute(delete(Gst2B).where(Gst2B.tenant_id == tenant, Gst2B.client_id == c.id, Gst2B.period == ym))
        for r in rows:
            ext = json.loads(r.ext or "{}")
            s.add(Gst2B(tenant_id=tenant, client_id=c.id, period=ym, typ="cn" if r.doc_type == "C" else "dn" if r.doc_type == "D" else "inv",
                        ctin=r.ctin, trdnm=r.trdnm, inum=r.inum, dt=r.dt, val=r.val, txval=r.txval, igst=r.igst, cgst=r.cgst, sgst=r.sgst,
                        cess=r.cess, rev=r.rev, itcavl=r.itcavl, rsn=r.rsn[:40], supprd=str(ext.get("supprd", ""))[:7], ims=r.action))
        s.commit()
        return len(rows)


def prepare(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    from ..appmaker.gst import valid_gstin
    GP = _gp()
    g, ym = gstin.strip().upper(), _ym(period)
    if not valid_gstin(g):
        raise Gstr3bError("That is not a valid GSTIN (shape or check digit).")
    used = _bring_2b(tenant, g, ym)
    try:
        res = GP.prepare_gstr3b(tenant, g, ym)
    except GP.GstError as e:
        raise Gstr3bError(str(e)) from None
    ret = res["return"]
    checks = list(ret.get("checks", []))
    if not used:
        checks.insert(0, "No GSTR-2B has been pulled in the Credit (ITC) tab for this month - credit is counted only from a 2B, so it may be zero.")
    sm = ret["summary"]
    return {"gstin": g, "period": ym, "return_id": ret["id"], "summary": sm, "tables": ret.get("tables", {}), "setoff": ret.get("setoff", {}),
            "checks": checks, "credit_rows_from_2b": used, "plan_hash": plan_hash(tenant, g, ym),
            "cash_to_pay": {"tax_cash": sm["cash"], "interest": sm["interest"], "late_fee": sm["late_fee"], "total": sm["pay_total"]}}


def _stored(tenant: str, g: str, ym: str) -> dict[str, Any]:
    GP = _gp()
    from ..gstp.service import GstReturn
    with session() as s:
        c = GP._client(s, tenant, g)
        r = s.scalars(select(GstReturn).where(GstReturn.tenant_id == tenant, GstReturn.client_id == c.id, GstReturn.period == ym,
                                              GstReturn.kind == "gstr3b")).first()
        if r is None or not r.data:
            raise Gstr3bError("Prepare GSTR-3B for this month first.")
        return json.loads(r.data)


def plan_hash(tenant: str, g: str, ym: str) -> str:
    try:
        d = _stored(tenant, g, ym)
    except Gstr3bError:
        return ""
    return hashlib.sha256(json.dumps({k: d.get(k) for k in ("summary", "tables", "setoff")}, sort_keys=True).encode()).hexdigest()[:20]


def body_from(g: str, ym: str, d: dict[str, Any]) -> dict[str, Any]:
    """The GSTR-3B save body (spec layout) from the prepared tables."""
    t = d["tables"]
    def amt(x, tx=True):
        o = {"iamt": x.get("igst", 0), "camt": x.get("cgst", 0), "samt": x.get("sgst", 0), "csamt": x.get("cess", 0)}
        return ({"txval": x.get("txval", 0)} | o) if tx else o
    avail = [{"ty": "ISRC", **amt(t.get("4A_rcm", {}), False)}]
    other = {h: round(t["4A"].get(h, 0) - t.get("4A_rcm", {}).get(h, 0), 2) for h in HEADS}
    avail.append({"ty": "OTH", **amt(other, False)})
    body = {"gstin": g, "ret_period": _mm(ym),
            "sup_details": {"osup_det": amt(t["3.1a"]), "osup_zero": {"txval": t["3.1b"].get("txval", 0), "iamt": t["3.1b"].get("igst", 0), "csamt": t["3.1b"].get("cess", 0)},
                            "osup_nil_exmp": {"txval": t["3.1c"].get("txval", 0)}, "isup_rev": amt(t["3.1d"])},
            "itc_elg": {"itc_avl": avail, "itc_rev": [{"ty": "RUL", **amt(t["4B1"], False)}, {"ty": "OTH", **amt(t["4B2"], False)}],
                        "itc_net": amt(t["4C"], False)},
            "intr_ltfee": {"intr_details": {"iamt": d["summary"]["interest"], "camt": 0, "samt": 0, "csamt": 0}}}
    if t.get("3.2"):
        body["inter_sup"] = {"unreg_details": [{"pos": u["pos"], "txval": u["txval"], "iamt": u["igst"]} for u in t["3.2"]]}
    return body


def _session(tenant: str, g: str):
    try:
        return CN.session_for(tenant, g)
    except CN.ConnectError as e:
        raise Gstr3bError(str(e)) from None


def _ev(tenant: str, what: str, g: str, ym: str, after: Any = "") -> None:
    ensure_tables()
    with session() as s:
        REG._event(s, tenant, what, f"{g}:{ym}", after=after, actor="owner")
        s.commit()


def compare_with_portal(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    """Read the portal's own auto-liability and interest and set them beside Hoola's. Where the portal's layout is not recognised the
    reply says so and lists its field names - it never pretends to agree."""
    from .apisetu import shape_keys
    g, ym = gstin.strip().upper(), _ym(period)
    d = _stored(tenant, g, ym)
    user, state, txn = _session(tenant, g)
    try:
        al = wb.data_of(wb.gstr3b_autoliab(tenant, g, _mm(ym), user, state, txn))
        ic = wb.data_of(wb.gstr3b_syscalcintrst(tenant, g, _mm(ym), user, state, txn))
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    mine = {h: d["tables"]["3.1a"].get(h, 0) + d["tables"]["3.1b"].get(h, 0) for h in ("igst", "cgst", "sgst", "cess")}
    theirs = _liab(al)
    rows = []
    if theirs:
        for h in HEADS:
            diff = round(mine[h] - theirs.get(h, 0), 2)
            rows.append({"head": h, "hoola": round(mine[h], 2), "portal": theirs.get(h, 0), "diff": diff,
                         "cause": "" if abs(diff) <= 1 else "Hoola counts more tax than the portal auto-liability: bills not yet in GSTR-1 / e-invoice?" if diff > 0
                         else "The portal's auto-liability is higher: sales in GSTR-1 or e-invoices that Hoola's books lack."})
    return {"compared": bool(theirs), "rows": rows, "portal_interest_fields": shape_keys(ic),
            "note": "" if theirs else f"The portal's auto-liability layout was not recognised, so nothing was compared. Its fields: {', '.join(shape_keys(al)) or 'none'}."}


def _liab(d: Any) -> dict[str, float]:
    """Pick tax-by-head out of an auto-liability reply when it is laid out as GSTN's tax-head objects (iamt / camt / samt / csamt)."""
    out = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
    found = False
    stack = [d]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            for k, h in (("iamt", "igst"), ("camt", "cgst"), ("samt", "sgst"), ("csamt", "cess")):
                if isinstance(x.get(k), (int, float)):
                    out[h] += float(x[k])
                    found = True
            stack += [v for v in x.values() if isinstance(v, (dict, list))]
        elif isinstance(x, list):
            stack += [v for v in x if isinstance(v, (dict, list))]
    return {k: round(v, 2) for k, v in out.items()} if found else {}


def save_draft(tenant: str, gstin: str, period: str, plan: str, confirm: bool) -> dict[str, Any]:
    if confirm is not True:
        raise Gstr3bError("This puts a draft on your GST portal - it needs your confirmation.")
    g, ym = gstin.strip().upper(), _ym(period)
    d = _stored(tenant, g, ym)
    if plan != plan_hash(tenant, g, ym):
        raise Gstr3bError("The return changed since you looked at it - review it again.")
    user, state, txn = _session(tenant, g)
    try:
        wb.gstr3b_retsave(tenant, g, _mm(ym), body_from(g, ym, d), user, state, txn)
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    _ev(tenant, "gstr3b_saved", g, ym)
    return {"saved": True, "next": "Compare with the portal, then apply the set-off."}


def offset_body(tenant: str, g: str, ym: str, d: dict[str, Any]) -> dict[str, Any]:
    """retoffset needs the ledger ids from the portal's own 3B summary - read them there, never guess."""
    user, state, txn = _session(tenant, g)
    try:
        summ = wb.data_of(wb.gstr3b_retsum(tenant, g, _mm(ym), user, state, txn))
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    ids = _ledger_ids(summ)
    if not ids:
        raise Gstr3bError("The portal's summary did not show the liability ledger ids, so the set-off cannot be sent from here - apply it on the GST portal.")
    u = d["setoff"].get("used", {})
    cash = d["summary"].get("cash_split", {})
    return {"pdcash": [{"liab_ldg_id": ids[0], "trans_typ": ids[1], "ipd": cash.get("igst", 0), "cpd": cash.get("cgst", 0),
                        "spd": cash.get("sgst", 0), "cspd": cash.get("cess", 0)}],
            "pditc": {"liab_ldg_id": ids[0], "trans_typ": ids[1], "i_pdi": u.get("igst->igst", 0), "i_pdc": u.get("igst->cgst", 0),
                      "i_pds": u.get("igst->sgst", 0), "c_pdi": u.get("cgst->igst", 0), "c_pdc": u.get("cgst->cgst", 0),
                      "s_pdi": u.get("sgst->igst", 0), "s_pds": u.get("sgst->sgst", 0), "cs_pdcs": u.get("cess->cess", 0)}}


def _ledger_ids(d: Any) -> tuple[Any, Any] | None:
    stack = [d]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            if x.get("liab_ldg_id") not in (None, "") and x.get("trans_typ") not in (None, ""):
                return x["liab_ldg_id"], x["trans_typ"]
            stack += [v for v in x.values() if isinstance(v, (dict, list))]
        elif isinstance(x, list):
            stack += [v for v in x if isinstance(v, (dict, list))]
    return None


def apply_setoff(tenant: str, gstin: str, period: str, plan: str, confirm: bool) -> dict[str, Any]:
    """Use her credit against the liability on the portal (retoffset). It uses ITC, it moves no cash - but it cannot be taken back, so it
    needs her confirm and the plan hash."""
    if confirm is not True:
        raise Gstr3bError("Setting off credit changes your portal ledgers and cannot be undone - it needs your confirmation.")
    g, ym = gstin.strip().upper(), _ym(period)
    d = _stored(tenant, g, ym)
    if plan != plan_hash(tenant, g, ym):
        raise Gstr3bError("The return changed since you looked at it - review it again.")
    body = offset_body(tenant, g, ym, d)
    user, state, txn = _session(tenant, g)
    try:
        wb.gstr3b_retoffset(tenant, g, _mm(ym), body, user, state, txn)
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    _ev(tenant, "gstr3b_setoff", g, ym, {"cash": d["summary"]["cash"]})
    return {"applied": True, "cash_still_to_pay": d["summary"]["cash"]}


def payment_plan(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    """The cash she must pay at her bank (PMT-06), compared with the cash already in her ledger. Hoola creates no challan and moves no money."""
    g, ym = gstin.strip().upper(), _ym(period)
    d = _stored(tenant, g, ym)
    sm = d["summary"]
    need = {h: round(sm["cash_split"].get(h, 0), 2) for h in HEADS}
    user, state, txn = _session(tenant, g)
    try:
        bal = wb.data_of(wb.ledger_balance(tenant, g, _mm(ym), user, state, txn))
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    cb = (bal or {}).get("cash_bal") or {}
    have = {h: float((cb.get(h) or {}).get("tx", 0) or 0) for h in HEADS}
    short = {h: round(max(0.0, need[h] - have[h]), 2) for h in HEADS}
    extra = round(sm["interest"] + sm["late_fee"], 2)
    return {"tax_cash_needed": need, "cash_in_ledger": have, "short": short, "interest_and_late_fee": extra,
            "pay_at_bank": round(sum(short.values()) + extra, 2),
            "how": ("Nothing to pay at the bank." if not sum(short.values()) and not extra else
                    "On the GST portal go to Payments > Create Challan (PMT-06), enter these amounts head by head, pay at your bank or net banking, "
                    "then come back. Hoola creates no challan and never moves money.")}


def _filing_on() -> None:
    if not get_settings().bahi_filing:
        raise Gstr3bError("Filing from Hoola is switched off on this server (BAHI_FILING). Save the draft here and file on the GST portal, or ask the owner to switch it on.")


def request_evc_otp(tenant: str, gstin: str, pan: str) -> dict[str, Any]:
    _filing_on()
    g, pan = gstin.strip().upper(), (pan or "").strip().upper()
    if len(pan) != 10:
        raise Gstr3bError("Type the PAN of the authorised signatory (10 characters).")
    user, state, txn = _session(tenant, g)
    try:
        wb.otp_for_evc(tenant, g, pan, "R3B", user, state, txn)
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    return {"sent": True, "message": "The GST portal sent an OTP to the signatory's registered mobile."}


def file_evc(tenant: str, gstin: str, period: str, pan: str, otp: str, plan: str, confirm: bool) -> dict[str, Any]:
    _filing_on()
    if confirm is not True:
        raise Gstr3bError("Filing is final - it needs your confirmation.")
    g, ym = gstin.strip().upper(), _ym(period)
    otp = re.sub(r"\D", "", otp or "")
    if not 4 <= len(otp) <= 8:
        raise Gstr3bError("Type the OTP the GST portal sent to the signatory (digits only).")
    if plan != plan_hash(tenant, g, ym):
        raise Gstr3bError("The return changed since you looked at it - review it again.")
    user, state, txn = _session(tenant, g)
    try:
        summ = wb.data_of(wb.gstr3b_retsum(tenant, g, _mm(ym), user, state, txn))
        if not isinstance(summ, dict) or not summ:
            raise Gstr3bError("The portal has no saved 3B summary for this month - save the draft first.")
        env_ = wb.gstr3b_evcfile(tenant, g, _mm(ym), pan.strip().upper(), otp, summ, user, state, txn)
    except wb.WbError as e:
        raise Gstr3bError(e.message) from None
    from .itc import _words
    _ev(tenant, "gstr3b_filed", g, ym, {"status": _words(wb.data_of(env_))})
    return {"filed": True, "portal_status": _words(wb.data_of(env_)),
            "next": "Check the status on the portal and record the ARN in GST Sahayak. Pay any remaining cash with a PMT-06 challan."}
