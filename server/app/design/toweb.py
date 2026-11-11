"""D7 bridge B: a Hoola Design frame -> Web Studio (docs/HOOLA_DESIGN_PLAN.md section 7 B).

Two halves:

1. `frame_to_html(doc, node_id, assets)` turns ONE frame into the HTML + CSS a person would write by hand: semantic
   tags (h1 / h2 / h3 / p by the size and weight order of the frame's texts, `<a class="btn">` for a frame that reads
   as a button, `<nav>` / `<header>` / `<footer>` by name, `<img>` with the layer name as its alt text, inline `<svg>`
   for vectors, polygons, stars and boolean groups), one class per layer named from the layer's own name (slugged,
   `d-` first so it never meets the website's own `.card` / `.btn` utilities, unique), and NO inline style and NO
   script, ever. Responsive by construction:
     - an auto layout frame is a flexbox (direction, gap, padding, alignment, wrap; fixed sizes get `max-width:100%`,
       fill = `flex:1`, hug = the content's size); a wide row turns into a column below 640 px, a narrow one wraps;
     - a frame WITHOUT auto layout keeps its composition: a box with the frame's own aspect ratio whose children are
       placed in container units (`cqw`), so the whole composition scales down like a picture instead of breaking;
       below 640 px a big one (wider than 400 px) becomes a stacked column in reading order (top to bottom, then left
       to right) and its pure decorations (shapes with no picture) are hidden - said in the warnings;
     - big type scales with the screen (`clamp`), long words wrap, nothing is wider than the screen.
   The CSS values follow the editor's own code export (hd-export.js `cssPairs`: the same gradient angle and stop
   maths, the same stroke = border / outline rule, the same shadow order) so "Copy as CSS" and the website agree.
   Anything that is not reproduced is NAMED in `warnings` (blend modes, blurs, masks, angular gradients in a shape,
   gradient strokes, fonts the website does not ship...) - nothing is dropped silently.

2. `send(...)` (POST /api/design/files/{id}/to-site) hands that section to Web Studio THROUGH Web Studio's own code:
   a new site is made by `site.service.new` (the builder's guards, numbering, preview token, legal pages), the code is
   cleaned by `site.code.clean` (= `build.sanitize_section`: no script / handler / outside file, CSS scoped to the
   section) exactly like a hand edit in the Studio's Code tab, the pictures go into the SITE's own photo store with
   `site.service.add_photo`, and the checked version is made by Web Studio's own save job (`_after_edit` for a section
   added to a built site, the `save` job for a new site). Nothing is published: going live stays her tap in Web Studio.
"""
from __future__ import annotations

import html as _html
import io
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.design.toweb")

FRAMES = frozenset({"FRAME", "COMPONENT", "INSTANCE", "SECTION", "COMPONENT_SET"})
CONTAINERS = FRAMES | {"GROUP"}
PATHY = frozenset({"VECTOR", "POLYGON", "STAR"})
SHAPES = frozenset({"RECT", "ELLIPSE", "LINE"}) | PATHY
PHONE = 640                     # the stacked / wrapped layout starts below this width
SMALL_COMPOSITION = 400         # a frame without auto layout this narrow keeps its composition on a phone
BAND = 960                      # a root frame this wide is a full-width band of the page
MAX_NODES = 4000
MAX_DEPTH = 40
BUTTON_WORDS = re.compile(r"button|btn|cta", re.I)
NAV_WORDS = re.compile(r"\b(nav|navbar|navigation|nav ?bar)\b", re.I)
GENERIC_NAME = re.compile(r"^\s*(frame|desktop|page|screen|artboard|group|section|web|phone|android|iphone|tablet|"
                          r"macbook|component|instance)(\s*[-\d.x ]*)?\s*$", re.I)
_FONT_DIR = Path(__file__).resolve().parent.parent / "site" / "assets" / "fonts"
KINDS_OK = ("FRAME", "COMPONENT", "INSTANCE", "SECTION")


class ToWebError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


# ------------------------------------------------------------------------------------------- small helpers
def _num(v: Any, d: float = 0.0) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return d
    return f if math.isfinite(f) else d


def _r(v: float, n: int = 2) -> str:
    s = f"{round(v, n):.{n}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _px(v: float) -> str:
    s = _r(v)
    return "0" if s == "0" else s + "px"


def _esc(s: Any) -> str:
    return _html.escape(str(s if s is not None else ""), quote=True)


def _hex_rgb(hx: Any) -> tuple[int, int, int, float]:
    x = str(hx or "").lstrip("#")
    if len(x) in (3, 4):
        x = "".join(c * 2 for c in x)
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", x):
        return 0, 0, 0, 1.0
    a = int(x[6:8], 16) / 255 if len(x) == 8 else 1.0
    return int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16), a


def _color(hx: Any, opacity: Any = 1) -> str:
    r, g, b, a = _hex_rgb(hx)
    a = max(0.0, min(1.0, a * (1.0 if opacity is None else _num(opacity, 1.0))))
    if a >= 1:
        return f"#{r:02X}{g:02X}{b:02X}"
    return f"rgba({r}, {g}, {b}, {_r(a, 3 if a < 0.1 else 2)})"


def _hex6(hx: Any) -> str:
    r, g, b, _a = _hex_rgb(hx)
    return f"#{r:02X}{g:02X}{b:02X}"


def slug(name: Any, fallback: str = "layer") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower().encode("ascii", "ignore").decode()).strip("-")[:32].strip("-")
    return s or fallback


def _vis(p: Any) -> bool:
    return isinstance(p, dict) and p.get("visible") is not False


# --------------------------------------------------------------------------------------- the node tree
class _V:
    """One node as the website sees it: an instance borrows from its component, overrides applied by path."""
    __slots__ = ("key", "n", "src", "ctx", "depth")

    def __init__(self, key: str, n: dict, src: str, ctx: list, depth: int):
        self.key, self.n, self.src, self.ctx, self.depth = key, n, src, ctx, depth

    @property
    def type(self) -> str:
        return str(self.n.get("type") or "")

    def get(self, k: str, d: Any = None) -> Any:
        v = self.n.get(k)
        return d if v is None else v


class _Tree:
    def __init__(self, nodes: dict[str, dict]):
        self.nodes = nodes
        kids: dict[str, list[tuple[str, str]]] = {}
        for nid, n in nodes.items():
            p = n.get("parent") if isinstance(n, dict) else None
            if p:
                kids.setdefault(p, []).append((str(n.get("idx") or ""), nid))
        self.kids = {p: [nid for _, nid in sorted(v)] for p, v in kids.items()}
        self.count = 0
        self.memo: dict[str, list[_V]] = {}

    def node(self, nid: str, props: dict | None = None, ctx: list | None = None, key: str = "", depth: int = 0) -> _V:
        n = dict(props if props is not None else self.nodes.get(nid) or {})
        src, ctx = nid, list(ctx or [])
        seen = set()
        while n.get("type") == "INSTANCE" and n.get("comp") in self.nodes and n["comp"] not in seen and len(seen) < 8:
            seen.add(n["comp"])
            comp = self.nodes[n["comp"]]
            merged = {k: v for k, v in comp.items() if k not in ("parent", "idx")}
            merged.update({k: v for k, v in n.items() if k not in ("comp", "ov")})
            merged["type"] = "INSTANCE" if comp.get("type") != "INSTANCE" else "INSTANCE"
            ov = n.get("ov") if isinstance(n.get("ov"), dict) else {}
            ctx = [(ov, "")] + ctx                    # an outer instance's overrides win over the inner one's own
            src = n["comp"]
            n = merged
            if comp.get("type") != "INSTANCE":
                break
        return _V(key or nid, n, src, ctx, depth)

    def children(self, v: _V) -> list[_V]:
        """Visible children (memoised per node, so every pass sees the SAME objects)."""
        if v.key in self.memo:
            return self.memo[v.key]
        out = []
        if v.depth >= MAX_DEPTH:
            self.memo[v.key] = out
            return out
        for cid in self.kids.get(v.src, []):
            self.count += 1
            if self.count > MAX_NODES:
                raise ToWebError(f"This frame has more than {MAX_NODES} layers; send a smaller frame.", 413)
            props = dict(self.nodes.get(cid) or {})
            for ov, prefix in reversed(v.ctx):        # the first context (outermost) is applied last = wins
                patch = ov.get(prefix + cid) if isinstance(ov, dict) else None
                if isinstance(patch, dict):
                    for k, val in patch.items():
                        if val is None:
                            props.pop(k, None)
                        else:
                            props[k] = val
            ctx = [(ov, prefix + cid + "/") for ov, prefix in v.ctx]
            out.append(self.node(cid, props, ctx, f"{v.key}/{cid}", v.depth + 1))
        out = [c for c in out if c.get("visible", True) is not False]
        self.memo[v.key] = out
        return out


# --------------------------------------------------------------------------------------- paints as CSS
def _stops(p: dict, place) -> list[str]:
    stops = p.get("stops") if isinstance(p.get("stops"), list) and p.get("stops") else [
        {"pos": 0, "color": "#000000"}, {"pos": 1, "color": "#FFFFFF"}]
    po = _num(p.get("opacity"), 1.0)
    out = []
    for s in stops:
        if not isinstance(s, dict):
            continue
        out.append(_color(s.get("color"), _num(s.get("opacity"), 1.0) * po) + " " + place(max(0.0, min(1.0, _num(s.get("pos")))))
                   )
    return out


