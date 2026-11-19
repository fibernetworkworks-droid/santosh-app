"""v0.978 APP ENGINE BRANCHES + E8 (owner: "GO APP ENGINE BRANCHES AND E8").

Held here:
- BRANCHES (the second half of L13 of docs/LOVABLE_STUDIO_PLAN.md): a branch is a named copy of an App Engine app with its
  own files, its own preview and its own preview data; it is hidden from the app list, never goes live, at most 3 per app,
  never a branch of a branch. Accept is HER tap: a three-way merge BY FILE against the copy taken when the branch started -
  a file only the branch changed comes in, a file only the app changed stays, a file BOTH changed is a NAMED conflict and
  nothing at all is written until she settles it. Hoola Cloud list changes made in the branch are replayed onto the app as
  one run; the look and added packages come in too. The agent may start and list branches, never accept one. In a real
  browser (Playwright, skipped without Chromium) the Studio's Branches tab starts a branch, shows the conflict, takes her
  choice and accepts.
- E8 LOOKS WITH THEIR OWN BODIES: a small site (at most SITE_LOOK_OWN_BODIES_MAX sections) has every section written by
  EACH look in its own design; nothing goes into the site's sections before she picks, and the picked look's files become
  the site (the build writes no page again). Above the cap the v0.649 shared-body rule stays: written once.
"""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0814_app_engine import _tool, ae_env  # noqa: F401  (fixture + helpers)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

PAGE = 'export default function {n}() {{\n  return <main className="p-6 bg-surface text-ink"><h1 className="text-2xl">{t}</h1></main>;\n}}\n'
ORDERS = {"op": "add_list", "key": "orders", "label": "Orders", "fields": [
    {"key": "item", "label": "Item", "type": "text", "required": True}],
    "rules": {"create": "member", "read": "own", "update": "own", "delete": "admin"}}


def _pg(name, title):
    return PAGE.format(n=name, t=title)


def _src(aid):
    from app.appengine import service as AE
    r = AE._load(T, aid)
    return {p.relative_to(AE.src_dir(r)).as_posix(): p.read_text() for p in AE._files(r)}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.39")


# ---------------------------------------------------------------- branches: start, hidden, never live, limits
def test_branch_is_a_hidden_copy_that_never_goes_live(ae_env):
    from app.appengine import branches as BR
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid = _tool(action="create", name="Mithai orders")["id"]
    CL.apply_changes(AE._load(T, aid), [ORDERS])
    AE.write(T, aid, "src/pages/Menu.tsx", _pg("Menu", "Menu"))
    b = _tool(action="branch_new", app=aid, name="New checkout")
    bid = b["id"]
    assert b["branch"]["name"] == "New checkout" and b["branch_of"] == aid
    assert "never goes live" in b["say"]
    # its own files, its own preview link, its own preview data (marked samples), the app's data untouched
    assert _src(bid)["src/pages/Menu.tsx"] == _src(aid)["src/pages/Menu.tsx"]
    br, ap = AE._load(T, bid), AE._load(T, aid)
    assert br.preview_token != ap.preview_token and br.slug != ap.slug
    assert CL.site_key(br, "preview") != CL.site_key(ap, "preview")
    assert [x["key"] for x in CL.schema(br)["lists"]] == ["orders"]
    # hidden from the app list, listed under its app
    assert [a["id"] for a in AE.list_(T)] == [aid]
    assert [x["id"] for x in _tool(action="branches", app=aid)["branches"]] == [bid]
    # never live; a branch of a branch refused; at most 3; the app cannot be deleted while branches are open
    AE._save(bid, version=1)
    with pytest.raises(AE.AppEngineError, match="never goes live"):
        AE.publish(T, bid, 1, confirm=True)
    with pytest.raises(AE.AppEngineError, match="already a branch"):
        BR.create(T, bid, "deeper")
    with pytest.raises(AE.AppEngineError, match="already a branch called"):
        BR.create(T, aid, "new checkout")
    BR.create(T, aid, "two")
    BR.create(T, aid, "three")
    with pytest.raises(AE.AppEngineError, match="3 open branches"):
        BR.create(T, aid, "four")
    with pytest.raises(AE.AppEngineError, match="open branches"):
        AE.delete_app(T, aid)
    # discard is her tap; the app stays as it was
    with pytest.raises(AE.AppEngineError, match="tap"):
        BR.discard(T, aid, bid)
    before = _src(aid)
    BR.discard(T, aid, bid, confirm=True)
    assert _src(aid) == before and len(BR.open_of(AE._load(T, aid))) == 2
    # the agent may start and list, never accept or discard
    from app.agent.appengine_tools import CHANGES, READS
    assert not ({"branch_accept", "branch_discard", "accept"} & (READS | CHANGES))


