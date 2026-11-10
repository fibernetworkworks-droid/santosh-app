"""v0.606 SAAF NAZAR - the "AI look" check on every built website (ideas from pbakaus/impeccable, Apache-2.0, re-written
in Hoola's own Python; no upstream code, see THIRD_PARTY_NOTICES.md).

Impeccable's finding: ask a model for a page with no other guidance and the same tells come back across models and
projects - Inter everywhere, purple-violet gradients, a cream page, a tiny label above every heading, an icon tile
above every card heading, gradient text, glowing halos, bounce easing, buzzword copy. Each is fine once on purpose;
reached for by reflex they make a site read as "an AI made this". This module reads the BUILT site (every page, the
section CSS in assets/site.css) and names each tell with the page and the section it sits in.

Rules, in plain words:
- It NEVER blocks a launch. Its rows are `warn` / `pass` in the gates list (gate "look").
- Before her first version, the per-section tells go into the build's existing fix rounds ONCE (`fix_items`), so the
  builder cleans its own reflexes before she sees them. Global tells (fonts, page colour) are only said.
- THE BRIEF WINS (Impeccable's first rule): when her own design set the fonts / colours (KOI BHI DESIGN look 1 or her
  brand colours) the font / colour tells are skipped, and any tell whose name she asked for in her words (marquee,
  gradient, neon, glow, brutalist...) is skipped too.
- Every page has a MODE (what the visitor's success is): persuade (home, services, pricing), operate (account, admin,
  cart, checkout), read (blog, faq, policies), experience (gallery, portfolio). Some tells are not judged on some modes
  (an icon tile on a dashboard is fine; numbered labels in a guide may carry meaning)."""
from __future__ import annotations

import colorsys
import re
from pathlib import Path
from typing import Any

OVERUSED_FONTS = ("Inter", "Roboto", "Fraunces", "Geist", "Plus Jakarta Sans", "Space Grotesk")
BUZZ = ("streamline", "empower", "supercharge", "world-class", "world class", "enterprise-grade", "next-generation",
        "next generation", "cutting-edge", "cutting edge", "seamless", "seamlessly", "revolutionize", "revolutionise",
        "game-changer", "game changer", "best-in-class", "state-of-the-art", "synergy", "unlock your", "elevate your",
        "take it to the next level", "one-stop solution", "one stop solution")
# words in HER brief that pin a tell (the brief wins)
PINNED = {"marquee": ("marquee", "ticker", "scrolling strip"),
          "gradient-text": ("gradient text", "gradient heading"),
          "ai-color-palette": ("purple", "violet", "neon", "gradient"),
          "dark-glow": ("glow", "neon"), "radial-halo": ("glow", "neon", "spotlight"),
          "hard-offset-shadow": ("brutal", "neobrutal", "retro", "comic"),
          "bounce-easing": ("bouncy", "bounce", "playful"),
          "cream-palette": ("cream", "beige", "ivory", "off-white", "off white"),
          "overused-font": ("inter", "roboto", "fraunces", "geist", "jakarta", "space grotesk"),
          "numbered-section-labels": ("step 1", "steps", "numbered"),
          "repeating-stripes": ("stripes", "striped"), "grid-background": ("blueprint", "grid paper", "graph paper")}

