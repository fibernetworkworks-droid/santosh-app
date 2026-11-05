"""C15: the Green & performance desk (register #104 Energy Manager / Auditor, #110 Green Building
Consultant's Assistant, #111 ECBC Compliance Checker, #112 Energy Modelling Assistant, #113 Daylight
& Thermal-comfort Analyst, #114 Embodied Carbon / LCA Assistant, #115 Water, Rainwater & Waste Planner,
#116 Commissioning Authority's Assistant, #117 T&C Records Keeper, #118 M&V Analyst) - Wave 3,
v0.550.0, plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md §7.

The honest limits, on every output:
- meter data, tariffs (HER bill's slab rows), benchmarks and savings projects are records and
  arithmetic; the AUDIT is the certified energy auditor's (tier C refusal rides the gate).
- ECBC / daylight checks run on HER sourced rule rows (clause + source required, drawqa's law);
  the verdict is arithmetic, the assessor decides.
- #112: Hoola prepares the INPUT register for the energy modeller (assumptions with their sources) -
  EnergyPlus is NOT run here and the card says so.
- embodied carbon = quantity x EPD factor with the factor's source REQUIRED; hot-spot list only.
- water demand rides the CPHEEO pack row; rainwater harvest = roof x runoff coeff x rainfall (the
  coefficient and the IMD station are hers, recorded).
- commissioning: plans, scripts, issue logs - the sign-off is the Cx authority's (tier C).
- T&C records: as-installed vs design vs tolerance is arithmetic; acceptance is the T&C engineer's.
- M&V: the baseline is the least-squares line through HER baseline rows (a, b, r2 printed); savings
  are the identity adjusted-baseline - actual. The IPMVP option is HER word."""
from __future__ import annotations

import math

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, today)
from .models import (CgrCarbon, CgrCheck, CgrCredit, CgrCx, CgrCxIssue, CgrEcbcRule, CgrMeter, CgrMv,
                     CgrTariff, CgrTc)
from . import statepacks as SP


def _rule(tenant: str, rule_id: str) -> CgrEcbcRule:
    with session() as s:
        return s.scalars(select(CgrEcbcRule).where(CgrEcbcRule.tenant_id == tenant,
                                                   CgrEcbcRule.rule_id == rule_id)).first()


# ---------------------------------------------------------------- #104 meters, tariffs, benchmark
def meter_add(tenant: str, site: str, meter: str, kwh: float, day: str = "", note: str = "") -> dict:
    """One meter reading, as fed (the bill / meter photo is the source of truth)."""
    if not str(site or "").strip() or not str(meter or "").strip():
        raise CstError("Site aur meter bataiye.")
    if _num(kwh) <= 0:
        raise CstError("kWh bataiye (> 0) - jaisa meter / bill bola.")
    with _LOCK, session() as s:
        x = CgrMeter(tenant_id=tenant, site=site.strip()[:160], meter=meter.strip()[:60],
                     day=(_date(day) or today(tenant)).isoformat(), kwh=_num(kwh), note=note[:200])
        s.add(x)
        s.flush()
        mid = x.id
    return {"meter_id": mid,
            "say": f"Reading: {meter.strip()} = {_num(kwh):g} kWh ({x.day}). Benchmark isi data se."}


def tariff_add(tenant: str, name: str, rows: list, source: str) -> dict:
    """Her tariff as DATA: slab rows from HER bill - [{from_kwh, to_kwh, rate, fixed_rs}] - with the
    bill named. No remembered rates."""
    clean = []
    for r in (rows or []):
        if not isinstance(r, dict) or _num(r.get("rate")) <= 0:
            continue
        clean.append({"from_kwh": _num(r.get("from_kwh")), "to_kwh": _num(r.get("to_kwh")),
                      "rate": _num(r.get("rate")), "fixed_rs": _num(r.get("fixed_rs"))})
    clean.sort(key=lambda r: r["from_kwh"])
    if not clean or not str(source or "").strip():
        raise CstError("Slab rows (from_kwh, to_kwh, rate) aur bill ka SOURCE bataiye - tariff guess "
                       "nahi hota.")
    with _LOCK, session() as s:
        x = CgrTariff(tenant_id=tenant, name=name.strip()[:80], rows=_dump(clean), source=source.strip()[:160])
        s.add(x)
        s.flush()
        tid = x.id
    return {"tariff_id": tid, "slabs": len(clean),
            "say": f"Tariff '{name.strip()}': {len(clean)} slabs ({source.strip()[:50]}). Bill isi se."}


