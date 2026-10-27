"""v0.97 Fingerprint-signed approvals: once a phone is set up, a money card is approved only with a fresh signature by
that phone's Keystore key over THIS card; a stolen app key can't approve, add a phone or remove one at once."""
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


@pytest.fixture
def bz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security
    bzc.reset_settings()
    security._vault = None
    from app.bazar import service
    service.set_executors(None)
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    yield {"svc": service, "conv": conv}
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


class Phone:
    """What ApproveKey.kt does: an EC P-256 key; only the public key leaves the phone."""

    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, challenge):
        sig = self.key.sign(challenge["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": challenge["challenge_id"], "device_id": self.device_id,
                "signature": base64.b64encode(sig).decode()}


_N = [0]


def _money_card(bz):
    svc, conv = bz["svc"], bz["conv"]
    _N[0] += 1
    bill = svc.run("default", conv, "msedcl-mahavitaran", "fetch_bill",
                   {"consumer_number": f"3300123456{_N[0]:02d}", "billing_unit": "4630"})
    pay = svc.run("default", conv, "msedcl-mahavitaran", "pay_bill", {"bill_ref": bill["bill_ref"], "amount": 1})
    assert pay["needs_approval"]
    return pay["approval_id"]


def _client():
    from fastapi.testclient import TestClient

    from app import main
    return TestClient(main.app)


def test_money_card_needs_this_phones_fingerprint(bz):
    phone = Phone("phone-meghana")
    with _client() as c:
        # nothing set up yet: the old slide approval works as before
        a0 = _money_card(bz)
        assert c.post(f"/api/bazar/approvals/{a0}", json={"decision": "approve"}).status_code == 200
        r = c.post("/api/approvekey/devices", json={"device_id": phone.device_id, "public_key": phone.pub, "label": "Pixel"}).json()
        assert r["status"] == "active" and c.get("/api/approvekey").json()["on"] is True
        a1 = _money_card(bz)
        # the app key alone is not enough any more
        r = c.post(f"/api/bazar/approvals/{a1}", json={"decision": "approve"})
        assert r.status_code == 428 and r.json()["detail"] == "fingerprint_needed"
        ch = c.post("/api/approvekey/challenge", json={"kind": "bazar", "target": a1}).json()
        assert ch["show"]["amount"] and ch["message"].startswith("hoola-approve|v1|default|bazar|" + a1)
        proof = phone.sign(ch)
        r = c.post(f"/api/bazar/approvals/{a1}", json={"decision": "approve", "proof": proof})
        assert r.status_code == 200 and r.json()["status"] == "approved"
        # the same signature can't be used twice, nor for another card
        a2 = _money_card(bz)
        r = c.post(f"/api/bazar/approvals/{a2}", json={"decision": "approve", "proof": proof})
        assert r.status_code == 428 and r.json()["detail"] == "fingerprint_invalid"
        # a stranger's key (stolen app key, own key pair) is refused
        thief = Phone("phone-meghana")
        ch = c.post("/api/approvekey/challenge", json={"kind": "bazar", "target": a2}).json()
        assert c.post(f"/api/bazar/approvals/{a2}", json={"decision": "approve", "proof": thief.sign(ch)}).status_code == 428
        # saying no never needs a fingerprint
        assert c.post(f"/api/bazar/approvals/{a2}", json={"decision": "reject"}).json()["status"] == "rejected"


def test_challenge_expires_and_binds_the_card(bz, monkeypatch):
    from app import approvekey as ak
    phone = Phone("p1")
    ak.register("default", phone.device_id, phone.pub, "Phone")
    a1, a2 = _money_card(bz), _money_card(bz)
    ch = ak.challenge("default", "bazar", a1)
    with pytest.raises(ak.ApproveError, match="fingerprint_invalid"):
        ak.verify("default", "bazar", a2, phone.sign(ch))           # signed for another card
    monkeypatch.setattr(ak, "CHALLENGE_TTL", timedelta(seconds=-1))
    ch = ak.challenge("default", "bazar", a1)
    with pytest.raises(ak.ApproveError, match="fingerprint_invalid"):
        ak.verify("default", "bazar", a1, phone.sign(ch))           # too late
    monkeypatch.setattr(ak, "CHALLENGE_TTL", timedelta(minutes=2))
    ch = ak.challenge("default", "bazar", a1)
    ak.verify("default", "bazar", a1, phone.sign(ch))                # fresh, same card: fine
    assert ak.STATS["verified"] >= 1


def test_a_second_phone_waits_a_day_unless_the_first_one_agrees(bz):
    from app import approvekey as ak
    from app.approvekey import ApproveDevice
    from app.db import session
    mine, thief, new = Phone("mine"), Phone("thief"), Phone("new-phone")
    ak.register("default", mine.device_id, mine.pub, "Mera phone")
    r = ak.register("default", thief.device_id, thief.pub, "Unknown")
    assert r["status"] == "pending" and "24 ghante" in r["say"]
    a1 = _money_card(bz)
    ch = ak.challenge("default", "bazar", a1)
    with pytest.raises(ak.ApproveError):
        ak.verify("default", "bazar", a1, thief.sign(ch))            # pending phones can't approve
    assert ak.cancel("default", thief.device_id)["status"] == "removed"   # she stops it
    # her own new phone, endorsed by the phone already set up: active at once
    ch = ak.challenge("default", "endorse", f"{new.device_id}|{new.pub}")
    r = ak.register("default", new.device_id, new.pub, "Naya phone", proof=mine.sign(ch))
    assert r["status"] == "active"
    # an unendorsed one becomes active after 24 hours
    later = Phone("tablet")
    ak.register("default", later.device_id, later.pub, "Tablet")
    with session() as s:
        d = s.query(ApproveDevice).filter_by(device_id="tablet").one()
        d.active_after = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert {d["device_id"]: d["status"] for d in ak.devices("default")["devices"]}["tablet"] == "active"


def test_removing_a_phone_needs_its_fingerprint_or_a_day(bz):
    from app import approvekey as ak
    mine = Phone("mine")
    ak.register("default", mine.device_id, mine.pub, "Mera phone")
    r = ak.remove("default", mine.device_id)                         # a stolen app key tries to switch it off
    assert r["status"] == "remove_pending" and ak.active_on("default")
    assert ak.cancel("default", mine.device_id)["status"] == "active"
    ch = ak.challenge("default", "remove", mine.device_id)
    assert ak.remove("default", mine.device_id, proof=mine.sign(ch))["status"] == "removed"
    assert not ak.active_on("default")


def test_only_money_cards_and_studio_spend_need_it(bz, monkeypatch):
    from app import approvekey as ak
    from app.bazar import service as bzs
    mine = Phone("mine")
    ak.register("default", mine.device_id, mine.pub, "Mera phone")
    monkeypatch.setattr(bzs, "approval_card", lambda t, i: {"id": i, "title": "PC par Save", "money": False})
    assert ak.needed("default", "bazar", "x") is False
    monkeypatch.setattr(bzs, "approval_card", lambda t, i: {"id": i, "title": "Bill", "money": True})
    assert ak.needed("default", "bazar", "x") is True
    assert ak.needed("default", "studio", "sa1") is True
    from app.studio import service as ss
    monkeypatch.setattr(ss, "approval_card", lambda t, i: {"title": "Video Studio: diwali - 4 shots", "inr": "₹420", "usd": "$5.00"})
    ch = ak.challenge("default", "studio", "sa1")
    assert ch["show"]["amount"] == "₹420"
    ak.verify("default", "studio", "sa1", mine.sign(ch))


def test_bad_keys_are_refused(bz):
    from app import approvekey as ak
    with pytest.raises(ak.ApproveError):
        ak.register("default", "d1", base64.b64encode(b"not a key" * 10).decode())
    rsa_like = ec.generate_private_key(ec.SECP384R1()).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    with pytest.raises(ak.ApproveError, match="P-256"):
        ak.register("default", "d1", base64.b64encode(rsa_like).decode())
