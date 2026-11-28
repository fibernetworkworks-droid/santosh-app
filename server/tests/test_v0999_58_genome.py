"""v0.999.59 D2 THE DESIGN GENOME (docs/WEB_DESIGN_ENGINE_PLAN.md phase D2): every app gets its own design as data -
an OKLCH palette generated from one brand hue (light AND dark, every text pair checked), bundled fonts by rule (incl.
Indian scripts, no over-used faces), shape / density / motion / imagery genes - written as tokens.css + the fonts +
DESIGN.md (import / export). Done-line: 100 random genomes all pass contrast + render (`kit.genome_check`)."""
from __future__ import annotations

import json
import os

import pytest

from app.appengine import genome as GN
from app.appengine import rules as RL
from app.appengine import tokens as TK
from tests.test_v0814_app_engine import _box, _refused, _tool, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_oklch_round_trip_and_gamut():
    for hx in ("#4f46e5", "#0f766e", "#c2410c", "#111111", "#fafafa"):
        L, C, h = GN.hex_oklch(hx)
        back = GN.oklch_hex(L, C, h)
        assert max(abs(int(back[i:i + 2], 16) - int(hx[i:i + 2], 16)) for i in (1, 3, 5)) <= 1, (hx, back)
    out = GN.oklch_hex(0.7, 0.4, 145)                     # far outside sRGB: chroma comes down, never a broken colour
    assert TK.HEX.match(out)


def test_one_hundred_random_genomes_all_pass_contrast_and_differ():
    gens = [GN.random_genome(i) for i in range(100)]
    for i, g in enumerate(gens):
        assert GN.audit(g) == [], (i, GN.audit(g))
        for m in GN.MODES:
            p = GN.palette(g["colour"], m)
            assert TK.contrast(p["ink"], p["bg"]) >= 7.0 and TK.contrast(p["muted"], p["surface"]) >= 4.5
            assert TK.contrast(p["primary_ink"], p["primary"]) >= 4.5 and TK.contrast(p["primary"], p["bg"]) >= 4.5
    assert len({GN.palette(g["colour"], g["colour"]["mode"])["primary"] for g in gens}) >= 90
    assert len({g["type"]["display"] for g in gens}) >= 12
    assert len({g["direction"]["seed"] for g in gens}) == len(GN.DIRECTIONS)
    assert {g["colour"]["mode"] for g in gens} == {"light", "dark"}
    assert GN.random_genome(7) == GN.random_genome(7)     # repeatable


def test_fonts_bundled_never_overused_and_indian_script_covered():
    for i in range(60):
        g = GN.random_genome(i)
        t = g["type"]
        for f in (t["display"], t["text"], t["deva"]):
            assert GN.font_files(f), f
            assert not GN.FONTS[f].get("overused"), f
        assert GN.has_deva(t["deva"]), t
        assert any("devanagari" in fn for _, _, _, fn in GN.fonts_used(g))
    css = GN.css(GN.random_genome(1))
    assert "@font-face" in css and "url(./fonts/" in css and "unicode-range" in css and "http" not in css


def test_her_words_and_colour_pin_the_genes():
    g = GN.for_brief("Gold Leaf", "a luxury jewellery boutique, dark and premium")
    assert g["direction"]["seed"] == "luxury_dark" and g["colour"]["mode"] == "dark"
    assert GN.for_brief("Gold Leaf", "a luxury jewellery boutique, dark and premium") == g   # same words, same design
    assert GN.for_brief("Tiny Tots", "a play school for kids")["direction"]["seed"] == "playful_bright"
    teal = GN.for_brief("Neel", "a teal and white yoga studio")
    assert abs(teal["colour"]["hue"] - 190) < 1
    # her exact brand colour is kept when it reads; else the nearest readable shade of it
    keep = GN.generate(seed=1, pin="#0f5132", mode="light")
    assert GN.palette(keep["colour"], "light")["primary"] == "#0f5132"
    pale = GN.generate(seed=1, pin="#ffd60a", mode="light")
    p = GN.palette(pale["colour"], "light")["primary"]
    assert p != "#ffd60a" and TK.contrast(p, GN.palette(pale["colour"], "light")["bg"]) >= 4.5
    assert abs(GN.hex_oklch(p)[2] - GN.hex_oklch("#ffd60a")[2]) < 20       # still her yellow-gold hue


def test_tokens_css_carries_every_gene_and_both_modes():
    g = GN.generate(seed="t", direction="minimal_swiss", mode="light")
    css = GN.css(g)
    for k in ("--color-*: initial;", "--color-primary:", "--radius-card:", "--shadow-card:", "--font-head:",
              "--font-body:", "--spacing:", "--text-5xl:", "--motion-reveal:", '[data-theme="dark"]'):
        assert k in css, k
    assert RL.drift("src/styles/tokens.css", css) == []
    root = GN.Path(__file__).resolve().parents[1]
    idx = (root / "app/appengine/template/src/index.css").read_text()
    assert "var(--motion-reveal" in idx and "var(--motion-distance" in idx
    assert "design_new" in (root / "app/appengine/template/AGENTS.md").read_text()
    ops = (root.parent / ".github/workflows/vps-ops.yml").read_text()
    assert "appengine_genomes)" in ops and "python -m app.appengine genomes 100" in ops


