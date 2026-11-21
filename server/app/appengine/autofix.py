"""v0.999.65 D4 AUTOFIX (docs/WEB_DESIGN_ENGINE_PLAN.md P5): every file written into an App Engine app is repaired by
code BEFORE the rules read it, so a slip a model always makes (a Tailwind palette colour, a hex value, `transition-all`,
an <img> with no alt, an emoji icon, a browser alert, two <h1> on one page, a button with no focus ring) never costs a
refused write and another model call. What is fixed is said in the write's answer (file:line, was -> now), so the writer
learns it; what code cannot fix safely is left for the rules, which still refuse it with file:line.

Every fixer only ever swaps a value for the design's OWN token (the app's tokens decide which one is nearest) or adds
what is missing; nothing is deleted except an emoji character and the colour stops of a gradient on a button.

Not fixed by code, said plainly: the browser's own <select> / date box / confirm() / prompt() (the replacement changes
how the code works), more than 3 gradients in a file, unsafe code, outside imports, and empty states for lists (code
cannot know what an empty list should say)."""
from __future__ import annotations

import colorsys
import math
import re
from typing import Any

from . import rules as RL

NEUTRAL = {"slate", "gray", "zinc", "neutral", "stone"}
# the hue of each Tailwind colour family, to tell the brand colour from the accent
HUES = {"red": 25, "orange": 45, "amber": 70, "yellow": 90, "lime": 120, "green": 145, "emerald": 160, "teal": 175,
        "cyan": 190, "sky": 210, "blue": 230, "indigo": 255, "violet": 270, "purple": 285, "fuchsia": 305, "pink": 330,
        "rose": 350}
STATE = {"red": "bad", "rose": "bad", "green": "ok", "emerald": "ok", "amber": "warn", "yellow": "warn"}
RX_PAL = re.compile(r"(?<![\w-])(" + RL._UTIL + r")-(?:(" + RL._PALETTE + r")-(\d{2,3})|(white|black))(?:/(\d{1,3}))?(?![\w-])")
RX_ARB = re.compile(r"(?<![\w-])(-?)([a-z][a-z0-9-]*?)-\[([^\]\s]+)\]")
SPACING = {"p", "px", "py", "pt", "pr", "pb", "pl", "ps", "pe", "m", "mx", "my", "mt", "mr", "mb", "ml", "ms", "me",
           "gap", "gap-x", "gap-y", "space-x", "space-y", "w", "h", "size", "min-w", "min-h", "max-h", "inset", "inset-x",
           "inset-y", "top", "right", "bottom", "left", "translate-x", "translate-y", "scroll-m", "scroll-p", "indent",
           "basis"}
MAX_W = [("xs", 320), ("sm", 384), ("md", 448), ("lg", 512), ("xl", 576), ("2xl", 672), ("3xl", 768), ("4xl", 896),
         ("5xl", 1024), ("6xl", 1152), ("7xl", 1280)]
TEXT = [("xs", 12), ("sm", 14), ("base", 16), ("lg", 18), ("xl", 20), ("2xl", 24), ("3xl", 30), ("4xl", 36),
        ("5xl", 48), ("6xl", 60), ("7xl", 72), ("8xl", 96)]
LEADING = [("none", 1.0), ("tight", 1.25), ("snug", 1.375), ("normal", 1.5), ("relaxed", 1.625), ("loose", 2.0)]
TRACKING = [("tighter", -0.05), ("tight", -0.025), ("normal", 0.0), ("wide", 0.025), ("wider", 0.05), ("widest", 0.1)]
WEIGHT = {"100": "thin", "200": "extralight", "300": "light", "400": "normal", "500": "medium", "600": "semibold",
          "700": "bold", "800": "extrabold", "900": "black"}
FRACTIONS = {"25%": "1/4", "33%": "1/3", "33.33%": "1/3", "50%": "1/2", "66%": "2/3", "66.66%": "2/3", "75%": "3/4",
             "100%": "full", "100vw": "screen", "100vh": "screen", "100dvh": "dvh", "100svh": "svh"}
