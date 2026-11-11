"""HOOLA DESIGN AI: the server's own layout pass for nodes the server makes.

The browser runs auto layout only for LOCAL edits (HD.layout.run at the end of a local transaction) - ops that
arrive from the server are drawn as they are. So a design the server makes must arrive already laid out: every
node with its x / y / w / h. This module is a port of `layoutAuto` / `layoutText` in hd-layout.js over plain
contract nodes ({id: props}), with ONE difference that is said plainly: the browser measures words with the real
font, this file ESTIMATES their width from a table of character widths. Line height is always written in pixels
by the AI code, so a text's height differs only when a line breaks at another word. The editor that asked for the
design runs the real layout once over the new nodes ("settle"), so what she ends up with is exact.

Not ported: `wrap` rows (treated as one line) and constraints of plain frames (children keep their place).
"""
from __future__ import annotations

import unicodedata
from typing import Callable

EPS = 0.01
CONTAINER = frozenset({"FRAME", "COMPONENT", "COMPONENT_SET", "SECTION"})

# ------------------------------------------------------------------------------------------- words
_NARROW = set("iljI.,:;'|!`[](){}")
_SEMI = set("frt\"*-/\\ ")
_WIDE = set("mwMW@%")
_FONT_FACTOR = {            # width against a typical grotesque (Inter = 1.0); a table, not a measurement
    "bebas neue": 0.72, "oswald": 0.80, "barlow": 0.90, "rajdhani": 0.86, "roboto": 0.96, "lato": 0.95,
    "source sans 3": 0.93, "noto sans": 1.0, "open sans": 1.02, "poppins": 1.07, "montserrat": 1.10, "sora": 1.08,
    "lexend": 1.10, "outfit": 0.98, "manrope": 1.02, "plus jakarta sans": 1.03, "dm sans": 0.98, "nunito": 1.0,
    "playfair display": 0.99, "dm serif display": 0.98, "fraunces": 1.0, "lora": 1.0, "merriweather": 1.10,
    "cormorant garamond": 0.86, "eb garamond": 0.88, "literata": 1.03, "source serif 4": 0.97,
    "space grotesk": 1.0, "urbanist": 0.97, "figtree": 0.98, "work sans": 1.03, "rubik": 1.02,
    "hind": 0.95, "mukta": 0.94, "baloo 2": 0.98, "noto sans devanagari": 1.02, "anek devanagari": 0.95,
}
_MONO = {"jetbrains mono", "ibm plex mono", "space mono", "fira code", "roboto mono"}


def _char_em(ch: str) -> float:
    o = ord(ch)
    if o < 128:
        if ch in _NARROW:
            return 0.29
        if ch in _SEMI:
            return 0.36
        if ch in _WIDE:
            return 0.86
        if ch.isdigit():
            return 0.62
        if ch.isupper():
            return 0.68
        return 0.56
    cat = unicodedata.category(ch)
    if cat == "Mn" or cat == "Cf":
        return 0.0                       # a mark that sits on its base letter (matra above / below, virama, joiner)
    if cat == "Mc":
        return 0.30                      # a spacing vowel sign
    if 0x0900 <= o <= 0x0DFF:
        return 0.64                      # Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam
    if 0x0600 <= o <= 0x06FF:
        return 0.50                      # Arabic script (Urdu)
    if 0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFFEF:
        return 1.0
    if o >= 0x1F000:
        return 1.25                      # emoji
    if ch == "₹":
        return 0.60
    return 0.60


def text_width(text: str, font: str, size: float, weight: float = 400, letter_spacing: float = 0.0) -> float:
    """Estimated width in px (see the module note: a table, not the font)."""
    if not text:
        return 0.0
    fam = str(font or "Inter").lower()
    if fam in _MONO:
        em = 0.6 * sum(1 for ch in text if unicodedata.category(ch) not in ("Mn", "Cf"))
    else:
        em = sum(_char_em(ch) for ch in text) * _FONT_FACTOR.get(fam, 1.0)
        if weight >= 700:
            em *= 1.06
        elif weight >= 600:
            em *= 1.04
    return em * size + letter_spacing * len(text)


