"""v0.999.316 DESIGN.md (owner: getdesign.md + VoltAgent/awesome-design-md -> "SHOW DESIGN FIRST" -> "GO BUILD").

DESIGN.md is Google Stitch's plain-text design system (github.com/google-labs-code/design.md, Apache-2.0, version "alpha"):
YAML tokens at the top (colors, typography, rounded, spacing, motion, components) and written rules in up to ten
sections in a fixed order. This module is Hoola's one reader of it:

- `parse(text)`   any DESIGN.md -> one dict. Tolerant: YAML whose description has a bare colon is repaired (and said),
                  `yaml` code blocks inside sections are read too, and an older file with no tokens at all has its
                  colours and fonts read from its own words (`- **Name** (`#hex`): role` lines).
- `lint(doc)`     Hoola's own copy of the spec's lint rules (section order, duplicates, missing primary / typography,
                  token references that do not resolve, unreadable colour pairs, unknown keys), in plain words.
- `to_ref(doc)`   the design as a `design_ref` (the v0.567 KOI BHI DESIGN shape) so look 1 of a website follows it:
                  colours, a font pair Hoola ships, corners, light or dark, AND its written rules for the writer + critic.
- the CATALOG     83 looks from awesome-design-md (MIT, `designmd_lib/`), each with a Hoola name, drawn previews,
                  the prompt, its tokens and rules; a full sample page in its look (light AND dark: the missing one is
                  made from the same colours and checked); never the source's name, logo, words or pictures on her site.
"""
from __future__ import annotations

import functools
import gzip
import json
import re
from pathlib import Path
from typing import Any

from ..appengine import tokens as TK

LIB = Path(__file__).with_name("designmd_lib")
MAX_TEXT = 400_000

SECTION_ORDER = ["Overview", "Colors", "Typography", "Layout", "Elevation & Depth", "Shapes",
                 "Motion & Micro-interaction", "Voice & Content Strategy", "Components", "Do's and Don'ts"]
_ALIAS = {
    "overview": "Overview", "brand & style": "Overview", "brand and style": "Overview", "visual theme & atmosphere": "Overview",
    "visual theme and atmosphere": "Overview",
    "colors": "Colors", "colours": "Colors", "color": "Colors", "color palette & roles": "Colors", "color palette": "Colors",
    "typography": "Typography", "type": "Typography", "typography rules": "Typography",
    "layout": "Layout", "layout & spacing": "Layout", "layout and spacing": "Layout", "layout principles": "Layout",
    "elevation & depth": "Elevation & Depth", "elevation": "Elevation & Depth", "depth & elevation": "Elevation & Depth",
    "shapes": "Shapes", "shape and space": "Shapes",
    "motion & micro-interaction": "Motion & Micro-interaction", "motion & micro-interactions": "Motion & Micro-interaction",
    "motion": "Motion & Micro-interaction",
    "voice & content strategy": "Voice & Content Strategy", "voice and content": "Voice & Content Strategy",
    "components": "Components", "component stylings": "Components",
    "do's and don'ts": "Do's and Don'ts", "dos and don'ts": "Do's and Don'ts", "do's and dont's": "Do's and Don'ts",
}
KNOWN_KEYS = {"version", "name", "description", "omitted", "colors", "typography", "rounded", "spacing", "motion",
              "components", "hoola", "generator", "shadow", "imagery", "direction"}
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
_REF = re.compile(r"\{([a-z][\w-]*(?:\.[\w-]+)+)\}")


class DesignMdError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- colours
def hexify(v: Any) -> str:
    """A CSS colour -> #rrggbb, or '' when it is not one Hoola can check (alpha is dropped)."""
    s = str(v or "").strip().strip("'\"").lower()
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        if len(h) in (6, 8):
            return "#" + h[:6]
        return ""
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)(?:[\s,/]+[\d.%]+)?\s*\)", s)
    if m:
        r, g, b = (max(0, min(255, int(x))) for x in m.groups())
        return f"#{r:02x}{g:02x}{b:02x}"
    named = {"white": "#ffffff", "black": "#000000", "red": "#ff0000", "transparent": ""}
    return named.get(s, "")


def lum(h: str) -> float:
    return TK._lum(h) if h else 0.0


def contrast(a: str, b: str) -> float:
    return TK.contrast(a, b) if a and b else 0.0


def readable(fg: str, bg: str, need: float = 4.5) -> str:
    """fg moved toward black or white until it reads at `need`:1 on bg; when no shade can (a mid-tone background and a
    7:1 ask), the most readable one of the two directions."""
    if not fg or not bg:
        return fg
    if contrast(fg, bg) >= need:
        return fg
    best = fg
    for to in (("#000000", "#ffffff") if lum(bg) > 0.18 else ("#ffffff", "#000000")):
        for i in range(1, 21):
            c = TK._mix(fg, to, i / 20)
            if contrast(c, bg) >= need:
                return c
            if contrast(c, bg) > contrast(best, bg):
                best = c
    return best