COLOR_UTILS = {"bg", "text", "border", "border-t", "border-r", "border-b", "border-l", "border-x", "border-y", "ring",
               "ring-offset", "from", "to", "via", "fill", "stroke", "outline", "decoration", "accent", "caret", "divide",
               "placeholder", "shadow"}
RX_TAG = re.compile(r"<(button|a|Link|NavLink)\b((?:[^>\"'{]|\"[^\"]*\"|'[^']*'|\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})*)>",
                    re.S)
RX_IMG = re.compile(r"<img\b((?:[^>\"'{]|\"[^\"]*\"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})*?)(/?)>", re.S)
RX_HEAD = re.compile(r"<(/?)h([1-6])(?=[\s>/])")
RX_ALERT = re.compile(r"(?<![\w.$])(?:window\.)?alert\s*\(")
RX_CSS_TRANS = re.compile(r"\btransition\s*:\s*all\b([^;}\n]*)")
RX_CSS_PROP = re.compile(r"\btransition-property\s*:\s*all\b")
RX_GRADIENT_CLS = re.compile(r"(?<![\w-])bg-(?:gradient-to|linear|radial|conic)-[\w-]+")
RX_STOPS = re.compile(r"(?<![\w-])(?:from|via|to)-[a-z][\w/.-]*(?=[\s\"'`}])")


# ---------------------------------------------------------------- colour: the nearest token
def _rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    h = h[:6]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _lab(c: tuple[float, float, float]) -> tuple[float, float, float]:
    def lin(u: float) -> float:
        return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in c)
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def _parse_colour(v: str) -> tuple[tuple[float, float, float], float] | None:
    """(rgb 0-1, alpha) of a hex / rgb() / hsl() value; None when it is not one."""
    v = v.strip().replace("_", " ")
    m = re.fullmatch(r"#([0-9a-fA-F]{3,8})", v)
    if m and len(m.group(1)) in (3, 4, 6, 8):
        h = m.group(1)
        a = 1.0
        if len(h) == 8:
            a = int(h[6:8], 16) / 255
        elif len(h) == 4:
            a = int(h[3] * 2, 16) / 255
        return _rgb(h), a
    m = re.fullmatch(r"(rgba?|hsla?)\(\s*([^)]*)\)", v, re.I)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    try:
        nums = [float(p.rstrip("%deg")) / (100 if p.endswith("%") and i == 3 else 1) for i, p in enumerate(parts)]
    except ValueError:
        return None
    if len(nums) < 3:
        return None
    a = nums[3] if len(nums) > 3 else 1.0
    if m.group(1).lower().startswith("rgb"):
        return (nums[0] / 255, nums[1] / 255, nums[2] / 255), a
    r, g, b = colorsys.hls_to_rgb(nums[0] / 360, nums[2] / 100, nums[1] / 100)
    return (r, g, b), a


def nearest(rgb: tuple[float, float, float], tokens: dict[str, Any], pool: tuple[str, ...] = ()) -> str:
    """The design token whose colour is closest (OKLab) to this one."""
    keys = pool or ("bg", "surface", "ink", "muted", "line", "primary", "accent", "ok", "warn", "bad")
    want = _lab(rgb)
    best, bd = "primary", 9e9
    for k in keys:
        val = str(tokens.get(k) or "")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", val):
            continue
        d = math.dist(want, _lab(_rgb(val)))
        if d < bd:
            best, bd = k, d
    return best.replace("_", "-")


def _hue(hexv: str) -> float:
    r, g, b = _rgb(hexv)
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360


