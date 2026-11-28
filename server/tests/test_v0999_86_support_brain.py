"""SUPPORT BRAIN (G1 of docs/SUPPORT_GLOBAL_PLAN.md): one business brain for Customer Support and the Telecaller -
each reads the other's approved knowledge; every answer keeps its versions (put back by her tap); an owner and a review
date per answer; an answer read from a web page goes stale when the page changes and is not used until she checks it;
help-center import (public Zendesk, or a JSON / CSV export) as drafts; suggestions from solved tickets; a live lookup
asked only with the asking customer's own number. Walked in a real browser."""
from __future__ import annotations

import ipaddress
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    from app.callcentre import knowledge as K
    monkeypatch.setattr(K, "_RESOLVE", lambda host: [ipaddress.ip_address("93.184.216.34")])
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    yield S
    K.set_transport(None)


def _cc_fact(text: str) -> str:
    from app.callcentre import knowledge as K
    v = K.add_source(T, "text", name="Price list", text=text)
    K.approve(T, v["id"], K.preview(T, v["id"])["pending_hash"])
    return v["id"]


def test_one_brain_both_ways(sv):
    from app.callcentre import knowledge as K
    S = sv
    # a Telecaller fact answers a WhatsApp customer when Support has no answer of its own
    assert S.answer(T, "how much is the split AC 1.5 ton", "whatsapp", "wa:919800000001")["status"] == "unknown"
    _cc_fact("Split AC 1.5 ton\nThe 1.5 ton split AC costs Rs 34,990 with free installation in Pune.")
    out = S.answer(T, "how much is the split AC 1.5 ton", "whatsapp", "wa:919800000001")
    assert out["status"] == "answered" and "34,990" in out["reply"] and "Telecaller" in out["source"]
    # a draft (unapproved) Telecaller source never answers
    K.add_source(T, "text", name="Draft", text="Window AC\nThe window AC costs Rs 21,000 this week only.")
    assert S.answer(T, "price of the window AC", "whatsapp", "wa:919800000001")["status"] == "unknown"
    # a Support answer reaches the Telecaller's line search
    S.kb_add(T, "Do you service on Sundays?", "Yes, from 10 am to 2 pm on Sundays.")
    hits = K.search(T, "do you service on sundays")
    assert hits and hits[0]["from"] == "Customer Support" and "10 am" in hits[0]["text"]
    assert all(h.get("from") != "Customer Support" for h in K.search(T, "sundays service", with_support=False))


def test_versions_and_put_back(sv):
    from app.seva import brain as B
    S = sv
    e = S.kb_add(T, "What are your timings?", "10 am to 7 pm.")
    S.kb_edit(T, e["id"], answer="9 am to 8 pm, Monday to Saturday.")
    S.kb_add(T, "What are your timings?", "9 am to 9 pm every day.")     # same question again = an update
    h = B.history(T, e["id"])
    assert [v["version"] for v in h["versions"]] == [3, 2, 1] and h["versions"][-1]["why"] == "added"
    out = B.restore(T, e["id"], 1)
    assert out["answer"] == "10 am to 7 pm." and out["version"] == 4
    assert B.history(T, e["id"])["versions"][0]["why"] == "restored"
    d = S.kb_import(T, text="Q: Is there a deposit?\nA: Rs 1,000 for the router.")["drafts"][0]
    S.kb_approve(T, [d["id"]])
    assert [v["why"] for v in B.history(T, d["id"])["versions"]] == ["approved", "added"]
    with pytest.raises(B.BrainError):
        B.restore(T, e["id"], 99)


def test_review_date_and_owner(sv):
    from app.seva import brain as B
    S = sv
    e = S.kb_add(T, "Do you deliver to Thane?", "Yes, free above Rs 500.")
    assert S.answer(T, "do you deliver to thane", "test")["status"] == "answered"
    B.meta(T, e["id"], owner="Meena", review_by="2020-01-01")
    v = S.kb_list(T, "live")[0]
    assert v["owner"] == "Meena" and v["review_by"] == "2020-01-01"
    assert S.answer(T, "do you deliver to thane", "test")["status"] == "unknown"        # past its date: not used
    assert [x["id"] for x in B.overview(T)["review_due"]] == [e["id"]]
    B.meta(T, e["id"], checked=True)
    assert S.answer(T, "do you deliver to thane", "test")["status"] == "answered"
    with pytest.raises(B.BrainError):
        B.meta(T, e["id"], review_by="next week")


