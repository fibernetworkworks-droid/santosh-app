"""v0.999.103 D8 wave 9: browser notifications on a React website - the same as her HTML website. On My account a signed-in
visitor taps "Notify me", the browser asks its own question, and her website's member app on Hoola keeps this browser's
address; her order moving, a team reply or her queue turn then reaches it. The worker that shows them is Hoola's locked
file, served from her website's own address. Signing out stops this browser's notifications. Under Hoola's address
(the sealed preview) it says it works on her own address."""
from __future__ import annotations

import base64
import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from app.appengine import rules as RL
from app.appengine import service as AE
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_82_own_address import _on  # noqa: F401  (autouse fixture)
from tests.test_v0999_91_live import _server, live_clinic  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

# Chromium treats a *.localhost address as secure (a worker may register there), as her real https address is
LOCAL = "sunrise-bakery.hoolasites.localhost"


@pytest.fixture(autouse=True)
def _local(_on, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SITES_BASE_DOMAIN", "hoolasites.localhost")
    from app.config import get_settings
    get_settings.cache_clear()
    yield


# ---------------------------------------------------------------- 1. by code
def test_the_worker_is_hoolas_locked_file_and_asks_only_on_her_tap():
    sw = (AE.TEMPLATE / "public" / "hoola-push-sw.js").read_text()
    assert "showNotification" in sw and "notificationclick" in sw and "addEventListener('fetch'" not in sw
    assert "public/hoola-push-sw.js" in RL.LOCKED and "public/hoola-push-sw.js" in AE.TOOLING
    member = (AE.TEMPLATE / "src" / "lib" / "member.ts").read_text()
    on = member.split("export async function pushOn")[1].split("export async function pushOff")[0]
    assert member.count("Notification.requestPermission") == 1 and "Notification.requestPermission" in on   # only her tap
    assert "consent: true" in on and 'scope: "/"' in on and "push/subscribe" in on
    assert '"sealed"' in member and "/api/" in member.split("export async function pushState")[1][:400]
    assert "await pushOff(site)" in member.split("export async function signOut")[1][:200]     # a shared computer stops
    rows = (AE.TEMPLATE / "src" / "islands" / "MemberRows.tsx").read_text()
    assert "pushOn(site)" in rows and "Notify me" in rows and "Stop notifications" in rows
    assert "<Notify site={site} />" in rows.split("function Account")[1]
    from app.appengine import image as IMG
    deps = set(IMG.project_package("x").get("dependencies") or {})
    assert RL.check_file("src/islands/MemberRows.tsx", rows, deps) == []
    assert "localStorage" not in rows and "Authorization" not in rows and "PushManager" not in rows


def test_the_checklist_ticks_browser_push():
    from app.appengine import parity
    st = {x["key"]: x for x in parity.check()["rows"]}
    assert st["push"]["state"] == "works", st["push"]
    assert st["ai"]["state"] == "partial"                                              # wave 10 built it (was "not yet")


# ---------------------------------------------------------------- 2. a real clinic website, live on its own address
def _keys() -> dict[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    pub = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    b = lambda x: base64.urlsafe_b64encode(x).decode().rstrip("=")   # noqa: E731
    return {"p256dh": b(pub), "auth": b(os.urandom(16))}


def test_a_visitor_turns_notifications_on_and_off_on_her_own_address(live_clinic):
    from playwright.sync_api import sync_playwright
    from app.main import app
    from app.site import webpush as WP
    sid = live_clinic
    c = TestClient(app)
    card = c.post(f"/api/sites/{sid}/launch-request", json={}).json()
    assert not card["blockers"], card["blockers"]
    assert c.post(f"/api/sites/{sid}/launch", json={"hash": card["hash"]}).status_code == 200
    sw = c.get("/hoola-push-sw.js", headers={"host": LOCAL})
    assert sw.status_code == 200 and "javascript" in sw.headers["content-type"] and b"showNotification" in sw.content
    asha = c.post(f"/api/site-app/{sid}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha",
                                                       "consent": True}).json()
    keys = _keys()
    ep = "https://fcm.googleapis.com/fcm/send/hoola-walk-" + keys["auth"][:8]
    # headless Chromium has no push service of its own: the browser's subscribe is answered with a real-shaped
    # subscription (Google's address, a real P-256 key); the worker and every server step are real
    fake = ("(() => { let sub = null; const mk = () => ({ endpoint: %s, toJSON: () => ({ endpoint: %s, keys: %s }),"
            " unsubscribe: async () => { sub = null; return true; } });"
            " PushManager.prototype.subscribe = async function () { sub = mk(); return sub; };"
            " PushManager.prototype.getSubscription = async function () { return sub; };"
            # headless Chromium answers every notification question with 'denied': the browser's own question is
            # answered 'granted' here, and counted - it must be asked only after her tap
            " let perm = 'default'; window.__asked = 0;"
            " Object.defineProperty(Notification, 'permission', { get: () => perm });"
            " Notification.requestPermission = async () => { window.__asked += 1; perm = 'granted'; return perm; }; })();"
            % (json.dumps(ep), json.dumps(ep), json.dumps(keys)))
    srv, port = _server()
    base = f"http://{LOCAL}:{port}"
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=[f"--host-resolver-rules=MAP {LOCAL} 127.0.0.1"],
                                   **({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            ctx = b.new_context(viewport={"width": 1280, "height": 900})
            ctx.grant_permissions(["notifications"], origin=base)
            ctx.add_init_script(f"localStorage.setItem({json.dumps('hoola:member:' + sid)}, {json.dumps(asha['token'])})")
            ctx.add_init_script(fake)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Error" in m.text else None)
            pg.goto(base + "/my-orders/", wait_until="load")
            box = pg.locator("[data-hoola-push]")
            box.wait_for(timeout=30000)
            assert box.get_attribute("data-hoola-push") == "off"
            assert pg.evaluate("window.__asked") == 0                                   # nothing asked on page load
            assert WP.has_subs(_bid(sid)) is False
            box.get_by_role("button", name="Notify me").click()
            box.get_by_text("Notifications are on for this browser.").wait_for(timeout=30000)
            assert pg.evaluate("window.__asked") == 1
            reg = pg.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration('/');
                return r ? { scope: r.scope, url: (r.active || r.waiting || r.installing).scriptURL } : null; }""")
            assert reg and reg["scope"] == base + "/" and reg["url"] == base + "/hoola-push-sw.js", reg
            rows = _subs(_bid(sid))
            assert [x.endpoint for x in rows] == [ep]
            # her order moves: Hoola encrypts the news for THIS browser and hands it to Google's push service
            sent: list[httpx.Request] = []
            WP.set_transport(httpx.MockTransport(lambda rq: (sent.append(rq), httpx.Response(201))[1]))
            try:
                assert WP.send(_bid(sid), [rows[0].member], "Order #12", "Ready for pickup.") == 1
            finally:
                WP.set_transport(None)
            assert str(sent[0].url) == ep and sent[0].headers["content-encoding"] == "aes128gcm"
            assert b"Ready for pickup" not in sent[0].content                            # Google only sees ciphertext
            box.get_by_role("button", name="Stop notifications").click()
            box.get_by_role("button", name="Notify me").wait_for(timeout=15000)
            assert _subs(_bid(sid)) == []
            b.close()
    finally:
        srv.should_exit = True
    assert not errors, errors


def _bid(sid: str) -> str:
    from app.appmaker import backend as BE
    from app.site import applink as AL
    from app.site import service as S
    return BE.bid(AL.project(S._load(sid)))


def _subs(site: str) -> list:
    from sqlalchemy import select
    from app.db import session
    from app.site import webpush as WP
    WP.ensure_table()
    with session() as s:
        return list(s.scalars(select(WP.SitePushSub).where(WP.SitePushSub.site_id == site)).all())
