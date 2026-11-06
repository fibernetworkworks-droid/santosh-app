"""v0.459 ABHI ABHI WEBSITE (web Step 5 = W6 live features + W7 connectors of docs/WEB_PLATFORM_PLAN.md; checkpoint
"Clinic live queue + SMS reminders").

W6: a linked website's live channel (the native apps' SSE on the same project, filtered by each list's read rule, replay on
reconnect, the website's own login rule), live chat visitor <-> team, presence / typing, the clinic queue (tokens under the
app lock, a public board with NUMBERS ONLY, the patient's own place + wait, ONE 'turn near' per token through her approved
connector), browser notifications only after the visitor's tap + the browser's permission (RFC 8291 + RFC 8292 here).
W7: reminders before a booking (once per booking time, never a cancelled one), the queue trigger, HubSpot + Composio actions
(her own connected account, no secrets in the arguments), signed inbound webhooks on the website's own address."""
import base64
import hashlib
import hmac
import json
import struct
import threading
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import T, app_site  # noqa: F401  (fixture)
from tests.test_v0434_app_pages import _h, _signup, linked  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

PUBLIC = lambda host, port: [(2, 1, 6, "", ("93.184.216.34", port))]  # noqa: E731


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.616.0"


def _events(body: str) -> list[dict]:
    out = []
    for blk in body.split("\n\n"):
        data = "".join(ln[6:] for ln in blk.split("\n") if ln.startswith("data: "))
        ev = next((ln[7:] for ln in blk.split("\n") if ln.startswith("event: ")), "")
        if data:
            j = json.loads(data)
            j.setdefault("type", ev)
            out.append(j)
    return out


def _proj(site_id):
    from app.db import session
    from app.site import applink as AL
    from app.site.models import Site
    with session() as s:
        r = s.get(Site, site_id)
        s.expunge(r)
    p = AL.project(r)
    assert p is not None
    return p


def _staff(c, linked, email, name):
    base = f"/api/site-app/{linked}"
    _signup(c, base, email, name)
    mem = {m["email"]: m["id"] for m in c.get(f"/api/sites/{linked}/app/members").json()["members"]}
    c.post(f"/api/sites/{linked}/app/members/{mem[email]}/role", json={"role": "staff"})
    return c.post(f"{base}/login", json={"email": email, "password": "pass-word-1"}).json()["token"]