def gradient(p: dict, w: float, h: float) -> str | None:
    """The CSS image of a gradient paint, exact for a w x h box (hd-export.js cssGradient)."""
    lin = p.get("type") == "linear"
    f = p.get("from") if isinstance(p.get("from"), list) else ([0.5, 0] if lin else [0.5, 0.5])
    t = p.get("to") if isinstance(p.get("to"), list) else ([0.5, 1] if lin else [1, 0.5])
    fx, fy = _num(f[0] if f else 0.5, 0.5) * w, _num(f[1] if len(f) > 1 else 0, 0) * h
    tx, ty = _num(t[0] if t else 0.5, 0.5) * w, _num(t[1] if len(t) > 1 else 1, 1) * h
    dx, dy = tx - fx, ty - fy
    length = math.hypot(dx, dy)

    def pct(v: float) -> str:
        return _r(v * 100) + "%"
    if lin:
        if not length > 0:
            return None
        ux, uy = dx / length, dy / length
        ang = math.atan2(dx, -dy)
        css_len = abs(w * math.sin(ang)) + abs(h * math.cos(ang))
        if not css_len > 0:
            return None
        sx, sy = w / 2 - ux * css_len / 2, h / 2 - uy * css_len / 2

        def place(tt: float) -> str:
            return pct((((fx + dx * tt) - sx) * ux + ((fy + dy * tt) - sy) * uy) / css_len)
        deg = (math.degrees(ang) % 360 + 360) % 360
        return f"linear-gradient({_r(deg)}deg, " + ", ".join(_stops(p, place)) + ")"
    at = f"{pct(fx / w if w else 0.5)} {pct(fy / h if h else 0.5)}"
    if p.get("type") == "radial":
        return f"radial-gradient(circle {_px(max(0.01, length))} at {at}, " + ", ".join(_stops(p, pct)) + ")"
    if p.get("type") == "angular":
        start = ((math.degrees(math.atan2(dy, dx)) + 90) % 360 + 360) % 360
        return f"conic-gradient(from {_r(start)}deg at {at}, " + ", ".join(_stops(p, lambda v: _r(v * 360) + "deg")) + ")"
    return None


def _first_color(paints: list[dict]) -> str | None:
    for p in reversed(paints):
        if p.get("type") in (None, "solid"):
            return _color(p.get("color"), p.get("opacity"))
        st = p.get("stops")
        if isinstance(st, list) and st and isinstance(st[0], dict):
            return _color(st[0].get("color"), _num(st[0].get("opacity"), 1.0) * _num(p.get("opacity"), 1.0))
    return None


def _shadow(e: dict, text: bool = False) -> str:
    c = _color(e.get("color") or "#000000", 0.25 if e.get("opacity") is None else e.get("opacity"))
    s = ("inset " if e.get("type") == "inner" else "") + f"{_px(_num(e.get('x')))} {_px(_num(e.get('y')))} {_px(max(0.0, _num(e.get('blur'))))}"
    if not text:
        s += " " + _px(_num(e.get("spread")))
    return s + " " + c


def _box4(vals: list[float]) -> str:
    a = [_px(v) for v in vals]
    if a[0] == a[1] == a[2] == a[3]:
        return a[0]
    if a[0] == a[2] and a[1] == a[3]:
        return f"{a[0]} {a[1]}"
    if a[1] == a[3]:
        return f"{a[0]} {a[1]} {a[2]}"
    return " ".join(a)


# ------------------------------------------------------------------------------------ vector geometry
def poly_points(sides: Any, ratio: Any, star: bool) -> list[tuple[float, float]]:
    """Same points as hd-render.js polyPoints: on the unit circle from the top, fitted into 0..1."""
    sides = max(3, min(60, int(round(_num(sides, 5 if star else 3)))))
    ratio = max(0.01, min(1.0, _num(ratio, 0.5)))
    count = sides * 2 if star else sides
    pts = []
    for i in range(count):
        a = -math.pi / 2 + i * 2 * math.pi / count
        rr = ratio if star and i % 2 else 1.0
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    return [((x - x0) / ((x1 - x0) or 1), (y - y0) / ((y1 - y0) or 1)) for x, y in pts]


def _rect_path(w: float, h: float, radius: Any) -> str:
    rs = radius if isinstance(radius, list) else [radius] * 4
    lim = min(w, h) / 2
    tl, tr, br, bl = (max(0.0, min(lim, _num(rs[i] if i < len(rs) else 0))) for i in range(4))
    if not any((tl, tr, br, bl)):
        return f"M0 0H{_r(w)}V{_r(h)}H0Z"
    return (f"M{_r(tl)} 0H{_r(w - tr)}A{_r(tr)} {_r(tr)} 0 0 1 {_r(w)} {_r(tr)}V{_r(h - br)}"
            f"A{_r(br)} {_r(br)} 0 0 1 {_r(w - br)} {_r(h)}H{_r(bl)}A{_r(bl)} {_r(bl)} 0 0 1 0 {_r(h - bl)}"
            f"V{_r(tl)}A{_r(tl)} {_r(tl)} 0 0 1 {_r(tl)} 0Z")


def _ellipse_path(w: float, h: float) -> str:
    rx, ry = w / 2, h / 2
    return f"M0 {_r(ry)}A{_r(rx)} {_r(ry)} 0 1 0 {_r(w)} {_r(ry)}A{_r(rx)} {_r(ry)} 0 1 0 0 {_r(ry)}Z"


_PATH_OK = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9eE.,+\-\s]*$")


def shape_path(v: _V) -> str | None:
    """The outline of one shape in its own 0..w / 0..h box (None = this layer has no outline)."""
    w, h = max(0.0, _num(v.get("w"), 100)), max(0.0, _num(v.get("h"), 100))
    t = v.type
    if t == "VECTOR":
        d = str(v.get("path") or "")
        return d if d and len(d) <= 200_000 and _PATH_OK.match(d) else None
    if t in ("POLYGON", "STAR"):
        pts = poly_points(v.get("sides"), v.get("ratio") if t == "STAR" else 1, t == "STAR")
        return "M" + "L".join(f"{_r(x * w)} {_r(y * h)}" for x, y in pts) + "Z"
    if t == "ELLIPSE":
        return _ellipse_path(w, h)
    if t in ("RECT", "FRAME", "COMPONENT", "INSTANCE"):
        return _rect_path(w, h, v.get("radius", 0))
    return None