def _hue_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def palette_token(util: str, family: str, shade: int, tokens: dict[str, Any], line: str) -> tuple[str, str]:
    """(token, opacity) for a Tailwind palette colour on this utility."""
    textish = util in ("text", "placeholder", "decoration", "caret")
    lineish = util.startswith("border") or util in ("ring", "outline", "divide", "stroke")
    if family in ("white", "black"):
        if family == "black":
            return ("ink", "")
        if textish:
            return ("bg" if "bg-ink" in line else "primary-ink", "")
        if lineish:
            return ("line", "")
        return ("surface", "")
    if family in NEUTRAL:
        if textish:
            return ("muted" if shade <= 500 else "ink", "")
        if lineish:
            return ("line" if shade <= 400 else "ink", "")
        if util == "ring-offset":
            return ("bg", "")
        if shade <= 100:
            return ("surface", "")
        if shade <= 300:
            return ("line", "")
        if shade <= 500:
            return ("muted", "")
        return ("ink", "")
    tok = STATE.get(family)
    if not tok:
        tok = "primary"
        h = HUES.get(family)
        p, a = str(tokens.get("primary") or ""), str(tokens.get("accent") or "")
        if h is not None and re.fullmatch(r"#[0-9a-fA-F]{6}", p) and re.fullmatch(r"#[0-9a-fA-F]{6}", a):
            if _hue_gap(h, _hue(a)) + 15 < _hue_gap(h, _hue(p)):
                tok = "accent"
    if textish or lineish:
        return (tok, "" if shade >= 400 else "60")
    if shade <= 50:
        return (tok, "5")
    if shade <= 100:
        return (tok, "10")
    if shade <= 200:
        return (tok, "20")
    if shade <= 300:
        return (tok, "40")
    if shade >= 900:
        return ("ink", "")
    return (tok, "")


# ---------------------------------------------------------------- one-off values: the nearest step on the scale
def _px(v: str) -> float | None:
    m = re.fullmatch(r"(-?\d*\.?\d+)(px|rem|em)?", v)
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) in ("rem", "em") else n


def _closest(pairs: list[tuple[str, float]], x: float) -> str:
    return min(pairs, key=lambda p: abs(p[1] - x))[0]


def one_off(neg: str, util: str, val: str, tokens: dict[str, Any]) -> str | None:
    """The scale class for `util-[val]`, or None when code cannot pick one safely."""
    col = _parse_colour(val)
    if col is not None and util in COLOR_UTILS:
        rgb, a = col
        pool = ("ink", "muted", "bg", "surface") if util in ("text", "placeholder") else ()
        tok = nearest(rgb, tokens, pool)
        op = "" if a >= 0.95 else f"/{max(5, min(95, int(round(a * 20)) * 5))}"
        return f"{util}-{tok}{op}"
    if util in SPACING:
        if val in FRACTIONS and util in ("w", "h", "basis", "size", "min-h", "min-w", "max-h"):
            f = FRACTIONS[val]
            return f"{neg}{util}-{f}"
        px = _px(val)
        if px is None:
            return None
        step = round(abs(px) / 4 * 4) / 4                 # Tailwind v4: every 0.25 step exists (p-13, gap-4.5)
        s = (f"{step:.2f}".rstrip("0").rstrip("."))
        return f"{neg}{util}-{s}"
    if util == "max-w":
        if val.endswith("ch"):
            return "max-w-prose"
        if val in FRACTIONS:
            return f"max-w-{FRACTIONS[val]}"
        px = _px(val)
        return f"max-w-{_closest(MAX_W, px)}" if px is not None else None
    if util == "text":
        px = _px(val)
        return f"text-{_closest(TEXT, px)}" if px is not None else None
    if util == "leading":
        try:
            n = float(val)
        except ValueError:
            px = _px(val)
            n = (px / 16) if px is not None else None
        return f"leading-{_closest(LEADING, n)}" if n is not None else None
    if util == "tracking":
        m = re.fullmatch(r"(-?\d*\.?\d+)em", val)
        return f"tracking-{_closest(TRACKING, float(m.group(1)))}" if m else None
    if util == "rounded" or util.startswith("rounded-"):
        if val in ("50%", "9999px", "999px", "100%"):
            return f"{util}-full"
        px = _px(val)
        if px is None:
            return None
        r = int(tokens.get("radius") or 12)
        side = util[len("rounded"):]                      # "", "-t", "-tl"...
        if px <= 0:
            return f"rounded{side}-none"
        if px >= 40:
            return f"rounded{side}-full"
        return f"rounded{side}-" + ("control" if abs(px - max(4, r - 4)) <= abs(px - (r + 4)) else "card")
    if util == "font" and val in WEIGHT:
        return f"font-{WEIGHT[val]}"
    if util == "z":
        try:
            n = int(val)
        except ValueError:
            return None
        return f"z-{min(50, max(0, int(round(n / 10.0)) * 10))}"
    if util in ("opacity", "duration", "delay"):
        m = re.fullmatch(r"(\d*\.?\d+)(ms|s)?", val)
        if not m:
            return None
        n = float(m.group(1))
        if util == "opacity":
            n = n * 100 if n <= 1 else n
            return f"opacity-{int(round(n / 5) * 5)}"
        n = n * 1000 if m.group(2) == "s" else n
        return f"{util}-{int(round(n))}"
    return None


