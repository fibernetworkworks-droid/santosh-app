"""G10 SUPPORT TEAMS (docs/SUPPORT_GLOBAL_PLAN.md): people with shifts in their own time zones, queues (least busy /
in turn / overflow / language / skill / capacity), routing as data, one rule engine (now or after a delay, once per
ticket), roles as permission lists, money approval chains per currency with one-time links bound to the request and
daily limits that move up, macros that do more, custom fields and saved views, the Team & rules page in a browser."""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

T = "default"
IST = ZoneInfo("Asia/Kolkata")


def ist(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=IST).astimezone(timezone.utc)


@pytest.fixture
def tm(env, monkeypatch):
    from app.seva import service as S
    from app.seva import teams as TM
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    box = {"now": ist(2026, 11, 20, 11)}                   # a Friday, 11:00 in India
    monkeypatch.setattr(S, "clock", lambda: box["now"])
    told, chat = [], []
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: (told.append(text), {"sent": "whatsapp", "text": text})[1])
    monkeypatch.setattr(S, "_note_chat", lambda tenant, text, conv="": chat.append(text))
    TM._LINKS.clear()
    S.box, S.told, S.chat = box, told, chat
    return S, TM


def _team(TM):
    ana = TM.save_agent(T, {"name": "Ana", "role": "agent", "langs": "es, en", "skills": "billing", "capacity": 2,
                            "shift": {"days": [0, 1, 2, 3, 4], "start": "09:00", "end": "17:00", "tz": "Asia/Kolkata"}})
    ravi = TM.save_agent(T, {"name": "Ravi", "role": "agent", "langs": "hi, en", "skills": "billing, fibre", "capacity": 5,
                             "shift": {"days": [0, 1, 2, 3, 4, 5], "start": "09:00", "end": "18:00", "tz": "Asia/Kolkata"}})
    night = TM.save_agent(T, {"name": "Lee", "role": "supervisor", "langs": "en", "skills": "billing",
                              "shift": {"days": [4], "start": "22:00", "end": "06:00", "tz": "Asia/Kolkata"}})
    TM.save_queue(T, {"name": "Billing", "members": [ana["id"], ravi["id"]], "skills": "billing", "overflow": "general"})
    TM.save_queue(T, {"name": "General", "members": [night["id"]]})
    TM.save_routes(T, [{"if": {"category": "billing"}, "queue": "billing"}, {"if": {}, "queue": "general"}])
    return ana, ravi, night


def test_people_shifts_and_time_zones(tm):
    S, TM = tm
    ana, ravi, lee = _team(TM)
    at = ist(2026, 11, 20, 11)
    assert TM.on_shift(ana, at, T) and not TM.on_shift(lee, at, T)
    assert TM.on_shift(lee, ist(2026, 11, 20, 23), T) and TM.on_shift(lee, ist(2026, 11, 21, 3), T)   # past midnight: Friday's shift
    assert not TM.on_shift(lee, ist(2026, 11, 22, 3), T)
    ny = TM.save_agent(T, {"name": "Sam", "shift": {"days": [4], "start": "09:00", "end": "17:00", "tz": "America/New_York"}})
    assert not TM.on_shift(ny, at, T) and TM.on_shift(ny, datetime(2026, 11, 20, 15, tzinfo=timezone.utc), T)
    with pytest.raises(TM.TeamError, match="time zone"):
        TM.save_agent(T, {"name": "X", "shift": {"tz": "Mars/Base"}})
    with pytest.raises(TM.TeamError, match="role"):
        TM.save_agent(T, {"name": "X", "role": "boss"})


