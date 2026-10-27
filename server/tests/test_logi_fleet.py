"""Fleet Sahayak: registration numbers + document rules, vehicles with their papers, reminders once per window, fuel km/l
(tank-to-tank) + theft / leak signals + fuel-card import, service schedule, tyres, breakdowns, challans, spends that ONLY her tap
(fingerprint once a phone key is active) approves, trips with load fit / split / papers / estimate from her rates, Maps distance,
cost per km, idle days, morning note, tools (staff / customer actors) and API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.fleet.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def fl(env, monkeypatch):
    from app.fleet import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_maps_distance", lambda *a, **k: None)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules():
    from app.fleet import rules as R
    assert R.reg_check("mh-30-ab-1234")["reg"] == "MH 30 AB 1234"
    assert R.reg_check("MH12 1")["ok"] and R.reg_check("22 BH 1234 AA")["bh"]
    assert not R.reg_check("XX 12 AB 1234")["ok"] and not R.reg_check("hello")["ok"] and not R.reg_check("MH 00 AB 1234")["ok"]
    assert R.type_of("Tata 407 tempo") == "tempo" and R.type_of("12 wheel truck") == "truck" and R.type_of("school bus") == "bus"
    assert R.doc_kind("PUC") == "puc" and R.doc_kind("national permit") == "national_permit" and R.doc_kind("bima") == "insurance"
    assert R.doc_kind("fitness") == "fitness" and R.doc_kind("AIS 140 GPS") == "ais140"
    assert "fitness" in R.required_docs("truck") and "national_permit" in R.required_docs("truck", national=True)
    assert "fitness" not in R.required_docs("car") and "ais140" in R.required_docs("bus")
    on = date(2026, 10, 23)
    assert R.fitness_months(date(2022, 1, 1), on) == 24 and R.fitness_months(date(2015, 1, 1), on) == 12
    assert R.suggest_expiry("fitness", date(2026, 10, 1), date(2015, 1, 1)) == date(2027, 9, 30)
    assert R.suggest_expiry("rc", date(2026, 1, 1)) is None
    st = R.doc_state(date(2026, 11, 5), on, [30, 15, 7, 1, 0])
    assert st["state"] == "due" and st["days_left"] == 13 and st["window"] == 15
    assert R.doc_state(date(2026, 10, 1), on, [30])["state"] == "expired" and R.doc_state(None, on, [30])["state"] == "missing"
    ser = R.kmpl_series([{"id": "a", "odo": 1000, "litres": 100, "full": True}, {"id": "b", "odo": 1200, "litres": 20, "full": False},
                         {"id": "c", "odo": 1500, "litres": 80, "full": True}])
    assert ser == [{"id": "c", "km": 500, "litres": 100.0, "kmpl": 5.0}]
    fl = R.fuel_flags({"odo": 900, "litres": 300, "amount": 33000}, 1000, [5.0, 5.2, 4.9, 5.1], 3.0, 250, [92, 93, 92.5])
    assert {"odo_back", "over_tank", "low_kmpl", "price"} <= {f["id"] for f in fl}
    assert R.service_due({"km": 10000, "months": 6, "last_km": 50000, "last_on": date(2026, 4, 1)}, 59500, on)["state"] == "late"
    assert R.service_due({"km": 10000, "last_km": 50000}, 52000, on)["state"] == "ok"
    v = {"reg": "T1", "capacity_t": 9, "capacity_cbm": 40, "body_l": 6, "body_w": 2.4, "body_h": 2.4}
    ok = R.load_fit([{"name": "cement", "weight_kg": 50, "cbm": 0.04, "count": 160}], v)
    assert ok["fits"] and ok["weight_kg"] == 8000
    over = R.load_fit([{"name": "steel", "weight_kg": 10000}], v)
    assert not over["fits"] and "zyada" in over["problems"][0]
    long = R.load_fit([{"name": "pipe", "weight_kg": 500, "dims": [7, 0.3, 0.3]}], v)
    assert not long["fits"] and "body" in long["problems"][0]
    nowt = R.load_fit([{"name": "boxes", "cbm": 2}], v)
    assert not nowt["fits"] and "wazan" in nowt["problems"][0]
    sp = R.split_load([{"name": "bags", "weight_kg": 1000, "count": 12}], [{"reg": "A", "capacity_t": 9}, {"reg": "B", "capacity_t": 4}])
    assert sum(p["weight_kg"] for p in sp["plan"]) == 12000 and not sp["left"]
    est = R.trip_estimate(300, 5, 92, toll=1200)
    assert est["fuel_l"] == 60 and est["fuel_rs"] == 5520 and est["total_rs"] == 6720
    miss = R.trip_estimate(300, 5, None)
    assert miss["total_rs"] is None and "aapka diesel rate" in miss["missing"]
    assert "8 ghante" in R.drive_hours_note(10) and R.drive_hours_note(5) == ""


def test_vehicle_docs_and_reminders(fl, monkeypatch):
    S = fl
    S.save_settings(T, business="Ingle Transport", home_state="MH", diesel_rate=92.5, morning_time="08:00")
    with pytest.raises(S.FleetError):
        S.save_vehicle(T, "XX 12 AB 1234")
    out = S.save_vehicle(T, "mh30ab1234", type="truck", make="Tata", model="1612", capacity_t=9, capacity_cbm=40,
                         body={"l": 6, "w": 2.4, "h": 2.4}, tank_l=250, reg_date="2016-04-01", national=True, odo=150000)
    v = out["vehicle"]
    assert out["new"] and v["reg"] == "MH 30 AB 1234" and "kaagazon ki expiry" in out["say"]
    kinds_ = {d["kind"] for d in v["docs"]}
    assert {"rc", "insurance", "fitness", "puc", "national_permit", "road_tax"} <= kinds_
    assert v["service"] and v["service"][0]["state"] == "unknown"
    again = S.save_vehicle(T, "MH 30 AB 1234", driver="Ramesh")
    assert not again["new"]
    with pytest.raises(S.FleetError):
        S.save_vehicle(T, "", "1234", odo=100)                   # odometer can't go back without odo_reset
    # papers
    on = S.today(T)
    S.save_doc(T, "1234", "insurance", (on + timedelta(days=12)).isoformat(), number="POL/1")
    S.save_doc(T, "1234", "puc", (on - timedelta(days=2)).isoformat())
    g = S.save_doc(T, "1234", "fitness", issued=(on - timedelta(days=10)).isoformat())
    assert g["doc"]["guess"] and "andaaza" in g["say"]           # 2016 truck -> 12 months, suggestion only
    with pytest.raises(S.FleetError):
        S.save_doc(T, "1234", "puc", "31-02-2026")
    due = S.docs_due(T)
    assert due[0]["kind"] == "puc" and due[0]["state"] == "expired"
    assert any(d["kind"] == "insurance" and d["window"] == 15 for d in due)
    # reminders once per window
    n = datetime.now(timezone.utc)
    r1 = S.tick(n)
    assert r1["docs"] >= 2 and "fleet_alert" in kinds(S)
    r2 = S.tick(n + timedelta(minutes=1))
    assert r2["docs"] == 0
    steps = S.official_steps("echallan")
    assert "echallan.parivahan.gov.in" in steps["steps"][0]


def _truck(S, reg="MH 30 AB 1234", **kw):
    base = dict(type="truck", capacity_t=9, capacity_cbm=40, body={"l": 6, "w": 2.4, "h": 2.4}, tank_l=250, reg_date="2021-01-01")
    base.update(kw)
    v = S.save_vehicle(T, reg, **base)["vehicle"]
    on = S.today(T)
    for k in ("insurance", "fitness", "puc", "road_tax", "rc", "state_permit", "national_permit"):
        S.save_doc(T, v["id"], k, (on + timedelta(days=300)).isoformat())
    return v


def test_fuel_kmpl_signals_and_import(fl):
    S = fl
    _truck(S)
    on = S.today(T)
    d = lambda k: (on - timedelta(days=k)).isoformat()                # noqa: E731
    S.add_fuel(T, "1234", 200, 18500, 100000, d(10))
    for i, odo in enumerate((101000, 102000, 103000, 104000), start=1):
        r = S.add_fuel(T, "1234", 200, 18500, odo, d(10 - i * 2))
    assert r["fuel"]["kmpl"] == 5.0 and not r["flags"]
    bad = S.add_fuel(T, "1234", 200, 18500, 104600, d(0))              # 600 km on 200 L = 3 km/l
    assert any(f["id"] == "low_kmpl" for f in bad["flags"]) and "fleet_alert" in kinds(S)
    assert S.add_fuel(T, "1234", 200, 18500, 104600, d(0))["duplicate"]
    with pytest.raises(S.FleetError):
        S.add_fuel(T, "1234", 0)
    csv_text = ("Fuel Card Statement\n,,\nTxn Date,Vehicle No,Product,Quantity (Ltrs),Amount (Rs),Odometer,Txn ID,Retail Outlet\n"
                f"{(on - timedelta(days=1)).strftime('%d/%m/%Y')},MH30AB1234,HSD,100,9250,105100,TX1,Akola HP\n"
                f"{(on - timedelta(days=1)).strftime('%d/%m/%Y')},MH30AB1234,Lube Oil,5,1500,,TX2,Akola HP\n"
                f"{on.strftime('%d/%m/%Y')},MH30AB1234,HSD,100,9250,105600,TX3,Akola HP\n"
                f"{on.strftime('%d/%m/%Y')},MH99ZZ9999,HSD,50,4600,,TX4,X\n")
    imp = S.import_fuel(T, data=csv_text.encode(), name="card.csv")
    assert imp["added"] == 2 and len(imp["problems"]) == 1           # lube skipped, unknown vehicle reported
    again = S.import_fuel(T, data=csv_text.encode(), name="card.csv")
    assert again["added"] == 0 and again["duplicates"] == 2
    rep = S.fuel_report(T, "1234")
    assert rep["vehicles"][0]["usual_kmpl"] and rep["vehicles"][0]["fills"] >= 7
    with pytest.raises(S.FleetError):
        S.import_fuel(T, data=b"a,b\n1,2\n", name="x.csv")


def test_service_tyres_breakdown_challan_and_spend_tap(fl, monkeypatch):
    S = fl
    _truck(S, odo=60000)
    sv = S.service_set(T, "1234", "Engine oil + filter", every_km=20000, every_months=6, last_km=41000,
                       last_on=(S.today(T) - timedelta(days=30)).isoformat())
    assert sv["item"]["state"] in ("due", "late") and not sv["item"]["starter"]
    r = S.tick(datetime.now(timezone.utc))
    assert r["service"] >= 1
    # spend card: the tool path can never approve
    sp = S.spend_request(T, "1234", "service", "Engine oil + filter (Sai Motors)", 6500, vendor="Sai Motors", actor="staff:x")
    x = sp["spend"]
    assert sp["status"] == "needs_tap" and x["number"] == "FS-0001" and "fleet_spend" in kinds(S) and "Hoola khud paise nahi" in sp["say"]
    assert S.spend_request(T, "1234", "service", "Engine oil + filter (Sai Motors)", 6500)["existing"]
    with pytest.raises(S.FleetError):
        S.spend_request(T, "1234", "tyre", "2 naye tyre", None)        # no invented amount
    with pytest.raises(S.FleetError):
        S.decide_spend(T, x["id"], True, x["hash"])                    # no by_tap
    with pytest.raises(S.FleetError):
        S.decide_spend(T, x["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.FleetError):
        S.spend_done(T, x["id"], 6500)                                 # not approved yet
    # fingerprint once a phone key is active
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.FleetError) as e:
        S.decide_spend(T, x["id"], True, x["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    monkeypatch.setattr(S, "_verify_fingerprint", lambda *a, **k: None)
    d = S.decide_spend(T, x["id"], True, x["hash"], by_tap=True)
    assert d["spend"]["status"] == "approved" and "khud dijiye" in d["say"]
    assert S.decide_spend(T, x["id"], False, x["hash"], by_tap=True)["spend"]["status"] == "approved"   # decided once
    done = S.spend_done(T, x["id"], 6400, ref="UPI 1234")
    assert done["spend"]["status"] == "done"
    S.service_done(T, "1234", ["engine oil"], odo=60100, amount=6400, spend=x["id"])
    assert [i for i in S.vehicle_view(T, "1234")["service"] if i["item"].startswith("Engine")][0]["state"] == "ok"
    # tyres
    S.tyre(T, "1234", "fit", "front-left", "MRF", "SN1", odo=10000, life_km=60000)
    S.tyre(T, "1234", "fit", "front-left", "Apollo", "SN2", odo=60100, life_km=60000)
    ty = S.vehicle_view(T, "1234")["tyres"]
    assert [t["status"] for t in ty].count("fitted") == 1 and any(t["status"] == "removed" and t["km_run"] == 50100 for t in ty)
    # breakdowns repeat
    for i in range(3):
        b = S.breakdown(T, "1234", "clutch plate", "Nagpur highway", hours=6, actor="staff:x")
    assert b["repeat"] == 3 and "badi marammat" in b["say"] and S.vehicle_view(T, "1234")["status"] == "workshop"
    S.event_close(T, b["event"]["id"], 3200)
    assert S.vehicle_view(T, "1234")["status"] == "active"
    # challan -> spend card -> her tap -> paid
    c = S.challan(T, "1234", "MH123456789", 2000, offence="Overload s.194")
    assert "Overload" in c["say"] and S.challan(T, "1234", "MH123456789", 2000)["duplicate"]
    cs = S.spend_request(T, "1234", "challan", "Challan MH123456789", 2500, link_id=c["event"]["id"])["spend"]
    assert any("2,000" in ch for ch in cs["checks"])
    S.decide_spend(T, cs["id"], True, cs["hash"], by_tap=True)
    S.spend_done(T, cs["id"], 2000)
    ev = [e for e in S.vehicle_view(T, "1234")["events"] if e["kind"] == "challan"][0]
    assert ev["status"] == "paid"
    rej = S.spend_request(T, "1234", "tyre", "Stepney", 9000)["spend"]
    assert S.decide_spend(T, rej["id"], False, rej["hash"], "abhi nahi", by_tap=True)["spend"]["status"] == "rejected"


def test_trips_loads_and_estimates(fl, monkeypatch):
    S = fl
    S.save_settings(T, home_state="MH", diesel_rate=92, avg_speed=40)
    _truck(S, "MH 30 AB 1234", capacity_t=9, national=False)
    _truck(S, "MH 30 CD 5678", type="tempo", capacity_t=2.5, capacity_cbm=14, body={"l": 3, "w": 1.8, "h": 1.8})
    on = S.today(T)
    for i, odo in enumerate((1000, 2000, 3000, 4000)):
        S.add_fuel(T, "1234", 200, 18400, odo, (on - timedelta(days=8 - i)).isoformat())
    items = [{"name": "cement bags", "weight_kg": 50, "cbm": 0.04, "count": 100}]   # 5 t
    out = S.plan_trip(T, "Akola", "Indore", on.isoformat(), items=items, km=360, toll=1800, dest_state="MP")
    tr = out["trip"]
    assert tr["number"] == "TR-0001" and tr["status"] == "planned" and "fleet_trip" in kinds(S)
    assert tr["checks"]["suggest"][0]["vehicle"] == "MH 30 AB 1234"        # tempo too small
    a = S.assign_trip(T, "1", vehicle="1234", driver="Ramesh", driver_phone="98220 12345")["trip"]
    assert a["status"] == "assigned" and a["driver_phone"] == "9822012345"
    assert any("national permit" in w for w in a["checks"]["warn"])          # MH -> MP goods without NP
    assert any("8 ghante" in w for w in a["checks"]["warn"])                 # 360 km at her 40 km/h
    est = a["estimate"]
    assert est["fuel_l"] == 72 and est["fuel_rs"] == 6624 and est["total_rs"] == 8424
    # same truck same day = busy
    b = S.plan_trip(T, "Akola", "Amravati", on.isoformat(), items=[{"name": "x", "weight_kg": 100}], vehicle="1234", km=100)["trip"]
    assert b["status"] == "planned" and any("doosri trip" in x for x in b["checks"]["block"])
    # overload never assigned; split suggestion
    big = S.plan_trip(T, "Akola", "Pune", (on + timedelta(days=1)).isoformat(),
                      items=[{"name": "steel coils", "weight_kg": 1000, "count": 11}], vehicle="1234", km=550)
    bt = big["trip"]
    assert bt["status"] == "planned" and any("zyada" in x for x in bt["checks"]["block"]) and bt["checks"]["split"]["plan"]
    # expired insurance blocks
    S.save_doc(T, "5678", "insurance", (on - timedelta(days=1)).isoformat())
    t3 = S.plan_trip(T, "Akola", "Washim", on.isoformat(), items=[{"name": "boxes", "weight_kg": 500}], vehicle="5678", km=80)["trip"]
    assert t3["status"] == "planned" and any("Insurance" in x for x in t3["checks"]["block"])
    with pytest.raises(S.FleetError):
        S.trip_status(T, t3["number"], "started")
    # start / done updates odometer
    S.trip_status(T, a["number"], "started", odo=4000)
    dn = S.trip_status(T, a["number"], "done", odo=4330)
    assert "330 km" in dn["say"] and S.vehicle_view(T, "1234")["odo"] == 4330
    with pytest.raises(S.FleetError):
        S.plan_trip(T, "Akola", "Pune", (on - timedelta(days=2)).isoformat())
    lc = S.load_check(T, [{"name": "bags", "weight_kg": 50, "count": 40}])
    assert lc["results"] and "MH 30" in lc["say"]
    # Maps distance when available (fake)
    monkeypatch.setattr(S, "_maps_distance", lambda *a, **k: (412.4, 480))
    m = S.plan_trip(T, "Akola", "Nagpur", (on + timedelta(days=2)).isoformat(), items=[{"name": "b", "weight_kg": 100}])["trip"]
    assert m["km"] == 412.4 and m["km_source"] == "maps" and m["duration_min"] == 480


def test_cost_idle_day_and_morning(fl):
    S = fl
    S.save_settings(T, morning_time="00:00", idle_days=3)
    _truck(S)
    _truck(S, "MH 30 EF 1111")
    on = S.today(T)
    S.add_fuel(T, "1234", 100, 9200, 5000, (on - timedelta(days=5)).isoformat())
    S.add_fuel(T, "1234", 100, 9200, 5500, (on - timedelta(days=1)).isoformat())
    S.expense(T, "1234", "Washing", 300)
    c = S.cost_report(T, "1234")
    v = c["vehicles"][0]
    assert v["km"] == 500 and v["total"] == 18700 and v["per_km"] == 37.4
    with S.session() as s:          # the second truck was added long ago and never ran
        from app.fleet.models import FleetVehicle
        x = s.query(FleetVehicle).filter_by(reg="MH 30 EF 1111").one()
        x.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    assert [i["vehicle"] for i in S.idle(T)] == ["MH 30 EF 1111"]
    d = S.day(T)
    assert "Khadi gaadiyan" in d["say"]
    S.EVENTS.clear()
    r = S.tick(datetime.now(timezone.utc))
    assert r["morning"] == 1 and "fleet_day" in kinds(S)
    assert S.tick(datetime.now(timezone.utc))["morning"] == 0


def test_tools_actors_and_api(fl, monkeypatch):
    from app.agent import fleet_tools as FT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    out = asyncio.run(FT.fleet(ctx, "vehicle", reg="MH 30 AB 1234", type="truck", capacity_t=9))
    assert out["new"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    with pytest.raises(ToolError):
        asyncio.run(FT.fleet(staff, "vehicle", reg="MH 30 XY 1000"))
    with pytest.raises(ToolError):
        asyncio.run(FT.fleet(Ctx(T, ctx.conversation_id, actor="customer:wa:1"), "fuel", vehicle="1234", litres=10))
    f = asyncio.run(FT.fleet(staff, "fuel", vehicle="1234", litres=50, amount=4600, odo=1000))
    assert f["fuel"]["by"]
    sp = asyncio.run(FT.fleet(staff, "spend", vehicle="1234", kind="tyre", what="2 tyre", amount=24000))
    assert sp["status"] == "needs_tap"
    with pytest.raises(ToolError):
        asyncio.run(FT.fleet(staff, "spend_done", spend=sp["spend"]["id"]))
    rd = asyncio.run(FT.fleet_dekho(ctx, "rules"))
    assert rd["never"] and rd["sources"]
    assert asyncio.run(FT.fleet_dekho(ctx, "steps", step="vahan"))["steps"]
    names = {t["name"] for t in FT.FLEET_TOOLS}
    assert names == set(FT.FLEET_HANDLERS) == set(FT.FLEET_LABELS)
    # API
    from app.fleet.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/fleet").status_code == 200
    r = c.post("/api/fleet/vehicles", json={"reg": "MH 30 CD 5678", "type": "tempo", "capacity_t": 2.5})
    assert r.status_code == 200 and r.json()["vehicle"]["type"] == "tempo"
    assert c.post("/api/fleet/vehicles", json={"reg": "bad"}).status_code == 400
    vid = r.json()["vehicle"]["id"]
    assert c.post(f"/api/fleet/vehicles/{vid}/docs", json={"kind": "puc", "expires": "2027-01-01"}).json()["doc"]["kind"] == "puc"
    x = sp["spend"]
    assert c.post(f"/api/fleet/spends/{x['id']}/decide", json={"hash": x["hash"]}).status_code == 400
    assert c.post(f"/api/fleet/spends/{x['id']}/decide", json={"yes": True, "hash": "nope"}).status_code == 400
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    assert c.post(f"/api/fleet/spends/{x['id']}/decide", json={"yes": True, "hash": x["hash"]}).status_code == 428
    ch = c.post(f"/api/fleet/spends/{x['id']}/challenge").json()
    assert ch["message"].startswith("hoola-approve|v1|default|fleet|")
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    ok = c.post(f"/api/fleet/spends/{x['id']}/decide", json={"yes": True, "hash": x["hash"]})
    assert ok.status_code == 200 and ok.json()["spend"]["status"] == "approved"
    assert c.post(f"/api/fleet/spends/{x['id']}/done", json={"amount": 23800}).json()["spend"]["status"] == "done"
    t = c.post("/api/fleet/trips", json={"origin": "Akola", "destination": "Akot", "km": 50, "items": [{"name": "a", "weight_kg": 100}]})
    assert t.status_code == 200 and t.json()["trip"]["number"].startswith("TR-")
    up = c.post("/api/fleet/fuel/import", files={"file": ("f.csv", b"Date,Vehicle No,Litres,Amount\n01/10/2026,MH30CD5678,20,1840\n")})
    assert up.status_code == 200 and up.json()["added"] == 1
    assert c.get("/api/fleet/cost").status_code == 200 and c.get("/api/fleet/steps/echallan").json()["steps"]