def test_design_md_round_trips_and_imports_another_tools_file():
    g = GN.generate(seed="md", direction="festive_traditional", name="Asha weds Ravi")
    md = GN.design_md(g)
    assert md.startswith("---\n") and "colors:" in md and "typography:" in md and "hoola:" in md
    assert "## Colors" in md and "## Imagery" in md   # v0.999.316 the spec's own section names
    assert GN.from_design_md(md) == g
    other = """---
name: Acme
colors:
  primary: "#e11d48"
  bg: "#0b0b0f"
typography:
  display: {fontFamily: Playfair Display}
  body: {fontFamily: DM Sans}
rounded:
  card: 8px
---
# Acme
Some rules.
"""
    h = GN.from_design_md(other)
    assert h["colour"]["mode"] == "dark" and h["type"]["display"] == "Playfair Display" and h["type"]["text"] == "DM Sans"
    assert GN.audit(h) == []
    with pytest.raises(ValueError):
        GN.from_design_md("no tokens here")


def test_a_new_app_gets_its_own_design_and_the_tool_changes_it(ae_env):
    a = _tool(action="create", name="Kaveri Foods", brief="a family restaurant menu and table booking")
    aid = a["id"]
    from app.appengine import service as AE
    r = AE._load(T, aid)
    d = AE.src_dir(r)
    assert (d / "DESIGN.md").exists()
    assert not list(d.rglob("*.woff2"))           # fonts ride the build copy only: her files stay text
    for f in AE._files(r):
        f.read_text("utf-8")
    css = (d / "src/styles/tokens.css").read_text()
    assert "@font-face" in css and "--motion-reveal" in css
    v = AE.view(r)
    assert v["design"]["seed_direction"] == "warm_local" and v["design"]["checks"] == "every colour pair readable"
    got = _tool(action="design", app=aid)
    assert got["design"]["direction"] and "hoola:" in got["design_md"]
    # locked files say how to change them
    assert "design_new" in _refused(action="write", app=aid, path="DESIGN.md", code="x")
    assert "design_new" in _refused(action="write", app=aid, path="src/styles/tokens.css", code="x")
    # a new design from her colour + feel
    nd = _tool(action="design_new", app=aid, colour="#7c2d12", direction="editorial_calm", mode="light")
    assert nd["design"]["primary"] == "#7c2d12" and nd["design"]["seed_direction"] == "editorial_calm"
    assert "#7c2d12" in (d / "src/styles/tokens.css").read_text()
    # change one gene
    one = _tool(action="design_new", app=aid, genes={"shape": {"radius": 2, "shadow": "none"}, "motion": "calm"})
    assert one["design"]["radius"] == 2 and one["design"]["motion"] == "calm" and one["design"]["primary"] == "#7c2d12"
    # import a DESIGN.md
    imp = _tool(action="design_import", app=aid, design_md=GN.design_md(GN.generate(seed="x", direction="tech_gradient", mode="dark")))
    assert imp["design"]["seed_direction"] == "tech_gradient" and imp["design"]["mode"] == "dark"
    # a named palette = the classic tokens (the genome steps aside, files tidied)
    _tool(action="tokens", app=aid, palette="fresh")
    assert not (d / "DESIGN.md").exists()
    assert "@font-face" not in (d / "src/styles/tokens.css").read_text()


def test_a_genome_app_builds_in_the_box_with_its_fonts(ae_env):
    _box()
    aid = _tool(action="create", name="Gold Leaf", brief="a luxury jewellery boutique, dark and premium")["id"]
    res = _tool(action="build", app=aid)
    assert res.get("built"), res.get("say")
    from app.appengine import service as AE
    r = AE._load(T, aid)
    dist = AE.ver_dir(r, r.version) / "dist"
    assert list(dist.rglob("*.woff2")), "the genome's fonts are bundled into the build"
    css = "".join(p.read_text() for p in dist.rglob("*.css"))
    assert "--motion-reveal" in css and "@font-face" in css


@pytest.mark.skipif(bool(os.environ.get("HOOLA_SKIP_KIT_RENDER")), reason="render check switched off")
def test_genomes_render_every_block():
    from app.appengine import kit as KIT
    from app.appengine import runner as RN
    if not RN.available()["ok"]:
        pytest.skip("no App Engine build box here")
    try:
        import playwright  # noqa: F401
    except ImportError:
        pytest.skip("no Playwright here")
    n = int(os.environ.get("HOOLA_GENOME_RENDER_N", "12"))
    r = KIT.genome_check(n)
    assert r["verdict"] == "PASS", json.dumps(r)[:3000]
    assert r["rendered"] == n and r["fonts_bundled"] > 0
