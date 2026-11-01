"""v0.352 KAAM BAANTO (App Sahayak Phase 16): a row is given to ONE staff member - by her (Hoola), an admin account, or a
staff account taking an unassigned row for itself; the person sees it under My work and hears about it in the app's update
check; nobody else on staff can change it; the customer sees only the first name of the person on her row."""
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def _acct(c, api, email, name):
    c.post(f"{api}/signup", json={"email": email, "password": "pass-" + name.split()[0].lower() + "-1", "name": name})


def _login(c, api, email, name):
    t = c.post(f"{api}/login", json={"email": email, "password": "pass-" + name.lower() + "-1"}).json()["token"]
    return {"Authorization": "Bearer " + t}


def test_assign_rules_my_work_updates_and_customer_view(droid_env):
    from app.appmaker import backend as BE
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    for e, n in (("asha@example.com", "Asha"), ("ravi@example.com", "Ravi Kumar"), ("meena@example.com", "Meena"),
                 ("boss@example.com", "Boss")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    for e, role in (("ravi@example.com", "staff"), ("meena@example.com", "staff"), ("boss@example.com", "admin")):
        c.post(f"/api/apps/{aid}/members/{mem[e]['id']}/role", json={"role": role})
    ha, hr, hm, hb = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("ravi@example.com", "Ravi"),
                                                         ("meena@example.com", "Meena"), ("boss@example.com", "Boss")))
    rid, mid = mem["ravi@example.com"]["id"], mem["meena@example.com"]["id"]
    row = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    o = row["id"]
    since = c.get(f"{api}/updates", headers=hr).json()["now"]
    # the team list: staff only, names only (no e-mails), admin flag
    assert c.get(f"{api}/team", headers=ha).status_code == 403 and c.get(f"{api}/team").status_code == 401
    t = c.get(f"{api}/team", headers=hb).json()
    assert t["admin"] is True and {p["name"] for p in t["team"]} == {"Ravi", "Meena", "Boss"}
    assert "email" not in str(t) and "@" not in str(t)
    assert c.get(f"{api}/team", headers=hr).json()["admin"] is False
    # a customer can never assign, even through the update outbox
    assert c.post(f"{api}/c/orders/{o}/assign", json={"to": rid}, headers=ha).status_code == 403
    assert c.post(f"{api}/c/orders/{o}", json={"_assign": "me"}, headers=ha).status_code == 403
    # a staff account cannot give work to someone else, but can take an unassigned row (through the outbox's update)
    assert c.post(f"{api}/c/orders/{o}/assign", json={"to": mid}, headers=hr).status_code == 403
    took = c.post(f"{api}/c/orders/{o}", json={"_assign": "me"}, headers=hr).json()
    assert took["assigned_to"] == rid and took["assigned_name"] == "Ravi"
    # now it is Ravi's: Meena can neither take it nor change it nor delete it; Ravi can work on it
    assert c.post(f"{api}/c/orders/{o}/assign", json={"to": "me"}, headers=hm).status_code == 403
    r = c.post(f"{api}/c/orders/{o}", json={"status": "Packed"}, headers=hm)
    assert r.status_code == 403 and "Ravi" in r.json()["error"]
    assert c.delete(f"{api}/c/orders/{o}", headers=hm).status_code == 403
    assert c.post(f"{api}/c/orders/{o}", json={"status": "Packed"}, headers=hr).json()["status"] == "Packed"
    # My work
    assert [x["id"] for x in c.get(f"{api}/c/orders?mine=1", headers=hr).json()["rows"]] == [o]
    assert c.get(f"{api}/c/orders?mine=1", headers=hm).json()["rows"] == []
    # Ravi's app hears it was given to him
    items = c.get(f"{api}/updates", params={"since": since}, headers=hr).json()["items"]
    assert any(i["kind"] == "assigned" and i["id"] == o for i in items)
    # the customer sees the first name only
    mine = c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]
    assert mine["assigned_name"] == "Ravi" and "assigned_to" not in mine
    # the admin moves it to Meena (by name too), the owner from Hoola takes it back
    moved = c.post(f"{api}/c/orders/{o}/assign", json={"to": "meena"}, headers=hb).json()
    assert moved["assigned_to"] == mid
    assert c.post(f"{api}/c/orders/{o}", json={"status": "Out for delivery"}, headers=hr).status_code == 403
    assert c.post(f"{api}/c/orders/{o}/assign", json={"to": mem["asha@example.com"]["id"]}, headers=hb).status_code == 404  # not staff
    # the dashboard: open work per person + unassigned
    st = c.get(f"{api}/stats", headers=hb).json()
    assert {p["name"]: p["open"] for p in st["team"]}["Meena"] == 1 and st["unassigned"] == 0
    back = c.patch(f"/api/apps/{aid}/data/orders/{o}", json={"assign": ""}).json()
    assert back["assigned_to"] == "" and c.get(f"{api}/stats", headers=hb).json()["unassigned"] == 1
    assert c.patch(f"/api/apps/{aid}/data/orders/{o}", json={"assign": "Ravi Kumar"}).json()["assigned_to"] == rid
    assert c.get(f"/api/apps/{aid}/data/orders").json()["rows"][0]["assigned_name"] == "Ravi"
    # Ravi gives it back; then anyone on staff may work on it again
    assert c.post(f"{api}/c/orders/{o}/assign", json={"to": ""}, headers=hr).json()["assigned_to"] == ""
    assert c.post(f"{api}/c/orders/{o}", json={"status": "Delivered"}, headers=hm).json()["status"] == "Delivered"
    assert BE.STATS["assigned"] >= 4 and BE.STATS["assign_refused"] >= 3


def test_tool_assigns_by_name(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from app.main import app
    from tests.test_v128_appdesign import T
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    o = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]},
               headers=_login(c, api, "asha@example.com", "Asha")).json()["id"]
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "data", {"app": aid, "coll": "orders", "row": o, "set": {"assign": "ravi"}})
    assert out["assigned_name"] == "Ravi"


def test_kits_phone_and_console_show_it():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    pro, acc = (kt / "Pro.kt").read_text(), (kt / "Accounts.kt").read_text()
    assert "object Team" in pro and "fun AssignBox(coll: String, r: Item)" in pro and '"/team"' in pro
    assert 'mapOf("_assign" to "me")' in pro and "fun mayWork(r: Item)" in pro
    assert "AssignBox(coll, r)" in acc and "Team.mayWork(r)" in acc and "Strings.myWork" in acc and "Strings.onIt" in acc
    assert '"assigned"' in (kt / "Updates.kt").read_text() and "val myWork" in (kt / "Strings.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    pro, acc = (sw / "Pro.swift").read_text(), (sw / "Accounts.swift").read_text()
    assert "final class Team: ObservableObject" in pro and "struct AssignBox: View" in pro and '["_assign": "me"]' in pro
    assert '"assigned" ? Words.assignedToYou' in pro
    assert "AssignBox(coll: coll, r: r)" in acc and "team.mayWork(r)" in acc and "Words.myWork" in acc
    assert "static var myWork" in (sw / "Kit.swift").read_text()
    from app.appmaker.ios import prompts as IP
    assert "AssignBox" in IP.KIT_SHEET
    assert "@Composable AssignBox(coll: String, r: Item)" in __import__("app.appmaker.android.prompts", fromlist=["x"]).kit_sheet()
    js = (root / "app/static/console/build.js").read_text()
    assert 'data-f="assign"' in js and "<th>With</th>" in js
    dart = (root.parent / "lib/ui/app_android.dart").read_text()
    assert "'assign': x" in dart and "Kiske paas" in dart
