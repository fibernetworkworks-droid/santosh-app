"""v0.531.0 const_rera tools (C9: #35 compliance manager + #93 escrow reconciler). The % is the
PROMOTER's number (never computed), a withdrawal needs the certificate reference, the form packs
name their professional with the sign line empty, the 70% reserve reads the state pack (stale
refuses). Tier C refusals ride gates.py."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

RERA_TOOLS = [
    {"name": "const_rera", "description": (
        "RERA & escrow desk (MahaRERA first). action=project: name, maha_rera (reg no), promoter, start_on, "
        "complete_on, escrow_acct -> project data pack. action=update_draft: rera_project, quarter (2026-Q4), "
        "pct_complete (as YOU tell it - I do not compute the %), units_booked, units_delivered, complaints. "
        "action=form_pack: rera_project, form_no (Form 3/4/5...), purpose, period, data [{item, value, source}], "
        "prepared_for (NAME of the CA/architect/engineer) -> the sign line stays empty. action=escrow_in: rera_project, "
        "amount, day, ref. action=escrow_withdraw: rera_project, amount, certificate_ref (REQUIRED - the engineer's/architect's/"
        "CA's certificate), day. action=reconcile: rera_project -> receipts vs 70% reserve (from the state pack, cited) + "
        "CA audit due. Filing only on the promoter's / professional's approval - never by Hoola."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["project", "update_draft", "form_pack", "escrow_in", "escrow_withdraw",
                                               "reconcile"]},
         "name": {"type": "string"}, "maha_rera": {"type": "string"}, "promoter": {"type": "string"},
         "start_on": {"type": "string"}, "complete_on": {"type": "string"}, "sanctioned_on": {"type": "string"},
         "escrow_acct": {"type": "string"}, "rera_project": {"type": "string"}, "quarter": {"type": "string"},
         "pct_complete": {"type": "number"}, "units_booked": {"type": "number"}, "units_delivered": {"type": "number"},
         "complaints": {"type": "number"}, "form_no": {"type": "string"}, "purpose": {"type": "string"},
         "period": {"type": "string"}, "data": {"type": "array", "items": {"type": "object"}},
         "prepared_for": {"type": "string"}, "amount": {"type": "number"}, "day": {"type": "string"},
         "ref": {"type": "string"}, "certificate_ref": {"type": "string"}, "note": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_rera_dekho", "description": (
        "Read RERA desk (nothing changes). what=day | projects | updates (rera_project optional) | forms | "
        "escrow (rera_project) | reconcile (rera_project)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "projects", "updates", "forms", "escrow", "reconcile"]},
         "rera_project": {"type": "string"}}, "required": ["what"]}},
]
RERA_LABELS = {"const_rera": "Compiling the RERA record", "const_rera_dekho": "Viewing the RERA desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import rera as R
    from ..construction.common import guard
    guard(f"{action} rera")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "project":
            return R.project_reg(t, _s(a.get("name")), _s(a.get("maha_rera")), _s(a.get("promoter")),
                                 _s(a.get("start_on")), _s(a.get("complete_on")), _s(a.get("sanctioned_on")),
                                 _s(a.get("escrow_acct")), conv)
        if action == "update_draft":
            return R.update_draft(t, _s(a.get("rera_project")), _s(a.get("quarter")), a.get("pct_complete"),
                                  a.get("units_booked"), a.get("units_delivered"), a.get("complaints"),
                                  _s(a.get("note")), conv)
        if action == "form_pack":
            return R.form_pack(t, _s(a.get("rera_project")), _s(a.get("form_no")), _s(a.get("purpose")),
                               _s(a.get("period")), a.get("data"), _s(a.get("prepared_for")), _s(a.get("note")))
        if action == "escrow_in":
            return R.escrow_in(t, _s(a.get("rera_project")), a.get("amount"), _s(a.get("day")), _s(a.get("ref")),
                               _s(a.get("note")))
        if action == "escrow_withdraw":
            return R.escrow_withdraw(t, _s(a.get("rera_project")), a.get("amount"), _s(a.get("day")),
                                     _s(a.get("certificate_ref")), _s(a.get("ref")), _s(a.get("note")))
        if action == "reconcile":
            return R.reconcile(t, _s(a.get("rera_project")))
    except (R.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import rera as R
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CreraEscrow, CreraForm, CreraProject, CreraUpdate
    t = ctx.tenant_id
    guard(f"read rera {what}")
    try:
        if what == "day":
            return R.day(t)
        if what == "projects":
            with session() as s:
                rows = s.scalars(select(CreraProject).where(CreraProject.tenant_id == t)).all()
            return {"projects": [{"id": r.id, "name": r.name, "maha_rera": r.maha_rera, "promoter": r.promoter,
                                  "complete_on": r.complete_on, "escrow_acct": r.escrow_acct} for r in rows]}
        if what == "updates":
            with session() as s:
                rows = s.scalars(select(CreraUpdate).where(CreraUpdate.tenant_id == t)).all()
            p = _s(a.get("rera_project"))
            if p:
                rows = [r for r in rows if r.project_id == p]
            return {"updates": [{"id": r.id, "quarter": r.quarter, "pct_complete": r.pct_complete,
                                 "units_booked": r.units_booked, "status": r.status} for r in rows]}
        if what == "forms":
            with session() as s:
                rows = s.scalars(select(CreraForm).where(CreraForm.tenant_id == t)).all()
            return {"forms": [{"id": r.id, "form_no": r.form_no, "purpose": r.purpose[:80],
                               "prepared_for": r.prepared_for, "status": r.status} for r in rows]}
        if what == "escrow":
            with session() as s:
                rows = s.scalars(select(CreraEscrow).where(CreraEscrow.tenant_id == t,
                                                           CreraEscrow.project_id == _s(a.get("rera_project")))).all()
            return {"escrow": [{"id": r.id, "kind": r.kind, "amount": r.amount, "day": r.day,
                                "certificate_ref": r.certificate_ref} for r in rows]}
        if what == "reconcile":
            return R.reconcile(t, _s(a.get("rera_project")))
    except (R.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown what")


async def const_rera(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_rera_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


RERA_HANDLERS = {"const_rera": const_rera, "const_rera_dekho": const_rera_dekho}
