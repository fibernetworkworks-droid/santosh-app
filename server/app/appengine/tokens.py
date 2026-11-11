"""v0.814 the design system of an App Engine app = ONE file, src/styles/tokens.css (the "design system first" law).

Tailwind v4 reads it as `@theme`: the default palette is switched OFF (`--color-*: initial`), so `bg-blue-500` makes
nothing at all, and only the semantic names exist - bg / surface / ink / muted / line / primary / primary-ink / accent /
ok / warn / bad, corners `rounded-card` / `rounded-control`, `shadow-card`, `font-head` / `font-body`. The file is
written by code from a small set of values (a named palette, her colours, or a Web Studio look); the write tools never
edit it by hand, so the drift check has one source of truth."""
from __future__ import annotations

import re
from typing import Any

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
KEYS = ("bg", "surface", "ink", "muted", "line", "primary", "primary_ink", "accent", "ok", "warn", "bad")
FONTS = {
    "sans": 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Helvetica Neue", Arial, sans-serif',
    "serif": 'ui-serif, Georgia, Cambria, "Times New Roman", "Noto Serif", serif',
    "rounded": 'ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif',
    "mono": 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
}
PALETTES: dict[str, dict[str, Any]] = {
    "calm": {"bg": "#f7f7f8", "surface": "#ffffff", "ink": "#16161d", "primary": "#4f46e5", "accent": "#0ea5a4",
             "radius": 14, "head": "sans", "body": "sans"},
    "warm": {"bg": "#fbf7f2", "surface": "#ffffff", "ink": "#2a1f17", "primary": "#c2410c", "accent": "#a16207",
             "radius": 12, "head": "serif", "body": "sans"},
    "fresh": {"bg": "#f3faf6", "surface": "#ffffff", "ink": "#11231a", "primary": "#15803d", "accent": "#0369a1",
              "radius": 16, "head": "rounded", "body": "sans"},
    "bold": {"bg": "#ffffff", "surface": "#f5f5f5", "ink": "#0a0a0a", "primary": "#e11d48", "accent": "#7c3aed",
             "radius": 8, "head": "sans", "body": "sans"},
    "night": {"bg": "#0d0f14", "surface": "#161a22", "ink": "#eef0f5", "primary": "#8b7cff", "accent": "#2dd4bf",
              "radius": 14, "head": "sans", "body": "sans"},
}
DEFAULT = "calm"


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(c: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(x))):02x}" for x in c)


def _mix(a: str, b: str, t: float) -> str:
    x, y = _rgb(a), _rgb(b)
    return _hex(tuple(x[i] + (y[i] - x[i]) * t for i in range(3)))


def _lum(h: str) -> float:
    def ch(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def resolve(values: dict[str, Any] | None = None, palette: str = "") -> dict[str, Any]:
    """Her values over a named palette; every colour checked; the rest derived (muted, line, primary-ink, states)."""
    base = dict(PALETTES.get(palette or DEFAULT) or PALETTES[DEFAULT])
    bad = []
    for k, v in (values or {}).items():
        k = str(k).replace("-", "_")
        if k in KEYS or k in ("radius", "head", "body"):
            if k in KEYS:
                v = str(v).strip()
                if not HEX.match(v):
                    bad.append(f"{k}: '{v}' is not a #rrggbb colour")
                    continue
            base[k] = v
    if bad:
        raise ValueError("; ".join(bad))
    t = dict(base)
    t["muted"] = t.get("muted") or _mix(t["ink"], t["bg"], 0.45)
    t["line"] = t.get("line") or _mix(t["ink"], t["bg"], 0.86)
    if not t.get("primary_ink"):
        t["primary_ink"] = "#ffffff" if contrast("#ffffff", t["primary"]) >= contrast("#111111", t["primary"]) else "#111111"
    t.setdefault("ok", "#15803d")
    t.setdefault("warn", "#d97706")
    t.setdefault("bad", "#dc2626")
    try:
        t["radius"] = max(0, min(32, int(t.get("radius", 14))))
    except (TypeError, ValueError):
        t["radius"] = 14
    for f in ("head", "body"):
        if t.get(f) not in FONTS:
            t[f] = "sans"
    return t


def from_site_look(look: dict[str, Any]) -> dict[str, Any]:
    """A Web Studio look's tokens -> App Engine values (the same brand on both engines)."""
    tk = (look or {}).get("tokens") or {}
    out = {k: tk[k] for k in ("bg", "surface", "ink", "primary", "accent") if HEX.match(str(tk.get(k) or ""))}
    try:
        out["radius"] = int(str(tk.get("radius", "14")).rstrip("px"))
    except ValueError:
        pass
    return out


def css(t: dict[str, Any]) -> str:
    r = int(t["radius"])
    shadow = "0 1px 2px rgb(0 0 0 / 0.06), 0 4px 16px rgb(0 0 0 / 0.06)"
    lines = ["/* Hoola App Engine - the design system. Written by Hoola from the app's look; do not edit by hand.",
             "   Use the names: bg surface ink muted line primary primary-ink accent ok warn bad,",
             "   rounded-card rounded-control shadow-card font-head font-body. */",
             "@theme {",
             "  --color-*: initial;",
             "  --color-transparent: transparent;",
             "  --color-current: currentColor;"]
    for k in KEYS:
        lines.append(f"  --color-{k.replace('_', '-')}: {t[k]};")
    lines += [f"  --radius-card: {r + 4}px;", f"  --radius-control: {max(4, r - 4)}px;",
              f"  --shadow-card: {shadow};",
              f"  --font-head: {FONTS[t['head']]};", f"  --font-body: {FONTS[t['body']]};", "}", ""]
    return "\n".join(lines)


def theme_json(t: dict[str, Any]) -> dict[str, Any]:
    """The resolved theme (for the Studio; the L9 style panel reads this)."""
    return {"colors": {k.replace("_", "-"): t[k] for k in KEYS}, "radius": t["radius"], "head": t["head"],
            "body": t["body"], "contrast_ink_on_bg": contrast(t["ink"], t["bg"]),
            "contrast_primary_ink": contrast(t["primary_ink"], t["primary"])}
