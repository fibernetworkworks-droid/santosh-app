"""v0.314 ASLI APP (Phase 1): every Hoola-made native app has its own backend - accounts, real saved data, roles - and the
generated Android project uses it (kit Cloud / Auth / Db with an offline outbox, code-made sign-in + account screens,
fallback screens that save for real). The Kotlin itself is compiled and driven end to end against a real Hoola server
on an emulator in CI (.github/workflows/appgen-check.yml, kit E2e)."""
import json
import re

from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


def _shop_app(fake):
    from app.appmaker import service as S
    ctx = conv_ctx()
    v = S.new(T, "Sharma Kirana ki app, ghar pe delivery", ctx.conversation_id, name="Sharma Kirana", goal="shop",
              answers={"phone": "9876543210", "address": "MG Road, Pune", "upi_id": "sharma@okicici"})
    S.approve_plan(T, v["id"], ctx.conversation_id)
    S.choose_look(T, v["id"], 1, 0, ctx.conversation_id)
    v = S.get(T, v["id"])
    assert v["status"] == "ready", v.get("error")
    S.approve(T, v["id"], v["hash"])
    return v["id"], ctx.conversation_id


def _built(droid_env):
    fake, _kt = droid_env
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    assert AN.get(T, aid)["status"] == "ready"
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        row = s.get(AppProject, aid)
        return aid, conv, json.loads(row.android)["app_key"], json.loads(row.backend)


