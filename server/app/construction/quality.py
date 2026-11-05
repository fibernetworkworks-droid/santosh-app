"""#75 Quality Auditor's Assistant + #76 Material Test Register Keeper + #78 Snagging punch-list glue
(v0.512.0, Wave 1). ITPs with hold points, NCRs, material-test lots, and the IS 456 cube-acceptance
DRAFT (M20 and above: mean of the group >= fck + 4 N/mm2 and every individual cube >= fck - 4 N/mm² -
IS 456:2000 cl 16.1 / Table 11). The DRAFT is explicitly a draft: acceptance is the QA engineer's act
(tier B edge inside a tier-A desk, said on every output). Punch list reads sitesup snags - never
duplicated here."""
from __future__ import annotations

import io
import re

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import (CItp, CNcr, CQualIncident, CQualIncRow, CQualPermit, CQualToolbox, CTestLot)

# IS 456:2000 cl 16.1 & Table 11 - M20 and above: mean >= fck + 4, individual >= fck - 4 (N/mm2).
# Below M20 Table 11 works on the standard deviation route - Hoola refuses and says so (never guesses sigma).
CUBE_MEAN_PLUS = 4.0
CUBE_INDIV_MINUS = 4.0


def itp(tenant: str, site: str, activity: str, steps: list | None, status: str = "", approved_by: str = "",
        note: str = "", conv: str = "") -> dict:
    if not str(site or "").strip() or not str(activity or "").strip():
        raise CstError("Site aur activity bataiye (jaise 'Footing concrete M25').")
    clean: list[dict] = []
    for st in (steps or []):
        if isinstance(st, dict) and str(st.get("step", "")).strip():
            clean.append({"step": str(st.get("step"))[:200], "spec": str(st.get("spec", ""))[:300],
                          "hold": bool(st.get("hold"))})
    if not clean:
        raise CstError("ITP ke steps bataiye [{step, spec, hold}] - hold = jahan inspection ke bina aage nahi.")
    with _LOCK, session() as s:
        x = CItp(tenant_id=tenant, site=site.strip()[:160], activity=activity.strip()[:200], steps=_dump(clean),
                 status=(status or "draft")[:12], approved_by=approved_by[:120], note=note[:300])
        s.add(x)
        s.flush()
        iid, holds = x.id, sum(1 for c in clean if c["hold"])
    from .common import publish
    publish(tenant, "const_quality", {"kind": "itp", "site": site, "activity": activity}, conv)
    return {"itp_id": iid, "steps": len(clean), "hold_points": holds,
            "say": f"ITP DRAFT: {activity} - {len(clean)} steps, {holds} HOLD points. QA/QC manager approve karega tab yeh chalega "
                   "(hold par Hoola kaam rukne ka card banata hai, khud nahi rokta)."}


def itp_approve(tenant: str, itp_id: str, approved_by: str) -> dict:
    """status -> approved, recorded on HER word (the QA/QC manager / owner)."""
    who = str(approved_by or "").strip()
    if not who:
        raise CstError("Kaun approve kar raha hai - naam bataiye (approval uska record hota hai).")
    with _LOCK, session() as s:
        x = s.get(CItp, itp_id)
        if not x or x.tenant_id != tenant:
            raise CstError("ITP nahi mili.")
        x.status = "approved"
        x.approved_by = who[:120]
        activity = x.activity
    return {"say": f"ITP '{activity}' approved ho gayi maane - {who} ke naam se record."}


def ncr(tenant: str, site: str, activity: str, defect: str, spec: str = "", severity: str = "minor",
        action: str = "", itp_id: str = "", conv: str = "") -> dict:
    if not str(defect or "").strip():
        raise CstError("Defect bataiye (kya spec fail hua).")
    if severity not in ("minor", "major", "critical"):
        raise CstError("severity: minor | major | critical")
    with _LOCK, session() as s:
        x = CNcr(tenant_id=tenant, site=site.strip()[:160], activity=activity[:200], defect=defect[:2000],
                 spec=spec[:300], severity=severity, action=action[:300], status="open",
                 raised_on=today(tenant).isoformat(), itp_id=itp_id[:40])
        s.add(x)
        s.flush()
        nid, sev = x.id, x.severity
    from .common import publish
    publish(tenant, "const_quality", {"kind": "ncr", "site": site, "severity": sev}, conv)
    return {"ncr_id": nid, "say": f"NCR #{nid[:8]} khuli: {site} - {defect[:80]}" + (f" (spec: {spec[:60]})" if spec else "")
            + f", severity {sev}. Repair / close-out QA/QC manager decide karenge."}


