"""v0.999.54 HOOLA CRED (owner: "LETS BUILD OUR OWN 1PASSWORD -- WE NAME IT A HOOLA CRED"; locking = master password +
Hoola use): a zero-knowledge vault - the server keeps only salt / rounds / the wrapped vault key / encrypted items; a
login switched to 'Hoola may use' is sealed into Saved sign-ins (never bank / payment), its 2-step key gives the code."""
import base64
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

B = lambda b: base64.b64encode(b).decode()  # noqa: E731
U = base64.b64decode
STATIC = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _device_side(master: str):
    """What her browser does: master -> KEK (PBKDF2 600k), a random vault key wrapped with it."""
    salt, iters = os.urandom(16), 100_000
    kek = PBKDF2HMAC(SHA256(), 32, salt, iters).derive(master.encode())
    vk = os.urandom(32)
    iv = os.urandom(12)
    return {"salt": B(salt), "iters": iters, "wrapped": {"iv": B(iv), "ct": B(AESGCM(kek).encrypt(iv, vk, None))}}, vk


def _seal(vk: bytes, item: dict):
    iv = os.urandom(12)
    return {"iv": B(iv), "ct": B(AESGCM(vk).encrypt(iv, json.dumps(item).encode(), None))}


def _open_vk(view: dict, master: str) -> bytes:
    kek = PBKDF2HMAC(SHA256(), 32, U(view["salt"]), view["iters"]).derive(master.encode())
    w = view["wrapped"]
    return AESGCM(kek).decrypt(U(w["iv"]), U(w["ct"]), None)


def test_vault_is_zero_knowledge_and_items_round_trip(env):
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/cred/vault").json() == {"exists": False}
    assert c.post("/api/cred/items", json={"iv": "AAAA", "ct": "AAAA"}).status_code in (400, 409)   # no vault yet
    body, vk = _device_side("correct horse battery")
    weak = dict(body, iters=1000)
    assert c.post("/api/cred/vault", json=weak).status_code in (400, 409)
    assert c.post("/api/cred/vault", json=body).json() == {"ok": True}
    assert c.post("/api/cred/vault", json=body).status_code in (400, 409)                         # only one vault
    secret = {"title": "GST portal", "username": "meghana@gst", "password": "Pa55-Cred!", "urls": ["gst.gov.in"]}
    r = c.post("/api/cred/items", json=_seal(vk, secret)).json()
    view = c.get("/api/cred/vault").json()
    raw = json.dumps(view)
    assert "Pa55" not in raw and "meghana" not in raw                                         # the server never sees it
    vk2 = _open_vk(view, "correct horse battery")
    it = view["items"][0]
    assert json.loads(AESGCM(vk2).decrypt(U(it["iv"]), U(it["ct"]), None))["password"] == "Pa55-Cred!"
    with pytest.raises(Exception):
        _open_vk(view, "wrong master")
    # optimistic versions: a stale save is refused
    up = dict(_seal(vk, dict(secret, password="new")), version=r["version"])
    assert c.put(f"/api/cred/items/{r['id']}", json=up).json()["version"] == 2
    assert c.put(f"/api/cred/items/{r['id']}", json=up).status_code in (400, 409)
    assert c.post("/api/cred/items", json={"iv": "not base64!", "ct": "x"}).status_code in (400, 409, 422)
    assert c.delete("/api/cred/vault").status_code in (400, 409)                                     # needs confirm=DELETE


