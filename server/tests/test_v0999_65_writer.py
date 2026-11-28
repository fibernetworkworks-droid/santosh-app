"""v0.999.65 D4 THE WRITER + AUTOFIX (docs/WEB_DESIGN_ENGINE_PLAN.md phase D4, P5): the prototype she approved becomes a
React website made only of the kit's blocks + the design's tokens; every App Engine write is repaired by code before the
rules read it; a refused custom section goes back to the model once and is drawn as a block if still refused, so no
refused write is ever left. Done-line: the 40 design-card briefs build with 0 refused writes left (`writercard`)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.appengine import autofix as AF
from app.appengine import image as IMG
from app.appengine import rules as RL
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _autofix_on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")    # conftest switches it off for the older suites
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


DEPS = set(IMG.CORE) | set(IMG.DEV)

SLOPPY = '''import * as React from "react";
export default function Promo() {
  return (
    <section className="bg-white py-[72px] px-[20px]">
      <h1 className="text-[44px] font-[700] text-gray-900 leading-[1.1] tracking-[-0.02em]">Big sale \U0001F389 today</h1>
      <h1 className="text-gray-500">Second title</h1>
      <h4>Jumped</h4>
      <p style={{ color: "#333333", background: "rgba(0,0,0,0.5)" }}>Hello</p>
      <img src="/photos/shop-front_2.jpg" className="rounded-[12px] max-w-[700px]" />
      <button className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 transition-all hover:scale-105" onClick={() => alert("Thanks!")}>Buy</button>
      <a href="#faq" className="text-blue-600">Questions</a>
      <div className="border border-gray-200 bg-blue-50 z-[60] opacity-[0.8] w-[50%]">x</div>
      <button className="bg-primary px-4 py-2 outline-none">Go</button>
    </section>
  );
}
'''


# ---------------------------------------------------------------- 1. AutoFix
def test_autofix_repairs_every_slip_onto_the_tokens():
    path = "src/components/sections/Promo.tsx"
    assert len(RL.check_file(path, SLOPPY, DEPS)) >= 20
    code, done = AF.fix(path, SLOPPY)
    assert RL.check_file(path, code, DEPS) == [], RL.say(RL.check_file(path, code, DEPS))
    rules = {d["rule"] for d in done}
    assert {"palette colour", "one-off value", "raw colour", "taste", "a11y", "states"} <= rules
    for want in ("bg-surface", "py-18", "text-5xl", "font-bold", "text-ink", "var(--color-ink)", "transition-transform",
                 'alt="shop front"', "<h2", "<h3>", 'import { toast } from "sonner";', "toast(\"Thanks!\")",
                 "outline-none focus-visible:outline-2", "hover:bg-primary/90", "w-1/2", "z-50"):
        assert want in code, want
    assert "\U0001F389" not in code and "bg-gradient" not in code
    # every fix names its file and line in the ORIGINAL file
    assert all(d["file"] == path and d["line"] >= 1 for d in done)
    assert "Fixed by itself" in AF.say(done)


def test_autofix_leaves_good_code_alone_and_unsafe_or_changed_behaviour_to_the_rules():
    good = (ROOT / "server/app/appengine/template/src/components/blocks/faq.tsx").read_text()
    assert AF.fix("src/components/blocks/faq.tsx", good) == (good, [])
    bad = 'export default function X(){ return <select><option>1</option></select>; }\n'
    code, _ = AF.fix("src/pages/X.tsx", bad)
    assert any("Select" in p["found"] for p in RL.check_file("src/pages/X.tsx", code, DEPS))
    unsafe = 'export default function X(){ return <div dangerouslySetInnerHTML={{__html: "x"}} />; }\n'
    assert RL.check_file("src/pages/X.tsx", AF.fix("src/pages/X.tsx", unsafe)[0], DEPS)


def test_the_nearest_token_follows_the_apps_own_design():
    t = {"bg": "#ffffff", "surface": "#f7f7f7", "ink": "#111111", "muted": "#666666", "line": "#dddddd",
         "primary": "#c0392b", "accent": "#2471a3", "ok": "#1e8449", "warn": "#b9770e", "bad": "#922b21", "radius": 8}
    code, _ = AF.fix("src/pages/A.tsx", 'export default () => <div className="bg-[#1f5f99] text-sky-700 border-red-500" />;\n', t)
    assert "bg-accent" in code and "text-accent" in code and "border-bad" in code


def test_every_app_engine_write_goes_through_autofix(ae_env):
    from app.appengine import service as AE
    a = AE.create(T, name="Fix test", render="site")
    res = AE.write(T, a["id"], "src/components/sections/Promo.tsx", SLOPPY)
    assert res["fixed"] and "Fixed by itself" in res["say"]
    on_disk = (AE.src_dir(AE._load(T, a["id"])) / "src/components/sections/Promo.tsx").read_text()
    assert "text-gray-900" not in on_disk and "bg-surface" in on_disk
    with pytest.raises(AE.AppEngineError) as e:
        AE.write(T, a["id"], "src/pages/X.tsx", 'export default function X(){ return <select />; }\n')
    assert e.value.code == 422 and "src/pages/X.tsx:1" in str(e.value)


# ---------------------------------------------------------------- 2. the writer
def _proto() -> list[dict]:
    return [
        {"slug": "home", "title": "Home", "for": "public", "sections": [
            {"type": "hero", "heading": "Nirmal Family Clinic", "line": "Gentle care for the whole family in Pune.",
             "items": ["Open six days", "Near the station"], "cta": "Book a visit"},
            {"type": "services_grid", "heading": "What we treat", "line": "", "items": [
                "Fever and flu - same-day visit - Rs 500 (sample)", "Child care - vaccines and growth checks"]},
            {"type": "reviews", "heading": "What families say", "items": ['"Kind and quick." - Priya (sample)']},
            {"type": "stats_counters", "heading": "In numbers", "items": ["Years open: 15+", "Families: 4,800+"]},
            {"type": "faq", "heading": "Questions", "items": ["Do you open on Sundays? Yes, till 2 pm", "Can I pay by UPI?"]},
            {"type": "contact_block", "heading": "Visit us", "line": "Call or walk in.", "items": []},
            {"type": "whatsapp_float"},
            {"type": "custom_highlights", "label": "What makes us different", "heading": "Different", "items": ["A", "B"]},
        ]},
        {"slug": "about", "title": "About", "for": "public", "sections": [
            {"type": "intro_story", "heading": "Our story", "line": "Two doctors, one promise.", "items": []},
            {"type": "team", "heading": "The doctors", "items": ["Dr Asha - family doctor (sample)"]}]},
        {"slug": "app-dashboard", "title": "Your dashboard", "for": "member", "sections": [
            {"type": "screen_dashboard", "heading": "Overview", "items": ["Visits: 3"]}]},
    ]


def test_every_section_becomes_a_kit_block_with_her_words_and_clean_code():
    ctx = W.Ctx("Nirmal Family Clinic", _proto(), {}, "t")
    files, rows = W.plan_files(_proto(), ctx)
    assert set(files) == {"src/pages/HomePage.tsx", "src/pages/AboutPage.tsx", "src/pages/AppDashboardPage.tsx",
                          "src/pages/NotFoundPage.tsx", "src/components/site/Layout.tsx", "src/App.tsx"}
    for rel, code in files.items():                       # the writer's own code needs no fix and breaks no rule
        assert RL.check_file(rel, code, DEPS) == [], (rel, RL.say(RL.check_file(rel, code, DEPS)))
        assert AF.fix(rel, code)[1] == [], (rel, AF.fix(rel, code)[1])
    home = files["src/pages/HomePage.tsx"]
    assert 'headline="Nirmal Family Clinic"' in home and "Fever and flu" in home and '"price":500' in home
    assert '"value":4800' in home and '"suffix":"+"' in home
    by = {r["type"]: r for r in rows}
    assert by["custom_highlights"]["block"] == "features_split"        # no model: the nearest block
    assert by["whatsapp_float"]["block"] is None                       # no number given: no button pretending
    dash = files["src/pages/AppDashboardPage.tsx"]
    assert "<AppPage>" in dash and "noindex" in dash and W.SAMPLE_ROWS_NOTE in dash
    assert '<Route path="/about"' in files["src/App.tsx"] and 'path="*"' in files["src/App.tsx"]


def test_no_fact_is_made_up_and_no_kit_sample_reaches_her_site():
    ctx = W.Ctx("Nirmal Family Clinic", _proto(), {}, "t")
    files, _ = W.plan_files(_proto(), ctx)
    allcode = "".join(files.values())
    for sample in ("98220 45117", "Ramdaspeth", "hello@example.in", "Shanti Complex"):
        assert sample not in allcode, sample
    assert "Your address (add yours)" in allcode and "address" in ctx.blanks
    sentences = W.sample_sentences()
    assert len(sentences) > 50
    assert [q for q in sentences if q in allcode] == []
    ctx2 = W.Ctx("Nirmal", _proto(), {"phone": "+91 90000 00001", "whatsapp": "9190000000001", "address": "1, Main Road",
                                      "hours": "Mon-Sat 10am-8pm"}, "t")
    files2, rows2 = W.plan_files(_proto(), ctx2)
    assert "+91 90000 00001" in files2["src/pages/HomePage.tsx"] and not ctx2.blanks or ctx2.blanks == ["answer"]
    assert {r["type"]: r for r in rows2}["whatsapp_float"]["block"] == "whatsapp_float"
    assert W.week_of("Mon-Sat 10am-8pm")[5] == {"day": "Saturday", "open": "10:00", "close": "20:00"}
    assert W.week_of("Mon-Sat 10am-8pm")[6] == {"day": "Sunday"} and W.week_of("by appointment") == []


def test_a_refused_custom_section_goes_back_once_then_becomes_a_block(ae_env):
    from app.appengine import service as AE
    from app.appengine import writercard as WC
    for kind, written, refused_first in (("sloppy", 1, 0), ("select", 1, 1), ("unsafe", 0, 1)):
        a = AE.create(T, name=f"Custom {kind}", render="site")
        st = W.write_app(T, a["id"], _proto(), name="Nirmal", facts={}, model=WC.scripted_model(kind), seed="t")
        assert st["custom_written"] == written, (kind, st)
        assert st["refused_left"] == 0, (kind, st["refusals"])        # the done-line: nothing refused is left
        assert st["refused_first"] >= refused_first, kind
        if kind == "sloppy":
            assert st["fixed"] >= 15
            code = (AE.src_dir(AE._load(T, a["id"])) / "src/components/sections/HighlightsSection.tsx").read_text()
            assert "text-gray-900" not in code and "<h2" in code
        if kind == "unsafe":
            assert st["custom_fallback"] == 1 and st["refusals"][-1].get("fell_back")


def test_going_live_waits_for_her_blanks(ae_env):
    from app.appengine import service as AE
    a = AE.create(T, name="Blanks", render="site")
    W.write_app(T, a["id"], _proto(), name="Nirmal", facts={}, seed="t")
    src = AE.src_dir(AE._load(T, a["id"]))
    assert "address" in AE.publish_blanks(src)
    page = src / "src/pages/HomePage.tsx"
    page.write_text(page.read_text().replace("Your address (add yours)", "1, Main Road").replace(
        "Your answer (add yours)", "Yes.").replace("Your email (add yours)", "a@b.in"))
    assert AE.publish_blanks(src) == []


def test_contact_blocks_leave_out_what_she_has_not_given():
    kit = ROOT / "server/app/appengine/template/src/components/blocks"
    cb = (kit / "contact-block.tsx").read_text()
    assert '.filter((w) => (w.name === "WhatsApp" ? !!d.whatsapp : !!w.value))' in cb
    assert "{d.phone ? <Button" in cb and 'import { cn } from "@/lib/utils";' in cb
    assert "{d.phone ? <p" in (kit / "cta-band.tsx").read_text()


# ---------------------------------------------------------------- 3. the Studio: behind the switch
def test_the_switch_is_off_until_she_says_so_and_wired_into_the_build_tap(monkeypatch):
    from app.config import get_settings
    from app.site import prototype as PT
    from app.site import service as S
    get_settings.cache_clear()
    assert get_settings().studio_react_sites is False and get_settings().app_engine_autofix is True
    from app.config import Settings
    assert Settings.model_fields["app_engine_autofix"].default is True
    assert Settings.model_fields["studio_react_sites"].default is False
    assert PT.react_on() is False
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    get_settings.cache_clear()
    assert PT.react_on() is True
    get_settings.cache_clear()
    src = (ROOT / "server/app/site/service.py").read_text()
    assert '"proto_react": PT.react_job' in src and 'v["react"]' in src
    assert 'S._start(r.id, "proto_react")' in (ROOT / "server/app/site/prototype.py").read_text()
    js = (ROOT / "server/app/static/console/webstudio.js").read_text()
    assert "Written in React from your prototype" in js and "EDIT && !isRx" in js
    assert S.view is not None


def test_approve_builds_the_react_website_in_the_box(ae_env, monkeypatch):
    _box()
    from app.appengine import service as AE
    from app.config import get_settings
    from app.site import prototype as PT
    from app.site import service as S
    from app.site import ai as AI
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    get_settings.cache_clear()
    v = S.new(T, "A website for Nirmal Family Clinic in Pune: doctors, timings, map and WhatsApp.", name="Nirmal Family Clinic")
    r = S._load(v["id"])
    PT._write_version(r, _proto(), "test", "hoola")
    h = PT.meta(S._load(v["id"]))["hash"]
    PT.approve(T, v["id"], h)
    r = S._load(v["id"])
    out = S.view(r)
    assert out["status"] == "ready", out.get("error")
    rx = out["react"]
    assert rx["built"] and rx["refused"] == 0 and out["preview"].startswith("/api/app-preview/")
    app = AE._load(T, rx["id"])
    assert json.loads(app.look)["render"] == "site" and json.loads(app.look).get("genome")
    get_settings.cache_clear()


# ---------------------------------------------------------------- 4. the card (the done-line)
def test_writer_card_one_brief_end_to_end(ae_env):
    _box()
    from app.appengine import writercard as WC
    from app.quality.design_asks import ASKS
    row = WC.run_one(ASKS[4], 4)                          # index 4: a custom section by the scripted sloppy "model"
    assert row["ok"], row
    assert row["built"] and row["types_ok"] and row["refused_left"] == 0 and not row["sample_leaks"]
    assert row["custom"] == "sloppy" and row["fixed"] >= 15 and row["pages_rendered"] >= 2


def test_writer_card_wiring():
    from app.appengine import writercard as WC
    from app.quality.design_asks import ASKS
    assert len(ASKS) == 40
    pages = WC.plan_pages(ASKS[0])
    assert pages and pages[0]["slug"] == "home"
    assert any(p["for"] != "public" for p in WC.plan_pages(next(a for a in ASKS if re.search(WC.APP_WORDS, a["ask"].lower()))))
    s = WC.summarise([{"built": True, "refused_left": 0, "ok": True, "blocks": ["hero"]}])
    assert s["verdict"] == "PASS"
    assert WC.summarise([{"built": True, "refused_left": 1, "ok": False}])["verdict"] == "FAIL"
    assert "writer-card" in (ROOT / "server/app/appengine/__main__.py").read_text()
    assert "site_writer_card)" in (ROOT / ".github/workflows/vps-ops.yml").read_text()