MODES = ("persuade", "operate", "read", "experience")
RULES: dict[str, dict[str, Any]] = {
    "overused-font": {"name": "Overused font", "kind": "slop", "scope": "site",
                      "fix": "Pick a face with its own character; Inter / Roboto / Fraunces / Geist / Plus Jakarta / Space "
                             "Grotesk are on so many sites they no longer say anything about this business."},
    "cream-palette": {"name": "Cream / beige page", "kind": "slop", "scope": "site",
                      "fix": "A warm cream page is the default 'tasteful' AI surface; choose the page colour from the "
                             "business's own world (its shop, its material, its city)."},
    "gradient-text": {"name": "Gradient text", "kind": "slop", "fix": "Remove the gradient fill on text; give emphasis "
                      "with size or weight, in a solid brand colour."},
    "ai-color-palette": {"name": "Purple / violet gradient", "kind": "slop", "fix": "Replace the violet gradient with a "
                         "solid surface or a gradient from the site's own palette."},
    "side-tab": {"name": "Thick side border on a card", "kind": "slop", "fix": "Remove the thick coloured left / right "
                 "border; mark the card with spacing, a heading or a full hairline border instead."},
    "nested-cards": {"name": "Card inside a card", "kind": "slop", "fix": "Flatten: keep one card level and separate the "
                     "inner items with spacing and type."},
    "icon-tile-stack": {"name": "Icon tile above every heading", "kind": "slop", "modes": ("persuade", "read", "experience"),
                        "fix": "Drop the rounded icon tile above each card heading; let the heading lead, or use a real "
                               "photo / one inline icon beside the words."},
    "kicker-above-heading": {"name": "Small label above a heading", "kind": "slop",
                             "fix": "Delete the small tracked / uppercase label above the heading; the heading carries "
                                    "its own weight."},
    "numbered-section-labels": {"name": "Numbered section labels (01 / 02 / 03)", "kind": "slop",
                                "modes": ("persuade", "experience"),
                                "fix": "Remove the 01 / 02 / 03 markers unless the order itself is information."},
    "bounce-easing": {"name": "Bounce / elastic easing", "kind": "slop", "fix": "Use a smooth deceleration "
                      "(cubic-bezier(0.22, 1, 0.36, 1)) instead of an overshooting curve."},
    "marquee": {"name": "Auto-scrolling marquee", "kind": "slop", "fix": "Replace the scrolling strip with a still row "
                "the visitor can read at once."},
    "dark-glow": {"name": "Glowing coloured shadow", "kind": "slop", "fix": "Replace the zero-offset coloured glow with "
                  "a soft offset shadow, or none."},
    "radial-halo": {"name": "Coloured radial halo behind a section", "kind": "slop", "fix": "Remove the coloured "
                    "radial-gradient wash; use a photo, a solid surface or the business's own texture."},
    "repeating-stripes": {"name": "Decorative stripes", "kind": "slop", "fix": "Remove the repeating-gradient stripes "
                          "unless the business's world has them (an awning, a ledger)."},
    "grid-background": {"name": "Decorative grid-line background", "kind": "slop", "fix": "Remove the hairline grid "
                        "background unless the page is a real map / blueprint / measuring surface."},
    "hard-offset-shadow": {"name": "Hard offset shadow", "kind": "quality", "fix": "Give the shadow a soft blur and a "
                           "small offset, or remove it."},
    "marketing-buzzword": {"name": "Marketing buzzwords", "kind": "slop", "fix": "Say plainly what the business does "
                           "and for whom; replace each buzzword with a fact from her words."},
    "theater-phrase": {"name": "'... theater' framing", "kind": "slop", "fix": "Say plainly what the thing does or "
                       "does not do."},
    "em-dash-overuse": {"name": "Em-dash overuse", "kind": "slop", "scope": "site", "modes": ("persuade", "read"),
                        "fix": "Use commas, full stops or brackets for most of the em dashes."},
    "emoji-icons": {"name": "Emoji used as icons", "kind": "quality", "fix": "Use the site's one icon set "
                    "(<i data-icon>) instead of emoji in headings and list items."},
    "italic-serif-display": {"name": "Italic serif hero headline", "kind": "slop", "modes": ("persuade",),
                             "fix": "Set the hero headline upright; the italic serif display is the reflex 'elegant' look."},
    "justified-text": {"name": "Justified text", "kind": "quality", "fix": "Set body text left-aligned "
                       "(text-align: start)."},
    "all-caps-body": {"name": "All-caps body text", "kind": "quality", "fix": "Set long text in sentence case; keep "
                      "uppercase for a few words at most."},
    "wide-tracking": {"name": "Wide letter spacing on body text", "kind": "quality", "fix": "Keep letter-spacing on "
                      "body text at or under 0.05em."},
    "crushed-tracking": {"name": "Crushed letter spacing", "kind": "quality", "fix": "Keep negative letter-spacing at "
                         "or above -0.04em."},
    "tight-leading": {"name": "Tight line height on body text", "kind": "quality", "fix": "Set body line-height "
                      "between 1.5 and 1.7."},
    "tiny-text": {"name": "Tiny body text", "kind": "quality", "fix": "Keep body text at 14px or more (16px for long "
                  "reading)."},
    "skipped-heading": {"name": "Skipped heading level", "kind": "quality", "scope": "page",
                        "fix": "Use heading levels in order (h1, then h2, then h3)."},
    "broken-image": {"name": "Broken / placeholder image", "kind": "quality", "fix": "Use a real image of the business "
                     "or remove the empty <img>."},
}
# the per-section tells the build's fix round may rewrite on its own (global ones are only said)
FIXABLE = ("gradient-text", "ai-color-palette", "side-tab", "nested-cards", "icon-tile-stack", "kicker-above-heading",
           "numbered-section-labels", "bounce-easing", "dark-glow", "radial-halo", "hard-offset-shadow",
           "marketing-buzzword", "emoji-icons", "theater-phrase", "justified-text", "tight-leading", "tiny-text")
