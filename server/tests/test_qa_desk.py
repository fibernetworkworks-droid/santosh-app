"""QA DESK: the App tester (QA)'s own section, built like the finance desks - its own chat (kind 'qa') with the desk block + the QA
tools in view; what she tests (her own site only after she proved it is hers); cases written from what Hoola found in a real browser;
runs in the background with results and screenshots; numbered bugs, fixed -> retest; release readiness; a GitHub issue only on her
tap; test accounts sealed; no OTP / card number / password outside a test account; GLOBAL: the accessibility law by her country and
daily runs at her own time in her time zone; the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_qa import HOST, T, qa, verified_url_target   # noqa: F401  (the QA engine's fake site + ownership proof)


@pytest.fixture
def qd(qa):        # noqa: F811
    from app import qachat as Q
    Q._OF.clear()
    Q._BLOCK.clear()
    qa._CC.clear()
    return Q


def _hire():
    from app.employee import hire
    hire.hire(T, "qa", trust="seekh")


def _wait_runs(S, n=90):
    for _ in range(n * 4):
        rs = S.runs(T)
        if rs and not [r for r in rs if r["status"] == "running"]:
            return
        time.sleep(0.25)
    raise AssertionError("run did not finish")


def test_hire_chat_block_and_wiring(qd):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert qd.summary(T)["hired"] is False and "Hire me from AI Employees" in qd.greeting(T)
    _hire()
    d = qd.summary(T)
    assert d["hired"] and d["desk"]["targets"] == [] and "never pays" in d["foot"]
    assert "Tell me what to test" in qd.greeting(T)
    chat = qd.current(T)
    assert qd.is_qa(chat["id"]) and qd.owns(T, chat["id"])
    b = qd.block(T)
    assert "<qa_desk>" in b and "never say it is filed" in b
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_qac.is_qa(conversation_id)" in src and "adm.admit_families(_qac.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["qa"] in qd.FAMILIES and FAMILY_OF["qa_dekho"] in qd.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"qa"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/qa")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "qadesk.js" in r.text
    html = (root / "server/app/static/console/qadesk.html").read_text()
    for x in ("chatkit.js", "rkdesk.css", "qadesk.css", "qadesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/qa')" in (root / "server/app/static/console/v2.js").read_text()
    assert "qa: 'qadesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["qa"]["desk"] == "qadesk"


def test_target_proof_cases_run_bugs_release(qd):
    S = qd._S()
    _hire()
    out = qd.do(T, "target_add", {"kind": "url", "url": f"https://{HOST}/"})
    tid = out["target"]["id"]
    k = qd.today_view(T)
    assert any("not proved yours" in n["say"] for n in k["needs"])
    with pytest.raises(qd.QaDeskError):                       # nothing is tested before she proves it is hers
        qd.do(T, "write", {"target": tid})
    qd.do(T, "target_remove", {"target": tid})
    tid = verified_url_target(S)
    w = qd.do(T, "write", {"target": tid, "text": "A visitor can send the contact form with a name."})
    cs = qd.do(T, "cases", {"target": tid})["cases"]
    assert len(cs) >= 5 and w["say"]
    qd.do(T, "run", {"target": tid, "which": "all"})
    _wait_runs(S)
    k = qd.today_view(T)
    assert k["last_run"]["counts"]["fail"] >= 1 and k["open"] >= 1
    assert k["readiness"][tid]["verdict"] in ("not_ready", "risky")
    bug = next(b for b in k["bugs"] if b["status"] == "open")
    rv = qd.do(T, "run_view", {"run": k["last_run"]["id"]})
    assert (rv.get("run") or rv)["results"]
    qd.do(T, "bug", {"bug": bug["id"], "status": "fixed"})
    assert qd.today_view(T)["fixed_waiting"] == 1
    with pytest.raises(qd.QaDeskError):                       # closing needs a reason
        qd.do(T, "bug", {"bug": bug["id"], "status": "closed"})
    # a manual case she checks herself
    c = qd.do(T, "case_add", {"target": tid, "title": "Logo looks right on a phone", "steps_text": "Open on a phone\nLook at the top",
                              "expected": "Logo is sharp", "type": "ui", "priority": "P2"})
    assert c["case"]["auto"] is False
    m = qd.do(T, "mark", {"case": c["case"]["id"], "result": "fail", "note": "Logo is blurry"})
    assert "created" in m["say"]
    # GitHub only as a card (needs her connection); refused plainly without one
    with pytest.raises(qd.QaDeskError, match="GitHub is not connected"):
        qd.do(T, "github", {"bug": bug["id"], "repo": "acme/site"})
    b = qd.block(T)
    assert bug["number"] in b and HOST in b


def test_global_accessibility_and_her_time_zone(qd, monkeypatch):
    S = qd._S()
    from app.qa import rules as R
    _hire()
    assert R.standard("IN", "govt")["source"] == "checked" and "GIGW" in R.standard("IN", "govt")["text"]
    assert R.standard("GB")["source"] == "check this" and "Equality Act" in R.standard("GB")["text"]
    assert "European Accessibility Act" in R.standard("NL")["text"]
    assert "Check which accessibility law" in R.standard("BR")["text"]
    qd.do(T, "settings", {"country": "GB", "team_name": "Acme QA", "rules": "Phone numbers are 11 digits."})
    k = qd.today_view(T)
    assert k["settings"]["country"] == "GB" and k["country_standard"]["source"] == "check this"
    tid = verified_url_target(S)
    t = next(x for x in qd.today_view(T)["targets"] if x["id"] == tid)
    assert t["standard_source"] == "check this" and "Equality Act" in t["standard"]
    rd = R.readiness([{"status": "active", "number": "TC-1", "title": "a11y", "priority": "P2", "type": "accessibility", "last_result": "fail"}],
                     [], govt_facing=True, country="GB")
    assert any("your accessibility law" in x for x in rd["blockers"]) and not any("GIGW" in x for x in rd["blockers"])
    # daily runs at HER time in HER time zone (London), not India's
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    import app.life as life
    monkeypatch.setattr(life, "tz_of", lambda tenant: ZoneInfo("Europe/London"))
    qd.do(T, "target_edit", {"target": tid, "schedule": "21:30"})
    started = []
    monkeypatch.setattr(S, "start_run", lambda *a, **kw: started.append(a))
    assert S.tick(datetime(2026, 6, 1, 20, 0, tzinfo=timezone.utc)) == 0            # 21:00 in London
    assert S.tick(datetime(2026, 6, 1, 20, 31, tzinfo=timezone.utc)) == 1            # 21:31 in London
    assert "Phone numbers are 11 digits" in qd.block(T)


def test_guards_routes_downloads(qd):
    S = qd._S()
    from app.main import app
    c = TestClient(app)
    assert c.post("/api/qadesk/do/target_add", json={"kind": "url", "url": f"https://{HOST}/"}).status_code == 403     # not hired
    _hire()
    tid = verified_url_target(S)
    assert c.post("/api/qadesk/do/case_add", json={"target": tid, "title": "x", "password": "hunter22"}).status_code == 403
    assert c.post("/api/qadesk/do/case_add", json={"target": tid, "title": "Enter the OTP 123456"}).status_code == 403
    r = c.post("/api/qadesk/do/account", json={"target": tid, "label": "test", "username": "qa@ingle.in", "password": "S3cret!pass"})
    assert r.status_code == 200
    d = c.get("/api/qadesk/desk").json()
    acc = d["desk"]["targets"][0]["accounts"]
    assert acc and "S3cret" not in str(d)
    assert c.post("/api/qadesk/do/pay", json={}).status_code == 400
    assert c.get("/api/qadesk/download?what=bugs").status_code == 400                 # no bugs yet: said, not an empty file
    qd.do(T, "case_add", {"target": tid, "title": "Home loads", "steps_text": "Open home", "expected": "It opens"})
    r = c.get(f"/api/qadesk/download?what=cases&target={tid}")
    assert r.status_code == 200 and "Home loads" in r.text
    assert c.get("/api/qadesk/download?what=readiness").status_code == 200
    assert c.get("/api/qadesk/chat").json()["id"]


@pytest.fixture
def qd_server(qd, monkeypatch):
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


def test_desk_in_a_real_browser(qd, qd_server):
    S = qd._S()
    base, browser, key = qd_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

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
    pg.on("dialog", lambda d: d.accept("Logo is blurry"))
    pg.goto(base + "/console/qa")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # her own site by address: not tested until proved
    go(pg, "#/targets", "form[data-form=tadd]")
    pg.select_option("form[data-form=tadd] [name=pick]", "url:")
    pg.fill("form[data-form=tadd] [name=url]", f"https://{HOST}/")
    pg.click("form[data-form=tadd] [type=submit]")
    pg.wait_for_selector("text=Not proved yet", timeout=30000)
    snap(pg, "qa-targets-unproved-1440")
    tid = S.targets(T)[0]["id"]
    tok = {"t": S.targets(T)[0]["verify"]["token"]}
    from tests.test_tech_qa import own_transport
    S.set_transport(own_transport(tok, "meta"))
    pg.click("[data-act=verify]")
    pg.wait_for_selector("text=Yours - proved", timeout=30000)
    # cases written from a real browser look
    go(pg, "#/cases", "form[data-form=write]")
    pg.fill("form[data-form=write] [name=text]", "A visitor can send the contact form with a name.")
    pg.click("form[data-form=write] [type=submit]")
    pg.wait_for_selector("details.qa-case", timeout=90000)
    snap(pg, "qa-cases-1440")
    # a run in the background
    go(pg, "#/runs", "form[data-form=run]")
    pg.click("form[data-form=run] [type=submit]")
    _wait_runs(S)
    pg.click("#sdRefresh")
    pg.wait_for_selector("a[href^='#/runs/']", timeout=30000)
    pg.click("a[href^='#/runs/']")
    pg.wait_for_selector(".qa-res", timeout=30000)
    pg.wait_for_selector("text=Needs a look", timeout=30000)
    pg.wait_for_selector("img.qa-shot[src^='blob:']", timeout=30000)
    snap(pg, "qa-run-1440")
    # bugs: open one, mark fixed
    go(pg, "#/bugs", "details.qa-bug")
    pg.click("details.qa-bug summary")
    pg.wait_for_selector("[data-bug=fixed]", timeout=20000)
    pg.click("[data-bug=fixed]")
    pg.wait_for_selector("text=Test it again", timeout=20000)
    snap(pg, "qa-bugs-1440")
    go(pg, "#/release", ".qa-meter")
    snap(pg, "qa-release-1440")
    go(pg, "#/settings", "form[data-form=qset]")
    pg.fill("form[data-form=qset] [name=country]", "DE")
    pg.click("form[data-form=qset] [type=submit]")
    pg.wait_for_selector("text=Barrierefreiheitsstärkungsgesetz", timeout=20000)
    snap(pg, "qa-settings-1440")
    go(pg, "#/today", ".cs-hero")
    pg.wait_for_selector(".iv-donut", timeout=20000)
    snap(pg, "qa-today-1440")
    assert tid
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".iv-donut", "today"), ("#/targets", "form[data-form=tadd]", "targets"), ("#/cases", "details.qa-case", "cases"),
                             ("#/runs", "table.tb", "runs"), ("#/bugs", "details.qa-bug", "bugs"), ("#/release", ".qa-meter", "release"),
                             ("#/settings", "form[data-form=qset]", "settings")):
        pg.goto(base + "/console/qa" + route)
        pg.wait_for_selector(sel, timeout=30000)
        snap(pg, f"qa-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#qaPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
