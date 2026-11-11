"""Figma file JSON -> Hoola Design nodes (docs/HOOLA_DESIGN_PLAN.md section 2 = the target, section 7A = the bridge).

Pure: no network, no database, no clock. `Converter(file_json, new_id).run()` walks the `document` of a Figma REST
`GET /v1/files/:key?geometry=paths` answer and produces ordered create ops (parents before children), plus what the
caller must still fetch: the image fills (`image_refs`) and the layers that could not be converted and are to be
replaced by Figma's own picture of them (`fallback`). `finish(images, renders)` fills those in and returns the ops.

Coordinates (the one place to get exactly right):
  Figma gives every node `relativeTransform` = [[a, c, e], [b, d, f]] mapping its own box (0..size.x, 0..size.y) into
  its CONTAINER: the nearest ancestor that is not a GROUP / BOOLEAN_OPERATION (groups have no coordinate space of
  their own in Figma). Hoola gives every node x, y, w, h, rot (degrees clockwise about the box centre) and flipH /
  flipV relative to its DIRECT parent's top-left - a Hoola GROUP does have a box. So each node's absolute matrix is
  built (container's absolute x relativeTransform; the result is checked against `absoluteBoundingBox`, and the
  direct-parent reading is taken instead when only that one matches), and the Hoola local matrix is
  inverse(Hoola parent's absolute) x the node's absolute, decomposed the way hd-core.js `store.move` does it:
  a mirror becomes flipH (flipV = flipH + 180 degrees), rot = atan2 of the first column.

Every Figma field that has no Hoola home is counted in `warnings` by name - nothing is dropped silently.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Callable

from . import fracidx
from .doc import FIRST_PAGE, ROOT

Matrix = tuple[float, float, float, float, float, float]       # canvas order: x' = a x + c y + e ; y' = b x + d y + f
IDENT: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
PATH_MAX = 200_000           # characters of one VECTOR path: an op over 256 KB is refused by the document rules
OV_MAX = 2000                # override entries on one instance
CONTAINERLESS = ("GROUP", "BOOLEAN_OPERATION")

FRAMEISH = {"FRAME": "FRAME", "COMPONENT": "COMPONENT", "COMPONENT_SET": "COMPONENT_SET", "SECTION": "SECTION",
            "INSTANCE": "INSTANCE"}
SHAPES = {"RECTANGLE", "ELLIPSE", "LINE", "REGULAR_POLYGON", "STAR", "VECTOR", "BOOLEAN_OPERATION", "TEXT"}
NO_BOOL = {"TEXT", "LINE"}                     # Hoola: text and lines take no part in a boolean
FALLBACK_TYPES = {"STICKY", "SHAPE_WITH_TEXT", "CONNECTOR", "WIDGET", "EMBED", "LINK_UNFURL", "MEDIA", "TABLE",
                  "TABLE_CELL", "WASHI_TAPE", "CODE_BLOCK", "STAMP", "HIGHLIGHT", "TEXT_PATH", "TRANSFORM_GROUP"}
SKIP_TYPES = {"SLICE"}

BLEND = {"PASS_THROUGH": None, "NORMAL": None, "DARKEN": "darken", "MULTIPLY": "multiply", "COLOR_BURN": "color-burn",
         "LIGHTEN": "lighten", "SCREEN": "screen", "COLOR_DODGE": "color-dodge", "OVERLAY": "overlay",
         "SOFT_LIGHT": "soft-light", "HARD_LIGHT": "hard-light", "DIFFERENCE": "difference", "EXCLUSION": "exclusion",
         "HUE": "hue", "SATURATION": "saturation", "COLOR": "color", "LUMINOSITY": "luminosity"}
SCALE_MODE = {"FILL": "fill", "FIT": "fit", "TILE": "tile", "STRETCH": "crop"}
ALIGN_MAIN = {"MIN": "start", "CENTER": "center", "MAX": "end", "SPACE_BETWEEN": "between"}
ALIGN_CROSS = {"MIN": "start", "CENTER": "center", "MAX": "end", "BASELINE": "start"}
CONS_H = {"LEFT": "left", "RIGHT": "right", "CENTER": "center", "LEFT_RIGHT": "leftright", "SCALE": "scale"}
CONS_V = {"TOP": "top", "BOTTOM": "bottom", "CENTER": "center", "TOP_BOTTOM": "topbottom", "SCALE": "scale"}
T_ALIGN = {"LEFT": "left", "CENTER": "center", "RIGHT": "right", "JUSTIFIED": "justify"}
T_ALIGN_V = {"TOP": "top", "CENTER": "middle", "BOTTOM": "bottom"}
T_RESIZE = {"WIDTH_AND_HEIGHT": "wh", "HEIGHT": "h", "NONE": "none", "TRUNCATE": "none"}
T_CASE = {"ORIGINAL": "none", "UPPER": "upper", "LOWER": "lower", "TITLE": "title"}
T_DECO = {"NONE": "none", "UNDERLINE": "underline", "STRIKETHROUGH": "strike"}
CAP = {"NONE": "butt", "ROUND": "round", "SQUARE": "square"}
JOIN = {"MITER": "miter", "BEVEL": "bevel", "ROUND": "round"}
ALIGN_STROKE = {"INSIDE": "inside", "OUTSIDE": "outside", "CENTER": "center"}
GRID_KIND = {"GRID": "grid", "COLUMNS": "columns", "ROWS": "rows"}
GRID_ALIGN = {"MIN": "start", "MAX": "end", "STRETCH": "stretch", "CENTER": "center"}
TRIGGER = {"ON_CLICK": "click", "ON_HOVER": "hover", "ON_PRESS": "press", "ON_DRAG": "drag", "AFTER_TIMEOUT": "after",
           "MOUSE_ENTER": "hover"}
NAV = {"NAVIGATE": "navigate", "OVERLAY": "overlay", "SWAP": "swap", "SCROLL_TO": "scroll", "CHANGE_TO": "navigate"}
ANIM = {"DISSOLVE": "dissolve", "SMART_ANIMATE": "smart", "MOVE_IN": "move", "MOVE_OUT": "moveout", "PUSH": "push",
        "SLIDE_IN": "slide", "SLIDE_OUT": "slideout", "SCROLL_ANIMATE": "smart"}
EASE = {"LINEAR": "linear", "EASE_IN": "in", "EASE_OUT": "out", "EASE_IN_AND_OUT": "inout", "EASE_IN_BACK": "in",
        "EASE_OUT_BACK": "out", "EASE_IN_AND_OUT_BACK": "inout", "GENTLE": "spring", "QUICK": "spring",
        "BOUNCY": "spring", "SLOW": "spring", "CUSTOM_SPRING": "spring"}
DIRECTION = {"LEFT": "left", "RIGHT": "right", "TOP": "up", "BOTTOM": "down"}
SCROLL = {"NONE": "none", "HORIZONTAL_SCROLLING": "h", "VERTICAL_SCROLLING": "v",
          "HORIZONTAL_AND_VERTICAL_SCROLLING": "both"}

# what an instance (or a layer inside it) may carry as its own look: compared with its component's value
LOOK_KEYS = ("fills", "strokes", "strokeWeight", "strokeAlign", "strokeCap", "strokeJoin", "dash", "radius", "effects",
             "opacity", "blend", "clip", "layout", "visible", "mask")
TEXT_KEYS = ("chars", "font", "fontSize", "fontWeight", "italic", "lineHeight", "letterSpacing", "align", "alignV",
             "decoration", "textCase", "runs")
OV_KEYS = LOOK_KEYS + TEXT_KEYS + ("comp",)
DEFAULTS: dict[str, Any] = {"fills": [], "strokes": [], "strokeWeight": 1, "strokeAlign": "center", "strokeCap": "butt",
                            "strokeJoin": "miter", "dash": [], "radius": 0, "effects": [], "opacity": 1, "blend": "normal",
                            "clip": False, "visible": True, "mask": False, "chars": "", "font": "Inter", "fontSize": 16,
                            "fontWeight": 400, "italic": False, "lineHeight": "auto", "letterSpacing": 0, "align": "left",
                            "alignV": "top", "decoration": "none", "textCase": "none", "runs": None, "comp": None,
                            "layout": None}


# ------------------------------------------------------------------------------------------------ numbers
def _f(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


def _r(v: float, places: int = 4) -> float | int:
    x = round(float(v), places)
    if x == 0:
        return 0
    return int(x) if x == int(x) else x


def hex_of(c: Any) -> str:
    c = c if isinstance(c, dict) else {}
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(_f(c.get(k)) * 255)))) for k in ("r", "g", "b"))


def mul(m: Matrix, n: Matrix) -> Matrix:
    """m x n: n is applied first (world = mul(parent, local)) - hd-math.js `mul`."""
    return (m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
            m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5])


def inv(m: Matrix) -> Matrix:
    det = m[0] * m[3] - m[1] * m[2]
    if not det or not math.isfinite(det):
        return IDENT
    a, b, c, d = m[3] / det, -m[1] / det, -m[2] / det, m[0] / det
    return (a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5]))


def apply(m: Matrix, x: float, y: float) -> tuple[float, float]:
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def translate(x: float, y: float) -> Matrix:
    return (1.0, 0.0, 0.0, 1.0, float(x), float(y))


def from_figma(rt: Any) -> Matrix | None:
    """Figma's [[m00, m01, m02], [m10, m11, m12]] -> canvas order, or None when it is not a usable matrix."""
    try:
        (a, c, e), (b, d, f) = rt[0][:3], rt[1][:3]
        out = tuple(float(v) for v in (a, b, c, d, e, f))
    except (TypeError, ValueError, IndexError):
        return None
    return out if all(math.isfinite(v) for v in out) else None          # type: ignore[return-value]