# ---------------------------------------------------------------- reading
def _lenient_yaml(block: str) -> tuple[dict[str, Any], bool]:
    """YAML front matter -> dict. A bare colon inside a long `description:` (the commonest mistake in real files) is
    repaired: the description is cut out, the rest read, and the description kept as plain text."""
    import yaml
    try:
        v = yaml.safe_load(block) or {}
        return (v if isinstance(v, dict) else {}), False
    except yaml.YAMLError:
        pass
    lines, keep, desc, in_desc = block.split("\n"), [], [], False
    for ln in lines:
        if re.match(r"^description\s*:", ln):
            in_desc = True
            desc.append(ln.split(":", 1)[1])
            continue
        if in_desc and re.match(r"^[A-Za-z][\w-]*\s*:", ln):
            in_desc = False
        (desc if in_desc else keep).append(ln)
    try:
        v = yaml.safe_load("\n".join(keep)) or {}
        v = v if isinstance(v, dict) else {}
    except yaml.YAMLError:
        v = {}
        for ln in keep:                                   # last resort: flat `key: value` lines only
            m = re.match(r"^([a-z][\w-]*)\s*:\s*(.+)$", ln)
            if m:
                v[m.group(1)] = m.group(2).strip().strip("'\"")
    if desc:
        v["description"] = re.sub(r"\s+", " ", " ".join(desc)).strip().strip("'\"")
    return v, True


