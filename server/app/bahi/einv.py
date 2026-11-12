"""v0.842 BAHI A5 - e-invoice (IRN) and e-way bill from any Hoola invoice, each on her confirm.

Laws: the attempt row is written BEFORE the call and the reply stored as it arrives (acc_irn), so a timeout or restart never loses or doubles an
IRN; a duplicate (NIC 2150) or a timeout is recovered by asking the IRP for the document and adopting what it already issued; an IRN with a live
e-way bill is never cancelled first (NIC 2174); the 24-hour cancel window, the 30-day report window (turnover Rs 10 crore and above) and the
e-way bill's 180-day document limit are checked BEFORE the call; her IRP password is sealed and returned by no route. Hoola never invents a
buyer address - the card asks for what the register lacks.
NOT VERIFIED on a live IRP: the success reply fields (Irn / AckNo / AckDt are looked up by name), the e-way cancel path.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..accounts import decrypt, encrypt
from ..db import session
from . import register as REG
from . import wb
from .itc import _find
from .models import AccDoc, AccGstConn, AccIrn, ensure_tables

TOKEN_HOURS = 5                         # NIC tokens last ~6 h; renew a little early
CANCEL_HOURS = 24
DOC_NO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/\-]{0,15}$")
DOC_TYPE = {"inv": "INV", "cn": "CRN", "dn": "DBN"}
AATO_30DAY = 100_000_000                # Rs 10 crore


class EinvError(Exception):
    pass


def _g(gstin: str) -> str:
    from ..appmaker.gst import valid_gstin
    g = (gstin or "").strip().upper()
    if not valid_gstin(g):
        raise EinvError("That is not a valid GSTIN (shape or check digit).")
    return g


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat(timespec="seconds")


def _row(s, tenant: str, g: str) -> AccGstConn | None:
    return s.scalars(select(AccGstConn).where(AccGstConn.tenant_id == tenant, AccGstConn.gstin == g)).first()


# ------------------------------------------------------------------ connect to the IRP (her e-invoice portal login)
def connect(tenant: str, gstin: str, username: str, password: str, seller: dict[str, Any], irp: str = "",
            ewb_username: str = "", ewb_password: str = "") -> dict[str, Any]:
    g = _g(gstin)
    user, pw = wb.clean(username), wb.clean(password)
    if not user or not pw:
        raise EinvError("Type the username and password you use on the e-invoice portal (einvoice1.gst.gov.in). The password is kept sealed and shown nowhere.")
    s_ = {k: str((seller or {}).get(k) or "").strip() for k in ("LglNm", "TrdNm", "Addr1", "Addr2", "Loc", "Pin", "Stcd", "Ph", "Em")}
    s_["Stcd"] = s_["Stcd"] or g[:2]
    miss = [k for k in ("LglNm", "Addr1", "Loc", "Pin") if not s_[k]]
    if miss:
        raise EinvError("Your seller details are needed on every invoice: " + ", ".join(miss) + ".")
    if not re.fullmatch(r"\d{6}", s_["Pin"]):
        raise EinvError("The pincode must be 6 digits.")
    try:
        env_ = wb.einv_auth(tenant, g, user, pw, irp=irp)
    except wb.WbError as e:
        raise EinvError(e.message) from None
    token = _find(env_, "AuthToken")
    if not token:
        raise EinvError("The e-invoice portal answered but gave no session token - nothing is connected.")
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None:
            r = AccGstConn(tenant_id=tenant, gstin=g, state_cd=g[:2])
            s.add(r)
        r.einv_username, r.einv_password_enc = user[:60], encrypt(pw) or ""
        r.einv_token, r.einv_token_at = encrypt(token) or "", _iso()
        r.einv_seller, r.einv_irp = json.dumps(s_), (irp or "")[:8]
        if ewb_username and ewb_password:
            r.ewb_username, r.ewb_password_enc = wb.clean(ewb_username)[:60], encrypt(wb.clean(ewb_password)) or ""
        REG._event(s, tenant, "einv_connected", g, actor="owner")
        s.commit()
    return status(tenant, g)


def status(tenant: str, gstin: str) -> dict[str, Any]:
    g = _g(gstin)
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None or not r.einv_username:
            return {"gstin": g, "connected": False}
        return {"gstin": g, "connected": True, "username": r.einv_username, "ewb": bool(r.ewb_username), "irp": r.einv_irp,
                "token_at": r.einv_token_at, "seller": json.loads(r.einv_seller or "{}")}      # never the password or the token


def _session(tenant: str, g: str) -> tuple[str, str, str, dict[str, Any]]:
    """(username, token, irp, seller) - renews the token with the sealed password when it is old."""
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None or not r.einv_username or not r.einv_password_enc:
            raise EinvError("Connect your e-invoice login first (e-Invoice tab).")
        user, pw, irp, tok, at = r.einv_username, decrypt(r.einv_password_enc) or "", r.einv_irp, decrypt(r.einv_token) or "", r.einv_token_at
        seller = json.loads(r.einv_seller or "{}")
    fresh = bool(tok and at and at > _iso(_now() - timedelta(hours=TOKEN_HOURS)))
    if not fresh:
        try:
            tok = _find(wb.einv_auth(tenant, g, user, pw, irp=irp), "AuthToken")
        except wb.WbError as e:
            raise EinvError(e.message) from None
        if not tok:
            raise EinvError("The e-invoice portal gave no session token - check the login.")
        with session() as s:
            r = _row(s, tenant, g)
            r.einv_token, r.einv_token_at = encrypt(tok) or "", _iso()
            s.commit()
    return user, tok, irp, seller


# ------------------------------------------------------------------ build INV-01
def _dmy(day: str) -> str:
    try:
        return datetime.strptime(day, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return ""


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _lines(s, tenant: str, d: AccDoc, extra: dict[str, Any]) -> list[dict[str, Any]]:
    """Itemised lines come from the GST Sahayak bill with the same number; any other source needs her HSN for ONE line from the totals."""
    try:
        from ..gstp.service import GstDoc
        gd = s.scalars(select(GstDoc).where(GstDoc.tenant_id == tenant, GstDoc.direction == "out", GstDoc.number == d.number)).first()
        if gd is not None and json.loads(gd.items or "[]"):
            return json.loads(gd.items)
    except Exception:   # noqa: BLE001
        pass
    hsn = re.sub(r"\D", "", str(extra.get("hsn") or ""))
    if not hsn:
        return []
    tx = d.taxable or max(0.0, (d.total or 0) - (d.tax or d.igst + d.cgst + d.sgst))
    rate = round(((d.igst + d.cgst + d.sgst) or d.tax) / tx * 100, 2) if tx else 0
    return [{"rate": rate, "txval": tx, "igst": d.igst, "cgst": d.cgst, "sgst": d.sgst, "cess": d.cess, "hsn": hsn,
             "desc": str(extra.get("desc") or "Goods / services as per invoice")[:300], "qty": 1, "uqc": "NOS"}]


def build(tenant: str, gstin: str, doc_id: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """INV-01 v1.1 for one register document, or the exact list of what is missing. Nothing is sent."""
    g, extra = _g(gstin), dict(extra or {})
    _, _, _, seller = _session_info(tenant, g)
    ensure_tables()
    with session() as s:
        d = s.get(AccDoc, doc_id)
        if d is None or d.tenant_id != tenant or d.direction != "out":
            raise EinvError("That sales document was not found in your register.")
        if d.kind not in DOC_TYPE:
            raise EinvError("Only invoices, credit notes and debit notes get an IRN.")
        missing: list[str] = []
        if not d.party_gstin:
            raise EinvError("This sale has no customer GSTIN - e-invoice (IRN) is for sales to registered businesses only.")
        if not DOC_NO.match(d.number or ""):
            missing.append("invoice number of at most 16 characters (letters, digits, / and -)")
        buyer = {"Gstin": d.party_gstin, "LglNm": (extra.get("buyer_name") or d.party_name or "").strip(), "Pos": d.pos or d.party_gstin[:2],
                 "Addr1": str(extra.get("buyer_addr1") or "").strip(), "Loc": str(extra.get("buyer_loc") or "").strip(),
                 "Pin": str(extra.get("buyer_pin") or "").strip(), "Stcd": d.party_gstin[:2]}
        for k, label in (("LglNm", "customer's legal name"), ("Addr1", "customer's address"), ("Loc", "customer's city"), ("Pin", "customer's pincode")):
            if not buyer[k]:
                missing.append(label)
        lines = _lines(s, tenant, d, extra)
        if not lines:
            missing.append("HSN code of the goods / service (this bill has no item lines)")
        if not seller.get("LglNm"):
            missing.append("your seller details (connect the e-invoice login)")
        if missing:
            return {"ready": False, "missing": missing, "doc": {"id": d.id, "number": d.number, "date": d.doc_date}}
        inter = (buyer["Pos"] != seller.get("Stcd", g[:2]))
        items, tot = [], {"ass": 0.0, "cg": 0.0, "sg": 0.0, "ig": 0.0, "ces": 0.0}
        for n, it in enumerate(lines, 1):
            tx, ig, cg, sg, ces = (round(_f(it.get(k)), 2) for k in ("txval", "igst", "cgst", "sgst", "cess"))
            qty = _f(it.get("qty")) or 1
            hsn = re.sub(r"\D", "", str(it.get("hsn") or ""))
            items.append({"SlNo": str(n), "PrdDesc": str(it.get("desc") or "Item")[:300], "IsServc": "Y" if hsn.startswith("99") else "N", "HsnCd": hsn,
                          "Qty": qty, "Unit": str(it.get("uqc") or "NOS")[:8], "UnitPrice": round(tx / qty, 3), "TotAmt": tx, "AssAmt": tx,
                          "GstRt": _f(it.get("rate")), "IgstAmt": ig, "CgstAmt": cg, "SgstAmt": sg, "CesAmt": ces, "TotItemVal": round(tx + ig + cg + sg + ces, 2)})
            tot["ass"] += tx; tot["cg"] += cg; tot["sg"] += sg; tot["ig"] += ig; tot["ces"] += ces     # noqa: E702
        val = round(sum(tot.values()), 2)
        rnd = round((d.total or val) - val, 2)
        if abs(rnd) > 1:
            return {"ready": False, "missing": [f"the lines add to Rs {val:g} but the invoice total is Rs {d.total:g} - fix the bill before an IRN"],
                    "doc": {"id": d.id, "number": d.number, "date": d.doc_date}}
        payload = {"Version": "1.1", "TranDtls": {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"},
                   "DocDtls": {"Typ": DOC_TYPE[d.kind], "No": d.number, "Dt": _dmy(d.doc_date)},
                   "SellerDtls": {k: v for k, v in seller.items() if v} | {"Gstin": g},
                   "BuyerDtls": buyer, "ItemList": items,
                   "ValDtls": {"AssVal": round(tot["ass"], 2), "CgstVal": round(tot["cg"], 2), "SgstVal": round(tot["sg"], 2),
                               "IgstVal": round(tot["ig"], 2), "CesVal": round(tot["ces"], 2), "RndOffAmt": rnd, "TotInvVal": round(val + rnd, 2)}}
        info = {"id": d.id, "number": d.number, "date": d.doc_date, "type": DOC_TYPE[d.kind], "total": round(val + rnd, 2), "inter_state": inter,
                "party": buyer["LglNm"], "doc_date": d.doc_date}
    return {"ready": True, "payload": payload, "doc": info, "plan_hash": _hash(payload), "window": window_note(tenant, g, info["doc_date"])}


def _session_info(tenant: str, g: str):
    ensure_tables()
    with session() as s:
        r = _row(s, tenant, g)
        if r is None or not r.einv_username:
            raise EinvError("Connect your e-invoice login first (e-Invoice tab).")
        return r.einv_username, "", r.einv_irp, json.loads(r.einv_seller or "{}")


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def window_note(tenant: str, g: str, doc_date: str) -> dict[str, Any]:
    """The IRP's 30-day report limit applies from Rs 10 crore turnover; below that Hoola shows the age but does not block."""
    aato = 0.0
    try:
        from ..gstp.service import GstClient
        with session() as s:
            c = s.scalars(select(GstClient).where(GstClient.tenant_id == tenant, GstClient.gstin == g)).first()
            aato = float(c.aato or 0) if c else 0.0
    except Exception:   # noqa: BLE001
        pass
    try:
        age = (date.today() - date.fromisoformat(doc_date)).days
    except ValueError:
        age = 0
    return {"age_days": age, "limit_applies": aato >= AATO_30DAY, "days_left": (30 - age) if aato >= AATO_30DAY else None, "aato_known": aato > 0}