# ---------------------------------------------------------------- the merge: incoming, stays, named conflict, nothing half done
def test_three_way_merge_names_conflicts_and_writes_nothing_until_settled(ae_env):
    from app.appengine import branches as BR
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]
    AE.write(T, aid, "src/pages/Menu.tsx", _pg("Menu", "Menu"))
    AE.write(T, aid, "src/pages/About.tsx", _pg("About", "About us"))
    AE.write(T, aid, "src/pages/Shared.tsx", _pg("Shared", "Shared"))
    bid = BR.create(T, aid, "Festive")["id"]
    # the branch changes Menu, adds Offers, deletes About; the app changes About? no - the app changes Shared and so does the branch
    AE.write(T, bid, "src/pages/Menu.tsx", _pg("Menu", "Diwali menu"))
    AE.write(T, bid, "src/pages/Offers.tsx", _pg("Offers", "Offers"))
    AE.delete(T, bid, "src/pages/About.tsx")
    AE.write(T, bid, "src/pages/Shared.tsx", _pg("Shared", "Shared by the branch"))
    AE.write(T, aid, "src/pages/Shared.tsx", _pg("Shared", "Shared by the app"))
    AE.write(T, aid, "src/pages/Contact.tsx", _pg("Contact", "Contact"))
    CL.apply_changes(AE._load(T, bid), [ORDERS])                 # a Hoola Cloud list added in the branch
    plan = BR.compare(T, aid, bid)
    inc = {x["id"] for x in plan["incoming"]}
    assert {"file:src/pages/Menu.tsx", "file:src/pages/Offers.tsx", "file:src/pages/About.tsx", "cloud"} <= inc
    assert [x["id"] for x in plan["conflicts"]] == ["file:src/pages/Shared.tsx"]
    assert plan["conflicts"][0]["what"] == "src/pages/Shared.tsx" and plan["conflicts"][0]["app"] == "changed in the app"
    assert any(x["id"] == "file:src/pages/Contact.tsx" for x in plan["stays"])
    assert "src/pages/Shared.tsx" in plan["say"] and "BOTH" in plan["say"]
    # accept: her tap; an unsettled conflict = nothing at all changes (files, Cloud, the branch)
    with pytest.raises(AE.AppEngineError, match="tap"):
        BR.accept(T, aid, bid)
    before = _src(aid)
    with pytest.raises(AE.AppEngineError) as e:
        BR.accept(T, aid, bid, confirm=True)
    assert e.value.code == 409 and "src/pages/Shared.tsx" in str(e.value)
    assert _src(aid) == before and CL.schema(AE._load(T, aid))["lists"] == []
    assert BR.open_of(AE._load(T, aid))
    # settled: keep the app's Shared -> the branch's other changes come in, the app's own changes stay
    out = BR.accept(T, aid, bid, {"file:src/pages/Shared.tsx": "site"}, confirm=True)
    s = _src(aid)
    assert "Diwali menu" in s["src/pages/Menu.tsx"] and "src/pages/Offers.tsx" in s
    assert "src/pages/About.tsx" not in s and "Shared by the app" in s["src/pages/Shared.tsx"]
    assert "src/pages/Contact.tsx" in s
    assert [x["key"] for x in CL.schema(AE._load(T, aid))["lists"]] == ["orders"]
    assert out["accepted"] and "rebuilding as one new version" in out["say"] and AE._load(T, aid).dirty
    assert BR.open_of(AE._load(T, aid)) == []
    with pytest.raises(AE.AppEngineError):
        AE._load(T, bid)


