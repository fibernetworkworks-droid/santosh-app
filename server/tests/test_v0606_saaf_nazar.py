"""v0.606 SAAF NAZAR - the "AI look" check on every built website (ideas from pbakaus/impeccable, Apache-2.0, own code).

1. CALIBRATED: every rule fires on its own planted fault, and a clean, well-made page gives ZERO findings (a checker
   that cries wolf on good work is worse than none).
2. It never blocks: the gate rows are warn / pass only, and a built site still launches.
3. The brief wins: her words (neon glow, marquee...) and her own design (look 1 / colours she set) switch the matching
   tells off.
4. Page modes: an icon tile on an account / admin page is fine; numbered steps in a guide are fine.
5. The builder's own defaults no longer ask for the tells: no style default uses an overused font, the section writer
   is not taught an eyebrow class and carries the craft floor, the design kit has no eyebrow part, no style defaults
   to a marquee or gradient glows.
6. The per-section tells go into the first fix round (once), mapped to the section keys the fixer rewrites."""
import json
from pathlib import Path

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.606.0"


CLEAN_CSS = (":root{--c-bg:#ffffff}"
             "#s-home-hero{padding:96px 20px 64px}#s-home-hero h1{font-size:3rem;line-height:1.1;letter-spacing:-0.02em}"
             "#s-home-hero p{font-size:1.125rem;line-height:1.6;max-width:68ch}"
             "#s-home-about .card{border:1px solid var(--c-line);border-radius:12px;padding:24px}"
             "#s-home-about .card:hover{box-shadow:0 8px 24px rgba(0,0,0,.08);transition:transform .3s cubic-bezier(.22,1,.36,1)}"
             ".k-btn{background:var(--c-primary);border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.12)}")
CLEAN_HTML = """<html lang="en"><body><main>
<section id="s-home-hero" class="hs"><h1>Sharma Sweets, Akola since 1985</h1><p>Fresh kaju katli and pedha, made every
morning in our kitchen on Station Road. Order by phone or walk in.</p><a class="btn btn-primary" href="tel:+919876543210">Call</a></section>
<section id="s-home-about" class="hs"><h2>What we make</h2><div class="grid g3">
<article class="card"><h3>Kaju katli</h3><p>Cashew and sugar, nothing else.</p></article>
<article class="card"><h3>Pedha</h3><p>Slow-cooked milk with cardamom.</p></article>
<article class="card"><h3>Besan laddu</h3><p>Roasted gram flour and ghee.</p></article></div>
<img data-hoola-img="kitchen" alt="Our kitchen"></section></main></body></html>"""


def _site(tmp: Path, html: dict[str, str], css: str) -> Path:
    (tmp / "assets").mkdir(parents=True, exist_ok=True)
    (tmp / "assets" / "site.css").write_text(css)
    for rel, h in html.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(h)
    return tmp


def _ctx(**kw):
    return {"tokens": {"head": "Eczar", "body": "Hind", "bg": "#FFFFFF"}, "facts": {}, "brief": "", **kw}


def test_a_well_made_page_gives_zero_findings(tmp_path):
    from app.site import look as LK
    out = _site(tmp_path, {"index.html": CLEAN_HTML}, CLEAN_CSS)
    res = LK.scan(out, _ctx())
    assert res["findings"] == [], res["findings"]
    rows = LK.rows(res)
    assert len(rows) == 1 and rows[0]["state"] == "pass" and "no reflex tells" in rows[0]["check"]


PLANTED_CSS = (
    "#s-home-hero h1{background:linear-gradient(90deg,#7c3aed,#06b6d4);-webkit-background-clip:text;background-clip:text;"
    "color:transparent;font-style:italic;letter-spacing:-0.08em}"
    "#s-home-hero{background:radial-gradient(circle at 50% 0,#f97316 0,transparent 60%)}"
    "#s-home-feat .card{border-left:4px solid #e11d48;box-shadow:0 0 24px #22d3ee}"
    "#s-home-feat .tile{transition:transform .5s cubic-bezier(.68,-0.6,.32,1.6)}"
    "#s-home-stats .box{box-shadow:6px 6px 0 #111}"
    "#s-home-stats{background-image:repeating-linear-gradient(45deg,#eee 0 2px,transparent 2px 8px)}"
    "#s-home-grid{background-image:linear-gradient(#ddd 1px,transparent 1px),linear-gradient(90deg,#ddd 1px,transparent 1px);"
    "background-size:24px 24px}"
    "#s-home-copy p{text-align:justify;line-height:1.1;font-size:11px;letter-spacing:.12em}"
    "#s-home-copy p.shout{text-transform:uppercase}")