def _num(v, d: float) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf") else d


def line_height(node: dict) -> float:
    lh = node.get("lineHeight")
    size = max(0.1, _num(node.get("fontSize"), 16))
    return float(lh) if isinstance(lh, (int, float)) and not isinstance(lh, bool) and lh > 0 else round(size * 1.2, 2)


def text_lines(node: dict, wrap_w: float | None) -> tuple[int, float]:
    """(number of lines, widest line) of a TEXT node wrapped at wrap_w (None = no wrapping)."""
    chars = node.get("chars")
    chars = "" if chars is None else str(chars)
    case = node.get("textCase")
    if case == "upper":
        chars = chars.upper()
    font, size = node.get("font") or "Inter", max(0.1, _num(node.get("fontSize"), 16))
    weight, ls = _num(node.get("fontWeight"), 400), _num(node.get("letterSpacing"), 0)
    width = lambda s: text_width(s, font, size, weight, ls)      # noqa: E731
    lines, widest = 0, 0.0
    for para in chars.split("\n"):
        if wrap_w is None:
            lines += 1
            widest = max(widest, width(para))
            continue
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else cur + " " + word
            if cur and width(trial) > wrap_w + EPS:
                lines += 1
                widest = max(widest, width(cur))
                cur = word
            else:
                cur = trial
            while width(cur) > wrap_w + EPS and len(cur) > 1 and wrap_w > 0:     # one word wider than the box
                cut = max(1, int(len(cur) * wrap_w / max(1.0, width(cur))))
                lines += 1
                widest = max(widest, width(cur[:cut]))
                cur = cur[cut:]
        lines += 1
        widest = max(widest, width(cur))
    return max(1, lines), widest


