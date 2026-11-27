"""NOC DESK: the NOC (ISP network) employee's own section, built like the finance desks - its own chat (kind 'noc') with the desk
block + the NOC tools in view; alarms read into the real fault; tickets with SLA from her hours; customer messages she sends; changes
on equipment only by her tap with the card hash; her network, the light budget and collectors (a secret shown once); GLOBAL: her
country - India's TRAI / BSNL / cyber notes only for India, 'check this' elsewhere, phones of any country; walked in a browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_ispnoc import T, noc, setup_net, ts   # noqa: F401


@pytest.fixture
def ndk(noc):        # noqa: F811
    from app import ncchat as N
    N._OF.clear()
    N._BLOCK.clear()
    return N


def _hire():
    from app.employee import hire
    hire.hire(T, "noc", trust="seekh")


def _cut(n=8):
    return "\n".join(f"{ts(30 - i * 0.2)} OLT-AKOT EPON0/1:{i} ONU LOS alarm" for i in range(1, n + 1))


def test_hire_chat_block_and_wiring(ndk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert ndk.summary(T)["hired"] is False and "Hire me from AI Employees" in ndk.greeting(T)
    with pytest.raises(PermissionError):
        ndk.do(T, "alarms", {"text": "x"})
    _hire()
    d = ndk.summary(T)
    assert d["hired"] and "without your tap" in d["foot"]
    assert any(n["go"] == "network" for n in d["desk"]["needs"]) and any(n["go"] == "settings" for n in d["desk"]["needs"])
    chat = ndk.current(T)
    assert ndk.is_noc(chat["id"]) and ndk.owns(T, chat["id"])
    assert "<noc_desk>" in ndk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_ncc.is_noc(conversation_id)" in src and "adm.admit_families(_ncc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"noc"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/noc")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "ncdesk.js" in r.text
    html = (root / "server/app/static/console/ncdesk.html").read_text()
    for x in ("chatkit.js", "dwdesk.css", "ncdesk.css", "ncdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/noc')" in (root / "server/app/static/console/v2.js").read_text()
    assert "noc: 'ncdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["noc"]["desk"] == "ncdesk"
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["noc"] in ndk.FAMILIES


def test_guards(ndk):
    _hire()
    with pytest.raises(PermissionError):
        ndk.do(T, "olt", {"name": "OLT-1", "password": "admin123"})          # a device password never comes here
    with pytest.raises(PermissionError):
        ndk.do(T, "olt", {"name": "OLT-1", "notes": "telnet password is admin@123"})
    ok = ndk.do(T, "alarms", {"text": "2026-11-27 10:00:00 OLT-X EPON0/1:2 password: admin LOS"})   # alarm text is data
    assert "read" in ok
    with pytest.raises(ndk.NcDeskError):
        ndk.do(T, "nope", {})
    with pytest.raises(ndk.NcDeskError):
        ndk.do(T, "settings", {"country": "India"})
    from app.employee import hire
    hire.pause(T, "noc")
    assert ndk.do(T, "report", {})["days"] == 30                               # reads still work
    with pytest.raises(PermissionError):
        ndk.do(T, "alarms", {"text": "x"})


def test_fault_ticket_change_by_tap(ndk):
    S = ndk._S()
    _hire()
    setup_net(S)
    r = ndk.do(T, "alarms", {"text": _cut()})
    f = r["new"][0]
    assert f["n_affected"] == 8
    k = ndk.summary(T)["desk"]
    assert k["down"] >= 8 and any("no ticket yet" in n["say"] for n in k["needs"])
    t = ndk.do(T, "ticket", {"fault": f["number"], "team": "field_fibre", "assignee": "Sandeep", "phone": "+44 20 7946 0958", "eta": "2 hours"})
    tk = t["ticket"]
    assert tk["tel"] == "tel:+442079460958" and "wa.me/442079460958" in tk["wa_link"] and "XXXX" in tk["phone"]
    m = ndk.do(T, "message", {"fault": f["number"]})
    assert m["text"] and m["count"] == 8
    c = ndk.do(T, "change", {"action_kind": "pon_reset", "olt": "OLT-AKOT", "pon": "0/1", "reason": "test"})["change"]
    assert c["status"] == "waiting"
    assert ndk.summary(T)["desk"]["waiting"] == 1
    with pytest.raises(ndk.NcDeskError):
        ndk.do(T, "decide", {"change": c["number"], "hash": "x" * 64, "yes": True})
    out = ndk.do(T, "decide", {"change": c["number"], "hash": c["hash"], "yes": True})
    assert out["change"]["status"] in ("approved", "queued")
    ndk.do(T, "ticket_update", {"ticket": tk["number"], "status": "fixed"})
    ndk.do(T, "resolve", {"fault": f["number"], "note": "spliced"})
    assert ndk.do(T, "fault_get", {"fault": f["number"]})["status"] == "resolved"
    col = ndk.do(T, "collector_new", {"name": "POP box"})
    assert len(col["secret"]) > 20 and ndk.summary(T)["desk"]["collectors"][0]["name"] == "POP box"
    opt = ndk.do(T, "optics", {"class": "gpon_b+", "km": 5, "splits": [8, 4], "rx": -27})
    assert opt["margin_db"] > 0 and opt["measured_band"]


def test_global_country(ndk):
    S = ndk._S()
    _hire()
    setup_net(S)                                                  # franchise of BSNL, country not set = India
    f = ndk.do(T, "alarms", {"text": _cut()})["new"][0]
    from datetime import timedelta
    from app.db import session
    from app.ispnoc.models import IspnocFault
    with session() as s_:                                         # the fault has lasted 5 hours
        row = s_.get(IspnocFault, f["id"])
        row.started_at = row.started_at - timedelta(hours=5)
    v = ndk.do(T, "fault_get", {"fault": f["number"]})
    assert any("TRAI" in n for n in v["notes"])
    s = ndk.do(T, "settings", {"country": "ng"})
    assert s["country"] == "NG" and s["india"] is False
    v2 = ndk.do(T, "fault_get", {"fault": f["number"]})
    assert v2["notes"] and not any("TRAI" in n or "BSNL" in n for n in v2["notes"]) and any("check this" in n for n in v2["notes"])
    assert "TRAI" not in " ".join(ndk.do(T, "report", {})["tips"])
    from app.ispnoc import rules as R
    assert "MSEB" not in R.TEAMS["electricity"]
    S.save_settings(T, teams={"field_fibre": [{"name": "Ade", "phone": "+234 803 123 4567"}]})
    assert ndk._S().settings(T)["teams"]["field_fibre"][0]["phone"] == "+2348031234567"
    assert "NG" in ndk.block(T)


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def nc_server(ndk, monkeypatch):
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


def test_desk_in_a_real_browser(ndk, nc_server):
    base, browser, key = nc_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []
    setup_net(ndk._S())

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
    pg.goto(base + "/console/noc")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # paste alarms -> the fault opens
    pg.fill("form[data-form=alarms] [name=text]", _cut())
    pg.click("form[data-form=alarms] [type=submit]")
    pg.wait_for_selector("text=What happened", timeout=30000)
    pg.fill("form[data-form=ticket] [name=assignee]", "Sandeep")
    pg.fill("form[data-form=ticket] [name=phone]", "+91 98500 11122")
    pg.fill("form[data-form=ticket] [name=eta]", "2 hours")
    pg.click("form[data-form=ticket] [type=submit]")
    pg.wait_for_selector(".nc-tk", timeout=30000)
    pg.click("[data-msg]")
    pg.wait_for_selector(".nc-msg", timeout=20000)
    snap(pg, "nc-fault-1440")
    # a change card + her tap (twice)
    go(pg, "#/changes", "form[data-form=change]")
    pg.select_option("form[data-form=change] [name=action_kind]", "reboot_ont")
    pg.fill("form[data-form=change] [name=pon]", "0/1")
    pg.fill("form[data-form=change] [name=onu]", "3")
    pg.click("form[data-form=change] [type=submit]")
    pg.wait_for_selector("[data-cdec][data-yes='1']", timeout=30000)
    snap(pg, "nc-changes-1440")
    pg.click("[data-cdec][data-yes='1']")
    pg.wait_for_selector("text=Tap again to approve", timeout=10000)
    pg.click("[data-cdec][data-yes='1']")
    pg.wait_for_selector("[data-cdec]", state="detached", timeout=30000)
    # network: light budget
    go(pg, "#/network", "form[data-form=optics]")
    pg.fill("form[data-form=optics] [name=km]", "4")
    pg.fill("form[data-form=optics] [name=splits]", "8, 4")
    pg.click("form[data-form=optics] [type=submit]")
    pg.wait_for_selector(".nc-opt", timeout=20000)
    snap(pg, "nc-network-1440")
    # a collector: the secret shows once
    go(pg, "#/collectors", "form[data-form=col]")
    pg.fill("form[data-form=col] [name=name]", "POP box")
    pg.click("form[data-form=col] [type=submit]")
    pg.wait_for_selector("code.nc-key", timeout=20000)
    snap(pg, "nc-collectors-1440")
    pg.click("[data-hidesecret]")
    pg.wait_for_selector("code.nc-key", state="detached", timeout=10000)
    # settings: country
    go(pg, "#/settings", "form[data-form=ncset]")
    pg.fill("form[data-form=ncset] [name=country]", "NG")
    pg.click("form[data-form=ncset] [type=submit]")
    pg.wait_for_selector("text=check this", timeout=20000)
    snap(pg, "nc-settings-1440")
    go(pg, "#/tickets", ".nc-tk")
    go(pg, "#/today", "text=Last 30 days")
    snap(pg, "nc-today-1440")
    fid = pg.evaluate("document.querySelector('[data-fault]').dataset.fault")
    for route, sel in (("#/today", "text=Needs you"), ("#/faults", "form[data-form=alarms]"), (f"#/faults/{fid}", "text=What happened"),
                       ("#/tickets", ".nc-tk"), ("#/changes", "form[data-form=change]"), ("#/network", "form[data-form=optics]"),
                       ("#/collectors", "form[data-form=col]"), ("#/settings", "form[data-form=ncset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#ncPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        if route.startswith("#/faults/"):
            snap(pg, "nc-fault-390")
    snap(pg, "nc-settings-390")
    assert not errs, errs
