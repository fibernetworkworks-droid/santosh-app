"""v0.85 Daftar Sahayak: Hoola as the office manager. Gets the job, tracks supplies (learned reorder point), repairs
(SLA, repeat faults), renewals (windows, notice date, price rise), reminds the team (drafts she sends), writes the weekly
office note, waits for her Haan on every spend, and learns from what happened."""
import asyncio
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, now, session
from tests.test_life import conv_ctx

T = "default"


def _O():
    from app.office import service as O
    return O


def _iso(days: int) -> str:
    return (_O().today(T) + timedelta(days=days)).isoformat()


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def _age_log(item_name: str, days: int):
    """Move an item's log back in time, as if it had been used over `days` days."""
    O = _O()
    with session() as s:
        it = s.scalars(select(O.OfficeItem).where(O.OfficeItem.name == item_name)).first()
        lg = json.loads(it.log)
        for i, e in enumerate(lg):
            e["at"] = (now() - timedelta(days=days - i * days / max(1, len(lg)))).isoformat()
        it.log = json.dumps(lg)


def test_dates_money_and_months(env):
    O = _O()
    assert O._date(T, "kal") == _iso(1) and O._date(T, "2 hafte") == _iso(14) and O._date(T, "2026-11-03") == "2026-11-03"
    assert O._paise("1,250.50") == 125050 and O._rs(125000) == "₹1,250"
    from datetime import date
    assert O._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    with pytest.raises(O.OfficeError):
        O._date(T, "jab bhi")


def test_supplies_learn_reorder_point_and_make_a_spend_card(env):
    O = _O()
    O.save_settings(T, lead_days=3, safety_days=2)
    v = O.vendor_upsert(T, "Sharma Stationers", phone="+91 98200 11111", category="stationery")
    O.item_upsert(T, "Printer toner", qty=10, unit="pcs", vendor="Sharma Stationers", price=1800)
    for _ in range(7):
        O.use(T, "toner", 1)
    _age_log("Printer toner", 14)
    it = O.items(T, "toner")[0]
    assert 0.4 < it["per_day"] < 0.6                     # 7 used over ~2 weeks
    assert it["reorder_point"] == 3                      # ceil(0.5 x (3 + 2))
    assert it["qty"] == 3 and it["low"]
    out = O.reorder(T, conv=conv_ctx().conversation_id)
    sp = out["spends"][0]
    assert sp["status"] == "pending" and sp["vendor"]["id"] == v["id"] and "reorder point" in sp["checks"][0]
    assert sp["lines"][0]["qty"] >= 15                    # ~30 days of use
    assert O.reorder(T)["spends"][0]["id"] == sp["id"]    # never asks twice
    # her Haan: on order, vendor draft (never sent by Hoola)
    got = O.decide_spend(T, sp["number"], True)
    assert got["spend"]["status"] == "approved" and got["spend"]["wa_link"].startswith("https://wa.me/919820011111")
    assert "apne app se" in got["say"]
    assert O.items(T, "toner")[0]["on_order"] >= 15 and not O.items(T, "toner")[0]["low"]
    r = O.restock(T, "toner", sp["lines"][0]["qty"], price=2200)
    assert "zyada" in r["price_note"] and r["on_order"] == 0
    assert _events("office_spend")


def test_repairs_sla_repeat_and_paid_repair_needs_haan(env):
    O = _O()
    a = O.ticket_new(T, "AC thanda nahi kar raha", asset="AC cabin 2", vendor="Cool Care")
    t = a["ticket"]
    assert t["number"] == "R-0001" and t["category"] == "ac" and t["priority"] == "normal" and t["status"] == "assigned"
    assert O.ticket_new(T, "Switch board se spark aa raha hai")["ticket"]["priority"] == "urgent"
    O.ticket_update(T, "R-0001", status="done")
    b = O.ticket_new(T, "AC se paani tapak raha", asset="AC cabin 2")
    assert b["notes"] and "R-0001" in b["notes"][0]                   # earlier work: same asset again
    assert b["ticket"]["vendor"]["name"] == "Cool Care"               # who fixed it before
    up = O.ticket_update(T, b["ticket"]["number"], cost=2500)
    assert up["spend"]["status"] == "pending" and up["spend"]["kind"] == "repair"
    O.decide_spend(T, up["spend"]["id"], False)
    assert O.spends(T, "rejected")[0]["number"] == up["spend"]["number"]
    # late ticket shows in the morning list
    O2 = _O()
    with session() as s:
        x = s.scalars(select(O2.OfficeTicket).where(O2.OfficeTicket.number == "R-0002")).first()
        x.due_at = now() - timedelta(hours=1)
    assert any(x["number"] == "R-0002" for x in O.day(T)["late_tickets"])


