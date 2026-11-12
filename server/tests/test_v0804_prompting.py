"""v0.804 HOOLA PROMPTING P1-P3 (built as 0.796) (docs/HOOLA_PROMPTING_PLAN.md): the understanding engine (a prompt = a BRIEF: her
facts locked, a guess labelled a guess, nothing silent, no magic phrase), the Improve button, and the Prompting page.
No model runs here: the one small fill call is replaced by a fake."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-prompting"
H = {"Authorization": f"Bearer {KEY}"}


def fake_model(system, prompt):
    """A model that proposes slots - including things it must NOT be allowed to add."""
    if "a picture" in prompt:
        return {"subject": {"value": "a brass diya with marigold flowers", "from": "guess"},
                "style": {"value": "Festive poster", "from": "her"},
                "scene": {"value": "big sale, 50% off, call 9812345678", "from": "her"},        # invented numbers
                "light": {"value": "masterpiece, 8k, best quality", "from": "guess"}}          # magic words
    if "a website" in prompt:
        return {"what": {"value": "a sweet shop", "from": "her"}, "who": {"value": "local families", "from": "guess"},
                "style": {"value": "warm and traditional", "from": "her"}}                     # she never said that
    return {"audience": {"value": "parents of class 10 students", "from": "guess"},
            "message": {"value": "small batches so every child is noticed", "from": "guess"}}


@pytest.fixture
def pr(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(B, "ASK", [fake_model])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    yield B
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------- P1: the engine
def test_section_is_read_from_her_words(pr):
    assert pr.guess_section("mere sweet shop ki website banao") == "web"
    assert pr.guess_section("diwali sale ka poster banao") == "image"
    assert pr.guess_section("coaching class ke liye reel ki script likho") == "script"
    assert pr.guess_section("write a youtube video script about my bakery website") == "script"
    assert pr.guess_section("aaj mausam kaisa hai") == ""


def test_her_facts_are_locked_and_copied_exactly(pr):
    f = pr.facts_of('Kaju Katli Rs 880 per kg, flat 30% off till 15 Nov, open 8 am to 10 pm, call 9812345678, write "Shubh Diwali"')
    got = {x["kind"]: x["text"] for x in f}
    assert got["price"] == "Rs 880" and got["percent"] == "30%" and got["phone"] == "9812345678"
    assert got["words"] == "Shubh Diwali" and "8 am to 10 pm" in got["time"] and got["date"].lower().startswith("15 nov")
    b = pr.understand("t", 'diwali poster, likho "Flat 30% Off"', use_model=False)
    assert b["slots"]["words"] == {"value": "Flat 30% Off", "source": "her_words"}
    from app.prompting import dialect as D
    assert '"Flat 30% Off"' in D.render(b)["prompt"]


def test_code_reads_shape_length_platform_language(pr):
    assert pr.code_slots("image", "instagram story ke liye offer image")["size"] == "9:16"
    assert pr.code_slots("image", "youtube thumbnail banao red and yellow")["colours"] == "red, yellow"
    s = pr.code_slots("script", "gym ke liye 20 second ki instagram reel script likho")
    assert s["length"] == "20 seconds" and s["platform"] == "Instagram reel" and s["language"] == "Hinglish"
    assert pr.code_slots("script", "write a 2 minute youtube video script")["length"] == "120 seconds"
    assert pr.code_slots("web", "salon ka site jisme booking ho")["action"] == "Book an appointment"


def test_the_model_is_checked_by_code(pr):
    """A value the model says is HERS must share its words with her text; a number she never wrote drops the value;
    praise words drop the value. The model can suggest, never add a fact."""
    b = pr.understand("t", "diwali sale ka poster banao")
    s = b["slots"]
    assert s["subject"]["source"] == "hoola_guess"                 # labelled a suggestion
    assert s["style"] == {"value": "Festive poster", "source": "her_words"}      # 'poster' is in her words
    assert "scene" not in s and "light" not in s                   # invented numbers / magic words: dropped
    assert [q["key"] for q in b["questions"]] == ["subject"] and b["questions"][0]["suggested"]
    w = pr.understand("t", "mere sweet shop ki website banao")
    assert w["slots"]["what"]["source"] == "her_words" and w["slots"]["who"]["source"] == "hoola_guess"
    assert w["slots"]["style"]["source"] == "hoola_guess"          # the model claimed 'her'; she never said it
    assert w["missing"] == ["action"] and len(w["questions"]) <= 3


def test_no_model_still_gives_a_brief(pr, monkeypatch):
    def down(*a):
        raise RuntimeError("model down")
    monkeypatch.setattr(pr, "ASK", [down])
    b = pr.understand("t", "gym ke liye 30 second ki reel script")
    assert b["section"] == "script" and b["slots"]["length"]["value"] == "30 seconds"
    assert set(b["missing"]) == {"audience", "message", "cta"} and len(b["questions"]) == 3


def test_her_answers_and_removals(pr):
    b = pr.understand("t", "mere sweet shop ki website banao")
    b2 = pr.apply(b, {"action": "Message on WhatsApp", "who": "families buying for festivals"}, ["style"])
    assert b2["slots"]["action"]["source"] == "her_answer" and b2["slots"]["who"]["source"] == "her_answer"
    assert "style" not in b2["slots"] and b2["missing"] == [] and b2["questions"] == []
    assert b2["intent"] == b["intent"] and b2["hash"] != b["hash"]
    assert pr.score(b2)["score"] > pr.score(b)["score"]
    b3 = pr.apply(b2, {"content": "Kaju Katli Rs 880 per kg"})
    assert any(f["text"] == "Rs 880" for f in b3["facts"])          # a fact in her answer is locked too
    junk = pr.validate({"section": "web", "intent": "x" * 5000, "slots": {"evil": {"value": "x"}, "what": {"value": "a shop", "source": "root"}}})
    assert list(junk["slots"]) == ["what"] and junk["slots"]["what"]["source"] == "hoola_guess" and len(junk["intent"]) == 2000
    with pytest.raises(ValueError):
        pr.validate({"section": "nope"})


def test_score_is_code_with_reasons(pr):
    b = pr.understand("t", "poster banao, no people, best quality 8k, dark background but bright white look", use_model=False)
    sc = pr.score(b)
    texts = " | ".join(r["text"] for r in sc["reasons"])
    assert "Main subject: missing" in texts and "pull against each other" in texts
    assert "do not help" in texts and "no people" in texts and sc["note"].startswith("This counts")
    full = pr.apply(b, {"subject": "a brass diya", "style": "Festive poster", "size": "4:5", "colours": "black and gold",
                        "composition": "diya low, space above", "light": "warm glow"})
    assert pr.score(full)["score"] > sc["score"] + 30
    long_words = pr.apply(full, {"words": "one two three four five six seven eight nine ten eleven twelve thirteen"})
    assert any("12 words" in r["text"] for r in pr.score(long_words)["reasons"])


def test_dialects_add_nothing_she_did_not_see(pr):
    from app.prompting import dialect as D
    w = pr.apply(pr.understand("t", "mere sweet shop ki website banao, Kaju Katli Rs 880 per kg"), {"action": "Message on WhatsApp"})
    out = D.render(w)
    assert out["prompt"].startswith("mere sweet shop ki website banao") and "FACTS (use exactly, invent nothing else): Rs 880" in out["prompt"]
    assert out["run"]["to"] == "web" and out["engine"] == "Web Studio"
    s = pr.apply(pr.understand("t", "coaching ke liye 30 second ki reel script"), {"cta": "Call now"})
    so = D.render(s)
    assert so["fields"]["length"] == "30 seconds" and "FACTS: none given - say no price, number or offer." in so["prompt"]
    assert so["run"]["to"] == "chat" and so["run"]["text"].startswith("Write this script in Hinglish:")
    i = D.render(pr.understand("t", "square logo for my chai shop", use_model=False))
    assert "No text, letters or logo anywhere" in i["prompt"] and i["fields"]["aspect"] == "1:1"
    for o in (out, so, i):
        assert not any(m in o["prompt"].lower() for m in pr.MAGIC)


def test_her_business_fills_blanks_and_is_labelled(pr, monkeypatch):
    from app.prompting import context as C
    monkeypatch.setattr(C, "known", lambda t: {"name": "Balaji Sweets", "tagline": "since 1984", "colours": ["#B8860B", "#111111"],
                                                "tone": "warm", "language": "", "about": "", "items": []})
    assert pr.understand("t", "website banao", use_model=False)["slots"]["what"] == {"value": "Balaji Sweets - since 1984", "source": "her_memory"}
    assert pr.understand("t", "poster banao", use_model=False)["slots"]["colours"]["source"] == "her_memory"
    assert pr.understand("t", "red poster banao", use_model=False)["slots"]["colours"] == {"value": "red", "source": "her_words"}   # her words win


def test_recipes_are_valid_and_never_invent(pr):
    from app.prompting import recipes as R
    assert R.check() == [] and len(R.RECIPES) >= 18
    got = R.use("img-festival-offer", {"festival": "Diwali", "business": "Balaji Sweets", "offer": "Flat 30% Off"})["brief"]
    assert got["slots"]["words"] == {"value": "Diwali Sale - Flat 30% Off", "source": "recipe"} and got["recipe_id"] == "img-festival-offer"
    empty = R.use("img-festival-offer", {"festival": "Diwali"})["brief"]
    assert "words" not in empty["slots"] and "[business]" in empty["intent"]        # an empty blank is left out, never made up
    web = R.listing("web", "bakery")
    assert web["items"] and web["items"][0]["id"].startswith("web:")
    ready = R.use(web["items"][0]["id"])["ready"]
    assert ready["run"]["to"] == "web" and len(ready["prompt"]) > 300
    with pytest.raises(ValueError):
        R.use("nope")


# ---------------------------------------------------------------- the routes
def test_routes_end_to_end(pr):
    c = client()
    assert c.get("/api/prompting/sections").status_code == 401
    from app.main import APP_VERSION
    page = c.get("/console/prompting").text                      # stamps follow the running version, whatever the file says
    assert page.count(f"?v={APP_VERSION}") == 5 and page.count("?v=") == 5
    secs = c.get("/api/prompting/sections", headers=H).json()
    assert [s["key"] for s in secs["sections"]] == ["web", "image", "script"]
    assert c.post("/api/prompting/understand", headers=H, json={"text": "aaj mausam kaisa hai"}).json() == {"choose_section": True}
    assert c.post("/api/prompting/understand", headers=H, json={"text": "a"}).status_code == 422
    pack = c.post("/api/prompting/understand", headers=H, json={"text": "diwali sale ka poster banao"}).json()
    assert pack["brief"]["section"] == "image" and pack["out"]["prompt"] and 0 < pack["score"]["score"] < 100
    pack2 = c.post("/api/prompting/compile", headers=H, json={"brief": pack["brief"], "set": {"subject": "a brass diya"}}).json()
    assert pack2["brief"]["slots"]["subject"]["source"] == "her_answer" and pack2["score"]["score"] > pack["score"]["score"]
    assert c.post("/api/prompting/compile", headers=H, json={"brief": {"section": "x"}}).status_code == 422
    assert c.get("/api/prompting/recipes?section=script", headers=H).json()["items"]
    used = c.post("/api/prompting/recipes/use", headers=H, json={"recipe_id": "scr-shop-intro", "values": {"business": "Roop Salon", "city": "Pune"}}).json()
    assert used["brief"]["section"] == "script" and "Roop Salon" in used["out"]["prompt"]
    assert c.post("/api/prompting/recipes/use", headers=H, json={"recipe_id": "zzz"}).status_code == 404
    saved = c.post("/api/prompting/saved", headers=H, json={"brief": pack2["brief"]}).json()
    assert saved["id"].startswith("pr") and c.get("/api/prompting/saved", headers=H).json()["items"][0]["id"] == saved["id"]
    one = c.get(f"/api/prompting/saved/{saved['id']}", headers=H).json()
    assert one["brief"]["slots"]["subject"]["value"] == "a brass diya" and one["out"]["prompt"]
    assert c.delete(f"/api/prompting/saved/{saved['id']}", headers=H).json() == {"ok": True}
    assert c.get(f"/api/prompting/saved/{saved['id']}", headers=H).status_code == 404


def test_saved_prompts_stay_with_their_owner(pr):
    from app.prompting import store as S
    b = pr.understand("a", "poster banao", use_model=False)
    row = S.save("tenant_a", b, "p")
    assert S.get("tenant_b", row["id"]) is None and S.listing("tenant_b") == [] and not S.delete("tenant_b", row["id"])
    assert S.get("tenant_a", row["id"])["brief"]["section"] == "image"


def test_switch_off_hides_page_and_routes(pr, monkeypatch):
    monkeypatch.setenv("PROMPTING_PAGE", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    c = client()
    assert c.get("/api/prompting/sections", headers=H).status_code == 404
    assert c.get("/console/prompting", follow_redirects=False).status_code == 307
    assert c.get("/api/console/config").json()["prompting"] is False


# ---------------------------------------------------------------- P2 + P3: the files are wired
def test_page_and_button_are_wired(pr):
    c = client()
    page = c.get("/console/prompting")
    assert page.status_code == 200 and "prompting.js" in page.text and "improve.js" in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert c.get("/api/console/config").json()["prompting"] is True
    v2, v2js = (CON / "v2.html").read_text(), (CON / "v2.js").read_text()
    assert 'id="impBtn"' in v2 and "console/improve.js" in v2 and "console/improve.css" in v2
    assert "['prompting', 'Hoola Prompting']" in v2js and "location.assign('/console/prompting')" in v2js
    assert "IMP_BACK" in v2js and "Undo" in v2js                    # her own words come back exactly
    ws, wsh = (CON / "webstudio.js").read_text(), (CON / "webstudio.html").read_text()
    assert "data-improve" in ws and "hoola.prompt.toWeb" in ws and "console/improve.js" in wsh
    assert "HoolaImprove.ui.open(q.value, {section: 'image'" in (CON / "studio.js").read_text()
    imp = (CON / "improve.js").read_text()
    assert "Keep mine" in imp and "/api/prompting/compile" in imp and "eval(" not in imp and "innerHTML = text" not in imp
    for f in ("improve.css", "prompting.css"):                      # CRISP TEXT rule: no blur, in every file
        assert "backdrop-filter" not in (CON / f).read_text()


def test_the_page_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """Home -> Improve -> the workbench (chips by source, a question, the score, the prompt) -> her answer raises the
    score -> Save -> My prompts -> Open in Web Studio hands the text over; then the console's Improve button and Undo."""
    import os
    base, browser, key = arena_server
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(B, "ASK", [fake_model])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "", "about": "", "items": []})
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"{e} @ {pg.url}"))
    shots = os.environ.get("HOOLA_SHOTS")
    snap = (lambda n: (pg.wait_for_timeout(350), pg.screenshot(path=f"{shots}/prompting_{n}.png"))) if shots else (lambda n: None)

    pg.goto(base + "/console/prompting")
    pg.wait_for_selector("#hpText")
    assert pg.locator(".hp-nav").count() == 8 and pg.locator(".hp-card").count() >= 3
    snap("1_home")
    pg.fill("#hpText", "mere sweet shop ki website banao, Kaju Katli Rs 880 per kg")
    pg.click("#hpAsk button[type=submit]")
    pg.wait_for_selector("#hpBrief .hpi-chip")
    assert pg.locator(".hpi-chip.s-her_words").count() >= 1 and pg.locator(".hpi-chip.s-hoola_guess").count() >= 1
    assert pg.locator(".hpi-chip.miss").count() == 1 and "Rs 880" in pg.inner_text(".hpi-facts")
    before = int(pg.inner_text(".hpi-num span"))
    assert "Rs 880" in pg.inner_text(".hpi-out") and pg.inner_text("#hpRun") == "Open in Web Studio"
    snap("2_workbench")
    pg.click(".hpi-q .hpi-opt >> text=Message on WhatsApp")
    pg.wait_for_selector(".hpi-chip.miss", state="detached")
    assert int(pg.inner_text(".hpi-num span")) > before and "Message on WhatsApp" in pg.inner_text(".hpi-out")
    pg.click(".hpi-chip.s-hoola_guess >> nth=0")                    # a suggestion she does not want: remove it
    pg.wait_for_selector(".hpi-edit")
    guesses = pg.locator(".hpi-chip.s-hoola_guess").count()
    pg.click(".hpi-edit [data-drop]")
    pg.wait_for_selector(".hpi-edit", state="detached")
    assert pg.locator(".hpi-chip.s-hoola_guess").count() == guesses - 1
    snap("3_answered")
    box = pg.evaluate("(() => { const m = document.querySelector('#hpMain'); return m.scrollWidth <= m.clientWidth + 1; })()")
    assert box, "the workbench overflows sideways"
    pg.click("#hpSave")
    pg.wait_for_selector('.hp-top .hp-tag >> text="Saved"')
    pg.goto(base + "/console/prompting#/saved")
    pg.wait_for_selector(".hp-rowi")
    assert pg.locator(".hp-rowi").count() == 1
    pg.click("[data-open]")
    pg.wait_for_selector("#hpRun")
    pg.goto(base + "/console/prompting#/recipes")
    pg.wait_for_selector(".hp-card")
    pg.click(".hp-card >> text=Festival offer poster")
    pg.wait_for_selector("#hpFill")
    pg.fill("#bl_festival", "Diwali")
    pg.fill("#bl_business", "Balaji Sweets")
    pg.fill("#bl_offer", "Flat 30% Off")
    snap("4_recipe")
    pg.click("#hpFill button[type=submit]")
    pg.wait_for_selector("#hpBrief .hpi-chip.s-recipe")
    assert '"Diwali Sale - Flat 30% Off"' in pg.inner_text(".hpi-out") and pg.inner_text("#hpRun") == "Put in the Hoola chat"
    snap("5_recipe_bench")
    pg.click("#hpRun")                                              # hands the text to the chat box; nothing is sent
    pg.wait_for_url("**/console/")
    assert not errs, errs

    # the phone width: nothing sideways, the box still usable
    ph = browser.new_context(viewport={"width": 390, "height": 800})
    ph.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p2 = ph.new_page()
    p2.goto(base + "/console/prompting")
    p2.wait_for_selector("#hpText")
    assert p2.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    if shots:
        p2.screenshot(path=f"{shots}/prompting_6_phone.png")
    ph.close()

    # the Improve sheet on its own (the piece the chat box, Web Studio and Create all use) + Undo keeps her words exactly
    pg.goto(base + "/console/prompting")
    pg.wait_for_selector("#hpText")
    mine = "diwali sale ka poster banao"
    used = pg.evaluate("""async (mine) => { const out = {};
        const api = async (m, p, b) => { const r = await fetch(p, {method: m, headers: {Authorization: 'Bearer ' + localStorage.getItem('hoola.console.token'), 'Content-Type': 'application/json'}, body: b === undefined ? undefined : JSON.stringify(b)}); return r.json(); };
        const ui = window.HoolaImprove({api, esc: s => String(s).replace(/[&<>"']/g, c => '&#' + c.charCodeAt(0) + ';'), toast() {}});
        window.__done = ui.open(mine, {onUse: (t, p) => { window.__used = t; window.__sec = p.brief.section; }}); return true; }""", mine)
    assert used
    pg.wait_for_selector(".hpi-sheet .hpi-chip")
    assert pg.inner_text(".hpi-hers") == mine and pg.locator(".hpi-sheet [data-use]").is_enabled()
    snap("7_sheet")
    pg.keyboard.press("Escape")                                     # Keep mine: nothing changes
    pg.wait_for_selector(".hpi-sheet", state="detached")
    assert pg.evaluate("window.__used") is None
    pg.evaluate("(mine) => { window.__done = window.HoolaImprove.ui.open(mine, {onUse: (t, p) => { window.__used = t; window.__sec = p.brief.section; }}); }", mine)
    pg.wait_for_selector(".hpi-sheet .hpi-chip")
    pg.click(".hpi-sheet [data-use]")
    pg.wait_for_selector(".hpi-sheet", state="detached")
    assert pg.evaluate("window.__sec") == "image" and "brass diya" in pg.evaluate("window.__used")
    assert not errs, errs
    ctx.close()