def node_matrix(x: float, y: float, w: float, h: float, rot: float, flip_h: bool, flip_v: bool) -> Matrix:
    """hd-math.js nodeMatrix: translate(x, y) x rotate about the box centre (degrees clockwise) x flips about it."""
    t = math.radians(rot or 0.0)
    c, s = math.cos(t), math.sin(t)
    fx, fy = (-1 if flip_h else 1), (-1 if flip_v else 1)
    a, b, cc, d = c * fx, s * fx, -s * fy, c * fy
    cx, cy = w / 2, h / 2
    return (a, b, cc, d, x + cx - (a * cx + cc * cy), y + cy - (b * cx + d * cy))


def decompose(m: Matrix, w: float, h: float) -> tuple[dict, bool]:
    """A local matrix -> {x, y, rot, flipH} for a w x h box (hd-core.js store.move's rule). The bool says the matrix
    also scaled or skewed (which a Hoola node can not hold: the box size already carries the size)."""
    a, b, c, d = m[0], m[1], m[2], m[3]
    det = a * d - b * c
    fx = -1.0 if det < 0 else 1.0
    rot = math.degrees(math.atan2(b * fx, a * fx))
    rot = rot - 360 if rot > 180 else rot + 360 if rot <= -180 else rot
    cx, cy = apply(m, w / 2, h / 2)
    out = {"x": _r(cx - w / 2), "y": _r(cy - h / 2)}
    rr = _r(rot, 4)
    if rr:
        out["rot"] = rr
    if fx < 0:
        out["flipH"] = True
    odd = abs(math.hypot(a, b) - 1) > 1e-3 or abs(math.hypot(c, d) - 1) > 1e-3 or abs(a * c + b * d) > 1e-3
    return out, odd


