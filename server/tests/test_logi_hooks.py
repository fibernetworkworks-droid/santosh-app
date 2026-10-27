"""Safar suite cross-module hooks (v0.139): Driver Sahayak reads vehicles from the Fleet Sahayak (fleet.find_vehicle, her own GVW
fills what fleet doesn't keep), Logistics reads courier tracking from the Courier desk (courier.track_awb), and wiring sanity
(tools registered once, customer-safe parcel tools only in the business inbox, approvekey kinds)."""
import httpx
import pytest

import app.courier.models  # noqa: F401
import app.drivers.models  # noqa: F401
import app.fleet.models  # noqa: F401
import app.logistics.models  # noqa: F401
import app.wapsi.models  # noqa: F401
from tests.test_logi_courier import CUST, WH, Fake

T = "default"


def test_drivers_reads_fleet_vehicle(env):
    from app.drivers import service as D
    from app.fleet import service as F
    assert F.find_vehicle(T, "") is None and F.find_vehicle(T, "MH 99 ZZ 0000") is None
    v = F.save_vehicle(T, "mh30ab1234", type="truck", capacity_t=9)["vehicle"]
    got = F.find_vehicle(T, "MH30AB1234")
    assert got["id"] == v["id"] and got["number"] == "MH 30 AB 1234" and got["kind"] == "truck" and got["gvw_kg"] is None
    info = D.vehicle_info(T, "MH 30 AB 1234")
    assert info["from"] == "fleet" and info["fleet_id"] == v["id"] and info["gvw_kg"] is None
    D.set_vehicle(T, "MH30AB1234", gvw_kg=16200)          # her own gross weight: used with the fleet record
    info = D.vehicle_info(T, "", fleet_id=v["id"])
    assert info["from"] == "fleet" and info["gvw_kg"] == 16200 and info["number"] == "MH 30 AB 1234"
    D.set_vehicle(T, "MH12XY9999", gvw_kg=3500, kind="tempo")   # not in fleet -> her light list
    info = D.vehicle_info(T, "MH 12 XY 9999")
    assert info["from"] == "drivers" and info["gvw_kg"] == 3500


@pytest.fixture
def cr(env, monkeypatch, tmp_path):
    from app.courier import carriers as K
    from app.courier import service as S
    from app.wapsi import couriers as wc
    monkeypatch.setenv("COURIER_DIR", str(tmp_path / "courier"))
    monkeypatch.setenv("WAPSI_DIR", str(tmp_path / "wapsi"))
    monkeypatch.setenv("LOGISTICS_DIR", str(tmp_path / "logi"))
    monkeypatch.setattr(K, "_public", lambda url: None)
    fake = Fake()
    wc.set_transport(httpx.MockTransport(fake))
    S.save_settings(T, business="Riya Fashions", warehouse=WH)
    yield S, fake
    wc.set_transport(None)


def test_courier_track_awb_for_logistics(cr):
    S, fake = cr
    with pytest.raises(S.CourierError):
        S.track_awb(T, courier="delhivery", awb="")
    with pytest.raises(S.CourierError) as e:                  # no parcel, no key: her courier's own page, never a guess
        S.track_awb(T, courier="delhivery", awb="999")
    assert "999" in str(e.value)
    # a parcel she booked herself (AWB typed): status from her own record, no carrier call
    S.new_parcel(T, order_ref="ORD-1", customer=CUST, items="Kurti x1 @ 500", payment="prepaid", weight_kg=0.5)
    S.set_awb(T, "P-0001", "MAN123", carrier="Blue Dart")
    r = S.track_awb(T, courier="bluedart", awb="MAN123")
    assert r["status"] == "booked" and r["events"] == []
    # her Shiprocket key, AWB not in her parcels: the carrier's own words
    S.set_keys(T, "shiprocket", {"email": "api@riya.in", "password": "x" * 10, "pickup_location": "Akot shop"})
    fake.track_status = "Out For Delivery"
    r = S.track_awb(T, courier="shiprocket", awb="SR555")
    assert r["status"] == "out_for_delivery" and r["events"][0]["where"] in ("Akola Hub", "") and r["events"][0]["what"]
    # Logistics uses the real hook (no monkeypatch)
    from app.logistics import service as L
    out = L._courier_track(T, "shiprocket", "SR555")
    assert out["status"] == "out_for_delivery"


def test_wiring(env):
    from app.agent import tools as T_
    from app.employee import inbox, roles
    names = [t["name"] for t in T_.TOOLS]
    for n in ("customs", "customs_dekho", "travel", "travel_dekho", "warehouse", "warehouse_dekho", "fleet", "fleet_dekho",
              "courier", "courier_dekho", "drivers", "drivers_dekho", "logistics", "logistics_dekho"):
        assert names.count(n) == 1 and n in T_.HANDLERS
    assert "biz_parcel_status" not in names and "biz_parcel_status" in T_.HANDLERS     # never offered to her model
    biz = [t["name"] for t in inbox.BIZ_TOOLS]
    assert "biz_parcel_status" in biz and "biz_parcel_fix" in biz and "biz_parcel_fix" in inbox.BIZ_HANDLERS
    assert {"biz_parcel_status", "biz_parcel_fix"} <= roles.CUSTOMER_TOOLS
    for d in ("customs_work", "travel_work", "warehouse_work", "fleet_work", "courier_desk", "driver_coord", "logistics_work"):
        assert d in roles.DUTIES
    for p in ("importer", "travel_agency", "warehouse", "fleet", "courier", "drivers", "logistics"):
        assert roles.PRESETS[p]["role"] in roles.ROLES
    from app.voice import VOICE_TOOL_NAMES
    assert {"fleet", "courier_dekho", "logistics", "drivers", "travel", "warehouse", "customs"} <= set(VOICE_TOOL_NAMES)
    from app import approvekey
    with pytest.raises(approvekey.ApproveError) as e:      # courier is a known kind: an unknown card, not an unknown kind
        approvekey.card_digest("courier", "nope", "default")
    assert "baaki nahi" in str(e.value)


def test_push_render():
    from app import push
    assert push.render("courier_card", {"card": {"status": "waiting", "body": {"title": "Book P-0001", "say": "Rs 72"}}})[1] == "Book P-0001 - Rs 72"
    assert push.render("courier_card", {"card": {"status": "done", "body": {}}}) is None
    assert push.render("courier_parcel", {"event": "picked", "parcel": {}}) is None
    assert "Parcel: P-1" in push.render("courier_parcel", {"event": "rto", "parcel": {"number": "P-1", "status_label": "RTO", "raw": "x"}})[0]
    assert push.render("customs_filing", {"filing": {"status": "approved"}, "say": "x"}) is None
    assert push.render("travel_booking", {"status": "waiting", "say": "B-0001"})[1] == "B-0001"
    assert push.render("warehouse_adjust", {"adjust": {"status": "waiting"}, "say": "s"})
    assert push.render("logistics_day", {"text": "aaj 3"})[1] == "aaj 3"
    assert push.render("fleet_spend", {"say": "Rs 500"})[1] == "Rs 500"
    for k in ("customs_filing", "travel_booking", "warehouse_adjust", "fleet_spend", "courier_card", "drivers_plan", "logistics_ewb"):
        assert k in push.PUSH_KINDS
