"""CYBER DESK: the Cyber security employee's own section, built like the finance desks - its own chat (kind 'cyber') with the desk block
+ the cyber tools in view; alerts filtered and mapped to MITRE ATT&CK; mails / links / files checked without opening or uploading; her
own domains; incidents with notice clocks for every country she works in (only India checked, the rest 'check this'); block / wipe
cards decided only by her tap through the desk with the card hash; the programme (CIS Controls v8 -> NIST CSF + ISO 27001, risks,
access review, secrets scan, vendors, tabletop, training, password policy); keys only in Settings; and the desk walked in a browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.test_tech_cyber import DEFENDER_CSV, PHISH_RAW, SSH_LOG, T, cy   # noqa: F401


@pytest.fixture
def cd(cy):        # noqa: F811
    from app import cychat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "cyber", trust="seekh")


USERS = """Email,Name,Admin role,2SV enrolled,Last sign in,Status
asha@acme.example,Asha,Super Admin,false,2026-11-20,Active
ravi@acme.example,Ravi,,true,2026-11-25,Active
old@acme.example,Old Timer,,true,2026-01-02,Active
info@acme.example,Info box,,false,2026-11-26,Active
gone@acme.example,Gone Person,,true,2026-11-01,Active
"""
CODE = """import os
AWS_KEY = "__AWS__"
db = "postgres://app:Sup3rSecret@db.internal:5432/app"
token = os.environ["TOKEN"]
STRIPE = "__STRIPE__"
""".replace("__AWS__", "AKIA" + "ABCDEFGHIJKLMNOP").replace("__STRIPE__", "sk_" + "live_" + "abcdefghijklmnopqrstuv12")


def test_hire_chat_block_and_wiring(cd):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert cd.summary(T)["hired"] is False and "Hire me from AI Employees" in cd.greeting(T)
    with pytest.raises(PermissionError):
        cd.do(T, "intake", {"text": SSH_LOG})
    _hire()
    d = cd.summary(T)
    assert d["hired"] and "never scans" in d["foot"]
    assert any("Set your country" in n["say"] for n in d["desk"]["needs"])
    chat = cd.current(T)
    assert cd.is_cyber(chat["id"]) and cd.owns(T, chat["id"])
    assert "<cyber_desk>" in cd.block(T) and "check this" in cd.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_cyc.is_cyber(conversation_id)" in src and "adm.admit_families(_cyc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["cyber"] in cd.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"cyber"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/cyber")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "cydesk.js" in r.text
    html = (root / "server/app/static/console/cydesk.html").read_text()
    for x in ("chatkit.js", "qadesk.css", "cydesk.css", "cydesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/cyber')" in (root / "server/app/static/console/v2.js").read_text()
    assert "cyber: 'cydesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["cyber"]["desk"] == "cydesk"


def test_guards_keys_and_tap(cd):
    S = cd._S()
    _hire()
    with pytest.raises(PermissionError):
        cd.do(T, "settings", {"rules": "x", "token": "abc"})              # a key only in key_set
    with pytest.raises(PermissionError):
        cd.do(T, "incident_new", {"title": "card number 4111"})
    out = cd.do(T, "check_email", {"text": PHISH_RAW + "\nEnter your OTP here"})     # a pasted mail may say OTP: it is data
    assert out["verdict"] in ("bad", "suspicious", "danger") or out.get("flags")
    cd.do(T, "key_set", {"provider": "hibp", "token": "0123456789abcdef0123456789abcdef"})
    assert "0123456789abcdef0123456789abcdef" not in str(cd.summary(T)) and "0123456789abcdef" not in cd.block(T)
    # a block card: only the desk tap with the right hash
    card = cd.do(T, "contain", {"kind": "block_ip", "target": "45.155.205.12", "reason": "brute force"})["action"]
    with pytest.raises(cd.CyDeskError):
        cd.do(T, "decide", {"action": card["id"], "yes": True, "hash": "wrong"})
    d = cd.do(T, "decide", {"action": card["id"], "yes": True, "hash": card["hash"]})
    assert d["action"]["status"] == "approved"
    from app.employee import hire
    hire.pause(T, "cyber")
    assert cd.do(T, "playbook", {"playbook": "ransomware"})["steps"]           # reads still work while paused
    with pytest.raises(PermissionError):
        cd.do(T, "intake", {"text": SSH_LOG})
    assert S.actions(T)


def test_alerts_attack_and_notice_clocks_global(cd):
    S = cd._S()
    _hire()
    r = cd.do(T, "intake", {"text": SSH_LOG})
    k = cd.today_view(T)
    a = next(x for x in k["open_alerts"] if x["kind"] in ("login_after_fail", "brute_force"))
    assert a["attack"]["id"] == "T1110" and k["by_tactic"]
    # India (default): CERT-In clock through the helpdesk, DPDP when personal data
    inc = cd.do(T, "incident_new", {"title": "SSH break-in", "kind": "intrusion", "alert_ids": [a["id"]], "personal_data": True})["incident"]
    p = cd.do(T, "notify_plan", {"incident": inc["id"]})
    ids = {x["id"]: x for x in p["rows"]}
    assert ids["in_certin"]["checked"] and ids["in_certin"]["due"] and ids["in_dpdp"]["applies"]
    # Germany + UK customers: GDPR / UK GDPR 72 h, 'check this', no CERT-In clock started
    cd.do(T, "settings", {"country": "DE", "extra_countries": "GB, XX"})
    inc2 = cd.do(T, "incident_new", {"title": "Leak", "kind": "data_leak", "personal_data": True})
    assert "check this" in inc2["say"].lower() or "GDPR" in inc2["say"]
    assert not inc2["incident"].get("helpdesk_incident")
    p2 = cd.do(T, "notify_plan", {"incident": inc2["incident"]["id"]})
    rows = {x["id"]: x for x in p2["rows"]}
    assert "eu_gdpr" in rows and "gb_ico" in rows and "in_certin" not in rows and not rows["eu_gdpr"]["checked"]
    assert rows["eu_gdpr"]["say"].startswith("Check this") and "XX" in p2["unknown"]
    m = cd.do(T, "notify_mark", {"incident": inc2["incident"]["id"], "rule_id": "eu_gdpr", "status": "done", "reference": "BfDI-123"})
    assert next(x for x in m["rows"] if x["id"] == "eu_gdpr")["status"] == "done"
    assert any(n["go"] == "incidents" for n in cd.today_view(T)["needs"])
    _ = r, S


def test_programme(cd):
    _hire()
    c = cd.do(T, "controls_save", {"answers": {"6.1": "no", "11.1": "yes", "11.2": "partial", "1.1": "yes", "zz": "yes"}})
    assert c["score"] == round(100 * 2.5 / 4) and c["gaps"][0]["id"] == "6.1" and c["functions"]["Protect"] is not None
    ar = cd.do(T, "access_review", {"text": USERS, "leavers": "gone@acme.example"})
    says = " | ".join(f"{f['user']}: {f['say']}" for f in ar["findings"])
    assert "gone@acme.example: Left the business" in says and "asha@acme.example: Admin without 2-step" in says
    assert "old@acme.example: Not used for" in says and "info@acme.example: Looks like a shared account" in says
    assert ar["summary"]["admins"] == 1 and ar["summary"]["high"] == 2
    sc = cd.do(T, "secrets_scan", {"text": CODE, "name": "app.py"})
    types = {f["type"] for f in sc["found"]}
    assert {"AWS access key", "Database URL with password", "Stripe key"} <= types
    assert "Sup3rSecret" not in str(sc) and "AKIA" + "ABCDEFGHIJKLMNOP" not in str(sc) and not any(f["line"] == 4 for f in sc["found"])
    rk = cd.do(T, "risk_save", {"title": "Ransomware on the Tally PC", "likelihood": 4, "impact": 5, "treatment": "reduce"})
    assert rk["risk"]["band"] == "high" and rk["risk"]["ref"] == "RK-0001"
    with pytest.raises(cd.CyDeskError):
        cd.do(T, "risk_save", {"title": "x", "likelihood": 9})
    v = cd.do(T, "vendor_save", {"name": "PayrollCo", "data_level": "sensitive", "answers": {"mfa": "yes", "encrypt": "yes"}})
    assert v["vendor"]["tier"] == "high" and v["vendor"]["next_review"]
    tt = cd.do(T, "tabletop_start", {"playbook": "phishing"})["tabletop"]
    cd.do(T, "tabletop_step", {"id": tt["id"], "i": 0, "ok": True})
    cd.do(T, "tabletop_step", {"id": tt["id"], "i": 1, "ok": False, "note": "nobody knew the admin console"})
    with pytest.raises(cd.CyDeskError):
        cd.do(T, "tabletop_finish", {"id": tt["id"], "lessons": ""})
    f = cd.do(T, "tabletop_finish", {"id": tt["id"], "lessons": "Write down who resets passwords", "minutes": "40"})
    assert f["tabletop"]["ready"] == 1 and f["tabletop"]["gaps"] == 1 and f["tabletop"]["status"] == "done"
    cd.do(T, "training_record", {"person": "Ravi", "topic": "phishing"})
    pol = cd.do(T, "policy_check", {"min_length": 6, "mfa": "some", "rotation_days": 90})
    assert pol["score"] < 50 and any("too short" in x["say"] for x in pol["findings"])
    k = cd.today_view(T)
    assert k["score"] is not None and any(p[0] == "Controls" for p in k["score_parts"])
    assert any("urgent account" in n["say"] for n in k["needs"]) and any("high risk" in n["say"] for n in k["needs"])


def test_uploads_and_tool(cd):
    import base64
    _hire()
    out = cd.upload(T, "defender.csv", DEFENDER_CSV.encode(), "intake")
    assert out.get("alerts") is not None or out.get("say")
    sc = cd.upload(T, "config.env", CODE.encode(), "secrets")
    assert sc["found"]
    from app.main import app
    from tests.test_v161_stream import KEY
    _ = base64, app, KEY
    import asyncio
    from app.agent.cyber_tools import CYBER_HANDLERS
    from app.agent.tools import Ctx
    ctx = Ctx(tenant_id=T, conversation_id="c1")
    r = asyncio.run(CYBER_HANDLERS["cyber"](ctx, action="playbook", playbook="lost_device"))
    assert r["title"].startswith("Lost")
    r2 = asyncio.run(CYBER_HANDLERS["cyber_dekho"](ctx, what="programme"))
    assert "controls" in r2 and r2["playbooks"]


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def cd_server(cd, monkeypatch):
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


def test_desk_in_a_real_browser(cd, cd_server):
    base, browser, key = cd_server
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
    pg.on("dialog", lambda d: d.accept("Our office VPN"))
    pg.goto(base + "/console/cyber")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    # alerts in, the one that matters opened
    go(pg, "#/alerts", "form[data-form=intake]")
    pg.fill("form[data-form=intake] [name=text]", SSH_LOG)
    pg.click("form[data-form=intake] [type=submit]")
    pg.wait_for_selector("details.qa-case", timeout=30000)
    pg.click("details.qa-case summary")
    pg.wait_for_selector("text=T1110", timeout=20000)
    snap(pg, "cy-alerts-1440")
    # a suspicious mail, secrets in code
    go(pg, "#/checks", "form[data-form=mail]")
    pg.fill("form[data-form=mail] [name=text]", PHISH_RAW)
    pg.click("form[data-form=mail] [type=submit]")
    pg.wait_for_selector(".cy-verdict", timeout=30000)
    pg.fill("form[data-form=secrets] [name=text]", CODE)
    pg.click("form[data-form=secrets] [type=submit]")
    pg.wait_for_selector("text=AWS access key", timeout=30000)
    snap(pg, "cy-checks-1440")
    # an incident with its notice clocks, a block card tapped
    go(pg, "#/incidents", "form[data-form=incident]")
    pg.fill("form[data-form=incident] [name=title]", "SSH break-in on the web server")
    pg.check("form[data-form=incident] [name=personal_data]")
    pg.click("form[data-form=incident] [type=submit]")
    pg.wait_for_selector("text=CERT-In", timeout=30000)
    pg.fill("form[data-form=contain] [name=target]", "45.155.205.12")
    pg.click("form[data-form=contain] [type=submit]")
    pg.wait_for_selector("form[data-form=decide]", timeout=30000)
    snap(pg, "cy-incidents-1440")
    pg.click("form[data-form=decide] [data-yes='1']")
    pg.wait_for_selector("form[data-form=decide]", state="detached", timeout=30000)
    # programme: controls, access review, a risk
    go(pg, "#/programme", "form[data-form=controls]")
    pg.click("details[data-key='ct:6'] summary")
    pg.click("details[data-key='ct:11'] summary")
    pg.select_option("form[data-form=controls] select[name='6.1']", "no")
    pg.select_option("form[data-form=controls] select[name='11.1']", "yes")
    pg.click("form[data-form=controls] [type=submit]")
    pg.wait_for_selector("text=Biggest gaps", timeout=30000)
    pg.click("[data-ps=access]")
    pg.fill("form[data-form=access] [name=text]", USERS)
    pg.fill("form[data-form=access] [name=leavers]", "gone@acme.example")
    pg.click("form[data-form=access] [type=submit]")
    pg.wait_for_selector("text=Left the business", timeout=30000)
    snap(pg, "cy-access-1440")
    pg.click("[data-ps=risks]")
    pg.fill("form[data-form=risk] [name=title]", "Ransomware on the Tally PC")
    pg.select_option("form[data-form=risk] [name=likelihood]", "4")
    pg.select_option("form[data-form=risk] [name=impact]", "5")
    pg.click("form[data-form=risk] [type=submit]")
    pg.wait_for_selector("text=RK-0001", timeout=30000)
    snap(pg, "cy-programme-1440")
    go(pg, "#/settings", "form[data-form=cyset]")
    pg.fill("form[data-form=cyset] [name=country]", "DE")
    pg.click("form[data-form=cyset] [type=submit]")
    pg.wait_for_selector("text=Saved", timeout=20000)
    go(pg, "#/today", "text=Security score")
    snap(pg, "cy-today-1440")
    for route, sel in (("#/today", "text=Needs you"), ("#/alerts", "form[data-form=intake]"), ("#/checks", "form[data-form=mail]"),
                       ("#/surface", "form[data-form=domain]"), ("#/incidents", "form[data-form=incident]"), ("#/programme", ".cy-sub"),
                       ("#/settings", "form[data-form=cyset]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
    snap(pg, "cy-programme-390")
    assert not errs, errs
