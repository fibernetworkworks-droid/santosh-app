"""v0.458 IS THE CAD ENGINEER ALIVE ON THIS SERVER? `python -m app.engineering check`

Every other desk can be asked this from the VPS (game_check, architect_check, lab_check, auth_check); the CAD desk
could not. All it had was `health()`, which only says whether three libraries IMPORT - and an importable library is
not a working desk. This runs the real thing instead: it BUILDS real parts through the same sandbox a real job goes
through, runs every study on them, and prints one line per stage saying `live` with the number it measured, or
`DEAD` with the reason.

It exists because this has already bitten her once: every test here was green while her own server answered
`fea false` - the stress engine was simply not installed. Nothing stopped the same thing happening again with
mujoco (the motion simulation), matplotlib (the charts) or reportlab (the drawing and the report), each of which
fails QUIETLY: the part still builds, the answer just silently stops carrying that piece.

No model is called, so a run costs nothing. Four builds + the studies, about 2-5 minutes (`--quick` drops the
slowest one). `DEAD` anywhere means that part of what Hoola tells her about a design is not actually running.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from . import sandbox

# The libraries the desk really needs, and what dies without each one - said in her terms, not the package's.
LIBS = [
    ("cadquery", "the parts themselves: nothing can be built at all"),
    ("OCP", "the CAD kernel under CadQuery (volumes, fillets, STEP)"),
    ("numpy", "every measurement and every solver"),
    ("scipy", "the solvers under the stress / motion checks"),
    ("skfem", "stress, heat, vibration, buckling and the permanent-bend check"),
    ("pyamg", "the fast stress solver (without it the slow direct solve is used)"),
    ("mujoco", "the motion simulation: motor torque, friction, backlash, cam contact"),
    ("matplotlib", "the cam and motor charts in the report"),
    ("reportlab", "the dimensioned drawing sheet and the analysis PDF"),
]
SOFT = {"pyamg", "mujoco", "matplotlib"}            # these degrade quietly instead of stopping the build

PART = """import cadquery as cq
plate = cq.Workplane('XY').box(120, 60, 14, centered=(False, True, False))
plate = plate.edges('|Z').fillet(6)
plate = (plate.faces('>Z').workplane(centerOption='CenterOfBoundBox')
         .pushPoints([(-40, 18), (-40, -18), (40, 18), (40, -18)]).hole(H.hole(6, 'clearance')))
plate = plate.faces('>Z').workplane(centerOption='CenterOfBoundBox').pushPoints([(0, 0)]).hole(10.0)
H.fit(10, 'H8')
H.drawing(projection='first', tolerance='m', part_no='HOOLA-CHECK-1')
H.expect(size=(120, 60, 14), solids=1, holes={'d': H.hole(6, 'clearance'), 'count': 4})
H.make('cnc', tool_d=6)
H.cam(tool_d=6, stepdown=2, stepover=0.45, ops=['profile', 'drill'])
result = plate
"""

GEARS = """import cadquery as cq
pinion = H.spur_gear(2.0, 20, 18, bore=10)
wheel = H.spur_gear(2.0, 60, 18, bore=16).translate((80, 0, 0))
H.gear_duty(2.0, 20, 60, 18, torque_Nm=22, rpm=1200, application='medium shock', quality=8, life_hours=20000,
            min_sf=1.4)
result = cq.Assembly(name='gearbox').add(pinion, name='pinion').add(wheel, name='wheel')
"""

MACHINE = """import cadquery as cq
base = cq.Workplane('XY').box(170, 170, 10, centered=(True, True, False)).translate((0, 0, -14))
mast = cq.Workplane('XY').box(26, 26, 70, centered=(True, True, False)).translate((-60, 0, -4))
camw = H.disc_cam('timing', [{'type': 'rise', 'lift': 9, 'deg': 120, 'law': 'cycloidal'},
                             {'type': 'dwell', 'deg': 60},
                             {'type': 'return', 'lift': 9, 'deg': 120, 'law': 'cycloidal'},
                             {'type': 'dwell', 'deg': 60}],
                 base_radius=28, roller_radius=6, rpm=150, thickness=12, bore=10,
                 cam_joint='cam_spin', follower_joint='lift', guide_mu=0.1, guide_len=30, overhang=10)