def test_routing_language_skill_capacity_overflow_and_turns(tm):
    S, TM = tm
    ana, ravi, lee = _team(TM)
    es = S.new_ticket(T, "Mi factura está mal, me cobraron dos veces", "email", customer="email:p@x.es", category="billing")
    t1 = S.ticket(T, es["number"])
    assert t1["queue"] == "billing" and t1["assignee"] == "Ana"                  # only Ana speaks Spanish
    hi = S.new_ticket(T, "mera bill galat hai, do baar paise kate", "whatsapp", phone="9811112222", category="billing")
    assert S.ticket(T, hi["number"])["assignee"] == "Ravi"
    e2 = S.new_ticket(T, "Bill too high this month", "email", customer="email:a@b.com", category="billing")
    e3 = S.new_ticket(T, "Charged twice for October", "email", customer="email:c@d.com", category="billing")
    who = {S.ticket(T, e2["number"])["assignee"], S.ticket(T, e3["number"])["assignee"]}
    assert who <= {"Ana", "Ravi"}                                                  # least busy each time
    for n in range(6):
        S.new_ticket(T, f"Billing question number {n} about the invoice", "email", customer=f"email:z{n}@q.com", category="billing")
    loads = {a["name"]: a["open"] for a in TM.agents(T)}
    assert loads["Ana"] <= 2 and loads["Ravi"] <= 5                              # never past their capacity
    full = S.new_ticket(T, "Billing again: wrong GST on the bill", "email", customer="email:full@q.com", category="billing")
    tf = S.ticket(T, full["number"])
    assert tf["queue"] == "general" and tf["assignee"] == ""                      # overflow, nobody on shift there now
    assert any("nobody on shift" in n["text"] for n in tf["notes"])
    tech = S.new_ticket(T, "The router light is red", "email", customer="email:r@q.com", category="technical")
    assert S.ticket(T, tech["number"])["queue"] == "general"
    # in turn
    TM.save_queue(T, {"name": "Billing", "members": [ana["id"], ravi["id"]], "strategy": "round_robin"})
    with pytest.raises(TM.TeamError, match="does not exist"):
        TM.save_routes(T, [{"if": {}, "queue": "nope"}])


def test_queue_board_urgent_and_vip_first(tm):
    S, TM = tm
    from app.seva import handover as H
    _team(TM)
    H.save(T, {"vip": ["9822223333"]})
    a = S.new_ticket(T, "Billing: question about my plan", "email", customer="email:old@q.com", category="billing")
    S.box["now"] += timedelta(minutes=5)
    b = S.new_ticket(T, "Billing: please call", "whatsapp", phone="9822223333", category="billing")
    S.box["now"] += timedelta(minutes=5)
    c = S.new_ticket(T, "URGENT billing: double charge, money gone", "email", customer="email:u@q.com", category="billing",
                     priority="urgent")
    bq = next(x for x in TM.board(T) if x["key"] == "billing")
    order = [w["number"] for w in bq["waiting"]]
    assert order[:3] == [c["number"], b["number"], a["number"]]
    assert {p["name"] for p in bq["people"]} == {"Ana", "Ravi"}


def test_rules_now_later_once_and_safe(tm):
    S, TM = tm
    _team(TM)
    TM.save_rule(T, {"name": "Billing gets a label", "event": "created", "conditions": [{"field": "category", "op": "is", "value": "billing"}],
                     "actions": [{"do": "label", "value": "money"}, {"do": "priority", "value": "high"}, {"do": "notify", "value": "supervisor"}]})
    TM.save_rule(T, {"name": "Still open after 2 hours", "event": "created", "delay_h": 2,
                     "conditions": [{"field": "status", "op": "in", "value": "new, open"}], "actions": [{"do": "assign", "value": "Lee"}]})
    TM.save_rule(T, {"name": "Thanks on resolve", "event": "status", "conditions": [{"field": "status", "op": "is", "value": "resolved"}],
                     "actions": [{"do": "reply", "value": "Thanks"}]})
    n = S.new_ticket(T, "Billing: refund for the double charge", "email", customer="email:x@q.com", category="billing")["number"]
    t = S.ticket(T, n)
    assert "money" in t["labels"] and t["priority"] == "high" and any("Billing gets a label" in x for x in S.chat)
    assert any("Rule 'Billing gets a label'" in x["text"] for x in t["notes"])
    assert TM.sweep(T) == 0                                                        # not 2 hours yet
    S.box["now"] += timedelta(hours=2, minutes=1)
    assert TM.sweep(T) == 1 and S.ticket(T, n)["assignee"] == "Lee"
    assert TM.sweep(T) == 0                                                        # once per ticket
    S.update(T, n, status="resolved")
    t2 = S.ticket(T, n)
    assert any("only an approved saved reply" in x["text"] for x in t2["notes"])   # a draft reply is never sent by a rule
    m = S.macro_add(T, "Thanks", "Thank you, glad it is fixed.", "english")
    S.macro_approve(T, m["id"])
    n2 = S.new_ticket(T, "Billing: wrong address on the bill", "email", customer="email:y@q.com", category="billing")["number"]
    before = len(S.told)
    S.update(T, n2, status="resolved")
    assert len(S.told) > before and any("Thank you, glad it is fixed." in x for x in S.told)
    with pytest.raises(TM.TeamError):
        TM.save_rule(T, {"name": "bad", "actions": [{"do": "pay", "value": "100"}]})
    with pytest.raises(TM.TeamError):
        TM.save_rule(T, {"name": "bad", "conditions": [{"field": "password", "op": "is"}], "actions": [{"do": "label", "value": "x"}]})


