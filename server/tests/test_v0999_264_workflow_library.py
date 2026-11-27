"""v0.999.264 THE WORKFLOW LIBRARY (owner: "https://github.com/Zie619/n8n-workflows.git -- now this is repo having
readymade workflows for n8n ---- make it fully fuctional for hoola route -- make a workflow section in sidebar in route
tool ---- first read then design and deployment").

- the library index ships with the server, built from the repo's last whole commit (f8639776), sha256 per file;
- a file is fetched only when opened, checked against its sha256, kept on the server;
- keys written into a workflow are taken out before anything is shown or saved;
- the importer now does Google Sheets / Gmail / email / Drive / Calendar, dates, hashes, HTML, Markdown, XML, RSS,
  list tools, files, every web request method, Set in JSON mode, chat messages (told to her in Hoola), and an
  expression it cannot read becomes text instead of a broken route;
- the Workflows page in the Route sidebar: search, filters, preview, Bring it in (switched off).
"""
import json
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fresh DB fixture)

from app.agent import dhara_tools as D
from app.route import n8n as N
from app.route import n8nlib as L


def _wipe(t):
    import shutil
    shutil.rmtree(Path("data") / "dhara" / t, ignore_errors=True)


def _wf(nodes, links):
    """A small n8n export: nodes [(name, type, params)], links [(from, to)] or [(from, to, output)]."""
    conns: dict = {}
    for ln in links:
        a, b, oi = (ln + (0,))[:3]
        outs = conns.setdefault(a, {}).setdefault("main", [])
        while len(outs) <= oi:
            outs.append([])
        outs[oi].append({"node": b, "type": "main", "index": 0})
    return {"name": "Test flow", "nodes": [{"name": n, "type": (t if "." in t else "n8n-nodes-base." + t),
                                             "parameters": p, "typeVersion": 2} for n, t, p in nodes],
            "connections": conns}


# ---------------------------------------------------------------- the index
def test_the_index_ships_and_is_pinned():
    ix = L.index()
    items = ix["items"]
    assert len(items) > 1800
    assert ix["source"]["commit"] == L.COMMIT == "f8639776c97c05e9730c2ec5c97163d76f6d2290"
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))
    for x in items[:400]:
        assert len(x["s"]) == 64 and x["p"].endswith(".json") and ".." not in x["p"] and not x["p"].startswith("/")
        assert x["r"] in ("ready", "check", "partial") and x["t"]
    assert sum(1 for x in items if x["r"] == "ready") > 80
    assert sum(1 for x in items if x["r"] in ("ready", "check")) > 300


def test_search_filters_and_pages():
    d = L.search()
    assert d["total"] == d["all"] > 1800 and len(d["items"]) == 24 and d["categories"] and d["apps"]
    g = L.search(q="gmail")
    assert 0 < g["total"] < d["total"] and all("gmail" in json.dumps(x).lower() for x in g["items"])
    r = L.search(ready="ready")
    assert r["total"] == d["ready_counts"]["ready"] and all(x["ready"] == "ready" for x in r["items"])
    cat = d["categories"][0][0]
    c = L.search(category=cat, per=500)
    assert c["total"] == d["categories"][0][1] and all(x["category"] == cat for x in c["items"][:60])
    p2 = L.search(page=2)
    assert p2["items"][0]["id"] != d["items"][0]["id"]
    s = L.search(trigger="schedule")
    assert all(x["trigger"] == "schedule" for x in s["items"])
    assert L.search(q="zzzz nothing matches this qqqq")["total"] == 0


# ---------------------------------------------------------------- fetching: sha256 checked, cached
def test_fetch_is_checked_and_kept(monkeypatch, tmp_path):
    import hashlib
    body = json.dumps(_wf([("Start", "manualTrigger", {})], [])).encode()
    good = {"id": "x1", "p": "Test/x1.json", "s": hashlib.sha256(body).hexdigest(), "n": "x", "r": "ready", "t": "manual"}
    monkeypatch.setattr(L, "_INDEX", {"source": L.SOURCE, "items": [good], "by_id": {"x1": good}})
    monkeypatch.chdir(tmp_path)
    got = []
    monkeypatch.setattr(L, "_download", lambda url: got.append(url) or body)
    assert L.raw_of("x1") == body and L.raw_of("x1") == body
    assert len(got) == 1, "the second open comes from the server's copy"
    assert L.COMMIT in got[0] and got[0].endswith("/workflows/Test/x1.json")
    monkeypatch.setattr(L, "_INDEX", {"source": L.SOURCE, "items": [], "by_id": {"x2": {**good, "id": "x2", "s": "0" * 64}}})
    with pytest.raises(L.LibError, match="not the one Hoola checked"):
        L.raw_of("x2")
    with pytest.raises(L.LibError, match="not in the library"):
        L.raw_of("../../etc/passwd")


