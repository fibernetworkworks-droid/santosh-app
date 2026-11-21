"""SUPPORT WORKFLOW (G8 of docs/SUPPORT_GLOBAL_PLAN.md): her ticket workflow - stages from her industry pack, changed on
the Workflow page; every ticket at one stage with one owner and a deadline; moves only along her arrows, Hoola only out of
its own stages, required fields first, every move recorded, the customer told where she ticked it; "where is my request"
answered from the real stage on every channel; tickets stuck at a stage. Walked in a real browser."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    return S


def _telecom():
    from app.seva import profile as PF
    pv = PF.preview(T, {"industry": "telecom"})
    PF.apply(T, {"industry": "telecom"}, pv["hash"])


def test_workflows_come_from_her_pack(sv):
    from app.seva import flow as FL
    assert [f["key"] for f in FL.flows(T)] == ["request"]                   # no setup = the default workflow
    from app.db import session
    with session() as s:
        s.query(FL.SevaFlow).delete()
    _telecom()
    keys = [f["key"] for f in FL.flows(T)]
    assert keys[0] == "fault" and "install" in keys


def test_check_a_workflow(sv):
    from app.seva import flow as FL
    good = {"key": "warranty", "name": "Warranty", "stages": [{"name": "New", "owner": "hoola", "hours": 2},
                                                             {"name": "Checked", "owner": "person:Meena", "hours": 24, "needs": ["serial"]},
                                                             {"name": "Closed", "owner": "team"}],
            "arrows": {"new": ["checked"], "checked": ["closed"], "closed": []}}
    c = FL.clean_flow(good)
    assert [s["key"] for s in c["stages"]] == ["new", "checked", "closed"] and c["stages"][1]["needs"] == ["serial"]
    for bad, word in ((good | {"arrows": {"new": ["checked"], "checked": [], "closed": []}}, "cannot be reached"),
                      (good | {"arrows": {"new": ["checked"], "checked": ["closed"], "closed": ["new"]}}, "must end"),
                      (good | {"stages": good["stages"][:1]}, "two stages"),
                      (good | {"stages": [dict(good["stages"][0], owner="boss")] + good["stages"][1:]}, "owner")):
        with pytest.raises(FL.FlowError, match=word):
            FL.clean_flow(bad)


def test_ticket_moves_along_her_arrows(sv, monkeypatch):
    from app.seva import flow as FL
    S = sv
    _telecom()
    told = []
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: (told.append(text), {"sent": "whatsapp"})[1])
    t = S.new_ticket(T, "no internet since morning, red light on the router", "whatsapp", name="Ana", phone="919800000001")
    v = S.ticket(T, t["number"])
    assert v["stage"]["flow"] == "fault" and v["stage"]["stage"] == "new" and v["stage"]["due"]
    with pytest.raises(FL.FlowError, match="can go to"):
        FL.move(T, t["number"], "fixed")                                   # not an arrow from New
    FL.move(T, t["number"], "checked", "hoola", "line looks down")          # New belongs to Hoola
    assert told and "step 2 of 7" in told[-1] and "Line checked remotely" in told[-1]
    FL.move(T, t["number"], "visit", "hoola")                               # 'Line checked' is Hoola's too
    with pytest.raises(FL.FlowError, match="belongs to"):
        FL.move(T, t["number"], "visited", "hoola", fields={"visit_window": "Thu 10-12"})   # the visit is the team's


def test_required_fields_and_history(sv, monkeypatch):
    from app.seva import flow as FL
    S = sv
    _telecom()
    monkeypatch.setattr(S, "_tell", lambda *a, **k: {"sent": ""})
    n = S.new_ticket(T, "no internet since morning", "phone", name="Ben", phone="919800000002")["number"]
    FL.move(T, n, "checked", "owner")
    FL.move(T, n, "visit", "owner")
    with pytest.raises(FL.FlowError, match="visit_window"):
        FL.move(T, n, "visited", "owner")                                  # 'Engineer visit booked' needs the window
    out = FL.move(T, n, "visited", "owner", "engineer went", {"visit_window": "Thu 10-12"})
    assert out["stage"]["stage"] == "visited" and out["stage"]["fields"]["visit_window"] == "Thu 10-12"
    moves = FL.history(T, out["id"])
    assert [m["to"] for m in moves] == ["new", "checked", "visit", "visited"] and moves[-1]["why"] == "engineer went"
    FL.move(T, n, "fixed", "owner")
    FL.move(T, n, "confirmed", "owner")
    done = FL.move(T, n, "closed", "owner")
    assert done["status"] == "closed" and done["stage"]["next"] == []


def test_where_is_my_request_answers_the_real_stage(sv, monkeypatch):
    from app.seva import engine as E
    from app.seva import flow as FL
    S = sv
    _telecom()
    monkeypatch.setattr(S, "_tell", lambda *a, **k: {"sent": ""})
    n = S.new_ticket(T, "no internet at home", "whatsapp", name="Chi", phone="919800000003")["number"]
    FL.move(T, n, "checked", "owner")
    st = S.customer_status(T, "wa:919800000003")
    assert st["tickets"][0]["stage"] == "checked" and "step 2 of 7: Line checked remotely" in st["tickets"][0]["line"]
    r = E.reply(T, "where is my complaint", "whatsapp", "wa:919800000003")
    assert r["decision"] == "status" and "Line checked remotely" in r["reply"] and n in r["reply"]


def test_her_changes_and_stuck(sv, monkeypatch):
    from app.db import session
    from app.seva import flow as FL
    S = sv
    _telecom()
    monkeypatch.setattr(S, "_tell", lambda *a, **k: {"sent": ""})
    n = S.new_ticket(T, "no internet", "phone", name="Dev", phone="919800000004")["number"]
    f = FL.flow(T, "fault")
    smaller = f | {"stages": [x for x in f["stages"] if x["key"] != "new"]}
    with pytest.raises(FL.FlowError, match="still at a stage you removed"):
        FL.save(T, smaller | {"arrows": {k: v for k, v in f["arrows"].items() if k != "new"}})
    renamed = f | {"stages": [dict(x, name="Ticket received") if x["key"] == "new" else x for x in f["stages"]]}
    assert FL.save(T, renamed)["version"] == 2
    assert FL.stuck(T) == []
    with session() as s:
        t = s.query(S.SevaTicket).filter(S.SevaTicket.number == n).one()
        from datetime import timedelta
        t.stage_due_at = S.clock() - timedelta(hours=1)
    assert [x["number"] for x in FL.stuck(T)] == [n]
    b = {x["key"]: x for x in FL.board(T)}["fault"]
    assert b["stages"][0]["open"] == 1 and b["stages"][0]["late"] == 1 and b["stages"][0]["name"] == "Ticket received"


def test_old_ticket_joins_and_routes_and_tool(sv):
    from app.agent import seva_tools as ST
    from app.db import session
    from app.main import app
    S = sv
    n = S.new_ticket(T, "please call me back about the bill", "phone", name="Eve", phone="919800000005")["number"]
    with session() as s:
        t = s.query(S.SevaTicket).filter(S.SevaTicket.number == n).one()
        t.flow, t.stage = "", ""                                            # as made before workflows
        from app.seva import flow as FL
        s.query(FL.SevaStageMove).filter(FL.SevaStageMove.ticket_id == t.id).delete()
    assert S.ticket(T, n)["stage"]["stage"] == "new"
    c = TestClient(app)
    r = c.get("/api/seva/flows").json()
    assert r["flows"][0]["key"] == "request" and r["board"]
    assert c.post(f"/api/seva/tickets/{n}/move", json={"to": "working"}).json()["stage"]["stage"] == "working"
    assert c.post(f"/api/seva/tickets/{n}/move", json={"to": "new"}).status_code == 400
    assert [m["to"] for m in c.get(f"/api/seva/tickets/{n}/moves").json()["moves"]] == ["new", "working"]
    bad = c.put("/api/seva/flows/x", json={"name": "X", "stages": [{"name": "Only", "owner": "team"}]})
    assert bad.status_code == 400
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    assert {"move", "flow_save"} <= set(names["seva"]["input_schema"]["properties"]["action"]["enum"])
    assert {"flows", "stuck"} <= set(names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"])


@pytest.fixture
def wf_server(sv, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    S = sv
    hire.hire(T, "support", trust="seekh")
    _telecom()
    n = S.new_ticket(T, "no internet since morning", "phone", name="Fay", phone="919800000006")["number"]
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
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, n
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_workflow_in_a_real_browser(wf_server):
    base, browser, key, n = wf_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/support#/workflow")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Where tickets are now')", timeout=20000)
    assert n in pg.inner_text("#spPage")
    form = "form.spFlow[data-key='fault']"
    pg.fill(f"{form} [data-stage]:first-child [data-k=name]", "Ticket received")
    pg.click(f"{form} button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Ticket received')", timeout=10000)
    pg.goto(base + f"/console/support#/ticket/{n}")
    pg.wait_for_selector("#spMove button[value=checked]")
    pg.click("#spMove button[value=checked]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Now: Line checked remotely')", timeout=10000)
    pg.click("#spPage details summary")
    pg.wait_for_function("() => document.querySelector('#spMoves').innerText.includes('Line checked remotely')", timeout=10000)
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 900})
    p2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(base + "/console/support#/workflow")
    m.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Your ticket workflow')", timeout=20000)
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    assert not errors, errors