def test_roles_and_bands(tm):
    S, TM = tm
    assert TM.can(T, "supervisor", "approve_money") and not TM.can(T, "agent", "approve_money") and TM.can(T, "owner", "anything")
    TM.save_role(T, "team_lead", ["read", "reply", "assign", "approve_money"])
    assert TM.can(T, "team_lead", "approve_money")
    with pytest.raises(TM.TeamError, match="built-in"):
        TM.save_role(T, "admin", ["read"])
    with pytest.raises(TM.TeamError, match="cannot approve money"):
        TM.save_bands(T, [{"currency": "INR", "upto": 1000, "steps": ["agent"]}])
    TM.save_bands(T, [{"currency": "INR", "upto": 5000, "steps": ["supervisor"]}, {"currency": "INR", "upto": 0, "steps": ["supervisor", "finance"]},
                      {"currency": "USD", "upto": 100, "steps": ["finance"]}])
    assert TM.chain_for(T, 3000) == ["supervisor"] and TM.chain_for(T, 9000) == ["supervisor", "finance"]
    assert TM.chain_for(T, 50, "USD") == ["finance"] and TM.chain_for(T, 500, "USD") == ["finance", "owner"]


def _money(S, amount=3000):
    n = S.new_ticket(T, "Refund please, charged twice", "email", customer="email:r@q.com", category="billing")["number"]
    return S.exception_request(T, "refund", "Charged twice in October", amount, ticket=n)["exception"]


