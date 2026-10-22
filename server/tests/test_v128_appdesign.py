"""v0.128 App Sahayak: 1 lakh app brief library -> plan card -> 3 Home-screen looks (real screenshots) -> every screen
designed (live board + thumbnails) -> checks in real Chromium on Android + iPhone looks (+ fix rounds) -> tap-through
prototype (public, signed, CSP) -> changes in her words -> 'Design pakka' only with the exact design hash.
The model is a fake that writes real screens with the app kit."""
import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def good_screen(sid, prompt):
    ids = re.search(r"SCREEN IDS you may link(?: with data-go)?: ([^\n]+?)\.?\n", prompt)
    ids = [x.strip() for x in ids.group(1).split(",")] if ids else ["home"]
    tab = "BOTTOM TAB" in prompt
    nxt = next((x for x in ("cart", "product_detail", "checkout", "payment", "order_success", "home") if x in ids and x != sid), ids[0])
    back = "" if tab else '<button class="ab-back" data-back aria-label="Back"></button>'
    links = "".join(f'<button class="li" data-go="{x}"><span class="li-lead"><i data-ic="chev-r"></i></span><span class="li-main">'
                    f'<span class="t-title">{x}</span></span></button>' for x in ids[:4] if x != sid)
    return {"html": f'<section id="scr-{sid}" class="scr"><header class="ab">{back}<h1 class="ab-title">Sharma {sid}</h1>'
                    f'<button class="ab-act" data-go="cart" data-cart aria-label="Cart"><i data-ic="cart"></i><span class="badge-dot">1</span></button>'
                    f'</header><div class="body"><div class="grid2" data-m="stagger"><div class="card" data-go="{nxt}"><div class="ph">'
                    f'<i data-ic="cake"></i></div><p class="t-title">Kaju katli</p><div class="row between"><span class="price">₹480</span>'
                    f'<button class="add-btn">ADD</button></div></div><div class="card"><div class="ph ph-2"><i data-ic="gift"></i></div>'
                    f'<p class="t-title">Gift box</p><p class="price"><em class="blank">[daam]</em></p></div></div>'
                    f'<div class="list">{links}</div></div><div class="bar"><button class="btn btn-primary grow" data-go="{nxt}">Aage badhiye</button></div></section>',
            "css": f"#scr-{sid} .card .t-title{{color:var(--c-primary-text)}}",
            "spec": {"purpose": f"{sid} of the sweet shop", "data": ["products"], "actions": [{"label": "Aage", "go": nxt, "does": "next"}],
                     "components": ["app bar", "grid", "list"]}, "notes": "ok"}


class FakeAI:
    def __init__(self, bad=None):
        self.calls = []
        self.bad = set(bad or ())
        self.change = None

    def __call__(self, system, prompt, max_tokens=7000):
        from app.appmaker import ai as AI
        if system.startswith(AI.CHANGE_SYSTEM[:40]):
            self.calls.append(("change", prompt))
            return self.change or {}
        sid = re.search(r"SCREEN_ID: scr-([\w-]+)", prompt).group(1)
        if system.startswith(AI.FIX_SYSTEM[:40]):
            self.calls.append(("fix", sid))
            return good_screen(sid, prompt)
        self.calls.append(("screen", sid, "LOOK" if "ONE of three alternative looks" in prompt else ""))
        if sid in self.bad:
            self.bad.discard(sid)
            return {"html": f'<section id="scr-{sid}"><div class="body"><div style="width:900px;height:20px;background:#eee">wide</div>'
                            f'<label class="field">Card number<input name="card"></label><label class="field">UPI PIN<input name="pin"></label>'
                            f'<button data-go="nowhere" style="width:20px;height:20px;padding:0">x</button>'
                            f'<img src="https://evil.example/a.png"><script>alert(1)</script><a href="javascript:alert(2)" onclick="x()">y</a>'
                            f'</div></section>', "css": "@import url(https://evil.example/a.css); p{color:red}"}
        return good_screen(sid, prompt)


