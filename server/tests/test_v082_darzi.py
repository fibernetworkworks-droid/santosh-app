"""v0.82 Darzi Sahayak: a tailor's coworker. Gets the job, keeps every customer's measurements, checks dates against
her rules and earlier work, prepares 'ready' messages (her tap sends), waits for her Haan on new prices, delivers and
learns how long each garment really takes."""
import asyncio
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"


def _today():
    from app.darzi import service as D
    return D.today(T)


def _iso(days: int) -> str:
    return (_today() + timedelta(days=days)).isoformat()


def _open_day(start: int, closed: set[int] = frozenset()) -> int:
    d = start
    while (_today() + timedelta(days=d)).weekday() in closed:
        d += 1
    return d


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


# ---------------------------------------------------------------- pure pieces
def test_reads_measurements_the_way_tailors_write_them():
    from app.darzi.garments import clean_values, garment_of, missing, parse
    v = parse("L 15, chest 34, kamar 30, bahi 11 1/2, gala aage 7 peeche 8, shoulder 14½, mudda 16")
    assert v == {"length": 15, "chest": 34, "waist": 30, "sleeve_length": 11.5, "front_neck": 7, "back_neck": 8,
                 "shoulder": 14.5, "armhole": 16}
    assert parse("Length: 40\nBust 36\nHip 40") == {"length": 40, "chest": 36, "hip": 40}
    assert garment_of("2 saree blouse") == "blouse" and garment_of("lehnga") == "lehenga" and garment_of("fall pico") == "saree_work"
    assert garment_of("gents kurta") == "kurta_pajama" and garment_of("kuch naya") == "other"
    assert clean_values({"Chest": "34", "kamar": 30, "unknown": 5, "waist2": "x"}) == {"chest": 34, "waist": 30}
    assert missing("blouse", {"length": 15, "chest": 34}) == ["waist", "shoulder", "sleeve_length", "sleeve_round"]


def test_dates_in_her_words(env):
    from app.darzi import service as D
    assert D._date(T, "kal") == _iso(1) and D._date(T, "5 din") == _iso(5) and D._date(T, "2 hafte") == _iso(14)
    assert D._date(T, "2026-11-03") == "2026-11-03"
    t = _today()
    nxt = t + timedelta(days=10)
    assert D._date(T, f"{nxt.day}/{nxt.month}") == nxt.isoformat()
    with pytest.raises(D.DarziError):
        D._date(T, "jab bhi")


# ---------------------------------------------------------------- measurements
def test_measurements_kept_per_person_with_history_and_changes(env):
    from app.darzi import service as D
    m1 = D.save_measure(T, garment="blouse", values="L 15 chest 34 kamar 30 shoulder 14 bahi 11 bahi gola 11",
                        name="Sunita Sharma", phone="+91 98765 43210", note="deep back, dori")
    assert m1["customer"]["phone"] == "9876543210" and not m1["missing"] and not m1["changed"]
    m2 = D.save_measure(T, customer="9876543210", garment="blouse", values={"chest": 36.5})
    assert m2["values"]["chest"] == 36.5 and m2["values"]["waist"] == 30           # partial update keeps the rest
    assert m2["changed"] and "pehle 34" in m2["changed"][0] and "check" in m2["say"]
    assert m2["note"] == "deep back, dori"                                         # style note carried over
    D.save_measure(T, customer="Sunita", garment="frock", person="beti", values="length 22 chest 24")
    got = D.measures(T, "Sunita")
    assert {(m["garment"], m["person"]) for m in got["measures"]} == {("blouse", ""), ("frock", "beti")}
    assert len(D.measures(T, "Sunita", history=True)["measures"]) == 3
    with pytest.raises(D.DarziError):
        D.save_measure(T, garment="blouse", values="kuch nahi")


