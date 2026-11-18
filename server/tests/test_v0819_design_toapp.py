"""v0.819 D7 bridge C - DESIGN -> APP STUDIO (docs/HOOLA_DESIGN_PLAN.md section 7 C).

Phone frames are read as screens (structure, colours, fonts, spacing, prototype links) and handed to App Studio
through its own inputs: each frame's structure becomes the matched screen's design line in the app's plan, a new app
starts through App Studio's own create path, an app past its look is drawn again by App Studio's own design run.
Never approved on her behalf, never a native build, never a store step."""
import base64
import io
import json

import pytest
from fastapi.testclient import TestClient

from app.design import toapp

H = {"Authorization": "Bearer kd"}
T = "default"
PAGE = "0:1"


def solid(c):
    return [{"type": "solid", "color": c, "opacity": 1, "visible": True}]


class Doc:
    def __init__(self):
        self.nodes = {"0:0": {"type": "DOCUMENT", "name": "Document"},
                      PAGE: {"type": "PAGE", "parent": "0:0", "idx": "V", "name": "Page 1"}}
        self.n = 10

    def add(self, parent, type_, **p):
        self.n += 1
        nid = f"1:{self.n}"
        self.nodes[nid] = {"type": type_, "parent": parent, "idx": f"a{self.n:04d}", **p}
        return nid

    def text(self, parent, chars, size=16, weight=400, **p):
        p.setdefault("fills", solid("#111111"))
        return self.add(parent, "TEXT", name=chars[:20], chars=chars, fontSize=size, fontWeight=weight, font="Inter", **p)


def phone_doc():
    d = Doc()
    # 1. Login: heading, body, two inputs, a button
    login = d.add(PAGE, "FRAME", name="Login", x=0, y=0, w=390, h=844, fills=solid("#FFFFFF"))
    d.text(login, "Welcome back", 28, 700, x=24, y=120, w=300, h=36)
    d.text(login, "Sign in with your phone number", 15, x=24, y=164, w=300, h=20)
    phone = d.add(login, "FRAME", name="Input / Phone", x=24, y=220, w=342, h=52, fills=solid("#F3F4F6"), radius=12)
    d.text(phone, "Phone number", 15, x=16, y=16, w=200, h=20)
    otp = d.add(login, "FRAME", name="OTP field", x=24, y=288, w=342, h=52, fills=solid("#F3F4F6"), radius=12)
    d.text(otp, "6 digit code", 15, x=16, y=16, w=200, h=20)
    btn = d.add(login, "FRAME", name="Button", x=24, y=372, w=342, h=52, fills=solid("#6D28D9"), radius=12,
                reactions=[])
    d.text(btn, "Send OTP", 16, 600, x=130, y=16, w=100, h=20, fills=solid("#FFFFFF"))
    # 2. Products: a top bar, 5 repeated cards in an auto-layout column, a bottom nav of 4 tabs
    home = d.add(PAGE, "FRAME", name="Products", x=440, y=0, w=390, h=844, fills=solid("#FAFAFA"))
    top = d.add(home, "FRAME", name="App bar", x=0, y=0, w=390, h=64, fills=solid("#FFFFFF"))
    d.text(top, "Fresh today", 20, 700, x=16, y=20, w=200, h=24)
    col = d.add(home, "FRAME", name="Cards", x=16, y=80, w=358, h=640, layout={"mode": "v", "gap": 12, "pad": [0, 0, 0, 0]})
    for i in range(5):
        card = d.add(col, "FRAME", name="Card", x=0, y=i * 120, w=358, h=108, fills=solid("#FFFFFF"), radius=16)
        d.add(card, "RECT", name="Photo", x=8, y=8, w=92, h=92, fills=[{"type": "image", "hash": "a" * 64, "mode": "fill"}])
        d.text(card, f"Item {i + 1}", 17, 600, x=112, y=16, w=200, h=22)
        d.text(card, "Rs 120", 14, x=112, y=44, w=100, h=18)
        b = d.add(card, "FRAME", name="Button", x=270, y=60, w=76, h=32, fills=solid("#6D28D9"), radius=8)
        d.text(b, "Add", 14, 600, x=24, y=6, w=30, h=18, fills=solid("#FFFFFF"))
    nav = d.add(home, "FRAME", name="Tab bar", x=0, y=764, w=390, h=80, fills=solid("#FFFFFF"))
    for i, lab in enumerate(["Home", "Search", "Cart", "Profile"]):
        tab = d.add(nav, "FRAME", name=lab, x=i * 97, y=8, w=97, h=64)
        d.add(tab, "VECTOR", name="icon", x=36, y=4, w=24, h=24, path="M0 0L24 24")
        d.text(tab, lab, 11, x=20, y=36, w=60, h=14)
    # 3. Cart
    cart = d.add(PAGE, "FRAME", name="Cart", x=880, y=0, w=390, h=844, fills=solid("#FFFFFF"))
    d.text(cart, "Your cart", 24, 700, x=24, y=60, w=300, h=30)
    cb = d.add(cart, "FRAME", name="Checkout button", x=24, y=760, w=342, h=52, fills=solid("#6D28D9"), radius=12,
               reactions=[{"trigger": "click", "action": "back"}])
    d.text(cb, "Checkout", 16, 600, x=130, y=16, w=100, h=20, fills=solid("#FFFFFF"))
    # prototype: Send OTP -> Products, a card's Add -> Cart
    d.nodes[btn]["reactions"] = [{"trigger": "click", "action": "navigate", "to": home, "anim": {"type": "smart"}}]
    first_add = [k for k, v in d.nodes.items() if v.get("name") == "Button" and d.nodes[v["parent"]].get("name") == "Card"][0]
    d.nodes[first_add]["reactions"] = [{"trigger": "click", "action": "navigate", "to": cart}]
    # a desktop frame
    web = d.add(PAGE, "FRAME", name="Landing", x=0, y=1000, w=1440, h=900, fills=solid("#FFFFFF"))
    d.text(web, "Big headline", 48, 700, x=80, y=80, w=600, h=60)
    return d, {"login": login, "home": home, "cart": cart, "web": web}


