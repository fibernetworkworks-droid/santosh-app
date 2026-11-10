"""C12: the Pre-design desk (register #10 Structural Pre-design Assistant, #11 MEP Design Assistant,
#12 Fire-safety Design Checker) - Wave 3, v0.550.0, plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md §7.

Working papers for the NAMED professional - the structural engineer, the MEP consultant, the fire
consultant. Design itself is largely UNGATED in India (the register's finding 2), and this desk stays
exactly in that room: load take-down and preliminary sizing by IS-code tables, MEP load estimates,
NBC-rule hit checks - every number with its formula and inputs, every rule row with its clause and
source (pack rows via statepacks, project rows via rule_add - a rule without its clause refuses).

The tier edges, said on every output:
- PRELIMINARY is the word on every structural row: member DESIGN and the stability certificate are the
  registered engineer's (tier C, gates.py). Column sizing is the cl 39.3 short-braced working paper.
- MEP estimates ride FED factors with their source; energisation and execution gates stay with humans.
- fire checks are arithmetic (declared vs limit, clause cited) - the verdict is the fire consultant's;
  Form A/B is the Licensed Agency's (tier C)."""
from __future__ import annotations

import math

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import CpdCalc, CpdRule, CpdScaffold
from . import statepacks as SP

LL_KINDS = {"residential": "is875_p2_residential", "office": "is875_p2_office", "stair": "is875_p2_stair"}
SPAN_KINDS = {"cantilever": "is456_beam_cantilever", "simply_supported": "is456_beam_ss",
              "continuous": "is456_beam_continuous"}


def _pack_ref(state: str, rule_id: str) -> dict:
    try:
        return SP.rule_cited(state, rule_id)
    except SP.PackError as ex:
        raise CstError(str(ex)) from None


def _store(tenant: str, project: str, kind: str, name: str, inputs: dict, result: dict, is_ref: str,
           note: str = "") -> str:
    with _LOCK, session() as s:
        x = CpdCalc(tenant_id=tenant, project=project.strip()[:160], kind=kind, name=name.strip()[:160],
                    inputs=_dump(inputs), result=_dump(result), is_ref=is_ref[:200], note=note[:200])
        s.add(x)
        s.flush()
        return x.id


# ---------------------------------------------------------------- rules as DATA
def rule_add(tenant: str, family: str, rule_id: str, text: str, value, unit: str, direction: str,
             clause: str, source: str, checked_on: str = "") -> dict:
    """A project rule row (fire travel distance, MEP norm...): clause + source REQUIRED - bina clause
    ka rule bye-law / code nahi hota. The national pack's determined rows already live in the pack."""
    fams = ("ll", "unit", "span", "fire", "mep", "other")
    if family not in fams:
        raise CstError(f"family: {' | '.join(fams)}")
    if not str(rule_id or "").strip() or not str(text or "").strip():
        raise CstError("Rule id aur text bataiye.")
    if _num(value) <= 0:
        raise CstError("Value bataiye (> 0).")
    if direction not in ("min", "max"):
        raise CstError("direction: min | max")
    cl, src = str(clause or "").strip(), str(source or "").strip()
    if not cl or not src:
        raise CstError("Clause aur source dono chahiye (jaise 'NBC 2016 Part 4 cl 4.4', 'MEP consultant "
                       "note 12 Oct') - bina clause ka rule guess hai. Nahi chalta.")
    with _LOCK, session() as s:
        x = CpdRule(tenant_id=tenant, family=family, rule_id=rule_id.strip()[:60], text=text.strip()[:300],
                    value=_num(value), direction=direction, unit=unit.strip()[:20], clause=cl[:160],
                    source=src[:200], checked_on=(_date(checked_on) or today(tenant)).isoformat())
        s.add(x)
        s.flush()
        rid = x.id
    return {"rule_id": rid,
            "say": f"Rule juda: {rule_id} = {_num(value):g} {unit} ({direction}) - {cl} ({src[:60]}). "
                   "Checks isi against honge; verdict professional ka."}


