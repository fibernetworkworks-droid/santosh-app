"""v0.412 NAKSHA LIVE (App Sahayak Pillar D, Phases 50-51): her tracking switch, rider shifts (staff only, her switch
first), positions accepted only during a shift and kept as ONE point (wiped at shift end), the customer sees ONLY the rider
bringing HER order and only while it is on its way, ETA as an estimate, near / arrived geofences written once through the
journal, live 'pos' events filtered per person, riders map for staff / her, store privacy answers, builds that carry the
location service only when tracking is on, and both kits."""
import json
from pathlib import Path

from tests.test_v0407_live import _shop
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"
DEST = (19.0760, 72.8777)


def _pos(c, api, h, lat, lng, **kw):
    from app.site import webapp as W
    W._RATE.clear()                                   # one point every 2 s per rider: the test does not wait
    return c.post(f"{api}/track/pos", json={"lat": lat, "lng": lng, **kw}, headers=h)


def test_tracking_end_to_end(droid_env, monkeypatch):
    from app.appmaker import backend as BE
    from app.appmaker import live as LV
    from app.appmaker import track as TR
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import webapp as W
    from sqlalchemy import select
    c, aid, api, hs, p1, ids = _shop(droid_env)
    st = c.get(f"/api/apps/{aid}/track").json()
    assert st["on"] is False and st["coll"] == "orders" and st["statuses"] == ["Out for delivery"] and st["loc"] == "pin"
    assert c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Ravi"]).status_code == 409    # her switch first
    assert c.put(f"/api/apps/{aid}/track", json={"on": True, "coll": "orders", "statuses": ["Nonsense"]}).status_code == 400
    assert c.put(f"/api/apps/{aid}/track", json={"on": True, "coll": "nope"}).status_code == 400
    st = c.put(f"/api/apps/{aid}/track", json={"on": True, "coll": "orders", "statuses": ["Out for delivery", "Packed"]}).json()
    assert st["on"] and st["statuses"] == ["Out for delivery", "Packed"]
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert BE.seed_hint(r)["track"] == {"on": True, "coll": "orders", "statuses": st["statuses"], "loc": "pin"}
    assert c.get(f"{api}/schema").json()["track"]["on"] is True
    # who may start a shift
    assert c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Asha"]).status_code == 403
    assert c.post(f"{api}/track/shift", json={"on": True}).status_code == 401
    assert _pos(c, api, hs["Ravi"], 19.1, 72.9).status_code == 409                                   # no shift yet
    assert c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Ravi"]).json()["on"] is True
    me = c.get(f"{api}/track/me", headers=hs["Ravi"]).json()
    assert me["on"] is True and me["tracking"] is True and me["started"]
    assert _pos(c, api, hs["Ravi"], 95, 72.9).status_code == 400
    assert _pos(c, api, hs["Ravi"], 0, 0).status_code == 400
    assert _pos(c, api, hs["Ravi"], 19.1, 72.9, acc=3000).json()["kept"] is False                      # a rough guess is dropped
    # two customers' orders; Asha's goes out with Ravi
    o_a = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876500002", "pin": f"{DEST[0]},{DEST[1]}",
                                          "cart": [{"id": p1["id"], "qty": 1}]}, headers=hs["Asha"]).json()
    o_n = c.post(f"{api}/c/orders", json={"name": "Neha", "phone": "9876500001", "cart": [{"id": p1["id"], "qty": 1}]},
                 headers=hs["Neha"]).json()
    trk = f"{api}/track/c/orders/{o_a['id']}"
    assert c.get(trk, headers=hs["Asha"]).json()["why"] == "not_on_the_way"
    c.patch(f"/api/apps/{aid}/data/orders/{o_a['id']}", json={"assign": ids["Ravi"]})
    c.patch(f"/api/apps/{aid}/data/orders/{o_a['id']}", json={"status": "Out for delivery"})
    assert c.get(trk, headers=hs["Neha"]).status_code == 404                                           # never someone else's
    assert c.get(f"{api}/track/c/orders/{o_n['id']}", headers=hs["Neha"]).json()["why"] == "not_on_the_way"
    # Ravi moves: 3 km away -> Asha sees him, an ETA, and nothing about him beyond his first name
    got = _pos(c, api, hs["Ravi"], DEST[0] + 0.027, DEST[1], speed=6.0).json()
    assert got["kept"] and got["orders"] == 1
    t = c.get(trk, headers=hs["Asha"]).json()
    assert t["tracking"] and t["rider"]["name"] == "Ravi" and t["rider"]["member"] == "rider" and t["rider"]["fresh"]
    assert 2.8 < t["km"] < 3.2 and t["eta_min"] >= 1 and t["eta_note"] == "estimate" and not t["near"]
    assert t["dest"] == {"lat": DEST[0], "lng": DEST[1]}
    assert c.get(trk, headers=hs["Ravi"]).json()["rider"]["member"] == ids["Ravi"]                    # staff see who
    assert c.get(f"/api/apps/{aid}/track/c/orders/{o_a['id']}").json()["tracking"] is True             # and so does she
    # the live 'pos' signal: Asha's stream gets it, Neha's never, staff get every rider
    LV.ensure_table()
    with session() as s:
        sig = s.scalars(select(LV.LiveSignal).where(LV.LiveSignal.kind == "pos").order_by(LV.LiveSignal.id.desc()).limit(1)).first()
        s.expunge(sig)

    def sub(n):
        x = LV.Sub.__new__(LV.Sub)
        x.w = W.Who(W.member_of("app:" + aid, hs[n]["Authorization"][7:]))
        return x
    ev_a, ev_n, ev_r = (LV.signal_event(sub(n), sig) for n in ("Asha", "Neha", "Ravi"))
    assert ev_a["type"] == "pos" and ev_a["member"] == "rider" and list(ev_a["orders"]) == [o_a["id"]] and "to" not in json.dumps(ev_a)
    assert ev_n is None
    assert ev_r["member"] == ids["Ravi"] and ev_r["orders"] == [o_a["id"]]
    # 300 m -> near (once), 50 m -> arrived (once), written on the row through the journal
    _pos(c, api, hs["Ravi"], DEST[0] + 0.0027, DEST[1])
    assert c.get(trk, headers=hs["Asha"]).json()["near"] is True
    _pos(c, api, hs["Ravi"], DEST[0] + 0.00045, DEST[1])
    t = c.get(trk, headers=hs["Asha"]).json()
    assert t["near"] and t["arrived"] and t["km"] < 0.1
    from app.appmaker.backup import AppJournal
    with session() as s:
        marks = [json.loads(j.after) for j in s.scalars(select(AppJournal).where(AppJournal.row_id == o_a["id"]))]
    assert sum(1 for m in marks if m.get("_near")) >= 1 and len({m.get("_near") for m in marks if m.get("_near")}) == 1
    # riders: staff + her, never a customer
    rs = c.get(f"{api}/track/riders", headers=hs["Ravi"]).json()["riders"]
    assert len(rs) == 1 and rs[0]["name"] == "Ravi" and rs[0]["orders"] == 1
    assert c.get(f"{api}/track/riders", headers=hs["Asha"]).status_code == 403
    assert len(c.get(f"/api/apps/{aid}/track").json()["riders"]) == 1
    # delivered -> no more tracking for her
    c.patch(f"/api/apps/{aid}/data/orders/{o_a['id']}", json={"status": "Delivered"})
    assert c.get(trk, headers=hs["Asha"]).json()["why"] == "not_on_the_way"
    # shift ends -> the position is wiped, the riders list is empty
    assert c.post(f"{api}/track/shift", json={"on": False}, headers=hs["Ravi"]).json()["on"] is False
    with session() as s:
        x = s.get(TR.AppRider, f"app:{aid}|{ids['Ravi']}")
        assert x.lat is None and x.lng is None and x.at is None and not x.on
    assert c.get(f"{api}/track/riders", headers=hs["Ravi"]).json()["riders"] == []
    assert _pos(c, api, hs["Ravi"], DEST[0], DEST[1]).status_code == 409
    # a shift left on is over after SHIFT_HOURS
    c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Ravi"])
    monkeypatch.setattr(TR, "SHIFT_HOURS", 0)
    assert _pos(c, api, hs["Ravi"], DEST[0], DEST[1]).status_code == 409
    # her switch off: no shifts
    monkeypatch.setattr(TR, "SHIFT_HOURS", 14)
    c.put(f"/api/apps/{aid}/track", json={"on": False, "coll": "orders", "statuses": ["Out for delivery"]})
    assert c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Ravi"]).status_code == 409
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert "track" not in BE.seed_hint(r)