# ------------------------------------------------------------------ generate / recover / cancel
def _is_dup(e: wb.WbError) -> bool:
    return "2150" in f"{e.code} {e.detail} {e.message}"


def _adopt(tenant: str, g: str, row_id: str, user: str, tok: str, irp: str, dtype: str, no: str, dt: str) -> bool:
    try:
        env_ = wb.einv_by_doc(tenant, g, user, tok, dtype, no, _dmy(dt), irp=irp)
    except wb.WbError:
        return False
    irn = _find(env_, "Irn")
    if not irn:
        return False
    _save_ok(row_id, env_, irn, irp, adopted=True)
    return True


def _save_ok(row_id: str, env_: dict[str, Any], irn: str, irp: str, adopted: bool = False) -> None:
    with session() as s:
        r = s.get(AccIrn, row_id)
        r.status, r.irn, r.ack_no, r.irp = "generated", irn, _find(env_, "AckNo"), irp
        r.ack_dt = _find(env_, "AckDt")
        r.raw = json.dumps(wb.data_of(env_), default=str)[:20000]
        r.error = "adopted: the IRP had already issued this IRN" if adopted else ""
        r.updated_at = _now()
        s.commit()


def generate(tenant: str, gstin: str, doc_id: str, extra: dict[str, Any] | None, plan: str, confirm: bool) -> dict[str, Any]:
    if confirm is not True:
        raise EinvError("An IRN is issued by the government and can be cancelled only within 24 hours - it needs your confirmation.")
    g = _g(gstin)
    b = build(tenant, g, doc_id, extra)
    if not b["ready"]:
        raise EinvError("Not ready: " + "; ".join(b["missing"]))
    if plan != b["plan_hash"]:
        raise EinvError("The invoice changed since you looked at it - review it again.")
    w = b["window"]
    if w["limit_applies"] and w["days_left"] is not None and w["days_left"] < 0:
        raise EinvError(f"This invoice is {w['age_days']} days old - the IRP does not take invoices older than 30 days at your turnover.")
    doc = b["doc"]
    with session() as s:
        old = s.scalars(select(AccIrn).where(AccIrn.tenant_id == tenant, AccIrn.doc_id == doc_id, AccIrn.status.in_(("generated", "pending", "unknown")))).first()
        if old is not None and old.status == "generated":
            return _view(old) | {"already": True}
        row = old or AccIrn(tenant_id=tenant, gstin=g, doc_id=doc_id)
        row.doc_type, row.doc_no, row.doc_date, row.status, row.error = doc["type"], doc["number"], doc["date"], "pending", ""
        s.add(row)
        s.commit()
        rid = row.id
    user, tok, irp, _ = _session(tenant, g)
    try:
        env_ = wb.einv_generate(tenant, g, user, tok, b["payload"], irp=irp)
    except wb.WbError as e:
        if (_is_dup(e) or e.code == "network") and _adopt(tenant, g, rid, user, tok, irp, doc["type"], doc["number"], doc["date"]):
            return _view_id(rid) | {"adopted": True}
        with session() as s:
            r = s.get(AccIrn, rid)
            r.status = "unknown" if e.code == "network" else "failed"
            r.error = e.message[:500]
            r.updated_at = _now()
            s.commit()
        raise EinvError(e.message if e.code != "network" else "The IRP did not answer. Hoola will check whether it was issued - ask again in a minute; nothing is doubled.") from None
    irn = _find(env_, "Irn")
    if not irn:
        with session() as s:
            r = s.get(AccIrn, rid)
            r.status, r.error, r.raw = "unknown", "reply had no Irn", json.dumps(wb.data_of(env_), default=str)[:20000]
            s.commit()
        raise EinvError("The IRP answered but its reply held no IRN - the reply is saved; ask again to check the portal for it.")
    _save_ok(rid, env_, irn, irp)
    with session() as s:
        REG._event(s, tenant, "irn_generated", f"{g}:{doc['number']}", after={"irn": irn[:16]}, actor="owner")
        s.commit()
    return _view_id(rid)


