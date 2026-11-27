"""v0.999.232 THE ROUTE EDITOR (R1 of the Hoola Route plan; owner: design canvas -> "GO BUILD").

The Route page gets a real editor: the route drawn on a canvas she can drag, add to, change and delete from, with
notes, undo, zoom and a mini-map; a panel to set every step and what starts the route; an add-a-step panel over the
step kinds and Hoola's tools; Test route (a real run, even while the route is off); and Ask Hoola beside the canvas
(the route's own chat, kind 'route', out of her chat lists) that changes the same route. The home is redrawn too.

Pinned here: a route made from the page starts OFF with one placeholder step; a canvas save goes through the
engine's own validation and is refused (409) when Hoola or another tab changed the route meanwhile; a value the page
only saw masked is never written back over the real one; layout and notes are checked and capped; the catalog finds
tools by her words with their argument fields; Test route runs a switched-off route; the route chat stays out of her
chat list and its turn knows the route; deleting a route forgets its layout. Plus a Chromium walk at computer and
phone width.
"""
import asyncio
import os
import shutil
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.agent.tools import Ctx

BASE = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _wipe(t):
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _run(c):
    return asyncio.run(c)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import get_settings
    return TestClient(app), get_settings().tenant_id


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(D, "polite_s", 0)
    D._RUNNING.clear()
    yield
    D._RUNNING.clear()


def test_new_route_starts_off_and_the_canvas_saves_through_the_engine(bz):
    c, t = _client()
    _wipe(t)
    try:
        r = c.post("/api/route/routes", json={"title": "Every new order to my sheet!", "folder": "Shop"}).json()
        assert r["name"] == "every_new_order_to_my_sheet" and r["enabled"] is False and r["folder"] == "Shop"
        assert [s["id"] for s in r["graph"]] == ["tell_me"] and r["version"]
        r2 = c.post("/api/route/routes", json={"title": "Every new order to my sheet"}).json()
        assert r2["name"] == "every_new_order_to_my_sheet_2", "a second route of the same name gets its own name"
        steps = [{"id": "ask", "type": "approval", "label": "Ask me first", "question": "Go?"},
                 {"id": "check", "type": "condition", "filter": {"left": "{{vars.total}}", "op": "gt", "right": 100},
                  "then": [{"id": "tell", "type": "notify", "text": "Big one"}], "else": []},
                 {"id": "note", "type": "notify", "text": "Done", "app": {"kind": "notify"}}]
        bad = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": [{"id": "x", "type": "nope"}], "base": r["version"]})
        assert bad.status_code == 400 and "unknown type" in bad.json()["detail"]
        ok = c.put(f"/api/route/routes/{r['id']}/graph",
                   json={"steps": steps, "trigger": "schedule", "trigger_spec": {"at": ["09:00"], "days": ["mon", "fri"],
                                                                                 "timezone": "Europe/Berlin"}, "base": r["version"]})
        assert ok.status_code == 200, ok.text
        new = ok.json()
        assert new["trigger"] == "schedule" and new["next_due_at"] and new["enabled"] is False
        wf = D.get_workflow(t, wf_id=r["id"])
        assert [s["id"] for s in wf["steps"]] == ["ask", "check", "note"] and "app" not in wf["steps"][2], "drawing keys never stored"
        assert wf["steps"][0]["label"] == "Ask me first"
        stale = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": steps, "base": r["version"]})
        assert stale.status_code == 409 and "changed since you opened it" in stale.json()["detail"]
        bad_t = c.put(f"/api/route/routes/{r['id']}/graph", json={"steps": steps, "trigger": "schedule",
                                                                  "trigger_spec": {"at": ["25:00"]}, "base": new["version"]})
        assert bad_t.status_code == 400 and "HH:MM" in bad_t.json()["detail"]
    finally:
        _wipe(t)


def test_a_masked_value_is_never_written_back(bz, monkeypatch):
    from app.route import editor as E
    monkeypatch.setattr(D, "_masked", lambda v: v.replace("ID-998877", "ID-XXXX77") if isinstance(v, str) else
                        ({k: D._masked(x) for k, x in v.items()} if isinstance(v, dict) else
                         [D._masked(x) for x in v] if isinstance(v, list) else v))
    old = [{"id": "fill", "type": "tool", "name": "web_fetch", "args": {"note": "card ID-998877", "url": "https://a.example"}}]
    page = [{"id": "fill", "type": "tool", "name": "web_fetch", "args": {"note": "card ID-XXXX77", "url": "https://b.example"}},
            {"id": "more", "type": "notify", "text": "ID-XXXX77"}]
    got = E.unmask(page, old)
    assert got[0]["args"]["note"] == "card ID-998877", "the real value stays"
    assert got[0]["args"]["url"] == "https://b.example", "her real edit is kept"
    assert got[1]["text"] == "ID-XXXX77", "a new step keeps what she typed"


