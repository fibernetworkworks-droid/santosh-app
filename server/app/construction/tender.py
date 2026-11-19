"""#52 Tender Manager's Assistant + #53 Tender Document Writer + #54 Bid Pricer +
#55 Pre-qualification Dossier Builder + #58 Vendor Developer (v0.531.0, Wave 2 C10).

The watch list, the bid / no-bid sheet (her call, her reasons - Hoola records, never decides to
bid), the pre-qualification dossier and the bid price pack (rows she feeds, each with its source -
the price pack rides the QS desk's take-off and rates where a project exists), and the vendor
register with HER ratings. Bidding into a portal is the bid manager's act - Hoola prepares."""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, _rs, today)
from .models import CTendPack, CTendVendor, CTender


def tender_add(tenant: str, name: str, authority: str, due_on: str, emd=None, scope: str = "",
               conv: str = "") -> dict:
    """One tender onto the watch list with its due date and EMD."""
    d = _date(due_on)
    if not str(name or "").strip() or d is None:
        raise CstError("Both the tender's name and the last date are needed.")
    with _LOCK, session() as s:
        x = CTender(tenant_id=tenant, name=name.strip()[:200], authority=authority.strip()[:160],
                    due_on=d.isoformat(), emd=_num(emd), scope=scope.strip()[:300])
        s.add(x)
        s.flush()
        tid = x.id
    from .common import publish
    publish(tenant, "const_tender", {"kind": "tender_add", "name": name}, conv)
    return {"tender_id": tid,
            "say": f"Tender watch: {name} ({authority or '-'}) due {d.strftime('%d %b')}"
                   + (f", EMD {_rs(emd)}" if _num(emd) else "") + f". To bid or not - fill in the sheet; the call is yours."}