@pytest.fixture
def app_env(env, monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DIR", str(tmp_path / "apps"))
    monkeypatch.setenv("APP_WORKER", "false")
    monkeypatch.setenv("APP_FONTS_FETCH", "false")
    monkeypatch.setenv("APP_FONTS_DIR", str(tmp_path / "fonts"))
    from app.appmaker import ai as AI
    fake = FakeAI(bad={"cart"})
    monkeypatch.setattr(AI, "ask_json", fake)
    monkeypatch.setattr(AI, "ask_edit", fake)
    return fake


# ---------------------------------------------------------------- 1. the library
def test_app_library_counts_understanding_and_rules(monkeypatch):
    monkeypatch.setenv("SEMANTIC_OFF", "1")
    from app.appmaker import library as L
    from app.appmaker import taxonomy as TX
    assert TX.check() == []
    c = L.counts()
    assert c["fields"] == 1000 and c["briefs"] == 160000 and c["goals"] == 10 and c["styles"] == 16
    assert c["screen_designs"] == 306 and c["screen_types"] == 57 and c["motion_presets"] == 100
    for q, field, goal in [("kirana ki app ghar pe delivery", "kirana", "shop"), ("मिठाई की दुकान का ऐप", "sweet_shop", "shop"),
                           ("gym app membership wala", "gym", "membership"), ("coaching classes ke liye app", None, "learning"),
                           ("restaurant app menu order", "restaurant", "food_order"), ("dant doctor app appointment", "dentist", "booking")]:
        u = L.understand(q)
        assert u["goal"] == goal, q
        if field:
            assert u["field"] == field, q
        assert len(set(u["styles"])) == 3
    shop = L.brief("kirana", "shop", "clean_commerce")
    assert shop["tabs"] == ["home", "categories", "cart", "orders", "profile"]
    assert {"consent", "seller_info", "privacy", "delete_account"} <= set(shop["code_screens"])
    assert "UPI" in shop["text"] and "card numbers, CVV or UPI PIN are NEVER" in shop["text"]
    clinic = L.brief("general_physician")
    assert clinic["goal"] == "booking" and any("5.1.1(ix)" in r for r in clinic["rules"])
    temple = L.brief("temple", "community") if "temple" in __import__("app.site.library", fromlist=["x"]).fields() else None
    if temple:
        assert "delete_account" not in temple["code_screens"] and "consent" not in temple["code_screens"]
    lux = L.brief("sweet_shop", "shop", "luxury_noir")
    assert lux["palettes"][0] == "midnight_gold"


# ---------------------------------------------------------------- 2. plan -> looks -> every screen -> checks -> prototype -> pakka
def test_full_flow_design_before_build(app_env):
    from app.appmaker import service as S
    from app.main import app
    c = TestClient(app)
    ctx = conv_ctx()
    v = S.new(T, "Sharma Sweets ki app, ghar pe delivery, order WhatsApp par", ctx.conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main road, Akot"})
    assert v["status"] == "planned" and v["field"] == "sweet_shop" and v["goal"] == "shop"
    assert any("UPI" in q for q in v["questions"]) and v["understood"]["goal"] == "Order & delivery"
    assert _events("app_board")[-1]["push"] is True
    S.answer(T, v["id"], {"upi_id": "sharma@okicici"})
    assert S.get(T, v["id"])["facts"]["upi_id"] == "sharma@okicici"
    # her Haan (and she drops one screen) -> 3 looks with real screenshots
    v = S.approve_plan(T, v["id"], ctx.conversation_id, drop=["offers", "home"])        # home can't be dropped
    v = S.get(T, v["id"])
    assert v["status"] == "looks" and len(v["looks"]) == 3 and all(lk["shots"].get("android") for lk in v["looks"])
    assert "offers" not in [s["id"] for s in v["plan"]["screens"]] and "home" in [s["id"] for s in v["plan"]["screens"]]
    assert len({lk["style"] for lk in v["looks"]}) == 3
    assert c.get(f"/api/apps/{v['id']}/shots/{v['looks'][0]['shots']['android']}").status_code == 200
    looks_calls = [x for x in app_env.calls if x[0] == "screen" and x[2] == "LOOK"]
    assert len(looks_calls) == 3
    # she picks look 2 with look 1's colours -> every screen designed, checked, fixed
    v = S.choose_look(T, v["id"], 1, 0, ctx.conversation_id)
    v = S.get(T, v["id"])
    assert v["status"] == "ready", v.get("error")
    assert v["version"] == 1 and v["checks"]["blocking"] == [] and v["checks"]["passed"] is True
    assert ("fix", "cart") in app_env.calls                               # the bad cart screen was fixed in a fix round
    screens = [s["id"] for s in v["plan"]["screens"]]
    designed = [x[1] for x in app_env.calls if x[0] == "screen" and x[2] == ""]
    assert "home" not in designed and set(designed) == set(screens) - {"home"}      # the chosen look's home is kept
    tiles = [t for p in v["board"]["pages"] for t in p["sections"]]
    assert all(t["state"] == "done" for t in tiles) and v["board"]["pct"] == 100
    assert sum(1 for t in tiles if t["thumb"]) >= len(screens) - 1
    assert v["board"]["overview"].get("android") and v["board"]["overview"].get("ios")
    for name in ("cart-android.jpg", "cart-ios.jpg", "privacy-ios.jpg", "thumb/home-android.jpg", "overview-android.jpg"):
        assert c.get(f"/api/apps/{v['id']}/shots/{name}").status_code == 200, name
    # the public prototype: every screen in one page, kit + proto, strict CSP, nothing from the network, no secrets
    tok = v["preview"].rstrip("/").split("/")[-1]
    r = c.get(f"/api/app-preview/{tok}/")
    assert r.status_code == 200 and "script-src 'self'" in r.headers["content-security-policy"]
    page = r.text
    for sid in screens + ["splash", "consent", "privacy", "delete_account", "seller_info", "notify_permission"]:
        assert f'data-screen="{sid}"' in page, sid
    assert "<script>alert" not in page and "evil.example" not in page and "javascript:" not in page
    assert "Card number" not in page and "UPI PIN<" not in page
    assert 'data-tabbed="1"' in page and 'class="tabbar"' in page and "sharma@okicici" not in page.split("seller_info")[0][-10:]
    assert "9876543210" in page                                            # seller details from her facts (code-made)
    assert c.get(f"/api/app-preview/{tok}/assets/proto.js").status_code == 200
    assert c.get(f"/api/app-preview/{tok}/all.html").status_code == 200
    assert c.get(f"/api/app-preview/{tok}/__shots/thumb/home-android.jpg").status_code == 200
    assert c.get(f"/api/app-preview/{tok}/../../etc/passwd").status_code == 404
    assert c.get("/api/app-preview/short/").status_code == 404
    # Design pakka: only with this exact design's hash, and the contract for the native build is frozen
    assert c.post(f"/api/apps/{v['id']}/approve", json={"hash": "nope"}).status_code == 400
    out = c.post(f"/api/apps/{v['id']}/approve", json={"hash": v["hash"]}).json()
    assert out["status"] == "approved" and out["approved"] is True
    spec = c.get(f"/api/apps/{v['id']}/spec").json()
    assert spec["approved"]["hash"] == v["hash"] and spec["tabs"][0] == "home"
    cart = next(s for s in spec["screens"] if s["id"] == "cart")
    assert cart["spec"]["purpose"] and "checkout" in cart["goes_to"] or cart["goes_to"]
    assert spec["tokens"]["primary"] and any(s.get("code") for s in spec["screens"])
    # a change in her words: only that screen is redesigned, the approval is cleared, new version
    app_env.change = {"say": "Cart mein coupon hata raha hoon", "screens": [{"id": "cart", "instruction": "coupon hatao"}]}
    n0 = len([x for x in app_env.calls if x[0] == "screen"])
    res = S.change(T, v["id"], "cart mein coupon hatao", ctx.conversation_id)
    assert "coupon" in res["say"].lower()
    v2 = S.get(T, v["id"])
    redone = [x[1] for x in app_env.calls[n0:] if x[0] == "screen"]
    assert redone == ["cart"] and v2["version"] == 2 and v2["status"] == "ready" and v2["approved"] is False


# ---------------------------------------------------------------- 3. sanitising + tools + API
def test_sanitizer_tools_and_api(app_env):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.appmaker import service as S
    from app.main import app
    s = S.clean_screen("cart", {"html": '<section><label class="field">CVV<input name="cvv"></label><input placeholder="Card number">'
                                       '<iframe src="https://x.example"></iframe><script>1</script><p onclick="x()">ok</p></section>',
                                "css": "@import url(https://e.example/a.css); .x{color:red}", "js": "fetch('/x')",
                                "spec": {"purpose": "p" * 400, "actions": [{"label": "Pay", "go": "payment"}, "junk"]}})
    h = s["html"]
    assert 'id="scr-cart"' in h and 'class="scr"' in h and 'data-screen="cart"' in h
    assert "cvv" not in h.lower() and "Card number" not in h and "iframe" not in h and "<script" not in h and "onclick" not in h
    assert "@import" not in s["css"] and s["css"].startswith("#scr-cart") and len(s["spec"]["purpose"]) <= 160
    assert s["spec"]["actions"] == [{"label": "Pay", "go": "payment", "does": ""}]
    ctx = conv_ctx()
    owner = Ctx(T, ctx.conversation_id, actor="owner")
    staff = Ctx(T, ctx.conversation_id, actor="staff:asha")
    out = asyncio.run(dispatch("app_banao", {"action": "new", "brief": "clinic ka app appointment ke liye", "name": "Patil Clinic"}, owner))
    assert out["status"] == "planned" and out["goal_label"] == "Bookings & appointments"
    from app.appmaker import library as L
    assert any("5.1.1(ix)" in r for r in L.brief(S.get(T, out["id"])["field"], "booking")["rules"])
    with pytest.raises(ToolError):
        asyncio.run(dispatch("app_banao", {"action": "approve", "app": out["number"]}, staff))
    with pytest.raises(ToolError):
        asyncio.run(dispatch("app_banao", {"action": "approve", "app": out["number"]}, owner))     # not designed yet
    u = asyncio.run(dispatch("app_dekho", {"what": "understand", "q": "kirana ki app"}, owner))
    assert u["field"] == "kirana" and u["goal"] == "shop"
    b = asyncio.run(dispatch("app_dekho", {"what": "brief", "field": "gym", "goal": "membership"}, owner))
    assert "member_card" in b["screens"] and b["id"].startswith("gym.membership.")
    c = TestClient(app)
    allv = c.get("/api/apps").json()
    assert allv["library"]["briefs"] == 160000 and allv["apps"][0]["number"] == out["number"]
    assert c.get("/api/apps-library?q=salon").json()["fields"][0]["goal"] == "booking"
    assert c.post(f"/api/apps/{out['id']}/look", json={"index": 0}).status_code == 400          # no looks yet
    assert c.post("/api/apps", json={"brief": "SBI jaisi app jismein OTP daalein"}).status_code == 400
    assert c.delete(f"/api/apps/{out['id']}").json()["ok"] is True
    assert c.get(f"/api/apps/{out['id']}").status_code == 400
    assert json.dumps(_events("app_board"))
