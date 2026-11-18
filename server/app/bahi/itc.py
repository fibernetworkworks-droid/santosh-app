"""v0.834 BAHI A2 - the monthly credit (ITC) loop: pull her GSTR-2B, match it with her purchase register, propose accept / pending /
reject WITH A REASON, and put her decisions on the portal's IMS only on her tap bound to the exact list (plan hash).

Laws: Hoola proposes, she decides; a non-duplicate is never proposed for reject (that is her call); supplier nudges are DRAFTED for her
to send, never sent; every change to the portal is an acc_events row; the session comes from the A1 connection (no token here); the
2B / IMS reply shapes are recorded by wb_check and the IMS body is built to the OpenAPI spec - NOT VERIFIED against a live portal.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import delete, select

from ..db import session
from . import connect as CN
from . import register as REG
from . import wb
from .models import AccDoc, AccTwoB, ensure_tables

TOL = 10.0                       # rupees of tax difference still counted as the same bill
_sleep = time.sleep              # tests replace it
SECTION_IMS = {"b2b": "b2b", "b2ba": "b2ba", "ecom": "ecom", "ecoma": "ecoma"}   # credit / debit notes are split by type below


class ItcError(Exception):
    pass


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _norm(n: str) -> str:
    s = re.sub(r"[^A-Z0-9]", "", str(n or "").upper())
    return re.sub(r"(?<![0-9])0+(?=\d)", "", s)


def _iso(d: str) -> str:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((d or "").strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def _mmyyyy(period: str) -> str:
    p = (period or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return p[5:] + p[:4]
    if re.fullmatch(r"\d{6}", p):
        return p
    raise ItcError("Month as YYYY-MM.")


# ------------------------------------------------------------------ parse + pull
def parse_2b(data: Any) -> list[dict[str, Any]]:
    """GSTN's 2B JSON (docdata.b2b / b2ba / cdnr / cdnra / ecom) -> flat rows. Items nested or flat are both read."""
    d = data if isinstance(data, dict) else {}
    d = d.get("data", d) if isinstance(d.get("data"), dict) else d
    dd = d.get("docdata") if isinstance(d.get("docdata"), dict) else {}
    out: list[dict[str, Any]] = []
    for sec in ("b2b", "b2ba", "cdnr", "cdnra", "ecom"):
        for sup in dd.get(sec) or []:
            for x in (sup.get("inv") or sup.get("nt") or []):
                items = x.get("items") or []
                def tot(k):                 # noqa: E306
                    return sum(_f(i.get(k)) for i in items) if items else _f(x.get(k))
                out.append({"section": sec, "ctin": str(sup.get("ctin") or "").upper(), "trdnm": str(sup.get("trdnm") or ""),
                            "inum": str(x.get("inum") or x.get("ntnum") or ""), "dt": _iso(str(x.get("dt") or "")),
                            "doc_type": str(x.get("typ") or ("R" if sec.startswith("b2b") or sec == "ecom" else "")).upper()[:1],
                            "val": _f(x.get("val")), "txval": tot("txval"), "igst": tot("igst"), "cgst": tot("cgst"), "sgst": tot("sgst"),
                            "cess": tot("cess"),
                            "rev": str(x.get("rev") or "").upper() in ("Y", "YES", "TRUE", "1"),
                            "itcavl": str(x.get("itcavl") or "Y").upper() != "N", "rsn": str(x.get("rsn") or "")[:60],
                            "ext": {"supprd": str(sup.get("supprd") or ""), "pos": str(x.get("pos") or ""), "inv_typ": str(x.get("typ") or "")}})
    return out