rod = cq.Workplane('XY').box(10, 56, 10, centered=(True, False, True)).translate((0, 34, 0))
# the arm swings about a HORIZONTAL axis, so it has to be LIFTED against gravity - otherwise every torque in the
# move comes out as zero and the check proves nothing
arm = cq.Workplane('XY').box(100, 16, 10, centered=(False, True, True)).translate((-60, 0, 50))
H.joint('cam_spin', 'base', 'cam', kind='continuous', origin=(0, 0, 0), axis=(0, 0, 1), bearing='ball', pin_d=10)
H.joint('lift', 'base', 'rod', kind='prismatic', origin=(0, 34, 0), axis=(0, 1, 0), limits=(0, 12), bearing='rail')
H.joint('mast_fix', 'base', 'mast', kind='fixed', origin=(-60, 0, -4), axis=(0, 0, 1))
H.joint('swing', 'mast', 'arm', origin=(-60, 0, 50), axis=(0, 1, 0), limits=(-80, 80), bearing='bush', pin_d=12)
H.robot(name='hoola_check', move_time_s=1.0, payload={'part': 'arm', 'kg': 0.5, 'at': (40, 0, 50)},
        accuracy_mm=0.5)
result = (cq.Assembly(name='machine').add(base, name='base').add(mast, name='mast').add(camw, name='cam')
          .add(rod, name='rod').add(arm, name='arm'))
"""


def libs() -> list[dict[str, Any]]:
    """Is each library importable BY THE BOX's own python (not this process)? That is the one that matters."""
    out = []
    for name, why in LIBS:
        ok = sandbox.installed(name)
        out.append({"lib": name, "ok": ok, "soft": name in SOFT, "why": why})
    return out


def _build(work: Path, name: str, code: str, material: str, timeout: int) -> dict[str, Any]:
    d = work / name
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        r = sandbox.run(d, code, timeout=timeout, material=material)
    except Exception as e:
        return {"ok": False, "errors": [f"{type(e).__name__}: {str(e)[:300]}"], "dir": d, "secs": 0.0}
    r["dir"] = d
    r["secs"] = round(time.time() - t0, 1)
    return r


def _studies(d: Path, studies: list, cam: dict | None, timeout: int) -> dict[str, Any]:
    try:
        return sandbox.analyse(d, studies, cam, timeout=timeout)
    except Exception as e:
        return {"ok": False, "errors": [f"{type(e).__name__}: {str(e)[:300]}"], "studies": []}


def _err(r: dict) -> str:
    e = r.get("errors") or []
    return (e[0] if e else "no reason given")[:200]