# ------------------------------------------------------------------------------------------ the writer
class _Gen:
    def __init__(self, tree: _Tree, root: _V, assets: dict[str, str] | None, img_mode: str, heading_top: bool,
                 scope: str):
        self.t, self.root = tree, root
        self.assets = assets or {}
        self.img_mode = img_mode
        self.heading_top = heading_top
        self.scope = scope
        self.rules: list[tuple[str, list[str]]] = []
        self.phone: list[tuple[str, list[str]]] = []
        self.used: Counter = Counter()
        self.warn: dict[str, list[str]] = {}
        self.images: list[dict[str, Any]] = []
        self.fonts: dict[str, set] = {}
        self.font_chars: Counter = Counter()
        self.roles: dict[str, str] = {}
        self.gid = 0
        self.hidden = 0
        self.rw = max(1.0, _num(root.get("w"), 1440))

    # ---- bookkeeping
    def note(self, key: str, name: Any) -> None:
        self.warn.setdefault(key, [])
        nm = str(name or "a layer")[:40]
        if nm not in self.warn[key]:
            self.warn[key].append(nm)

    def cls(self, v: _V, suffix: str = "") -> str:
        base = "d-" + slug(v.get("name"), v.type.lower() or "layer") + suffix
        self.used[base] += 1
        return base if self.used[base] == 1 else f"{base}-{self.used[base]}"

    def rule(self, sel: str, decls: list[str], phone: bool = False) -> None:
        decls = [d for d in decls if d]
        if decls:
            (self.phone if phone else self.rules).append((sel, decls))

    def slot(self) -> int:
        """A place for a container's own rule, kept BEFORE its children's rules (the stylesheet reads top down)."""
        self.rules.append(("", []))
        return len(self.rules) - 1

    def fill(self, at: int, sel: str, decls: list[str]) -> None:
        self.rules[at] = (sel, [d for d in decls if d])

    # ---- what kind of thing a node is
    def fills(self, v: _V) -> list[dict]:
        f = v.get("fills")
        return [p for p in f if _vis(p)] if isinstance(f, list) else []

    def strokes(self, v: _V) -> list[dict]:
        s = v.get("strokes")
        if not isinstance(s, list) or _num(v.get("strokeWeight"), 1) <= 0:
            return []
        return [p for p in s if _vis(p)]

    def effects(self, v: _V) -> list[dict]:
        e = v.get("effects")
        return [x for x in e if _vis(x)] if isinstance(e, list) else []

    def image_fill(self, v: _V) -> dict | None:
        for p in reversed(self.fills(v)):
            if p.get("type") == "image" and re.fullmatch(r"[0-9a-f]{64}", str(p.get("hash") or "")):
                return p
        return None

    def has_layout(self, v: _V) -> bool:
        lay = v.get("layout")
        return isinstance(lay, dict) and lay.get("mode") in ("h", "v") and v.type in FRAMES

    def texts_in(self, v: _V, limit: int = 30) -> list[_V]:
        out, todo = [], [v]
        while todo and len(out) <= limit:
            x = todo.pop()
            if x.type == "TEXT":
                out.append(x)
            elif x.type in CONTAINERS:
                todo.extend(self.t.children(x))
        return out

    def is_button(self, v: _V, kids: list[_V]) -> bool:
        if v.type not in CONTAINERS or (v.type == "GROUP" and v.get("bool") is not None):
            return False
        texts = self.texts_in(v, 3)
        if len(texts) != 1:
            return False
        chars = str(texts[0].get("chars") or "").strip()
        if not chars or len(chars) > 40 or "\n" in chars:
            return False
        others, todo = 0, list(kids)
        while todo:
            x = todo.pop()
            if x.type in CONTAINERS and x.get("bool") is None:
                todo.extend(self.t.children(x))
            elif x.type != "TEXT" and not (x.type in SHAPES or x.get("bool") is not None):
                return False
            elif x.type != "TEXT":
                others += 1
        if others > 3:
            return False
        if BUTTON_WORDS.search(str(v.get("name") or "")):
            return True
        w, h = _num(v.get("w"), 100), _num(v.get("h"), 100)
        painted = bool(self.fills(v) or self.strokes(v))
        rad = v.get("radius", 0)
        rounded = any(_num(x) > 0 for x in rad) if isinstance(rad, list) else _num(rad) > 0
        return painted and rounded and w <= 360 and 24 <= h <= 72

    # ---- roles of the texts (before anything is written)
    def plan_roles(self) -> None:
        texts: list[tuple[_V, bool, bool]] = []     # (text, inside a button, inside a nav)

        def walk(v: _V, in_btn: bool, in_nav: bool, order: list[str]) -> None:
            kids = self.t.children(v) if v.type in CONTAINERS else []
            if v.type == "TEXT":
                texts.append((v, in_btn, in_nav))
                return
            btn = in_btn or (v is not self.root and self.is_button(v, kids))
            nav = in_nav or bool(NAV_WORDS.search(str(v.get("name") or "")))
            if btn and not in_btn:
                self.roles[v.key] = "button"
            for k in self._reading(v, kids):
                walk(k, btn, nav, order)
        walk(self.root, False, False, [])
        body = Counter()
        for tv, b, _n in texts:
            body[round(_num(tv.get("fontSize"), 16))] += len(str(tv.get("chars") or ""))
        body_size = body.most_common(1)[0][0] if body else 16
        # nav: short texts are links, except the brand (the one strictly biggest text of the nav)
        navs = [tv for tv, b, n in texts if n and not b]
        if navs:
            sizes = sorted((_num(t.get("fontSize"), 16) for t in navs), reverse=True)
            brand = sizes[0] if len(sizes) > 1 and sizes[0] > sizes[1] else None
            for tv in navs:
                if brand is not None and _num(tv.get("fontSize"), 16) == brand:
                    self.roles[tv.key] = "brand"
                elif len(str(tv.get("chars") or "").strip()) <= 30:
                    self.roles[tv.key] = "link"
        cands = []
        for tv, b, n in texts:
            if b or tv.key in self.roles:
                continue
            size = _num(tv.get("fontSize"), 16)
            chars = str(tv.get("chars") or "").strip()
            if size >= max(20.0, body_size * 1.2) and 0 < len(chars) <= 160:
                cands.append(tv)
        tiers = sorted({round(_num(t.get("fontSize"), 16) * (1.12 if _num(t.get("fontWeight"), 400) >= 600 else 1), 1)
                        for t in cands}, reverse=True)
        top_done = False
        for tv in cands:                               # cands are in reading order
            score = round(_num(tv.get("fontSize"), 16) * (1.12 if _num(tv.get("fontWeight"), 400) >= 600 else 1), 1)
            tier = tiers.index(score)
            if not self.heading_top:                   # a section of a page that has its h1 already
                level = 2 if tier == 0 else 3
            elif tier == 0:                            # the biggest: h1 once, its twins h2
                level, top_done = (2 if top_done else 1), True
            else:
                level = min(3, 1 + tier)
            self.roles[tv.key] = f"h{level}"
        for tv, b, _n in texts:
            self.roles.setdefault(tv.key, "span" if b else "p")

    def _reading(self, v: _V, kids: list[_V]) -> list[_V]:
        """DOM order: an auto layout frame keeps its flow order; a free composition reads top to bottom."""
        if self.has_layout(v):
            return kids
        return sorted(kids, key=lambda k: (round(_num(k.get("y")) / 4), _num(k.get("x"))))

    # ---- the document
    def run(self) -> tuple[str, str]:
        self.plan_roles()
        html = self.render_root()
        return html, self.css()

    def render_root(self) -> str:
        v = self.root
        w, h = max(1.0, _num(v.get("w"), 1440)), max(1.0, _num(v.get("h"), 800))
        kids = self.t.children(v)
        sec = self.cls(v)
        box = sec + "-box"
        self.used[box] += 1
        band = w >= BAND
        tag_attr = f' class="{sec}"'
        root_sel = "&"
        sec_decls = ["position:relative", "width:100%", "padding:" + ("0" if band else "48px 20px")]
        box_decls = ["position:relative", "width:100%", f"max-width:{_px(w)}", "margin-inline:auto"]
        if v.get("clip") is not False:
            box_decls.append("overflow:hidden")
        paint = self.paint_decls(v, w, h)
        if band:
            sec_decls += paint
        else:
            box_decls += paint
        if _num(v.get("opacity"), 1) < 1:
            (sec_decls if band else box_decls).append(f"opacity:{_r(_num(v.get('opacity')), 3)}")
        self.unsupported(v)
        at_sec, at_box = self.slot(), self.slot()
        bg_img = self.bg_image(v, box, w, h)
        inner = self.render_kids(v, kids, w, h, box, box_decls, is_root=True)
        if bg_img:
            box_decls.append("isolation:isolate")
            inner = bg_img + inner
        self.fill(at_sec, root_sel, sec_decls)
        self.fill(at_box, "." + box, box_decls)
        if not band:
            self.rule(root_sel, ["padding:32px 16px"], phone=True)
        name = str(v.get("name") or "")
        tag = ("nav" if NAV_WORDS.search(name) else "header" if re.search(r"\bheader\b", name, re.I)
               else "footer" if re.search(r"\bfooter\b", name, re.I) else "div")
        return f"<section{tag_attr}>\n<{tag} class=\"{box}\">\n{inner}</{tag}>\n</section>\n"

    def render_kids(self, v: _V, kids: list[_V], w: float, h: float, cl: str, decls: list[str], is_root: bool = False) -> str:
        """The container's own layout rules + its children. decls = the container's rule (added to here)."""
        if self.has_layout(v):
            return self.flow(v, kids, w, h, cl, decls, is_root)
        return self.free(v, kids, w, h, cl, decls, is_root)

    # ---- auto layout = flexbox
    def flow(self, v: _V, kids: list[_V], w: float, h: float, cl: str, decls: list[str], is_root: bool) -> str:
        lay = v.get("layout")
        horiz = lay.get("mode") == "h"
        decls += ["display:flex", "flex-direction:" + ("row" if horiz else "column")]
        if lay.get("wrap"):
            decls.append("flex-wrap:wrap")
        jm = {"center": "center", "end": "flex-end", "between": "space-between"}.get(str(lay.get("alignMain") or "start"))
        if jm:
            decls.append(f"justify-content:{jm}")
        decls.append("align-items:" + {"center": "center", "end": "flex-end", "stretch": "stretch"}.get(
            str(lay.get("alignCross") or "start"), "flex-start"))
        gap = max(0.0, _num(lay.get("gap")))
        if gap:
            decls.append(f"gap:{_px(gap)}")
        pad = lay.get("pad") if isinstance(lay.get("pad"), list) else [0, 0, 0, 0]
        pad = [max(0.0, _num(pad[i] if i < len(pad) else 0)) for i in range(4)]
        if any(pad):
            decls.append("padding:" + _box4(pad))
        size_v = str(v.get("sizeV") or "fixed")
        if size_v == "fixed" and not is_root:
            pass                                       # the parent's rules gave it its height (min-height)
        elif size_v == "fixed" and is_root:
            decls.append(f"min-height:{_px(h)}")
            ph_root = ["min-height:0"]
            self.rule("." + cl, ph_root, phone=True)
        flow_kids = [k for k in kids if k.get("layoutPos") != "absolute"]
        if any(k.get("layoutPos") == "absolute" for k in kids) and "position:relative" not in decls:
            decls.append("position:relative")
        # phone: a wide row becomes a column, a narrow one wraps; big padding and gaps come down
        ph = []
        collapse = horiz and w >= 600 and len(flow_kids) >= 2
        if collapse:
            ph += ["flex-direction:column", "align-items:stretch"] + ([] if gap >= 12 else ["gap:12px"])
        elif horiz and len(flow_kids) >= 2:
            ph.append("flex-wrap:wrap")
        if any(p > 24 for p in pad):
            ph.append("padding:" + _box4([min(p, 24.0) for p in pad]))
        if gap > 24:
            ph.append(f"gap:{_px(min(gap, 24.0))}")
        self.rule("." + cl, ph, phone=True)
        out = []
        for k in kids:
            if k.get("layoutPos") == "absolute":
                out.append(self.node(k, ("abs-px", v, w, h)))
            else:
                out.append(self.node(k, ("flow", v, horiz, collapse)))
        return "".join(out)

    # ---- a free composition = a box of its own aspect ratio, children in container units
    def free(self, v: _V, kids: list[_V], w: float, h: float, cl: str, decls: list[str], is_root: bool) -> str:
        decls += ["container-type:inline-size", f"aspect-ratio:{_r(w)} / {_r(h)}"]
        if "position:relative" not in decls and not any(d.startswith("position:") for d in decls):
            decls.append("position:relative")
        stack = w > SMALL_COMPOSITION
        order = self._reading(v, kids)
        paint_order = {k.key: i for i, k in enumerate(kids)}
        need_z = [paint_order[k.key] for k in order] != sorted(paint_order[k.key] for k in order)
        if stack:
            self.rule("." + cl, ["aspect-ratio:auto", "height:auto", "display:flex", "flex-direction:column",
                                 "align-items:flex-start", "gap:16px"] + (["padding:28px 20px"] if is_root else []), phone=True)
        out = []
        for k in order:
            bg = self.is_backdrop(k, w, h, paint_order[k.key])
            out.append(self.node(k, ("free", v, w, h, stack, bg, paint_order[k.key] + 1 if need_z else 0)))
        return "".join(out)

    def is_backdrop(self, k: _V, w: float, h: float, paint_i: int) -> bool:
        if paint_i != 0 or k.type not in ("RECT", "ELLIPSE", "FRAME") or self.t.children(k):
            return False
        return (_num(k.get("x")) <= 1 and _num(k.get("y")) <= 1 and _num(k.get("w"), 100) >= w - 2
                and _num(k.get("h"), 100) >= h - 2)

    # ---- one child
    def node(self, v: _V, where: tuple) -> str:
        if v.get("mask"):
            self.note("mask", v.get("name"))
            return ""
        t = v.type
        kids = self.t.children(v) if t in CONTAINERS else []
        role = self.roles.get(v.key, "")
        cl = self.cls(v)
        decls: list[str] = []
        w, h = max(0.0, _num(v.get("w"), 100)), max(0.0, _num(v.get("h"), 100))
        self.unsupported(v)
        if t == "TEXT":
            self.place(v, cl, decls, where, w, h, kind="text")
            return self.text(v, cl, decls, where)
        if t == "LINE":
            self.place(v, cl, decls, where, w, max(h, _num(v.get("strokeWeight"), 1)), kind="line")
            sc = _first_color(self.strokes(v))
            sw = max(0.5, _num(v.get("strokeWeight"), 1))
            decls += ["border:0", f"border-top:{_px(sw)} {'dashed' if v.get('dash') else 'solid'} {sc or 'currentColor'}",
                      "margin:0", "height:0"]
            self.rule("." + cl, decls)
            return f'<hr class="{cl}">\n'
        if t in PATHY or (t == "GROUP" and v.get("bool") is not None):
            self.place(v, cl, decls, where, w, h, kind="shape")
            return self.svg(v, cl, w, h, kids, decls)
        img = self.image_fill(v)
        if img and not kids:
            self.place(v, cl, decls, where, w, h, kind="image")
            if not any(d.startswith("position:") for d in decls):
                decls.insert(0, "position:relative")
            decls += self.paint_decls(v, w, h, skip_image=True) + ["overflow:hidden"]
            if t == "ELLIPSE":
                decls.append("border-radius:50%")
            self.rule("." + cl, decls)
            return f'<div class="{cl}">' + self.img_tag(v, img, cl + "-img") + "</div>\n"
        if t in ("RECT", "ELLIPSE") or (t in CONTAINERS and not kids):
            self.place(v, cl, decls, where, w, h, kind="shape")
            decls += self.paint_decls(v, w, h)
            if t == "ELLIPSE":
                decls.append("border-radius:50%")
            if _num(v.get("opacity"), 1) < 1:
                decls.append(f"opacity:{_r(_num(v.get('opacity')), 3)}")
            self.rule("." + cl, decls)
            return f'<div class="{cl}" aria-hidden="true"></div>\n'
        # a container: a button, a nav, a group or a frame
        self.place(v, cl, decls, where, w, h, kind="box", layout=self.has_layout(v))
        decls += self.paint_decls(v, w, h)
        if _num(v.get("opacity"), 1) < 1:
            decls.append(f"opacity:{_r(_num(v.get('opacity')), 3)}")
        clip = v.get("clip")
        if (clip is None and t in ("FRAME", "COMPONENT", "INSTANCE")) or clip:
            if t != "GROUP":
                decls.append("overflow:hidden")
        at = self.slot()
        bg_img = self.bg_image(v, cl, w, h)
        if bg_img:
            decls.append("isolation:isolate")
        inner = self.render_kids(v, kids, w, h, cl, decls)
        if bg_img:
            inner = bg_img + inner
        self.fill(at, "." + cl, decls)
        if role == "button":
            href, todo = self.link_of(v)
            return (f'<a class="btn {cl}" href="{_esc(href)}">' + ("<!-- TODO: link -->" if todo else "") + inner.strip()
                    + "</a>\n")
        name = str(v.get("name") or "")
        tag = ("nav" if NAV_WORDS.search(name) else "header" if re.search(r"\bheader\b", name, re.I)
               else "footer" if re.search(r"\bfooter\b", name, re.I) else "div")
        return f'<{tag} class="{cl}">\n{inner}</{tag}>\n'

    def link_of(self, v: _V) -> tuple[str, bool]:
        """Her own prototype link (a 'url' reaction to https / tel / mailto) or '#' with a TODO - never invented."""
        for r in v.get("reactions") or []:
            if isinstance(r, dict) and r.get("action") == "url":
                u = str(r.get("url") or "").strip()
                if re.match(r"^(https://|tel:|mailto:)[^\s\"'<>]{1,500}$", u, re.I):
                    return u, False
        return "#", True

    # ---- where a child sits and how big it is
    def place(self, v: _V, cl: str, decls: list[str], where: tuple, w: float, h: float, kind: str,
              layout: bool = False) -> None:
        mode = where[0]
        if mode == "flow":
            _, parent, horiz, collapse = where
            size_h, size_v = str(v.get("sizeH") or "fixed"), str(v.get("sizeV") or "fixed")
            auto = str(v.get("autoResize") or "wh") if kind == "text" else ""
            ph = []
            if horiz:
                if size_h == "fill":
                    decls += ["flex:1 1 0", "min-width:0"]
                    if collapse:
                        ph += ["flex:0 0 auto", "width:auto"]
                elif size_h == "fixed" and not (kind == "text" and auto == "wh"):
                    decls += [f"width:{_px(w)}", "max-width:100%"]
                if size_v == "fill":
                    decls.append("align-self:stretch")
                elif size_v == "fixed":
                    self._height(decls, kind, h, layout, auto)
            else:
                if size_v == "fill":
                    decls += ["flex:1 1 0", "min-height:0"]
                elif size_v == "fixed":
                    self._height(decls, kind, h, layout, auto)
                if size_h == "fill":
                    decls.append("align-self:stretch")
                elif size_h == "fixed" and not (kind == "text" and auto == "wh"):
                    decls += [f"width:{_px(w)}", "max-width:100%"]
            for key, prop in (("minW", "min-width"), ("maxW", "max-width"), ("minH", "min-height"), ("maxH", "max-height")):
                if _num(v.get(key)) > 0:
                    decls.append(f"{prop}:{_px(_num(v.get(key)))}")
            if kind in ("image", "shape") and size_h == "fixed" and size_v == "fixed" and w and h:
                ph += ["height:auto", f"aspect-ratio:{_r(w)} / {_r(h)}"]
            self.rule("." + cl, ph, phone=True)
        elif mode == "abs-px":                         # placed freely inside an auto layout frame: across = a share of it
            pw = max(1.0, where[2])
            decls += ["position:absolute", f"left:{_r(_num(v.get('x')) / pw * 100, 3)}%", f"top:{_px(_num(v.get('y')))}"]
            if kind != "text" or str(v.get("autoResize") or "wh") != "wh":
                decls.append(f"width:{_px(w)}")
            if kind != "text":
                decls.append(f"height:{_px(h)}")
            if kind in ("shape", "line"):
                self.rule("." + cl, ["display:none"], phone=True)
                self.hidden += 1
        else:                                          # free composition: container units of the parent
            _, parent, pw, ph_, stack, bg, z = where
            q = 100.0 / pw
            if bg:
                decls += ["position:absolute", "inset:0", "width:100%", "height:100%", "z-index:0" if z else ""]
                return
            decls += ["position:absolute", f"left:{_r(_num(v.get('x')) * q, 3)}cqw", f"top:{_r(_num(v.get('y')) * q, 3)}cqw"]
            auto = str(v.get("autoResize") or "wh") if kind == "text" else ""
            if not (kind == "text" and auto == "wh"):
                decls.append(f"width:{_r(w * q, 3)}cqw")
            if kind != "text" or auto == "none":
                decls.append(f"height:{_r(max(h, 0.0) * q, 3)}cqw" if kind != "text" else f"min-height:{_r(h * q, 3)}cqw")
            if z:
                decls.append(f"z-index:{z}")
            if stack:
                ph = ["position:relative", "left:auto", "top:auto"]
                cx = _num(v.get("x")) + w / 2
                centred = abs(cx - pw / 2) <= pw * 0.06
                if kind == "text":
                    ph += ["width:auto", "max-width:100%", "align-self:stretch", "min-height:0", "white-space:pre-line"]
                elif kind in ("shape", "line"):
                    ph.append("display:none")
                    self.hidden += 1
                else:
                    ph += [f"width:{_px(w)}", "max-width:100%", "height:auto"]
                    if kind in ("image",) or (kind == "box" and not layout):
                        ph.append(f"aspect-ratio:{_r(w)} / {_r(max(h, 1.0))}")
                    if centred:
                        ph.append("align-self:center")
                self.rule("." + cl, ph, phone=True)

    def _height(self, decls: list[str], kind: str, h: float, layout: bool, auto: str) -> None:
        if kind == "text":
            if auto == "none":
                decls.append(f"min-height:{_px(h)}")
        elif kind == "box":
            decls.append(f"min-height:{_px(h)}" if layout else f"height:{_px(h)}")
        else:
            decls.append(f"height:{_px(h)}")

    # ---- paint of a box
    def paint_decls(self, v: _V, w: float, h: float, skip_image: bool = False) -> list[str]:
        out: list[str] = []
        layers = []
        fills = self.fills(v)
        for i in range(len(fills) - 1, -1, -1):
            p = fills[i]
            last = i == 0
            typ = p.get("type")
            if typ == "image":
                continue                                 # pictures are <img> elements (the site's photo store)
            if typ in (None, "solid"):
                c = _color(p.get("color"), p.get("opacity"))
                layers.append(c if last else f"linear-gradient({c}, {c})")
            else:
                g = gradient(p, w or 1, h or 1)
                if g:
                    layers.append(g)
        if layers:
            if len(layers) > 1 and not layers[-1].startswith(("linear-gradient", "radial", "conic")):
                pass
            out.append("background:" + ", ".join(layers))
        strokes = self.strokes(v)
        if strokes:
            sc = _first_color(strokes)
            if any(p.get("type") not in (None, "solid") for p in strokes):
                self.note("gradient_stroke", v.get("name"))
            sw = max(0.0, _num(v.get("strokeWeight"), 1))
            line = f"{_px(sw)} {'dashed' if v.get('dash') else 'solid'} {sc}"
            align = str(v.get("strokeAlign") or "center")
            if align == "inside":
                out.append(f"border:{line}")
            else:
                out.append(f"outline:{line}")
                if align == "center":
                    out.append(f"outline-offset:{_px(-sw / 2)}")
        if v.type != "ELLIPSE":
            rad = v.get("radius", 0)
            lim = min(w, h) / 2 if w and h else 0
            rs = rad if isinstance(rad, list) else [rad] * 4
            vals = [max(0.0, min(lim, _num(rs[i] if i < len(rs) else 0))) for i in range(4)]
            if any(vals):
                out.append("border-radius:" + _box4(vals))
        shadows = [e for e in self.effects(v) if e.get("type") in ("drop", "inner")]
        if shadows:
            out.append("box-shadow:" + ", ".join(_shadow(e) for e in shadows))
        tf = self.transform(v)
        if tf:
            out.append("transform:" + tf)
        return out

    def transform(self, v: _V) -> str:
        tf = []
        if _num(v.get("rot")):
            tf.append(f"rotate({_r(_num(v.get('rot')))}deg)")
        if v.get("flipH"):
            tf.append("scaleX(-1)")
        if v.get("flipV"):
            tf.append("scaleY(-1)")
        return " ".join(tf)

    def unsupported(self, v: _V) -> None:
        blend = str(v.get("blend") or "normal")
        if blend not in ("normal", "pass", "source-over"):
            self.note("blend", v.get("name"))
        for e in self.effects(v):
            if e.get("type") in ("blur", "bgblur") and _num(e.get("blur")) > 0:
                self.note("blur", v.get("name"))
        for p in self.fills(v):
            if p.get("type") == "image" and p.get("mode") == "tile":
                self.note("tile", v.get("name"))

    # ---- pictures
    def bg_image(self, v: _V, cl: str, w: float, h: float) -> str:
        """A frame with children and a picture fill: the picture is the first child, behind everything."""
        img = self.image_fill(v)
        if not img:
            return ""
        icl = cl + "-bg"
        self.used[icl] += 1
        return self.img_tag(v, img, icl, backdrop=True)

    def img_tag(self, v: _V, paint: dict, cl: str, backdrop: bool = False) -> str:
        sha = str(paint.get("hash"))
        alt = re.sub(r"\s+", " ", str(v.get("name") or "")).strip()[:120]
        if GENERIC_NAME.match(alt) or re.fullmatch(r"(rectangle|ellipse|image|img|photo|picture)\s*\d*", alt, re.I):
            alt = "" if backdrop else alt
        fit = "contain" if paint.get("mode") == "fit" else "cover"
        self.images.append({"hash": sha, "name": slug(alt or "picture", "picture"), "alt": alt, "node": v.key.rsplit("/", 1)[-1]})
        decls = ["position:absolute", "inset:0", "width:100%", "height:100%", f"object-fit:{fit}", "display:block"]
        if backdrop:
            decls.append("z-index:-1")
        if _num(paint.get("opacity"), 1) < 1:
            decls.append(f"opacity:{_r(_num(paint.get('opacity')), 3)}")
        self.rule("." + cl, decls)
        alt_attr = f' alt="{_esc(alt)}"' + (' aria-hidden="true"' if backdrop and not alt else "")
        if self.img_mode == "hoola":
            name = self.assets.get(sha)
            if not name:
                self.note("missing_image", v.get("name"))
                return ""
            return f'<img class="{cl}" data-hoola-img="{_esc(name)}"{alt_attr}>'
        src = self.assets.get(sha) or f"/api/design/assets/{sha}"
        return f'<img class="{cl}" src="{_esc(src)}"{alt_attr} loading="lazy" decoding="async">'

    # ---- text
    def font_stack(self, fam: str, head: bool) -> str:
        fam = re.sub(r"[\"'\\;{}<>]", "", fam)[:60] or "Inter"
        return f'"{fam}", var(--font-{"head" if head else "body"}, system-ui), sans-serif'

    def text(self, v: _V, cl: str, decls: list[str], where: tuple) -> str:
        role = self.roles.get(v.key, "p")
        tag = {"h1": "h1", "h2": "h2", "h3": "h3", "span": "span", "brand": "p", "link": "a"}.get(role, "p")
        chars = str(v.get("chars") or "")
        case = str(v.get("textCase") or "none")
        size = max(1.0, _num(v.get("fontSize"), 16))
        weight = int(_num(v.get("fontWeight"), 400))
        fam = str(v.get("font") or "Inter")
        self.fonts.setdefault(fam, set()).add(weight)
        self.font_chars[fam] += len(chars)
        fills = self.fills(v)
        grad = fills[-1] if fills and fills[-1].get("type") in ("linear", "radial", "angular") else None
        if grad is not None:
            g = gradient(grad, _num(v.get("w"), 100) or 1, _num(v.get("h"), 20) or 1)
            if g:
                decls += [f"background:{g}", "-webkit-background-clip:text", "background-clip:text", "color:transparent"]
        else:
            c = _first_color([p for p in fills if p.get("type") != "image"])
            if c:
                decls.append(f"color:{c}")
        head = tag in ("h1", "h2", "h3")
        decls += [f"font-family:{self.font_stack(fam, head)}", f"font-weight:{weight}"]
        mode = where[0]
        if mode == "free":
            q = 100.0 / where[2]
            decls.append(f"font-size:clamp({_px(min(size, 10.0))}, {_r(size * q, 3)}cqw, {_px(size)})")
        elif size >= 28:
            decls.append(f"font-size:clamp({_px(max(20.0, round(size * 0.6)))}, {_r(size / self.rw * 100, 3)}vw, {_px(size)})")
        else:
            decls.append(f"font-size:{_px(size)}")
        if (mode == "free" and where[4]) or (mode != "free" and size >= 28):
            self.rule("." + cl, [f"font-size:{_px(max(min(size, 18.0), round(size * 0.6)) if size >= 28 else size)}"], phone=True)
        if v.get("italic"):
            decls.append("font-style:italic")
        lh = v.get("lineHeight")
        decls.append("line-height:" + (_r(_num(lh) / size, 3) if isinstance(lh, (int, float)) and _num(lh) > 0 else "1.2"))
        decls.append(f"letter-spacing:{_px(_num(v.get('letterSpacing')))}")
        align = str(v.get("align") or "left")
        if align in ("center", "right", "justify"):
            decls.append(f"text-align:{align}")
        deco = str(v.get("decoration") or "none")
        if deco == "underline":
            decls.append("text-decoration:underline")
        elif deco == "strike":
            decls.append("text-decoration:line-through")
        elif tag == "a":
            decls.append("text-decoration:none")
        if case in ("upper", "lower", "title"):
            decls.append("text-transform:" + {"upper": "uppercase", "lower": "lowercase", "title": "capitalize"}[case])
        auto = str(v.get("autoResize") or "wh")
        decls.append("white-space:" + ("pre" if mode == "free" and auto == "wh" else "pre-line"))
        decls += ["margin:0", "overflow-wrap:break-word"]
        if _num(v.get("opacity"), 1) < 1:
            decls.append(f"opacity:{_r(_num(v.get('opacity')), 3)}")
        shadows = [e for e in self.effects(v) if e.get("type") == "drop"]
        if shadows:
            decls.append("text-shadow:" + ", ".join(_shadow(e, True) for e in shadows))
        sc = _first_color(self.strokes(v))
        if sc:
            decls.append(f"-webkit-text-stroke:{_px(_num(v.get('strokeWeight'), 1))} {sc}")
        tf = self.transform(v)
        if tf:
            decls.append("transform:" + tf)
        if auto == "wh" and mode == "free" and where[4]:
            self.rule("." + cl, ["white-space:pre-line"], phone=True)
        self.rule("." + cl, decls)
        body = self.runs(v, chars, cl, size)
        if tag == "a":
            href, todo = self.link_of(v)
            return f'<a class="{cl}" href="{_esc(href)}">' + ("<!-- TODO: link -->" if todo else "") + body + "</a>\n"
        return f'<{tag} class="{cl}">{body}</{tag}>' + ("" if tag == "span" else "\n")

    def runs(self, v: _V, chars: str, cl: str, size: float) -> str:
        runs = v.get("runs")
        if not isinstance(runs, list) or not runs:
            return _esc(chars)
        marks = []
        for r in runs:
            if not isinstance(r, dict):
                continue
            s, e = int(_num(r.get("s"))), int(_num(r.get("e")))
            if 0 <= s < e <= len(chars):
                marks.append((s, e, r))
        marks.sort(key=lambda m: m[0])
        out, at, n = [], 0, 0
        for s, e, r in marks:
            if s < at:
                continue
            out.append(_esc(chars[at:s]))
            decls = []
            fills = r.get("fills") if isinstance(r.get("fills"), list) else (
                [{"type": "solid", "color": r["color"]}] if isinstance(r.get("color"), str) else None)
            if fills:
                c = _first_color([p for p in fills if _vis(p)])
                if c:
                    decls.append(f"color:{c}")
            if r.get("fontWeight") is not None:
                decls.append(f"font-weight:{int(_num(r.get('fontWeight'), 400))}")
            if r.get("italic") is not None:
                decls.append("font-style:" + ("italic" if r.get("italic") else "normal"))
            if r.get("fontSize") is not None:
                decls.append(f"font-size:{_r(_num(r.get('fontSize'), size) / size, 3)}em")
            if r.get("decoration") in ("underline", "strike"):
                decls.append("text-decoration:" + ("underline" if r["decoration"] == "underline" else "line-through"))
            if r.get("font"):
                fam = str(r.get("font"))
                self.fonts.setdefault(fam, set()).add(int(_num(r.get("fontWeight") or v.get("fontWeight"), 400)))
                decls.append(f"font-family:{self.font_stack(fam, False)}")
            if decls:
                n += 1
                rc = f"{cl}-r{n}"
                self.used[rc] += 1
                self.rule("." + rc, decls)
                out.append(f'<span class="{rc}">{_esc(chars[s:e])}</span>')
            else:
                out.append(_esc(chars[s:e]))
            at = e
        out.append(_esc(chars[at:]))
        return "".join(out)

    # ---- inline SVG (vectors, polygons, stars, boolean groups)
    def svg_paint(self, paints: list[dict], defs: list[str], name: Any) -> str:
        top = paints[-1] if paints else None
        if top is None:
            return "none"
        typ = top.get("type")
        if typ in (None, "solid"):
            return _color(top.get("color"), top.get("opacity"))
        if typ == "image":
            self.note("svg_image", name)
            return "none"
        if typ == "angular":
            self.note("angular_shape", name)
            return _first_color([top]) or "none"
        self.gid += 1
        gid = f"dg{self.gid}"
        f = top.get("from") if isinstance(top.get("from"), list) else [0.5, 0] if typ == "linear" else [0.5, 0.5]
        t = top.get("to") if isinstance(top.get("to"), list) else [0.5, 1] if typ == "linear" else [1, 0.5]
        stops = "".join(
            f'<stop offset="{_r(max(0.0, min(1.0, _num(s.get("pos")))), 4)}" stop-color="{_hex6(s.get("color"))}"'
            + (f' stop-opacity="{_r(_hex_rgb(s.get("color"))[3] * _num(s.get("opacity"), 1) * _num(top.get("opacity"), 1), 3)}"'
               if _hex_rgb(s.get("color"))[3] * _num(s.get("opacity"), 1) * _num(top.get("opacity"), 1) < 1 else "") + "/>"
            for s in (top.get("stops") or []) if isinstance(s, dict))
        if typ == "linear":
            defs.append(f'<linearGradient id="{gid}" x1="{_r(_num(f[0]), 4)}" y1="{_r(_num(f[1]), 4)}" '
                        f'x2="{_r(_num(t[0]), 4)}" y2="{_r(_num(t[1]), 4)}">{stops}</linearGradient>')
        else:
            rr = math.hypot(_num(t[0]) - _num(f[0]), _num(t[1]) - _num(f[1]))
            defs.append(f'<radialGradient id="{gid}" cx="{_r(_num(f[0]), 4)}" cy="{_r(_num(f[1]), 4)}" r="{_r(rr, 4)}">'
                        f'{stops}</radialGradient>')
        return f"url(#{gid})"

    def svg(self, v: _V, cl: str, w: float, h: float, kids: list[_V], place: list[str]) -> str:
        defs: list[str] = []
        fill = self.svg_paint(self.fills(v), defs, v.get("name"))
        strokes = self.strokes(v)
        stroke = ""
        if strokes:
            sc = _first_color(strokes) or "none"
            stroke = (f' stroke="{sc}" stroke-width="{_r(max(0.0, _num(v.get("strokeWeight"), 1)))}" vector-effect="non-scaling-stroke"'
                      + (f' stroke-linecap="{v.get("strokeCap")}"' if v.get("strokeCap") in ("round", "square") else "")
                      + (f' stroke-linejoin="{v.get("strokeJoin")}"' if v.get("strokeJoin") in ("round", "bevel") else ""))
        rule = ' fill-rule="evenodd"' if v.get("fillRule") == "evenodd" else ""
        body = ""
        if v.type == "GROUP":
            parts = []
            for k in kids:
                d = shape_path(k)
                if d is None or k.type == "TEXT":
                    continue
                tf = f"translate({_r(_num(k.get('x')))} {_r(_num(k.get('y')))})"
                if _num(k.get("rot")):
                    tf += f" rotate({_r(_num(k.get('rot')))} {_r(_num(k.get('w'), 100) / 2)} {_r(_num(k.get('h'), 100) / 2)})"
                parts.append((d, tf))
            if not parts:
                return ""
            op = str(v.get("bool") or "union")
            self.gid += 1
            gid = self.gid
            if op == "subtract" and len(parts) > 1:
                cut = "".join(f'<path d="{d}" transform="{tf}" fill="#000"/>' for d, tf in parts[1:])
                defs.append(f'<mask id="dm{gid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{_r(w)}" height="{_r(h)}">'
                            f'<rect width="{_r(w)}" height="{_r(h)}" fill="#fff"/>{cut}</mask>')
                d, tf = parts[0]
                body = f'<path d="{d}" transform="{tf}" fill="{fill}"{stroke} mask="url(#dm{gid})"/>'
            elif op == "intersect" and len(parts) > 1:
                body = f'<path d="{parts[-1][0]}" transform="{parts[-1][1]}" fill="{fill}"{stroke}/>'
                for i, (d, tf) in enumerate(reversed(parts[:-1])):
                    defs.append(f'<clipPath id="dc{gid}-{i}"><path d="{d}" transform="{tf}"/></clipPath>')
                    body = f'<g clip-path="url(#dc{gid}-{i})">{body}</g>'
            elif op == "exclude" and len(parts) > 1:
                # each shape minus all the others: for two shapes that IS the exclusion (their overlap is left open)
                body = ""
                for i, (d, tf) in enumerate(parts):
                    cut = "".join(f'<path d="{d2}" transform="{tf2}" fill="#000"/>' for j, (d2, tf2) in enumerate(parts) if j != i)
                    defs.append(f'<mask id="dx{gid}-{i}" maskUnits="userSpaceOnUse" x="0" y="0" width="{_r(w)}" '
                                f'height="{_r(h)}"><rect width="{_r(w)}" height="{_r(h)}" fill="#fff"/>{cut}</mask>')
                    body += f'<path d="{d}" transform="{tf}" fill="{fill}"{stroke} mask="url(#dx{gid}-{i})"/>'
                if len(parts) > 2:
                    self.note("exclude", v.get("name"))
            else:
                body = f'<g fill="{fill}"{stroke}>' + "".join(f'<path d="{d}" transform="{tf}"/>' for d, tf in parts) + "</g>"
        else:
            d = shape_path(v)
            if not d:
                return ""
            body = f'<path d="{d}" fill="{fill}"{stroke}{rule}/>'
        shadows = [e for e in self.effects(v) if e.get("type") == "drop"]
        extra = []
        if shadows:
            extra.append("filter:" + " ".join(f"drop-shadow({_shadow(e, True)})" for e in shadows))
        if _num(v.get("opacity"), 1) < 1:
            extra.append(f"opacity:{_r(_num(v.get('opacity')), 3)}")
        tf = self.transform(v)
        if tf:
            extra.append("transform:" + tf)
        self.rule("." + cl, place + ["display:block", "overflow:visible"] + extra)
        d = f"<defs>{''.join(defs)}</defs>" if defs else ""
        return (f'<svg class="{cl}" viewBox="0 0 {_r(max(w, 0.01))} {_r(max(h, 0.01))}" preserveAspectRatio="none" '
                f'aria-hidden="true" focusable="false">{d}{body}</svg>\n')

    # ---- the stylesheet
    def css(self) -> str:
        root = f"#{self.scope}" if self.scope else "." + slug_root(self.root)
        base = [(f"{root}, {root} *", ["box-sizing:border-box"]),
                (", ".join(f"{root} :where({t})" for t in ("h1", "h2", "h3", "p")), ["margin:0"]),
                (f"{root} :where(.btn)", ["display:flex", "align-items:center", "justify-content:center", "min-height:0", "padding:0",
                                  "gap:0", "border:0", "border-radius:0", "background:none", "box-shadow:none",
                                  "font:inherit", "color:inherit", "text-decoration:none", "cursor:pointer"]),
                (f"{root} :where(.btn):focus-visible", ["outline:2px solid currentColor", "outline-offset:3px"]),
                (f"{root} :where(svg)", ["max-width:100%"])]

        def one(sel: str, decls: list[str], ind: str = "") -> str:
            s = root if sel == "&" else sel if sel.startswith(root) else (f"{root} {sel}" if self.scope else sel)
            body = "".join(f"{ind}  {d};\n" for d in decls)
            return f"{ind}{s} {{\n{body}{ind}}}\n"
        out = "".join(one(s, d) for s, d in base) + "".join(one(s, d) for s, d in _merged(self.rules))
        if self.phone:
            out += f"@media (max-width: {PHONE}px) {{\n" + "".join(one(s, d, "  ") for s, d in _merged(self.phone)) + "}\n"
        return out


