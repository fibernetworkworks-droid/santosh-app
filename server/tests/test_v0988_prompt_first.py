"""v0.988 PROMPT FIRST (owner: "EVERY TIME AI BUILD SAME LANDING PAGE FOR ALL INPUTS ... FIRST REMOVE THAT PAGE ENTIERLY.
THEN BASED OF USER PROMPT AI WILL UNDERSTAND IT PROPERLY AND FIND THE PERFECT DESIGN, FONT, FONT SIZE FOR IT ON ITS OWN ...
ASK THE QUERIES TO USER IF REQUIRED ... I JUST TELL HOOLA WEB TO BUILD THE ISP PORTAL --- IT START BUILDING A STALE AND
RANDOM MARKETING PAGE ... THE PORTAL MEANS IT HAS A LOGIN PAGE AND A PORATL WITH ITS DATA").

Root causes found: (1) the 'A few quick choices' page and every look's colours / fonts came from fixed tables matched on
keywords - the AI only read her words after them; (2) a failed plan call fell back to the library's marketing page set
for the business type, even for a portal ask; (3) a plan the model called a 'lead_site' stayed a marketing site even
when her words said portal. Now the AI reads her words first and asks what changes the build, the plan chooses the
design (colours, font pair, text sizes) and look 1 is built from it, and a portal is always a sign-in front door + the
signed-in pages with their data."""
import json
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).parents[1] / "app" / "static" / "console"

# what a model gave back for "Build the ISP portal" when it drew a marketing site: no signed-in page, kind lead_site
ISP_RAW = {"name": "SwiftNet", "summary": "Internet plans", "field_hint": "internet service provider", "kind": "lead_site",
           "complexity": "standard", "goal": "enquiry",
           "roles": [{"key": "customer", "label": "Customer", "can": "pays bills"}],
           "pages": [{"slug": "home", "title": "Home", "purpose": "front", "for": "public",
                      "sections": [{"type": "hero", "design": "big photo"}, {"type": "features_split", "design": "why us"}]},
                     {"slug": "plans", "title": "Plans", "purpose": "plans", "for": "public",
                      "sections": [{"type": "hero", "design": "header"}]}],
           "design": {"mood": "calm, quick to scan for a customer paying a bill", "style": "corporate_trust",
                      "fonts": "inter_inter", "palette": {"bg": "#F7F9FC", "surface": "#FFFFFF", "ink": "#0E1726",
                                                          "primary": "#1F5EFF", "accent": "#00A88F"},
                      "radius": 8, "base_px": 15, "scale": 1.18}}


