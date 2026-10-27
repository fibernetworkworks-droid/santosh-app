"""Hoola Network v0.34: avatars on different servers (signed server-to-server HTTPS) and the A2A agent card."""
import base64
import hashlib
import json
import secrets
from datetime import datetime, timezone
from email.utils import formatdate

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from tests.test_net import _people, ev

REMOTE = "remote.example"


def _pub(k):
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


class Remote:
    """A fake Hoola server on another domain with one avatar (Kunal's Raju)."""
    def __init__(self):
        self.server = Ed25519PrivateKey.generate()
        self.avatar = Ed25519PrivateKey.generate()
        self.addr = f"hl_{secrets.token_hex(8)}@{REMOTE}"
        self.got = []
        self.files = {}

    def card(self):
        return {"address": self.addr, "handle": "kunal", "owner_name": "Kunal", "avatar_name": "Raju", "avatar_gender": "m",
                "public_key": _pub(self.avatar), "server": REMOTE, "verified": False, "business": False, "language": "hinglish"}

    def envelope(self, to, kind, body, thread="tk_r1", ts=None):
        from app.net import identity as idn
        env = {"v": 1, "id": "env_" + secrets.token_hex(6), "from": self.addr, "to": to, "kind": kind, "thread": thread,
               "body": body, "ts": ts or datetime.now(timezone.utc).isoformat(), "nonce": secrets.token_hex(4), "card": self.card()}
        env["sig"] = base64.b64encode(self.avatar.sign(idn.canonical(env))).decode()
        return env

    def headers(self, method, path, body, domain=REMOTE, date=None, key=None):
        date = date or formatdate(usegmt=True)
        digest = hashlib.sha256(body).hexdigest()
        sig = (key or self.server).sign(f"{method}\n{path}\n{domain}\n{date}\n{digest}".encode())
        return {"X-Hoola-Server": domain, "Date": date, "X-Hoola-Digest": digest, "X-Hoola-Sig": base64.b64encode(sig).decode(),
                "Content-Type": "application/json"}

    def handler(self, req: httpx.Request):
        p = req.url.path
        if p == "/.well-known/hoola.json":
            return httpx.Response(200, json={"protocol": "hoola-net/1", "domain": REMOTE, "server_key": _pub(self.server),
                                             "inbox": f"https://{REMOTE}/hoola/inbox"})
        if p == "/hoola/lookup":
            return httpx.Response(200, json=self.card()) if req.url.params.get("handle") == "kunal" else httpx.Response(404)
        if p == "/hoola/inbox":
            from app.net import federation as fed
            from app.net import identity as idn
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            body = req.content
            h = req.headers
            msg = f"POST\n/hoola/inbox\n{h['x-hoola-server']}\n{h['date']}\n{hashlib.sha256(body).hexdigest()}".encode()
            Ed25519PublicKey.from_public_bytes(base64.b64decode(fed.server_public_key())).verify(base64.b64decode(h["x-hoola-sig"]), msg)
            env = json.loads(body)
            assert idn.verify(env, env["card"]["public_key"])
            self.got.append(env)
            return httpx.Response(200, json={"ok": True, "status": "requested" if env["kind"] == "connect_request" else "pending"})
        if p.startswith("/hoola/share/"):
            sid = p.rsplit("/", 1)[-1]
            data = self.files[sid]
            return httpx.Response(200, content=data, headers={"content-type": "text/plain", "x-hoola-name": "plan.txt",
                                                              "x-hoola-sha256": hashlib.sha256(data).hexdigest()})
        return httpx.Response(404)


@pytest.fixture
def remote(env, monkeypatch):
    monkeypatch.setenv("HOOLA_DOMAIN", "home.example")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.net import federation as fed
    r = Remote()
    fed.set_http(httpx.Client(transport=httpx.MockTransport(r.handler)))
    yield r
    fed.set_http(None)


def _post(cl, r, env, **hk):
    body = json.dumps(env).encode()
    return cl.post("/hoola/inbox", content=body, headers=r.headers("POST", "/hoola/inbox", body, **hk))


def test_cards(remote):
    from app import main
    with TestClient(main.app) as cl:
        sc = cl.get("/.well-known/hoola.json").json()
        assert sc["protocol"] == "hoola-net/1" and sc["domain"] == "home.example" and sc["server_key"]
        ac = cl.get("/.well-known/agent-card.json").json()
        assert ac["name"] == "Hoola on home.example" and ac["skills"][0]["id"] == "business-counter"
        _people()
        assert cl.get("/hoola/lookup", params={"handle": "meghana.fnw"}).json()["avatar_name"] == "Santosh"
        assert "phone" not in json.dumps(cl.get("/hoola/lookup", params={"handle": "meghana.fnw"}).json())