def test_layout_notes_are_checked(bz):
    from app.route import editor as E
    lay = E.clean_layout({"pos": {"trigger": [0, 0], "ask": [300.33, -40]},
                          "notes": [{"id": "n1", "x": 10, "y": 20, "w": 9000, "text": "Ask Ravi first", "color": "red"}]})
    assert lay["pos"]["ask"] == [300.3, -40.0]
    assert lay["notes"][0]["w"] == 600.0 and lay["notes"][0]["color"] == "yellow"
    for bad in ({"pos": {"a b": [1, 2]}}, {"pos": {"a": [1]}}, {"pos": {"a": ["x", 2]}}, {"notes": [{"x": 1}]},
                {"notes": [{"id": "n", "text": "x" * 3000}]}, {"notes": [{"id": f"n{i}"} for i in range(40)]}):
        with pytest.raises(ValueError):
            E.clean_layout(bad)


def test_layout_saves_and_the_route_carries_it(bz):
    c, t = _client()
    _wipe(t)
    try:
        r = c.post("/api/route/routes", json={"title": "Layout one"}).json()
        put = c.put(f"/api/route/routes/{r['id']}/layout", json={"pos": {"tell_me": [400, 80]},
                                                                  "notes": [{"id": "n1", "x": 0, "y": 200, "text": "hello"}]})
        assert put.status_code == 200
        again = c.get(f"/api/route/routes/{r['id']}").json()
        assert again["layout"]["pos"]["tell_me"] == [400, 80] and again["layout"]["notes"][0]["text"] == "hello"
        assert c.put(f"/api/route/routes/{r['id']}/layout", json={"pos": {"x y": [1, 1]}}).status_code == 400
        # deleting the route forgets its layout
        assert c.request("DELETE", f"/api/route/routes/{r['id']}", json={"confirm": r["name"]}).status_code == 200
        from app.route import editor as E
        assert E.meta(t, r["id"]) == {"pos": {}, "notes": [], "chat": ""}
    finally:
        _wipe(t)


def test_catalog_finds_tools_by_her_words(bz):
    c, _ = _client()
    cat = c.get("/api/route/catalog").json()
    kinds = {k["type"] for k in cat["kinds"]}
    assert {"approval", "notify", "condition", "router", "filter", "loop", "wait", "set", "code", "http"} <= kinds
    assert cat["tools"] and all(not t["name"].startswith("dhara_") for t in cat["tools"])
    q = c.get("/api/route/catalog?q=sheet append row").json()["tools"]
    assert q and q[0]["name"].startswith("sheet"), [x["name"] for x in q[:5]]
    one = next(x for x in q if x["name"] == "sheet_append")
    assert one["fields"] and all({"name", "type", "help", "required"} <= set(f) for f in one["fields"])
    assert one["app"]["slug"] == "googlesheets"
    t1 = c.get("/api/route/catalog/tool/sheet_append").json()
    assert t1["name"] == "sheet_append"
    assert c.get("/api/route/catalog/tool/no_such_tool_here").status_code == 404
    assert not [x for x in c.get("/api/route/catalog?q=workflow dhara").json()["tools"] if x["name"].startswith("dhara_")]


def test_test_route_runs_even_when_the_route_is_off(bz):
    c, t = _client()
    _wipe(t)
    try:
        r = c.post("/api/route/routes", json={"title": "Test me"}).json()
        assert r["enabled"] is False
        x = c.post(f"/api/route/routes/{r['id']}/test", json={}).json()
        assert x["status"] == "queued" and x["run_id"]
        for _ in range(100):
            run = D.get_run(t, x["run_id"])
            if run and run["status"] not in ("queued", "running"):
                break
            time.sleep(0.05)
        assert run["status"] == "done", run
        assert [l["id"] for l in run["steps_log"]] == ["tell_me"]
    finally:
        _wipe(t)


