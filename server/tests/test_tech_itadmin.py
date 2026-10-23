"""IT Admin Sahayak: licences + renewal windows + free seats, people & access register (no secrets), joiner / mover / leaver with
change cards, her tap as the ONLY approval (hash checked), Microsoft Graph + Google Workspace read-only sync with fake transports,
the exact API call sent only after her tap in manage mode, guides (model + fallback, versions, EXIF-free screenshots) and staff
questions (guide / access request card / helpdesk ticket), access review, tick, tools and API."""
import asyncio
import io
import json
from datetime import date, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.helpdesk.models  # noqa: F401
import app.itadmin.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def ia(env, monkeypatch, tmp_path):
    from app.helpdesk import service as H
    from app.itadmin import connectors as K
    from app.itadmin import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(H, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "model_steps", lambda topic, words: None)
    monkeypatch.setattr(S, "DATA_ROOT", tmp_path / "itadmin")
    S.EVENTS = events
    yield S
    K.set_http(None)


def kinds(S):
    return [k for k, _ in S.EVENTS]


class Fake:
    """Fake Google + Microsoft admin APIs. Records every request."""

    def __init__(self):
        self.calls = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        u = str(req.url)
        body = req.content.decode() if req.content else ""
        self.calls.append((req.method, u, body))
        if "login.microsoftonline.com" in u and u.endswith("/token"):
            if "client_secret=bad" in body:
                return httpx.Response(401, json={"error": "invalid_client", "error_description": "bad secret"})
            return httpx.Response(200, json={"access_token": "ms-tok", "expires_in": 3600})
        if u.startswith("https://graph.microsoft.com/v1.0/subscribedSkus"):
            return httpx.Response(200, json={"value": [{"skuId": "sku-basic", "skuPartNumber": "O365_BUSINESS_ESSENTIALS", "appliesTo": "User",
                                                        "consumedUnits": 3, "prepaidUnits": {"enabled": 5}}]})
        if u.startswith("https://graph.microsoft.com/v1.0/users?"):
            return httpx.Response(200, json={"value": [
                {"id": "u1", "displayName": "Ramesh Patil", "userPrincipalName": "ramesh@ingle.in", "mail": "ramesh@ingle.in",
                 "accountEnabled": True, "assignedLicenses": [{"skuId": "sku-basic"}], "jobTitle": "Accountant"},
                {"id": "u2", "displayName": "Asha", "userPrincipalName": "asha@ingle.in", "mail": "asha@ingle.in",
                 "accountEnabled": True, "assignedLicenses": [{"skuId": "sku-basic"}]},
                {"id": "u3", "displayName": "Guest", "userPrincipalName": "x_gmail.com#EXT#@ingle.in", "accountEnabled": True}]})
        if "deviceManagement/managedDevices" in u:
            return httpx.Response(403, json={"error": {"code": "Forbidden", "message": "Intune licence nahi"}})
        if "directoryRoles" in u:
            return httpx.Response(200, json={"value": [{"displayName": "Global Administrator", "members": [{"id": "u2"}]}]})
        if req.method == "PATCH" and u.startswith("https://graph.microsoft.com/v1.0/users/"):
            return httpx.Response(204)
        if u == "https://oauth2.googleapis.com/token":
            sc = " ".join(["openid", "email", "https://www.googleapis.com/auth/admin.directory.user.readonly",
                           "https://www.googleapis.com/auth/admin.directory.device.mobile.readonly",
                           "https://www.googleapis.com/auth/apps.licensing", "https://www.googleapis.com/auth/admin.directory.user"])
            return httpx.Response(200, json={"access_token": "g-tok", "refresh_token": "g-ref", "expires_in": 3600, "scope": sc})
        if "openidconnect.googleapis.com" in u:
            return httpx.Response(200, json={"email": "admin@ingle.in"})
        if u.startswith("https://admin.googleapis.com/admin/directory/v1/users?"):
            return httpx.Response(200, json={"users": [
                {"id": "g1", "primaryEmail": "ramesh@ingle.in", "name": {"fullName": "Ramesh Patil"}, "isAdmin": False,
                 "suspended": False, "isEnrolledIn2Sv": True, "lastLoginTime": "2026-10-20T10:00:00.000Z"},
                {"id": "g2", "primaryEmail": "admin@ingle.in", "name": {"fullName": "Meghana"}, "isAdmin": True, "isEnrolledIn2Sv": False,
                 "lastLoginTime": "2026-10-22T10:00:00.000Z"}]})
        if "devices/mobile" in u:
            return httpx.Response(200, json={"mobiledevices": [{"serialNumber": "R58N1234", "model": "Galaxy A35", "os": "Android 15",
                                                                 "name": ["Ramesh Patil"]}]})
        if "devices/chromeos" in u:
            return httpx.Response(403, json={"error": {"message": "Not authorized"}})
        if u.startswith("https://licensing.googleapis.com/apps/licensing/v1/product/Google-Apps/users"):
            return httpx.Response(200, json={"items": [{"skuId": "1010020027", "skuName": "Google Workspace Business Starter", "userId": "ramesh@ingle.in"},
                                                       {"skuId": "1010020027", "skuName": "Google Workspace Business Starter", "userId": "admin@ingle.in"}]})
        if req.method == "PATCH" and u.startswith("https://admin.googleapis.com/admin/directory/v1/users/"):
            return httpx.Response(200, json={"suspended": True})
        return httpx.Response(404, json={"error": {"message": "unknown " + u}})