# ---------------------------------------------------------------- W6 browser notifications: the standards themselves
def _decrypt(body: bytes, ua_priv, auth: bytes) -> bytes:
    """RFC 8291 from the browser's side - proves our encryption is the standard one."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from app.site import webpush as WP
    salt, rs, idlen = body[:16], struct.unpack("!L", body[16:20])[0], body[20]
    as_pub_b = body[21:21 + idlen]
    ct = body[21 + idlen:]
    assert rs == 4096 and idlen == 65
    ua_pub_b = ua_priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    secret = ua_priv.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub_b))
    ikm = WP._hkdf(auth, secret, b"WebPush: info\x00" + ua_pub_b + as_pub_b, 32)
    cek = WP._hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = WP._hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    pt = AESGCM(cek).decrypt(nonce, ct, None)
    assert pt.endswith(b"\x02")
    return pt[:-1]


def _browser():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    from app.site import webpush as WP
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = bytes(range(16))
    return priv, auth, {"p256dh": WP.b64u(pub), "auth": WP.b64u(auth)}


def test_web_push_is_rfc8291_and_vapid_is_rfc8292():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

    from app.site import webpush as WP
    priv, auth, keys = _browser()
    msg = json.dumps({"title": "Order", "body": "Taiyaar hai"}).encode()
    body = WP.encrypt(msg, keys["p256dh"], keys["auth"])
    assert _decrypt(body, priv, auth) == msg
    assert WP.encrypt(msg, keys["p256dh"], keys["auth"]) != body                      # a fresh key + salt every message
    # VAPID: an ES256 JWT for the push service's origin, signed by the key the page subscribed with
    h = WP.vapid_header("https://fcm.googleapis.com/fcm/send/abc", at=1_000_000)
    tok, k = h.removeprefix("vapid t=").split(", k=")
    head, claims, sig = tok.split(".")
    assert k == WP.public_key() and json.loads(WP.unb64u(head)) == {"typ": "JWT", "alg": "ES256"}
    cl = json.loads(WP.unb64u(claims))
    assert cl["aud"] == "https://fcm.googleapis.com" and cl["exp"] == 1_000_000 + 12 * 3600 and cl["sub"].startswith("mailto:")
    raw = WP.unb64u(sig)
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), WP.unb64u(k))
    pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
               f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))                 # raises if wrong
    assert WP.public_key() == WP.public_key()                                          # derived, stable, never stored
    # only the browser makers' push services: a 'subscription' can never point the server at any other address
    for good in ("https://fcm.googleapis.com/fcm/send/x", "https://updates.push.services.mozilla.com/wpush/v2/x",
                 "https://web.push.apple.com/QX", "https://db5p.notify.windows.com/w/?token=x"):
        assert WP.host_ok(good), good
    for bad in ("http://fcm.googleapis.com/x", "https://evil.example/x", "https://127.0.0.1/x", "https://fcm.googleapis.com:8443/x",
                "https://user@fcm.googleapis.com/x", "https://notify.windows.com.evil.in/x"):
        assert not WP.host_ok(bad), bad


def test_push_needs_her_yes_sends_encrypted_and_forgets_a_closed_browser(linked):
    from app.appmaker import backend as BE
    from app.main import app
    from app.site import webpush as WP
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    tok = _signup(c, base, "meena@x.in", "Meena").json()["token"]
    assert c.get(f"{base}/schema").json()["live"] == {"queue": False, "push": True}
    key = c.get(f"{base}/push/key").json()["key"]
    assert key == WP.public_key()
    priv, auth, keys = _browser()
    ep = "https://fcm.googleapis.com/fcm/send/meena-1"
    assert c.post(f"{base}/push/subscribe", json={"endpoint": ep, "keys": keys}).status_code == 401           # login first
    assert c.post(f"{base}/push/subscribe", json={"endpoint": ep, "keys": keys}, headers=_h(tok)).status_code == 400   # no tap
    r = c.post(f"{base}/push/subscribe", json={"endpoint": "https://evil.example/x", "keys": keys, "consent": True}, headers=_h(tok))
    assert r.status_code == 400
    assert c.post(f"{base}/push/subscribe", json={"endpoint": ep, "keys": {"p256dh": "x", "auth": "y"}, "consent": True},
                  headers=_h(tok)).status_code == 400
    assert c.post(f"{base}/push/subscribe", json={"endpoint": ep, "keys": keys, "consent": True}, headers=_h(tok)).json()["on"] is True
    p = _proj(linked)
    me = c.get(f"{base}/me", headers=_h(tok)).json()["me"]["id"]
    got = []

    def hand(req: httpx.Request) -> httpx.Response:
        got.append(req)
        return httpx.Response(201 if len(got) == 1 else 410)
    WP.set_transport(httpx.MockTransport(hand))
    try:
        assert WP.send(BE.bid(p), [me], "Order 12", "Taiyaar hai", "/", "o12") == 1
        q = got[0]
        assert q.headers["content-encoding"] == "aes128gcm" and q.headers["ttl"] == str(WP.TTL)
        assert q.headers["authorization"].startswith("vapid t=") and str(q.url) == ep
        assert json.loads(_decrypt(q.content, priv, auth)) == {"title": "Order 12", "body": "Taiyaar hai", "url": "/", "tag": "o12"}
        assert b"Taiyaar" not in q.content                                              # the push service sees ciphertext only
        assert WP.send(BE.bid(p), [me], "x", "y") == 0                                  # 410: she turned it off
        assert WP.status(BE.bid(p))["browsers"] == 0
    finally:
        WP.set_transport(None)
    # deleting her account forgets her browsers too
    c.post(f"{base}/push/subscribe", json={"endpoint": ep, "keys": keys, "consent": True}, headers=_h(tok))
    assert WP.status(BE.bid(p))["browsers"] == 1
    c.post(f"{base}/me/delete", headers=_h(tok))
    assert WP.status(BE.bid(p))["browsers"] == 0


# ---------------------------------------------------------------- W6 live channel + chat on the website
def test_live_stream_on_the_website_is_filtered_and_replays(linked, monkeypatch):
    from app.appmaker import live as LV
    from app.appmaker.backup import AppJournal
    from app.db import session
    from app.main import app
    from sqlalchemy import select
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    assert c.get(f"{base}/live").status_code == 401                                   # no anonymous streams
    a = _signup(c, base, "asha@x.in", "Asha").json()["token"]
    n = _signup(c, base, "neha@x.in", "Neha").json()["token"]
    with session() as s:
        last = s.scalar(select(AppJournal.id).order_by(AppJournal.id.desc()).limit(1)) or 0
    oa = c.post(f"{base}/c/orders", json={"item": "Cake", "phone": "9876500002"}, headers=_h(a)).json()
    on = c.post(f"{base}/c/orders", json={"item": "Bread", "phone": "9876500001"}, headers=_h(n)).json()
    ravi = _staff(c, linked, "ravi@x.in", "Ravi")
    monkeypatch.setattr(LV, "STREAM_SECONDS", 1.0)
    evs = _events(c.get(f"{base}/live", headers={**_h(a), "Last-Event-ID": f"j{last}"}).text)
    assert evs[0]["type"] == "hello"
    rows = {e["id"] for e in evs if e["type"] == "row"}
    assert oa["id"] in rows and on["id"] not in rows                                    # 'own' list: only her order
    evs_r = _events(c.get(f"{base}/live?last=j{last}", headers=_h(ravi)).text)
    assert {oa["id"], on["id"]} <= {e["id"] for e in evs_r if e["type"] == "row"}       # staff hear every order
    # an ended login ends the stream on the website's own rule (old site-signed logins + ended sessions)
    from app.site import livesite as LS
    p = _proj(linked)
    me = c.get(f"{base}/me", headers=_h(a)).json()["me"]["id"]
    assert LS.still(linked, p, a, me) is True
    c.post(f"{base}/logout", headers=_h(a))
    assert LS.still(linked, p, a, me) is False


def test_live_chat_between_a_visitor_and_her_team(linked):
    from app.main import app
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    assert c.post(f"{base}/chat", json={"text": "hi"}).status_code == 401
    a = _signup(c, base, "asha@x.in", "Asha").json()["token"]
    assert c.post(f"{base}/chat", json={"text": "Mera order kab aayega?"}, headers=_h(a)).status_code == 200
    assert c.get(f"{base}/chat?all=1", headers=_h(a)).status_code == 403                # a customer never sees other threads
    ravi = _staff(c, linked, "ravi@x.in", "Ravi")
    th = c.get(f"{base}/chat?all=1", headers=_h(ravi)).json()
    assert th["unread"] == 1 and th["threads"][0]["name"] == "Asha"
    member = th["threads"][0]["member"]
    assert c.post(f"{base}/live/typing", json={"thread": member}, headers=_h(ravi)).json()["ok"] is True
    assert c.post(f"{base}/chat/{member}", json={"text": "Shaam tak"}, headers=_h(ravi)).json()["staff"] is True
    mine = c.get(f"{base}/chat", headers=_h(a)).json()["messages"]
    assert [m["text"] for m in mine] == ["Mera order kab aayega?", "Shaam tak"]
    assert c.post(f"{base}/chat/{member}", json={"text": "x"}, headers=_h(a)).status_code == 403
    assert c.get(f"{base}/live/presence", headers=_h(a)).status_code == 200
    # her own reply from the console needs her tap
    p = _proj(linked)
    assert c.post(f"/api/apps/{p.id}/chat/{member}", json={"text": "Ji"}).status_code == 403
    assert c.post(f"/api/apps/{p.id}/chat/{member}", json={"text": "Ji", "her_tap": True}).status_code == 200


# ---------------------------------------------------------------- W6 clinic queue (the checkpoint)
@pytest.fixture()
def fake():
    from app.appmaker import connect as CN
    calls = []

    def hand(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        return httpx.Response(200, json={"type": "success"})
    CN.set_transport(httpx.MockTransport(hand), PUBLIC)
    CN._TOKENS.clear()
    CN._RATE.clear()
    yield calls
    CN.set_transport(None, None)


def _sync_pool(monkeypatch):
    from app.appmaker import connect as CN

    class P:
        def submit(self, fn, *a):
            fn(*a)
    monkeypatch.setattr(CN, "_POOL", P())


def test_clinic_queue_tokens_board_numbers_only_and_one_sms_when_near(linked, fake, monkeypatch):
    from app.appmaker import connect as CN
    from app.main import app
    from app.site import livesite as LS
    from app.site import webapp as W
    _sync_pool(monkeypatch)
    c = TestClient(app)
    base = f"/api/site-app/{linked}"
    p = _proj(linked)
    assert c.get(f"{base}/queue").json() == {"on": False, "label": "Queue"}
    a = _signup(c, base, "asha@x.in", "Asha Rao").json()["token"]
    assert c.post(f"{base}/queue/take", json={}, headers=_h(a)).status_code == 409            # queue off
    # her settings + her SMS pack (DLT template) approved by her tap
    r = c.put(f"/api/apps/{p.id}/queue", json={"on": True, "label": "OPD Dr. Rao", "near": 2, "avg_min": 6})
    assert r.status_code == 200 and r.json()["settings"]["near"] == 2
    st = CN.apply_pack(p, "sms_queue", {"template_id": "tpl-q"}, {"msg91_authkey": "MSG-SECRET-KEY"})
    assert st["made"] == ["sms_queue_near"] and not st["problems"]
    CN.approve(p, "sms_queue_near", her_tap=True)
    assert c.get(f"{base}/schema").json()["live"]["queue"] is True
    # reception adds walk-ins; a patient takes her own token (one per day)
    owner = W.Who(owner=True)
    LS.add(p, owner, {"name": "Ram", "phone": "98765 43210"})
    with pytest.raises(W.AppError):
        LS.add(p, owner, {"name": "Bad", "phone": "12345"})
    mine = c.post(f"{base}/queue/take", json={"phone": "9123456780"}, headers=_h(a)).json()
    assert mine["token"] == 2 and mine["ahead"] == 1 and mine["est_min"] == 6
    assert c.post(f"{base}/queue/take", json={}, headers=_h(a)).json()["token"] == 2      # the same token again
    LS.add(p, owner, {"name": "Sita"})                                                   # no phone: no SMS, still a token
    # the two at the front were told ONCE each (near = 2); the SMS carries name + token through her template
    sms = [json.loads(x.content) for x in fake]
    assert [(m["recipients"][0]["var1"], m["recipients"][0]["var2"]) for m in sms] == [("Ram", 1), ("Asha Rao", 2)]
    assert sms[0]["template_id"] == "tpl-q" and sms[0]["recipients"][0]["mobiles"] == "919876543210"
    assert fake[0].headers["authkey"] == "MSG-SECRET-KEY"
    # the public board: numbers only - never a name, never a phone
    b = c.get(f"{base}/queue").json()
    assert b["now"] is None and b["next"] == [1, 2, 3] and b["waiting"] == 3
    txt = json.dumps(b)
    assert "Ram" not in txt and "Asha" not in txt and "98765" not in txt
    assert c.get(f"{base}/queue?staff=1", headers=_h(a)).status_code == 403             # names are staff-only
    # call next: 1 is called, 3 comes within 2 -> Sita has no phone, so no SMS; each told once only
    v = LS.call_next(p, owner)
    assert v["board"]["now"] == 1 and v["board"]["next"] == [2, 3] and len(fake) == 2
    assert c.get(f"{base}/queue?mine=1", headers=_h(a)).json()["ahead"] == 0
    LS.call_next(p, owner)
    assert c.get(f"{base}/queue?mine=1", headers=_h(a)).json()["status"] == "called"
    v = LS.mark(p, owner, 3, "skipped")
    assert [k["status"] for k in v["tokens"]] == ["done", "called", "skipped"]
    LS.mark(p, owner, 3, "waiting")
    assert len(fake) == 2                                                              # near_sent stays: never twice
    with pytest.raises(W.AppError):
        LS.call_next(p, owner, 99)
    # the TV board page + its stream are public; the page has no personal data at all
    page = c.get(f"{base}/queue/board")
    assert page.status_code == 200 and "OPD Dr. Rao" in page.text and "/queue/live" in page.text and "Asha" not in page.text
    monkeypatch.setattr(LS, "board_stream", _short_stream(LS.board_stream))
    evs = _events(c.get(f"{base}/queue/live").text)
    assert evs[0]["type"] == "board" and evs[0]["now"] == 2 and "Asha" not in json.dumps(evs)


def _short_stream(real):
    def go(p, ip, gone=None, seconds=600, every=1.0):
        return real(p, ip, gone=None, seconds=0.3, every=0.1)
    return go


def test_tokens_are_unique_under_parallel_reception_desks(linked):
    from app.site import livesite as LS
    from app.site import webapp as W
    p = _proj(linked)
    LS.save_cfg(p, {"on": True})
    errs = []

    def one(i):
        try:
            LS.add(p, W.Who(owner=True), {"name": f"P{i}"})
        except Exception as e:                                     # noqa: BLE001
            errs.append(e)
    ts = [threading.Thread(target=one, args=(i,)) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs
    toks = [k["token"] for k in LS.staff_view(p, W.Who(owner=True))["tokens"]]
    assert sorted(toks) == list(range(1, 9))


def test_board_streams_are_capped_per_address(monkeypatch):
    from app.site import livesite as LS
    from app.site import webapp as W
    monkeypatch.setattr(LS, "_BOARDS", {"1.2.3.4": LS.BOARD_PER_IP})
    with pytest.raises(W.AppError) as e:
        LS.board_admit("1.2.3.4")
    assert e.value.code == 429
    LS.board_admit("5.6.7.8")


# ---------------------------------------------------------------- W7 reminders before a booking + new connector kinds
def _with_appointments(p):
    from app.appmaker import backend as BE
    from app.site import webapp as W

    def fn(be):
        sch = be["schema"]
        sch["collections"] = [x for x in sch["collections"] if x["key"] != "appointments"] + W.clean_schema({"collections": [
            {"key": "appointments", "label": "Appointments", "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "phone", "label": "Mobile", "type": "phone"},
                {"key": "date", "label": "Date", "type": "date"}, {"key": "time", "label": "Time", "type": "text"},
                {"key": "status", "label": "Status", "type": "choice", "options": ["Booked", "Cancelled"], "default": "Booked"}],
             "rules": {"create": "public", "read": "own", "update": "admin", "delete": "admin"}}]})["collections"]
    BE.patch_backend(p, fn=fn)


def test_sms_reminder_goes_once_per_booking_and_never_for_a_cancelled_one(linked, fake, monkeypatch):
    from app.appmaker import backend as BE
    from app.appmaker import connect as CN
    from app.db import now
    from app.site import webapp as W
    _sync_pool(monkeypatch)
    p = _proj(linked)
    _with_appointments(p)
    st = CN.apply_pack(p, "sms_reminder", {"coll": "appointments", "before_min": "120", "template_id": "tpl-r"}, {"msg91_authkey": "K"})
    assert st["made"] == ["sms_remind"] and not st["problems"]
    act = next(a for a in st["actions"] if a["key"] == "sms_remind")
    assert act["trigger"] == "remind" and act["before_min"] == 120 and act["leaves"]["fields"] == ["date", "name", "phone", "time"]
    at = now().astimezone(CN.IST)
    soon, later = at + timedelta(minutes=60), at + timedelta(days=2)
    owner = W.Who(owner=True)

    def book(name, t, status="Booked"):
        row = BE.create(p, "appointments", {"name": name, "phone": "9876543210", "date": t.strftime("%Y-%m-%d"),
                                            "time": t.strftime("%H:%M"), "status": status}, owner)
        return row["id"]
    due = book("Asha", soon)
    book("Later", later)
    book("Gone", soon, "Cancelled")
    assert CN.remind_tick() == 0                                       # not approved yet: nothing at all
    CN.approve(p, "sms_remind", her_tap=True)
    assert [x[1] for x in CN.due_reminders(p)] == [due]
    assert CN.remind_tick() == 1
    body = json.loads(fake[-1].content)
    assert body["recipients"][0]["var1"] == "Asha" and body["recipients"][0]["var2"] == soon.strftime("%Y-%m-%d")
    assert CN.remind_tick() == 0 and len(fake) == 1                    # once per booking time
    # moved to a new time -> a reminder for the NEW time (the old one does not block it)
    with pytest.raises(Exception):
        CN.save_action(p, {**act, "key": "bad", "before_min": 2})      # 5 minutes .. 7 days
    assert CN._start_of({"date": "2026-11-03", "time": "6:30 pm"}, {"date_field": "date", "time_field": "time"}).hour == 18
    assert CN._start_of({"date": "nope"}, {"date_field": "date"}) is None


def test_hubspot_and_composio_actions_on_her_own_account(linked, monkeypatch):
    from app.appmaker import connect as CN
    from app.appmaker import connect_packs as P
    from app.bazar import composio as cmp
    p = _proj(linked)
    hs = P.actions_for("hubspot", {"coll": "orders"})[0]
    assert hs["url"] == "https://api.hubapi.com/crm/v3/objects/contacts" and hs["auth"] == {"type": "bearer", "secret": "hubspot_token"}
    CN.save_action(p, hs)
    seen = []

    class Fake:
        def execute(self, slug, user, ca, args):
            seen.append((slug, user, ca, args))
            return {"successful": True, "data": {"ts": "1.2"}}
    monkeypatch.setattr(CN, "_COMPOSIO", Fake())
    monkeypatch.setattr(cmp, "account", lambda s, u, kit, check=True: (None, "ca_her_slack"))
    monkeypatch.setattr(cmp, "take_call", lambda s, u: None)
    act = P.actions_for("composio", {"coll": "orders", "toolkit": "slack", "tool": "SLACK_SEND_MESSAGE", "trigger": "manual",
                                     "args": '{"channel": "#orders", "text": "New {{row.item}}"}'})[0]
    st = CN.save_action(p, act)
    a = next(x for x in st["actions"] if x["key"] == "app_slack")
    assert a["kind"] == "composio" and not a["approved"] and a["leaves"]["fields"] == ["item"]
    from app.site import webapp as W
    row = __import__("app.appmaker.backend", fromlist=["x"]).create(p, "orders", {"item": "Cake", "phone": "9876500002"}, W.Who(owner=True))
    with pytest.raises(W.AppError):
        CN.run(p, "app_slack", row["id"])                              # her tap first
    CN.approve(p, "app_slack", her_tap=True)
    out = CN.run(p, "app_slack", row["id"])
    assert out["status"] == "ok"
    assert seen == [("SLACK_SEND_MESSAGE", cmp.composio_user(p.tenant_id), "ca_her_slack", {"channel": "#orders", "text": "New Cake"})]
    # a changed argument needs her tap again; no secrets in Composio arguments; the tool must belong to the toolkit
    st = CN.save_action(p, {**act, "args": {"channel": "#all", "text": "x"}})
    assert not next(x for x in st["actions"] if x["key"] == "app_slack")["approved"]
    for bad in ({**act, "args": {"text": "{{secret.msg91_authkey}}"}}, {**act, "tool": "GMAIL_SEND_EMAIL"}, {**act, "toolkit": "x y"}):
        with pytest.raises(W.AppError):
            CN.save_action(p, bad)
    # the queue trigger is only for the queue list
    with pytest.raises(W.AppError):
        CN.save_action(p, {"key": "q", "url": "https://x.example.in/a", "trigger": "queue", "coll": "orders"})


def test_signed_webhook_on_the_websites_own_address(linked):
    from app.appmaker import backend as BE
    from app.appmaker import connect as CN
    from app.main import app
    from app.site import webapp as W
    c = TestClient(app)
    p = _proj(linked)
    row = BE.create(p, "orders", {"item": "Cake", "phone": "9876500002"}, W.Who(owner=True))
    st = CN.save_hook(p, {"key": "kitchen", "coll": "orders", "match": {"item": "$.item"}, "set": {"status": "$.state"}})
    secret = st["new_secret"]
    raw = json.dumps({"item": "Cake", "state": "Taiyaar"}).encode()
    url = f"/api/site-app/{linked}/hook/kitchen"
    assert c.post(url, content=raw, headers={"x-signature": "bad"}).status_code == 401
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    assert c.post(url, content=raw, headers={"x-signature": sig}).json()["matched"] == 1
    assert BE.rows(p, "orders", W.Who(owner=True))[0]["status"] == "Taiyaar"


# ---------------------------------------------------------------- the page script, the service worker, the console
def test_page_script_asks_only_on_a_tap_and_the_console_has_the_panel():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    js = (root / "site/assets/hoola-app.js").read_text()
    assert "fetch(API + '/live'" in js and "Authorization: 'Bearer ' + tok" in js           # header, never ?token=
    i = js.index("function notifyBox")
    block = js[i:js.index("function all()")]
    assert block.index("btn(t.notifyon") < block.index("Notification.requestPermission")      # only inside the button's click
    assert "consent: true" in block and "userVisibleOnly: true" in block
    assert "Notification.requestPermission" not in js[:i]
    sw = (root / "site/assets/hoola-push-sw.js").read_text()
    assert "showNotification" in sw and "addEventListener('fetch'" not in sw
    assert '"hoola-push-sw.js"' in (root / "site/build.py").read_text()
    con = (root / "static/console/build.js").read_text()
    assert "async function liveBox" in con and "her_tap: true" in con[con.index("async function liveBox"):]
    from app.appmaker import connect_packs as P
    keys = {p["key"] for p in P.catalog()}
    assert {"sms_reminder", "wa_reminder", "sms_queue", "hubspot", "composio"} <= keys