def test_schemas_per_kind_of_app():
    from app.appmaker import backend as BE
    from app.appmaker import blueprint as BP

    class R:
        def __init__(self, goal, plan="{}"):
            self.goal, self.plan = goal, plan
    shop = BE.schema_for(R("shop"))
    assert shop["kind"] == "customer" and shop["order"] == "orders"
    o = shop["collections"][0]
    f = {x["key"]: x for x in o["fields"]}
    assert o["rules"] == {"create": "member", "read": "own", "update": "admin", "delete": "admin"}
    assert f["total"]["admin_only"] and f["items"]["admin_only"] and f["status"]["admin_only"]   # the phone never prices
    assert f["phone"]["type"] == "phone" and f["name"]["required"]
    assert [c["key"] for c in BE.schema_for(R("booking"))["collections"]] == ["bookings"]
    assert BE.schema_for(R("catalogue"))["collections"][0]["rules"]["create"] == "public"
    assert BE.schema_for(R("music_streaming"))["kind"] == "product"
    # a complex staff app: its OWN modules first, staff-only rules, no secret / sensitive fields
    for goal, first in (("isp_ops", "plan_package"), ("school_erp", "guardian"), ("crm", "customer")):
        sch = BE.schema_for(R(goal, json.dumps({"blueprint": BP.make(goal, ["home"], goal)})))
        keys = [c["key"] for c in sch["collections"]]
        assert sch["kind"] == "staff" and keys[0] == first and 1 <= len(keys) <= 12, (goal, keys)
        for c in sch["collections"]:
            assert c["rules"] == {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"}
            assert not any(re.search(r"password|aadhaar|cvv|token", x["key"]) for x in c["fields"])
            assert not re.search(r"_line$|_item$|^audit_log$", c["key"])


def test_installed_app_flow_orders_dedup_rules_staff_and_delete(droid_env):
    from app.appmaker import backend as BE
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    assert be["schema"]["order"] == "orders" and be["made"]
    api = f"/api/app-api/{key}"
    sch = c.get(f"{api}/schema").json()
    assert sch["order"] == "orders" and sch["collections"][0]["key"] == "orders"
    assert c.get("/api/app-api/akdeadbeef00/schema").status_code == 404
    assert c.get("/api/app-api/../schema").status_code in (404, 405)
    # the content the app refreshes carries the backend too (a newer copy than the build wins in the app)
    content = c.get(f"/api/app-content/{key}").json()
    assert content["backend"]["order"] == "orders"
    prods = content["lists"]["products"]
    p1, p2 = prods[0], prods[1]
    # accounts
    bad = c.post(f"{api}/signup", json={"email": "x", "password": "12345678"})
    assert bad.status_code == 400
    a = c.post(f"{api}/signup", json={"email": "Asha@Example.com", "password": "asha-pass-1", "name": "Asha"}).json()
    assert a["token"] and a["me"]["role"] == "member" and a["me"]["email"] == "asha@example.com"
    assert c.post(f"{api}/login", json={"email": "asha@example.com", "password": "wrong-pass"}).status_code == 401
    ha = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "asha@example.com", "password": "asha-pass-1"}).json()["token"]}
    assert c.get(f"{api}/me", headers=ha).json()["me"]["name"] == "Asha"
    # an order needs an account
    assert c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}).status_code == 401
    # the SERVER prices the cart; a price / total / status the phone sends is ignored
    body = {"cid": "phoneWrite0001", "name": "Asha", "phone": "98765 43210", "address": "Flat 4", "total": 1, "status": "Delivered",
            "items": "free stuff", "cart": [{"id": p1["id"], "qty": 2, "price": 1}, {"id": p2["id"], "qty": 1}, {"id": "nope", "qty": 5}]}
    r = c.post(f"{api}/c/orders", json=body, headers=ha)
    assert r.status_code == 200, r.text
    row = r.json()
    want = round(float(p1["price"]) * 2 + float(p2["price"]), 2)
    assert row["total"] == want and row["status"] == "New" and row["phone"] == "9876543210"
    assert f"2 x {p1['name']}" in row["items"] and "free stuff" not in row["items"] and "nope" not in row["items"]
    # the same write again (retry after a lost answer) = the same row, never a second order
    again = c.post(f"{api}/c/orders", json=body, headers=ha).json()
    assert again["id"] == row["id"] and again.get("dedup") is True
    assert len(c.get(f"{api}/c/orders", headers=ha).json()["rows"]) == 1
    assert c.post(f"{api}/c/orders", json={**body, "cid": "bad cid!"}, headers=ha).status_code == 400
    assert c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "cart": []}, headers=ha).status_code == 400
    # another customer never sees Asha's order and can't change it
    b = c.post(f"{api}/signup", json={"email": "ravi@example.com", "password": "ravi-pass-1", "name": "Ravi"}).json()
    hb = {"Authorization": "Bearer " + b["token"]}
    assert c.get(f"{api}/c/orders", headers=hb).json()["rows"] == []
    assert c.post(f"{api}/c/orders/{row['id']}", json={"status": "Cancelled"}, headers=hb).status_code == 403
    assert c.post(f"{api}/c/orders/{row['id']}", json={"status": "Cancelled"}, headers=ha).status_code == 403   # update = staff
    # her chat heard about the new order (one note, not two for the retry)
    from app.db import Message, session
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "Nayi order" in str(m.content)]
    assert len(notes) == 1 and str(want).rstrip("0").rstrip(".") in notes[0].replace("Rs ", "")
    # she runs it from Hoola: sees the order, accepts it, makes Ravi staff
    v = c.get(f"/api/apps/{aid}/data").json()
    assert v["counts"]["orders"] == 1 and v["counts"]["members"] == 2 and v["api"].endswith(key)
    rows = c.get(f"/api/apps/{aid}/data/orders").json()["rows"]
    assert rows[0]["id"] == row["id"]
    up = c.patch(f"/api/apps/{aid}/data/orders/{row['id']}", json={"status": "Accepted"}).json()
    assert up["status"] == "Accepted"
    assert c.patch(f"/api/apps/{aid}/data/orders/{row['id']}", json={"status": "Teleported"}).status_code == 400
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    assert c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"}).json()["role"] == "staff"
    assert c.get(f"{api}/c/orders", headers=hb).status_code == 401          # a new role = sign in again
    hb = {"Authorization": "Bearer " + c.post(f"{api}/login", json={"email": "ravi@example.com", "password": "ravi-pass-1"}).json()["token"]}
    staff_rows = c.get(f"{api}/c/orders", headers=hb).json()["rows"]
    assert [x["id"] for x in staff_rows] == [row["id"]]                     # staff see everyone's
    assert c.post(f"{api}/c/orders/{row['id']}", json={"status": "Packed"}, headers=hb).json()["status"] == "Packed"
    assert c.get(f"{api}/members", headers=hb).status_code == 200
    assert c.get(f"{api}/members", headers=ha).status_code == 403
    # Asha sees her order's new status; then deletes her account inside the app: account + rows gone
    assert c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]["status"] == "Packed"
    assert c.post(f"{api}/delete-me", headers=ha).json()["ok"] is True
    assert c.get(f"{api}/me", headers=ha).json()["me"] is None
    assert c.post(f"{api}/login", json={"email": "asha@example.com", "password": "asha-pass-1"}).status_code == 401
    assert c.get(f"/api/apps/{aid}/data").json()["counts"].get("orders", 0) == 0
    assert c.post(f"{api}/delete-me").status_code == 401
    # logout ends every token of that account
    assert c.post(f"{api}/logout", headers=hb).json()["ok"] is True
    assert c.get(f"{api}/c/orders", headers=hb).status_code == 401
    assert BE.STATS["dedup"] >= 1 and BE.STATS["orders"] >= 1


