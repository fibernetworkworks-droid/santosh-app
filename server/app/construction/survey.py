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
from .models import CGisLayer, CGisOverlay, CsurCalc, CsurCarpet, CsurCarpetRoom, CsurJob, CsurPoint
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
        raise CstError("Give the project and the job name.")
    if source_kind not in ("coords", "landxml"):
        raise CstError("source_kind: coords | landxml")
    text = str(text or "").strip()
    if not text:
        raise CstError("Send the points as text (coords: 'id,x,y,z' per line; LandXML: the CgPoints xml).")
    parsed: list[tuple[str, float, float, float]] = []
    if source_kind == "landxml":
        for m in _CGPOINT.finditer(text):
            pid = m.group(1).strip()[:40]
            vals = [float(v) for v in m.group(2).split()]
            if len(vals) >= 2:
                parsed.append((pid, vals[0], vals[1], vals[2] if len(vals) > 2 else 0.0))
        if not parsed:
            raise CstError("No CgPoint found in the LandXML - surfaces/observations are NOT parsed "
                           "(said on the tin); send the text with CgPoints.")
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
            raise CstError("Could not read the coords - each line: 'id,x,y,z' (id,x,y works too; z is taken as 0 "
                           "and the say() will tell you so).")
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
           + (f"{z0} rows have no Z - they sit at 0; give real Z for volume. " if z0 else "")
           + "Traverse / area / volume run on this job - the certificate is the surveyor's.")
    return {"job_id": jid, "points": len(parsed), "say": say}


def traverse(tenant: str, project: str, job_id: str, order: list, note: str = "") -> dict:
    """Traverse closure (#22): the ordered points walked as a LOOP - perimeter, closing error
    (first <-> last), and the precision ratio. Pure coordinate arithmetic; angles/observations
    parse nahi hote (LandXML note on the tin)."""
    pts = _pts(tenant, job_id)
    seq = [str(p).strip() for p in (order or [])]
    if len(seq) < 3:
        raise CstError("For a loop traverse, send the ORDER of at least 3 points.")
    missing = [p for p in seq if p not in pts]
    if missing:
        raise CstError(f"These points are not in the job: {', '.join(missing[:8])}.")
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
                   + (f" (precision 1 in {prec:,.0f})" if prec else " (the loop is closed)")
                   + ". This is arithmetic - the traverse certificate is the licensed surveyor's."}


def area_shoelace(tenant: str, project: str, job_id: str, order: list, record_m2: float = 0.0,
                  record_source: str = "", tolerance_pct: float = 2.0, note: str = "") -> dict:
    """Boundary area (#22): the ordered boundary points through the shoelace identity (math, not a
    notification); vs the 7/12 / record area with its source -> within / exceeds the tolerance."""
    pts = _pts(tenant, job_id)
    seq = [str(p).strip() for p in (order or [])]
    if len(seq) < 3:
        raise CstError("For a boundary, send the order of at least 3 points.")
    missing = [p for p in seq if p not in pts]
    if missing:
        raise CstError(f"These points are not in the job: {', '.join(missing[:8])}.")
    s2 = 0.0
    for i in range(len(seq)):
        a, b = pts[seq[i]], pts[seq[(i + 1) % len(seq)]]
        s2 += a.x * b.y - b.x * a.y
    area = round(abs(s2) / 2.0, 2)
    result = {"area_m2": area, "area_ha": round(area / 10000.0, 4),
              "formula": "shoelace: |sum(x_i x y_{i+1} - x_{i+1} x y_i)| / 2"}
    if _num(record_m2) > 0:
        if not str(record_source or "").strip():
            raise CstError("Give the SOURCE of the record area (7/12 no / sale deed) - without a source there is "
                           "no record comparison.")
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
                "The decision on a discrepancy is the surveyor's + the advocate's.")
    else:
        say += "The certificate is the licensed surveyor's."
    return {"calc_id": cid, **result, "say": say}


def volume_grid(tenant: str, project: str, name: str, elevations: list, design_level: float,
                cell_area_m2: float, note: str = "") -> dict:
    """Cut / fill volumes (#23): her grid of spot elevations vs the design level, average-height
    method - V = sum(z - design) x cell area, cut and fill kept SEPARATE (never netted silently).
    The elevation readings are the survey lead's; Hoola does the arithmetic."""
    if not elevations:
        raise CstError("Send elevations [z, z, z...] - the grid's spot levels, the survey lead's readings.")
    if _num(cell_area_m2) <= 0:
        raise CstError("Give the cell area (> 0).")
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
                   f"{_num(cell_area_m2):g} m2). Net {cut - fill:,.1f} m3 - kept separate, not "
                   "hidden. Reading the DSM/orthomosaic is the survey lead's job; this is the arithmetic on those readings."}


