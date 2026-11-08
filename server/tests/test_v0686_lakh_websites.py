"""v0.686 EK LAKH ALAG WEBSITE (owner, after v0.683 showed 100 'Sweet shop' cards in a row: "world wide website template
across every field ... not just a small business ... 1 lakh unique templates, 1 lakh website, not same name everywhere").

The Templates page = 1,00,000 UNIQUE websites: 1,000 subjects in 50 world sectors x 10 positionings x 10 cities, each
with its own working name, a website type that suits its sector and a design style; neighbours always differ."""
from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import T, site_env  # noqa: F401

D = Path(__file__).resolve().parents[1] / "app"


def test_world_catalogue_is_whole():
    from app.site import world as W
    assert W.check() == [] and W.check_roots() == []
    assert len(W.SECTORS) == 50 and len(W.subjects()) == 1000 and len({s for _, s in W.subjects()}) == 1000
    labels = {s[1] for s in W.SECTORS}
    for must in ("Software & SaaS", "AI & data", "Hospitals & clinics", "Colleges & universities", "Non-profits & causes",
                 "Energy, solar & climate", "Gaming & esports", "Public services & civic"):
        assert must in labels
    assert len(W.CITIES) == 10 and {c[1] for c in W.CITIES} >= {"India", "UK", "USA", "Kenya", "Germany", "UAE"}
    assert all(len(v) == 6 for v in W.SECTOR_TYPES.values()) and len(W.SECTOR_TYPES) == 50


def test_one_lakh_unique_websites():
    from app.site import templates as TP
    assert TP.total() == 100000
    cards = [TP.card(n) for n in range(100000)]
    assert len({c["title"] for c in cards}) == 100000                          # every website its own name
    assert len({c["line"] for c in cards}) == 100000                           # and its own business
    assert len({(c["subject"], c["angle"], c["city"]) for c in cards}) == 100000
    first = cards[:50]
    assert len({c["sector"] for c in first}) == 50                             # the first page spans the world
    for i in range(1, 2000):
        a, b = cards[i - 1], cards[i]
        assert a["sector"] != b["sector"] and a["title"] != b["title"] and a["style"] != b["style"]
    from app.site import world as W
    assert all(c["type"] in W.SECTOR_TYPES[c["sector"]] for c in cards[::97])    # the type suits the field
    st, ty = Counter(c["style"] for c in cards), Counter(c["type"] for c in cards)
    assert len(st) == 10 and min(st.values()) > 8000 and len(ty) == 10


def test_deep_prompts_fit_and_are_clean():
    from app.site import guard
    from app.site import templates as TP
    rnd = random.Random(11)
    for n in [1, 100000] + rnd.sample(range(1, 100001), 1200):
        p = TP.prompt(n)
        t = p["prompt"]
        assert len(t) <= 2000 and TP.prompt(p["id"])["prompt"] == t
        for part in ("WHO VISITS:", "MAIN ACTION", "PAGES:", "HOME PAGE", "MUST WORK:", "POSITIONING:", "DESIGN -",
                     "BUILD QUALITY:", "RULES:", "Never invent", f"[Hoola template #{n:,} of 1,00,000]", p["title"], p["city"]):
            assert part in t, (n, part)
        assert not guard.brief_problem(" ".join(t.split())), n                # all 1,00,000 checked once at ship


def test_search_filters_names_and_paging():
    from app.site import templates as TP
    r = TP.search()
    assert r["total"] == 100000 and len(r["rows"]) == 30 and r["sectors_count"] == 50 and len(r["types"]) == 10
    assert len({x["sector"] for x in r["rows"]}) == 30
    s = TP.search("school")
    assert s["total"] >= 100 and all("school" in (x["subject"] + x["sector_label"]).lower() for x in s["rows"])
    c = TP.search("cafe berlin")
    assert c["total"] and all(x["city"] == "Berlin" and "cafe" in x["subject"] for x in c["rows"])
    e = TP.search("eco-friendly", "ai")
    assert e["total"] == 200 and all(x["angle"] == "eco-friendly" and x["sector"] == "ai" for x in e["rows"])
    k = TP.search("", "saas", "webapp", "tech_gradient")
    assert k["total"] and all(x["type"] == "webapp" and x["style"] == "tech_gradient" for x in k["rows"])
    nm = TP.card(4242)["title"]
    assert TP.search(nm.lower())["rows"][0]["n"] == 4243
    p2 = TP.search("", "health", offset=30)
    assert p2["rows"][0]["id"] not in {x["id"] for x in TP.search("", "health")["rows"]}
    assert TP.search("zzqqxx")["total"] == 0
    try:
        TP.prompt(100001)
        raise AssertionError("past the end must refuse")
    except KeyError:
        pass


def test_routes_and_use_builds_from_the_card(site_env):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    r = c.get("/api/site-templates?q=bakery&kind=store").json()
    assert r["total"] and r["rows"][0]["type"] == "store"
    p = c.get(f"/api/site-templates/{r['rows'][0]['id']}").json()
    assert p["prompt"].startswith("Build a complete") and c.get(f"/api/site-templates/{p['n']}").json()["id"] == p["id"]
    assert c.get("/api/site-templates/nope").status_code == 404
    v = S.new(T, p["prompt"], "", field=p["field"], goal=p["goal"], style=p["style"])   # what the Studio's Use sends
    assert v["field"] == p["field"] and v["goal"] == p["goal"] and v["style"] == p["style"]


def test_studio_markers():
    js = (D / "static" / "console" / "webstudio.js").read_text()
    for m in ("/api/site-templates?", "sector: TPL.sector, kind: TPL.kind", "All sectors", "Any website type",
              "${esc(r.line)}", "r.sector_label", "Use this prompt", "field: TPLSEL.field", "'[Hoola template #'"):
        assert m in js, m
    assert "r.hi)" not in js and "industry_label" not in js.split("function tplCard")[1].split("function tplOptions")[0]


def test_templates_page_in_a_browser(arena_server):
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/web#/templates")
    pg.wait_for_selector("#wsTplGrid .tcard", timeout=20000)
    titles = pg.locator("#wsTplGrid .tcard b").all_inner_texts()
    assert len(titles) == 30 and len(set(titles)) == 30                      # no repeated name on the page
    assert len(set(pg.locator("#wsTplGrid .tcard .tl").all_inner_texts())) == 30
    pg.fill("#wsTplQ", "school")
    for _ in range(40):
        if "school" in pg.inner_text("#wsTplGrid").lower() and "match" in pg.inner_text("#wsTplCount"):
            break
        pg.wait_for_timeout(250)
    assert "match" in pg.inner_text("#wsTplCount")
    pg.select_option("#wsTplGoal", "landing")
    pg.wait_for_timeout(800)
    pg.locator("#wsTplGrid .tcard").first.click()
    pg.wait_for_selector("dialog.tpld .tpre", timeout=8000)
    txt = pg.inner_text("dialog.tpld .tpre")
    assert "Build a complete" in txt and "landing page" in txt and "BUILD QUALITY" in txt
    pg.click("dialog.tpld [data-x='use']")
    pg.wait_for_selector("#wsAsk", timeout=8000)
    assert pg.input_value("#wsAsk").startswith("Build a complete")
    ctx.close()
    assert not errs, errs