def test_renewals_windows_notice_rise_and_roll(env):
    O = _O()
    r = O.renewal_add(T, "Fire NOC Form B", "10 din", amount=4000, notice_by="", vendor="Agni Safety")["renewal"]
    assert r["kind"] == "certificate" and r["every_months"] == 12 and r["days_left"] == 10
    O.renewal_add(T, "AC AMC", "5 din", kind="amc", notice_by="2 din", amount=12000)
    d = O.send_morning(T)
    names = {x["name"] for x in d["renewals"]}
    assert names == {"Fire NOC Form B", "AC AMC"} and "Mana karne ki aakhri tareekh" in d["text"]
    assert not O.send_morning(T)["renewals"]                          # same window = no repeat reminder
    pay = O.renewal_pay(T, "AC AMC")
    assert pay["spend"]["amount"] == "₹12,000" and pay["spend"]["status"] == "pending"
    O.renewal_done(T, "AC AMC", paid=12000)
    done = O.renewal_done(T, "AC AMC", paid=14000)
    assert "zyada" in done["warn"]
    assert done["renewal"]["due_on"] > _iso(300)                      # rolled a year ahead each time
    st = {x["name"]: x["added"] for x in O.starters(T)}
    assert len(st) > 10 and st["AC AMC"] is True and st["Pest control"] is False


def test_team_deadlines_nudge_drafts_only(env):
    O = _O()
    O.save_settings(T, team=[{"name": "Rahul", "phone": "9812345678"}, "Priya"], office_name="Newtika")
    O.deadline_add(T, "Monthly sales report", "kal", owner="Rahul")
    O.deadline_add(T, "Vendor list update", "aaj", owner="Rahul")
    O.deadline_add(T, "Annual plan", "20 din", owner="Priya")
    n = O.nudge(T, owner="Rahul")
    assert len(n["cards"]) == 1 and "Monthly sales report" in n["cards"][0]["text"] and "Newtika" in n["cards"][0]["text"]
    assert n["cards"][0]["wa_link"].startswith("https://wa.me/919812345678")
    assert O.nudge(T, owner="Priya")["cards"] == []                  # not due yet
    O.deadline_done(T, "Vendor list")
    assert [d["title"] for d in O.deadlines(T)] == ["Monthly sales report", "Annual plan"]


def test_petty_bills_msme_and_duplicates(env):
    O = _O()
    O.petty_add(T, 5000, "float", kind="in")
    out = O.petty_add(T, 300, "chai biscuit", by="Ramesh")
    assert out["balance"] == "₹4,700" and "Bill ki photo" in out["say"]
    O.vendor_upsert(T, "Small Supplier", udyam=True, gstin="27AAPFU0939F1ZV")
    b = O.bill_add(T, "Small Supplier", 11800, number="INV-77", bill_date=_iso(-40), gst=1800)
    assert any("MSME" in f for f in b["bill"]["flags"])
    assert O.bill_add(T, "Small Supplier", 11800, number="inv-77")["duplicate"]
    assert O.day(T)["bills"]
    O.bill_paid(T, "INV-77")
    assert O.bills(T) == []


