"""v0.999.34 SAB SECTION (built as 0.999.31 / 0.999.32) (P5 of docs/HOOLA_PROMPTING_PLAN.md): five more sections in Hoola Prompting - app, video,
music, marketing message, business document - each with its anatomy, code-read slots, engine wording (dialect),
starter recipes and its own checks. No model runs here."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-sab-section"
H = {"Authorization": f"Bearer {KEY}"}
NEW = ("app", "video", "music", "marketing", "doc")


@pytest.fixture
def pr(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    yield B
    get_settings.cache_clear()


def test_eight_sections_old_three_keep_their_place():
    from app.prompting import anatomy as A
    from app.prompting import dialect as D
    from app.prompting import ledger as L
    assert A.ORDER[:8] == ("web", "image", "script", "app", "video", "music", "marketing", "doc")
    assert L.SECTIONS == A.ORDER and set(D.RENDER) == set(A.ORDER) == set(D.DIALECT_V)
    for sec in NEW:
        assert 3 <= len(A.required(sec)) <= 4, sec
        for s in A.slots(sec):
            assert "?" in s["q"] and s["label"], (sec, s["key"])


@pytest.mark.parametrize("text,section", [
    ("ek kirana app banao android aur iphone, upi payment, home delivery", "app"),
    ("8 second video of chai being poured, slow push in, reel", "video"),
    ("reel video banao for my cafe", "video"),
    ("diwali jingle for my shop, female voice, hindi, 30 seconds", "music"),
    ("whatsapp message to my customers: flat 20% off till 15 nov", "marketing"),
    ("quotation pdf for ABC industries AMC Rs 45000", "doc"),
    ("leave application letter for my staff", "doc"),
    ("30 second reel script for coaching", "script"),            # the old three are read as before
    ("product reel banao", "script"),
    ("video ad script for a gym", "script"),
    ("diwali sale ka poster banao", "image"),
    ("website for my clinic with booking", "web"),
    ("a website with an app-like login for members", "web"),
    ("aaj mausam kaisa hai", ""),
])
def test_which_section(text, section):
    from app.prompting import brief as B
    assert B.guess_section(text) == section


def test_code_reads_each_new_section_for_certain():
    from app.prompting import brief as B
    assert B.code_slots("app", "kirana app, android aur iphone, upi payment, home delivery") == {
        "platform": "Android and iPhone", "money": "UPI to my account", "job": "Place an order"}
    assert B.code_slots("video", "8 second clip, slow push in, for a reel") == {
        "camera": "Slow push in", "size": "9:16", "length": "8 seconds"}
    m = B.code_slots("music", 'diwali jingle, female voice, hindi, 30 seconds, sing "Balaji ki mithai"')
    assert m == {"use": "Shop jingle", "mood": "Festive", "vocals": "Female voice", "language": "Hindi",
                 "lyrics": "Balaji ki mithai", "length": "30 seconds"}
    assert B.code_slots("marketing", "email newsletter to customers, call us")["channel"] == "Email"
    assert B.code_slots("doc", "a quotation as a word document") == {"kind": "Quotation", "format": "Word document"}


def test_each_dialect_locks_her_facts_and_never_sends(pr):
    from app.prompting import dialect as D
    app = D.render(pr.understand("t", "kirana app banao: android, upi payment, Rs 50 delivery charge"))
    assert app["run"]["to"] == "app" and app["run"]["label"] == "Open in App Studio" and "Rs 50" in app["prompt"]
    assert "money goes to my own account only" in app["prompt"] and app["dialect"] == "app-1"
    vid = D.render(pr.apply(pr.understand("t", "8 second clip for a reel, slow push in"),
                            {"subject": "a cup of masala chai", "action": "milk is poured in"}))
    assert vid["prompt"].startswith("A cup of masala chai - milk is poured in.") and "9:16" not in vid["prompt"]
    assert vid["fields"] == {"aspect": "9:16", "seconds": 8} and "price" in vid["run"]["text"]   # length + shape = settings
    mus = D.render(pr.understand("t", 'shop jingle, folk, happy, sing "Balaji ki mithai"'))
    assert 'LYRICS (sing exactly these words): "Balaji ki mithai"' in mus["prompt"] and mus["run"]["to"] == "chat"
    mkt = D.render(pr.understand("t", "whatsapp message to my regular customers: flat 20% off till 15 Nov"))
    assert "20%" in mkt["prompt"] and "15 Nov" in mkt["prompt"] and "Reply STOP" in mkt["prompt"]
    assert "Do not send it" in mkt["prompt"] and mkt["run"]["text"].startswith("Draft this message (do not send)")
    doc = D.render(pr.understand("t", "quotation pdf for ABC Industries, AMC for 10 ACs Rs 45,000"))
    assert doc["run"]["text"].startswith("Make this quotation as a PDF") and "Rs 45,000" in doc["prompt"]
    assert "never make one up" in doc["prompt"]


def test_section_checks_say_why(pr):
    def reasons(text, **set_):
        b = pr.understand("t", text)
        if set_:
            b = pr.apply(b, set_)
        return " ".join(r["text"] for r in pr.score(b)["reasons"])
    assert "4 to 10 seconds" in reasons("a 30 second video clip of my shop")
    assert "ONE thing" in reasons("video clip of my shop", action="the door opens and then people walk in")
    assert "instrumental" in reasons('instrumental reel music, sing "hello"')
    assert "no end date" in reasons("whatsapp message: flat 20% off on sarees")
    assert "no end date" not in reasons("whatsapp message: flat 20% off on sarees till 15 Nov")
    assert "Nothing is sent from here" in reasons("whatsapp message: flat 20% off till 15 Nov")
    assert "A quotation needs prices" in reasons("a quotation for AC servicing")
    assert "never holds or moves it" in reasons("shop app with upi payment")
    assert "Picture engines handle 'no" in reasons("video clip of a street, no cars")


def test_recipes_for_every_new_section(pr):
    from app.prompting import dialect as D
    from app.prompting import recipes as R
    assert R.check() == [] and len(R.RECIPES) >= 40
    for sec in NEW:
        mine = [r for r in R.RECIPES if r["section"] == sec]
        assert len(mine) >= 4, sec
        assert R.listing(sec)["items"] and all(x["section"] == sec for x in R.listing(sec)["items"])
        for r in mine:                                    # every starter, filled with its own examples, renders and scores
            b = R.use(r["id"], {x["key"]: x["eg"] for x in r["blanks"]})["brief"]
            assert D.render(b)["prompt"] and pr.score(b)["score"] >= 70, r["id"]
    b = R.use("mkt-wa-offer", {"business": "Balaji", "offer": "Flat 30% Off"})["brief"]     # an empty blank = a question
    assert "offer" not in b["slots"] and any(q["key"] == "offer" for q in b["questions"])


def test_ledger_counts_the_new_sections_and_app_studio_claims(pr):
    from app import main as M
    from app.db import session
    from app.prompting import dialect as D
    from app.prompting import ledger as L
    b = pr.understand("t1", "kirana app banao: order and home delivery, upi payment, android")
    text = D.render(b)["run"]["text"]
    rid = L.hand("t1", text, b)
    assert rid and "app" in L.numbers("t1")["sections"]
    M._pled_app("t1", text, {"id": "app_test_1"})              # the App Studio started on that prompt
    with session() as s:
        r = s.get(L.PromptRun, rid)
        assert r.status == "ready" and " app_test_1 " in r.refs and r.section == "app" and r.dialect == "app-1"
    M._pled("t1", "app_test_1", "deleted")
    with session() as s:
        assert s.get(L.PromptRun, rid).grade == "dropped"
    M._pled_app("t1", "an app nobody prompted for on the prompting page", {"id": "app_test_2"})    # unclaimed = nothing


def test_page_and_app_studio_wiring():
    js = (CON / "prompting.js").read_text()
    for sec in NEW:
        assert f"{sec}: I(" in js and f"{sec}: '" in js, sec          # an icon and a placeholder for every section
    assert "'hoola.prompt.toApp', '/console/apps'" in js
    app = (CON / "appstudio.js").read_text()
    assert "localStorage.getItem('hoola.prompt.toApp')" in app and "localStorage.removeItem('hoola.prompt.toApp')" in app
    main = (REPO / "server" / "app" / "main.py").read_text()
    assert "_pled_app, tenant" in main and '_pled(tenant, ref, "deleted")' in main


def test_new_sections_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """A marketing ask on the page: the right section, her offer locked, the end-date check, the chat hand-off;
    then an app ask goes to the App Studio box and nothing is built."""
    base, browser, key = arena_server
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/prompting")
    pg.wait_for_selector("#hpText")
    assert pg.locator(".hp-nav").count() == 19
    pg.fill("#hpText", "whatsapp message to my regular customers: flat 20% off on sarees")
    pg.click("#hpAsk button[type=submit]")
    pg.wait_for_selector("#hpBrief .hpi-chip")
    assert "Marketing message" in pg.inner_text(".hp-top h1") and "20%" in pg.inner_text(".hpi-facts")
    assert "no end date" in pg.inner_text("#hpMain") and pg.inner_text("#hpRun") == "Put in the Hoola chat"
    pg.goto(base + "/console/prompting#/s/app")
    pg.wait_for_selector("#hpText")
    pg.fill("#hpText", "kirana app banao: order, home delivery, upi payment, android")
    pg.click("#hpAsk button[type=submit]")
    pg.wait_for_selector("#hpRun")
    assert pg.inner_text("#hpRun") == "Open in App Studio" and "App Studio" in pg.inner_text("#hpMain")
    pg.click("#hpRun")
    pg.wait_for_url("**/console/apps**")
    pg.wait_for_selector("#asAsk")
    assert "kirana app banao" in pg.input_value("#asAsk")
    assert pg.evaluate("localStorage.getItem('hoola.prompt.toApp')") is None
    assert not [e for e in errs if "prompting" in e or "appstudio" in e], errs