def _rule(tenant: str, rule_id: str, state: str = "india") -> dict:
    """Her project row first, then the pack rows - the same precedence the state-pack law sets."""
    with session() as s:
        r = s.scalars(select(CpdRule).where(CpdRule.tenant_id == tenant,
                                            CpdRule.rule_id == rule_id)).first()
    if r:
        return {"rule_id": r.rule_id, "value": r.value, "direction": r.direction, "unit": r.unit,
                "clause": r.clause, "source": r.source}
    return _pack_ref(state, rule_id)


# ---------------------------------------------------------------- structural pre-design (#10)
def slab_load(tenant: str, project: str, name: str, occupancy: str, thickness_m: float,
              finish_kn_m2: float = 1.0, state: str = "india") -> dict:
    """Slab load take-down: LL (pack row by occupancy) + slab self-weight (t x RCC unit weight) +
    floor finish. kN/m2 with the full trail; the design combination is the engineer's."""
    occ = (occupancy or "").strip().lower()
    if occ not in LL_KINDS:
        raise CstError(f"occupancy: {' | '.join(sorted(LL_KINDS))} (pack rows yahi rakhti hain; baaki "
                       "occupancy ke liye apni sourced rule row jodo).")
    if _num(thickness_m) <= 0:
        raise CstError("Slab thickness bataiye (> 0).")
    ll = _pack_ref(state, LL_KINDS[occ])
    sw = _pack_ref(state, "is875_p1_rcc")
    llv, swv = float(ll["value"]), float(sw["value"])
    dl = round(_num(thickness_m) * swv + _num(finish_kn_m2), 3)
    total = round(llv + dl, 3)
    inputs = {"occupancy": occ, "thickness_m": _num(thickness_m), "finish_kn_m2": _num(finish_kn_m2),
              "ll_kn_m2": llv, "rcc_kn_m3": swv}
    result = {"dl_kn_m2": dl, "ll_kn_m2": llv, "total_kn_m2": total,
              "formula": f"LL {llv:g} + t {_num(thickness_m):g} x RCC {swv:g} + finish {_num(finish_kn_m2):g}"}
    cid = _store(tenant, project, "slab_load", name, inputs, result,
                 f"{ll['clause']} ({ll['source'][:50]}); {sw['clause']} ({sw['source'][:50]})")
    return {"calc_id": cid, **result,
            "say": f"Slab load ({name}): DL {dl:g} + LL {llv:g} = {total:g} kN/m2. PRELIMINARY - "
                   "combinations aur design structural engineer ka; yeh take-down hai."}


def column_load(tenant: str, project: str, name: str, tributary_m2: float, floors: int,
                load_kn_m2: float, beam_add_kn: float = 0.0, wall_add_kn: float = 0.0) -> dict:
    """Column axial take-down: tributary area x floors x floor load + beam/wall additions (kN) -
    the tributary area is HER reading, recorded as fed."""
    if _num(tributary_m2) <= 0 or _num(load_kn_m2) <= 0 or not floors or int(floors) < 1:
        raise CstError("Tributary area, floors aur floor load bataiye (sab > 0).")
    pu = round(_num(tributary_m2) * int(floors) * _num(load_kn_m2) + _num(beam_add_kn) + _num(wall_add_kn), 2)
    inputs = {"tributary_m2": _num(tributary_m2), "floors": int(floors), "load_kn_m2": _num(load_kn_m2),
              "beam_add_kn": _num(beam_add_kn), "wall_add_kn": _num(wall_add_kn)}
    result = {"pu_kn": pu, "formula": "A_trib x floors x load + beams + walls"}
    cid = _store(tenant, project, "column_load", name, inputs, result,
                 "tributary-area take-down as fed; combinations = engineer ka")
    return {"calc_id": cid, **result,
            "say": f"Column load ({name}): Pu ~ {pu:,.0f} kN (tributary x floors x load + additions). "
                   "PRELIMINARY - the load path and combinations are the structural engineer's."}


