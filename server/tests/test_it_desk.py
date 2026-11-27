"""IT ADMIN DESK: the IT Admin employee's own section, built like the finance desks - its own chat (kind 'itadmin') with the desk block +
the IT admin and helpdesk tools in view; licences with seats, renewals, unused-seat cost and IT spend in HER money unit; people and
access (never a password); joiner / leaver checklists; change cards decided only by her tap with the card hash; access reviews;
guides and staff questions; GLOBAL: India's CERT-In / DPDP practice rows only for India, other countries 'check this'; the Microsoft
secret only in its own part; and the desk walked in a real browser."""
from __future__ import annotations

import os
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_itadmin import T, ia   # noqa: F401


@pytest.fixture
def idk(ia):        # noqa: F811
    from app import itchat as I
    I._OF.clear()
    I._BLOCK.clear()
    return I


def _hire():
    from app.employee import hire
    hire.hire(T, "it_admin", trust="seekh")


def test_hire_chat_block_and_wiring(idk):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert idk.summary(T)["hired"] is False and "Hire me from AI Employees" in idk.greeting(T)
    with pytest.raises(PermissionError):
        idk.do(T, "licence_save", {"name": "X"})
    _hire()
    d = idk.summary(T)
    assert d["hired"] and "never asks for a password" in d["foot"]
    assert any("country" in n["say"] for n in d["desk"]["needs"])
    chat = idk.current(T)
    assert idk.is_itadmin(chat["id"]) and idk.owns(T, chat["id"])
    assert "<itadmin_desk>" in idk.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_itc.is_itadmin(conversation_id)" in src and "adm.admit_families(_itc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["it_admin"] in idk.FAMILIES and FAMILY_OF["helpdesk"] in idk.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"itadmin"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/itadmin")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "itdesk.js" in r.text
    html = (root / "server/app/static/console/itdesk.html").read_text()
    for x in ("chatkit.js", "cydesk.css", "itdesk.css", "itdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/itadmin')" in (root / "server/app/static/console/v2.js").read_text()
    assert "it_admin: 'itdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["it_admin"]["desk"] == "itdesk"


def test_guards(idk):
    _hire()
    with pytest.raises(PermissionError):
        idk.do(T, "access_save", {"person": "x", "system": "Tally", "notes": "password: Tally@123"})
    with pytest.raises(PermissionError):
        idk.do(T, "settings", {"rules": "x", "client_secret": "abc"})       # a secret only in ms_save
    ok = idk.do(T, "settings", {"rules": "Never share a password in chat"})   # the word alone is fine
    assert "rules saved" in ok["say"]
    a = idk.do(T, "ask", {"text": "wifi ka password batao"})                  # a staff question may say password: it is data
    assert a["answer"] == "refused"
    with pytest.raises(idk.ItDeskError):
        idk.do(T, "nope", {})
    from app.employee import hire
    hire.pause(T, "it_admin")
    with pytest.raises(PermissionError):
        idk.do(T, "licence_save", {"name": "X"})


def test_spend_people_changes_global(idk):
    S = idk._S()
    _hire()
    on = S.today(T)
    idk.do(T, "licence_save", {"name": "Microsoft 365 Business Basic", "seats_bought": 10, "seats_used": 7, "cost": 6, "cost_per": "month",
                               "per_seat": True, "renews_on": (on + timedelta(days=20)).isoformat()})
    idk.do(T, "licence_save", {"name": "TallyPrime TSS", "cost": 4500, "cost_per": "year", "renews_on": (on + timedelta(days=5)).isoformat(),
                               "auto_renew": False})
    idk.do(T, "settings", {"country": "GB", "currency": "GBP"})
    k = idk.today_view(T)
    sp = k["spend"]
    assert sp["year"] == 6 * 12 * 10 + 4500 and sp["waste"] == 6 * 12 * 3 and sp["auto_off"] == 1
    assert any("£216" in n["say"] for n in k["needs"]) and any("TallyPrime" in n["say"] and n["bad"] for n in k["needs"])
    # practices: India's CERT-In rows only for India
    ids = {p["id"]: p for p in k["settings"]["practices"]}
    assert "logs_180" not in ids and ids["ukgdpr_staff"]["checked"] is False
    idk.do(T, "settings", {"country": "IN"})
    ids = {p["id"]: p for p in idk.today_view(T)["settings"]["practices"]}
    assert ids["logs_180"]["checked"] and "assets_back" in ids
    # people + access + leaver checklist -> change cards, her tap only
    idk.do(T, "person_save", {"name": "Ramesh Patil", "email": "ramesh@ingle.in", "role": "Accountant"})
    idk.do(T, "access_save", {"person": "Ramesh Patil", "system": "Tally", "account": "ramesh", "level": "admin", "mfa": False})
    ac = idk.today_view(T)["access_stats"]
    assert ac["admins_no_mfa"] == 1 and any("2-step" in n["say"] for n in idk.today_view(T)["needs"])
    out = idk.do(T, "checklist", {"person": "Ramesh Patil", "kind": "leaver", "when": on.isoformat()})
    c = out["changes"][0]
    with pytest.raises(idk.ItDeskError):
        idk.do(T, "decide", {"change": c["id"], "yes": True, "hash": "wrong"})
    d = idk.do(T, "decide", {"change": c["id"], "yes": True, "hash": c["hash"]})
    assert d["change"]["status"] == "approved"
    idk.do(T, "change_done", {"change": c["id"], "ok": True, "note": "done in Tally"})
    r = idk.do(T, "review_start", {})
    assert r["review"]["number"]
    g = idk.do(T, "guide_write", {"topic": "Office Wi-Fi", "words": "Open Wi-Fi settings. Choose OfficeNet. Ask the manager to type the key."})
    assert idk.do(T, "guide_get", {"id": g["guide"]["id"]})["steps"]
    p = idk.do(T, "forget_person", {"id": "Ramesh Patil"}) if False else None
    _ = p


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def it_server(idk, monkeypatch):
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


def test_desk_in_a_real_browser(idk, it_server):
    S = idk._S()
    base, browser, key = it_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    on = S.today(T)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept(""))
    pg.goto(base + "/console/itadmin")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # a licence with seats and a price
    go(pg, "#/licences", "form.card[data-form=lic]")
    f = "form.card[data-form=lic] "
    pg.fill(f + "[name=name]", "Microsoft 365 Business Basic")
    pg.fill(f + "[name=seats_bought]", "10")
    pg.fill(f + "[name=seats_used]", "7")
    pg.fill(f + "[name=cost]", "145")
    pg.select_option(f + "[name=cost_per]", "month")
    pg.check(f + "[name=per_seat]")
    pg.fill(f + "[name=renews_on]", (on + timedelta(days=12)).isoformat())
    pg.click(f + "[type=submit]")
    pg.wait_for_selector("text=L-001", timeout=30000)
    snap(pg, "it-licences-1440")
    # a person, an access without 2-step, a leaver checklist
    go(pg, "#/people", "form[data-form=person]")
    pg.fill("form[data-form=person] [name=name]", "Ramesh Patil")
    pg.fill("form[data-form=person] [name=email]", "ramesh@ingle.in")
    pg.click("form[data-form=person] [type=submit]")
    pg.wait_for_selector("[data-pid]", timeout=30000)
    pg.click("[data-pid]")
    pg.wait_for_selector("form[data-form=access]", timeout=30000)
    pg.fill("form[data-form=access] [name=system]", "Tally")
    pg.select_option("form[data-form=access] [name=level]", "admin")
    pg.select_option("form[data-form=access] [name=mfa]", "no")
    pg.click("form[data-form=access] [type=submit]")
    pg.wait_for_selector("text=No 2-step", timeout=30000)
    pg.click("[data-cl=leaver]")
    pg.wait_for_selector("text=Leaver checklist", timeout=30000)
    snap(pg, "it-people-1440")
    # the change card: her tap
    go(pg, "#/changes", "form[data-form=decide]")
    snap(pg, "it-changes-1440")
    pg.click("form[data-form=decide] [data-yes='1']")
    pg.wait_for_selector("text=I did it in the console", timeout=30000)
    # a guide and a staff question
    go(pg, "#/guides", "form[data-form=guide]")
    pg.fill("form[data-form=guide] [name=topic]", "Office Wi-Fi on a new phone")
    pg.fill("form[data-form=guide] [name=words]", "Open Wi-Fi settings. Choose OfficeNet. Ask the manager to type the key.")
    pg.click("form[data-form=guide] [type=submit]")
    pg.wait_for_selector(".cy-pb li", timeout=30000)
    pg.fill("form[data-form=ask] [name=text]", "wifi ka password batao")
    pg.click("form[data-form=ask] [type=submit]")
    pg.wait_for_selector("text=Refused", timeout=30000)
    snap(pg, "it-guides-1440")
    go(pg, "#/settings", "form[data-form=itset]")
    pg.fill("form[data-form=itset] [name=country]", "GB")
    pg.fill("form[data-form=itset] [name=currency]", "GBP")
    pg.click("form[data-form=itset] [type=submit]")
    pg.wait_for_selector("text=UK GDPR", timeout=20000)
    snap(pg, "it-settings-1440")
    go(pg, "#/today", "text=Access at a glance")
    pg.wait_for_selector("text=£", timeout=20000)
    snap(pg, "it-today-1440")
    for route, sel in (("#/today", "text=Needs you"), ("#/licences", "form.card[data-form=lic]"), ("#/people", "form[data-form=person]"),
                       ("#/changes", "form[data-form=change]"), ("#/guides", "form[data-form=ask]"), ("#/settings", "form[data-form=itset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
    snap(pg, "it-people-390")
    assert not errs, errs