STATS = {"scans": 0, "findings": 0}

SEC_RE = re.compile(r"""<section\b[^>]*\bid\s*=\s*["'](s-[\w-]+)["'][^>]*>(.*?)</section>""", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


# ---------------------------------------------------------------- page modes
def page_mode(rel: str) -> str:
    """What the visitor's success on this page is (Impeccable's surface modes), from its address."""
    p = "/" + rel.lower().lstrip("/")
    if re.search(r"/(account|admin|app|cart|checkout|orders?|login|signup|my-(?:account|orders|bookings|profile)|cms|dashboard)(/|\.html|$)", p):
        return "operate"
    if re.search(r"/(blog|faq|help|guide|docs?|policy|policies|privacy|terms|refund|shipping|returns|disclaimer)(/|\.html|$|-)",
                 p):
        return "read"
    if re.search(r"/(gallery|portfolio|work|projects?|showcase)(/|\.html|$)", p):
        return "experience"
    return "persuade"


# ---------------------------------------------------------------- css
def css_rules(css: str) -> list[tuple[str, str]]:
    """(selector, declarations) for every plain rule, @media / @supports opened; @keyframes / @font-face skipped."""
    out: list[tuple[str, str]] = []
    i, n = 0, len(css)
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    n = len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        sel = css[i:j].strip()
        if sel.startswith("@") and re.match(r"@(media|supports|layer|container)\b", sel):
            i = j + 1                               # step inside, its rules are read as plain rules
            continue
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        if not sel.startswith("@"):
            out.append((sel.lstrip("}").strip(), body))
        i = k
    return out


def _secs_of(sel: str) -> list[str]:
    return sorted(set(re.findall(r"#(s-[\w-]+)", sel)))


def _hex_rgb(h: str) -> tuple[float, float, float] | None:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8) or not re.fullmatch(r"[0-9a-fA-F]+", h):
        return None
    return tuple(int(h[k:k + 2], 16) / 255 for k in (0, 2, 4))  # type: ignore[return-value]


def _colors(s: str) -> list[tuple[float, float, float]]:
    got = []
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", s):
        c = _hex_rgb(m.group(0))
        if c:
            got.append(c)
    for m in re.finditer(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)", s):
        got.append(tuple(int(m.group(k)) / 255 for k in (1, 2, 3)))  # type: ignore[arg-type]
    for m in re.finditer(r"hsla?\(\s*(\d+)(?:deg)?[ ,]+(\d+)%[ ,]+(\d+)%", s):
        got.append(colorsys.hls_to_rgb(int(m.group(1)) / 360, int(m.group(3)) / 100, int(m.group(2)) / 100))
    return got