# ---------------------------------------------------------------- the fixers
def _line_of(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


class _Fix:
    def __init__(self, path: str):
        self.path = path
        self.done: list[dict[str, Any]] = []

    def add(self, line: int, rule: str, was: str, now: str) -> None:
        self.done.append({"file": self.path, "line": line, "rule": rule, "was": was[:80], "now": now[:80]})


def _fix_colours(code: str, tokens: dict[str, Any], f: _Fix, css: bool) -> str:
    out = []
    for n, line in enumerate(code.splitlines(True), 1):
        if css and "@apply" not in line:
            out.append(line)
            continue

        def pal(m: re.Match) -> str:
            util, fam, shade, bw, op = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            if util == "shadow":                              # a shadow's colour: the design's own shadow instead
                f.add(n, "palette colour", m.group(0), "shadow-card")
                return "shadow-card"
            tok, auto = palette_token(util, fam or bw, int(shade or 500), tokens, line)
            o = op or auto
            now = f"{util}-{tok}" + (f"/{o}" if o else "")
            f.add(n, "palette colour", m.group(0), now)
            return now
        line = RX_PAL.sub(pal, line)

        def arb(m: re.Match) -> str:
            s = m.group(0)
            if RL.RX_ARB_OK.search(s):
                return s
            got = one_off(m.group(1), m.group(2), m.group(3), tokens)
            if not got:
                return s
            f.add(n, "one-off value", s, got)
            return got
        line = RX_ARB.sub(arb, line)
        out.append(line)
    return "".join(out)


def _fix_raw(code: str, tokens: dict[str, Any], f: _Fix, path: str) -> str:
    """Hex / rgb() / hsl() left outside classes (inline styles, CSS, chart colours) -> var(--color-<token>)."""
    probs = {(p["line"], p["found"]) for p in RL.drift(path, code) if p["rule"] == "raw colour"}
    if not probs:
        return code
    lines = code.splitlines(True)
    rx = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])|"
                    r"\b(?:rgba?|hsla?)\([^()]*\)")
    for n in sorted({ln for ln, _ in probs}):
        line = lines[n - 1]

        def sub(m: re.Match) -> str:
            before = line[max(0, m.start() - 8):m.start()]
            if re.search(r"""(?:href|to|id)=["'{]?$""", before):
                return m.group(0)
            col = _parse_colour(m.group(0))
            if col is None:
                return m.group(0)
            rgb, a = col
            tok = nearest(rgb, tokens)
            now = f"var(--color-{tok})" if a >= 0.95 else \
                f"color-mix(in oklch, var(--color-{tok}) {int(round(a * 100))}%, transparent)"
            f.add(n, "raw colour", m.group(0), now)
            return now
        lines[n - 1] = rx.sub(sub, line)
    return "".join(lines)