def test_hoola_use_seals_into_saved_signins_and_never_money(env):
    from app import cred
    from app.pc import vault as pcv
    body, vk = _device_side("master-pass-123")
    cred.create_vault("owner", body["salt"], body["iters"], body["wrapped"])
    s = _seal(vk, {"t": 1})
    iid = cred.add_item("owner", s["iv"], s["ct"])["id"]
    with pytest.raises(cred.CredError):
        cred.set_hoola("owner", iid, True, "GST", "u", "p", urls=[])                          # no site = refused
    with pytest.raises(cred.CredError):
        cred.set_hoola("owner", iid, True, "HDFC net banking", "u", "p", urls=["netbanking.hdfcbank.com"])
    with pytest.raises(cred.CredError):
        cred.set_hoola("owner", iid, True, "GST", "u", "p", urls=["gst.gov.in"], totp="not!base32")
    r = cred.set_hoola("owner", iid, True, "GST portal", "meghana@gst", "Pa55",
                       urls=["https://services.gst.gov.in/login"], totp="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
    assert r == {"hoola": True, "sites": ["gst.gov.in"]}
    saved = pcv.find("owner", "gst.gov.in")
    assert saved["from_cred"] and saved["two_step"] and saved["user"] == "m***@gst"
    with pcv.session() as ses:
        row = ses.get(pcv.PcLogin, saved["id"])
        assert "Pa55" not in row.pw_sealed and "GEZDGNBV" not in (row.totp_sealed or "")
    assert pcv.open_("owner", saved["id"]) == ("meghana@gst", "Pa55")
    assert len(pcv.totp_of("owner", saved["id"])) == 6
    cred.set_hoola("owner", iid, False)                                                       # switched off = gone
    assert pcv.find("owner", "gst.gov.in") is None
    cred.set_hoola("owner", iid, True, "GST portal", "u", "p", urls=["gst.gov.in"])
    assert cred.delete_item("owner", iid) and pcv.find("owner", "gst.gov.in") is None         # deleted = gone
    s2 = _seal(vk, {"t": 2})
    iid2 = cred.add_item("owner", s2["iv"], s2["ct"])["id"]
    cred.set_hoola("owner", iid2, True, "IRCTC", "u", "p", urls=["irctc.co.in"])
    pcv.save("owner", "incometax.gov.in", "Income tax", "x", "y")                            # her own, not from cred
    assert cred.delete_vault("owner")["deleted"] == 1
    assert pcv.find("owner", "irctc.co.in") is None and pcv.find("owner", "incometax.gov.in") is not None


def test_totp_rfc6238_vector_and_otpauth():
    from app.pc import vault as pcv
    sec = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"               # RFC 6238 SHA1 key '12345678901234567890'
    assert pcv.totp_now(sec, at=59, digits=8) == "94287082"
    assert pcv.totp_now(sec, at=59) == "287082"
    assert pcv.totp_now(sec, at=1111111109, digits=8) == "07081804"
    assert pcv.totp_secret(f"otpauth://totp/GST:me?secret={sec.lower()}&issuer=GST") == sec
    assert pcv.totp_secret("hello world!") == "" and pcv.totp_now("") == ""


def test_saved_two_step_fills_the_next_code_box(monkeypatch):
    import asyncio
    import time
    import types
    from app.pc import hands, vault as pcv
    monkeypatch.setattr(pcv, "totp_of", lambda tenant, lid: "123456" if lid == "pcl1" else "")
    op = types.SimpleNamespace(id="t1", tenant="owner", saved_otp=("gst.gov.in", "pcl1", time.time()), onepw_otp=None)
    req = types.SimpleNamespace(status="pending", value="", source="", event=None)
    monkeypatch.setattr(hands, "_wake", lambda ev: None)
    assert asyncio.run(hands.otp_from_onepw(op, req)) is True
    assert req.value == "123456" and req.source == "your Hoola Cred"
    old = types.SimpleNamespace(id="t2", tenant="owner", saved_otp=("k", "pcl1", time.time() - 700), onepw_otp=None)
    req2 = types.SimpleNamespace(status="pending", value="", source="", event=None)
    assert asyncio.run(hands.otp_from_onepw(old, req2)) is False and req2.value == ""          # 10 minutes only


def test_pwned_prefix_only_and_device_route_needs_pairing(env, monkeypatch):
    from app import cred
    from app.main import app
    c = TestClient(app)
    for bad in ("ABC", "ZZZZZ", "abcdef"):
        assert c.get(f"/api/cred/pwned/{bad}").status_code == 400
    sent = []

    class R:
        text = "0018A45C4D1DEF81644B54AB7F969B88D65:1"

        def raise_for_status(self):
            pass
    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **k: sent.append(url) or R())
    cred._PWNED.clear()
    assert c.get("/api/cred/pwned/21bd1").text.startswith("0018A45C")
    assert sent == ["https://api.pwnedpasswords.com/range/21BD1"]                             # only 5 hex leave
    assert c.get("/api/cred/device/vault").status_code == 401
    assert c.get("/api/cred/device/vault", headers={"Authorization": "Bearer spc_nope"}).status_code == 401
    assert "hunter2" not in repr(cred.HoolaIn(on=True, password="hunter2-secret"))


def test_console_page_extension_and_version():
    from app.main import APP_VERSION, app
    c = TestClient(app)
    r = c.get("/console/cred")
    assert r.status_code == 200 and "cred.js" in r.text
    js = (STATIC / "cred.js").read_text()
    for need in ("PBKDF2", "AES-GCM", "600000", "/api/cred/pwned/", "Hoola may use"):
        assert need in js
    ext = (Path(__file__).resolve().parents[2] / "desktop/ext/hoola-extension")
    assert "cred.js" in (ext / "popup.html").read_text()
    ej = (ext / "cred.js").read_text()
    assert "/api/cred/device/vault" in ej and "chrome.storage.session" in ej and "executeScript" in ej
    assert "'cred'" in (STATIC / "v2.js").read_text()
    assert APP_VERSION >= "0.999.54"
