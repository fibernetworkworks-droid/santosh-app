"""v0.999.82 D8 wave 7: a React website's portal uses her website's OWN member app on Hoola - the same members, lists,
rules and sessions as her HTML website. The sign-in page signs a visitor in (email + password, a new account only with
the privacy tick, a phone code when SMS is set up, the authenticator step), the signed-in pages show the rows the rules
let them see and add rows where the rules allow, and My account signs out / gives a copy / deletes after a confirm.
On her own address the member app answers; the Studio preview uses the preview's own data (<site>~p)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.appengine import rules as RL
from app.appengine import service as AE
from app.appengine import writer as W
from app.site import rxhost as RH
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_82_own_address import HOST, _on  # noqa: F401  (autouse fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

def _portal():
    return [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Sunrise Bakery", "line": "Fresh bread every morning in Pune.", "cta": "Order now"},
        {"type": "contact_block", "heading": "Visit us", "items": []}]},
        {"slug": "sign-in", "title": "Sign in", "for": "public", "sections": [
            {"type": "screen_signin", "heading": "Sign in", "line": "Your orders in one place."}]},
        {"slug": "my-orders", "title": "My orders", "for": "member", "sections": [
            {"type": "screen_table", "heading": "Your orders", "line": "Every order you placed."},
            {"type": "screen_form", "heading": "Place an order", "line": "Tell us what you need."},
            {"type": "screen_dashboard", "heading": "At a glance", "line": ""},
            {"type": "screen_settings", "heading": "Your account", "line": ""}]}]


SITE = {"id": "site_abc123", "app": {"lists": [{"key": "notices", "label": "Notices"}, {"key": "orders", "label": "Orders"}]}}


# ---------------------------------------------------------------- 1. by code
def test_her_member_app_answers_on_her_own_address_only_for_her_site():
    assert RH.allowed("site_abc", "/api/site-app/site_abc/login")
    assert RH.allowed("site_abc", "/api/site-app/site_abc/c/orders")
    assert not RH.allowed("site_abc", "/api/site-app/site_abc~p/login")         # the preview's data: never on her address
    assert not RH.allowed("site_abc", "/api/site-app/site_xyz/login")
    assert not RH.allowed("site_abc", "/api/site-app/site_abcd/me")


def test_the_signed_in_screens_become_her_real_sign_in_and_rows():
    ctx = W.Ctx("Sunrise Bakery", _portal(), {"phone": "+91 90000 00001", "_site": SITE}, "s", None)
    assert ctx.signin == "./sign-in" and ctx.app_home == "./my-orders"
    code, rows = W.page_file(_portal()[1], ctx, {})
    assert 'import MemberSignIn from "@/islands/MemberSignIn";' in code
    assert 'site="site_abc123"' in code and 'next="./my-orders"' in code and "ScreenSignin" not in code
    code2, rows2 = W.page_file(_portal()[2], ctx, {})
    assert code2.count("<MemberRows ") == 4 and "ScreenTable" not in code2 and W.SAMPLE_ROWS_NOTE not in code2
    assert 'list="orders"' in code2.split('data-sec="my-orders:0"')[1].split("</div>")[0]   # her words name the list
    assert 'mode="add"' in code2 and 'mode="counts"' in code2 and 'mode="account"' in code2 and 'signin="./sign-in"' in code2
    assert [r["block"] for r in rows2] == ["member_rows", "member_add", "member_counts", "member_account"]
    kit = W.kit_files(rows + rows2, False)
    assert "src/islands/MemberSignIn.tsx" in kit and "src/islands/MemberRows.tsx" in kit
    assert not any("member" in k and "blocks" in k for k in kit)
    # no lists joined: the screens stay the kit's blocks with their marked sample rows
    bare = W.Ctx("Sunrise Bakery", _portal(), {"phone": "+91 90000 00001", "_site": {"id": "site_abc123"}}, "s", None)
    code3, _ = W.page_file(_portal()[2], bare, {})
    assert "MemberRows" not in code3 and W.SAMPLE_ROWS_NOTE in code3 and bare.signin == ""


def test_a_screen_takes_the_list_its_words_name_else_the_first():
    ctx = W.Ctx("x", _portal(), {"_site": SITE}, "s", None)
    assert W.list_for({"heading": "Latest notices"}, ctx) == "notices"
    assert W.list_for({"heading": "Your order history"}, ctx) == "orders"
    assert W.list_for({"heading": "Everything"}, ctx) == "notices"


def test_the_token_lives_only_in_hoolas_locked_member_file():
    from pathlib import Path
    assert "src/lib/member.ts" in RL.LOCKED and "src/lib/member.ts" in AE.TOOLING
    tpl = Path(AE.__file__).resolve().parent / "template"
    member = (tpl / "src" / "lib" / "member.ts").read_text()
    assert "~p" in member and "/api/app-preview/" in member and "Authorization" in member
    from app.appengine import image as IMG
    deps = set(IMG.project_package("x").get("dependencies") or {})
    for f in ("src/islands/MemberSignIn.tsx", "src/islands/MemberRows.tsx"):
        t = (tpl / f).read_text()
        assert "localStorage" not in t and "Authorization" not in t, f      # the islands never touch the token
        assert RL.check_file(f, t, deps) == [], (f, RL.check_file(f, t, deps))
    sign = (tpl / "src" / "islands" / "MemberSignIn.tsx").read_text()
    assert "tick the privacy notice first" in sign and "consent: true" in sign and '"2fa/login"' in sign


def test_the_checklist_ticks_portals():
    from app.appengine import parity
    st = {x["key"]: x for x in parity.check()["rows"]}
    assert st["portals"]["state"] == "works", st["portals"]


# ---------------------------------------------------------------- 2. a real React portal, live on its own address
@pytest.fixture
def live_portal(ae_env, monkeypatch):
    _box()
    from app.net import booking as BK
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    from app.site import webapp as WA
    from tests.test_v0305_web_apps import DESIGN
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    monkeypatch.setattr(BK, "free_slots", lambda tenant, n=12: ["2030-01-07T10:00"][:n])
    monkeypatch.setattr(BK, "say_slot", lambda tenant, iso: "Mon 7 Jan, " + iso[-5:])
    real = AI.ask_json

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(WA.DESIGN_SYSTEM[:40]):
            return json.loads(json.dumps(DESIGN))
        return real(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    v = S.new(T, "A website for Sunrise Bakery in Pune: breads, cakes, order online.", name="Sunrise Bakery",
              answers={"phone": "9876543210", "address": "12, Shanti Complex, Pune", "email": "hello@sunrise.example"})
    S.design_app(T, v["id"], "customers place and track their orders")
    WA._RATE.clear()
    PT._write_version(S._load(v["id"]), _portal(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"], out["react"]["id"]


def test_a_visitor_signs_up_adds_an_order_and_sees_only_hers(live_portal):
    from playwright.sync_api import sync_playwright
    from app.appengine import speed as SP
    from app.main import app
    sid, ref = live_portal
    c = TestClient(app)
    card = c.post(f"/api/sites/{sid}/launch-request", json={}).json()
    assert not card["blockers"], card["blockers"]
    assert c.post(f"/api/sites/{sid}/launch", json={"hash": card["hash"]}).status_code == 200
    page = c.get("/my-orders", headers={"host": HOST})
    assert page.status_code == 200 and "MemberRows" not in page.text            # pre-rendered: no data in the HTML
    assert c.get(f"/api/site-app/{sid}/schema", headers={"host": HOST}).json()["collections"]
    assert c.get(f"/api/site-app/{sid}~p/schema", headers={"host": HOST}).status_code == 404
    # someone else's order is never shown to her
    other = c.post(f"/api/site-app/{sid}/signup", json={"email": "ravi@x.in", "password": "ravi-pass-1", "name": "Ravi",
                                                         "consent": True}).json()
    c.post(f"/api/site-app/{sid}/c/orders", json={"item": "Ravi's cake", "phone": "9876500000"},
           headers={"Authorization": "Bearer " + other["token"]})
    import http.server
    import socketserver
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _go(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else None
            hd = {"host": HOST}
            for k in ("content-type", "authorization"):
                if self.headers.get(k):
                    hd[k] = self.headers[k]
            res = c.request(method, self.path, content=body, headers=hd)
            self.send_response(res.status_code)
            for k, v in res.headers.items():
                if k.lower() not in ("content-length", "transfer-encoding", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(res.content)))
            self.end_headers()
            try:
                self.wfile.write(res.content)
            except BrokenPipeError:
                pass

        def do_GET(self):  # noqa: N802
            self._go("GET")

        def do_POST(self):  # noqa: N802
            self._go("POST")
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    errors: list[str] = []

    def awake(pg):                                   # every island on the page has woken (React owns it)
        pg.wait_for_function(SP._AWAKE.replace(".filter(", ".every(").replace(").length", ")"), timeout=30000)
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(base + "/my-orders", wait_until="load")
            pg.get_by_text("Sign in to see this.").first.wait_for(timeout=20000)    # a visitor is sent to sign in
            pg.goto(base + "/sign-in", wait_until="load")
            awake(pg)
            pg.get_by_role("button", name="New here? Create an account").click()
            pg.get_by_label("Your name").fill("Asha")
            pg.get_by_label("Email").fill("asha@x.in")
            pg.get_by_label("Password").fill("asha-pass-1")
            pg.get_by_role("button", name="Create account").click()
            pg.get_by_role("alert").get_by_text("tick the privacy notice first").wait_for(timeout=5000)   # no tick, no account
            pg.get_by_role("checkbox", name="I agree to the privacy notice").click()
            pg.get_by_role("button", name="Create account").click()
            pg.wait_for_url("**/my-orders", timeout=20000)
            awake(pg)
            pg.get_by_text("Nothing in Orders yet.").first.wait_for(timeout=20000)
            assert pg.get_by_text("Ravi's cake").count() == 0                     # only her own rows
            form = pg.locator('[data-sec="my-orders:1"]')
            form.get_by_label("Item *").fill("Chocolate cake 1 kg")
            form.get_by_label("Mobile *").fill("9876543210")
            form.get_by_role("button", name="Add to Orders").click()
            pg.wait_for_timeout(1500)
            pg.reload(wait_until="load")
            awake(pg)
            pg.get_by_role("cell", name="Chocolate cake 1 kg").first.wait_for(timeout=20000)   # kept signed in, her row
            assert pg.get_by_text("Ravi's cake").count() == 0
            acct = pg.locator('[data-sec="my-orders:3"]')
            acct.get_by_role("button", name="Sign out", exact=True).click()
            pg.get_by_text("Sign in to see this.").first.wait_for(timeout=20000)
            assert pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hoola:member:'))") == []
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
    rows = c.get(f"/api/site-app/{sid}/c/orders", headers={"Authorization": "Bearer " + other["token"]}).json()["rows"]
    assert [r["item"] for r in rows] == ["Ravi's cake"]                              # the server's rules, not the page
