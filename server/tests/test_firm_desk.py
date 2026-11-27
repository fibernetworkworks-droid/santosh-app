"""FIRM PRACTICE DESK: the Firm Practice employee's own section, built like Payroll, Tax, Cash & Treasury and Credit & Lending - its own
chat (kind 'firm') with the desk block + the firm tool in view; a firm set up on the desk with her as the first partner; who she is on the
desk (the owner picks her person, a partner links a team member's login); clients, papers asked for and received, drafts that go
preparer -> reviewer -> the named signer -> the client's portal with the engine's checks (no self-review, only the signer signs, the
approval holds only for the exact text); engagement letters, fact-finds, meeting notes, suitability, the CFO pack, the audit trail; the
downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def fm(env):
    from app import firmchat as FC
    FC._OF.clear()
    FC._BLOCK.clear()
    return FC


def _firm(fm, name="Bright & Co"):
    return fm.setup(T, {"name": name, "partner": "Asha Rao", "country": "GB", "currency": "GBP"})


def _team(fm, ws):
    c = fm.do(T, "client_add", {"workspace": ws, "name": "Leaf Bakery"})["client"]
    fm.do(T, "person_add", {"workspace": ws, "name": "Ben Shah", "role": "preparer", "clients": [c["id"]]})
    fm.do(T, "person_add", {"workspace": ws, "name": "Cara Lim", "role": "reviewer", "clients": "all"})
    fm.do(T, "person_add", {"workspace": ws, "name": "Dev Leaf", "role": "client", "clients": [c["id"]]})
    return c["id"]


def test_hire_setup_chat_block_and_wiring(fm):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert fm.summary(T)["hired"] is False
    hire.hire(T, "firm_practice", trust="seekh")
    d = fm.summary(T)
    assert d["hired"] and d["workspace"] is None and "files nothing" in d["foot"]
    assert "Set up your firm" in fm.greeting(T) and "No firm set up yet" in fm.block(T)
    with pytest.raises(fm.FirmDeskError):
        fm.setup(T, {"name": "X", "partner": "", "country": "GB", "currency": "GBP"})
    f = _firm(fm)
    d = fm.summary(T)
    assert d["workspace"]["id"] == f["firm"]["id"] and d["me"]["name"] == "Asha Rao" and d["me"]["role"] == "partner"
    assert any("first client" in n["say"] for n in d["desk"]["needs"])
    chat = fm.current(T)
    assert fm.is_firm(chat["id"]) and fm.owns(T, chat["id"])
    fm.forget(T)
    blk = fm.block(T)
    assert "<firm_desk>" in blk and "person id asha-rao" in blk and "files nothing" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_fmc.is_firm(conversation_id)" in src and "adm.admit_families(_fmc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["firm_practice"] in fm.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"credit", "firm"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/firm")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "firmdesk.js" in r.text
    html = (root / "server/app/static/console/firmdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "firmdesk.css", "firmdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/firm')" in (root / "server/app/static/console/v2.js").read_text()
    assert "firm_practice: 'firmdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/firm'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_people_draft_review_sign_share_and_who_sees_what(fm):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "firm_practice", trust="seekh")
    ws = _firm(fm)["firm"]["id"]
    cid = _team(fm, ws)
    fm.do(T, "client_add", {"workspace": ws, "name": "Other Ltd"})
    r = fm.do(T, "request", {"workspace": ws, "client": cid, "items": ["Bank statements", "Payroll summary"], "due": "2026-01-10"})
    assert r["request"] == "rq1"
    d = fm.summary(T)["desk"]
    assert any("paper(s) late" in n["say"] for n in d["needs"]) and len(d["clients"]) == 2
    # Ben (preparer) makes the draft
    fm.do(T, "be", {"workspace": ws, "person": "ben-shah"})
    me = fm.summary(T)
    assert me["me"]["role"] == "preparer" and [c["name"] for c in me["desk"]["clients"]] == ["Leaf Bakery"]   # only his client
    with pytest.raises(fm.FirmDeskError):
        fm.do(T, "client", {"workspace": ws, "client": next(c for c in fm._clients(T, ws) if c != cid)})
    dr = fm.do(T, "new_draft", {"workspace": ws, "client": cid, "kind": "accounts", "title": "Year-end accounts",
                                "body": "# Accounts\nProfit 12,000", "signer": "asha-rao"})["draft"]
    v = fm.do(T, "draft", {"workspace": ws, "draft": dr["id"]})
    assert not v["can"]["review"] and v["why_not_review"] and not v["can"]["sign"]
    with pytest.raises(fm.FirmDeskError, match="Only partner, manager, reviewer"):
        fm.do(T, "review", {"workspace": ws, "draft": dr["id"], "verdict": "approve"})
    # Cara reviews: send back, Ben changes, Cara approves
    fm.do(T, "be", {"workspace": ws, "person": "cara-lim"})
    assert fm.summary(T)["desk"]["queue"]["to_review"][0]["id"] == dr["id"]
    with pytest.raises(fm.FirmDeskError, match="notes"):
        fm.do(T, "review", {"workspace": ws, "draft": dr["id"], "verdict": "send_back"})
    fm.do(T, "review", {"workspace": ws, "draft": dr["id"], "verdict": "send_back", "notes": "Add the tax line"})
    fm.do(T, "be", {"workspace": ws, "person": "ben-shah"})
    assert any("Sent back to you" in n["say"] for n in fm.summary(T)["desk"]["needs"])
    fm.do(T, "edit", {"workspace": ws, "draft": dr["id"], "body": "# Accounts\nProfit 12,000\nTax 2,280"})
    fm.do(T, "be", {"workspace": ws, "person": "cara-lim"})
    h = fm.do(T, "draft", {"workspace": ws, "draft": dr["id"]})["hash"]
    fm.do(T, "review", {"workspace": ws, "draft": dr["id"], "verdict": "approve", "hash": h})
    with pytest.raises(fm.FirmDeskError, match="named signer"):
        fm.do(T, "sign", {"workspace": ws, "draft": dr["id"]})
    # Asha signs and shares; the client sees it on their portal, and only their own
    fm.do(T, "be", {"workspace": ws, "person": "asha-rao"})
    assert fm.do(T, "draft", {"workspace": ws, "draft": dr["id"]})["can"]["sign"]
    s = fm.do(T, "sign", {"workspace": ws, "draft": dr["id"]})
    assert s["draft"]["state"] == "signed" and "Asha Rao" in s["says"]
    fm.do(T, "share", {"workspace": ws, "draft": dr["id"]})
    pdf = TestClient(app).get("/api/firm/download", params={"workspace": ws, "draft": dr["id"]})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    md = TestClient(app).get("/api/firm/download", params={"workspace": ws, "draft": dr["id"], "what": "md"})
    assert "Tax 2,280" in md.text
    own = fm.do(T, "new_draft", {"workspace": ws, "client": cid, "kind": "memo", "title": "Note", "body": "x", "signer": "asha-rao"})["draft"]
    with pytest.raises(fm.FirmDeskError, match="cannot review"):
        fm.do(T, "review", {"workspace": ws, "draft": own["id"], "verdict": "approve"})       # nobody reviews their own draft
    fm.do(T, "be", {"workspace": ws, "person": "dev-leaf"})
    cd = fm.summary(T)["desk"]
    assert cd["portal"]["client"] == "Leaf Bakery" and cd["portal"]["shared_with_you"][0]["title"] == "Year-end accounts"
    assert "clients" not in cd and any("paper(s) your firm asked for" in n["say"] for n in cd["needs"])
    fm.do(T, "provide", {"workspace": ws, "request": "rq1", "item": "Bank statements"})
    with pytest.raises(fm.FirmDeskError, match="only see their own portal"):
        fm.do(T, "new_draft", {"workspace": ws, "client": cid, "kind": "memo", "body": "x", "signer": "asha-rao"})
    fm.do(T, "be", {"workspace": ws, "person": "asha-rao"})
    a = fm.do(T, "audit", {"workspace": ws, "client": cid})
    assert len(a["events"]) >= 5
    from app.fin import laws as L
    with pytest.raises(L.Refused):
        fm._engine(T, "x", "file_return", {"firm": ws, "person": "asha-rao"})


def test_engagement_factfind_meeting_suitability_and_logins(fm):
    from app.employee import hire
    hire.hire(T, "firm_practice", trust="seekh")
    ws = _firm(fm)["firm"]["id"]
    cid = _team(fm, ws)
    e = fm.do(T, "engagement", {"workspace": ws, "client": cid, "client_name": "Leaf Bakery", "services": ["Year-end accounts", "Tax return"],
                                "fee": "1,800 a year", "signer": "asha-rao"})
    assert e["draft"]["kind"] == "engagement" and "Year-end accounts" in e["draft"]["body"]
    ff = fm.do(T, "factfind", {"workspace": ws, "client": cid, "answers": {"objectives": "Retire at 60", "attitude_to_risk": "Medium"}})
    assert "income" in ff["missing"] and ff["factfind"]["objectives"] == "Retire at 60"
    m = fm.do(T, "meeting", {"workspace": ws, "client": cid, "text": "Action: send payslips by 2026-12-05\nDecided: move to quarterly VAT"})
    assert m["actions"][0]["due"] == "2026-12-05" and m["decisions"] == ["move to quarterly VAT"]
    with pytest.raises(fm.FirmDeskError, match="recommendation"):
        fm.do(T, "suitability", {"workspace": ws, "client": cid})
    su = fm.do(T, "suitability", {"workspace": ws, "client": cid, "recommendation": "A workplace pension top-up"})
    assert "costs and charges" in su["missing"] and "Retire at 60" in su["body"]
    cv = fm.do(T, "client", {"workspace": ws, "client": cid})
    assert cv["client"]["name"] == "Leaf Bakery" and [s["id"] for s in cv["signers"]] == ["asha-rao"] and cv["client_people"][0]["name"] == "Dev Leaf"
    # a partner links a team member's login; only a partner may
    out = fm.do(T, "link", {"workspace": ws, "target": "ben-shah", "email": "ben@example.com"})
    assert out["logins"]["ben-shah"] == "ben@example.com"
    with pytest.raises(fm.FirmDeskError, match="email"):
        fm.do(T, "link", {"workspace": ws, "target": "ben-shah", "email": "nope"})
    fm.do(T, "be", {"workspace": ws, "person": "ben-shah"})
    with pytest.raises(fm.FirmDeskError, match="Only a partner"):
        fm.do(T, "link", {"workspace": ws, "target": "cara-lim", "email": "c@example.com"})
    with pytest.raises(fm.FirmDeskError):
        fm.do(T, "person_add", {"workspace": ws, "name": "Zed", "role": "preparer"})       # only a partner adds people


def test_routes(fm):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "firm_practice", trust="seekh")
    c = TestClient(app)
    assert c.post("/api/firm/setup", json={"name": "Bright & Co", "partner": "Asha Rao", "country": "GB", "currency": "GBP"}).status_code == 200
    d = c.get("/api/firm/desk").json()
    ws = d["workspace"]["id"]
    assert d["me"]["id"] == "asha-rao"
    assert c.post("/api/firm/do/client_add", json={"workspace": ws, "name": "Leaf Bakery"}).status_code == 200
    assert c.post("/api/firm/do/nope", json={"workspace": ws}).status_code == 400
    assert c.get("/api/firm/chat").json()["id"]
    assert c.put("/api/firm/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/firm/download", params={"workspace": ws, "draft": "x"}).status_code == 400


@pytest.fixture
def fm_server(fm, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "firm_practice", trust="seekh")
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
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(fm, fm_server):
    base, browser, key = fm_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/firm")
    pg.wait_for_selector("text=Set up your firm", timeout=20000)
    snap(pg, "firm-setup-1440")
    pg.fill("form[data-form=setup] [name=name]", "Bright & Co")
    pg.fill("form[data-form=setup] [name=partner]", "Asha Rao")
    pg.fill("form[data-form=setup] [name=country]", "GB")
    pg.fill("form[data-form=setup] [name=currency]", "GBP")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Add your first client", timeout=20000)
    ws = fm.summary(T)["workspace"]["id"]
    cid = _team(fm, ws)
    fm.do(T, "request", {"workspace": ws, "client": cid, "items": ["Bank statements", "Payroll summary"], "due": "2026-01-10"})
    fm.do(T, "be", {"workspace": ws, "person": "ben-shah"})
    d1 = fm.do(T, "new_draft", {"workspace": ws, "client": cid, "kind": "accounts", "title": "Year-end accounts",
                                "body": "# Accounts\n\n- Profit 12,000\n- Tax 2,280", "signer": "asha-rao"})["draft"]
    fm.do(T, "be", {"workspace": ws, "person": "cara-lim"})
    fm.do(T, "review", {"workspace": ws, "draft": d1["id"], "verdict": "approve"})
    fm.do(T, "be", {"workspace": ws, "person": "ben-shah"})
    d2 = fm.do(T, "new_draft", {"workspace": ws, "client": cid, "kind": "letter", "title": "Payroll letter", "body": "Dear Dev", "signer": "asha-rao"})["draft"]
    fm.do(T, "be", {"workspace": ws, "person": "asha-rao"})
    pg.reload()
    pg.wait_for_selector(".fm-lane.sig .fm-mini", timeout=20000)
    assert pg.locator(".fm-lane.rev .fm-mini").count() == 1 and pg.locator(".fm-stack .row").count() == 1
    snap(pg, "firm-today-1440")
    pg.goto(base + f"/console/firm#/clients/{cid}")
    pg.wait_for_selector("text=Papers asked for", timeout=20000)
    pg.fill("#fmE2", "2,400 a year")                       # half-typed in another box ...
    pg.click("[data-provide='rq1'][data-item='Bank statements']")
    pg.wait_for_selector("text=Marked as received", timeout=20000)
    assert pg.input_value("#fmE2") == "2,400 a year"        # ... survives the save that redraws the page
    pg.fill("form[data-form=meeting] [name=text]", "Action: send payslips by 2026-12-05\nDecided: move to quarterly VAT")
    pg.click("form[data-form=meeting] [type=submit]")
    pg.wait_for_selector("text=move to quarterly VAT", timeout=20000)
    pg.click("[data-audit]")
    pg.wait_for_selector(".fm-trail >> text=papers asked for", timeout=20000)
    snap(pg, "firm-client-1440")
    pg.goto(base + f"/console/firm#/draft/{d1['id']}")
    pg.wait_for_selector("[data-sign]", timeout=20000)
    pg.click("[data-sign]")
    pg.wait_for_selector(".fm-seal", timeout=20000)
    pg.click("[data-share]")
    pg.wait_for_selector("text=Shared to the client", timeout=20000)
    snap(pg, "firm-draft-1440")
    pg.goto(base + f"/console/firm#/draft/{d2['id']}")
    pg.wait_for_selector("form[data-form=review]", timeout=20000)
    pg.fill("form[data-form=review] [name=notes]", "Add the dates")
    pg.click("form[data-form=review] [data-verdict='send_back']")
    pg.wait_for_selector(".md-alert >> text=Add the dates", timeout=20000)
    pg.goto(base + "/console/firm#/work")
    pg.wait_for_selector(".fm-flow", timeout=20000)
    pg.click("[data-wf='sent_back']")
    pg.wait_for_function("document.querySelectorAll('.fm-rows .fm-row').length === 1")
    snap(pg, "firm-work-1440")
    pg.goto(base + "/console/firm#/team")
    pg.wait_for_selector("text=Add a person", timeout=20000)
    pg.click("[data-linkp='ben-shah']")
    pg.fill("form[data-form=link] [name=email]", "ben@example.com")
    pg.click("form[data-form=link] [type=submit]")
    pg.wait_for_selector("text=login ben@example.com", timeout=20000)
    snap(pg, "firm-team-1440")
    pg.goto(base + "/console/firm#/settings")
    pg.wait_for_selector("text=Who you are on this desk", timeout=20000)
    pg.click("[data-be='dev-leaf']")
    pg.wait_for_selector("text=Papers your firm asked for", timeout=20000)
    assert pg.locator("#sdTabs [data-tab]").count() == 1 and pg.locator("text=Year-end accounts").count() == 1
    snap(pg, "firm-portal-1440")
    ctx.close()
    fm.do(T, "be", {"workspace": ws, "person": "asha-rao"})
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".fm-lanes", "today"), (f"#/clients/{cid}", "text=Papers asked for", "client"),
                             (f"#/draft/{d1['id']}", ".fm-seal", "draft"), ("#/work", ".fm-flow", "work"), ("#/team", "text=Add a person", "team")):
        pg.goto(base + "/console/firm" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"firm-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), name
    ctx.close()
    assert not errs, errs