def test_take_the_branch_look_and_cloud_conflicts(ae_env):
    from app.appengine import branches as BR
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]
    bid = BR.create(T, aid, "Bold")["id"]
    AE.set_tokens(T, bid, palette="bold")
    AE.set_tokens(T, aid, palette="warm")
    CL.apply_changes(AE._load(T, bid), [ORDERS])
    CL.apply_changes(AE._load(T, aid), [{**ORDERS, "key": "notes", "label": "Notes"}])
    AE.write(T, bid, "src/pages/Home.tsx", _pg("Home", "Bold home"))
    AE.write(T, aid, "src/pages/Home.tsx", _pg("Home", "Calm home"))
    plan = BR.compare(T, aid, bid)
    assert {x["id"] for x in plan["conflicts"]} == {"look", "cloud", "file:src/pages/Home.tsx"}
    out = BR.accept(T, aid, bid, {"look": "branch", "cloud": "branch", "file:src/pages/Home.tsx": "branch"}, confirm=True)
    r = AE._load(T, aid)
    assert json.loads(r.look)["palette"] == "bold" and "Bold home" in _src(aid)["src/pages/Home.tsx"]
    assert sorted(x["key"] for x in CL.schema(r)["lists"]) == ["notes", "orders"]
    assert out["brought_in"] == 3


def test_routes(ae_env, monkeypatch):
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]
    c = TestClient(main.app)
    h = {"Authorization": f"Bearer {KEY}"}
    assert c.get(f"/api/appengine/{aid}/branches").status_code == 401
    bid = c.post(f"/api/appengine/{aid}/branches", headers=h, json={"name": "Try"}).json()["id"]
    AE.write(T, bid, "src/pages/Home.tsx", _pg("Home", "Tried"))
    assert c.get(f"/api/appengine/{aid}/branches", headers=h).json()["branches"][0]["changes"]["incoming"] == 1
    assert c.get(f"/api/appengine/{aid}/branches/{bid}/compare", headers=h).json()["conflicts"] == []
    assert c.post(f"/api/appengine/{aid}/branches/{bid}/accept", headers=h, json={}).status_code == 403
    assert c.post(f"/api/appengine/{aid}/branches/{bid}/accept", headers=h, json={"confirm": True}).json()["accepted"]
    assert "Tried" in _src(aid)["src/pages/Home.tsx"]
    b2 = c.post(f"/api/appengine/{aid}/branches", headers=h, json={"name": "Two"}).json()["id"]
    assert c.delete(f"/api/appengine/{aid}/branches/{b2}", headers=h).status_code == 403
    assert c.delete(f"/api/appengine/{aid}/branches/{b2}?confirm=true", headers=h).json()["ok"]
    assert c.get(f"/api/appengine/{aid}/branches/{b2}/compare", headers=h).status_code == 404


