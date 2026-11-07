"""#92 Customer Payment & Demand-letter Manager + #97/#98 Handover / DLP desk (v0.512.0, Wave 1, tier A).
Milestone-linked demand letters drafted as PDFs (sent only on HER haan - status=send is owner-only, the
house confirm-card law), receipts against them, possession checklists, and the DLP clock after
possession (arithmetic from the agreement months; vendor dispatch recorded after it happens)."""
from __future__ import annotations

import io

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, _rs, add_months, publish, today)
from .models import CCustDemand, CCustReceipt, CDlpTicket, CHandover


def demand(tenant: str, project: str, unit: str, customer: str = "", phone: str = "", milestone: str = "",
           amount=None, due: str = "", interest_pct=None, note: str = "") -> dict:
    amt = _num(amount)
    if not str(project or "").strip() or not str(unit or "").strip() or amt <= 0:
        raise CstError("Project, unit aur rakam bataiye.")
    d = _date(due)
    if not d:
        raise CstError("Demand ki tareekh (due) bataiye.")
    with _LOCK, session() as s:
        x = CCustDemand(tenant_id=tenant, project=project.strip()[:160], unit=unit.strip()[:60],
                        customer=customer[:160], phone=phone[:20], milestone=milestone[:200], amount=amt,
                        due=d.isoformat(), interest_pct=_num(interest_pct), note=note[:300])
        s.add(x)
        s.flush()
        did, ip = x.id, x.interest_pct
    return {"demand_id": did, "say": (f"Demand DRAFT: {project} unit {unit} - {customer or 'grahak'} se {_rs(amt)} "
                                      f"({milestone or 'milestone'}), due {d.strftime('%d %b')}"
                                      + (f", byaaj {ip:g}%/mahina (aapke agreement ka clause)" if ip else "")
                                      + ". Letter PDF bana sakta hoon; BHEJNA aapki haan se.")}


def demand_letter(tenant: str, demand_id: str) -> bytes:
    """The demand letter PDF: her facts, the interest clause from HER agreement, a courteous collection
    letter a CRM head would sign. No template poetry - one clean page."""
    with session() as s:
        x = s.get(CCustDemand, demand_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Demand nahi mili.")
        project, unit, customer, milestone, amount, due, ip = x.project, x.unit, x.customer, x.milestone, x.amount, x.due, x.interest_pct
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text).replace("₹", "Rs ")[:110])
        y -= size + 6

    t(50, "PAYMENT DEMAND - MILESTONE DUE", 13, True)
    t(50, f"Project: {project}    Unit: {unit}")
    t(50, f"To: {customer or 'Unit holder'}")
    y -= 6
    t(50, f"Milestone: {milestone or '-'}", 11)
    t(50, f"Amount due: Rs {amount:,.2f}")
    t(50, f"Due date: {due}")
    if ip:
        t(50, f"Interest on delay: {ip:g}% per month (as per the agreement's payment schedule).")
    y -= 10
    for ln in ("Kindly arrange the payment against this milestone. For any query on the measurement,",
               "scope or schedule of payment, please contact our office - the agreement and the",
               "approved payment schedule remain the basis of this demand."):
        t(50, ln, 9.5)
    y -= 24
    t(50, "For the builder", 10)
    t(50, "(authorised signatory - signs by hand)", 9)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def demand_send(tenant: str, demand_id: str, actor: str, on: str = "", conv: str = "") -> dict:
    """status -> sent. OWNER ONLY (the card law): the letter leaves on her word, never Hoola's."""
    if actor != "owner" and not str(actor).startswith("approved:"):
        raise CstError("Demand bhejne ki haan sirf owner.")
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CCustDemand, demand_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Demand nahi mili.")
        x.status = "sent"
        x.sent_on = d.isoformat()
        project, unit, customer, amount = x.project, x.unit, x.customer, x.amount
    publish(tenant, "const_customer", {"kind": "demand_sent", "demand_id": demand_id, "unit": unit}, conv)
    return {"say": f"{project} unit {unit} ki demand ({_rs(amount)}) BHEJ DI gaya maane - {customer or 'grahak'} ko. "
                   "WhatsApp se bhejna ho to campaigns / chat se aap bhejiye (Hoola akele nahi bhejta)."}