def column_size(tenant: str, project: str, name: str, pu_kn: float, fck: float, fy: float,
                steel_pct: float = 1.0) -> dict:
    """Preliminary column size: IS 456 cl 39.3 short braced axially loaded - Pu = 0.4 fck Ac + 0.67 fy Asc,
    Asc = p x Ac -> Ac = Pu / (0.4 fck + 0.67 fy p). Side rounded UP to the 50 mm module, rounding shown.
    PRELIMINARY: eccentricity, slenderness and the design are the registered engineer's."""
    if _num(pu_kn) <= 0 or _num(fck) <= 0 or _num(fy) <= 0:
        raise CstError("Pu, fck, fy bataiye (sab > 0).")
    p = _num(steel_pct) / 100.0
    if not 0.004 <= p <= 0.06:
        raise CstError("steel_pct 0.4 - 6% ke beech rakho (IS 456 ki limit ke andar).")
    ac = _num(pu_kn) / (0.4 * _num(fck) + 0.67 * _num(fy) * p)
    side = math.ceil(math.sqrt(max(ac, 1.0)) / 50.0) * 50
    inputs = {"pu_kn": _num(pu_kn), "fck": _num(fck), "fy": _num(fy), "steel_pct": _num(steel_pct)}
    result = {"ac_mm2": round(ac, 0), "side_mm": side,
              "formula": "Ac = Pu / (0.4 fck + 0.67 fy p), side = ceil(sqrt(Ac)/50) x 50"}
    cid = _store(tenant, project, "column_size", name, inputs, result,
                 "IS 456:2000 cl 39.3 - short braced, axially loaded only; preliminary sizing")
    return {"calc_id": cid, **result,
            "say": f"Column ({name}): Ac ~ {ac:,.0f} mm2 -> {side} mm square (50 mm module). PRELIMINARY "
                   "working paper (short, braced, axial only) - design, eccentricity and the stability "
                   "certificate registered engineer ke: Hoola sirf hisaab dikhata hai."}


def beam_depth(tenant: str, project: str, name: str, span_m: float, support: str, depth_mm: float = 0.0,
               state: str = "india") -> dict:
    """Deflection route check: span / basic ratio (IS 456 cl 23.2.1, spans <= 10 m) vs the fed depth.
    Spans beyond 10 m need the modification factors - refused, never improvised."""
    if support not in SPAN_KINDS:
        raise CstError(f"support: {' | '.join(sorted(SPAN_KINDS))}")
    if _num(span_m) <= 0:
        raise CstError("Span bataiye (> 0).")
    if _num(span_m) > 10.0:
        raise CstError("Span > 10 m: basic ratio ke modification factors (IS 456 Fig. 4) lagte hain - "
                       "yeh engineer ka hisaab hai, Hoola guess nahi karta.")
    r = _pack_ref(state, SPAN_KINDS[support])
    ratio = float(r["value"])
    dmin = round(_num(span_m) * 1000 / ratio, 0)
    verdict = "no_depth_fed"
    if _num(depth_mm) > 0:
        verdict = "ok" if _num(depth_mm) >= dmin else "short"
    inputs = {"span_m": _num(span_m), "support": support, "depth_mm": _num(depth_mm), "ratio": ratio}
    result = {"depth_min_mm": dmin, "verdict": verdict,
              "formula": f"span x 1000 / {ratio:g} = {dmin:g} mm"}
    cid = _store(tenant, project, "beam_depth", name, inputs, result,
                 f"{r['clause']} ({r['source'][:60]})")
    say = (f"Beam ({name}): min effective depth {dmin:g} mm (span {span_m:g} m / {ratio:g}, {support}) - "
           "PRELIMINARY deflection route; design engineer ka. "
           if verdict == "no_depth_fed" else
           f"Beam ({name}): fed {depth_mm:g} mm vs min {dmin:g} mm -> "
           f"{'WITHIN (arithmetic)' if verdict == 'ok' else 'SHORT (arithmetic)'}. "
           f"Rule: {r['clause']}. Design faisla structural engineer ka. ")
    return {"calc_id": cid, **result, "say": say}