def _flat(d: Any, pre: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        key = f"{pre}{k}"
        if isinstance(v, dict) and not any(x in v for x in ("fontFamily", "fontSize", "duration")):
            out.update(_flat(v, key + "."))
        else:
            out[key] = v
    return out


def _canon(heading: str) -> str:
    h = re.sub(r"^\s*\d+[.)]\s*", "", heading).strip().lower().replace("’", "'")
    return _ALIAS.get(h, "")


def parse(text: str) -> dict[str, Any]:
    t = str(text or "").replace("\r\n", "\n").lstrip("﻿")
    if len(t) > MAX_TEXT:
        raise DesignMdError("That DESIGN.md is too large (over 400 KB).")
    if not t.strip():
        raise DesignMdError("That DESIGN.md is empty.")
    notes: list[str] = []
    front: dict[str, Any] = {}
    body = t
    m = re.match(r"\s*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", t, re.S)
    if m:
        front, repaired = _lenient_yaml(m.group(1))
        if repaired:
            notes.append("yaml-repaired")
        body = t[m.end():]
    dup_keys: list[str] = []
    for blk in re.findall(r"```ya?ml[ \t]*\n(.*?)\n```", body, re.S):   # interleaved token blocks
        try:
            import yaml
            v = yaml.safe_load(blk) or {}
        except Exception:
            continue
        if isinstance(v, dict):
            for k, val in v.items():
                if k in front:
                    dup_keys.append(str(k))
                else:
                    front[k] = val
    secs: list[dict[str, Any]] = []
    parts = re.split(r"^##[ \t]+(.+?)[ \t]*$", body, flags=re.M)
    title = ""
    tm = re.search(r"^#[ \t]+(.+?)\s*$", parts[0] if parts else "", re.M)
    if tm:
        title = tm.group(1).strip()
    for i in range(1, len(parts), 2):
        head = parts[i].strip()
        txt = parts[i + 1].strip() if i + 1 < len(parts) else ""
        secs.append({"heading": head, "canon": _canon(head), "text": txt})
    colors = {k: v for k, v in _flat(front.get("colors")).items()}
    typo = front.get("typography") if isinstance(front.get("typography"), dict) else {}
    typo = {k: v for k, v in _flat(typo).items() if isinstance(v, dict)} if typo else {}
    doc = {
        "name": str(front.get("name") or title or "").strip()[:120],
        "description": re.sub(r"\s+", " ", str(front.get("description") or "")).strip()[:1200],
        "version": str(front.get("version") or ""),
        "has_tokens": bool(m) or bool(front),
        "front": front, "colors": colors, "typography": typo,
        "rounded": _flat(front.get("rounded")), "spacing": _flat(front.get("spacing")),
        "motion": front.get("motion") if isinstance(front.get("motion"), dict) else {},
        "components": front.get("components") if isinstance(front.get("components"), dict) else {},
        "sections": secs, "notes": notes, "dup_keys": dup_keys,
    }
    doc["roles"] = roles(doc)
    doc["fonts"] = fonts(doc)
    doc["radius"] = radius(doc)
    return doc


def section(doc: dict[str, Any], canon: str) -> str:
    for s in doc.get("sections") or []:
        if s["canon"] == canon:
            return s["text"]
    return ""


def _pick(colors: dict[str, Any], names: tuple[str, ...]) -> str:
    low = {k.lower(): v for k, v in colors.items()}
    for n in names:
        for k, v in low.items():
            if k == n or k.endswith("." + n):
                h = hexify(v)
                if h:
                    return h
    return ""


_PROSE = {
    "bg": [(r"page canvas|page background|body background|primary page|default (body |dark |light )?(background|surface)|the canvas|entire (home)?page", 5),
           (r"\bcanvas\b|\bbackground\b", 2)],
    "surface": [(r"primary (card|surface)|card surface|\bcards?\b|\bpanels?\b|surface", 3), (r"alternate|lifted|raised", 2)],
    "ink": [(r"primary (headline|text)|headline and body|heading|body text|primary text", 4), (r"\btext\b", 1)],
    "primary": [(r"primary cta|filled[- ]cta|cta|primary (action )?buttons?|main button|primary action|sole accent|only chromatic|signature accent", 5), (r"\bbutton|link|interactive|brand accent", 2)],
}
_PROSE_NO = r"\blogo\b|never as a ui|semantic|success|error|warning|disabled|placeholder|hover"
_PROSE_MINUS = r"border|divider|outline|wash|gradient|overlay|badge|footer|strip|secondary|variant"


def _from_prose(doc: dict[str, Any]) -> dict[str, str]:
    """An older DESIGN.md with no tokens: `- **Name** (`#hex`): what it is for` lines in its colour section, each
    scored for each role by what the line says it is for (a logo colour or a footer is never the page)."""
    txt = section(doc, "Colors") or ""
    best: dict[str, tuple[int, str]] = {}
    sub = ""
    for ln in txt.split("\n"):
        if ln.startswith("###"):
            sub = ln.lower()
            continue
        hm = _HEX.search(ln)
        if not hm or not ln.lstrip().startswith(("-", "*")):
            continue
        h = hexify(hm.group(0))
        role = (ln.split("):", 1)[-1] if "):" in ln else ln).lower()
        name = ln.split("(", 1)[0].lower()
        if not h or re.search(_PROSE_NO, role.split(".")[0]):
            continue
        minus = 3 if re.search(_PROSE_MINUS, role.split(".")[0]) else 0
        for key, pats in _PROSE.items():
            sc = sum(w for rx, w in pats if re.search(rx, role))
            if key == "bg" and "canvas" in name:
                sc += 3
            if not sc:
                continue
            sc -= minus
            if key == "primary" and not (0.0 < lum(h) < 0.92):
                sc -= 3
            if key == "primary" and re.search(r"page background|card surface|canvas", role.split(".")[0]):
                sc -= 4
            if key == "bg" and re.search(r"cta|button", role):
                sc -= 4
            if key in ("bg", "surface") and "surface" in sub:
                sc += 1
            if sc > 0 and sc > best.get(key, (0, ""))[0]:
                best[key] = (sc, h)
    out = {k: v[1] for k, v in best.items()}
    if "bg" not in out and out.get("surface"):
        out["bg"] = out.pop("surface")
    return out


def roles(doc: dict[str, Any]) -> dict[str, str]:
    c = doc.get("colors") or {}
    r = {
        "bg": _pick(c, ("canvas", "background", "bg", "page", "surface", "neutral")),
        "surface": _pick(c, ("surface-1", "surface-card", "surface-soft", "surface-2", "surface-container", "card",
                             "surface-raised", "panel", "surface")),
        "ink": _pick(c, ("ink", "on-surface", "on-background", "text", "foreground", "body", "heading")),
        "muted": _pick(c, ("ink-muted", "muted", "ink-subtle", "text-muted", "body-muted", "secondary-text", "on-surface-variant")),
        "line": _pick(c, ("hairline", "border", "line", "divider", "outline")),
        "primary": _pick(c, ("primary", "brand", "accent", "cta")),
        "on_primary": _pick(c, ("on-primary", "primary-ink", "on-brand")),
        "accent": _pick(c, ("secondary", "tertiary", "accent", "highlight")),
    }
    if not (r["bg"] and r["primary"] and r["ink"]):
        p = _from_prose(doc)
        for k, v in p.items():
            r[k] = r.get(k) or v
    if r["surface"] == r["bg"]:
        r["surface"] = ""
    if r["accent"] == r["primary"]:
        r["accent"] = ""
    return r


def _family(v: Any) -> str:
    s = str(v or "").strip()
    first = s.split(",")[0].strip().strip("'\"`")
    return first[:60]


def fonts(doc: dict[str, Any]) -> dict[str, Any]:
    ty = doc.get("typography") or {}

    def find(names: tuple[str, ...]) -> tuple[str, dict[str, Any]]:
        for n in names:
            for k, v in ty.items():
                if (k == n or k.startswith(n)) and v.get("fontFamily"):
                    return k, v
        return "", {}

    hk, h = find(("display-xl", "display-lg", "display", "headline-display", "headline", "hero", "h1", "heading"))
    bk, b = find(("body-md", "body", "body-lg", "text", "paragraph"))
    out = {"display": _family(h.get("fontFamily")), "text": _family(b.get("fontFamily")),
           "display_size": str(h.get("fontSize") or ""), "display_weight": str(h.get("fontWeight") or ""),
           "display_tracking": str(h.get("letterSpacing") or ""), "body_size": str(b.get("fontSize") or ""),
           "family_raw": str(h.get("fontFamily") or "")}
    if not out["display"]:                                   # an older file: "- **Display**: `Font`, ..."
        txt = section(doc, "Typography")
        m = re.search(r"\*\*(?:display|headline|heading)[^*]*\*\*\s*:?\s*`([^`]+)`", txt, re.I)
        n = re.search(r"\*\*(?:text|body|ui)[^*]*\*\*\s*:?\s*`([^`]+)`", txt, re.I)
        if m:
            out["display"] = _family(m.group(1))
            out["family_raw"] = m.group(1)
        if n:
            out["text"] = _family(n.group(1))
        sz = re.search(r"\|\s*(?:hero|display)[^|]*\|\s*(\d+)px", txt, re.I)
        if sz:
            out["display_size"] = sz.group(1) + "px"
    return out


def radius(doc: dict[str, Any]) -> int | None:
    r = doc.get("rounded") or {}
    for k in ("card", "md", "default", "lg", "sm"):
        v = r.get(k)
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(px|rem)?", str(v or ""))
        if v is not None and m:
            return int(round(float(m.group(1)) * (16 if m.group(2) == "rem" else 1)))
    return None


# ---------------------------------------------------------------- the checker (Google's lint rules, Hoola's words)
def lint(doc: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []

    def add(rule: str, sev: str, msg: str) -> None:
        out.append({"rule": rule, "severity": sev, "message": msg})

    r = doc.get("roles") or {}
    if "yaml-repaired" in doc.get("notes", []):
        add("yaml-repaired", "info", "The tokens at the top had a YAML mistake (a colon inside the description). Hoola read them anyway.")
    if not doc.get("has_tokens"):
        add("no-tokens", "warning", "There are no tokens at the top (between --- lines). Hoola read the colours and fonts from the words instead.")
    if not r.get("primary"):
        add("missing-primary", "warning", "No main brand colour (colors.primary). Hoola will choose one that fits.")
    if not (doc.get("typography") or (doc.get("fonts") or {}).get("display")):
        add("missing-typography", "warning", "No typography tokens. Hoola will choose fonts that fit the look.")
    if not r.get("bg"):
        add("missing-background", "warning", "No page background colour (canvas / background). Hoola assumes a light page.")
    seen: dict[str, int] = {}
    order = []
    for s in doc.get("sections") or []:
        if s["canon"]:
            seen[s["canon"]] = seen.get(s["canon"], 0) + 1
            order.append(SECTION_ORDER.index(s["canon"]))
    for k, n in seen.items():
        if n > 1:
            add("duplicate-section", "error", f"The section '{k}' appears {n} times. Only the first is used.")
    if order != sorted(order):
        add("section-order", "warning", "The sections are not in the usual order (Overview, Colors, Typography, Layout, "
            "Elevation & Depth, Shapes, Motion, Voice, Components, Do's and Don'ts).")
    for k in doc.get("dup_keys") or []:
        add("duplicate-key", "error", f"'{k}' is defined twice (at the top and in a yaml block). The first one is used.")
    tree = doc.get("front") or {}

    def resolve(path: str) -> bool:
        cur: Any = tree
        parts = path.split(".")
        for i, p in enumerate(parts):
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            elif isinstance(cur, dict) and ".".join(parts[i:]) in cur:
                return True
            else:
                return False
        return True

    broken = []
    blob = json.dumps(doc.get("components") or {}) + " " + " ".join(s["text"] for s in doc.get("sections") or [])
    for ref in sorted(set(_REF.findall(blob))):
        if ref.split(".")[0] in ("colors", "typography", "rounded", "spacing", "motion", "components") and not resolve(ref):
            broken.append(ref)
    if broken:
        add("broken-ref", "warning", f"{len(broken)} token reference(s) point at nothing: " + ", ".join("{" + b + "}" for b in broken[:5]))
    bad = [k for k, v in (doc.get("colors") or {}).items() if v not in (None, "") and not hexify(v) and not re.match(r"\s*(hsl|oklch|lab|lch|color-mix)", str(v))]
    if bad:
        add("bad-color", "warning", f"{len(bad)} colour value(s) Hoola cannot read: " + ", ".join(bad[:5]))
    if r.get("ink") and r.get("bg") and contrast(r["ink"], r["bg"]) < 4.5:
        add("contrast-ratio", "warning", f"Text {r['ink']} on {r['bg']} reads at {contrast(r['ink'], r['bg']):.1f}:1 (4.5 needed). "
            "Hoola darkens or lightens it on your site.")
    if r.get("primary"):
        on = r.get("on_primary") or ("#ffffff" if lum(r["primary"]) < 0.45 else "#000000")
        if contrast(on, r["primary"]) < 4.5:
            add("contrast-ratio", "warning", f"Button text {on} on {r['primary']} reads at {contrast(on, r['primary']):.1f}:1. "
                "Hoola picks a readable button text colour.")
    unknown = [k for k in (doc.get("front") or {}) if k not in KNOWN_KEYS]
    if unknown:
        add("unknown-key", "info", "Kept but not used: " + ", ".join(str(k) for k in unknown[:6]))
    return out


def usable(doc: dict[str, Any]) -> bool:
    r = doc.get("roles") or {}
    return bool(r.get("bg") or r.get("primary"))


# ---------------------------------------------------------------- the two modes
def modes(r: dict[str, str]) -> dict[str, dict[str, str]]:
    """The look's own mode as read + the other one made from the same colours; every text pair readable."""
    bg = r.get("bg") or "#ffffff"
    dark = lum(bg) < 0.2
    prim = r.get("primary") or ("#5b45e0" if not dark else "#8b7bff")

    def finish(m: dict[str, str]) -> dict[str, str]:
        m["ink"] = readable(m["ink"], m["bg"], 7)
        m["muted"] = readable(m.get("muted") or TK._mix(m["ink"], m["bg"], 0.42), m["bg"], 4.5)
        m["line"] = m.get("line") or TK._mix(m["bg"], m["ink"], 0.12)
        m["surface"] = m.get("surface") or TK._mix(m["bg"], m["ink"], 0.04)
        p = m["primary"]
        if contrast(p, m["bg"]) < 3:
            p = readable(p, m["bg"], 3)
        m["primary"] = p
        on = m.get("on_primary") or ""
        if not on or contrast(on, p) < 4.5:
            on = "#ffffff" if contrast("#ffffff", p) >= contrast("#000000", p) else "#000000"
        m["on_primary"] = on
        return m

    own = finish({"bg": bg, "surface": r.get("surface") or "", "ink": r.get("ink") or ("#f5f5f5" if dark else "#141414"),
                  "muted": r.get("muted") or "", "line": r.get("line") or "", "primary": prim, "on_primary": r.get("on_primary") or ""})
    if dark:
        ink = bg if contrast(bg, "#ffffff") >= 12 else "#111214"
        other = finish({"bg": "#ffffff", "surface": TK._mix("#ffffff", prim, 0.035), "ink": ink, "muted": "", "line": "",
                        "primary": prim, "on_primary": ""})
    else:
        base = TK._mix("#0c0d10", prim, 0.07)
        other = finish({"bg": base, "surface": TK._mix(base, "#ffffff", 0.05), "ink": "#f3f4f6", "muted": "",
                        "line": TK._mix(base, "#ffffff", 0.12), "primary": prim, "on_primary": ""})
    return {"own": "dark" if dark else "light", "dark": own if dark else other, "light": other if dark else own}


# ---------------------------------------------------------------- the design as look 1's reference
def _clip(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def _detok(s: str, doc: dict[str, Any]) -> str:
    """`{colors.primary}` in prose -> its value, so a rule reads on its own."""
    flat = {}
    for grp in ("colors", "rounded", "spacing"):
        for k, v in (doc.get(grp) or {}).items():
            flat[f"{grp}.{k}"] = str(v)

    def rep(m):
        return flat.get(m.group(1), m.group(1).split(".")[-1])
    out = _REF.sub(rep, s)
    return re.sub(r"(#[0-9a-fA-F]{3,8})\s*\(\1\)", r"\1", out)


def rules(doc: dict[str, Any], brand: str = "", n: int = 10) -> list[str]:
    """The Do's and Don'ts as short lines (the source's own name replaced by 'the brand')."""
    txt = section(doc, "Do's and Don'ts")
    out: list[str] = []
    sub = ""
    for ln in txt.split("\n"):
        if ln.startswith("###"):
            sub = "Don't: " if "don" in ln.lower() else "Do: " if "do" in ln.lower() else ""
            continue
        m = re.match(r"\s*[-*]\s+(.+)", ln)
        if not m:
            continue
        line = _detok(m.group(1).replace("`", ""), doc).replace("**", "")
        line = scrub(line, brand)
        if sub and not re.match(r"(?i)(do|don'?t)\b", line):
            line = sub + line
        out.append(_clip(line, 170))
        if len(out) >= n:
            break
    return out


def scrub(s: str, brand: str) -> str:
    """The source's own name out of a line: "the Linear", "Linear's", "signature Linear" read as "the brand", "the
    brand's", "signature brand"; a font named after it ("Linear Display") stays as the font's name."""
    if not brand:
        return s
    for b in sorted({brand, brand.split(".")[0], brand.split()[0]}, key=len, reverse=True):
        if len(b) < 3:
            continue
        nb = (rf"{re.escape(b)}(?:\s+(?:Group|Inc|Ltd|Corp)\b\.?)?"      # "Ant Group" reads as "the brand"
              rf"(?!\s+(?:Display|Text|Sans|Mono|Serif|Grotesk|Headline)\b)(?!\.\w)")
        s = re.sub(rf"\b(the|The)\s+{nb}('s)?\b", lambda m: m.group(1) + " brand" + (m.group(2) or ""), s)
        s = re.sub(rf"\b([a-z]+),?\s+{nb}('s)?\b",
                   lambda m: m.group(1) + " "
                   + ("the brand" if m.group(1) in ("in", "of", "on", "for", "by", "to", "from", "at", "with", "like", "as",
                                                    "and", "or", "than") else "brand") + (m.group(2) or ""), s)
        s = re.sub(rf"\b{nb}('s)?\b", lambda m: "The brand" + (m.group(1) or ""), s)
    return s


def type_note(doc: dict[str, Any]) -> str:
    f = doc.get("fonts") or {}
    bits = []
    if f.get("display_size"):
        bits.append(f"headings up to {f['display_size']}" + (f", weight {f['display_weight']}" if f.get("display_weight") else "")
                    + (f", letter-spacing {f['display_tracking']}" if f.get("display_tracking") else ""))
    if f.get("body_size"):
        bits.append(f"body {f['body_size']}")
    return "; ".join(bits)


def to_ref(doc: dict[str, Any], look: str = "", brand: str = "") -> dict[str, Any]:
    """The design_ref (inspire.normalise's shape, source 'designmd') + the long written rules."""
    from . import inspire as IN
    if not usable(doc):
        raise DesignMdError("Hoola could not find any colours in that DESIGN.md (no canvas / background and no primary).")
    r = doc["roles"]
    f = doc["fonts"]
    rad = doc.get("radius")
    raw = {"bg": r.get("bg"), "surface": r.get("surface"), "ink": r.get("ink"), "primary": r.get("primary"),
           "accent": r.get("accent"), "head_family": f.get("display") or "", "head_kind": head_kind(doc),
           "radius_px": 8 if rad is None else rad, "style": "", "sections": [], "notes": ""}
    ref = IN.normalise("designmd", raw, None)
    overview = scrub(_detok(section(doc, "Overview"), doc), brand)
    rs = rules(doc, brand, 12)
    tn = type_note(doc)
    notes = "; ".join(x for x in [
        _clip(scrub(doc.get("description") or "", brand), 360) or _clip(overview, 360),
        f"type: {tn}" if tn else "",
        ("rules: " + " | ".join(rs)) if rs else "",
    ] if x)
    ref["notes"] = _clip(notes, 1800)
    ref["rules"] = rs
    ref["look"] = (look or doc.get("name") or "Your DESIGN.md")[:80]
    ref["read_by"] = "her DESIGN.md" if not look else f"the {look} design from the catalog"
    ref["md_type"] = tn
    return ref


# ---------------------------------------------------------------- the catalog
CATS = [("all", "All"), ("saas", "SaaS and productivity"), ("ai", "AI"), ("dev", "Developer"), ("fin", "Finance"),
        ("shop", "Shops"), ("consumer", "Consumer"), ("auto", "Automotive"), ("design", "Design"), ("retro", "Retro web")]


CAT_SHORT = {"saas": "SaaS", "ai": "AI", "dev": "Developer", "fin": "Finance", "shop": "Shop", "consumer": "Consumer",
             "auto": "Automotive", "design": "Design", "retro": "Retro"}


@functools.lru_cache(maxsize=1)
def _lib() -> dict[str, Any]:
    p = LIB / "looks.json.gz"
    try:
        return json.loads(gzip.decompress(p.read_bytes()))
    except (OSError, ValueError):
        return {"looks": [], "source": {}}


@functools.lru_cache(maxsize=256)
def _entry(lid: str) -> dict[str, Any] | None:
    for x in _lib()["looks"]:
        if x["id"] == lid:
            doc = parse(x["text"])
            return {**x, "doc": doc}
    return None


def head_kind(doc: dict[str, Any]) -> str:
    """serif / sans / display / rounded / handwritten / mono - from the first family, or the stack's generic fallback
    ('sans-serif' at the end of a stack must not read as 'serif')."""
    from . import inspire as IN
    raw = str((doc.get("fonts") or {}).get("family_raw") or (doc.get("fonts") or {}).get("display") or "")
    stack = [x.strip().strip("'\"`").lower() for x in raw.split(",") if x.strip()]
    first = stack[0] if stack else ""
    k = IN.font_kind(first.replace("sans-serif", "").replace("sans serif", "")) if first else "sans"
    if k != "sans":
        return k
    if "serif" in stack and "sans-serif" not in stack:
        return "serif"
    if "monospace" in stack and len(stack) <= 2:
        return "mono"
    return "sans"


_head_kind = head_kind


def _card(x: dict[str, Any]) -> dict[str, Any]:
    e = _entry(x["id"]) or {}
    doc = e.get("doc") or {}
    md = modes(doc.get("roles") or {})
    own = md[md["own"]]
    rad = doc.get("radius")
    kind = _head_kind(doc) if doc else "sans"
    return {"id": x["id"], "name": x["name"], "src": x["src"], "cat": x["cat"],
            "cat_label": dict(CATS).get(x["cat"], x["cat"]), "cat_short": CAT_SHORT.get(x["cat"], x["cat"]), "line": x.get("line") or "", "new": bool(x.get("new")),
            "dark": md["own"] == "dark",
            "t": {"bg": own["bg"], "surf": own["surface"], "ink": own["ink"], "muted": own["muted"], "acc": own["primary"],
                  "on": own["on_primary"], "line": own["line"], "r": 8 if rad is None else max(0, min(28, rad)),
                  "kind": kind, "upper": bool(x.get("upper"))}}


def catalog(cat: str = "", q: str = "") -> dict[str, Any]:
    looks = _lib()["looks"]
    counts: dict[str, int] = {}
    for x in looks:
        counts[x["cat"]] = counts.get(x["cat"], 0) + 1
    cats = [{"id": k, "label": v, "count": len(looks) if k == "all" else counts.get(k, 0)}
            for k, v in CATS if k == "all" or counts.get(k)]
    q = (q or "").strip().lower()
    rows = [x for x in looks if (not cat or cat == "all" or x["cat"] == cat)
            and (not q or q in (x["name"] + " " + x.get("line", "") + " " + x["src"] + " " + x["cat"]).lower())]
    return {"total": len(looks), "cats": cats, "looks": [_card(x) for x in rows],
            "source": _lib().get("source") or {}}


def _swatches(m: dict[str, str]) -> list[dict[str, str]]:
    return [{"role": a, "hex": m[b]} for a, b in (("Canvas", "bg"), ("Surface", "surface"), ("Text", "ink"),
                                                   ("Muted text", "muted"), ("Main colour", "primary"), ("Hairline", "line"))]


def prompt_for(name: str, doc: dict[str, Any]) -> str:
    md = modes(doc["roles"])
    own = md[md["own"]]
    kind = _head_kind(doc)
    fk = {"serif": "serif headlines", "display": "bold display headlines", "rounded": "rounded friendly headlines",
          "mono": "monospaced headlines", "handwritten": "hand-drawn headlines"}.get(kind, "clean sans-serif headlines")
    rad = doc.get("radius")
    corners = "square corners" if rad == 0 else "pill-round buttons" if (rad or 8) >= 20 else f"{rad or 8}px corners"
    tn = type_note(doc)
    return (f"Build a website for [your business] in the {name} look: {md['own']} canvas ({own['bg']}), text {own['ink']}, "
            f"one main colour {own['primary']} kept for the main button, focus and links. {fk.capitalize()}"
            + (f" ({tn})" if tn else "") + f", {corners}. Follow the look's rules; use my words and name only.")


def look(lid: str) -> dict[str, Any]:
    e = _entry(lid)
    if not e:
        raise DesignMdError("That design is not in the catalog.", 404)
    doc = e["doc"]
    md = modes(doc["roles"])
    ref = to_ref(doc, e["name"], e.get("brand") or "")
    fk = ref["fonts"]
    from . import taxonomy as T
    adds = [f"A {'light' if md['own'] == 'dark' else 'dark'} version, made from the same colours"]
    raw_font = doc["fonts"].get("display") or ""
    if raw_font and raw_font.lower() != T.FONTS[fk]["head"].lower():
        adds.append(f"Its font ({raw_font}) is replaced by {T.FONTS[fk]['head']} and {T.FONTS[fk]['body']}, which Hoola bundles, Hindi included")
    adds.append("Every text and background pair checked for readability")
    adds.append("Your own pages, words, photos and name - never the source site's")
    return {**_card(e), "description": _clip(scrub(_detok(doc.get("description") or section(doc, "Overview"), doc), e.get("brand") or ""), 600),
            "source_note": (f"Read from the DESIGN.md that {(e.get('from') or {}).get('repo')} publishes (MIT). " if e.get("from") else
                            f"Read from the public DESIGN.md analysis of {e['src']} (awesome-design-md, MIT). ")
                           + "Hoola uses the look, never their name, logo, words or pictures.",
            "prompt": prompt_for(e["name"], doc), "rules": ref["rules"][:8], "type": {
                "head": T.FONTS[fk]["head"], "body": T.FONTS[fk]["body"], "source": raw_font, "note": type_note(doc)},
            "radius": doc.get("radius"), "modes": md, "swatches": {"dark": _swatches(md["dark"]), "light": _swatches(md["light"])},
            "adds": adds, "lint": lint(doc), "own_mode": md["own"],
            "similar": [_card(x) for x in _lib()["looks"] if x["cat"] == e["cat"] and x["id"] != e["id"]][:4]}


def md_text(lid: str) -> str:
    e = _entry(lid)
    if not e:
        raise DesignMdError("That design is not in the catalog.", 404)
    return e["text"]


def ref_for(look_id: str = "", text: str = "") -> dict[str, Any] | None:
    """POST /api/sites {design_look | design_md}: the reference look 1 follows, or None."""
    if look_id:
        e = _entry(str(look_id)[:80])
        if not e:
            raise DesignMdError("That design is not in the catalog.", 404)
        return to_ref(e["doc"], e["name"], e.get("brand") or "")
    if text and text.strip():
        doc = parse(text)
        return to_ref(doc, doc.get("name") or "Your DESIGN.md")
    return None


def check(text: str) -> dict[str, Any]:
    """Her own DESIGN.md: read + checked, nothing saved (the Studio shows it before she uses it)."""
    doc = parse(text)
    ok = usable(doc)
    md = modes(doc["roles"]) if ok else None
    out = {"ok": ok, "name": doc.get("name") or "Your DESIGN.md", "lint": lint(doc),
           "found": {"colours": sum(1 for v in doc["roles"].values() if v), "fonts": doc["fonts"].get("display") or "",
                     "sections": [s["heading"] for s in doc["sections"]][:14], "rules": len(rules(doc, "", 50))}}
    if ok:
        ref = to_ref(doc, out["name"])
        own = md[md["own"]]
        out.update({"own_mode": md["own"], "t": {"bg": own["bg"], "surf": own["surface"], "ink": own["ink"], "muted": own["muted"],
                                                 "acc": own["primary"], "on": own["on_primary"], "line": own["line"],
                                                 "r": 8 if doc.get("radius") is None else max(0, min(28, doc["radius"])),
                                                 "kind": _head_kind(doc)},
                    "style": ref["style_label"], "fonts": f"{ref['head']} + {ref['body']}", "rules_list": ref["rules"][:6]})
    else:
        out["say"] = "Hoola could not find any colours in it. A DESIGN.md needs at least a background or a main colour."
    return out


# ---------------------------------------------------------------- a full sample page in the look (public, no script)
def sample_page(lid: str, mode: str = "") -> str:
    e = _entry(lid)
    if not e:
        raise DesignMdError("That design is not in the catalog.", 404)
    doc = e["doc"]
    md = modes(doc["roles"])
    m = md.get(mode if mode in ("dark", "light") else md["own"])
    from . import taxonomy as T
    from . import designq as DQ
    ref = to_ref(doc, e["name"], e.get("brand") or "")
    fk = ref["fonts"]
    head, body = T.FONTS[fk]["head"], T.FONTS[fk]["body"]
    faces = ""
    for fam, w in ((head, 600), (body, 400), (body, 600)):
        u = DQ._font_url(fam, w)
        if u:
            faces += f"@font-face{{font-family:'{fam}';src:url('{u}') format('woff2');font-weight:{w};font-display:swap}}"
    r = doc.get("radius")
    r = 8 if r is None else max(0, min(28, r))
    rb = 999 if r >= 20 else r
    f = doc["fonts"]
    tr = f.get("display_tracking") or ("-0.02em" if _head_kind(doc) != "serif" else "-0.01em")
    up = "uppercase" if e.get("upper") else "none"
    hw = 400 if _head_kind(doc) == "serif" else 600
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
    css = f"""{faces}
*{{box-sizing:border-box}}html,body{{margin:0}}body{{background:{m['bg']};color:{m['ink']};font:16px/1.55 '{body}',system-ui,sans-serif}}
.w{{max-width:1120px;margin:0 auto;padding:0 32px}}nav{{display:flex;align-items:center;gap:22px;padding:20px 0;flex-wrap:wrap}}
.lg{{display:flex;align-items:center;gap:9px;font-weight:600}}.lg i{{width:18px;height:18px;border-radius:{min(r, 6)}px;background:{m['primary']};display:block}}
.sp{{flex:1}}.nl{{color:{m['muted']};font-size:14px}}
.b{{display:inline-flex;align-items:center;height:40px;padding:0 18px;border-radius:{rb}px;background:{m['primary']};color:{m['on_primary']};font-weight:600;font-size:15px;text-decoration:none}}
.g{{display:inline-flex;align-items:center;height:40px;padding:0 18px;border-radius:{rb}px;border:1px solid {m['line']};color:{m['ink']};font-size:15px;text-decoration:none;background:{m['surface']}}}
h1,h2,h3{{font-family:'{head}',system-ui,sans-serif;font-weight:{hw};letter-spacing:{tr};text-transform:{up};margin:0}}
h1{{font-size:clamp(38px,6vw,68px);line-height:1.04;max-width:820px}}h2{{font-size:clamp(28px,3.6vw,40px);line-height:1.1}}h3{{font-size:19px;letter-spacing:-0.01em}}
.hero{{padding:72px 0 36px;display:flex;flex-direction:column;gap:20px}}.ey{{align-self:flex-start;font-size:13px;color:{m['muted']};border:1px solid {m['line']};border-radius:999px;padding:4px 12px;background:{m['surface']}}}
.lead{{font-size:19px;color:{m['muted']};max-width:600px;margin:0}}.row{{display:flex;gap:10px;flex-wrap:wrap}}
.shot{{margin:28px 0;background:{m['surface']};border:1px solid {m['line']};border-radius:{min(r, 16)}px;padding:18px}}
.it{{display:flex;align-items:center;gap:12px;padding:12px 4px;border-bottom:1px solid {m['line']};font-size:14px}}.it:last-child{{border:0}}
.dot{{width:10px;height:10px;border-radius:999px;border:2px solid {m['primary']}}}.mu{{color:{m['muted']};font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:28px 0}}
.c{{background:{m['surface']};border:1px solid {m['line']};border-radius:{min(r, 14)}px;padding:22px;display:flex;flex-direction:column;gap:10px;align-items:flex-start}}
.c.hi{{border-color:{m['primary']}}}.ic{{width:32px;height:32px;border-radius:{min(r, 9)}px;background:{TK._mix(m['primary'], m['surface'], 0.82)}}}
.c p{{margin:0;color:{m['muted']};font-size:14px}}.pr{{font-family:'{head}';font-size:26px;font-weight:{hw}}}
.band{{margin:40px 0;background:{m['surface']};border:1px solid {m['line']};border-radius:{min(r, 18)}px;padding:44px;display:flex;flex-wrap:wrap;gap:18px;align-items:center;justify-content:space-between}}
footer{{border-top:1px solid {m['line']};padding:26px 0 40px;display:flex;flex-wrap:wrap;gap:20px;justify-content:space-between;color:{m['muted']};font-size:13px}}
@media(max-width:600px){{.w{{padding:0 18px}}.nl{{display:none}}.hero{{padding-top:40px}}.band{{padding:26px}}}}"""
    rows = "".join(f'<div class="it"><span class="dot"></span><span class="mu">#{140 - i * 3}</span><span>{t}</span>'
                   f'<span class="sp"></span><span class="mu">{g}</span></div>'
                   for i, (t, g) in enumerate([("New enquiry from the website", "Today"), ("Order ready to send", "Today"),
                                               ("Booking for Saturday", "Tomorrow"), ("Weekly report", "Mon")]))
    feats = "".join(f'<div class="c"><span class="ic"></span><h3>{a}</h3><p>A short line about {b}.</p></div>'
                    for a, b in (("What you offer", "the first thing you offer"), ("How it works", "how a customer starts"),
                                 ("Why people choose you", "what makes you different")))
    tiers = "".join(f'<div class="c{" hi" if i == 1 else ""}"><span class="mu">{n}</span><span class="pr">[YOUR PRICE]</span>'
                    f'<p>{d}</p><a class="{"b" if i == 1 else "g"}" href="#">Choose</a></div>'
                    for i, (n, d) in enumerate((("Starter", "For getting going."), ("Most chosen", "For growing."), ("Large", "Talk to us."))))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(e['name'])} - sample page</title><style>{css}</style></head><body>
<div class="w"><nav><span class="lg"><i></i>Your business</span><span class="sp"></span><span class="nl">Services</span><span class="nl">Prices</span><span class="nl">About</span><a class="g" href="#">Contact</a><a class="b" href="#">Get started</a></nav>
<section class="hero"><span class="ey">A short announcement goes here</span><h1>Your headline, in your own words</h1>
<p class="lead">One line about what you do. Hoola writes it from your business, never from the site this look came from.</p>
<div class="row"><a class="b" href="#">Get started</a><a class="g" href="#">See how it works</a></div></section>
<div class="shot">{rows}</div><div class="grid">{feats}</div><div class="grid">{tiers}</div>
<div class="band"><h2>Ready to start?</h2><a class="b" href="#">Get started</a></div>
<footer><span>&copy; Your business</span><span>Privacy &middot; Terms &middot; Contact</span></footer></div>
</body></html>"""


__all__ = ["parse", "lint", "to_ref", "ref_for", "check", "catalog", "look", "md_text", "sample_page", "modes",
           "hexify", "DesignMdError", "SECTION_ORDER"]