def receipt(tenant: str, demand_id: str = "", project: str = "", unit: str = "", customer: str = "",
            amount=None, mode: str = "", day: str = "", note: str = "") -> dict:
    amt = _num(amount)
    if amt <= 0:
        raise CstError("Rakam bataiye.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        dm = s.get(CCustDemand, demand_id) if demand_id else None
        if demand_id and (not dm or dm.tenant_id != tenant):
            raise CstError("Demand nahi mili.")
        if dm is not None:
            got = round(sum(r.amount for r in s.scalars(select(CCustReceipt).where(
                CCustReceipt.tenant_id == tenant, CCustReceipt.demand_id == demand_id)).all()) + amt, 2)
            dm.status = "paid" if got >= dm.amount - 1e-9 else "part"
            project, unit, customer = dm.project, dm.unit, dm.customer
        s.add(CCustReceipt(tenant_id=tenant, demand_id=demand_id or "", project=project[:160], unit=unit[:60],
                           customer=customer[:160], amount=amt, mode=mode[:20], day=d.isoformat(), note=note[:300]))
    return {"say": f"Receipt: {project or '-'} unit {unit or '-'} - {_rs(amt)} ({mode or 'mode? '}) {d.strftime('%d %b')} ko."
                   + (" Demand paid mark ho gayi." if demand_id and amt else "")}


def handover(tenant: str, project: str, unit: str, customer: str = "", items: list | None = None,
             status: str = "", keys_on: str = "", utilities: str = "", conv: str = "") -> dict:
    if not str(project or "").strip() or not str(unit or "").strip():
        raise CstError("Project aur unit bataiye.")
    with _LOCK, session() as s:
        x = next((r for r in s.scalars(select(CHandover).where(CHandover.tenant_id == tenant)).all()
                  if r.project == project.strip()[:160] and r.unit == unit.strip()[:60]), None)
        new = x is None
        if new:
            x = CHandover(tenant_id=tenant, project=project.strip()[:160], unit=unit.strip()[:60], customer=customer[:160])
            s.add(x)
            s.flush()                                           # status default lands before the read
        if items is not None:
            x.items = _dump([{"item": str(i.get("item", ""))[:160], "done": bool(i.get("done")),
                              "day": str(i.get("day", ""))[:10], "note": str(i.get("note", ""))[:160]} for i in items if isinstance(i, dict)][:40])
            x.status = "ready" if all(bool(i.get("done")) for i in items if isinstance(i, dict)) else x.status
        if customer:
            x.customer = customer[:160]
        if keys_on:
            x.keys_on = (_date(keys_on) or today(tenant)).isoformat()
            x.status = "handed"
        if utilities:
            x.utilities = utilities[:300]
        if status in ("open", "ready", "handed"):
            x.status = status
        out = {"project": x.project, "unit": x.unit, "status": x.status, "keys_on": x.keys_on}
    from .common import publish as pub
    pub(tenant, "const_customer", {"kind": "handover", "unit": unit, "status": out["status"]}, conv)
    return {**out, "say": (f"Naya" if new else "Update") + f" handover: {project} unit {unit} - status {out['status']}"
                                             + (f", keys {out['keys_on']}" if out["keys_on"] else "") + "."}


def dlp_open(tenant: str, project: str, unit: str, issue: str, trade: str = "", vendor: str = "",
             dlp_months=None, possession_on: str = "", opened_on: str = "", note: str = "") -> dict:
    """A defect ticket in the DLP window. dlp_until = possession date + the agreement's DLP months (arithmetic)."""
    if not str(issue or "").strip():
        raise CstError("Problem bataiye (kya kharab hai, kahan).")
    pos = _date(possession_on) or today(tenant)
    months = _num(dlp_months) or 12.0
    until = add_months(pos, int(months))
    d = _date(opened_on, today(tenant))
    with _LOCK, session() as s:
        x = CDlpTicket(tenant_id=tenant, project=project[:160], unit=unit[:60], customer="", issue=issue[:2000],
                       trade=trade[:40], vendor=vendor[:160], opened_on=d.isoformat(), dlp_until=until.isoformat(),
                       note=note[:300])
        s.add(x)
        s.flush()
        tid = x.id
    in_win = today(tenant) <= until
    return {"ticket_id": tid, "dlp_until": until.isoformat(),
            "say": f"DLP ticket #{tid[:8]}: {project} unit {unit} - {issue[:80]}. DLP window {pos.strftime('%d %b')} + {months:g} mahine = {until.strftime('%d %b %Y')}"
                   + (" (window khuli hai - vendor ko bhejne se pehle aapki haan)." if in_win else " (window KHATAM - warranty only, DLP nahi).")}


def dlp_sent(tenant: str, ticket_id: str, actor: str, day: str = "") -> dict:
    """Record that the vendor WAS dispatched (her tap / her letter) - Hoola does not send it."""
    if actor != "owner" and not str(actor).startswith("approved:"):
        raise CstError("Vendor ko bhejne ki haan sirf owner.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CDlpTicket, ticket_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Ticket nahi mila.")
        x.status = "vendor_sent"
        x.vendor_sent_on = d.isoformat()
        project, unit, vendor = x.project, x.unit, x.vendor
    return {"say": f"Record: {project} unit {unit} ka ticket vendor ({vendor or '-'}) ko {d.strftime('%d %b')} ko gaya."}


def dlp_close(tenant: str, ticket_id: str, day: str = "", note: str = "") -> dict:
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CDlpTicket, ticket_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Ticket nahi mila.")
        x.status = "closed"
        x.closed_on = d.isoformat()
        if note:
            x.note = (x.note + " " + note)[:300]
        project, unit = x.project, x.unit
    return {"say": f"DLP ticket #{ticket_id[:8]} ({project} unit {unit}) band ho gaya."}


def demands(tenant: str, status: str = "") -> list[dict]:
    with session() as s:
        rows = s.scalars(select(CCustDemand).where(CCustDemand.tenant_id == tenant).order_by(CCustDemand.due)).all()
    if status:
        rows = [r for r in rows if r.status == status]
    return [{"id": r.id, "project": r.project, "unit": r.unit, "customer": r.customer, "milestone": r.milestone,
             "amount": r.amount, "due": r.due, "status": r.status, "interest_pct": r.interest_pct} for r in rows]


def dlp_list(tenant: str, open_only: bool = True) -> list[dict]:
    with session() as s:
        rows = s.scalars(select(CDlpTicket).where(CDlpTicket.tenant_id == tenant).order_by(CDlpTicket.opened_on)).all()
    if open_only:
        rows = [r for r in rows if r.status != "closed"]
    return [{"id": r.id, "project": r.project, "unit": r.unit, "issue": r.issue[:120], "trade": r.trade,
             "vendor": r.vendor, "opened_on": r.opened_on, "dlp_until": r.dlp_until, "status": r.status} for r in rows]


# ---------------------------------------------------------------- Wave 4: #94-#99 sales, docs, handover, investor
def lead_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#94: rows [name, contact, source, unit_interest, status] - the pipeline as HER words."""
    from . import models as WM
    from .common import publish as pub
    if not rows:
        raise CstError("Lead rows chahiye [name, contact, source, unit, status].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="lead",
                                name=str(r[0])[:120],
                                data=_dump({"contact": str(r[1])[:80], "source": str(r[2])[:60] if len(r) > 2 else "",
                                            "unit": str(r[3])[:40] if len(r) > 3 else "",
                                            "status": str(r[4])[:24] if len(r) > 4 else "new"})))
            made += 1
    pub(tenant, "const_customer", {"kind": "leads", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "said": f"{made} lead row(s) - follow-up CRM ke apne rules par."}


def inventory_mark(tenant: str, project: str, unit: str, status: str) -> dict:
    """#94: unit status available | booked | sold - HER word, recorded."""
    from . import models as WM
    if status not in ("available", "booked", "sold"):
        raise CstError("status available | booked | sold.")
    with session() as s:
        s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="inventory", ref=unit[:40],
                            name=unit[:40], data=_dump({"status": status})))
    return {"ok": True, "unit": unit, "status": status, "said": f"{unit} -> {status} (aapka word)."}


