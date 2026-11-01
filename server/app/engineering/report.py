"""v0.365 pictures + PDF for the after-build stage: FEA colour maps with a scale bar, sheet-metal flat pattern
(PNG + DXF with bend lines), CNC toolpath preview, and the analysis report (A4 pages, DRAFT for an engineer)."""
from __future__ import annotations

import io
import math
from datetime import date
from typing import Any

from PIL import Image, ImageDraw

from . import render
from .render import BG, EDGE, _font

INK = (32, 40, 52)
MUTE = (90, 98, 110)


def fea_view(surface: dict[str, Any], scale: dict[str, Any], view: str = "iso", size: int = 900) -> Image.Image:
    part, _ = render.draw_view(surface, view, size - 130, size - 60, sharp=_feature_edges(surface))
    img = Image.new("RGB", (size, size), BG)
    img.paste(part, (0, 60))                          # the scale bar keeps its own strip on the right
    d = ImageDraw.Draw(img)
    from .fea import colormap
    x0, y0, bw, bh = size - 70, 120, 26, size - 260
    for i in range(bh):
        c = colormap(1 - i / bh)
        d.line([(x0, y0 + i), (x0 + bw, y0 + i)], fill=tuple(int(255 * v) for v in c))
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=INK)
    f = _font(18)
    lo, hi = float(scale.get("lo", 0)), float(scale.get("hi", 1))
    for k in range(6):
        v = lo + (hi - lo) * (5 - k) / 5
        v = 0.0 if abs(v) < 1e-9 * max(abs(hi), abs(lo), 1e-12) else v
        y = y0 + bh * k / 5
        txt = f"{v:.3g}"
        d.text((x0 - 10 - d.textlength(txt, font=f), y - 9), txt, fill=INK, font=f)
    d.text((24, 20), str(scale.get("label", "")), fill=INK, font=_font(24))
    return img


def _feature_edges(mesh: dict[str, Any], deg: float = 30.0) -> set:
    """Outline edges of an FEA surface: triangle orientation is not consistent there, so the fold test uses |cos|."""
    import numpy as np
    V = np.asarray(mesh["v"], dtype=float)
    T = np.asarray(mesh["t"], dtype=np.int64)
    if not len(T):
        return set()
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    edges: dict[tuple[int, int], list[int]] = {}
    for ti, (a, b, c) in enumerate(T.tolist()):
        for u, v in ((a, b), (b, c), (c, a)):
            edges.setdefault((min(u, v), max(u, v)), []).append(ti)
    lim = math.cos(math.radians(deg))
    return {e for e, ts in edges.items() if len(ts) == 2 and abs(float(n[ts[0]] @ n[ts[1]])) < lim}


def flat_dxf(sheet: dict[str, Any]) -> str:
    """DXF R12: outline (layer CUT) + bend lines (layer BEND, dashed) of the flat pattern, mm."""
    ents: list[str] = []

    def line(a, b, layer="CUT"):
        ents.append(f"0\nLINE\n8\n{layer}\n6\n{'DASHED' if layer == 'BEND' else 'CONTINUOUS'}\n10\n{a[0]:.4f}\n20\n{a[1]:.4f}\n30\n0\n"
                    f"11\n{b[0]:.4f}\n21\n{b[1]:.4f}\n31\n0\n")
    for a, b in _flat_lines(sheet)["cut"]:
        line(a, b)
    for a, b in _flat_lines(sheet)["bend"]:
        line(a, b, "BEND")
    head = ("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLTYPE\n70\n2\n"
            "0\nLTYPE\n2\nCONTINUOUS\n70\n0\n3\nSolid\n72\n65\n73\n0\n40\n0.0\n"
            "0\nLTYPE\n2\nDASHED\n70\n0\n3\nDashed\n72\n65\n73\n2\n40\n6.0\n49\n4.0\n49\n-2.0\n0\nENDTAB\n0\nENDSEC\n")
    return head + "0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n0\nEOF\n"