def bill(tenant: str, name: str, kwh_month: float) -> dict:
    """The bill arithmetic: kwh walked through HER slab rows, slab by slab, + fixed charges."""
    if _num(kwh_month) <= 0:
        raise CstError("Month ke units bataiye (> 0).")
    with session() as s:
        t = s.scalars(select(CgrTariff).where(CgrTariff.tenant_id == tenant,
                                              CgrTariff.name == name)).first()
    if not t:
        raise CstError(f"Tariff '{name}' nahi hai - tariff_add se apne bill ki slabs jodo.")
    slabs = _j(t.rows, [])
    left, total, walk = _num(kwh_month), 0.0, []
    for sl in slabs:
        lo, hi = sl["from_kwh"], (sl["to_kwh"] if sl["to_kwh"] > 0 else float("inf"))
        if left <= 0 or _num(kwh_month) <= lo:
            continue
        take = min(left, hi - lo if hi != float("inf") else left)
        if take <= 0:
            continue
        amt = round(take * sl["rate"], 2)
        total += amt + sl["fixed_rs"]
        walk.append({"units": round(take, 1), "rate": sl["rate"], "amount": amt,
                     "fixed_rs": sl["fixed_rs"]})
        left -= take
    if left > 1e-9 and walk:
        return {"total_rs": total, "walk": walk,
                "warn": f"{left:g} units kisi slab se cover nahi hue - tariff ki slabs check karo."}
    return {"total_rs": round(total, 2), "walk": walk,
            "say": f"Bill ({name}): {_num(kwh_month):g} units -> Rs {total:,.0f} "
                   f"({len(walk)} slabs, {t.source[:40]}). HISAB hai - bill DISCOM ka hoga."}


def benchmark(tenant: str, site: str, builtup_m2: float, benchmark_kwh_m2_mo: float = 0.0,
              benchmark_source: str = "") -> dict:
    """Energy performance intensity: sum of the site's kWh / built-up -> kWh/m2/month - vs HER
    sourced benchmark (ECBC / CII / her historical). The audit stays with the certified auditor."""
    if _num(builtup_m2) <= 0:
        raise CstError("Built-up area bataiye (> 0).")
    with session() as s:
        rows = s.scalars(select(CgrMeter).where(CgrMeter.tenant_id == tenant,
                                                CgrMeter.site == site)).all()
    if not rows:
        raise CstError(f"'{site}' ke meter readings nahi - pehle meter_add se data jodo.")
    total = sum(r.kwh for r in rows)
    months = len({r.day[:7] for r in rows}) or 1
    epi = round(total / months / _num(builtup_m2), 2)
    out = {"kwh_total": round(total, 1), "months": months, "epi_kwh_m2_mo": epi}
    if _num(benchmark_kwh_m2_mo) > 0:
        if not str(benchmark_source or "").strip():
            raise CstError("Benchmark ka SOURCE bataiye (ECBC table / apna purana data) - bina source "
                           "ka benchmark comparison nahi hota.")
        out |= {"benchmark": _num(benchmark_kwh_m2_mo), "benchmark_source": benchmark_source.strip()[:160],
                "vs_benchmark_pct": round((epi - _num(benchmark_kwh_m2_mo)) / _num(benchmark_kwh_m2_mo) * 100.0, 1)}
    say = (f"EPI ({site}): {epi:,.2f} kWh/m2/month ({total:,.0f} kWh / {months} month / "
           f"{_num(builtup_m2):g} m2). "
           + (f"Benchmark {_num(benchmark_kwh_m2_mo):g} se "
              f"{out['vs_benchmark_pct']:+.1f}% (source: {benchmark_source.strip()[:40]}). " if "benchmark" in out else "")
           + "Yeh record + hisaab hai - energy audit certified auditor ka.")
    return {**out, "say": say}