# ---------------------------------------------------------------- MEP estimates (#11)
def mep_elec(tenant: str, project: str, name: str, connected_kw: float, demand_factor: float,
             diversity: float = 1.0, pf: float = 0.8) -> dict:
    """Electrical load estimate: connected x demand x diversity / pf -> kVA. The factors are FED with
    their source in the note - Hoola never owns a demand factor."""
    if _num(connected_kw) <= 0 or _num(demand_factor) <= 0:
        raise CstError("Connected load aur demand factor bataiye (> 0).")
    if _num(pf) <= 0 or _num(pf) > 1.0:
        raise CstError("Power factor 0-1 ke beech bataiye.")
    kva = round(_num(connected_kw) * _num(demand_factor) * _num(diversity) / _num(pf), 2)
    inputs = {"connected_kw": _num(connected_kw), "demand_factor": _num(demand_factor),
              "diversity": _num(diversity), "pf": _num(pf)}
    result = {"kva": kva, "formula": "kW x demand x diversity / pf"}
    cid = _store(tenant, project, "elec", name, inputs, result,
                 "factors as fed (source note mein) - estimate, sanction MESDCL/utility ke through")
    return {"calc_id": cid, **result,
            "say": f"Electrical estimate ({name}): ~{kva:,.1f} kVA (factors aapne feed kiye - note mein "
                   "source likha hai?). Load-sanction application utility ke through, aapke naam se."}


def mep_water(tenant: str, project: str, name: str, occupants: float, state: str = "india") -> dict:
    """Water demand: occupants x per-capita norm (CPHEEO pack row) -> KLD, cited."""
    if _num(occupants) <= 0:
        raise CstError("Occupants bataiye (> 0).")
    r = _pack_ref(state, "cpheeo_lpcd")
    kld = round(_num(occupants) * float(r["value"]) / 1000.0, 2)
    inputs = {"occupants": _num(occupants), "lpcd": float(r["value"])}
    result = {"kld": kld, "formula": f"{_num(occupants):g} x {float(r['value']):g} lpcd / 1000"}
    cid = _store(tenant, project, "water", name, inputs, result,
                 f"{r['clause']} ({r['source'][:70]})")
    return {"calc_id": cid, **result,
            "say": f"Water demand ({name}): {kld:,.2f} KLD ({r['clause'][:60]}). Estimate - plumbing "
                   "design MEP consultant ka."}


def mep_hvac(tenant: str, project: str, name: str, area_m2: float, tr_per_m2: float, source: str) -> dict:
    """HVAC tonnage estimate: area x TR/m2 - the norm is FED with its source (rule-of-thumb stays
    labelled); the detailed cooling load is the consultant's work."""
    if _num(area_m2) <= 0 or _num(tr_per_m2) <= 0:
        raise CstError("Area aur TR/m2 bataiye (> 0).")
    if not str(source or "").strip():
        raise CstError("TR/m2 norm ka SOURCE bataiye (consultant note / OEM table) - bina source ka "
                       "norm estimate nahi banta.")
    tr = round(_num(area_m2) * _num(tr_per_m2), 2)
    inputs = {"area_m2": _num(area_m2), "tr_per_m2": _num(tr_per_m2)}
    result = {"tr": tr, "formula": f"{_num(area_m2):g} m2 x {_num(tr_per_m2):g} TR/m2"}
    cid = _store(tenant, project, "hvac", name, inputs, result, f"norm as fed - {source.strip()[:80]}")
    return {"calc_id": cid, **result,
            "say": f"HVAC estimate ({name}): ~{tr:,.1f} TR (norm: {source.strip()[:50]}). "
                   "Rule-of-thumb hai - detailed cooling load MEP consultant ka."}


# ---------------------------------------------------------------- fire checks (#12)
def fire_check(tenant: str, project: str, rule_id: str, declared, note: str = "") -> dict:
    """One fire-rule check: declared vs limit (min/max from the rule) - ARITHMETIC with the clause
    cited; the verdict belongs to the fire consultant, Form A/B to the Licensed Agency."""
    with session() as s:
        r = s.scalars(select(CpdRule).where(CpdRule.tenant_id == tenant,
                                            CpdRule.rule_id == rule_id, CpdRule.family == "fire")).first()
    if r is None:
        raise CstError(f"Fire rule '{rule_id}' nahi hai - rule_add se clause + source ke saath jodo. "
                       "Bina rule ke check nahi hota (guess bye-law nahi hota).")
    val = _num(declared)
    if r.direction == "min":
        verdict = "ok" if val >= r.value else "breach"
        margin = round(val - r.value, 3)
    else:
        verdict = "ok" if val <= r.value else "breach"
        margin = round(r.value - val, 3)
    cid = _store(tenant, project, "fire_check", r.rule_id,
                 {"rule": r.rule_id, "declared": val}, {"limit": r.value, "verdict": verdict, "margin": margin},
                 f"{r.clause} ({r.source[:70]})", note)
    return {"calc_id": cid, "rule": r.rule_id, "declared": val, "limit": r.value, "verdict": verdict,
            "margin": margin,
            "say": f"{r.rule_id}: declared {val:g} vs limit {r.value:g} {r.unit} ({r.direction}) -> "
                   f"{'WITHIN' if verdict == 'ok' else 'BREACH'} (arithmetic). Rule: {r.clause} "
                   f"({r.source[:50]}). Faisla fire consultant ka; Form A/B Licensed Agency ki."}


