"""#75 Quality Auditor's Assistant + #76 Material Test Register Keeper + #78 Snagging punch-list glue
(v0.512.0, Wave 1). ITPs with hold points, NCRs, material-test lots, and the IS 456 cube-acceptance
DRAFT (M20 and above: mean of the group >= fck + 4 N/mm2 and every individual cube >= fck - 4 N/mm² -
IS 456:2000 cl 16.1 / Table 11). The DRAFT is explicitly a draft: acceptance is the QA engineer's act
(tier B edge inside a tier-A desk, said on every output). Punch list reads sitesup snags - never
duplicated here."""
from __future__ import annotations

import re

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import CItp, CNcr, CTestLot

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
    """The QA morning: open NCRs, hold points due, lots pending verdict / retest."""
    t0 = today(tenant)
    with session() as s:
        ncrs = s.scalars(select(CNcr).where(CNcr.tenant_id == tenant, CNcr.status == "open")).all()
        lots = s.scalars(select(CTestLot).where(CTestLot.tenant_id == tenant, CTestLot.verdict == "pending")).all()
        retest = [r for r in s.scalars(select(CTestLot).where(CTestLot.tenant_id == tenant)).all()
                  if r.retest_due and r.retest_due <= t0.isoformat()]
    say = (f"Quality: {len(ncrs)} NCR khuli, {len(lots)} lab results verdict-pending"
           + (f", {len(retest)} retest due" if retest else "") + ".")
    return {"open_ncrs": len(ncrs), "pending_lots": len(lots), "retest_due": len(retest), "say": say}