def aabb(m: Matrix, w: float, h: float) -> tuple[float, float, float, float]:
    pts = [apply(m, x, y) for x, y in ((0, 0), (w, 0), (w, h), (0, h))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


# ------------------------------------------------------------------------------------------------- paths
_TOK = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_path(d: str) -> tuple[list[tuple], bool]:
    """SVG path data -> absolute segments ('M', x, y) ('L', x, y) ('C', x1, y1, x2, y2, x, y) ('Z',) and whether an
    arc had to be drawn as a straight line (Figma's own geometry never uses arcs)."""
    toks = _TOK.findall(d or "")
    out: list[tuple] = []
    i, cmd, cx, cy, sx, sy, lx, ly, last, arc = 0, "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "", False

    def num() -> float:
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    def has_num(k: int) -> bool:
        return i + k <= len(toks) and all(not t.isalpha() for t in toks[i:i + k])
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
        elif not cmd:
            break
        rel, up = cmd.islower(), cmd.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if up == "Z":
            out.append(("Z",))
            cx, cy, last, cmd = sx, sy, "Z", ""
            continue
        need = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[up]
        if not has_num(need):
            break
        if up == "M":
            cx, cy = num() + ox, num() + oy
            sx, sy = cx, cy
            out.append(("M", cx, cy))
            cmd = "l" if rel else "L"
        elif up == "L":
            cx, cy = num() + ox, num() + oy
            out.append(("L", cx, cy))
        elif up == "H":
            cx = num() + ox
            out.append(("L", cx, cy))
        elif up == "V":
            cy = num() + oy
            out.append(("L", cx, cy))
        elif up == "C":
            a, b, c2, e, x, y = num() + ox, num() + oy, num() + ox, num() + oy, num() + ox, num() + oy
            out.append(("C", a, b, c2, e, x, y))
            lx, ly, cx, cy = c2, e, x, y
        elif up == "S":
            sm = last in ("C", "S")
            a, b = (2 * cx - lx, 2 * cy - ly) if sm else (cx, cy)
            c2, e, x, y = num() + ox, num() + oy, num() + ox, num() + oy
            out.append(("C", a, b, c2, e, x, y))
            lx, ly, cx, cy = c2, e, x, y
        elif up in ("Q", "T"):
            if up == "Q":
                qx, qy = num() + ox, num() + oy
            else:
                sm = last in ("Q", "T")
                qx, qy = (2 * cx - lx, 2 * cy - ly) if sm else (cx, cy)
            x, y = num() + ox, num() + oy
            out.append(("C", cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y))
            lx, ly, cx, cy = qx, qy, x, y
        else:                                                   # A: rx ry phi large sweep x y -> a straight line
            for _ in range(5):
                num()
            cx, cy = num() + ox, num() + oy
            out.append(("L", cx, cy))
            arc = True
        last = up
    return out, arc


def path_bounds(segs: list[tuple]) -> tuple[float, float, float, float] | None:
    """The true bounds of the drawn curve (hd-render.js pathBBox: end points + cubic extrema)."""
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    px = py = 0.0

    def pt(x: float, y: float) -> None:
        nonlocal x0, y0, x1, y1
        x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    for sg in segs:
        if sg[0] == "Z":
            continue
        if sg[0] != "C":
            px, py = sg[1], sg[2]
            pt(px, py)
            continue
        pt(sg[5], sg[6])
        for k in (0, 1):
            p0, p1, p2, p3 = (py if k else px), sg[1 + k], sg[3 + k], sg[5 + k]
            A, B, C = -p0 + 3 * p1 - 3 * p2 + p3, 2 * (p0 - 2 * p1 + p2), p1 - p0
            ts = []
            if abs(A) < 1e-12:
                if abs(B) > 1e-12:
                    ts.append(-C / B)
            else:
                disc = B * B - 4 * A * C
                if disc >= 0:
                    sq = math.sqrt(disc)
                    ts += [(-B + sq) / (2 * A), (-B - sq) / (2 * A)]
            for t in ts:
                if 0 < t < 1:
                    u = 1 - t
                    v = u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3
                    if k:
                        y0, y1 = min(y0, v), max(y1, v)
                    else:
                        x0, x1 = min(x0, v), max(x1, v)
        px, py = sg[5], sg[6]
    return None if x0 == math.inf else (x0, y0, x1, y1)


def _n(v: float) -> str:
    s = f"{round(v, 3):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def path_text(segs: list[tuple], dx: float = 0.0, dy: float = 0.0) -> str:
    out = []
    for sg in segs:
        if sg[0] == "Z":
            out.append("Z")
            continue
        pts = sg[1:]
        out.append(sg[0] + " ".join(_n(v + (dx if j % 2 == 0 else dy)) for j, v in enumerate(pts)))
    return " ".join(out)


def poly_points(sides: int, ratio: float, star: bool) -> list[tuple[float, float]]:
    """hd-render.js polyPoints: the corners in the 0..1 box (first one at the top centre, clockwise)."""
    n = sides * 2 if star else sides
    raw = []
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        r = ratio if star and i % 2 else 1.0
        raw.append((math.cos(a) * r, math.sin(a) * r))
    x0, x1 = min(p[0] for p in raw), max(p[0] for p in raw)
    y0, y1 = min(p[1] for p in raw), max(p[1] for p in raw)
    return [((x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)) for x, y in raw]


def _match_points(pts: list[tuple[float, float]], want: list[tuple[float, float]], w: float, h: float) -> float:
    """The largest distance (in layer units) from a wanted corner to its nearest real one; inf when counts differ."""
    if len(pts) != len(want):
        return math.inf
    worst = 0.0
    for wx, wy in want:
        worst = max(worst, min(math.hypot(wx * w - px, wy * h - py) for px, py in pts))
    return worst


# ------------------------------------------------------------------------------------------------ the converter
class Converter:
    def __init__(self, file_json: dict, new_id: Callable[[], str], max_nodes: int = 200_000):
        self.file = file_json if isinstance(file_json, dict) else {}
        self.new_id = new_id
        self.cap = max(1, int(max_nodes))
        self.ops: list[tuple[str, dict]] = []
        self.props: dict[str, dict] = {}          # hoola id -> props (the same dict objects as in ops)
        self.fid2hid: dict[str, str] = {}
        self.chain: dict[str, list[str]] = {}     # figma id of a node inside a component -> hoola path from it
        self.warn: Counter = Counter()
        self.image_refs: set[str] = set()
        self.fallback: dict[str, str] = {}        # hoola id -> figma id of a layer drawn by Figma's own render
        self.pending: list[tuple[dict, str, dict]] = []    # (figma instance, hoola id, its props)
        self.reacts: list[tuple[dict, list]] = []
        self.flow_starts: dict[str, str] = {}     # figma frame id -> flow name
        self.styles: dict[str, dict] = {}
        self.count = 2                            # the root and the first page already exist in a new file
        self.over_cap = 0
        self.components: set[str] = set()
        self.quiet = False                        # True while the layers inside an instance are read (no double counts)
        self._scan(self.file.get("document") or {})

    # ---------------------------------------------------------------- bookkeeping
    def w(self, text: str, n: int = 1) -> None:
        if not self.quiet:
            self.warn[text] += n

    def _scan(self, node: dict, depth: int = 0) -> None:
        stack = [node]
        while stack:
            n = stack.pop()
            if not isinstance(n, dict):
                continue
            if n.get("type") == "COMPONENT" and isinstance(n.get("id"), str):
                self.components.add(n["id"])
            stack.extend(c for c in (n.get("children") or []) if isinstance(c, dict))

    def _emit(self, hid: str, props: dict) -> None:
        self.ops.append((hid, props))
        self.props[hid] = props

    def warnings(self) -> list[dict]:
        out = [{"text": t, "count": c} for t, c in self.warn.most_common()]
        if self.over_cap:
            out.insert(0, {"text": f"Layers not imported: the file is over the {self.cap:,}-layer limit of one Hoola Design file",
                           "count": self.over_cap})
        return out

    # ---------------------------------------------------------------- the walk
    def run(self) -> "Converter":
        doc = self.file.get("document") or {}
        pages = [c for c in (doc.get("children") or []) if isinstance(c, dict)]
        if not pages:
            self.w("The Figma file has no pages")
        keys = fracidx.n_between(None, None, max(1, len(pages)))
        for i, canvas in enumerate(pages):
            if canvas.get("type") != "CANVAS":
                self.w(f"Top-level {canvas.get('type')} that is not a page (not imported)")
                continue
            if i and self.count >= self.cap:
                self.over_cap += 1 + self._descendants(canvas)
                continue
            hid = FIRST_PAGE if i == 0 else self.new_id()
            if i:
                self.count += 1
            p: dict[str, Any] = {"name": str(canvas.get("name") or f"Page {i + 1}")[:200], "idx": keys[i]}
            if i:
                p.update(type="PAGE", parent=ROOT)
            bg = canvas.get("backgroundColor")
            if isinstance(bg, dict):
                p["bg"] = hex_of(bg)
            self.fid2hid[str(canvas.get("id"))] = hid
            self._emit(hid, p)
            start = canvas.get("prototypeStartNodeID")
            if isinstance(start, str):
                self.flow_starts.setdefault(start, "")
            for fl in canvas.get("flowStartingPoints") or []:
                if isinstance(fl, dict) and isinstance(fl.get("nodeId"), str):
                    self.flow_starts[fl["nodeId"]] = str(fl.get("name") or "")[:120]
            if canvas.get("prototypeDevice") and (canvas["prototypeDevice"] or {}).get("type") not in (None, "NONE"):
                self.w("Prototype device frame setting (not imported)")
            self._children(canvas, hid, IDENT, IDENT, IDENT, None, None)
        for fn, hid, props in self.pending:
            self._instance(fn, hid, props)
        self._reactions()
        if self.styles:
            self._emit(ROOT, {"styles": self.styles})
        return self

    def _children(self, fparent: dict, hparent: str, parent_abs: Matrix, container_abs: Matrix, hparent_abs: Matrix,
                  layout_mode: str | None, comp_chain: list[str] | None) -> None:
        kids = [c for c in (fparent.get("children") or []) if isinstance(c, dict)]
        keys = fracidx.n_between(None, None, len(kids))
        for kid, key in zip(kids, keys):
            self._node(kid, hparent, key, parent_abs, container_abs, hparent_abs, layout_mode, fparent, comp_chain)

    def _abs(self, fn: dict, parent_abs: Matrix, container_abs: Matrix, fparent: dict | None) -> tuple[Matrix, float, float]:
        """The node's absolute matrix and box size, read from relativeTransform (checked against absoluteBoundingBox)."""
        size = fn.get("size") if isinstance(fn.get("size"), dict) else None
        bb = fn.get("absoluteBoundingBox") if isinstance(fn.get("absoluteBoundingBox"), dict) else None
        rt = from_figma(fn.get("relativeTransform"))
        w = _f(size.get("x")) if size else _f(bb.get("width")) if bb else 0.0
        h = _f(size.get("y")) if size else _f(bb.get("height")) if bb else 0.0
        if rt is None:
            if bb:
                if size and (abs(w - _f(bb.get("width"))) > 0.5 or abs(h - _f(bb.get("height"))) > 0.5):
                    self.w("Layer without a transform: its rotation could not be read (placed by its outer box)")
                    w, h = _f(bb.get("width")), _f(bb.get("height"))
                return translate(_f(bb.get("x")), _f(bb.get("y"))), w, h
            self.w("Layer without a position (placed at 0, 0)")
            return parent_abs, w, h
        cand = mul(container_abs, rt)
        if bb and fparent is not None and fparent.get("type") in CONTAINERLESS:
            want = (_f(bb.get("x")), _f(bb.get("y")), _f(bb.get("width")), _f(bb.get("height")))

            def off(m: Matrix) -> float:
                return max(abs(a - b) for a, b in zip(aabb(m, w, h), want))
            alt = mul(parent_abs, rt)
            if off(cand) > 0.5 and off(alt) <= 0.5:
                cand = alt
        return cand, w, h

    def _kind(self, fn: dict) -> str | None:
        t = fn.get("type")
        if t in FRAMEISH:
            if t == "INSTANCE" and fn.get("componentId") not in self.components:
                return "FRAME"                                   # detached: its component is not in this file
            return FRAMEISH[t]
        if t == "GROUP":
            return "GROUP"
        if t == "RECTANGLE":
            return "RECT"
        if t == "ELLIPSE":
            arc = fn.get("arcData") if isinstance(fn.get("arcData"), dict) else None
            if arc and (abs(_f(arc.get("endingAngle"), 2 * math.pi) - _f(arc.get("startingAngle"))) < 2 * math.pi - 1e-6
                        or _f(arc.get("innerRadius")) > 0):
                return "VECTOR"
            return "ELLIPSE"
        if t == "LINE":
            return "LINE"
        if t in ("REGULAR_POLYGON", "STAR"):
            return t                                             # decided against the geometry in _shape
        if t == "VECTOR":
            return "VECTOR"
        if t == "BOOLEAN_OPERATION":
            return "BOOL"
        if t == "TEXT":
            return "TEXT"
        if t in SKIP_TYPES:
            return None
        return "FALLBACK"

    def _node(self, fn: dict, hparent: str, idx: str, parent_abs: Matrix, container_abs: Matrix, hparent_abs: Matrix,
              layout_mode: str | None, fparent: dict, comp_chain: list[str] | None) -> None:
        fid = str(fn.get("id") or "")
        ftype = str(fn.get("type") or "?")
        kind = self._kind(fn)
        if kind is None:
            self.w("Export slices (not imported: Hoola keeps export settings on layers instead)")
            return
        if self.count >= self.cap:
            self.over_cap += 1 + self._descendants(fn)
            return
        fabs, w, h = self._abs(fn, parent_abs, container_abs, fparent)
        props: dict[str, Any] = {"name": str(fn.get("name") or ftype.title())[:200]}
        box_abs = fabs
        if kind == "FALLBACK":
            if fn.get("absoluteBoundingBox"):
                kind = "RECT"
                self.w(f"{ftype.replace('_', ' ').title()} layers (no Hoola equivalent: kept as Figma's picture of them)")
                hid = self.new_id()
                self.fallback[hid] = fid
                props["fills"] = [{"type": "image", "hash": None, "_render": fid, "mode": "fill", "opacity": 1}]
            else:
                self.w(f"{ftype} layers (not imported)")
                return
        else:
            hid = self.new_id()
        if kind in ("REGULAR_POLYGON", "STAR", "VECTOR", "BOOL"):
            kind, extra, box = self._shape(fn, kind, w, h)
            if kind is None:
                return
            props.update(extra)
            if box is not None:
                x0, y0, bw, bh = box
                box_abs, w, h = mul(fabs, translate(x0, y0)), bw, bh
        props["type"] = kind
        props["parent"] = hparent
        props["idx"] = idx
        local = mul(inv(hparent_abs), box_abs)
        geo, odd = decompose(local, w, h)
        if odd:
            self.w("Layers scaled or skewed by their transform (only rotation and mirroring are kept)")
        props.update(geo)
        props["w"] = _r(max(0.0, w))
        props["h"] = _r(max(0.0, h)) if kind != "LINE" else 0
        self.fid2hid[fid] = hid
        if comp_chain is not None:
            chain = comp_chain + [hid]
            self.chain[fid] = chain
        else:
            chain = None
        if ftype == "COMPONENT":
            chain = []
            self.chain[fid] = []
        props.update(self._look(fn, kind, hid))
        self._in_layout(fn, props, layout_mode, kind)
        if kind == "TEXT":
            props.update(self._text(fn))
        if ftype == "COMPONENT":
            if fn.get("description"):
                props["desc"] = str(fn["description"])[:2000]
        self.count += 1
        self._emit(hid, props)
        if fid in self.flow_starts:
            props["protoStart"] = True
            if self.flow_starts[fid]:
                props["flowName"] = self.flow_starts[fid]
        if fn.get("reactions") or fn.get("interactions"):
            self.reacts.append((props, fn.get("interactions") or fn.get("reactions") or []))
        if kind == "INSTANCE":
            self.pending.append((fn, hid, props))
            return                                               # an instance's layers come from its component
        if ftype == "INSTANCE":
            self.w("Instances of a component that is not in this file (kept as frames, detached)")
        if kind in ("FRAME", "COMPONENT", "COMPONENT_SET", "SECTION", "GROUP", "BOOL"):
            is_container = ftype not in CONTAINERLESS
            mode = (props.get("layout") or {}).get("mode") if isinstance(props.get("layout"), dict) else None
            self._children(fn, hid, fabs, fabs if is_container else container_abs, box_abs,
                           mode if mode in ("h", "v") else None, chain)
            if ftype in ("COMPONENT", "COMPONENT_SET"):
                self._cprops(fn, props, hid)

    def _descendants(self, fn: dict) -> int:
        n, stack = 0, list(fn.get("children") or [])
        while stack:
            c = stack.pop()
            if isinstance(c, dict):
                n += 1
                stack.extend(c.get("children") or [])
        return n

    # ---------------------------------------------------------------- geometry kinds
    def _geometry(self, fn: dict) -> tuple[list[tuple], str, bool]:
        """(segments, fill rule, from the stroke) of the node's own geometry; [] when there is none."""
        fill = [g for g in (fn.get("fillGeometry") or []) if isinstance(g, dict) and isinstance(g.get("path"), str)]
        src, stroke = fill, False
        if not src:
            src = [g for g in (fn.get("strokeGeometry") or []) if isinstance(g, dict) and isinstance(g.get("path"), str)]
            stroke = bool(src)
        segs: list[tuple] = []
        rules = set()
        for g in src:
            s, arc = parse_path(g["path"])
            if arc:
                self.w("Arc commands in a path (drawn as straight lines)")
            segs += s
            rules.add(str(g.get("windingRule") or "NONZERO").upper())
        if len(rules) > 1:
            self.w("Vectors whose parts use different fill rules (one rule kept)")
        rule = "evenodd" if "EVENODD" in rules and len(rules) == 1 else "nonzero"
        return segs, rule, stroke

    def _shape(self, fn: dict, kind: str, w: float, h: float) -> tuple[str | None, dict, tuple | None]:
        if kind == "BOOL":
            op = str(fn.get("booleanOperation") or "UNION").lower()
            kids = [c for c in (fn.get("children") or []) if isinstance(c, dict)]
            if kids and op in ("union", "subtract", "intersect", "exclude") and not self._has(kids, NO_BOOL | FALLBACK_TYPES):
                return "GROUP", {"bool": op}, None
            self.w("Boolean groups holding text or lines (kept as one flat vector)")
            kind = "VECTOR"
        segs, rule, stroke = self._geometry(fn)
        if kind in ("REGULAR_POLYGON", "STAR"):
            got = self._regular(segs, kind == "STAR", w, h)
            if got is not None:
                return got[0], got[1], None
            kind = "VECTOR"
        if not segs:
            if fn.get("type") == "VECTOR" or kind == "VECTOR":
                self.w("Vectors with no geometry in the file (not imported)")
            return None, {}, None
        b = path_bounds(segs)
        if b is None:
            return None, {}, None
        x0, y0, x1, y1 = b
        d = path_text(segs, -x0, -y0)
        if len(d) > PATH_MAX:
            self.w("Vectors too detailed for one layer (not imported)")
            return None, {}, None
        extra: dict[str, Any] = {"path": d}
        if rule == "evenodd":
            extra["fillRule"] = "evenodd"
        if stroke:
            extra["_stroke_outline"] = True
            self.w("Open vector strokes (imported as outlined shapes)")
        return "VECTOR", extra, (x0, y0, x1 - x0, y1 - y0)

    def _has(self, kids: list, types: set) -> bool:
        stack = list(kids)
        while stack:
            c = stack.pop()
            if not isinstance(c, dict):
                continue
            if c.get("type") in types:
                return True
            stack.extend(c.get("children") or [])
        return False

    def _regular(self, segs: list[tuple], star: bool, w: float, h: float) -> tuple[str, dict] | None:
        """POLYGON / STAR when the geometry is exactly Hoola's own shape (sharp corners); else None (-> VECTOR)."""
        if not segs or segs[0][0] != "M" or any(s[0] not in ("M", "L", "Z") for s in segs) or \
                sum(1 for s in segs if s[0] == "M") != 1:
            return None
        pts = [(s[1], s[2]) for s in segs if s[0] in ("M", "L")]
        if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-6:
            pts = pts[:-1]
        tol = max(0.5, 0.01 * max(w, h))
        if not star:
            n = len(pts)
            if 3 <= n <= 60 and _match_points(pts, poly_points(n, 1, False), w, h) <= tol:
                return "POLYGON", {"sides": n}
            return None
        if len(pts) % 2 or not 6 <= len(pts) <= 120:
            return None
        n = len(pts) // 2
        best, best_r = math.inf, 0.5
        for k in range(1, 1000):
            r = k / 1000
            e = _match_points(pts, poly_points(n, r, True), w, h)
            if e < best:
                best, best_r = e, r
        if best <= tol:
            return "STAR", {"sides": n, "ratio": _r(best_r, 3)}
        return None

    # ---------------------------------------------------------------- the look
    def _paint(self, pt: Any, what: str) -> dict | None:
        if not isinstance(pt, dict):
            return None
        t = str(pt.get("type") or "")
        op = _f(pt.get("opacity"), 1.0)
        out: dict[str, Any]
        if t == "SOLID":
            col = pt.get("color") or {}
            out = {"type": "solid", "color": hex_of(col), "opacity": _r(op * _f(col.get("a"), 1.0), 4)}
        elif t in ("GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "GRADIENT_DIAMOND"):
            kind = {"GRADIENT_LINEAR": "linear", "GRADIENT_RADIAL": "radial", "GRADIENT_ANGULAR": "angular",
                    "GRADIENT_DIAMOND": "radial"}[t]
            if t == "GRADIENT_DIAMOND":
                self.w("Diamond gradients (drawn as radial gradients)")
            hs = [(_f(p.get("x")), _f(p.get("y"))) for p in (pt.get("gradientHandlePositions") or []) if isinstance(p, dict)]
            if len(hs) < 2:
                hs = [(0.5, 0.0), (0.5, 1.0)] if kind == "linear" else [(0.5, 0.5), (1.0, 0.5)]
            stops = []
            for s in pt.get("gradientStops") or []:
                if isinstance(s, dict):
                    c = s.get("color") or {}
                    stops.append({"pos": _r(min(1.0, max(0.0, _f(s.get("position")))), 4), "color": hex_of(c),
                                  "opacity": _r(_f(c.get("a"), 1.0), 4)})
            stops.sort(key=lambda s: s["pos"])
            out = {"type": kind, "stops": stops, "from": [_r(hs[0][0]), _r(hs[0][1])], "to": [_r(hs[1][0]), _r(hs[1][1])],
                   "opacity": _r(op, 4)}
            if kind == "radial" and len(hs) >= 3:
                r1 = math.hypot(hs[1][0] - hs[0][0], hs[1][1] - hs[0][1])
                r2 = math.hypot(hs[2][0] - hs[0][0], hs[2][1] - hs[0][1])
                if abs(r1 - r2) > 0.02 * max(r1, r2, 1e-9):
                    self.w("Radial gradients with two different radii (drawn with one)")
        elif t == "IMAGE":
            ref = pt.get("imageRef")
            if not isinstance(ref, str) or not ref:
                self.w("Image fills without a picture in the file")
                return None
            self.image_refs.add(ref)
            mode = str(pt.get("scaleMode") or "FILL")
            out = {"type": "image", "hash": None, "_ref": ref, "mode": SCALE_MODE.get(mode, "fill"), "opacity": _r(op, 4)}
            if mode == "STRETCH" and pt.get("imageTransform"):
                self.w("Cropped image fills (the crop is not kept: the picture fills the layer)")
            if pt.get("filters") and any(_f(v) for v in (pt.get("filters") or {}).values()):
                self.w("Image adjustments (exposure, contrast ...) (not imported)")
            if _f(pt.get("rotation")):
                self.w("Rotated image fills (not rotated)")
        elif t in ("EMOJI", "VIDEO"):
            self.w(f"{t.title()} {what}s (not imported)")
            return None
        else:
            self.w(f"{t or 'Unknown'} {what}s (not imported)")
            return None
        if pt.get("visible") is False:
            out["visible"] = False
        elif t == "SOLID":
            out["visible"] = True
        bm = str(pt.get("blendMode") or "NORMAL")
        if bm not in ("NORMAL", "PASS_THROUGH"):
            self.w("Blend modes on single fills (the fill is drawn normally)")
        return out

    def _paints(self, items: Any, what: str) -> list[dict]:
        if not isinstance(items, list):
            return []
        return [p for p in (self._paint(x, what) for x in items) if p is not None]

    def _effects(self, fn: dict) -> list[dict]:
        out = []
        for e in fn.get("effects") or []:
            if not isinstance(e, dict):
                continue
            t = e.get("type")
            vis = e.get("visible") is not False
            if t in ("DROP_SHADOW", "INNER_SHADOW"):
                c, off = e.get("color") or {}, e.get("offset") or {}
                out.append({"type": "drop" if t == "DROP_SHADOW" else "inner", "x": _r(_f(off.get("x"))),
                            "y": _r(_f(off.get("y"))), "blur": _r(_f(e.get("radius"))), "spread": _r(_f(e.get("spread"))),
                            "color": hex_of(c), "opacity": _r(_f(c.get("a"), 1.0), 4), "visible": vis})
                if str(e.get("blendMode") or "NORMAL") != "NORMAL":
                    self.w("Shadow blend modes (drawn normally)")
            elif t in ("LAYER_BLUR", "BACKGROUND_BLUR"):
                out.append({"type": "blur" if t == "LAYER_BLUR" else "bgblur", "blur": _r(_f(e.get("radius"))), "visible": vis})
            else:
                self.w(f"{str(t).replace('_', ' ').title()} effects (not imported)")
        return out

    def _look(self, fn: dict, kind: str, hid: str) -> dict:
        p: dict[str, Any] = {}
        if fn.get("visible") is False:
            p["visible"] = False
        if fn.get("locked"):
            p["locked"] = True
        op = _f(fn.get("opacity"), 1.0)
        if op < 1:
            p["opacity"] = _r(op, 4)
        bm = str(fn.get("blendMode") or "PASS_THROUGH")
        if bm in BLEND:
            if BLEND[bm]:
                p["blend"] = BLEND[bm]
        else:
            self.w(f"{bm.replace('_', ' ').title()} blend mode (drawn normally)")
        if fn.get("isMask"):
            p["mask"] = True
            if str(fn.get("maskType") or "ALPHA") == "LUMINANCE":
                self.w("Luminance masks (used as alpha masks)")
        fills = self._paints(fn.get("fills"), "fill")
        strokes = self._paints(fn.get("strokes"), "stroke")
        if kind == "GROUP" and fn.get("type") == "GROUP":
            fills, strokes = [], []                               # a Figma group has no look of its own
        if fills:
            p["fills"] = fills
        if strokes:
            p["strokes"] = strokes
            sw = _f(fn.get("strokeWeight"), 1.0)
            if sw != 1:
                p["strokeWeight"] = _r(sw)
            isw = fn.get("individualStrokeWeights")
            if isinstance(isw, dict) and len({_f(v) for v in isw.values()}) > 1:
                p["strokeWeight"] = _r(max(_f(v) for v in isw.values()))
                self.w("Different stroke weights per side (the widest is used on every side)")
            al = ALIGN_STROKE.get(str(fn.get("strokeAlign") or "CENTER"), "center")
            if al != "center":
                p["strokeAlign"] = al
            cap = str(fn.get("strokeCap") or "NONE")
            if cap in CAP:
                if CAP[cap] != "butt":
                    p["strokeCap"] = CAP[cap]
            else:
                self.w("Arrow and other stroke end caps (drawn as plain ends)")
            jn = JOIN.get(str(fn.get("strokeJoin") or "MITER"), "miter")
            if jn != "miter":
                p["strokeJoin"] = jn
            dash = [_r(_f(v)) for v in (fn.get("strokeDashes") or []) if _f(v) >= 0]
            if dash:
                p["dash"] = dash
        rad = fn.get("rectangleCornerRadii")
        if isinstance(rad, list) and len(rad) == 4 and len({_f(v) for v in rad}) > 1:
            p["radius"] = [_r(_f(v)) for v in rad]
        elif _f(fn.get("cornerRadius")) > 0 and kind in ("RECT", "FRAME", "COMPONENT", "INSTANCE", "COMPONENT_SET", "SECTION"):
            p["radius"] = _r(_f(fn.get("cornerRadius")))
        elif isinstance(rad, list) and len(rad) == 4 and _f(rad[0]) > 0:
            p["radius"] = _r(_f(rad[0]))
        if _f(fn.get("cornerSmoothing")) > 0:
            self.w("Smooth corners (drawn as plain round corners)")
        eff = self._effects(fn)
        if eff:
            p["effects"] = eff
        if kind in ("FRAME", "COMPONENT", "INSTANCE", "COMPONENT_SET"):
            p["clip"] = fn.get("clipsContent") is not False
            lay = self._layout(fn)
            if lay:
                p["layout"] = lay
            grids = self._grids(fn)
            if grids:
                p["grids"] = grids
            ov = SCROLL.get(str(fn.get("overflowDirection") or "NONE"), "none")
            if ov != "none":
                p["scroll"] = ov
        if fn.get("isFixed") or str(fn.get("scrollBehavior") or "") in ("FIXED", "STICKY_SCROLLS"):
            p["fixed"] = True
            if fn.get("scrollBehavior") == "STICKY_SCROLLS":
                self.w("Sticky scrolling layers (kept fixed)")
        cons = fn.get("constraints")
        if isinstance(cons, dict):
            c = {"h": CONS_H.get(str(cons.get("horizontal")), "left"), "v": CONS_V.get(str(cons.get("vertical")), "top")}
            if c != {"h": "left", "v": "top"}:
                p["cons"] = c
        exp = []
        for e in fn.get("exportSettings") or []:
            if not isinstance(e, dict):
                continue
            fmt = str(e.get("format") or "PNG").lower()
            fmt = "jpg" if fmt == "jpeg" else fmt
            if fmt not in ("png", "jpg", "svg", "pdf"):
                self.w(f"{fmt.upper()} export settings (not imported)")
                continue
            con = e.get("constraint") if isinstance(e.get("constraint"), dict) else {}
            scale = _f(con.get("value"), 1.0) if str(con.get("type") or "SCALE") == "SCALE" else 1.0
            if con and str(con.get("type") or "SCALE") != "SCALE":
                self.w("Export settings sized by width or height (exported at 1x)")
            exp.append({"fmt": fmt, "scale": _r(scale or 1), "suffix": str(e.get("suffix") or "")[:60]})
        if exp:
            p["exports"] = exp
        st = fn.get("styles") if isinstance(fn.get("styles"), dict) else {}
        for skind, key in (("fill", "fill"), ("fill", "fills"), ("effect", "effect"), ("effect", "effects")):
            sid = st.get(key)
            if isinstance(sid, str) and (fills if skind == "fill" else p.get("effects")):
                self._style(sid, skind, p["fills"] if skind == "fill" else p["effects"], p)
        if any(k in st for k in ("stroke", "strokes", "grid")):
            self.w("Stroke and grid styles (the values are kept, the link to the style is not)")
        if fn.get("boundVariables"):
            self.w("Variable bindings (the values are kept, the link to the variable is not)")
        return p

    def _style(self, sid: str, kind: str, value: Any, p: dict) -> None:
        meta = (self.file.get("styles") or {}).get(sid) if isinstance(self.file.get("styles"), dict) else None
        hs = "fs_" + re.sub(r"[^A-Za-z0-9]+", "_", sid)[:40]
        if hs not in self.styles:
            self.styles[hs] = {"kind": kind, "name": str((meta or {}).get("name") or sid)[:200], "value": value}
        p[{"fill": "fillStyle", "effect": "effectStyle", "text": "textStyle"}[kind]] = hs

    def _layout(self, fn: dict) -> dict | None:
        mode = str(fn.get("layoutMode") or "NONE")
        if mode == "NONE":
            return None
        if mode not in ("HORIZONTAL", "VERTICAL"):
            self.w("Grid auto layout (not imported: children keep their places)")
            return None
        pad = [_r(_f(fn.get(k), _f(fn.get(alt)))) for k, alt in (("paddingTop", "verticalPadding"),
                                                                  ("paddingRight", "horizontalPadding"),
                                                                  ("paddingBottom", "verticalPadding"),
                                                                  ("paddingLeft", "horizontalPadding"))]
        out = {"mode": "h" if mode == "HORIZONTAL" else "v", "gap": _r(_f(fn.get("itemSpacing"))), "pad": pad,
               "alignMain": ALIGN_MAIN.get(str(fn.get("primaryAxisAlignItems") or "MIN"), "start"),
               "alignCross": ALIGN_CROSS.get(str(fn.get("counterAxisAlignItems") or "MIN"), "start"),
               "wrap": str(fn.get("layoutWrap") or "NO_WRAP") == "WRAP"}
        if fn.get("counterAxisAlignItems") == "BASELINE":
            self.w("Baseline alignment in auto layout (aligned to the start)")
        if out["wrap"] and fn.get("counterAxisSpacing") is not None and _f(fn.get("counterAxisSpacing")) != out["gap"]:
            self.w("A different gap between wrapped rows (the item gap is used)")
        if fn.get("itemReverseZIndex"):
            self.w("Auto layout stacking reversed (first on top) (not imported)")
        if fn.get("strokesIncludedInLayout"):
            self.w("Strokes counted in auto layout (not imported)")
        return out

    def _grids(self, fn: dict) -> list[dict]:
        out = []
        for g in fn.get("layoutGrids") or []:
            if not isinstance(g, dict):
                continue
            c = g.get("color") or {}
            kind = GRID_KIND.get(str(g.get("pattern") or "GRID"), "grid")
            item = {"type": kind, "size": _r(_f(g.get("sectionSize"), 10)), "count": int(_f(g.get("count"), 0)),
                    "gutter": _r(_f(g.get("gutterSize"))), "margin": _r(_f(g.get("offset"))),
                    "align": GRID_ALIGN.get(str(g.get("alignment") or "STRETCH"), "stretch"), "color": hex_of(c),
                    "opacity": _r(_f(c.get("a"), 0.1), 4), "visible": g.get("visible") is not False}
            out.append(item)
        return out

    def _in_layout(self, fn: dict, p: dict, parent_mode: str | None, kind: str) -> None:
        """sizeH / sizeV (fixed | hug | fill), layoutPos and min / max sizes. Newer files say it outright
        (layoutSizingHorizontal / Vertical); older ones through the axis fields (primary / counterAxisSizingMode on
        the frame, layoutGrow / layoutAlign on the child)."""
        size = {"FIXED": "fixed", "HUG": "hug", "FILL": "fill"}
        own = (p.get("layout") or {}).get("mode") if isinstance(p.get("layout"), dict) else None
        gh = gv = "fixed"
        if own in ("h", "v"):
            prim = str(fn.get("primaryAxisSizingMode") or "FIXED") == "AUTO"
            cnt = str(fn.get("counterAxisSizingMode") or "FIXED") == "AUTO"
            main, cross = ("hug" if prim else "fixed"), ("hug" if cnt else "fixed")
            gh, gv = (main, cross) if own == "h" else (cross, main)
        if parent_mode in ("h", "v"):
            grow = _f(fn.get("layoutGrow")) > 0
            stretch = str(fn.get("layoutAlign") or "INHERIT") == "STRETCH"
            if parent_mode == "h":
                gh, gv = ("fill" if grow else gh), ("fill" if stretch else gv)
            else:
                gh, gv = ("fill" if stretch else gh), ("fill" if grow else gv)
        h = size.get(str(fn.get("layoutSizingHorizontal")), gh)
        v = size.get(str(fn.get("layoutSizingVertical")), gv)
        if kind == "TEXT":                                      # a text sizes itself through autoResize
            h, v = (h if h == "fill" else "fixed"), (v if v == "fill" else "fixed")
        if parent_mode not in ("h", "v"):                       # fill means nothing outside auto layout
            h, v = (h if h != "fill" else "fixed"), (v if v != "fill" else "fixed")
        if h != "fixed":
            p["sizeH"] = h
        if v != "fixed":
            p["sizeV"] = v
        if parent_mode in ("h", "v") and str(fn.get("layoutPositioning") or "AUTO") == "ABSOLUTE":
            p["layoutPos"] = "absolute"
        for fk, hk in (("minWidth", "minW"), ("maxWidth", "maxW"), ("minHeight", "minH"), ("maxHeight", "maxH")):
            if fn.get(fk) is not None and _f(fn.get(fk), -1) >= 0:
                p[hk] = _r(_f(fn.get(fk)))

    # ---------------------------------------------------------------- text
    def _tstyle(self, st: dict, base_size: float | None = None) -> dict:
        out: dict[str, Any] = {}
        if not isinstance(st, dict):
            return out
        if st.get("fontFamily"):
            out["font"] = str(st["fontFamily"])[:120]
        size = _f(st.get("fontSize"), 0) or None
        if size:
            out["fontSize"] = _r(size)
        if st.get("fontWeight") is not None:
            out["fontWeight"] = int(_f(st.get("fontWeight"), 400))
        if "italic" in st:
            out["italic"] = bool(st.get("italic"))
        unit = str(st.get("lineHeightUnit") or "")
        fs = size or base_size or 16
        if unit == "INTRINSIC_%":
            out["lineHeight"] = "auto"
        elif unit == "FONT_SIZE_%" and st.get("lineHeightPercentFontSize") is not None:
            out["lineHeight"] = _r(_f(st.get("lineHeightPercentFontSize")) / 100 * fs, 3)
        elif st.get("lineHeightPx") is not None and unit in ("PIXELS", ""):
            out["lineHeight"] = _r(_f(st.get("lineHeightPx")), 3)
        if st.get("letterSpacing") is not None:
            out["letterSpacing"] = _r(_f(st.get("letterSpacing")), 3)
        if st.get("textAlignHorizontal"):
            out["align"] = T_ALIGN.get(str(st["textAlignHorizontal"]), "left")
        if st.get("textAlignVertical"):
            out["alignV"] = T_ALIGN_V.get(str(st["textAlignVertical"]), "top")
        tc = st.get("textCase")
        if tc:
            if tc in T_CASE:
                out["textCase"] = T_CASE[tc]
            else:
                self.w("Small caps (shown in normal letters)")
        td = st.get("textDecoration")
        if td:
            out["decoration"] = T_DECO.get(str(td), "none")
        if isinstance(st.get("fills"), list):
            out["fills"] = self._paints(st["fills"], "text fill")
        if _f(st.get("paragraphSpacing")) or _f(st.get("paragraphIndent")):
            self.w("Paragraph spacing and indents (not imported)")
        if st.get("hyperlink"):
            self.w("Links inside text (the words are kept, the link is not)")
        if st.get("listSpacing") or st.get("textTruncation") == "ENDING":
            self.w("List spacing and truncated text endings (not imported)")
        return out

    def _text(self, fn: dict) -> dict:
        st = fn.get("style") if isinstance(fn.get("style"), dict) else {}
        p: dict[str, Any] = {"chars": str(fn.get("characters") or "")}
        base = self._tstyle(st)
        base.pop("fills", None)
        p.update({"font": "Inter", "fontSize": 16, "fontWeight": 400})
        p.update(base)
        ar = str(st.get("textAutoResize") or fn.get("textAutoResize") or "NONE")
        p["autoResize"] = T_RESIZE.get(ar, "none")
        if ar == "TRUNCATE":
            self.w("Truncated text boxes (the text is kept whole)")
        if any(t not in (None, "NONE") for t in (fn.get("lineTypes") or [])):
            self.w("Bulleted and numbered lists (kept as plain lines)")
        overrides = fn.get("characterStyleOverrides") or []
        table = fn.get("styleOverrideTable") if isinstance(fn.get("styleOverrideTable"), dict) else {}
        runs = []
        if isinstance(overrides, list) and overrides:
            start, cur = 0, None
            seq = [int(_f(v)) for v in overrides] + [0]
            for i, sid in enumerate(seq):
                if sid != cur:
                    if cur:
                        style = self._tstyle(table.get(str(cur)) or {}, _f(base.get("fontSize"), 16))
                        if style:
                            runs.append({"s": start, "e": i, **style})
                    start, cur = i, sid
        if runs:
            p["runs"] = runs
        sid = (fn.get("styles") or {}).get("text") if isinstance(fn.get("styles"), dict) else None
        if isinstance(sid, str):
            self._style(sid, "text", {k: p[k] for k in ("font", "fontSize", "fontWeight", "italic", "lineHeight",
                                                        "letterSpacing", "decoration", "textCase") if k in p}, p)
        return p

    # ---------------------------------------------------------------- components
    def _cprops(self, fn: dict, props: dict, hid: str) -> None:
        defs = fn.get("componentPropertyDefinitions") if isinstance(fn.get("componentPropertyDefinitions"), dict) else {}
        if not defs:
            return
        kinds = {"TEXT": "text", "BOOLEAN": "bool", "INSTANCE_SWAP": "swap"}
        comps = [fn] if fn.get("type") == "COMPONENT" else [c for c in (fn.get("children") or [])
                                                            if isinstance(c, dict) and c.get("type") == "COMPONENT"]
        for comp in comps:
            chid = self.fid2hid.get(str(comp.get("id")))
            if not chid:
                continue
            out = []
            stack = [c for c in (comp.get("children") or []) if isinstance(c, dict)]
            while stack:
                n = stack.pop()
                refs = n.get("componentPropertyReferences") if isinstance(n.get("componentPropertyReferences"), dict) else {}
                for field, key in refs.items():
                    d = defs.get(key) if isinstance(defs.get(key), dict) else None
                    kind = kinds.get(str((d or {}).get("type")))
                    chain = self.chain.get(str(n.get("id")))
                    if not d or not kind or chain is None:
                        continue
                    if (kind, field) not in (("text", "characters"), ("bool", "visible"), ("swap", "mainComponent")):
                        continue
                    dv = d.get("defaultValue")
                    if kind == "swap":
                        dv = self.fid2hid.get(str(dv), "")
                    out.append({"id": re.sub(r"[^A-Za-z0-9]+", "_", key)[:60], "name": key.split("#")[0][:120],
                                "type": kind, "target": "/".join(chain), "def": dv})
                if n.get("type") != "INSTANCE":
                    stack.extend(c for c in (n.get("children") or []) if isinstance(c, dict))
            if out:
                self.props[chid]["cprops"] = out
        if any(isinstance(d, dict) and d.get("type") not in ("TEXT", "BOOLEAN", "INSTANCE_SWAP", "VARIANT")
               for d in defs.values()):
            self.w("Component properties of other kinds (not imported)")

    def _virtual(self, fn: dict, out: dict[str, dict]) -> None:
        """The look of every layer inside an instance, keyed by its Figma id (no ops: an instance has no layers)."""
        for kid in fn.get("children") or []:
            if not isinstance(kid, dict):
                continue
            kind = self._kind(kid) or "SKIP"
            if kind in ("FALLBACK", "SKIP"):
                continue
            if kind in ("BOOL",):
                kind = "GROUP"
            p = self._look(kid, kind, "")
            if kind == "TEXT":
                p.update(self._text(kid))
            if kid.get("type") == "INSTANCE":
                p["comp"] = self.fid2hid.get(str(kid.get("componentId")))
            out[str(kid.get("id"))] = p
            self._virtual(kid, out)

    def _segments(self, inst_id: str, dfid: str) -> list[str] | None:
        pre = (inst_id if inst_id.startswith("I") else "I" + inst_id) + ";"
        if not dfid.startswith(pre):
            return None
        return dfid[len(pre):].split(";")

    def _instance(self, fn: dict, hid: str, props: dict) -> None:
        comp = self.fid2hid.get(str(fn.get("componentId")))
        if comp is None or comp not in self.props:
            props["type"] = "FRAME"                              # the component was over the cap: keep the box
            self.w("Instances whose component could not be imported (kept as empty frames)")
            return
        props["comp"] = comp
        base = self.props[comp]
        for k in LOOK_KEYS:
            mine, theirs = props.get(k, DEFAULTS.get(k)), base.get(k, DEFAULTS.get(k))
            if k == "clip":
                mine, theirs = props.get(k, True), base.get(k, True)
            if mine == theirs:
                props.pop(k, None)
            elif k not in props:
                props[k] = DEFAULTS.get(k) if k != "clip" else True
        props.pop("cprops", None)
        virtual: dict[str, dict] = {}
        self.quiet = True
        try:
            self._virtual(fn, virtual)
        finally:
            self.quiet = False
        ov: dict[str, dict] = {}
        lost = 0
        for dfid, dp in virtual.items():
            segs = self._segments(str(fn.get("id")), dfid)
            if not segs:
                lost += 1
                continue
            # each segment's chain runs from ITS component's root: the full path is the chains one after another
            path: list[str] = []
            for seg in segs:
                ch = self.chain.get(seg)
                if ch is None:
                    path = []
                    break
                path.extend(ch)
            if not path:
                lost += 1
                continue
            last = self.fid2hid.get(segs[-1])
            bp = self.props.get(last or "", {})
            diff = {}
            for k in OV_KEYS:
                mine, theirs = dp.get(k, DEFAULTS.get(k)), bp.get(k, DEFAULTS.get(k))
                if k == "comp" and (mine is None or mine == theirs):
                    continue
                if mine != theirs and not (k in ("layout", "runs") and not mine and not theirs):
                    diff[k] = mine if mine is not None else DEFAULTS.get(k)
            if diff:
                ov["/".join(path)] = diff
        if lost:
            self.w("Instance overrides on layers that could not be matched to the component (not imported)", lost)
        if len(ov) > OV_MAX:
            self.w("Instance overrides over the limit of one instance (the rest not imported)", len(ov) - OV_MAX)
            ov = dict(list(ov.items())[:OV_MAX])
        if ov:
            props["ov"] = ov

    # ---------------------------------------------------------------- prototype
    def _reactions(self) -> None:
        for props, items in self.reacts:
            out = []
            for r in items:
                if not isinstance(r, dict):
                    continue
                trig = r.get("trigger") if isinstance(r.get("trigger"), dict) else {}
                t = TRIGGER.get(str(trig.get("type")))
                acts = r.get("actions") if isinstance(r.get("actions"), list) else [r.get("action")]
                acts = [a for a in acts if isinstance(a, dict)]
                if not t or not acts:
                    self.w("Prototype triggers with no Hoola equivalent (not imported)")
                    continue
                if len(acts) > 1:
                    self.w("Prototype interactions with several actions (the first one kept)")
                a = acts[0]
                item: dict[str, Any] = {"trigger": t}
                if t == "after":
                    tm = _f(trig.get("timeout"), 0.8)
                    item["delay"] = int(round(tm * 1000 if tm < 30 else tm))
                at = str(a.get("type") or "")
                if at == "BACK":
                    item["action"] = "back"
                elif at == "CLOSE":
                    item["action"] = "close"
                elif at == "URL":
                    item["action"] = "url"
                    item["url"] = str(a.get("url") or "")[:2000]
                elif at == "NODE":
                    nav = NAV.get(str(a.get("navigation") or "NAVIGATE"))
                    dest = self.fid2hid.get(str(a.get("destinationId")))
                    if not nav or not dest:
                        self.w("Prototype links to layers that were not imported")
                        continue
                    item["action"], item["to"] = nav, dest
                else:
                    self.w("Prototype actions with no Hoola equivalent (variables, conditions, media ...)")
                    continue
                tr = a.get("transition") if isinstance(a.get("transition"), dict) else None
                if tr:
                    anim = ANIM.get(str(tr.get("type")))
                    if not anim:
                        self.w("Prototype animations with no Hoola equivalent (instant)")
                        anim = "instant"
                    dur = _f(tr.get("duration"), 0.3)
                    ease = (tr.get("easing") or {}).get("type") if isinstance(tr.get("easing"), dict) else None
                    item["anim"] = {"type": anim, "dir": DIRECTION.get(str(tr.get("direction") or "LEFT"), "left"),
                                    "dur": int(round(dur * 1000 if dur < 30 else dur)), "ease": EASE.get(str(ease), "out")}
                    if str(ease) == "CUSTOM_CUBIC_BEZIER":
                        self.w("Custom animation curves (ease out used)")
                else:
                    item["anim"] = {"type": "instant", "dir": "left", "dur": 0, "ease": "out"}
                out.append(item)
            if out:
                props["reactions"] = out

    # ---------------------------------------------------------------- the end
    def finish(self, images: dict[str, str], renders: dict[str, str]) -> list[dict]:
        """Put the stored pictures in (imageRef / Figma id -> asset hash); a paint whose picture is missing is
        dropped and counted; a fallback layer without its picture is removed. Returns the ops, parents first."""
        dead: set[str] = set()
        missing = 0
        for hid, props in self.ops:
            for key in ("fills", "strokes"):
                paints = props.get(key)
                if not isinstance(paints, list):
                    continue
                keep = []
                for pnt in paints:
                    if pnt.get("type") == "image" and ("_ref" in pnt or "_render" in pnt):
                        got = images.get(pnt.pop("_ref")) if "_ref" in pnt else renders.get(pnt.pop("_render"))
                        if not got:
                            if hid in self.fallback:
                                dead.add(hid)
                            else:
                                missing += 1
                            continue
                        pnt["hash"] = got
                    keep.append(pnt)
                props[key] = keep
                if not keep:
                    props.pop(key)
            if props.pop("_stroke_outline", False):            # an open stroke came as its outline: paint it as a fill
                props["fills"] = props.pop("strokes", props.get("fills", []))
                for k in ("strokeWeight", "strokeAlign", "strokeCap", "strokeJoin", "dash"):
                    props.pop(k, None)
                if not props["fills"]:
                    props.pop("fills")
        for style in self.styles.values():                    # a fill style shares its paints with the layers
            if style.get("kind") == "fill" and isinstance(style.get("value"), list):
                style["value"] = [q for q in style["value"] if q.get("type") != "image" or q.get("hash")]
        if missing:
            self.w("Image fills whose picture could not be downloaded (not imported)", missing)
        if dead:
            self.w("Layers Figma could not draw a picture of (not imported)", len(dead))
        out = []
        for hid, props in self.ops:
            if hid in dead or props.get("parent") in dead:
                dead.add(hid)
                continue
            out.append({"id": hid, "p": props})
        return out