def fire_demand(tenant: str, project: str, name: str, density_lpm_m2: float, area_m2: float,
                duration_min: float, hose_add_lpm: float = 0.0, density_source: str = "") -> dict:
    """Sprinkler/hydrant demand arithmetic: density x area + hose allowance, x duration -> litres and
    m3. The density is HER sourced row (hazard class se); the system design is the fire consultant's."""
    if _num(density_lpm_m2) <= 0 or _num(area_m2) <= 0 or _num(duration_min) <= 0:
        raise CstError("Density, area aur duration bataiye (sab > 0).")
    if not str(density_source or "").strip():
        raise CstError("Density ka SOURCE bataiye (NBC hazard table / consultant note) - bina source ki "
                       "density demand nahi banti.")
    lpm = round(_num(density_lpm_m2) * _num(area_m2) + _num(hose_add_lpm), 1)
    litres = round(lpm * _num(duration_min), 0)
    inputs = {"density_lpm_m2": _num(density_lpm_m2), "area_m2": _num(area_m2),
              "duration_min": _num(duration_min), "hose_add_lpm": _num(hose_add_lpm)}
    result = {"lpm": lpm, "litres": litres, "m3": round(litres / 1000.0, 2),
              "formula": f"density x area + hose, x {duration_min:g} min"}
    cid = _store(tenant, project, "fire_demand", name, inputs, result, f"density as fed - {density_source.strip()[:80]}")
    return {"calc_id": cid, **result,
            "say": f"Fire demand ({name}): {lpm:,.0f} L/min, {litres:,.0f} L ({litres / 1000.0:,.1f} m3) "
                   f"over {duration_min:g} min (density source: {density_source.strip()[:40]}). "
                   "System design fire consultant ka - Hoola ka arithmetic."}


# --------------------------------------------------- #74 formwork & scaffold (Wave 3.5, v0.565.0)
_FORM_KINDS = ("slab", "beam", "column", "wall")


def form_area(tenant: str, project: str, name: str, rows: list, note: str = "") -> dict:
    """Formwork contact area (#74): plain GEOMETRY on HER element rows - [kind, L, B, H, count]
    (metres; slab soffit L x B, beam soffit + 2 sides, column 4 faces, wall both faces). The
    formwork DESIGN (props, shores, panels, ties) is the site engineer's - this is the take-off."""
    if not rows:
        raise CstError("Element rows bhejo [kind, L, B, H, count] - dims AAPKI readings, metre mein.")
    out, total = [], 0.0
    for r in (rows or []):
        try:
            v = r if isinstance(r, list) else [p.strip() for p in str(r).split(",")]
            kind = str(v[0]).strip().lower()
            L, B, H = float(v[1]), float(v[2]), float(v[3])
            n = int(float(v[4])) if len(v) > 4 and str(v[4]).strip() else 1
        except (TypeError, ValueError, IndexError):
            continue
        if kind not in _FORM_KINDS or L <= 0 or n < 1:
            continue
        if kind == "slab":
            one, f = L * B, "L x B (soffit)"
        elif kind == "beam":
            one, f = L * B + 2.0 * L * H, "L x B (soffit) + 2 x L x H (sides)"
        elif kind == "column":
            one, f = 2.0 * (L + B) * H, "2 x (L + B) x H (4 faces)"
        else:
            one, f = 2.0 * L * H, "2 x L x H (both faces)"
        one = round(one * n, 3)
        out.append({"kind": kind, "L": L, "B": B, "H": H, "count": n, "area_m2": one, "formula": f})
        total += one
    if not out:
        raise CstError("Koi valid row nahi - kind: slab | beam | column | wall, dims metre mein (> 0), "
                       "count >= 1 (slab mein H=0 chalega).")
    total = round(total, 2)
    inputs = {"rows": len(out)}
    result = {"total_m2": total, "rows": out, "formula": "geometry on HER dims - no factor invented"}
    cid = _store(tenant, project, "formwork", name, inputs, result,
                 "contact-area geometry as fed; formwork design + prop loads = site engineer ka")
    return {"calc_id": cid, "total_m2": total, "rows": out,
            "say": f"Formwork contact area ({name}): {total:,.2f} m2 ({len(out)} element rows, geometry "
                   "AAPKE dims se). Yeh take-off hai - shuttering design, props aur load checks site "
                   "engineer ke (supplier tables wahan lagti hain). Striking time strike_check se."}