def _fix_transitions(code: str, f: _Fix, css: bool) -> str:
    out = []
    for n, line in enumerate(code.splitlines(True), 1):
        if re.search(r"(?<![\w-])transition-all(?![\w-])", line):
            pick = ("transition-transform" if re.search(r"(?<![\w-])-?(?:scale|translate|rotate|skew)-", line) else
                    "transition-opacity" if re.search(r"(?<![\w-])opacity-", line) else
                    "transition-shadow" if re.search(r"(?<![\w-])shadow-", line) and "bg-" not in line else
                    "transition-colors")
            line = re.sub(r"(?<![\w-])transition-all(?![\w-])", pick, line)
            f.add(n, "taste", "transition-all", pick)

        def css_all(m: re.Match) -> str:
            rest = m.group(1).strip()
            props = ("color", "background-color", "border-color", "opacity", "transform", "box-shadow")
            now = "transition: " + ", ".join(f"{p} {rest}".strip() for p in props)
            f.add(n, "taste", m.group(0).strip(), now)
            return now
        line = RX_CSS_TRANS.sub(css_all, line)
        if RX_CSS_PROP.search(line):
            line = RX_CSS_PROP.sub("transition-property: color, background-color, border-color, opacity, transform, box-shadow", line)
            f.add(n, "taste", "transition-property: all", "the properties that move")
        out.append(line)
    return "".join(out)


def _fix_gradient_buttons(code: str, f: _Fix) -> str:
    out = []
    for n, line in enumerate(code.splitlines(True), 1):
        if RL.RX_BTN.search(line) and RL.RX_GRAD.search(line) and RX_GRADIENT_CLS.search(line):
            line = RX_GRADIENT_CLS.sub("bg-primary", line, count=1)
            line = RX_GRADIENT_CLS.sub("", line)
            line = RX_STOPS.sub("", line)
            line = re.sub(r"(className=[\"'])\s+", r"\1", re.sub(r"(?<=\S)  +", " ", line))
            f.add(n, "taste", "a gradient on a button", "bg-primary")
        out.append(line)
    return "".join(out)


def _words_of(src: str) -> str:
    base = src.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    words = re.sub(r"[-_]+|\d+", " ", base).strip()
    return words[:60]


def _fix_img_alt(code: str, f: _Fix) -> str:
    def sub(m: re.Match) -> str:
        attrs = m.group(1)
        if re.search(r"(?<![\w-])alt\s*=", attrs) or "{..." in attrs:
            return m.group(0)
        src = re.search(r"""\bsrc\s*=\s*["']([^"']+)["']""", attrs)
        alt = _words_of(src.group(1)) if src else ""
        f.add(_line_of(code, m.start()), "a11y", "<img> with no alt", f'alt="{alt}"')
        return f'<img alt="{alt}"{attrs}{m.group(2)}>'
    return RX_IMG.sub(sub, code)


def _fix_emoji(code: str, f: _Fix) -> str:
    out = []
    for n, line in enumerate(code.splitlines(True), 1):
        if RL.RX_EMOJI.search(line):
            found = "".join(RL.RX_EMOJI.findall(line))[:8]
            line = re.sub(r"[ \t]?(?:" + RL.RX_EMOJI.pattern + r")+[ \t]?",
                          lambda m: " " if m.group(0).startswith(" ") and m.group(0).endswith(" ") else "", line)
            f.add(n, "taste", f"emoji {found}", "removed (use a lucide-react icon)")
        out.append(line)
    return "".join(out)


def _fix_alert(code: str, f: _Fix) -> str:
    if not RX_ALERT.search(code) or re.search(r"(?:function|const|let|var)\s+alert\b", code):
        return code
    hits = [m.start() for m in RX_ALERT.finditer(code)]
    for p in hits:
        f.add(_line_of(code, p), "taste", "alert(...)", "toast(...) from sonner")
    code = RX_ALERT.sub("toast(", code)
    if not re.search(r"""import\s*\{[^}]*\btoast\b[^}]*\}\s*from\s*["']sonner["']""", code):
        m = re.match(r"(?:\s*[\"']use client[\"'];?\s*\n)?", code)
        at = m.end() if m else 0
        code = code[:at] + 'import { toast } from "sonner";\n' + code[at:]
    return code