def _merged(rules: list[tuple[str, list[str]]]) -> list[tuple[str, list[str]]]:
    """One block per selector (in the order they first appear); a later value of a property replaces the earlier."""
    order: dict[str, dict[str, str]] = {}
    for sel, decls in rules:
        if not sel or not decls:
            continue
        box = order.setdefault(sel, {})
        for d in decls:
            prop = d.split(":", 1)[0].strip()
            box.pop(prop, None)
            box[prop] = d
    return [(sel, list(box.values())) for sel, box in order.items()]


def slug_root(v: _V) -> str:
    return "d-" + slug(v.get("name"), v.type.lower() or "layer")


WARN_TEXT = {
    "blend": "Blend modes are not reproduced on the website",
    "blur": "Blur effects are not reproduced on the website",
    "mask": "Masks are not reproduced; the masked layers were left out",
    "gradient_stroke": "Gradient strokes become their first colour",
    "tile": "A tiled picture fill is shown once, filling its box",
    "svg_image": "A picture inside a vector shape is not reproduced",
    "angular_shape": "An angular gradient inside a vector shape becomes its first colour",
    "exclude": "An exclude of more than two shapes leaves every overlap open (places where three shapes meet stay empty)",
    "missing_image": "A picture could not be copied to the website and was left out",
}


