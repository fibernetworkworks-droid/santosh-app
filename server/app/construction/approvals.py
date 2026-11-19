"""#28 Approvals Tracker + #29 Building-permission File Assembler + #30 Fire-NOC Packet +
#31 EC / CTE-CTO Tracker + #32 Utility Liaison + #34 Statutory Calendar + #36 OC/CC Packet
(v0.531.0, Wave 2 C7).

One file per authority per purpose; the checklist is DATA (starter lists below, editable per file -
every ULB's exact list differs, so the starter says so); each paper is needed -> ready; the packet
is the assembler's index PDF. SUBMISSION IS NEVER HOOLA'S: the file goes in with the owner's DSC or
the named licensee's hand (tier C, construction/gates.py - "file a permission application"). The
statutory calendar (#34) counts days on the dates SHE records; renewals stay the compliance
officer's act."""
from __future__ import annotations

import io

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today, add_months)
from .models import CApprovCal, CApprovDoc, CApprovFile

# Starter checklists - DATA, deliberately editable (her ULB's exact list wins; Hoola's starter is
# the common shape and says so on the packet). Keys match by purpose keyword.
STARTER: dict[str, list[str]] = {
    "building_permission": [
        "Application form (the authority's prescribed form)",
        "Ownership / title papers (7-12 extract, index II, property card)",
        "Latest property-tax paid receipt",
        "Sanctioned / proposed plan drawings (architect sealed)",
        "Structural design + stability certificate (registered engineer sealed)",
        "NOCs required by the authority (fire / society / highway...)",
        "Undertakings (owner + licensed professional)",
        "Fee challan / receipts",
    ],
    "fire_noc": [
        "Building plan with fire exits, access and hydrant layout",
        "Fire-protection details as per the licensed fire consultant's scheme",
        "Stability certificate (structural engineer)",
        "Licensed agency engagement details",
        "Fee challan",
    ],
    "oc_cc": [
        "Completion certificate by architect / engineer (their seal, their sign)",
        "Structural stability certificate",
        "Fire NOC",
        "Water & drainage completion NOCs",
        "Lift inspection certificate (where there is a lift)",
        "Property tax assessment / clearance",
    ],
    "cte_cto": [
        "MPCB / pollution board application (consent to establish / operate)",
        "Project process description and water / air / waste loads",
        "Site layout with Effluent / stack locations",
        "Consent fees challan",
        "Undertaking on board's format",
    ],
    "utility": [
        "Application form (MSEDCL / water board / gas)",
        "Load estimate / demand note basis papers",
        "Ownership or occupation proof",
        "Test report / completion report (sealed by the electrical contractor, where applicable)",
        "Fee challan",
    ],
}


def _starter_for(purpose: str) -> list[dict]:
    p = (purpose or "").lower()
    for key, items in STARTER.items():
        for w in key.split("_"):
            if w and w in p:
                return [{"item": it, "done": False, "note": "starter - change it to match your ULB"} for it in items]
    return [{"item": "Application form (the authority's prescribed form)", "done": False, "note": ""}]


def file_new(tenant: str, project: str, authority: str, purpose: str, kind: str = "permission",
             licensee: str = "", fee=None, conv: str = "") -> dict:
    """One approval file opens with the starter checklist (#28); the licensee who files is NAMED or
    the owner does it - Hoola files nothing (tier C)."""
    if not str(project or "").strip() or not str(authority or "").strip() or not str(purpose or "").strip():
        raise CstError("Give the project, authority and purpose (for example: 'MCGM', 'building permission').")
    if kind not in ("permission", "noc", "consent", "certificate"):
        raise CstError("kind: permission | noc | consent | certificate")
    with _LOCK, session() as s:
        x = CApprovFile(tenant_id=tenant, project=project.strip()[:160], authority=authority.strip()[:160],
                        purpose=purpose.strip()[:200], kind=kind, status="draft",
                        licensee=licensee.strip()[:120], fee=_num(fee),
                        checklist=_dump(_starter_for(purpose)))
        s.add(x)
        s.flush()
        fid, n = x.id, len(_j(x.checklist, []))
    from .common import publish
    publish(tenant, "const_approvals", {"kind": "file_open", "project": project, "authority": authority}, conv)
    return {"file_id": fid, "checklist_items": n,
            "say": f"File opened: {project} - {authority} ({purpose}), checklist {n} items. "
                   + (f"The file goes in the name of licensee {licensee}. " if licensee else "The file goes under the OWNER's DSC. ")
                   + "Submitting is not Hoola's job (you/the licensee do it) - assembling, remembering and preparing are mine."}