# ---------------------------------------------------------------- keys taken out
def test_keys_written_in_are_taken_out():
    doc = _wf([("Start", "manualTrigger", {}),
               ("Call", "httpRequest", {"url": "https://api.example.com/v1?key=sk-abcdefghijklmnopqrstuvwxyz123456",
                                        "method": "POST", "headerParameters": {"parameters": [
                                            {"name": "Authorization", "value": "Bearer abcdefghijklmnopqrstuvwxyz0123"},
                                            {"name": "Accept", "value": "application/json"}]},
                                        "apiKey": "live_9f8e7d6c5b4a"}),
               ("Note", "set", {"assignments": {"assignments": [{"name": "who", "value": "<your-api-key>"}]}})],
              [("Start", "Call"), ("Call", "Note")])
    doc["nodes"][1]["credentials"] = {"httpHeaderAuth": {"id": "7", "name": "mine"}}
    doc["pinData"] = {"Call": [{"json": {"secret": "x"}}]}
    clean, found = L.scrub(doc)
    text = json.dumps(clean)
    for secret in ("sk-abcdefghijklmnop", "abcdefghijklmnopqrstuvwxyz0123", "live_9f8e7d6c5b4a", "credentials", "pinData"):
        assert secret not in text, secret
    assert "application/json" in text and "<your-api-key>" in text, "ordinary values and placeholders stay"
    assert len(found) == 3 and all(f["variable"].startswith("N8N_") for f in found)
    plan = N.convert(clean)
    D.validate_steps(plan["steps"])
    call = plan["steps"][0]
    assert call["type"] == "http" and "{{env.N8N_" in call["url"] and call["headers"]["Authorization"].startswith("{{env.N8N_")


# ---------------------------------------------------------------- the importer does more nodes now
def test_more_nodes_become_real_steps():
    doc = _wf([
        ("Every day", "scheduleTrigger", {"rule": {"interval": [{"field": "days", "triggerAtHour": 9}]}}),
        ("Fields", "set", {"mode": "raw", "jsonOutput": '={\n "who": "{{ $json.name }}",\n "n": {{ $json.count }},\n "fixed": 3\n}'}),
        ("Today", "dateTime", {"operation": "formatDate", "date": "={{ $now }}", "format": "custom",
                               "customFormat": "dd-MM-yyyy", "outputFieldName": "day"}),
        ("Page", "httpRequest", {"url": "https://example.com", "method": "PUT"}),
        ("Pick", "html", {"operation": "extractHtmlContent", "extractionValues": {"values": [
            {"key": "title", "cssSelector": "h1"}, {"key": "links", "cssSelector": "a", "returnValue": "attribute",
                                                     "attribute": "href", "returnArray": True}]}}),
        ("Sheet", "googleSheets", {"operation": "append", "documentId": {"__rl": True, "value": "SHEET1", "mode": "id"},
                                   "sheetName": {"__rl": True, "value": "gid=0", "cachedResultName": "Leads"},
                                   "columns": {"value": {"Day": "={{ $('Today').item.json.day }}", "Title": "={{ $json.title }}"}}}),
        ("Mail", "gmail", {"sendTo": "boss@example.com", "subject": "Report {{ $('Today').item.json.day }}", "message": "={{ $json.title }}"}),
        ("Hash", "crypto", {"type": "SHA256", "value": "={{ $json.who }}", "dataPropertyName": "h"}),
        ("Tell", "telegram", {"chatId": "123", "text": "=Done: {{ $json.h }}"}),
        ("Sorted", "itemLists", {"operation": "sort", "sortFieldsUi": {"sortField": [{"fieldName": "Day"}]}}),
        ("Feed", "rssFeedRead", {"url": "https://example.com/feed.xml"}),
    ], [("Every day", "Fields"), ("Fields", "Today"), ("Today", "Page"), ("Page", "Pick"), ("Pick", "Sheet"),
        ("Sheet", "Mail"), ("Mail", "Hash"), ("Hash", "Tell"), ("Tell", "Sorted"), ("Sorted", "Feed")])
    plan = N.convert(doc)
    steps = D.validate_steps(plan["steps"])
    by = {s["label"]: s for s in steps}
    assert not plan["report"]["placeholders"], plan["report"]["placeholders"]
    assert by["Fields"]["op"] == "fields" and by["Fields"]["values"]["fixed"] == 3
    assert by["Fields"]["values"]["who"] == "{{vars.name}}" and by["Fields"]["values"]["n"] == "{{vars.count}}"
    assert by["Today"]["op"] == "date" and by["Today"]["format"] == "%d-%m-%Y" and by["Today"]["value"] == "{{now()}}"
    assert by["Page"]["method"] == "PUT"
    picks = [s for s in steps if s.get("action") == "html_select"]
    assert [p["selector"] for p in picks] == ["h1", "a"] and picks[1]["attr"] == "href"
    sheet = by["Sheet"]
    assert sheet["type"] == "tool" and sheet["name"] == "sheet_append" and sheet["args"]["tab"] == "Leads"
    row = sheet["args"]["rows"][0]
    assert row["Day"] == "{{steps.today.output}}", "a field an earlier node added reads that node's step"
    assert row["Title"].startswith("{{steps.pick_title.output[0]")
    mail = by["Mail"]
    assert mail["name"] == "email_draft" and mail["args"]["to"] == "boss@example.com" and "{{steps.today.output}}" in mail["args"]["subject"]
    assert by["Hash"]["action"] == "sha256"
    assert by["Tell"]["type"] == "notify" and "steps.hash.output" in by["Tell"]["text"]
    assert by["Sorted"]["op"] == "sort" and by["Sorted"]["by"] == "Day"
    assert [s["type"] for s in steps[-2:]] == ["http", "data"] and steps[-1]["action"] == "xml_to_data"
    whys = " ".join(c["why"] for c in plan["report"]["check"])
    assert "draft that waits for your OK" in whys and "Hoola tells you in your Hoola chat" in whys


