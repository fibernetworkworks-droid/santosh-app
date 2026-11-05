"""C13a: the Survey & measurement desk (register #22 Land Survey Data Processor, #23 Drone Survey &
Photogrammetry Processor, #24 Laser Scan / Point-cloud Reality Capture Assistant, #26 RERA Carpet-area
Measurement Assistant) - Wave 3, v0.550.0, plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md §7.

What Hoola actually reads, said on every output:
- LandXML is read as TEXT for its CgPoints (id + E/N/Z) - surfaces and observations are NOT parsed and
  the desk says so; plain coordinate rows ride the same path.
- the drone/photogrammetry numbers are THE SURVEY LEAD'S readings: Hoola does the volume arithmetic on
  the elevations she feeds (average-height grid method) and the progress comparison on the areas she
  reads off the orthomosaic. The orthomosaic itself is never interpreted here.
- the point-cloud desk does NOT parse E57/LAS binaries: exported CSV points in, deviations out,
  registration QA as the RMS of the residuals she feeds - honest about the format, always.
- the RERA carpet-area statement computes from HER room rows (each read off the plan by a human) under
  HER recorded wall policy, checks the declared area against the tolerance row, and prints the
  discrepancy report with the sign line EMPTY. Certification (RERA s.2(k) statements, survey
  certificates) stays with the project architect / CE / licensed surveyor (tier C)."""
from __future__ import annotations

import io
import math
import re

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _dump, _j, _num, today)
from .models import CsurCalc, CsurCarpet, CsurCarpetRoom, CsurJob, CsurPoint
from . import statepacks as SP

_CGPOINT = re.compile(r"<CgPoint[^>]*name=\"([^\"]+)\"[^>]*>\s*([-\d.eE+ ]+)\s*</CgPoint>", re.I)


def _pts(tenant: str, job_id: str) -> dict[str, CsurPoint]:
    with session() as s:
        rows = s.scalars(select(CsurPoint).where(CsurPoint.tenant_id == tenant,
                                                 CsurPoint.job_id == job_id)).all()
    return {r.pid: r for r in rows}


# ---------------------------------------------------------------- jobs & points (#22)
def pts_add(tenant: str, project: str, name: str, source_kind: str, text: str, note: str = "",
            conv: str = "") -> dict:
    """One survey job: coordinate rows 'id,x,y,z' (one per line, metres) or LandXML text - CgPoints
    are read as text; what is NOT read (surfaces, observations) is said out loud."""
    if not str(project or "").strip() or not str(name or "").strip():
        raise CstError("Project aur job ka naam bataiye.")
    if source_kind not in ("coords", "landxml"):
        raise CstError("source_kind: coords | landxml")
    text = str(text or "").strip()
    if not text:
        raise CstError("Points ka text bhejo (coords: 'id,x,y,z' per line; LandXML: CgPoints ka xml).")
    parsed: list[tuple[str, float, float, float]] = []
    if source_kind == "landxml":
        for m in _CGPOINT.finditer(text):
            pid = m.group(1).strip()[:40]
            vals = [float(v) for v in m.group(2).split()]
            if len(vals) >= 2:
                parsed.append((pid, vals[0], vals[1], vals[2] if len(vals) > 2 else 0.0))
        if not parsed:
            raise CstError("LandXML mein CgPoint nahi mile - surfaces/observations parse NAHI hote "
                           "(said on the tin); CgPoints wala text bhejo.")
    else:
        for ln in text.splitlines():
            ln = ln.strip().strip(",")
            if not ln:
                continue
            parts = [p for p in re.split(r"[,;\s]+", ln) if p]
            if len(parts) < 3:
                continue
            try:
                parsed.append((parts[0][:40], float(parts[1]), float(parts[2]),
                               float(parts[3]) if len(parts) > 3 else 0.0))
            except ValueError:
                continue
        if not parsed:
            raise CstError("Coords samajh nahi aaye - har line: 'id,x,y,z' (id,x,y chalega, z 0 maana "
                           "jayega aur yeh say() mein bol dunga).")
    with _LOCK, session() as s:
        x = CsurJob(tenant_id=tenant, project=project.strip()[:160], name=name.strip()[:160],
                    source_kind=source_kind, points=len(parsed), note=note.strip()[:300])
        s.add(x)
        s.flush()
        jid = x.id
        for pid, px, py, pz in parsed[:5000]:
            s.add(CsurPoint(tenant_id=tenant, job_id=jid, pid=pid, x=px, y=py, z=pz))
    from .common import publish
    publish(tenant, "const_survey", {"kind": "pts_add", "project": project, "job": name}, conv)
    z0 = sum(1 for _p, _x, _y, pz in parsed if pz == 0.0)
    say = (f"Survey job '{name}': {len(parsed)} points ({source_kind}). "
           + (f"{z0} rows bina Z - woh 0 baithe hain, volume ke liye asli Z do. " if z0 else "")
           + "Traverse / area / volume isi job pe chalega - certificate surveyor ka.")
    return {"job_id": jid, "points": len(parsed), "say": say}