def test_generated_project_uses_the_backend(droid_env, tmp_path):
    from app.appmaker.android import gen as G
    from app.appmaker.android import prompts as PR
    aid, _conv, key, be = _built(droid_env)
    from app.appmaker import kit as K
    from app.appmaker.models import AppProject
    from app.db import session
    with session() as s:
        row = s.get(AppProject, aid)
        proj = K.app_dir(row.tenant_id, aid) / "android" / "project"
    seed = json.loads((proj / "app/src/main/assets/seed.json").read_text())
    assert seed["backend"]["order"] == "orders" and seed["backend"]["collections"][0]["fields"]
    kit = proj / "app/src/main/java/hoola/kit"
    for f in ("Backend.kt", "Accounts.kt", "E2e.kt"):
        assert (kit / f).exists(), f
    screens = (proj / "app/src/main/java/hoola/app/AppScreens.kt").read_text()
    assert '"hoola_login" -> AuthScreen()' in screens and '"hoola_account" -> AccountScreen()' in screens
    main = (proj / "app/src/main/java/hoola/app/MainActivity.kt").read_text()
    assert "Cloud.init(" in main and "Db.load(this)" in main and "Db.watch(this)" in main and "Db.sync()" in main
    assert re.search(r"if \(BuildConfig\.DEBUG\) intent\?\.getStringExtra\(\"hoola_test_server\"\)", main)
    man = (proj / "app/src/main/AndroidManifest.xml").read_text()
    assert "ACCESS_NETWORK_STATE" in man and "READ_SMS" not in man
    rel = (proj / "app/src/main/res/xml/network_security_config.xml").read_text()
    dbg = (proj / "app/src/debug/res/xml/network_security_config.xml").read_text()
    assert 'cleartextTrafficPermitted="true"' not in rel and "10.0.2.2" in dbg       # release stays https-only
    # the token is sealed with the Keystore; the password box exists only in the kit's own screen
    assert "AndroidKeyStore" in (kit / "Backend.kt").read_text()
    assert "PasswordVisualTransformation" in (kit / "Accounts.kt").read_text()
    # model screens may link to the kit's screens, still never draw a password field
    ids = ["home", "cart"]
    good = 'package hoola.app.screens\n\nimport androidx.compose.runtime.Composable\nimport hoola.kit.*\n\n@Composable\nfun ScreenHome() {\n' \
           '    val nav = LocalNav.current\n    Page("Home") { block { Btn("Account") { nav.go("hoola_account") } } }\n}\n'
    assert G.scan_screen(good, "home", ids) == []
    assert G.scan_screen(good.replace('Btn("Account")', 'TextField(visualTransformation = PasswordVisualTransformation())'), "home", ids)
    # fallback screens save for real: a cart places an order, an orders list shows the user's rows, a booking form submits
    bk = {"order": "orders", "collections": be["schema"]["collections"] + [{"key": "bookings", "rules": {"create": "member"},
          "fields": [{"key": "service", "label": "Service", "type": "text", "required": True},
                     {"key": "slot", "label": "Slot", "type": "choice", "options": ["Morning", "Evening"]},
                     {"key": "status", "label": "Status", "type": "choice", "options": ["New"], "admin_only": True}]}]}
    cart = G.fallback_screen({"id": "cart", "label": "Cart"}, ["cart", "home"], ["home"], bk)
    assert 'OrderBtn("Place order"' in cart and 'Field("Mobile number *", "phone", keyboard = KeyboardType.Phone' in cart
    assert '"total"' not in cart and '"status"' not in cart                       # staff-only fields never on the phone form
    orders = G.fallback_screen({"id": "orders", "label": "Orders", "lists": ["orders"]}, ["orders"], [], bk)
    assert 'LiveRowsBlock("orders")' in orders and "AppData.list" not in orders
    book = G.fallback_screen({"id": "book_slot", "label": "Book"}, ["book_slot"], [], bk)
    assert 'SubmitBtn("Send", "bookings"' in book and 'Chips(listOf("Morning", "Evening"), "slot")' in book
    plain = G.fallback_screen({"id": "about", "label": "About"}, ["about"], [], bk)
    assert "SubmitBtn" not in plain and "OrderBtn" not in plain
    # the model is told the real lists and the kit's data API (from the Kotlin source)
    sheet = PR.kit_sheet()
    assert "SubmitBtn(" in sheet and "liveRows(" in sheet and "Db.rows(" in sheet and "AuthScreen" not in sheet
    assert "Auth.signup" not in sheet and "Cloud." not in sheet and "E2e" not in sheet
    line = PR.backend_line(bk)
    assert "orders (create member): name*, phone*" in line and "total" not in line and "order list = orders" in line
    sys_ = PR.screen_system("home", False, ids + list(G.KIT_SCREENS), {}, [], "English", ["home"], bk)
    assert "hoola_account" in sys_ and "NEVER write your own login" in sys_


