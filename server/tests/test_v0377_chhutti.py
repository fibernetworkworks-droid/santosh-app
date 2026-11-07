"""v0.377 CHHUTTI (App Sahayak Phase 41): her holidays (no slots those days; an order on a holiday is taken with a note) and
changing an order's delivery time - her customer before the cut-off, staff any time, the new slot booked under the lock, a lost
race keeps the order exactly as it was."""
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_holidays_and_change_time(droid_env, monkeypatch):
    from app.appmaker import delivery as DL
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "neha@example.com", "Neha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    clock = {"t": datetime(2026, 11, 2, 8, 0)}
    monkeypatch.setattr(DL, "_ist", lambda: clock["t"])
    c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"label": "Morning", "start": "09:00", "end": "11:00", "cap": 1},
                                                      {"label": "Evening", "start": "17:00", "end": "19:00", "cap": 1}],
                                           "days": 2, "cutoff": 60})
    assert c.put(f"/api/apps/{aid}/delivery", json={"holidays": "03-11-2026"}).status_code == 400
    v = c.put(f"/api/apps/{aid}/delivery", json={"holidays": "2026-11-03, 2020-01-01"}).json()
    assert v["holidays"] == ["2026-11-03"]                                   # past dates dropped
    keys = [s["key"] for s in c.get(f"{api}/slots").json()["slots"]]
    assert not any(k.startswith("2026-11-03") for k in keys) and "2026-11-04|09:00" in keys
    order = lambda slot, h: c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "slot": slot,
                                                            "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).json()
    o = order("2026-11-02|17:00", ha)
    # her customer moves it; another customer cannot; a full slot is refused and the order keeps its slot
    assert c.post(f"{api}/c/orders/{o['id']}/slot", json={"slot": "2026-11-04|09:00"}, headers=hn).status_code == 404
    r = c.post(f"{api}/c/orders/{o['id']}/slot", json={"slot": "2026-11-04|09:00"}, headers=ha)
    assert r.status_code == 200 and r.json()["slot"] == "2026-11-04|09:00"
    o2 = order("2026-11-04|17:00", hn)
    bad = c.post(f"{api}/c/orders/{o['id']}/slot", json={"slot": "2026-11-04|17:00"}, headers=ha)
    assert bad.status_code == 409
    assert {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[o["id"]]["slot"] == "2026-11-04|09:00"
    assert "2026-11-02|17:00" in [s["key"] for s in c.get(f"{api}/slots").json()["slots"]]            # the old place freed
    # past the cut-off: the customer cannot move it, staff can
    clock["t"] = datetime(2026, 11, 4, 8, 30)
    assert c.post(f"{api}/c/orders/{o['id']}/slot", json={"slot": "2026-11-05|17:00"}, headers=ha).status_code == 409
    clock["t"] = datetime(2026, 11, 4, 7, 0)
    c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"label": "Morning", "start": "09:00", "end": "11:00", "cap": 1},
                                                      {"label": "Evening", "start": "17:00", "end": "19:00", "cap": 1}],
                                           "days": 2, "cutoff": 60})
    clock["t"] = datetime(2026, 11, 4, 8, 30)
    assert c.post(f"{api}/c/orders/{o['id']}/slot", json={"slot": "2026-11-05|09:00"}, headers=hr).status_code == 200
    # an order placed on a holiday: taken, with the holiday note
    clock["t"] = datetime(2026, 11, 3, 10, 0)
    oh = c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    assert "chhutti" in {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[oh["id"]]["delivery_note"]


def test_kit_markers():
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert "fun SlotChange(coll: String, r: Item)" in (kt / "Pro.kt").read_text() and "SlotChange(coll, r)" in (kt / "Accounts.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct SlotChange: View" in (sw / "Pro.swift").read_text() and "SlotChange(coll: coll, r: r)" in (sw / "Accounts.swift").read_text()
    assert "Save holidays" in (root / "app/static/console/build.js").read_text()