def inventory_sum(tenant: str, project: str) -> dict:
    from . import models as WM
    with session() as s:
        rows = s.scalars(select(WM.Cw4ExtItem).where(WM.Cw4ExtItem.tenant_id == tenant,
                                                     WM.Cw4ExtItem.project == project,
                                                     WM.Cw4ExtItem.kind == "inventory")).all()
    counts: dict[str, int] = {}
    for r in rows:
        st = str(_j(r.data, {}).get("status") or "?")
        counts[st] = counts.get(st, 0) + 1
    return {"units": counts, "said": "Inventory aapke marks se hai."}


def mkt_asset(tenant: str, project: str, rows: list) -> dict:
    """#95: rows [asset, status, rera_no] - RERA number ke bina ad nahi (tier C refuses)."""
    from . import models as WM
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="mkt",
                                name=str(r[0])[:120],
                                data=_dump({"status": str(r[1])[:24] if len(r) > 1 else "",
                                            "rera_no": str(r[2])[:40] if len(r) > 2 else ""})))
            made += 1
    return {"ok": True, "rows": made,
            "said": (f"{made} marketing asset row(s) - RERA number ke bina advertise karna "
                     "gates mein block hai (RERA 2016 s.3).")}


def afs_doc(tenant: str, project: str, unit: str, rows: list, by: str = "") -> dict:
    """#96: agreement-for-sale document checklist [doc, status] - status needs the doer's name;
    the signed agreement is hers."""
    from . import models as WM
    if not by:
        raise CstError("Doc status ke saath US KA NAAM jo rakh raha hai.")
    if not rows:
        raise CstError("Doc rows chahiye [doc, status].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="afs", ref=unit[:40],
                                name=str(r[0])[:120], data=_dump({"status": str(r[1])[:24]}), by=by))
            made += 1
    return {"ok": True, "unit": unit, "rows": made, "by": by,
            "said": f"{made} doc row(s) '{unit}' ke liye - agreement par sign aapki."}