def checklist(tenant: str, file_id: str = "", purpose: str = "") -> dict:
    """The checklist as DATA: for a file (its live rows) or for a purpose (the starter list)."""
    if file_id:
        with session() as s:
            x = s.get(CApprovFile, file_id)
            if not x or x.tenant_id != tenant:
                raise CstError("File not found.")
            rows = _j(x.checklist, [])
            return {"file_id": file_id, "authority": x.authority, "items": rows,
                    "say": f"{x.authority} checklist: {sum(1 for r in rows if r.get('done'))}/{len(rows)} done."}
    if purpose:
        rows = _starter_for(purpose)
        return {"purpose": purpose, "items": rows,
                "say": f"'{purpose}': STARTER checklist ({len(rows)} items) - change it to match your ULB, "
                       "this is data, not a rule."}
    raise CstError("file or purpose - give one.")


def check_mark(tenant: str, file_id: str, item: str, done: bool = True, note: str = "") -> dict:
    """One checklist row done / undone - the record follows HER word."""
    with _LOCK, session() as s:
        x = s.get(CApprovFile, file_id)
        if not x or x.tenant_id != tenant:
            raise CstError("File not found.")
        rows = _j(x.checklist, [])
        hit = None
        for r in rows:
            if item.strip().lower()[:60] in str(r.get("item", "")).lower():
                hit = r
                if done != bool(r.get("done")):
                    r["done"] = bool(done)
                if note:
                    r["note"] = note[:100]
                break
        if hit is None:
            rows.append({"item": item.strip()[:160], "done": bool(done), "note": note[:100]})
            hit = rows[-1]
        x.checklist = _dump(rows)
        pending = sum(1 for r in rows if not r.get("done"))
        authority, project = x.authority, x.project
    return {"file_id": file_id, "pending": pending,
            "say": f"{authority} ({project}): '{hit['item'][:60]}' {'done' if done else 're-open'}"
                   + (f", {pending} pending." if pending else " - whole checklist READY. Shall I assemble the packet?")}


def doc_add(tenant: str, file_id: str, kind: str, name: str, ref: str = "", note: str = "") -> dict:
    """One paper in the file (#29): form / drawing / ownership / NOC / undertaking / fee."""
    if not str(name or "").strip():
        raise CstError("Give the paper's name.")
    if kind not in ("form", "drawing", "ownership", "noc", "undertaking", "fee"):
        raise CstError("kind: form | drawing | ownership | noc | undertaking | fee")
    with _LOCK, session() as s:
        x = CApprovDoc(tenant_id=tenant, file_id=file_id[:40], kind=kind, name=name.strip()[:200],
                       ref=ref[:120], status="ready", note=note[:200])
        s.add(x)
        s.flush()
        did, fid = x.id, x.file_id
    return {"doc_id": did, "say": f"Paper added ({kind}): {name}" + (f" ({ref})" if ref else "") + " - marked READY."}


def doc_needed(tenant: str, file_id: str, kind: str, name: str, note: str = "") -> dict:
    """Mark a paper still missing - the packet shouts the gaps, never hides them."""
    if kind not in ("form", "drawing", "ownership", "noc", "undertaking", "fee"):
        raise CstError("kind: form | drawing | ownership | noc | undertaking | fee")
    with _LOCK, session() as s:
        x = CApprovDoc(tenant_id=tenant, file_id=file_id[:40], kind=kind, name=name.strip()[:200],
                       status="needed", note=note[:200])
        s.add(x)
        s.flush()
        did = x.id
    return {"doc_id": did, "say": f"Marked missing: {name} ({kind}) - this line will show in red when the packet is made."}


def packet(tenant: str, file_id: str) -> dict:
    """#29 / #36 the assembler: index + gaps + the cover PDF. The signature line stays empty for the
    licensee / owner - Hoola assembles, filing remains the human's act."""
    with session() as s:
        x = s.get(CApprovFile, file_id)
        if not x or x.tenant_id != tenant:
            raise CstError("File not found.")
        docs = s.scalars(select(CApprovDoc).where(CApprovDoc.tenant_id == tenant, CApprovDoc.file_id == file_id)).all()
    rows = _j(x.checklist, [])
    pending = [r["item"] for r in rows if not r.get("done")]
    missing = [d.name for d in docs if d.status == "needed"]
    ready = [d.name for d in docs if d.status == "ready"]
    gaps = pending + missing
    pdf = _packet_pdf(x, rows, docs)
    from .. import chatfiles
    f = chatfiles.store(tenant, f"Packet-{x.authority[:20].replace(' ', '')}-{x.id[:6]}.pdf", pdf, "application/pdf")
    say = (f"Packet ready: {x.project} - {x.authority} ({x.purpose}). Papers ready: {len(ready)}, gaps: {len(gaps)}. "
           + ("All done. " if not gaps else f"First complete these: {'; '.join(g[:70] for g in gaps[:5])}. ")
           + "Submission is under the OWNER's DSC / by the licensee's hand - Hoola does not submit.")
    return {"file_id": file_id, "ready": len(ready), "gaps": gaps, "file": f, "say": say}