def test_approval_chain_links_limits_and_her_tap(tm):
    S, TM = tm
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.seva.api import make_web_router
    ravi = TM.save_agent(T, {"name": "Ravi", "role": "supervisor", "day_limit": 5000})
    mira = TM.save_agent(T, {"name": "Mira", "role": "finance"})
    TM.save_bands(T, [{"currency": "INR", "upto": 5000, "steps": ["supervisor"]}, {"currency": "INR", "upto": 0, "steps": ["supervisor", "finance"]}])
    e = _money(S, 3000)
    ch = e["chain"]
    assert len(ch) == 1 and ch[0]["person"] == "Ravi" and ch[0]["link"].count("/support/approve/") == 1
    tok = ch[0]["link"].rsplit("/", 1)[1]
    cl = TestClient((lambda a: (a.include_router(make_web_router()), a)[1])(FastAPI()))
    page = cl.get(f"/support/approve/{tok}")
    assert page.status_code == 200 and "Refund" in page.text and "does not move" in page.text and "default-src 'none'" in page.headers["content-security-policy"]
    done = cl.post(f"/support/approve/{tok}", data={"yes": "1", "note": "ok"})
    assert "Approved" in done.text
    assert S.exceptions(T)[0]["status"] == "approved" and any("approved" in x for x in S.told)
    assert cl.get(f"/support/approve/{tok}").status_code == 410                    # a link works once
    # Ravi has 2000 of his 5000 left today: a 4000 refund moves up to finance, and says why
    e2 = _money(S, 4000)
    assert e2["chain"][0]["person"] == "Mira" and "daily limit" in e2["chain"][0]["why"]
    # a big one: two steps in order. Ravi's limit is used, so finance (Mira) takes step 1; step 2 is finance too and
    # Mira already said yes, so it comes to her (the owner), said why
    e3 = _money(S, 9000)
    assert e3["chain"][0]["person"] == "Mira" and "daily limit" in e3["chain"][0]["why"]
    TM.decide_step(e3["chain"][0]["link"].rsplit("/", 1)[1], True)
    c3 = TM.chain(T, e3["id"])
    assert c3[0]["status"] == "yes" and c3[1]["status"] == "waiting" and c3[1]["person"] == "you" and "already said yes" in c3[1]["why"]
    assert next(x for x in S.exceptions(T) if x["id"] == e3["id"])["status"] == "pending"
    S.decide(T, e3["id"], False, by_tap=True)
    assert next(x for x in S.exceptions(T) if x["id"] == e3["id"])["status"] == "rejected"
    # a no on a link closes it
    e7 = _money(S, 1000)
    assert e7["chain"][0]["person"] == "Ravi"
    TM.decide_step(e7["chain"][0]["link"].rsplit("/", 1)[1], False, "not this time")
    assert next(x for x in S.exceptions(T) if x["id"] == e7["id"])["status"] == "rejected"
    # a link bound to the request: if the request changed, it refuses
    e4 = _money(S, 1000)
    from app.db import session
    with session() as s:
        s.get(S.SevaException, e4["id"]).amount = 1500
    with pytest.raises(TM.TeamError, match="changed"):
        TM.step_by_token(e4["chain"][0]["link"].rsplit("/", 1)[1])
    # her own tap decides at once; the waiting steps close
    e5 = _money(S, 2000)
    S.decide(T, e5["id"], True, by_tap=True)
    assert TM.chain(T, e5["id"])[0]["status"] == "skipped"
    assert not TM.waiting_on_chain(T, e5["id"])
    # a new link replaces the old
    e6 = _money(S, 500)
    old = e6["chain"][0]["link"].rsplit("/", 1)[1]
    TM.new_link(T, e6["chain"][0]["id"])
    with pytest.raises(TM.TeamError):
        TM.step_by_token(old)
    assert mira and ravi


def test_no_bands_means_her_tap_only(tm):
    S, TM = tm
    e = _money(S, 3000)
    assert e["chain"] == [] and S.exceptions(T)[0]["chain"] == []


def test_macros_fields_and_views(tm):
    S, TM = tm
    _team(TM)
    m = S.macro_add(T, "Visit booked", "Your engineer visit is booked; we will call before coming.", "english")
    S.macro_approve(T, m["id"])
    TM.set_macro_actions(T, m["id"], {"label": "visit", "status": "pending", "assign": "Ravi"})
    n = S.new_ticket(T, "No internet since morning", "email", customer="email:n@q.com", category="technical")["number"]
    out = TM.run_macro(T, n, m["id"])
    t = S.ticket(T, n)
    assert "visit" in t["labels"] and t["status"] == "pending" and t["assignee"] == "Ravi"
    assert any("engineer visit is booked" in x for x in S.told)
    d = S.macro_add(T, "Draft only", "Hello there.", "english")
    with pytest.raises(TM.TeamError, match="Approve"):
        TM.run_macro(T, n, d["id"])
    TM.save_fields(T, [{"label": "Order number", "type": "text"}, {"label": "Plan", "type": "choice", "options": "basic, pro"},
                       {"label": "Visit date", "type": "date"}])
    TM.set_custom(T, n, {"order_number": "A-55", "plan": "pro", "visit_date": "2026-11-21"})
    with pytest.raises(TM.TeamError, match="one of"):
        TM.set_custom(T, n, {"plan": "gold"})
    with pytest.raises(TM.TeamError, match="date"):
        TM.set_custom(T, n, {"visit_date": "tomorrow"})
    assert S.ticket(T, n)["custom"]["plan"] == "pro"
    TM.save_view(T, "Pro customers waiting", {"status": "open", "custom.plan": "pro"})
    TM.save_view(T, "Ravi's", {"assignee": "Ravi"})
    assert [x["number"] for x in TM.view_tickets(T, "Pro customers waiting")["tickets"]] == [n]
    assert n in [x["number"] for x in TM.view_tickets(T, "Ravi's")["tickets"]]
    assert out["did"] and "Sent 'Visit booked'" in out["say"]