def _flat_lines(sh: dict[str, Any]) -> dict[str, list]:
    cut, bend = [], []
    if sh.get("kind") == "strip":
        L, W = float(sh["length"]), float(sh["width"])
        cut = [((0, 0), (L, 0)), ((L, 0), (L, W)), ((L, W), (0, W)), ((0, W), (0, 0))]
        x = 0.0
        for p in sh.get("pieces") or []:
            if p[0] == "flat":
                x += p[1]
            else:
                bend.append(((x + p[1] / 2, 0), (x + p[1] / 2, W)))
                x += p[1]
    else:                                              # tray: base + 4 flanges (cross shape), square corner reliefs
        bx, by = sh["base"]
        f = float(sh["flange"]) + float(sh["ba"]) / 2
        e = float(sh["ba"]) / 2
        X0, X1, Y0, Y1 = f, f + bx, f, f + by
        pts = [(X0, 0), (X1, 0), (X1, Y0), (X1 + f, Y0), (X1 + f, Y1), (X1, Y1), (X1, Y1 + f), (X0, Y1 + f),
               (X0, Y1), (0, Y1), (0, Y0), (X0, Y0)]
        cut = list(zip(pts, pts[1:] + pts[:1]))
        bend = [((X0, Y0 - e), (X1, Y0 - e)), ((X0, Y1 + e), (X1, Y1 + e)), ((X0 - e, Y0), (X0 - e, Y1)),
                ((X1 + e, Y0), (X1 + e, Y1))]
    return {"cut": cut, "bend": bend}


def flat_png(sheet: dict[str, Any], size: int = 900) -> Image.Image:
    ln = _flat_lines(sheet)
    xs = [p[0] for seg in ln["cut"] for p in seg]
    ys = [p[1] for seg in ln["cut"] for p in seg]
    w, h = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1
    sc = 0.8 * min(size / w, size / h)
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    ox, oy = (size - w * sc) / 2 - min(xs) * sc, (size + h * sc) / 2 + min(ys) * sc

    def P(p):
        return (ox + p[0] * sc, oy - p[1] * sc)
    for a, b in ln["cut"]:
        d.line([P(a), P(b)], fill=INK, width=3)
    for a, b in ln["bend"]:
        A, B = P(a), P(b)
        n = max(2, int(math.dist(A, B) / 14))
        for i in range(0, n, 2):
            d.line([(A[0] + (B[0] - A[0]) * i / n, A[1] + (B[1] - A[1]) * i / n),
                    (A[0] + (B[0] - A[0]) * (i + 1) / n, A[1] + (B[1] - A[1]) * (i + 1) / n)], fill=(200, 60, 50), width=2)
    f = _font(22)
    d.text((24, 20), f"Flat pattern {w:.2f} x {h:.2f} mm · t {sheet['t']:g} · R {sheet['r']:g} · K {sheet['k']:g}",
           fill=INK, font=f)
    d.text((24, size - 40), "Red dashed = bend lines (centre of the bend allowance)", fill=MUTE, font=_font(18))
    return img


def cam_png(paths: list[dict[str, Any]], size_xy: list[float], size: int = 900) -> Image.Image:
    xs = [p[0] for pa in paths for p in pa["pts"]] + [0, size_xy[0]]
    ys = [p[1] for pa in paths for p in pa["pts"]] + [0, size_xy[1]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sc = 0.86 * min(size / max(x1 - x0, 1), size / max(y1 - y0, 1))
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)

    def P(x, y):
        return ((size - (x1 - x0) * sc) / 2 + (x - x0) * sc, (size + (y1 - y0) * sc) / 2 - (y - y0) * sc)
    d.rectangle([P(0, size_xy[1]), P(size_xy[0], 0)], outline=(170, 176, 186), width=2)
    cols = {"face": (150, 170, 200), "pocket": (40, 140, 90), "profile": (200, 70, 50), "drill": (60, 60, 200)}
    for pa in paths:
        c = cols.get(pa["op"], INK)
        if pa["op"] == "drill":
            x, y = pa["pts"][0]
            r = max(3, pa.get("d", 3) / 2 * sc)
            cx, cy = P(x, y)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=3)
        elif len(pa["pts"]) > 1:
            d.line([P(*p) for p in pa["pts"]], fill=c, width=1 if pa["op"] == "face" else 2)
    f = _font(20)
    y = 16
    for k, c in cols.items():
        d.rectangle([20, y + 4, 40, y + 20], fill=c)
        d.text((48, y), k, fill=INK, font=f)
        y += 28
    return img