def test_improve_button_in_the_console_and_the_web_studio(arena_server, monkeypatch):  # noqa: F811
    """The chat box: Improve opens the sheet, Use replaces her text, Undo puts her own words back byte for byte, and the
    sidebar has the Hoola Prompting row. The Web Studio: the same sheet on its home box, and a prompt handed over from
    the Prompting page lands in the box without being sent."""
    import os
    base, browser, key = arena_server
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(B, "ASK", [fake_model])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "", "about": "", "items": []})
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"{e} @ {pg.url}"))
    shots = os.environ.get("HOOLA_SHOTS")
    pg.goto(base + "/console/")
    pg.wait_for_selector("#impBtn:not([hidden])")
    assert pg.locator('.sn[data-v="prompting"]').count() == 1
    mine = "diwali sale ka poster banao  "                           # trailing spaces: Undo must keep them
    pg.fill("#msg", mine)
    pg.click("#impBtn")
    pg.wait_for_selector(".hpi-sheet .hpi-chip")
    if shots:
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{shots}/prompting_8_console_sheet.png")
    pg.click(".hpi-sheet [data-use]")
    pg.wait_for_selector(".hpi-sheet", state="detached")
    used = pg.input_value("#msg")
    assert used.startswith("Make this picture") and "brass diya" in used and pg.inner_text("#impTxt") == "Undo"
    pg.click("#impBtn")
    assert pg.input_value("#msg") == mine and pg.inner_text("#impTxt") == "Improve"
    pg.fill("#msg", "hello")
    pg.click("#impBtn")                                              # not a web / picture / script ask: she chooses, or keeps hers
    pg.wait_for_selector(".hpi-sheet .hpi-pick")
    pg.click(".hpi-sheet .hpi-foot [data-close]")
    pg.wait_for_selector(".hpi-sheet", state="detached")
    assert pg.input_value("#msg") == "hello"

    pg.evaluate("localStorage.setItem('hoola.prompt.toWeb', 'A website for Balaji Sweets in Akola')")
    pg.goto(base + "/console/web")
    pg.wait_for_selector("#wsAsk")
    assert pg.input_value("#wsAsk") == "A website for Balaji Sweets in Akola"
    assert pg.evaluate("localStorage.getItem('hoola.prompt.toWeb')") is None
    pg.fill("#wsAsk", "mere sweet shop ki website banao")
    pg.click("[data-improve]")
    pg.wait_for_selector(".hpi-sheet .hpi-chip")
    assert "Web Studio" in pg.inner_text(".hpi-sheet h4")
    if shots:
        pg.wait_for_timeout(300)
        pg.screenshot(path=f"{shots}/prompting_9_webstudio_sheet.png")
    pg.click(".hpi-sheet .hpi-opt >> text=Message on WhatsApp")
    pg.wait_for_selector(".hpi-sheet .hpi-chip.miss", state="detached")
    pg.click(".hpi-sheet [data-use]")
    pg.wait_for_selector(".hpi-sheet", state="detached")
    v = pg.input_value("#wsAsk")
    assert v.startswith("mere sweet shop ki website banao") and "THE ONE KEY ACTION: Message on WhatsApp." in v
    assert pg.inner_text("[data-improve]") == "Undo"
    pg.click("[data-improve]")
    assert pg.input_value("#wsAsk") == "mere sweet shop ki website banao"
    assert not errs, errs
    ctx.close()


def test_first_visit_race_on_the_connectors_user_row(env):
    """Found while wiring the Improve button: the Connectors page loads its lists together, and on her FIRST visit two
    requests both created her bazar user row - the loser answered 500. The loser now reads the row instead."""
    from app.bazar import service as BS
    from app.bazar.db import User
    from app.db import session
    with session() as s:
        BS.ensure_user(s, "race_t")
    with session() as s:
        real_get, seen = s.get, []

        def get(model, key, *a, **k):               # this request looked a moment before the other one committed
            if model is User and not seen:
                seen.append(1)
                return None
            return real_get(model, key, *a, **k)
        s.get = get
        u = BS.ensure_user(s, "race_t")
        assert u is not None and u.id == "race_t"
    with session() as s:
        assert s.get(User, "race_t") is not None


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.854.0"
    assert "0.854.0+853" in (REPO / "pubspec.yaml").read_text()
