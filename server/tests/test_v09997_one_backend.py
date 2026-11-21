"""B4 ONE BACKEND (owner: "LETS CONTINUE THE NEXT WORK" -> B4 of docs/research/lovable/03_backend_vs_hoola.md).

Before: three backends shared two tables - A = the v0.305 site engine, B = a website on App Sahayak's backend + logic,
C = Hoola Cloud for React App Engine apps on its own `ae:<app>:p|l` keys with no journal, backups, logic, OTP, 2FA or
sessions. Now C runs on B's engine (one App Sahayak project per app, a preview twin for the Studio), and A no longer
serves anything (an unlinked site joins B on its first call)."""
import json

from fastapi.testclient import TestClient

from tests.test_v0814_app_engine import _tool, ae_env  # noqa: F401  (fixture + helper)
from tests.test_v0827_hoola_cloud import ORDERS, _app, _live
from tests.test_v0305_web_apps import app_site  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.71"


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _key(r, ds):
    from app.appengine import cloud as CL
    return CL.key_of(r, ds)


def test_a_react_app_lives_on_the_one_backend(ae_env):
    from app.appengine import cloud as CL
    from app.appmaker import backend as BE
    from app.appmaker import service as AS
    from app.db import session
    from app.site import twin as TW
    from app.site import webapp as W
    aid, r = _app([ORDERS])
    live, prev = CL.data_project(r, "live"), CL.data_project(r, "preview")
    assert live.status == "engine" and CL.site_key(r, "live") == BE.bid(live)
    assert TW.of(prev) == live.id and CL.site_key(r, "preview") == BE.bid(prev) != BE.bid(live)
    assert [c["key"] for c in (json.loads(live.backend)["schema"]["collections"])] == ["orders"]
    assert CL.link(r).id == live.id                                     # idempotent: one project per app
    assert all(x["id"] != live.id for x in AS.apps(T))                # never in her App Sahayak app list
    # a visitor's write goes through the same engine as websites: journaled (backups + restore read the journal)
    r = _live(r)
    out = TestClient(__import__("app.main", fromlist=["app"]).app)
    k = _key(r, "live")
    a = out.post(f"/api/cloud/{k}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha"}).json()
    h = {"Authorization": "Bearer " + a["token"]}
    row = out.post(f"/api/cloud/{k}/create", headers=h, json={"list": "orders", "data": {"item": "Laddoo", "qty": 2}}).json()["row"]
    assert row["item"] == "Laddoo"
    with session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id=BE.bid(live)).count() == 1
        assert s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id.like("ae:%")).count() == 0
    from app.appmaker import backup as BK
    BK.ensure_table()
    with session() as s:
        n = s.execute(__import__("sqlalchemy").text("select count(*) from app_journal where site_id = :s"),
                      {"s": BE.bid(live)}).scalar()
    assert n >= 1
    # preview and live stay apart: the preview's sample rows never show in live
    assert out.post(f"/api/cloud/{k}/list", headers=h, json={"list": "orders"}).json()["rows"][0]["id"] == row["id"]
    assert all(x.get("sample") for x in CL.owner_rows(r, "preview", "orders"))


def test_old_ae_data_and_logins_move_over_once(ae_env):
    """An app made before B4: its rows + members sit under `ae:<app>:l`; the first call moves them, the old login works."""
    from app.appengine import cloud as CL
    from app.appmaker import backend as BE
    from app.db import session
    from app.site import webapp as W
    aid, r = _app()
    sch = {"version": 1, "signup": True, "lists": [{"key": "orders", "label": "Orders", "fields": [
        {"key": "item", "label": "Item", "type": "text", "required": True, "admin_only": False}],
        "rules": {"create": "member", "read": "own", "update": "own", "delete": "admin"}}]}
    CL._save_schema(r, sch)
    W.ensure_tables()
    old = CL.old_key(r, "live")
    a = W.signup(old, CL.core_schema(sch), "ravi@x.in", "ravi-pass-1", "Ravi", "1.2.3.4")
    W.create(old, CL.core_schema(sch), "orders", {"item": "Barfi"}, W.Who(W.member_of(old, a["token"])), "1.2.3.4")
    assert not CL._pid(r)
    r = _live(r)
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    h = {"Authorization": "Bearer " + a["token"]}
    me = c.post(f"/api/cloud/{_key(r, 'live')}/me", headers=h, json={}).json()["me"]
    assert me and me["email"] == "ravi@x.in"                           # the login made before the move still works
    rows = c.post(f"/api/cloud/{_key(r, 'live')}/list", headers=h, json={"list": "orders"}).json()["rows"]
    assert [x["item"] for x in rows] == ["Barfi"]
    with session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id=old).count() == 0
        assert s.query(W.SiteAppMember).filter_by(site_id=old).count() == 0
        assert s.query(W.SiteAppRow).filter_by(site_id=CL.site_key(r, "live")).count() == 1
    assert CL.site_key(r, "live") == BE.bid(CL.link(r))