def check(quick: bool = False) -> list[dict[str, Any]]:
    """The whole desk, stage by stage, on THIS machine. Each row: name, ok, say (the measured evidence)."""
    rows: list[dict[str, Any]] = []

    def row(name: str, ok: bool | None, say: str, soft: bool = False) -> None:
        rows.append({"stage": name, "ok": ok, "say": say, "soft": soft})

    have = {x["lib"]: x["ok"] for x in libs()}
    for x in libs():
        row(f"library {x['lib']}", x["ok"], ("there" if x["ok"] else f"MISSING - without it: {x['why']}"),
            soft=x["soft"])
    row("the box's python", True, sandbox.python())
    iso = sandbox.net_isolation()
    row("box has no network", iso, "unshare -rn works, the script cannot reach out"
        if iso else "this VPS has no unshare: the runner's own lockdown is what holds (v0.361)", soft=True)
    if not have.get("cadquery"):
        row("everything else", False, "cadquery is missing, so nothing can be built - run cad_setup first")
        return rows

    work = Path(tempfile.mkdtemp(prefix="hoola-cad-check-"))
    try:
        # ---------------------------------------------------------------- 1. a real part, with its drawing and G-code
        p = _build(work, "part", PART, "aluminium", 420)
        if not p.get("ok"):
            row("build a part", False, f"the bracket did not build: {_err(p)}")
        else:
            bb = p.get("bbox") or {}
            row("build a part", True, f"bracket {bb.get('x')} x {bb.get('y')} x {bb.get('z')} mm, "
                f"{p.get('volume_mm3', 0):,.0f} mm3, {p.get('faces', 0)} faces, {p['secs']}s")
            files = {f for f in (p.get("exported") or [])}
            want = {"part.step", "part.stl", "part.glb"}
            row("files out (STEP / STL / GLB)", want <= files, ", ".join(sorted(files)) or "none")
            exp = p.get("expect") or []
            row("her own numbers measured (H.expect)", bool(exp) and all(e.get("ok") for e in exp),
                "; ".join(f"{e.get('name')}: {e.get('got')}" for e in exp) or "nothing came back")
            d = p.get("dfm") or {}
            row("made-how checks (DFM, cnc)", bool(d.get("rows")),
                f"{len(d.get('rows') or [])} checks, {d.get('fails', 0)} fail, {d.get('reviews', 0)} to look at"
                if d.get("rows") else "no DFM rows came back")
            hlr = (work / "part" / "hlr.json")
            nviews = len(json.loads(hlr.read_text(encoding="utf-8"))) if hlr.exists() else 0
            row("hidden-line views for the drawing", nviews >= 3, f"{nviews} views")
            # the studies on that same part: stress + buckling (+ the permanent-bend check unless --quick)
            if not have.get("skfem"):
                row("stress / buckling / past-yield", False,
                    "scikit-fem is MISSING: the whole strength side is dead - run cad_setup")
            else:
                st = [{"kind": "static", "material": "aluminium", "fixed": "<X", "nodes": 1500, "converge": False,
                       "loads": [{"faces": ">X", "force": [0, 0, -900]}], "min_sf": 2},
                      {"kind": "buckling", "material": "aluminium", "fixed": "<Z", "nodes": 1200, "converge": False,
                       "loads": [{"faces": ">Z", "force": [0, 0, -4000]}], "min_lf": 2}]
                if not quick:
                    st.append({"kind": "plastic", "material": "aluminium", "fixed": "<X", "nodes": 900,
                               "max_factor": 1.3, "max_set_mm": 0.3,
                               "loads": [{"faces": ">X", "force": [0, 0, -2500]}]})
                a = _studies(work / "part", st, (p.get("cam") or [None])[0], 1500)
                got = {s.get("kind"): s for s in (a.get("studies") or [])}
                s1 = got.get("static") or {}
                row("stress (FEA static)", bool(s1.get("ok")),
                    f"peak {s1.get('peak_vm_away_MPa')} MPa, safety {s1.get('safety_factor')}, "
                    f"{(s1.get('mesh') or {}).get('nodes')} nodes, equilibrium error "
                    f"{s1.get('equilibrium_error_pct')} %, {s1.get('seconds')}s"
                    if s1.get("ok") else f"did not run: {str(s1.get('error') or _err(a))[:160]}")
                s2 = got.get("buckling") or {}
                row("buckling (does it FOLD)", bool(s2.get("ok")),
                    f"load factor {s2.get('load_factor')}, governs: {s2.get('governs')}, {s2.get('seconds')}s"
                    if s2.get("ok") else f"did not run: {str(s2.get('error') or _err(a))[:160]}")
                if quick:
                    row("past yield (permanent bend)", None, "skipped by --quick (it is the slow one)")
                else:
                    s3 = got.get("plastic") or {}
                    hl = s3.get("at_her_load") or {}
                    row("past yield (permanent bend)", bool(s3.get("ok")),
                        f"first yields at x{s3.get('first_yield_factor')}, permanent set "
                        f"{hl.get('permanent_set_mm')} mm, carries up to x{s3.get('carries_up_to')}, "
                        f"{s3.get('seconds')}s" if s3.get("ok")
                        else f"did not run: {str(s3.get('error') or _err(a))[:160]}")
                cm = a.get("cam") or {}
                row("CNC G-code", bool(cm.get("ok")),
                    f"{', '.join(cm.get('ops') or [])}, {cm.get('lines', 0):,} lines, {cm.get('minutes')} min"
                    if cm.get("ok") else f"did not run: {str(cm.get('error') or '-')[:160]}")

        # ---------------------------------------------------------------- 2. gears: the real hobbed root + ISO 6336
        g = _build(work, "gears", GEARS, "case hardened steel", 420)
        if not g.get("ok"):
            row("gears", False, f"the pair did not build: {_err(g)}")
        else:
            gr = (g.get("gears") or [{}])[0]
            row("gear teeth drawn (real hobbed root)", bool(g.get("gears")),
                f"{len(g.get('gears') or [])} gears, pinion {gr.get('teeth')}T module {gr.get('module')}, "
                f"undercut: {gr.get('undercut')}")
            gd = (g.get("gear_duty") or [{}])[0]
            ok_gd = bool(gd) and not gd.get("error")
            row("will the teeth last (ISO 6336)", ok_gd,
                f"bending safety {gd.get('bending_sf')}, pitting safety {gd.get('pitting_sf')}, "
                f"contact ratio {gd.get('contact_ratio')}, {len(gd.get('rows') or [])} checks"
                if ok_gd else f"did not run: {str(gd.get('error') or 'no duty came back')[:160]}")

        # ---------------------------------------------------------------- 3. a machine that MOVES
        m = _build(work, "machine", MACHINE, "steel", 900)
        if not m.get("ok"):
            row("build a machine (joints + cam)", False, f"did not build: {_err(m)}")
        else:
            k = m.get("kinematics") or {}
            if not k.get("ok"):
                row("mechanism solved", False, "; ".join(k.get("problems") or ["no kinematics came back"])[:200])
            else:
                row("mechanism solved", True, f"{len(k.get('joints') or [])} joints, "
                    f"{len(k.get('range') or [])} ranges swept, driven by "
                    f"{', '.join(k.get('drivers') or []) or 'the independent joints'}"
                    + (f", loops {', '.join(k['loops'])}" if k.get("loops") else ""))
                u = k.get("urdf") or {}
                bad = [r["check"] for r in (u.get("rows") or []) if not r.get("ok")]
                row("robot files (URDF / SDF / MJCF / SRDF)", not bad,
                    f"{u.get('links')} links, {u.get('joints')} joints, "
                    f"{len(u.get('rows') or [])} checks" + (f", failing: {', '.join(bad)}" if bad else ""))
                dyn = k.get("dynamics") or {}
                if dyn.get("ok") is None:
                    row("the machine MOVES (MuJoCo)", False,
                        f"not run: {dyn.get('note') or 'mujoco missing'} - the motor torque, friction and backlash "
                        "numbers are all silently absent", soft=True)
                elif not dyn.get("rows"):
                    row("the machine MOVES (MuJoCo)", False, str(dyn.get("note"))[:180])
                else:
                    r0 = max(dyn["rows"], key=lambda x: abs(x.get("peak") or 0))
                    cam_t = next((x.get("cam_peak") for x in dyn["rows"] if x.get("cam_peak") is not None), None)
                    row("the machine MOVES (MuJoCo)", bool(abs(r0.get("peak") or 0) > 0),
                        f"{len(dyn['rows'])} motors, hardest worked {r0['joint']} peak {r0['peak']} {r0['unit']} "
                        f"at {r0['peak_speed']} {r0['speed_unit']}"
                        + (f", cam shaft {cam_t} N·m" if cam_t is not None else "")
                        + f", loop gap {dyn.get('loop_gap_m')} m, move {dyn.get('move_time_s')}s"
                        if abs(r0.get("peak") or 0) > 0 else
                        "every motor came back at zero torque - the simulation ran but loaded nothing")
                    row("friction in the move", bool(dyn.get("friction")),
                        f"{len(dyn.get('friction') or [])} joints, "
                        f"{dyn.get('friction_share_pct')} % of the motors' work lost"
                        if dyn.get("friction") else "no friction rows (bearings were named in the script)")
                ct = (k.get("cam_contact") or {}).get("timing") or {}
                row("cam contact (spring / Hertz / jam)", bool(ct.get("rows")),
                    f"spring {ct.get('spring_k_n_mm')} N/mm, min push {ct.get('min_push_n')} N, "
                    f"Hertz {ct.get('max_hertz_mpa')} MPa (limit {ct.get('allow_mpa')}), from {ct.get('force_from')}"
                    if ct.get("rows") else "no contact rows came back")
            cams = m.get("cams") or {}
            row("cam designed from the motion", bool(cams),
                f"{len(cams)} cam(s), {len(((cams.get('timing') or {}).get('rows')) or [])} checks, "
                f"lift {(cams.get('timing') or {}).get('lift')} mm" if cams else "no cam came back")

        # ---------------------------------------------------------------- 4. the drawing sheet and the report (PDF)
        rows += _papers(work, have, p if p.get("ok") else None)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---------------------------------------------------------------- 5. the calculator, the charts, the wiring
    rows += _calc_rows()
    rows += _chart_rows(have)
    rows += _wiring_rows()
    return rows