def test_rules():
    from app.itadmin import rules as R
    assert R.kind_of("Microsoft 365 Business Basic") == "m365" and R.kind_of("TallyPrime TSS") == "tally"
    assert R.kind_of("Quick Heal Total Security") == "antivirus" and R.kind_of("abc", "ssl") == "ssl"
    assert R.window_due(25, [60, 30, 15, 7, 1, 0], []) == 30
    assert R.window_due(25, [60, 30, 15, 7, 1, 0], [30]) is None and R.window_due(5, [60, 30, 7], [30]) == 7
    assert R.window_due(90, [60, 30], []) is None
    w = R.seat_waste(10, 7, 145.0, "month", True)
    assert w == {"free": 3, "rupees_year": 5220}
    assert R.seat_waste(10, 10, 100, "month", True) is None and R.seat_waste(5, 2, None, "year", False)["rupees_year"] is None
    api = R.change_api("user_disable", "microsoft", "u1")
    assert api == {"method": "PATCH", "url": "https://graph.microsoft.com/v1.0/users/u1", "body": {"accountEnabled": False}}
    assert R.change_api("user_disable", "google", "a@b.in")["body"] == {"suspended": True}
    assert R.change_api("licence_remove", "microsoft", "u1", "sku")["body"] == {"addLicenses": [], "removeLicenses": ["sku"]}
    assert R.change_api("user_create", "google", "a@b.in") == {} and R.change_api("password_reset", "microsoft", "u1") == {}
    assert R.change_api("user_disable", "manual", "x") == {}
    assert R.ACCESS_REQ.search("mujhe Tally ka access chahiye") and R.ACCESS_REQ.search("password reset kar do")
    assert R.SECRET_ASK.search("wifi ka password batao") and not R.ACCESS_REQ.search("printer kaise lagaye")
    f = R.review_flags({"level": "admin", "mfa": "no", "shared": True, "last_login": "2026-01-01"}, {"status": "left"}, date(2026, 10, 23))
    assert {"admin rights", "admin bina 2-step", "shared login", "90 din se login nahi", "insaan office chhod chuka / chhod raha"} <= set(f)
    assert R.quarter_of(date(2026, 10, 23)) == "R-2026-Q4"
    assert any(p["id"] == "logs_180" for p in R.practices_list())


