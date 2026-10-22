"""v0.128.1 The app design system catalogue: every structure the prototype can draw (and the native build will follow).

  12 navigation patterns (bottom bars, floating glass pill, side bar / drawer, drawer + bar, nav rail, top tabs, bottom app
     bar with a docked FAB, segmented top, side sheet, none), 8 FAB types, 10 card looks (incl. glass, neumorphic, gradient
     mesh, image overlay, stacked, ticket), 9 header types (incl. collapsing and parallax), 6 button looks,
  40 original textures (SVG drawn by code, coloured from her tokens: grain, paper, linen, terrazzo, marble, bandhani, ikat,
     block print, kantha, jaali, rangoli, mandala ...),
  100 motion presets (screen transitions + micro-interactions, each with the Compose / SwiftUI way to build it),
  3D: tilt cards, flip cards, 3D carousel, 3D object viewer (three.js in the prototype; SceneView / RealityKit natively).
Everything is original: no other app's look is copied."""
from __future__ import annotations

import math
from typing import Any
from urllib.parse import quote

NAV: dict[str, dict[str, str]] = {
    "bar": {"label": "Bottom bar", "android": "Material 3 NavigationBar", "ios": "TabView",
            "desc": "Material 3 navigation bar with a pill indicator / iOS tab bar"},
    "bar_labels": {"label": "Bottom bar + labels", "android": "NavigationBar(alwaysShowLabel)", "ios": "TabView",
                   "desc": "icon + label on every tab, active tab tinted"},
    "bar_minimal": {"label": "Minimal bar", "android": "NavigationBar (labels off)", "ios": "TabView (no titles)",
                    "desc": "icons only with a dot under the active one"},
    "floating_pill": {"label": "Floating glass pill", "android": "custom floating NavigationBar", "ios": "TabView + .ultraThinMaterial",
                      "desc": "a frosted pill floating above the content"},
    "drawer": {"label": "Side bar (drawer)", "android": "ModalNavigationDrawer", "ios": "NavigationSplitView / side menu",
               "desc": "hamburger button opens a side bar with every section"},
    "drawer_bar": {"label": "Side bar + bottom bar", "android": "ModalNavigationDrawer + NavigationBar", "ios": "TabView + side menu",
                   "desc": "main tabs at the bottom, everything else in the side bar"},
    "rail": {"label": "Navigation rail", "android": "NavigationRail", "ios": "sidebar in NavigationSplitView",
             "desc": "slim vertical bar on the left (tablet / foldable look)"},
    "top_tabs": {"label": "Top tabs", "android": "PrimaryTabRow / ScrollableTabRow", "ios": "segmented Picker / custom tabs",
                 "desc": "tabs under the app bar, swipe between them"},
    "bottom_app_bar": {"label": "Bottom app bar + docked FAB", "android": "BottomAppBar + FloatingActionButton", "ios": "toolbar + floating button",
                       "desc": "bottom bar with the main action button docked in the middle"},
    "segmented_top": {"label": "Segmented top", "android": "SingleChoiceSegmentedButtonRow", "ios": "Picker(.segmented)",
                      "desc": "a pill segmented control at the top switches the main sections"},
    "side_sheet": {"label": "Side sheet (right)", "android": "ModalDrawerSheet (end)", "ios": "inspector / sheet",
                   "desc": "a menu that slides in from the right"},
    "none": {"label": "No navigation bar", "android": "single NavHost flow", "ios": "NavigationStack",
             "desc": "one guided flow from the home screen (for very simple apps)"},
}
FAB: dict[str, dict[str, str]] = {
    "none": {"label": "No FAB", "android": "-", "ios": "-"},
    "regular": {"label": "FAB", "android": "FloatingActionButton", "ios": "overlay Button"},
    "small": {"label": "Small FAB", "android": "SmallFloatingActionButton", "ios": "overlay Button"},
    "large": {"label": "Large FAB", "android": "LargeFloatingActionButton", "ios": "overlay Button"},
    "extended": {"label": "Extended FAB (icon + words)", "android": "ExtendedFloatingActionButton", "ios": "overlay Label button"},
    "speed_dial": {"label": "Speed dial (3 actions)", "android": "FAB + AnimatedVisibility mini FABs", "ios": "Menu / expanding buttons"},
    "menu": {"label": "FAB menu", "android": "FloatingActionButtonMenu", "ios": "Menu"},
    "docked": {"label": "Docked in the bottom bar", "android": "BottomAppBar(floatingActionButton)", "ios": "toolbar centre button"},
}
CARDS: dict[str, str] = {
    "elevated": "soft shadow", "outlined": "thin border", "filled": "tinted fill", "glass": "frosted glass (blur)",
    "block": "bold 2 px border + offset shadow", "neumorphic": "soft 3D (light + dark shadows)", "mesh": "gradient mesh fill",
    "image_overlay": "big art with text over a scrim", "stacked": "stacked paper layers", "ticket": "ticket with punched edges",
}
HEADERS: dict[str, str] = {
    "search_bar": "search pill in the app bar", "large_title": "large title under the buttons", "greeting": "hello + name",
    "brand_bar": "brand colour bar with logo", "center_title": "centred small title", "big_type": "huge confident title",
    "collapsing": "large title that shrinks on scroll", "parallax_hero": "hero art that moves slower than the list",
    "transparent": "app bar over the hero art",
}
BUTTONS: dict[str, str] = {"rounded": "rounded", "pill": "fully round", "square": "sharp", "chunky": "thick border + press-down",
                           "gradient": "gradient fill + glow", "soft": "soft 3D (neumorphic)"}