def _view(r: AccIrn) -> dict[str, Any]:
    hrs = None
    if r.status == "generated" and r.ack_dt:
        t = _parse_ack(r.ack_dt)
        hrs = round(max(0.0, CANCEL_HOURS - (_now() - t).total_seconds() / 3600), 1) if t else None
    return {"id": r.id, "doc_id": r.doc_id, "doc_no": r.doc_no, "doc_date": r.doc_date, "status": r.status, "irn": r.irn, "ack_no": r.ack_no,
            "ack_dt": r.ack_dt, "ewb_no": r.ewb_no, "ewb_dt": r.ewb_dt, "error": r.error, "cancel_hours_left": hrs}


def _view_id(rid: str) -> dict[str, Any]:
    with session() as s:
        return _view(s.get(AccIrn, rid))


def _parse_ack(v: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
        try:
            return datetime.strptime(v.strip()[:19], fmt).replace(tzinfo=timezone(timedelta(hours=5, minutes=30))).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def listing(tenant: str, gstin: str) -> dict[str, Any]:
    g = _g(gstin)
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccIrn).where(AccIrn.tenant_id == tenant, AccIrn.gstin == g).order_by(AccIrn.created_at.desc()).limit(100)).all()
        return {"irns": [_view(r) for r in rows], "watch": watch(tenant, g)}


