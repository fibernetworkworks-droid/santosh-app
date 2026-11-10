"""C13b: the Delay Analyst's working-paper desk (register #47) - Wave 3, v0.550.0, plan
docs/CONSTRUCTION_EMPLOYEE_PLAN.md §7.

The register's own words: "baseline vs updates, as-planned vs as-built, windows; the conclusion is not
computable". So the desk keeps the programmes as DATA (baseline rows with HER criticality marks - Hoola
never computes a CPM network), the windows she chooses, the notice-compliance arithmetic the contract
itself fixes, and prints the as-planned vs as-built comparison with slip days per activity. The
ENTITLEMENT (EOT, delay damages) is the forensic planner's and counsel's conclusion on the working
paper - the tier-C refusal (gates.py: "decide delay entitlement") rides every ask."""
from __future__ import annotations

import io
from datetime import date

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import CdelNotice, CdelProg, CdelWindow


def _clean_rows(rows: list, kind: str) -> list[dict]:
    clean: list[dict] = []
    for r in (rows or []):
        if not isinstance(r, dict) or not str(r.get("activity", "")).strip():
            continue
        st = _date(r.get("start"))
        fi = _date(r.get("finish"))
        if not st or not fi:
            raise CstError(f"Activity '{r.get('activity')}' ke start/finish dates parse nahi hue "
                           "(YYYY-MM-DD bhejo).")
        row = {"activity": str(r.get("activity")).strip()[:160],
               "start": st.isoformat(), "finish": fi.isoformat()}
        if kind == "baseline":
            row["critical"] = bool(r.get("critical"))
        clean.append(row)
    if not clean:
        fields = "activity, start, finish" + (", critical" if kind == "baseline" else "")
        raise CstError(f"Programme rows bhejo [{{{fields}}}].")
    return clean


def prog_add(tenant: str, project: str, kind: str, rows: list, note: str = "", conv: str = "") -> dict:
    """One programme as DATA: baseline (criticality marks HERS - the CPM is never computed here) or
    as-built actuals. Versioned by row; the working paper compares what she feeds."""
    if kind not in ("baseline", "asbuilt"):
        raise CstError("kind: baseline | asbuilt")
    clean = _clean_rows(rows, kind)
    with _LOCK, session() as s:
        x = CdelProg(tenant_id=tenant, project=project.strip()[:160], kind=kind, rows=_dump(clean),
                     note=note.strip()[:200])
        s.add(x)
        s.flush()
        pid, cnt = x.id, len(clean)
    from .common import publish
    publish(tenant, "const_delay", {"kind": "prog_add", "project": project, "prog": kind}, conv)
    crit = sum(1 for r in clean if r.get("critical")) if kind == "baseline" else 0
    say = (f"Baseline {cnt} activities (critical marks AAPKI: {crit} rows) - Hoola CPM compute NAHI "
           "karta, criticality wahi hai jo aapne likhi." if kind == "baseline" else
           f"As-built {cnt} activities (actual start/finish as fed).")
    return {"prog_id": pid, "rows": cnt, "say": say + " Working paper isi se banta hai."}


def window_add(tenant: str, project: str, label: str, start: str, finish: str, note: str = "") -> dict:
    """One analysis window: her date range - windows are the analyst's choice, not code's."""
    st, fi = _date(start), _date(finish)
    if not str(label or "").strip() or not st or not fi:
        raise CstError("Label aur window ki dates bataiye (YYYY-MM-DD).")
    if fi < st:
        raise CstError("Window ka finish start se pehle nahi ho sakta.")
    with _LOCK, session() as s:
        x = CdelWindow(tenant_id=tenant, project=project.strip()[:160], label=label.strip()[:80],
                       start=st.isoformat(), finish=fi.isoformat(), note=note.strip()[:200])
        s.add(x)
        s.flush()
        wid = x.id
    return {"window_id": wid,
            "say": f"Window '{label.strip()}': {st} -> {fi}. As-built actuals isi mein gir kar dekhe "
                   "jaate hain - impact table mein."}


def impact(tenant: str, project: str) -> dict:
    """The comparison: per as-built activity, planned finish vs actual finish -> slip days, the
    windows the slip fell into, her criticality flag beside it. A working paper, not a verdict."""
    with session() as s:
        progs = s.scalars(select(CdelProg).where(CdelProg.tenant_id == tenant,
                                                 CdelProg.project == project)).all()
        wins = s.scalars(select(CdelWindow).where(CdelWindow.tenant_id == tenant,
                                                  CdelWindow.project == project)).all()
    base = next((p for p in progs if p.kind == "baseline"), None)
    built = next((p for p in progs if p.kind == "asbuilt"), None)
    if not base or not built:
        raise CstError("Baseline AUR as-built dono chahiye (prog_add se). Slip unke beech ka hisaab hai.")
    bmap = {r["activity"]: r for r in _j(base.rows, [])}
    rows = []
    for r in _j(built.rows, []):
        b = bmap.get(r["activity"])
        if not b:
            continue
        slip = (_date(r["finish"]) - _date(b["finish"])).days
        hits = [w.label for w in wins
                if w.start <= r["finish"] <= w.finish or w.start <= b["finish"] <= w.finish]
        rows.append({"activity": r["activity"], "planned_finish": b["finish"],
                     "actual_finish": r["finish"], "slip_days": slip,
                     "critical_her_mark": bool(b.get("critical")), "windows": hits})
    rows.sort(key=lambda r: -r["slip_days"])
    crit = [r for r in rows if r["critical_her_mark"]]
    return {"rows": rows, "windows": [w.label for w in wins],
            "critical_slipped": sum(1 for r in crit if r["slip_days"] > 0),
            "max_slip_days": rows[0]["slip_days"] if rows else 0,
            "say": (f"As-planned vs as-built: {len(rows)} activities compared, worst slip "
                    f"{rows[0]['slip_days'] if rows else 0} days, {sum(1 for r in crit if r['slip_days'] > 0)} "
                    "of HER critical activities slipped. Yeh working paper hai - ENTITLEMENT (EOT / LD) "
                    "ka nishkarsh code se NAHI nikalta: forensic planner ka paper, counsel ka conclusion.")}


