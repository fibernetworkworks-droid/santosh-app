"""v0.566 LOTTIE on her website: small vector animations played by lottie-web's LIGHT player (MIT, SVG renderer only, no
expressions -> no eval, so the site's CSP stays `script-src 'self'`), loaded only on pages that use one.

Two sources:
- BUILT-IN animations made here by code (pulse, check, sparkle, scroll, dots, wave) in two placeholder colours that the
  page swaps for the site's own --c-primary / --c-accent at runtime, so they always match the look;
- HER OWN Lottie JSON file (e.g. downloaded from LottieFiles under a licence she holds), checked before it is kept: real
  Lottie shape (v / w / h / fr / ip / op / layers), at most 1.5 MB and 200 layers, images only embedded PNG / JPEG / WebP
  (never a link to another server), expressions stripped (the light player would not run them anyway).

A section writes `<div data-hoola-lottie="check" data-loop="false" aria-hidden="true"></div>`; the build adds the file address
(data-src) and copies only the animations used. Reduced motion = one still frame; off screen = paused.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PRIMARY = [1, 0, 1, 1]          # #FF00FF placeholder -> --c-primary
ACCENT = [0, 1, 1, 1]           # #00FFFF placeholder -> --c-accent
MAX_BYTES, MAX_LAYERS = 1_500_000, 200
NAME = re.compile(r"^[a-z][a-z0-9-]{1,39}$")


class LottieError(Exception):
    pass


# ---------------------------------------------------------------- built-ins, made by code
def _v(k):
    return {"a": 0, "k": k}


def _anim(frames: list[tuple[int, list[float]]], ease=(0.4, 1.0, 0.6, 0.0)) -> dict[str, Any]:
    ks = []
    for i, (t, s) in enumerate(frames):
        k: dict[str, Any] = {"t": t, "s": s}
        if i < len(frames) - 1:
            n = len(s)
            k["i"] = {"x": [ease[0]] * n, "y": [ease[1]] * n}
            k["o"] = {"x": [ease[2]] * n, "y": [ease[3]] * n}
        ks.append(k)
    return {"a": 1, "k": ks}


def _tr(p=(0, 0), s=(100, 100), r=0, o=100) -> dict[str, Any]:
    return {"ty": "tr", "p": _v(list(p)), "a": _v([0, 0]), "s": _v(list(s)), "r": _v(r), "o": _v(o), "sk": _v(0), "sa": _v(0)}


def _layer(ind: int, name: str, shapes: list, op: int, pos=(100, 100), scale=None, opacity=None, rot=None, ip: int = 0) -> dict:
    return {"ddd": 0, "ind": ind, "ty": 4, "nm": name, "sr": 1, "ao": 0, "ip": ip, "op": op, "st": 0, "bm": 0,
            "ks": {"o": opacity or _v(100), "r": rot or _v(0), "p": _v([pos[0], pos[1], 0]), "a": _v([0, 0, 0]),
                   "s": scale or _v([100, 100, 100])}, "shapes": shapes}


def _doc(name: str, op: int, layers: list, w: int = 200, h: int = 200) -> dict[str, Any]:
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": op, "w": w, "h": h, "nm": name, "ddd": 0, "assets": [], "layers": layers}


def _ellipse(d, stroke=None, fill=None, width=8):
    it = [{"ty": "el", "p": _v([0, 0]), "s": _v([d, d]), "d": 1}]
    if fill:
        it.append({"ty": "fl", "c": _v(fill), "o": _v(100), "r": 1})
    if stroke:
        it.append({"ty": "st", "c": _v(stroke), "o": _v(100), "w": _v(width), "lc": 2, "lj": 2})
    it.append(_tr())
    return {"ty": "gr", "it": it}


def _path(points: list[tuple[float, float]], closed=False) -> dict[str, Any]:
    n = len(points)
    return {"ty": "sh", "ks": _v({"i": [[0, 0]] * n, "o": [[0, 0]] * n, "v": [list(p) for p in points], "c": closed})}


def _star(r=26):
    pts = []
    import math
    for i in range(8):
        rad = r if i % 2 == 0 else r * 0.32
        a = math.pi / 4 * i - math.pi / 2
        pts.append((round(rad * math.cos(a), 2), round(rad * math.sin(a), 2)))
    return pts


def builtin(name: str) -> dict[str, Any]:
    if name == "pulse":                                   # a ring that breathes out from a dot (live / open / call)
        ring = _layer(1, "ring", [_ellipse(80, stroke=PRIMARY, width=6)], 60,
                      scale=_anim([(0, [40, 40, 100]), (59, [150, 150, 100])]), opacity=_anim([(0, [90]), (59, [0])]))
        dot = _layer(2, "dot", [_ellipse(46, fill=PRIMARY)], 60)
        return _doc("pulse", 60, [ring, dot])
    if name == "check":                                   # a circle and a tick drawn in (done / booked / paid)
        circ = {"ty": "gr", "it": [{"ty": "el", "p": _v([0, 0]), "s": _v([150, 150]), "d": 1},
                                   {"ty": "st", "c": _v(PRIMARY), "o": _v(100), "w": _v(9), "lc": 2, "lj": 2},
                                   {"ty": "tm", "s": _v(0), "e": _anim([(0, [0]), (24, [100])]), "o": _v(0), "m": 1}, _tr()]}
        tick = {"ty": "gr", "it": [_path([(-34, 2), (-8, 28), (38, -24)]),
                                   {"ty": "st", "c": _v(ACCENT), "o": _v(100), "w": _v(11), "lc": 2, "lj": 2},
                                   {"ty": "tm", "s": _v(0), "e": _anim([(18, [0]), (40, [100])]), "o": _v(0), "m": 1}, _tr()]}
        return _doc("check", 60, [_layer(1, "tick", [tick], 60), _layer(2, "circle", [circ], 60)])
    if name == "sparkle":                                 # three stars that twinkle (new / offer / festive)
        layers = []
        for i, (x, y, d) in enumerate(((70, 80, 0), (135, 60, 10), (115, 135, 20))):
            sh = {"ty": "gr", "it": [_path(_star(), closed=True), {"ty": "fl", "c": _v(PRIMARY if i != 1 else ACCENT), "o": _v(100), "r": 1}, _tr()]}
            layers.append(_layer(i + 1, f"star{i}", [sh], 60, pos=(x, y),
                                 scale=_anim([(d, [0, 0, 100]), (d + 15, [110, 110, 100]), (d + 30, [0, 0, 100])]),
                                 rot=_anim([(d, [0]), (d + 30, [90])])))
        return _doc("sparkle", 60, layers)
    if name == "scroll":                                  # an arrow that nudges down (scroll for more)
        arrow = {"ty": "gr", "it": [_path([(-26, -10), (0, 16), (26, -10)]),
                                    {"ty": "st", "c": _v(PRIMARY), "o": _v(100), "w": _v(10), "lc": 2, "lj": 2}, _tr()]}
        return _doc("scroll", 45, [_layer(1, "arrow", [arrow], 45,
                                          opacity=_anim([(0, [100]), (22, [45]), (44, [100])]),
                                          scale=_anim([(0, [100, 100, 100]), (22, [92, 92, 100]), (44, [100, 100, 100])]))])
    if name == "dots":                                    # three dots taking turns (working / typing)
        layers = []
        for i, x in enumerate((60, 100, 140)):
            d = i * 8
            layers.append(_layer(i + 1, f"dot{i}", [_ellipse(26, fill=PRIMARY if i != 1 else ACCENT)], 48, pos=(x, 100),
                                 scale=_anim([(d, [70, 70, 100]), (d + 12, [120, 120, 100]), (d + 24, [70, 70, 100])])))
        return _doc("dots", 48, layers)
    if name == "wave":                                    # a hand-wave arc (hello / welcome)
        arc = {"ty": "gr", "it": [_path([(-50, 20), (-25, -20), (0, 20), (25, -20), (50, 20)]),
                                  {"ty": "st", "c": _v(PRIMARY), "o": _v(100), "w": _v(10), "lc": 2, "lj": 2},
                                  {"ty": "tm", "s": _anim([(20, [0]), (50, [100])]), "e": _anim([(0, [0]), (30, [100])]), "o": _v(0), "m": 1}, _tr()]}
        return _doc("wave", 60, [_layer(1, "wave", [arc], 60)])
    raise LottieError(f"built-in animation '{name}' nahi hai")


BUILTINS = ("pulse", "check", "sparkle", "scroll", "dots", "wave")


# ---------------------------------------------------------------- her own file
def _strip_expr(node: Any, n: list[int]) -> Any:
    if isinstance(node, dict):
        if "x" in node and isinstance(node.get("x"), str) and ("k" in node or "a" in node):
            node.pop("x")                               # an expression (code): never shipped
            n[0] += 1
        for v in node.values():
            _strip_expr(v, n)
    elif isinstance(node, list):
        for v in node:
            _strip_expr(v, n)
    return node


def check(data: bytes) -> tuple[dict[str, Any], list[str]]:
    """Her Lottie JSON, made safe to serve. Returns (animation, notes) or raises LottieError with the reason."""
    if not data or len(data) > MAX_BYTES:
        raise LottieError("Lottie file khaali hai ya 1.5 MB se badi.")
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise LottieError("Yeh Lottie JSON file nahi lagti (.json bhejiye, .lottie zip nahi).")
    if not isinstance(doc, dict) or not all(k in doc for k in ("v", "w", "h", "fr", "ip", "op", "layers")) \
            or not isinstance(doc.get("layers"), list):
        raise LottieError("Isme Lottie ki zaroori cheezein nahi hain (v, w, h, fr, ip, op, layers).")
    if not doc["layers"] or len(doc["layers"]) > MAX_LAYERS:
        raise LottieError(f"Animation mein 1 se {MAX_LAYERS} layers honi chahiye.")
    notes: list[str] = []
    for a in doc.get("assets") or []:
        if not isinstance(a, dict):
            continue
        p, u = str(a.get("p") or ""), str(a.get("u") or "")
        if "layers" in a:
            continue                                    # a precomposition, not a file
        if p and not re.match(r"^data:image/(png|jpe?g|webp);base64,", p):
            raise LottieError("Animation kisi aur server ki tasveer maangti hai; sirf andar rakhi (embedded) tasveerein chalti hain.")
        if u:
            a["u"] = ""
        a["e"] = 1
    n = [0]
    _strip_expr(doc, n)
    if n[0]:
        notes.append(f"{n[0]} expressions hata diye (light player unhe chalata bhi nahi).")
    if doc.get("fonts") or doc.get("chars"):
        notes.append("Text layers ke fonts website ke font se dikhenge.")
    return doc, notes


def store(src: Path, name: str, data: bytes) -> dict[str, Any]:
    name = (name or "").strip().lower()
    if not NAME.match(name) or name in BUILTINS:
        raise LottieError("Naam chhota, angrezi akshar / ank / '-' mein, aur pehle se bane naam se alag (jaise 'meri-dukaan').")
    doc, notes = check(data)
    d = src / "lottie"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(doc, separators=(",", ":")))
    return {"name": name, "frames": int(doc["op"]) - int(doc["ip"]), "seconds": round((doc["op"] - doc["ip"]) / (doc["fr"] or 30), 1),
            "size": [doc["w"], doc["h"]], "notes": notes}


def hers(src: Path) -> list[str]:
    d = src / "lottie"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


LOTTIE_ATTR = re.compile(r"""data-hoola-lottie=["']([\w-]+)["']""")


def expand(html: str, rel: str, available: set[str]) -> tuple[str, set[str], list[str]]:
    """data-hoola-lottie="name" -> + data-src (the file this page loads). Unknown names lose the attribute (reported)."""
    used: set[str] = set()
    problems: list[str] = []

    def rep(m: re.Match) -> str:
        nm = m.group(1).lower()
        if nm not in available:
            problems.append(f"animation '{nm}' nahi hai")
            return 'data-hoola-lottie-missing=""'
        used.add(nm)
        return f'data-hoola-lottie="{nm}" data-src="{rel}assets/lottie/{nm}.json"'
    return LOTTIE_ATTR.sub(rep, html), used, problems


def write(out: Path, used: set[str], src: Path) -> None:
    d = out / "assets" / "lottie"
    d.mkdir(parents=True, exist_ok=True)
    mine = src / "lottie"
    for nm in sorted(used):
        if nm in BUILTINS:
            (d / f"{nm}.json").write_text(json.dumps(builtin(nm), separators=(",", ":")))
        elif (mine / f"{nm}.json").exists():
            (d / f"{nm}.json").write_bytes((mine / f"{nm}.json").read_bytes())
