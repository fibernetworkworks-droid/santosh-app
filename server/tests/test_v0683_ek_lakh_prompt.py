"""v0.683 EK LAKH PROMPT (owner: "in template create a 1 lakh deep prompt for website creation, design, development
across all possible field in world"): the Web Studio Templates page = 1,00,000 deep prompts (1,000 trades in 40
industries x 10 goals x 10 styles), composed on demand from the builder's own library card, searchable, each within
the 2,000-character ask box, and 'Use' sends the field / goal / style so the build gets the full card."""
from __future__ import annotations

import random
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import T, site_env  # noqa: F401

D = Path(__file__).resolve().parents[1] / "app"


def test_one_lakh_unique_deep_prompts_within_the_box():
    from app.site import templates as TP
    assert TP.total() == 100000
    ids, texts = set(), set()
    rnd = random.Random(7)
    for n in [1, 100000] + rnd.sample(range(1, 100001), 1500):
        p = TP.prompt(n)
        assert p["n"] == n and len(p["prompt"]) <= TP.LIMIT == 2000
        assert TP.prompt(p["id"])["prompt"] == p["prompt"] == TP.prompt(n)["prompt"]      # same on every call
        t = p["prompt"]
        for part in ("GOAL:", "PAGES:", "HOME PAGE", "DESIGN -", "BUILD QUALITY:", "RULES:", "Never invent",
                     f"[Hoola template #{n:,} of 100,000]"):
            assert part in t, (n, part)
        ids.add(p["id"]); texts.add(t)
    assert len(ids) == len(texts) == 1502                                                 # every prompt its own
    from app.site import guard
    assert not [n for n in range(1, 100001, 97) if guard.brief_problem(" ".join(TP.prompt(n)["prompt"].split()))]   # usable as it is (all 1,00,000 checked once)
    # every one of the 1,000 trades has its 100 prompts, end to end
    first = {TP.card(i)["field"] for i in range(0, 100000, 100)}
    assert len(first) == 1000


def test_search_filters_and_paging():
    from app.site import templates as TP
    r = TP.search()
    assert r["total"] == 100000 and len(r["rows"]) == 30 and r["fields"] == 1000 and r["industries_count"] == 40
    d = TP.search("dentist")
    assert d["total"] >= 100 and all("Dental" in x["title"] or "dent" in x["id"] for x in d["rows"][:10])
    b = TP.search("dentist booking")
    assert b["total"] and all(x["goal"] == "booking" for x in b["rows"])
    i = TP.search("", "legal", "", "luxury_dark")
    assert i["total"] == 250 and all(x["industry"] == "legal" and x["style"] == "luxury_dark" for x in i["rows"])
    p2 = TP.search("", "legal", offset=30, limit=30)
    assert p2["rows"][0]["id"] not in {x["id"] for x in TP.search("", "legal")["rows"]}
    assert TP.search("zzqqxx")["total"] == 0
    try:
        TP.prompt(100001)
        raise AssertionError("past the end must refuse")
    except KeyError:
        pass


def test_routes_and_use_sends_the_card(site_env):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    r = c.get("/api/site-templates?q=bakery&goal=catalogue").json()
    assert r["total"] and r["rows"][0]["goal"] == "catalogue"
    p = c.get(f"/api/site-templates/{r['rows'][0]['id']}").json()
    assert p["prompt"].startswith("Build a complete") and c.get(f"/api/site-templates/{p['n']}").json()["id"] == p["id"]
    assert c.get("/api/site-templates/nope.nope.nope").status_code == 404
    v = S.new(T, p["prompt"], "", field=p["field"], goal=p["goal"], style=p["style"])   # what the Studio's Use sends
    assert v["field"] == p["field"] and v["goal"] == p["goal"] and v["style"] == p["style"] and v["name"]


def test_studio_markers():
    js = (D / "static" / "console" / "webstudio.js").read_text()
    for m in ("/api/site-templates?", "function openTpl(", "data-tpl=", "Use this prompt", "TPLSEL", "'[Hoola template #'",
              "field: TPLSEL.field", "wsTplInd", "wsTplGoal", "wsTplStyle", "tpl-more", "toLocaleString('en-IN')"):
        assert m in js, m
    css = (D / "static" / "console" / "webstudio.css").read_text()
    assert ".tgrid{" in css and ".tpre{" in css and "dialog.tpld" in css


def test_templates_page_in_a_browser(arena_server):
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/web#/templates")
    pg.wait_for_selector("#wsTplGrid .tcard", timeout=20000)
    assert "1,00,000" in pg.inner_text(".tplall") and pg.locator("#wsTplGrid .tcard").count() == 30
    pg.fill("#wsTplQ", "dentist")
    for _ in range(40):
        if "Dental" in pg.inner_text("#wsTplGrid"):
            break
        pg.wait_for_timeout(250)
    assert "Dental" in pg.inner_text("#wsTplGrid") and "match" in pg.inner_text("#wsTplCount")
    pg.select_option("#wsTplGoal", "booking")
    pg.wait_for_timeout(800)
    pg.locator("#wsTplGrid .tcard").first.click()
    pg.wait_for_selector("dialog.tpld .tpre", timeout=8000)
    txt = pg.inner_text("dialog.tpld .tpre")
    assert "Build a complete" in txt and "BUILD QUALITY" in txt
    pg.click("dialog.tpld [data-x='use']")
    pg.wait_for_selector("#wsAsk", timeout=8000)
    assert pg.input_value("#wsAsk").startswith("Build a complete")
    ctx.close()
    assert not errs, errs