def bid_sheet(tenant: str, tender_id: str, decision: str, reasons: list, conv: str = "") -> dict:
    """The bid / no-bid sheet: HER decision with HER factor rows ({factor, note}) - recorded, not
    judged. Hoola never makes the bid decision."""
    if decision not in ("bid", "no_bid"):
        raise CstError("decision: bid | no_bid - this call is yours, I only keep the record.")
    rows = [r for r in (reasons or []) if isinstance(r, dict) and str(r.get("factor", "")).strip()]
    if not rows:
        raise CstError("Send the reasons [{factor, note}] - an empty sheet does not make a bid.")
    with _LOCK, session() as s:
        x = s.get(CTender, tender_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Tender not found.")
        x.status = decision
        x.reasons = _dump(rows)
        name = x.name
    from .common import publish
    publish(tenant, "const_tender", {"kind": f"bid_{decision}", "tender": name}, conv)
    return {"tender_id": tender_id, "factors": len(rows),
            "say": f"{name}: {decision.upper()} sheet record ({len(rows)} factors) - the call was yours, "
                   "recorded with your reasons. "
                   + ("Preparation starts - shall I make the prequal dossier?" if decision == "bid"
                      else "OK - closed, with the record.")}


def pack(tenant: str, tender_id: str, kind: str, rows: list, note: str = "") -> dict:
    """#55 prequal dossier / #54 bid price pack: rows [{item, value, source}]; the price pack's
    numbers point at their source (SOR / QS take-off / quote) - bina source ki row nahi rehti."""
    if kind not in ("prequal", "price"):
        raise CstError("kind: prequal | price")
    clean = []
    for r in (rows or []):
        if isinstance(r, dict) and str(r.get("item", "")).strip():
            if not str(r.get("source", "")).strip():
                raise CstError(f"'{str(r.get('item'))[:40]}' needs a source - every row carries its own "
                               "source (SOR page / quote / certificate no).")
            clean.append({"item": str(r.get("item"))[:160], "value": str(r.get("value", ""))[:200],
                          "source": str(r.get("source"))[:160]})
    if not clean:
        raise CstError("Send rows [{item, value, source}].")
    with _LOCK, session() as s:
        t = s.get(CTender, tender_id)
        if not t or t.tenant_id != tenant:
            raise CstError("Tender not found.")
        x = CTendPack(tenant_id=tenant, tender_id=tender_id[:40], kind=kind, rows=_dump(clean),
                      prepared_on=today(tenant).isoformat(), status="ready", note=note[:200])
        s.add(x)
        s.flush()
        pid, tname = x.id, t.name
    return {"pack_id": pid, "rows": len(clean),
            "say": (f"Pre-qual dossier ({tname}): {len(clean)} rows, all sourced. The bid manager prepares it and "
                    "uploads it to the portal." if kind == "prequal" else
                    f"Bid price pack ({tname}): {len(clean)} rows - linked to the QS take-off and rates. "
                    "The bid goes in only with the bid manager's approval.")}


def tender_mark(tenant: str, tender_id: str, status: str, ref: str = "") -> dict:
    if status not in ("watch", "bid", "no_bid", "submitted", "won", "lost"):
        raise CstError("status: watch | bid | no_bid | submitted | won | lost")
    with _LOCK, session() as s:
        x = s.get(CTender, tender_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Tender not found.")
        x.status = status
        if ref:
            x.ref = ref[:120]
        name = x.name
    return {"say": f"{name}: status -> {status}" + (f" (ref {ref})" if ref else "") + "."}


def due(tenant: str, days: int = 14) -> dict:
    """The watch: tenders due in the window, still on 'watch' - the clock is honest."""
    d0 = today(tenant)
    with session() as s:
        rows = s.scalars(select(CTender).where(CTender.tenant_id == tenant,
                                               CTender.status.in_(("watch", "bid")))).all()
    out = []
    for r in rows:
        dd = _date(r.due_on)
        if dd is None:
            continue
        delta = (dd - d0).days
        if delta <= max(0, int(days)):
            out.append({"name": r.name, "authority": r.authority, "due_on": r.due_on, "in_days": delta,
                        "status": r.status, "emd": r.emd})
    out.sort(key=lambda x: x["in_days"])
    say = (f"Tender watch: {len(out)} due in the next {days} days."
           + (f" First: {out[0]['name']} ({out[0]['in_days']} days)." if out else "")
           + " The bid / no-bid call is yours.")
    return {"due": out, "say": say}


def vendor_add(tenant: str, vendor: str, scope: str = "", rating: str = "watch", last_work: str = "",
               note: str = "") -> dict:
    """#58 the vendor register: HER rating (preferred / ok / watch / blocked) - Hoola keeps the
    score she gives, never invents one."""
    if not str(vendor or "").strip():
        raise CstError("Give the vendor's name.")
    if rating not in ("preferred", "ok", "watch", "blocked"):
        raise CstError("rating: preferred | ok | watch | blocked - the rating is yours, I do not judge.")
    with _LOCK, session() as s:
        x = CTendVendor(tenant_id=tenant, vendor=vendor.strip()[:160], scope=scope.strip()[:200],
                        rating=rating, last_work=last_work.strip()[:200], note=note[:200])
        s.add(x)
        s.flush()
        vid = x.id
    return {"vendor_id": vid, "say": f"Vendor register: {vendor} ({scope[:60] or '-'}) - rating {rating} (yours)."}


def vendor_rate(tenant: str, vendor_id: str, rating: str, note: str = "") -> dict:
    if rating not in ("preferred", "ok", "watch", "blocked"):
        raise CstError("rating: preferred | ok | watch | blocked")
    with _LOCK, session() as s:
        x = s.get(CTendVendor, vendor_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Vendor not found.")
        x.rating = rating
        if note:
            x.note = note[:200]
        v = x.vendor
    return {"say": f"{v}: rating -> {rating} (recorded on your word)."}


def vendors(tenant: str, rating: str = "") -> dict:
    with session() as s:
        rows = s.scalars(select(CTendVendor).where(CTendVendor.tenant_id == tenant)).all()
    if rating:
        rows = [r for r in rows if r.rating == rating]
    rows.sort(key=lambda r: (r.rating, r.vendor))
    say = f"Vendor register: {len(rows)} vendor" + (f", rating {rating}" if rating else "") + "."
    return {"vendors": [{"id": r.id, "vendor": r.vendor, "scope": r.scope, "rating": r.rating,
                         "last_work": r.last_work} for r in rows], "say": say}


# ---------------------------------------------------------------- Wave 4: #57 purchase, #59 expediting, #60 EXIM
def purchase_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#57: indent->PO register - rows [item, qty, unit, need_by, po_no, po_date, vendor]."""
    from . import models as WM
    from .common import publish as pub
    if not rows:
        raise CstError("Purchase rows are needed [item, qty, unit, need_by, po_no, po_date, vendor].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 4:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="purchase",
                                name=str(r[0])[:120],
                                data=_dump({"qty": _num(r[1]), "unit": str(r[2])[:12],
                                            "need_by": str(r[3])[:10],
                                            "po_no": str(r[4])[:40] if len(r) > 4 else "",
                                            "po_date": str(r[5])[:10] if len(r) > 5 else "",
                                            "vendor": str(r[6])[:120] if len(r) > 6 else ""})))
            made += 1
    pub(tenant, "const_tender", {"kind": "purchase", "project": project, "rows": made}, conv)
    no_po = sum(1 for r in rows if isinstance(r, (list, tuple)) and len(r) > 4 and not str(r[4] or "").strip())
    return {"ok": True, "rows": made, "without_po": no_po,
            "said": f"{made} indent row(s) ({no_po} without a PO) - issuing the PO is the purchase engineer's job."}


def expedite_add(tenant: str, project: str, po: str, promised: str, need_by: str,
                 note: str = "") -> dict:
    """#59: vendor promise vs need-by - the gap is arithmetic; the call is the expediter's."""
    from . import models as WM
    if not po:
        raise CstError("Give the PO ref.")
    if not promised or not need_by:
        raise CstError("Both the promised date and need_by are needed.")
    late = promised > need_by
    with session() as s:
        s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="expedite", ref=po[:40],
                            name="promise",
                            data=_dump({"promised": promised, "need_by": need_by,
                                        "late": late, "note": note[:200]})))
    return {"ok": True, "po": po, "promised": promised, "need_by": need_by,
            "verdict": "LATE - follow up" if late else "in time",
            "said": ("The vendor's promise is AFTER the need-by date - keep a follow-up log."
                     if late else "The promise is within the need-by date.")}


