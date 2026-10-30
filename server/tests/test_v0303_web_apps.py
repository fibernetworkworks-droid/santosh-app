"""v0.303 WEB DESIGN PHASE 4, web apps like Lovable's backend: Opus designs the lists / fields / rules from her words
(cleaned to a fixed vocabulary), the site gets My account + a staff panel, members sign up / log in (PBKDF2, signed
tokens, revoked on a role change), every rule is enforced by the server (own rows, staff-only fields, roles), the owner
sees and edits everything from her console, and the version exports as a React + Vite project."""
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

T = "default"
DESIGN = {"say": "Customers apna order dekhenge, staff status badlega.", "signup": True, "collections": [
    {"key": "orders", "label": "Orders", "fields": [
        {"key": "item", "label": "Item", "type": "text", "required": True},
        {"key": "qty", "label": "Quantity", "type": "number"},
        {"key": "phone", "label": "Mobile", "type": "phone", "required": True},
        {"key": "status", "label": "Status", "type": "choice", "options": ["Naya", "Ban raha", "Taiyaar"], "default": "Naya",
         "admin_only": True},
        {"key": "id", "label": "bad reserved key", "type": "text"},
        {"key": "weird", "label": "Weird", "type": "hologram"},
        {"key": "pick", "label": "Pick", "type": "choice"}],
     "rules": {"create": "member", "read": "own", "update": "admin", "delete": "own"}},
    {"key": "notices", "label": "Notices", "fields": [{"key": "text", "type": "long_text"}],
     "rules": {"create": "admin", "read": "public", "update": "nuke", "delete": "admin"}}]}


def test_schema_is_cleaned_to_the_fixed_vocabulary():
    from app.site import webapp as W
    s = W.clean_schema(DESIGN)
    o = s["collections"][0]
    keys = [f["key"] for f in o["fields"]]
    assert keys == ["item", "qty", "phone", "status", "weird"]                 # reserved 'id' and an empty choice dropped
    assert o["fields"][-1]["type"] == "text" and o["fields"][3]["default"] == "Naya"
    assert s["collections"][1]["rules"]["update"] == "admin"                     # unknown rule -> the safe one
    assert W.clean_schema("junk") == {"collections": []}
    assert W.check_pw("secret123", W.hash_pw("secret123")) and not W.check_pw("x", W.hash_pw("secret123"))