TILE = '<div class="tile"><i data-icon="star"></i></div><h3>{}</h3><p>x</p>'
PLANTED_HTML = """<html><body>
<section id="s-home-hero"><span class="eyebrow">NEW IN AKOLA</span><h1>We streamline sweets with world-class, seamless taste</h1>
<img src="" alt="x"></section>
<section id="s-home-feat"><span>01</span><h2>Features</h2><div class="card"><div class="card">inner</div></div>
""" + "".join(TILE.format(n) for n in ("A", "B", "C")) + """
<marquee>offer</marquee><h4>\U0001F525 Hot</h4><ul><li>✨ one</li><li>\U0001F680 two</li></ul></section>
<section id="s-home-stats"><span>02</span><h2>Stats</h2><p>Compliance is not security theater.</p></section>
<section id="s-home-grid"><span>03</span><h2>Grid</h2></section>
<section id="s-home-copy"><h2>Copy</h2><h4>skipped</h4><p class="shout">all caps</p></section>
</body></html>"""


def test_every_rule_fires_on_its_planted_fault(tmp_path):
    from app.site import look as LK
    out = _site(tmp_path, {"index.html": PLANTED_HTML}, PLANTED_CSS)
    res = LK.scan(out, _ctx(tokens={"head": "Fraunces", "body": "Inter", "bg": "#F7EFE2"}))
    got = set(res["by_rule"])
    want = {"overused-font", "cream-palette", "gradient-text", "ai-color-palette", "radial-halo", "side-tab", "dark-glow",
            "bounce-easing", "hard-offset-shadow", "repeating-stripes", "grid-background", "justified-text", "tight-leading",
            "tiny-text", "wide-tracking", "all-caps-body", "crushed-tracking", "italic-serif-display",
            "kicker-above-heading", "marketing-buzzword", "broken-image", "numbered-section-labels", "nested-cards",
            "icon-tile-stack", "marquee", "emoji-icons", "theater-phrase", "skipped-heading"}
    assert want - got == set(), sorted(want - got)
    assert got - set(LK.RULES) == set()
    # each finding names the section the fixer rewrites
    by = {f["rule"]: f for f in res["findings"]}
    assert by["side-tab"]["sections"] == ["s-home-feat"] and by["gradient-text"]["sections"] == ["s-home-hero"]
    assert by["overused-font"]["sections"] == [] and "Fraunces" in by["overused-font"]["read"]
    assert set(by["numbered-section-labels"]["sections"]) == {"s-home-feat", "s-home-stats", "s-home-grid"}
    assert "streamline" in by["marketing-buzzword"]["read"] and "world-class" in by["marketing-buzzword"]["read"]
    rows = LK.rows(res)
    assert rows and all(r["state"] == "warn" and r["gate"] == "look" for r in rows)
    fix = LK.fix_items(res)
    rules_fixed = {i["text"].split(":")[0] for i in fix}
    assert all(i["sections"] for i in fix) and not any("Overused font" in t for t in rules_fixed)
    assert any("Thick side border" in t for t in rules_fixed)


def test_em_dash_overuse_is_site_wide_and_advisory(tmp_path):
    from app.site import look as LK
    body = " ".join(["Fresh sweets — made daily — in Akola."] * 6)
    out = _site(tmp_path, {"index.html": f'<section id="s-home-a"><h2>A</h2><p>{body}</p></section>'}, "")
    res = LK.scan(out, _ctx())
    f = [x for x in res["findings"] if x["rule"] == "em-dash-overuse"]
    assert f and f[0]["sections"] == [] and "em-dash-overuse" not in LK.FIXABLE


def test_the_brief_wins(tmp_path):
    from app.site import look as LK
    out = _site(tmp_path, {"index.html": PLANTED_HTML}, PLANTED_CSS)
    tk = {"head": "Fraunces", "body": "Inter", "bg": "#F7EFE2"}
    res = LK.scan(out, _ctx(tokens=tk, brief="Ek neon glow wala website, upar ek marquee strip chahiye", her_look=True))
    got = set(res["by_rule"])
    for pinned in ("dark-glow", "radial-halo", "marquee", "overused-font", "cream-palette", "ai-color-palette"):
        assert pinned not in got, pinned
    assert {"side-tab", "kicker-above-heading"} <= got                     # what she did not ask for is still said
    assert "marquee" in res["pinned"]
    # brand colours she gave also make the palette hers
    res2 = LK.scan(out, _ctx(tokens=tk, facts={"brand_colors": {"primary": "#7c3aed"}}))
    assert "ai-color-palette" not in res2["by_rule"] and "overused-font" not in res2["by_rule"]