# ---------------------------------------------------------------- #111 ECBC + #113 daylight checks
def rule_add(tenant: str, family: str, rule_id: str, text: str, value, unit: str, direction: str,
             clause: str, source: str, checked_on: str = "") -> dict:
    """A performance rule row (ECBC prescriptive, daylight ratio): clause + source REQUIRED."""
    fams = ("ecbc", "daylight", "benchmark", "other")
    if family not in fams:
        raise CstError(f"family: {' | '.join(fams)}")
    if not str(rule_id or "").strip() or not str(text or "").strip():
        raise CstError("Rule id aur text bataiye.")
    if _num(value) <= 0:
        raise CstError("Value bataiye (> 0).")
    if direction not in ("min", "max"):
        raise CstError("direction: min | max")
    if not str(clause or "").strip() or not str(source or "").strip():
        raise CstError("Clause aur source dono chahiye (jaise 'ECBC 2017 Table 3.2', 'ECBC user guide "
                       "PDF p.24') - bina clause ka rule code nahi hota.")
    with _LOCK, session() as s:
        x = CgrEcbcRule(tenant_id=tenant, family=family, rule_id=rule_id.strip()[:60], text=text.strip()[:300],
                        value=_num(value), direction=direction, unit=unit.strip()[:20],
                        clause=clause.strip()[:160], source=source.strip()[:200],
                        checked_on=(_date(checked_on) or today(tenant)).isoformat())
        s.add(x)
        s.flush()
        rid = x.id
    return {"rule_id": rid,
            "say": f"Rule juda: {rule_id} = {_num(value):g} {unit} ({direction}) - {clause.strip()[:60]} "
                   f"({source.strip()[:50]}). Checks isi against honge; verdict assessor ka."}


def check(tenant: str, project: str, rule_id: str, declared, note: str = "") -> dict:
    """Declared vs limit (min/max) - ARITHMETIC with the clause cited; ECBC assessor / building
    physicist own the outcome (tier B)."""
    r = _rule(tenant, rule_id)
    if r is None:
        raise CstError(f"Rule '{rule_id}' nahi hai - rule_add se clause + source ke saath jodo. Bina "
                       "rule ke check nahi hota (guess code nahi hota).")
    val = _num(declared)
    if r.direction == "min":
        verdict = "ok" if val >= r.value else "breach"
        margin = round(val - r.value, 3)
    else:
        verdict = "ok" if val <= r.value else "breach"
        margin = round(r.value - val, 3)
    with _LOCK, session() as s:
        x = CgrCheck(tenant_id=tenant, project=project.strip()[:160], rule_id=rule_id[:60], declared=val,
                     limit_value=r.value, unit=r.unit[:20], verdict=verdict,
                     checked_on=today(tenant).isoformat(), note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"check_id": cid, "rule": rule_id, "declared": val, "limit": r.value, "verdict": verdict,
            "margin": margin,
            "say": f"{rule_id}: declared {val:g} vs limit {r.value:g} {r.unit} ({r.direction}) -> "
                   f"{'WITHIN' if verdict == 'ok' else 'BREACH'} (arithmetic). Rule: {r.clause} "
                   f"({r.source[:50]}). Faisla assessor ka - Hoola ka number."}


