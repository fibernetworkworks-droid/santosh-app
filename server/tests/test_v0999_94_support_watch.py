"""SUPPORT WATCH (G9 of docs/SUPPORT_GLOBAL_PLAN.md): watching every ticket until it is truly solved - clocks in HER
working hours and time zone, "did this fix it?" before closing (YES closes, NO sends it back, no answer closes after her
days), the same problem again reopens it, the reminder ladder (before / at / past the deadline / again, never in quiet
hours, a daily cap), "still on it" updates to the customer, the list per person and stuck tickets with the reason.
Walked in a real browser."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import app.seva.service  # noqa: F401  (tables for init_db)

T = "default"
IST = ZoneInfo("Asia/Kolkata")
WEEK = {"mon": ["09:00", "18:00"], "tue": ["09:00", "18:00"], "wed": ["09:00", "18:00"], "thu": ["09:00", "18:00"],
        "fri": ["09:00", "18:00"], "sat": [], "sun": []}


def ist(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=IST).astimezone(timezone.utc)


@pytest.fixture
def sv(env, monkeypatch):
    from app.seva import service as S
    monkeypatch.setattr(S, "_ai", lambda *a, **k: "")
    monkeypatch.setattr(S, "_ai_json", lambda *a, **k: {})
    from app import supportchat as SC
    SC._OF.clear()
    SC._BLOCK.clear()
    box = {"now": ist(2026, 11, 20, 10)}                   # a Friday, 10:00 in India
    monkeypatch.setattr(S, "clock", lambda: box["now"])
    told, chat = [], []
    monkeypatch.setattr(S, "_tell", lambda tenant, tid, text, **k: (told.append(text), _mark(S, tid, k), {"sent": "whatsapp", "text": text})[2])
    monkeypatch.setattr(S, "_note_chat", lambda tenant, text, conv="": chat.append(text))
    S.box, S.told, S.chat = box, told, chat
    return S


def _mark(S, tid, k):
    from app.db import session
    with session() as s:
        t = s.get(S.SevaTicket, tid)
        t.told_at = S.clock()
        if k.get("first"):
            t.awaiting_since = None
            S._mark_first(t)


def _telecom():
    from app.seva import profile as PF
    pv = PF.preview(T, {"industry": "telecom"})
    PF.apply(T, {"industry": "telecom"}, pv["hash"])


def _to_fixed(S, n):
    from app.seva import flow as FL
    FL.move(T, n, "checked", "owner")
    FL.move(T, n, "fixed", "owner")


def test_working_hours_arithmetic(sv):
    from app.seva import watch as W
    W.save(T, {"hours_on": True, "week": WEEK, "holidays": ["2026-11-24"]})
    fri5 = ist(2026, 11, 20, 17)
    assert W.add_work(T, fri5, 2) == ist(2026, 11, 23, 10)          # Friday 17:00 + 2 working hours = Monday 10:00
    assert W.add_work(T, ist(2026, 11, 23, 17), 2) == ist(2026, 11, 25, 10)   # Tuesday is her holiday
    assert W.work_seconds(T, fri5, ist(2026, 11, 23, 10)) == 2 * 3600
    assert not W.open_now(T, ist(2026, 11, 21, 12)) and W.open_now(T, ist(2026, 11, 20, 12))
    W.save(T, {"hours_on": False})
    assert W.add_work(T, fri5, 2) == fri5 + timedelta(hours=2)        # 24/7 = plain hours
    for bad, word in (({"week": WEEK | {"mon": ["18:00", "09:00"]}}, "after the opening"), ({"holidays": ["24 Nov"]}, "YYYY-MM-DD"),
                      ({"quiet": ["25:00", "08:00"]}, "HH:MM"), ({"hours_on": True, "week": {d: [] for d in WEEK}}, "no day has hours"),
                      ({"max_day": 0}, "between 1")):
        with pytest.raises(W.WatchError, match=word):
            W.save(T, bad)


def test_stage_deadline_and_clock_in_her_hours(sv):
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"hours_on": True, "week": WEEK})
    S.box["now"] = ist(2026, 11, 20, 17, 30)
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Ana", phone="919800000001")["number"]
    v = S.ticket(T, n)
    assert v["stage"]["due"] == ist(2026, 11, 23, 9, 30).isoformat()     # 1 working hour: half today, half Monday
    S.box["now"] = ist(2026, 11, 23, 9, 0)
    c = S.ticket(T, n)["clocks"]
    assert c["working_hours"] and c["total_h"] == 0.5                    # the weekend does not count
    assert S.ticket(T, n)["sla"]["active_h"] == 0.5


def test_did_this_fix_it_yes_closes(sv):
    from app.seva import engine as E
    S = sv
    _telecom()
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Ben", phone="919800000002")["number"]
    _to_fixed(S, n)
    from app.seva import flow as FL
    FL.move(T, n, "confirmed", "owner")
    v = S.ticket(T, n)
    assert v["status"] == "resolved" and "Did this fix it?" in S.told[-1] and v["clocks"]["confirm_by"]
    r = E.reply(T, "yes it works now, thanks", "whatsapp", "wa:919800000002")
    assert r["decision"] == "confirmed" and n in r["reply"]
    v = S.ticket(T, n)
    assert v["status"] == "closed" and v["stage"]["stage"] == "closed" and "1 to 5" in S.told[-1]   # rating asked after closing
    r = E.reply(T, "5", "whatsapp", "wa:919800000002")
    assert r["decision"] == "rated" and S.ticket(T, n)["csat"] == 5


def test_did_this_fix_it_no_goes_back(sv):
    from app.seva import engine as E
    from app.seva import flow as FL
    S = sv
    _telecom()
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Chi", phone="919800000003")["number"]
    _to_fixed(S, n)
    FL.move(T, n, "confirmed", "owner")
    r = E.reply(T, "no, still not working", "whatsapp", "wa:919800000003")
    assert r["decision"] == "not_fixed"
    v = S.ticket(T, n)
    assert v["status"] == "open" and v["stage"]["stage"] == "fixed" and v["clocks"]["waiting_reply_h"] == 0
    assert any("NOT fixed" in c for c in S.chat)
    assert [m["to"] for m in FL.history(T, v["id"])][-1] == "fixed"


def test_no_answer_closes_after_her_days(sv):
    from app.seva import flow as FL
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"confirm_days": 2})
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Dev", phone="919800000004")["number"]
    _to_fixed(S, n)
    FL.move(T, n, "confirmed", "owner")
    S.box["now"] += timedelta(days=1)
    W.sweep(T)
    assert S.ticket(T, n)["status"] == "resolved"
    S.box["now"] += timedelta(days=1, minutes=5)
    assert W.sweep(T)["closed_quiet"] == 1
    v = S.ticket(T, n)
    assert v["status"] == "closed" and any(x["kind"] == "closed_quiet" for x in W.reminders(T, v["id"]))


def test_same_problem_again_reopens(sv):
    from app.seva import flow as FL
    S = sv
    _telecom()
    n = S.new_ticket(T, "no internet since morning, red light on the router", "whatsapp", name="Eve", phone="919800000005")["number"]
    _to_fixed(S, n)
    FL.move(T, n, "confirmed", "owner")
    FL.move(T, n, "closed", "owner")
    S.box["now"] += timedelta(days=2)
    out = S.new_ticket(T, "no internet since morning, red light on the router again", "whatsapp", name="Eve", phone="919800000005")
    assert out["reopened"] and out["number"] == n
    v = S.ticket(T, n)
    assert v["status"] == "open" and v["clocks"]["reopens"] == 1 and v["stage"]["stage"] == "fixed"
    assert any("reopened" in c for c in S.chat)
    S.box["now"] += timedelta(days=30)
    FL.move(T, n, "confirmed", "owner")
    FL.move(T, n, "closed", "owner")
    S.box["now"] += timedelta(days=20)
    assert S.new_ticket(T, "no internet since morning, red light on the router", "whatsapp", name="Eve",
                        phone="919800000005")["number"] != n           # outside her window: a new ticket


def test_reminder_ladder(sv):
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"before_h": 0.5, "boss_after_h": 2, "repeat_h": 3, "supervisor": "Meena", "quiet": [], "update_h": 0})
    from app.seva import flow as FL
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Fay", phone="919800000006")["number"]
    FL.move(T, n, "checked", "owner")
    FL.move(T, n, "visit", "owner")                                        # 'Engineer visit' = the team's, 24 h
    t0 = S.box["now"]
    S.reply(T, n, "We are on it.")
    dl = t0 + timedelta(hours=24)
    kinds = []
    for at in (dl - timedelta(minutes=20), dl + timedelta(minutes=1), dl + timedelta(hours=2, minutes=5), dl + timedelta(hours=3),
               dl + timedelta(hours=5, minutes=10)):
        S.box["now"] = at
        W.sweep(T)
    kinds = [x["kind"] for x in reversed(W.reminders(T)) if x["kind"] in ("before", "due", "boss", "repeat")]
    assert kinds == ["before", "due", "boss", "repeat"]
    due = next(x for x in W.reminders(T) if x["kind"] == "due")
    assert "Meena" in due["to"] and any("Past their deadline" in c and n in c for c in S.chat)


def test_quiet_hours_and_daily_cap(sv):
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"quiet": ["21:00", "08:00"], "boss_after_h": 0.5, "repeat_h": 0.5, "max_day": 3, "update_h": 0})
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Gia", phone="919800000007")["number"]
    S.box["now"] = ist(2026, 11, 20, 23)                                   # 23:00: quiet
    assert W.sweep(T)["reminders"] == 0
    for h in range(8, 14):
        S.box["now"] = ist(2026, 11, 21, h)
        W.sweep(T)
    assert len([x for x in W.reminders(T) if x["number"] == n]) == 3       # never more than her cap a day


def test_customer_kept_informed(sv):
    from app.seva import flow as FL
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"update_h": 6, "ladder_on": False})
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Hal", phone="919800000008")["number"]
    FL.move(T, n, "checked", "owner")
    FL.move(T, n, "visit", "owner")
    S.box["now"] += timedelta(hours=5)
    assert W.sweep(T)["updates"] == 0
    S.box["now"] += timedelta(hours=2)
    assert W.sweep(T)["updates"] == 1 and S.told[-1].startswith("We are still on it.") and "Engineer visit" in S.told[-1]
    S.box["now"] += timedelta(hours=1)
    assert W.sweep(T)["updates"] == 0                                    # not again before her hours


def test_digest_stuck_routes_and_tools(sv):
    from app.agent import seva_tools as ST
    from app.db import session
    from app.main import app
    from app.seva import flow as FL
    from app.seva import watch as W
    S = sv
    _telecom()
    W.save(T, {"supervisor": "Meena"})
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Ivy", phone="919800000009")["number"]
    FL.move(T, n, "checked", "owner")
    for to in ("visit", "visited", "visit", "visited"):
        FL.move(T, n, to, "owner", fields={"visit_window": "Thu 10-12"})
    st = {x["number"]: x for x in W.stuck_all(T)}
    assert "moving back and forth between stages" in st[n]["reasons"]
    people = W.digest(T)
    assert people[0]["person"] == "Meena" and people[0]["supervisor"] and n in people[0]["open"]
    with session() as s:
        t = s.scalars(S.select(S.SevaTicket).where(S.SevaTicket.number == n)).one()
        t.assignee = "Ravi"
    assert any(x["person"] == "Ravi" for x in W.digest(T))
    c = TestClient(app)
    r = c.get("/api/seva/watch").json()
    assert {"confirming", "reminders", "digest", "stuck", "rules"} <= set(r)
    assert c.put("/api/seva/watch", json={"hours_on": True, "week": WEEK}).json()["hours_on"] is True
    assert c.put("/api/seva/watch", json={"repeat_h": 0}).status_code == 400
    assert c.post(f"/api/seva/tickets/{n}/confirm", json={"yes": True}).json()["decision"] == "confirmed"
    assert c.get(f"/api/seva/reminders?ticket={n}").json()["reminders"][0]["kind"] == "confirmed"
    names = {t["name"]: t for t in ST.SEVA_TOOLS}
    assert {"confirm", "watch_save"} <= set(names["seva"]["input_schema"]["properties"]["action"]["enum"])
    assert {"watch", "reminders", "digest"} <= set(names["seva_dekho"]["input_schema"]["properties"]["what"]["enum"])
    from app import push
    assert push.render("seva_remind", {"kind": "due", "ticket": n, "text": "x"}) and "seva_remind" in push.PUSH_KINDS


@pytest.fixture
def w_server(sv, monkeypatch):
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
    from app.seva import flow as FL
    S = sv
    S.box["now"] = datetime.now(timezone.utc)
    hire.hire(T, "support", trust="seekh")
    _telecom()
    n = S.new_ticket(T, "no internet since morning", "whatsapp", name="Jo", phone="919800000010")["number"]
    _to_fixed(S, n)
    FL.move(T, n, "confirmed", "owner")
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


def test_watch_in_a_real_browser(w_server):
    base, browser, key, n = w_server
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base + "/console/support#/today")
    pg.wait_for_function("() => document.querySelector('#spPage').innerText.includes('Waiting for the customer to confirm')", timeout=20000)
    pg.goto(base + "/console/support#/settings")
    pg.wait_for_selector("#spWatch")
    pg.check("#spWatch [name=hours_on]")
    pg.fill("#spWatch [name=supervisor]", "Meena")
    with pg.expect_response(lambda r: "/api/seva/watch" in r.url and r.request.method == "GET", timeout=10000):
        with pg.expect_response(lambda r: "/api/seva/watch" in r.url and r.request.method == "PUT", timeout=10000) as put:
            pg.click("#spWatch button[type=submit]")
    assert put.value.json()["supervisor"] == "Meena" and put.value.json()["hours_on"] is True
    pg.wait_for_function("() => document.querySelector('#spWatch [name=supervisor]') && document.querySelector('#spWatch [name=supervisor]').value === 'Meena'", timeout=10000)
    pg.wait_for_timeout(300)
    pg.goto(base + f"/console/support#/ticket/{n}")
    pg.wait_for_selector("button[data-confirm=yes]")
    assert "Counted in your working hours" in pg.inner_text("#spPage")
    pg.click("button[data-confirm=yes]")
    pg.wait_for_function("() => !document.querySelector('button[data-confirm=yes]') && document.querySelector('#spPage').innerText.includes('Clocks')", timeout=10000)
    ctx.close()
    p2 = browser.new_context(viewport={"width": 390, "height": 900})
    p2.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    m = p2.new_page()
    m.on("pageerror", lambda e: errors.append(str(e)))
    m.goto(base + "/console/support#/settings")
    m.wait_for_selector("#spWatch")
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
    p2.close()
    assert not errors, errors