def ncr_close(tenant: str, ncr_id: str, action: str = "", note: str = "") -> dict:
    with _LOCK, session() as s:
        x = s.get(CNcr, ncr_id)
        if not x or x.tenant_id != tenant:
            raise CstError("NCR nahi mili.")
        x.status = "closed"
        x.closed_on = today(tenant).isoformat()
        if action:
            x.action = action[:300]
        if note:
            x.defect = (x.defect + " | close-out: " + note)[:2000]
        site, defect = x.site, x.defect
    return {"say": f"NCR #{ncr_id[:8]} ({site}) band ho gayi. {note[:120]}"}


def test_lot(tenant: str, kind: str, lot_no: str = "", vendor: str = "", test: str = "", lab: str = "",
             result: str = "", verdict: str = "pending", tested_on: str = "", retest_due: str = "",
             report_ref: str = "", note: str = "") -> dict:
    """#76 the register: what the lab REPORTED goes in as reported; pass/fail is the QC engineer's word
    (verdict pending until a human says it) - Hoola never grades a lab result by itself."""
    if not str(kind or "").strip():
        raise CstError("Material / lot bataiye (jaise 'Cement OPC 53').")
    if verdict not in ("pending", "pass", "fail"):
        raise CstError("verdict: pending | pass | fail")
    with _LOCK, session() as s:
        x = CTestLot(tenant_id=tenant, kind=kind.strip()[:60], vendor=vendor[:160], lot_no=lot_no[:80],
                     test=test[:160], lab=lab[:160], result=result[:300], verdict=verdict,
                     tested_on=(_date(tested_on) or today(tenant)).isoformat(),
                     retest_due=(_date(retest_due) or "").isoformat() if retest_due else "",
                     report_ref=report_ref[:120], note=note[:300])
        s.add(x)
        s.flush()
        tid, v = x.id, x.verdict
    return {"lot_id": tid, "say": f"Test lot juda: {kind} (lot {lot_no or '-'}) - {test or 'test? '}, lab {lab or '-'}: {result[:60] or 'result aane wala'}. "
            + ("Verdict QC engineer dega (abhi pending)." if v == "pending" else f"Verdict record: {v}.")}