def daylight(tenant: str, project: str, room: str, glazing_m2: float, floor_m2: float,
             rule_id: str = "") -> dict:
    """Daylight route (#113): window-to-floor ratio = glazing / floor - vs her sourced rule row when
    given. 'Results explained, not certified' - the building physicist owns the analysis."""
    if _num(glazing_m2) <= 0 or _num(floor_m2) <= 0:
        raise CstError("Glazing area aur floor area bataiye (sab > 0).")
    wfr = round(_num(glazing_m2) / _num(floor_m2) * 100.0, 2)
    out = {"wfr_pct": wfr, "glazing_m2": _num(glazing_m2), "floor_m2": _num(floor_m2),
           "formula": f"{_num(glazing_m2):g} / {_num(floor_m2):g} x 100"}
    if rule_id:
        r = _rule(tenant, rule_id)
        if not r:
            raise CstError(f"Rule '{rule_id}' nahi hai - rule_add se sourced row jodo.")
        verdict = "ok" if (wfr <= r.value if r.direction == "max" else wfr >= r.value) else "breach"
        out |= {"rule": rule_id, "limit": r.value, "direction": r.direction, "verdict": verdict}
    cid = None
    with _LOCK, session() as s:
        x = CgrCheck(tenant_id=tenant, project=project.strip()[:160],
                     rule_id=(rule_id or "wfr_computed")[:60], declared=wfr,
                     limit_value=(r.value if rule_id else 0.0), unit="%", verdict=out.get("verdict", "pending"),
                     checked_on=today(tenant).isoformat(), note=f"daylight WFR {room}"[:200])
        s.add(x)
        s.flush()
        cid = x.id
    say = (f"Daylight ({room}): WFR {wfr:.2f}% ({out['formula']}). "
           + (f"Rule {rule_id}: {'WITHIN' if out.get('verdict') == 'ok' else 'BREACH'} vs "
              f"{r.value:g}% ({r.direction}) - {r.clause[:40]}. " if rule_id else "")
           + "Explained, not certified - thermal comfort / DF analysis building physicist ki.")
    return {"check_id": cid, **out, "say": say}


# ---------------------------------------------------------------- #112 model input register
def model_inputs(tenant: str, project: str, rows: list) -> dict:
    """The energy-model INPUT register (#112): [{param, value, unit, source}] with every source named.
    EnergyPlus is NOT run here - the input set is the deliverable, the modeller runs and owns it."""
    clean = []
    for r in (rows or []):
        if not isinstance(r, dict) or not str(r.get("param", "")).strip():
            continue
        if not str(r.get("source", "")).strip():
            raise CstError(f"Param '{r.get('param')}' ka SOURCE bataiye - assumption bina source ke "
                           "register mein nahi ghusta.")
        clean.append({"param": str(r.get("param"))[:80], "value": str(r.get("value"))[:60],
                      "unit": str(r.get("unit", ""))[:20], "source": str(r.get("source"))[:160]})
    if not clean:
        raise CstError("Input rows bhejo [{param, value, unit, source}].")
    return {"rows": clean,
            "say": f"Model input register: {len(clean)} parameters, sab source ke saath. EnergyPlus "
                   "YAHAN nahi chalta - yeh input set modeller ke liye hai; results bhi wahi explain "
                   "karega (not certified here)."}


# ---------------------------------------------------------------- #114 embodied carbon
def carbon_add(tenant: str, project: str, material: str, qty: float, unit: str, factor_kgco2e: float,
               factor_source: str) -> dict:
    """One embodied-carbon row (#114): qty x EPD factor - the factor's source is REQUIRED (an EPD or
    an LCA database, named). No remembered factors."""
    if not str(material or "").strip() or _num(qty) <= 0 or _num(factor_kgco2e) <= 0:
        raise CstError("Material, qty aur factor bataiye (sab > 0).")
    if not str(factor_source or "").strip():
        raise CstError("Factor ka SOURCE bataiye (EPD no / LCA database + row) - bina source ka factor "
                       "carbon number nahi banta.")
    kg = round(_num(qty) * _num(factor_kgco2e), 1)
    with _LOCK, session() as s:
        x = CgrCarbon(tenant_id=tenant, project=project.strip()[:160], material=material.strip()[:120],
                      qty=_num(qty), unit=unit.strip()[:12], factor_kgco2e=_num(factor_kgco2e),
                      factor_source=factor_source.strip()[:200], kgco2e=kg)
        s.add(x)
        s.flush()
        cid = x.id
    return {"row_id": cid, "kgco2e": kg,
            "say": f"Carbon row: {material.strip()} {_num(qty):g} {unit} x {_num(factor_kgco2e):g} "
                   f"kgCO2e = {kg:,.0f} kgCO2e (factor: {factor_source.strip()[:40]}). "
                   "Hot-spot list isi se."}