def frame_to_html(doc: dict, node_id: str, assets: dict[str, str] | None = None, *, scope: str = "",
                  heading_top: bool = True, img_mode: str = "src") -> dict[str, Any]:
    """ONE frame -> {html, css, images[], fonts[], warnings[]}. Pure: reads the document, writes nothing.

    assets: picture hash -> the value to use (img_mode "src": a URL, default /api/design/assets/<hash>; "hoola": the
    website's own photo name, written as data-hoola-img for Web Studio to turn into a responsive <picture>).
    scope: the website section id the CSS is scoped to (without it the root class scopes it). heading_top: the frame
    may carry the page's one h1 (a new site); False = its headings start at h2 (a section added to a page)."""
    nodes = doc.get("nodes") if isinstance(doc, dict) and isinstance(doc.get("nodes"), dict) else doc
    if not isinstance(nodes, dict) or node_id not in nodes:
        raise ToWebError("That frame is not in this file any more.", 404)
    n = nodes[node_id]
    if not isinstance(n, dict) or n.get("type") not in KINDS_OK:
        raise ToWebError("Pick a frame (a frame, component, instance or section) to send to Web Studio.", 400)
    tree = _Tree(nodes)
    root = tree.node(node_id, key=node_id)
    if root.get("visible") is False:
        raise ToWebError("That frame is hidden; show it first.", 400)
    g = _Gen(tree, root, assets, img_mode, heading_top, scope)
    html, css = g.run()
    warnings = []
    for key, names in g.warn.items():
        more = f" (and {len(names) - 5} more)" if len(names) > 5 else ""
        warnings.append(f"{WARN_TEXT.get(key, key)}: " + ", ".join(names[:5]) + more + ".")
    if g.hidden:
        warnings.append(f"{g.hidden} decorative shape{'s are' if g.hidden != 1 else ' is'} hidden on phones, where the "
                        "layout stacks into one column.")
    shipped = shipped_fonts()
    fonts = []
    for fam, weights in sorted(g.fonts.items(), key=lambda kv: -g.font_chars[kv[0]]):
        ok = fam.lower() in shipped
        fonts.append({"family": fam, "weights": sorted(weights), "shipped": ok, "chars": g.font_chars[fam]})
        if not ok:
            warnings.append(f"The font {fam} is not one the website ships; the website's own font is used in its place.")
    seen, images = set(), []
    for im in g.images:
        if im["hash"] not in seen:
            seen.add(im["hash"])
            images.append(im)
    return {"html": html, "css": css, "images": images, "fonts": fonts, "warnings": warnings,
            "name": str(root.get("name") or "Frame"), "w": _num(root.get("w"), 0), "h": _num(root.get("h"), 0),
            "layers": tree.count}