def _hls(c: tuple[float, float, float]) -> tuple[float, float, float]:
    h, l, s = colorsys.rgb_to_hls(*c)
    return h * 360, l, s


def _violet(c: tuple[float, float, float]) -> bool:
    h, l, s = _hls(c)
    return 255 <= h <= 300 and s >= 0.45 and 0.2 <= l <= 0.8


def _saturated(c: tuple[float, float, float]) -> bool:
    h, l, s = _hls(c)
    return s >= 0.45 and 0.15 <= l <= 0.85


def _len_px(v: str, base: float = 16) -> float | None:
    m = re.match(r"\s*(-?[\d.]+)(px|rem|em)?", v)
    if not m:
        return None
    x = float(m.group(1))
    return x * base if m.group(2) in ("rem", "em") else x


def css_findings(css: str) -> list[tuple[str, list[str], str]]:
    """(rule, sections, evidence) from the SECTION css (selectors under #s-...)."""
    out: list[tuple[str, list[str], str]] = []
    body_sel = re.compile(r"(^|[\s>,])(p|li|body|\.lead|blockquote|dd|td)\b")
    for sel, body in css_rules(css):
        secs = _secs_of(sel)
        if not secs and not sel.lstrip().startswith(".k-"):
            continue                                # Hoola's own base css is not judged; the site's kit (.k-) is
        d = body.lower()
        ev = f"{sel[:80]} {{{body[:120]}}}"
        if re.search(r"(-webkit-)?background-clip\s*:\s*text", d) and "gradient(" in d:
            out.append(("gradient-text", secs, ev))
        for g in re.finditer(r"(linear|radial|conic)-gradient\(([^;]*)", d):
            cs = _colors(g.group(2))
            if sum(1 for c in cs if _violet(c)) >= 1 and len(cs) >= 2:
                out.append(("ai-color-palette", secs, ev))
                break
        if re.search(r"radial-gradient\([^;]*transparent", d) and any(_saturated(c) for c in _colors(d)) \
                and re.search(r"background(-image)?\s*:", d):
            out.append(("radial-halo", secs, ev))
        if "repeating-linear-gradient" in d or "repeating-radial-gradient" in d:
            out.append(("repeating-stripes", secs, ev))
        if re.search(r"linear-gradient\([^;]*\b1px\b", d) and re.search(r"background-size\s*:\s*\d+px", d):
            out.append(("grid-background", secs, ev))
        for m in re.finditer(r"border-(?:left|right|inline-start|inline-end)\s*:\s*(\d+(?:\.\d+)?)px", d):
            if float(m.group(1)) >= 2:
                out.append(("side-tab", secs, ev))
                break
        for m in re.finditer(r"cubic-bezier\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", d):
            ys = (float(m.group(2)), float(m.group(4)))
            if any(y > 1.0 or y < 0 for y in ys):
                out.append(("bounce-easing", secs, ev))
                break
        if re.search(r"animation[^;]*\b(bounce|elastic|wobble|jello)\b", d):
            out.append(("bounce-easing", secs, ev))
        for m in re.finditer(r"(box|text)-shadow\s*:\s*([^;]+)", d):
            for part in re.split(r",(?![^(]*\))", m.group(2)):
                nums = re.findall(r"(-?[\d.]+)(?:px)?\b", re.sub(r"(rgba?|hsla?)\([^)]*\)|#[0-9a-f]{3,8}", "", part))
                cs = _colors(part)
                if len(nums) >= 3:
                    x, y, blur = (float(v) for v in nums[:3])
                    if x == 0 and y == 0 and blur >= 8 and any(_saturated(c) for c in cs):
                        out.append(("dark-glow", secs, ev))
                    elif blur == 0 and max(abs(x), abs(y)) >= 4 and m.group(1) == "box":
                        out.append(("hard-offset-shadow", secs, ev))
        if body_sel.search(sel.split("#", 1)[-1] if "#" in sel else sel):
            if re.search(r"text-align\s*:\s*justify", d):
                out.append(("justified-text", secs, ev))
            if re.search(r"text-transform\s*:\s*uppercase", d) and re.search(r"(^|[\s>,])p\b", sel):
                out.append(("all-caps-body", secs, ev))
            for m in re.finditer(r"letter-spacing\s*:\s*(-?[\d.]+)em", d):
                if float(m.group(1)) > 0.05:
                    out.append(("wide-tracking", secs, ev))
            for m in re.finditer(r"line-height\s*:\s*([\d.]+)\s*(;|$|!)", d):
                if float(m.group(1)) < 1.3:
                    out.append(("tight-leading", secs, ev))
            for m in re.finditer(r"font-size\s*:\s*([\d.]+(?:px|rem|em))", d):
                px = _len_px(m.group(1))
                if px is not None and px < 12:
                    out.append(("tiny-text", secs, ev))
        for m in re.finditer(r"letter-spacing\s*:\s*(-[\d.]+)em", d):
            if float(m.group(1)) < -0.04:
                out.append(("crushed-tracking", secs, ev))
        if re.search(r"(^|[\s>,])h1\b", sel) and re.search(r"font-style\s*:\s*italic", d):
            out.append(("italic-serif-display", secs, ev))
    return out


