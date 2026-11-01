"""Pictures of a CAD part from its triangle mesh (mesh.json from the runner), drawn with PIL in the main process (the
mesh is plain numbers, so nothing from the script runs here): four shaded views and a one-page drawing PDF with the
three orthographic views at one scale, overall dimensions and a title block."""
from __future__ import annotations

import io
import math
from datetime import date
from typing import Any

from PIL import Image, ImageDraw, ImageFont

BG = (255, 255, 255)
BASE = (122, 146, 176)          # steel blue-grey
EDGE = (32, 40, 52)
SHARP_DEG = 28

VIEWS = {   # (rotation about z, then about x) in degrees; screen x right, y up, depth toward the viewer
    "iso": (-45.0, -54.7356),
    "front": (0.0, -90.0),
    "top": (0.0, 0.0),
    "right": (-90.0, -90.0),
}
LABEL = {"iso": "3D view", "front": "Front", "top": "Top", "right": "Right side"}


def _rot(v: list[float], view: str) -> tuple[float, float, float]:
    az, el = VIEWS[view]
    a, e = math.radians(az), math.radians(el)
    x, y, z = v
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    y, z = y * math.cos(e) - z * math.sin(e), y * math.sin(e) + z * math.cos(e)
    return x, y, z


def _norm(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    ln = math.sqrt(sum(k * k for k in n)) or 1.0
    return n[0] / ln, n[1] / ln, n[2] / ln


def _sharp_edges(verts: list, tris: list) -> set[tuple[int, int]]:
    normals = [_norm(verts[t[0]], verts[t[1]], verts[t[2]]) for t in tris]
    by_edge: dict[tuple[int, int], list[int]] = {}
    for i, t in enumerate(tris):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            by_edge.setdefault((min(a, b), max(a, b)), []).append(i)
    lim = math.cos(math.radians(SHARP_DEG))
    out = set()
    for e, fs in by_edge.items():
        if len(fs) != 2:
            out.add(e)
            continue
        n1, n2 = normals[fs[0]], normals[fs[1]]
        if n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2] < lim:
            out.add(e)
    return out


