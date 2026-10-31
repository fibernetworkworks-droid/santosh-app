"""v0.325 APP UPDATES (App Sahayak Phase 4): an update rewrites only the screens that changed, versions only go up, every
build has a changelog, any kept build comes back as a new version, the installed app offers the update, and her data
changes (add / hide / label a field) stay safe for app versions already on people's phones."""
import json

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _shop_app
from tests.test_v128_appdesign import T
from tests.test_v132_android import FakeBuild, droid_env  # noqa: F401  (fixture)


def test_updates_rewrite_only_changes_history_rollback_latest(droid_env):
    fake, kt = droid_env
    from app.appmaker import service as AS
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.main import app
    c = TestClient(app)
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    v1 = AN.get(T, aid)
    h1 = v1["history"][0]
    assert v1["status"] == "ready" and h1["build"] == 1 and h1["changed"] and h1["notes"]
    # the same design again: no screen is rewritten, the version still goes UP
    n0 = len(kt.calls)
    AN.build(T, aid, conv)
    v2 = AN.get(T, aid)
    h2 = v2["history"][0]
    simple = set(h1["simple_ids"])                                     # code-made screens get another try
    assert [x for x in kt.calls[n0:] if x[0] == "screen" and x[1] not in simple] == []     # nothing else asked of Opus
    assert h2["changed"] == [] and h2["kept"] >= 5 and h2["version_code"] > h1["version_code"]
    assert h2["version_name"].endswith(".2") and v2["kept_builds"] == [1, 2]
    # one screen's design changes: only that screen is rewritten
    r = AS._load(aid)
    f = AS._scr_path(r, "cart")
    scr = json.loads(f.read_text())
    scr["html"] = scr["html"].replace("</section>", "<p class='t-small'>Free delivery above Rs 499</p></section>", 1)
    f.write_text(json.dumps(scr))
    from app.appmaker import kit as K
    from app.appmaker.models import AppProject
    from app.db import session
    h = K.design_hash(AS._screens(r), AS._ctx(r))
    with session() as s:
        row = s.get(AppProject, aid)
        row.approved_hash = h
    n1 = len(kt.calls)
    AN.build(T, aid, conv)
    h3 = AN.get(T, aid)["history"][0]
    wrote = sorted({x[1] for x in kt.calls[n1:] if x[0] == "screen"} - simple)
    assert wrote == ["cart"] and "Cart" in " ".join(h3["changed"]) and h3["version_code"] > h2["version_code"]
    assert any(n.startswith("Updated: ") for n in h3["notes"])
    # the installed app's update check + the APK it downloads
    with session() as s:
        key = json.loads(s.get(AppProject, aid).android)["app_key"]
    lt = c.get(f"/api/app-api/{key}/latest").json()
    assert lt["version_code"] == h3["version_code"] and lt["url"].endswith(f"/api/app-api/{key}/apk") and lt["notes"]
    apk = c.get(f"/api/app-api/{key}/apk")
    assert apk.status_code == 200 and apk.headers["content-type"] == "application/vnd.android.package-archive"
    assert c.get("/api/app-api/akdeadbeef0000/latest").status_code == 404
    # bring back build 1: its exact project, a NEW higher version, no Opus at all
    n2 = len(kt.calls)
    out = c.post(f"/api/apps/{aid}/rollback", json={"build": 1}).json()
    assert out["status"] in ("building", "ready")
    v4 = AN.get(T, aid)
    h4 = v4["history"][0]
    assert v4["status"] == "ready" and h4["rollback_of"] == 1 and h4["version_code"] > h3["version_code"]
    assert kt.calls[n2:] == [] and h4["notes"][0].startswith("Back to the version of build 1")
    assert c.get(f"/api/app-api/{key}/latest").json()["version_code"] == h4["version_code"]
    assert c.post(f"/api/apps/{aid}/rollback", json={"build": 77}).status_code == 400
    from app.db import Message
    with session() as s:
        notes = [m.content for m in s.query(Message).filter(Message.conversation_id == conv).all() if "wapas aa gayi" in str(m.content)]
    assert notes
    # the tool: 'pichhli wali wapas lao' (0 = the one before the current)
    import asyncio
    from app.agent.tools import Ctx, dispatch
    res = asyncio.run(dispatch("app_banao", {"action": "rollback", "app": aid}, Ctx(tenant_id=T, conversation_id=conv)))
    assert res["status"] in ("building", "ready") and AN.get(T, aid)["history"][0]["rollback_of"] in (2, 3)


def test_screen_key_changes_only_with_that_screen():
    from app.appmaker.android import service as AN
    ctx = {"tokens": {"primary": "#123456", "bg": "#fff"}, "plan": {"tabs": ["home"]}}
    sp = {"screens": [{"id": "home", "label": "Home"}, {"id": "cart", "label": "Cart"}], "seed": {"backend": {"order": "orders"}}}
    screens = {"home": {"html": "<section>a</section>", "css": ""}, "cart": {"html": "<section>b</section>", "css": ""}}
    k_home, k_cart = AN._skey("home", ctx, sp, screens), AN._skey("cart", ctx, sp, screens)
    screens2 = {**screens, "cart": {"html": "<section>b2</section>", "css": ""}}
    assert AN._skey("home", ctx, sp, screens2) == k_home and AN._skey("cart", ctx, sp, screens2) != k_cart
    # the look or the server lists change every screen (they are in every screen's code)
    assert AN._skey("home", {**ctx, "tokens": {"primary": "#654321", "bg": "#fff"}}, sp, screens) != k_home
    assert AN._skey("home", ctx, {**sp, "seed": {"backend": {"order": ""}}}, screens) != k_home