def shipped_fonts() -> set[str]:
    """The font families Web Studio serves from its own files (no font is ever loaded from outside a website)."""
    out = set()
    try:
        meta = json.loads((_FONT_DIR / "fonts.json").read_text())
        fams = meta.get("families") if isinstance(meta, dict) else None
        if isinstance(fams, (list, dict)):
            out |= {str(f).lower() for f in fams}
    except Exception:
        pass
    try:
        from ..site import taxonomy as T
        for pair in T.FONTS.values():
            for k in ("head", "body", "deva"):
                fam = str(pair.get(k) or "")
                slugged = re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")
                if any(_FONT_DIR.glob(f"{slugged}-*.woff2")):
                    out.add(fam.lower())
    except Exception:
        log.info("font list unreadable", exc_info=True)
    return out


# ------------------------------------------------------------------------------- the design's own colours
def design_tokens(doc: dict, node_id: str) -> dict[str, Any]:
    """Web Studio tokens from the frame itself: its background, its text colour, its button colour, its corners and
    the family of its biggest text (mapped to a font pair the website ships). Only HER colours, never a guess."""
    from ..site import inspire as INS
    nodes = doc["nodes"] if isinstance(doc.get("nodes"), dict) else doc
    tree = _Tree(nodes)
    root = tree.node(node_id, key=node_id)
    g = _Gen(tree, root, {}, "src", True, "")
    g.plan_roles()
    ink, sizes, buttons, radii = Counter(), [], [], []
    todo = [root]
    while todo:
        v = todo.pop()
        kids = tree.children(v) if v.type in CONTAINERS else []
        todo.extend(kids)
        if v.type == "TEXT":
            c = _first_color([p for p in g.fills(v) if p.get("type") in (None, "solid")])
            if c and c.startswith("#"):
                ink[c] += len(str(v.get("chars") or ""))
            sizes.append((_num(v.get("fontSize"), 16), str(v.get("font") or "Inter")))
        if g.roles.get(v.key) == "button":
            f = [p for p in g.fills(v) if p.get("type") in (None, "solid")]
            if f:
                buttons.append(_hex6(f[-1].get("color")))
            rad = v.get("radius", 0)
            radii.append(_num(rad[0] if isinstance(rad, list) and rad else rad))
    bgf = [p for p in g.fills(root) if p.get("type") in (None, "solid")]
    over: dict[str, Any] = {}
    if bgf:
        over["bg"] = over["surface"] = _hex6(bgf[-1].get("color"))
    if ink:
        over["ink"] = ink.most_common(1)[0][0][:7]
    if buttons:
        over["primary"] = buttons[0]
        over["accent"] = next((b for b in buttons[1:] if b != buttons[0]), buttons[0])
    head = max(sizes, default=(0, "Inter"))[1]
    kind = INS.font_kind(head)
    over["fonts"] = INS.font_pair(kind, head)
    over["radius"] = int(max(0, min(40, radii[0] if radii else 8)))
    dark = bool(over.get("bg")) and INS._rel_lum(over["bg"]) < 0.2
    vivid = bool(over.get("primary")) and INS._sat(over["primary"]) > 0.45
    style = INS.pick_style(kind, dark, over["radius"], vivid, "")
    return {"style": style, "overrides": over}