def traverse(tenant: str, project: str, job_id: str, order: list, note: str = "") -> dict:
    """Traverse closure (#22): the ordered points walked as a LOOP - perimeter, closing error
    (first <-> last), and the precision ratio. Pure coordinate arithmetic; angles/observations
    parse nahi hote (LandXML note on the tin)."""
    pts = _pts(tenant, job_id)
    seq = [str(p).strip() for p in (order or [])]
    if len(seq) < 3:
        raise CstError("Loop traverse ke liye kam se kam 3 points ki ORDER bhejo.")
    missing = [p for p in seq if p not in pts]
    if missing:
        raise CstError(f"Yeh points job mein nahi: {', '.join(missing[:8])}.")
    per = 0.0
    for i in range(len(seq)):
        a, b = pts[seq[i]], pts[seq[(i + 1) % len(seq)]]
        per += math.hypot(b.x - a.x, b.y - a.y)
    first, last = pts[seq[0]], pts[seq[-1]]
    close = math.hypot(last.x - first.x, last.y - first.y) if seq[0] != seq[-1] else 0.0
    prec = round(per / close, 1) if close > 1e-9 else 0.0
    inputs = {"job_id": job_id, "order": seq}
    result = {"perimeter_m": round(per, 3), "closing_error_m": round(close, 3),
              "precision": f"1 in {prec:,.0f}" if prec else "closed",
              "formula": "sum of leg distances; closing error = dist(first, last)"}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="traverse",
                     name=f"loop of {len(seq)} pts", inputs=_dump(inputs), result=_dump(result),
                     is_ref="coordinate closure (loop); no angular observations parsed", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"calc_id": cid, **result,
            "say": f"Traverse: perimeter {per:,.2f} m, closing error {close:,.3f} m"
                   + (f" (precision 1 in {prec:,.0f})" if prec else " (loop band hai)")
                   + ". Arithmetic hai - traverse certificate licensed surveyor ka."}


def area_shoelace(tenant: str, project: str, job_id: str, order: list, record_m2: float = 0.0,
                  record_source: str = "", tolerance_pct: float = 2.0, note: str = "") -> dict:
    """Boundary area (#22): the ordered boundary points through the shoelace identity (math, not a
    notification); vs the 7/12 / record area with its source -> within / exceeds the tolerance."""
    pts = _pts(tenant, job_id)
    seq = [str(p).strip() for p in (order or [])]
    if len(seq) < 3:
        raise CstError("Boundary ke liye kam se kam 3 points ki order bhejo.")
    missing = [p for p in seq if p not in pts]
    if missing:
        raise CstError(f"Yeh points job mein nahi: {', '.join(missing[:8])}.")
    s2 = 0.0
    for i in range(len(seq)):
        a, b = pts[seq[i]], pts[seq[(i + 1) % len(seq)]]
        s2 += a.x * b.y - b.x * a.y
    area = round(abs(s2) / 2.0, 2)
    result = {"area_m2": area, "area_ha": round(area / 10000.0, 4),
              "formula": "shoelace: |sum(x_i x y_{i+1} - x_{i+1} x y_i)| / 2"}
    if _num(record_m2) > 0:
        if not str(record_source or "").strip():
            raise CstError("Record area ka SOURCE bataiye (7/12 no / sale deed) - bina source ka "
                           "record comparison nahi hota.")
        diff = round(abs(area - _num(record_m2)) / _num(record_m2) * 100.0, 3)
        verdict = "within" if diff <= _num(tolerance_pct) else "exceeds"
        result |= {"record_m2": _num(record_m2), "record_source": record_source.strip()[:160],
                   "diff_pct": diff, "tolerance_pct": _num(tolerance_pct), "verdict": verdict}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="area" if _num(record_m2) <= 0
                     else "boundary", name=f"{len(seq)}-pt boundary", inputs=_dump({"job_id": job_id,
                     "order": seq}), result=_dump(result),
                     is_ref="shoelace identity (planar coordinates); record area as fed", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    say = f"Area: {area:,.2f} m2 ({area / 10000.0:,.4f} ha), shoelace on your ordered points. "
    if "verdict" in result:
        say += (f"Record {result['record_m2']:,.2f} m2 ({record_source.strip()[:40]}): difference "
                f"{diff:.3f}% -> {'WITHIN' if verdict == 'within' else 'EXCEEDS'} {tolerance_pct:g}% tolerance. "
                "Discrepancy ka faisla surveyor + advocate ka.")
    else:
        say += "Certificate licensed surveyor ka."
    return {"calc_id": cid, **result, "say": say}