def test_data_changes_are_safe_for_old_app_versions(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.appmaker.models import AppProject
    from app.db import session
    from app.main import app
    import asyncio
    from app.agent.tools import Ctx, dispatch
    c = TestClient(app)
    fake, _kt = droid_env
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    with session() as s:
        key = json.loads(s.get(AppProject, aid).android)["app_key"]
    api = f"/api/app-api/{key}"
    tok = c.post(f"{api}/signup", json={"email": "a@example.com", "password": "pass-word-1", "name": "A"}).json()["token"]
    h = {"Authorization": "Bearer " + tok}
    pid = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]["id"]
    first = c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "note": "old note", "cart": [{"id": pid, "qty": 1}]},
                   headers=h).json()
    # add: a plain field is never required (an old app can't send it); a choice may be, with its default
    out = c.post(f"/api/apps/{aid}/data_change", json={"ops": {"add": [
        {"coll": "orders", "key": "delivery_time", "label": "Delivery time", "type": "text", "required": True},
        {"coll": "orders", "key": "packing", "label": "Packing", "type": "choice", "options": ["Bag", "Box"], "required": True}]},
        "words": "delivery time aur packing chahiye"}).json()
    assert out["rev"] == 1 and len(out["done"]) == 2
    sch = BE.schema(BE.by_key_or_ref(T, aid))
    f = {x["key"]: x for x in sch["collections"][0]["fields"]}
    assert f["delivery_time"]["required"] is False and f["packing"]["required"] is False and f["packing"]["default"] == "Bag"
    # the app version already on phones (it knows nothing of the new fields) still places orders
    old_app = c.post(f"{api}/c/orders", json={"name": "A", "phone": "9876543210", "cart": [{"id": pid, "qty": 1}]}, headers=h)
    assert old_app.status_code == 200 and old_app.json()["packing"] == "Bag"
    # hide: out of the forms, the data stays; essential order fields can't be hidden
    c.post(f"/api/apps/{aid}/data_change", json={"ops": {"hide": [{"coll": "orders", "key": "note"}]}})
    assert c.post(f"/api/apps/{aid}/data_change", json={"ops": {"hide": [{"coll": "orders", "key": "phone"}]}}).status_code == 400
    rows = c.get(f"/api/apps/{aid}/data/orders").json()["rows"]
    assert any(r.get("note") == "old note" for r in rows) and any(r["id"] == first["id"] for r in rows)
    content = c.get(f"/api/app-content/{key}").json()
    note_f = next(x for x in content["backend"]["collections"][0]["fields"] if x["key"] == "note")
    assert note_f.get("hidden") is True                    # the app hides it at once (Db.fields filters hidden)
    # label, then a bad op
    c.post(f"/api/apps/{aid}/data_change", json={"ops": {"label": [{"coll": "orders", "key": "address", "label": "Ghar ka pata"}]}})
    assert c.post(f"/api/apps/{aid}/data_change", json={"ops": {"add": [{"coll": "nope", "key": "x"}]}}).status_code == 400
    assert c.post(f"/api/apps/{aid}/data_change", json={"ops": {}}).status_code == 400
    # her changes survive a backend upgrade (replayed on the rebuilt lists)
    with session() as s:
        row = s.get(AppProject, aid)
        be = json.loads(row.backend)
        be["v"] = 1
        row.backend = json.dumps(be)
    sch2 = BE.schema(BE.by_key_or_ref(T, aid))
    f2 = {x["key"]: x for x in sch2["collections"][0]["fields"]}
    assert "delivery_time" in f2 and f2["note"].get("hidden") and f2["address"]["label"] == "Ghar ka pata"
    # the tool path + the next build's changelog says so; forms skip the hidden field
    res = asyncio.run(dispatch("app_banao", {"action": "data_change", "app": aid, "ops": {"add": [{"coll": "orders", "key": "gift_wrap",
                                                                                                   "type": "yes_no"}]}},
                                Ctx(tenant_id=T, conversation_id=conv)))
    assert res["rev"] >= 4
    AN.build(T, aid, conv)
    hist = AN.get(T, aid)["history"][0]
    assert hist["schema_changed"] and "New details you can fill in." in hist["notes"]
    from app.appmaker.android import gen as G
    form = G.fallback_screen({"id": "cart", "label": "Cart"}, ["cart"], [], BE.seed_hint(BE.by_key_or_ref(T, aid)))
    assert '"note"' not in form and '"delivery_time"' in form


def test_generated_project_offers_updates(droid_env):
    from app.appmaker import kit as K
    from app.appmaker.android import runners as RN
    from app.appmaker.android import service as AN
    from app.appmaker.models import AppProject
    from app.db import session
    fake, _kt = droid_env
    aid, conv = _shop_app(fake)
    RN.set_runner(FakeBuild())
    AN.build(T, aid, conv)
    with session() as s:
        row = s.get(AppProject, aid)
        proj = K.app_dir(row.tenant_id, aid) / "android" / "project"
    kit = proj / "app/src/main/java/hoola/kit"
    assert (kit / "AppUpdate.kt").exists() and "fun link(" in (kit / "Actions.kt").read_text()
    assert '!it.b("hidden")' in (kit / "Backend.kt").read_text()
    main = (proj / "app/src/main/java/hoola/app/MainActivity.kt").read_text()
    assert "AppUpdate.check(this@MainActivity, BuildConfig.VERSION_CODE)" in main and 'if (stage == "app") UpdateDialog()' in main
    gradle = (proj / "app/build.gradle.kts").read_text()
    import re
    vc = int(re.search(r"versionCode = (\d+)", gradle).group(1))
    assert vc == AN.get(T, aid)["history"][0]["version_code"]