def test_weekly_note_and_morning_card(env):
    O = _O()
    O.item_upsert(T, "A4 paper", qty=5, unit="ream", min_qty=10)
    O.use(T, "A4 paper", 2)
    O.ticket_new(T, "Wifi band hai", priority="high")
    O.deadline_add(T, "GST data to CA", "3 din", owner="Priya")
    n = O.weekly_note(T, make_file=True, conv=conv_ctx().conversation_id)
    assert "Repair aur maintenance" in n["text"] and "A4 paper" in n["text"] and n["numbers"]["tickets_opened"] == 1
    assert "GST data to CA" in n["text"]
    assert n.get("file", {}).get("file_id")
    assert _events("office_note")
    from datetime import datetime
    O.save_settings(T, morning_time=datetime.now(O._tz(T)).strftime("%H:%M"))
    assert T in O.due_mornings() and T not in O.due_mornings()       # once a day
    O.send_morning(T)
    assert _events("office_day") and "A4 paper" in _events("office_day")[-1]["text"]
    assert "DAFTAR" in O.prompt_block(T)


def test_tools_owner_only_and_employee_wiring(env):
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    ctx = conv_ctx()

    def run(tool, **a):
        return asyncio.run(HANDLERS[tool](ctx, **a))

    assert run("office", action="item_add", name="Pen", qty=50, unit="pcs")["item"]["qty"] == 50
    assert run("office", action="use", item="pen", qty=5)["qty"] == 45
    assert run("office", action="ticket_new", title="Printer jam")["ticket"]["category"] == "printer"
    assert run("office", action="spend_request", title="Naya chair", amount=3500, kind="purchase")["spend"]["status"] == "pending"
    assert run("office_dekho", what="spends")["spends"]
    assert run("office_dekho", what="today")["today"].startswith("Office ka din")
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["office"](staff, action="rules", month_budget=1))
    with pytest.raises(ToolError):
        run("office", action="ticket_update", ticket="R-0999", status="done")
    assert roles.duty_of("office") == "office_admin" and roles.kind_of("office_dekho") == "read"
    assert "office_admin" in roles.role_duties("office_manager") and roles.PRESETS["office_manager"]["role"] == "office_manager"
    from app import voice
    assert "office" in voice.VOICE_TOOL_NAMES


def test_api(env):
    from app import main
    with TestClient(main.app) as c:
        assert "office" in c.get("/healthz").json()["features"]
        c.put("/api/office/settings", json={"office_name": "Test Office", "month_budget": 5000})
        it = c.post("/api/office/items", json={"name": "Toner", "qty": 1, "min_qty": 2, "price": 1500}).json()
        assert it["low"]
        sp = c.post("/api/office/reorder", json={}).json()["spends"][0]
        assert sp["month_left"] == "₹5,000"
        assert c.post(f"/api/office/spends/{sp['id']}", json={"approve": True}).json()["spend"]["status"] == "approved"
        t = c.post("/api/office/tickets", json={"title": "Light nahi jal rahi"}).json()["ticket"]
        assert c.patch(f"/api/office/tickets/{t['id']}", json={"status": "done"}).json()["ticket"]["status"] == "done"
        rn = c.post("/api/office/renewals", json={"name": "Domain hoola.in", "due_on": "20 din"}).json()["renewal"]
        assert rn["kind"] == "domain"
        assert c.post(f"/api/office/renewals/{rn['id']}/done", json={"paid": 900}).status_code == 200
        dl = c.post("/api/office/deadlines", json={"title": "Report", "due_on": "kal", "owner": "Rahul"}).json()["deadline"]
        assert c.post(f"/api/office/deadlines/{dl['id']}/done", json={}).json()["deadline"]["status"] == "done"
        assert c.post("/api/office/petty", json={"amount": 100, "what": "courier"}).status_code == 200
        assert c.post("/api/office/bills", json={"vendor": "X", "amount": 500}).status_code == 200
        allv = c.get("/api/office").json()
        assert allv["settings"]["office_name"] == "Test Office" and allv["items"] and allv["starters"]
        assert c.post("/api/office/note", json={"file": False}).json()["text"]
        assert c.post("/api/office/renewals", json={"name": "x", "due_on": "jab bhi"}).status_code == 400