def carbon_hotspots(tenant: str, project: str) -> dict:
    """The hot-spot list (#114): rows sorted by kgCO2e, share % - a working paper, the LCA assessor
    decides."""
    with session() as s:
        rows = s.scalars(select(CgrCarbon).where(CgrCarbon.tenant_id == tenant,
                                                 CgrCarbon.project == project)).all()
    if not rows:
        raise CstError(f"'{project}' ke carbon rows nahi - carbon_add se jodo (factor sources ke saath).")
    total = sum(r.kgco2e for r in rows) or 1.0
    ranked = sorted(({"material": r.material, "kgco2e": r.kgco2e,
                      "share_pct": round(r.kgco2e / total * 100.0, 1),
                      "factor_source": r.factor_source[:60]} for r in rows),
                    key=lambda r: -r["kgco2e"])
    return {"total_kgco2e": round(total, 1), "rows": ranked,
            "say": f"Embodied carbon ({project}): {total:,.0f} kgCO2e total, top hot-spot "
                   f"'{ranked[0]['material']}' ({ranked[0]['share_pct']}%). Yeh hot-spot list hai - "
                   "LCA assessment assessor karta hai."}


# ---------------------------------------------------------------- #115 water / rainwater
def water_demand(tenant: str, project: str, name: str, occupants: float, state: str = "india") -> dict:
    """Demand (#115): occupants x CPHEEO per-capita (the national pack row) -> KLD, cited."""
    if _num(occupants) <= 0:
        raise CstError("Occupants bataiye (> 0).")
    r = SP.rule_cited(state, "cpheeo_lpcd")
    kld = round(_num(occupants) * float(r["value"]) / 1000.0, 2)
    return {"kld": kld, "occupants": _num(occupants), "lpcd": float(r["value"]),
            "is_ref": f"{r['clause']} ({r['source'][:60]})",
            "say": f"Water demand ({name}): {kld:,.2f} KLD ({r['clause'][:60]}). STP sizing aur plumbing "
                   "design consultant ka - yeh demand ka hisaab hai."}


def rwh(tenant: str, project: str, name: str, roof_m2: float, runoff_coeff: float, rainfall_mm: float,
        rain_source: str) -> dict:
    """Rainwater harvest potential (#115): roof x runoff coefficient x rainfall / 1000 -> m3/yr.
    The coefficient and the IMD station are HERS, recorded with the number."""
    if _num(roof_m2) <= 0 or _num(rainfall_mm) <= 0:
        raise CstError("Roof area aur annual rainfall bataiye (sab > 0).")
    if not 0.0 < _num(runoff_coeff) <= 1.0:
        raise CstError("Runoff coefficient 0-1 ke beech bataiye (jaise concrete ~0.9, tile ~0.8 - "
                       "aapki value, aapka source).")
    if not str(rain_source or "").strip():
        raise CstError("Rainfall ka SOURCE bataiye (IMD station / year) - bina source ki barish "
                       "harvest nahi banati.")
    m3 = round(_num(roof_m2) * _num(runoff_coeff) * _num(rainfall_mm) / 1000.0, 1)
    return {"harvest_m3_yr": m3, "roof_m2": _num(roof_m2), "runoff_coeff": _num(runoff_coeff),
            "rainfall_mm": _num(rainfall_mm), "rain_source": rain_source.strip()[:160],
            "formula": "roof x runoff_coeff x mm / 1000",
            "say": f"RWH ({name}): ~{m3:,.0f} m3/yr (roof {_num(roof_m2):g} x coeff {_num(runoff_coeff):g} "
                   f"x {_num(rainfall_mm):g} mm - {rain_source.strip()[:40]}). Recharge / storage ka "
                   "design consultant ka."}


