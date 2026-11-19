"""v0.999.35 MUQABLA (P8 of docs/HOOLA_PROMPTING_PLAN.md): the same ask as two prompts side by side. Comparing the two
prompts is free and in code; running both (pictures, scripts) happens only with the token of the price she was shown;
her pick is kept as shape and the winner's ledger run gets her thumb. No real model or picture engine runs here."""
import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-muqabla"
H = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def cm(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import compare as CM
    from app.prompting import context as C
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    yield CM
    get_settings.cache_clear()


def poster():
    from app.prompting import recipes as R
    return R.use("img-festival-offer", {"festival": "Diwali", "business": "Balaji Sweets", "offer": "Flat 30% Off"})["brief"]


def raw(b):
    return {"section": b["section"], "intent": b["intent"], "slots": {}}


def script():
    from app.prompting import recipes as R
    return R.use("scr-shop-intro", {"business": "Roop Salon", "city": "Pune", "product": "bridal makeup"})["brief"]


def test_the_free_comparison(cm):
    a = poster()
    pr = cm.pair(a, raw(a))
    assert pr["section"] == "image" and pr["runnable"] and pr["a"]["score"]["score"] > pr["b"]["score"]["score"]
    assert any(r["key"] == "words" and r["a"] == "Diwali Sale - Flat 30% Off" and r["b"] == "" for r in pr["rows"])
    assert any(n.startswith("A is more complete") and "not always the better result" in n for n in pr["notes"])
    with pytest.raises(cm.CompareError, match="same kind"):
        cm.pair(a, script())
    same = cm.pair(a, a)
    assert any("the same" in n for n in same["notes"])
    web = cm.pair({"section": "web", "intent": "a website for my clinic", "slots": {}},
                  {"section": "web", "intent": "a website for my dental clinic in Pune with booking", "slots": {}})
    assert web["runnable"] is False and "Web Studio" in web["why_not"]


def test_price_first_and_only_the_price_she_saw_runs(cm, monkeypatch):
    a = poster()
    q = cm.quote(a, raw(a))
    assert q["a"]["credits"] > 0 and q["b"]["credits"] > 0 and q["total"] == q["a"]["credits"] + q["b"]["credits"]
    assert "list price" in q["a"]["basis"] and q["a"]["estimate"] is False and "Nothing runs until you confirm" in q["say"]
    best = cm.quote(a, raw(a), "best")
    assert best["total"] > q["total"] and best["token"] != q["token"]
    with pytest.raises(cm.CompareError, match="price changed or was not shown"):
        cm.check_token(a, raw(a), "fast", "")                                  # no quote shown = nothing runs
    with pytest.raises(cm.CompareError, match="price changed or was not shown"):
        cm.check_token(a, raw(a), "best", q["token"])                          # a different quality = a different price
    from app.prompting import brief as B
    changed = B.apply(a, {"light": "bright daylight"})
    with pytest.raises(cm.CompareError, match="price changed or was not shown"):
        cm.check_token(changed, raw(a), "fast", q["token"])                    # a changed prompt needs a new quote
    pr, q2 = cm.check_token(a, raw(a), "fast", q["token"])
    assert q2["total"] == q["total"] and pr["section"] == "image"
    s = cm.quote(script(), raw(script()))
    assert s["a"]["estimate"] is True and "estimate" in s["a"]["basis"]
    with pytest.raises(cm.CompareError, match="Web Studio"):
        cm.quote({"section": "web", "intent": "a site for my shop", "slots": {}}, {"section": "web", "intent": "a shop site", "slots": {}})
    with pytest.raises(cm.CompareError, match="the same"):
        cm.quote(a, a)


def test_routes_run_both_pictures_after_the_price(cm, monkeypatch):
    from app import photogen
    from app.prompting import ledger as L
    made = []

    def fake_make(prompt, imgs=None, aspect="", quality="fast"):
        made.append((prompt, aspect, quality))
        return {"png": b"\x89PNG\r\n\x1a\nfake", "model": "fake-pic", "aspect": aspect or "1:1", "quality": quality, "edit": False,
                "cost_inr": photogen.COST_INR[quality]}
    monkeypatch.setattr(photogen, "make", fake_make)
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    a = poster()
    assert c.post("/api/prompting/compare/run", headers=H, json={"a": a, "b": raw(a)}).status_code == 422   # no price shown
    assert made == []
    q = c.post("/api/prompting/compare/quote", headers=H, json={"a": a, "b": raw(a)}).json()
    r = c.post("/api/prompting/compare/run", headers=H, json={"a": a, "b": raw(a), "quality": "fast", "token": q["token"]}).json()
    assert r["credits"] == q["total"] and r["a"]["job"]["id"] != r["b"]["job"]["id"]
    for _ in range(50):
        if all(c.get(f"/api/create/jobs/{r[s]['job']['id']}", headers=H).json()["status"] == "done" for s in "ab"):
            break
        asyncio.run(asyncio.sleep(0.05))
    assert len(made) == 2 and made[0][0] != made[1][0]                       # the two different prompts really ran
    assert any('"Diwali Sale - Flat 30% Off"' in p for p, *_ in made)
    picked = c.post(f"/api/prompting/compare/{r['id']}/pick", headers=H, json={"side": "a"}).json()
    assert picked["pick"] == "a" and picked["ran"] == "both"
    from app.db import session
    from app.prompting import compare as CM
    with session() as s:
        row = s.get(CM.PromptCompare, r["id"])
        runs = json.loads(row.runs)
        blob = json.dumps({k: str(getattr(row, k)) for k in ("a_slots", "b_slots", "refs", "runs", "a_hash", "b_hash")})
        win = s.get(L.PromptRun, runs["a"])
        assert win.thumb == "up" and win.grade == "kept"                      # her pick reached the ledger
    for secret in ("Balaji", "Diwali", "30%"):
        assert secret not in blob                                            # shape only
    assert c.post(f"/api/prompting/compare/{r['id']}/pick", headers=H, json={"side": "x"}).status_code == 422
    assert c.post("/api/prompting/compare/nope/pick", headers=H, json={"side": "a"}).status_code == 404


def test_routes_run_both_scripts_and_judge_without_running(cm, monkeypatch):
    from app.create import service as cs
    seen = []

    async def fake_write(kind, brief, fmt="", length="", language="English", tone="", genre="", mood=""):
        seen.append(brief)
        return f"SCENE 1. ({len(seen)})"
    monkeypatch.setattr(cs, "write", fake_write)
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    a = script()
    q = c.post("/api/prompting/compare/quote", headers=H, json={"a": a, "b": raw(a)}).json()
    r = c.post("/api/prompting/compare/run", headers=H, json={"a": a, "b": raw(a), "token": q["token"]}).json()
    assert r["a"]["text"].startswith("SCENE 1.") and r["b"]["text"].startswith("SCENE 1.") and len(seen) == 2
    web_a = {"section": "web", "intent": "a website for my dental clinic in Pune", "slots": {}}
    web_b = {"section": "web", "intent": "a website for my dental clinic in Pune with online booking and prices", "slots": {}}
    assert c.post("/api/prompting/compare", headers=H, json={"a": web_a, "b": web_b}).json()["runnable"] is False
    assert c.post("/api/prompting/compare/quote", headers=H, json={"a": web_a, "b": web_b}).status_code == 422
    jid = c.post("/api/prompting/compare/judge", headers=H, json={"a": web_a, "b": web_b}).json()["id"]
    assert c.post(f"/api/prompting/compare/{jid}/pick", headers=H, json={"side": "b"}).json()["pick"] == "b"
    t = c.get("/api/prompting/compare/tally", headers=H).json()
    assert t["picked"] == 1 and t["rate"] is None and "5 picks" in t["note"]


def test_tally_says_whether_the_score_matches_her_eye(cm):
    a = poster()
    pr = cm.pair(a, raw(a))
    for side in ("a", "a", "a", "b", "a"):
        cid = cm.record("t1", pr)
        cm.pick("t1", cid, side)
    t = cm.tally("t1")
    assert t["decided"] == 5 and t["higher_score_won"] == 4 and t["rate"] == 0.8
    assert cm.tally("t2")["picked"] == 0


def test_page_wiring():
    js = (CON / "prompting.js").read_text()
    for needle in ("id=\"hpCmp\"", "#/c", "#/cx", "data-cmpb=\"raw\"", "hpCmpPrice", "hpCmpGo", "data-pick", "/api/prompting/compare/quote",
                   "token: st.cmp.quote.token"):
        assert needle in js, needle
    assert ".hp-cmp{" in (CON / "prompting.css").read_text()


def test_compare_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """A script prompt against her words alone: free comparison -> See the price -> Run both -> both results -> pick A."""
    base, browser, key = arena_server
    from app.create import service as cs
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})

    async def fake_write(kind, brief, fmt="", length="", language="English", tone="", genre="", mood=""):
        return "SCENE 1. The shutter goes up." if "AUDIENCE" in brief else "SCENE 1. A shop."
    monkeypatch.setattr(cs, "write", fake_write)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/prompting#/recipes")
    pg.wait_for_selector(".hp-card")
    pg.click(".hp-card >> text=Shop introduction")
    pg.wait_for_selector("#hpFill")
    pg.fill("#bl_business", "Roop Salon")
    pg.fill("#bl_city", "Pune")
    pg.fill("#bl_product", "bridal makeup")
    pg.click("#hpFill button[type=submit]")
    pg.wait_for_selector("#hpCmp")
    pg.click("#hpCmp")
    pg.wait_for_selector('[data-cmpb="raw"]')
    pg.click('[data-cmpb="raw"]')
    pg.wait_for_selector(".hp-cmp")
    assert pg.locator(".hp-cmpcol").count() == 2 and "more complete" in pg.inner_text("#hpMain")
    assert pg.locator("#hpCmpGo").count() == 0                               # nothing to run before the price
    pg.click("#hpCmpPrice")
    pg.wait_for_selector("#hpCmpGo")
    assert "credits" in pg.inner_text("#hpCmpRun") and "Nothing runs until you confirm" in pg.inner_text("#hpCmpRun")
    pg.click("#hpCmpGo")
    pg.wait_for_selector("#hpRes_a pre")
    assert "shutter" in pg.inner_text("#hpRes_a") and "A shop." in pg.inner_text("#hpRes_b")
    pg.click('[data-pick="a"]')
    pg.wait_for_selector(".hp-tag >> text=You picked A")
    box = pg.evaluate("(() => { const m = document.querySelector('#hpMain'); return m.scrollWidth <= m.clientWidth + 1; })()")
    assert box and not [e for e in errs if "prompting" in e], errs