def test_a_bot_reply_is_not_turned_into_a_message_to_her():
    doc = _wf([("Bot", "n8n-nodes-base.telegramTrigger", {"updates": ["message"]}),
               ("Answer", "telegram", {"chatId": "={{ $json.message.chat.id }}", "text": "Hi"})], [("Bot", "Answer")])
    plan = N.convert(doc)
    assert plan["report"]["placeholders"] and plan["steps"][0]["type"] == "stop"


def test_an_expression_hoola_cannot_read_is_text_not_a_broken_route():
    doc = _wf([("Start", "manualTrigger", {}),
               ("Ask", "@n8n/n8n-nodes-langchain.agent", {"text": "Today is {{ DateTime.local().toFormat('cccc') }}",
                                                          "options": {"systemMessage": "=You help. {{ $json.name }}"}}),
               ("Long", "respondToWebhook", {"respondWith": "text", "responseBody": "x" * 5000})],
              [("Start", "Ask"), ("Ask", "Long")])
    plan = N.convert(doc)
    steps = D.validate_steps(plan["steps"])
    assert "[n8n:" in steps[0]["prompt"] and "{{vars.name}}" in steps[0]["prompt"]
    assert len(steps[1]["body"]) <= 2000
    assert any("could not be brought in" in c["why"] for c in plan["report"]["check"])