# ---------------------------------------------------------------- #110 green-rating credits
def credit_add(tenant: str, project: str, rating: str, credit: str, points_available: float,
               points_claimed: float, evidence_ref: str = "", status: str = "claimed") -> dict:
    """A credit row (#110): IGBC | GRIHA | LEED - HER points claimed with the evidence reference;
    the score is a sum, the rating is the assessor's."""
    if rating not in ("IGBC", "GRIHA", "LEED"):
        raise CstError("rating: IGBC | GRIHA | LEED")
    if not str(credit or "").strip() or _num(points_available) <= 0:
        raise CstError("Credit ka naam aur available points bataiye.")
    if _num(points_claimed) > _num(points_available):
        raise CstError(f"Claimed ({_num(points_claimed):g}) > available ({_num(points_available):g}) - "
                       "credit ke points check karo.")
    if status not in ("planned", "claimed", "denied"):
        raise CstError("status: planned | claimed | denied")
    with _LOCK, session() as s:
        x = CgrCredit(tenant_id=tenant, project=project.strip()[:160], rating=rating,
                      credit=credit.strip()[:80], points_available=_num(points_available),
                      points_claimed=_num(points_claimed), evidence_ref=evidence_ref.strip()[:160],
                      status=status)
        s.add(x)
        s.flush()
        cid = x.id
    return {"credit_id": cid,
            "say": f"Credit row: {rating} '{credit.strip()}' {_num(points_claimed):g}/"
                   f"{_num(points_available):g} ({status}"
                   + (f", evidence: {evidence_ref.strip()[:40]}" if evidence_ref else "") + ")."}


def credits_score(tenant: str, project: str) -> dict:
    """The score by rating: claimed vs available - a SUM on her rows; the certification is the
    assessor's (tier C refusal rides the gate)."""
    with session() as s:
        rows = s.scalars(select(CgrCredit).where(CgrCredit.tenant_id == tenant,
                                                 CgrCredit.project == project)).all()
    if not rows:
        raise CstError(f"'{project}' ke credit rows nahi - credit_add se jodo.")
    by: dict[str, dict] = {}
    for r in rows:
        b = by.setdefault(r.rating, {"claimed": 0.0, "available": 0.0, "rows": 0, "no_evidence": 0})
        b["claimed"] += r.points_claimed
        b["available"] += r.points_available
        b["rows"] += 1
        b["no_evidence"] += 0 if (r.evidence_ref or r.status == "planned") else 1
    for b in by.values():
        b["pct"] = round(b["claimed"] / b["available"] * 100.0, 1) if b["available"] else 0.0
    return {"ratings": by,
            "say": (f"Credit score ({project}): "
                    + "; ".join(f"{k} {v['claimed']:g}/{v['available']:g} ({v['pct']}%)" for k, v in by.items())
                    + ". Sum AAPKI claimed rows ka hai - rating assessor decide karta hai.")}


# ---------------------------------------------------------------- #116 commissioning
def cx_add(tenant: str, project: str, system: str, test: str, steps: list, season: str = "first") -> dict:
    """A commissioning item (#116): the functional test SCRIPT steps as data; the sign-off is the Cx
    authority's (tier C)."""
    if not str(system or "").strip() or not str(test or "").strip():
        raise CstError("System aur test bataiye (jaise 'Chilled water loop', 'Flow > design x 1.1').")
    if season not in ("first", "seasonal"):
        raise CstError("season: first | seasonal")
    clean = [str(s_).strip()[:200] for s_ in (steps or []) if str(s_).strip()]
    if not clean:
        raise CstError("Test ke steps bhejo (list) - script bina steps ke script nahi hoti.")
    with _LOCK, session() as s:
        x = CgrCx(tenant_id=tenant, project=project.strip()[:160], system=system.strip()[:120],
                  test=test.strip()[:200], steps=_dump(clean), season=season)
        s.add(x)
        s.flush()
        cid = x.id
    return {"cx_id": cid, "steps": len(clean),
            "say": f"Cx item: {system.strip()} - '{test.strip()}' ({len(clean)} steps, {season}). "
                   "Sign-off Cx authority ka - Hoola script aur log rakhta hai."}