def analysis_pdf(title: str, part: dict[str, Any], studies: list[dict[str, Any]], pictures: list[Image.Image],
                 cam: dict[str, Any] | None) -> bytes:
    W, H = 1654, 2339                                # A4 portrait at 200 dpi
    pages = []
    page = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(page)
    fb, f, fs = _font(46), _font(28), _font(24)
    y = 90
    d.text((90, y), f"Analysis report · {title[:60]}", fill=INK, font=fb)
    y += 80
    d.text((90, y), f"Hoola CAD Engineer · {date.today():%d %b %Y} · DRAFT - for a qualified engineer's review, "
                    "not certified", fill=MUTE, font=fs)
    y += 70
    bb = part.get("bbox") or {}
    d.text((90, y), f"Part: {bb.get('x', 0):g} x {bb.get('y', 0):g} x {bb.get('z', 0):g} mm, volume "
                    f"{part.get('volume_mm3', 0):,.0f} mm³, material {part.get('material') or '-'}", fill=INK, font=f)
    y += 70
    for st in studies:
        rows = summary_rows(st)
        d.text((90, y), rows[0], fill=INK, font=_font(34))
        y += 56
        for line in rows[1:]:
            d.text((120, y), line, fill=INK if not line.startswith("!") else (180, 40, 30), font=fs)
            y += 38
        y += 30
    if cam:
        d.text((90, y), "CNC G-code", fill=INK, font=_font(34))
        y += 56
        for line in cam_rows(cam):
            d.text((120, y), line, fill=INK, font=fs)
            y += 38
    y += 20
    for line in ("Method: quadratic tetrahedra (scikit-fem) on a mesh made from the part's own B-rep; loads and supports on",
                 "the named faces; linear elastic, small displacement, steady state. Peaks AT a support edge are a known",
                 "singularity of ideal clamping - judge strength by the peak away from supports. Verify with an independent",
                 "check (hand calculation / physical test) before use."):
        d.text((90, y), line, fill=MUTE, font=fs)
        y += 34
    pages.append(page)
    for i in range(0, len(pictures), 2):
        pg = Image.new("RGB", (W, H), BG)
        for j, pic in enumerate(pictures[i:i + 2]):
            pg.paste(pic.resize((1050, 1050)), (302, 100 + j * 1120))
        pages.append(pg)
    b = io.BytesIO()
    pages[0].save(b, "PDF", resolution=200.0, save_all=len(pages) > 1, append_images=pages[1:])
    return b.getvalue()