def lot_verdict(tenant: str, lot_id: str, verdict: str, by: str = "") -> dict:
    if verdict not in ("pass", "fail"):
        raise CstError("verdict: pass | fail")
    with _LOCK, session() as s:
        x = s.get(CTestLot, lot_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Lot nahi mila.")
        x.verdict = verdict
        kind, res = x.kind, x.result
    return {"say": f"{kind} lot verdict record: {verdict}" + (f" ({by})" if by else "") + f". Lab ka result: {res[:80]}."}


def cube_draft(tenant: str, grade: str, results: list) -> dict:
    """IS 456 Table 11 DRAFT for M20 and above: mean of the group >= fck+4 and every cube >= fck-4.
    Below M20 the standard-deviation route applies - refused with the reason, never faked.
    THE VERDICT IS A DRAFT: acceptance is the QA engineer's act (tier C edge, said on the output)."""
    g = (grade or "").strip().upper()
    m = re.fullmatch(r"M(\d{2})", g)
    if not m:
        raise CstError("Grade bataiye (M20, M25, M30...).")
    fck = int(m.group(1))
    if fck < 20:
        raise CstError(f"{g} ke liye IS 456 Table 11 standard-deviation route chalta hai - Hoola sigma guess nahi karta. "
                       "Lab report ke saath QA engineer se poochho.")
    vals = [_num(v) for v in (results or []) if _num(v) > 0]
    if len(vals) < 3:
        raise CstError("Kam se kam 3 cube results chahiye (N/mm2).")
    mean = round(sum(vals) / len(vals), 2)
    low = round(min(vals), 2)
    ok_mean = mean >= fck + CUBE_MEAN_PLUS
    ok_ind = low >= fck - CUBE_INDIV_MINUS
    draft = "PASS (DRAFT)" if (ok_mean and ok_ind) else "NOT MET (DRAFT)"
    say = (f"IS 456 cl 16.1 / Table 11 DRAFT ({g}, fck {fck} N/mm2): mean {mean} >= {fck + CUBE_MEAN_PLUS:g}? "
           f"{'haan' if ok_mean else 'NAHI'}; sabse kam cube {low} >= {fck - CUBE_INDIV_MINUS:g}? {'haan' if ok_ind else 'NAHI'} -> {draft}. "
           "Acceptance QA engineer ke sign se - yeh sirf computing hai.")
    return {"grade": g, "mean": mean, "min": low, "mean_ok": ok_mean, "individual_ok": ok_ind, "draft": draft, "say": say}


def punch(tenant: str, site: str = "") -> dict:
    """#78 glue over sitesup snags (never duplicated): the punch list by trade with the open count."""
    from ..sitesup import service as SS
    rows = SS.snags(tenant, site=site, status="") if site else SS.snags(tenant, status="")
    open_rows = [r for r in rows if r.get("status") == "open"]
    by_trade: dict[str, int] = {}
    for r in open_rows:
        t = r.get("trade") or "misc"
        by_trade[t] = by_trade.get(t, 0) + 1
    say = (f"Punch list{' - ' + site if site else ''}: {len(open_rows)} open / {len(rows)} total."
           + (" Trades: " + ", ".join(f"{k} {v}" for k, v in sorted(by_trade.items(), key=lambda x: -x[1])[:6]) if by_trade else "")
           + " Close-out verification QA engineer ki.")
    return {"open": len(open_rows), "total": len(rows), "by_trade": by_trade, "rows": rows[:20], "say": say}


def day(tenant: str) -> dict:
    """The QA morning: open NCRs, hold points due, lots pending verdict / retest, permits expiring,
    incidents open (v0.550: the #82 investigations ride this desk)."""
    t0 = today(tenant)
    with session() as s:
        ncrs = s.scalars(select(CNcr).where(CNcr.tenant_id == tenant, CNcr.status == "open")).all()
        lots = s.scalars(select(CTestLot).where(CTestLot.tenant_id == tenant, CTestLot.verdict == "pending")).all()
        retest = [r for r in s.scalars(select(CTestLot).where(CTestLot.tenant_id == tenant)).all()
                  if r.retest_due and r.retest_due <= t0.isoformat()]
        permits = [p for p in s.scalars(select(CQualPermit).where(CQualPermit.tenant_id == tenant,
                                                          CQualPermit.status == "issued")).all()
                   if p.valid_till and p.valid_till <= t0.isoformat()]
        incidents = s.scalars(select(CQualIncident).where(CQualIncident.tenant_id == tenant,
                                                          CQualIncident.status == "open")).all()
    say = (f"Quality: {len(ncrs)} NCR khuli, {len(lots)} lab results verdict-pending"
           + (f", {len(retest)} retest due" if retest else "")
           + (f", {len(permits)} permit ki validity khatam" if permits else "")
           + (f", {len(incidents)} incident investigation khuli" if incidents else "") + ".")
    return {"open_ncrs": len(ncrs), "pending_lots": len(lots), "retest_due": len(retest),
            "permits_expired": len(permits), "incidents_open": len(incidents), "say": say}


# ------------------------------------------------------------------ #81 EHS Officer's Assistant (Wave 2 C10)
def permit_draft(tenant: str, site: str, kind: str, hazard: str, controls: list, valid_from: str = "",
                 valid_till: str = "", conv: str = "") -> dict:
    """Permit-to-work DRAFT: hazard + controls as data. The PERMIT ITSELF the safety officer issues
    (tier C: 'give a permit-to-work') - Hoola prepares the paper and keeps the record."""
    if not str(site or "").strip() or not str(hazard or "").strip():
        raise CstError("Site aur hazard bataiye (jaise 'Tower B', '5 m neeche gadda - worker fall').")
    if kind not in ("height", "confined space", "hot work", "excavation", "electrical"):
        raise CstError("kind: height | confined space | hot work | excavation | electrical")
    clean = [{"control": str(c.get("control", ""))[:200], "done": bool(c.get("done"))}
             for c in (controls or []) if isinstance(c, dict) and str(c.get("control", "")).strip()]
    if not clean:
        raise CstError("Controls bhejo [{control, done}] - bina control ka permit kagaz nahi hota.")
    with _LOCK, session() as s:
        x = CQualPermit(tenant_id=tenant, site=site.strip()[:160], kind=kind, hazard=hazard.strip()[:300],
                        controls=_dump(clean), valid_from=(_date(valid_from) or today(tenant)).isoformat(),
                        valid_till=(_date(valid_till) or "").isoformat() if valid_till else "", status="draft")
        s.add(x)
        s.flush()
        pid = x.id
    from .common import publish
    publish(tenant, "const_ehs", {"kind": "permit_draft", "site": site, "permit": kind}, conv)
    return {"permit_id": pid, "controls": len(clean),
            "say": f"Permit DRAFT ({kind}): {site} - {hazard[:80]}, {len(clean)} controls. "
                   "Issue SAFETY OFFICER karegi (main kabhi nahi) - unke naam ke saath 'issued' hota hai."}


def permit_issue(tenant: str, permit_id: str, issued_by: str) -> dict:
    """status -> issued, on the safety officer's NAMED word. Bina naam ke permit issue nahi hota."""
    who = str(issued_by or "").strip()
    if not who:
        raise CstError("Kaun issue kar rahi hai? Safety officer ka naam chahiye - permit unki haan se "
                       "hoti hai (main DRAFT se aage nahi jaata khud se).")
    with _LOCK, session() as s:
        x = s.get(CQualPermit, permit_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Permit nahi mili.")
        x.status = "issued"
        x.issued_by = who[:120]
        site, kind = x.site, x.kind
    from .common import publish
    publish(tenant, "const_ehs", {"kind": "permit_issued", "site": site, "permit": kind})
    return {"say": f"Permit ({kind}, {site}) ISSUED - {who} ke naam se record. Validity unki tay ki hui."}


def permit_close(tenant: str, permit_id: str, note: str = "") -> dict:
    with _LOCK, session() as s:
        x = s.get(CQualPermit, permit_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Permit nahi mili.")
        x.status = "closed"
        if note:
            x.note = note[:200]
        site, kind = x.site, x.kind
    return {"say": f"Permit ({kind}, {site}) closed. Kaam poora - record band."}


def toolbox_log(tenant: str, site: str, topic: str, day: str = "", attendees=None, gang: str = "",
                note: str = "", conv: str = "") -> dict:
    """The toolbox talk, recorded as it happened: topic, day, gang, headcount."""
    if not str(site or "").strip() or not str(topic or "").strip():
        raise CstError("Site aur topic bataiye (jaise 'Tower B', 'height work - harness').")
    with _LOCK, session() as s:
        x = CQualToolbox(tenant_id=tenant, site=site.strip()[:160], topic=topic.strip()[:200],
                         day=(_date(day) or today(tenant)).isoformat(), gang=gang.strip()[:120],
                         attendees=int(_num(attendees)), note=note[:300])
        s.add(x)
        s.flush()
        tid = x.id
    from .common import publish
    publish(tenant, "const_ehs", {"kind": "toolbox", "site": site, "topic": topic}, conv)
    return {"toolbox_id": tid,
            "say": f"Toolbox talk record: {topic[:60]} ({site}, gang {gang or '-'}, {int(_num(attendees))} aadami). "
                   "Safety talk ka hisaab EHS officer ke saath."}


# ---------------------------------------------------------------- #82 incident investigation (C13, Wave 3)
# The register: "timeline, witness question lists, root-cause tools, corrective actions; findings by
# the safety officer". The record and the 5-why structure are Hoola's; the ROOT CAUSE and the findings
# are the safety head's word, recorded WITH the name - a closed incident without a name does not exist.

WITNESS_QUESTIONS = [
    "Aap tab kahan khade the / kya kar rahe the?",
    "Aapne kya dekha - pehle kya hua, phir kya hua (order mein bataiye)?",
    "Us waqt kaam / machine / area ke baare mein kya alag (unusual) lag raha tha?",
    "Kya safety equipment / guard us waqt lagi thi (PPE, railing, lockout)?",
    "Kya pehle bhi aisi ghatna / lagbhag-ghatna (near miss) hui thi?",
    "Kisne dekha / suna iske alawa - aur kaun pukaar kar pehle pahuncha?",
]


def incident_open(tenant: str, site: str, kind: str, severity: str, description: str,
                  day: str = "", reported_by: str = "", conv: str = "") -> dict:
    """An incident opens (#82): near_miss | injury | property | environmental, severity, what happened
    as reported. The investigation walks from here; findings close it."""
    if not str(site or "").strip() or not str(description or "").strip():
        raise CstError("Site aur ghatna ka varnan bataiye.")
    if kind not in ("near_miss", "injury", "property", "environmental"):
        raise CstError("kind: near_miss | injury | property | environmental")
    if severity not in ("minor", "major", "critical"):
        raise CstError("severity: minor | major | critical")
    with _LOCK, session() as s:
        x = CQualIncident(tenant_id=tenant, site=site.strip()[:160], day=(_date(day) or today(tenant)).isoformat(),
                          kind=kind, severity=severity, description=description.strip()[:500],
                          reported_by=reported_by.strip()[:120])
        s.add(x)
        s.flush()
        iid = x.id
    from .common import publish
    publish(tenant, "const_ehs", {"kind": "incident_open", "site": site, "sev": severity}, conv)
    return {"incident_id": iid,
            "say": f"Incident khula ({kind}, {severity}): {description.strip()[:60]}... Timeline, "
                   "witness notes, 5-why aur corrective actions isi pe judenge. Findings SAFETY HEAD "
                   "ke naam se band hongi - Hoola sirf paper rakhta hai."}


def incident_row(tenant: str, incident_id: str, kind: str, text: str = "", at: str = "",
                 answer: str = "", owner: str = "", due: str = "", status: str = "") -> dict:
    """One row of the investigation: timeline (at + event), witness note, a 5-why step (text = why,
    answer = answer), or a corrective action (text, owner, due, status)."""
    if kind not in ("timeline", "witness", "why", "action"):
        raise CstError("kind: timeline | witness | why | action")
    text = str(text or "").strip()
    if not text:
        raise CstError("Row ka text bataiye (event / note / why / action).")
    if kind == "action" and status and status not in ("open", "done"):
        raise CstError("Action ka status: open | done.")
    with _LOCK, session() as s:
        inc = s.get(CQualIncident, incident_id)
        if not inc or inc.tenant_id != tenant:
            raise CstError("Incident nahi mila.")
        if inc.status == "closed":
            raise CstError("Yeh incident band ho chuki hai - nayi rows ke liye pehle findings reopen "
                           "karna hoga (safety head ke word se).")
        x = CQualIncRow(tenant_id=tenant, incident_id=incident_id, kind=kind, at=(at or "")[:10],
                        text=text[:300], answer=str(answer or "").strip()[:300], owner=owner.strip()[:120],
                        due=(due or "")[:10], status=(status or ("open" if kind == "action" else ""))[:16])
        s.add(x)
        s.flush()
        rid = x.id
    say = {"timeline": f"Timeline + {at or '-'}: {text[:60]}",
           "witness": f"Witness note: {text[:60]}",
           "why": f"5-why: {text[:50]} -> {str(answer or '').strip()[:50] or '(answer baaki)'}",
           "action": f"Corrective action: {text[:50]} ({owner.strip() or 'owner?'}"
                     f", due {due or '-'}, {x.status})"}[kind]
    return {"row_id": rid, "say": say}


def incident_questions() -> dict:
    """The witness question list (#82) - the standard six, in Hinglish, ready to ask. Not legal advice;
    the interview conduct is the safety head's."""
    return {"questions": WITNESS_QUESTIONS,
            "say": f"{len(WITNESS_QUESTIONS)} witness sawaal - sab se pehle jo dekha, order mein. "
                   "Interview karna aur likhna safety head ka tareeqa hai; yeh list sirf yaad dilati hai."}


def incident_close(tenant: str, incident_id: str, root_cause: str, findings_by: str) -> dict:
    """Close the investigation: ROOT CAUSE and findings recorded - with the SAFETY HEAD'S NAME (tier B
    edge: without the name the close refuses; the findings are hers, Hoola keeps the paper)."""
    if not str(root_cause or "").strip():
        raise CstError("Root cause bataiye - yeh AAPKI (safety head ki) finding hai, Hoola nahi nikalta.")
    if not str(findings_by or "").strip():
        raise CstError("Findings kiski? Safety head ka NAAM zaroori hai - bina naam findings kisi ki "
                       "nahi hoti.")
    with _LOCK, session() as s:
        x = s.get(CQualIncident, incident_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Incident nahi mila.")
        open_actions = s.scalars(select(CQualIncRow).where(
            CQualIncRow.tenant_id == tenant, CQualIncRow.incident_id == incident_id,
            CQualIncRow.kind == "action", CQualIncRow.status != "done")).all()
        if open_actions:
            raise CstError(f"{len(open_actions)} corrective action abhi open hain - pehle unhe done karo, "
                           "phir findings.")
        x.root_cause, x.findings_by, x.status = root_cause.strip()[:300], findings_by.strip()[:120], "closed"
    return {"say": f"Incident band ({findings_by.strip()} ki findings): root cause - "
                   f"'{root_cause.strip()[:70]}'. Corrective actions sab done. Yeh record hai - "
                   "reporting / notification ka decision management + consultant ka."}


def incident_pack(tenant: str, incident_id: str) -> dict:
    """The investigation pack PDF: description, timeline, witness notes, the 5-why chain, corrective
    actions, the root cause and findings line - her name if closed, EMPTY if still open."""
    with session() as s:
        x = s.get(CQualIncident, incident_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Incident nahi mila.")
        rows = s.scalars(select(CQualIncRow).where(CQualIncRow.tenant_id == tenant,
                                                   CQualIncRow.incident_id == incident_id)).all()
    buf = io.BytesIO()

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text)[:110])
        y -= size + 5

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50
    t(50, "INCIDENT INVESTIGATION PACK", 13, True)
    t(50, f"{x.kind} / {x.severity}    Site: {x.site}    Day: {x.day}    Reported by: {x.reported_by or '-'}")
    t(50, f"What happened: {x.description[:100]}")
    y -= 6
    for kind, label in (("timeline", "TIMELINE"), ("witness", "WITNESS"), ("why", "5-WHY"),
                        ("action", "CORRECTIVE ACTIONS")):
        mine = [r for r in rows if r.kind == kind]
        if not mine:
            continue
        t(50, label, 10, True)
        for r in mine[:12]:
            line = f"{r.at or '-':10s} {r.text[:60]}" if kind in ("timeline", "witness") else \
                   f"why: {r.text[:50]} -> {r.answer[:40]}" if kind == "why" else \
                   f"[{r.status or 'open'}] {r.text[:50]} ({r.owner or '-'}, due {r.due or '-'})"
            t(56, line, 9)
        y -= 4
    y -= 6
    t(50, f"Root cause: {x.root_cause or '(abhi - safety head likhenge)'}")
    t(50, f"Findings by: {x.findings_by or '____________________________'}", 10)
    t(50, "(safety head - yeh findings unke shabd hain; Hoola kabhi findings nahi likhta)", 8.5)
    pdf.showPage()
    pdf.save()
    from .. import chatfiles
    f = chatfiles.store(tenant, f"INC-{x.site[:16].replace(' ', '-')}-{x.id[:6]}.pdf", buf.getvalue(),
                        "application/pdf")
    return {"file": f, "status": x.status,
            "say": f"Investigation pack: {len(rows)} rows, status {x.status}. Findings line safety head "
                   "ki hai - khali ya unke naam se."}