# ------------------------------------------------------------------------------- into Web Studio
def _pictures(tenant: str, site_id: str, images: list[dict], behind: str) -> tuple[dict[str, str], list[str]]:
    """Each picture of the frame into the SITE's own photo store (site.service.add_photo: re-encoded, EXIF gone).
    Returns hash -> the website's photo name, plus warnings."""
    from ..site import service as S
    from . import assets as DA
    names: dict[str, str] = {}
    warns: list[str] = []
    flat = 0
    for im in images:
        path = DA.asset_path(tenant, im["hash"])
        if path is None:
            continue
        data = path.read_bytes()
        try:
            data, was_clear = _flatten(data, behind)
        except Exception:
            warns.append(f"The picture in {im['alt'] or 'a layer'} could not be read and was left out.")
            continue
        flat += was_clear
        try:
            got = S.add_photo(tenant, site_id, data=data, about=im["alt"] or "From Hoola Design", name=im["name"])
        except S.SiteError as e:
            warns.append(f"The picture in {im['alt'] or 'a layer'} was not kept: {e}")
            continue
        names[im["hash"]] = got["name"]
    if flat:
        warns.append(f"{flat} picture{'s have' if flat != 1 else ' has'} see-through parts; the website keeps photos as JPEG, "
                     f"so those parts are filled with the colour behind them ({behind}).")
    return names, warns


def _flatten(data: bytes, behind: str) -> tuple[bytes, int]:
    """An SVG picture becomes pixels (resvg when the server has it); a see-through PNG / WebP / GIF is laid on the
    colour behind it, because the website keeps photos as JPEG."""
    from PIL import Image
    head = data[:512].lstrip()
    if head.startswith(b"<") and b"<svg" in data[:4096].lower():
        import resvg_py                                  # noqa: F401 - optional; without it the picture is skipped
        png = resvg_py.svg_to_bytes(svg_string=data.decode("utf-8", "replace"), width=1600)
        data = bytes(png)
    im = Image.open(io.BytesIO(data))
    clear = 0
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        lo, _hi = rgba.getchannel("A").getextrema()
        if lo < 255:
            r, g, b, _a = _hex_rgb(behind)
            bg = Image.new("RGBA", rgba.size, (r, g, b, 255))
            bg.alpha_composite(rgba)
            buf = io.BytesIO()
            bg.convert("RGB").save(buf, "PNG")
            return buf.getvalue(), 1
    return data, clear