def deviations(tenant: str, project: str, name: str, rows: list, tolerance_mm: float = 25.0,
               note: str = "") -> dict:
    """As-built vs design deviations (#24): rows [x, y, z_asbuilt, x, y, z_design] (CSV-style export -
    E57/LAS binaries parse NAHI hote, said on the tin). Per-point 3D deviation, RMS, and the
    out-of-tolerance list - the scan technician's QA, arithmetically."""
    if not rows:
        raise CstError("Deviation rows bhejo [x, y, z_asbuilt, x, y, z_design].")
    if _num(tolerance_mm) <= 0:
        raise CstError("Give the tolerance (> 0, mm).")
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
        raise CstError("No valid row found - each row needs 6 numbers (as-built x,y,z + design x,y,z).")
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
                   f"{max(devs) * 1000.0:,.1f} mm, {len(out_of)} outside the tolerance ({_num(tolerance_mm):g} mm"
                   "). This is the scan's QA paper - the final word on registration is the scan technician's."}


# ---------------------------------------------------------------- RERA carpet area (#26)
def carpet_new(tenant: str, project: str, unit_no: str, wall_policy: str, declared_m2: float = 0.0,
               declared_source: str = "", note: str = "") -> dict:
    """A carpet-area statement (#26) starts with HER wall policy - RERA s.2(k) excludes external walls,
    balconies and service shafts; how internal walls are treated is HER word, recorded."""
    if not str(project or "").strip() or not str(unit_no or "").strip():
        raise CstError("Give the project and the unit number.")
    if not str(wall_policy or "").strip():
        raise CstError("Give the wall policy (for example 'internal walls included at 100 mm' / 'carpet = net "
                       "usable, internal walls excluded') - no statement is made without a written policy.")
    if _num(declared_m2) > 0 and not str(declared_source or "").strip():
        raise CstError("Give the SOURCE of the declared area (agreement / marketing plan).")
    with _LOCK, session() as s:
        x = CsurCarpet(tenant_id=tenant, project=project.strip()[:160], unit_no=unit_no.strip()[:60],
                       wall_policy=wall_policy.strip()[:200], declared_m2=_num(declared_m2),
                       declared_source=declared_source.strip()[:160], note=note.strip()[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"carpet_id": cid,
            "say": f"Carpet statement {unit_no} opened (policy: {wall_policy.strip()[:60]}). Add the "
                   "rooms - a person reads every measurement off the plan. Balcony / shaft are outside RERA s.2(k); "
                   "certification is the architect's / CE's."}


def carpet_room(tenant: str, carpet_id: str, room: str, length_m: float, breadth_m: float) -> dict:
    """One room row: length x breadth as read by a human off the plan."""
    if not str(room or "").strip() or _num(length_m) <= 0 or _num(breadth_m) <= 0:
        raise CstError("Give the room name and length x breadth (all > 0).")
    with _LOCK, session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement not found.")
        x = CsurCarpetRoom(tenant_id=tenant, carpet_id=carpet_id, room=room.strip()[:80],
                           length_m=_num(length_m), breadth_m=_num(breadth_m))
        s.add(x)
        s.flush()
        rid = x.id
    return {"room_id": rid, "area_m2": round(_num(length_m) * _num(breadth_m), 3),
            "say": f"{room.strip()}: {_num(length_m):g} x {_num(breadth_m):g} = "
                   f"{_num(length_m) * _num(breadth_m):,.2f} m2 added."}


def carpet_calc(tenant: str, carpet_id: str, tolerance_pct: float = 0.0, state: str = "maharashtra") -> dict:
    """The arithmetic: sum of rooms vs the declared area, against the tolerance (her number, else the
    state pack row). exceeds = the discrepancy report for the architect / CE - certification reserved."""
    with session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement not found.")
        rooms = s.scalars(select(CsurCarpetRoom).where(CsurCarpetRoom.tenant_id == tenant,
                                                       CsurCarpetRoom.carpet_id == carpet_id)).all()
    if not rooms:
        raise CstError("Add rooms first - there is no arithmetic on an empty statement.")
    comp = round(sum(r.length_m * r.breadth_m for r in rooms), 3)
    tol = _num(tolerance_pct)
    if tol <= 0:
        try:
            tol = float(SP.rule_value(state, "rera_carpet_tolerance_pct", 0.0))
        except SP.PackError:
            tol = 0.0
    if tol <= 0:
        raise CstError("No tolerance found (no pack row either) - give tolerance_pct with your source.")
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
                    "The discrepancy report is for the architect / CE - the certification is theirs."
                    if c.declared_m2 > 0 else
                    f"Carpet {c.unit_no}: computed {comp:,.2f} m2 ({len(rooms)} rooms). Declared area "
                    "is not there yet - give it and the tolerance check will run.")}