def _packet_pdf(x: CApprovFile, rows: list, docs: list) -> bytes:
    """The packet cover: file facts, checklist state, the papers, the EMPTY signature line."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text)[:110])
        y -= size + 5

    t(50, "SUBMISSION PACKET - INDEX", 13, True)
    t(50, f"Project: {x.project}    Authority: {x.authority}")
    t(50, f"Purpose: {x.purpose}    Kind: {x.kind}")
    if x.licensee:
        t(50, f"Filed by (licensee): {x.licensee}")
    else:
        t(50, "Filed by: OWNER (DSC)")
    y -= 8
    t(50, "CHECKLIST:", 11, True)
    for r in rows[:14]:
        t(56, f"[{'x' if r.get('done') else ' '}] {r.get('item', '')}", 9.5)
    y -= 6
    t(50, "PAPERS IN FILE:", 11, True)
    for d in docs[:16]:
        t(56, f"{d.status.upper():7s} {d.kind}: {d.name}" + (f" ({d.ref})" if d.ref else ""), 9.5)
    y -= 16
    t(50, "Submitted by: ____________________________   Date: ____________", 10)
    t(50, "(owner / licensed professional - Hoola can never fill in this line)", 8.5)
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def file_mark(tenant: str, file_id: str, status: str, ref_no: str = "", on: str = "", valid_till: str = "") -> dict:
    """Status walk: draft -> ready -> submitted -> queried -> approved/rejected. Submission and
    approval dates are recorded AS THE AUTHORITY DID THEM - Hoola watches the clock, not the file."""
    if status not in ("draft", "ready", "submitted", "queried", "approved", "rejected"):
        raise CstError("status: draft | ready | submitted | queried | approved | rejected")
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CApprovFile, file_id)
        if not x or x.tenant_id != tenant:
            raise CstError("File not found.")
        x.status = status
        if ref_no:
            x.ref_no = ref_no[:80]
        if status == "submitted" and d:
            x.submitted_on = d.isoformat()
        if status == "approved":
            if d:
                x.approved_on = d.isoformat()
            vt = _date(valid_till)
            if vt:
                x.valid_till = vt.isoformat()
            # #34 the approval's validity lands on the statutory calendar the moment she records it
            if x.valid_till:
                s.add(CApprovCal(tenant_id=tenant, authority=x.authority[:160],
                                 item=f"{x.purpose} validity (ref {x.ref_no or x.id[:8]})",
                                 due_on=x.valid_till, last_done=x.approved_on, file_id=x.id, status="open"))
        if status == "rejected" and d:
            x.note = (f"rejected on {d.isoformat()} | " + x.note)[:300]
        authority, project, purpose = x.authority, x.project, x.purpose
    from .common import publish
    publish(tenant, "const_approvals", {"kind": f"file_{status}", "file_id": file_id, "authority": authority})
    return {"file_id": file_id, "status": status,
            "say": f"{authority} ({project}, {purpose}): status -> {status}" + (f", ref {ref_no}" if ref_no else "")
                   + (f", valid till {valid_till} (added to the calendar)" if status == "approved" and valid_till else "")
                   + ". Further work (renewal, compliance) only with the compliance officer's approval."}


def cal_add(tenant: str, authority: str, item: str, due_on: str, last_done: str = "", file_id: str = "",
            conv: str = "") -> dict:
    """#34 statutory calendar: the due date SHE records (fire NOC renewal, CTO validity...)."""
    d = _date(due_on)
    if not str(item or "").strip() or d is None:
        raise CstError("Both the item and the due date are needed (for example 'Fire NOC renewal', '2027-06-30').")
    with _LOCK, session() as s:
        x = CApprovCal(tenant_id=tenant, authority=authority.strip()[:160], item=item.strip()[:200],
                       due_on=d.isoformat(), last_done=(_date(last_done) or "").isoformat() if last_done else "",
                       file_id=file_id[:40], status="open")
        s.add(x)
        s.flush()
        cid = x.id
    from .common import publish
    publish(tenant, "const_approvals", {"kind": "cal_add", "item": item, "due_on": d.isoformat()}, conv)
    return {"cal_id": cid, "say": f"Calendar: {item} ({authority or '-'}) due {d.strftime('%d %b %Y')}. "
                                  "I remind you when it is due - renewal only with your / the compliance officer's approval."}