def test_sessions_two_factor_and_approvals_reach_react_apps(ae_env, monkeypatch):
    from app.appengine import cloud as CL
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "secret_key", "test-secret-key-for-2fa-only-0123456789")   # the 2FA key is encrypted
    aid, r = _app([ORDERS])
    r = _live(r)
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    k = _key(r, "live")
    c.post(f"/api/cloud/{k}/signup", json={"email": "meera@x.in", "password": "meera-pass-1", "name": "Meera"})
    tok = c.post(f"/api/cloud/{k}/signin", json={"email": "meera@x.in", "password": "meera-pass-1"},
                 headers={"User-Agent": "Phone browser"}).json()["token"]
    h = {"Authorization": "Bearer " + tok}
    ses = c.post(f"/api/cloud/{k}/sessions", headers=h, json={}).json()["sessions"]
    assert ses and any(x.get("this") for x in ses)                    # this device marked
    two = c.post(f"/api/cloud/{k}/2fa_start", headers=h, json={})
    assert two.status_code == 403 and "staff and admin" in two.json()["detail"]        # as on websites: staff / admin only
    mid = c.post(f"/api/cloud/{k}/me", headers=h, json={}).json()["me"]["id"]
    CL.set_role(r, "live", mid, "staff")                                                # a new role = sign in again
    assert c.post(f"/api/cloud/{k}/me", headers=h, json={}).json()["me"] is None
    tok = c.post(f"/api/cloud/{k}/signin", json={"email": "meera@x.in", "password": "meera-pass-1"}).json()["token"]
    h = {"Authorization": "Bearer " + tok}
    two = c.post(f"/api/cloud/{k}/2fa_start", headers=h, json={}).json()
    assert two["secret"] and two["uri"].startswith("otpauth://totp/")
    assert c.post(f"/api/cloud/{k}/approvals", headers=h, json={}).json() == {"approvals": []}
    assert c.post(f"/api/cloud/{k}/signout_all", headers=h, json={}).status_code == 200
    assert c.post(f"/api/cloud/{k}/me", headers=h, json={}).json()["me"] is None          # ended = stops at once
    assert c.post(f"/api/cloud/{k}/sessions", json={}).status_code == 401
    sch = c.post(f"/api/cloud/{k}/schema", json={}).json()
    assert sch["dataset"] == "live" and "security" in sch
    otp = c.post(f"/api/cloud/{k}/otp_start", json={"phone": "9876500000"})
    assert otp.status_code == 503 and "sign in with email" in otp.json()["detail"]     # no SMS service = said, in English
    assert c.post(f"/api/cloud/{k}/nonsense", json={}).status_code == 400
    ov = CL.overview(r)
    assert ov["backend"]["linked"] and "phone OTP sign-in" not in ov["not_built"]


def test_the_data_project_is_hidden_and_goes_with_the_app(ae_env):
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    from app.appmaker.models import AppProject
    from app.db import session
    from app.site import webapp as W
    aid, r = _app([ORDERS])
    p = CL.link(r)
    prev = CL.data_project(r, "preview")
    src = (ROOT / "app/appmaker/service.py").read_text()
    assert src.count('"engine"') >= 2                                    # never in her App Sahayak app lists
    AE.delete_app(T, aid)
    with session() as s:
        assert s.get(AppProject, p.id) is None and s.get(AppProject, prev.id) is None
        assert s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id.in_(["app:" + p.id, "app:" + prev.id])).count() == 0


def test_the_old_site_engine_serves_nothing(app_site, monkeypatch):
    """Path A: a site that still has lists but no link joins the one backend on its first public call."""
    from app.config import get_settings
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    monkeypatch.setattr(get_settings(), "site_app_link", False)       # an OLD site: designed before sites linked at once
    S.design_app(T, app_site, "customers apna order track karein")
    assert AL.linked_id(S._load(app_site)) == ""
    c = TestClient(app)
    base = f"/api/site-app/{app_site}"
    assert c.get(f"{base}/schema").status_code == 200
    assert AL.linked_id(S._load(app_site))                               # joined on that first call
    a = c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha"}).json()
    assert c.get(f"{base}/approvals", headers={"Authorization": "Bearer " + a["token"]}).status_code == 200
    src = (ROOT / "app/site/applink.py").read_text()
    assert "the v0.305 engine, exactly as before" not in src and "W.signup(site_id" not in src


def test_shell_and_client_pins():
    shell = (ROOT / "app/appengine/shell.js").read_text()
    for op in ("otp_start", "'2fa_login'", "sessions", "signout_all", "approvals", "decide", "fn"):
        assert op in shell
    ts = (ROOT / "app/appengine/template/src/lib/hoola.ts").read_text()
    for k in ("phoneStart", "phoneVerify", "verifyCode", "signOutEverywhere", "need_2fa", "approvals:", "fn:"):
        assert k in ts
    assert "Runs on the same backend as your websites and phone apps" in (ROOT / "app/static/console/appengine.js").read_text()
    assert "([a-z0-9_]+)$" in (ROOT / "app/appengine/saboot.py").read_text()          # the in-browser check forwards every op
    main = (ROOT / "app/main.py").read_text()
    assert 'CL.call, key, op, args, tok, ip, request.headers.get("user-agent")' in main