def carpet_pack(tenant: str, carpet_id: str) -> dict:
    """The discrepancy report PDF for the project architect / CE: rooms, policy, declared vs computed,
    tolerance verdict - sign line EMPTY."""
    with session() as s:
        c = s.get(CsurCarpet, carpet_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Carpet statement not found.")
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
    t(50, "(project architect / civil engineer - Hoola can never fill in this line)", 8.5)
    pdf.showPage()
    pdf.save()
    from .. import chatfiles
    f = chatfiles.store(tenant, f"CARPET-{c.unit_no[:20].replace('/', '-')}-{c.id[:6]}.pdf",
                        buf.getvalue(), "application/pdf")
    return {"file": f, "computed_m2": c.computed_m2, "diff_pct": c.diff_pct, "verdict": c.verdict,
            "say": f"Carpet working paper {c.unit_no}: computed {c.computed_m2:,.2f} m2 vs declared "
                   f"{c.declared_m2:,.2f} m2 ({c.diff_pct:.3f}%). The sign line is empty - the architect / CE fills it in."}


# -------------------------------------- #27 GIS layers + #77 setting-out (Wave 3.5, v0.565.0)
def gis_add(tenant: str, project: str, name: str, geojson_text: str, crs: str = "", units: str = "",
            note: str = "", conv: str = "") -> dict:
    """One GIS layer (#27): GeoJSON read as TEXT for its Polygon/MultiPolygon rings (json module,
    no geo deps). The CRS is recorded AS FED (RFC 7946 default is WGS84 degrees); `units` 'm' |
    'deg' decides whether an AREA is ever possible - degrees have no square metres. Flood/seismic/
    zoning VALUES ride gis_overlay as HER readings; the maps are never fetched or interpreted here."""
    if not str(project or "").strip() or not str(name or "").strip():
        raise CstError("Give the project and the layer name.")
    import json as _json
    try:
        gj = _json.loads(str(geojson_text or ""))
    except _json.JSONDecodeError as ex:
        raise CstError(f"Could not read the GeoJSON: {ex}") from None
    if not isinstance(gj, dict) or gj.get("type") not in ("FeatureCollection", "Feature", "Polygon",
                                                          "MultiPolygon"):
        raise CstError("This does not look like GeoJSON (FeatureCollection/Feature/Polygon needed).")
    polys: list[list[list[tuple[float, float]]]] = []   # [polygon][ring][ (x, y) ]
    geoms = []
    if gj.get("type") == "FeatureCollection":
        geoms = [f.get("geometry") or {} for f in (gj.get("features") or []) if isinstance(f, dict)]
    elif gj.get("type") == "Feature":
        geoms = [gj.get("geometry") or {}]
    else:
        geoms = [gj]
    for g in geoms:
        gt, gc = g.get("type"), g.get("coordinates")
        if gt == "Polygon" and isinstance(gc, list) and gc:
            polys.append([[tuple(map(float, p[:2])) for p in ring if isinstance(p, (list, tuple))
                           and len(p) >= 2] for ring in gc])
        elif gt == "MultiPolygon" and isinstance(gc, list):
            for poly in gc:
                if isinstance(poly, list) and poly:
                    polys.append([[tuple(map(float, p[:2])) for p in ring if isinstance(p, (list, tuple))
                                   and len(p) >= 2] for ring in poly])
    polys = [[[pt for pt in ring] for ring in poly] for poly in polys if poly]
    if not polys:
        raise CstError("No Polygon/MultiPolygon rings found in the GeoJSON - send geometry with boundaries; "
                       "point layers are not supported yet (said on the tin).")
    verts = sum(len(ring) for poly in polys for ring in poly)
    holes = sum(max(0, len(poly) - 1) for poly in polys)
    u = (units or "").strip().lower()
    if u and u not in ("m", "deg"):
        raise CstError("units: 'm' (projected, metre - like UTM) | 'deg' (WGS84 lat/lng). This "
                       "decides whether an area can be computed or not.")
    if not u:
        u = "deg"   # RFC 7946 default: WGS84 - honest until she says projected
    with _LOCK, session() as s:
        x = CGisLayer(tenant_id=tenant, project=project.strip()[:160], name=name.strip()[:160],
                      crs=(crs or ("WGS84 (RFC 7946 default)" if u == "deg" else "")).strip()[:80],
                      units=u, polygons=_dump([poly[0] for poly in polys]), holes=holes, vertices=verts,
                      note=note.strip()[:300])
        s.add(x)
        s.flush()
        lid = x.id
    from .common import publish
    publish(tenant, "const_survey", {"kind": "gis_add", "project": project, "layer": name}, conv)
    say = (f"GIS layer '{name}': {len(polys)} polygon (outer rings), {verts} vertices, {holes} inner "
           f"rings (read, NOT subtracted - boundary comparison is the surveyor's), CRS {x.crs or 'as fed'} "
           f"[{u}]. "
           + ("Degree coordinates - area is NOT computed until a projected metre CRS (UTM) comes; "
              "reprojection is for QGIS/the surveyor. " if u == "deg" else
              "Projected metre CRS - gis_area will run the shoelace. ")
           + "You read the VALUES of flood/seismic/zoning layers and have them noted in gis_overlay - "
             "the map is not interpreted here.")
    return {"layer_id": lid, "polygons": len(polys), "vertices": verts, "holes": holes, "units": u,
            "say": say}


def gis_area(tenant: str, layer_id: str, record_m2: float = 0.0, record_source: str = "",
             tolerance_pct: float = 2.0) -> dict:
    """Area of a GIS layer (#27): shoelace on the OUTER rings - and ONLY when the layer's units are
    projected metres. A degree has no square metres; the desk refuses, never converts silently."""
    with session() as s:
        lay = s.get(CGisLayer, layer_id)
        if not lay or lay.tenant_id != tenant:
            raise CstError("GIS layer not found.")
    if lay.units != "m":
        raise CstError(f"Layer '{lay.name}' is in {lay.units} units (CRS {lay.crs or 'as fed'}) - "
                       "a shoelace m2 on lat/lng is WRONG and I do not make that mistake. "
                       "Reproject the layer to a projected CRS (UTM zone, metre) and send it.")
    polys = _j(lay.polygons, [])
    if not polys:
        raise CstError("The layer has no outer rings.")
    area = 0.0
    for ring in polys:
        s2 = 0.0
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            s2 += a[0] * b[1] - b[0] * a[1]
        area += abs(s2) / 2.0
    area = round(area, 2)
    result = {"area_m2": area, "area_ha": round(area / 10000.0, 4), "polygons": len(polys),
              "holes_not_subtracted": lay.holes,
              "formula": "shoelace per outer ring, summed (projected metre CRS)"}
    if _num(record_m2) > 0:
        if not str(record_source or "").strip():
            raise CstError("Give the SOURCE of the record area (7/12 / sale deed / GIS record).")
        diff = round(abs(area - _num(record_m2)) / _num(record_m2) * 100.0, 3)
        verdict = "within" if diff <= _num(tolerance_pct) else "exceeds"
        result |= {"record_m2": _num(record_m2), "record_source": record_source.strip()[:160],
                   "diff_pct": diff, "tolerance_pct": _num(tolerance_pct), "verdict": verdict}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=lay.project, kind="gis_area", name=f"layer {lay.name}",
                     inputs=_dump({"layer_id": layer_id, "crs": lay.crs}), result=_dump(result),
                     is_ref="GeoJSON outer rings, shoelace (projected metre CRS only)", note="")
        s.add(x)
        s.flush()
        cid = x.id
    say = (f"GIS area ('{lay.name}'): {area:,.2f} m2 ({area / 10000.0:,.4f} ha) - shoelace on "
           f"{len(polys)} outer rings ({lay.holes} inner rings NOT subtracted, counted). ")
    if "verdict" in result:
        say += (f"Record {result['record_m2']:,.2f} m2 ({record_source.strip()[:40]}): {diff:.3f}% -> "
                f"{'WITHIN' if verdict == 'within' else 'EXCEEDS'} {tolerance_pct:g}%. The decision is the planner's/"
                "surveyor's.")
    return {"calc_id": cid, **result, "say": say}


