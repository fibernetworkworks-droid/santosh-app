"""v0.325 ANY DESIGN - the site's own DESIGN KIT (web design Phase 6 step 2).

Before this every section styled its own buttons, cards and titles inside its #id, so on a big site page 40's cards
drifted from page 3's. Now, once a look is chosen, Opus writes ONE kit for the site - its buttons, cards, section
heads, badges, quotes, stats, media frames - as `.k-*` classes built only from the site's CSS variables (so her colour
changes still flow through), and every section is told to use them. The kit sits in site.css after the base styles.

Only `.k-` rules survive the cleaner (no element / id / global selectors, no @import, no external url(), no fonts), so a
kit can never restyle the header, the footer or another section.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger("santosh.site.kit")

PARTS = ("k-btn", "k-btn-ghost", "k-card", "k-eyebrow", "k-title", "k-sub", "k-head", "k-badge", "k-media", "k-quote",
         "k-stat", "k-list", "k-divider", "k-chip")
MAX_CSS = 24000

KIT_SYSTEM = """You are the design-systems lead of a top studio. The look of a business website is chosen; write its DESIGN
KIT: the shared components every section of every page will use, so a 100-page site reads as ONE site.
Return ONE JSON object: {"css": "...", "notes": {"k-btn": "one line: when to use it", ...}}
CSS rules:
- Only these class selectors (and their :hover / :focus-visible / ::before / ::after, and descendants that are also
  .k- classes): .k-btn (primary action), .k-btn-ghost (secondary), .k-card, .k-eyebrow, .k-title (section title),
  .k-sub (the line under a title), .k-head (a section header block: eyebrow + title + sub), .k-badge, .k-media (a
  photo frame), .k-quote, .k-stat (a big number + label), .k-list (a ticked list), .k-divider, .k-chip.
  @media (min-width: ...) wrappers are fine. Nothing else: no element, id, :root, html or body selectors.
- Colours, fonts, radius ONLY through the site variables: --c-bg --c-surface --c-ink --c-muted --c-line --c-primary
  --c-on-primary --c-accent --c-on-accent --c-primary-text --c-accent-text --font-head --font-body --radius, plus
  color-mix(in srgb, var(--c-primary) N%, transparent) tints. No url(), no @import, no font-face, no hard-coded colours.
- Express the chosen look's art direction (its concept, signature, type and shape language) in these components:
  this is where the look becomes a system. Tap targets >= 44px; visible :focus-visible; contrast safe.
- Animate only transform / opacity, and wrap motion in @media (prefers-reduced-motion: no-preference)."""


def _st():
    from ..config import get_settings
    return get_settings()


def on() -> bool:
    return str(getattr(_st(), "site_kit", "true")).lower() not in ("0", "false", "off", "no")


def _blocks(css: str):
    """Top-level (selector, body) pairs with nested braces kept in the body."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            return
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        yield sel, css[j + 1:k - 1]
        i = k


def _sel_ok(sel: str) -> bool:
    parts = [p.strip() for p in sel.split(",") if p.strip()]
    if not parts:
        return False
    for p in parts:
        if not p.startswith(".k-"):
            return False
        # every class in the selector is a kit class; no ids, no attribute / universal tricks
        if "#" in p or "*" in p or "[" in p:
            return False
        if any(not c.startswith("k-") for c in re.findall(r"\.([\w-]+)", p)):
            return False
    return True


def clean(css: str) -> str:
    """Keep only kit rules (see the module note); media / supports wrappers keep their kit rules inside."""
    css = re.sub(r"/\*.*?\*/", "", str(css or ""), flags=re.S)
    css = re.sub(r"@import[^;]*;?", "", css, flags=re.I)
    css = re.sub(r"url\([^)]*\)", "none", css, flags=re.I)
    css = re.sub(r"expression\s*\(|behavior\s*:|-moz-binding|</style", "", css, flags=re.I)
    out: list[str] = []
    for sel, body in _blocks(css):
        if sel.startswith("@media") or sel.startswith("@supports"):
            inner = clean(body)
            if inner:
                out.append(f"{sel}{{{inner}}}")
        elif sel.startswith("@keyframes k-"):
            out.append(f"{sel}{{{body}}}")
        elif sel.startswith("@"):
            continue
        elif _sel_ok(sel) and "{" not in body:
            out.append(f"{sel}{{{body.strip()}}}")
    return "\n".join(out)[:MAX_CSS]


def make(tokens: dict[str, Any], dna: dict[str, Any] | None, style: str, brief_text: str) -> dict[str, Any] | None:
    """One Opus call -> {css, notes, parts}. None when off or the model gave nothing usable."""
    if not on():
        return None
    from . import ai as AI
    prompt = "\n".join([
        brief_text[:2500],
        f"\nCHOSEN LOOK: style {style}; tokens {json.dumps({k: tokens.get(k) for k in ('bg', 'surface', 'ink', 'primary', 'accent', 'radius', 'head', 'body')})}",
        "ART DIRECTION (data): " + json.dumps(dna or {}, ensure_ascii=False)[:2500],
    ])
    raw = AI.ask_json(KIT_SYSTEM, prompt, 7000, "site_art")
    css = clean((raw or {}).get("css") or "")
    if not css:
        return None
    notes = raw.get("notes") if isinstance(raw.get("notes"), dict) else {}
    parts = [p for p in PARTS if f".{p}" in css]
    return {"css": css, "parts": parts,
            "notes": {p: re.sub(r"\s+", " ", str(notes.get(p) or ""))[:120] for p in parts}}


def prompt_line(kit: dict[str, Any] | None) -> str:
    """What every section writer is told about the kit."""
    if not kit or not kit.get("parts"):
        return ""
    return ("SITE DESIGN KIT (shared by every page - USE these classes for buttons, cards, section heads, badges, quotes, "
            "stats, photo frames, lists; style only layout and what is unique to this section yourself): "
            + "; ".join(f".{p}" + (f" = {kit['notes'].get(p)}" if kit.get("notes", {}).get(p) else "") for p in kit["parts"]))