def extent(mesh: dict[str, Any], view: str) -> tuple[float, float, float, float]:
    pts = [_rot(v, view) for v in mesh["v"]] or [(0, 0, 0)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def draw_view(mesh: dict[str, Any], view: str, w: int, h: int, scale: float | None = None,
              sharp: set | None = None, ss: int = 2) -> tuple[Image.Image, float]:
    """(RGB image w x h, px per mm used). scale=None fits the part with a margin. A depth buffer (numpy) decides
    what is in front, so faces and edges hide correctly at any triangle size."""
    import numpy as np
    verts, tris = mesh["v"], mesh["t"]
    rv = np.array([_rot(v, view) for v in verts] or [(0.0, 0.0, 0.0)], dtype=float)
    x0, x1, y0, y1 = extent(mesh, view)
    if scale is None:
        scale = 0.84 * min(w / max(x1 - x0, 1e-6), h / max(y1 - y0, 1e-6))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    W, H = w * ss, h * ss
    sx = W / 2 + (rv[:, 0] - cx) * scale * ss
    sy = H / 2 - (rv[:, 1] - cy) * scale * ss
    sz = rv[:, 2]
    zbuf = np.full((H, W), -np.inf)
    rgb = np.full((H, W, 3), BG, dtype=np.float64)
    lx, ly, lz = -0.35, 0.45, 0.82
    base = np.array(BASE, dtype=float)
    tri_part = mesh.get("c") or []
    tri_col = mesh.get("tc") or []                    # v0.365 per-triangle colours (FEA maps)
    part_cols = [np.array([min(255.0, 255 * float(x)) for x in c[:3]]) for c in (mesh.get("colors") or [])]
    for ti, t in enumerate(tris):
        a, b, c = t
        xa, ya, xb, yb, xc, yc = sx[a], sy[a], sx[b], sy[b], sx[c], sy[c]
        den = (yb - yc) * (xa - xc) + (xc - xb) * (ya - yc)
        if abs(den) < 1e-9:
            continue
        lo_x, hi_x = int(max(0, np.floor(min(xa, xb, xc)))), int(min(W - 1, np.ceil(max(xa, xb, xc))))
        lo_y, hi_y = int(max(0, np.floor(min(ya, yb, yc)))), int(min(H - 1, np.ceil(max(ya, yb, yc))))
        if lo_x > hi_x or lo_y > hi_y:
            continue
        gx, gy = np.meshgrid(np.arange(lo_x, hi_x + 1) + 0.5, np.arange(lo_y, hi_y + 1) + 0.5)
        w1 = ((yb - yc) * (gx - xc) + (xc - xb) * (gy - yc)) / den
        w2 = ((yc - ya) * (gx - xc) + (xa - xc) * (gy - yc)) / den
        w3 = 1 - w1 - w2
        inside = (w1 >= -1e-6) & (w2 >= -1e-6) & (w3 >= -1e-6)
        if not inside.any():
            continue
        z = w1 * sz[a] + w2 * sz[b] + w3 * sz[c]
        zb = zbuf[lo_y:hi_y + 1, lo_x:hi_x + 1]
        win = inside & (z > zb)
        if not win.any():
            continue
        n = _norm(rv[a], rv[b], rv[c])
        if n[2] < 0:
            n = (-n[0], -n[1], -n[2])
        k = 0.42 + 0.58 * max(0.0, n[0] * lx + n[1] * ly + n[2] * lz)
        if tri_col:
            pc = np.array([255.0 * float(x) for x in tri_col[ti][:3]])
        else:
            pc = part_cols[tri_part[ti]] if part_cols and ti < len(tri_part) and tri_part[ti] < len(part_cols) else base
        col = pc * (0.62 + 0.38 * k) if tri_col else pc * k + 30 * (1 - k)
        zb[win] = z[win]
        rgb[lo_y:hi_y + 1, lo_x:hi_x + 1][win] = col
    img = Image.fromarray(np.clip(rgb, 0, 255).astype("uint8"), "RGB")
    d = ImageDraw.Draw(img)
    sharp = sharp if sharp is not None else _sharp_edges(verts, tris)
    eps = 4e-3 * max(x1 - x0, y1 - y0, 1.0)          # v0.362 wider: no speckle on gear teeth / curved facets
    lw = max(1, ss)
    for u, v in sharp:                       # an edge is drawn where it is not hidden behind a nearer face
        steps = max(2, int(math.hypot(sx[v] - sx[u], sy[v] - sy[u]) / 3))
        seg: list[tuple[float, float]] = []
        for i in range(steps + 1):
            f = i / steps
            px_, py_ = sx[u] + (sx[v] - sx[u]) * f, sy[u] + (sy[v] - sy[u]) * f
            pz = sz[u] + (sz[v] - sz[u]) * f
            ix, iy = min(W - 1, max(0, int(px_))), min(H - 1, max(0, int(py_)))
            near = zbuf[max(0, iy - 1):iy + 2, max(0, ix - 1):ix + 2].max()
            if pz >= near - eps:
                seg.append((px_, py_))
            else:
                if len(seg) > 1:
                    d.line(seg, fill=EDGE, width=lw)
                seg = []
        if len(seg) > 1:
            d.line(seg, fill=EDGE, width=lw)
    if ss > 1:
        img = img.resize((w, h), Image.LANCZOS)
    return img, scale


def png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG", optimize=True)
    return b.getvalue()


def views(mesh: dict[str, Any], size: int = 900) -> dict[str, bytes]:
    sharp = _sharp_edges(mesh["v"], mesh["t"])
    return {v: png(draw_view(mesh, v, size, size, sharp=sharp)[0]) for v in VIEWS}


def _font(px: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _dim(d: ImageDraw.ImageDraw, a: tuple[float, float], b: tuple[float, float], text: str, f, vertical: bool) -> None:
    d.line([a, b], fill=EDGE, width=2)
    for p in (a, b):                                   # end ticks
        if vertical:
            d.line([(p[0] - 10, p[1]), (p[0] + 10, p[1])], fill=EDGE, width=2)
        else:
            d.line([(p[0], p[1] - 10), (p[0], p[1] + 10)], fill=EDGE, width=2)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    tw = d.textlength(text, font=f)
    if vertical:
        d.text((mx - tw - 16, my - 14), text, fill=EDGE, font=f)
    else:
        d.text((mx - tw / 2, my + 12), text, fill=EDGE, font=f)


def svg_png(svg: str, w: int, h: int) -> Image.Image | None:
    """v0.362 a CadQuery hidden-line SVG -> RGB image (resvg-py; None when it is not installed)."""
    try:
        import resvg_py
        data = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=w, height=h))
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        bg = Image.new("RGBA", im.size, BG + (255,))
        bg.alpha_composite(im)
        return bg.convert("RGB")
    except Exception:
        return None