def cx_issue(tenant: str, cx_id: str, severity: str, note: str) -> dict:
    """An issue off a Cx test: severity + note, the log the Cx authority reviews."""
    if severity not in ("minor", "major", "critical"):
        raise CstError("severity: minor | major | critical")
    if not str(note or "").strip():
        raise CstError("Issue ka note bataiye.")
    with _LOCK, session() as s:
        x = s.get(CgrCx, cx_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Cx item nahi mila.")
        iss = CgrCxIssue(tenant_id=tenant, cx_id=cx_id, severity=severity, note=note.strip()[:300])
        s.add(iss)
        s.flush()
        iid, sysname = iss.id, x.system
    return {"issue_id": iid,
            "say": f"Cx issue ({sysname}): {severity} - '{note.strip()[:60]}'."}


def cx_status(tenant: str, cx_id: str, status: str) -> dict:
    """Planned | done | failed - the test RAN (a person ran it); the record follows."""
    if status not in ("planned", "done", "failed"):
        raise CstError("status: planned | done | failed")
    with _LOCK, session() as s:
        x = s.get(CgrCx, cx_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Cx item nahi mila.")
        x.status = status
        sysname = x.system
    return {"say": f"{sysname}: Cx status -> {status} (test insaan ne chalaya, record rakha)."}


# ---------------------------------------------------------------- #117 T&C records
def tc_add(tenant: str, project: str, system: str, cert_no: str, agency: str, tested_on: str,
           as_installed: float, design: float, tolerance_pct: float, unit: str = "") -> dict:
    """A T&C record (#117): the certificate as the agency reported it, as-installed vs design with the
    tolerance arithmetic - ok / exceeds is a number; acceptance is the T&C engineer's."""
    if not str(system or "").strip() or _num(design) <= 0:
        raise CstError("System aur design value bataiye (> 0).")
    if _num(tolerance_pct) <= 0:
        raise CstError("Tolerance % bataiye (spec / agency limit se).")
    dev = round(abs(_num(as_installed) - _num(design)) / _num(design) * 100.0, 2)
    verdict = "ok" if dev <= _num(tolerance_pct) else "exceeds"
    with _LOCK, session() as s:
        x = CgrTc(tenant_id=tenant, project=project.strip()[:160], system=system.strip()[:120],
                  cert_no=cert_no.strip()[:80], agency=agency.strip()[:160],
                  tested_on=(_date(tested_on) or today(tenant)).isoformat(), as_installed=_num(as_installed),
                  design=_num(design), tolerance_pct=_num(tolerance_pct), unit=unit.strip()[:20],
                  dev_pct=dev, verdict=verdict)
        s.add(x)
        s.flush()
        tid = x.id
    return {"tc_id": tid, "dev_pct": dev, "verdict": verdict,
            "say": f"T&C ({system.strip()}): as-installed {_num(as_installed):g} vs design "
                   f"{_num(design):g} {unit} -> {dev:.2f}% deviation vs tolerance {_num(tolerance_pct):g}% "
                   f"-> {'WITHIN (arithmetic)' if verdict == 'ok' else 'EXCEEDS (arithmetic)'}. "
                   "Certificate " + (f"{cert_no.strip()} ({agency.strip()[:30]})" if cert_no else "-")
                   + ". Acceptance T&C engineer ki."}


# ---------------------------------------------------------------- #118 M&V
def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Least-squares y = a + b x with r2 - pure math, printed in the trail."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    b = sxy / sxx if sxx else 0.0
    a = my - b * mx
    r2 = (sxy * sxy) / (sxx * syy) if sxx and syy else 0.0
    return a, b, r2


def mv_add(tenant: str, project: str, option: str, baseline: list, report: list, note: str = "") -> dict:
    """An M&V job (#118): baseline + reporting rows [{driver, kwh}] and HER IPMVP option letter.
    Savings sirf baseline model ke baad."""
    if option not in ("A", "B", "C", "D"):
        raise CstError("IPMVP option: A | B | C | D - aapka option, Hoola ka nahi.")
    bl = [{"driver": _num(r.get("driver")), "kwh": _num(r.get("kwh"))}
          for r in (baseline or []) if isinstance(r, dict) and _num(r.get("kwh")) > 0]
    rp = [{"driver": _num(r.get("driver")), "kwh": _num(r.get("kwh"))}
          for r in (report or []) if isinstance(r, dict) and _num(r.get("kwh")) > 0]
    if len(bl) < 3:
        raise CstError("Baseline ke kam se kam 3 rows chahiye (driver + kwh) - model usi par banta hai.")
    if not rp:
        raise CstError("Reporting period ki rows bhejo [{driver, kwh}].")
    with _LOCK, session() as s:
        x = CgrMv(tenant_id=tenant, project=project.strip()[:160], option=option,
                  baseline=_dump(bl), report=_dump(rp), note=note.strip()[:200])
        s.add(x)
        s.flush()
        mid = x.id
    return {"mv_id": mid, "baseline_rows": len(bl), "report_rows": len(rp),
            "say": f"M&V job ({project}, Option {option}) khuli. Savings mv_savings se - baseline model "
                   "least-squares se, sab printed."}


def mv_savings(tenant: str, mv_id: str) -> dict:
    """The savings arithmetic (#118): the least-squares baseline line through HER rows (a, b, r2 in the
    trail), adjusted baseline = a + b x driver per reporting row, savings = adjusted - actual, summed.
    The verification ROUTINE is IPMVP's - her option named on the record."""
    with session() as s:
        m = s.get(CgrMv, mv_id)
        if not m or m.tenant_id != tenant:
            raise CstError("M&V job nahi mili.")
    bl, rp = _j(m.baseline, []), _j(m.report, [])
    xs = [r["driver"] for r in bl]
    ys = [r["kwh"] for r in bl]
    a, b, r2 = _ols(xs, ys)
    if b <= 0 or r2 < 0.5:
        warn = (f"Model weak (b={b:.4g}, r2={r2:.3f}) - driver ka relationship baseline mein clear "
                "nahi. IPMVP ke hisaab se routine ya data dobara dekho; Hoola number dikhata hai, "
                "model ki pasandigi physicist verify karega.")
    else:
        warn = ""
    per = []
    total = 0.0
    for r in rp:
        adj = a + b * r["driver"]
        sav = adj - r["kwh"]
        total += sav
        per.append({"driver": r["driver"], "actual_kwh": r["kwh"], "adjusted_baseline_kwh": round(adj, 1),
                    "savings_kwh": round(sav, 1)})
    result = {"a": round(a, 4), "b": round(b, 6), "r2": round(r2, 4), "periods": len(per),
              "savings_kwh_total": round(total, 1), "formula": "adj = a + b x driver; savings = adj - actual",
              "option": m.option}
    with _LOCK, session() as s:
        m2 = s.get(CgrMv, mv_id)
        m2.result = _dump(result)
    return {"mv_id": mv_id, "per_period": per, **result, "warn": warn,
            "say": (f"M&V savings (Option {m.option}): baseline model kwh = {a:.1f} + {b:.4g} x driver "
                    f"(r2 {r2:.3f}); {len(per)} periods, total savings {total:,.0f} kWh. "
                    + (warn + " " if warn else "")
                    + "Savings verified - routine IPMVP ki, option AAPKA; audit certified auditor ka.")}


def day(tenant: str) -> dict:
    """The performance morning: meters due-ish, open Cx issues, exceeding T&C rows, credit shortfall."""
    with session() as s:
        meters = s.scalars(select(CgrMeter).where(CgrMeter.tenant_id == tenant)).all()
        issues = s.scalars(select(CgrCxIssue).where(CgrCxIssue.tenant_id == tenant,
                                                    CgrCxIssue.status == "open")).all()
        tcs = s.scalars(select(CgrTc).where(CgrTc.tenant_id == tenant)).all()
        credits = s.scalars(select(CgrCredit).where(CgrCredit.tenant_id == tenant)).all()
    exceeds = sum(1 for t in tcs if t.verdict == "exceeds")
    no_evidence = sum(1 for c in credits if not c.evidence_ref and c.status == "claimed")
    return {"meters": len(meters), "cx_issues_open": len(issues), "tc_exceeds": exceeds,
            "credits_without_evidence": no_evidence,
            "say": f"Performance desk: {len(meters)} readings, {len(issues)} open Cx issues, {exceeds} "
                   f"T&C rows tolerance se bahar, {no_evidence} credits bina evidence. Har verdict "
                   "arithmetic hai - har certification insaan ki."}
