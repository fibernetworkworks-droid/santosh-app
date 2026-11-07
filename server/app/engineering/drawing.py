"""v0.395 REAL DRAWINGS (server side): an A3 shop drawing as a VECTOR PDF from the box's drawing.json.

- Three orthographic views from the kernel's hidden-line removal at ONE standard scale (ISO 5455), first angle by
  default (India, IS / SP 46; ISO E) or third angle on request; hidden lines dashed, centre marks on every hole.
- Real dimensions measured from the geometry: overall size (no duplicates across views), hole positions as
  baseline (ordinate-style) chains from the part's corner, hole CALLOUTS grouped by kind ("4× Ø5.5 THRU",
  "Ø6.6 THRU / CBORE Ø11 DEEP 6.5", "Ø5 DEEP 8", "CSK Ø12 × 90°"), radius callouts ("4× R5"), outside diameters.
- Tolerances: a fit she asked for (H.fit) printed with its ISO 286 limits ("Ø20 H7 (+0.021/0)"), and the general
  tolerance class (ISO 2768-m by default) as note 1.
- ISO 7200-style title block: title, part no., material, mass, scale, projection symbol, units, sheet, date,
  revision = the version, drawn by Hoola, DRAFT status. Page 2 keeps the shaded views.
Every number on the sheet is measured, none typed - a changed model changes its drawing."""
from __future__ import annotations

import io
import math
import re
from datetime import date
from typing import Any

from . import calc

W, H = 420.0, 297.0                                  # A3 landscape, mm
FRAME = (20.0, 10.0, 410.0, 287.0)                   # left binding margin 20 (ISO 5457)
TB = (230.0, 10.0, 410.0, 66.0)                      # title block
SCALES = [(10, 1), (5, 1), (2, 1), (1, 1), (1, 2), (1, 5), (1, 10), (1, 20), (1, 50), (1, 100)]
TXT = 3.5                                            # text height mm


def tol_text(d: float, code: str) -> str:
    """'H7' / 'g6' / 'H7/g6' -> ' H7 (+0.021/0)'. Hole basis only for holes; shafts by letter."""
    code = str(code).strip()
    m = re.fullmatch(r"([A-Za-z]{1,2})(\d{1,2})", code)
    if not m:
        return f" {code}"
    letter, grade = m.group(1), int(m.group(2))
    if grade not in calc.IT:
        return f" {code}"
    i = calc._ri(float(d))
    it = calc.IT[grade][i] / 1000
    if letter == "H":
        lo, hi = 0.0, it
    elif letter in calc.SHAFT_ES:
        es = calc.SHAFT_ES[letter][i] / 1000
        lo, hi = es - it, es
    elif letter in calc.SHAFT_EI:
        ei = calc.SHAFT_EI[letter][i] / 1000
        lo, hi = ei, ei + it
    elif letter == "js":
        lo, hi = -it / 2, it / 2
    else:
        return f" {code}"

    def f(x):
        return "0" if abs(x) < 1e-9 else f"{x:+.3f}"
    return f" {code} ({f(hi)}/{f(lo)})"


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".") if abs(x - round(x)) > 1e-6 else str(int(round(x)))


def _counts(data: dict, side: str) -> dict[str, dict[str, int]]:
    out = {}
    for n in ("front", "top", side):
        hs = [h for h in data.get("holes") or [] if h["view"] == n]
        out[n] = {"nx": min(8, len({round(h["c"][0], 3) for h in hs})), "ny": min(8, len({round(h["c"][1], 3) for h in hs}))}
    return out