def volume_grid(tenant: str, project: str, name: str, elevations: list, design_level: float,
                cell_area_m2: float, note: str = "") -> dict:
    """Cut / fill volumes (#23): her grid of spot elevations vs the design level, average-height
    method - V = sum(z - design) x cell area, cut and fill kept SEPARATE (never netted silently).
    The elevation readings are the survey lead's; Hoola does the arithmetic."""
    if not elevations:
        raise CstError("Elevations bhejo [z, z, z...] - grid ke spot levels, survey lead ki reading.")
    if _num(cell_area_m2) <= 0:
        raise CstError("Cell area bataiye (> 0).")
    zs = [_num(z) for z in elevations]
    cut = sum(max(z - _num(design_level), 0.0) for z in zs) * _num(cell_area_m2)
    fill = sum(max(_num(design_level) - z, 0.0) for z in zs) * _num(cell_area_m2)
    result = {"cut_m3": round(cut, 2), "fill_m3": round(fill, 2), "net_m3": round(cut - fill, 2),
              "points": len(zs), "cell_area_m2": _num(cell_area_m2), "design_level": _num(design_level),
              "formula": "sum(max(z - design, 0)) x cell (cut); sum(max(design - z, 0)) x cell (fill)"}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="volume", name=name.strip()[:160],
                     inputs=_dump({"points": len(zs), "cell_area_m2": _num(cell_area_m2),
                                   "design_level": _num(design_level)}), result=_dump(result),
                     is_ref="average-height grid method on the elevations as fed", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"calc_id": cid, **result,
            "say": f"Volume ({name}): cut {cut:,.1f} m3, fill {fill:,.1f} m3 ({len(zs)} spot levels x "
                   f"{_num(cell_area_m2):g} m2). Net {cut - fill:,.1f} m3 - alag-alag rakha hai, chhupa "
                   "nahi. DSM/orthomosaic padhna survey lead ka kaam hai; yeh uski readings ka hisaab hai."}


def deviations(tenant: str, project: str, name: str, rows: list, tolerance_mm: float = 25.0,
               note: str = "") -> dict:
    """As-built vs design deviations (#24): rows [x, y, z_asbuilt, x, y, z_design] (CSV-style export -
    E57/LAS binaries parse NAHI hote, said on the tin). Per-point 3D deviation, RMS, and the
    out-of-tolerance list - the scan technician's QA, arithmetically."""
    if not rows:
        raise CstError("Deviation rows bhejo [x, y, z_asbuilt, x, y, z_design].")
    if _num(tolerance_mm) <= 0:
        raise CstError("Tolerance bataiye (> 0, mm).")
    devs, out_of = [], []
    for r in (rows or []):
        try:
            v = [float(x) for x in (r if isinstance(r, list) else str(r).split(","))]
        except (TypeError, ValueError):
            continue
        if len(v) < 6:
            continue
        d = math.dist(v[0:3], v[3:6])
        devs.append(d)
        if d * 1000.0 > _num(tolerance_mm):
            out_of.append({"point": [round(c, 3) for c in v[0:3]], "dev_mm": round(d * 1000.0, 1)})
    if not devs:
        raise CstError("Koi valid row nahi mili - har row mein 6 numbers chahiye (as-built x,y,z + design x,y,z).")
    rms = math.sqrt(sum(d * d for d in devs) / len(devs))
    result = {"points": len(devs), "rms_mm": round(rms * 1000.0, 1), "max_mm": round(max(devs) * 1000.0, 1),
              "tolerance_mm": _num(tolerance_mm), "out_of_tolerance": len(out_of),
              "formula": "dev = dist(as-built, design); rms = sqrt(sum(d^2)/n)"}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="deviation", name=name.strip()[:160],
                     inputs=_dump({"tolerance_mm": _num(tolerance_mm)}), result=_dump(result),
                     is_ref="CSV export (E57/LAS NOT parsed - said on the tin)", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"calc_id": cid, "worst": out_of[:20], **result,
            "say": f"Deviations: {len(devs)} points, RMS {rms * 1000.0:,.1f} mm, max "
                   f"{max(devs) * 1000.0:,.1f} mm, {len(out_of)} tolerance ({_num(tolerance_mm):g} mm) se "
                   "bahar. Scan ka QA paper - registration ka final word scan technician ka."}