@pytest.fixture
def app_site(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import service as S
    from app.site import webapp as W

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(W.DESIGN_SYSTEM[:40]):
            return json.loads(json.dumps(DESIGN))
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    W._RATE.clear()
    return v["id"]


def test_web_app_end_to_end(app_site):
    from app.main import app
    from app.site import build as B
    from app.site import service as S
    sid = app_site
    c = TestClient(app)
    ver = S.get(T, sid)["version"]
    r = c.post(f"/api/sites/{sid}/app-design", json={"words": "customers apna order track karein"}).json()
    assert "order" in r["say"].lower() and [x["key"] for x in r["app"]["collections"]] == ["orders", "notices"]
    g = S.get(T, sid)
    assert g["version"] == ver + 1 and g["app"][0]["label"] == "Orders"
    out = B.out_dir(T, sid, g["version"])
    home, acct, adm = (out / "index.html").read_text(), (out / "account" / "index.html").read_text(), (out / "admin" / "index.html").read_text()
    assert 'href="account/"' in home and 'href="admin/"' not in home                      # Account in the menu, staff page not
    assert f'name="hoola-app" content="/api/site-app/{sid}"' in acct and "assets/hoola-app.js" in acct
    assert 'data-hoola-app="form" data-c="orders"' in acct and 'data-hoola-app="list" data-c="notices"' in acct
    assert 'data-hoola-app="form" data-c="notices"' not in acct                           # notices: only staff create
    assert 'data-hoola-app="admin"' in adm and 'content="noindex"' in adm and (out / "assets" / "hoola-app.js").exists()
    # the public API
    base = f"/api/site-app/{sid}"
    pre = c.options(f"{base}/c/orders")
    assert pre.status_code == 204 and "Authorization" in pre.headers["access-control-allow-headers"]
    sch = c.get(f"{base}/schema").json()
    assert sch["signup"] is True and len(sch["collections"]) == 2
    assert c.post(f"{base}/signup", json={"email": "bad", "password": "longenough"}).status_code == 400
    assert c.post(f"{base}/signup", json={"email": "a@x.in", "password": "short"}).status_code == 400
    a = c.post(f"{base}/signup", json={"email": "Asha@x.in", "password": "asha-pass-1", "name": "Asha"}).json()
    b = c.post(f"{base}/signup", json={"email": "ravi@x.in", "password": "ravi-pass-1", "name": "Ravi"}).json()
    assert c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "asha-pass-1"}).status_code == 400   # same email
    assert c.post(f"{base}/login", json={"email": "asha@x.in", "password": "wrong-pass"}).status_code == 401
    ha = {"Authorization": "Bearer " + c.post(f"{base}/login", json={"email": "asha@x.in", "password": "asha-pass-1"}).json()["token"]}
    hb = {"Authorization": "Bearer " + b["token"]}
    assert c.get(f"{base}/me", headers=ha).json()["me"]["name"] == "Asha"
    assert c.post(f"{base}/c/orders", json={"item": "Kaju katli", "phone": "9876500000"}).status_code == 401   # login first
    row = c.post(f"{base}/c/orders", headers=ha, json={"item": "Kaju katli", "qty": "2", "phone": "+91 98765 00000",
                                                        "status": "Taiyaar"}).json()
    assert row["status"] == "Naya" and row["qty"] == 2 and row["phone"] == "9876500000" and row["mine"]   # her own 'Taiyaar' ignored
    assert c.post(f"{base}/c/orders", headers=ha, json={"item": "", "phone": "9876500000"}).status_code == 400
    c.post(f"{base}/c/orders", headers=hb, json={"item": "Laddoo", "phone": "9876500001"})
    assert [x["item"] for x in c.get(f"{base}/c/orders", headers=ha).json()["rows"]] == ["Kaju katli"]   # only her own
    assert c.get(f"{base}/c/orders").status_code == 401
    assert c.patch(f"{base}/c/orders/{row['id']}", headers=ha, json={"item": "X"}).status_code == 403    # update: admin only
    assert c.post(f"{base}/c/notices", headers=ha, json={"text": "Diwali offer"}).status_code == 403
    assert c.get(f"{base}/members", headers=ha).status_code == 403
    # the owner (her Hoola login) sees everything, changes the status, makes Ravi staff
    own = c.get(f"/api/sites/{sid}/app/rows/orders").json()["rows"]
    assert {x["item"] for x in own} == {"Kaju katli", "Laddoo"}
    assert c.patch(f"/api/sites/{sid}/app/rows/orders/{row['id']}", json={"status": "Ban raha"}).json()["status"] == "Ban raha"
    mem = c.get(f"/api/sites/{sid}/app/members").json()["members"]
    ravi = next(m for m in mem if m["email"] == "ravi@x.in")
    assert "pw" not in json.dumps(mem)
    c.post(f"/api/sites/{sid}/app/members/{ravi['id']}/role", json={"role": "staff"})
    assert c.get(f"{base}/me", headers=hb).json()["me"] is None                         # a new role = log in again
    hb = {"Authorization": "Bearer " + c.post(f"{base}/login", json={"email": "ravi@x.in", "password": "ravi-pass-1"}).json()["token"]}
    assert len(c.get(f"{base}/c/orders", headers=hb).json()["rows"]) == 2                # staff sees all
    assert c.patch(f"{base}/c/orders/{row['id']}", headers=hb, json={"status": "Taiyaar"}).json()["status"] == "Taiyaar"
    assert c.post(f"{base}/c/notices", headers=hb, json={"text": "Diwali offer"}).status_code == 200
    assert c.get(f"{base}/c/notices").json()["rows"][0]["text"] == "Diwali offer"        # public read, no login
    assert c.post(f"{base}/members/{a['me']['id']}/role", headers=hb, json={"role": "admin"}).status_code == 403   # staff != admin
    assert c.delete(f"{base}/c/orders/{row['id']}", headers=ha).status_code == 200        # delete: own
    c.post(f"{base}/logout", headers=ha)
    assert c.get(f"{base}/me", headers=ha).json()["me"] is None
    assert c.get(f"/api/site-app/nope/schema").status_code == 404


def test_signup_rate_limit_and_tokens_cannot_cross_sites(app_site):
    from app.main import app
    from app.site import service as S
    from app.site import webapp as W
    sid = app_site
    S.design_app(T, sid, "customers order track karein")
    c = TestClient(app)
    base = f"/api/site-app/{sid}"
    codes = [c.post(f"{base}/signup", json={"email": f"u{i}@x.in", "password": "password-1"}).status_code for i in range(7)]
    assert codes[:5] == [200] * 5 and codes[5] == 429
    tok = W.make_token(sid, W.SiteAppMember(id="mem_x", gen=0))
    assert W.member_of("another-site", tok) is None
    assert W.member_of(sid, tok[:-2] + "00") is None


def test_react_export(app_site):
    from app.site import service as S
    sid = app_site
    S.design_app(T, sid, "customers order track karein")
    r = S._load(sid)
    from app.site import build as B
    from app.site import reactx
    data = reactx.react_zip(B.out_dir(T, sid, r.version), "Sharma Sweets", S.app_api(r))
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    assert {"package.json", "index.html", "vite.config.js", "src/main.jsx", "src/hoola.js", "public/assets/site.css",
            "public/assets/hoola-app.js", "README.md"} <= names
    pages = [n for n in names if n.startswith("src/pages/")]
    assert len(pages) >= 4
    main = z.read("src/main.jsx").decode()
    assert 'path="/"' in main and 'path="/account/"' in main and "BrowserRouter" in main
    assert json.loads(z.read("package.json"))["dependencies"]["react"].startswith("^18")
    assert f"/api/site-app/{sid}" in z.read("src/hoola.js").decode()
    body = z.read(pages[0]).decode()
    assert "dangerouslySetInnerHTML" in body and "<script" not in body.split("const HTML")[1].split(";\n")[0]
    out = S.export(T, sid, "react")
    assert out["name"].endswith("-react.zip")


def test_tool_and_version():
    from app.agent import site_tools as ST
    assert "app" in ST.SITE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.303.0"
    assert "0.303.0+343" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