# ---------------------------------------------------------------- rules + earlier work
def test_check_against_her_rules(env):
    from app.darzi import service as D
    closed = {6}
    D.save_settings(T, pieces_per_day=2, closed_days=["Ravi"], rush_percent=20, min_days={"blouse": 4},
                    prices={"blouse": 500}, rules=["Bridal blouse 15 din se kam nahi"])
    D.save_measure(T, garment="blouse", values="L 15 chest 34 kamar 30 shoulder 14 bahi 11 bahi gola 11", name="Asha", phone="9000000001")
    ck = D.check(T, [{"garment": "blouse"}], "kal", customer="Asha")
    assert not ck["ok"] and any("4 din chahiye" in p for p in ck["problems"]) and ck["rush"]
    assert "20%" in " ".join(ck["problems"]) and ck["your_rules"] == ["Bridal blouse 15 din se kam nahi"]
    assert date.fromisoformat(ck["earliest"]) >= _today() + timedelta(days=4)
    assert date.fromisoformat(ck["earliest"]).weekday() != 6
    # a closed day
    sunday = next(_today() + timedelta(days=k) for k in range(5, 12) if (_today() + timedelta(days=k)).weekday() == 6)
    assert any("band" in p for p in D.check(T, [{"garment": "blouse"}], sunday.isoformat(), customer="Asha")["problems"])
    # capacity: 2 pieces a day
    d = _open_day(6, closed)
    r = D.new_order(T, [{"garment": "blouse", "qty": 2}], customer="Asha", deliver_on=_iso(d))
    assert r["saved"], r
    ck = D.check(T, [{"garment": "blouse"}], _iso(d), customer="Asha")
    assert any("roz 2 ka niyam" in p for p in ck["problems"])
    # no measurement yet -> a problem; a new customer -> a note
    D.customer_upsert(T, "Neha", "9000000002")
    assert any("naap nahi hai" in p for p in D.check(T, [{"garment": "blouse"}], _iso(_open_day(8, closed)), customer="Neha")["problems"])
    assert any("Naya graahak" in n for n in D.check(T, [{"garment": "blouse"}], _iso(_open_day(8, closed)), name="Koi Naya")["notes"])


def test_new_order_flow_quote_ready_deliver_and_learning(env):
    from app.darzi import service as D
    conv = conv_ctx().conversation_id
    D.save_settings(T, pieces_per_day=0, prices={"blouse": 500}, shop_name="Meghana Boutique")
    D.save_measure(T, garment="blouse", values="L 15 chest 34 kamar 30 shoulder 14 bahi 11 bahi gola 11", name="Riya Patil",
                   phone="9822012345")
    D.save_measure(T, customer="9822012345", garment="lehenga", values="L 15 chest 34 kamar 30 shoulder 14 bahi 11 "
                   "lehenga length 40 hip 40")
    # breaking a rule: not saved until she agrees
    r = D.new_order(T, [{"garment": "blouse"}], name="Riya Patil", phone="9822012345", deliver_on="kal", conv=conv)
    assert r["saved"] is False and r["check"]["problems"]
    r = D.new_order(T, [{"garment": "blouse", "qty": 2, "style": "boat neck"}, {"garment": "lehenga", "price": 4500}],
                    name="Riya Patil", phone="9822012345", deliver_on="12 din", trial_on="8 din", advance=1000, conv=conv)
    assert r["saved"], r
    o = r["order"]
    assert o["number"] == "D-0001" and o["items"][0]["price_paise"] == 50000 and "price_paise" not in o["items"][1]
    assert o["total"] == "₹1,000" and o["paid"] == "₹1,000" and o["balance"] == "₹0"   # lehenga not priced yet
    assert len(r["quotes"]) == 1 and r["quotes"][0]["price"] == "₹4,500" and "pehli baar" not in r["quotes"][0]["why"]
    assert _events("darzi_quote")[-1]["status"] == "pending"
    # her Haan: price in, list updated (a garment new to her list)
    q = D.decide_quote(T, r["quotes"][0]["id"], True)
    assert q["quote"]["status"] == "approved" and D.settings(T)["prices"]["lehenga"] == 4500
    v = D.get_order(T, "1")
    assert v["total"] == "₹5,500" and v["balance"] == "₹4,500" and not v["quote_pending"]
    with pytest.raises(D.DarziError):
        D.decide_quote(T, r["quotes"][0]["id"], True)                     # decided once
    # status -> ready: a draft card, never sent by itself
    out = D.set_status(T, "D-0001", "taiyaar", conv=conv)
    card = out["ready"]
    assert card["status"] == "draft" and "Riya" in card["text"] and "Meghana Boutique" in card["text"]
    assert "₹4,500" in card["text"] and card["wa_link"].startswith("https://wa.me/919822012345?text=")
    assert card["can_business"] is False and _events("darzi_ready")[-1]["number"] == "D-0001"
    # money she received, then delivery closes it with a log
    D.pay(T, "D-0001", 2000, "UPI")
    done = D.deliver(T, "D-0001", paid_now=2500, conv=conv)
    assert done["order"]["status"] == "delivered" and done["order"]["balance"] == "₹0"
    assert done["order"]["late_days"] == 0 and any("De diya" in x["what"] for x in done["log"])
    with pytest.raises(D.DarziError):
        D.cancel(T, "D-0001")
    # slip PDF
    pdf = D.slip_pdf(T, "D-0001")
    assert pdf[:4] == b"%PDF" and len(pdf) > 800