def test_licences_renewals_and_tick(ia):
    S = ia
    S.save_settings(T, org_name="Ingle Traders", windows=[30, 7, 0])
    on = S.today(T)
    a = S.save_licence(T, name="Microsoft 365 Business Basic", seats_bought=10, seats_used=7, cost=145, cost_per="month",
                       per_seat=True, renews_on=(on + timedelta(days=20)).isoformat(), auto_renew=True)
    assert a["licence"]["kind"] == "m365" and a["licence"]["waste"]["rupees_year"] == 5220 and "3 seat khaali" in a["say"]
    b = S.save_licence(T, name="TallyPrime TSS", cost=4500, renews_on=(on + timedelta(days=5)).isoformat())
    assert "Auto-renew on hai ya off" in b["say"]
    with pytest.raises(S.ItadminError):
        S.save_licence(T, name="X", renews_on="kal")
    r = S.renewals(T, 30)
    assert [x["number"] for x in r["licences"]] == ["L-002", "L-001"] and r["save_year"] == 5220
    S.EVENTS.clear()
    S.tick()
    S.tick()
    ren = [p for k, p in S.EVENTS if k == "itadmin_renewal"]
    assert len(ren) == 2 and any("seat khaali" in p["say"] for p in ren)
    with pytest.raises(S.ItadminError):
        S.renewed(T, "L-002", actor="staff:tm_1")
    out = S.renewed(T, "L-002", cost=5400)
    assert out["rise_pct"] == 20 and "20%" in out["say"]
    assert S.licences(T, "tally")[0]["renews_on"] == (on + timedelta(days=5)).replace(year=on.year + 1).isoformat()
    assert [k for k, _ in S.EVENTS].count("itadmin_day") == 1


