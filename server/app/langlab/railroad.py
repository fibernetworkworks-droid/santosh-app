"""Railroad diagrams of grammar rules as SVG (drawn by our own code from Grammar.shape; all text escaped)."""
from __future__ import annotations

from html import escape
from typing import Any

H = 24          # box height
GAP = 14
CH = 7.3        # width of one character (monospace 12px)
STYLE = ("<style>.rr-l{fill:none;stroke:#8a8698;stroke-width:1.6}.rr-b{stroke:#3d3a4b;stroke-width:1.2}"
         ".rr-lit{fill:#fff3e2}.rr-tok{fill:#e8f3ff}.rr-ref{fill:#f1edff}text{font:12px ui-monospace,Menlo,monospace;"
         "fill:#211d2e;dominant-baseline:central}</style>")


class _D:
    def __init__(self, w: float, up: float, down: float, draw):
        self.w, self.up, self.down, self.draw = w, up, down, draw


def _box(kind: str, s: str) -> _D:
    w = max(28.0, len(s) * CH + 20)
    label = f'"{s}"' if kind == "lit" else s

    def draw(x: float, y: float) -> str:
        rx = 11 if kind == "lit" else 3
        return (f'<rect class="rr-b rr-{kind}" x="{x:.1f}" y="{y - H / 2:.1f}" width="{w:.1f}" height="{H}" rx="{rx}"/>'
                f'<text x="{x + w / 2:.1f}" y="{y:.1f}" text-anchor="middle">{escape(label)}</text>')
    if kind == "lit":
        w = max(28.0, len(label) * CH + 18)
    return _D(w, H / 2, H / 2, draw)


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<path class="rr-l" d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"/>'


def _curve(x1: float, y1: float, x2: float, y2: float) -> str:
    mx = (x1 + x2) / 2
    return f'<path class="rr-l" d="M{x1:.1f} {y1:.1f}C{mx:.1f} {y1:.1f} {mx:.1f} {y2:.1f} {x2:.1f} {y2:.1f}"/>'


def _seq(parts: list[_D]) -> _D:
    if not parts:
        return _D(10, 0, 0, lambda x, y: _line(x, y, x + 10, y))
    w = sum(p.w for p in parts) + GAP * (len(parts) - 1)
    up, down = max(p.up for p in parts), max(p.down for p in parts)

    def draw(x: float, y: float) -> str:
        out, cx = [], x
        for i, p in enumerate(parts):
            out.append(p.draw(cx, y))
            cx += p.w
            if i < len(parts) - 1:
                out.append(_line(cx, y, cx + GAP, y))
                cx += GAP
        return "".join(out)
    return _D(w, up, down, draw)


def _alt(parts: list[_D]) -> _D:
    inner = max(p.w for p in parts)
    w = inner + 2 * 24
    offs, y = [], 0.0
    for i, p in enumerate(parts):
        if i:
            y += parts[i - 1].down + 10 + p.up
        offs.append(y)
    up, down = parts[0].up, offs[-1] + parts[-1].down

    def draw(x: float, y0: float) -> str:
        out = []
        for p, o in zip(parts, offs):
            py = y0 + o
            out.append(_curve(x, y0, x + 24, py) if o else _line(x, y0, x + 24, py))
            out.append(p.draw(x + 24, py))
            out.append(_line(x + 24 + p.w, py, x + 24 + inner, py))
            out.append(_curve(x + 24 + inner, py, x + w, y0) if o else _line(x + 24 + inner, py, x + w, y0))
        return "".join(out)
    return _D(w, up, down, draw)


def _opt(p: _D, loop: bool, skip: bool) -> _D:
    w = p.w + 2 * 24
    up = p.up + (16 if skip else 0)
    down = p.down + (16 if loop else 0)

    def draw(x: float, y: float) -> str:
        out = [_line(x, y, x + 24, y), p.draw(x + 24, y), _line(x + 24 + p.w, y, x + w, y)]
        if skip:
            top = y - p.up - 10
            out.append(f'<path class="rr-l" d="M{x:.1f} {y:.1f}Q{x + 10:.1f} {y:.1f} {x + 12:.1f} {top + 6:.1f}'
                       f'L{x + 12:.1f} {top + 6:.1f}Q{x + 12:.1f} {top:.1f} {x + 20:.1f} {top:.1f}L{x + w - 20:.1f} {top:.1f}'
                       f'Q{x + w - 12:.1f} {top:.1f} {x + w - 12:.1f} {top + 6:.1f}Q{x + w - 10:.1f} {y:.1f} {x + w:.1f} {y:.1f}"/>')
        if loop:
            bot = y + p.down + 10
            out.append(f'<path class="rr-l" d="M{x + 24 + p.w:.1f} {y:.1f}Q{x + w - 10:.1f} {y:.1f} {x + w - 10:.1f} {bot - 6:.1f}'
                       f'Q{x + w - 10:.1f} {bot:.1f} {x + w - 18:.1f} {bot:.1f}L{x + 18:.1f} {bot:.1f}'
                       f'Q{x + 10:.1f} {bot:.1f} {x + 10:.1f} {bot - 6:.1f}Q{x + 10:.1f} {y:.1f} {x + 24:.1f} {y:.1f}"/>')
        return "".join(out)
    return _D(w, up, down, draw)


def _build(s: dict[str, Any]) -> _D:
    k = s.get("k")
    if k in ("lit", "tok", "ref"):
        return _box(k, str(s.get("s") or ""))
    kids = [_build(c) for c in s.get("c") or []]
    if k == "seq":
        return _seq(kids)
    if k == "alt":
        return _alt(kids)
    if k == "opt":
        return _opt(kids[0], loop=False, skip=True)
    if k == "many":
        return _opt(kids[0], loop=True, skip=True)
    if k == "many1":
        return _opt(kids[0], loop=True, skip=False)
    return _box("lit", "?")


def svg(shape: dict[str, Any], styled: bool = True) -> str:
    d = _build(shape)
    pad = 14
    w = d.w + 2 * 22 + 2 * pad
    h = d.up + d.down + 2 * pad
    y = pad + d.up
    x0 = pad
    body = (f'<circle cx="{x0 + 4:.1f}" cy="{y:.1f}" r="4" fill="#3d3a4b"/>' + _line(x0 + 8, y, x0 + 22, y) + d.draw(x0 + 22, y) +
            _line(x0 + 22 + d.w, y, x0 + 36 + d.w, y) +
            f'<circle cx="{x0 + 40 + d.w:.1f}" cy="{y:.1f}" r="4" fill="none" stroke="#3d3a4b" stroke-width="1.6"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="rr" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'role="img">' + (STYLE if styled else "") + body + "</svg>")