def strike_check(tenant: str, project: str, element_kind: str, cement: str, ambient_c: float,
                 age_h: float, state: str = "india") -> dict:
    """Striking-time check (#74): age vs the IS 456 cl 11.3 Table 10 minimum (pack rows, OPC +
    ambient above 15 degC ONLY - outside that scope the desk REFUSES; the striking order stays
    with the site engineer, tier C)."""
    kinds = {"vertical": "is456_strike_vertical", "slab_soffit": "is456_strike_slab_soffit",
             "beam_soffit": "is456_strike_beam_soffit", "props_slab_le4m5": "is456_strike_props_slab_le4m5",
             "props_beam_le6m": "is456_strike_props_beam_le6m", "props_slab_gt4m5": "is456_strike_props_slab_gt4m5",
             "props_beam_gt6m": "is456_strike_props_beam_gt6m"}
    if element_kind not in kinds:
        raise CstError(f"element_kind: {' | '.join(sorted(kinds))} (IS 456 Table 10 rows yahi rakhti hain).")
    cem = (cement or "").strip().lower()
    if cem not in ("opc", "opc43", "opc53"):
        raise CstError("IS 456 Table 10 sirf OPC (ambient > 15 degC) ke liye hai - blending/mineral "
                       "cements ke liye striking time maturity se engineer decide karta hai; Hoola "
                       "guess nahi karta. cement=opc batao ya hisaab engineer se.")
    if _num(ambient_c) <= 15.0:
        raise CstError(f"Ambient {_num(ambient_c):g} degC: Table 10 ka scope nahi (> 15 degC chahiye, "
                       "OPC) - thandi / blending conditions par striking time engineer ka hisaab hai.")
    if _num(age_h) <= 0:
        raise CstError("Age (hours) bataiye (> 0).")
    r = _pack_ref(state, kinds[element_kind])
    mn = float(r["value"])
    verdict = "ok" if _num(age_h) >= mn else "short"
    inputs = {"element_kind": element_kind, "cement": "opc", "ambient_c": _num(ambient_c), "age_h": _num(age_h)}
    result = {"min_h": mn, "verdict": verdict, "margin_h": round(_num(age_h) - mn, 1),
              "formula": f"age {_num(age_h):g} h vs Table 10 min {mn:g} h"}
    cid = _store(tenant, project, "strike", element_kind, inputs, result,
                 f"{r['clause']} ({r['source'][:60]}); OPC + ambient > 15 C scope")
    say = (f"Striking ({element_kind}): age {_num(age_h):g} h vs IS 456 Table 10 min {mn:g} h -> "
           f"{'WITHIN (arithmetic)' if verdict == 'ok' else 'SHORT (arithmetic)'}. Rule: {r['clause']} "
           "(OPC, ambient > 15 degC). Formwork hatane ka ORDER site engineer ka hai - Hoola ka "
           "hisaab, tier C.")
    return {"calc_id": cid, **result, "say": say}