def test_learns_how_long_a_garment_really_takes(env):
    from app.darzi import service as D
    from app.darzi.service import DarziOrder
    D.save_settings(T, pieces_per_day=0, prices={"kurti": 400})
    for k in range(3):
        r = D.new_order(T, [{"garment": "alteration"}, {"garment": "kurti"}], name=f"C{k}", phone=f"90000001{k:02d}",
                        deliver_on="10 din", force=True)
        with session() as s:                                        # these took 9 days in real life
            o = s.get(DarziOrder, r["order"]["id"])
            o.received_on = (_today() - timedelta(days=9)).isoformat()
        D.deliver(T, r["order"]["id"])
    ck = D.check(T, [{"garment": "kurti"}], "", name="Nayi")
    assert ck["need_days"] >= 9 and any("asal mein ~9 din" in n for n in ck["notes"])
    # the price she charged before is what Hoola proposes for a garment not in her list
    D.save_settings(T, prices={"kurti": None})
    r = D.new_order(T, [{"garment": "kurti"}], name="C1", phone="9000000101", deliver_on="20 din", force=True)
    assert r["quotes"][0]["price"] == "₹400" and "pichhla" in r["quotes"][0]["why"].lower()


def test_day_summary_and_morning_once(env, monkeypatch):
    from app.darzi import service as D
    D.save_settings(T, pieces_per_day=0)
    r = D.new_order(T, [{"garment": "alteration"}], name="Late Wali", phone="9000000201", deliver_on="3 din", force=True)
    from app.darzi.service import DarziOrder
    with session() as s:
        s.get(DarziOrder, r["order"]["id"]).deliver_on = (_today() - timedelta(days=2)).isoformat()
    D.new_order(T, [{"garment": "alteration"}], name="Trial Wali", phone="9000000202", deliver_on="3 din", trial_on="aaj", force=True)
    d = D.day(T)
    assert [o["customer"]["name"] for o in d["late"]] == ["Late Wali"]
    assert [o["customer"]["name"] for o in d["trials"]] == ["Trial Wali"]
    assert "Der ho gayi" in d["text"] and len(d["week"]) == 7
    conv_ctx()
    now_local = datetime.now(D._tz(T))
    D.save_settings(T, morning_time=f"{now_local.hour:02d}:{now_local.minute:02d}")
    assert D.due_mornings() == [T] and D.due_mornings() == []          # once a day
    D.send_morning(T)
    assert _events("darzi_day")[-1]["late"] == 1