def test_ask_hoola_chat_is_the_routes_own_and_knows_it(bz):
    c, t = _client()
    _wipe(t)
    try:
        r = c.post("/api/route/routes", json={"title": "Orders to sheet"}).json()
        ch = c.get(f"/api/route/routes/{r['id']}/chat").json()
        assert ch["new"] is True
        assert c.get(f"/api/route/routes/{r['id']}/chat").json() == {"id": ch["id"], "new": False}, "one chat per route"
        from app.route import chat as RC
        assert RC.is_route(ch["id"]) and not RC.is_route("no-such-chat")
        blk = RC.block(t, ch["id"])
        assert "<route_editor>" in blk and 'name exactly "orders_to_sheet"' in blk and "tell_me" in blk
        assert "Do not switch the route on" in blk
        listed = [x["id"] for x in c.get("/api/conversations").json().get("conversations", [])]
        assert ch["id"] not in listed, "the route chat stays out of her chat list"
        msgs = c.get(f"/api/conversations/{ch['id']}/messages").json()["messages"]
        assert msgs and msgs[0]["role"] == "assistant" and "Nothing runs until you switch it on" in msgs[0]["text"]
    finally:
        _wipe(t)


def test_summary_and_cards_carry_the_week(bz):
    c, t = _client()
    _wipe(t)
    try:
        ctx = Ctx(tenant_id=t, conversation_id="")
        _run(D.dhara_save(ctx, name="weekly_one", steps=[{"id": "n", "type": "notify", "text": "hi"}], settings={"folder": "Office"}))
        wf = D.get_workflow(t, name="weekly_one")
        _run(D.execute_run(t, D.create_run(t, wf)))
        s = c.get("/api/route/summary").json()
        assert s["runs_7d"] == 1 and s["failed_7d"] == 0 and s["success_30d"] == 100 and s["folders"] == ["Office"]
        card = c.get("/api/route/routes").json()["routes"][0]
        assert len(card["days7"]) == 7 and card["days7"][-1]["ok"] == 1
    finally:
        _wipe(t)


def test_page_source_rules():
    js = (BASE / "route.js").read_text()
    css = (BASE / "route.css").read_text()
    html = (BASE / "route.html").read_text()
    assert "onerror=" not in js and "onclick=" not in js and "eval(" not in js and "prompt(" not in js and "confirm(" not in js
    for part in ("/graph`", "/layout`", "/test`", "/chat`", "/api/route/catalog", "data-addafter", "Ask Hoola", "Test route",
                 "Tidy up", "Add a note", "Keep changes", "A test runs the real steps", "beforeunload", "renameStep", "refsFor"):
        assert part in js, part
    for part in (".canvas{", ".nd.sel{", ".sticky", ".mini{", ".edside{", "table.rt td[data-l]::before", ".tog::before"):
        assert part in css, part
    assert 'id="needCount"' in html and 'href="#/needs"' in html and 'id="folders"' in html
    for word in ("₹", "IST", "Haan", "udhaar", "GST"):
        assert word not in js and word not in html


# ---------------------------------------------------------------- a real browser
@pytest.fixture
def br(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    ctx = Ctx(tenant_id=t, conversation_id="")
    _run(D.dhara_save(ctx, name="order_to_sheet", settings={"folder": "Shop"},
                      steps=[{"id": "check", "type": "condition", "label": "Is it big?", "filter": {"left": "{{vars.total}}", "op": "gt", "right": 500},
                              "then": [{"id": "tell_big", "type": "notify", "text": "Big order"}], "else": []},
                             {"id": "done_note", "type": "notify", "label": "Tell me", "text": "Order handled"}]))
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    try:
        pw = sync_api.sync_playwright().start()
        try:
            b = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as ex:      # noqa: BLE001
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(ex)[:80]}")
        yield f"http://127.0.0.1:{port}/console/route", b, KEY, t
        b.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def _open(b, key, w, h):
    c = b.new_context(viewport={"width": w, "height": h})
    c.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p = c.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    return p, errs


def _ready(p):
    p.wait_for_function("() => !document.querySelector('#main').innerText.includes('Opening Hoola Route')", timeout=20000)