def test_branches_in_the_studio(arena_server, ae_env):
    base, browser, key = arena_server
    from app.appengine import branches as BR
    from app.appengine import service as AE
    aid = AE.create(T, "Mithai orders")["id"]                  # plain calls: Playwright's loop is running here
    AE.write(T, aid, "src/pages/Menu.tsx", _pg("Menu", "Menu"))
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base}/console/web#/app/{aid}/branches")
    page.locator("[data-ae-form=br-new] input").wait_for(timeout=20000)
    page.fill("[data-ae-form=br-new] input", "Festive")
    page.click("[data-ae-form=br-new] button")
    page.locator(".ae-br b", has_text="Festive").wait_for(timeout=20000)
    bid = BR.open_of(AE._load(T, aid))[0].id
    AE.write(T, bid, "src/pages/Menu.tsx", _pg("Menu", "Diwali menu"))
    AE.write(T, aid, "src/pages/Menu.tsx", _pg("Menu", "Plain menu"))
    AE.write(T, bid, "src/pages/Offers.tsx", _pg("Offers", "Offers"))
    page.click("[data-ae-br=compare]")
    page.locator("#aeBrCmp .dfc legend", has_text="src/pages/Menu.tsx").wait_for(timeout=20000)
    page.click("[data-ae-br=accept]")                          # no choice yet: told, nothing sent
    page.wait_for_timeout(300)
    assert "src/pages/Offers.tsx" not in _src(aid)
    page.check("#aeBrCmp .dfc input[value=branch]")
    page.click("[data-ae-br=accept]")
    page.locator("button", has_text="Accept the branch").click()
    for _ in range(40):
        if "src/pages/Offers.tsx" in _src(aid):
            break
        page.wait_for_timeout(250)
    s = _src(aid)
    assert "src/pages/Offers.tsx" in s and "Diwali menu" in s["src/pages/Menu.tsx"]
    # the branch's own workspace says it is one and offers no Publish
    b2 = BR.create(T, aid, "Look")["id"]
    page.goto(f"{base}/console/web#/app/{b2}")
    page.locator("#aeBranchPill", has_text="Branch: Look").wait_for(timeout=20000)
    assert page.locator("#aeTop button[data-ae-tab=publish]").count() == 0
    assert page.locator("#aeTabs [data-ae-tab=publish]").count() == 0
    ctx.close()
    assert not errors, errors


# ---------------------------------------------------------------- E8: looks with their own bodies
def _small_site(site_env, monkeypatch, cap="40"):
    monkeypatch.setenv("SITE_FULL_LOOKS", "true")
    monkeypatch.setenv("SITE_LOOK_OWN_BODIES", "true")
    monkeypatch.setenv("SITE_LOOK_OWN_BODIES_MAX", cap)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", "", name="Sharma Sweets")
    S.approve_plan(T, v["id"])
    return S, v["id"]


def test_small_site_looks_have_their_own_bodies(site_env, monkeypatch):
    from app.site import build as B
    S, sid = _small_site(site_env, monkeypatch)
    g = S.get(T, sid)
    assert g["status"] == "looks" and all(lk["full"] and lk["own_bodies"] for lk in g["looks"])
    plan = S._j(S._load(sid).plan, {})
    body = [S.sec_key(p["slug"], s["type"]) for p in plan["pages"] if p["slug"] != "home" for s in p["sections"]]
    assert body
    secs = [x[1] for x in site_env.calls if x[0] == "section"]
    for k in body:                                           # each look wrote every body section itself
        sid_ = S.sec_id(*k.split("__", 1))
        assert secs.count(sid_) == 3, (k, secs.count(sid_))
    # nothing in the site's own sections before she picks
    have = set(S._sections(S._load(sid)))
    assert not (have & set(body)), have & set(body)
    looks = B.site_dir(T, sid) / "looks"
    for i in range(3):
        for k in body:
            assert (looks / str(i) / f"{k}.json").is_file()
    # mark look 1's copy, pick look 1: that copy becomes the site, and the build writes no page again
    k0 = body[0]
    f1 = looks / "1" / f"{k0}.json"
    d = json.loads(f1.read_text())
    d["html"] = d["html"].replace(">", ' data-look-one="1">', 1)
    f1.write_text(json.dumps(d))
    n = len(site_env.calls)
    S.choose_look(T, sid, 1)
    again = [x for x in site_env.calls[n:] if x[0] == "section"]
    assert again == [], again
    assert 'data-look-one="1"' in S._sections(S._load(sid))[k0]["html"]


def test_above_the_cap_the_shared_body_rule_stays(site_env, monkeypatch):
    S, sid = _small_site(site_env, monkeypatch, cap="2")
    g = S.get(T, sid)
    assert all(lk["full"] and not lk["own_bodies"] for lk in g["looks"])
    secs = [x[1] for x in site_env.calls if x[0] == "section"]
    body = [x for x in secs if not x.startswith("s-home-")]
    assert body and len(body) == len(set(body))                # written once, shared by the three looks