def pull(tenant: str, gstin: str, period: str, ip: str = "") -> dict[str, Any]:
    """Read her GSTR-2B for a month through the live connection and keep it (her earlier decisions on the same invoice are kept)."""
    g = gstin.strip().upper()
    rtn = _mmyyyy(period)
    try:
        user, state, txn = CN.session_for(tenant, g)
        rows: list[dict[str, Any]] = []
        files = 1
        n = 0
        while n < files and n < 10:
            n += 1
            env_ = wb.gstr2b_all(tenant, g, rtn, user, state, txn, filenum=n if files > 1 or n > 1 else 0, ip=ip)
            d = wb.data_of(env_)
            dd = d if isinstance(d, dict) else {}
            if n == 1:
                files = int(_f(dd.get("fc") or dd.get("filecount") or (dd.get("data") or {}).get("fc") or 1)) or 1
            rows += parse_2b(d)
    except (CN.ConnectError, wb.WbError) as e:
        raise ItcError(getattr(e, "message", None) or str(e)) from None
    if not rows:
        raise ItcError("GSTN sent no invoices for this month - GSTR-2B may not be generated yet (it is ready around the 14th).")
    ensure_tables()
    with session() as s:
        old = {(r.section, r.ctin, _norm(r.inum)): r for r in s.scalars(select(AccTwoB).where(
            AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn)).all()}
        s.execute(delete(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn))
        kept = 0
        for r in rows:
            prev = old.get((r["section"], r["ctin"], _norm(r["inum"])))
            ext = r.pop("ext")
            row = AccTwoB(tenant_id=tenant, gstin=g, period=rtn, ext=json.dumps(ext), **r)
            if prev is not None:
                row.action, row.applied_at = prev.action, prev.applied_at
                kept += bool(prev.action)
            s.add(row)
        REG._event(s, tenant, "2b_pulled", f"{g}:{rtn}", after={"invoices": len(rows)}, actor="owner")
        s.commit()
    return {"gstin": g, "period": rtn, "invoices": len(rows), "decisions_kept": kept}


# ------------------------------------------------------------------ match + propose
def _books(s, tenant: str, g: str, period: str) -> list[AccDoc]:
    ym = f"{period[2:]}-{period[:2]}"
    y, m = int(ym[:4]), int(ym[5:])
    lo = f"{y - 1}-{m:02d}" if m else ym              # purchases up to a year back can first show in this 2B
    return [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "in", AccDoc.status != "gone",
                                                      AccDoc.period <= ym, AccDoc.period >= lo)).all() if d.gstin in (g, "")]


def _tax(x) -> float:
    return round((x.igst or 0) + (x.cgst or 0) + (x.sgst or 0) or (getattr(x, "tax", 0) or 0), 2)


def propose(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    g = gstin.strip().upper()
    rtn = _mmyyyy(period)
    ensure_tables()
    with session() as s:
        twob = s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn)).all()
        if not twob:
            raise ItcError("Pull this month's GSTR-2B first.")
        books = _books(s, tenant, g, rtn)
        by_key: dict[tuple, list[AccDoc]] = {}
        by_sup: dict[str, list[AccDoc]] = {}
        for b in books:
            by_key.setdefault((b.party_gstin, _norm(b.number)), []).append(b)
            by_sup.setdefault(b.party_gstin, []).append(b)
        used: set[str] = set()
        seen2b: set[tuple] = set()
        rows, groups = [], {"accept": [], "pending": [], "reject": [], "none": []}
        for r in twob:
            tax = round(r.igst + r.cgst + r.sgst, 2)
            base = {"id": r.id, "supplier": r.trdnm or r.ctin, "ctin": r.ctin, "number": r.inum, "date": r.dt, "section": r.section,
                    "type": r.doc_type, "tax": tax, "decided": r.action, "applied": bool(r.applied_at)}
            key = (r.section, r.ctin, _norm(r.inum))
            if r.rev:
                p = ("none", 1.0, "Reverse charge: you pay this tax in cash first (3B 3.1(d)), then take the credit - not an IMS action.")
            elif not r.itcavl:
                p = ("none", 1.0, f"GSTN already marks this credit as not available ({r.rsn or 'reason not given'}).")
            elif key in seen2b:
                p = ("reject", 0.9, "The same invoice number from the same supplier appears twice in your 2B - the second is a duplicate.")
            else:
                seen2b.add(key)
                cand = [b for b in by_key.get((r.ctin, _norm(r.inum)), []) if b.id not in used]
                if cand:
                    b = cand[0]
                    used.add(b.id)
                    diff = round(tax - _tax(b), 2)
                    if abs(diff) <= TOL:
                        p = ("accept", 0.99 if diff == 0 else 0.9, f"Matches your purchase {b.number} ({b.doc_date}) - tax agrees"
                             + ("" if diff == 0 else f" within Rs {TOL:g} (difference Rs {diff:g})") + ".")
                    else:
                        p = ("pending", 0.8, f"Matches your purchase {b.number} but the tax differs by Rs {diff:g} (2B Rs {tax:g}, your books Rs {_tax(b):g}) - ask the supplier to correct it.")
                else:
                    like = [b for b in by_sup.get(r.ctin, []) if b.id not in used and abs(_tax(b) - tax) <= TOL and tax > 0]
                    if like:
                        used.add(like[0].id)
                        p = ("pending", 0.7, f"Not found under this number, but you have {like[0].number} ({like[0].doc_date}) from the same supplier with the same tax - "
                             "probably a numbering difference. Confirm, then accept.")
                    else:
                        p = ("pending", 0.5, "Not in your purchase register. If you did not receive these goods / services, or the bill is not yours, tell Hoola - "
                             "rejecting is always your decision.")
            base.update(proposal=p[0], confidence=p[1], reason=p[2])
            rows.append(base)
            groups[p[0]].append(base)
            if r.reason != p[2]:
                r.reason = p[2]
        s.commit()
        absent = []
        for b in books:
            if b.id in used or not b.party_gstin or (b.party_gstin, _norm(b.number)) in {(x["ctin"], _norm(x["number"])) for x in rows}:
                continue
            if b.direction == "in" and _tax(b) > 0:
                absent.append({"doc_id": b.id, "supplier": b.party_name or b.party_gstin, "ctin": b.party_gstin, "number": b.number,
                               "date": b.doc_date, "tax": _tax(b), "nudge": nudge_text(b, rtn)})
    tx = lambda k: round(sum(x["tax"] for x in groups[k]), 2)   # noqa: E731
    return {"gstin": g, "period": rtn, "rows": rows,
            "groups": {k: {"count": len(v), "tax": tx(k), "ids": [x["id"] for x in v]} for k, v in groups.items()},
            "missing_in_2b": absent, "itc_at_stake_missing": round(sum(x["tax"] for x in absent), 2),
            "note": "Accepted credit appears in GSTR-2B; pending / rejected does not. Act before the return is filed; a change after the 14th needs a 2B recompute."}