def line_page(hlr: dict[str, str], info: dict[str, Any]) -> Image.Image | None:
    """Page 2: front / top / right with hidden edges dashed + an isometric line view, each fitted to its box."""
    if not hlr:
        return None
    W, H = 2339, 1654
    page = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(page)
    d.rectangle([40, 40, W - 40, H - 40], outline=EDGE, width=3)
    f, fs = _font(30), _font(24)
    slots = {"front": (80, 80), "right": (1180, 80), "top": (80, 860), "iso": (1180, 860)}
    any_ = False
    for v, (ox, oy) in slots.items():
        if not hlr.get(v):
            continue
        img = svg_png(hlr[v], 1060, 700)
        if img is None:
            continue
        page.paste(img, (ox, oy))
        d.text((ox + 10, oy + 6), LABEL[v] + ("" if v == "iso" else " (hidden edges dashed)"), fill=EDGE, font=f)
        any_ = True
    if not any_:
        return None
    d.text((80, H - 100), f"{str(info.get('title') or 'Part')[:60]} · line views, each fitted to its box (not to one scale) "
                          "· DRAFT - for a qualified engineer's review, not certified", fill=(90, 98, 110), font=fs)
    return page


def drawing_pdf(mesh: dict[str, Any], info: dict[str, Any], hlr: dict[str, str] | None = None) -> bytes:
    """A4 landscape at 200 dpi: front (top left), top (below it), right side (beside front), 3D view, title block."""
    W, H = 2339, 1654
    page = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(page)
    d.rectangle([40, 40, W - 40, H - 40], outline=EDGE, width=3)
    f, fs, fb = _font(30), _font(24), _font(40)
    sharp = _sharp_edges(mesh["v"], mesh["t"])
    cell_w, cell_h = 820, 600
    ex = {v: extent(mesh, v) for v in ("front", "top", "right")}
    need_w = max(ex[v][1] - ex[v][0] for v in ex) or 1
    need_h = max(ex[v][3] - ex[v][2] for v in ex) or 1
    scale = 0.72 * min(cell_w / need_w, cell_h / need_h)
    slots = {"front": (90, 90), "right": (960, 90), "top": (90, 760)}
    bb = info.get("bbox") or {}
    sizes = {"front": (bb.get("x"), bb.get("z")), "right": (bb.get("y"), bb.get("z")), "top": (bb.get("x"), bb.get("y"))}
    for v, (ox, oy) in slots.items():
        img, _ = draw_view(mesh, v, cell_w, cell_h, scale=scale, sharp=sharp)
        page.paste(img, (ox, oy))
        x0, x1, y0, y1 = ex[v]
        pw, ph = (x1 - x0) * scale, (y1 - y0) * scale
        left, top = ox + cell_w / 2 - pw / 2, oy + cell_h / 2 - ph / 2
        wmm, hmm = sizes[v]
        if wmm is not None:
            _dim(d, (left, top + ph + 34), (left + pw, top + ph + 34), f"{wmm:g}", fs, False)
        if hmm is not None:
            _dim(d, (left - 34, top), (left - 34, top + ph), f"{hmm:g}", fs, True)
        d.text((ox + 10, oy + 6), LABEL[v], fill=EDGE, font=f)
    iso, _ = draw_view(mesh, "iso", 640, 560, sharp=sharp)
    page.paste(iso, (1640, 120))
    d.text((1650, 126), LABEL["iso"], fill=EDGE, font=f)
    # title block
    tx, ty = 1160, 1180
    d.rectangle([tx, ty, W - 60, H - 60], outline=EDGE, width=3)
    rows = [("Part", str(info.get("title") or "Part")[:48]),
            ("Size (mm)", f"{bb.get('x', 0):g} x {bb.get('y', 0):g} x {bb.get('z', 0):g}"),
            ("Volume", f"{info.get('volume_mm3', 0):,.0f} mm³"),
            ("Units / scale", f"mm / {scale * 25.4 / 200:.2f} : 1 (A4)"),
            ("Made by", f"Hoola CAD Engineer · {date.today():%d %b %Y}"),
            ("Status", "DRAFT - for a qualified engineer's review, not certified")]
    y = ty + 18
    for k, val in rows:
        d.text((tx + 20, y), k, fill=(90, 98, 110), font=fs)
        d.text((tx + 260, y), val, fill=EDGE, font=fb if k == "Part" else f)
        y += 64
    d.text((90, H - 100), "Third-angle projection · dimensions in mm · overall sizes only (Phase 1)", fill=(90, 98, 110), font=fs)
    if info.get("material") or info.get("mass_g"):
        d.text((90, H - 140), f"Material: {info.get('material') or '-'} · mass about {info.get('mass_g', 0):,.0f} g",
               fill=(90, 98, 110), font=fs)
    extra = [p for p in [line_page(hlr or {}, info)] if p is not None]
    b = io.BytesIO()
    page.save(b, "PDF", resolution=200.0, save_all=bool(extra), append_images=extra)
    return b.getvalue()
