"""INSTITUTION DESK: the Institution employee's own section, built like Payroll, Tax, Cash & Treasury, Credit & Lending, Firm Practice and
Payments - its own chat (kind 'institution') with the desk block + the institution tool in view; an institution set up on the desk with her
as the first admin; who she is on the desk (the owner picks her person, an admin links a team member's login); the five areas - financial
crime (transactions -> alerts -> a SAR draft into maker-checker, scored by the MLRO, sanctions against her list, KYC), compliance
(obligations with sources, marked done; complaints; policy and promotion checks), risk (incidents with her clocks, RCSA heat map, third
parties, models, ECL), audit (prepared-by-client list, a recorded sample, results per item -> the control test, journal tests), governance
(board pack, cap table, related parties, whistleblowing with a case number only) - and maker-checker under all of them (the maker never
checks, two checkers above her limit, a check holds for the exact text); the downloads; and the desk walked in a real browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def ic(env):
    from app import instchat as IC
    IC._OF.clear()
    IC._BLOCK.clear()
    return IC


def _inst(ic, name="Northgate Bank"):
    return ic.setup(T, {"name": name, "admin": "Ada Shaw", "country": "GB", "currency": "GBP", "roles": ["compliance"]})


def _team(ic, ws):
    for n, r in (("Mia Cole", ["maker"]), ("Cal Ng", ["checker"]), ("Cat Ruiz", ["checker"]), ("Mo Khan", ["mlro", "checker"]),
                 ("Rita Bose", ["risk"]), ("Aud Lee", ["audit"]), ("Sam Ford", ["secretary"])):
        ic.do(T, "person_add", {"workspace": ws, "name": n, "roles": r})


TX = ("id,customer,date,amount,direction,channel,country,counterparty\n"
      + "".join(f"t{k},C1,2026-03-0{k},9500,in,cash,GB,\n" for k in range(1, 5))
      + "u1,C2,2026-03-01,100,in,cash,GB,\nu2,C2,2026-03-02,4000,out,wire,GB,Ravi Shah\n")


def test_hire_setup_chat_block_and_wiring(ic):
    from pathlib import Path
    from app.employee import hire
    root = Path(__file__).resolve().parents[2]
    assert ic.summary(T)["hired"] is False
    hire.hire(T, "institution_desk", trust="seekh")
    d = ic.summary(T)
    assert d["hired"] and d["workspace"] is None and "Nothing is filed" in d["foot"]
    assert "Set up your institution" in ic.greeting(T) and "No institution set up yet" in ic.block(T)
    with pytest.raises(ic.InstDeskError):
        ic.setup(T, {"name": "X", "admin": "", "country": "GB", "currency": "GBP"})
    f = _inst(ic)
    d = ic.summary(T)
    assert d["workspace"]["id"] == f["institution"]["id"] and d["me"]["name"] == "Ada Shaw" and d["me"]["roles"] == ["admin", "compliance"]
    assert any("second person" in n["say"] for n in d["desk"]["needs"])
    chat = ic.current(T)
    assert ic.is_institution(chat["id"]) and ic.owns(T, chat["id"])
    ic.forget(T)
    blk = ic.block(T)
    assert "<institution_desk>" in blk and "person id ada-shaw" in blk and "files nothing" in blk
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_inc.is_institution(conversation_id)" in src and "adm.admit_families(_inc.FAMILIES)" in src
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["institution_desk"] in ic.FAMILIES
    for f_ in ("callconv.py", "convs.py"):
        assert '"payments", "institution"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/institution")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "instdesk.js" in r.text
    html = (root / "server/app/static/console/instdesk.html").read_text()
    for x in ("chatkit.js", "seodesk.css", "moneydesk.css", "cashdesk.css", "creditdesk.css", "instdesk.css", "instdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/institution')" in (root / "server/app/static/console/v2.js").read_text()
    assert "institution_desk: 'instdesk'" in (root / "server/app/static/console/employees.js").read_text()
    assert "'/console/institution'" in (root / "lib/ui/shell/hoola_employees.dart").read_text()


def test_crime_sar_maker_checker_and_score(ic):
    from app.employee import hire
    from app.fin import laws as L
    hire.hire(T, "institution_desk", trust="seekh")
    ws = _inst(ic)["institution"]["id"]
    _team(ic, ws)
    ic.do(T, "limits", {"workspace": ws, "single_check_limit": 10000})
    ic.do(T, "be", {"workspace": ws, "person": "sam-ford"})
    with pytest.raises(ic.InstDeskError, match="does not hold"):
        ic.do(T, "upload", {"workspace": ws, "kind": "transactions", "text": TX})
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    up = ic.do(T, "upload", {"workspace": ws, "kind": "transactions", "text": TX, "name": "march.csv"})
    assert up["rows"] == 6
    r = ic.do(T, "aml", {"workspace": ws})
    assert [a["rule"] for a in r["alerts"]] == ["structuring"] and r["alerts"][0]["customer"] == "C1"
    assert ic.summary(T)["desk"]["areas"]["crime"]["alerts"] == 1
    s = ic.do(T, "sar_draft", {"workspace": ws, "alert": r["alerts"][0], "customer": {"name": "X Ltd", "expected_activity": "salary"}})
    assert s["checks"]["ok"] and s["draft"]["state"] == "waiting" and "38,000.00" in s["body"]
    did = s["draft"]["id"]
    v = ic.do(T, "draft", {"workspace": ws, "draft": did})
    assert not v["can"]["check"] and "another checker" in v["why_not_check"]
    with pytest.raises(ic.InstDeskError):
        ic.do(T, "check", {"workspace": ws, "draft": did, "verdict": "approve", "hash": v["hash"]})
    ic.do(T, "be", {"workspace": ws, "person": "cal-ng"})
    d = ic.summary(T)["desk"]
    assert d["drafts"]["for_me"][0]["id"] == did and any(n["go"] == f"drafts/{did}" for n in d["needs"])
    with pytest.raises(ic.InstDeskError, match="not the current text"):
        ic.do(T, "check", {"workspace": ws, "draft": did, "verdict": "approve", "hash": "x"})
    with pytest.raises(ic.InstDeskError, match="Only an MLRO"):
        ic.do(T, "sar_score", {"workspace": ws, "draft": did, "scores": {k: 4 for k in ("facts_complete", "clear_and_ordered", "why_suspicious",
                                                                                      "no_accusation", "ready_to_file")}})
    assert ic.do(T, "check", {"workspace": ws, "draft": did, "verdict": "approve", "hash": v["hash"]})["draft"]["state"] == "approved"
    ic.do(T, "be", {"workspace": ws, "person": "mo-khan"})
    sc = ic.do(T, "sar_score", {"workspace": ws, "draft": did, "scores": {k: 4 for k in ("facts_complete", "clear_and_ordered", "why_suspicious",
                                                                                        "no_accusation", "ready_to_file")}, "comment": "good"})
    assert sc["total"] == 20
    assert ic.do(T, "draft", {"workspace": ws, "draft": did})["scores"][0]["by_name"] == "Mo Khan"
    # an amount above the limit needs two checkers
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    big = ic.do(T, "submit", {"workspace": ws, "kind": "limit", "title": "Raise the cash limit", "body": "raise", "amount": 50000})["draft"]
    assert big["needs_checks"] == 2
    ic.do(T, "be", {"workspace": ws, "person": "cal-ng"})
    assert ic.do(T, "check", {"workspace": ws, "draft": big["id"], "verdict": "approve", "hash": big["hash"]})["draft"]["state"] == "waiting"
    assert not ic.do(T, "draft", {"workspace": ws, "draft": big["id"]})["can"]["check"]
    ic.do(T, "be", {"workspace": ws, "person": "cat-ruiz"})
    assert ic.do(T, "check", {"workspace": ws, "draft": big["id"], "verdict": "approve", "hash": big["hash"]})["draft"]["state"] == "approved"
    # a changed text drops every check; a rejection needs a reason
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    p = ic.do(T, "submit", {"workspace": ws, "kind": "policy", "title": "AML policy", "body": "v1"})["draft"]
    ic.do(T, "be", {"workspace": ws, "person": "cal-ng"})
    with pytest.raises(ic.InstDeskError, match="reason"):
        ic.do(T, "check", {"workspace": ws, "draft": p["id"], "verdict": "reject", "hash": p["hash"]})
    ic.do(T, "check", {"workspace": ws, "draft": p["id"], "verdict": "reject", "hash": p["hash"], "reason": "No owner named"})
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    assert any("Rejected" in n["say"] for n in ic.summary(T)["desk"]["needs"])
    r2 = ic.do(T, "revise", {"workspace": ws, "draft": p["id"], "body": "v2\nOwner: Ada"})["draft"]
    assert r2["state"] == "waiting" and r2["checks"] == []
    # sanctions on her own list
    ic.do(T, "register", {"workspace": ws, "register": "watch", "item": {"name": "Ivan Petrov", "list": "UK", "ref": "R1"}})
    sn = ic.do(T, "sanctions", {"workspace": ws, "names": "Ivan Petrov\nJane Doe"})
    assert sn["results"][0]["possible_matches"][0]["watch_name"] == "Ivan Petrov" and not sn["results"][1]["possible_matches"]
    with pytest.raises(L.Refused):
        ic._engine(T, "x", "file_sar", {"workspace": ws, "person": "mo-khan"})


def test_compliance_risk_audit_governance(ic):
    from app.employee import hire
    hire.hire(T, "institution_desk", trust="seekh")
    ws = _inst(ic)["institution"]["id"]
    _team(ic, ws)
    with pytest.raises(ic.InstDeskError, match="source"):
        ic.do(T, "obligation_add", {"workspace": ws, "item": {"name": "AML policy review"}})
    ic.do(T, "obligation_add", {"workspace": ws, "item": {"name": "AML policy review", "source": "MLR 2017 reg 19", "owner": "Mo",
                                                          "control": "annual review", "every_days": 365, "last_done": "2025-01-01"}})
    assert ic.summary(T)["desk"]["areas"]["compliance"]["overdue"] == ["AML policy review"]
    ic.do(T, "obligation_done", {"workspace": ws, "i": 0})
    assert ic.summary(T)["desk"]["areas"]["compliance"]["overdue"] == []
    ic.do(T, "upload", {"workspace": ws, "kind": "complaints", "text": "category,received,closed,upheld\nfees,2026-01-01,2026-01-20,yes\n"
                                                                      "fees,2026-01-01,2026-04-20,no\nservice,2026-02-01,,\n"})
    cm = ic.do(T, "complaints", {"workspace": ws})
    assert cm["total"] == 3 and cm["late"] == 1 and "check this" in cm["deadline_days"]
    pr = ic.do(T, "promotion_check", {"workspace": ws, "text": "Guaranteed 12% returns!"})
    assert not pr["ok"] and any("promise" in x for x in pr["problems"])
    # risk: incidents with clocks, recorded reports, rcsa, vendors, models, ecl
    ic.do(T, "be", {"workspace": ws, "person": "rita-bose"})
    i = ic.do(T, "incident", {"workspace": ws, "title": "Card outage", "detected": "2026-03-01T09:00", "severity": "high"})
    assert i["due"][0]["due"] == "2026-03-01T13:00" and "check this" in i["says"]
    ic.do(T, "settings", {"workspace": ws, "clocks": [{"report": "Initial", "hours": 2}]})
    i2 = ic.do(T, "incident", {"workspace": ws, "title": "Data leak", "detected": "2026-03-02T09:00"})
    assert i2["due"] == [{"report": "Initial", "due": "2026-03-02T11:00"}]
    inc = ic.do(T, "incident_report", {"workspace": ws, "n": 1, "report": "Initial notification", "at": "2026-03-01T12:00"})["incidents"]
    first = next(x for x in inc if x["title"] == "Card outage")
    assert first["clocks"][0]["reported"] == "2026-03-01T12:00" and not first["clocks"][0]["late"] and first["clocks"][1]["late"]
    for r in ({"name": "Fraud", "likelihood": 4, "impact": 5}, {"name": "Outage", "likelihood": 2, "impact": 3, "control_effect": 2}):
        ic.do(T, "register", {"workspace": ws, "register": "risks", "item": r})
    rc = ic.do(T, "rcsa", {"workspace": ws})
    assert rc["over_appetite"] == ["Fraud"] and rc["heat_map_impact_by_likelihood"][4][3] == 1
    ic.do(T, "register", {"workspace": ws, "register": "vendors", "item": {"name": "CloudCo", "service": "hosting", "critical": "yes"}})
    assert ic.do(T, "third_party", {"workspace": ws})["critical_without_exit_plan"] == ["CloudCo"]
    ic.do(T, "register", {"workspace": ws, "register": "models", "item": {"name": "Credit score", "owner": "Rita", "validated": "2024-01-01"}})
    assert ic.do(T, "models", {"workspace": ws})["overdue"] == ["Credit score"]
    ic.do(T, "upload", {"workspace": ws, "kind": "exposures", "text": "id,ead,pd,lgd,dpd\nL1,10000,0.02,0.4,0\nL2,5000,0.05,0.5,95\n"})
    e = ic.do(T, "ecl", {"workspace": ws})
    assert e["total_ecl"] == 2580.0 and e["by_stage"]["stage3"] == 2500.0
    with pytest.raises(ic.InstDeskError, match="does not hold"):
        ic.do(T, "register", {"workspace": ws, "register": "pbc", "item": {"item": "Bank letters"}})
    # audit: pbc, a recorded sample, results -> the control test, journal tests
    ic.do(T, "be", {"workspace": ws, "person": "aud-lee"})
    ic.do(T, "register", {"workspace": ws, "register": "pbc", "item": {"item": "Bank letters", "owner": "Finance", "due": "2026-01-01"}})
    assert ic.do(T, "pbc", {"workspace": ws})["late"] == ["Bank letters"]
    ic.do(T, "register", {"workspace": ws, "register": "pbc", "edit": 1, "set": {"received": True}})
    assert ic.do(T, "pbc", {"workspace": ws})["outstanding"] == []
    sm = ic.do(T, "sample", {"workspace": ws, "population": "a\nb\nc\nd\ne", "size": 2, "seed": 7, "control": "Payment approval"})["sample"]
    again = ic.do(T, "sample", {"workspace": ws, "population": "a\nb\nc\nd\ne", "size": 2, "seed": 7})["sample"]
    assert sm["sample"] == again["sample"] and sm["seed"] == 7
    ic.do(T, "test_result", {"workspace": ws, "n": sm["n"], "item": sm["sample"][0], "passed": True})
    t = ic.do(T, "test_result", {"workspace": ws, "n": sm["n"], "item": sm["sample"][1], "passed": False, "note": "no approval"})
    assert t["test"]["conclusion"] == "deficiency"
    ic.do(T, "upload", {"workspace": ws, "kind": "journals", "text": "id,date,amount,user,description\nJ1,2026-03-07,5000,zed,\nJ2,2026-03-04,123.4,ann,ok\n"})
    ic.do(T, "settings", {"workspace": ws, "period_end": "2026-03-08", "usual_users": "ann"})
    jf = ic.do(T, "je_test", {"workspace": ws})["flagged"]
    assert jf[0]["id"] == "J1" and set(jf[0]["flags"]) >= {"weekend", "round amount", "near period end", "unusual user", "no description"}
    # governance: board pack, cap table, related parties, whistleblowing
    ic.do(T, "be", {"workspace": ws, "person": "sam-ford"})
    ic.do(T, "register", {"workspace": ws, "register": "agenda", "item": {"item": "Risk report", "paper": "Risk pack"}})
    ic.do(T, "register", {"workspace": ws, "register": "actions", "item": {"action": "Hire an MLRO deputy", "owner": "Ada"}})
    b = ic.do(T, "board", {"workspace": ws})
    assert b["papers_missing"] == ["Risk pack"] and len(b["open_actions"]) == 1
    ic.do(T, "register", {"workspace": ws, "register": "papers", "item": {"paper": "Risk pack"}})
    assert ic.do(T, "board", {"workspace": ws})["papers_missing"] == []
    for h in ({"name": "Founders", "shares": 800}, {"name": "Seed Fund", "shares": 200}):
        ic.do(T, "register", {"workspace": ws, "register": "holders", "item": h})
    ct = ic.do(T, "cap_table", {"workspace": ws, "raise": 500000, "pre_money": 2000000, "investor": "Series A"})
    assert ct["new_shares"] == 250 and ct["after"]["Series A"]["pct"] == 20.0
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    ic.do(T, "upload", {"workspace": ws, "kind": "transactions", "text": TX})
    ic.do(T, "be", {"workspace": ws, "person": "sam-ford"})
    ic.do(T, "register", {"workspace": ws, "register": "related", "item": {"name": "Ravi Shah", "relation": "director"}})
    assert ic.do(T, "related", {"workspace": ws})["total"] == 4000.0
    with pytest.raises(ic.InstDeskError, match="no name"):
        ic.do(T, "whistle", {"workspace": ws, "what": "x", "name": "Bob"})
    w = ic.do(T, "whistle", {"workspace": ws, "what": "Expenses padded", "area": "finance"})
    assert w["case"].startswith("WB-")
    ic.do(T, "be", {"workspace": ws, "person": "ada-shaw"})
    ic.do(T, "whistle_status", {"workspace": ws, "case": w["case"], "status": "looking", "note": "Asked finance"})
    assert ic.do(T, "whistle_list", {"workspace": ws})["cases"][0]["status"] == "looking"


def test_team_logins_roles_keys_and_routes(ic):
    from app.employee import hire
    from app.main import app
    hire.hire(T, "institution_desk", trust="seekh")
    c = TestClient(app)
    assert c.post("/api/institution/setup", json={"name": "Northgate Bank", "admin": "Ada Shaw", "country": "GB", "currency": "GBP"}).status_code == 200
    d = c.get("/api/institution/desk").json()
    ws = d["workspace"]["id"]
    assert d["me"]["id"] == "ada-shaw"
    _team(ic, ws)
    out = ic.do(T, "link", {"workspace": ws, "target": "mia-cole", "email": "mia@example.com"})
    assert out["logins"]["mia-cole"] == "mia@example.com"
    with pytest.raises(ic.InstDeskError, match="email"):
        ic.do(T, "link", {"workspace": ws, "target": "mia-cole", "email": "nope"})
    assert ic.do(T, "roles", {"workspace": ws, "target": "mia-cole", "roles": ["maker", "viewer"]})["person"]["roles"] == ["maker", "viewer"]
    with pytest.raises(ic.InstDeskError, match="at least one admin"):
        ic.do(T, "roles", {"workspace": ws, "target": "ada-shaw", "roles": ["compliance"]})
    k = ic.do(T, "api_key", {"workspace": ws, "scopes": ["read"]})
    assert k["key"].startswith("hik_") and ic.summary(T)["desk"]["keys"][0]["scopes"] == ["read"] and "hash" not in ic.summary(T)["desk"]["keys"][0]
    ic.do(T, "retention", {"workspace": ws, "keep_years": {"sar": 5}})
    ex = c.get("/api/institution/download", params={"workspace": ws, "what": "export"})
    assert ex.status_code == 200 and b'"registers"' in ex.content and b"hik_" not in ex.content
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    with pytest.raises(ic.InstDeskError, match="Only an admin"):
        ic.do(T, "link", {"workspace": ws, "target": "cal-ng", "email": "c@example.com"})
    dr = ic.do(T, "submit", {"workspace": ws, "kind": "board", "title": "Board paper", "body": "# Paper\nText"})["draft"]
    pdf = c.get("/api/institution/download", params={"workspace": ws, "what": "draft", "draft": dr["id"]})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert c.post("/api/institution/do/nope", json={"workspace": ws}).status_code == 400
    assert c.post("/api/institution/do/file_sar", json={"workspace": ws}).status_code == 400
    assert c.get("/api/institution/chat").json()["id"]
    assert c.put("/api/institution/workspace", json={"workspace": "nope"}).status_code == 400
    assert c.get("/api/institution/download", params={"workspace": ws, "what": "draft", "draft": "x"}).status_code == 400


@pytest.fixture
def ic_server(ic, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "institution_desk", trust="seekh")
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


def test_desk_in_a_real_browser(ic, ic_server, tmp_path):
    base, browser, key = ic_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route):
        pg.evaluate(f"location.hash = '{route}'")

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/institution")
    pg.wait_for_selector("text=Set up your institution", timeout=20000)
    snap(pg, "inst-setup-1440")
    pg.fill("form[data-form=setup] [name=name]", "Northgate Bank")
    pg.fill("form[data-form=setup] [name=admin]", "Ada Shaw")
    pg.fill("form[data-form=setup] [name=country]", "GB")
    pg.fill("form[data-form=setup] [name=currency]", "GBP")
    pg.check("form[data-form=setup] input[value=compliance]")
    pg.click("form[data-form=setup] [type=submit]")
    pg.wait_for_selector("text=Add a second person", timeout=20000)
    ws = ic.summary(T)["workspace"]["id"]
    _team(ic, ws)
    ic.do(T, "limits", {"workspace": ws, "single_check_limit": 10000})
    ic.do(T, "obligation_add", {"workspace": ws, "item": {"name": "AML policy review", "source": "MLR 2017 reg 19", "owner": "Mo Khan",
                                                          "control": "annual review", "every_days": 365, "last_done": "2025-01-01"}})
    ic.do(T, "be", {"workspace": ws, "person": "rita-bose"})
    ic.do(T, "incident", {"workspace": ws, "title": "Card outage", "detected": "2026-03-01T09:00", "severity": "high"})
    for r in ({"name": "Fraud", "likelihood": 4, "impact": 5, "owner": "Rita"}, {"name": "Outage", "likelihood": 2, "impact": 3}):
        ic.do(T, "register", {"workspace": ws, "register": "risks", "item": r})
    ic.do(T, "register", {"workspace": ws, "register": "vendors", "item": {"name": "CloudCo", "service": "hosting", "critical": "yes"}})
    ic.do(T, "register", {"workspace": ws, "register": "models", "item": {"name": "Credit score", "owner": "Rita", "validated": "2024-01-01", "ai": "yes"}})
    ic.do(T, "upload", {"workspace": ws, "kind": "exposures", "text": "id,ead,pd,lgd,dpd\nL1,10000,0.02,0.4,0\nL2,5000,0.05,0.5,95\nL3,8000,0.03,0.4,40\n"})
    ic.do(T, "be", {"workspace": ws, "person": "sam-ford"})
    ic.do(T, "register", {"workspace": ws, "register": "agenda", "item": {"item": "Risk report", "paper": "Risk pack"}})
    ic.do(T, "register", {"workspace": ws, "register": "actions", "item": {"action": "Hire an MLRO deputy", "owner": "Ada"}})
    for h in ({"name": "Founders", "shares": 800}, {"name": "Seed Fund", "shares": 200}):
        ic.do(T, "register", {"workspace": ws, "register": "holders", "item": h})
    ic.do(T, "be", {"workspace": ws, "person": "mia-cole"})
    pg.reload()
    pg.wait_for_selector(".ins-areas .ins-area", timeout=20000)
    # financial crime: upload the transactions in the page, draft a report from the alert
    go(pg, "#/crime")
    pg.wait_for_selector("text=Upload transactions", timeout=20000)
    f = tmp_path / "march.csv"
    f.write_text(TX)
    pg.set_input_files("form[data-kind=transactions] input[type=file]", str(f))
    pg.wait_for_selector(".ins-alert", timeout=20000)
    pg.click(".ins-alert [data-sar='0']")
    pg.fill("form[data-form=sar] [name=name]", "X Ltd")
    pg.fill("form[data-form=sar] [name=expected_activity]", "salary")
    pg.click("form[data-form=sar] [type=submit]")
    pg.wait_for_selector("text=Machine checks passed", timeout=20000)
    snap(pg, "inst-crime-1440")
    did = ic.do(T, "drafts", {"workspace": ws})["drafts"][0]["id"]
    # the checker approves it on the draft page
    ic.do(T, "be", {"workspace": ws, "person": "cal-ng"})
    pg.goto(base + "/console/institution#/today")
    pg.reload()
    pg.wait_for_selector(".ins-areas", timeout=20000)
    snap(pg, "inst-today-1440")
    go(pg, f"#/drafts/{did}")
    pg.wait_for_selector("form[data-form=check]", timeout=20000)
    pg.click("form[data-form=check] [data-verdict='approve']")
    pg.wait_for_selector(".fm-seal", timeout=20000)
    snap(pg, "inst-draft-1440")
    # the MLRO scores it
    ic.do(T, "be", {"workspace": ws, "person": "mo-khan"})
    pg.reload()
    pg.wait_for_selector("form[data-form=score]", timeout=20000)
    pg.select_option("form[data-form=score] [name=facts_complete]", "5")
    pg.click("form[data-form=score] [type=submit]")
    pg.wait_for_selector("text=17/25", timeout=20000)
    # risk: mark a report done
    ic.do(T, "be", {"workspace": ws, "person": "rita-bose"})
    pg.reload()
    go(pg, "#/risk")
    pg.wait_for_selector(".ins-heat .has", timeout=20000)
    pg.click("[data-reported='1'][data-rep='Initial notification']")
    pg.wait_for_selector(".ins-clock.done", timeout=20000)
    snap(pg, "inst-risk-1440")
    # audit: a sample, pass and fail
    ic.do(T, "be", {"workspace": ws, "person": "aud-lee"})
    pg.reload()
    go(pg, "#/audit")
    pg.wait_for_selector("form[data-form=sample]", timeout=20000)
    pg.fill("form[data-form=sample] [name=control]", "Payment approval")
    pg.fill("form[data-form=sample] [name=size]", "2")
    pg.fill("form[data-form=sample] [name=population]", "P1\nP2\nP3\nP4")
    pg.click("form[data-form=sample] [type=submit]")
    pg.wait_for_selector(".ins-sample", timeout=20000)
    pg.locator(".ins-item [data-pass='1']").first.click()
    pg.wait_for_selector(".ins-item.ok", timeout=20000)
    pg.locator(".ins-item input[data-note]").first.fill("no approval")
    pg.locator(".ins-item [data-pass='0']").first.click()
    pg.wait_for_selector(".ins-sample .cs-tag.bad >> text=Deficiency", timeout=20000)
    snap(pg, "inst-audit-1440")
    # governance: a round, a whistleblowing case
    ic.do(T, "be", {"workspace": ws, "person": "sam-ford"})
    pg.reload()
    go(pg, "#/governance")
    pg.wait_for_selector("form[data-form=round]", timeout=20000)
    pg.fill("form[data-form=round] [name=raise]", "500000")
    pg.fill("form[data-form=round] [name=pre_money]", "2000000")
    pg.fill("form[data-form=round] [name=investor]", "Series A")
    pg.click("form[data-form=round] [type=submit]")
    pg.wait_for_selector(".ins-cap.after >> text=Series A", timeout=20000)
    pg.fill("form[data-form=whistle] [name=what]", "Expenses padded")
    pg.click("form[data-form=whistle] [type=submit]")
    pg.wait_for_selector(".ins-case", timeout=20000)
    snap(pg, "inst-governance-1440")
    # compliance and team as the admin
    ic.do(T, "be", {"workspace": ws, "person": "ada-shaw"})
    pg.reload()
    go(pg, "#/compliance")
    pg.wait_for_selector("[data-obdone='0']", timeout=20000)
    pg.click("[data-obdone='0']")
    pg.wait_for_selector("text=Marked done today", timeout=20000)
    pg.fill("form[data-form=promo] [name=text]", "Guaranteed 12% returns!")
    pg.click("form[data-form=promo] [type=submit]")
    pg.wait_for_selector("text=problems found", timeout=20000)
    snap(pg, "inst-compliance-1440")
    go(pg, "#/team")
    pg.wait_for_selector("form[data-form=person]", timeout=20000)
    pg.click("[data-linkp='mia-cole']")
    pg.fill("form[data-form=link] [name=email]", "mia@example.com")
    pg.click("form[data-form=link] [type=submit]")
    pg.wait_for_selector("text=login mia@example.com", timeout=20000)
    snap(pg, "inst-team-1440")
    go(pg, "#/drafts")
    pg.wait_for_selector(".fm-flow", timeout=20000)
    pg.click("[data-df='approved']")
    pg.wait_for_function("document.querySelectorAll('.fm-cards .fm-card').length === 1")
    snap(pg, "inst-drafts-1440")
    ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for route, sel, name in (("", ".ins-areas", "today"), ("#/crime", ".ins-alert", "crime"), ("#/compliance", "text=Obligations", "compliance"),
                             ("#/risk", ".ins-heat", "risk"), ("#/audit", ".ins-sample", "audit"), ("#/governance", "text=Board pack", "governance"),
                             (f"#/drafts/{did}", ".fm-seal", "draft"), ("#/team", "form[data-form=person]", "team")):
        pg.goto(base + "/console/institution" + route)
        pg.wait_for_selector(sel, timeout=20000)
        snap(pg, f"inst-{name}-390")
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (name, pg.evaluate("[...document.querySelectorAll('#insPage *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right))"))
    ctx.close()
    assert not errs, errs
