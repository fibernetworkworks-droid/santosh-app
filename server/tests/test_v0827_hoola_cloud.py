"""v0.827 HOOLA CLOUD (L10 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L10"): saved data + sign-in for App Engine apps.

Proof the plan asks for: the RULE AUDIT (every rule checked on the server, a public read of personal data refused at
plan time) and MIGRATION REFUSAL (drop / rename / type change never done by Hoola; her "I accept data loss" tap only),
plus preview vs live data kept apart, the sealed app frame + shell, and the Studio's Cloud tab in a real browser."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _refused, _tool, ae_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ORDERS = {"op": "add_list", "key": "orders", "label": "Orders", "fields": [
    {"key": "item", "label": "Item", "type": "text", "required": True},
    {"key": "qty", "label": "Quantity", "type": "number"},
    {"key": "phone", "label": "Phone", "type": "phone"},
    {"key": "status", "label": "Status", "type": "choice", "options": ["new", "packed"], "default": "new", "admin_only": True}],
    "rules": {"create": "member", "read": "own", "update": "own", "delete": "admin"}}


def _app(changes=None):
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid = _tool(action="create", name="Mithai orders")["id"]
    r = AE._load(T, aid)
    if changes:
        CL.apply_changes(r, changes)
    return aid, AE._load(T, aid)


def _live(r):
    from app.appengine import service as AE
    AE._save(r.id, live_version=1)
    return AE._load(T, r.id)


# ---------------------------------------------------------------- 1. migrations
def test_migrations_are_additive_one_run_and_data_loss_is_her_tap(ae_env):
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid, r = _app([ORDERS])
    assert CL.schema(r)["version"] == 1 and "orders: {" in (AE.src_dir(r) / "src/lib/cloud.types.ts").read_text()
    types = (AE.src_dir(r) / "src/lib/cloud.types.ts").read_text()
    assert "item: string;" in types and "qty?: number;" in types and 'status?: "new" | "packed";' in types
    # destructive changes are refused, named with the add-copy-hide way, and NOTHING changes
    for c in ({"op": "drop_field", "list": "orders", "field": "qty"}, {"op": "rename_field", "list": "orders", "field": "qty", "to": "count"},
              {"op": "change_type", "list": "orders", "field": "qty", "type": "text"}, {"op": "drop_list", "list": "orders"},
              {"op": "remove_option", "list": "orders", "field": "status", "option": "new"}):
        with pytest.raises(CL.CloudError) as e:
            CL.apply_changes(r, [{"op": "add_field", "list": "orders", "key": "note", "type": "long_text"}, c])
        assert e.value.code == 409 and "I accept data loss" in str(e.value) and CL.DESTRUCTIVE[c["op"]][:20] in str(e.value)
    assert CL.schema(r)["version"] == 1 and not any(f["key"] == "note" for f in CL.schema(r)["lists"][0]["fields"])
    # one run = all or nothing: a bad change in the middle leaves the schema untouched
    with pytest.raises(CL.CloudError, match="type must be one of"):
        CL.apply_changes(r, [{"op": "add_field", "list": "orders", "key": "note", "type": "long_text"},
                             {"op": "add_field", "list": "orders", "key": "weird", "type": "blob"}])
    assert CL.schema(r)["version"] == 1
    out = CL.apply_changes(r, [{"op": "add_field", "list": "orders", "key": "note", "type": "long_text"},
                               {"op": "add_option", "list": "orders", "field": "status", "option": "delivered"},
                               {"op": "label", "list": "orders", "field": "qty", "label": "How many"}])
    assert out["version"] == 2 and len(CL.migrations(r)) == 2 and CL.migrations(r)[-1]["by"] == "hoola"
    # the tool: a destructive ask is refused and waits as her card; the tool can never run it
    msg = _refused(action="cloud_change", app=aid, changes=[{"op": "drop_field", "list": "orders", "field": "note"}])
    assert "data-loss card is now waiting" in msg and CL.pending(r)[0]["op"] == "drop_field"
    with pytest.raises(CL.CloudError) as e:
        CL.destructive_run(r, CL.pending(r), confirm=True, accept=False)
    assert e.value.code == 403
    # her tap: the field and its VALUES go, in both datasets
    k = CL.key_of(r, "preview")
    tok = CL.call(k, "signup", {"email": "asha@example.com", "password": "long-enough-1"})["token"]
    CL.call(k, "create", {"list": "orders", "data": {"item": "Kaju katli", "note": "less sugar"}}, tok)
    CL.destructive_run(r, CL.pending(r), confirm=True, accept=True)
    assert not CL.pending(r) and CL.migrations(r)[-1]["destructive"] and CL.migrations(r)[-1]["by"].startswith("her")
    from app.site import webapp as W
    from app.db import session
    from sqlalchemy import select
    with session() as s:
        for d in s.scalars(select(W.SiteAppRow.data).where(W.SiteAppRow.site_id == CL.site_key(r, "preview"))).all():
            assert "note" not in json.loads(d)


def test_hide_keeps_values_and_show_brings_them_back(ae_env):
    from app.appengine import cloud as CL
    aid, r = _app([ORDERS])
    k = CL.key_of(r, "preview")
    tok = CL.call(k, "signup", {"email": "a@example.com", "password": "long-enough-1"})["token"]
    CL.call(k, "create", {"list": "orders", "data": {"item": "Peda", "qty": 2}}, tok)
    CL.apply_changes(r, [{"op": "hide_field", "list": "orders", "field": "qty"}])
    row = CL.call(k, "list", {"list": "orders"}, tok)["rows"][0]
    assert "qty" not in row and row["item"] == "Peda"
    CL.apply_changes(r, [{"op": "show_field", "list": "orders", "field": "qty"}])
    assert CL.call(k, "list", {"list": "orders"}, tok)["rows"][0]["qty"] == 2                 # the value was kept


# ---------------------------------------------------------------- 2. the rule audit (on the server)
def test_rule_audit_and_every_rule_checked_on_the_server(ae_env):
    from app.appengine import cloud as CL
    aid, r = _app([ORDERS])
    # anyone on the internet reading personal data is refused at plan time, unless it says confirm_public
    with pytest.raises(CL.CloudError) as e:
        CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "public"}])
    assert e.value.code == 409 and "ANYONE on the internet" in str(e.value) and "phone" in str(e.value)
    with pytest.raises(CL.CloudError, match="rules.read must be one of"):
        CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "everyone"}])
    a = CL.audit(CL.schema(r))[0]
    assert a["read"] == "each member - only their own" and a["add"] == "signed-in members" and not a["flags"]
    CL.apply_changes(r, [{"op": "add_list", "key": "menu", "fields": [{"key": "dish", "type": "text"}],
                          "rules": {"create": "admin", "read": "public"}}])
    menu = next(x for x in CL.audit(CL.schema(r)) if x["list"] == "menu")
    assert menu["flags"][0]["level"] == "info" and "Public on purpose" in menu["flags"][0]["say"]
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "public", "confirm_public": True}])
    assert next(x for x in CL.audit(CL.schema(r)) if x["list"] == "orders")["flags"][0]["level"] == "high"
    CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "own"}])
    # the server decides: no sign-in = no orders; a member sees only her own; a role comes only from her (owner) tap
    k = CL.key_of(r, "preview")
    with pytest.raises(CL.CloudError) as e:
        CL.call(k, "create", {"list": "orders", "data": {"item": "x"}})
    assert e.value.code == 401 and str(e.value) == "Please sign in first."                     # English for her visitors
    t1 = CL.call(k, "signup", {"email": "one@example.com", "password": "long-enough-1"})["token"]
    t2 = CL.call(k, "signup", {"email": "two@example.com", "password": "long-enough-2"})["token"]
    mine = CL.call(k, "create", {"list": "orders", "data": {"item": "Barfi", "status": "packed"}}, t1)["row"]
    assert mine["status"] == "new"                                                             # admin_only: a member cannot set it
    assert [x["item"] for x in CL.call(k, "list", {"list": "orders"}, t2)["rows"]] == []
    with pytest.raises(CL.CloudError) as e:
        CL.call(k, "update", {"list": "orders", "id": mine["id"], "data": {"item": "stolen"}}, t2)
    assert e.value.code == 403
    CL.call(k, "update", {"list": "orders", "id": mine["id"], "data": {"role": "admin"}}, t1)    # a role is not app data:
    assert {m["email"]: m["role"] for m in CL.members(r, "preview")}["one@example.com"] == "member"   # ignored, nothing changes
    two = next(m for m in CL.members(r, "preview") if m["email"] == "two@example.com")
    CL.set_role(r, "preview", two["id"], "staff")
    t2 = CL.call(k, "signin", {"email": "two@example.com", "password": "long-enough-2"})["token"]
    assert [x["item"] for x in CL.call(k, "list", {"list": "orders"}, t2)["rows"] if not x.get("sample")] == ["Barfi"]
    with pytest.raises(CL.CloudError, match="Wrong email or password"):
        CL.call(k, "signin", {"email": "two@example.com", "password": "nope-nope-1"})


def test_preview_and_live_are_different_data(ae_env):
    from app.appengine import cloud as CL
    aid, r = _app([ORDERS, {"op": "add_list", "key": "menu", "fields": [{"key": "dish", "type": "text", "required": True}],
                            "rules": {"create": "admin", "read": "public"}}])
    pk, lk = CL.key_of(r, "preview"), CL.key_of(r, "live")
    prev = CL.call(pk, "list", {"list": "menu"})["rows"]
    assert len(prev) == 3 and all(x["sample"] for x in prev) and prev[0]["dish"].startswith("Sample")   # marked samples
    with pytest.raises(CL.CloudError) as e:
        CL.call(lk, "schema", {})
    assert e.value.code == 404                                                                 # not live yet = no live data door
    r = _live(r)
    assert CL.call(lk, "list", {"list": "menu"})["rows"] == []                                 # live starts empty
    CL.call(pk, "signup", {"email": "p@example.com", "password": "long-enough-1"})
    with pytest.raises(CL.CloudError, match="Wrong email"):
        CL.call(lk, "signin", {"email": "p@example.com", "password": "long-enough-1"})         # a preview account is not live
    assert CL.clear_preview(r) >= 3 and CL.call(pk, "list", {"list": "menu"})["rows"] == []
    assert CL.call(lk, "schema", {})["dataset"] == "live"


def test_shell_sealed_app_routes_and_the_tool(ae_env, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid, r = _app([ORDERS])
    d = AE.ver_dir(r, 1) / "dist"                                                              # a built version, without the box
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<html><head><title>x</title></head><body><div id=root></div></body></html>")
    AE._save(r.id, version=1)
    shell = AE.preview_file(r.preview_token, "")[0].decode()
    assert f'"cloud": "/api/cloud/p-{r.preview_token}"' in shell.replace("&quot;", '"') and "__hoola/shell.js" in shell
    assert "data-hs" not in shell and AE.preview_file(r.preview_token, "orders/42")[0].decode() == shell          # app routes -> shell
    app_html = AE.preview_file(r.preview_token, "__app/")[0].decode()
    assert f'<base href="/api/app-preview/{r.preview_token}/__app/">' in app_html and "__hoola/preview.js" in app_html
    assert b"allow-scripts" in AE.preview_file(r.preview_token, "__hoola/shell.js")[0]
    assert b"ae-cmd" in AE.preview_file(r.preview_token, "__app/__hoola/preview.js")[0]          # the helper, from the app's base
    r = _live(r)
    (AE.live_dir(r)).mkdir(parents=True, exist_ok=True)
    (AE.live_dir(r) / "index.html").write_text((d / "index.html").read_text())
    assert f'"cloud": "/api/cloud/l-{r.slug}"' in AE.live_file(r.slug, "")[0].decode().replace("&quot;", '"')
    with pytest.raises(AE.AppEngineError):
        AE.live_file(r.slug, "__hoola/preview.js")                                              # the Studio helper is never live
    c = TestClient(main.app)
    assert c.options(f"/api/cloud/p-{r.preview_token}/list").headers["access-control-allow-origin"] == "*"
    got = c.post(f"/api/cloud/p-{r.preview_token}/list", json={"list": "orders"})
    assert got.status_code == 401 and got.json()["detail"] == "Please sign in first."
    assert c.post("/api/cloud/p-nope-nope-nope-nope/list", json={}).status_code == 404
    assert c.post(f"/api/cloud/p-{r.preview_token}/list", content=b"x" * 40000).status_code == 413
    h = {"Authorization": f"Bearer {KEY}"}
    ov = c.get(f"/api/appengine/{aid}/cloud", headers=h).json()
    assert ov["schema"]["lists"][0]["key"] == "orders" and "files" in ov["not_built"]
    assert c.get(f"/api/appengine/{aid}/cloud", headers={}).status_code == 401
    assert len(c.get(f"/api/appengine/{aid}/cloud/preview/rows/orders", headers=h).json()["rows"]) == 3
    # the model reads PREVIEW data only and never runs a data-loss change; Plan mode refuses its changes
    assert _tool(action="cloud_rows", app=aid, list="orders")["dataset"] == "preview"
    from app.agent import turnmode as TM
    tk = TM.MODE.set("plan")
    try:
        assert "Plan mode" in _refused(action="cloud_change", app=aid, changes=[{"op": "signup", "on": False}])
        assert _tool(action="cloud", app=aid)["audit"]
    finally:
        TM.MODE.reset(tk)
    assert "hoola.db.collection" in CL.prompt_block(r) and "orders (item:text*" in CL.prompt_block(r)
    from app.appengine import rules as RL
    assert "src/lib/cloud.types.ts" in RL.LOCKED
    bad = RL.check_file("src/pages/A.tsx", 'localStorage.setItem("k", "v");', set())
    assert bad and "sealed frame" in bad[0]["found"]


# ---------------------------------------------------------------- 3. the Studio's Cloud tab, in a real browser
def test_cloud_tab_in_a_browser(arena_server, ae_env):
    base, browser, key = arena_server
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]                  # plain calls: Playwright's loop is running here
    r = AE._load(T, aid)
    CL.apply_changes(r, [ORDERS])
    CL.queue_pending(r, [{"op": "drop_field", "list": "orders", "field": "qty"}])
    CL.call(CL.key_of(r, "preview"), "signup", {"email": "asha@example.com", "password": "long-enough-1"})
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/app/{aid}/cloud")
    page.locator(".ae-cl h3", has_text="Orders").wait_for(timeout=20000)
    assert page.locator(".ae-cl .pill", has_text="Sample").count() == 3
    assert "each member - only their own" in page.inner_text(".ae-cloud")
    page.locator(".ae-loss", has_text="drop_field").wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "ae10-1-cloud.png"), full_page=True)
    page.click("[data-ae=loss-yes]")                                                           # not ticked: nothing happens
    page.locator("#toast", has_text="I accept data loss").wait_for()
    assert any(f["key"] == "qty" for f in CL.schema(r)["lists"][0]["fields"])
    page.check("#aeLossOk")
    page.click("[data-ae=loss-yes]")
    page.locator(".ae-loss").wait_for(state="detached")                                       # the card is gone (History keeps it)
    assert not any(f["key"] == "qty" for f in CL.schema(r)["lists"][0]["fields"])
    page.select_option("select[data-ae-role]", "staff")
    page.locator("#toast", has_text="Role changed").wait_for()
    assert CL.members(r, "preview")[0]["role"] == "staff"
    page.click("[data-ae=ds][data-ae-ds=live]")
    page.locator(".ae-cloud", has_text="No entries in live yet").first.wait_for()
    if shots:
        page.screenshot(path=os.path.join(shots, "ae10-2-live.png"))
    ctx.close()
    assert not errors, errors