def _papers(work: Path, have: dict, part: dict | None) -> list[dict[str, Any]]:
    out = []
    if not have.get("reportlab"):
        return [{"stage": "drawing sheet + report PDF", "ok": False, "soft": False,
                 "say": "reportlab is MISSING: she gets no dimensioned drawing and no analysis report"}]
    if not part:
        return [{"stage": "drawing sheet + report PDF", "ok": None, "soft": False,
                 "say": "skipped: the part did not build"}]
    try:
        from . import drawing as dwg
        d = work / "part"
        dj = d / "drawing.json"
        if not dj.exists():
            return [{"stage": "dimensioned drawing sheet (PDF)", "ok": False, "soft": False,
                     "say": "the build made no drawing.json: the hidden-line / dimension stage did not run"}]
        data = json.loads(dj.read_text(encoding="utf-8"))
        ds = part.get("drawing") or {}
        pdf = dwg.make(data, {"title": "Hoola CAD check", "material": "aluminium", "mass_g": 400, "version": 1,
                              "pid": "check", "fits": ds.get("fits"), "tolerance": ds.get("tolerance"),
                              "notes": ds.get("notes"), "part_no": ds.get("part_no")}, None)
        ok = isinstance(pdf, (bytes, bytearray)) and bytes(pdf[:4]) == b"%PDF" and len(pdf) > 4000
        nd = len(data.get("dims") or []) or len(data.get("views") or {})
        out.append({"stage": "dimensioned drawing sheet (PDF)", "ok": ok, "soft": False,
                    "say": f"{len(pdf):,} bytes, {nd} dimensioned items, fits {len(ds.get('fits') or [])}"
                           if ok else f"came back {len(pdf) if pdf else 0} bytes, not a usable PDF"})
    except Exception as e:
        out.append({"stage": "dimensioned drawing sheet (PDF)", "ok": False, "soft": False,
                    "say": f"{type(e).__name__}: {str(e)[:170]}"})
    return out