# ---------------------------------------------------------------- html
def _text(h: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.I | re.S))).strip()


KICKER_CLS = re.compile(r"""class\s*=\s*["'][^"']*\b(eyebrow|kicker|overline|k-eyebrow|pretitle|pre-title|tagline-sm|label-sm|"""
                        r"""section-label|subtitle-top)\b""", re.I)
SHORT_BEFORE_HEAD = re.compile(r"<(p|span|div|small)\b([^>]*)>([^<]{1,40})</\1>\s*<h([1-3])\b", re.I)
ICON_TILE = re.compile(r"<(div|span)\b[^>]*>\s*(?:<svg\b.*?</svg>|<i\b[^>]*data-icon[^>]*>\s*</i>)\s*</\1>\s*<h[2-4]\b",
                       re.I | re.S)
NUM_LABEL = re.compile(r">\s*0[1-9]\s*(?:/|\.|—|-)?\s*<", re.I)
CARD_OPEN = re.compile(r"""<(\w+)\b[^>]*class\s*=\s*["'][^"']*\b(card|k-card)\b[^"']*["'][^>]*>""", re.I)


def _nested_cards(sec_html: str) -> bool:
    """A .card element that has another .card inside it (opened before the outer one closes)."""
    for m in CARD_OPEN.finditer(sec_html):
        tag = m.group(1).lower()
        depth, pos = 1, m.end()
        tok = re.compile(rf"<(/?){tag}\b[^>]*>", re.I)
        end = len(sec_html)
        for t in tok.finditer(sec_html, pos):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = t.start()
                break
        if CARD_OPEN.search(sec_html, pos, end):
            return True
    return False