def test_people_access_leaver_and_her_tap(ia):
    S = ia
    from app.helpdesk import service as H
    S.save_settings(T, standard_systems=["Tally", "Wi-Fi"])
    S.save_person(T, name="Ramesh Patil", email="ramesh@ingle.in", role="Accountant")
    H.save_asset(T, name="Accounts laptop", kind="laptop", user="Ramesh Patil", serial="5CD123")
    with pytest.raises(S.ItadminError):
        S.save_access(T, person="Ramesh Patil", system="Tally", account="ramesh", notes="password: Tally@123")
    S.save_access(T, person="Ramesh Patil", system="Tally", account="ramesh", level="admin")
    S.save_access(T, person="Ramesh Patil", system="Wi-Fi office", account="shared", shared=True)
    pv = S.person_view(T, "Ramesh")
    assert len(pv["access"]) == 2 and pv["devices"][0]["serial"] == "5CD123"
    S.EVENTS.clear()
    out = S.start_checklist(T, "Ramesh Patil", "leaver", when=S.today(T).isoformat())
    kinds_ = [i["kind"] for i in out["checklist"]["items"]]
    assert kinds_.count("account_disable") == 2 and "device_collect" in kinds_ and "password_rotate" in kinds_
    assert len(out["changes"]) == 3 and all(c["status"] == "waiting" and not c["by_api"] for c in out["changes"])
    assert kinds(S).count("itadmin_change") == 3 and "itadmin_checklist" in kinds(S)
    c = next(x for x in out["changes"] if x["kind"] == "user_disable" and x["system"] == "Tally")
    item = next(i for i in out["checklist"]["items"] if i.get("change") == c["id"])
    with pytest.raises(S.ItadminError):                       # change items can't be ticked by hand
        S.check_item(T, out["checklist"]["id"], item["id"], True)
    with pytest.raises(S.ItadminError):                       # only her tap
        S.decide_change(T, c["id"], True, c["hash"])
    with pytest.raises(S.ItadminError):
        S.decide_change(T, c["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.ItadminError):                       # not approved yet
        S.change_done(T, c["id"])
    d = S.decide_change(T, c["id"], True, c["hash"], by_tap=True)
    assert d["change"]["status"] == "approved" and "console" in d["say"]
    with pytest.raises(S.ItadminError):
        S.change_done(T, c["id"], actor="staff:tm_1")
    S.change_done(T, c["id"], True, "Tally mein band kiya")
    acc = {a["system"]: a for a in S.access_list(T, status="")}
    assert acc["Tally"]["status"] == "disabled"
    cl = S.checklists(T)[0]
    assert next(i for i in cl["items"] if i["id"] == item["id"])["done"]
    with pytest.raises(S.ItadminError):                       # still has active access -> can't forget
        S.forget_person(T, "Ramesh Patil")
    rot = next(x for x in out["changes"] if x["kind"] == "password_rotate")
    assert "chat" in " ".join(rot["steps"]).lower()
    assert S.decide_change(T, rot["id"], False, rot["hash"], "baad mein", by_tap=True)["change"]["status"] == "rejected"
    # tick on the last day: one leaver alert
    S.EVENTS.clear()
    S.tick()
    S.tick()
    assert kinds(S).count("itadmin_checklist") == 1


def test_microsoft_sync_and_api_change_on_tap(ia):
    S = ia
    from app.helpdesk import service as H
    from app.itadmin import connectors as K
    fake = Fake()
    K.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    with pytest.raises(K.ConnError):
        K.ms_save(T, "dir-1", "app-1", "bad")
    out = K.ms_save(T, "dir-1", "app-1", "s3cret-value", mode="manage")
    assert "adminconsent" in out["consent_url"]
    st = K.status(T)
    assert "s3cret" not in json.dumps(st) and st["microsoft"]["mode"] == "manage"
    from app.db import session
    from app.itadmin.models import ItadminConn
    with session() as s:
        assert "s3cret" not in s.get(ItadminConn, f"{T}:microsoft").secret_sealed
    r = S.sync(T, "microsoft")
    assert r["counts"]["users"] == 3 and "devices" in r["missing"] and "kuch badla nahi" in r["say"]
    lic = S.licences(T, "m365")[0]
    assert lic["seats_bought"] == 5 and lic["seats_used"] == 3 and lic["name"] == "Microsoft 365 Business Basic"
    acc = {a["account"]: a for a in S.access_list(T)}
    assert "x_gmail.com#ext#@ingle.in" not in acc and acc["asha@ingle.in"]["level"] == "admin"
    assert not [c for c in fake.calls if c[0] in ("PATCH", "POST") and "graph.microsoft.com" in c[1]]      # sync never writes
    S.sync(T, "microsoft")                                                                                   # idempotent
    assert len(S.people(T)) == 2 and len(S.licences(T)) == 1
    ch = S.request_change(T, "user_disable", access=acc["ramesh@ingle.in"]["id"])
    c = ch["change"]
    assert ch["needs_tap"] and c["by_api"] and c["api"] == {"method": "PATCH", "url": "https://graph.microsoft.com/v1.0/users/u1",
                                                            "body": {"accountEnabled": False}}
    assert not [x for x in fake.calls if x[0] == "PATCH"]
    assert S.request_change(T, "user_disable", access=acc["ramesh@ingle.in"]["id"])["change"]["id"] == c["id"]   # never asked twice
    d = S.decide_change(T, c["id"], True, c["hash"], by_tap=True)
    assert d["change"]["status"] == "done" and "admin API" in d["say"]
    patches = [x for x in fake.calls if x[0] == "PATCH"]
    assert len(patches) == 1 and json.loads(patches[0][2]) == {"accountEnabled": False}
    assert {a["account"]: a for a in S.access_list(T, status="")}["ramesh@ingle.in"]["status"] == "disabled"
    # read mode: the tap only approves, the API is never called
    K.ms_save(T, "dir-1", "app-1", "s3cret-value", mode="read")
    c2 = S.request_change(T, "user_signout", access=acc["asha@ingle.in"]["id"])["change"]
    d2 = S.decide_change(T, c2["id"], True, c2["hash"], by_tap=True)
    assert d2["change"]["status"] == "approved" and "khud" in d2["say"] and not [x for x in fake.calls if "revokeSignInSessions" in x[1]]
    assert K.forget(T, "microsoft")["removed"] == "microsoft" and K.status(T)["microsoft"] is None
    assert H.assets(T) == []


def test_google_link_sync_and_change(ia, monkeypatch):
    S = ia
    from app.helpdesk import service as H
    from app.itadmin import connectors as K
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example")
    from app.config import get_settings
    get_settings.cache_clear()
    fake = Fake()
    K.set_http(httpx.Client(transport=httpx.MockTransport(fake)))
    url = K.google_start(T, "manage")
    from urllib.parse import parse_qs, urlparse
    scopes = parse_qs(urlparse(url).query)["scope"][0].split()
    assert "https://www.googleapis.com/auth/admin.directory.user.readonly" in scopes
    assert "https://www.googleapis.com/auth/admin.directory.user" in scopes
    state = url.split("state=")[1].split("&")[0]
    assert K.is_link_state(state) and state.startswith("ita_m_")
    with pytest.raises(K.ConnError):
        K.google_finish("code", "ita_m_fake")
    v = K.google_finish("code", state)
    assert v["mode"] == "manage" and v["account"] == "admin@ingle.in"
    r = S.sync(T, "google")
    assert r["counts"] == {"users": 2, "licences": 1, "devices": 1} and "chromeos" in r["missing"]
    lic = S.licences(T, "workspace")[0]
    assert lic["seats_used"] == 2 and lic["seats_bought"] is None
    S.save_licence(T, lic["number"], seats_bought=5, cost=136, per_seat=True)
    assert S.licences(T, "workspace")[0]["waste"]["free"] == 3
    dev = H.assets(T)
    assert dev[0]["serial"] == "R58N1234" and dev[0]["user"] == "Ramesh Patil"
    acc = {a["account"]: a for a in S.access_list(T)}
    assert acc["admin@ingle.in"]["level"] == "admin" and acc["admin@ingle.in"]["mfa"] == "no"
    rv = S.start_review(T)["review"]
    flagged = {i["account"]: i["flags"] for i in rv["items"]}
    assert "admin bina 2-step" in flagged["admin@ingle.in"]
    with pytest.raises(S.ItadminError):
        S.review_item(T, rv["id"], acc["ramesh@ingle.in"]["id"], "remove", actor="staff:tm_1")
    out = S.review_item(T, rv["id"], acc["ramesh@ingle.in"]["id"], "remove")
    c = out["change"]
    assert c["kind"] == "user_disable" and c["api"]["url"].endswith("/users/ramesh@ingle.in") and c["api"]["body"] == {"suspended": True}
    with pytest.raises(S.ItadminError):
        S.close_review(T, rv["id"])
    S.review_item(T, rv["id"], acc["admin@ingle.in"]["id"], "keep")
    assert S.close_review(T, rv["id"])["review"]["status"] == "done"
    S.decide_change(T, c["id"], True, c["hash"], by_tap=True)
    g = [x for x in fake.calls if x[0] == "PATCH" and "admin.googleapis.com" in x[1]]
    assert len(g) == 1 and json.loads(g[0][2]) == {"suspended": True}
    # user creation / password: never by API, console steps only
    nc = S.request_change(T, "password_reset", person="Ramesh Patil", system="Google Workspace")["change"]
    assert not nc["by_api"] and any("khud" in x for x in nc["steps"])
    get_settings.cache_clear()


def test_guides_and_staff_questions(ia, monkeypatch):
    S = ia
    from PIL import Image
    g = S.write_guide(T, "Naye PC par office email lagana", "Outlook kholo. File > Add account. Apna email ramesh@ingle.in daalo "
                      "phir apna password daalo. Password is Abc@123 kabhi share mat karo")
    gv = g["guide"]
    assert gv["number"] == "G-001" and len(gv["steps"]) >= 3 and "Abc@123" not in json.dumps(gv)
    # the model adding a fact that is not in her words is thrown away
    monkeypatch.setattr(S, "model_steps", lambda topic, words: ["Kholo https://evil.example", "Login karo"])
    g2 = S.write_guide(T, "Printer lagana", "Settings mein Printers kholo, Add printer dabao, HP chuno")
    assert "evil" not in json.dumps(g2["guide"]["steps"])
    monkeypatch.setattr(S, "model_steps", lambda topic, words: ["Settings > Printers kholiye", "Add printer dabaiye", "HP chuniye"])
    g3 = S.write_guide(T, "Printer lagana", "Settings mein Printers kholo, Add printer dabao, HP chuno", guide=g2["guide"]["id"])
    assert g3["guide"]["version"] == 2 and g3["guide"]["steps"][0]["text"].startswith("Settings")
    assert S.restore_version(T, g2["guide"]["id"], 1)["guide"]["version"] == 3
    img = Image.new("RGB", (40, 30), "red")
    ex = img.getexif()
    ex[0x010F] = "SecretCam"
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=ex.tobytes())
    sh = S.add_shot(T, gv["id"], 1, buf.getvalue(), "s.jpg")
    data, mime = S.shot_bytes(T, sh["shot"])
    assert mime == "image/png" and b"SecretCam" not in data
    with pytest.raises(S.ItadminError):
        S.publish_guide(T, gv["id"], actor="staff:tm_1")
    S.publish_guide(T, gv["id"])
    a = S.ask(T, "naye laptop par email kaise lagaun?", person="Asha", actor="staff:tm_1")
    assert a["answer"] == "guide" and a["guide"]["number"] == "G-001"
    q = S.ask(T, "mujhe Tally ka access chahiye", person="Asha", actor="staff:tm_1")
    assert q["answer"] == "access_request" and q["change"]["status"] == "waiting" and "haan" in q["say"]
    assert S.ask(T, "wifi ka password batao")["answer"] == "refused"
    t = S.ask(T, "scanner se scan nahi ho raha", person="Asha", actor="staff:tm_1")
    assert t["answer"] == "ticket" and t["ticket"]["number"].startswith("HD-")
    S.ask(T, "scanner se scan nahi ho raha phir se", person="Asha")
    assert S.gaps(T)[0]["count"] >= 1
    assert S.guide_file(T, gv["id"])["file"]["name"].endswith(".docx")
    assert S.day(T)["waiting"]


def test_tools_and_api(ia):
    S = ia
    from app.agent import itadmin_tools as I
    from app.agent.tools import Ctx, ToolError
    assert {t["name"] for t in I.ITADMIN_TOOLS} == set(I.ITADMIN_HANDLERS) == set(I.ITADMIN_LABELS)
    enum = I.ITADMIN_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert not any(x in enum for x in ("approve", "decide"))
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(I.ITADMIN_HANDLERS[tool](c, **a))      # noqa: E731
    staff = Ctx(T, ctx.conversation_id, actor="staff:tm_1")
    run(ctx, "it_admin", action="licence", name="Quick Heal Total Security", seats_bought=5, renews_on="2027-01-10")
    with pytest.raises(ToolError):
        run(staff, "it_admin", action="settings", org_name="x")
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9198"), "it_admin_dekho", what="licences")
    run(ctx, "it_admin", action="person", name="Sunita", email="sunita@ingle.in")
    j = run(staff, "it_admin", action="joiner", person="Sunita")
    assert j["checklist"]["kind"] == "joiner"
    ch = run(staff, "it_admin", action="change", kind="admin_grant", person="Sunita", system="Tally")
    assert ch["needs_tap"]
    assert run(ctx, "it_admin_dekho", what="day")["waiting"]
    assert run(ctx, "it_admin_dekho", what="rules")["never_by_api"]
    from app.itadmin.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        o = cl.get("/api/itadmin").json()
        assert o["licences"] and o["people"] and o["changes"]
        cid, h = ch["change"]["id"], ch["change"]["hash"]
        assert cl.post(f"/api/itadmin/changes/{cid}/decide", json={}).status_code == 400
        assert cl.post(f"/api/itadmin/changes/{cid}/decide", json={"yes": True, "hash": "x"}).status_code == 400
        assert cl.post(f"/api/itadmin/changes/{cid}/decide", json={"yes": True, "hash": h}).json()["change"]["status"] == "approved"
        assert cl.post(f"/api/itadmin/changes/{cid}/done", json={"ok": True}).json()["change"]["status"] == "done"
        assert cl.post("/api/itadmin/licences", json={"name": ""}).status_code == 400
        assert cl.post("/api/itadmin/access", json={"system": "GST portal", "notes": "pin 4455"}).status_code == 400
        assert cl.post("/api/itadmin/ask", json={"text": "printer kaise lagaye"}).json()["answer"] in ("ticket", "unknown", "playbook")
        r = cl.post("/api/itadmin/guides", json={"topic": "Wi-Fi jodna", "steps": ["Wi-Fi list kholo", "Office-5G chuno"]}).json()
        gid = r["guide"]["id"]
        buf = io.BytesIO()
        from PIL import Image
        Image.new("RGB", (10, 10)).save(buf, "PNG")
        up = cl.post(f"/api/itadmin/guides/{gid}/shot", data={"n": "1"}, files={"file": ("a.png", buf.getvalue(), "image/png")})
        assert up.status_code == 200
        assert cl.get(f"/api/itadmin/shots/{up.json()['shot']}").headers["content-type"] == "image/png"
        assert cl.post(f"/api/itadmin/guides/{gid}/publish", json={}).status_code == 200
        assert cl.get("/api/itadmin/connections").json()["microsoft"] is None
        assert cl.post("/api/itadmin/sync", json={"provider": "google"}).status_code == 400
        assert cl.post("/api/itadmin/people/xyz/fired", json={}).status_code == 404
        assert cl.post("/api/itadmin/register").status_code == 200
        assert cl.post("/api/itadmin/reviews").json()["review"]["number"].startswith("R-")