@pytest.fixture
def ask_on(site_env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("STUDIO_ASK_FIRST", "true")
    get_settings.cache_clear()
    yield site_env
    get_settings.cache_clear()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.40")
    assert "v0.988.0 PROMPT FIRST" in (Path(__file__).parents[1] / "app" / "main.py").read_text()


def test_the_choices_page_is_off_and_gone():
    from app.config import Settings
    assert Settings.model_fields["studio_design_questions"].default is False
    js = (CONSOLE / "webstudio.js").read_text()
    assert "askDesign" not in js and "A few quick choices" not in js


def test_hoola_asks_before_it_plans(ask_on, monkeypatch):
    from app.site import activity as AC
    from app.site import architect as AR
    seen = []

    def inner(system, prompt, max_tokens, kind):
        seen.append(system[:40])
        assert system == AR.UNDERSTAND and "ISP portal" in prompt
        return {"kind": "portal", "reading": "A portal where internet customers sign in.",
                "questions": [{"q": "Who signs in?", "options": ["Customers", "Staff", "Resellers"]},
                              {"q": "", "options": ["dropped"]},
                              {"q": "What do customers do?", "options": ["Pay bills", "See usage", "Raise complaints"]}]}
    monkeypatch.setattr(AR, "_ask_inner", inner)
    monkeypatch.setattr(AR, "draft", lambda *a, **k: (_ for _ in ()).throw(AssertionError("planned before asking")))
    v = AR.build_now(T, "Build the ISP portal", "", "ask-12345678")
    assert [q["q"] for q in v["questions"]] == ["Who signs in?", "What do customers do?"] and not v.get("id")
    assert v["questions"][1]["options"] == ["Pay bills", "See usage", "Raise complaints"] and v["kind"] == "portal"
    assert AC.read(T, "stage-ask-12345678")["steps"][-1]["label"] == "A few questions before the plan."
    assert seen == [AR.UNDERSTAND[:40]]                                       # one short read, no plan call


def test_answers_reach_the_plan_and_a_clear_ask_is_not_asked(ask_on, monkeypatch):
    from app.site import architect as AR
    from app.site import service as S
    got = {}

    def draft(tenant, words, conv="", logic_ask=None, quiet=False):
        got["words"] = words
        return {"id": "c1", "hash": "h", "number": 1}
    monkeypatch.setattr(AR, "_ask_inner", lambda *a, **k: (_ for _ in ()).throw(AssertionError("asked again")))
    monkeypatch.setattr(AR, "draft", draft)
    monkeypatch.setattr(AR, "approve", lambda *a, **k: {"site": "s1", "say": "ok"})
    monkeypatch.setattr(S, "_load", lambda sid: object())
    monkeypatch.setattr(S, "view", lambda row: {"id": "s1"})
    AR.build_now(T, "Build the ISP portal", "", "", [{"q": "Who signs in?", "a": "Customers; Staff"},
                                                    {"q": "Ignored", "a": ""}], True)
    assert got["words"].startswith("Build the ISP portal") and "- Who signs in? Customers; Staff" in got["words"]
    assert "Ignored" not in got["words"]
    long_ask = "Build " + " ".join(["a detailed portal requirement"] * 10)      # 40+ words: she already said it all
    AR.build_now(T, long_ask, "", "")
    assert got["words"] == long_ask[:2600]


def test_a_portal_is_a_sign_in_and_its_data_never_a_marketing_page():
    from app.site import architect as AR
    spec = AR.clean(json.loads(json.dumps(ISP_RAW)), "Build the ISP portal", "standard")
    assert spec["kind"] == "portal"                                           # her word 'portal' wins over 'lead_site'
    home = next(p for p in spec["pages"] if p["slug"] == "home")
    assert [x["type"] for x in home["sections"]][:2] == ["hero", "screen_signin"]
    inner = [p for p in spec["pages"] if p["for"] != "public"]
    assert inner and inner[0]["sections"][1]["type"] == "screen_dashboard" and spec["main_screen"] == inner[0]["slug"]
    plan = AR.site_plan(spec, {}, {"pages": []})
    h = plan["pages"][0]
    assert [x["type"] for x in h["sections"]][:3] == ["hero", "screen_signin", "screen_dashboard"]
    assert "NOT a marketing hero" in h["sections"][0]["design"] and plan["spec"]["kind"] == "portal"
    shop = AR.clean({**json.loads(json.dumps(ISP_RAW)), "kind": "shop"}, "a sweet shop website", "simple")
    assert shop["kind"] == "shop" and not any(p["for"] != "public" for p in shop["pages"])   # a brochure stays one


def test_the_design_is_the_ais_choice_from_her_words():
    from app.site import architect as AR
    from app.site import build as B
    d = AR.design_of(ISP_RAW["design"])
    assert d["fonts"] == "inter_inter" and d["palette"]["primary"] == "#1F5EFF" and d["base_px"] == 15.0
    bad = AR.design_of({"style": "nope", "fonts": "comic_sans", "palette": {"bg": "red"}, "base_px": 40, "scale": 3})
    assert bad == {}                                                          # nothing real = nothing kept
    ref = AR.design_ref({"design": d})
    assert ref["source"] == "ai" and ref["overrides"]["fonts"] == "inter_inter" and "15 px text" in ref["notes"]
    tk = B.tokens(ref["style"], "paper_ink", None, ref["overrides"])
    assert (tk["head"], tk["body"], tk["primary"], tk["bg"]) == ("Inter", "Inter", "#1F5EFF", "#F7F9FC")
    assert tk["fonts"] == "inter_inter" and tk["base_px"] == 15.0 and tk["scale"] == 1.18
    css = B.tokens_css(tk)
    assert "--fs-base:15.0px" in css and "--fs-h1:clamp(" in css
    plain = B.tokens("corporate_trust", "paper_ink")
    assert "--fs-base" not in B.tokens_css(plain)                             # no choice = the stylesheet's own sizes
    again = B.tokens("corporate_trust", "paper_ink", None, {**B.carry(tk), "primary": "#AA2200"})
    assert again["head"] == "Inter" and again["base_px"] == 15.0              # a colour edit keeps the type
    site_css = (Path(__file__).parents[1] / "app" / "site" / "assets" / "hoola-site.css").read_text()
    assert "font-size:var(--fs-base,clamp(16px" in site_css and "h1{font-size:var(--fs-h1," in site_css


def test_the_plan_prompt_asks_for_the_design_and_names_real_ids():
    from app.site import ai as AI
    from app.site import architect as AR
    sysp = AR._system()
    assert '"design": {' in sysp and "inter_inter: Inter / Inter" in sysp and "corporate_trust (Corporate trust)" in sysp
    assert "NOT a marketing site" in sysp and "@@" not in sysp
    assert AI.EFFORT["site_art"] == "xhigh"                                  # the plan thinks hard (reasoning on)


def test_look_one_is_built_from_the_ai_design(site_env, monkeypatch):
    from app.site import architect as AR
    from app.site import designq as DQ
    from app.site import service as S
    spec = AR.clean(json.loads(json.dumps(ISP_RAW)), "Build the ISP portal", "standard")
    seen = {}

    def new(*a, **k):
        seen["ref"] = DQ.PENDING.get()
        raise S.SiteError("stop here")
    monkeypatch.setattr(S, "new", new)
    monkeypatch.setattr(AR, "card", lambda t, ref: {"status": "waiting", "hash": "h", "data_none": True})

    class P:
        id, plan = "p1", json.dumps({"architect": {"spec": spec}})
    monkeypatch.setattr(AR, "_project", lambda t, ref: P)
    with pytest.raises(AR.ArchError):
        AR.approve(T, "p1", "h")
    assert seen["ref"]["source"] == "ai" and seen["ref"]["overrides"]["primary"] == "#1F5EFF"
    assert DQ.PENDING.get() is None                                           # nothing leaks to the next site


def test_a_failed_portal_plan_never_becomes_a_marketing_page(site_env, monkeypatch):
    from app.site import architect as AR
    from app.site import service as S
    monkeypatch.setattr(AR, "draft", lambda *a, **k: (_ for _ in ()).throw(AR.ArchError("timeout", 502)))
    monkeypatch.setattr(S, "new", lambda *a, **k: (_ for _ in ()).throw(AssertionError("library marketing pages")))
    with pytest.raises(AR.ArchError) as e:
        AR.build_now(T, "Build the ISP portal", "", "")
    assert e.value.code == 502 and "Nothing was built" in str(e.value)
    called = []
    monkeypatch.setattr(S, "new", lambda *a, **k: called.append(a) or {"id": "s1", "say": ""})
    AR.build_now(T, "a website for my sweet shop", "", "")                    # a plain website may still start plainly
    assert called


def test_the_questions_card_in_a_browser(arena_server, site_env):
    base, browser, key = arena_server
    errors, bodies = [], []
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))

    def sites(route):
        if route.request.method != "POST":
            return route.continue_()
        b = route.request.post_data_json or {}
        bodies.append(b)
        if not b.get("asked"):
            return route.fulfill(json={"questions": [{"q": "Who signs in?", "options": ["Customers", "Staff"]},
                                                     {"q": "What do customers do?", "options": ["Pay bills", "See usage"]}],
                                       "reading": "A portal where internet customers sign in.", "kind": "portal"})
        return route.fulfill(status=502, json={"detail": "stop the walk here"})
    page.route("**/api/sites", sites)
    page.goto(f"{base}/console/web#/")
    page.locator("#wsAsk").wait_for(timeout=20000)
    page.fill("#wsAsk", "Build the ISP portal")
    page.click("button.go")
    page.locator("#wsAskQ").wait_for(timeout=20000)
    assert page.locator("#wsAskQ fieldset").count() == 2 and "Nothing is planned yet" in page.inner_text("#wsPeek")
    assert page.locator("form.wsq").count() == 0                             # the old choices page never opens
    import os
    if os.environ.get("CONSOLE_SHOTS"):
        page.screenshot(path=os.path.join(os.environ["CONSOLE_SHOTS"], "v0988-questions.png"))
    page.click("#wsAskQ label.aqc:has-text('Customers')")
    page.click("#wsAskQ label.aqc:has-text('Pay bills')")
    page.fill("#wsAskQ input[name=t1]", "check data usage")
    page.click("#wsAskQ button[type=submit]")
    page.locator("#wsAsk").wait_for(timeout=20000)                            # the stub refused: back home, words kept
    assert len(bodies) == 2 and bodies[1]["asked"] is True and bodies[1]["brief"] == "Build the ISP portal"
    assert bodies[1]["qa"] == [{"q": "Who signs in?", "a": "Customers"},
                               {"q": "What do customers do?", "a": "Pay bills; check data usage"}]
    assert "Build the ISP portal" in page.input_value("#wsAsk")
    ctx.close()
    assert not errors or all("stop the walk" in x for x in errors), errors
