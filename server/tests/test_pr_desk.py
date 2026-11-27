"""PRODUCT MANAGER DESK: the Product manager's own section, built like the finance desks - its own chat (kind 'product') with the
desk block + the product tools in view; a backlog of customer problems with evidence, scored only with HER numbers (RICE / ICE),
Kano, merge / drop / depends; Now / Next / Later against her capacity; specs with Given / When / Then; release notes in English
and only the second language SHE picks (Hinglish only by default in India); publishing only by her tap with the card hash; KPIs and
30-day before / after; GLOBAL: her country, money unit and language; the GitHub token only in its own part; walked in a browser."""
from __future__ import annotations

import os

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_tech_product import T, FakeGitHub, _seed, pm   # noqa: F401


@pytest.fixture
def pdk(pm):        # noqa: F811
    from app import prchat as P
    P._OF.clear()
    P._BLOCK.clear()
    return P


def _hire():
    from app.employee import hire
    hire.hire(T, "product", trust="seekh")


def test_hire_chat_block_and_wiring(pdk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert pdk.summary(T)["hired"] is False and "Hire me from AI Employees" in pdk.greeting(T)
    with pytest.raises(PermissionError):
        pdk.do(T, "opp_add", {"title": "X"})
    _hire()
    d = pdk.summary(T)
    assert d["hired"] and "never makes up a number" in d["foot"]
    chat = pdk.current(T)
    assert pdk.is_product(chat["id"]) and pdk.owns(T, chat["id"])
    assert "<product_desk>" in pdk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_prc.is_product(conversation_id)" in src and "adm.admit_families(_prc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"product"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/product")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "prdesk.js" in r.text
    html = (root / "server/app/static/console/prdesk.html").read_text()
    for x in ("chatkit.js", "creditdesk.css", "prdesk.css", "prdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/product')" in (root / "server/app/static/console/v2.js").read_text()
    assert "product: 'prdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["product"]["desk"] == "prdesk"


def test_guards(pdk):
    _hire()
    tok = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2"
    with pytest.raises(PermissionError):
        pdk.do(T, "settings", {"rules": "use " + tok})               # a token never outside the GitHub part
    with pytest.raises(PermissionError):
        pdk.do(T, "opp_add", {"title": "x", "token": tok})
    ok = pdk.do(T, "opp_add", {"title": "Cannot reset my password", "quote": "my password is lost, OTP never comes"})   # quotes are data
    assert ok["opportunity"]["number"]
    with pytest.raises(pdk.PrDeskError):
        pdk.do(T, "nope", {})
    from app.employee import hire
    hire.pause(T, "product")
    assert pdk.do(T, "opp_get", {"id": ok["opportunity"]["id"]})             # reads still work
    with pytest.raises(PermissionError):
        pdk.do(T, "opp_add", {"title": "Y"})


def test_backlog_roadmap_specs_releases_global(pdk):
    S = pdk._S()
    _hire()
    _seed(S)
    pdk.do(T, "harvest", {})
    k = pdk.today_view(T)
    items = k["backlog"]["items"]
    assert items and k["backlog"]["unscored"] == len(items) and any("score" in n["say"].lower() for n in k["needs"])
    o = items[0]
    out = pdk.do(T, "score", {"id": o["id"], "reach": 500, "impact": 2, "confidence": 0.8, "effort": "2 months"})
    assert out["opportunity"]["score"] == 400.0
    pdk.do(T, "settings", {"capacity": {"now": "1 months"}})
    pdk.do(T, "place", {"id": o["id"], "bucket": "now"})
    rm = pdk.today_view(T)["roadmap"]
    assert rm["buckets"]["now"]["over"] and any(p["id"].startswith("over_") for p in rm["problems"])
    sp = pdk.do(T, "spec_write", {"id": o["id"]})
    spec = pdk.do(T, "spec_get", {"id": (sp.get("spec") or sp)["id"]})
    assert ((spec.get("spec") or spec)["body"]["stories"])
    # GLOBAL: outside India there is no Hinglish unless she picks a language
    assert pdk.today_view(T)["settings"]["second_lang"] == "Hinglish"     # unset in India: Hinglish
    pdk.do(T, "settings", {"country": "DE", "currency": "EUR"})
    rel = pdk.do(T, "release_new", {"version": "2.4.0", "text": "You can now track your order\nFaster checkout"})
    rv = rel.get("release") or rel
    full = pdk.do(T, "release_get", {"id": rv["id"]})
    notes = (full.get("release") or full)["notes"]
    assert notes["english"] and not notes["hinglish"]
    assert pdk.today_view(T)["money_unit"] == "EUR"
    pdk.do(T, "settings", {"second_lang": "German"})            # no model here: no German is made up either
    rel2 = pdk.do(T, "release_new", {"version": "2.5.0", "text": "Dark mode"})
    assert not pdk.do(T, "release_get", {"id": (rel2.get("release") or rel2)["id"]}).get("release", {}).get("notes", {}).get("hinglish")
    pdk.do(T, "settings", {"country": "IN", "currency": "INR", "second_lang": "Hinglish"})
    rel3 = pdk.do(T, "release_new", {"version": "2.6.0", "text": "Order tracking"})
    r3 = pdk.do(T, "release_get", {"id": (rel3.get("release") or rel3)["id"]})
    assert (r3.get("release") or r3)["notes"]["hinglish"]
    # publishing only by her tap, with the card's hash
    card = pdk.do(T, "publish", {"id": rv["id"], "dest": "copy", "lang": "english"})
    c = card.get("card") or card
    with pytest.raises(pdk.PrDeskError):
        pdk.do(T, "decide", {"publish": c["id"], "yes": True, "hash": "wrong"})
    d = pdk.do(T, "decide", {"publish": c["id"], "yes": True, "hash": c["hash"]})
    assert d["status"] == "published"
    # KPIs
    pdk.do(T, "settings", {"north_star": {"name": "Weekly orders", "unit": "orders", "target": 300}})
    pdk.do(T, "metric", {"kpi": "north_star", "value": 210})
    ks = pdk.today_view(T)["metrics"]["kpis"]
    assert any(x["north_star"] and x["latest"] == 210 for x in ks)


def test_github_token_only_in_its_part(pdk):
    S = pdk._S()
    _hire()
    gh = FakeGitHub()
    S.set_transport(httpx.MockTransport(gh.handler))
    tok = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8"
    r = pdk.do(T, "github", {"token": tok, "repo": "newtika/kirana"})
    assert tok not in str(r) and tok not in str(pdk.today_view(T)) and tok not in pdk.block(T)
    assert pdk.today_view(T)["settings"]["github"]["joined"]


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def pr_server(pdk, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(pdk, pr_server):
    S = pdk._S()
    base, browser, key = pr_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    _seed(S)

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    answers = iter(["", "2.0.0"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept(next(answers, "")))
    pg.goto(base + "/console/product")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # settings first: capacity, country
    go(pg, "#/settings", "form[data-form=prset]")
    f = "form[data-form=prset] "
    pg.fill(f + "[name=product]", "Kirana delivery app")
    pg.fill(f + "[name=country]", "IN")
    pg.fill(f + "[name=currency]", "INR")
    pg.fill(f + "[name=cap_now]", "1")
    pg.click(f + "[type=submit]")
    pg.wait_for_selector("text=Kirana delivery app", timeout=20000)
    snap(pg, "pr-settings-1440")
    # backlog: harvest, then score the first problem
    go(pg, "#/backlog", "[data-act=harvest]")
    pg.click("[data-act=harvest]")
    pg.wait_for_selector("details.qa-case", timeout=30000)
    pg.click("details.qa-case summary")
    pg.wait_for_selector("form[data-form=score]", timeout=30000)
    s_ = "form[data-form=score] "
    pg.fill(s_ + "[name=reach]", "500")
    pg.select_option(s_ + "[name=impact]", "2.0")
    pg.select_option(s_ + "[name=confidence]", "80")
    pg.fill(s_ + "[name=effort]", "2 months")
    pg.click(s_ + "[type=submit]")
    pg.wait_for_selector("text=400", timeout=30000)
    pg.wait_for_selector("text=Loading evidence", state="detached", timeout=30000)
    snap(pg, "pr-backlog-1440")
    pg.select_option("[data-place]", "now")
    pg.wait_for_selector("details.qa-case .cs-tag:has-text('Now')", timeout=30000)
    pg.click("[data-spec]")
    pg.wait_for_selector(".pr-story", timeout=30000)
    snap(pg, "pr-specs-1440")
    go(pg, "#/roadmap", ".pr-board")
    pg.click("[data-act=plan]")
    pg.wait_for_selector("text=Suggested plan", timeout=30000)
    snap(pg, "pr-roadmap-1440")
    # release notes + the publish card + her tap
    go(pg, "#/releases", "form[data-form=release]")
    pg.fill("form[data-form=release] [name=version]", "2.4.0")
    pg.fill("form[data-form=release] [name=text]", "You can now track your order\nFaster checkout")
    pg.click("form[data-form=release] [type=submit]")
    pg.wait_for_selector("form[data-form=publish]", timeout=30000)
    pg.click("form[data-form=publish] [type=submit]")
    pg.wait_for_selector("form[data-form=decide]", timeout=30000)
    snap(pg, "pr-releases-1440")
    pg.click("form[data-form=decide] [data-yes='1']")
    pg.wait_for_selector("form[data-form=decide]", state="detached", timeout=30000)
    # KPIs: a north star and a reading
    go(pg, "#/metrics", "form[data-form=kpi]")
    pg.fill("form[data-form=kpi] [name=name]", "Weekly orders")
    pg.fill("form[data-form=kpi] [name=target]", "300")
    pg.check("form[data-form=kpi] [name=north]")
    pg.click("form[data-form=kpi] [type=submit]")
    pg.wait_for_selector("form[data-form=metric]", timeout=30000)
    pg.fill("form[data-form=metric] [name=value]", "210")
    pg.click("form[data-form=metric] [type=submit]")
    pg.wait_for_selector(".pr-kpi b:has-text('210')", timeout=30000)
    snap(pg, "pr-metrics-1440")
    go(pg, "#/today", "text=Roadmap vs capacity")
    snap(pg, "pr-today-1440")
    for route, sel in (("#/today", "text=Needs you"), ("#/backlog", "form[data-form=opp]"), ("#/roadmap", ".pr-board"),
                       ("#/specs", "text=Specs"), ("#/releases", "form[data-form=release]"), ("#/metrics", "form[data-form=kpi]"),
                       ("#/settings", "form[data-form=prset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
    snap(pg, "pr-backlog-390")
    assert not errs, errs