def test_most_of_the_library_comes_in():
    ix = L.index()
    from collections import Counter
    r = Counter(x["r"] for x in ix["items"])
    assert r["ready"] + r["check"] >= 350 and ix["left_out"] < 150
    share = sorted(x["sh"] for x in ix["items"])[len(ix["items"]) // 2]
    assert share >= 0.65, "the median workflow has most of its steps brought in"


# ---------------------------------------------------------------- the routes
def _fake_lib(monkeypatch):
    import hashlib
    doc = _wf([("Start", "manualTrigger", {}),
               ("Get", "httpRequest", {"url": "https://api.example.com/items", "headerParameters": {"parameters": [
                   {"name": "X-API-Key", "value": "abcd1234efgh5678"}]}}),
               ("Mail", "emailSend", {"toEmail": "a@example.com", "subject": "Items", "text": "={{ $json.count }}"})],
              [("Start", "Get"), ("Get", "Mail")])
    body = json.dumps(doc).encode()
    row = {"id": "0001_Test_Flow", "p": "Test/0001_Test_Flow.json", "s": hashlib.sha256(body).hexdigest(), "n": "Test flow",
           "c": "Business Process Automation", "a": ["Email"], "t": "manual", "k": 3, "r": "check", "cv": 2, "ph": 0,
           "sh": 1.0, "d": "Gets items and mails a quokka count."}
    ix = {"source": L.SOURCE, "items": [row], "left_out": 0, "by_id": {row["id"]: row}}
    monkeypatch.setattr(L, "_INDEX", ix)
    monkeypatch.setattr(L, "_download", lambda url: body)
    return row


def test_library_routes(bz, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    from app.config import get_settings
    t = get_settings().tenant_id
    _wipe(t)
    row = _fake_lib(monkeypatch)
    try:
        c = TestClient(main.app)
        h = {"Authorization": f"Bearer {get_settings().api_key}"} if get_settings().api_key else {}
        d = c.get("/api/route/library?q=quokka", headers=h).json()
        assert d["total"] == 1 and d["items"][0]["id"] == row["id"] and d["source"]["licence"] == "MIT"
        p = c.get(f"/api/route/library/{row['id']}", headers=h).json()
        assert p["library"]["taken_out"][0]["field"] == "X-API-Key" and "abcd1234efgh5678" not in json.dumps(p)
        assert any("From the n8n workflow library" in n for n in p["report"]["notes"])
        assert c.get("/api/route/library/nope", headers=h).status_code == 404
        o = c.post(f"/api/route/library/{row['id']}/use", json={"new_name": "lib_test"}, headers=h).json()
        wf = D.get_workflow(t, name="lib_test")
        assert wf and not wf["enabled"] and o["workflow_id"] == wf["id"]
        assert "abcd1234efgh5678" not in json.dumps(wf)
        assert c.post(f"/api/route/library/{row['id']}/use", json={"new_name": "lib_test"}, headers=h).status_code == 409
    finally:
        _wipe(t)


# ---------------------------------------------------------------- the page, in a real browser
def test_the_workflows_page_by_clicking(bz, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    t = get_settings().tenant_id
    _wipe(t)
    real = L.index()
    row = _fake_lib(monkeypatch)
    # the real index for the list (so the page shows the real library), the fake file for the one opened
    items = real["items"] + [row]
    monkeypatch.setattr(L, "_INDEX", {"source": L.SOURCE, "items": items, "left_out": real.get("left_out", 0),
                                      "by_id": {**real["by_id"], row["id"]: row}})
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
        try:
            for w, h in ((1440, 1000), (390, 844)):
                c = b.new_context(viewport={"width": w, "height": h})
                c.add_init_script(f"localStorage.setItem('hoola.console.token', '{KEY}')")
                p = c.new_page()
                errs = []
                p.on("pageerror", lambda e: errs.append(str(e)))
                p.goto(f"http://127.0.0.1:{port}/console/route#/workflows")
                p.wait_for_selector("#libG .wlc")
                assert p.locator('.side [data-nav="workflows"]').get_attribute("aria-current") == "page"
                assert p.locator("#libG .wlc").count() == 24
                assert "MIT licence" in p.inner_text(".libsrc")
                if os.environ.get("HOOLA_SHOTS"):
                    p.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], f"lib_list_{w}.png"), full_page=w < 600)
                assert p.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "no sideways scroll"
                # filters
                p.click('#libRdy [data-r="ready"]')
                p.wait_for_function("() => document.querySelector('#libRdy [data-r=\"ready\"]').getAttribute('aria-pressed') === 'true'")
                assert all(x == "Runs as it is" for x in p.locator("#libG .wlc .lmeta .lr").all_inner_texts())
                p.click('#libRdy [data-r=""]')
                p.wait_for_function("() => document.querySelector('#libRdy [data-r=\"\"]').getAttribute('aria-pressed') === 'true'")
                if w == 1440:
                    p.click("[data-pg='2']")
                    p.wait_for_function("() => document.querySelector('#libN').textContent.startsWith('25-')")
                    p.click("[data-pg='1']")
                    p.wait_for_function("() => document.querySelector('#libN').textContent.startsWith('1-')")
                p.select_option("#libCat", index=1)
                p.wait_for_function("() => !document.querySelector('#libN').textContent.endsWith('of 1,905')")
                assert len(set(p.locator("#libG .wlc .tf .mut").all_inner_texts())) == 1, "one category"
                p.select_option("#libCat", index=0)
                p.wait_for_function("() => document.querySelector('#libN').textContent.endsWith('of 1,905')")
                # search, open, bring in
                p.fill("#libQ", "quokka")
                p.press("#libQ", "Enter")
                p.wait_for_function("() => document.querySelectorAll('#libG .wlc').length === 1")
                p.click("#libG .wlc a.btn")
                p.wait_for_selector("#libUse")
                body = p.inner_text("#main")
                assert "Keys taken out" in body and "N8N_GET_X_API_KEY" in body and "abcd1234efgh5678" not in body
                assert "The steps" in body and "Web request" in body and "Email (draft for your OK)" in body
                if os.environ.get("HOOLA_SHOTS"):
                    p.screenshot(path=os.path.join(os.environ["HOOLA_SHOTS"], f"lib_one_{w}.png"), full_page=True)
                name = "lib_page_" + str(w)
                p.fill('[data-k="libname"]', name)
                p.click("#libUse button[type=submit]")
                p.wait_for_function("() => location.hash.startsWith('#/r/')")
                wf = D.get_workflow(t, name=name)
                assert wf and not wf["enabled"]
                p.goto(f"http://127.0.0.1:{port}/console/route#/workflows")
                p.wait_for_selector("#libG .wlc")
                assert not errs, errs
                c.close()
        finally:
            b.close()
            pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)
        _wipe(t)


def test_version():
    from app.main import APP_VERSION
    assert tuple(int(x) for x in APP_VERSION.split(".")) >= (0, 999, 269)