# ---------------------------------------------------------------- RERA carpet area (#26)
def carpet_new(tenant: str, project: str, unit_no: str, wall_policy: str, declared_m2: float = 0.0,
               declared_source: str = "", note: str = "") -> dict:
    """A carpet-area statement (#26) starts with HER wall policy - RERA s.2(k) excludes external walls,
    balconies and service shafts; how internal walls are treated is HER word, recorded."""
    if not str(project or "").strip() or not str(unit_no or "").strip():
        raise CstError("Project aur unit number bataiye.")
    if not str(wall_policy or "").strip():
        raise CstError("Wall policy bataiye (jaise 'internal walls included at 100 mm' / 'carpet = net "
                       "usable, internal walls excluded') - policy bina likhe statement nahi banti.")
    if _num(declared_m2) > 0 and not str(declared_source or "").strip():
        raise CstError("Declared area ka SOURCE bataiye (agreement / marketing plan).")
    with _LOCK, session() as s:
        x = CsurCarpet(tenant_id=tenant, project=project.strip()[:160], unit_no=unit_no.strip()[:60],
                       wall_policy=wall_policy.strip()[:200], declared_m2=_num(declared_m2),
                       declared_source=declared_source.strip()[:160], note=note.strip()[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"carpet_id": cid,
            "say": f"Carpet statement {unit_no} khuli (policy: {wall_policy.strip()[:60]}). Rooms add "
                   "karo - har naap plan se insaan padhta hai. Balcony / shaft RERA s.2(k) se bahar "
                   "hain; certification architect / CE ki."}


def carpet_room(tenant: str, carpet_id: str, room: str, length_m: float, breadth_m: float) -> dict:
    """One room row: length x breadth as read by a human off the plan."""
    if not str(room or "").strip() or _num(length_m) <= 0 or _num(breadth_m) <= 0:
        raise CstError("Room ka naam aur length x breadth bataiye (sab > 0).")
    with _LOCK, session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement nahi mili.")
        x = CsurCarpetRoom(tenant_id=tenant, carpet_id=carpet_id, room=room.strip()[:80],
                           length_m=_num(length_m), breadth_m=_num(breadth_m))
        s.add(x)
        s.flush()
        rid = x.id
    return {"room_id": rid, "area_m2": round(_num(length_m) * _num(breadth_m), 3),
            "say": f"{room.strip()}: {_num(length_m):g} x {_num(breadth_m):g} = "
                   f"{_num(length_m) * _num(breadth_m):,.2f} m2 joda."}


def carpet_calc(tenant: str, carpet_id: str, tolerance_pct: float = 0.0, state: str = "maharashtra") -> dict:
    """The arithmetic: sum of rooms vs the declared area, against the tolerance (her number, else the
    state pack row). exceeds = the discrepancy report for the architect / CE - certification reserved."""
    with session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement nahi mili.")
        rooms = s.scalars(select(CsurCarpetRoom).where(CsurCarpetRoom.tenant_id == tenant,
                                                       CsurCarpetRoom.carpet_id == carpet_id)).all()
    if not rooms:
        raise CstError("Pehle rooms jodo - khaali statement par arithmetic nahi hota.")
    comp = round(sum(r.length_m * r.breadth_m for r in rooms), 3)
    tol = _num(tolerance_pct)
    if tol <= 0:
        try:
            tol = float(SP.rule_value(state, "rera_carpet_tolerance_pct", 0.0))
        except SP.PackError:
            tol = 0.0
    if tol <= 0:
        raise CstError("Tolerance nahi mili (pack row bhi nahi) - tolerance_pct batao apne source ke saath.")
    result = {"computed_m2": comp, "rooms": len(rooms), "declared_m2": c.declared_m2,
              "tolerance_pct": tol}
    if c.declared_m2 > 0:
        diff = round(abs(comp - c.declared_m2) / c.declared_m2 * 100.0, 3)
        verdict = "within" if diff <= tol else "exceeds"
        result |= {"diff_pct": diff, "verdict": verdict}
    else:
        diff, verdict = 0.0, "no_declared"
        result |= {"diff_pct": 0.0, "verdict": verdict}
    with _LOCK, session() as s:
        c2 = s.get(CsurCarpet, carpet_id)
        c2.computed_m2, c2.diff_pct, c2.verdict = comp, diff, verdict
    return {"carpet_id": carpet_id, **result,
            "say": (f"Carpet {c.unit_no}: computed {comp:,.2f} m2 ({len(rooms)} rooms, policy: "
                    f"{c.wall_policy[:40]}) vs declared {c.declared_m2:,.2f} m2 -> difference "
                    f"{diff:.3f}%, tolerance {tol:g}% -> "
                    f"{'WITHIN (arithmetic)' if verdict == 'within' else 'EXCEEDS (arithmetic)'}. "
                    "Discrepancy report architect / CE ke liye - certification unki."
                    if c.declared_m2 > 0 else
                    f"Carpet {c.unit_no}: computed {comp:,.2f} m2 ({len(rooms)} rooms). Declared area "
                    "abhi nahi hai - agar dijiye to tolerance-check hoga.")}


def carpet_pack(tenant: str, carpet_id: str) -> dict:
    """The discrepancy report PDF for the project architect / CE: rooms, policy, declared vs computed,
    tolerance verdict - sign line EMPTY."""
    with session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement nahi mili.")
        rooms = s.scalars(select(CsurCarpetRoom).where(CsurCarpetRoom.tenant_id == tenant,
                                                       CsurCarpetRoom.carpet_id == carpet_id)).all()
    buf = io.BytesIO()

    def t(a, text, size=10, bold=False):
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(a, y, str(text)[:110])
        y -= size + 5

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50
    t(50, "RERA CARPET-AREA STATEMENT - WORKING PAPER", 13, True)
    t(50, f"Project: {c.project}    Unit: {c.unit_no}")
    t(50, f"Wall policy (her word): {c.wall_policy}")
    t(50, "RERA s.2(k): external walls, service shafts, balcony / verandah, open terrace excluded.")
    y -= 6
    for r in rooms:
        t(56, f"{r.room:20s} {r.length_m:8.3f} x {r.breadth_m:8.3f} = {r.length_m * r.breadth_m:10.3f} m2", 9.5)
    y -= 6
    t(50, f"Computed carpet: {c.computed_m2:,.3f} m2      Declared: {c.declared_m2:,.3f} m2 "
          f"({c.declared_source or '-'})")
    t(50, f"Difference: {c.diff_pct:.3f}%      Verdict (arithmetic): {c.verdict}")
    y -= 16
    t(50, "Prepared by Hoola - PREPARE, never CERTIFY.")
    t(50, "Reviewed & certified by: ____________________________   Date: ____________", 10)
    t(50, "(project architect / civil engineer - yeh line Hoola kabhi nahi bhar sakta)", 8.5)
    pdf.showPage()
    pdf.save()
    from .. import chatfiles
    f = chatfiles.store(tenant, f"CARPET-{c.unit_no[:20].replace('/', '-')}-{c.id[:6]}.pdf",
                        buf.getvalue(), "application/pdf")
    return {"file": f, "computed_m2": c.computed_m2, "diff_pct": c.diff_pct, "verdict": c.verdict,
            "say": f"Carpet working paper {c.unit_no}: computed {c.computed_m2:,.2f} m2 vs declared "
                   f"{c.declared_m2:,.2f} m2 ({c.diff_pct:.3f}%). Sign line khaali - architect / CE bharenge."}