def _calc_rows() -> list[dict[str, Any]]:
    """The hand calculations: every kind answers, with a number anyone can check."""
    from . import calc
    want = [("fit", {"size": 20, "fit": "H7/g6"}, "clearance_mm"),
            ("bolt", {"m": 10, "grade": "8.8", "count": 4, "tension_N": 9000}, "torque_Nm"),
            ("weld", {"force_N": 12000, "length_mm": 60, "leg_mm": 5}, "utilisation"),
            ("beam", {"support": "cantilever", "length_mm": 300, "section": {"type": "rect", "b": 20, "h": 10},
                      "load_N": 200}, "max_deflection_mm"),
            ("pipe", {"flow_lpm": 30, "diameter_mm": 25, "length_m": 12}, "pressure_drop_Pa"),
            ("joint", {"m": 12, "grade": "8.8", "grip_mm": 30, "load_N": 15000}, "load_factor_C"),
            ("fatigue", {"sigma_max_MPa": 180, "sigma_min_MPa": 0}, "fatigue_sf"),
            ("column", {"length_mm": 300, "section": {"type": "rect", "b": 10, "h": 10}, "ends": "cantilever",
                        "load_N": 1000}, "critical_load_N"),
            ("gear", {"module": 3.0, "pinion_teeth": 20, "wheel_teeth": 60, "width_mm": 25, "torque_Nm": 40,
                      "rpm": 900, "material": "case hardened"}, "bending_sf")]
    bad, shown = [], []
    for kind, args, key in want:
        try:
            r = calc.run(kind, args)
            if r.get(key) is None:
                raise ValueError(f"{key} missing")
            shown.append(f"{kind} {r[key]}")
        except Exception as e:
            bad.append(f"{kind}: {type(e).__name__}")
    return [{"stage": "hand calculations (eng_calc)", "ok": not bad, "soft": False,
             "say": f"{len(want) - len(bad)}/{len(want)} answered ({', '.join(shown[:4])} ...)"
                    + (f"; FAILING: {', '.join(bad)}" if bad else "")}]