def test_builds_and_store_answers(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.android import gen as AG
    from app.appmaker.android import store as ST
    from app.appmaker.ios import appstore as AS
    from app.appmaker.ios import gen as IG
    from app.appmaker.models import AppProject
    from app.db import session
    c, aid, api, hs, p1, ids = _shop(droid_env)
    spec = {"seed": {"backend": {"track": {"on": True}, "collections": []}}}
    m = AG.manifest_xml(spec)
    assert 'android:name="hoola.kit.TrackService"' in m and 'foregroundServiceType="location"' in m
    assert "FOREGROUND_SERVICE_LOCATION" in m and "ACCESS_FINE_LOCATION" in m and "BACKGROUND_LOCATION" not in m
    assert "TrackService" not in AG.manifest_xml({})
    import plistlib
    assert "location" in plistlib.loads(IG.info_plist(spec).encode())["UIBackgroundModes"]
    assert "location" not in plistlib.loads(IG.info_plist({}).encode())["UIBackgroundModes"]
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert not any("staff on shift" in x["type"] for x in ST.data_safety(r))
    c.put(f"/api/apps/{aid}/track", json={"on": True, "coll": "orders", "statuses": ["Out for delivery"]})
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    assert any("staff on shift" in x["type"] for x in ST.data_safety(r))
    assert any("staff on shift" in x["type"] for x in AS.privacy_answers(r))
    assert BE.seed_hint(r)["track"]["on"] is True


def test_kits_and_map_files():
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/Track.kt").read_text()
    for s in ("class TrackService", "FOREGROUND_SERVICE_TYPE_LOCATION", "/track/pos", "/track/shift", "fun ShiftBlock",
              "fun LiveMap", "fun TrackOrderBlock", "fun RidersMap", "fun TrackButton", "tiles.openfreemap.org", "/static/vendor/maplibre/"):
        assert s in kt, s
    assert "ACCESS_BACKGROUND_LOCATION" not in kt
    sw = (ROOT / "ios/template/Sources/Kit/Track.swift").read_text()
    for s in ("CLLocationManager", "requestWhenInUseAuthorization", "showsBackgroundLocationIndicator", "/track/pos",
              "struct ShiftBlock", "struct LiveMap", "struct TrackOrderBlock", "struct RidersMap", "struct TrackButton"):
        assert s in sw, s
    assert "requestAlwaysAuthorization" not in sw
    assert "Track.onPos(e)" in (ROOT / "android/template/app/src/main/java/hoola/kit/Live.kt").read_text()
    assert "Track.shared.onPos(e)" in (ROOT / "ios/template/Sources/Kit/Live.swift").read_text()
    assert "TrackButton(coll, r)" in (ROOT / "android/template/app/src/main/java/hoola/kit/Accounts.kt").read_text()
    assert "TrackButton(coll: coll, r: r)" in (ROOT / "ios/template/Sources/Kit/Accounts.swift").read_text()
    v = ROOT.parent / "static/vendor/maplibre"
    assert (v / "maplibre-gl.js").stat().st_size > 500_000 and (v / "LICENSE.txt").exists()
    assert "MapLibre" in (ROOT.parents[2] / "THIRD_PARTY_NOTICES.md").read_text()