def gis_overlay(tenant: str, project: str, layer_id: str, hazard: str, zone_value: str, source: str,
                note: str = "") -> dict:
    """One overlay reading (#27): the flood / seismic / zoning value as READ OFF THE MAP BY A HUMAN,
    with its source - Hoola records the reading, it never reads the map."""
    if not str(zone_value or "").strip() or not str(source or "").strip():
        raise CstError("Both the zone/layer value (that YOU read off the map) and its SOURCE are needed - "
                       "the map is not fetched or interpreted here.")
    with _LOCK, session() as s:
        x = CGisOverlay(tenant_id=tenant, project=project.strip()[:160], layer_id=layer_id.strip()[:40],
                        hazard=hazard.strip()[:40], zone_value=zone_value.strip()[:160],
                        source=source.strip()[:200], note=note.strip()[:200])
        s.add(x)
        s.flush()
        oid = x.id
    return {"overlay_id": oid,
            "say": f"Overlay: {hazard or 'layer'} = '{zone_value.strip()[:40]}' ({source.strip()[:50]}) - "
                   "YOUR reading, recorded. The zoning/flood conclusion is the planner's; "
                   "authority verification goes in the planner's paper."}


def _rows_to_pts(rows: list, min_cols: int) -> list[tuple[str, float, float, float]]:
    out: list[tuple[str, float, float, float]] = []
    for r in (rows or []):
        try:
            v = r if isinstance(r, list) else [p for p in re.split(r"[,;\s]+", str(r).strip()) if p]
            if len(v) < min_cols:
                continue
            out.append((str(v[0]).strip()[:40], float(v[1]), float(v[2]),
                        float(v[3]) if len(v) > 3 and str(v[3]).strip() else 0.0))
        except (TypeError, ValueError):
            continue
    return out