def html_findings(page_html: str) -> list[tuple[str, list[str], str]]:
    out: list[tuple[str, list[str], str]] = []
    sections = list(SEC_RE.finditer(page_html))
    numbered = []
    for m in sections:
        sid, inner = m.group(1), m.group(2)
        if KICKER_CLS.search(inner):
            out.append(("kicker-above-heading", [sid], KICKER_CLS.search(inner).group(0)[:80]))
        else:
            for k in SHORT_BEFORE_HEAD.finditer(inner):
                words = k.group(3).strip()
                if words and len(words.split()) <= 5 and (words.isupper() or "uppercase" in k.group(2).lower()):
                    out.append(("kicker-above-heading", [sid], words[:40]))
                    break
        if len(ICON_TILE.findall(inner)) >= 3:
            out.append(("icon-tile-stack", [sid], f"{len(ICON_TILE.findall(inner))} icon tiles above headings"))
        if NUM_LABEL.search(inner[:600]):
            numbered.append(sid)
        if _nested_cards(inner):
            out.append(("nested-cards", [sid], "a .card inside a .card"))
        if "data-m=\"marquee\"" in inner or "data-m='marquee'" in inner or re.search(r"<marquee\b", inner, re.I):
            out.append(("marquee", [sid], "data-m=marquee"))
        heads = re.findall(r"<(h[1-4]|li)\b[^>]*>\s*([^<]{0,6})", inner, re.I)
        if sum(1 for _t, s in heads if EMOJI.search(s or "")) >= 3:
            out.append(("emoji-icons", [sid], "emoji leading headings / list items"))
        text = _text(inner).lower()
        bz = sorted({w for w in BUZZ if re.search(rf"\b{re.escape(w)}\b", text)})
        if bz:
            out.append(("marketing-buzzword", [sid], ", ".join(bz[:5])))
        if re.search(r"\b\w+\s+theat(?:er|re)\b", text) and not re.search(r"\b(movie|cinema|film|drama|home) theat", text):
            out.append(("theater-phrase", [sid], "... theater"))
        for im in re.finditer(r"<img\b([^>]*)>", inner, re.I):
            a = im.group(1)
            src = re.search(r"""\ssrc\s*=\s*["']([^"']*)["']""", a)
            if not src and "data-hoola-img" not in a and "srcset" not in a:
                out.append(("broken-image", [sid], "<img> without src"))
                break
            if src and (not src.group(1).strip() or src.group(1).strip() == "#" or "placeholder" in src.group(1).lower()
                        or "via.placeholder" in src.group(1)):
                out.append(("broken-image", [sid], src.group(1)[:60]))
                break
    if len(numbered) >= 3:
        out.append(("numbered-section-labels", numbered, f"{len(numbered)} sections open with 01 / 02 / 03"))
    levels = [int(x) for x in re.findall(r"<h([1-6])\b", page_html, re.I)]
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            out.append(("skipped-heading", [], f"h{prev} then h{lv}"))
            break
        prev = lv
    return out


# ---------------------------------------------------------------- the scan
def _pinned(site: dict[str, Any]) -> set[str]:
    """Tells HER own words or her own design asked for: the brief wins."""
    facts = site.get("facts") or {}
    words = " ".join(str(x) for x in (site.get("brief") or "", facts.get("about") or "", facts.get("style_words") or "",
                                      facts.get("notes") or "")).lower()
    got = {rule for rule, keys in PINNED.items() if any(k in words for k in keys)}
    if site.get("her_look") or facts.get("brand_colors"):
        got |= {"overused-font", "cream-palette", "ai-color-palette"}
    return got


def _tokens_findings(tk: dict[str, Any]) -> list[tuple[str, str]]:
    out = []
    used = [tk.get("head") or "", tk.get("body") or ""]
    bad = [f for f in used if f in OVERUSED_FONTS]
    if bad:
        out.append(("overused-font", " + ".join(dict.fromkeys(bad))))
    c = _hex_rgb(str(tk.get("bg") or ""))
    if c:
        h, l, s = _hls(c)
        if 28 <= h <= 55 and l >= 0.9 and 0.25 <= s and l < 0.985:
            out.append(("cream-palette", str(tk.get("bg"))))
    return out


def _pages(out: Path) -> list[Path]:
    return [p for p in out.rglob("*.html") if p.is_file()][:2000]


