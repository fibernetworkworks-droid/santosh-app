"""v0.550.0 const_predesign tools (C12, Wave 3: #10 Structural Pre-design Assistant, #11 MEP Design
Assistant, #12 Fire-safety Design Checker). Working papers for the NAMED professional - PRELIMINARY on
every structural row (the stability certificate is the registered engineer's, tier C); MEP factors are
FED with their source; fire rules need clause + source (a rule without its clause refuses) and the
verdict is arithmetic - Form A/B stays with the Licensed Agency."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

PREDESIGN_TOOLS = [
    {"name": "const_predesign", "description": (
        "Pre-design desk - load take-down, preliminary sizing, MEP estimates, fire rule checks (all "
        "PRELIMINARY working papers; design/stability sign-off is the registered engineer's, tier C). action=rule_add: "
        "family ll|unit|span|fire|mep|other, rule_id, text, value, unit, direction min|max, clause, source - "
        "a rule without a clause is not kept. action=slab_load: project, name, occupancy residential|office|stair, "
        "thickness_m, finish_kn_m2 -> DL+LL trail (IS 875 pack rows). action=column_load: project, name, "
        "tributary_m2, floors, load_kn_m2, beam_add_kn, wall_add_kn -> Pu kN. action=column_size: project, "
        "name, pu_kn, fck, fy, steel_pct -> IS 456 cl 39.3 working paper (50 mm module, rounding shown). "
        "action=beam_depth: project, name, span_m, support cantilever|simply_supported|continuous, depth_mm "
        "-> span/ratio check (span > 10 m is refused - modification factors are the engineer's). action=mep_elec: "
        "project, name, connected_kw, demand_factor, diversity, pf, note (write the source) -> kVA. "
        "action=mep_water: project, name, occupants -> KLD (CPHEEO pack row). action=mep_hvac: project, name, "
        "area_m2, tr_per_m2, source -> TR. action=fire_check: project, rule_id, declared -> within/breach "
        "(clause cited; the fire consultant decides). action=fire_demand: project, name, density_lpm_m2, "
        "density_source, area_m2, duration_min, hose_add_lpm -> L/min + m3. Wave 3.5: action=form_area: "
        "project, name, rows [kind slab|beam|column|wall, L, B, H, count] -> contact area, geometry is YOURS "
        "from dims (#74; shuttering DESIGN is the site engineer's). action=strike_check: project, element_kind "
        "vertical|slab_soffit|beam_soffit|props_slab_le4m5|props_beam_le6m|props_slab_gt4m5|props_beam_gt6m, "
        "cement opc, ambient_c, age_h -> IS 456 Table 10 min (OPC + >15 degC only, else REFUSE; striking "
        "the ORDER is the site engineer's, tier C). action=props_check: project, name, declared_kn_m2, "
        "allowable_kn_m2, source (supplier table) -> within/exceeds. action=scaffold_tag: project, "
        "scaffold_id, status ok|defective|altered, checked_by (competent person's NAME), next_check -> "
        "tag register (#74, the competent person applies the tag). action=day: desk summary."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["rule_add", "slab_load", "column_load", "column_size",
                                               "beam_depth", "mep_elec", "mep_water", "mep_hvac",
                                               "fire_check", "fire_demand", "form_area", "strike_check",
                                               "props_check", "scaffold_tag", "day"]},
         "family": {"type": "string"}, "rule_id": {"type": "string"}, "text": {"type": "string"},
         "value": {"type": "number"}, "unit": {"type": "string"}, "direction": {"type": "string"},
         "clause": {"type": "string"}, "source": {"type": "string"}, "checked_on": {"type": "string"},
         "project": {"type": "string"}, "name": {"type": "string"}, "occupancy": {"type": "string"},
         "thickness_m": {"type": "number"}, "finish_kn_m2": {"type": "number"},
         "tributary_m2": {"type": "number"}, "floors": {"type": "number"}, "load_kn_m2": {"type": "number"},
         "beam_add_kn": {"type": "number"}, "wall_add_kn": {"type": "number"},
         "pu_kn": {"type": "number"}, "fck": {"type": "number"}, "fy": {"type": "number"},
         "steel_pct": {"type": "number"}, "span_m": {"type": "number"}, "support": {"type": "string"},
         "depth_mm": {"type": "number"}, "connected_kw": {"type": "number"}, "demand_factor": {"type": "number"},
         "diversity": {"type": "number"}, "pf": {"type": "number"}, "note": {"type": "string"},
         "occupants": {"type": "number"}, "area_m2": {"type": "number"}, "tr_per_m2": {"type": "number"},
         "declared": {"type": "number"}, "density_lpm_m2": {"type": "number"},
         "density_source": {"type": "string"}, "duration_min": {"type": "number"},
         "hose_add_lpm": {"type": "number"}, "rows": {"type": "array", "items": {}},
         "cement": {"type": "string"}, "ambient_c": {"type": "number"}, "age_h": {"type": "number"},
         "declared_kn_m2": {"type": "number"}, "allowable_kn_m2": {"type": "number"},
         "scaffold_id": {"type": "string"}, "checked_by": {"type": "string"}, "next_check": {"type": "string"}},
         "required": ["action"]}},
    {"name": "const_predesign_dekho", "description": (
        "Read pre-design (nothing changes). what=rules (family optional) | calcs (project/kind optional) | "
        "scaffolds (project optional) | day."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["rules", "calcs", "scaffolds", "day"]},
         "family": {"type": "string"}, "project": {"type": "string"}, "kind": {"type": "string"}},
         "required": ["what"]}},
]
PREDESIGN_LABELS = {"const_predesign": "Doing pre-design calculations",
                    "const_predesign_dekho": "Viewing the pre-design desk"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import predesign as P
    from ..construction.common import guard
    guard(f"{action} predesign")
    t = ctx.tenant_id
    try:
        if action == "rule_add":
            return P.rule_add(t, _s(a.get("family")), _s(a.get("rule_id")), _s(a.get("text")),
                              a.get("value"), _s(a.get("unit")), _s(a.get("direction")) or "max",
                              _s(a.get("clause")), _s(a.get("source")), _s(a.get("checked_on")))
        if action == "slab_load":
            return P.slab_load(t, _s(a.get("project")), _s(a.get("name")), _s(a.get("occupancy")),
                               a.get("thickness_m"), a.get("finish_kn_m2") if a.get("finish_kn_m2") is not None
                               else 1.0)
        if action == "column_load":
            return P.column_load(t, _s(a.get("project")), _s(a.get("name")), a.get("tributary_m2"),
                                 a.get("floors"), a.get("load_kn_m2"), a.get("beam_add_kn") or 0.0,
                                 a.get("wall_add_kn") or 0.0)
        if action == "column_size":
            return P.column_size(t, _s(a.get("project")), _s(a.get("name")), a.get("pu_kn"), a.get("fck"),
                                 a.get("fy"), a.get("steel_pct") if a.get("steel_pct") is not None else 1.0)
        if action == "beam_depth":
            return P.beam_depth(t, _s(a.get("project")), _s(a.get("name")), a.get("span_m"),
                                _s(a.get("support")), a.get("depth_mm") or 0.0)
        if action == "mep_elec":
            return P.mep_elec(t, _s(a.get("project")), _s(a.get("name")), a.get("connected_kw"),
                              a.get("demand_factor"), a.get("diversity") if a.get("diversity") is not None
                              else 1.0, a.get("pf") if a.get("pf") is not None else 0.8)
        if action == "mep_water":
            return P.mep_water(t, _s(a.get("project")), _s(a.get("name")), a.get("occupants"))
        if action == "mep_hvac":
            return P.mep_hvac(t, _s(a.get("project")), _s(a.get("name")), a.get("area_m2"),
                              a.get("tr_per_m2"), _s(a.get("source")))
        if action == "fire_check":
            return P.fire_check(t, _s(a.get("project")), _s(a.get("rule_id")), a.get("declared"),
                                _s(a.get("note")))
        if action == "fire_demand":
            return P.fire_demand(t, _s(a.get("project")), _s(a.get("name")), a.get("density_lpm_m2"),
                                 a.get("area_m2"), a.get("duration_min"), a.get("hose_add_lpm") or 0.0,
                                 _s(a.get("density_source")))
        if action == "form_area":
            return P.form_area(t, _s(a.get("project")), _s(a.get("name")), a.get("rows") or [],
                               _s(a.get("note")))
        if action == "strike_check":
            return P.strike_check(t, _s(a.get("project")), _s(a.get("element_kind")) or _s(a.get("kind")),
                                  _s(a.get("cement")) or "opc", a.get("ambient_c"), a.get("age_h"))
        if action == "props_check":
            return P.props_check(t, _s(a.get("project")), _s(a.get("name")), a.get("declared_kn_m2"),
                                 a.get("allowable_kn_m2"), _s(a.get("source")), _s(a.get("note")))
        if action == "scaffold_tag":
            return P.scaffold_tag(t, _s(a.get("project")), _s(a.get("scaffold_id")), _s(a.get("status")),
                                  _s(a.get("checked_by")) or _s(a.get("by")), _s(a.get("next_check")),
                                  _s(a.get("note")))
        if action == "day":
            return P.day(t)
    except (P.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown action")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..construction import predesign as P
    from ..construction.common import guard
    from ..db import session
    from sqlalchemy import select
    from ..construction.models import CpdCalc, CpdRule, CpdScaffold
    guard(f"read predesign {what}")
    t = ctx.tenant_id
    try:
        if what == "day":
            return P.day(t)
        if what == "rules":
            q = select(CpdRule).where(CpdRule.tenant_id == t)
            if _s(a.get("family")):
                q = q.where(CpdRule.family == _s(a.get("family")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"rules": [{"id": r.id, "family": r.family, "rule_id": r.rule_id, "text": r.text[:80],
                               "value": r.value, "direction": r.direction, "unit": r.unit, "clause": r.clause,
                               "source": r.source[:60]} for r in rows]}
        if what == "calcs":
            q = select(CpdCalc).where(CpdCalc.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CpdCalc.project == _s(a.get("project")))
            if _s(a.get("kind")):
                q = q.where(CpdCalc.kind == _s(a.get("kind")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"calcs": [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                               "result": P._j(r.result, {}), "is_ref": r.is_ref[:80]} for r in rows]}
        if what == "scaffolds":
            q = select(CpdScaffold).where(CpdScaffold.tenant_id == t)
            if _s(a.get("project")):
                q = q.where(CpdScaffold.project == _s(a.get("project")))
            with session() as s:
                rows = s.scalars(q).all()
            return {"scaffolds": [{"id": r.id, "project": r.project, "scaffold_id": r.scaffold_id,
                                   "status": r.status, "checked_by": r.checked_by, "next_check": r.next_check}
                                  for r in rows]}
    except (P.CstError, ValueError) as ex:
        raise ToolError(str(ex)) from None
    raise ToolError("unknown what")


async def const_predesign(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def const_predesign_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


PREDESIGN_HANDLERS = {"const_predesign": const_predesign, "const_predesign_dekho": const_predesign_dekho}