def handover_unit(tenant: str, project: str, unit: str, dues_rows: list, snags_ref: str = "") -> dict:
    """#97: dues [type, amount, paid] + optional snag reference (const_quality punch). Possession
    letter hers; the arithmetic here."""
    from . import models as WM
    if not dues_rows:
        raise CstError("Dues rows chahiye [type, amount, paid].")
    rows_out, due_t, paid_t = [], 0.0, 0.0
    with session() as s:
        for r in dues_rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            amt, pd = _num(r[1]), _num(r[2])
            due_t, paid_t = due_t + amt, paid_t + pd
            rows_out.append({"type": str(r[0])[:60], "amount": amt, "paid": pd,
                             "balance": round(amt - pd, 2)})
        s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="handover", ref=unit[:40],
                            name="dues",
                            data=_dump({"rows": rows_out, "due_total": round(due_t, 2),
                                        "paid_total": round(paid_t, 2),
                                        "balance": round(due_t - paid_t, 2),
                                        "snags_ref": snags_ref[:40]})))
    bal = round(due_t - paid_t, 2)
    return {"ok": True, "unit": unit, "rows": rows_out, "due_total": round(due_t, 2),
            "paid_total": round(paid_t, 2), "balance": bal, "snags_ref": snags_ref,
            "said": (f"Balance {bal:,.0f} baaki - possession letter dues clear hone par hi, "
                     "decision aapka." if bal > 0 else "Dues clear (arithmetic) - handover aapka faisla.")}


def investor_pack(tenant: str, project: str, rows: list, milestones: list) -> dict:
    """#99: drawdown rows [period, planned, actual] + milestone rows [milestone, status] - the
    lender/investor pack draft, sign line empty."""
    from . import models as WM
    if not rows:
        raise CstError("Drawdown rows chahiye [period, planned, actual].")
    per, tp, ta = [], 0.0, 0.0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            p, a = _num(r[1]), _num(r[2])
            tp, ta = tp + p, ta + a
            per.append({"period": str(r[0])[:20], "planned": p, "actual": a, "var": round(a - p, 2)})
        for m in milestones or []:
            if isinstance(m, (list, tuple)) and m:
                s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="investor",
                                    name=str(m[0])[:120], data=_dump({"status": str(m[1])[:24] if len(m) > 1 else ""})))
    return {"ok": True, "drawdown": per, "total_planned": round(tp, 2), "total_actual": round(ta, 2),
            "variance": round(ta - tp, 2),
            "said": ("Pack ka DRAFT hai - sign line khaali; lender ke samne CFO/MD hi present karenge.")}
