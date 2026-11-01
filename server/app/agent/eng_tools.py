"""v0.357 ENGINEERING DESK chat tool: the hired CAD Engineer designs a part from her words (CadQuery in Hoola's locked
box) and changes it on her words. Files (STEP / STL / drawing PDF / views) land on the CAD Desk; the chat gets one line."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

ENG_TOOLS = [
    {"name": "cad_part", "description": (
        "The CAD Engineer (an employee she hires in Employees). Designs a mechanical part from her words and sizes in mm "
        "as parametric CadQuery code, builds it in Hoola's locked box (no network), checks it (valid solid, one body, "
        "the size asked) and gives STEP (CAD / CNC), STL (3D printing), 4 views and a dimensioned drawing PDF on the CAD "
        "Desk. v0.365 it also does: assemblies with a BOM, real threads, sheet metal with flat pattern (DXF), smooth "
        "freeform bodies, FEA (stress + safety factor, fatigue life, heat, vibration / natural frequencies, laminar "
        "flow / pressure drop through a channel) and measured manufacturability checks (3D print / CNC / sheet metal / "
        "injection moulding: walls, overhangs, inside corners, deep holes, setups, bends, draft, undercuts) that send a weak "
        "or unmakeable design "
        "back to be strengthened, and CNC G-code - put her load (kg / N), fixing, temperature / watts, motor rpm, CNC "
        "machine or sheet thickness in the brief and the engineer uses them. "
        "action=new brief=<what the part is, every size she gave in mm, holes, fillets, material> starts a part "
        "(runs in the background, about a minute; the chat gets a line when ready). action=change project_id=... "
        "words=<her change> makes the next version. action=list / get project_id=... show parts and files. "
        "If she has not hired the CAD Engineer, tell her to hire it from Employees (one tap). Never call a design "
        "certified, approved or safe without a qualified engineer; refuse weapons and export-controlled parts."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "change", "list", "get"]},
         "brief": {"type": "string"}, "project_id": {"type": "string"}, "words": {"type": "string"}},
         "required": ["action"]}},
]
ENG_TOOLS.append(
    {"name": "eng_calc", "description": (
        "Engineering hand calculations, exact, no CAD needed (part of the CAD Engineer). kind=fit args={size, fit:'H7/g6'} "
        "ISO 286 limits + clearance; kind=stack args={chain:[{name, nominal, plus, minus, dir:+1|-1}], lower, upper} "
        "tolerance stack-up worst case / RSS / Monte Carlo + Cpk; kind=bolt args={m, grade:'8.8', count, shear_N, "
        "tension_N} preload, torque, utilisation; kind=weld args={force_N, length_mm, leg_mm} fillet weld; kind=beam "
        "args={support: cantilever|simple|fixed_fixed, length_mm, section:{type: rect|round|tube|rect_tube|i, ...}, "
        "load_N, udl_N_per_mm, material} deflection, stress, first natural frequency; kind=pipe args={flow_lpm, "
        "diameter_mm, length_m, fluid: water|air|oil|diesel, roughness_mm, fittings_k} pressure drop; kind=joint args={m, "
        "grade, grip_mm, plates: steel|aluminium|cast iron|copper, load_N (total tension), shear_N, bolts, preload_pct} "
        "VDI 2230-style bolted joint (stiffness, load factor, separation, yield, bolt fatigue, slip); kind=fatigue "
        "args={sigma_max_MPa, sigma_min_MPa, material, finish, size_mm, reliability, life, kt} stress-life fatigue "
        "(Goodman + Marin). Show the numbers "
        "with units and say it is a draft for an engineer's check."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["fit", "stack", "bolt", "weld", "beam", "pipe", "joint", "fatigue"]},
         "args": {"type": "object"}}, "required": ["kind", "args"]}})
ENG_LABELS = {"cad_part": "CAD part bana raha hoon", "eng_calc": "Engineering hisaab laga raha hoon"}


async def eng_calc(ctx: Ctx, kind, args=None, **_):
    from ..engineering import calc

    def go():
        try:
            return calc.run(str(kind or ""), dict(args or {}))
        except calc.CalcError as e:
            raise ToolError(str(e))
    return await asyncio.to_thread(go)


async def cad_part(ctx: Ctx, action, brief="", project_id="", words="", **_):
    from ..engineering import service as eng

    def go():
        try:
            if action == "new":
                p = eng.start(ctx.tenant_id, ctx.conversation_id, str(brief or ""))
                return {"project_id": p["id"], "status": p["status"],
                        "say": "Part ban raha hai (lagbhag ek minute). Taiyaar hote hi chat mein line aayegi; files CAD Desk par."}
            if action == "change":
                p = eng.change(ctx.tenant_id, str(project_id or ""), str(words or ""), ctx.conversation_id)
                return {"project_id": p["id"], "status": p["status"], "say": "Naya version ban raha hai."}
            if action == "get":
                return eng.get(ctx.tenant_id, str(project_id or ""))
            if action == "list":
                return {"projects": [{k: p[k] for k in ("id", "title", "status", "stage")} for p in eng.projects(ctx.tenant_id, 15)]}
        except eng.EngError as e:
            raise ToolError(str(e))
        raise ToolError("action must be new, change, list or get")
    return await asyncio.to_thread(go)


ENG_HANDLERS = {"cad_part": cad_part, "eng_calc": eng_calc}
