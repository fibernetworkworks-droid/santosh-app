"""Driver Sahayak: law limits on duties (OSH Code 8 h / 48 h, rest, spread-over, 6 days), licence in the Pehchaan Locker,
licence class vs vehicle weight, overlaps never saved, her force + reason only as owner, duty planning, trip sheets from words /
driver messages / photo OCR with km continuity + fuel checks, missing sheets, message drafts sent ONLY by her tap (self /
business WhatsApp / Hoola Network), worker reminders once per window, attendance + payroll export, tools (staff / customer) and API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.drivers.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
IST = timezone(timedelta(hours=5, minutes=30))
N0 = datetime(2026, 10, 23, 10, 0, tzinfo=IST).astimezone(timezone.utc)      # Friday 23 Oct 2026, 10 am IST


@pytest.fixture
def dv(env, monkeypatch):
    from app.drivers import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "clock", lambda: N0)
    monkeypatch.setattr(S, "_model_extract", lambda text: None)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules_pure():
    from app.drivers import rules as R
    p = R.parse_sheet("start 45210 end 45480, diesel 40 L Rs 3800, toll 450, khana 200. Pune se Nashik tak")
    assert p["start_km"] == 45210 and p["end_km"] == 45480 and p["fuel_l"] == 40 and p["fuel_amount"] == 3800 and p["tolls"] == 450
    assert p["route"] == "Pune - Nashik" and p["expenses"] == [{"what": "Khana / bhatta", "amount": 200.0}]
    q = R.parse_sheet("km 12,300 - 12,560 subah 6 baje se shaam 7 baje tak tel 30 litre 2900")
    assert (q["start_km"], q["end_km"], q["start_time"], q["end_time"]) == (12300, 12560, "06:00", "19:00")
    assert R.parse_sheet("aaj trip theek rahi") == {}                       # nothing invented
    assert R.classes_of("LMV, HGV") == ["lmv", "hgv"] and R.classes_of("lmv-tr") == ["lmv_tr"]
    assert R.hm("shaam 7") == "19:00" and R.hm("6:30 pm") == "18:30" and R.hm("raat 2") == "02:00" and R.hm("abc") == ""
    assert R.limits({"day_h": 10})["day_h"] == 8 and R.limits({"day_h": 7})["day_h"] == 7 and R.limits({"between_h": 6})["between_h"] == 9
    assert "7,500" in R.licence_ok_for(["lmv"], 12000)[0] and R.licence_ok_for(["lmv"], 6500) == [] and R.licence_ok_for(["hgv"], 25000) == []
    assert "0062821" not in R.mask_ids("DL MH1420110062821 phone 9822012345") and "2821" in R.mask_ids("DL MH1420110062821")
    assert "9822012345" not in R.mask_ids("phone 9822012345")
    assert R.dl_valid("MH14 2011 0062821") and not R.dl_valid("12345")
    assert R.window_hit(20) == 30 and R.window_hit(5) == 7 and R.window_hit(0) == 0 and R.window_hit(-3) == -1 and R.window_hit(45) is None
    d = date(2026, 10, 26)
    drv = {"name": "Ramesh", "active": True, "dl_valid_to": date(2030, 1, 1), "classes": ["lmv"]}
    c = R.check_duty({"day": d, "start": "06:00", "end": "17:00", "break_min": 30}, [], drv, set())
    assert c["work_h"] == 10.5 and c["ot_h"] == 2.5 and not c["block"] and any("overtime" in x for x in c["law"])
    assert c["spread_h"] == 11
    c = R.check_duty({"day": d, "start": "06:00", "end": "13:00"}, [{"day": d - timedelta(days=1), "start": "14:00", "end": "23:00"}], drv, set())
    assert any("7 ghante aaraam" in x for x in c["law"]) and any("30 minute" in x for x in c["warn"])
    c = R.check_duty({"day": d, "start": "08:00", "end": "12:00"}, [{"day": d, "start": "11:00", "end": "15:00"}], drv, set())
    assert c["block"]
    c = R.check_duty({"day": d, "start": "08:00", "end": "12:00"}, [], {**drv, "dl_valid_to": date(2026, 10, 1)}, set())
    assert any("s.181" in x for x in c["block"])
    six = [{"day": d - timedelta(days=i), "start": "08:00", "end": "14:00"} for i in range(1, 7)]
    c = R.check_duty({"day": d, "start": "08:00", "end": "14:00"}, six, drv, set())
    assert any("Lagaatar 7 din" in x for x in c["law"])
    wk = [{"day": date(2026, 10, 26) + timedelta(days=i), "start": "06:00", "end": "16:00", "break_min": 30} for i in range(5)]
    c = R.check_duty({"day": date(2026, 10, 31), "start": "06:00", "end": "11:00"}, wk, drv, set())
    assert any("hafte" in x for x in c["law"]) and c["week_h"] > 48
    f = R.check_trip({"start_km": 100, "end_km": 300, "fuel_l": 40}, 90, 10.0)
    assert {x["kind"] for x in f} == {"km_gap", "fuel_odd"}
    assert R.check_trip({"start_km": 500, "end_km": 400}, None, None)[0]["kind"] == "km_back"


def test_drivers_locker_duties_and_plan(dv):
    S = dv
    from app import idvault
    S.save_settings(T, business="Ingle Transport")
    S.set_vehicle(T, "MH12 AB 1234", gvw_kg=12000, kind="truck", kmpl=4)
    S.set_vehicle(T, "MH12CD5678", gvw_kg=1800, kind="car")
    r = S.save_driver(T, "Ramesh Patil", phone="98220 12345", licence="MH14 2011 0062821", classes="LMV, HGV",
                      dl_valid_to="12-11-2027", medical_valid_to="2027-05-01", vehicle="MH12AB1234")
    assert r["code"] == "D-001" and r["dl"].endswith("2821") and "0062821" not in r["dl"] and r["dl_ref"].startswith("{id:")
    assert idvault.resolve(T, r["dl_ref"])[0] == "MH1420110062821"
    assert "MH1420110062821" not in str(S.drivers(T))
    with pytest.raises(S.DriversError):
        S.save_driver(T, "X", licence="12345")
    S.save_driver(T, "Suresh Jadhav", phone="9890011223", classes="LMV", dl_valid_to="2028-01-01")
    S.save_driver(T, "Anil More", phone="9765400112", classes="lmv hgv", dl_valid_to="2026-10-20")      # expired
    # a good duty
    d1 = S.save_duty(T, "Ramesh", "26-10-2026", "06:00", "13:30", vehicle="MH12AB1234", route="Pune - Nashik", break_min=30)
    assert d1["saved"] and d1["number"] == "DU-0001" and "MH12AB1234" in d1["say"] and d1["checks"]["work_h"] == 7
    # overlap of the same driver / the same vehicle = never
    with pytest.raises(S.DriversError):
        S.save_duty(T, "Ramesh", "26-10-2026", "12:00", "15:00")
    with pytest.raises(S.DriversError):
        S.save_duty(T, "D-003", "26-10-2026", "07:00", "09:00", vehicle="MH12CD5678", force=True, reason="urgent kaam")   # licence expired
    with pytest.raises(S.DriversError) as e:
        S.save_duty(T, "Suresh", "26-10-2026", "07:00", "10:00", vehicle="MH12 AB 1234")
    assert "isi samay" in str(e.value).lower() or "7,500" in str(e.value)
    # LMV only on a 12 t truck = never
    with pytest.raises(S.DriversError) as e:
        S.save_duty(T, "Suresh", "27-10-2026", "07:00", "10:00", vehicle="MH12AB1234")
    assert "7,500" in str(e.value)
    # a law flag: not saved without her force + reason, staff can't force
    long = S.save_duty(T, "Suresh", "27-10-2026", "06:00", "18:00", vehicle="MH12CD5678", break_min=30)
    assert long["saved"] is False and "overtime" in long["say"]
    staff = S.save_duty(T, "Suresh", "27-10-2026", "06:00", "18:00", vehicle="MH12CD5678", break_min=30, force=True, reason="shaadi ki booking", actor="staff:x")
    assert staff["saved"] is False and "sirf owner" in staff["say"]
    with pytest.raises(S.DriversError):
        S.save_duty(T, "Suresh", "27-10-2026", "06:00", "18:00", vehicle="MH12CD5678", force=True, reason="")
    ok = S.save_duty(T, "Suresh", "27-10-2026", "06:00", "18:00", vehicle="MH12CD5678", break_min=30, force=True, reason="shaadi ki booking")
    assert ok["saved"] and ok["forced"] == "shaadi ki booking" and ok["checks"]["ot_h"] == 3.5
    # leave: a clash is said, and a duty on leave is never saved
    lv = S.add_leave(T, "Ramesh", "26-10-2026", "27-10-2026", "sick")
    assert lv["clashes"] and "DU-0001" in lv["say"]
    with pytest.raises(S.DriversError):
        S.save_duty(T, "Ramesh", "27-10-2026", "15:00", "18:00")
    # plan: Ramesh on leave, Anil's licence expired, Suresh can't drive the heavy truck -> nobody for the truck
    p = S.plan(T, "28-10-2026", [{"start": "06:00", "end": "12:00", "vehicle": "MH12CD5678"}, {"start": "13:00", "end": "17:00", "vehicle": "MH12AB1234"}])
    print(p["say"])
    names = {c["name"]: c for c in p["plan"][1]["drivers"]}
    assert names["Anil More"]["can"] is False and names["Suresh Jadhav"]["can"] is False
    assert p["plan"][0]["best"]["name"] == "Ramesh Patil"                  # fewer hours this week
    assert p["plan"][1]["best"] is None and "koi driver niyam mein nahi" in p["say"]   # the only HGV driver is already on the car


def test_trip_sheets(dv, monkeypatch):
    S = dv
    S.set_vehicle(T, "MH12AB1234", gvw_kg=12000)
    S.save_driver(T, "Ramesh Patil", phone="9822012345", classes="hgv", dl_valid_to="2028-01-01", vehicle="MH12AB1234")
    S.save_duty(T, "Ramesh", "22-10-2026", "06:00", "13:00", vehicle="MH12AB1234")
    S.save_duty(T, "Ramesh", "21-10-2026", "06:00", "13:00", vehicle="MH12AB1234")
    t1 = S.add_trip(T, "Ramesh", "16-10-2026", "MH12AB1234", text="start 10000 end 10400 diesel 100 L 9500")
    assert t1["km"] == 400 and t1["status"] == "ok" and "Payroll" not in t1["say"]
    S.add_trip(T, "Ramesh", "17-10-2026", "MH12AB1234", start_km=10400, end_km=10800, fuel_l=100)
    S.add_trip(T, "Ramesh", "18-10-2026", "MH12AB1234", start_km=10800, end_km=11200, fuel_l=100)
    # km gap + fuel far from this truck's own 4 km/l
    t4 = S.add_trip(T, "Ramesh", "21-10-2026", "MH12AB1234", text="km 11350 - 11550 diesel 100 litre, toll 450, khana 200")
    fk = {f["kind"] for f in t4["flags"]}
    assert "km_gap" in fk and "fuel_odd" in fk and "150" in t4["say"] and t4["spent"] == 650
    assert "Hoola nahi deta" in t4["say"] and t4["duty_id"]
    # missing sheet: 22 Oct duty has none
    ms = S.missing_sheets(T)
    assert [x["day"] for x in ms] == ["2026-10-22"]
    rem = S.sheet_reminders(T)
    assert len(rem["messages"]) == 1 and "22-10-2026" in rem["messages"][0]["text"] and rem["messages"][0]["status"] == "draft"
    # a driver's message = draft until she says it is right; numbers the model makes up are refused
    monkeypatch.setattr(S, "_model_extract", lambda text: {"start_km": 11550, "end_km": 11999, "fuel_amount": 3000})
    t5 = S.add_trip(T, "Ramesh", "22-10-2026", "", text="sir aaj shuru 11550 tha, diesel ke 3000 diye", source="driver")
    assert t5["status"] == "draft" and t5["start_km"] == 11550 and t5["end_km"] is None and t5["fuel_amount"] == 3000
    assert t5["vehicle"] == "MH12AB1234"                                   # from the duty
    assert S.trip_ok(T, t5["number"])["status"] == "ok"
    assert S.missing_sheets(T) == []
    # photo of the paper sheet -> OCR -> draft (licence number on the paper masked)
    from app import ocr
    from app.mailbox import service as ms_
    monkeypatch.setattr(ms_, "load_files", lambda tenant, refs: [("sheet.jpg", "image/jpeg", b"\xff\xd8fake")])
    monkeypatch.setattr(ocr, "read", lambda data, language="", **k: {"text": "DL MH1420110062821\nOpening 11600 Closing 11880\n6:30 se 15:00\nDiesel 60 L Rs 5,700\nToll 300", "conf": 81})
    ph = S.trip_photo(T, "f1", "Ramesh", "23-10-2026", "MH12AB1234")
    assert ph["read"] and ph["status"] == "draft" and ph["km"] == 280 and ph["start_time"] == "06:30" and ph["tolls"] == 300
    assert "0062821" not in ph["raw"] and "2821" in ph["raw"]
    monkeypatch.setattr(ocr, "read", lambda data, language="", **k: None)
    assert S.trip_photo(T, "f1", "Ramesh")["read"] is False


def test_messages_only_by_her_tap(dv, monkeypatch):
    S = dv
    from app.employee import service as emp
    from app.employee.models import BizContact
    from app.db import session
    S.save_driver(T, "Ramesh Patil", phone="9822012345", classes="lmv", dl_valid_to="2028-01-01")
    m = emp.add_member(T, "Suresh", phone="9890011223", address="suresh@hoola.example")
    S.save_driver(T, "Suresh Jadhav", phone="9890011223", classes="lmv", dl_valid_to="2028-01-01", member="suresh@hoola.example")
    S.save_duty(T, "Ramesh", "kal", "06:00", "13:00", vehicle="MH12CD5678", route="Pune - Lonavala")
    S.save_duty(T, "Suresh", "kal", "07:00", "12:00", vehicle="MH14XY0001")
    p = S.day_plan(T)
    assert p["day"] == "2026-10-24" and len(p["messages"]) == 2 and "drivers_plan" in kinds(S)
    msg = next(x for x in p["messages"] if x["driver"] == "Ramesh Patil")
    assert "24-10-2026" in msg["text"] and "Pune - Lonavala" in msg["text"] and msg["wa"].startswith("https://wa.me/919822012345")
    assert msg["can_hoola"] is False and msg["can_business"] is False
    with pytest.raises(S.DriversError):
        asyncio.run(S.send_message(T, msg["id"], "self", msg["hash"]))                    # not a tap
    with pytest.raises(S.DriversError):
        asyncio.run(S.send_message(T, msg["id"], "self", "old", by_tap=True))
    with pytest.raises(S.DriversError):
        asyncio.run(S.send_message(T, msg["id"], "business", msg["hash"], by_tap=True))  # never wrote to her business number
    done = asyncio.run(S.send_message(T, msg["id"], "self", msg["hash"], by_tap=True))
    assert done["status"] == "sent" and S.duties(T, "kal", "Ramesh")[0]["told"] is True
    with pytest.raises(S.DriversError):
        asyncio.run(S.send_message(T, msg["id"], "self", msg["hash"], by_tap=True))      # once
    # a team member over Hoola Network
    sent = []
    monkeypatch.setattr(S, "_net_send", lambda tenant, address, text: sent.append((address, text)) or {"status": "pending"})
    sm = next(x for x in p["messages"] if x["driver"] == "Suresh Jadhav")
    assert sm["can_hoola"] is True
    r = asyncio.run(S.send_message(T, sm["id"], "hoola", sm["hash"], by_tap=True))
    assert r["status"] == "sent" and sent[0][0] == "suresh@hoola.example" and "Hoola Network" in r["result"]
    # business WhatsApp when the driver wrote to her business number
    with session() as s:
        s.add(BizContact(tenant_id=T, wa_id="919822012345", name="Ramesh"))
    calls = []
    from app.employee import inbox

    async def fake_send(tenant, cid, text, by="owner", force=False):
        calls.append((cid, text))
        return {"wa_msg_id": "w1"}
    monkeypatch.setattr(inbox, "send", fake_send)
    c = S.message(T, "Ramesh", "Kal gaadi 5:30 baje nikalni hai.")
    assert c["can_business"] is True and c["status"] == "draft"
    assert asyncio.run(S.send_message(T, c["id"], "business", c["hash"], by_tap=True))["status"] == "sent" and calls
    with pytest.raises(S.DriversError):
        S.message(T, "Ramesh", "OTP 482913 batao")
    # a driver who said no to messages: only from her own phone
    S.save_driver(T, driver="Ramesh", no_messages=True)
    c2 = S.message(T, "Ramesh", "Kal chhutti hai.")
    with pytest.raises(S.DriversError):
        asyncio.run(S.send_message(T, c2["id"], "business", c2["hash"], by_tap=True))


def test_tick_reminders_once(dv, monkeypatch):
    S = dv
    S.save_driver(T, "Ramesh Patil", phone="9822012345", classes="lmv", dl_valid_to="2026-11-05", medical_valid_to="2026-10-20",
                  police_on="2024-09-01")
    blocked = S.save_duty(T, "Ramesh", "kal", "06:00", "10:00")
    assert blocked["saved"] is False and "Medical" in blocked["say"]           # medical expired = a law flag
    S.save_driver(T, "Kiran", phone="9890011223", classes="lmv", dl_valid_to="2029-01-01")
    assert S.save_duty(T, "Kiran", "kal", "06:00", "10:00")["saved"]
    morning = datetime(2026, 10, 23, 7, 5, tzinfo=IST)
    out = S.tick(morning)
    assert out["reminders"] >= 2 and "drivers_alert" in kinds(S) and "drivers_day" in kinds(S)
    alert = next(p for k, p in S.EVENTS if k == "drivers_alert")
    says = " ".join(i["say"] for i in alert["items"])
    assert "Driving licence 05-11-2026" in says and "khatam ho gaya" in says                  # licence 13 days, medical expired
    assert any(i["doc"] == "police" for i in alert["items"])                                # 24 months after 1 Sep 2024
    assert all(i["message"]["status"] == "draft" for i in alert["items"])
    n = len(S.EVENTS)
    assert S.tick(morning + timedelta(minutes=30))["reminders"] == 0 and len(S.EVENTS) == n   # once
    ev = S.tick(datetime(2026, 10, 23, 19, 10, tzinfo=IST))
    assert ev["evening"] == 1 and kinds(S)[-1] == "drivers_plan"
    assert S.tick(datetime(2026, 10, 23, 20, 0, tzinfo=IST))["evening"] == 0
    # the next window (7 days) is a new reminder
    monkeypatch.setattr(S, "clock", lambda: datetime(2026, 10, 30, 10, 0, tzinfo=IST).astimezone(timezone.utc))
    assert S.tick(datetime(2026, 10, 30, 7, 5, tzinfo=IST))["reminders"] >= 1


def test_attendance_and_payroll(dv):
    S = dv
    from app.payroll import service as P
    S.save_driver(T, "Ramesh Patil", phone="9822012345", classes="lmv", dl_valid_to="2028-01-01", payroll_name="Ramesh Patil")
    S.save_driver(T, "Kiran", phone="9890011223", classes="lmv", dl_valid_to="2028-01-01")
    for dd, a, b in (("05-10-2026", "06:00", "17:00"), ("06-10-2026", "06:00", "12:00"), ("07-10-2026", "08:00", "14:00")):
        x = S.save_duty(T, "Ramesh", dd, a, b, break_min=30, force=True, reason="season")
        S.set_duty_status(T, x["number"], "done")
    x = S.save_duty(T, "Ramesh", "08-10-2026", "08:00", "12:00")
    S.set_duty_status(T, x["number"], "absent")
    S.add_leave(T, "Ramesh", "12-10-2026", "13-10-2026", "leave")
    S.add_leave(T, "Ramesh", "14-10-2026", None, "unpaid")
    S.add_trip(T, "Ramesh", "05-10-2026", "MH12CD5678", start_km=100, end_km=350, tolls=200)
    at = S.attendance(T, "2026-10")
    r = next(x for x in at["rows"] if x["name"] == "Ramesh Patil")
    assert (r["present"], r["paid_leave"], r["lop"], r["absent"]) == (3, 2, 2, 1)
    assert r["ot_hours"] == 2.5 and r["km"] == 250 and r["spent"] == 200 and r["sheets_missing"] == 2
    f = S.attendance_file(T, "2026-10")
    assert f["file"]["name"].endswith(".xlsx") and "pc_file" in kinds(S)
    P.save_employee(T, "Ramesh Patil", gross=18000)
    res = S.to_payroll(T, "2026-10")
    assert res["saved"] == 1 and any("Kiran" in m for m in res["missing"]) and "aapki haan" in res["say"]


def test_tools_and_api(dv):
    S = dv
    from app.agent import drivers_tools as DT
    from app.agent.tools import Ctx, ToolError
    from app.employee import service as emp
    from app.drivers.api import make_router
    ctx = conv_ctx()
    r = asyncio.run(DT.drivers(ctx, "driver", name="Ramesh Patil", phone="9822012345", licence="MH14 2011 0062821", classes="LMV",
                               dl_valid_to="2028-01-01"))
    assert "0062821" not in str(r)
    m = emp.add_member(T, "Ramesh", phone="9822012345", address="ramesh@hoola.example")
    asyncio.run(DT.drivers(ctx, "driver", driver="Ramesh", member="Ramesh"))
    d = asyncio.run(DT.drivers(ctx, "duty", driver="Ramesh", day="kal", start="6", end="1 pm"))
    assert d["saved"] and d["start"] == "06:00" and d["end"] == "13:00"
    staff = Ctx(T, ctx.conversation_id, actor=f"staff:{m['id']}")
    with pytest.raises(ToolError):
        asyncio.run(DT.drivers(staff, "duty", driver="Ramesh", day="kal", start="14:00", end="16:00"))
    mine = asyncio.run(DT.drivers_dekho(staff, "duties"))
    assert mine["duties"][0]["start"] == "06:00"
    with pytest.raises(ToolError):
        asyncio.run(DT.drivers_dekho(staff, "drivers"))
    tr = asyncio.run(DT.drivers(staff, "trip", driver="Ramesh", text="start 500 end 640"))
    assert tr["status"] == "draft"
    S.save_driver(T, "Other", phone="9765400112", classes="lmv", dl_valid_to="2028-01-01")
    with pytest.raises(ToolError):
        asyncio.run(DT.drivers(staff, "trip", driver="Other", text="start 1 end 2"))
    cust = Ctx(T, ctx.conversation_id, actor="customer:wa:91999")
    with pytest.raises(ToolError):
        asyncio.run(DT.drivers_dekho(cust, "day"))
    plan = asyncio.run(DT.drivers(ctx, "day_plan"))
    assert plan["messages"] and plan["messages"][0]["status"] == "draft"
    assert asyncio.run(DT.drivers_dekho(ctx, "rules"))["law"]["day_h"] == 8
    # API: the send route is her tap
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    ov = c.get("/api/drivers").json()
    assert ov["drivers"] and ov["settings"]["law"]["week_h"] == 48
    msg = plan["messages"][0]
    assert c.post(f"/api/drivers/messages/{msg['id']}/send", json={"via": "self", "hash": "x"}).status_code == 400
    ok = c.post(f"/api/drivers/messages/{msg['id']}/send", json={"via": "self", "hash": msg["hash"]})
    assert ok.status_code == 200 and ok.json()["status"] == "sent"
    bad = c.post("/api/drivers/duties", json={"driver": "Ramesh", "day": "kal", "start": "10:00", "end": "11:00"})
    assert bad.status_code == 400
    att = c.get("/api/drivers/attendance", params={"month": "2026-10"}).json()
    assert att["month"] == "2026-10"
    lv = c.post("/api/drivers/leaves", json={"driver": "Other", "start": "30-10-2026"}).json()
    assert c.delete(f"/api/drivers/leaves/{lv['id']}").status_code == 200