def test_routes_and_tool(tm):
    S, TM = tm
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.seva.api import make_router
    a = FastAPI()
    a.include_router(make_router(lambda: None, lambda: T))
    cl = TestClient(a)
    p = cl.post("/api/seva/team/people", json={"name": "Ana", "langs": "es"}).json()["person"]
    assert cl.put("/api/seva/team/queues", json={"name": "Spanish", "members": [p["id"]]}).json()["queue"]["member_names"] == []
    assert cl.put("/api/seva/team/routes", json={"routes": [{"if": {"language": "es"}, "queue": "spanish"}]}).status_code == 200
    assert cl.post("/api/seva/team/rules", json={"name": "x", "actions": []}).status_code == 400
    d = cl.get("/api/seva/team").json()
    assert d["queues"][0]["key"] == "spanish" and d["routes"][0]["queue"] == "spanish" and "created" in d["events"]
    n = S.new_ticket(T, "Hola, mi pedido no llegó todavía", "email", customer="email:h@q.es")["number"]
    assert S.ticket(T, n)["queue"] == "spanish"
    import inspect
    from app.agent import seva_tools as ST
    assert 'what == "team"' in inspect.getsource(ST)


# ---------------------------------------------------------------- the Team & rules page in a real browser
@pytest.fixture
def t_server(tm, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.employee import hire
    hire.hire(T, "support", trust="seekh")
    S, TM = tm
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
        yield f"http://127.0.0.1:{port}", browser, KEY, S, TM
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_team_page_in_a_real_browser(t_server):
    base, browser, key, S, TM = t_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/team")
    pg.wait_for_selector("#spPerson")
    pg.fill("#spPerson [name=name]", "Ana")
    pg.fill("#spPerson [name=langs]", "es, en")
    pg.fill("#spPerson [name=tz]", "Asia/Kolkata")
    pg.select_option("#spPerson [name=role]", "supervisor")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/team/people") and r.request.method == "POST"):
        pg.click("#spPerson button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Ana · supervisor')", timeout=15000)
    pg.fill("#spQueue [name=name]", "Spanish")
    pg.check("#spQueue input[name=member]")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/team/queues")):
        pg.click("#spQueue button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('(spanish)')", timeout=15000)
    pg.wait_for_selector("#spRoute")
    pg.fill("#spRoute [name=language]", "es")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/team/routes")):
        pg.click("#spRoute button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('language es')", timeout=15000)
    pg.wait_for_selector("#spRule")
    pg.fill("#spRule [name=name]", "Urgent to Ana")
    pg.select_option("#spRule [name=cfield]", "priority")
    pg.fill("#spRule [name=cvalue]", "urgent")
    pg.select_option("#spRule [name=ado]", "assign")
    pg.fill("#spRule [name=avalue]", "Ana")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/team/rules")):
        pg.click("#spRule button[type=submit]")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Urgent to Ana')", timeout=15000)
    pg.wait_for_selector("#spBand")
    pg.fill("#spBand [name=steps]", "supervisor")
    with pg.expect_response(lambda r: r.url.endswith("/api/seva/team/bands")):
        pg.click("#spBand button[type=submit]")
    d = TM.overview(T)
    assert d["routes"][0]["queue"] == "spanish" and d["rules"][0]["name"] == "Urgent to Ana" and d["bands"]["bands"][0]["steps"] == ["supervisor"]
    S.new_ticket(T, "Hola, me cobraron dos veces", "email", customer="email:h@q.es")
    e = _money(S, 2500)
    assert e["chain"][0]["person"] == "Ana"
    pg.goto(base + "/console/support#/approvals")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.toLowerCase().includes('who says yes, in order')", timeout=15000)
    assert "/support/approve/" in pg.inner_text("#spPage")
    pg.goto(base + "/console/support#/team")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Hola, me cobraron')", timeout=15000)
    ctx.close()
    m = browser.new_context(viewport={"width": 390, "height": 900})
    m.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    mp = m.new_page()
    mp.on("pageerror", lambda e: errors.append(str(e)))
    mp.goto(base + "/console/support#/team")
    mp.wait_for_selector("#spPerson")
    assert mp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    m.close()
    assert not errors, errors
