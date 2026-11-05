"""v0.463 Phase 4 wiring: fleet_dekho what=nearest - which FREE truck is closest to a pickup by road time.
A vehicle has no live GPS here, so its position is the last drop of its last FINISHED trip; one without any is
listed as unknown, never guessed."""
import asyncio

import pytest

import app.fleet.models  # noqa: F401
from app import maps
from app.db import session
from app.fleet import service as S
from app.fleet.models import FleetTrip, FleetVehicle
from tests.test_life import conv_ctx

T = "default"
PLACES = {"Nagpur": (21.1, 79.0), "Akola": (20.7, 77.0), "Amravati": (20.9, 77.7), "Pune": (18.5, 73.8)}


@pytest.fixture
def nv(env, monkeypatch):
    calls = []

    async def resolve(text, tenant, near=None):
        p = PLACES.get(str(text))
        return {"name": text, "lat": p[0], "lng": p[1]} if p else None

    async def matrix(origins, dests, mode="DRIVE", language="en-IN", tenant_id=""):
        calls.append((len(origins), len(dests), mode))
        return [[{"ok": True, "distance_km": round(abs(o["lat"] - dests[0]["lat"]) * 100, 1),
                  "duration_min": round(abs(o["lat"] - dests[0]["lat"]) * 100),
                  "duration": "x"}] for o in origins]
    monkeypatch.setattr(maps, "configured", lambda: True)
    monkeypatch.setattr(maps, "resolve", resolve)
    monkeypatch.setattr(maps, "matrix", matrix)
    monkeypatch.setattr(S, "_publish", lambda *a, **k: None)
    return calls


def _veh(reg, cap=10.0, status="active", dropped=None, trip_status="done"):
    with session() as s:
        v = FleetVehicle(tenant_id=T, reg=reg, reg_key=reg.replace(" ", ""), capacity_t=cap, status=status)
        s.add(v); s.flush()
        if dropped:
            s.add(FleetTrip(tenant_id=T, number="TR-" + reg[-4:], origin="x", destination=dropped, day="2020-01-01",
                            vehicle_id=v.id, status=trip_status))
        return v.id


def _ask(*a, **k):
    return S.nearest_vehicle(T, *a, **k)


def test_the_truck_whose_last_drop_is_closest_wins(nv):
    _veh("MH 30 AA 0001", dropped="Pune")
    _veh("MH 30 AA 0002", dropped="Amravati")
    r = _ask("Akola")
    assert r["nearest"]["vehicle"] == "MH 30 AA 0002" and r["nearest"]["last_drop"] == "Amravati"
    assert [x["vehicle"] for x in r["ranked"]] == ["MH 30 AA 0002", "MH 30 AA 0001"]
    assert nv == [(2, 1, "DRIVE")], "one matrix call, trucks x one pickup"


def test_a_truck_with_no_finished_trip_is_listed_unknown_not_guessed(nv):
    _veh("MH 30 AA 0001", dropped="Amravati")
    _veh("MH 30 AA 0002")
    _veh("MH 30 AA 0003", dropped="Amravati", trip_status="started")      # last trip not finished: no position
    r = _ask("Akola")
    assert [x["vehicle"] for x in r["ranked"]] == ["MH 30 AA 0001"]
    assert set(r["no_known_position"]) == {"MH 30 AA 0002", "MH 30 AA 0003"}


def test_workshop_busy_and_too_small_trucks_are_left_out_and_named(nv):
    _veh("MH 30 AA 0001", dropped="Amravati", status="workshop")
    _veh("MH 30 AA 0002", cap=2.0, dropped="Amravati")
    b = _veh("MH 30 AA 0003", dropped="Amravati")
    _veh("MH 30 AA 0004", dropped="Nagpur")
    day = S.today(T).isoformat()
    with session() as s:
        s.add(FleetTrip(tenant_id=T, number="TR-B", origin="a", destination="b", day=day, vehicle_id=b, status="assigned"))
    r = _ask("Akola", load_t=5)
    assert [x["vehicle"] for x in r["ranked"]] == ["MH 30 AA 0004"]
    why = {x["vehicle"]: x["why"] for x in r["skipped"]}
    assert "capacity" in why["MH 30 AA 0002"] and "trip" in why["MH 30 AA 0003"]
    assert "MH 30 AA 0001" not in why, "a workshop truck is not even a candidate"


def test_no_maps_key_or_no_pickup_says_so_instead_of_guessing(nv, monkeypatch):
    with pytest.raises(S.FleetError):
        _ask("")
    monkeypatch.setattr(maps, "configured", lambda: False)
    with pytest.raises(S.FleetError):
        _ask("Akola")


def test_an_unfindable_pickup_is_an_error(nv):
    _veh("MH 30 AA 0001", dropped="Amravati")
    with pytest.raises(S.FleetError):
        _ask("Nowhereville")


def test_the_fleet_tool_reaches_it(nv):
    from app.agent import fleet_tools
    _veh("MH 30 AA 0001", dropped="Amravati")
    r = asyncio.run(fleet_tools.fleet_dekho(conv_ctx(), "nearest", place="Akola"))
    assert r["nearest"]["vehicle"] == "MH 30 AA 0001"
    names = {t["name"]: t for t in fleet_tools.FLEET_TOOLS}
    assert "nearest" in names["fleet_dekho"]["input_schema"]["properties"]["what"]["enum"]