def png(w=8, h=16):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (109, 40, 217)).save(buf, "PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- 1. reading frames as screens
def test_frames_to_screens_structure():
    d, f = phone_doc()
    out = toapp.frames_to_screens({"nodes": d.nodes}, [f["login"], f["home"], f["cart"]])
    login, home, cart = out["screens"]
    assert login["name"] == "Login" and login["size_class"] == "phone" and login["orientation"] == "portrait"
    kinds = [e["kind"] for e in login["elements"]]
    assert kinds == ["text", "text", "input", "input", "button"], login["elements"]
    assert login["elements"][0] == {"kind": "text", "role": "heading", "text": "Welcome back", "size": 28, "bold": True}
    assert login["elements"][1]["role"] == "body"
    assert login["elements"][2]["placeholder"] == "Phone number" and login["elements"][4]["text"] == "Send OTP"
    assert login["colors"]["background"] == "#FFFFFF" and "#6D28D9" in login["colors"]["accent"]
    assert "Inter" in login["fonts"]["families"] and 28 in login["fonts"]["sizes"]
    assert login["spacing"]["margin"] == 24 and 12 in login["spacing"]["radius"]
    # the list screen: top bar, a list of 5 cards (image + texts + a button), a bottom bar of 4 tabs
    assert [e["kind"] for e in home["elements"]] == ["nav", "list", "nav"], home["elements"]
    topbar, lst, nav = home["elements"]
    assert topbar["where"] == "top" and topbar["title"] == "Fresh today"
    assert lst["count"] == 5 and lst["direction"] == "v"
    item = lst["item"]
    assert item["kind"] == "box" and [e["kind"] for e in item["elements"]] == ["image", "text", "text", "button"]
    assert nav == {"kind": "nav", "where": "bottom", "count": 4, "items": ["Home", "Search", "Cart", "Profile"]}
    assert 12 in home["spacing"]["gaps"]
    # prototype links between the selected frames
    links = {(x["from"], x["to"], x["action"]) for x in out["links"]}
    assert (f["login"], f["home"], "navigate") in links and (f["home"], f["cart"], "navigate") in links
    assert (f["cart"], "", "back") in links
    assert login["links"] == [{"to": f["home"], "to_name": "Products", "action": "navigate", "via": "Send OTP"}]
    assert cart["elements"][-1] == {"kind": "button", "text": "Checkout"}
    words = toapp.design_text(home, "Shop app")
    assert "a list of 5" in words and "bottom navigation with 4 tabs (Home, Search, Cart, Profile)" in words
    assert "'Add' -> Cart" in words and len(words) <= toapp.DESIGN_MAX


def test_size_classes_and_bad_ids():
    d, f = phone_doc()
    out = toapp.frames_to_screens(d.nodes, [f["web"]])
    assert out["screens"][0]["size_class"] == "other" and "not a phone or tablet size" in out["warnings"][0]
    assert toapp.size_class(820, 1180) == ("tablet", "portrait") and toapp.size_class(844, 390) == ("phone", "landscape")
    with pytest.raises(toapp.BridgeError):
        toapp.frames_to_screens(d.nodes, ["9:999"])
    txt = [k for k, v in d.nodes.items() if v["type"] == "TEXT"][0]
    with pytest.raises(toapp.BridgeError, match="not a frame"):
        toapp.frames_to_screens(d.nodes, [txt])
    with pytest.raises(toapp.BridgeError):
        toapp.frames_to_screens(d.nodes, [])


def test_screen_matching():
    m = toapp.match_screen
    assert m("Login", [], []) == ("login", "name")
    assert m("Sign In", [], []) == ("login", "name")
    assert m("Products", [], []) == ("product_list", "name")
    assert m("Cart", [], []) == ("cart", "name")
    assert m("Screen 4", ["Enter OTP", "Verify"], []) == ("login", "content")
    assert m("Dashboard", [], ["home"]) == ("home", "name")
    assert m("Zzz blob", ["lorem"], []) == ("", "")


# ---------------------------------------------------------------- 2. the route, through App Studio
@pytest.fixture()
def bridge(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.appmaker import service as A
    from app.appmaker.android import service as AN
    from app.appmaker.ios import service as IO
    calls = {"start": [], "never": []}
    monkeypatch.setattr(A, "_start", lambda app_id, job, **kw: calls["start"].append((app_id, job, kw)))
    for mod, fn in ((AN, "build"), (IO, "build"), (A, "approve")):
        monkeypatch.setattr(mod, fn, lambda *a, _n=f"{mod.__name__}.{fn}", **k: calls["never"].append(_n))
    from app.appmaker.android import store as AS
    monkeypatch.setattr(AS, "build_bundle", lambda *a, **k: calls["never"].append("store.build_bundle"))
    yield calls
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def design_file(name="Sweet Shop"):
    from app.design import store
    d, f = phone_doc()
    from app.design.doc import dumps_nodes
    row = store.create_file(T, name, dumps_nodes(d.nodes), len(d.nodes))
    return row, f


def make_app():
    from app.appmaker import kit as K
    from app.appmaker import service as A
    v = A.new(T, "Sharma Sweets ki app, ghar pe delivery", name="Sharma Sweets", quiet=True)
    return v


def test_existing_app_ready_gets_screens_redrawn_never_approved(bridge):
    from app.appmaker import kit as K
    from app.appmaker import service as A
    c = client()
    v = make_app()
    A._save(v["id"], status="approved", approved_hash="abc", look={"tokens": K.tokens(v["style"], "paper_ink"), "from": 0})
    row, f = design_file()
    pic = base64.b64encode(png()).decode()
    r = c.post(f"/api/design/files/{row['id']}/to-app", headers=H,
               json={"nodes": [f["login"], f["home"], f["cart"]], "app": v["id"], "pictures": {f["login"]: pic}})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["url"] == f"/console/apps#/app/{v['id']}" and out["approved"] is False and out["redraw"] is True
    by = {s["name"]: s for s in out["screens"]}
    assert by["Login"]["screen"] == "login" and by["Products"]["screen"] == "product_list" and by["Cart"]["screen"] == "cart"
    assert all(s["state"] == "drawing" for s in out["screens"])
    assert by["Login"]["picture"] is True and by["Cart"]["picture"] is False
    # App Studio's own design run was asked for exactly these screens, with her frame as the owner's instruction
    (app_id, job, kw), = bridge["start"]
    assert app_id == v["id"] and job == "design" and set(kw["only"]) == {"login", "product_list", "cart"}
    assert "OWNER'S DESIGN" in kw["extra"]["product_list"] and "a list of 5" in kw["extra"]["product_list"]
    assert bridge["never"] == []                          # no approve, no native build, no store step
    # visible through App Studio's own read route: the design line on each screen of the plan
    got = c.get(f"/api/apps/{v['id']}", headers=H).json()
    designs = {s["id"]: s["design"] for s in got["plan"]["screens"]}
    assert "HER OWN DESIGN from Hoola Design" in designs["login"] and "button 'Send OTP'" in designs["login"]
    assert "bottom navigation with 4 tabs" in designs["product_list"]
    assert got["status"] == "designing"
    assert any("approval" in w for w in out["warnings"])
    keep = K.app_dir(T, v["id"]) / "from_design"
    assert (keep / "login.png").read_bytes() == png()
    man = json.loads((keep / "manifest.json").read_text())
    assert man["login"]["frame"] == f["login"] and man["login"]["picture"] is True


def test_existing_app_before_its_look_only_plan(bridge):
    c = client()
    v = make_app()                                       # status planned: no look chosen yet
    row, f = design_file()
    r = c.post(f"/api/design/files/{row['id']}/to-app", headers=H, json={"nodes": [f["login"], f["cart"]], "app": v["number"]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["redraw"] is False and bridge["start"] == [] and bridge["never"] == []
    assert {s["state"] for s in out["screens"]} == {"waiting_plan"}
    got = c.get(f"/api/apps/{v['id']}", headers=H).json()
    assert got["status"] == "planned"
    assert "Send OTP" in {s["id"]: s["design"] for s in got["plan"]["screens"]}["login"]


def test_new_app_through_app_studio_create(bridge):
    c = client()
    row, f = design_file("Sharma Sweets")
    before = c.get("/api/apps", headers=H).json()["apps"]
    r = c.post(f"/api/design/files/{row['id']}/to-app", headers=H,
               json={"nodes": [f["login"], f["home"], f["web"]], "brief": "mithai ki dukaan ki app, ghar pe delivery"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["app"]["created"] is True and out["app"]["status"] == "planned"
    listed = c.get("/api/apps", headers=H).json()["apps"]
    assert len(listed) == len(before) + 1 and listed[0]["id"] == out["app"]["id"]
    got = c.get(f"/api/apps/{out['app']['id']}", headers=H).json()
    assert got["name"] == "Sharma Sweets"
    designs = {s["id"]: s["design"] for s in got["plan"]["screens"]}
    assert "HER OWN DESIGN" in designs["login"] and "a list of 5" in designs["product_list"]
    assert any("not a phone or tablet" in w for w in out["warnings"])
    assert bridge["start"] == [] and bridge["never"] == []


def test_refusals_tenant_view_only_and_caps(bridge):
    from app import accounts
    from app.db import User, session
    c = client()
    row, f = design_file()
    url = f"/api/design/files/{row['id']}/to-app"
    assert c.post(url, json={"nodes": [f["login"]]}).status_code == 401          # signed out (a view-only link guest)
    share = c.post(f"/api/design/files/{row['id']}/share", headers=H, json={"role": "view"}).json()
    assert c.post(url, headers={"Authorization": f"Bearer {share['token']}"}, json={"nodes": [f["login"]]}).status_code == 401
    with session() as s:
        u = User(email="other@example.com", name="Other")
        s.add(u)
        s.flush()
        uid = u.id
    other = {"Authorization": f"Bearer {accounts.issue_session(uid)}"}
    assert c.post(url, headers=other, json={"nodes": [f["login"]]}).status_code == 404
    v = make_app()
    assert c.post(url, headers=H, json={"nodes": ["9:999"], "app": v["id"]}).status_code == 404
    assert c.post(url, headers=H, json={"nodes": [f["login"]], "app": "nope-app"}).status_code == 404
    big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * (toapp.PICTURE_MAX + 10)).decode()
    r = c.post(url, headers=H, json={"nodes": [f["login"]], "app": v["id"], "pictures": {f["login"]: big}})
    assert r.status_code == 413
    r = c.post(url, headers=H, json={"nodes": [f["login"]], "app": v["id"], "pictures": {f["login"]: base64.b64encode(b"hello").decode()}})
    assert r.status_code == 415
    r = c.post(url, headers=H, json={"nodes": [f["login"]], "app": v["id"], "pictures": {f["cart"]: base64.b64encode(png()).decode()}})
    assert r.status_code == 400
    assert bridge["never"] == []
    # trashed file
    c.delete(f"/api/design/files/{row['id']}", headers=H)
    assert c.post(url, headers=H, json={"nodes": [f["login"]], "app": v["id"]}).status_code == 404


def test_agent_tool_to_app(bridge):
    import asyncio
    from app.agent import design_tools as DT
    from app.agent.tools import Ctx
    v = make_app()
    row, f = design_file()
    out = asyncio.run(DT.hoola_design(Ctx(tenant_id=T, conversation_id=""), "to_app", file=row["id"],
                                      nodes=["Login", f["cart"]], app=v["id"]))
    assert out["status"] == "sent" and out["url"].endswith(f"#/app/{v['id']}")
    assert {s["screen"] for s in out["screens"]} == {"login", "cart"}
    assert "editor" in out["pictures_note"] and bridge["never"] == []


def test_her_design_reaches_app_studios_screen_writer(env, tmp_path, monkeypatch):
    """No stand-in for App Studio's run: its real design run draws the screen, and the prompt its screen writer gets
    carries her frame twice - as the screen's design line and as the owner's instruction. Approval stays hers."""
    import re
    from tests.test_v128_appdesign import good_screen
    for k, val in (("API_KEY", "kd"), ("DESIGN_DIR", str(tmp_path / "design")), ("APP_DIR", str(tmp_path / "apps")),
                   ("APP_WORKER", "false"), ("APP_FONTS_FETCH", "false"), ("APP_FONTS_DIR", str(tmp_path / "fonts"))):
        monkeypatch.setenv(k, val)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.appmaker import ai as AI
    from app.appmaker import kit as K
    from app.appmaker import service as A
    seen = []

    def fake(system, prompt, max_tokens=7000):
        sid = re.search(r"SCREEN_ID: scr-([\w-]+)", prompt).group(1)
        seen.append((sid, prompt))
        return good_screen(sid, prompt)
    monkeypatch.setattr(AI, "ask_json", fake)
    v = make_app()
    A._save(v["id"], status="ready", look={"tokens": K.tokens(v["style"], "paper_ink"), "from": 0})
    row, f = design_file()
    r = client().post(f"/api/design/files/{row['id']}/to-app", headers=H, json={"nodes": [f["login"]], "app": v["id"]})
    assert r.status_code == 200, r.text
    prompt = next(p for s, p in seen if s == "login")
    assert "Design: HER OWN DESIGN from Hoola Design" in prompt and "OWNER'S DESIGN" in prompt and "button 'Send OTP'" in prompt
    got = A.get(T, v["id"])          # ready, or failed where this machine has no Chromium for App Studio's checks
    assert got["status"] in ("ready", "failed") and got["approved"] is False
    get_settings.cache_clear()
