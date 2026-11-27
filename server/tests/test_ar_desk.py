"""APP REVIEWER DESK: the App reviewer's own section, built like the finance desks - its own chat (kind 'appreview') with the desk
block + the review tools in view; a static review of HER app / code / website (nothing run, nothing uploaded anywhere) with each
risk's evidence, fix and snippet; marking a risk as intended; report files; fix lists that go to the Developer Assistant or her
developer only by her tap with the card hash; website verification; GLOBAL: her country names the privacy / children / payment law,
only India's is checked, every other country's is 'check this'; the GitHub token only in its own part; walked in a browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_appreview import T, apk, ar   # noqa: F401


@pytest.fixture
def adk(ar):        # noqa: F811
    from app import archat as A
    A._OF.clear()
    A._BLOCK.clear()
    return A


def _hire():
    from app.employee import hire
    hire.hire(T, "app_review", trust="seekh")


def _upload(S, bad=True, target=34):
    return S.upload(T, "dukaan.apk", apk(bad=bad, target=target))["file"]


def test_hire_chat_block_and_wiring(adk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert adk.summary(T)["hired"] is False and "Hire me from AI Employees" in adk.greeting(T)
    with pytest.raises(PermissionError):
        adk.do(T, "review_web", {"url": "x.in"})
    _hire()
    d = adk.summary(T)
    assert d["hired"] and "only on your tap" in d["foot"]
    assert any(n["go"] == "new" for n in d["desk"]["needs"]) and any(n["go"] == "settings" for n in d["desk"]["needs"])
    chat = adk.current(T)
    assert adk.is_appreview(chat["id"]) and adk.owns(T, chat["id"])
    assert "<appreview_desk>" in adk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_arc.is_appreview(conversation_id)" in src and "adm.admit_families(_arc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"appreview")' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/appreview")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "ardesk.js" in r.text
    html = (root / "server/app/static/console/ardesk.html").read_text()
    for x in ("chatkit.js", "prdesk.css", "ardesk.css", "ardesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/appreview')" in (root / "server/app/static/console/v2.js").read_text()
    assert "app_review: 'ardesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["app_review"]["desk"] == "ardesk"
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["app_review"] in adk.FAMILIES


def test_guards(adk):
    _hire()
    tok = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2"
    with pytest.raises(PermissionError):
        adk.do(T, "review_repo", {"repo": "me/app", "ref": tok})          # a token never outside the GitHub part
    with pytest.raises(PermissionError):
        adk.do(T, "settings", {"developer": "Ravi", "token": tok})
    with pytest.raises(PermissionError):
        adk.do(T, "settings", {"developer": "my password is hunter2"})
    with pytest.raises(adk.ArDeskError):
        adk.do(T, "nope", {})
    with pytest.raises(adk.ArDeskError):
        adk.do(T, "settings", {"country": "India"})                       # two letters only
    v = adk.do(T, "review_file", {"file": _upload(adk._S())})
    from app.employee import hire
    hire.pause(T, "app_review")
    assert adk.do(T, "review_get", {"id": v["id"]})["number"] == v["number"]   # reads still work
    assert adk.do(T, "rules", {})["areas"]
    with pytest.raises(PermissionError):
        adk.do(T, "review_file", {"file": _upload(adk._S())})


def test_review_mark_fixlist_and_tap_only_handoff(adk):
    S = adk._S()
    _hire()
    v = adk.do(T, "review_file", {"file": _upload(S)})
    assert v["number"] == "AR-0001" and v["score"] < 50
    d = adk.summary(T)["desk"]
    assert d["targets"][0]["id"] == v["id"] and d["avg_score"] == v["score"]
    assert any("Google Play now needs 36" in n["say"] and n["bad"] for n in d["needs"])
    assert any("critical" in n["say"] for n in d["needs"])
    assert d["facts"][v["target"]]["target_sdk"] == 34
    with pytest.raises(adk.ArDeskError, match="reason"):
        adk.do(T, "mark", {"id": v["id"], "key": "target_sdk", "status": "ignored"})
    m = adk.do(T, "mark", {"id": v["id"], "key": "perm_query_all", "status": "ignored", "note": "A launcher app, Play declaration filed"})
    assert next(r for r in m["risks"] if r["key"] == "perm_query_all")["status"] == "ignored"
    fl = adk.do(T, "fixlist", {"id": v["id"]})
    assert fl["tasks"] and "perm_query_all" not in {t["key"] for t in fl["tasks"]} and "Fix list" in fl["markdown"]
    files = adk.do(T, "files", {"id": v["id"]})
    assert all(f.get("url") for f in files["files"]) and any(f["name"].endswith(".pdf") for f in files["files"])
    card = adk.do(T, "handoff", {"id": v["id"], "to": "developer"})
    assert card["status"] == "needs_tap"
    d = adk.summary(T)["desk"]
    assert d["waiting"] == 1 and d["handoffs"][0]["status"] == "card" and d["needs"][0]["go"] == "fixes"
    with pytest.raises(adk.ArDeskError, match="old"):
        adk.do(T, "decide", {"handoff": card["id"], "hash": "x" * 64, "yes": True})
    out = adk.do(T, "decide", {"handoff": card["id"], "hash": card["hash"], "yes": True})
    assert out["status"] == "sent" and out["wa"].startswith("https://wa.me/")
    h = adk.summary(T)["desk"]["handoffs"][0]
    assert h["status"] == "sent" and h["result"]["wa"] and adk.summary(T)["desk"]["waiting"] == 0
    # the same app again, fixed: compared, the score moves, the trend has two points
    v2 = adk.do(T, "review_file", {"file": _upload(S, bad=False, target=36)})
    assert v2["compare"]["previous"] == "AR-0001" and v2["score"] > v["score"]
    d = adk.summary(T)["desk"]
    assert len(d["trend"][v["target"]]) == 2 and len(d["targets"]) == 1
    assert not any("Google Play now needs" in n["say"] for n in d["needs"])


def test_global_country_law(adk):
    S = adk._S()
    _hire()
    adk.do(T, "settings", {"kids": True})
    v = adk.do(T, "review_file", {"file": _upload(S)})               # no country = India (as before): DPDP + RBI, checked
    r = next(x for x in v["risks"] if x["code"] == "dpdp_notice")
    assert "DPDP" in r["title"] and r["sources"] and not r.get("check")
    s = adk.do(T, "settings", {"country": "de"})
    assert s["country"] == "DE" and "GDPR" in s["law"]["privacy"] and s["law"]["checked"] is False and "Check this" in s["law"]["say"]
    v2 = adk.do(T, "review_file", {"file": _upload(S)})
    for code in ("dpdp_notice", "dpdp_children", "rbi_payment"):
        x = next(y for y in v2["risks"] if y["code"] == code)
        assert x["check"] is True and "DPDP" not in x["title"] + x["explain"] and "RBI" not in x["title"] + x["explain"], code
        assert not x["sources"]
    assert "GDPR" in next(y for y in v2["risks"] if y["code"] == "dpdp_notice")["explain"]
    adk.do(T, "settings", {"country": "BR"})
    v3 = adk.do(T, "review_file", {"file": _upload(S)})
    assert "LGPD" in next(y for y in v3["risks"] if y["code"] == "dpdp_notice")["explain"]
    adk.do(T, "settings", {"country": "MX"})                           # a country with no pack: generic, still 'check this'
    v4 = adk.do(T, "review_file", {"file": _upload(S)})
    x = next(y for y in v4["risks"] if y["code"] == "dpdp_notice")
    assert "your country's data protection law" in x["explain"] and x["check"]
    rv = adk.do(T, "rules", {})
    laws = {lw["country"]: lw for lw in rv["laws"]}
    assert laws["IN"]["checked"] and not laws["US"]["checked"] and "COPPA" in laws["US"]["children"]
    assert "MX" in adk.block(T)


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def ar_server(adk, monkeypatch):
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


def test_desk_in_a_real_browser(adk, ar_server, tmp_path):
    base, browser, key = ar_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    bad = tmp_path / "dukaan-1.2.apk"
    bad.write_bytes(apk(bad=True))
    good = tmp_path / "dukaan-1.3.apk"
    good.write_bytes(apk(bad=False, target=36))

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/appreview")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    snap(pg, "ar-today-empty-1440")
    # settings: country
    go(pg, "#/settings", "form[data-form=arset]")
    pg.fill("form[data-form=arset] [name=country]", "IN")
    pg.fill("form[data-form=arset] [name=developer]", "Ravi")
    pg.click("form[data-form=arset] [type=submit]")
    pg.wait_for_selector("text=Checked: DPDP", timeout=20000)
    snap(pg, "ar-settings-1440")
    # review a file: upload through the page, it opens the review
    go(pg, "#/new", "form[data-form=upload]")
    snap(pg, "ar-new-1440")
    pg.set_input_files("form[data-form=upload] [name=file]", str(bad))
    pg.click("form[data-form=upload] [type=submit]")
    pg.wait_for_selector(".ar-score", timeout=60000)
    pg.wait_for_selector("details.ar-risk", timeout=30000)
    pg.click("details.ar-risk summary")
    pg.wait_for_selector("details.ar-risk[open] .ar-code", timeout=20000)
    snap(pg, "ar-review-1440")
    # mark one as intended (a medium one has no reason needed)
    form = pg.locator("details.ar-risk.medium form[data-form=mark]").first
    pg.locator("details.ar-risk.medium summary").first.click()
    form.locator("[name=note]").fill("Only our staff install this build")
    form.locator("[type=submit]").click()
    pg.wait_for_selector("#toast:has-text('later reviews keep it')", timeout=20000)
    # report files
    pg.click("[data-act=files]")
    pg.wait_for_selector("text=Files ready", timeout=30000)
    # the fix list + a card for her developer + her tap
    pg.click("[data-fix]")
    pg.wait_for_selector("ol.ar-tasks li", timeout=30000)
    pg.click("[data-hand][data-to=developer]")
    pg.wait_for_selector("[data-dec][data-yes='1']", timeout=30000)
    snap(pg, "ar-fixes-1440")
    with ctx.expect_page(timeout=20000) as popup:
        pg.click("[data-dec][data-yes='1']")
    popup.value.close()
    pg.wait_for_selector("text=Earlier cards", timeout=30000)
    # the same app, fixed: the review compares
    go(pg, "#/new", "form[data-form=upload]")
    pg.set_input_files("form[data-form=upload] [name=file]", str(good))
    pg.click("form[data-form=upload] [type=submit]")
    pg.wait_for_selector("text=fixed since AR-0001", timeout=60000)
    # websites: add one, the verification record shows
    go(pg, "#/sites", "form[data-form=domain]")
    pg.fill("form[data-form=domain] [name=url]", "ingle-dukaan.in")
    pg.click("form[data-form=domain] [type=submit]")
    pg.wait_for_selector(".ar-how code", timeout=20000)
    snap(pg, "ar-sites-1440")
    go(pg, "#/rules", "text=Privacy, children and payment law by country")
    snap(pg, "ar-rules-1440")
    go(pg, "#/reviews", "table.tb")
    snap(pg, "ar-reviews-1440")
    go(pg, "#/today", ".ar-tg")
    pg.wait_for_selector(".ar-trend", timeout=20000)
    snap(pg, "ar-today-1440")
    rid = pg.evaluate("document.querySelector('[data-open]').dataset.open")
    for route, sel in (("#/today", ".ar-tg"), ("#/new", "form[data-form=upload]"), ("#/reviews", "table.tb"), (f"#/reviews/{rid}", ".ar-score"),
                       ("#/fixes", "ol.ar-tasks"), ("#/sites", "form[data-form=domain]"), ("#/rules", "text=What is checked"),
                       ("#/settings", "form[data-form=arset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        if route.startswith("#/reviews/"):
            snap(pg, "ar-review-390")
    snap(pg, "ar-settings-390")
    go(pg, "#/today", ".ar-tg")
    snap(pg, "ar-today-390")
    assert not errs, errs