def cal_done(tenant: str, cal_id: str, on: str = "") -> dict:
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CApprovCal, cal_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Calendar row not found.")
        x.status = "done"
        x.last_done = d.isoformat() if d else x.last_done
        item = x.item
    return {"say": f"'{item}' marked done ({d.isoformat() if d else 'today'}). The next due date comes from a new row."}


def cal_due(tenant: str, days: int = 30) -> dict:
    """What falls due: late first, then the coming window - the counts are honest, the act is hers."""
    d0 = today(tenant)
    with session() as s:
        rows = s.scalars(select(CApprovCal).where(CApprovCal.tenant_id == tenant, CApprovCal.status == "open")).all()
    late, soon = [], []
    for r in rows:
        dd = _date(r.due_on)
        if dd is None:
            continue
        delta = (dd - d0).days
        if delta < 0:
            late.append({"item": r.item, "authority": r.authority, "due_on": r.due_on, "late_by": -delta})
        elif delta <= max(0, int(days)):
            soon.append({"item": r.item, "authority": r.authority, "due_on": r.due_on, "in_days": delta})
    late.sort(key=lambda x: -x["late_by"])
    soon.sort(key=lambda x: x["in_days"])
    say = (f"Statutory calendar: {len(late)} LATE, {len(soon)} due in the next {days} days."
           + (f" Late: {'; '.join(r['item'][:40] for r in late[:3])}" if late else "")
           + (f" Coming up: {'; '.join(r['item'][:40] for r in soon[:3])}" if soon else "")
           + " Renewal needs the compliance officer's approval.")
    return {"late": late, "soon": soon, "say": say}


def day(tenant: str) -> dict:
    """The approvals morning: files in play, gaps open, calendar shouting."""
    with session() as s:
        files = s.scalars(select(CApprovFile).where(CApprovFile.tenant_id == tenant)).all()
        docs = s.scalars(select(CApprovDoc).where(CApprovDoc.tenant_id == tenant, CApprovDoc.status == "needed")).all()
    open_files = [f for f in files if f.status in ("draft", "ready", "submitted", "queried")]
    say = (f"Approvals: {len(open_files)} files in progress, {len(docs)} papers still needed"
           + (f" ({', '.join(f.authority for f in open_files[:3])})" if open_files else "") + ".")
    return {"open_files": len(open_files), "missing_papers": len(docs), "say": say}

# ---------------------------------------------------------------- Wave 4: #33 Heritage / AAI / CRZ screener
def screener_add(tenant: str, project: str, rows: list, by: str = "", note: str = "",
                 conv: str = "") -> dict:
    """Clearance APPLICABILITY register - rows [clearance, applies(yes/no/unsure), trigger,
    documents]. `applies` is HER mark (with the liaison officer's name), the trigger her note; the
    application itself stays the owner's (tier C: 'file a permission application' already gates)."""
    from . import models as WM
    from .common import publish as pub
    if not rows:
        raise CstError("Screener rows are needed [clearance, applies, trigger, documents].")
    if not by:
        raise CstError("Applicability needs the NAME of the person stating it (liaison/consultant).")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            applies = str(r[1])[:8].lower()
            if applies not in ("yes", "no", "unsure"):
                raise CstError(f"'{r[0]}': applies yes | no | unsure (your mark, recorded).")
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="screener",
                                name=str(r[0])[:120],
                                data=_dump({"applies": applies,
                                            "trigger": str(r[2])[:160] if len(r) > 2 else "",
                                            "docs": str(r[3])[:300] if len(r) > 3 else "",
                                            "note": note[:200]}),
                                by=by))
            made += 1
    pub(tenant, "const_approvals", {"kind": "screener", "project": project, "rows": made}, conv)
    unsure = sum(1 for r in rows if isinstance(r, (list, tuple)) and len(r) > 1
                 and str(r[1]).lower() == "unsure")
    return {"ok": True, "rows": made, "by": by, "unsure": unsure,
            "said": (f"{made} clearance row(s) ({by}). {unsure} 'unsure' - the consultant/liaison "
                     "confirms those; Hoola does not fetch/decide any clearance.")}


def screener_list(tenant: str, project: str) -> dict:
    from . import models as WM
    with session() as s:
        rows = s.scalars(select(WM.Cw4ExtItem).where(WM.Cw4ExtItem.tenant_id == tenant,
                                                     WM.Cw4ExtItem.project == project,
                                                     WM.Cw4ExtItem.kind == "screener")).all()
    return {"rows": [{"clearance": r.name, **_j(r.data, {}), "by": r.by} for r in rows]}
