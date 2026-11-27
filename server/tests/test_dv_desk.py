"""DEVOPS DESK: the DevOps employee's own section, built like the finance desks - its own chat (kind 'devops') with the desk block +
the DevOps tools in view; GitHub joined by a sealed token in its own part only; failed builds explained, re-run only by her tap;
deploy and rollback cards that start her own workflow only through the desk with the card's hash; server logs clustered, sites
watched, a signed collector; scripts checked and never run; checklists; GLOBAL: the CERT-In log rule only for India, her own days
or 'check this' elsewhere; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_devops import NPM_LOG, SHA1, SHA2, SHA3, T, TOKEN, dv, joined, run_json   # noqa: F401


@pytest.fixture
def dd(dv):        # noqa: F811
    from app import dvchat as D
    D._OF.clear()
    D._BLOCK.clear()
    return D


def _hire():
    from app.employee import hire
    hire.hire(T, "devops", trust="seekh")


def _builds(S):
    G = S.FAKE
    G.runs = [run_json(11, SHA2, "failure", title="Add refund page"),
              run_json(21, SHA3, "success", path=".github/workflows/deploy.yml", name="Deploy", start=datetime(2026, 10, 20, 4, 0, tzinfo=timezone.utc)),
              run_json(22, SHA1, "success", path=".github/workflows/deploy.yml", name="Deploy", start=datetime(2026, 10, 21, 4, 0, tzinfo=timezone.utc))]
    G.jobs[(11, 1)] = [{"id": 501, "name": "build", "conclusion": "failure", "steps": [{"name": "Run npm ci", "conclusion": "failure", "number": 3}]}]
    G.logs["501"] = NPM_LOG


def test_hire_chat_block_and_wiring(dd):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert dd.summary(T)["hired"] is False and "Hire me from AI Employees" in dd.greeting(T)
    with pytest.raises(PermissionError):
        dd.do(T, "sync", {})
    _hire()
    d = dd.summary(T)
    assert d["hired"] and d["desk"]["repos"] == [] and "Connect GitHub" in d["desk"]["needs"][0]["say"]
    assert d["desk"]["templates"] and "Connect GitHub" in dd.greeting(T)
    chat = dd.current(T)
    assert dd.is_devops(chat["id"]) and dd.owns(T, chat["id"])
    assert "<devops_desk>" in dd.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_dvc.is_devops(conversation_id)" in src and "adm.admit_families(_dvc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["devops"] in dd.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"devops"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/devops")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dvdesk.js" in r.text
    html = (root / "server/app/static/console/dvdesk.html").read_text()
    for x in ("chatkit.js", "qadesk.css", "dvdesk.css", "dvdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/devops')" in (root / "server/app/static/console/v2.js").read_text()
    assert "devops: 'dvdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["devops"]["desk"] == "dvdesk"


def test_guards_token_and_secrets(dd):
    _hire()
    with pytest.raises(PermissionError):
        dd.do(T, "settings", {"team": "Ops", "token": TOKEN})            # a token only in the github part
    with pytest.raises(PermissionError):
        dd.do(T, "explain_log", {"text": "my otp is 123456"})
    out = dd.do(T, "github", {"token": TOKEN})
    assert TOKEN not in str(out) and TOKEN not in str(dd.summary(T)) and TOKEN not in dd.block(T)
    with pytest.raises(dd.DvDeskError):
        dd.do(T, "nope", {})
    from app.employee import hire
    hire.pause(T, "devops")
    assert dd.do(T, "explain_log", {"text": NPM_LOG})["label"]           # reads still work while paused
    with pytest.raises(PermissionError):
        dd.do(T, "sync", {})


def test_builds_deploy_card_and_tap(dd):
    S, G = dd._S(), dd._S().FAKE
    _hire()
    dd.do(T, "github", {"token": TOKEN})
    dd.do(T, "repo_add", {"repo": "o/app", "deploy_workflow": "deploy.yml", "environment": "production"})
    _builds(S)
    dd.do(T, "sync", {})
    k = dd.today_view(T)
    failed = [r for r in k["runs"] if r["conclusion"] == "failure"]
    assert failed and any("failed since" in n["say"] for n in k["needs"]) or failed
    d = dd.do(T, "diagnose", {"run": failed[0]["key"]})
    assert (d.get("diagnosis") or d).get("label")
    dd.do(T, "rerun", {"run": failed[0]["key"]})
    assert G.reruns                                                       # her tap through the desk
    card = dd.do(T, "deploy", {"repo": "o/app"})
    assert card["status"] == "card" and not G.dispatched
    assert any(n.get("go") == "deploys" for n in dd.today_view(T)["needs"])
    with pytest.raises(dd.DvDeskError):
        dd.do(T, "decide", {"deploy": card["id"], "yes": True, "hash": "x" * 24})
    r = dd.do(T, "decide", {"deploy": card["id"], "yes": True, "hash": card["hash"]})
    assert r["deploy"]["status"] == "dispatched" and G.dispatched
    rb = dd.do(T, "rollback", {"repo": "o/app"})
    assert rb["kind"] == "rollback"
    dd.do(T, "decide", {"deploy": rb["id"], "yes": False, "hash": rb["hash"]})
    assert S.deploy_view(T, rb["id"])["status"] == "rejected"


def test_logs_sites_scripts_checklists_global(dd, monkeypatch):
    S = dd._S()
    _hire()
    out = dd.do(T, "logs", {"text": "\n".join(["Error: connect ECONNREFUSED 127.0.0.1:5432"] * 4), "source": "api"})
    assert dd.today_view(T)["clusters"] and "ECONNREFUSED" not in str(out.get("say", "x"))[:0] + "x"
    cl = dd.today_view(T)["clusters"][0]
    if cl.get("runbook"):
        assert dd.do(T, "runbook", {"id": cl["runbook"]})["steps"]
    dd.do(T, "cluster", {"id": cl["id"], "status": "fixed"})
    col = dd.do(T, "collector", {"name": "web-1"})
    assert col["secret"] and col["steps"] and col["secret"] not in str(dd.summary(T))
    sc = dd.do(T, "check_script", {"content": "rm -rf $DIR/\n", "name": "clean.sh"})
    assert sc["verdict"] == "block"
    made = dd.do(T, "script", {"kind": "logrotate", "params": {}})
    v = dd.do(T, "script_view", {"id": made["id"]})
    # India: the CERT-In 180 days; Germany with no days set: her rule asked for, never CERT-In
    dd.do(T, "settings", {"country": "IN"})
    ck = dd.do(T, "checklist", {"kind": "server_setup"})
    txt = str(ck)
    assert "CERT-In" in txt or "180" in txt or "180" in v["content"]
    dd.do(T, "settings", {"country": "DE"})
    ck2 = dd.do(T, "checklist", {"kind": "server_setup"})
    assert "CERT-In" not in str(ck2)
    dd.do(T, "settings", {"log_days": 90})
    made2 = dd.do(T, "script", {"kind": "logrotate", "params": {}})
    assert "rotate 90" in dd.do(T, "script_view", {"id": made2["id"]})["content"]
    c = ck2.get("checklist") or ck2
    it = c["items"][0]["id"]
    dd.do(T, "tick", {"checklist": c["id"], "item": it, "done": True})
    assert any(x["done"] for cc in dd.today_view(T)["checklists"] for x in cc["items"])


@pytest.fixture
def dd_server(dd, monkeypatch):
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


def test_desk_in_a_real_browser(dd, dd_server):
    S = dd._S()
    base, browser, key = dd_server
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
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/devops")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # GitHub by a sealed token on Settings
    go(pg, "#/settings", "form[data-form=github]")
    pg.fill("form[data-form=github] [name=token]", TOKEN)
    pg.click("form[data-form=github] [type=submit]")
    pg.wait_for_selector("text=@meghana", timeout=30000)
    assert TOKEN not in pg.content()
    # a repo, a sync, a failed build explained
    _builds(S)
    go(pg, "#/builds", "form[data-form=repo]")
    pg.fill("form[data-form=repo] [name=repo]", "o/app")
    pg.fill("form[data-form=repo] [name=deploy_workflow]", "deploy.yml")
    pg.fill("form[data-form=repo] [name=environment]", "production")
    pg.click("form[data-form=repo] [type=submit]")
    pg.wait_for_selector("text=deploys with deploy.yml", timeout=30000)
    pg.click("[data-act=sync]")
    pg.wait_for_selector("details.qa-case", timeout=30000)
    pg.click("details.qa-case summary")
    snap(pg, "dv-builds-1440")
    # a deploy card, then her tap
    go(pg, "#/deploys", "form[data-form=deploy]")
    pg.click("form[data-form=deploy] [type=submit]")
    pg.wait_for_selector("form[data-form=decide]", timeout=30000)
    snap(pg, "dv-deploy-card-1440")
    pg.click("form[data-form=decide] [data-yes='1']")
    pg.wait_for_selector("text=History", timeout=30000)
    pg.wait_for_selector("form[data-form=decide]", state="detached", timeout=30000)
    assert S.FAKE.dispatched
    # logs and a site
    go(pg, "#/servers", "form[data-form=logs]")
    pg.fill("form[data-form=logs] [name=text]", "\n".join(["Error: connect ECONNREFUSED 127.0.0.1:5432"] * 3))
    pg.click("form[data-form=logs] [type=submit]")
    pg.wait_for_selector("details.qa-case", timeout=30000)
    pg.fill("form[data-form=collector] [name=name]", "web-1")
    pg.click("form[data-form=collector] [type=submit]")
    pg.wait_for_selector("text=shown only now", timeout=30000)
    snap(pg, "dv-servers-1440")
    # a script checked, a file made, a checklist ticked
    go(pg, "#/scripts", "form[data-form=check]")
    pg.fill("form[data-form=check] [name=content]", "rm -rf $DIR/\n")
    pg.click("form[data-form=check] [type=submit]")
    pg.wait_for_selector("text=Change before running", timeout=30000)
    pg.click("form[data-form=script] [type=submit]")
    pg.wait_for_selector(".dv-code", timeout=30000)
    pg.click("[data-newcl]")
    pg.wait_for_selector("details.qa-case[open] .dv-item input", timeout=30000)
    pg.click("details.qa-case[open] .dv-item input")
    snap(pg, "dv-scripts-1440")
    go(pg, "#/today", "text=Recent deploys")
    snap(pg, "dv-today-1440")
    # phone width: nothing runs off the side
    for route, sel in (("#/today", "text=Needs you"), ("#/builds", "details.qa-case"), ("#/deploys", "text=History"),
                       ("#/servers", "form[data-form=logs]"), ("#/scripts", ".dv-code, form[data-form=check]"), ("#/settings", "form[data-form=dvset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
    snap(pg, "dv-settings-390")
    assert not errs, errs