def test_the_editor_in_a_real_browser(br):
    base, b, key, t = br
    wf = D.get_workflow(t, name="order_to_sheet")
    p, errs = _open(b, key, 1440, 900)
    p.goto(base)
    _ready(p)
    assert "What should run by itself?" in p.inner_text("#main")
    assert p.locator("table.rt .d7 i").count() == 7, "the last 7 days of the route"
    # the editor: the trigger, the steps, the if / else ways
    p.goto(base + "#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='check']")
    txt = p.inner_text("#world")
    assert "By hand" in txt and "Is it big?" in txt and "If yes" in txt and "If no" in txt and "Tell me" in txt
    assert p.locator(".addn").count() >= 2, "an empty way and the end can take a new step"
    # pick a step: its settings open
    p.click(".nd[data-node='done_note']")
    p.wait_for_selector("#edPanel [data-k='text']")
    assert p.input_value("#edPanel [data-k='text']") == "Order handled"
    p.fill("#edPanel [data-k='text']", "Order handled well")
    assert "Not saved" in p.inner_text("#edState")
    # add a step after it from the add panel
    p.hover(".nd[data-node='done_note']")
    p.click(".nd[data-node='done_note'] .addaf")
    p.wait_for_selector("#addList .arow[data-kind='approval']")
    p.click("#addList .arow[data-kind='approval']")
    p.wait_for_selector(".nd[data-node='ask_me_first']")
    p.fill("#edPanel [data-k='question']", "Send it now?")
    # a tool from the search, with its own fields
    p.click(".nd[data-node='ask_me_first'] .addaf", force=True)
    p.fill("#addQ", "sheet append")
    p.wait_for_selector("#addList .arow[data-tool]")
    p.click("#addList .arow[data-tool]")
    p.wait_for_selector("#edPanel .tbox")
    assert p.locator("#edPanel [data-k^='arg:']").count() >= 1
    # undo the tool, then save
    p.keyboard.press("Escape")
    p.click("#edUndo")
    p.wait_for_function("() => !document.querySelector('[data-node^=\"sheet_\"]')")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    got = D.get_workflow(t, wf_id=wf["id"])
    ids = [s["id"] for s in got["steps"]]
    assert ids == ["check", "done_note", "ask_me_first"], ids
    assert got["steps"][1]["text"] == "Order handled well" and got["steps"][2]["question"] == "Send it now?"
    # drag a node: its place is kept
    box = p.locator(".nd[data-node='check']").bounding_box()
    p.mouse.move(box["x"] + 60, box["y"] + 30)
    p.mouse.down()
    p.mouse.move(box["x"] + 60, box["y"] + 230, steps=6)
    p.mouse.up()
    time.sleep(1.2)
    from app.route import editor as E
    assert "check" in E.meta(t, wf["id"])["pos"]
    # a note
    p.click("#tNote")
    p.wait_for_selector(".sticky textarea")
    p.fill(".sticky textarea", "Ask Ravi before changing this")
    time.sleep(1.2)
    assert E.meta(t, wf["id"])["notes"][0]["text"] == "Ask Ravi before changing this"
    # what starts it: a schedule
    p.click(".nd[data-node='trigger']")
    p.click("[data-tk='schedule']")
    p.click("[data-day='mon']")
    p.click("#edSave")
    p.wait_for_function("() => document.querySelector('#edState').innerText === 'Saved'", timeout=10000)
    got = D.get_workflow(t, wf_id=wf["id"])
    assert got["trigger_kind"] == "schedule" and got["trigger_spec"]["days"] == ["mon"]
    # test route: asks once, then runs the real steps and stops at the approval
    p.click("#edTest")
    assert p.is_visible("#testAsk")
    p.click("#testGo")
    p.wait_for_selector("#edLog .lc", timeout=15000)
    p.wait_for_function("() => document.querySelector('#edLog').innerText.includes('Waiting for your OK')", timeout=15000)
    # ask hoola: the route's own chat opens with its greeting
    p.click(".ptab[data-ptab='ask']")
    p.wait_for_selector("#askList .ma")
    assert "Nothing runs until you switch it on" in p.inner_text("#askList")
    # leaving with unsaved changes asks first
    p.click(".nd[data-node='done_note']")
    p.fill("#edPanel [data-k='text']", "x")
    p.evaluate("location.hash = '#/routes'")
    p.wait_for_selector("#lvDrop")
    p.click("#lvDrop")
    p.wait_for_function("() => location.hash === '#/routes'")
    assert not errs, errs


def test_every_page_fits_a_phone(br):
    base, b, key, t = br
    wf = D.get_workflow(t, name="order_to_sheet")
    p, errs = _open(b, key, 390, 860)
    for h in ("", "#/routes", "#/needs", "#/runs", "#/templates", "#/r/" + wf["id"], "#/r/" + wf["id"] + "/settings", "#/r/" + wf["id"] + "/runs"):
        p.goto(base + h)
        _ready(p)
        time.sleep(0.5)
        over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        assert over <= 1, f"{h or 'home'} scrolls sideways by {over}px on a phone"
    p.goto(base + "#/r/" + wf["id"])
    p.wait_for_selector(".nd[data-node='check']")
    assert p.is_visible("#edPanel") and p.is_visible("#canvas")
    assert not errs, errs