def watch(tenant: str, gstin: str) -> list[dict[str, Any]]:
    """Sales to registered customers in the last 45 days with no IRN yet - with days left when the 30-day limit applies to her."""
    g = _g(gstin)
    ensure_tables()
    cut = (date.today() - timedelta(days=45)).isoformat()
    with session() as s:
        done = {r.doc_id for r in s.scalars(select(AccIrn).where(AccIrn.tenant_id == tenant, AccIrn.status.in_(("generated", "pending", "unknown")))).all()}
        out = []
        for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "out", AccDoc.doc_date >= cut, AccDoc.status != "gone")).all():
            if d.kind in DOC_TYPE and d.party_gstin and d.gstin in (g, "") and d.id not in done:
                w = window_note(tenant, g, d.doc_date)
                out.append({"doc_id": d.id, "number": d.number, "date": d.doc_date, "party": d.party_name, "total": d.total, **w})
    out.sort(key=lambda x: (x["days_left"] if x["days_left"] is not None else 999, x["date"]))
    return out[:50]


def cancel(tenant: str, irn_id: str, reason: str, remark: str, confirm: bool) -> dict[str, Any]:
    if confirm is not True:
        raise EinvError("Cancelling an IRN is permanent - it needs your confirmation.")
    if reason not in ("1", "2", "3", "4"):
        raise EinvError("Reason: 1 duplicate, 2 data entry mistake, 3 order cancelled, 4 other.")
    with session() as s:
        r = s.get(AccIrn, irn_id)
        if r is None or r.tenant_id != tenant or r.status != "generated":
            raise EinvError("No live IRN found for that.")
        g, irn, irp, ewb, ack = r.gstin, r.irn, r.irp, r.ewb_no, r.ack_dt
    t = _parse_ack(ack)
    if t is not None and (_now() - t) > timedelta(hours=CANCEL_HOURS):
        raise EinvError("The 24-hour window to cancel this IRN has passed. Issue a credit note instead.")
    if ewb:
        raise EinvError("This IRN has an e-way bill. Cancel the e-way bill first (NIC rule 2174), then the IRN.")
    user, tok, irp2, _ = _session(tenant, g)
    try:
        wb.einv_cancel(tenant, g, user, tok, irn, reason, remark or "Cancelled", irp=irp or irp2)
    except wb.WbError as e:
        raise EinvError(e.message) from None
    with session() as s:
        r = s.get(AccIrn, irn_id)
        r.status, r.updated_at = "cancelled", _now()
        REG._event(s, tenant, "irn_cancelled", f"{g}:{r.doc_no}", after={"reason": reason}, actor="owner")
        s.commit()
    return _view_id(irn_id)


