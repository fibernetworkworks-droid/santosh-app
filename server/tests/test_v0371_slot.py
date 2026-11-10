"""v0.371 SLOT (App Sahayak Phase 35): delivery time slots - her slots / capacity / days ahead / cut-off, the cart's fresh list
(full and past-cut-off slots left out), the order's slot booked by the server (a full one = the order still goes with a note),
two racing orders for the last place = one gets the slot, the other the note; cancelled orders free their place."""
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_slots_end_to_end(droid_env, monkeypatch):
    from datetime import datetime
    from app.appmaker import delivery as DL
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    monkeypatch.setattr(DL, "_ist", lambda: datetime(2026, 11, 2, 8, 0))         # a Monday, 8 am IST
    assert c.get(f"{api}/slots").json() == {"slots": [], "on": False}
    assert c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"label": "x", "start": "11:00", "end": "09:00", "cap": 2}]}).status_code == 400
    assert c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"start": "09:00", "end": "11:00", "cap": 0}]}).status_code == 400
    v = c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"label": "Morning", "start": "09:00", "end": "11:00", "cap": 2},
                                                          {"label": "Evening", "start": "17:00", "end": "19:00", "cap": 5}],
                                               "days": 1, "cutoff": 90}).json()
    assert len(v["slots"]) == 2 and v["cutoff"] == 90
    assert c.get(f"/api/app-content/{key}").json()["backend"]["delivery"]["slots"] is True
    keys = [s["key"] for s in c.get(f"{api}/slots").json()["slots"]]
    assert "2026-11-02|09:00" not in keys                       # 8:00 + 90 min cut-off > 9:00
    assert keys == ["2026-11-02|17:00", "2026-11-03|09:00", "2026-11-03|17:00"]
    order = lambda slot, h=ha: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "slot": slot,
                                                                 "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).json()
    o1 = order("2026-11-03|09:00")
    o2 = order("2026-11-03|09:00")
    rows = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}
    assert rows[o1["id"]]["slot"] == "2026-11-03|09:00" and rows[o1["id"]]["slot_label"] == "Tomorrow Morning"
    assert "2026-11-03|09:00" not in [s["key"] for s in c.get(f"{api}/slots").json()["slots"]]   # full now
    o3 = order("2026-11-03|09:00")                               # full: still placed, with a note
    r3 = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[o3["id"]]
    assert "slot" not in r3 and "dukaan call" in r3["delivery_note"]
    late = order("2026-11-02|09:00")["id"]                      # past its cut-off: placed, no slot
    assert "slot" not in {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}[late]
    # a cancelled order frees its place
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)
    assert "2026-11-03|09:00" in [s["key"] for s in c.get(f"{api}/slots").json()["slots"]]
    # staff see it on the order
    assert {x["id"]: x for x in c.get(f"{api}/c/orders", headers=hr).json()["rows"]}[o1["id"]]["slot_label"] == "Tomorrow Morning"


def test_race_for_the_last_place(droid_env, monkeypatch):
    from datetime import datetime
    from app.appmaker import delivery as DL
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    ha = _login(c, api, "asha@example.com", "Asha")
    monkeypatch.setattr(DL, "_ist", lambda: datetime(2026, 11, 2, 8, 0))
    c.put(f"/api/apps/{aid}/delivery", json={"slots": [{"label": "Evening", "start": "17:00", "end": "19:00", "cap": 1}]})
    real = DL.book
    monkeypatch.setattr(DL, "book", lambda r, k: ({"slot": k, "slot_label": "Today Evening"}, ""))   # both pass the first check
    a = c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "slot": "2026-11-02|17:00", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    b = c.post(f"{api}/c/orders", json={"name": "B", "phone": "9876543210", "slot": "2026-11-02|17:00", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    monkeypatch.setattr(DL, "book", real)
    rows = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}
    assert rows[a["id"]].get("slot") == "2026-11-02|17:00" and "slot" not in rows[b["id"]] and "usi waqt bhar gaya" in rows[b["id"]]["delivery_note"]


def test_kits_console():
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    assert "fun SlotPicker()" in (kt / "Pro.kt").read_text() and 'data["_slot"] = AppState.slot.value' in (kt / "Backend.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct SlotPicker: View" in (sw / "Pro.swift").read_text() and 'data["_slot"] = st.slot' in (sw / "Backend.swift").read_text()
    assert "Save slots" in (root / "app/static/console/build.js").read_text()