# ---------------------------------------------------------------- 40 textures (original SVG, coloured by code)
def _svg(w: int, h: int, body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def _noise(freq: float, octaves: int, op: float, c: str) -> str:
    return _svg(160, 160, f'<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" '
                          f'stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 {_c01(c, 0)} 0 0 0 0 {_c01(c, 1)} 0 0 0 0 {_c01(c, 2)} '
                          f'0 0 0 {op} 0"/></filter><rect width="160" height="160" filter="url(#n)"/>')


def _c01(c: str, i: int) -> str:
    try:
        return f"{int(c[1 + 2 * i:3 + 2 * i], 16) / 255:.3f}"
    except ValueError:
        return "0"


def _tex(kind: str, c: str, a: str) -> str:
    s = f'stroke="{c}" fill="none"'
    f = f'fill="{c}"'
    T = {
        "grain": lambda: _noise(0.9, 2, 0.16, c),
        "paper": lambda: _noise(0.04, 4, 0.10, c),
        "noise_fine": lambda: _noise(1.6, 1, 0.12, c),
        "concrete": lambda: _noise(0.25, 5, 0.14, c),
        "sand": lambda: _noise(1.2, 3, 0.2, a),
        "linen": lambda: _svg(8, 8, f'<path d="M0 0h8M0 4h8" {s} stroke-opacity=".10"/><path d="M0 0v8M4 0v8" {s} stroke-opacity=".07"/>'),
        "canvas": lambda: _svg(6, 6, f'<path d="M0 3h6M3 0v6" {s} stroke-opacity=".09"/>'),
        "dots": lambda: _svg(16, 16, f'<circle cx="2" cy="2" r="1.2" {f} fill-opacity=".18"/>'),
        "dots_large": lambda: _svg(32, 32, f'<circle cx="8" cy="8" r="3" {f} fill-opacity=".12"/><circle cx="24" cy="24" r="3" {f} fill-opacity=".12"/>'),
        "grid": lambda: _svg(24, 24, f'<path d="M24 0H0v24" {s} stroke-opacity=".10"/>'),
        "grid_dense": lambda: _svg(10, 10, f'<path d="M10 0H0v10" {s} stroke-opacity=".08"/>'),
        "graph": lambda: _svg(50, 50, f'<path d="M50 0H0v50" {s} stroke-opacity=".14"/><path d="M10 0v50M20 0v50M30 0v50M40 0v50M0 10h50M0 20h50M0 30h50M0 40h50" {s} stroke-opacity=".05"/>'),
        "diagonal": lambda: _svg(12, 12, f'<path d="M-3 3l6-6M0 12L12 0M9 15l6-6" {s} stroke-opacity=".10"/>'),
        "crosshatch": lambda: _svg(12, 12, f'<path d="M0 12L12 0M0 0l12 12" {s} stroke-opacity=".08"/>'),
        "waves": lambda: _svg(40, 12, f'<path d="M0 6c10-8 10 8 20 0s10-8 20 0" {s} stroke-opacity=".14"/>'),
        "topography": lambda: _svg(120, 120, "".join(f'<ellipse cx="60" cy="60" rx="{10 + 11 * i}" ry="{7 + 8 * i}" transform="rotate({i * 9} 60 60)" {s} stroke-opacity=".09"/>' for i in range(5))),
        "chevron": lambda: _svg(24, 12, f'<path d="M0 12l12-10 12 10" {s} stroke-opacity=".12"/>'),
        "zigzag": lambda: _svg(20, 10, f'<path d="M0 8l5-6 5 6 5-6 5 6" {s} stroke-opacity=".14"/>'),
        "herringbone": lambda: _svg(16, 16, f'<path d="M0 4l8 4 8-4M0 12l8 4 8-4" {s} stroke-opacity=".10"/>'),
        "hex": lambda: _svg(28, 49, f'<path d="M14 0l14 8v16L14 32 0 24V8zM14 32v17" {s} stroke-opacity=".09"/>'),
        "triangles": lambda: _svg(24, 21, f'<path d="M0 21L12 0l12 21z" {s} stroke-opacity=".08"/>'),
        "circles": lambda: _svg(30, 30, f'<circle cx="15" cy="15" r="11" {s} stroke-opacity=".08"/>'),
        "rings": lambda: _svg(60, 60, f'<circle cx="0" cy="0" r="20" {s} stroke-opacity=".08"/><circle cx="60" cy="60" r="20" {s} stroke-opacity=".08"/><circle cx="30" cy="30" r="12" {s} stroke-opacity=".06"/>'),
        "plus": lambda: _svg(20, 20, f'<path d="M10 6v8M6 10h8" {s} stroke-opacity=".14"/>'),
        "stars": lambda: _svg(40, 40, f'<path d="M10 6l1.2 2.6 2.8.4-2 2 .5 2.8L10 12.5 7.5 13.8l.5-2.8-2-2 2.8-.4zM30 26l.8 1.7 1.8.3-1.3 1.3.3 1.8L30 30.2l-1.6.9.3-1.8-1.3-1.3 1.8-.3z" {f} fill-opacity=".14"/>'),
        "confetti": lambda: _svg(60, 60, f'<rect x="6" y="8" width="5" height="2" rx="1" transform="rotate(30 8 9)" fill="{a}" fill-opacity=".35"/><rect x="38" y="16" width="5" height="2" rx="1" transform="rotate(-20 40 17)" {f} fill-opacity=".25"/><circle cx="20" cy="42" r="1.6" fill="{a}" fill-opacity=".35"/><rect x="46" y="44" width="4" height="2" rx="1" transform="rotate(60 48 45)" {f} fill-opacity=".25"/>'),
        "terrazzo": lambda: _svg(90, 90, f'<path d="M12 10l9 3-4 7-8-2z" fill="{a}" fill-opacity=".22"/><path d="M58 18l7 2-1 6-8-1z" {f} fill-opacity=".14"/><path d="M30 52l10-1 2 7-9 3z" fill="{a}" fill-opacity=".16"/><path d="M70 66l6 5-5 5-5-4z" {f} fill-opacity=".18"/><circle cx="44" cy="30" r="2" {f} fill-opacity=".2"/><circle cx="14" cy="74" r="2.5" fill="{a}" fill-opacity=".2"/>'),
        "marble": lambda: _svg(200, 200, f'<filter id="m"><feTurbulence type="turbulence" baseFrequency="0.012 0.04" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 {_c01(c, 0)} 0 0 0 0 {_c01(c, 1)} 0 0 0 0 {_c01(c, 2)} 0 0 0 -2.2 1.1"/></filter><rect width="200" height="200" filter="url(#m)" opacity=".18"/>'),
        "wood": lambda: _svg(200, 40, "".join(f'<path d="M0 {4 + 6 * i}c50 {(-1) ** i * 3} 120 {(-1) ** i * -4} 200 0" {s} stroke-opacity=".07"/>' for i in range(6))),
        "bandhani": lambda: _svg(24, 24, f'<circle cx="6" cy="6" r="2.2" {s} stroke-opacity=".22"/><circle cx="6" cy="6" r=".7" {f} fill-opacity=".25"/><circle cx="18" cy="18" r="2.2" {s} stroke-opacity=".22"/><circle cx="18" cy="18" r=".7" {f} fill-opacity=".25"/>'),
        "ikat": lambda: _svg(40, 40, f'<path d="M20 4l8 16-8 16-8-16z" fill="{a}" fill-opacity=".12"/><path d="M20 10l5 10-5 10-5-10z" {f} fill-opacity=".10"/><path d="M0 20h6M34 20h6" {s} stroke-opacity=".15" stroke-dasharray="2 2"/>'),
        "block_print": lambda: _svg(48, 48, f'<g {s} stroke-opacity=".16"><circle cx="24" cy="24" r="8"/><path d="M24 10v6M24 32v6M10 24h6M32 24h6"/></g><g fill="{a}" fill-opacity=".14"><circle cx="24" cy="24" r="3"/><circle cx="4" cy="4" r="2"/><circle cx="44" cy="44" r="2"/></g>'),
        "kantha": lambda: _svg(30, 12, f'<path d="M2 6h6M12 6h6M22 6h6" {s} stroke-opacity=".22" stroke-linecap="round"/>'),
        "mandala": lambda: _svg(120, 120, "".join(f'<ellipse cx="60" cy="38" rx="6" ry="20" transform="rotate({i * 30} 60 60)" {s} stroke-opacity=".08"/>' for i in range(12)) + f'<circle cx="60" cy="60" r="8" {s} stroke-opacity=".12"/>'),
        "rangoli": lambda: _svg(80, 80, "".join(f'<circle cx="{40 + 18 * math.cos(i * math.pi / 4):.1f}" cy="{40 + 18 * math.sin(i * math.pi / 4):.1f}" r="5" fill="{a if i % 2 else c}" fill-opacity=".14"/>' for i in range(8)) + f'<circle cx="40" cy="40" r="6" {s} stroke-opacity=".18"/>'),
        "paisley": lambda: _svg(56, 56, f'<path d="M20 44c-10-4-12-20 0-26 10-5 20 4 14 14-4 6-12 4-12-2" {s} stroke-opacity=".14"/><circle cx="24" cy="30" r="2" fill="{a}" fill-opacity=".18"/>'),
        "jaali": lambda: _svg(32, 32, f'<path d="M16 0c0 9 7 16 16 16-9 0-16 7-16 16 0-9-7-16-16-16 9 0 16-7 16-16z" {s} stroke-opacity=".12"/>'),
        "leaf": lambda: _svg(50, 50, f'<path d="M10 40C10 20 22 10 40 10c0 18-10 30-30 30zM10 40l18-18" {s} stroke-opacity=".12"/>'),
        "petals": lambda: _svg(40, 40, "".join(f'<ellipse cx="20" cy="12" rx="4" ry="8" transform="rotate({i * 72} 20 20)" fill="{a}" fill-opacity=".09"/>' for i in range(5))),
        "sparkle": lambda: _svg(50, 50, f'<path d="M12 6v8M8 10h8M38 32v6M35 35h6" {s} stroke-opacity=".2" stroke-linecap="round"/><circle cx="30" cy="12" r="1" {f} fill-opacity=".3"/>'),
    }
    return T[kind]()


TEXTURES = ["grain", "paper", "noise_fine", "concrete", "sand", "linen", "canvas", "dots", "dots_large", "grid", "grid_dense", "graph",
            "diagonal", "crosshatch", "waves", "topography", "chevron", "zigzag", "herringbone", "hex", "triangles", "circles", "rings",
            "plus", "stars", "confetti", "terrazzo", "marble", "wood", "bandhani", "ikat", "block_print", "kantha", "mandala",
            "rangoli", "paisley", "jaali", "leaf", "petals", "sparkle"]


def textures_css(tk: dict[str, Any], alt: bool = False) -> str:
    """.tx-<name> classes (any element) + body.tex-<name> (behind every screen), coloured from her ink / accent tokens;
    alt=True writes the same for the other colour mode (body.mode-alt)."""
    c, a = tk.get("ink", "#222222"), tk.get("accent", "#888888")
    pre = "body.mode-alt " if alt else ""
    out = []
    for t in TEXTURES:
        data = quote(_tex(t, c, a), safe="")
        sel = f"{pre}.tx-{t},body{'.mode-alt' if alt else ''}.tex-{t} .scr:not(.splash)"
        out.append(f'{sel}{{background-image:url("data:image/svg+xml,{data}");background-repeat:repeat}}')
    return "\n".join(out)


# ---------------------------------------------------------------- 100 motion presets (web key the prototype plays + native hint)
_TRANS = [("push", "iOS push: new screen slides in from the right", "slideInHorizontally", ".navigationTransition(.automatic)"),
          ("fade_through", "Material fade-through (fade + 92% scale)", "fadeIn + scaleIn", ".transition(.opacity)"),
          ("axis_x", "shared X axis (forward / back slide + fade)", "MaterialSharedAxis X", ".transition(.move(edge:))"),
          ("axis_y", "shared Y axis (vertical step flows)", "MaterialSharedAxis Y", ".transition(.move(edge: .bottom))"),
          ("axis_z", "shared Z axis (parent -> child zoom)", "MaterialSharedAxis Z", ".transition(.scale)"),
          ("container", "container transform: the tapped card grows into the next screen", "SharedTransitionLayout / sharedBounds", "matchedGeometryEffect / .zoom"),
          ("sheet", "slides up as a sheet", "ModalBottomSheet", ".sheet"),
          ("zoom", "zooms in from the centre", "scaleIn", ".transition(.scale)"),
          ("cube", "3D cube rotation between screens", "graphicsLayer rotationY", "rotation3DEffect"),
          ("flip", "3D card flip between screens", "graphicsLayer rotationY 180", "rotation3DEffect 180"),
          ("curl", "page turn / curl (onboarding, catalogues)", "custom page curl shader", "UIPageViewController .pageCurl"),
          ("reveal", "circular reveal from the tap point", "custom clip reveal", "mask circle animation")]
_MICRO = [("stagger", "list / grid items rise in one by one"), ("pop", "springs in"), ("float", "floats slowly"), ("pulse", "gentle pulse"),
          ("count", "number counts up to her value"), ("tilt", "3D tilt following the finger"), ("flip", "card flips to show the back"),
          ("spin3d", "3D object turns"), ("parallax", "moves slower than the scroll"), ("reveal", "appears when scrolled into view"),
          ("marquee", "strip scrolls slowly"), ("shimmer", "skeleton shimmer"), ("typewriter", "text types itself"),
          ("wiggle", "wiggles once"), ("bounce", "bounces once"), ("glow", "soft glow"), ("ripple", "Android ink ripple"),
          ("morph", "blob shape morphs"), ("carousel3d", "3D carousel"), ("confetti", "confetti burst"), ("draw", "SVG line draws itself"),
          ("progress", "bar / ring fills"), ("gradient", "gradient slowly shifts"), ("breathe", "breathing scale"), ("shake", "shakes (error)"),
          ("slide_left", "slides in from the left"), ("slide_right", "slides in from the right"), ("slide_up", "slides up"),
          ("slide_down", "drops down"), ("zoom_in", "zooms in"), ("blur_in", "sharpens from blur"), ("rotate_in", "rotates in"),
          ("swing", "swings like a toran"), ("heartbeat", "heartbeat"), ("jelly", "jelly squash"), ("press", "shrinks while pressed"),
          ("badge", "badge pops"), ("check", "check mark draws"), ("sparkle", "sparkles"), ("orbit", "small dots orbit"),
          ("wave", "wave motion"), ("tick", "clock tick"), ("ken_burns", "slow pan + zoom on art"), ("unfold", "unfolds like paper"),
          ("stack", "cards stack / unstack"), ("swipe_hint", "hints that the card can be swiped"), ("drag", "drag to reorder (prototype: hint)"),
          ("pull", "pull to refresh"), ("expand", "accordion expands smoothly"), ("tab_slide", "tab indicator slides"),
          ("fab_morph", "FAB morphs into a sheet"), ("hero_image", "list art grows into the detail header"), ("qr_sweep", "QR light sweep"),
          ("date_slide", "date strip slides to today"), ("toast", "snackbar slides up"), ("chip", "chip fills on select"),
          ("stepper", "number bumps on +/-"), ("success", "success icon scales with a bounce"), ("lottie_like", "vector animation loop"),
          ("map_pin", "map pin drops and bounces"), ("route_draw", "route line draws on the map"), ("chart_grow", "chart bars grow"),
          ("pie_fill", "pie / donut fills"), ("number_roll", "digits roll like a meter"), ("typing", "chat typing dots"),
          ("message_in", "chat bubble slides in"), ("swipe_card", "card swipes away"), ("long_press", "long-press menu blooms"),
          ("haptic_like", "tiny press shake (haptic in the real app)"), ("pin_entry", "PIN dots fill"), ("biometric", "fingerprint pulse"),
          ("upload", "upload progress fills"), ("download", "download arrow drops"), ("sync", "sync arrows spin"),
          ("offline", "offline banner slides"), ("rating", "stars fill one by one"), ("timer", "countdown ring"),
          ("weather", "subtle sun / cloud motion"), ("festive", "diya flicker"), ("rangoli_draw", "rangoli draws itself"),
          ("map_layers", "map layers fade in"), ("gis_measure", "measure line stretches"), ("tilt_device", "content tilts with the phone"),
          ("depth", "layers separate in depth"), ("glass_shine", "light sweeps across glass"),
          ("scroll_snap", "cards snap while swiping"), ("magnetic", "button leans toward the finger"), ("split_text", "title letters rise one by one")]
MOTION: dict[str, dict[str, str]] = {}
for _k, _d, _a, _i in _TRANS:
    MOTION[f"t_{_k}"] = {"kind": "transition", "web": _k, "desc": _d, "android": _a, "ios": _i}
for _k, _d in _MICRO:
    MOTION[f"m_{_k}"] = {"kind": "micro", "web": _k, "desc": _d, "android": "Compose animate*AsState / Animatable / InfiniteTransition",
                         "ios": "withAnimation / PhaseAnimator / KeyframeAnimator"}
PLAYED = {"stagger", "pop", "float", "pulse", "count", "tilt", "flip", "spin3d", "parallax", "reveal", "marquee", "shimmer",
          "typewriter", "wiggle", "bounce", "glow", "ripple", "morph", "carousel3d", "confetti", "draw", "progress", "gradient",
          "breathe", "shake", "slide_left", "slide_right", "slide_up", "slide_down", "zoom_in", "blur_in", "rotate_in", "swing",
          "heartbeat", "jelly", "press", "badge", "check", "sparkle", "ken_burns", "chart_grow", "typing", "map_pin",
          "route_draw", "glass_shine", "success", "number_roll"}

THREE_D: dict[str, str] = {
    "tilt": "card tilts in 3D under the finger: <div class='card' data-m='tilt'>",
    "flip": "flip card: <div class='flip' data-m='flip'><div class='flip-front'>..</div><div class='flip-back'>..</div></div>",
    "carousel3d": "3D carousel: <div class='carousel3d' data-m='carousel3d'><div>..</div> x 3-8 </div>",
    "object": "3D object viewer: <div class='obj3d' data-shape='box|cylinder|sphere|torus|cake|bottle|phone|gem' data-spin></div>",
    "depth": "layers at different depths: data-depth='1..3' inside a .depth-stage",
}


def counts() -> dict[str, int]:
    return {"nav": len(NAV), "fab": len(FAB), "cards": len(CARDS), "headers": len(HEADERS), "buttons": len(BUTTONS),
            "textures": len(TEXTURES), "motion": len(MOTION), "motion_played": len(PLAYED) + len(_TRANS), "three_d": len(THREE_D)}


def check() -> list[str]:
    p = []
    if len(NAV) != 12 or len(FAB) != 8 or len(CARDS) != 10 or len(HEADERS) != 9 or len(BUTTONS) != 6:
        p.append("structure counts")
    if len(TEXTURES) != 40:
        p.append(f"{len(TEXTURES)} textures")
    if len(MOTION) != 100:
        p.append(f"{len(MOTION)} motion presets")
    for t in TEXTURES:
        try:
            _tex(t, "#222222", "#cc6600")
        except Exception as e:  # pragma: no cover - a broken generator
            p.append(f"texture {t}: {e}")
    return p
