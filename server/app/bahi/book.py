"""v0.848 BAHI A9 - her book and the CA hand-off.

Tally: the register becomes Tally voucher XML (Sales, Credit Note, Purchase, Debit Note, Receipt, Payment) with the GST tax ledgers, party ledgers created in the
same file, and ledger names that are HERS (Tally imports into ledgers that exist). A JSON copy of the same vouchers is made for Zoho-style imports.
The monthly CA pack is one ZIP: the vouchers, the register, the source bills she sent, the GSTR-1 / 2B / 3B worksheets, the bank reconciliation, the TDS register and
an OPEN QUESTIONS page - everything Hoola was not sure of. She closes the month on the pack's hash, which locks it in the register.
NOT BUILT: Zoho Books over OAuth (read the chart of accounts, write drafts), live Tally (the bridge is frozen PC code), a CA login that closes a month (A11).
NOT VERIFIED: a real Tally import - the file follows Tally's documented voucher import and the existing app export, but has not been loaded into her Tally.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from sqlalchemy import select

from ..db import session
from . import register as REG
from .models import (AccBankLine, AccBookCfg, AccDoc, AccIntake, AccPack, AccParty, AccTds, AccTwoB, ensure_tables)

DEFAULTS = {"sales": "Sales", "purchase": "Purchase", "bank": "Bank Account", "round": "Round Off", "cgst_out": "Output CGST", "sgst_out": "Output SGST",
            "igst_out": "Output IGST", "cess_out": "Output Cess", "cgst_in": "Input CGST", "sgst_in": "Input SGST", "igst_in": "Input IGST", "cess_in": "Input Cess"}
PACK_DIR = Path("data") / "bahi" / "packs"


class BookError(Exception):
    pass


def ledgers(tenant: str) -> dict[str, str]:
    ensure_tables()
    with session() as s:
        row = s.scalars(select(AccBookCfg).where(AccBookCfg.tenant_id == tenant)).first()
        saved = json.loads(row.ledgers) if row else {}
    return {**DEFAULTS, **{k: v for k, v in saved.items() if k in DEFAULTS and v}}


def set_ledgers(tenant: str, body: dict[str, Any]) -> dict[str, str]:
    clean = {k: re.sub(r"[\x00-\x1f<>&\"]+", " ", str(v or "")).strip()[:60] for k, v in (body or {}).items() if k in DEFAULTS and str(v or "").strip()}
    ensure_tables()
    with session() as s:
        row = s.scalars(select(AccBookCfg).where(AccBookCfg.tenant_id == tenant)).first()
        if row is None:
            row = AccBookCfg(tenant_id=tenant)
            s.add(row)
        row.ledgers = json.dumps({**json.loads(row.ledgers or "{}"), **clean})
        s.commit()
    return ledgers(tenant)


# ------------------------------------------------------------------ vouchers
def _ymd(day: str) -> str:
    return (day or "").replace("-", "")[:8]


def _entry(ledger: str, amount: float, debit: bool) -> str:
    a = -abs(amount) if debit else abs(amount)        # Tally: a debit is ISDEEMEDPOSITIVE Yes with a negative amount
    return (f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(ledger)}</LEDGERNAME><ISDEEMEDPOSITIVE>{'Yes' if debit else 'No'}</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{a:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")


def _taxes(d: AccDoc, mine_state: str) -> dict[str, float]:
    cg, sg, ig, ce = d.cgst or 0.0, d.sgst or 0.0, d.igst or 0.0, d.cess or 0.0
    lump = d.tax or (round((d.total or 0) - (d.taxable or 0), 2) if d.taxable and (d.total or 0) - d.taxable > 1 else 0.0)   # tax known only as a lump
    if not (cg or sg or ig) and lump:
        inter = bool(d.party_gstin and mine_state and d.party_gstin[:2] != mine_state)
        if inter:
            ig = lump
        else:
            cg = sg = round(lump / 2, 2)
    return {"cgst": round(cg, 2), "sgst": round(sg, 2), "igst": round(ig, 2), "cess": round(ce, 2)}


def _vtype(d: AccDoc) -> tuple[str, bool]:
    """(Tally voucher type, is it a sale-side voucher)."""
    if d.direction == "out":
        return ("Credit Note" if d.kind == "cn" else "Sales"), True
    return ("Debit Note" if d.kind == "cn" else "Purchase"), False


def voucher_of(d: AccDoc, ln: dict[str, str], mine_state: str) -> dict[str, Any]:
    vt, sale_side = _vtype(d)
    tx = _taxes(d, mine_state)
    total = round(d.total or 0.0, 2)
    taxable = round(d.taxable or max(0.0, total - sum(tx.values())), 2)
    flip = d.kind == "cn"                                        # a credit / debit note is the mirror image
    party_dr = (sale_side and not flip) or (not sale_side and flip)      # sales: party Dr; purchase: party Cr; notes reverse
    base = ln["sales"] if sale_side else ln["purchase"]
    suffix = "out" if sale_side else "in"
    rows = [(d.party_name or "Cash", total, party_dr), (base, taxable, not party_dr)]
    for k in ("cgst", "sgst", "igst", "cess"):
        if tx[k]:
            rows.append((ln[f"{k}_{suffix}"], tx[k], not party_dr))
    diff = round(total - taxable - sum(tx.values()), 2)
    if diff:
        rows.append((ln["round"], diff, not party_dr))
    return {"type": vt, "number": d.number, "date": d.doc_date, "party": d.party_name or "Cash", "gstin": d.party_gstin, "rows": rows,
            "narration": f"{vt} {d.number} - {d.reason[:80] if d.reason else 'from your register'} [{d.source}]", "ref": d.id}


def voucher_of_line(l: AccBankLine, d: AccDoc, ln: dict[str, str]) -> dict[str, Any]:
    receipt = l.credit > 0
    amt = l.credit or l.debit
    party = d.party_name or "Cash"
    rows = [(ln["bank"], amt, receipt), (party, amt, not receipt)]
    return {"type": "Receipt" if receipt else "Payment", "number": f"BK-{l.id[-6:]}", "date": l.date, "party": party, "gstin": d.party_gstin, "rows": rows,
            "narration": f"{'Received' if receipt else 'Paid'} against {d.number} ({l.mode.upper()} {l.ref})".strip(), "ref": l.id}


def to_xml(vs: list[dict[str, Any]]) -> str:
    masters = []
    seen = set()
    for v in vs:
        if v["party"] not in seen and v["type"] in ("Sales", "Credit Note", "Purchase", "Debit Note", "Receipt", "Payment"):
            seen.add(v["party"])
            parent = "Sundry Debtors" if v["type"] in ("Sales", "Credit Note", "Receipt") else "Sundry Creditors"
            masters.append(f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME="{escape(v["party"])}" ACTION="Create"><NAME>{escape(v["party"])}</NAME>'
                           f'<PARENT>{parent}</PARENT>' + (f'<PARTYGSTIN>{escape(v["gstin"])}</PARTYGSTIN>' if v.get("gstin") else "") + "</LEDGER></TALLYMESSAGE>")
    body = []
    for v in vs:
        body.append(f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="{v["type"]}" ACTION="Create" OBJVIEW="Accounting Voucher View"><DATE>{_ymd(v["date"])}</DATE>'
                    f'<VOUCHERTYPENAME>{v["type"]}</VOUCHERTYPENAME><VOUCHERNUMBER>{escape(v["number"])}</VOUCHERNUMBER><PARTYLEDGERNAME>{escape(v["party"])}</PARTYLEDGERNAME>'
                    + (f'<PARTYGSTIN>{escape(v["gstin"])}</PARTYGSTIN>' if v.get("gstin") else "")
                    + f'<NARRATION>{escape(v["narration"][:240])}</NARRATION><PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>'
                    + "".join(_entry(n, a, dr) for n, a, dr in v["rows"]) + "</VOUCHER></TALLYMESSAGE>")
    return ('<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC><REQUESTDATA>'
            + "".join(masters) + "".join(body) + "</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")


def vouchers(tenant: str, gstin: str, month: str) -> list[dict[str, Any]]:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise BookError("Month as YYYY-MM.")
    ln = ledgers(tenant)
    ensure_tables()
    with session() as s:
        docs = [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period == month, AccDoc.status != "gone").order_by(AccDoc.doc_date, AccDoc.number)).all()
                if d.gstin in (gstin, "") and d.kind in ("inv", "bill", "cn", "dn") and (d.total or 0) > 0]
        out = [voucher_of(d, ln, gstin[:2]) for d in docs]
        by_id = {d.id: d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant)).all()}
        for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.status == "matched", AccBankLine.date.like(month + "%"))).all():
            d = by_id.get(l.match_doc_id)
            if d is not None:
                out.append(voucher_of_line(l, d, ln))
    return out


# ------------------------------------------------------------------ the CA pack
def _csv(rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def _questions(tenant: str, gstin: str, month: str) -> list[str]:
    q: list[str] = []
    ensure_tables()
    with session() as s:
        for r in s.scalars(select(AccIntake).where(AccIntake.tenant_id == tenant, AccIntake.status == "draft")).all():
            f = json.loads(r.fields or "{}")
            q.append(f"Bill {f.get('number') or '(no number)'} from {f.get('party_name') or f.get('supplier_gstin') or 'unknown'} is a draft - not yet in the books.")
        for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.date.like(month + "%"), AccBankLine.status.in_(("open", "proposed")))).all():
            q.append(f"Bank line {l.date} Rs {l.credit or l.debit:g} '{l.narration[:50]}' is {'matched but not confirmed' if l.status == 'proposed' else 'not matched to any document'}.")
        for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period == month, AccDoc.status != "gone")).all():
            if d.problems and d.problems != "[]":
                q.append(f"{d.number} ({d.party_name}): " + "; ".join(json.loads(d.problems)[:2]))
            if d.source == "intake" and "accepted by you" in (d.reason or ""):
                q.append(f"Bill {d.number} was added with checks she accepted: {d.reason[:160]}")
        for t in s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == gstin, AccTwoB.period == month[5:] + month[:4], AccTwoB.action == "")).all():
            q.append(f"2B invoice {t.inum} from {t.trdnm or t.ctin} has no accept / pending / reject decision.")
        for t in s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.paid_on.like(month + "%"), AccTds.deposited_on == "")).all():
            q.append(f"TDS Rs {t.tds:g} on {t.party_name} ({t.section}) is recorded but not deposited (due {t.due_on}).")
    return q[:200]


def build_pack(tenant: str, gstin: str, month: str) -> dict[str, Any]:
    from ..appmaker.gst import valid_gstin
    g = (gstin or "").strip().upper()
    if not valid_gstin(g):
        raise BookError("That is not a valid GSTIN (shape or check digit).")
    vs = vouchers(tenant, g, month)
    xml = to_xml(vs)
    ensure_tables()
    files: dict[str, str] = {}
    files["vouchers/tally-vouchers.xml"] = xml
    files["vouchers/vouchers.json"] = json.dumps([{**v, "rows": [{"ledger": n, "amount": a, "debit": dr} for n, a, dr in v["rows"]]} for v in vs], indent=1)
    with session() as s:
        docs = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period == month).order_by(AccDoc.direction, AccDoc.doc_date)).all()
        files["register.csv"] = _csv([["direction", "kind", "number", "date", "party", "party_gstin", "taxable", "cgst", "sgst", "igst", "cess", "total", "source", "status", "confidence"]]
                                     + [[d.direction, d.kind, d.number, d.doc_date, d.party_name, d.party_gstin, d.taxable, d.cgst, d.sgst, d.igst, d.cess, d.total, d.source, d.status, d.confidence] for d in docs])
        files["parties.csv"] = _csv([["name", "gstin", "pan", "pan_valid", "msme", "agreed_days"]]
                                    + [[p.name, p.gstin, p.pan, p.pan_ok, p.msme_class, p.agreed_days] for p in s.scalars(select(AccParty).where(AccParty.tenant_id == tenant)).all()])
        rtn = month[5:] + month[:4]
        files["worksheets/gstr2b.csv"] = _csv([["section", "supplier", "gstin", "invoice", "date", "taxable", "igst", "cgst", "sgst", "itc_available", "your_decision", "applied_to_portal", "reason"]]
                                              + [[t.section, t.trdnm, t.ctin, t.inum, t.dt, t.txval, t.igst, t.cgst, t.sgst, t.itcavl, t.action, bool(t.applied_at), t.reason] for t in
                                                 s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn)).all()])
        try:
            from ..gstp.service import GstClient, GstReturn
            c = s.scalars(select(GstClient).where(GstClient.tenant_id == tenant, GstClient.gstin == g)).first()
            if c is not None:
                for kind, name in (("gstr1", "gstr1"), ("gstr3b", "gstr3b")):
                    r = s.scalars(select(GstReturn).where(GstReturn.tenant_id == tenant, GstReturn.client_id == c.id, GstReturn.period == month, GstReturn.kind == kind)).first()
                    if r is not None:
                        files[f"worksheets/{name}-summary.json"] = r.data or "{}"
                        if r.portal_json:
                            files[f"worksheets/{name}-portal.json"] = r.portal_json
                        files[f"worksheets/{name}-checks.json"] = r.checks or "[]"
        except Exception:   # noqa: BLE001
            pass
        from .models import AccBankRecon
        rec = s.scalars(select(AccBankRecon).where(AccBankRecon.tenant_id == tenant, AccBankRecon.month == month)).first()
        files["bank-reconciliation.json"] = rec.body if rec else json.dumps({"note": "No stored bank reconciliation for this month - run it on the Bank tab."})
        files["tds-register.csv"] = _csv([["party", "pan", "section", "paid_on", "base", "rate", "tds", "due_on", "deposited_on", "challan"]]
                                         + [[t.party_name, t.pan, t.section, t.paid_on, t.base, t.rate, t.tds, t.due_on, t.deposited_on, t.challan] for t in
                                            s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.paid_on.like(month + "%"))).all()])
        sources, missing = [], 0
        for r in s.scalars(select(AccIntake).where(AccIntake.tenant_id == tenant, AccIntake.status == "confirmed", AccIntake.file_id != "")).all():
            d = s.get(AccDoc, r.doc_id)
            if d is None or d.period != month:
                continue
            try:
                from ..gstp.service import _load_file
                name, data = _load_file(tenant, r.file_id)
                files[f"source-documents/{re.sub(r'[^A-Za-z0-9._-]', '_', d.number or r.id)}-{re.sub(r'[^A-Za-z0-9._-]', '_', name)[:60]}"] = data
                sources.append(d.number)
            except Exception:   # noqa: BLE001
                missing += 1
    qs = _questions(tenant, g, month)
    files["OPEN-QUESTIONS.txt"] = (f"Open questions for {g}, {month}\n\n" + ("\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1)) if qs else "None - everything Hoola handled this month was settled.")
                                   + ("\n\nNote: %d bill file(s) could not be attached (no longer stored)." % missing if missing else ""))
    counts = {"vouchers": len(vs), "documents": len(docs), "source_files": len(sources), "open_questions": len(qs)}
    files["README.txt"] = (f"Hoola monthly CA pack - {g} - {month}\n\nvouchers/tally-vouchers.xml : Gateway of Tally > Import > Vouchers. Create these ledgers first (names are set in Hoola): "
                           + ", ".join(sorted(set(ledgers(tenant).values()))) + ".\nvouchers/vouchers.json : the same vouchers as data.\nregister.csv, parties.csv : the books and the parties.\n"
                           "worksheets/ : GSTR-1, 2B (with the owner's accept / pending / reject), 3B as Hoola prepared them. They are worksheets, not filed returns.\n"
                           "bank-reconciliation.json, tds-register.csv, source-documents/ : the evidence.\nOPEN-QUESTIONS.txt : what Hoola was not sure of.\n\n"
                           f"Counts: {json.dumps(counts)}\nHoola prepares; the CA decides. Nothing in this pack was filed or paid by Hoola.\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))     # fixed stamp: the same books always give the same zip, so the hash means something
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, files[name])
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    path = PACK_DIR / re.sub(r"[^A-Za-z0-9_-]", "_", tenant) / f"{g}-{month}-{sha[:12]}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    with session() as s:
        row = s.scalars(select(AccPack).where(AccPack.tenant_id == tenant, AccPack.sha == sha)).first()
        if row is None:
            row = AccPack(tenant_id=tenant, gstin=g, month=month, sha=sha, path=str(path), counts=json.dumps(counts), open_questions=len(qs))
            s.add(row)
            REG._event(s, tenant, "ca_pack_built", f"{g}:{month}", after={"sha": sha[:12], **counts}, actor="owner")
        s.commit()
        return _pack_view(row)


def _pack_view(r: AccPack) -> dict[str, Any]:
    return {"id": r.id, "gstin": r.gstin, "month": r.month, "sha": r.sha, "counts": json.loads(r.counts or "{}"), "open_questions": r.open_questions,
            "closed_at": r.closed_at, "closed_by": r.closed_by, "created_at": r.created_at.isoformat() if r.created_at else ""}


def packs(tenant: str, month: str = "") -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(AccPack).where(AccPack.tenant_id == tenant).order_by(AccPack.created_at.desc()).limit(60)
        if month:
            q = q.where(AccPack.month == month)
        return [_pack_view(r) for r in s.scalars(q).all()]


def pack_bytes(tenant: str, pack_id: str) -> tuple[str, bytes]:
    with session() as s:
        r = s.get(AccPack, pack_id)
        if r is None or r.tenant_id != tenant:
            raise BookError("That pack was not found.")
        p = Path(r.path)
        if not p.is_file():
            raise BookError("That pack's file is no longer stored - build it again.")
        return p.name, p.read_bytes()


def close_month(tenant: str, pack_id: str, sha: str, confirm: bool, by: str = "owner") -> dict[str, Any]:
    """Mark the month CLOSED on the exact pack she (or her CA) reviewed: the month locks in the register, so later changes are held as amendments."""
    if confirm is not True:
        raise BookError("Closing a month locks it - it needs your confirmation.")
    ensure_tables()
    with session() as s:
        r = s.get(AccPack, pack_id)
        if r is None or r.tenant_id != tenant:
            raise BookError("That pack was not found.")
        if r.sha != sha:
            raise BookError("The pack changed - review the latest one.")
        g, month = r.gstin, r.month
    REG.set_lock(tenant, month, True, gstin=g, by=by, note=f"Closed on pack {sha[:12]}")
    with session() as s:
        r = s.get(AccPack, pack_id)
        r.closed_at, r.closed_by = datetime.now().isoformat(timespec="seconds"), by
        s.commit()
        return _pack_view(r)