# ------------------------------------------------------------------ e-way bill
def ewb_from_irn(tenant: str, irn_id: str, transport: dict[str, Any], confirm: bool) -> dict[str, Any]:
    if confirm is not True:
        raise EinvError("An e-way bill is issued by the government - it needs your confirmation.")
    with session() as s:
        r = s.get(AccIrn, irn_id)
        if r is None or r.tenant_id != tenant or r.status != "generated":
            raise EinvError("Make the IRN first.")
        if r.ewb_no:
            return _view(r) | {"already": True}
        g, irn, irp, dt = r.gstin, r.irn, r.irp, r.doc_date
    try:
        age = (date.today() - date.fromisoformat(dt)).days
    except ValueError:
        age = 0
    if age > 180:
        raise EinvError("An e-way bill cannot be made for a document older than 180 days.")
    dist = transport.get("distance")
    veh = re.sub(r"[^A-Za-z0-9]", "", str(transport.get("vehicle_no") or "")).upper()
    tid = str(transport.get("transporter_gstin") or "").strip().upper()
    if dist in (None, "") or not (veh or tid):
        raise EinvError("Type the distance in km and either the vehicle number or the transporter's GSTIN.")
    body = {"Irn": irn, "Distance": int(dist), "TransMode": str(transport.get("mode") or "1"), "VehNo": veh, "VehType": str(transport.get("vehicle_type") or "R"),
            "TransId": tid, "TransName": str(transport.get("transporter_name") or "")[:100]}
    body = {k: v for k, v in body.items() if v not in ("", None)}
    user, tok, irp2, _ = _session(tenant, g)
    try:
        env_ = wb.einv_ewb_by_irn(tenant, g, user, tok, body, irp=irp or irp2)
    except wb.WbError as e:
        raise EinvError(e.message) from None
    no = _find(env_, "EwbNo")
    if not no:
        raise EinvError("The portal answered without an e-way bill number - check the portal before trying again.")
    with session() as s:
        r = s.get(AccIrn, irn_id)
        r.ewb_no, r.ewb_dt, r.updated_at = no, _find(env_, "EwbDt"), _now()
        REG._event(s, tenant, "ewb_generated", f"{g}:{r.doc_no}", after={"ewb": no}, actor="owner")
        s.commit()
    return _view_id(irn_id)


def ewb_cancel(tenant: str, irn_id: str, reason_code: str, remark: str, confirm: bool) -> dict[str, Any]:
    if confirm is not True:
        raise EinvError("Cancelling an e-way bill is permanent - it needs your confirmation.")
    with session() as s:
        r = s.get(AccIrn, irn_id)
        if r is None or r.tenant_id != tenant or not r.ewb_no:
            raise EinvError("No e-way bill on that IRN.")
        g, no = r.gstin, r.ewb_no
        c = _row(s, tenant, g)
        eu, ep = (c.ewb_username, decrypt(c.ewb_password_enc) or "") if c else ("", "")
    if not (eu and ep):
        raise EinvError("Connect your e-way bill login first (e-Invoice tab).")
    try:
        wb.ewb_auth(tenant, g, eu, ep)
        wb.ewb_cancel(tenant, g, eu, no, reason_code, remark or "Cancelled")
    except wb.WbError as e:
        raise EinvError(e.message) from None
    with session() as s:
        r = s.get(AccIrn, irn_id)
        r.ewb_no, r.updated_at = "", _now()
        REG._event(s, tenant, "ewb_cancelled", f"{g}:{r.doc_no}", actor="owner")
        s.commit()
    return _view_id(irn_id)