def _fix_headings(code: str, f: _Fix, path: str) -> str:
    """One <h1> a page, and no skipped level (h2 -> h4 becomes h3): screen readers and Google read the outline."""
    if not path.startswith(("src/pages/", "src/components/sections/")):
        return code
    out, pos, prev, stack, h1 = [], 0, 0, [], 0
    for m in RX_HEAD.finditer(code):
        close, lv = m.group(1) == "/", int(m.group(2))
        new = lv
        if close:
            if stack and stack[-1][0] == lv:
                new = stack.pop()[1]
        else:
            if lv == 1:
                h1 += 1
                if h1 > 1:
                    new = 2
            if prev and new > prev + 1:
                new = prev + 1
            if new != lv:
                f.add(_line_of(code, m.start()), "a11y", f"<h{lv}>", f"<h{new}>")
            stack.append((lv, new))
            prev = new
        out.append(code[pos:m.start()])
        out.append(f"<{m.group(1)}h{new}")
        pos = m.end()
    out.append(code[pos:])
    return "".join(out)


def _fix_states(code: str, f: _Fix) -> str:
    """The kit gives every focusable element a focus ring (index.css :focus-visible); code that switches it off
    (outline-none) gets it back. A button or a card link with its own colours and no hover state gets one."""
    def sub(m: re.Match) -> str:
        tag, attrs = m.group(1), m.group(2)
        cm = re.search(r"""\bclassName\s*=\s*(["'])([^"']*)\1""", attrs)
        if not cm:
            return m.group(0)
        cls = cm.group(2)
        add, why = [], []
        if re.search(r"(?<![\w-])(?:focus:)?outline-none(?![\w-])", cls) and not re.search(r"(?<![\w-])focus-visible:", cls):
            add.append("focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary")
            why.append("focus ring switched off")
        inside_button = "asChild" in code[max(0, m.start() - 160):m.start()]
        if not re.search(r"(?<![\w-])hover:", cls) and not inside_button:
            if re.search(r"(?<![\w-])bg-primary(?![\w/-])", cls):
                add.append("hover:bg-primary/90")
                why.append("hover")
            elif re.search(r"(?<![\w-])bg-(?:surface|bg)(?![\w-])", cls) and re.search(r"(?<![\w-])border(?![\w-])", cls):
                add.append("hover:border-primary")
                why.append("hover")
        if not add:
            return m.group(0)
        if "transition" not in cls and any(a.startswith("hover:") for a in add):
            add.append("transition-colors")
        now = (cls + " " + " ".join(add)).strip()
        f.add(_line_of(code, m.start()), "states", f"<{tag}> with no " + " / ".join(why), " ".join(add))
        q = cm.group(1)
        new_attrs = attrs[:cm.start()] + f"className={q}{now}{q}" + attrs[cm.end():]
        return f"<{tag}{new_attrs}>"
    return RX_TAG.sub(sub, code)


def fix(path: str, code: str, tokens: dict[str, Any] | None = None) -> tuple[str, list[dict[str, Any]]]:
    """The repaired code + what was repaired. Never raises: a fixer that trips leaves the code to the rules."""
    p, e = RL.norm(path), RL.ext(path)
    if e not in RL.CODE_EXT or p == "src/styles/tokens.css":
        return code, []
    from . import tokens as TK
    t = tokens or TK.resolve({}, "")
    f = _Fix(p)
    css = e == ".css"
    steps = [lambda c: _fix_colours(c, t, f, css), lambda c: _fix_raw(c, t, f, p), lambda c: _fix_transitions(c, f, css)]
    if not css:
        steps += [lambda c: _fix_gradient_buttons(c, f), lambda c: _fix_emoji(c, f)]
    if e == ".tsx":
        steps += [lambda c: _fix_img_alt(c, f), lambda c: _fix_headings(c, f, p), lambda c: _fix_states(c, f)]
    if not css:
        steps.append(lambda c: _fix_alert(c, f))      # last: it may add an import line (line numbers above stay right)
    for step in steps:
        try:
            code = step(code)
        except Exception:                            # noqa: BLE001 - a fixer never blocks a write; the rules still judge
            continue
    return code, f.done


def say(done: list[dict[str, Any]], limit: int = 6) -> str:
    if not done:
        return ""
    rows = [f"{x['file']}:{x['line']} {x['was']} -> {x['now']}" for x in done[:limit]]
    more = f" (+{len(done) - limit} more)" if len(done) > limit else ""
    return f" Fixed by itself before writing ({len(done)}): " + "; ".join(rows) + more + ". Write it that way next time."