def summary_rows(st: dict[str, Any]) -> list[str]:
    if not st.get("ok"):
        return [f"{str(st.get('kind') or 'analysis').title()}: did not run", f"! {st.get('error', '')[:110]}"]
    k = st["kind"]
    mesh = st.get("mesh") or {}
    mline = f"Mesh: {mesh.get('nodes', 0):,} nodes, {mesh.get('elements', 0):,} quadratic tetra, h {mesh.get('h_mm', 0):g} mm"
    if k == "static":
        conv = st.get("convergence") or {}
        rows = [f"Stress (static) · {st['material']} (E {st['E_MPa']:,} MPa, yield {st['yield_MPa']} MPa)",
                f"Max displacement {st['max_disp_mm']:.4g} mm at {st['at_disp']}",
                f"Peak von Mises away from supports {st['peak_vm_away_MPa']:.4g} MPa at {st['at_peak']} "
                f"(at a support {st['peak_vm_MPa']:.4g} MPa)",
                f"Safety factor vs yield {st['safety_factor']:.3g}" + (f" (needed {st['min_sf']:g}: "
                                                                      f"{'PASS' if st.get('passes') else 'FAIL'})" if st.get('min_sf') else ""),
                f"Loads {st['applied_N']} N, equilibrium error {st['equilibrium_error_pct']:.3g} %",
                (f"Mesh check: displacement changed {conv.get('disp_change_pct')} %, stress {conv.get('stress_change_pct')} % "
                 f"from a 3x coarser mesh ({'converged' if conv.get('ok') else 'NOT converged - treat with care'})") if conv else "",
                mline]
        fat = st.get("fatigue")
        if fat:
            rows.append(f"Fatigue ({fat['load']}): amplitude {fat['sigma_a_MPa']:.4g} MPa, mean {fat['sigma_m_MPa']:.4g} MPa, "
                        f"Se {fat['Se_MPa']:.4g} MPa ({fat['basis']}), life {fat['predicted_cycles']} cycles, "
                        f"fatigue SF {fat['fatigue_sf']:.3g} (needed {fat['need_sf']:g}: {'PASS' if fat['passes'] else 'FAIL'})")
            if not fat["passes"]:
                rows.append("! Fatigue: will crack under the repeated load before the target life")
        if st.get("glued_assembly"):
            rows.append("! Assembly analysed as ONE glued body (no contact / bolt preload)")
        if st.get("min_sf") and not st.get("passes"):
            rows.append("! Below the safety factor asked for")
        return [r for r in rows if r]
    if k == "thermal":
        return [f"Heat (steady) · {st['material']} (k {st['k_W_mmK'] * 1000:g} W/m·K)",
                f"Max {st['t_max_C']:.4g} °C at {st['at_max']}, min {st['t_min_C']:.4g} °C, heat in {st['heat_in_W']:g} W",
                mline]
    if k == "flow":
        rows = [f"Flow (laminar CFD) · {st['fluid']} · {st['flow_lpm']:g} L/min",
                f"Pressure drop {st['pressure_drop_Pa']:.4g} Pa · max speed {st['max_speed_mm_s']:.4g} mm/s · "
                f"Re {st['reynolds']:.4g} ({st['regime']})",
                f"Mass balance {st['mass_balance_pct']:g} % out / in · {st['iterations']} solver rounds"
                + ("" if st.get("converged") else " (NOT converged)"), mline + " (Taylor-Hood P2-P1)"]
        if not st.get("valid"):
            rows.append("! Turbulent flow: this laminar result is NOT valid; use the hand estimate "
                        f"{st.get('turbulent_estimate_Pa_per_m', '-')} Pa/m or a RANS CFD")
        if st.get("max_dp_pa") is not None:
            rows.append(("OK: " if st.get("passes") else "! Above ") + f"her pressure-drop limit {st['max_dp_pa']:g} Pa")
        return rows
    rows = [f"Vibration (modal) · {st['material']} · supports {st['supports']}",
            "Natural frequencies: " + ", ".join(f"{x:g} Hz" for x in st["frequencies_hz"]), mline]
    rz = st.get("resonance")
    if rz:
        rows.append(("OK: no mode inside " if rz["ok"] else "! Mode(s) inside ") + f"{rz['band_hz']} Hz"
                    + ("" if rz["ok"] else f": {rz['inside']}"))
    return rows


def cam_rows(cam: dict[str, Any]) -> list[str]:
    if not cam.get("ok"):
        return [f"! did not run: {cam.get('error', '')[:110]}"]
    return [f"Operations: {', '.join(cam['ops'])} · tool Ø{cam['tool_d']:g} mm, stepdown {cam['stepdown']:g} mm, "
            f"stepover {cam['stepover_mm']:g} mm",
            f"Feed {cam['feed']:g} mm/min, {cam['rpm']} rpm · cutting {cam['cut_m']:g} m · about {cam['minutes']:g} min",
            f"Stock about {cam['stock_mm'][0]:g} x {cam['stock_mm'][1]:g} x {cam['stock_mm'][2]:g} mm · zero = part corner, Z0 = part top",
            "Simulate in your CAM viewer and dry-run above the stock before the first cut."]
