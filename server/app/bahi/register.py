"""The register (plan law 1): every document ONCE, whichever engine made it.

The seven engines keep working exactly as they do; this only READS them (adapters) and writes `acc_docs`:
- gst_sahayak  gstp's sales + purchase documents (gst_docs)                       - both directions, tax split
- thok         wholesale bills (billed orders) + purchase bills                    - tax total, split by intra / inter
- office       vendor bills (office_bills)                                         - purchases, GST total only
- app          GST tax invoices + credit notes of her Hoola-built app + website    - via hisaab.build (same numbers the CA gets)
A row is keyed by (source, source_ref), so a re-sync updates instead of duplicating. The same invoice arriving from TWO sources
(e.g. a thok bill also typed into GST Sahayak) is FLAGGED on both rows, never merged silently. A document in a LOCKED month is never
overwritten: the change is recorded in the trail and flagged for an amendment instead (plan law 5). Nothing here touches the sources.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import func, select

from ..db import now, session
from .models import AccDoc, AccEvent, AccPeriod, ensure_tables

log = logging.getLogger("bahi.register")

FIELDS = ("gstin", "period", "direction", "kind", "number", "doc_date", "party_name", "party_gstin", "pos",
          "taxable", "cgst", "sgst", "igst", "cess", "tax", "total", "irn")
SOURCES = {"gst_sahayak": "GST Sahayak", "thok": "Wholesale (Thok)", "office": "Office bills", "app": "Your app + website"}
PERIOD = re.compile(r"^\d{4}-\d{2}$")


class RegisterError(Exception):
    pass


def months_back(n: int = 3, today: date | None = None) -> list[str]:
    t = today or date.today()
    out, y, m = [], t.year, t.month
    for _ in range(max(1, n)):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def _period_of(day: str) -> str:
    return str(day or "")[:7] if re.match(r"^\d{4}-\d{2}", str(day or "")) else ""


def _r2(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _num(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def _fp(d: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps({k: d.get(k) for k in FIELDS}, sort_keys=True, default=str).encode()).hexdigest()[:32]


def _split(tax: float, intra: bool) -> dict[str, float]:
    if intra:
        h = round(tax / 2, 2)
        return {"cgst": h, "sgst": round(tax - h, 2), "igst": 0.0}
    return {"cgst": 0.0, "sgst": 0.0, "igst": round(tax, 2)}


# ------------------------------------------------------------------ adapters (read-only)
def _from_gstp(tenant: str, months: list[str]) -> list[dict[str, Any]]:
    from ..gstp.service import GstClient, GstDoc
    out = []
    with session() as s:
        clients = {c.id: c for c in s.scalars(select(GstClient).where(GstClient.tenant_id == tenant)).all()}
        for d in s.scalars(select(GstDoc).where(GstDoc.tenant_id == tenant, GstDoc.period.in_(months))).all():
            c = clients.get(d.client_id)
            tax = _r2(d.cgst) + _r2(d.sgst) + _r2(d.igst) + _r2(d.cess)
            out.append({"source": "gst_sahayak", "source_ref": d.id, "gstin": (c.gstin if c else "") or "", "period": d.period,
                        "direction": "in" if d.direction == "in" else "out", "kind": d.kind or "inv", "number": d.number,
                        "doc_date": d.doc_date, "party_name": d.party_name, "party_gstin": d.party_gstin, "pos": d.pos,
                        "taxable": _r2(d.txval), "cgst": _r2(d.cgst), "sgst": _r2(d.sgst), "igst": _r2(d.igst), "cess": _r2(d.cess),
                        "tax": round(tax, 2), "total": _r2(d.value) or round(_r2(d.txval) + tax, 2), "irn": d.irn or "",
                        "reason": f"GST Sahayak {'purchase' if d.direction == 'in' else 'sale'} entry ({d.source or 'manual'})"})
    return out


def _from_thok(tenant: str, months: list[str]) -> list[dict[str, Any]]:
    from ..thok.service import ThokOrder, ThokParty, ThokPurchase, ThokSettings
    out = []
    with session() as s:
        st = s.get(ThokSettings, tenant)
        own = (st.gstin if st else "") or ""
        own_state = (st.state if st else "") or ""
        parties = {p.id: p for p in s.scalars(select(ThokParty).where(ThokParty.tenant_id == tenant)).all()}
        for o in s.scalars(select(ThokOrder).where(ThokOrder.tenant_id == tenant, ThokOrder.status == "billed")).all():
            per = _period_of(o.bill_date)
            if per not in months:
                continue
            p = parties.get(o.party_id)
            out.append({"source": "thok", "source_ref": o.id, "gstin": own, "period": per, "direction": "out", "kind": "inv",
                        "number": o.number, "doc_date": o.bill_date, "party_name": p.name if p else "", "party_gstin": (p.gstin if p else ""),
                        "pos": (p.state if p and p.state else own_state), "taxable": _r2(o.taxable), **_split(_r2(o.tax), bool(o.intra)),
                        "cess": 0.0, "tax": _r2(o.tax), "total": _r2(o.total), "irn": "", "reason": "Wholesale bill (Thok)"})
        for b in s.scalars(select(ThokPurchase).where(ThokPurchase.tenant_id == tenant)).all():
            per = _period_of(b.bill_date)
            if per not in months:
                continue
            p = parties.get(b.supplier_id)
            intra = not (p and p.state and own_state and p.state != own_state)
            out.append({"source": "thok", "source_ref": b.id, "gstin": own, "period": per, "direction": "in", "kind": "bill",
                        "number": b.bill_no, "doc_date": b.bill_date, "party_name": p.name if p else "", "party_gstin": (p.gstin if p else ""),
                        "pos": own_state, "taxable": _r2(b.taxable), **_split(_r2(b.tax), intra), "cess": 0.0, "tax": _r2(b.tax),
                        "total": _r2(b.total), "irn": "", "reason": "Wholesale purchase bill (Thok)"})
    return out


def _from_office(tenant: str, months: list[str]) -> list[dict[str, Any]]:
    from ..office.service import OfficeBill, OfficeVendor
    out = []
    with session() as s:
        vendors = {v.id: v for v in s.scalars(select(OfficeVendor).where(OfficeVendor.tenant_id == tenant)).all()}
        for b in s.scalars(select(OfficeBill).where(OfficeBill.tenant_id == tenant)).all():
            per = _period_of(b.bill_date)
            if per not in months:
                continue
            v = vendors.get(b.vendor_id)
            total, tax = _r2(b.amount_paise / 100), _r2(b.gst_paise / 100)
            out.append({"source": "office", "source_ref": b.id, "gstin": "", "period": per, "direction": "in", "kind": "bill",
                        "number": b.number, "doc_date": b.bill_date, "party_name": v.name if v else "", "party_gstin": ((v.gstin or "")[:15] if v else ""),
                        "pos": "", "taxable": round(total - tax, 2), "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "cess": 0.0, "tax": tax,
                        "total": total, "irn": "", "reason": f"Office vendor bill{' - ' + b.what if b.what else ''}"[:200]})
    return out


def _from_app(tenant: str, months: list[str]) -> list[dict[str, Any]]:
    from ..appmaker import gst as G
    from ..appmaker import hisaab as H
    from ..appmaker.models import AppProject
    out = []
    with session() as s:
        apps = s.scalars(select(AppProject).where(AppProject.tenant_id == tenant)).all()
        for a in apps:
            s.expunge(a)
    for a in apps:
        try:
            if not G.on(a):
                continue
            own = str(G.settings(a).get("gstin") or "")
            for m in months:
                h = H.build(a, m)
                for row in h["invoices"]:    # no, date, customer, buyer gstin, "pos-name", taxable, cgst, sgst, igst, value
                    out.append({"source": "app", "source_ref": f"{a.id}:inv:{row[0]}", "gstin": own, "period": m, "direction": "out",
                                "kind": "inv", "number": row[0], "doc_date": row[1], "party_name": row[2], "party_gstin": row[3] or "",
                                "pos": str(row[4]).split("-")[0][:2], "taxable": _r2(row[5]), "cgst": _r2(row[6]), "sgst": _r2(row[7]),
                                "igst": _r2(row[8]), "cess": 0.0, "tax": round(_r2(row[6]) + _r2(row[7]) + _r2(row[8]), 2), "total": _r2(row[9]),
                                "irn": "", "reason": f"Tax invoice from your app '{a.name}'"[:200]})
                for row in h["credit_notes"]:   # no, date, against inv, inv date, customer, reason, taxable, cgst, sgst, igst, value
                    out.append({"source": "app", "source_ref": f"{a.id}:cn:{row[0]}", "gstin": own, "period": m, "direction": "out",
                                "kind": "cn", "number": row[0], "doc_date": row[1], "party_name": row[4], "party_gstin": "",
                                "pos": "", "taxable": _r2(row[6]), "cgst": _r2(row[7]), "sgst": _r2(row[8]), "igst": _r2(row[9]), "cess": 0.0,
                                "tax": round(_r2(row[7]) + _r2(row[8]) + _r2(row[9]), 2), "total": _r2(row[10]), "irn": "",
                                "reason": f"Credit note against {row[2]} from your app '{a.name}'"[:200]})
        except Exception as e:   # noqa: BLE001 - one app with odd data never stops the others
            log.warning("bahi app adapter skipped %s: %s", a.id, e)
    return out


ADAPTERS: dict[str, Callable[[str, list[str]], list[dict[str, Any]]]] = {
    "gst_sahayak": _from_gstp, "thok": _from_thok, "office": _from_office, "app": _from_app}


# ------------------------------------------------------------------ locks + trail
def locked(s, tenant: str, gstin: str, period: str) -> bool:
    for g in {gstin, ""}:   # a lock on "" (all her GSTINs) covers every one
        r = s.scalars(select(AccPeriod).where(AccPeriod.tenant_id == tenant, AccPeriod.gstin == g, AccPeriod.period == period)).first()
        if r is not None and r.state == "locked":
            return True
    return False


def _event(s, tenant: str, what: str, ref: str, before: Any = "", after: Any = "", actor: str = "hoola") -> None:
    s.add(AccEvent(tenant_id=tenant, actor=actor, what=what, ref=ref[:80],
                   before=json.dumps(before, default=str)[:4000] if before not in ("", None) else "",
                   after=json.dumps(after, default=str)[:4000] if after not in ("", None) else ""))


def set_lock(tenant: str, period: str, on: bool, gstin: str = "", by: str = "owner", note: str = "") -> dict[str, Any]:
    if not PERIOD.match(period or ""):
        raise RegisterError("Month as YYYY-MM.")
    ensure_tables()
    with session() as s:
        r = s.scalars(select(AccPeriod).where(AccPeriod.tenant_id == tenant, AccPeriod.gstin == gstin, AccPeriod.period == period)).first()
        if r is None:
            r = AccPeriod(tenant_id=tenant, gstin=gstin, period=period)
            s.add(r)
        r.state, r.locked_by, r.note, r.at = ("locked" if on else "open"), (by if on else ""), note[:500], now()
        _event(s, tenant, "lock" if on else "unlock", f"{gstin or 'all'}:{period}", after={"by": by, "note": note[:200]}, actor=by)
        s.commit()
    return {"period": period, "gstin": gstin, "state": "locked" if on else "open"}


# ------------------------------------------------------------------ sync
def sync(tenant: str, months: list[str] | None = None, sources: list[str] | None = None, today: date | None = None) -> dict[str, Any]:
    """Pull the chosen months from every source into the register. Idempotent; reports what changed."""
    ensure_tables()
    months = [m for m in (months or months_back(3, today)) if PERIOD.match(m)]
    if not months:
        raise RegisterError("Months as YYYY-MM.")
    res: dict[str, Any] = {"months": months, "added": 0, "changed": 0, "unchanged": 0, "held_locked": 0, "gone": 0,
                           "by_source": {}, "errors": {}, "duplicates": 0}
    for name, fn in ADAPTERS.items():
        if sources and name not in sources:
            continue
        try:
            docs = fn(tenant, months)
        except Exception as e:   # noqa: BLE001 - a source that fails is reported, the others still sync
            log.exception("bahi adapter %s failed", name)
            res["errors"][name] = f"{type(e).__name__}: {str(e)[:160]}"
            continue
        res["by_source"][name] = len(docs)
        seen: set[str] = set()
        with session() as s:
            for d in docs:
                seen.add(d["source_ref"])
                fp = _fp(d)
                row = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.source == name,
                                                     AccDoc.source_ref == d["source_ref"])).first()
                if row is None:
                    row = AccDoc(tenant_id=tenant, source=name, source_ref=d["source_ref"], fingerprint=fp, reason=d.get("reason", ""),
                                 status="confirmed", confidence=1.0, **{k: d.get(k, "") if k in ("gstin", "period", "direction", "kind", "number",
                                                                                                   "doc_date", "party_name", "party_gstin", "pos", "irn")
                                                                        else d.get(k, 0.0) for k in FIELDS})
                    s.add(row)
                    _event(s, tenant, "added", f"{name}:{d['source_ref']}", after={k: d.get(k) for k in FIELDS})
                    res["added"] += 1
                    continue
                if row.fingerprint == fp and row.status != "gone":
                    res["unchanged"] += 1
                    continue
                if locked(s, tenant, row.gstin, row.period):
                    probs = [p for p in json.loads(row.problems or "[]") if p.get("kind") != "changed_after_lock"]
                    probs.append({"kind": "changed_after_lock", "text": f"Changed in {SOURCES.get(name, name)} after {row.period} was locked - "
                                  "needs an amendment, the locked figures were kept."})
                    row.problems = json.dumps(probs)
                    _event(s, tenant, "change_held_locked", f"{name}:{d['source_ref']}", before={k: getattr(row, k) for k in FIELDS},
                           after={k: d.get(k) for k in FIELDS})
                    res["held_locked"] += 1
                    continue
                before = {k: getattr(row, k) for k in FIELDS}
                for k in FIELDS:
                    setattr(row, k, d.get(k, getattr(row, k)))
                row.fingerprint, row.reason, row.status, row.updated_at = fp, d.get("reason", row.reason), "confirmed", now()
                _event(s, tenant, "changed", f"{name}:{d['source_ref']}", before=before, after={k: d.get(k) for k in FIELDS})
                res["changed"] += 1
            # a row its source no longer has (deleted / cancelled there) is marked, never deleted - the trail keeps it
            for row in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.source == name,
                                                      AccDoc.period.in_(months), AccDoc.status != "gone")).all():
                if row.source_ref not in seen and not locked(s, tenant, row.gstin, row.period):
                    row.status, row.updated_at = "gone", now()
                    _event(s, tenant, "gone_at_source", f"{name}:{row.source_ref}")
                    res["gone"] += 1
            s.commit()
    res["duplicates"] = _flag_duplicates(tenant, months)
    return res


def _flag_duplicates(tenant: str, months: list[str]) -> int:
    """Same invoice number from the same party in the same direction, coming from two different sources: flag both rows."""
    n = 0
    with session() as s:
        rows = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period.in_(months), AccDoc.status != "gone")).all()
        groups: dict[tuple, list[AccDoc]] = {}
        for r in rows:
            key_party = r.party_gstin or r.party_name.strip().lower()
            if not (r.number and key_party):
                continue
            kind = r.kind if r.kind in ("cn", "dn") else "doc"   # a purchase is "inv" in GST Sahayak, "bill" in Thok / office
            groups.setdefault((r.direction, kind, key_party, _num(r.number)), []).append(r)
        for rs in groups.values():
            srcs = {r.source for r in rs}
            for r in rs:
                probs = [p for p in json.loads(r.problems or "[]") if p.get("kind") != "duplicate"]
                if len(srcs) > 1:
                    others = ", ".join(SOURCES.get(x, x) for x in sorted(srcs - {r.source}))
                    probs.append({"kind": "duplicate", "text": f"The same document is also in {others} - it should be counted once."})
                    n += 1
                r.problems = json.dumps(probs)
        s.commit()
    return n


# ------------------------------------------------------------------ reads
def view(r: AccDoc) -> dict[str, Any]:
    return {"id": r.id, "source": r.source, "source_name": SOURCES.get(r.source, r.source), "gstin": r.gstin, "period": r.period,
            "direction": r.direction, "kind": r.kind, "number": r.number, "date": r.doc_date, "party": r.party_name,
            "party_gstin": r.party_gstin, "taxable": r.taxable, "tax": r.tax or round(r.cgst + r.sgst + r.igst + r.cess, 2),
            "cgst": r.cgst, "sgst": r.sgst, "igst": r.igst, "total": r.total, "status": r.status, "confidence": r.confidence,
            "reason": r.reason, "problems": json.loads(r.problems or "[]")}


def listing(tenant: str, period: str = "", direction: str = "", source: str = "", q: str = "", limit: int = 200) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        st = select(AccDoc).where(AccDoc.tenant_id == tenant)
        if period:
            st = st.where(AccDoc.period == period)
        if direction in ("in", "out"):
            st = st.where(AccDoc.direction == direction)
        if source:
            st = st.where(AccDoc.source == source)
        rows = s.scalars(st.order_by(AccDoc.doc_date.desc(), AccDoc.number).limit(max(1, min(limit, 1000)))).all()
        out = [view(r) for r in rows]
    if q:
        ql = q.lower()
        out = [r for r in out if ql in (r["number"] + " " + r["party"] + " " + r["party_gstin"]).lower()]
    return out


def summary(tenant: str, period: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period == period, AccDoc.status != "gone")).all()
        lock = locked(s, tenant, "", period)
        total = s.scalar(select(func.count()).select_from(AccDoc).where(AccDoc.tenant_id == tenant)) or 0
    out: dict[str, Any] = {"period": period, "locked": lock, "all_documents": int(total), "documents": len(rows),
                           "sales": {"count": 0, "taxable": 0.0, "tax": 0.0, "total": 0.0},
                           "purchases": {"count": 0, "taxable": 0.0, "tax": 0.0, "total": 0.0},
                           "by_source": {}, "problems": 0}
    for r in rows:
        b = out["sales" if r.direction == "out" else "purchases"]
        sign = -1 if r.kind == "cn" else 1
        b["count"] += 1
        tax = r.tax or (r.cgst + r.sgst + r.igst + r.cess)
        b["taxable"] = round(b["taxable"] + sign * r.taxable, 2)
        b["tax"] = round(b["tax"] + sign * tax, 2)
        b["total"] = round(b["total"] + sign * r.total, 2)
        out["by_source"][r.source] = out["by_source"].get(r.source, 0) + 1
        if json.loads(r.problems or "[]"):
            out["problems"] += 1
    return out


def events(tenant: str, limit: int = 30) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccEvent).where(AccEvent.tenant_id == tenant).order_by(AccEvent.at.desc()).limit(limit)).all()
        out = []
        for r in rows:
            label = r.ref
            src, _, ref = r.ref.partition(":")
            if src in SOURCES and ref:   # "office:ob_2c68..." -> "Office bills · AT-991 · Airtel" (never an internal id)
                d = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.source == src, AccDoc.source_ref == ref)).first()
                label = " · ".join(x for x in (SOURCES[src], d.number if d else "", d.party_name if d else "") if x)
            elif r.what in ("lock", "unlock"):
                g, _, per = r.ref.partition(":")
                label = per + ("" if g == "all" else f" · {g}")
            out.append({"at": r.at.isoformat() if isinstance(r.at, datetime) else str(r.at), "actor": r.actor, "what": r.what,
                        "ref": r.ref, "label": label})
        return out