def setout_add(tenant: str, project: str, name: str, design_rows: list, note: str = "", conv: str = "") -> dict:
    """A setting-out sheet (#77): the DESIGN coordinates [id, x, y(, z)] - the survey engineer's
    values, stored as a survey job (source_kind 'setout'); the as-laid check rides setout_check."""
    parsed = _rows_to_pts(design_rows, 3)
    if not parsed:
        raise CstError("Send design coordinates - each row [id, x, y(, z)].")
    with _LOCK, session() as s:
        x = CsurJob(tenant_id=tenant, project=project.strip()[:160], name=name.strip()[:160],
                    source_kind="setout", points=len(parsed), note=note.strip()[:300])
        s.add(x)
        s.flush()
        jid = x.id
        for pid, px, py, pz in parsed[:5000]:
            s.add(CsurPoint(tenant_id=tenant, job_id=jid, pid=pid, x=px, y=py, z=pz))
    from .common import publish
    publish(tenant, "const_survey", {"kind": "setout_add", "project": project, "sheet": name}, conv)
    return {"job_id": jid, "points": len(parsed),
            "say": f"Setting-out sheet '{name}': {len(parsed)} design points. Give the rows you "
                   "set out in the field to setout_check - deviation in mm, the tolerance is yours."}


def setout_check(tenant: str, project: str, job_id: str, aslaid_rows: list, tolerance_mm: float = 25.0,
                 note: str = "") -> dict:
    """As-laid vs design (#77): rows [id, x, y(, z)] as STAKED on site, against the sheet's design
    points - plan deviation per point, RMS, the out-of-tolerance list. Arithmetic; re-staking and
    the acceptance stay with the survey engineer."""
    design = _pts(tenant, job_id)
    if not design:
        raise CstError("Setting-out job not found / empty - run setout_add first.")
    if _num(tolerance_mm) <= 0:
        raise CstError("Give the tolerance (> 0, mm).")
    devs, out_of, missing = [], [], []
    for r in _rows_to_pts(aslaid_rows, 3):
        pid = r[0]
        if pid not in design:
            missing.append(pid)
            continue
        d = math.hypot(r[1] - design[pid].x, r[2] - design[pid].y)
        devs.append((pid, d))
        if d * 1000.0 > _num(tolerance_mm):
            out_of.append({"point": pid, "dev_mm": round(d * 1000.0, 1)})
    if not devs:
        raise CstError("No valid as-laid row found - each row [id, x, y] (staked position).")
    rms = math.sqrt(sum(d * d for _p, d in devs) / len(devs))
    result = {"points": len(devs), "rms_mm": round(rms * 1000.0, 1),
              "max_mm": round(max(d for _p, d in devs) * 1000.0, 1),
              "tolerance_mm": _num(tolerance_mm), "out_of_tolerance": len(out_of),
              "missing_in_sheet": missing[:20],
              "formula": "dev = hypot(x_laid - x_design, y_laid - y_design) (plan)"}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="setout", name=f"check vs {job_id[:12]}",
                     inputs=_dump({"job_id": job_id, "tolerance_mm": _num(tolerance_mm)}),
                     result=_dump(result), is_ref="setting-out sheet (design) vs as-laid rows", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"calc_id": cid, "worst": out_of[:20], **result,
            "say": f"Setting-out check: {len(devs)} points, RMS {rms * 1000.0:,.1f} mm, max "
                   f"{max(d for _p, d in devs) * 1000.0:,.1f} mm, {len(out_of)} outside the tolerance "
                   f"({_num(tolerance_mm):g} mm)"
                   + (f", {len(missing)} not on the sheet" if missing else "")
                   + ". This is a record - the decision to set out again or to accept is the survey engineer's."}


