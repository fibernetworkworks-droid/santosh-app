"""v0.999.36 SEEKHO (P9 of docs/HOOLA_PROMPTING_PLAN.md): short lessons made from HER OWN prompts, one idea each, her
line + a better way written by code; real before / after only from her own results and compares, else said to be Hoola's
starter guidance; her read ('Got it' / 'Not useful') hides a lesson. No model runs here."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-seekho"
H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def ln(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    from app.prompting import learn as LN
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    yield LN
    get_settings.cache_clear()


def ids(ln, text, section=""):
    from app.prompting import brief as B
    return {x["id"]: x for x in ln.on_brief(B.understand("t", text, section))}


def test_lessons_from_her_own_words(ln):
    got = ids(ln, "a premium diwali poster, no people, 8k best quality, flat 30% off")
    assert set(got) == {"vague:premium", "magic", "negative", "offer_date"}            # 'best' inside 'best quality' = magic only
    assert got["vague:premium"]["hers"].startswith("a premium diwali poster")
    assert got["vague:premium"]["instead"] == "Instead of 'premium': black and gold, a serif heading, lots of empty space."
    assert "no people" in got["negative"]["instead"] and "till 15 Nov" in got["offer_date"]["instead"]
    s = ids(ln, "a catchy reel script for everyone about our sale and also a poster and also a website")
    assert {"vague:catchy", "everyone", "one_ask"} <= set(s)
    assert "first 3 seconds" in s["vague:catchy"]["instead"]                           # the tip fits the kind of prompt
    w = ids(ln, "a premium website for my clinic")
    assert "serif heading, wide margins" in w["vague:premium"]["instead"]
    assert ids(ln, "flat 30% off till 15 Nov on kaju katli, a poster in gold and maroon") == {}   # a clear prompt teaches nothing
    assert "offer_date" not in ids(ln, "whatsapp message: flat 20% off till 15 nov")
    long_words = ids(ln, 'a poster with the words "Grand Diwali Sale on all sweets and dry fruits this week only at our new shop"')
    assert "poster_words" in long_words


def test_the_same_part_missing_again_and_again(ln):
    from app.prompting import brief as B
    from app.prompting import dialect as D
    from app.prompting import store as S
    for t in ("a 30 second reel for my salon", "a reel for my bakery opening", "an instagram reel for diwali", "a reel about our new menu"):
        b = B.understand("t1", t, "script")
        S.save("t1", b, D.render(b)["prompt"])
    p = ln.page("t1")
    miss = [x for x in p["lessons"] if x["id"].startswith("missing:script:")]
    assert p["from"] == 4 and miss and miss[0]["idea"].startswith("4 of your 4 saved script prompts have no")
    assert all(x["starter"] and "starter guidance" in x["basis"] for x in p["lessons"])        # no record yet = said so
    assert ln.page("t2")["lessons"] == [] and "Save a few prompts" in ln.page("t2")["note"]


def test_real_numbers_only_from_her_own_record(ln):
    from app.db import now, session
    from app.prompting import compare as CM
    from app.prompting import ledger as L
    assert ln.evidence("t1", "script", "hook") is None
    L.ensure_table()
    with session() as s:
        for i in range(16):
            has = i < 8
            s.add(L.PromptRun(id=f"prn_e{i}", tenant_id="t1", section="script",
                              slots=json.dumps({"hook": "her_answer"} if has else {"hook": "hoola_guess"}),
                              grade=("kept" if (i < 7 if has else i < 10) else "redone"), status="settled",
                              handed_at=now() - timedelta(days=2)))
    ev = ln.evidence("t1", "script", "hook")
    assert ev["ledger"]["with"] == {"kept": 7, "of": 8} and ev["ledger"]["without"] == {"kept": 2, "of": 8}
    assert ev["ledger"]["say"] == "With it, 7 of 8 of your results were kept; without it, 2 of 8."   # a guess is NOT 'with it'
    assert ln.evidence("t2", "script", "hook") is None                                            # someone else's record
    CM.ensure_table()
    with session() as s:
        for i, pick in enumerate(("a", "a", "b")):
            s.add(CM.PromptCompare(id=f"pcm_e{i}", tenant_id="t1", section="image", a_slots=json.dumps({"light": "her_answer"}),
                                   b_slots="{}", pick=pick))
    assert ln.evidence("t1", "image", "light")["compare"]["say"] == "In your own compares, the prompt that had it won 2 of 3 times."
    assert ln.for_brief("t1", __import__("app.prompting.brief", fromlist=["x"]).validate(
        {"section": "script", "intent": "a catchy reel", "slots": {}}))[0]["id"] == "vague:catchy"


def test_her_read_hides_a_lesson(ln):
    from app.db import now, session
    from app.prompting import brief as B
    b = B.understand("t1", "a premium diwali poster")
    assert [x["id"] for x in ln.for_brief("t1", b)] == ["vague:premium"]
    ln.mark("t1", "vague:premium", "got_it")
    assert ln.for_brief("t1", b) == [] and ln.for_brief("t2", b)                               # only hers is hidden
    with session() as s:                                                                       # 'got it' comes back after 30 days
        s.get(ln.LessonSeen, "t1:vague:premium").at = now() - timedelta(days=31)
    assert ln.for_brief("t1", b)
    ln.mark("t1", "vague:premium", "not_useful")
    with session() as s:
        s.get(ln.LessonSeen, "t1:vague:premium").at = now() - timedelta(days=400)
    assert ln.for_brief("t1", b) == []                                                         # not useful = gone for good
    with pytest.raises(ValueError):
        ln.mark("t1", "vague:premium", "love it")


def test_routes(ln):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.get("/api/prompting/learn").status_code == 401
    b = c.post("/api/prompting/understand", headers=H, json={"text": "a premium diwali poster, no people"}).json()["brief"]
    got = c.post("/api/prompting/learn/brief", headers=H, json={"brief": b}).json()["lessons"]
    assert {x["id"] for x in got} == {"vague:premium", "negative"}
    c.post("/api/prompting/saved", headers=H, json={"brief": b})
    page = c.get("/api/prompting/learn", headers=H).json()
    assert page["from"] == 1 and {x["id"] for x in page["lessons"]} == {"vague:premium", "negative"}
    assert c.put("/api/prompting/learn/negative", headers=H, json={"state": "not_useful"}).json()["state"] == "not_useful"
    after = c.get("/api/prompting/learn", headers=H).json()
    assert [x["id"] for x in after["lessons"]] == ["vague:premium"] and after["not_useful"] == 1 and after["hidden"] == 1
    assert c.put("/api/prompting/learn/negative", headers=H, json={"state": "maybe"}).status_code == 422
    assert c.post("/api/prompting/learn/brief", headers=H, json={"brief": {"section": "x"}}).status_code == 422


def test_page_wiring():
    js = (CON / "prompting.js").read_text()
    for needle in ("#/learn", "nav('learn'", "Learn from this prompt", "data-lesson", "You wrote", "/api/prompting/learn/brief"):
        assert needle in js, needle
    assert ".hp-lesson{" in (CON / "prompting.css").read_text()


def test_learn_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
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
    assert pg.locator(".hp-nav").count() == 6        # v0.999.315: the top bar (Make a prompt, Library, starters, My prompts, Results, Learn)
    pg.fill("#hpText", "a premium diwali poster, no people")
    pg.click("#hpAsk button[type=submit]")
    pg.wait_for_selector("#hpLearn .hp-lesson")
    assert pg.locator("#hpLearn .hp-lesson").count() == 2
    assert "black and gold" in pg.inner_text("#hpLearn") and "starter guidance" in pg.inner_text("#hpLearn")
    pg.click("#hpSave")
    pg.wait_for_selector("#hpMine .hp-mrow")
    pg.goto(base + "/console/prompting#/learn")
    pg.wait_for_selector(".hp-lessons .hp-lesson")
    assert pg.locator(".hp-lessons .hp-lesson").count() == 2
    pg.click('.hp-lesson[data-lesson-card="negative"] [data-state="got_it"]')
    pg.wait_for_selector('.hp-lesson[data-lesson-card="negative"]', state="detached")
    pg.reload()
    pg.wait_for_selector(".hp-lessons .hp-lesson")
    assert pg.locator(".hp-lessons .hp-lesson").count() == 1 and "1 lesson hidden" in pg.inner_text("#hpMain")
    box = pg.evaluate("(() => { const m = document.querySelector('#hpMain'); return m.scrollWidth <= m.clientWidth + 1; })()")
    assert box and not [e for e in errs if "prompting" in e], errs
