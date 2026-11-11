"""v0.550.0 const_survey tools (C13a, Wave 3: #22 Land Survey Data Processor, #23 Drone Survey &
Photogrammetry Processor, #24 Point-cloud Reality Capture Assistant, #26 RERA Carpet-area Measurement
Assistant). Honest about formats: LandXML read for CgPoints only, E57/LAS NOT parsed (CSV in), the
orthomosaic read by the survey lead. Arithmetic for the survey lead / architect - certification
stays with the licensed surveyor / project architect / CE (tier C: gates.py rides every action)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

SURVEY_TOOLS = [
    {"name": "const_survey", "description": (
        "Survey & measurement desk - traverse/area/volume/deviation arithmetic + RERA carpet statement. "
        "action=pts_add: project, name, source_kind coords|landxml, text ('id,x,y,z' lines or LandXML "
        "CgPoints) -> survey job (surfaces/observations are NOT parsed - said on the tin). action=traverse: "
        "project, job (id), order [point ids] -> loop closure + precision. action=area: project, job, order, "
        "record_m2 (optional), record_source (7/12 etc), tolerance_pct -> shoelace area + boundary-vs-record. "
        "action=volume: project, name, elevations [z...], design_level, cell_area_m2 -> cut/fill separately "
        "(readings are the survey lead's). action=deviations: project, name, rows [x,y,z_asbuilt,x,y,z_design], "
        "tolerance_mm -> RMS + out-of-tolerance (E57/LAS is not parsed - CSV in). action=carpet_new: project, "
        "unit_no, wall_policy (YOUR word, recorded), declared_m2, declared_source -> a statement is opened. "
        "action=carpet_room: carpet (id), room, length_m, breadth_m. action=carpet_calc: carpet (id), "
        "tolerance_pct (optional; default state pack row) -> computed vs declared, within/exceeds. "
        "action=carpet_pack: carpet (id) -> discrepancy report PDF, sign line empty (for the architect/CE). "
        "Wave 3.5: action=gis_add: project, name, geojson (GeoJSON text, Polygon/MultiPolygon), crs, units "
        "m|deg (default deg - RFC 7946; area only on a projected metre CRS) -> layer (#27, maps are NOT fetched/interpreted). action=gis_area: layer (id), record_m2, record_source, tolerance_pct -> shoelace outer "
        "rings (deg layers REFUSE). action=gis_overlay: project, layer (id), hazard flood|seismic|zoning|other, "
        "zone_value (read off the map by YOU), source -> reading record. action=setout_add: project, name, "
        "design_rows [id, x, y(, z)] -> setting-out sheet (#77). action=setout_check: project, job (id), "
        "aslaid_rows [id, x, y(, z)], tolerance_mm -> plan deviation, RMS, out-of-tolerance. action=level_check: "
        "project, job (id), obs_rows [id, z_obs], tolerance_mm -> dz with its sign (design z on the sheet points)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["pts_add", "traverse", "area", "volume", "deviations",
                                               "carpet_new", "carpet_room", "carpet_calc", "carpet_pack",
                                               "gis_add", "gis_area", "gis_overlay", "setout_add",
                                               "setout_check", "level_check"]},
         "project": {"type": "string"}, "name": {"type": "string"}, "source_kind": {"type": "string"},
         "text": {"type": "string"}, "job": {"type": "string"}, "order": {"type": "array", "items": {"type": "string"}},
         "record_m2": {"type": "number"}, "record_source": {"type": "string"}, "tolerance_pct": {"type": "number"},
         "elevations": {"type": "array", "items": {"type": "number"}}, "design_level": {"type": "number"},
         "cell_area_m2": {"type": "number"}, "rows": {"type": "array", "items": {}},
         "tolerance_mm": {"type": "number"}, "unit_no": {"type": "string"}, "wall_policy": {"type": "string"},
         "declared_m2": {"type": "number"}, "declared_source": {"type": "string"},
         "carpet": {"type": "string"}, "room": {"type": "string"}, "length_m": {"type": "number"},
         "breadth_m": {"type": "number"}, "note": {"type": "string"},
         "geojson": {"type": "string"}, "crs": {"type": "string"}, "units": {"type": "string"},
         "layer": {"type": "string"}, "hazard": {"type": "string"}, "zone_value": {"type": "string"},
         "design_rows": {"type": "array", "items": {}}, "aslaid_rows": {"type": "array", "items": {}},
         "obs_rows": {"type": "array", "items": {}}, "source": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_survey_dekho", "description": (
        "Read the survey desk (nothing changes). what=jobs | points (job) | calcs (kind optional) | carpets "
        "(project optional) | carpet (id - rooms + result) | layers (project optional) | overlays (project "
        "optional)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["jobs", "points", "calcs", "carpets", "carpet", "layers",
                                             "overlays"]},
         "job": {"type": "string"}, "kind": {"type": "string"}, "project": {"type": "string"},
         "carpet": {"type": "string"}},
         "required": ["what"]}},
]
SURVEY_LABELS = {"const_survey": "Survey desk par kaam kar raha hoon",
                 "const_survey_dekho": "Survey desk dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import survey as S
    from ..construction.common import guard
    guard(f"{action} survey")
    t, conv = ctx.tenant_id, ctx.conversation_id
    try:
        if action == "pts_add":
            return S.pts_add(t, _s(a.get("project")), _s(a.get("name")), _s(a.get("source_kind")) or "coords",
                             _s(a.get("text")), _s(a.get("note")), conv)
        if action == "traverse":
            return S.traverse(t, _s(a.get("project")), _s(a.get("job")), a.get("order") or [],
                              _s(a.get("note")))
        if action == "area":
            return S.area_shoelace(t, _s(a.get("project")), _s(a.get("job")), a.get("order") or [],
                                   a.get("record_m2") or 0.0, _s(a.get("record_source")),
                                   a.get("tolerance_pct") if a.get("tolerance_pct") is not None else 2.0,
                                   _s(a.get("note")))
        if action == "volume":
            return S.volume_grid(t, _s(a.get("project")), _s(a.get("name")), a.get("elevations") or [],
                                 a.get("design_level"), a.get("cell_area_m2"), _s(a.get("note")))
        if action == "deviations":
            return S.deviations(t, _s(a.get("project")), _s(a.get("name")), a.get("rows") or [],
                                a.get("tolerance_mm") if a.get("tolerance_mm") is not None else 25.0,
                                _s(a.get("note")))
        if action == "carpet_new":
            return S.carpet_new(t, _s(a.get("project")), _s(a.get("unit_no")), _s(a.get("wall_policy")),
                                a.get("declared_m2") or 0.0, _s(a.get("declared_source")), _s(a.get("note")))
        if action == "carpet_room":
            return S.carpet_room(t, _s(a.get("carpet")), _s(a.get("room")), a.get("length_m"), a.get("breadth_m"))
        if action == "carpet_calc":
            return S.carpet_calc(t, _s(a.get("carpet")), a.get("tolerance_pct") or 0.0)
        if action == "carpet_pack":
            return S.carpet_pack(t, _s(a.get("carpet")))
        if action == "gis_add":
            return S.gis_add(t, _s(a.get("project")), _s(a.get("name")), _s(a.get("geojson")),
                             _s(a.get("crs")), _s(a.get("units")), _s(a.get("note")), conv)
        if action == "gis_area":
            return S.gis_area(t, _s(a.get("layer")), a.get("record_m2") or 0.0, _s(a.get("record_source")),
                              a.get("tolerance_pct") if a.get("tolerance_pct") is not None else 2.0)
        if action == "gis_overlay":
            return S.gis_overlay(t, _s(a.get("project")), _s(a.get("layer")), _s(a.get("hazard")),
                                 _s(a.get("zone_value")), _s(a.get("source")), _s(a.get("note")))
        if action == "setout_add":
            return S.setout_add(t, _s(a.get("project")), _s(a.get("name")), a.get("design_rows") or [],
                                _s(a.get("note")), conv)
        if action == "setout_check":
            return S.setout_check(t, _s(a.get("project")), _s(a.get("job")), a.get("aslaid_rows") or [],
                                  a.get("tolerance_mm") if a.get("tolerance_mm") is not None else 25.0,
                                  _s(a.get("note")))
        if action == "level_check":
            return S.level_check(t, _s(a.get("project")), _s(a.get("job")), a.get("obs_rows") or [],
                                 a.get("tolerance_mm") if a.get("tolerance_mm") is not None else 25.0,
                                 _s(a.get("note")))
    except (S.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("Unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import survey as S
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CGisLayer, CGisOverlay, CsurCalc, CsurCarpet, CsurCarpetRoom, CsurJob, CsurPoint
    guard(f"read survey {what}")
    t = ctx.tenant_id
    try:
        if what == "jobs":
            with session() as s:
                rows = s.scalars(select(CsurJob).where(CsurJob.tenant_id == t)).all()
            return {"jobs": [{"id": r.id, "project": r.project, "name": r.name, "source": r.source_kind,
                              "points": r.points} for r in rows]}
        if what == "points":
            with session() as s:
                rows = s.scalars(select(CsurPoint).where(CsurPoint.tenant_id == t,
                                                         CsurPoint.job_id == _s(a.get("job")))).all()
            return {"points": [{"pid": r.pid, "x": r.x, "y": r.y, "z": r.z} for r in rows]}
        if what == "calcs":
            q = select(CsurCalc).where(CsurCalc.tenant_id == t)
            if _s(a.get("kind")):
                q = q.where(CsurCalc.kind == _s(a.get("kind")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"calcs": [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                               "result": S._j(r.result, {})} for r in rows]}
        if what == "carpets":
            q = select(CsurCarpet).where(CsurCarpet.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CsurCarpet.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"carpets": [{"id": r.id, "project": r.project, "unit_no": r.unit_no,
                                 "policy": r.wall_policy[:60], "declared": r.declared_m2,
                                 "computed": r.computed_m2, "diff_pct": r.diff_pct, "verdict": r.verdict}
                                for r in rows]}
        if what == "layers":
            q = select(CGisLayer).where(CGisLayer.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CGisLayer.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"layers": [{"id": r.id, "project": r.project, "name": r.name, "crs": r.crs,
                                "units": r.units, "vertices": r.vertices, "holes": r.holes} for r in rows]}
        if what == "overlays":
            q = select(CGisOverlay).where(CGisOverlay.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CGisOverlay.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"overlays": [{"id": r.id, "project": r.project, "hazard": r.hazard,
                                  "zone_value": r.zone_value, "source": r.source[:60]} for r in rows]}
        if what == "carpet":
            with session() as s:
                c = s.get(CsurCarpet, _s(a.get("carpet")))
                if not c or c.tenant_id != t:
                    raise S.CstError("Carpet statement not found.")
                rooms = s.scalars(select(CsurCarpetRoom).where(CsurCarpetRoom.tenant_id == t,
                                                               CsurCarpetRoom.carpet_id == c.id)).all()
            return {"carpet": {"id": c.id, "unit_no": c.unit_no, "policy": c.wall_policy,
                               "declared_m2": c.declared_m2, "declared_source": c.declared_source,
                               "computed_m2": c.computed_m2, "diff_pct": c.diff_pct, "verdict": c.verdict},
                    "rooms": [{"room": r.room, "length": r.length_m, "breadth": r.breadth_m,
                               "area": round(r.length_m * r.breadth_m, 3)} for r in rooms]}
    except (S.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("Unknown what")


async def const_survey(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_survey_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


SURVEY_HANDLERS = {"const_survey": const_survey, "const_survey_dekho": const_survey_dekho}