def test_tools_chat_and_owner_only_rules(env):
    from app.agent.tools import HANDLERS, Ctx, ToolError
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    out = run("darzi", action="measure", name="Pooja", phone="9811111111", garment="salwar suit",
              values="length 40 chest 36 kamar 32 hip 40 shoulder 15 bahi 18 bahi gola 12 salwar length 38 mohri 14")
    assert out["garment"] == "salwar_suit" and not out["missing"]
    out = run("darzi", action="new_order", customer="Pooja", items=[{"garment": "salwar suit", "price": 900}], deliver_on="10 din")
    assert out["saved"] and out["quotes"]
    assert run("darzi_dekho", what="orders")["orders"][0]["number"] == out["order"]["number"]
    assert run("darzi_dekho", what="customer", customer="Pooja")["measures"][0]["garment"] == "salwar_suit"
    assert run("darzi_dekho", what="prices")["pending_cards"]
    staff = Ctx("default", ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["darzi"](staff, action="rules", prices={"blouse": 1}))
    with pytest.raises(ToolError):
        run("darzi", action="status", order="D-9999", status="ready")


def test_employee_role_and_customer_whatsapp_status(env):
    from app.darzi import service as D
    from app.employee import roles
    from app.employee.models import BizContact, EmployeeProfile
    assert "tailoring" in roles.role_duties("tailor") and roles.PRESETS["tailor"]["role"] == "tailor"
    assert roles.duty_of("darzi") == "tailoring" and roles.kind_of("darzi_dekho") == "read"
    D.new_order(T, [{"garment": "alteration"}], name="Meena", phone="9890098900", deliver_on="2 din", force=True)
    D.new_order(T, [{"garment": "alteration"}], name="Doosri", phone="9000000999", deliver_on="2 din", force=True)
    with session() as s:
        s.add(EmployeeProfile(tenant_id=T, enabled=True, role="tailor"))
        c = BizContact(tenant_id=T, wa_id="919890098900", name="Meena")
        s.add(c)
        s.flush()
        cid = c.id
    from app.agent.tools import HANDLERS, Ctx, dispatch
    ctx = Ctx(T, conv_ctx().conversation_id, actor=f"customer:{cid}")
    got = asyncio.run(HANDLERS["biz_order_status"](ctx))
    assert [o["status"] for o in got["orders"]] == ["Naya"] and len(got["orders"]) == 1      # only her own
    del dispatch


def test_api(env):
    from app import main
    from app.darzi import service as D
    with TestClient(main.app) as c:
        assert "darzi" in c.get("/healthz").json()["features"]
        assert any(g["id"] == "blouse" for g in c.get("/api/darzi/garments").json()["garments"])
        c.put("/api/darzi/settings", json={"pieces_per_day": 0, "prices": {"shirt": 600}, "shop_name": "Test Tailors"})
        r = c.post("/api/darzi/measures", json={"name": "Raj", "phone": "9123456789", "garment": "shirt",
                                                 "values": {"length": 30, "chest": 40, "waist": 36, "hip": 40, "shoulder": 18,
                                                            "sleeve": 24}})
        assert r.status_code == 200, r.text
        r = c.post("/api/darzi/orders", json={"name": "Raj", "phone": "9123456789", "items": [{"garment": "shirt", "qty": 2}],
                                              "deliver_on": "7 din", "advance": 500})
        assert r.status_code == 200 and r.json()["saved"], r.text
        oid = r.json()["order"]["id"]
        assert c.get("/api/darzi/orders").json()["orders"][0]["total"] == "₹1,200"
        assert c.post(f"/api/darzi/orders/{oid}/status", json={"status": "ready"}).json()["ready"]["text"]
        slip = c.get(f"/api/darzi/orders/{oid}/slip")
        assert slip.status_code == 200 and slip.content[:4] == b"%PDF"
        assert c.post(f"/api/darzi/orders/{oid}/send_business", json={}).status_code == 400   # never wrote to the business number
        assert c.post(f"/api/darzi/orders/{oid}/deliver", json={"amount": 700}).json()["order"]["balance"] == "₹0"
        assert c.get("/api/darzi/today").status_code == 200
        cust = c.get("/api/darzi/customers").json()["customers"][0]
        assert c.get(f"/api/darzi/customers/{cust['id']}").json()["measures"][0]["garment"] == "shirt"
        assert c.post("/api/darzi/orders/nope/status", json={"status": "ready"}).status_code == 400
        assert c.post("/api/darzi/check", json={"items": [{"garment": "shirt"}], "deliver_on": "kal"}).json()["problems"]
    assert D.settings(T)["shop_name"] == "Test Tailors"
