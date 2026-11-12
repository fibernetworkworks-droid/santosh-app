"""v0.550.0 const_bim tools (C11, Wave 3: #18 BIM/Information Manager, #19 CDE & Document Controller,
#20 Clash Detection Coordinator, #21 4D/5D Planner). OPEN FORMATS ONLY: IFC (STEP text) is READ and
the read says what it saw; BCF 2.1 is WRITTEN; IDS is checked on an honest SUBSET (entity + property
presence facets; the rest comes back UNVERIFIED). A PDF was never a model. Clash runs on the elements'
own declared extents at their placement points, axis-aligned, and lists what it could NOT check.
Quantities are THE MODEL'S; the only arithmetic is qty x rate with a sourced rate. Candidates are
candidates - the BIM coordinator accepts."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

BIM_TOOLS = [
    {"name": "const_bim", "description": (
        "BIM / information desk - open formats only (IFC read, BCF write, IDS subset). action=ifc_add: project, "
        "name, ifc_text (STEP text; FILE_SCHEMA is required), file_ref -> honest parse + health gaps. "
        "action=health: model -> what it has, what it lacks (duplicate GUIDs, nameless, no quantities). "
        "action=naming: filenames [list], pattern (default Project-Originator-Volume-Level-Type-Role-Number) -> "
        "ISO 19650 violations. action=cde_add: project, code, title, rev, status wip|shared|published|archived -> "
        "CDE register (same code+new rev superscedes the old). action=cde_status: cde (id), status, note. "
        "action=transmit: project, codes [list], to_whom, note -> transmittal RECORD (sending only on your tap). "
        "action=clash_scan: model, clearance_m -> overlap candidates on declared extents (axis-aligned; "
        "rotation ignored; not-checkable counted). action=clash_mark: clash (id), status assigned|resolved|"
        "accepted, by (BIM coordinator's NAME), note. action=bcf: model -> BCF 2.1 zip of open candidates. "
        "action=link4d: model, activity, match_kind class|storey|name, match_value, start, finish -> 4D mapping "
        "(the schedule is YOURS). action=report4d: model -> per-activity element/volume report. action=qty5d: model "
        "(match_kind/match_value optional) -> model's own Volume/Area rows with GUID trail. action=cost5d: "
        "takeoff (id), rate, rate_source (SOR/quote) -> qty x rate, the ONLY arithmetic. action=ids: model, "
        "ids_text (IDS XML) -> entity+property facets checked, rest UNVERIFIED. Wave 3.5: "
        "action=asbuilt_set: project, name, required [codes ya 'CODE | Title'] -> as-built set (#25, "
        "completeness against YOUR list). action=asbuilt_mark: set (id), code, status received|pending|na, "
        "by (NAME), note. action=asbuilt_check: set (id) -> received/na/pending + missing + % (approval "
        "site architect/QS ka, tier C). action=twin_asset: project, asset_id, guid (IFC GlobalId), name, "
        "kind, space, model -> data-link row (#109, twin = a register, not a 3D view). action=twin_read: "
        "project, rows [asset_id, sensor, value], unit, band_min, band_max, band_source (a band needs "
        "its source) -> out-of-band flagged. action=cobie_check: project, csv_text (Component sheet "
        "CSV) -> required headers + rows without AssetIdentifier/TypeName."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["ifc_add", "health", "naming", "cde_add", "cde_status",
                                               "transmit", "clash_scan", "clash_mark", "bcf", "link4d",
                                               "report4d", "qty5d", "cost5d", "ids", "asbuilt_set",
                                               "asbuilt_mark", "asbuilt_check", "twin_asset", "twin_read",
                                               "cobie_check"]},
         "project": {"type": "string"}, "name": {"type": "string"}, "ifc_text": {"type": "string"},
         "file_ref": {"type": "string"}, "model": {"type": "string"},
         "filenames": {"type": "array", "items": {"type": "string"}}, "pattern": {"type": "string"},
         "code": {"type": "string"}, "title": {"type": "string"}, "rev": {"type": "string"},
         "status": {"type": "string"}, "cde": {"type": "string"}, "note": {"type": "string"},
         "codes": {"type": "array", "items": {"type": "string"}}, "to_whom": {"type": "string"},
         "clearance_m": {"type": "number"}, "clash": {"type": "string"}, "by": {"type": "string"},
         "activity": {"type": "string"}, "match_kind": {"type": "string"}, "match_value": {"type": "string"},
         "start": {"type": "string"}, "finish": {"type": "string"}, "takeoff": {"type": "string"},
         "rate": {"type": "number"}, "rate_source": {"type": "string"}, "ids_text": {"type": "string"},
         "set": {"type": "string"}, "required": {"type": "array", "items": {"type": "string"}},
         "asset_id": {"type": "string"}, "guid": {"type": "string"},
         "kind": {"type": "string"}, "space": {"type": "string"}, "rows": {"type": "array", "items": {}},
         "unit": {"type": "string"}, "band_min": {"type": "number"}, "band_max": {"type": "number"},
         "band_source": {"type": "string"}, "csv_text": {"type": "string"}, "model_id": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_bim_dekho", "description": (
        "Read the BIM desk (nothing changes). what=models | elements (model) | cde (project optional) | "
        "transmittals | clashes (model, status optional) | takeoff (model) | links (model) | health (model) | "
        "asbuilt (set) | twins (project optional) | readings (asset optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["models", "elements", "cde", "transmittals", "clashes",
                                             "takeoff", "links", "health", "asbuilt", "twins", "readings"]},
         "model": {"type": "string"}, "project": {"type": "string"}, "status": {"type": "string"},
         "set": {"type": "string"}, "asset": {"type": "string"}},
         "required": ["what"]}},
]
BIM_LABELS = {"const_bim": "Working on the BIM desk", "const_bim_dekho": "Viewing the BIM desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import bim as B
    from ..construction.common import guard
    guard(f"{action} bim")     # tier-C refusal rides every construction action
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "ifc_add":
            return B.ifc_add(t, _s(a.get("project")), _s(a.get("name")), _s(a.get("ifc_text")),
                             _s(a.get("file_ref")), conv)
        if action == "health":
            return B.health(t, _s(a.get("model")))
        if action == "naming":
            return B.naming_check(a.get("filenames") or [], _s(a.get("pattern"))
                                  or "Project-Originator-Volume-Level-Type-Role-Number")
        if action == "cde_add":
            return B.cde_add(t, _s(a.get("project")), _s(a.get("code")), _s(a.get("title")),
                             _s(a.get("rev")), _s(a.get("status")) or "wip", _s(a.get("file_ref")),
                             _s(a.get("note")))
        if action == "cde_status":
            return B.cde_status(t, _s(a.get("cde")), _s(a.get("status")), _s(a.get("note")))
        if action == "transmit":
            return B.transmit(t, _s(a.get("project")), a.get("codes") or [], _s(a.get("to_whom")),
                              _s(a.get("note")), conv)
        if action == "clash_scan":
            return B.clash_scan(t, _s(a.get("model")), a.get("clearance_m") if a.get("clearance_m") is not None
                                else 0.02, conv)
        if action == "clash_mark":
            return B.clash_mark(t, _s(a.get("clash")), _s(a.get("status")), _s(a.get("by")), _s(a.get("note")))
        if action == "bcf":
            return B.bcf_export(t, _s(a.get("model")), conv)
        if action == "link4d":
            return B.link4d(t, _s(a.get("model")), _s(a.get("activity")), _s(a.get("match_kind")) or "class",
                            _s(a.get("match_value")), _s(a.get("start")), _s(a.get("finish")), _s(a.get("note")))
        if action == "report4d":
            return B.report4d(t, _s(a.get("model")))
        if action == "qty5d":
            return B.qty5d(t, _s(a.get("model")), _s(a.get("match_kind")), _s(a.get("match_value")))
        if action == "cost5d":
            return B.cost5d(t, _s(a.get("takeoff")), a.get("rate"), _s(a.get("rate_source")))
        if action == "ids":
            return B.ids_check(t, _s(a.get("model")), _s(a.get("ids_text")))
        if action == "asbuilt_set":
            return B.asbuilt_set(t, _s(a.get("project")), _s(a.get("name")), a.get("required") or [],
                                 _s(a.get("note")), conv)
        if action == "asbuilt_mark":
            return B.asbuilt_mark(t, _s(a.get("set")), _s(a.get("code")), _s(a.get("status")),
                                  _s(a.get("by")), _s(a.get("note")))
        if action == "asbuilt_check":
            return B.asbuilt_check(t, _s(a.get("set")))
        if action == "twin_asset":
            return B.twin_asset(t, _s(a.get("project")), _s(a.get("asset_id")), _s(a.get("guid")),
                                _s(a.get("name")), _s(a.get("kind")), _s(a.get("space")),
                                _s(a.get("model_id")), _s(a.get("note")), conv)
        if action == "twin_read":
            return B.twin_read(t, _s(a.get("project")), a.get("rows") or [], _s(a.get("unit")),
                               a.get("band_min") or 0.0, a.get("band_max") or 0.0,
                               _s(a.get("band_source")), _s(a.get("note")), conv)
        if action == "cobie_check":
            return B.cobie_check(t, _s(a.get("project")), _s(a.get("csv_text")))
    except (B.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import bim as B
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import (CBimAsbuilt, CBimAsbuiltDoc, CBimCde, CBimClash, CBimElement,
                                       CBimLink4d, CBimModel, CBimTakeoff, CBimTransmit, CTwinAsset,
                                       CTwinReading)
    guard(f"read bim {what}")
    t = ctx.tenant_id
    try:
        if what == "models":
            with session() as s:
                rows = s.scalars(select(CBimModel).where(CBimModel.tenant_id == t)).all()
            return {"models": [{"id": r.id, "project": r.project, "name": r.name, "schema": r.schema_,
                                "entities": r.entities, "elements": r.elements} for r in rows]}
        if what == "elements":
            with session() as s:
                rows = s.scalars(select(CBimElement).where(CBimElement.tenant_id == t,
                                                           CBimElement.model_id == _s(a.get("model")))).all()
            return {"elements": [{"guid": r.guid, "class": r.ifc_class, "name": r.name, "storey": r.storey,
                                  "qty": B._j(r.qty, {})} for r in rows[:400]]}
        if what == "cde":
            with session() as s:
                rows = s.scalars(select(CBimCde).where(CBimCde.tenant_id == t)).all()
            p = _s(a.get("project"))
            if p:
                rows = [r for r in rows if r.project == p]
            return {"cde": [{"id": r.id, "project": r.project, "code": r.code, "title": r.title, "rev": r.rev,
                             "status": r.status, "superseded_by": r.superseded_by} for r in rows]}
        if what == "transmittals":
            with session() as s:
                rows = s.scalars(select(CBimTransmit).where(CBimTransmit.tenant_id == t)).all()
            return {"transmittals": [{"id": r.id, "project": r.project, "to_whom": r.to_whom,
                                      "codes": B._j(r.codes, []), "day": r.day} for r in rows]}
        if what == "clashes":
            q = select(CBimClash).where(CBimClash.tenant_id == t)
            if _s(a.get("model")):
                q = q.where(CBimClash.model_id == _s(a.get("model")))
            if _s(a.get("status")):
                q = q.where(CBimClash.status == _s(a.get("status")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"clashes": [{"id": r.id, "model": r.model_id, "a": r.a_guid[:12], "b": r.b_guid[:12],
                                 "pair": r.group_key, "status": r.status, "by": r.by} for r in rows]}
        if what == "takeoff":
            with session() as s:
                rows = s.scalars(select(CBimTakeoff).where(CBimTakeoff.tenant_id == t,
                                                           CBimTakeoff.model_id == _s(a.get("model")))).all()
            return {"takeoff": [{"id": r.id, "guid": r.guid[:12], "class": r.ifc_class, "name": r.name,
                                 "qty": r.qty, "unit": r.unit, "rate": r.rate, "amount": r.amount,
                                 "rate_source": r.rate_source} for r in rows]}
        if what == "links":
            with session() as s:
                rows = s.scalars(select(CBimLink4d).where(CBimLink4d.tenant_id == t,
                                                          CBimLink4d.model_id == _s(a.get("model")))).all()
            return {"links": [{"id": r.id, "activity": r.activity, "match": f"{r.match_kind}={r.match_value}",
                               "start": r.start, "finish": r.finish} for r in rows]}
        if what == "health":
            return B.health(t, _s(a.get("model")))
        if what == "asbuilt":
            with session() as s:
                st = s.get(CBimAsbuilt, _s(a.get("set")))
                if not st or st.tenant_id != t:
                    raise B.CstError("As-built set not found.")
                docs = s.scalars(select(CBimAsbuiltDoc).where(CBimAsbuiltDoc.tenant_id == t,
                                                              CBimAsbuiltDoc.set_id == st.id)).all()
            return {"set": {"id": st.id, "project": st.project, "name": st.name},
                    "docs": [{"code": r.code, "title": r.title, "status": r.status, "by": r.by}
                             for r in docs]}
        if what == "twins":
            q = select(CTwinAsset).where(CTwinAsset.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CTwinAsset.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"twins": [{"id": r.id, "project": r.project, "asset_id": r.asset_id, "guid": r.guid,
                               "name": r.name, "kind": r.kind, "space": r.space} for r in rows]}
        if what == "readings":
            q = select(CTwinReading).where(CTwinReading.tenant_id == t)
            if _s(a.get("asset")):
                q = q.where(CTwinReading.asset_id == _s(a.get("asset")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"readings": [{"id": r.id, "asset_id": r.asset_id, "sensor": r.sensor, "value": r.value,
                                  "unit": r.unit, "out_band": r.out_band} for r in rows]}
    except (B.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown what")


async def const_bim(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_bim_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


BIM_HANDLERS = {"const_bim": const_bim, "const_bim_dekho": const_bim_dekho}
