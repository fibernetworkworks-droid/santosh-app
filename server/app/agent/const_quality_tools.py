"""v0.512.0 const_quality tools (#75 Quality Auditor's Assistant + #76 Material Test Register Keeper +
#78 punch-list glue), extended v0.531.0 Wave 2 C10 with the EHS Officer's Assistant (#81):
permit-to-work DRAFTS (the permit itself is the safety officer's - tier C) and toolbox-talk records.
`const_quality_dekho` only reads; `const_quality` does the work. ITPs with HOLD points (the card law:
Hoola prepares the stop card, the QA manager's tap decides), NCRs, material-test lots (the lab result
goes in AS REPORTED; verdict is a human's word), and the IS 456 cube-acceptance DRAFT (explicitly a
draft - acceptance is the QA engineer's act). Punch list reads sitesup snags."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

QUALITY_TOOLS = [
    {"name": "const_quality", "description": (
        "Quality records desk (ITP, NCR, material tests, cube draft). action=itp: site, activity, steps [{step, spec, "
        "hold}] (hold = inspection ke bina aage nahi), note -> ITP DRAFT. action=itp_approve: itp (id), approved_by "
        "(kaun - naam record hota hai). action=ncr: site, activity, defect, spec (jo clause / spec fail hua), severity "
        "minor|major|critical, action, itp (id) -> NCR khulti hai. action=ncr_close: ncr (id), action, note. action=lot: "
        "kind (cement OPC 53 lot...), lot_no, vendor, test, lab, result (Jaisa lab ne bola WAISA), verdict "
        "pending|pass|fail, tested_on, retest_due, report_ref. action=lot_verdict: lot (id), verdict pass|fail, by. "
        "action=cube_draft: grade (M20+), results [N/mm2] -> IS 456 Table 11 DRAFT (acceptance QA engineer ka sign). "
        "action=punch: site (optional) -> open snag punch list by trade (sitesup snags). "
        "EHS (#81): action=permit_draft: site, kind height|confined space|hot work|excavation|electrical, hazard, "
        "controls [{control, done}], valid_till -> permit DRAFT (issue SAFETY OFFICER karti hai). action=permit_issue: "
        "permit (id), issued_by (safety officer ka naam - bina naam issue nahi). action=permit_close: permit (id), note. "
        "action=toolbox: site, topic, day, attendees, gang - talk ka record."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["itp", "itp_approve", "ncr", "ncr_close", "lot", "lot_verdict",
                                               "cube_draft", "punch", "permit_draft", "permit_issue",
                                               "permit_close", "toolbox"]},
         "site": {"type": "string"}, "activity": {"type": "string"}, "steps": {"type": "array", "items": {"type": "object"}},
         "note": {"type": "string"}, "itp": {"type": "string"}, "approved_by": {"type": "string"}, "defect": {"type": "string"},
         "spec": {"type": "string"}, "severity": {"type": "string"}, "action_taken": {"type": "string"},
         "ncr": {"type": "string"}, "kind": {"type": "string"}, "lot_no": {"type": "string"}, "vendor": {"type": "string"},
         "test": {"type": "string"}, "lab": {"type": "string"}, "result": {"type": "string"}, "verdict": {"type": "string"},
         "tested_on": {"type": "string"}, "retest_due": {"type": "string"}, "report_ref": {"type": "string"},
         "lot": {"type": "string"}, "by": {"type": "string"}, "grade": {"type": "string"},
         "results": {"type": "array", "items": {"type": "number"}},
         "permit": {"type": "string"}, "issued_by": {"type": "string"}, "valid_till": {"type": "string"},
         "controls": {"type": "array", "items": {"type": "object"}}, "topic": {"type": "string"},
         "day": {"type": "string"}, "attendees": {"type": "number"}, "gang": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_quality_dekho", "description": (
        "Read quality records (nothing changes). what=day (open NCRs, pending verdicts, retest due, expiring permits) | "
        "itps | ncrs | lots (verdict filter optional) | punch (site optional) | permits (site optional) | toolbox."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "itps", "ncrs", "lots", "punch", "permits", "toolbox"]},
         "verdict": {"type": "string"}, "site": {"type": "string"}},
         "required": ["what"]}},
]
QUALITY_LABELS = {"const_quality": "Quality ka record likh raha hoon", "const_quality_dekho": "Quality records dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import quality as Q
    from ..construction.common import guard
    guard(f"{action} quality")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "itp":
            return Q.itp(t, _s(a.get("site")), _s(a.get("activity")), a.get("steps"), _s(a.get("status")),
                         _s(a.get("approved_by")), _s(a.get("note")), conv)
        if action == "itp_approve":
            return Q.itp_approve(t, _s(a.get("itp")), _s(a.get("approved_by")))
        if action == "ncr":
            return Q.ncr(t, _s(a.get("site")), _s(a.get("activity")), _s(a.get("defect")), _s(a.get("spec")),
                         _s(a.get("severity")) or "minor", _s(a.get("action_taken")), _s(a.get("itp")), conv)
        if action == "ncr_close":
            return Q.ncr_close(t, _s(a.get("ncr")), _s(a.get("action_taken")), _s(a.get("note")))
        if action == "lot":
            return Q.test_lot(t, _s(a.get("kind")), _s(a.get("lot_no")), _s(a.get("vendor")), _s(a.get("test")),
                              _s(a.get("lab")), _s(a.get("result")), _s(a.get("verdict")) or "pending",
                              _s(a.get("tested_on")), _s(a.get("retest_due")), _s(a.get("report_ref")), _s(a.get("note")))
        if action == "lot_verdict":
            return Q.lot_verdict(t, _s(a.get("lot")), _s(a.get("verdict")), _s(a.get("by")))
        if action == "cube_draft":
            return Q.cube_draft(t, _s(a.get("grade")), a.get("results"))
        if action == "punch":
            return Q.punch(t, _s(a.get("site")))
        if action == "permit_draft":
            return Q.permit_draft(t, _s(a.get("site")), _s(a.get("kind")), _s(a.get("hazard")),
                                  a.get("controls"), _s(a.get("valid_from")), _s(a.get("valid_till")), conv)
        if action == "permit_issue":
            return Q.permit_issue(t, _s(a.get("permit")), _s(a.get("issued_by")))
        if action == "permit_close":
            return Q.permit_close(t, _s(a.get("permit")), _s(a.get("note")))
        if action == "toolbox":
            return Q.toolbox_log(t, _s(a.get("site")), _s(a.get("topic")), _s(a.get("day")),
                                 a.get("attendees"), _s(a.get("gang")), _s(a.get("note")), conv)
    except (Q.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import quality as Q
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CItp, CNcr, CQualPermit, CQualToolbox, CTestLot
    t = ctx.tenant_id
    try:
        if what == "day":
            return Q.day(t)
        if what == "itps":
            with session() as s:
                rows = s.scalars(select(CItp).where(CItp.tenant_id == t)).all()
            return {"itps": [{"id": r.id, "site": r.site, "activity": r.activity, "status": r.status,
                              "approved_by": r.approved_by} for r in rows]}
        if what == "ncrs":
            with session() as s:
                rows = s.scalars(select(CNcr).where(CNcr.tenant_id == t)).all()
            return {"ncrs": [{"id": r.id, "site": r.site, "activity": r.activity, "defect": r.defect[:120],
                              "severity": r.severity, "status": r.status, "raised_on": r.raised_on} for r in rows]}
        if what == "lots":
            with session() as s:
                rows = s.scalars(select(CTestLot).where(CTestLot.tenant_id == t)).all()
            v = _s(a.get("verdict"))
            if v:
                rows = [r for r in rows if r.verdict == v]
            return {"lots": [{"id": r.id, "kind": r.kind, "lot_no": r.lot_no, "test": r.test, "lab": r.lab,
                              "result": r.result[:80], "verdict": r.verdict, "retest_due": r.retest_due} for r in rows]}
        if what == "punch":
            return Q.punch(t, _s(a.get("site")))
        if what == "permits":
            with session() as s:
                rows = s.scalars(select(CQualPermit).where(CQualPermit.tenant_id == t)).all()
            site = _s(a.get("site"))
            if site:
                rows = [r for r in rows if r.site == site]
            return {"permits": [{"id": r.id, "site": r.site, "kind": r.kind, "status": r.status,
                                 "issued_by": r.issued_by, "valid_till": r.valid_till} for r in rows]}
        if what == "toolbox":
            with session() as s:
                rows = s.scalars(select(CQualToolbox).where(CQualToolbox.tenant_id == t)).all()
            site = _s(a.get("site"))
            if site:
                rows = [r for r in rows if r.site == site]
            return {"toolbox": [{"id": r.id, "site": r.site, "topic": r.topic[:80], "day": r.day,
                                 "gang": r.gang, "attendees": r.attendees} for r in rows]}
    except (Q.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def const_quality(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_quality_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


QUALITY_HANDLERS = {"const_quality": const_quality, "const_quality_dekho": const_quality_dekho}