def props_check(tenant: str, project: str, name: str, declared_kn_m2: float, allowable_kn_m2: float,
                source: str, note: str = "") -> dict:
    """Prop/shoring load check (#74): HER declared load vs the SUPPLIER TABLE's allowable - the
    allowable needs its source (the supplier sheet), the comparison is arithmetic."""
    if _num(declared_kn_m2) <= 0 or _num(allowable_kn_m2) <= 0:
        raise CstError("Declared aur allowable load bataiye (sab > 0).")
    if not str(source or "").strip():
        raise CstError("Allowable ka SOURCE bataiye (supplier table / design note) - bina source ki "
                       "allowable value check nahi hoti.")
    verdict = "ok" if _num(declared_kn_m2) <= _num(allowable_kn_m2) else "exceeds"
    margin = round(_num(allowable_kn_m2) - _num(declared_kn_m2), 3)
    inputs = {"declared_kn_m2": _num(declared_kn_m2), "allowable_kn_m2": _num(allowable_kn_m2)}
    result = {"verdict": verdict, "margin_kn_m2": margin,
              "formula": f"declared {_num(declared_kn_m2):g} vs allowable {_num(allowable_kn_m2):g} kN/m2"}
    cid = _store(tenant, project, "props", name, inputs, result,
                 f"allowable as fed - {source.strip()[:80]}", note)
    return {"calc_id": cid, **result,
            "say": f"Props ({name}): declared {_num(declared_kn_m2):g} vs allowable "
                   f"{_num(allowable_kn_m2):g} kN/m2 ({source.strip()[:40]}) -> "
                   f"{'WITHIN (arithmetic)' if verdict == 'ok' else 'EXCEEDS (arithmetic)'}. Shoring "
                   "design aur safe scheme site engineer ki - Form-hatane se pehle uska check."}


def scaffold_tag(tenant: str, project: str, scaffold_id: str, status: str, checked_by: str,
                 next_check: str = "", note: str = "") -> dict:
    """Scaffold inspection tag row (#74): the competent person's word, NAME required (ok |
    defective | altered) - Hoola keeps the register; the tag itself is her hand's act."""
    if status not in ("ok", "defective", "altered"):
        raise CstError("status: ok | defective | altered")
    if not str(checked_by or "").strip():
        raise CstError("Kisne check kiya? (competent person ka NAAM record hota hai).")
    if not str(scaffold_id or "").strip():
        raise CstError("Scaffold ka id bataiye.")
    with _LOCK, session() as s:
        x = CpdScaffold(tenant_id=tenant, project=project.strip()[:160], scaffold_id=scaffold_id.strip()[:80],
                        status=status, checked_by=checked_by.strip()[:120], next_check=(next_check or "")[:10],
                        note=note.strip()[:200])
        s.add(x)
        s.flush()
        sid = x.id
    return {"tag_id": sid,
            "say": f"Scaffold {scaffold_id.strip()[:16]}: {status} ({checked_by.strip()}"
                   + (f", next check {next_check}" if next_check else "") + "). Tag competent person "
                   "ke haath ka act hai - register Hoola rakhta hai (tier C)."}


def day(tenant: str) -> dict:
    """The pre-design morning (Wave 3.5 adds scaffolds): rules, calcs by kind, breach-flags, scaffold tags."""
    with session() as s:
        rules = s.scalars(select(CpdRule).where(CpdRule.tenant_id == tenant)).all()
        calcs = s.scalars(select(CpdCalc).where(CpdCalc.tenant_id == tenant)).all()
        scaffolds = s.scalars(select(CpdScaffold).where(CpdScaffold.tenant_id == tenant)).all()
    by_kind: dict[str, int] = {}
    for c in calcs:
        by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
    breaches = sum(1 for c in calcs if _j(c.result, {}).get("verdict") in ("breach", "short", "exceeds"))
    defectives = sum(1 for sc in scaffolds if sc.status != "ok")
    return {"rules": len(rules), "calcs": by_kind, "breach_flags": breaches, "scaffold_tags": len(scaffolds),
            "scaffold_defective": defectives,
            "say": f"Pre-design desk: {len(rules)} rules, {len(calcs)} calcs, {breaches} breach/short/"
                   f"exceeds flag, {len(scaffolds)} scaffold tags ({defectives} defective/altered). "
                   "Sab PRELIMINARY working papers - sign lines khaali hain."}