def test_connect_and_talk_across_servers(remote):
    _people()
    from app.net import identity as idn
    from app.net import service as net
    me = idn.my_card("default")["address"]
    assert me.endswith("@home.example")
    out = net.connect("default", "@kunal@" + REMOTE, relation="business", note="FNW se")
    assert out["status"] == "requested" and remote.got[-1]["kind"] == "connect_request"
    assert net.connections("default")[0]["label"] == "Kunal ka Raju"
    from app import main
    with TestClient(main.app) as cl:
        assert _post(cl, remote, remote.envelope(me, "connect_accept", {"relation": "business"})).json()["status"] == "active"
        assert net.connections("default")[0]["status"] == "active"
        e = remote.envelope(me, "message", {"text": "Kal FNW pitch par baat karein?"})
        assert _post(cl, remote, e).json()["status"] == "pending"
        assert _post(cl, remote, e).json()["status"] == "duplicate"                          # replay
        k = ev("default", "hoola_knock")[-1]
        assert k["from"] == "Kunal ka Raju" and "FNW pitch" in k["body"]["text"]
        net.decide("default", k["id"], "accept", note="Haan, 5 baje")
        assert remote.got[-1]["kind"] == "accepted" and remote.got[-1]["body"]["text"] == "Haan, 5 baje"
        # forged / wrong-server / old requests are refused
        bad = remote.envelope(me, "message", {"text": "x"})
        other = Ed25519PrivateKey.generate()
        assert _post(cl, remote, bad, key=other).status_code == 401
        assert _post(cl, remote, bad, domain="evil.example").status_code == 401
        assert _post(cl, remote, bad, date="Mon, 01 Jan 2024 00:00:00 GMT").status_code == 401
        tampered = dict(remote.envelope(me, "message", {"text": "hello"}), body={"text": "evil"})
        assert _post(cl, remote, tampered).json()["status"] == "refused"
        # a file from the other server is fetched with a signed request, then checked like any file
        remote.files["sh_remote1abcdef"] = b"Plan: open Nashik office in December. " * 4
        fe = remote.envelope(me, "file", {"text": "Plan", "name": "plan.txt", "size": 140, "share_id": "sh_remote1abcdef",
                                          "sha256": hashlib.sha256(remote.files["sh_remote1abcdef"]).hexdigest()})
        assert _post(cl, remote, fe).json()["status"] == "pending"
        assert ev("default", "hoola_knock")[-1]["scan"]["verdict"] == "clear"


def test_blocked_servers_and_off_switch(remote, monkeypatch):
    _people()
    from app.config import get_settings
    from app.net import service as net
    monkeypatch.setenv("HOOLA_BLOCKED_SERVERS", REMOTE)
    get_settings.cache_clear()
    with pytest.raises(net.NetError, match="band"):
        net.connect("default", "@kunal@" + REMOTE)
    monkeypatch.setenv("HOOLA_BLOCKED_SERVERS", "")
    monkeypatch.setenv("HOOLA_FEDERATION", "false")
    get_settings.cache_clear()
    with pytest.raises(net.NetError, match="band"):
        net.resolve("default", "@kunal@" + REMOTE)


def test_a2a_only_reaches_public_businesses(remote):
    _people()
    from app.net import business as biz
    biz.setup("kunal", name="FNW Support", category="isp")
    from app import main
    with TestClient(main.app) as cl:
        ok = cl.post("/a2a", json={"jsonrpc": "2.0", "id": 1, "method": "message/send",
                                   "params": {"message": {"role": "user", "parts": [{"kind": "text", "text": "Akola mein plans?"}],
                                                          "metadata": {"to": "kunal.raj"}}}}).json()
        assert ok["result"]["status"]["state"] == "working"          # v0.116 waits for the owner's answer
        assert "bahar ke" in ev("kunal", "a2a_task")[-1]["say"].lower()
        no = cl.post("/a2a", json={"jsonrpc": "2.0", "id": 2, "method": "message/send",
                                   "params": {"message": {"parts": [{"kind": "text", "text": "hi"}], "metadata": {"to": "meghana.fnw"}}}}).json()
        assert no["error"]["code"] == -32602
        assert cl.post("/a2a", json={"jsonrpc": "2.0", "id": 3, "method": "tasks/get"}).json()["error"]["code"] == -32001
        assert cl.post("/a2a", json={"jsonrpc": "2.0", "id": 4, "method": "tasks/nope"}).json()["error"]["code"] == -32601
