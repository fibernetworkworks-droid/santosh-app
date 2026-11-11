"""HOOLA DESIGN AI: a small built-in icon set (own simple drawings on a 24 x 24 grid, stroke icons).

The model names an icon; code turns it into a VECTOR node. The renderer stretches a VECTOR's path so that the
path's own right / bottom edge meets the node's box (`vecScale` in hd-render.js), so an icon is emitted as its ink
box: `build(name, size)` gives the path moved to (0, 0) and scaled, the ink's width / height, and where that ink
box sits inside the size x size square. Only M / L / C / Z are used, absolute, so the bounds worked out here are
exactly the ones the browser works out.
"""
from __future__ import annotations

import math
import re

GRID = 24.0
_K = 0.5522847498


def _n(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _circle(cx: float, cy: float, r: float) -> str:
    k = r * _K
    return (f"M{_n(cx + r)} {_n(cy)} C{_n(cx + r)} {_n(cy + k)} {_n(cx + k)} {_n(cy + r)} {_n(cx)} {_n(cy + r)} "
            f"C{_n(cx - k)} {_n(cy + r)} {_n(cx - r)} {_n(cy + k)} {_n(cx - r)} {_n(cy)} "
            f"C{_n(cx - r)} {_n(cy - k)} {_n(cx - k)} {_n(cy - r)} {_n(cx)} {_n(cy - r)} "
            f"C{_n(cx + k)} {_n(cy - r)} {_n(cx + r)} {_n(cy - k)} {_n(cx + r)} {_n(cy)} Z")


def _rrect(x: float, y: float, w: float, h: float, r: float) -> str:
    k = r * (1 - _K)
    x1, y1 = x + w, y + h
    return (f"M{_n(x + r)} {_n(y)} L{_n(x1 - r)} {_n(y)} C{_n(x1 - k)} {_n(y)} {_n(x1)} {_n(y + k)} {_n(x1)} {_n(y + r)} "
            f"L{_n(x1)} {_n(y1 - r)} C{_n(x1)} {_n(y1 - k)} {_n(x1 - k)} {_n(y1)} {_n(x1 - r)} {_n(y1)} "
            f"L{_n(x + r)} {_n(y1)} C{_n(x + k)} {_n(y1)} {_n(x)} {_n(y1 - k)} {_n(x)} {_n(y1 - r)} "
            f"L{_n(x)} {_n(y + r)} C{_n(x)} {_n(y + k)} {_n(x + k)} {_n(y)} {_n(x + r)} {_n(y)} Z")


def _star(cx: float, cy: float, outer: float, inner: float) -> str:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = outer if i % 2 == 0 else inner
        pts.append(f"{_n(cx + r * math.cos(a))} {_n(cy + r * math.sin(a))}")
    return "M" + " L".join(pts) + " Z"


# name -> path data on the 24 grid. `FILLABLE` icons are closed shapes that also read well filled.
ICONS: dict[str, str] = {
    "arrow-right": "M4 12 L20 12 M13 5 L20 12 L13 19",
    "arrow-left": "M20 12 L4 12 M11 5 L4 12 L11 19",
    "arrow-up": "M12 20 L12 4 M5 11 L12 4 L19 11",
    "arrow-down": "M12 4 L12 20 M5 13 L12 20 L19 13",
    "chevron-right": "M9 5 L16 12 L9 19",
    "chevron-down": "M5 9 L12 16 L19 9",
    "check": "M4 12.5 L9.5 18 L20 6",
    "plus": "M12 4 L12 20 M4 12 L20 12",
    "minus": "M4 12 L20 12",
    "close": "M5 5 L19 19 M19 5 L5 19",
    "menu": "M4 6 L20 6 M4 12 L20 12 M4 18 L20 18",
    "filter": "M4 6 L20 6 M7 12 L17 12 M10 18 L14 18",
    "search": _circle(10.5, 10.5, 6.5) + " M15.5 15.5 L21 21",
    "user": _circle(12, 8, 4) + " M4 21 C4 16.5 7.5 14 12 14 C16.5 14 20 16.5 20 21",
    "cart": "M2 3 L5 3 L7.5 15 L18.5 15 L21 6.5 L6 6.5 " + _circle(9, 19.5, 1.5) + " " + _circle(17, 19.5, 1.5),
    "bag": "M5 8 L19 8 L20 21 L4 21 Z M9 8 C9 5 10 3.5 12 3.5 C14 3.5 15 5 15 8",
    "phone": _rrect(7, 2, 10, 20, 2.5) + " M11 18.5 L13 18.5",
    "mail": _rrect(3, 5, 18, 14, 2) + " M3.5 7 L12 13 L20.5 7",
    "chat": "M4 5 L20 5 L20 16 L11 16 L6.5 20 L6.5 16 L4 16 Z",
    "star": _star(12, 12.6, 9.6, 4.1),
    "heart": ("M12 20.5 C5 15.5 3 12 3 8.8 C3 6 5.2 4 7.8 4 C9.5 4 11 4.9 12 6.3 C13 4.9 14.5 4 16.2 4 "
              "C18.8 4 21 6 21 8.8 C21 12 19 15.5 12 20.5 Z"),
    "home": "M3 11 L12 3 L21 11 M5.5 9.5 L5.5 20 L18.5 20 L18.5 9.5 M10 20 L10 14 L14 14 L14 20",
    "calendar": _rrect(3, 5, 18, 16, 2) + " M3 10 L21 10 M8 3 L8 7 M16 3 L16 7",
    "clock": _circle(12, 12, 9) + " M12 7 L12 12 L15.5 14",
    "map-pin": ("M12 21.5 C7 16 5 13 5 9.8 C5 5.9 8.1 3 12 3 C15.9 3 19 5.9 19 9.8 C19 13 17 16 12 21.5 Z "
                + _circle(12, 9.8, 2.5)),
    "rupee": "M7 4 L17 4 M7 8.5 L17 8.5 M7 4 L10 4 C13 4 14.5 6 14.5 8.5 C14.5 11 13 13 10 13 L7 13 L15 21",
    "wallet": _rrect(3, 6, 18, 14, 2.5) + " M3 10 L21 10 " + _circle(16.5, 15, 1.2),
    "tag": "M3 3 L12 3 L21 12 L12 21 L3 12 Z " + _circle(7.5, 7.5, 1.3),
    "gift": (_rrect(3, 8, 18, 4, 1) + " M5 12 L5 21 L19 21 L19 12 M12 8 L12 21 "
             "M12 8 C10 8 7.5 7 7.5 5 C7.5 3.5 10 3 12 8 C14 3 16.5 3.5 16.5 5 C16.5 7 14 8 12 8"),
    "bell": ("M6 17 L6 11 C6 7.5 8.5 5 12 5 C15.5 5 18 7.5 18 11 L18 17 M4 17 L20 17 "
             "M10.5 20.5 C11 21.2 13 21.2 13.5 20.5 M12 3 L12 5"),
    "share": "M12 15 L12 3 M7.5 7.5 L12 3 L16.5 7.5 M5 12 L5 20 L19 20 L19 12",
    "download": "M12 3 L12 15 M7.5 10.5 L12 15 L16.5 10.5 M4 20 L20 20",
    "play": "M7 4 L20 12 L7 20 Z",
    "camera": _rrect(3, 7, 18, 13, 2) + " M8.5 7 L10 4.5 L14 4.5 L15.5 7 " + _circle(12, 13.5, 3.5),
    "image": _rrect(3, 4, 18, 16, 2) + " M3.5 17 L9 11.5 L13 15.5 L16 12.5 L20.5 17 " + _circle(15.5, 8.5, 1.5),
    "bolt": "M13 2 L4 14 L11 14 L10 22 L20 9.5 L13 9.5 Z",
    "lock": _rrect(5, 10.5, 14, 10.5, 2) + " M8 10.5 L8 7.5 C8 5 9.5 3 12 3 C14.5 3 16 5 16 7.5 L16 10.5",
    "shield": "M12 3 L19 6 L19 11.5 C19 16 16 19.5 12 21 C8 19.5 5 16 5 11.5 L5 6 Z",
    "truck": ("M2 6 L14 6 L14 17 L2 17 Z M14 10 L18.5 10 L22 13.5 L22 17 L14 17 "
              + _circle(6.5, 18.5, 2) + " " + _circle(17.5, 18.5, 2)),
    "globe": _circle(12, 12, 9) + " M3 12 L21 12 M12 3 C9 6 9 18 12 21 M12 3 C15 6 15 18 12 21",
    "sparkle": "M12 3 L13.8 9.2 L20 11 L13.8 12.8 L12 19 L10.2 12.8 L4 11 L10.2 9.2 Z",
}
FILLABLE = frozenset({"star", "heart", "play", "bolt", "sparkle", "shield", "chat", "tag"})
ALIASES = {"arrow": "arrow-right", "tick": "check", "done": "check", "add": "plus", "x": "close", "cross": "close",
           "person": "user", "profile": "user", "account": "user", "shopping-cart": "cart", "basket": "cart",
           "shopping-bag": "bag", "call": "phone", "mobile": "phone", "email": "mail", "envelope": "mail",
           "message": "chat", "comment": "chat", "favorite": "heart", "favourite": "heart", "like": "heart",
           "hamburger": "menu", "date": "calendar", "time": "clock", "location": "map-pin", "pin": "map-pin",
           "map": "map-pin", "money": "rupee", "price": "rupee", "inr": "rupee", "payment": "wallet",
           "notification": "bell", "offer": "tag", "discount": "tag", "present": "gift", "upload": "share",
           "send": "share", "save": "download", "video": "play", "photo": "image", "picture": "image",
           "flash": "bolt", "fast": "bolt", "secure": "lock", "safe": "shield", "delivery": "truck",
           "shipping": "truck", "web": "globe", "world": "globe", "ai": "sparkle", "magic": "sparkle",
           "chevron": "chevron-right", "next": "arrow-right", "back": "arrow-left"}

_TOK = re.compile(r"[MLCZ]|-?\d+(?:\.\d+)?")


def resolve(name: object) -> str:
    """The built-in icon a model's word means; '' when there is none."""
    key = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    if key in ICONS:
        return key
    return ALIASES.get(key, "")


def _segments(d: str) -> list[tuple]:
    out: list[tuple] = []
    tok = _TOK.findall(d)
    i, cmd = 0, ""
    while i < len(tok):
        if tok[i] in "MLCZ":
            cmd = tok[i]
            i += 1
            if cmd == "Z":
                out.append(("Z",))
            continue
        need = 6 if cmd == "C" else 2
        nums = [float(t) for t in tok[i:i + need]]
        i += need
        if len(nums) == need and cmd:
            out.append((cmd, *nums))
            if cmd == "M":
                cmd = "L"
    return out


def _bounds(segs: list[tuple]) -> tuple[float, float, float, float]:
    """Exact bounds of the path (the curve itself, not its control points): the same sums as the browser's pathBBox."""
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    px = py = 0.0
    for sg in segs:
        if sg[0] == "Z":
            continue
        if sg[0] != "C":
            px, py = sg[1], sg[2]
            x0, x1, y0, y1 = min(x0, px), max(x1, px), min(y0, py), max(y1, py)
            continue
        ex, ey = sg[5], sg[6]
        x0, x1, y0, y1 = min(x0, ex), max(x1, ex), min(y0, ey), max(y1, ey)
        for k in (0, 1):
            p0, p1, p2, p3 = (py if k else px), sg[1 + k], sg[3 + k], sg[5 + k]
            a, b, c = -p0 + 3 * p1 - 3 * p2 + p3, 2 * (p0 - 2 * p1 + p2), p1 - p0
            ts: list[float] = []
            if abs(a) < 1e-12:
                if abs(b) > 1e-12:
                    ts.append(-c / b)
            else:
                disc = b * b - 4 * a * c
                if disc >= 0:
                    sq = math.sqrt(disc)
                    ts += [(-b + sq) / (2 * a), (-b - sq) / (2 * a)]
            for t in ts:
                if 0 < t < 1:
                    u = 1 - t
                    v = u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3
                    if k:
                        y0, y1 = min(y0, v), max(y1, v)
                    else:
                        x0, x1 = min(x0, v), max(x1, v)
        px, py = ex, ey
    if x0 is math.inf or x0 == math.inf:
        return 0.0, 0.0, 0.0, 0.0
    return x0, y0, x1, y1


def build(name: str, size: float) -> dict | None:
    """{path, w, h, x, y}: the icon's ink box for a size x size square (path starts at 0,0 and ends at w,h)."""
    d = ICONS.get(name)
    if not d:
        return None
    segs = _segments(d)
    x0, y0, x1, y1 = _bounds(segs)
    s = float(size) / GRID
    parts: list[str] = []
    for sg in segs:
        if sg[0] == "Z":
            parts.append("Z")
            continue
        nums = sg[1:]
        vals = [_n(((v - (x0 if i % 2 == 0 else y0)) * s)) for i, v in enumerate(nums)]
        parts.append(sg[0] + " ".join(vals))
    w, h = max(0.01, (x1 - x0) * s), max(0.01, (y1 - y0) * s)
    return {"path": " ".join(parts), "w": round(w, 2), "h": round(h, 2), "x": round(x0 * s, 2), "y": round(y0 * s, 2)}
