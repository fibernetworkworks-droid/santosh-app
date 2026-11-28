"""v0.999.51 D1 THE KIT (docs/WEB_DESIGN_ENGINE_PLAN.md phase D1): the full shadcn-style kit + 39 React section blocks
+ Emergent's taste rules in code + the contrast floor. Done-line: every block renders in 3 genomes with 0 rule
breaks - proved for real by `kit.render_check()` when the build box (or the local runner) and Chromium are here."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from app.appengine import image as IMG
from app.appengine import kit as KIT
from app.appengine import rules as RL
from app.appengine import tokens as TK

ROOT = Path(__file__).resolve().parents[2]


def test_image_rev_2_carries_the_whole_kit():
    # v0.999.326 the image moved to rev 3 (the awesome-react libraries + tests in the box); the kit it carries is unchanged
    assert IMG.IMAGE_REV == "3" and 'hoola.appengine.rev="3"' in IMG.DOCKERFILE_TEXT
    for p in ("@radix-ui/react-select", "@radix-ui/react-accordion", "@radix-ui/react-avatar", "cmdk", "vaul",
              "input-otp", "react-day-picker", "embla-carousel-react", "@radix-ui/react-navigation-menu"):
        assert p in IMG.CORE, p
    assert set(IMG.EXTRA) == {"motion"}                 # the kit animates with CSS only; motion stays her add
    lock = json.loads(IMG.LOCK.read_text())["packages"]
    root = lock[""]
    for name, v in {**IMG.CORE, **{k: x[0] for k, x in IMG.EXTRA.items()}, **IMG.DEV}.items():
        assert lock[f"node_modules/{name}"]["version"] == v, name
        assert (root.get("dependencies", {}) | root.get("devDependencies", {}))[name] == v, name


@pytest.mark.parametrize("code,word", [
    ('<div className="transition-all duration-200" />', "transition-all"),
    ('.x { transition: all 0.2s }', "transition-all"),
    ("<select value={x}>", "Select"),
    ('<Input id="d" type="date" />', "DatePicker"),
    ('<input type="time" />', "DatePicker"),
    ('alert("saved")', "toast"),
    ("if (window.confirm('sure?')) go();", "AlertDialog"),
    ("<span>★ 4.8</span>", "lucide-react"),
    ("<p>\U0001F680 Launch</p>", "lucide-react"),
    ('<Button className="bg-linear-to-r from-primary to-accent">Go</Button>', "gradient on a button"),
])
def test_taste_rules_refuse_with_the_kit_part_to_use(code, word):
    path = "src/x.css" if code.startswith(".x") else "src/pages/X.tsx"
    found = " ".join(x["found"] for x in RL.check_file(path, code, set(IMG.CORE)))
    assert word in found, found


@pytest.mark.parametrize("code", [
    '<div className="transition-colors hover:bg-surface" />',
    "const confirm = useConfirm(); dialog.confirm();",
    '<p>₹499 per month → Book now</p>',
    '<input type="radio" value="a" />',
    '<div className="bg-linear-to-b from-bg to-surface" />',
])
def test_taste_rules_leave_good_code_alone(code):
    assert RL.taste("src/pages/X.tsx", code) == []


def test_at_most_three_gradients_a_file():
    four = "\n".join(f'<div className="bg-linear-to-r from-primary to-accent" />' for _ in range(4))
    assert any("gradients in one file" in x["found"] for x in RL.taste("src/pages/X.tsx", four))
    three = "\n".join(f'<div className="bg-linear-to-r from-primary to-accent" />' for _ in range(3))
    assert RL.taste("src/pages/X.tsx", three) == []


def test_contrast_floor_every_palette_and_the_derived_grey():
    for p in TK.PALETTES:
        t = TK.resolve({}, p)
        assert TK.audit(t) == [], (p, TK.audit(t))
        assert TK.contrast(t["muted"], t["surface"]) >= 4.5
    bad = TK.resolve({"bg": "#ffffff", "ink": "#bbbbbb", "primary": "#fafafa"}, "calm")
    words = " ".join(TK.audit(bad))
    assert "ink on bg" in words and "primary on bg" in words
    for g in KIT.GENOMES:
        assert TK.audit(KIT.genome_tokens(g)) == [], g


def test_every_section_type_has_a_block_with_variants_and_its_data_block():
    ids = KIT.block_ids()
    assert len(ids) == 39
    assert KIT.missing_blocks() == []
    for b in ids:
        code = (KIT.BLOCKS_DIR / KIT.file_of(b)).read_text()
        assert re.search(r"export const variants\s*=\s*\[", code), b
        assert "export default function" in code, b
        assert f'block="{b}"' in code, b
        assert "export const sample" in code or "const sample" in code, b
    idx = (KIT.BLOCKS_DIR / "index.ts").read_text()
    for b in ids:
        assert f'"{b}"' in idx, b


def test_the_kit_holds_the_full_ui_set():
    parts = set(KIT.ui_parts())
    need = {"accordion", "alert", "alert-dialog", "avatar", "badge", "breadcrumb", "button", "calendar", "card",
            "carousel", "chart", "checkbox", "collapsible", "command", "context-menu", "date-picker", "dialog",
            "drawer", "dropdown-menu", "empty", "form", "hover-card", "input", "input-otp", "label", "menubar",
            "navigation-menu", "pagination", "popover", "progress", "radio-group", "scroll-area", "select",
            "separator", "sheet", "skeleton", "slider", "sonner", "spinner", "switch", "table", "tabs", "textarea",
            "toggle", "toggle-group", "tooltip"}
    assert need <= parts, sorted(need - parts)
    # older apps keep working: the names they import are still there
    assert "tone" in (KIT.UI / "badge.tsx").read_text()
    btn = (KIT.UI / "button.tsx").read_text()
    for v in ("primary", "secondary", "ghost", "danger", "link", "outline", "accent"):
        assert f"{v}:" in btn, v


def test_zero_rule_breaks_in_every_kit_file():
    probs = KIT.rule_check()
    assert probs == [], RL.say(probs, 20)


def test_kit_motion_is_css_and_respects_reduced_motion():
    css = (KIT.TEMPLATE / "src" / "index.css").read_text()
    for a in ("--animate-fade-up", "--animate-marquee", "--animate-accordion-down", "--animate-slide-in-right"):
        assert a in css
    assert "prefers-reduced-motion: reduce" in css
    for p in KIT.kit_files():
        assert "from \"motion" not in p.read_text() and "framer-motion" not in p.read_text(), p.name


def test_gallery_lists_every_block_and_the_model_hears_of_the_kit(tmp_path):
    page = KIT.gallery_page()
    for b in KIT.block_ids():
        assert f'"@/components/blocks/{KIT.file_of(b)[:-4]}"' in page
    d = KIT.gallery_dir("night", tmp_path / "app")
    assert "--color-bg: #0d0f14" in (d / "src" / "styles" / "tokens.css").read_text()
    assert "hero" in KIT.prompt_line() and "screen-dashboard" in KIT.prompt_line()
    agents = (KIT.TEMPLATE / "AGENTS.md").read_text()
    assert "src/components/blocks/" in agents and "transition-all" in agents
    ops = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "appengine_kit)" in ops and "python -m app.appengine kit" in ops


def _can_render() -> str:
    from app.appengine import runner as RN
    if not RN.available()["ok"]:
        return "no App Engine build box here"
    try:
        import playwright  # noqa: F401
    except ImportError:
        return "no Playwright here"
    return ""


@pytest.mark.skipif(bool(os.environ.get("HOOLA_SKIP_KIT_RENDER")), reason="render check switched off")
def test_every_block_renders_in_three_genomes_with_zero_rule_breaks(tmp_path):
    why = _can_render()
    if why:
        pytest.skip(why)
    r = KIT.render_check(shots=str(tmp_path))
    msgs = [p for g in r["genomes"] for p in g["problems"]]
    assert r["verdict"] == "PASS", msgs[:30]
    assert r["blocks"] == 39 and r["rules"] == 0
    for g in r["genomes"]:
        for w in ("1280", "390"):
            assert g["widths"][w]["items"] >= 39 * 2, g["genome"]