def nudge_text(b: AccDoc, rtn: str) -> dict[str, str]:
    msg = (f"Hello {b.party_name or 'team'}, your invoice {b.number} dated {b.doc_date} (tax Rs {_tax(b):g}) is not showing in our GSTR-2B "
           f"for {rtn[:2]}/{rtn[2:]}. Please check it was reported in your GSTR-1 and filed. Thank you.")
    return {"text": msg, "wa_link": "https://wa.me/?text=" + quote(msg)}      # she picks the contact and sends it; Hoola sends nothing


# ------------------------------------------------------------------ her decision, then the portal
def decide(tenant: str, gstin: str, period: str, decisions: dict[str, str]) -> dict[str, Any]:
    g, rtn = gstin.strip().upper(), _mmyyyy(period)
    n = 0
    with session() as s:
        for rid, act in (decisions or {}).items():
            act = str(act).lower()
            if act not in ("accept", "reject", "pending", ""):
                raise ItcError("Action must be accept, reject or pending.")
            r = s.get(AccTwoB, rid)
            if r is not None and r.tenant_id == tenant and r.gstin == g and r.period == rtn and not r.applied_at:
                r.action = act
                n += 1
        REG._event(s, tenant, "ims_decided", f"{g}:{rtn}", after={"rows": n}, actor="owner")
        s.commit()
    return {"updated": n}


def _ready(s, tenant: str, g: str, rtn: str) -> list[AccTwoB]:
    return [r for r in s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn,
                                                      AccTwoB.action != "")).all() if not r.applied_at]


def plan_hash(rows: list[AccTwoB], g: str, rtn: str) -> str:
    return hashlib.sha256(json.dumps([g, rtn, sorted((r.id, r.action) for r in rows)]).encode()).hexdigest()[:20]