def scan(out: Path, site: dict[str, Any]) -> dict[str, Any]:
    """Every tell on the built site: {findings: [{rule, name, kind, page, mode, sections, read}], counts, pinned}."""
    STATS["scans"] += 1
    pinned = _pinned(site)
    found: list[dict[str, Any]] = []

    def add(rule: str, page: str, mode: str, secs: list[str], read: str) -> None:
        meta = RULES[rule]
        if rule in pinned or (meta.get("modes") and mode not in meta["modes"]):
            return
        found.append({"rule": rule, "name": meta["name"], "kind": meta["kind"], "page": page, "mode": mode,
                      "sections": secs, "read": read[:160]})

    for rule, read in _tokens_findings(site.get("tokens") or {}):
        add(rule, "", "persuade", [], read)
    css_path = out / "assets" / "site.css"
    css = css_path.read_text(encoding="utf-8", errors="ignore") if css_path.exists() else ""
    sec_page: dict[str, tuple[str, str]] = {}
    dash_words, dash_count = 0, 0
    for p in _pages(out):
        rel = p.relative_to(out).as_posix()
        mode = page_mode(rel)
        html = p.read_text(encoding="utf-8", errors="ignore")
        for m in SEC_RE.finditer(html):
            sec_page.setdefault(m.group(1), (rel, mode))
        for rule, secs, read in html_findings(html):
            add(rule, rel, mode, secs, read)
        if mode in ("persuade", "read"):
            t = _text(html)
            dash_words += len(t.split())
            dash_count += t.count("—")
    for rule, secs, read in css_findings(css):
        if secs and secs[0] not in sec_page:
            continue                                # css for a section no page carries any more
        rel, mode = sec_page[secs[0]] if secs else ("", "persuade")      # no section = the site's design kit
        add(rule, rel, mode, secs, ("kit: " if not secs else "") + read)
    if dash_count >= 6 and dash_words and dash_count / dash_words * 100 > 1.2:
        add("em-dash-overuse", "", "persuade", [], f"{dash_count} em dashes in {dash_words} words")
    seen, uniq = set(), []
    for f in found:                                  # one row per rule + page + section
        key = (f["rule"], f["page"], tuple(f["sections"]))
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    STATS["findings"] += len(uniq)
    by_rule: dict[str, int] = {}
    for f in uniq:
        by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1
    return {"findings": uniq, "count": len(uniq), "by_rule": by_rule, "pinned": sorted(pinned),
            "pages": len(_pages(out))}


def rows(res: dict[str, Any]) -> list[dict[str, Any]]:
    """The gate rows (gate "look"): a WARN per tell found (never a fail), one PASS when the site is clean."""
    out = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for f in res["findings"]:
        groups.setdefault(f["rule"], []).append(f)
    for rule, fs in groups.items():
        meta = RULES[rule]
        where = sorted({f["page"] for f in fs if f["page"]})
        say = meta["fix"] + (f" ({len(fs)} jagah: {', '.join(where[:4])})" if where else "")
        row = {"gate": "look", "check": f"AI look: {meta['name']}", "state": "warn", "say": say,
               "read": "; ".join(f["read"] for f in fs[:3])[:300]}
        secs = sorted({s for f in fs for s in f["sections"]})
        if secs:
            row["sections"] = secs[:12]
        out.append(row)
    if not out:
        out.append({"gate": "look", "check": "AI look: no reflex tells found", "state": "pass",
                    "say": f"{res['pages']} pages read; none of the {len(RULES)} AI-look tells found"
                           + (f" (her own choices kept: {', '.join(res['pinned'])})" if res["pinned"] else "") + ".",
                    "read": ""})
    return out


def fix_items(res: dict[str, Any]) -> list[dict[str, Any]]:
    """Blocking-shaped items for the build's fix round (sections + the plain fix), only the per-section tells."""
    out = []
    for f in res["findings"]:
        if f["rule"] in FIXABLE and f["sections"]:
            out.append({"kind": "look", "text": f"AI look - {RULES[f['rule']]['name']}: {RULES[f['rule']]['fix']}",
                        "sections": f["sections"]})
    return out