def test_changed_page_marks_answers_stale(sv, monkeypatch):
    from app.seva import brain as B
    S = sv
    page = {"text": "Q: What is the delivery charge?\nA: Delivery costs Rs 40 inside the city."}
    monkeypatch.setattr(S, "_source_text", lambda t, file_id="", data=None, name="", url="", text="": (
        text or page["text"], "your words" if text else f"website: {url[:200]}"))
    d = S.kb_import(T, url="https://shop.example/faq")["drafts"]
    S.kb_approve(T, [x["id"] for x in d])
    assert S.answer(T, "what is the delivery charge", "test")["status"] == "answered"
    assert B.check_pages(T, fetch=lambda u: page["text"]) == 0            # checked recently: not again
    from app.db import session
    with session() as s:
        for w in s.query(B.SevaPageWatch).all():
            w.checked_at = None
    page["text"] = "Q: What is the delivery charge?\nA: Delivery costs Rs 60 inside the city."
    assert B.check_pages(T, fetch=lambda u: page["text"]) == 1
    assert S.answer(T, "what is the delivery charge", "test")["status"] == "unknown"
    o = B.overview(T)
    assert len(o["stale"]) == 1 and o["pages"][0]["changed"]
    B.meta(T, o["stale"][0]["id"], checked=True)
    assert S.answer(T, "what is the delivery charge", "test")["status"] == "answered"


def test_help_center_import(sv):
    from app.callcentre import knowledge as K
    from app.seva import brain as B
    S = sv
    seen = []

    def zd(req):
        seen.append(str(req.url))
        if "page=2" in str(req.url):
            return httpx.Response(200, json={"articles": [{"title": "Returns", "body": "<p>Return within <b>30</b> days.</p>"}],
                                             "next_page": None})
        return httpx.Response(200, json={"articles": [{"title": "Shipping times", "body": "<p>2 to 5 days in India.</p>"},
                                                      {"title": "Secret draft", "body": "x", "draft": True}],
                                         "next_page": "https://help.shop.example/api/v2/help_center/articles.json?page=2"})
    K.set_transport(httpx.MockTransport(zd))
    out = B.import_helpcenter(T, "https://help.shop.example/hc/en-us")
    assert out["count"] == 2 and out["source"] == "help center: help.shop.example"
    assert seen[0].startswith("https://help.shop.example/api/v2/help_center/articles.json")
    drafts = {e["question"]: e for e in S.kb_list(T, "draft")}
    assert drafts["Returns"]["answer"] == "Return within 30 days." and drafts["Returns"]["kind"] == "policy"
    assert S.answer(T, "how long does shipping take", "test")["status"] == "unknown"     # drafts wait for her
    js = json.dumps([{"title": "Warranty", "description": "<div>One year on every phone.</div>"}]).encode()
    assert B.import_helpcenter(T, data=js, name="freshdesk.json")["count"] == 1
    csvb = b"Title,Body\nOpening hours,9 am to 6 pm\n"
    assert B.import_helpcenter(T, data=csvb, name="intercom.csv")["count"] == 1
    with pytest.raises(B.BrainError):
        B.import_helpcenter(T, data=b"x", name="notes.txt")


def test_suggestions_from_solved_tickets(sv):
    from app.seva import brain as B
    S = sv
    for i, who in enumerate(("Ana", "Ben", "Chi")):
        t = S.new_ticket(T, "router red light is blinking after rain", "whatsapp", name=who, phone=f"98000000{i}1")
        S.reply(T, t["number"], "Please switch the router off for 30 seconds and on again; if the light stays red we send an engineer.",
                by="staff:meena")
        S.update(T, t["number"], status="resolved", by="staff:meena")
    one = S.new_ticket(T, "bill shows double charge", "whatsapp", name="Dev", phone="9800000099")
    S.update(T, one["number"], status="resolved")
    sg = B.suggestions(T)
    assert len(sg) == 1 and sg[0]["count"] == 3 and "30 seconds" in sg[0]["answer"]
    e = B.suggestion_decide(T, sg[0]["id"], True, answer="Switch the router off for 30 seconds, then on again.")
    assert e["source"] == "solved tickets (3)" and e["status"] == "live"
    assert B.suggestions(T) == []                                         # now in the knowledge: not suggested again
    assert S.answer(T, "router red light is blinking after rain", "test")["status"] == "answered"