def test_tools_read_and_run_the_app_data(droid_env):
    import asyncio
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.main import app
    c = TestClient(app)
    aid, conv, key, _be = _built(droid_env)
    api = f"/api/app-api/{key}"
    tok = c.post(f"{api}/signup", json={"email": "meena@example.com", "password": "meena-pass-1", "name": "Meena"}).json()["token"]
    pid = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]["id"]
    row = c.post(f"{api}/c/orders", json={"name": "Meena", "phone": "9123456780", "cart": [{"id": pid, "qty": 1}]},
                 headers={"Authorization": "Bearer " + tok}).json()
    owner = Ctx(tenant_id=T, conversation_id=conv)
    d = asyncio.run(dispatch("app_dekho", {"what": "data", "app": aid}, owner))
    assert d["order"] == "orders" and d["counts"]["orders"] == 1 and d["collections"][0]["key"] == "orders"
    rows = asyncio.run(dispatch("app_dekho", {"what": "data", "app": aid, "coll": "orders"}, owner))
    assert rows["rows"][0]["id"] == row["id"]
    out = asyncio.run(dispatch("app_banao", {"action": "data", "app": aid, "coll": "orders", "row": row["id"],
                                             "set": {"status": "Accepted"}}, owner))
    assert out["status"] == "Accepted"
    mem = asyncio.run(dispatch("app_dekho", {"what": "members", "app": aid}, owner))["members"]
    assert mem[0]["email"] == "meena@example.com"
    staff = Ctx(tenant_id=T, conversation_id=conv, actor="staff:x")
    try:
        asyncio.run(dispatch("app_banao", {"action": "data", "app": aid, "coll": "orders", "row": row["id"],
                                           "set": {"status": "Cancelled"}}, staff))
        raise AssertionError("staff changed her app data")
    except ToolError:
        pass
    # newest app when she names none
    assert asyncio.run(dispatch("app_dekho", {"what": "data"}, owner))["app"] == aid
