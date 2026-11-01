"""v0.353 RAAY (App Sahayak Phase 17): once her row is finished the customer who made it rates it ONCE (1-5 stars + a short
note); nobody else can, it is never changed, a low one reaches the owner's chat, and the dashboard shows the average per list
and per staff member (who had the job)."""
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_rating_rules_stats_and_low_note(droid_env):
    from app.appmaker import backend as BE
    from app.db import Message, session
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    mk = lambda h: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=h).json()["id"]
    o1, o2 = mk(ha), mk(ha)
    c.post(f"{api}/c/orders/{o1}/assign", json={"to": "me"}, headers=hr)
    # not finished yet: no rating, and the app is told it cannot rate
    assert c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]["can_rate"] is False
    assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": 5}, headers=ha).status_code == 409
    c.post(f"{api}/c/orders/{o1}", json={"status": "Delivered"}, headers=hr)
    c.post(f"{api}/c/orders/{o2}", json={"status": "Cancelled"}, headers=hr)
    rows = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}
    assert rows[o1]["can_rate"] is True and rows[o2]["can_rate"] is False          # a cancelled order is never rated
    # nobody else rates: not staff, not another customer, not signed out; stars must be 1-5 whole
    assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": 5}, headers=hr).status_code == 403
    assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": 5}, headers=hn).status_code in (403, 404)
    assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": 5}).status_code == 401
    for bad in (0, 6, 4.5, "five", True):
        assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": bad}, headers=ha).status_code == 400, bad
    # her rating through the outbox's update path; the note is cleaned and cut
    out = c.post(f"{api}/c/orders/{o1}", json={"_rate": {"stars": 2, "note": "Late\x00 by 2 hours " + "x" * 400}}, headers=ha).json()
    assert out["rating"] == 2 and "\x00" not in out["rating_note"] and len(out["rating_note"]) <= 300 and out["can_rate"] is False
    assert c.post(f"{api}/c/orders/{o1}/rate", json={"stars": 5}, headers=ha).status_code == 409    # never changed
    # staff and the owner see it; a low rating reached her chat
    assert {x["id"]: x for x in c.get(f"{api}/c/orders", headers=hr).json()["rows"]}[o1]["rating"] == 2
    assert {x["id"]: x for x in c.get(f"/api/apps/{aid}/data/orders").json()["rows"]}[o1]["rating"] == 2
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "2/5" in str(m.content)]
    assert notes and "Ravi" in notes[0] and "Late" in notes[0]
    # the dashboard: average per list and per person who had the job
    st = c.get(f"{api}/stats", headers=hr).json()
    orders = next(l for l in st["lists"] if l["key"] == "orders")
    assert orders["rating"] == {"avg": 2.0, "count": 1}
    assert {p["name"]: p for p in st["team"]}["Ravi"]["rating"] == 2.0
    assert BE.STATS["ratings"] >= 1 and BE.STATS["rating_low"] >= 1 and BE.STATS["rating_refused"] >= 3


def test_kits_phone_console_show_it():
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    pro = (kt / "Pro.kt").read_text()
    assert "fun RateBox(coll: String, r: Item)" in pro and 'mapOf("_rate" to JSONObject().put("stars", stars)' in pro
    assert 'r.b("can_rate")' in pro and 'optJSONObject("rating")' in pro and "Strings.myTeam" in pro
    assert "RateBox(coll, r)" in (kt / "Accounts.kt").read_text() and "val rateIt" in (kt / "Strings.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    pro = (sw / "Pro.swift").read_text()
    assert "struct RateBox: View" in pro and '["_rate": ["stars": stars' in pro and "Words.myTeam" in pro
    assert "RateBox(coll: coll, r: r)" in (sw / "Accounts.swift").read_text() and "static var rateIt" in (sw / "Kit.swift").read_text()
    from app.appmaker.android import prompts as AP
    from app.appmaker.ios import prompts as IP
    assert "RateBox" in IP.KIT_SHEET and "@Composable RateBox(coll: String, r: Item)" in AP.kit_sheet()
    assert "<th>Rating</th>" in (root / "app/static/console/build.js").read_text()
    assert "rating_note" in (root.parent / "lib/ui/app_android.dart").read_text()