def test_page_modes_judge_differently(tmp_path):
    from app.site import look as LK
    assert LK.page_mode("index.html") == "persuade" and LK.page_mode("services/index.html") == "persuade"
    assert LK.page_mode("account/index.html") == "operate" and LK.page_mode("admin/index.html") == "operate"
    assert LK.page_mode("blog/my-post/index.html") == "read" and LK.page_mode("privacy/index.html") == "read"
    assert LK.page_mode("gallery/index.html") == "experience"
    tiles = '<section id="s-x-a"><h2>Tools</h2>' + "".join(TILE.format(n) for n in "ABC") + "</section>"
    steps = "".join(f'<section id="s-g-{i}"><span>0{i}</span><h2>Step {i}</h2></section>' for i in (1, 2, 3))
    out = _site(tmp_path, {"admin/index.html": tiles, "guide/index.html": steps, "index.html": tiles}, "")
    res = LK.scan(out, _ctx())
    pages = {(f["rule"], f["page"]) for f in res["findings"]}
    assert ("icon-tile-stack", "index.html") in pages and ("icon-tile-stack", "admin/index.html") not in pages
    assert not any(r == "numbered-section-labels" for r, _p in pages)     # a guide's steps carry information


def test_the_gate_warns_and_never_blocks_a_built_site(site_env):
    from app.site import gates as G
    from app.site import service as S
    from tests.test_v0551_suraksha_gates import _built
    sid, r, out = _built(S)
    res = G.scan(out, S._ctx(r), {"source": "hoola+axe", "blocking": []}, S.form_endpoint(r))
    look = [x for x in res["rows"] if x["gate"] == "look"]
    assert look and all(x["state"] in ("warn", "pass") for x in look)
    assert not [x for x in res["rows"] if x["state"] == "fail"]
    merged = G.merge({"blocking": [], "warnings": []}, res)
    assert merged["passed"] is True
    # the switch turns the gate off
    from app.config import get_settings
    st = get_settings()
    old = st.site_look
    try:
        st.site_look = False
        assert not [x for x in G.scan(out, S._ctx(r), {}, "")["rows"] if x["gate"] == "look"]
    finally:
        st.site_look = old


def test_first_fix_round_gets_the_section_tells(site_env, tmp_path):
    from app.site import look as LK
    from app.site import service as S
    out = _site(tmp_path, {"index.html": PLANTED_HTML}, PLANTED_CSS)
    plan = {"pages": [{"slug": "home", "sections": [{"type": t} for t in ("hero", "feat", "stats", "grid", "copy")]}]}
    fx = S._fixable({"blocking": LK.fix_items(LK.scan(out, _ctx()))}, plan)
    assert "home__feat" in fx and any("Thick side border" in p for p in fx["home__feat"])
    assert "home__hero" in fx and any("Gradient text" in p for p in fx["home__hero"])
    src = (Path(S.__file__)).read_text()
    assert "if rnd == 0:" in src and "_look_fixable(r, live, plan)" in src          # once, before her first look


def test_builder_defaults_no_longer_ask_for_the_tells():
    from app.site import ai as AI
    from app.site import kit as K
    from app.site import look as LK
    from app.site import taxonomy as TX
    for key, st in TX.STYLES.items():
        f = TX.FONTS[st["fonts"]]
        assert f["head"] not in LK.OVERUSED_FONTS and f["body"] not in LK.OVERUSED_FONTS, key
        assert not any("marquee" in m or "glow" in m for m in st["motion"]), key
        assert not any("marquee" in h or "glow" in h for h in st["heroes"]), key
        assert not any(w in st["do"].lower() for w in ("small caps label", "letter-spaced label", "numbered section",
                                                         "marquee", "gradient glow")), key
    # her old choices still exist (a site built before keeps its fonts; her design can still map onto them)
    assert "fraunces_inter" in TX.FONTS and "inter_inter" in TX.FONTS
    assert ".eyebrow" not in AI.SECTION_SYSTEM and "CRAFT FLOOR" in AI.SECTION_SYSTEM
    assert "at least two motion attributes" not in AI.SECTION_SYSTEM
    assert "k-eyebrow" not in K.PARTS and "k-eyebrow" not in K.KIT_SYSTEM
    assert "streamline" in AI.CRAFT_FLOOR and "eyebrow" in AI.CRAFT_FLOOR


def test_her_own_look_is_remembered_on_the_chosen_look():
    from app.site import service as S
    src = Path(S.__file__).read_text()
    assert '"mine": bool(lk.get("mine"))' in src                         # choose_look keeps "this is her design"
    assert 'look["her_tokens"] = True' in src                              # colours / type she asked for are hers
    assert '"her_look": bool(look.get("mine") or look.get("her_tokens"))' in src


def test_attribution_is_recorded():
    root = Path(__file__).resolve().parents[2]
    notices = (root / "THIRD_PARTY_NOTICES.md").read_text()
    assert "impeccable" in notices.lower() and "Apache" in notices
    assert (root / "docs" / "research" / "impeccable" / "00_READ.md").exists()
