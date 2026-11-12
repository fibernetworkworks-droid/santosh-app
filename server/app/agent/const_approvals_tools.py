"""v0.531.0 const_approvals tools (C7: #28 tracker + #29 file assembler + #34 statutory calendar +
#36 OC/CC packet). `const_approvals_dekho` only reads; `const_approvals` does the work. The packet
assembles papers and gaps; SUBMISSION stays with the owner's DSC / the named licensee (tier C -
"file a permission application" refuses in gates)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

APPROVALS_TOOLS = [
    {"name": "const_approvals", "description": (
        "Approvals office (building permission, fire NOC, CTE/CTO, OC/CC, utility liaison). action=file: project, "
        "authority, purpose, kind permission|noc|consent|certificate, licensee (who will file) -> file with its checklist. "
        "action=checklist: file (id) or purpose (starter list). action=check_mark: file, item, done, note. "
        "action=doc_add: file, kind form|drawing|ownership|noc|undertaking|fee, name, ref. action=doc_needed: file, kind, "
        "name (still missing). action=packet: file -> index + gaps + cover PDF (submission only on the OWNER's / licensee's approval). "
        "action=file_mark: file, status draft|ready|submitted|queried|approved|rejected, ref_no, on, valid_till. "
        "action=cal_add: authority, item, due_on, last_done (statutory calendar). action=cal_done: cal (id), on. "
        "action=cal_due: days (late ones first, then upcoming). Wave 4 #33: action=screener_add: project, "
        "rows [clearance, applies(yes/no/unsure - YOUR mark), trigger, documents], by (liaison's "
        "name) - heritage/AAI/CRZ applicability register; Hoola fetches / decides nothing. "
        "action=screener_list: project."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["file", "checklist", "check_mark", "doc_add", "doc_needed", "packet",
                                               "file_mark", "cal_add", "cal_done", "cal_due",
                                               "screener_add", "screener_list"]},
         "project": {"type": "string"}, "authority": {"type": "string"}, "purpose": {"type": "string"},
         "kind": {"type": "string"}, "licensee": {"type": "string"}, "fee": {"type": "number"},
         "file": {"type": "string"}, "item": {"type": "string"}, "done": {"type": "boolean"}, "note": {"type": "string"},
         "name": {"type": "string"}, "ref": {"type": "string"}, "ref_no": {"type": "string"},
         "status": {"type": "string"}, "on": {"type": "string"}, "valid_till": {"type": "string"},
         "due_on": {"type": "string"}, "last_done": {"type": "string"}, "cal": {"type": "string"},
         "days": {"type": "number"}},
         "required": ["action"]}},
    {"name": "const_approvals_dekho", "description": (
        "Read approvals office (nothing changes). what=day (open files, missing papers) | files | file (one file ka "
        "checklist + papers, file=id) | calendar (days window optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "files", "file", "calendar"]}, "file": {"type": "string"},
         "days": {"type": "number"}}, "required": ["what"]}},
]
APPROVALS_LABELS = {"const_approvals": "Compiling the approvals file", "const_approvals_dekho": "Checking approvals"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import approvals as A
    from ..construction.common import guard
    guard(f"{action} approvals")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "file":
            return A.file_new(t, _s(a.get("project")), _s(a.get("authority")), _s(a.get("purpose")),
                              _s(a.get("kind")) or "permission", _s(a.get("licensee")), a.get("fee"), conv)
        if action == "checklist":
            return A.checklist(t, _s(a.get("file")), _s(a.get("purpose")))
        if action == "check_mark":
            return A.check_mark(t, _s(a.get("file")), _s(a.get("item")), bool(a.get("done", True)), _s(a.get("note")))
        if action == "doc_add":
            return A.doc_add(t, _s(a.get("file")), _s(a.get("kind")), _s(a.get("name")), _s(a.get("ref")),
                             _s(a.get("note")))
        if action == "doc_needed":
            return A.doc_needed(t, _s(a.get("file")), _s(a.get("kind")), _s(a.get("name")), _s(a.get("note")))
        if action == "packet":
            return A.packet(t, _s(a.get("file")))
        if action == "file_mark":
            return A.file_mark(t, _s(a.get("file")), _s(a.get("status")), _s(a.get("ref_no")), _s(a.get("on")),
                               _s(a.get("valid_till")))
        if action == "cal_add":
            return A.cal_add(t, _s(a.get("authority")), _s(a.get("item")), _s(a.get("due_on")), _s(a.get("last_done")),
                             _s(a.get("file")), conv)
        if action == "cal_done":
            return A.cal_done(t, _s(a.get("cal")), _s(a.get("on")))
        if action == "cal_due":
            return A.cal_due(t, int(a.get("days") or 30))

        if action == "screener_add":
            return A.screener_add(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("by")),
                                  _s(a.get("note")), conv)
        if action == "screener_list":
            return A.screener_list(t, _s(a.get("project")))
    except (A.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import approvals as A
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CApprovDoc, CApprovFile
    t = ctx.tenant_id
    guard(f"read approvals {what}")
    try:
        if what == "day":
            return A.day(t)
        if what == "files":
            with session() as s:
                rows = s.scalars(select(CApprovFile).where(CApprovFile.tenant_id == t)).all()
            return {"files": [{"id": r.id, "project": r.project, "authority": r.authority, "purpose": r.purpose,
                               "status": r.status, "licensee": r.licensee, "ref_no": r.ref_no,
                               "valid_till": r.valid_till} for r in rows]}
        if what == "file":
            return A.checklist(t, _s(a.get("file")))
        if what == "calendar":
            return A.cal_due(t, int(a.get("days") or 30))
    except (A.CstError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("unknown what")


async def const_approvals(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_approvals_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


APPROVALS_HANDLERS = {"const_approvals": const_approvals, "const_approvals_dekho": const_approvals_dekho}