def pick_scale(data: dict, side: str, first: bool) -> tuple[float, str, dict]:
    v = data["views"]
    cnt = _counts(data, side)
    upper, lower = ("front", "top") if first else ("top", "front")
    top_m = 14 + 7 * (cnt[upper]["nx"] + (1 if upper == "front" else 0))
    bot_m = 14 + 7 * (cnt[lower]["nx"] + (1 if lower == "front" else 0))
    n_left = len([h for h in data.get("holes") or [] if h["view"] in ("front", "top")])
    gap_v = 22 + 6.5 * min(4, n_left)
    gap_h = 20 + 7 * max(cnt["front"]["ny"], cnt["top"]["ny"]) + 6
    fw, fh = v["front"]["box"][2] - v["front"]["box"][0], v["front"]["box"][3] - v["front"]["box"][1]
    tw, th = v["top"]["box"][2] - v["top"]["box"][0], v["top"]["box"][3] - v["top"]["box"][1]
    sw, sh = v[side]["box"][2] - v[side]["box"][0], v[side]["box"][3] - v[side]["box"][1]
    x0, y0, x1, y1 = FRAME
    for a, b in SCALES:
        s = a / b
        col1 = max(fw, tw) * s
        need_w = 34 + col1 + gap_h + sw * s + 22 + 7 * cnt[side]["ny"]
        need_h = top_m + fh * s + gap_v + th * s + bot_m
        if need_w > (x1 - x0) or need_h > (y1 - y0):
            continue
        left = x0 + 34
        if first:                                     # front on top, top view below it
            front_y = y1 - top_m - fh * s
            top_y = front_y - gap_v - th * s
        else:                                         # top view above the front
            top_y = y1 - top_m - th * s
            front_y = top_y - gap_v - fh * s
        side_x = left + col1 + gap_h
        place = {"front": (left, front_y), "top": (left, top_y), side: (side_x, front_y)}
        # nothing may sit on the title block
        boxes = {"front": (fw, fh), "top": (tw, th), side: (sw, sh)}
        clash = False
        for n, (ox, oy) in place.items():
            w_, h_ = boxes[n][0] * s, boxes[n][1] * s
            if oy < y0 + 4 or ox + w_ > x1 - 4:
                clash = True
            if ox + w_ + 6 > TB[0] and oy - (bot_m if n == lower else 12) < TB[3]:
                clash = True
        if clash:
            continue
        return s, (f"{a}:{b}"), place
    s = 0.01
    return s, "NTS", {"front": (x0 + 34, y1 - 120), "top": (x0 + 34, y1 - 220), side: (x0 + 200, y1 - 120)}


