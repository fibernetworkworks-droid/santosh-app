"""v0.999.66 D5 THE CRITIC LOOP (docs/WEB_DESIGN_ENGINE_PLAN.md phase D5, P7): a React website is photographed on a
computer and a phone with every section numbered, code measures what it can, a SEPARATE critic (never the writer's
company) scores the D0 card's 9 criteria and names fixes from a fixed list, code checks each fix and the writer writes
the site again - max 3 rounds or until the bar; the best round is the one kept; 3 hero directions are tried internally
and the critic picks one. Done-line: the D0 design score beaten on the card (a LIVE card - the free card proves the pipes)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.appengine import critic as C
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _autofix_on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")    # conftest switches it off for the older suites
    monkeypatch.setenv("SITE_CRITIC", "true")           # ... and the critic loop
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pages():
    return [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Fresh bread every morning", "line": "Baked in Pune since 1998", "cta": "Order now"},
        {"type": "stats_counters", "heading": "Numbers", "items": ["Some", "Words"]},      # no numbers: not a stat block
        {"type": "services_grid", "heading": "What we bake", "items": ["Pav - soft rolls", "Nankhatai - butter biscuits"]},
        {"type": "faq", "heading": "Questions", "items": ["Do you deliver? - Yes, in Kothrud"]},
        {"type": "reviews", "heading": "What people say", "items": ["Best pav in town - Asha"]},
        {"type": "contact_block", "heading": "Visit us"}]},
        {"slug": "menu", "title": "Menu", "for": "public", "sections": [
            {"type": "services_grid", "heading": "Breads", "items": ["Pav - soft", "Bun - sweet"]},
            {"type": "cta_band", "heading": "Order today"}]}]


# ---------------------------------------------------------------- 1. the writer takes the design choices
def test_every_section_wears_its_number_and_design_choices_apply_only_where_allowed():
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"phone": "+91 90000 00001"}, "s", None)
    code, rows = W.page_file(_pages()[0], ctx, {})
    assert code.count('data-sec="home:') == 6 and 'className="contents"' in code     # every section, numbered
    secs = {r["sec"]: r for r in rows}
    assert secs["home:1"]["block"] == "features_split"                               # stats with no numbers: not a stat
    sv = secs["home:2"]
    assert sv["block"] == "services_grid" and sv["alts"] and sv["variant"] not in sv["alts"]
    design = {"home:2": {"variant": sv["alts"][0], "tone": "ink"}, "home:3": {"drop": True},
              "home:4": {"variant": "kinetic-does-not-exist"}, "home:0": {"tone": "primary"}}   # last two: not allowed
    code2, rows2 = W.page_file(_pages()[0], ctx, {}, design)
    r2 = {r["sec"]: r for r in rows2}
    assert r2["home:2"]["variant"] == sv["alts"][0] and r2["home:2"]["tone"] == "ink"
    assert r2["home:3"]["block"] is None and "after the design review" in r2["home:3"]["why"]
    assert r2["home:4"]["variant"] == secs["home:4"]["variant"]                     # a layout it cannot take: ignored
    assert 'tone="primary"' not in code2.split('data-sec="home:0"')[1].split("</div>")[0]
    assert W.alts_of("hero", "split") == ["overlay"] and "kinetic" not in W.ALTS["hero"]   # rotating words never offered
    assert W.alts_of("features_split", "checklist", {"features": []}) == []
    assert "primary" in W.tones_of("cta_band") and W.tones_of("screen_table") == []


def test_hidden_pages_get_a_route_but_no_menu_link():
    pages = _pages()
    ctx = W.Ctx("Sunrise Bakery", pages, {}, "s", None)
    extra = [{**pages[0], "slug": "hoola-hero-b"}]
    files, rows = W.plan_files(pages, ctx, {}, {"hoola-hero-b:0": {"variant": "overlay"}}, extra)
    assert "src/pages/HoolaHeroBPage.tsx" in files and 'path="/hoola-hero-b"' in files["src/App.tsx"]
    assert "hoola-hero-b" not in files["src/components/site/Layout.tsx"]
    assert 'variant="overlay"' in files["src/pages/HoolaHeroBPage.tsx"]
    assert all(r["page"] != "hoola-hero-b" for r in rows)


# ---------------------------------------------------------------- 2. the critic: never the writer's company, never a guess
def test_the_critic_is_never_the_writers_company(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    get_settings.cache_clear()
    monkeypatch.setattr("app.devsahayak.brain._or_key", lambda: "k")
    assert C.critic_who("qwen/qwen3.8-27b")["route"] == "anthropic"
    w = C.critic_who("anthropic/claude-opus-5.5")
    assert w["route"] == "openrouter" and w["company"] != "anthropic" and w["ok"]
    monkeypatch.setenv("SITE_CRITIC_ALT_MODEL", "anthropic/claude-sonnet-5.5")
    get_settings.cache_clear()
    w = C.critic_who("anthropic/claude-opus-5.5")
    assert not w["ok"] and "another company" in w["why"]
    assert C.company_of("claude-opus-5-5") == "anthropic" and C.company_of("google/gemini-3.8-flash") == "google"


def _shots():
    def sec(sec, n, block, variant, bg, **kw):
        return {"sec": sec, "n": n, "block": block, "variant": variant, "bg": bg, "imgs": 0, "small": 0, "wide": 0,
                "longest": 60, **kw}
    desk = [sec("home:0", 1, "hero", "split", "rgb(1, 1, 1)"), sec("home:2", 2, "services_grid", "cards", "rgb(9, 9, 9)"),
            sec("home:3", 3, "faq", "accordion", "rgb(9, 9, 9)", longest=120),
            sec("home:4", 4, "services_grid", "cards", "rgb(5, 5, 5)")]
    phone = [dict(s, wide=(1 if s["sec"] == "home:4" else 0), small=(3 if s["sec"] == "home:2" else 0)) for s in desk]
    return {"pages": {"home": {"desk": {"sections": desk}, "phone": {"sections": phone}}}}


def _rows():
    ctx = W.Ctx("Sunrise Bakery", _pages(), {"phone": "+91 90000 00001"}, "s", None)
    _, rows = W.page_file(_pages()[0], ctx, {})
    rows = [{"page": "home", **r} for r in rows]
    for r in rows:                                  # line the fake page up with the rows (home:4 a services grid too)
        if r["sec"] == "home:4":
            r.update(block="services_grid", variant="cards", alts=["numbered"], tones=["surface", "ink"])
    return rows


def test_code_measures_what_it_can_see():
    got = C.measure(_shots(), _rows())
    why = " | ".join(m["why"] for m in got)
    assert "sections 2 and 3 run together on the same background" in why
    assert "section 4 (services_grid) is wider than a phone screen" in why
    assert "section 4 repeats the layout of section 2" in why
    assert "tap targets under 24 px" in why and "lines of about 120 characters" in why
    fixes = {(m["sec"], m["fix"]) for m in got if m["fix"]}
    assert ("home:3", "tone") in fixes and ("home:4", "variant") in fixes


def test_the_critics_words_are_read_strictly():
    from app.quality import designcard as DC
    rows, shots = _rows(), _shots()
    good = {"scores": {k: 6 for k in DC.CRITERIA}, "looks_ai_made": True, "problems": ["flat"],
            "fixes": [{"page": "home", "n": 2, "fix": "variant", "why": "too plain"},
                      {"page": "home", "n": 1, "fix": "drop", "why": "the hero"},          # a hero is never left out
                      {"page": "home", "n": 3, "fix": "tone", "to": "neon"},               # not a listed background
                      {"page": "home", "n": 9, "fix": "tone"},                             # no such section
                      {"page": "home", "n": 3, "fix": "rewrite"}]}                         # rewrite: custom only
    v = C.parse("Here: " + json.dumps(good), rows, shots)
    assert v["design"] == 6.0 and v["ai_made"] and [f["sec"] for f in v["fixes"]] == ["home:2"] and v["fixes_dropped"] == 4
    bad = {**good, "scores": {**good["scores"], "layout": 11}}
    with pytest.raises(C.CriticError):
        C.parse(json.dumps(bad), rows, shots)
    with pytest.raises(C.CriticError):
        C.parse("looks lovely", rows, shots)
    txt = C.section_list(rows, shots)
    assert "home 2: services_grid" in txt and "variant to" in txt and "home 1: hero" in txt
    assert "never ask for new words" in C.loop_system().lower() and "fixes" in C.loop_system()


def test_code_decides_which_fixes_apply():
    rows = _rows()
    design, tried = {}, {}
    fixes = [{"sec": "home:2", "fix": "variant", "to": ""}, {"sec": "home:2", "fix": "tone", "to": ""},   # one a round
             {"sec": "home:3", "fix": "tone", "to": ""}, {"sec": "home:0", "fix": "drop"}]
    done, notes = C.apply(design, fixes, rows, tried)
    assert [f["sec"] for f in done] == ["home:2", "home:3"] and notes == {}
    assert design["home:2"]["variant"] in W.ALTS["services_grid"] and design["home:3"]["tone"] in ("surface", "plain")
    first = design["home:2"]["variant"]
    C.apply(design, [{"sec": "home:2", "fix": "variant", "to": ""}], rows, tried)
    assert design["home:2"]["variant"] != first or len(W.ALTS["services_grid"]) < 3      # a tried layout is not tried again
    shown = [r for r in rows if r.get("block")]
    drops = [{"sec": r["sec"], "fix": "drop"} for r in shown if r["block"] not in C.NEVER_DROP]
    d2: dict = {}
    for f in drops:
        C.apply(d2, [f], rows, {})
    assert sum(1 for v in d2.values() if v.get("drop")) <= len(shown) - 2               # a page keeps two sections
    custom = [{"page": "home", "sec": "home:9", "type": "custom_x", "block": "custom"}]
    _, n = C.apply({}, [{"sec": "home:9", "fix": "rewrite", "why": "fits badly"}], custom, {})
    assert n == {"home:custom_x": "fits badly"}


# ---------------------------------------------------------------- 3. the loop, in the box
def test_the_loop_fixes_keeps_the_best_and_picks_a_hero(ae_env):
    _box()
    from app.appengine import service as AE
    from app.quality import designcard as DC
    app = AE.create(T, name="Sunrise Bakery", brief="a bakery in Pune", render="site")
    seen = []

    def critic(imgs, rows, shots, measured):
        k = len(seen) + 1
        seen.append({"imgs": len(imgs), "numbered": [s["sec"] for s in shots["pages"]["home"]["desk"]["sections"]],
                     "rows": rows})
        sc = {1: 5, 2: 7, 3: 6}[k]
        fix = [{"sec": "home:2", "fix": "variant", "to": "", "why": "plain"}] if k == 1 else \
            [{"sec": "home:4", "fix": "tone", "to": "ink", "why": "flat"}]
        return {"scores": {c: sc for c in DC.CRITERIA}, "design": float(sc), "problems": ["p"], "fixes": fix}

    picks = []

    def picker(dirs):
        picks.append([(letter, bool(rec.get("desk")) and bool(rec.get("phone"))) for letter, rec in dirs])
        return {"pick": "B", "why": "bolder"}

    rep = C.improve(T, app["id"], _pages(), name="Sunrise Bakery", facts={"phone": "+91 90000 00001"}, seed="s",
                    brief="a bakery in Pune", critic=critic, picker=picker, bar_=7.5)
    assert picks == [[("A", True), ("B", True), ("C", True)]]                 # 3 directions photographed
    assert rep["hero"]["pick"] == "B" and rep["design"]["home:0"] == {"variant": "overlay"}
    assert len(rep["rounds"]) == 3 and [r["score"] for r in rep["rounds"]] == [5.0, 7.0, 6.0]
    assert seen[0]["imgs"] >= 3 and seen[0]["numbered"][:3] == ["home:0", "home:1", "home:2"]
    assert rep["best_round"] == 2 and rep["restored"] == 2 and rep["score"] == 7.0 and not rep["passed"]
    assert rep["build"]["built"] and rep["write"]["refused_left"] == 0
    r = AE._load(T, app["id"])
    src = AE.src_dir(r) / "src"
    assert not (src / "pages" / "HoolaHeroBPage.tsx").exists() and "hoola-hero" not in (src / "App.tsx").read_text()
    home = (src / "pages" / "HomePage.tsx").read_text()
    assert 'variant="overlay"' in home.split('data-sec="home:0"')[1].split("</div>")[0]   # the picked hero kept
    assert 'tone="ink"' not in home.split('data-sec="home:4"')[1].split("</div>")[0]      # round 3's fix undone
    assert "Design review 7.0 / 10 after 3 rounds" in C.say(rep)


def test_the_loop_stops_at_the_bar_and_without_a_critic_it_builds_once(ae_env):
    _box()
    from app.appengine import service as AE
    from app.quality import designcard as DC
    app = AE.create(T, name="Sunrise Bakery", brief="a bakery", render="site")
    rep = C.improve(T, app["id"], _pages(), name="Sunrise Bakery", seed="s", hero=False,
                    critic=lambda *a: {"scores": {c: 8 for c in DC.CRITERIA}, "design": 8.0, "fixes": []})
    assert len(rep["rounds"]) == 1 and rep["passed"] and rep["rounds"][0]["passed"] and rep["hero"] is None
    app2 = AE.create(T, name="Sunrise Bakery 2", brief="a bakery", render="site")
    rep2 = C.improve(T, app2["id"], _pages(), name="Sunrise Bakery", seed="s",
                     who={"ok": False, "why": "no critic from another company is set up"})
    assert rep2["skipped"] and len(rep2["rounds"]) == 1 and rep2["build"]["built"] and rep2["score"] is None
    assert C.say(rep2).startswith("No design review")


# ---------------------------------------------------------------- 4. wiring
def test_build_the_real_website_goes_through_the_loop():
    src = (ROOT / "server/app/site/prototype.py").read_text()
    assert "C.improve(" in src and 'link["critic"]' in src and "C.say(review)" in src
    from app.config import get_settings
    st = get_settings()
    assert st.site_critic and st.site_critic_rounds == 3 and st.site_critic_bar == 7.5 and st.site_critic_hero
    assert C.company_of(st.site_critic_alt_model) != "anthropic"
    js = (ROOT / "server/app/static/console/webstudio.js").read_text()
    assert "data-critic" in js and "Design review" in js


def test_the_card_never_calls_a_free_run_a_win():
    from app.appengine import writercard as WC
    rows = [{"score_first": 5.0, "score": 7.2, "passed": False, "rounds": 3, "review_fixes": 4, "critic_inr": 1.5,
             "hero": {"pick": "B"}}, {"score_first": 6.0, "score": 8.0, "passed": True, "rounds": 1, "hero": {"pick": "A"}}]
    rv = WC._review_sum(rows)["review"]
    assert rv["passed"] == 1 and rv["hero_not_a"] == 1 and rv["fixes"] == 4
    card = {"kind": "free", "summary": {"review": rv}}
    assert WC.against(card, {"rows": [{"design": 6.1}]})["beaten"] is None
    live = {"kind": "live", "summary": {"review": rv}}
    assert WC.against(live, None)["beaten"] is None
    assert WC.against(live, {"rows": [{"design": 6.1}, {"design": 6.5}, {"design": None}]})["beaten"] is True
    assert "--critic" in (ROOT / "server/app/appengine/__main__.py").read_text()
    assert "writer-card --critic" in (ROOT / ".github/workflows/vps-ops.yml").read_text()


def test_her_build_tap_runs_the_review_and_keeps_its_line(ae_env, monkeypatch):
    _box()
    from app.config import get_settings
    from app.quality import designcard as DC
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    from tests.test_v0999_65_writer import _proto
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(C, "critic_who", lambda writer="": {"ok": True, "route": "x", "model": "a-critic", "company": "x"})
    monkeypatch.setattr(C, "pick_hero", lambda who, brief, dirs: {"pick": "C", "why": "darker"})
    monkeypatch.setattr(C, "review", lambda who, brief, purpose, imgs, rows, shots, measured, photos_off=True:
                        {"scores": {c: 8 for c in DC.CRITERIA}, "design": 8.0, "problems": [], "fixes": []})
    get_settings.cache_clear()
    v = S.new(T, "A website for Nirmal Family Clinic in Pune: doctors, timings, map and WhatsApp.", name="Nirmal Family Clinic")
    PT._write_version(S._load(v["id"]), _proto(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    cr = out["react"]["critic"]
    assert cr["score"] == 8.0 and cr["passed"] and cr["rounds"] == 1 and cr["model"] == "a-critic"
    assert cr["say"].startswith("Design review 8.0 / 10 after 1 round")
    if cr.get("hero"):                                  # the prototype opens with a hero: the critic's pick is kept
        assert cr["hero"]["pick"] == "C"
    get_settings.cache_clear()


def test_every_layout_the_critic_may_ask_for_builds_with_her_words_only(ae_env):
    """Each block in every layout the critic may switch it to, drawn with real words: it builds, type-checks and shows
    no kit sample text (a layout that read a prop the mapper never fills would show the kit's sample bakery)."""
    _box()
    from app.appengine import service as AE
    from app.appengine import writercard as WC
    facts = {"phone": "+91 90000 00001", "whatsapp": "919000000001", "address": "1, Main Road", "hours": "Mon-Sat 10am-8pm"}
    pages, design = [], {}
    for block in sorted(W.ALTS):
        slug = "home" if block == "hero" else block.replace("_", "-")
        variants = list(dict.fromkeys(list(W.ALTS[block]) + (["split"] if block == "cta_band" else [])
                                      + (["phone"] if block == "contact_block" else [])))
        secs = [{"type": block, "label": block.replace("_", " ").title()} for _ in variants]
        pages.append({"slug": slug, "title": block.replace("_", " ").title(), "for": "public", "sections": secs})
        for i, v in enumerate(variants):
            design[f"{slug}:{i}"] = {"variant": v}
    pages.sort(key=lambda p: p["slug"] != "home")
    pages = WC.sample_copy(pages, "Sunrise Bakery", "A bakery in Pune: fresh bread every morning.")
    app = AE.create(T, name="Sunrise Bakery", brief="a bakery", render="site")
    st = W.write_app(T, app["id"], pages, name="Sunrise Bakery", facts=facts, seed="s", design=design)
    assert st["refused_left"] == 0, st["refusals"]
    drawn = {(r["block"], r["variant"]) for r in st["sections"] if r.get("block")}
    for k, d in design.items():
        page = next(p for p in pages if p["slug"] == k.split(":")[0])
        blk = page["sections"][0]["type"]
        if blk in ("stats_counters", "pricing_table", "menu_list"):
            continue                                        # the words decide these (no numbers = another block)
        assert (blk, d["variant"]) in drawn, (blk, d["variant"])
    res = AE.build(T, app["id"])
    r = AE._load(T, app["id"])
    lb = json.loads(r.last_build or "{}")
    assert res.get("built") and lb.get("types_ok"), lb.get("types")
    html = WC._html_pages(AE.ver_dir(r, r.version) / "dist")
    own = json.dumps(pages, ensure_ascii=False) + "".join(
        f.read_text("utf-8", "replace") for f in (AE.src_dir(r) / "src" / "pages").glob("*.tsx"))
    leaks = sorted({q for h in html.values() for q in W.leaks(h, own)})
    assert not leaks, leaks