def level_check(tenant: str, project: str, job_id: str, obs_rows: list, tolerance_mm: float = 25.0,
                note: str = "") -> dict:
    """Level check (#77): observed RLs [id, z_observed] vs the sheet's design Z - difference KEPT
    WITH ITS SIGN (up/down matters), out-of-tolerance listed. The level book and the closure are
    the survey engineer's craft; this is the comparison."""
    design = _pts(tenant, job_id)
    if not design:
        raise CstError("Setting-out/design job not found - run setout_add first (with design z).")
    if _num(tolerance_mm) <= 0:
        raise CstError("Give the tolerance (> 0, mm).")
    rows, out_of, missing = [], [], []
    for r in (obs_rows or []):
        try:
            v = r if isinstance(r, list) else [p for p in re.split(r"[,;\s]+", str(r).strip()) if p]
            if len(v) < 2:
                continue
            pid, zo = str(v[0]).strip()[:40], float(v[1])
        except (TypeError, ValueError):
            continue
        if pid not in design or design[pid].z == 0.0:
            missing.append(pid)
            continue
        dz_mm = round((zo - design[pid].z) * 1000.0, 1)   # sign kept: + up, - down
        ok = abs(dz_mm) <= _num(tolerance_mm)
        if not ok:
            out_of.append({"point": pid, "dz_mm": dz_mm})
        rows.append({"point": pid, "design_z": design[pid].z, "observed_z": zo, "dz_mm": dz_mm,
                     "verdict": "ok" if ok else "out"})
    if not rows:
        raise CstError("No valid level row found - each row [id, z_observed]; design z must be on the sheet "
                       "points (points with z=0 are refused).")
    result = {"points": len(rows), "tolerance_mm": _num(tolerance_mm), "out_of_tolerance": len(out_of),
              "max_abs_mm": max(abs(r["dz_mm"]) for r in rows), "rows": rows[:40],
              "missing_or_zero_design": missing[:20],
              "formula": "dz = (z_obs - z_design) x 1000, sign kept"}
    with _LOCK, session() as s:
        x = CsurCalc(tenant_id=tenant, project=project.strip()[:160], kind="level", name=f"levels vs {job_id[:12]}",
                     inputs=_dump({"job_id": job_id, "tolerance_mm": _num(tolerance_mm)}),
                     result=_dump({k: v for k, v in result.items() if k != "rows"}),
                     is_ref="design RLs from the setting-out sheet; observed RLs as fed", note=note[:200])
        s.add(x)
        s.flush()
        cid = x.id
    return {"calc_id": cid, **result,
            "say": f"Level check: {len(rows)} points, {len(out_of)} outside the tolerance ({_num(tolerance_mm):g} mm)"
                   f", max |dz| {result['max_abs_mm']:,.1f} mm (signed - up and down are different "
                   "things). Benchmark closure is the survey engineer's job; this is a comparison."}