def expedite_board(tenant: str, project: str) -> dict:
    from . import models as WM
    with session() as s:
        rows = s.scalars(select(WM.Cw4ExtItem).where(WM.Cw4ExtItem.tenant_id == tenant,
                                                     WM.Cw4ExtItem.project == project,
                                                     WM.Cw4ExtItem.kind == "expedite")).all()
    out = [{"po": r.ref, **_j(r.data, {})} for r in rows]
    late = [o for o in out if o.get("late")]
    return {"rows": out, "late_count": len(late),
            "said": f"{len(late)} promise(s) late - chase list ready."}


def exim_add(tenant: str, project: str, rows: list) -> dict:
    """#60: shipment register - rows [shipment, bl_date, be_date, docs_missing, note]. Customs act
    stays with the CHA/broker; Hoola keeps the register and the doc checklist."""
    from . import models as WM
    if not rows:
        raise CstError("EXIM rows are needed [shipment, bl_date, be_date, docs_missing, note].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="exim",
                                name=str(r[0])[:80],
                                data=_dump({"bl_date": str(r[1])[:10], "be_date": str(r[2])[:10],
                                            "docs_missing": str(r[3])[:200] if len(r) > 3 else "",
                                            "note": str(r[4])[:160] if len(r) > 4 else ""})))
            made += 1
    return {"ok": True, "rows": made,
            "said": f"{made} shipment row(s) - the CHA/broker does the customs work, Hoola keeps the register."}