def notice_check(tenant: str, project: str, event: str, event_date: str, notice_date: str,
                 notice_days: int, contract_ref: str) -> dict:
    """Notice-compliance arithmetic: (notice_date - event_date) <= the contract's window -> in-window
    or late-by-N, the contract row cited. The notice itself is never issued (tier C)."""
    ed, nd = _date(event_date), _date(notice_date)
    if not str(event or "").strip() or not ed or not nd:
        raise CstError("Event, event date aur notice date bataiye (YYYY-MM-DD).")
    if not notice_days or int(notice_days) <= 0:
        raise CstError("Contract ke notice window ke din bataiye (> 0).")
    if not str(contract_ref or "").strip():
        raise CstError("Contract ka reference bataiye (clause / agreement no) - bina cite ke window "
                       "kahan se aaya?")
    taken = (nd - ed).days
    if 0 <= taken <= int(notice_days):
        verdict, where = "in-window", "IN-WINDOW"
    elif taken > int(notice_days):
        verdict, where = "late", f"LATE by {taken - int(notice_days)} din"
    else:
        verdict, where = "pre-dated", "PRE-DATED (notice event se pehle?)"
    with _LOCK, session() as s:
        x = CdelNotice(tenant_id=tenant, project=project.strip()[:160], event=event.strip()[:200],
                       event_date=ed.isoformat(), notice_date=nd.isoformat(), notice_days=int(notice_days),
                       contract_ref=contract_ref.strip()[:160], taken_days=taken, verdict=verdict)
        s.add(x)
        s.flush()
        nid = x.id
    return {"notice_id": nid, "taken_days": taken, "window_days": int(notice_days), "verdict": verdict,
            "say": (f"Notice compliance: {taken} din event ke baad, contract window {int(notice_days)} din "
                    f"({contract_ref.strip()[:50]}) -> {where}. "
                    "Arithmetic hai - notice issue karna aur claim ka nishkarsh advocate/counsel ka.")}


def pack(tenant: str, project: str, prepared_for: str) -> dict:
    """The delay working paper PDF: baseline vs as-built with slips, her criticality marks, windows,
    notice rows - addressed to the forensic planner, sign line EMPTY, entitlement refused in writing."""
    if not str(prepared_for or "").strip():
        raise CstError("prepared_for bataiye (forensic planner ka naam) - working paper kisi ke NAAM ki "
                       "hoti hai.")
    with session() as s:
        wins = s.scalars(select(CdelWindow).where(CdelWindow.tenant_id == tenant,
                                                  CdelWindow.project == project)).all()
        notices = s.scalars(select(CdelNotice).where(CdelNotice.tenant_id == tenant,
                                                     CdelNotice.project == project)).all()
    imp = impact(tenant, project)
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
    t(50, "DELAY ANALYSIS - WORKING PAPER (PREPARE, never CERTIFY)", 13, True)
    t(50, f"Project: {project}    Prepared for: {prepared_for.strip()}")
    t(50, "Criticality = HER baseline marks; no CPM computed. Entitlement is counsel's conclusion.")
    y -= 8
    for r in imp["rows"][:34]:
        t(56, f"slip {r['slip_days']:>4d} d  {r['activity'][:38]:38s} planned {r['planned_finish']} "
              f"actual {r['actual_finish']} {'CRIT' if r['critical_her_mark'] else ''} "
              f"{','.join(r['windows'][:2])}", 9)
    y -= 10
    for n in notices[:10]:
        t(56, f"notice {n.verdict.upper():10s} {n.event[:36]:36s} +{n.taken_days}d / window {n.notice_days}d "
              f"({n.contract_ref[:34]})", 9)
    y -= 16
    t(50, "Reviewed by (forensic planner): ______________________   Entitlement conclusion by "
          "(counsel): ______________________", 9)
    t(50, "(yeh lines Hoola kabhi nahi bhar sakta)", 8.5)
    pdf.showPage()
    pdf.save()
    from .. import chatfiles
    f = chatfiles.store(tenant, f"DELAY-{str(project)[:20].replace('/', '-')}-{today(tenant).isoformat()}.pdf",
                        buf.getvalue(), "application/pdf")
    return {"file": f, "rows": len(imp["rows"]), "windows": len(wins), "notices": len(notices),
            "say": f"Delay working paper: {len(imp['rows'])} activities, {len(wins)} windows, "
                   f"{len(notices)} notice checks - prepared_for {prepared_for.strip()}. Sign lines "
                   "khaali; entitlement ka faisla paper par insaan karega."}
