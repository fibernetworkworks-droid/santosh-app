"""v0.435 PARIVAAR (App Sahayak Pillar H, Phases 58-59): one business, several apps, one backend + a web admin.

A food-delivery shape on a real built app: restaurants -> dishes, food orders pointing at a restaurant. The delivery
partner app and the partner shop app are their own projects whose app_keys land on the MAIN backend; partners apply
and only she / an app admin approves; a shop sees only its own orders and never the customer's phone; a rider sees
ready jobs without the phone, takes one (first tap wins), then moves it only through his steps; the live stream, the
shift and the web admin follow the same rules; generators carry the jobs screen only in a partner build."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1] / "app" / "appmaker"
STATUSES = ["New", "Accepted", "Preparing", "Ready", "Picked up", "Out for delivery", "Delivered", "Cancelled"]
LISTS = [
    {"key": "restaurants", "label": "Restaurants", "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"},
     "fields": [{"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "area", "label": "Area", "type": "text"}]},
    {"key": "dishes", "label": "Dishes", "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"},
     "fields": [{"key": "shop", "label": "Restaurant", "type": "ref", "to": "restaurants", "required": True},
                {"key": "name", "label": "Dish", "type": "text", "required": True},
                {"key": "price", "label": "Price", "type": "number"}]},
    {"key": "food_orders", "label": "Food orders", "rules": {"create": "member", "read": "own", "update": "admin", "delete": "admin"},
     "fields": [{"key": "shop", "label": "Restaurant", "type": "ref", "to": "restaurants", "required": True},
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "phone", "label": "Phone", "type": "phone"},
                {"key": "address", "label": "Address", "type": "text"},
                {"key": "items", "label": "Items", "type": "long_text"},
                {"key": "total", "label": "Total", "type": "number", "admin_only": True},
                {"key": "status", "label": "Status", "type": "choice", "options": STATUSES, "admin_only": True}]},
]
LOGIC = {"relations": [
    {"name": "dishes", "from": "dishes", "field": "shop", "to": "restaurants", "label": "Dishes", "on_delete": "restrict"},
    {"name": "orders", "from": "food_orders", "field": "shop", "to": "restaurants", "label": "Orders", "on_delete": "restrict"}]}


def _app(aid):
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


def _setup(droid_env):
    from app.appmaker.android import service as AN
    from app.main import app
    from app.site import webapp as W
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    got = c.put(f"/api/apps/{aid}/logic", json={"logic": LOGIC, "lists": LISTS}).json()
    assert got["ok"] is True, got
    people = {"Asha": "asha@example.com", "Ravi": "ravi@example.com", "Boss": "boss@example.com"}
    for n, e in people.items():
        _acct(c, api, e, n)
    mem = {m["email"]: m["id"] for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']}/role", json={"role": "staff"})
    c.post(f"/api/apps/{aid}/members/{mem['boss@example.com']}/role", json={"role": "admin"})
    hs = {n: _login(c, api, e, n) for n, e in people.items()}
    shops = {}
    for nm in ("Swaad Dhaba", "Pizza Point"):
        W._RATE.clear()
        shops[nm] = c.post(f"{api}/c/restaurants", json={"name": nm, "area": "Akola"}, headers=hs["Ravi"]).json()["id"]
    dish_b = c.post(f"{api}/c/dishes", json={"shop": shops["Pizza Point"], "name": "Margherita", "price": 199},
                    headers=hs["Ravi"]).json()
    assert dish_b.get("id"), dish_b
    return c, aid, key, api, hs, mem, shops, dish_b, AN


def test_family_end_to_end(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import family as FA
    from app.appmaker import live as LV
    from app.site import webapp as W
    c, aid, key, api, hs, mem, shops, dish_b, AN = _setup(droid_env)

    # her settings: the order list, the rider's and the shop's steps, the shop link - read from the app's own lists
    st = c.put(f"/api/apps/{aid}/family/settings", json={"jobs": "food_orders"}).json()
    assert st["jobs"] == "food_orders" and st["statuses"] == STATUSES
    assert st["rider"]["offer"] == ["Accepted", "Ready"] and st["rider"]["steps"] == ["Picked up", "Out for delivery", "Delivered"]
    assert st["vendor"] == {"link": "restaurants", "ref": "shop", "steps": ["Accepted", "Preparing", "Ready", "Cancelled"],
                            "lists": ["dishes"]}
    st = c.put(f"/api/apps/{aid}/family/settings", json={"rider": {"offer": ["Ready"]}}).json()
    assert st["rider"]["offer"] == ["Ready"]
    assert c.put(f"/api/apps/{aid}/family/settings", json={"rider": {"offer": ["Nonsense"]}}).status_code == 400
    assert c.put(f"/api/apps/{aid}/family/settings", json={"rider": {"offer": ["Ready"], "steps": ["Ready"]}}).status_code == 400

    # two more apps on the SAME backend: their own projects, the main app's data
    fr = c.post(f"/api/apps/{aid}/family/face", json={"kind": "rider"}).json()
    fv = c.post(f"/api/apps/{aid}/family/face", json={"kind": "vendor", "words": "restaurants"}).json()
    assert fr["face"]["kind"] == "rider" and fv["face"]["kind"] == "vendor" and fr["id"] != aid
    assert c.post(f"/api/apps/{aid}/family/face", json={"kind": "rider"}).json()["existing"] is True
    fs = c.post(f"/api/apps/{fr['id']}/family/face", json={"kind": "staff"}).json()      # asked from a face: the MAIN app's
    assert fs["face"]["of"] == aid
    assert c.post(f"/api/apps/{aid}/family/face", json={"kind": "pilot"}).status_code == 400
    fam = c.get(f"/api/apps/{aid}/family").json()
    assert [f["kind"] for f in fam["faces"]] == ["main", "rider", "vendor", "staff"] and fam["problems"] == {"rider": "", "vendor": ""}
    assert fam["admin_url"].endswith(f"/app-admin/{key}")
    assert c.get(f"/api/apps/{fr['id']}/family").json()["app"] == aid                    # a face's family = the main app's
    rk, vk = (AN._app_key(_app(x["id"])) for x in (fr, fv))
    rapi, vapi = f"/api/app-api/{rk}", f"/api/app-api/{vk}"
    assert BE.by_key(rk).id == aid and FA.kind_for_key(rk) == "rider" and FA.kind_for_key(key) == ""
    assert c.get(f"/api/apps/{fv['id']}/data").json()["app"] == aid                       # her console: the same data
    hint = BE.seed_hint(_app(fr["id"]))
    assert hint["partner"] == "rider" and hint["face"] == "rider"
    assert {x["key"] for x in hint["collections"]} >= {"restaurants", "dishes", "food_orders"}
    assert "partner" not in BE.seed_hint(_app(aid))

    # partners apply from their own apps; nothing is theirs until she approves
    for n, e, a in (("Raju", "raju@example.com", rapi), ("Vijay", "vijay@example.com", rapi), ("Sonu", "sonu@example.com", vapi)):
        _acct(c, a, e, n)
        hs[n] = _login(c, a, e, n)
    assert c.get(f"{rapi}/partner/jobs").json()["state"] == "login"
    j = c.get(f"{rapi}/partner/jobs", headers=hs["Raju"]).json()
    assert j["state"] == "none" and j["can_request"] is True and j["kind"] == "rider"
    assert c.post(f"{rapi}/partner/request", headers=hs["Ravi"]).status_code == 409        # staff are not partners
    assert c.post(f"{api}/partner/request", headers=hs["Asha"]).status_code == 400         # the customer app is no partner app
    for n, a in (("Raju", rapi), ("Vijay", rapi), ("Sonu", vapi)):
        assert c.post(f"{a}/partner/request", headers=hs[n]).json()["state"] == "waiting"
    assert c.get(f"{rapi}/partner/jobs", headers=hs["Raju"]).json()["state"] == "waiting"
    waiting = {p["name"]: p for p in c.get(f"/api/apps/{aid}/family").json()["partners"]}
    assert {k: v["state"] for k, v in waiting.items()} == {"Raju": "waiting", "Vijay": "waiting", "Sonu": "waiting"}
    # an app admin approves on the web admin; staff may only look
    assert c.post(f"{api}/admin/partners/{waiting['Raju']['id']}", json={"action": "approve"}, headers=hs["Ravi"]).status_code == 403
    assert c.post(f"{api}/admin/partners/{waiting['Raju']['id']}", json={"action": "approve"}, headers=hs["Boss"]).json()["state"] == "approved"
    assert c.post(f"/api/apps/{aid}/family/partners/{waiting['Vijay']['id']}", json={"action": "approve"}).json()["state"] == "approved"
    assert c.post(f"/api/apps/{aid}/family/partners/{waiting['Sonu']['id']}", json={"action": "approve"}).status_code == 400   # which shop?
    assert c.post(f"/api/apps/{aid}/family/partners/{waiting['Sonu']['id']}",
                  json={"action": "approve", "link_row": dish_b["id"]}).status_code == 400                                   # not a shop
    ok = c.post(f"/api/apps/{aid}/family/partners/{waiting['Sonu']['id']}",
                json={"action": "approve", "link_row": shops["Swaad Dhaba"]}).json()
    assert ok["state"] == "approved" and ok["link_name"] == "Swaad Dhaba"

    # Asha orders from both restaurants (customer app); Sonu's phone hears only his
    W._RATE.clear()
    o_a = c.post(f"{api}/c/food_orders", json={"shop": shops["Swaad Dhaba"], "name": "Asha Verma", "phone": "9876500002",
                                               "address": "12 MG Road", "items": "Thali x2\nLassi x1"}, headers=hs["Asha"]).json()
    o_b = c.post(f"{api}/c/food_orders", json={"shop": shops["Pizza Point"], "name": "Asha Verma", "phone": "9876500002",
                                               "address": "12 MG Road", "items": "Margherita x1"}, headers=hs["Asha"]).json()
    assert o_a["status"] == "New" and o_b["id"]

    # the partner shop: only its own order, no phone, first name only, only its steps
    rows_v = c.get(f"{vapi}/c/food_orders", headers=hs["Sonu"]).json()["rows"]
    assert [x["id"] for x in rows_v] == [o_a["id"]]
    assert "phone" not in rows_v[0] and rows_v[0]["name"] == "Asha" and rows_v[0]["partner"] == "limited"
    jv = c.get(f"{vapi}/partner/jobs", headers=hs["Sonu"]).json()
    assert jv["state"] == "active" and jv["shop"] == "Swaad Dhaba" and [x["id"] for x in jv["mine"]] == [o_a["id"]]
    assert jv["mine"][0]["phone"] == "" and "9876500002" not in json.dumps(jv) and jv["offers"] == []
    assert c.patch(f"{vapi}/c/food_orders/{o_b['id']}", json={"status": "Accepted"}, headers=hs["Sonu"]).status_code == 403
    assert c.patch(f"{vapi}/c/food_orders/{o_a['id']}", json={"status": "Delivered"}, headers=hs["Sonu"]).status_code == 403
    assert c.patch(f"{vapi}/c/food_orders/{o_a['id']}", json={"address": "x"}, headers=hs["Sonu"]).status_code == 403
    assert c.post(f"{vapi}/partner/jobs/{o_a['id']}/step", json={"status": "Accepted"}, headers=hs["Sonu"]).json()["status"] == "Accepted"
    # the rider sees nothing yet: only READY jobs are offered
    assert c.get(f"{rapi}/partner/jobs", headers=hs["Raju"]).json()["offers"] == []
    c.post(f"{vapi}/partner/jobs/{o_a['id']}/step", json={"status": "Ready"}, headers=hs["Sonu"])
    jr = c.get(f"{rapi}/partner/jobs", headers=hs["Raju"]).json()
    assert [x["id"] for x in jr["offers"]] == [o_a["id"]] and jr["offers"][0]["take"] is True
    assert jr["offers"][0]["phone"] == "" and "9876500002" not in json.dumps(jr)
    assert any(ln.startswith("Pickup: Swaad Dhaba") for ln in jr["offers"][0]["lines"])
    assert any(ln == "Drop: 12 MG Road" for ln in jr["offers"][0]["lines"])
    assert c.patch(f"{rapi}/c/food_orders/{o_a['id']}", json={"status": "Picked up"}, headers=hs["Raju"]).status_code == 403  # take first
    # first tap wins
    took = c.post(f"{rapi}/partner/jobs/{o_a['id']}/take", headers=hs["Raju"]).json()
    assert took["partner"] == "full" and took["phone"] == "9876500002" and took["steps"] == ["Picked up", "Out for delivery", "Delivered"]
    assert c.post(f"{rapi}/partner/jobs/{o_a['id']}/take", headers=hs["Vijay"]).status_code == 409
    assert c.get(f"{rapi}/c/food_orders", headers=hs["Vijay"]).json()["rows"] == []
    assert c.patch(f"{rapi}/c/food_orders/{o_a['id']}", json={"status": "Accepted"}, headers=hs["Raju"]).status_code == 403   # not his step
    assert c.patch(f"{rapi}/c/food_orders/{o_a['id']}", json={"address": "elsewhere"}, headers=hs["Raju"]).status_code == 403
    for stp in ("Picked up", "Out for delivery"):
        assert c.post(f"{rapi}/partner/jobs/{o_a['id']}/step", json={"status": stp}, headers=hs["Raju"]).json()["status"] == stp
    # the shop cannot move it once it is the rider's
    assert c.post(f"{vapi}/partner/jobs/{o_a['id']}/step", json={"status": "Cancelled"}, headers=hs["Sonu"]).status_code == 403
    assert c.get(f"{vapi}/partner/jobs", headers=hs["Sonu"]).json()["mine"][0]["steps"] == []
    raw = BE._row("app:" + aid, o_a["id"])
    d = json.loads(raw.data)
    assert d["_to_name"] == "Raju" and d["_by_kind"] == "rider" and d["status"] == "Out for delivery"

    # the partner shop keeps its own menu: the shop link is the server's, never its own
    W._RATE.clear()
    dish = c.post(f"{vapi}/c/dishes", json={"name": "Dal Makhani", "price": 180, "shop": shops["Pizza Point"]}, headers=hs["Sonu"]).json()
    assert dish["partner"] == "full" and dish["shop"] == shops["Swaad Dhaba"]
    assert c.patch(f"{vapi}/c/dishes/{dish['id']}", json={"price": 190}, headers=hs["Sonu"]).json()["price"] == 190
    assert c.patch(f"{vapi}/c/dishes/{dish['id']}", json={"shop": shops["Pizza Point"]}, headers=hs["Sonu"]).status_code == 403
    assert c.patch(f"{vapi}/c/dishes/{dish_b['id']}", json={"price": 1}, headers=hs["Sonu"]).status_code == 403
    assert c.delete(f"{vapi}/c/dishes/{dish_b['id']}", headers=hs["Sonu"]).status_code == 403
    assert c.post(f"{vapi}/c/restaurants", json={"name": "Mine now"}, headers=hs["Sonu"]).status_code == 403   # list rules still apply

    # the live stream: a partner hears only its own work, in its limited view
    from app.appmaker.backup import AppJournal
    from app.db import session
    from sqlalchemy import select
    with session() as s:
        jb = s.scalars(select(AppJournal).where(AppJournal.row_id == o_b["id"]).order_by(AppJournal.id.desc())).first()
        ja = s.scalars(select(AppJournal).where(AppJournal.row_id == o_a["id"]).order_by(AppJournal.id.desc())).first()
        s.expunge(jb)
        s.expunge(ja)

    def sub(n):
        x = LV.Sub.__new__(LV.Sub)
        x.r, x.colls = _app(aid), None
        x.w = W.Who(W.member_of("app:" + aid, hs[n]["Authorization"][7:]))
        return x
    assert LV.event_for(sub("Sonu"), jb) is None and LV.event_for(sub("Vijay"), ja) is None
    ev = LV.event_for(sub("Sonu"), ja)
    assert ev["row"]["partner"] == "limited" and "phone" not in ev["row"]
    assert LV.event_for(sub("Raju"), ja)["row"]["phone"] == "9876500002"

    # the shift (Pillar D) is open to an approved rider now, never to a shop or a customer
    assert c.post(f"{rapi}/track/shift", json={"on": True}, headers=hs["Raju"]).status_code != 403
    assert c.post(f"{rapi}/track/shift", json={"on": True}, headers=hs["Sonu"]).status_code == 403
    assert c.post(f"{api}/track/shift", json={"on": True}, headers=hs["Asha"]).status_code == 403

    # removed: signed out at once, open jobs back in the pool
    c.post(f"/api/apps/{aid}/family/partners/{waiting['Raju']['id']}", json={"action": "remove"})
    assert c.get(f"{rapi}/partner/jobs", headers=hs["Raju"]).json()["state"] == "login"
    d = json.loads(BE._row("app:" + aid, o_a["id"]).data)
    assert not d.get("_to") and d["status"] == "Out for delivery"          # back in the pool, nothing lost
    assert c.post(f"{rapi}/partner/jobs/{o_a['id']}/take", headers=hs["Vijay"]).status_code == 409   # not "Ready" any more


def test_web_admin_and_roles(droid_env):
    from app.site import webapp as W
    c, aid, key, api, hs, mem, shops, dish_b, AN = _setup(droid_env)
    page = c.get(f"/app-admin/{key}")
    assert page.status_code == 200 and "admin.js" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"] and "script-src 'self'" in page.headers["content-security-policy"]
    assert c.get("/app-admin/not-a-key").status_code == 404
    js = (ROOT.parent / "static" / "appadmin" / "admin.js").read_text()
    assert "innerHTML" not in js and "textContent" in js                                     # data is never HTML
    assert c.get(f"{api}/admin/overview").status_code == 401
    assert c.get(f"{api}/admin/overview", headers=hs["Asha"]).status_code == 403
    ov = c.get(f"{api}/admin/overview", headers=hs["Ravi"]).json()
    assert ov["admin"] is False and {x["key"] for x in ov["lists"]} >= {"restaurants", "food_orders"}
    assert c.get(f"{api}/admin/overview", headers=hs["Boss"]).json()["admin"] is True
    # CSV export: staff only, Excel-safe
    W._RATE.clear()
    c.post(f"{api}/c/food_orders", json={"shop": shops["Swaad Dhaba"], "name": "=HYPERLINK(\"http://x\")", "phone": "9876500002"},
           headers=hs["Asha"])
    assert c.get(f"{api}/admin/export/food_orders", headers=hs["Asha"]).status_code == 403
    csv_r = c.get(f"{api}/admin/export/food_orders", headers=hs["Ravi"])
    assert csv_r.status_code == 200 and csv_r.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in csv_r.text and ",=HYPERLINK" not in csv_r.text
    # roles: an admin makes member / staff, never admin; staff cannot; nobody changes their own
    assert c.post(f"{api}/admin/members/{mem['asha@example.com']}/role", json={"role": "staff"}, headers=hs["Ravi"]).status_code == 403
    assert c.post(f"{api}/admin/members/{mem['asha@example.com']}/role", json={"role": "admin"}, headers=hs["Boss"]).status_code == 403
    assert c.post(f"{api}/admin/members/{mem['boss@example.com']}/role", json={"role": "member"}, headers=hs["Boss"]).status_code == 409
    assert c.post(f"{api}/admin/members/{mem['asha@example.com']}/role", json={"role": "staff"}, headers=hs["Boss"]).json()["role"] == "staff"
    assert len(c.get(f"{api}/admin/members", headers=hs["Boss"]).json()["members"]) >= 3
    assert c.get(f"{api}/admin/partners", headers=hs["Boss"]).json()["link"] == ""            # no shop link set up yet: honest


def test_generators_carry_the_jobs_screen_only_in_partner_builds(tmp_path):
    import subprocess
    import sys
    from app.appmaker.android import gen as G
    from app.appmaker.ios import gen as IG
    sp = json.loads((ROOT / "android/fixture/spec.json").read_text())
    plain = tmp_path / "plain.json"
    plain.write_text(json.dumps(sp))
    sp["seed"].setdefault("backend", {})["partner"] = "rider"
    part = tmp_path / "part.json"
    part.write_text(json.dumps(sp))
    for spec, has in ((plain, False), (part, True)):
        out = tmp_path / ("a" + spec.stem)
        r = subprocess.run([sys.executable, str(ROOT / "android/gen.py"), str(spec), str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        reg = (out / "app/src/main/java/hoola/app/AppScreens.kt").read_text()
        assert ('"hoola_jobs" -> PartnerScreen()' in reg) is has
        assert ("hoola_jobs" in (out / "hoola_qa/screens.txt").read_text()) is has
        assert (out / "app/src/main/java/hoola/kit/Partner.kt").exists()
        outi = tmp_path / ("i" + spec.stem)
        r = subprocess.run([sys.executable, str(ROOT / "ios/gen.py"), str(spec), str(outi)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        assert ("hoola_jobs" in (outi / "hoola_qa/screens.txt").read_text()) is has
        assert (outi / "Sources/Kit/Partner.swift").exists()
    s0 = {"id": "home", "label": "Home", "purpose": "Jobs"}
    assert "PartnerJobsBlock()" in G.fallback_screen(s0, ["home"], ["home"], {"partner": "rider", "collections": []})
    assert "PartnerJobsBlock()" not in G.fallback_screen(s0, ["home"], ["home"], {"collections": []})
    assert "PartnerJobsBlock()" in IG.code_screen(s0, ["home"], ["home"], {"partner": "vendor", "collections": []})
    kt = (ROOT / "android/template/app/src/main/java/hoola/kit/Partner.kt").read_text()
    sw = (ROOT / "ios/template/Sources/Kit/Partner.swift").read_text()
    for src in (kt, sw):                       # the kit only shows what the server decided and sends the taps
        assert "/partner/jobs" in src and "/take" in src and "/step" in src and "/partner/request" in src
    from app.appmaker import family as FA
    assert "PartnerJobsBlock()" in FA.prompt_line({"partner": "rider"}) and FA.prompt_line({}) == ""