def test_live_lookup_only_with_the_customers_own_number(sv):
    from app.callcentre import knowledge as K
    S = sv
    seen = []

    def api(req):
        seen.append(str(req.url))
        return httpx.Response(200, json={"data": [{"order": "A-77", "status": "Out for delivery", "card": "4111 1111 1111 1111"}]})
    K.set_transport(httpx.MockTransport(api))
    lv = K.add_source(T, "api", name="Orders", mode="live", url="https://api.shop.example/orders?phone={phone}", path="data",
                      fields=["order", "status"], lookup="order status where is my order")
    assert S.answer(T, "where is my order", "whatsapp", "wa:919811112222")["status"] == "unknown"     # not approved yet
    K.approve(T, lv["id"], K.preview(T, lv["id"])["pending_hash"])
    out = S.answer(T, "where is my order", "whatsapp", "wa:919811112222")
    assert out["status"] == "looked_up" and out["rows"] == [{"order": "A-77", "status": "Out for delivery"}]
    assert "phone=919811112222" in seen[-1] and "own number" in out["source"]
    n = len(seen)
    assert S.answer(T, "where is my order", "test")["status"] == "unknown" and len(seen) == n   # no customer = no lookup


def test_routes_tool_and_page(sv):
    from pathlib import Path
    from app.main import app
    from app.agent import seva_tools as ST
    S = sv
    c = TestClient(app)
    e = S.kb_add(T, "Parking?", "Free parking behind the shop.")
    assert c.get("/api/seva/brain").status_code == 200
    assert c.get(f"/api/seva/kb/{e['id']}/history").json()["versions"][0]["version"] == 1
    assert c.post(f"/api/seva/kb/{e['id']}/meta", json={"owner": "Ravi"}).json()["owner"] == "Ravi"
    assert c.post(f"/api/seva/kb/{e['id']}/restore", json={"version": 9}).status_code == 400
    r = c.post("/api/seva/kb/helpcenter", files={"file": ("x.csv", b"title,body\nA,B b b\n", "text/csv")})
    assert r.status_code == 200 and r.json()["count"] == 1
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    acts = names["seva"]["input_schema"]["properties"]["action"]["enum"]
    for a in ("kb_history", "kb_restore", "kb_meta", "kb_helpcenter", "suggestion_ok", "suggestion_no"):
        assert a in acts
    assert "brain" in names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"]
    js = (Path(__file__).resolve().parents[1] / "app/static/console/supportdesk.js").read_text()
    for w in ("/api/seva/brain", "Suggested from solved tickets", "Shared with the Telecaller", "Import a help center",
              "data-kbhist", "data-kbrestore", "Needs a look"):
        assert w in js, w


@pytest.fixture
def br_server(sv, monkeypatch):
    import os
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    S = sv
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    e = S.kb_add(T, "What are your timings?", "10 am to 7 pm.")
    S.kb_edit(T, e["id"], answer="9 am to 8 pm.")
    for i, who in enumerate(("Ana", "Ben")):
        t = S.new_ticket(T, "router red light is blinking", "whatsapp", name=who, phone=f"98000000{i}1")
        S.reply(T, t["number"], "Please restart the router for 30 seconds.", by="staff:meena")
        S.update(T, t["number"], status="resolved", by="staff:meena")
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
        yield f"http://127.0.0.1:{port}", browser, KEY, e["id"]
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_knowledge_brain_in_a_real_browser(br_server):
    base, browser, key, eid = br_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(base + "/console/support#/knowledge")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Suggested from solved tickets')", timeout=20000)
    txt = pg.inner_text("#spPage")
    assert "Shared with the Telecaller" in txt and "Import a help center" in txt and "version 2" in txt
    pg.click(f"[data-kbhist='{eid}']")
    pg.wait_for_selector(f"[data-kbrestore='{eid}'][data-v='1']")
    pg.click(f"[data-kbrestore='{eid}'][data-v='1']")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('version 3')", timeout=10000)
    pg.click("form.spSugg button[type=submit]")
    pg.wait_for_function("() => !document.querySelector('form.spSugg')", timeout=10000)
    assert "solved tickets (2)" in pg.inner_text("#spPage")
    ctx.close()
    pg2 = browser.new_context(viewport={"width": 390, "height": 900})
    pg2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    p2 = pg2.new_page()
    p2.on("pageerror", lambda e: errors.append(str(e)))
    p2.goto(base + "/console/support#/knowledge")
    p2.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Shared with the Telecaller')", timeout=20000)
    assert p2.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    pg2.close()
    assert not errors, errors