# ------------------------------------------------------------------------------------------- layout
class Layout:
    """One pass over a subtree. `nodes` are changed in place (x, y, w, h only); `changed` collects the ids."""

    def __init__(self, nodes: dict[str, dict], children: Callable[[str], list[str]]):
        self.nodes, self.children = nodes, children
        self.changed: set[str] = set()
        self.remeasure: set[str] | None = None    # an EDIT: only these texts are measured again (see _text)
        self._w0: dict[str, float] = {}
        self._depth = 0

    # ---- reading
    def _g(self, n: dict, key: str, default):
        v = n.get(key)
        return default if v is None else v

    def _w(self, n: dict) -> float:
        return _num(n.get("w"), 100.0)

    def _h(self, n: dict) -> float:
        return 0.0 if n.get("type") == "LINE" else _num(n.get("h"), 100.0)

    def has_layout(self, n: dict) -> bool:
        lay = n.get("layout")
        return bool(isinstance(lay, dict) and lay.get("mode") in ("h", "v") and n.get("type") not in ("GROUP", "INSTANCE"))

    def _text_auto(self, n: dict, axis_h: bool) -> bool:
        ar = n.get("autoResize") or "wh"
        if self._g(n, "sizeH" if axis_h else "sizeV", "fixed") == "fill":
            return False
        return ar == "wh" if axis_h else ar != "none"

    def _hugs(self, n: dict, axis_h: bool) -> bool:
        if n.get("type") == "TEXT":
            return self._text_auto(n, axis_h)
        return self.has_layout(n) and self._g(n, "sizeH" if axis_h else "sizeV", "fixed") == "hug"

    def _in_flow(self, n: dict | None) -> bool:
        return bool(n) and n.get("visible") is not False and self._g(n, "layoutPos", "auto") != "absolute"

    @staticmethod
    def _clamp(c: dict, v: float, axis_h: bool) -> float:
        mn = _num(c.get("minW" if axis_h else "minH"), 0.0)
        mx = _num(c.get("maxW" if axis_h else "maxH"), float("inf"))
        if mx >= mn and v > mx:
            v = mx
        if v < mn:
            v = mn
        return max(0.0, v)

    # ---- writing
    def _put(self, nid: str, **vals: float) -> bool:
        n = self.nodes.get(nid)
        if n is None:
            return False
        hit = False
        for k, v in vals.items():
            v = round(float(v), 2)
            cur = self._w(n) if k == "w" else self._h(n) if k == "h" else _num(n.get(k), 0.0)
            if abs(cur - v) > EPS:
                n[k] = int(v) if v == int(v) else v
                hit = True
        if hit:
            self.changed.add(nid)
        return hit

    # ---- the pass
    def run(self, root: str) -> set[str]:
        """Lay out `root` and everything in it, deepest first (a container reads the sizes its children ended with)."""
        order: list[tuple[int, str]] = []
        stack = [(root, 0)]
        while stack:
            nid, depth = stack.pop()
            if nid not in self.nodes:
                continue
            order.append((depth, nid))
            stack.extend((c, depth + 1) for c in self.children(nid))
        if self.remeasure is not None:
            self._w0 = {nid: self._w(self.nodes[nid]) for _, nid in order if self.nodes[nid].get("type") == "TEXT"}
        for _, nid in sorted(order, key=lambda t: -t[0]):
            self._self(nid)
        return self.changed

    def _self(self, nid: str) -> None:
        n = self.nodes.get(nid)
        if n is None:
            return
        if n.get("type") == "TEXT":
            self._text(nid)
        elif self.has_layout(n):
            self._auto(nid)

    def _resized(self, nid: str) -> None:
        if self._depth > 200:
            return
        self._depth += 1
        try:
            self._self(nid)
        finally:
            self._depth -= 1

    def _text(self, nid: str) -> None:
        n = self.nodes[nid]
        w_auto, h_auto = self._text_auto(n, True), self._text_auto(n, False)
        if not w_auto and not h_auto:
            return
        if self.remeasure is not None and nid not in self.remeasure:
            # a text the edit did not touch keeps the size the browser measured, unless its wrapping width moved
            if w_auto or abs(self._w(n) - self._w0.get(nid, self._w(n))) <= EPS:
                return
        lines, widest = text_lines(n, None if w_auto else max(0.0, self._w(n)))
        vals = {}
        if w_auto:
            vals["w"] = widest
        if h_auto:
            vals["h"] = lines * line_height(n)
        self._put(nid, **vals)

    def _auto(self, nid: str) -> None:
        nodes = self.nodes
        n = nodes[nid]
        lay = n["layout"]
        if lay.get("wrap"):
            return                              # wrapping rows are not ported: left exactly as the browser laid them
        horiz = lay.get("mode") == "h"
        gap = _num(lay.get("gap"), 0.0)
        pad = lay.get("pad")
        if not isinstance(pad, list):
            pad = [_num(pad, 0.0)] * 4
        pt, pr, pb, pl = (_num(pad[i] if i < len(pad) else 0, 0.0) for i in range(4))
        pm0, pm1, pc0, pc1 = (pl, pr, pt, pb) if horiz else (pt, pb, pl, pr)
        align_main, align_cross = lay.get("alignMain") or "start", lay.get("alignCross") or "start"
        hug_main = self._g(n, "sizeH" if horiz else "sizeV", "fixed") == "hug"
        hug_cross = self._g(n, "sizeV" if horiz else "sizeH", "fixed") == "hug"
        kids = [c for c in self.children(nid) if self._in_flow(nodes.get(c))]
        main_of = (lambda c: self._w(c)) if horiz else (lambda c: self._h(c))
        cross_of = (lambda c: self._h(c)) if horiz else (lambda c: self._w(c))
        set_main = (lambda cid, v: self._put(cid, w=v)) if horiz else (lambda cid, v: self._put(cid, h=v))
        set_cross = (lambda cid, v: self._put(cid, h=v)) if horiz else (lambda cid, v: self._put(cid, w=v))

        def fills_main(c: dict) -> bool:
            return (not hug_main and c.get("type") != "GROUP"
                    and self._g(c, "sizeH" if horiz else "sizeV", "fixed") == "fill"
                    and not (c.get("type") == "LINE" and not horiz))

        def fills_cross(c: dict) -> bool:
            if c.get("type") == "GROUP" or (c.get("type") == "LINE" and horiz):
                return False
            sz = self._g(c, "sizeV" if horiz else "sizeH", "fixed")
            if sz == "fill":
                return True
            if align_cross != "stretch" or sz == "hug":
                return False
            return not self._hugs(c, not horiz)

        inner_main = max(0.0, main_of(n) - pm0 - pm1)
        inner_cross = max(0.0, cross_of(n) - pc0 - pc1)
        # 1. cross sizes that are already known
        if not hug_cross:
            for cid in kids:
                c = nodes[cid]
                if fills_cross(c) and (set_cross(cid, self._clamp(c, inner_cross, not horiz)) or c.get("type") == "TEXT"):
                    self._resized(cid)
        # 3. the free main space goes to the fill children
        if not hug_main:
            flex = [cid for cid in kids if fills_main(nodes[cid])]
            if flex:
                fixed = sum(main_of(nodes[cid]) for cid in kids if cid not in flex)
                free = inner_main - fixed - gap * (len(kids) - 1)
                size: dict[str, float] = {}
                open_ = list(flex)
                for _ in range(20):
                    if not open_:
                        break
                    share = max(0.0, free) / len(open_)
                    frozen = False
                    for cid in list(open_):
                        v = self._clamp(nodes[cid], share, horiz)
                        if abs(v - share) > EPS:
                            size[cid] = v
                            free -= v
                            open_.remove(cid)
                            frozen = True
                    if not frozen:
                        for cid in open_:
                            size[cid] = share
                        open_ = []
                for cid in flex:
                    if set_main(cid, size.get(cid, 0.0)) or nodes[cid].get("type") == "TEXT":
                        self._resized(cid)
        # 4. the line's cross size, then stretch what fills it

        def line_cross_now() -> tuple[float, bool]:
            mx, seen = 0.0, False
            for cid in kids:
                c = nodes[cid]
                if not fills_cross(c):
                    mx, seen = max(mx, cross_of(c)), True
            return mx, seen

        mx, seen = line_cross_now()
        if not seen:
            for cid in kids:
                c = nodes[cid]
                base = _num(c.get("minH" if horiz else "minW"), cross_of(c)) if hug_cross else inner_cross
                mx = max(mx, self._clamp(c, base, not horiz))
        line_cross = mx if hug_cross else inner_cross
        if hug_cross:
            for cid in kids:
                c = nodes[cid]
                if fills_cross(c) and (set_cross(cid, self._clamp(c, line_cross, not horiz)) or c.get("type") == "TEXT"):
                    self._resized(cid)
            mx, seen = line_cross_now()
            if seen:
                line_cross = mx
        # 5. the container's own hugging sizes
        own = {}
        if hug_main:
            m = sum(main_of(nodes[cid]) for cid in kids) + gap * max(0, len(kids) - 1) + pm0 + pm1
            own["w" if horiz else "h"] = self._clamp(n, m, horiz)
        if hug_cross:
            own["h" if horiz else "w"] = self._clamp(n, line_cross + pc0 + pc1, not horiz)
        if own:
            self._put(nid, **own)
        avail_main = max(0.0, main_of(n) - pm0 - pm1)
        line_cross = max(0.0, cross_of(n) - pc0 - pc1)
        # 6. place
        used = sum(main_of(nodes[cid]) for cid in kids)
        g, at = gap, pm0
        free = avail_main - used - gap * max(0, len(kids) - 1)
        if align_main == "center":
            at += free / 2
        elif align_main == "end":
            at += free
        elif align_main == "between" and len(kids) > 1:
            g = (avail_main - used) / (len(kids) - 1)
        for cid in kids:
            c = nodes[cid]
            cm, cc = main_of(c), cross_of(c)
            cr = pc0
            if align_cross == "center":
                cr += (line_cross - cc) / 2
            elif align_cross == "end":
                cr += line_cross - cc
            if horiz:
                self._put(cid, x=at, y=cr)
            else:
                self._put(cid, x=cr, y=at)
            at += cm + g


def run(nodes: dict[str, dict], children: Callable[[str], list[str]], root: str) -> set[str]:
    """Lay out one subtree in place; the ids whose box changed."""
    return Layout(nodes, children).run(root)
