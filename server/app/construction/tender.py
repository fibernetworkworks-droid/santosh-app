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
        raise CstError("Tender ka naam aur last date dono chahiye.")
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
                   + (f", EMD {_rs(emd)}" if _num(emd) else "") + f". Bid lena ya nahi - sheet bhar ke aapki call."}


def bid_sheet(tenant: str, tender_id: str, decision: str, reasons: list, conv: str = "") -> dict:
    """The bid / no-bid sheet: HER decision with HER factor rows ({factor, note}) - recorded, not
    judged. Hoola never makes the bid decision."""
    if decision not in ("bid", "no_bid"):
        raise CstError("decision: bid | no_bid - yeh call aapki hai, main sirf record rakhta hoon.")
    rows = [r for r in (reasons or []) if isinstance(r, dict) and str(r.get("factor", "")).strip()]
    if not rows:
        raise CstError("Reasons bhejo [{factor, note}] - khaali sheet bid nahi banati.")
    with _LOCK, session() as s:
        x = s.get(CTender, tender_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Tender nahi mila.")
        x.status = decision
        x.reasons = _dump(rows)
        name = x.name
    from .common import publish
    publish(tenant, "const_tender", {"kind": f"bid_{decision}", "tender": name}, conv)
    return {"tender_id": tender_id, "factors": len(rows),
            "say": f"{name}: {decision.upper()} sheet record ({len(rows)} factors) - call aapki thi, "
                   "record aapke reasons ke saath. "
                   + ("Taiyaari shuru - prequal dossier bana doon?" if decision == "bid"
                      else "Theek hai - record ke saath band.")}


def pack(tenant: str, tender_id: str, kind: str, rows: list, note: str = "") -> dict:
    """#55 prequal dossier / #54 bid price pack: rows [{item, value, source}]; the price pack's
    numbers point at their source (SOR / QS take-off / quote) - bina source ki row nahi rehti."""
    if kind not in ("prequal", "price"):
        raise CstError("kind: prequal | price")
    clean = []
    for r in (rows or []):
        if isinstance(r, dict) and str(r.get("item", "")).strip():
            if not str(r.get("source", "")).strip():
                raise CstError(f"'{str(r.get('item'))[:40]}' ka source bataiye - har row apna source leke "
                               "chalti hai (SOR page / quote / certificate no).")
            clean.append({"item": str(r.get("item"))[:160], "value": str(r.get("value", ""))[:200],
                          "source": str(r.get("source"))[:160]})
    if not clean:
        raise CstError("Rows bhejo [{item, value, source}].")
    with _LOCK, session() as s:
        t = s.get(CTender, tender_id)
        if not t or t.tenant_id != tenant:
            raise CstError("Tender nahi mila.")
        x = CTendPack(tenant_id=tenant, tender_id=tender_id[:40], kind=kind, rows=_dump(clean),
                      prepared_on=today(tenant).isoformat(), status="ready", note=note[:200])
        s.add(x)
        s.flush()
        pid, tname = x.id, t.name
    return {"pack_id": pid, "rows": len(clean),
            "say": (f"Pre-qual dossier ({tname}): {len(clean)} rows, sab sourced. Bid manager taiyaar karke "
                    "portal par daalega." if kind == "prequal" else
                    f"Bid price pack ({tname}): {len(clean)} rows - QS take-off aur rates se juda hua. "
                    "Bid daalna bid manager ki haan se.")}


def tender_mark(tenant: str, tender_id: str, status: str, ref: str = "") -> dict:
    if status not in ("watch", "bid", "no_bid", "submitted", "won", "lost"):
        raise CstError("status: watch | bid | no_bid | submitted | won | lost")
    with _LOCK, session() as s:
        x = s.get(CTender, tender_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Tender nahi mila.")
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
    say = (f"Tender watch: {len(out)} agle {days} dinon mein."
           + (f" Sabse pehle: {out[0]['name']} ({out[0]['in_days']} din)." if out else "")
           + " Bid / no-bid ki call aapki.")
    return {"due": out, "say": say}


def vendor_add(tenant: str, vendor: str, scope: str = "", rating: str = "watch", last_work: str = "",
               note: str = "") -> dict:
    """#58 the vendor register: HER rating (preferred / ok / watch / blocked) - Hoola keeps the
    score she gives, never invents one."""
    if not str(vendor or "").strip():
        raise CstError("Vendor ka naam bataiye.")
    if rating not in ("preferred", "ok", "watch", "blocked"):
        raise CstError("rating: preferred | ok | watch | blocked - aapki rating hai, main nahi sochta.")
    with _LOCK, session() as s:
        x = CTendVendor(tenant_id=tenant, vendor=vendor.strip()[:160], scope=scope.strip()[:200],
                        rating=rating, last_work=last_work.strip()[:200], note=note[:200])
        s.add(x)
        s.flush()
        vid = x.id
    return {"vendor_id": vid, "say": f"Vendor register: {vendor} ({scope[:60] or '-'}) - rating {rating} (aapki)."}


def vendor_rate(tenant: str, vendor_id: str, rating: str, note: str = "") -> dict:
    if rating not in ("preferred", "ok", "watch", "blocked"):
        raise CstError("rating: preferred | ok | watch | blocked")
    with _LOCK, session() as s:
        x = s.get(CTendVendor, vendor_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Vendor nahi mila.")
        x.rating = rating
        if note:
            x.note = note[:200]
        v = x.vendor
    return {"say": f"{v}: rating -> {rating} (aapke word par record)."}


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
        raise CstError("Purchase rows chahiye [item, qty, unit, need_by, po_no, po_date, vendor].")
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
            "said": f"{made} indent row(s) ({no_po} bina PO) - PO jaari karna purchase engineer ka kaam."}


def expedite_add(tenant: str, project: str, po: str, promised: str, need_by: str,
                 note: str = "") -> dict:
    """#59: vendor promise vs need-by - the gap is arithmetic; the call is the expediter's."""
    from . import models as WM
    if not po:
        raise CstError("PO ka ref do.")
    if not promised or not need_by:
        raise CstError("Promised date aur need_by dono chahiye.")
    late = promised > need_by
    with session() as s:
        s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="expedite", ref=po[:40],
                            name="promise",
                            data=_dump({"promised": promised, "need_by": need_by,
                                        "late": late, "note": note[:200]})))
    return {"ok": True, "po": po, "promised": promised, "need_by": need_by,
            "verdict": "LATE - follow-up karo" if late else "in time",
            "said": ("Vendor promise need-by ke BAAD ka hai - follow-up log rakho."
                     if late else "Promise need-by ke andar hai.")}


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
        raise CstError("EXIM rows chahiye [shipment, bl_date, be_date, docs_missing, note].")
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
            "said": f"{made} shipment row(s) - customs ka kaam CHA/broker karega, Hoola register rakhta hai."}