class Sheet:
    def __init__(self, c):
        self.c = c
        self.texts: list[tuple[float, float, float, float]] = []

    def free(self, x0, y0, x1, y1) -> bool:
        for a in self.texts:
            if not (x1 < a[0] or x0 > a[2] or y1 < a[1] or y0 > a[3]):
                return False
        return True

    def text(self, x, y, s, size=TXT, anchor="middle", angle=0.0):
        from reportlab.lib.units import mm
        c = self.c
        c.saveState()
        c.translate(x * mm, y * mm)
        c.rotate(angle)
        fs = size * mm / 0.72                        # cap height ~ 0.72 em -> the text is `size` mm tall
        c.setFont("Helvetica", fs)
        wdt = c.stringWidth(s, "Helvetica", fs) / mm
        dx = {"middle": -wdt / 2, "start": 0.0, "end": -wdt}[anchor]
        c.drawString(dx * mm, 0, s)
        c.restoreState()
        if angle:
            self.texts.append((x - size, y + dx, x + 0.5, y + dx + wdt))
        else:
            self.texts.append((x + dx, y - 0.6, x + dx + wdt, y + size))
        return wdt

    def line(self, pts, width=0.25, dash=None, gray=0.0):
        from reportlab.lib.units import mm
        c = self.c
        c.setLineWidth(width * mm)
        c.setStrokeGray(gray)
        c.setDash([d * mm for d in dash] if dash else [])
        p = c.beginPath()
        p.moveTo(pts[0][0] * mm, pts[0][1] * mm)
        for x, y in pts[1:]:
            p.lineTo(x * mm, y * mm)
        c.drawPath(p, stroke=1, fill=0)
        c.setDash([])

    def arrow(self, tip, toward):
        from reportlab.lib.units import mm
        dx, dy = toward[0] - tip[0], toward[1] - tip[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        a, w = 3.0, 0.9
        base = (tip[0] + ux * a, tip[1] + uy * a)
        p = self.c.beginPath()
        p.moveTo(tip[0] * mm, tip[1] * mm)
        p.lineTo((base[0] - uy * w) * mm, (base[1] + ux * w) * mm)
        p.lineTo((base[0] + uy * w) * mm, (base[1] - ux * w) * mm)
        p.close()
        self.c.setFillGray(0)
        self.c.drawPath(p, stroke=0, fill=1)

    def dim_h(self, xa, ya, xb, yb, y, txt):
        """Horizontal dimension between feature points A and B, dimension line at y."""
        for x, yy in ((xa, ya), (xb, yb)):
            s = 1.0 if y > yy else -1.0
            self.line([(x, yy + s * 1.2), (x, y + s * 2.0)], 0.18)
        self.line([(xa, y), (xb, y)], 0.18)
        if abs(xb - xa) > 8:
            self.arrow((xa, y), (xb, y))
            self.arrow((xb, y), (xa, y))
        else:
            self.arrow((xa, y), (xa - 5, y))
            self.arrow((xb, y), (xb + 5, y))
        self.text((xa + xb) / 2, y + 1.0, txt)

    def dim_v(self, xa, ya, xb, yb, x, txt):
        for xx, y in ((xa, ya), (xb, yb)):
            s = 1.0 if x > xx else -1.0
            self.line([(xx + s * 1.2, y), (x + s * 2.0, y)], 0.18)
        self.line([(x, ya), (x, yb)], 0.18)
        if abs(yb - ya) > 8:
            self.arrow((x, ya), (x, yb))
            self.arrow((x, yb), (x, ya))
        else:
            self.arrow((x, ya), (x, ya - 5))
            self.arrow((x, yb), (x, yb + 5))
        self.text(x - 1.0, (ya + yb) / 2, txt, angle=90)

    def leader(self, tip, txt, toward):
        """Leader from a feature point to text placed at `toward` (sheet mm), with a short knee."""
        kx = toward[0]
        self.line([tip, toward], 0.18)
        right = kx >= tip[0]
        self.line([toward, (toward[0] + (6 if right else -6), toward[1])], 0.18)
        self.arrow(tip, toward)
        self.text(toward[0] + (7 if right else -7), toward[1] - 1.2, txt, anchor="start" if right else "end")


def make(data: dict, info: dict, iso_png: bytes | None = None) -> bytes:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    first = data.get("projection", "first") != "third"
    side = "left" if first else "right"
    s, scale_txt, place = pick_scale(data, side, first)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W * mm, H * mm), invariant=1)
    c.setTitle(str(info.get("title") or "Part"))
    c.setAuthor("Hoola CAD Engineer")
    sh = Sheet(c)
    # frame + centring marks
    x0, y0, x1, y1 = FRAME
    sh.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], 0.7)
    for (a, b, cx, cy) in (((W / 2, y0), (W / 2, y0 - 5), 0, 0), ((W / 2, y1), (W / 2, y1 + 5), 0, 0),
                           ((x0, H / 2), (x0 - 5, H / 2), 0, 0), ((x1, H / 2), (x1 + 5, H / 2), 0, 0)):
        sh.line([a, b], 0.5)

    def to_sheet(view, p):
        bx = data["views"][view]["box"]
        ox, oy = place[view]
        return (ox + (p[0] - bx[0]) * s, oy + (p[1] - bx[1]) * s)

    # views
    for name in ("front", "top", side):
        v = data["views"][name]
        for pl in v["hid"]:
            sh.line([to_sheet(name, p) for p in pl], 0.18, dash=(1.6, 0.8), gray=0.35)
        for pl in v["vis"]:
            sh.line([to_sheet(name, p) for p in pl], 0.5)
        bx = v["box"]
        ox, oy = place[name]
        sh.texts.append((ox - 2, oy - 2, ox + (bx[2] - bx[0]) * s + 2, oy + (bx[3] - bx[1]) * s + 2))   # keep clear

    def corners(view):
        bx = data["views"][view]["box"]
        a = to_sheet(view, (bx[0], bx[1]))
        b = to_sheet(view, (bx[2], bx[3]))
        return a, b, bx
    # overall size: width + height on the front, depth on the top view
    (fa, fb, fbx) = corners("front")
    levels = set()                                     # step heights: every level a long horizontal edge sits at
    fw_ = fbx[2] - fbx[0]
    for pl in data["views"]["front"]["vis"]:
        if len(pl) == 2 and abs(pl[0][1] - pl[1][1]) < 1e-3 and abs(pl[0][0] - pl[1][0]) > 0.04 * fw_:
            y = round(pl[0][1], 3)
            if fbx[1] + 0.05 < y < fbx[3] - 0.05:
                levels.add(y)
    levels = sorted(levels)[:4]
    for k, yv in enumerate(levels):                    # shorter dimensions sit closer to the part
        py = to_sheet("front", (0, yv))[1]
        sh.dim_v(fa[0], fa[1], fa[0], py, fa[0] - 9 - 7 * k, _fmt(yv - fbx[1]))
    if first:                                          # front is the upper view: width above it
        sh.dim_h(fa[0], fb[1], fb[0], fb[1], fb[1] + 8, _fmt(fbx[2] - fbx[0]))
    else:                                              # front is the lower view: width below it
        sh.dim_h(fa[0], fa[1], fb[0], fa[1], fa[1] - 8, _fmt(fbx[2] - fbx[0]))
    sh.dim_v(fa[0], fa[1], fa[0], fb[1], fa[0] - 9 - 7 * len(levels), _fmt(fbx[3] - fbx[1]))
    (ta, tb, tbx) = corners("top")
    sh.dim_v(ta[0], ta[1], ta[0], tb[1], ta[0] - 9, _fmt(tbx[3] - tbx[1]))
    # holes: centre marks, baseline positions, grouped callouts
    fits = info.get("fits") or []

    def fit_for(dia):
        for f in fits:
            if abs(float(f.get("d", -1)) - dia) < 0.01:
                return tol_text(dia, f.get("fit", ""))
        return ""
    holes = data.get("holes") or []
    groups: dict[tuple, list] = {}
    for hl in holes:
        key = (hl["view"], hl["dia"], hl["through"], hl["depth"], tuple(hl["cbore"] or ()), tuple(hl["csk"] or ()))
        groups.setdefault(key, []).append(hl)
        cx, cy = to_sheet(hl["view"], hl["c"])
        r = hl["dia"] / 2 * s
        e = r + 2.0
        sh.line([(cx - e, cy), (cx + e, cy)], 0.18, dash=(4, 1, 1, 1))
        sh.line([(cx, cy - e), (cx, cy + e)], 0.18, dash=(4, 1, 1, 1))
    for view in ("top", "front", side):
        vh = [h for h in holes if h["view"] == view]
        if not vh:
            continue
        a, b, bx = corners(view)
        xs = sorted({round(h["c"][0], 3) for h in vh})[:8]
        ys = sorted({round(h["c"][1], 3) for h in vh})[:8]
        upper_v = "front" if first else "top"
        outer_up = view == upper_v                            # chains go on the view's OUTER side
        extra = 7 if view == "front" else 0                   # past the overall width on the front
        for k, xv in enumerate(xs):                          # baseline from the left edge
            px = to_sheet(view, (xv, 0))[0]
            if outer_up:
                sh.dim_h(a[0], b[1], px, b[1], b[1] + 9 + extra + 7 * k, _fmt(xv - bx[0]))
            else:
                sh.dim_h(a[0], a[1], px, a[1], a[1] - 9 - extra - 7 * k, _fmt(xv - bx[0]))
        for k, yv in enumerate(ys):                          # baseline from the bottom edge, on the right
            py = to_sheet(view, (0, yv))[1]
            sh.dim_v(b[0], a[1], b[0], py, b[0] + 9 + 7 * k, _fmt(yv - bx[1]))
    n_ys = {}
    for view in ("top", "front", side):
        n_ys[view] = len({round(h["c"][1], 3) for h in holes if h["view"] == view})
    pending: dict[tuple, list] = {}
    for key, hs in groups.items():
        hl = hs[0]
        n = len(hs)
        t = (f"{n}× " if n > 1 else "") + f"Ø{_fmt(hl['dia'])}" + fit_for(hl["dia"])
        t += " THRU" if hl["through"] else (f" DEEP {_fmt(hl['depth'])}" if hl["depth"] else "")
        if hl["cbore"]:
            t += f" / CBORE Ø{_fmt(hl['cbore'][0])} DEEP {_fmt(hl['cbore'][1])}"
        if hl["csk"]:
            t += f" / CSK Ø{_fmt(hl['csk'][0])} × {_fmt(abs(hl['csk'][1]))}°"
        if hl.get("far"):
            t += " (FAR SIDE)"
        a_, b_, _bx = corners(hl["view"])
        mid = (a_[0] + b_[0]) / 2
        # the member of the group nearest a side edge leads, so the leader stays short
        lead = max(hs, key=lambda h: abs(to_sheet(h["view"], h["c"])[0] - mid))
        cxy = to_sheet(lead["view"], lead["c"])
        right = cxy[0] >= mid and lead["view"] in ("top", side)
        r = lead["dia"] / 2 * s
        tip = (cxy[0] + (r * 0.707 if right else -r * 0.707), cxy[1] + r * 0.707)
        pending.setdefault((lead["view"], right), []).append((tip, t))
    for (view, right), items in pending.items():
        a_, b_, _bx = corners(view)
        if not right:                     # callouts in the free band between the two rows, never off-sheet
            is_upper = view == ("front" if first else "top")
            step = -6.5 if is_upper else 6.5
            ty = (a_[1] - 8) if is_upper else (b_[1] + 7)
            for tip, t in sorted(items, key=lambda it: it[0][0]):
                tx = tip[0] + 4
                for _ in range(12):
                    wdt = 7 + 2.1 * len(t)
                    if sh.free(tx, ty - 1, tx + wdt, ty + TXT + 1):
                        break
                    ty += step
                sh.leader(tip, t, (tx, ty))
                ty += step
            continue
        tx = b_[0] + 9 + 7 * n_ys.get(view, 0) + 6
        last = None
        for tip, t in sorted(items, key=lambda it: -it[0][1]):
            ty = tip[1] + 6 if last is None else min(tip[1] + 6, last - 6.5)
            for _ in range(30):
                wdt = 7 + 2.1 * len(t)
                xa, xb = (tx, tx + wdt) if right else (tx - wdt, tx)
                if sh.free(xa, ty - 1, xb, ty + TXT + 1):
                    break
                ty -= 6.5
            sh.leader(tip, t, (tx, ty))
            last = ty
    # outside radii / diameters
    rgroups: dict[tuple, list] = {}
    for a_ in data.get("arcs") or []:
        rgroups.setdefault((a_["view"], a_["r"], a_["full"]), []).append(a_)
    for (view, r, full), arcs in list(rgroups.items())[:6]:
        a0 = arcs[0]
        n = len(arcs)
        t = (f"{n}× " if n > 1 else "") + (f"Ø{_fmt(2 * r)}" + fit_for(2 * r) if full else f"R{_fmt(r)}")
        tip = to_sheet(view, a0["at"])
        a, b, _bx = corners(view)
        left = tip[0] < (a[0] + b[0]) / 2
        tx = (a[0] - 12) if left else (b[0] + 12)
        ty = tip[1] + 8
        for _ in range(20):
            if sh.free(tx - (6 + 2.2 * len(t) if left else 0), ty - 1, tx + (0 if left else 6 + 2.2 * len(t)), ty + TXT + 1):
                break
            ty += 6
        sh.leader(tip, t, (tx, ty))
    # notes just above the title block, the isometric picture above them
    tol = str(info.get("tolerance") or "m")
    notes = [f"GENERAL TOLERANCES ISO 2768-{tol} UNLESS STATED.", "ALL DIMENSIONS IN MILLIMETRES.",
             "BREAK SHARP EDGES 0.2-0.5.", "DRAFT - FOR A QUALIFIED ENGINEER'S REVIEW, NOT CERTIFIED."]
    notes += [str(n_)[:70].upper() for n_ in (info.get("notes") or [])][:4]
    ny = TB[3] + 3 + 4.2 * (len(notes) - 1)
    for k, n_ in enumerate(notes):
        sh.text(TB[0] + 1, ny - 4.2 * k, f"{k + 1}. {n_}", size=2.3, anchor="start")
    sh.text(TB[0] + 1, ny + 5, "NOTES", size=2.8, anchor="start")
    notes_top = ny + 9
    if iso_png:
        from reportlab.lib.utils import ImageReader
        sx_end = max(place[n][0] + (data["views"][n]["box"][2] - data["views"][n]["box"][0]) * s
                     for n in ("front", "top", side) if place[n][1] < notes_top + 100)
        x_left = max(TB[0], sx_end + 30)
        top_lim = min([place[n][1] - 12 for n in ("front", "top", side)
                       if place[n][0] + (data["views"][n]["box"][2] - data["views"][n]["box"][0]) * s > x_left] or [y1 - 4])
        size_ = min(top_lim - notes_top, x1 - 4 - x_left, 110)
        while size_ >= 40:                                  # biggest square that touches no view, dimension or text
            done = False
            for yb in range(int(notes_top), int(y1 - 4 - size_) + 1, 4):
                if sh.free(x1 - 4 - size_, yb, x1 - 4, yb + size_):
                    c.drawImage(ImageReader(io.BytesIO(iso_png)), (x1 - 4 - size_) * mm, yb * mm, size_ * mm,
                                size_ * mm, preserveAspectRatio=True, mask="auto")
                    done = True
                    break
            if done:
                break
            size_ -= 8
    # title block
    tx0, ty0, tx1, ty1 = TB
    sh.line([(tx0, ty0), (tx1, ty0), (tx1, ty1), (tx0, ty1), (tx0, ty0)], 0.5)
    rows = [("TITLE", str(info.get("title") or "Part")[:40]),
            ("PART NO.", str(info.get("part_no") or info.get("pid") or "-")[:30]),
            ("MATERIAL", str(info.get("material") or "-")[:30]),
            ("MASS", f"{info['mass_g']:,.0f} g" if info.get("mass_g") else "-"),
            ("SCALE", scale_txt), ("UNITS", "mm"), ("SHEET", "A3, 1 OF 2"),
            ("REV", f"v{info.get('version', 1)}"), ("DATE", f"{date.today():%d %b %Y}"),
            ("DRAWN", "Hoola CAD Engineer"), ("STATUS", "DRAFT")]
    rh = (ty1 - ty0) / 6
    colw = (tx1 - tx0) / 2
    for k, (lab, val) in enumerate(rows):
        col, row = (0, k) if k < 6 else (1, k - 6)
        cx, cy = tx0 + col * colw, ty1 - (row + 1) * rh
        sh.line([(cx, cy), (cx + colw, cy)], 0.18)
        sh.text(cx + 2, cy + rh - 3.2, lab, size=2.0, anchor="start")
        sh.text(cx + 2, cy + 1.4, val, size=3.0 if lab != "TITLE" else 3.5, anchor="start")
    sh.line([(tx0 + colw, ty0), (tx0 + colw, ty1)], 0.18)
    # projection symbol in the last free cell
    px, py = tx0 + colw + 2, ty0 + 2
    sh.text(px + 34, py + 1.5, "FIRST ANGLE" if first else "THIRD ANGLE", size=2.2, anchor="start")
    _proj_symbol(sh, px + 6, py + rh / 2 - 1, first)
    c.showPage()
    c.save()
    return buf.getvalue()


def _proj_symbol(sh: Sheet, x: float, y: float, first: bool) -> None:
    """ISO 128 projection symbol: a cone frustum's side view and end view (circles)."""
    cone = [(x, y - 2.5), (x + 9, y - 4), (x + 9, y + 4), (x, y + 2.5), (x, y - 2.5)]
    cx = x + 18 if first else x + 4
    ox = x if first else x + 10
    sh.line([(p[0] - x + ox, p[1]) for p in cone], 0.25)
    for r in (2.5, 4.0):
        pts = [(cx + r * math.cos(t / 24 * 2 * math.pi), y + r * math.sin(t / 24 * 2 * math.pi)) for t in range(25)]
        sh.line(pts, 0.25)


def with_page2(sheet_pdf: bytes, page2_pdf: bytes | None) -> bytes:
    if not page2_pdf:
        return sheet_pdf
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for src in (sheet_pdf, page2_pdf):
        for pg in PdfReader(io.BytesIO(src)).pages:
            w.add_page(pg)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