def _chart_rows(have: dict) -> list[dict[str, Any]]:
    if not have.get("matplotlib"):
        return [{"stage": "charts in the report", "ok": False, "soft": True,
                 "say": "matplotlib is MISSING: the cam curve and motor-torque charts are quietly left out"}]
    try:
        from . import report
        cams = {"c": {"rpm": 60, "curve": {"deg": [0, 90, 180, 270], "s": [0, 5, 10, 5],
                                           "v": [0, 1, 0, -1], "a": [0, 0.1, 0, -0.1]}}}
        png = report.cam_curve_png(cams)
        dyn = report.dynamics_png({"t": [0, 0.5, 1.0], "tau": {"j1": [0.0, 1.2, 0.4]}})
        ok = png[:4] == b"\x89PNG" and dyn[:4] == b"\x89PNG"
        return [{"stage": "charts in the report", "ok": ok, "soft": True,
                 "say": f"cam curve {len(png):,} bytes, motor torque {len(dyn):,} bytes"}]
    except Exception as e:
        return [{"stage": "charts in the report", "ok": False, "soft": True,
                 "say": f"{type(e).__name__}: {str(e)[:170]}"}]


def _wiring_rows() -> list[dict[str, Any]]:
    """Is the desk REACHABLE? A working engine nobody can call is the v0.393 lesson."""
    out = []
    try:
        from app.agent.tools import FAMILY_OF, HANDLERS
        ok = FAMILY_OF.get("cad_part") == "eng" and "cad_part" in HANDLERS and "eng_calc" in HANDLERS
        out.append({"stage": "the agent can call the desk", "ok": ok, "soft": False,
                    "say": "cad_part + eng_calc registered in the agent's tools"
                           if ok else "cad_part / eng_calc NOT registered - the model cannot reach the desk"})
    except Exception as e:
        out.append({"stage": "the agent can call the desk", "ok": False, "soft": False,
                    "say": f"{type(e).__name__}: {str(e)[:170]}"})
    try:
        from .ai import GUIDE
        marks = ["H.analyze('buckling'", "H.gear_duty", "H.analyze('plastic'", "H.disc_cam", "H.make("]
        miss = [m for m in marks if m not in GUIDE]
        out.append({"stage": "the designer's guide carries every feature", "ok": not miss, "soft": False,
                    "say": f"{len(GUIDE):,} characters, all {len(marks)} markers present"
                           if not miss else f"MISSING from the guide: {', '.join(miss)}"})
    except Exception as e:
        out.append({"stage": "the designer's guide carries every feature", "ok": False, "soft": False,
                    "say": f"{type(e).__name__}: {str(e)[:170]}"})
    return out


def verdict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    live = [r for r in rows if r.get("ok") is True]
    dead = [r for r in rows if r.get("ok") is False and not r.get("soft")]
    weak = [r for r in rows if r.get("ok") is False and r.get("soft")]
    skip = [r for r in rows if r.get("ok") is None]
    return {"live": len(live), "dead": len(dead), "degraded": len(weak), "skipped": len(skip),
            "total": len(rows), "ok": not dead,
            "dead_stages": [r["stage"] for r in dead], "degraded_stages": [r["stage"] for r in weak]}


def report_lines(quick: bool = False) -> list[str]:
    t0 = time.time()
    rows = check(quick=quick)
    v = verdict(rows)
    lines = [f"HOOLA CAD ENGINEER on this server{' (--quick)' if quick else ''}", "=" * 72]
    for r in rows:
        mark = "live" if r["ok"] is True else ("off " if r["ok"] is None else ("WEAK" if r.get("soft") else "DEAD"))
        lines.append(f"[{mark}] {r['stage']}: {r['say']}")
    lines += ["=" * 72,
              f"{v['live']} live, {v['dead']} DEAD, {v['degraded']} degraded, {v['skipped']} skipped "
              f"of {v['total']} - {round(time.time() - t0, 1)}s"]
    if v["dead"]:
        lines.append("GADBAD: " + ", ".join(v["dead_stages"]))
        lines.append("-> run the vps-ops job cad_setup, then this again. Until it is clean, what Hoola tells her "
                     "about a design is missing those pieces.")
    elif v["degraded"]:
        lines.append("Chalega, but degraded: " + ", ".join(v["degraded_stages"])
                     + " -> cad_setup installs these; nothing breaks without them, the answer just carries less.")
    else:
        lines.append("Sab live: every piece of the CAD desk ran on this machine.")
    return lines