def _body(rows: list[AccTwoB], g: str) -> dict[str, Any]:
    inv: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        ext = json.loads(r.ext or "{}")
        sec = SECTION_IMS.get(r.section) or ("b2bcn" if r.section == "cdnr" and r.doc_type == "C" else "b2bdn" if r.section == "cdnr" else "")
        if not sec:
            continue
        idt = datetime.strptime(r.dt, "%Y-%m-%d").strftime("%d-%m-%Y") if r.dt else ""
        inv.setdefault(sec, []).append({"stin": r.ctin, "rtnprd": ext.get("supprd", ""), "srcform": "GSTR1", "inum": r.inum, "idt": idt,
                                        "inv_typ": ext.get("inv_typ", "R") or "R", "pos": ext.get("pos", ""), "val": r.val, "txval": r.txval,
                                        "iamt": r.igst, "camt": r.cgst, "samt": r.sgst, "cess": r.cess,
                                        "action": {"accept": "A", "reject": "R", "pending": "P"}[r.action], "prev_status": ""})
    return {"rtin": g, "reqtyp": "SAVE", "invdata": inv}


def preview(tenant: str, gstin: str, period: str) -> dict[str, Any]:
    g, rtn = gstin.strip().upper(), _mmyyyy(period)
    ensure_tables()
    with session() as s:
        rows = _ready(s, tenant, g, rtn)
        counts = {a: sum(1 for r in rows if r.action == a) for a in ("accept", "reject", "pending")}
        return {"gstin": g, "period": rtn, "will_send": len(rows), "counts": counts, "plan_hash": plan_hash(rows, g, rtn),
                "says": "Nothing is sent until you confirm this exact list on the apply step."}


def apply(tenant: str, gstin: str, period: str, plan: str, confirm: bool, ip: str = "") -> dict[str, Any]:
    """Send her decided rows to the portal's IMS. Needs her confirm AND the plan hash of exactly this list."""
    if confirm is not True:
        raise ItcError("This changes your GST portal - it needs your confirmation.")
    g, rtn = gstin.strip().upper(), _mmyyyy(period)
    ensure_tables()
    with session() as s:
        rows = _ready(s, tenant, g, rtn)
        if not rows:
            raise ItcError("No decisions waiting to be sent.")
        if plan != plan_hash(rows, g, rtn):
            raise ItcError("The list changed since you looked at it - review it again.")
        body = _body(rows, g)
        ids = [r.id for r in rows]
    if not body["invdata"]:
        raise ItcError("None of these invoice types can be sent to IMS yet.")
    try:
        user, state, txn = CN.session_for(tenant, g)
        env_ = wb.ims_save(tenant, g, rtn, body, user, state, txn, ip=ip)
    except (CN.ConnectError, wb.WbError) as e:
        raise ItcError(getattr(e, "message", None) or str(e)) from None
    tid = _find(env_, "int_tran_id")
    now_s = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with session() as s:
        for rid in ids:
            r = s.get(AccTwoB, rid)
            r.applied_at = now_s
        REG._event(s, tenant, "ims_saved", f"{g}:{rtn}", after={"rows": len(ids), "int_tran_id": tid}, actor="owner")
        s.commit()
    out: dict[str, Any] = {"sent": len(ids), "int_tran_id": tid, "portal_status": "", "recompute": ""}
    try:
        if tid:
            _sleep(1)
            out["portal_status"] = _words(wb.data_of(wb.ims_status(tenant, g, tid, user, state, txn, ip=ip)))
        g2 = wb.gen2b(tenant, g, rtn, user, state, txn, ip=ip)
        out["recompute"] = "asked"
        out["recompute_id"] = _find(g2, "int_tran_id")
    except wb.WbError as e:
        out["recompute"] = f"not asked: {e.message}"
    return out


def _find(env_: Any, key: str) -> str:
    stack = [env_, wb.data_of(env_) if isinstance(env_, dict) else None]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            if x.get(key):
                return str(x[key])
            stack += [v for v in x.values() if isinstance(v, (dict, list))]
        elif isinstance(x, list):
            stack += [v for v in x[:5] if isinstance(v, (dict, list))]
    return ""


def _words(d: Any) -> str:
    """A portal status reply reduced to a short line of its own status words (no invoice data)."""
    out = []
    stack = [d]
    while stack and len(out) < 4:
        x = stack.pop()
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    stack.append(v)
                elif "status" in k.lower() or k.lower() in ("message", "msg"):
                    out.append(f"{k}: {str(v)[:60]}")
        elif isinstance(x, list) and x:
            stack.append(x[0])
    return "; ".join(out)