def _behind(doc: dict, node_id: str) -> str:
    n = (doc.get("nodes") or {}).get(node_id) or {}
    for p in reversed(n.get("fills") or []):
        if _vis(p) and p.get("type") in (None, "solid"):
            return _hex6(p.get("color"))
    return "#FFFFFF"


def _frame_name(doc: dict, node_id: str, file_name: str) -> str:
    n = (doc.get("nodes") or {}).get(node_id) or {}
    name = re.sub(r"\s+", " ", str(n.get("name") or "")).strip()
    if not name or GENERIC_NAME.match(name):
        name = re.sub(r"\s+", " ", str(file_name or "")).strip() or name or "My website"
    return name[:120]


def _english(e: Exception) -> str:
    return str(e) or "Web Studio refused it."


FALLBACK_FIELD = "designer_profile"


def frame_by_name(doc: dict, ref: str) -> str:
    """A frame by id, else by its name (one clear match among the top-level frames first, then any frame)."""
    nodes = doc.get("nodes") or {}
    ref = str(ref or "").strip()
    if not ref:
        raise ToWebError("Which frame? Give its id or its name.")
    if ref in nodes:
        return ref
    frames = [(i, n) for i, n in nodes.items() if isinstance(n, dict) and n.get("type") in KINDS_OK]
    for pool in ([x for x in frames if (nodes.get(x[1].get("parent")) or {}).get("type") == "PAGE"], frames):
        hits = [i for i, n in pool if str(n.get("name") or "").strip().lower() == ref.lower()]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ToWebError(f"More than one frame is called '{ref[:60]}'; give its id.")
    raise ToWebError(f"No frame called '{ref[:60]}' in this file.", 404)


def preview(doc: dict, node: str, heading_top: bool = True) -> dict[str, Any]:
    out = frame_to_html(doc, node, {}, heading_top=heading_top, img_mode="src")
    return {k: out[k] for k in ("html", "css", "images", "fonts", "warnings", "name", "w", "h", "layers")}


def send(tenant: str, file: dict, doc: dict, body: dict) -> dict[str, Any]:
    """POST /files/{id}/to-site: ONE frame into Web Studio. mode new = a new site whose first page is this frame;
    mode section = the frame added to a page of her built site. Never publishes."""
    from ..site import build as B
    from ..site import code as CD
    from ..site import library as L
    from ..site import service as S
    from ..site import taxonomy as T
    node = str(body.get("node") or "").strip()
    mode = str(body.get("mode") or ("section" if body.get("site") else "new")).strip().lower()
    if mode not in ("new", "section"):
        raise ToWebError('mode is "new" or "section".')
    if not node:
        raise ToWebError("Which frame? Select one frame first.")
    first = frame_to_html(doc, node, {}, heading_top=mode == "new")      # checks the frame + lists the pictures
    name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:120] or _frame_name(doc, node, file.get("name", ""))
    typ = T.custom_type(_frame_name(doc, node, file.get("name", "")))
    note = f"From Hoola Design: {file.get('name') or 'a file'} / {first['name']}"[:200]
    if mode == "new":
        brief = re.sub(r"\s+", " ", str(body.get("brief") or "")).strip()[:2000] or f"{name} website"
        try:
            fid = L.understand(brief).get("field") or FALLBACK_FIELD
        except Exception:
            fid = FALLBACK_FIELD
        section = {"type": typ, "label": first["name"][:40] or "Design", "design": note}

        def shape(br: dict, plan: dict) -> dict:
            legal = [p for p in plan.get("pages", []) if p.get("slug") in B.LEGAL_PAGES]
            home = {"slug": "home", "title": "Home", "nav": "Home", "why": "", "sections": [section]}
            return {**plan, "pages": [home] + legal, "collections": []}
        try:
            v = S.new(tenant, brief, "", name=name, field=fid, shape=shape)
        except S.SiteError as e:
            raise ToWebError(_english(e), 400) from None
        sid, slug_ = v["id"], "home"
        r = S._load(sid)
        extra = [] if fid != FALLBACK_FIELD or body.get("brief") else [
            "Web Studio could not tell the kind of business from the name, so the site is set up as a general profile; "
            "say what it is for in Web Studio's chat."]
    else:
        ref = str(body.get("site") or "").strip()
        if not ref:
            raise ToWebError("Which website? Pick one of your sites.")
        try:
            with_row = S.get(tenant, ref)
        except S.SiteError:
            raise ToWebError("That website was not found.", 404) from None
        sid = with_row["id"]
        r = S._load(sid)
        if r.status in ("planned", "looks", "draft"):
            raise ToWebError("This website is not built yet. Finish it in Web Studio first, or send the frame as a new site.", 409)
        if S.busy(sid) and S._JOBS.get(sid) != "save":
            raise ToWebError("Web Studio is working on this website right now. Try again when it finishes.", 409)
        try:
            r = S._editable(tenant, sid)
        except S.SiteError as e:
            raise ToWebError(_english(e), 409) from None
        plan = S._j(r.plan, {})
        slug_ = str(body.get("page") or "home").strip().lower()
        page = next((p for p in plan.get("pages", []) if p.get("slug") == slug_), None)
        if page is None or page.get("template_of"):
            raise ToWebError("That page is not on this website.", 404)
        if slug_ in B.LEGAL_PAGES:
            raise ToWebError("The legal pages are written by Web Studio itself; pick another page.", 409)
        customs = [s for s in page.get("sections", []) if s.get("type") not in T.SECTIONS]
        if len(customs) >= T.CUSTOM_PER_PAGE:
            raise ToWebError(f"That page already has {T.CUSTOM_PER_PAGE} free-form sections, Web Studio's limit. "
                             "Pick another page or remove one in Web Studio.", 409)
        have = {s.get("type") for s in page.get("sections", [])}
        base, i = typ, 2
        while typ in have:
            typ = f"{base[:28]}_{i}"
            i += 1
        extra = []
    key = S.sec_key(slug_, typ)
    scope = S.sec_id(slug_, typ)
    behind = _behind(doc, node)
    names, warns = _pictures(tenant, sid, first["images"], behind)
    out = frame_to_html(doc, node, names, scope=scope, heading_top=mode == "new", img_mode="hoola")
    sec, removed = CD.clean(key, {"html": "", "css": out["css"], "js": ""}, "html", out["html"])
    sec["from_design"] = {"file": file.get("id"), "node": node}
    r = S._load(sid)
    if mode == "new":
        plan = S._j(r.plan, {})
        look = {"tokens": None, "mine": True}
        tk = design_tokens(doc, node)
        look["tokens"] = B.tokens(tk["style"], "paper_ink", None, tk["overrides"])
        S._put_sec(r, key, sec)
        S._save(sid, style=tk["style"], look=look, status="checking", stage="checks",
                board=S._board(r, plan, {key: "done"}, "From Hoola Design"))
        if not S._start(sid, "save", note=note):
            S._SAVE_PENDING.add(sid)
    else:
        plan = S._j(r.plan, {})
        for p in plan.get("pages", []):
            if p.get("slug") == slug_:
                p.setdefault("sections", []).append({"type": typ, "label": first["name"][:40] or "Design", "design": note})
        r = S._save(sid, plan=plan)
        S._put_sec(r, key, sec)
        r = S._save(sid, board=S._board(r, plan, {key: "done"}))
        S._after_edit(r, note, quick=[slug_])
    final = S._load(sid)
    return {"ok": True, "site": sid, "number": final.number, "name": final.name, "page": slug_, "section": key,
            "mode": mode, "url": f"/console/web#/site/{sid}", "status": final.status,
            "images": len(names), "fonts": out["fonts"], "removed": removed,
            "warnings": out["warnings"] + warns + extra,
            "say": ("A new website was started in Web Studio from this frame." if mode == "new" else
                    f"The frame was added to the {slug_} page in Web Studio.") +
                   " Web Studio checks it and saves a version; nothing is published until you go live there."}


# ------------------------------------------------------------------------------- routes
def mount(r, current_tenant) -> None:
    """Two routes on the design router (auth + tenant come from it): the code preview and the send."""
    from fastapi import Depends, HTTPException

    from . import store
    from .doc import loads
    from .room import HUB, bg

    async def _doc(file_id: str, tenant: str) -> tuple[dict, dict]:
        f = await bg(store.get_file, tenant, file_id)
        if f is None:
            raise HTTPException(404, "File not found")
        if f.get("trashed"):
            raise HTTPException(409, "This file is in the trash; restore it first.")
        if f.get("role", "edit") != "edit":
            raise HTTPException(403, "This file is view only.")
        got = await HUB.read(file_id, tenant)
        if got is None:
            raise HTTPException(404, "File not found")
        return f, await bg(loads, got[1])

    @r.post("/files/{file_id}/to-site/preview")
    async def to_site_preview(file_id: str, body: dict, tenant: str = Depends(current_tenant)):
        """The code Web Studio would get, read only (nothing is sent, no site is touched)."""
        _f, doc = await _doc(file_id, tenant)
        try:
            return await bg(preview, doc, str((body or {}).get("node") or ""), str((body or {}).get("mode") or "new") != "section")
        except ToWebError as e:
            raise HTTPException(e.status, str(e)) from None

    @r.post("/files/{file_id}/to-site")
    async def to_site(file_id: str, body: dict, tenant: str = Depends(current_tenant)):
        """{node, mode: new|section, site?, page?, name?, brief?} -> {site, page, url, warnings}. Never publishes."""
        f, doc = await _doc(file_id, tenant)
        try:
            return await bg(send, tenant, f, doc, body or {})
        except ToWebError as e:
            raise HTTPException(e.status, str(e)) from None
