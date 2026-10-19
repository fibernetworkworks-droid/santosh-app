"""Hoola Network v0.33: business avatars (public counter, tickets, webhook to the business's own system, quotes,
orders, verified badge by the operator) and chains (signed, max 5 hops, no loops, news flows back)."""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_net import _connect, ev


def _team():
    net = _connect()                       # default=Meghana (customer), kunal=Kunal (business owner)
    from app.avatar import service as av
    from app.db import Profile, session
    from app.net import identity as idn
    for t, n, h in (("swati", "Swati", "swati.tech"), ("ravi", "Ravi", "ravi.field")):
        with session() as s:
            s.merge(Profile(tenant_id=t, name=n))
        av.save(t, name="Sakhi" if t == "swati" else "Veer", gender="f" if t == "swati" else "m", rules={"quiet": {"on": False}})
        idn.ensure(t)
        idn.set_handle(t, h)
    for a, b in (("kunal", "@swati.tech"), ("swati", "@ravi.field"), ("ravi", "@kunal.raj")):
        net.connect(a, b, relation="team")
        peer = net.resolve(a, b)
        bt = idn.tenant_of(peer)
        lid = net.connections(bt, "incoming")[0]["id"]
        net.answer_connect(bt, lid, "accept")
    return net


@pytest.fixture
def hooks(monkeypatch):
    from app.bazar import custom_mcp
    import httpx
    sent = []
    monkeypatch.setattr(custom_mcp, "check_url", lambda u: u)

    class R:
        status_code = 200
    monkeypatch.setattr(httpx, "post", lambda url, content=b"", **k: sent.append((url, json.loads(content), k["headers"])) or R())
    return sent


def test_complaint_ticket_webhook_and_chain(env, hooks):
    net = _team()
    from app.net import business as biz
    from app.net import chain as chn
    biz.setup("kunal", name="FNW Support", category="isp", area="Akola", hours="9 se 7", ticket_prefix="FNW",
              webhook_url="https://flow.example.com/hook", webhook_secret="s3cret", team=["@swati.tech"])
    d = biz.directory("ravi", "fnw")
    assert d[0]["name"] == "FNW Support" and d[0]["verified"] is False
    out = biz.complain("ravi", "@kunal.raj", "Mera internet 2 din se band hai, laal light")
    assert out["ticket"] == "FNW-1001"
    t = ev("kunal", "hoola_ticket")[-1]
    assert t["number"] == "FNW-1001" and t["webhook"] == "200"
    url, payload, headers = hooks[-1]
    want = hmac.new(b"s3cret", json.dumps(payload, ensure_ascii=False).encode(), hashlib.sha256).hexdigest()
    assert payload["event"] == "ticket.created" and headers["X-Hoola-Signature"] == f"sha256={want}"
    assert biz.my_tickets("ravi")[0]["number"] == "FNW-1001"
    # the business passes it to its technician's avatar along a chain
    biz.assign("kunal", "FNW-1001", "@swati.tech", "Akola site jaiye")
    c = ev("swati", "hoola_chain")[-1]
    assert c["event"] == "with_me" and "FNW-1001" in c["goal"]
    assert "di gayi" in ev("ravi", "hoola_msg")[-1]["text"]
    chn.act("swati", c["chain_id"], "done", note="Fiber joint badla, net chalu")
    assert biz.tickets("kunal")[0]["status"] == "resolved"
    assert "theek ho gayi" in ev("ravi", "hoola_msg")[-1]["text"]
    assert biz.my_tickets("ravi")[0]["status"] == "resolved"


def test_chain_pass_loops_and_signatures(env):
    net = _team()
    from app.net import chain as chn
    c = chn.start("kunal", "@swati.tech", "Akola OLT 7 ka backup")
    chn.act("swati", c["chain_id"], "pass", to="@ravi.field", note="Ravi tum kar lo")
    got = ev("ravi", "hoola_chain")[-1]
    assert got["event"] == "with_me" and got["hops"] == 2
    with pytest.raises(net.NetError, match="chakkar"):
        chn.act("ravi", c["chain_id"], "pass", to="@kunal.raj")
    chn.act("ravi", c["chain_id"], "done", note="Backup le liya")
    k = [e for e in ev("kunal", "hoola_chain") if e["event"] == "progress"]
    assert k and "poora" in k[-1]["text"] and chn.chains("kunal")[0]["status"] == "done"
    # a forged trail is refused
    from app.net import identity as idn
    row = chn._row("ravi", c["chain_id"])
    steps = list(row.steps)
    steps[0] = dict(steps[0], note="Paise bhejo")
    env_ = net.envelope("swati", idn.my_card("ravi")["address"], "chain_step",
                        {"chain_id": "chain_x", "origin": steps[0]["address"], "goal": "x", "steps": steps[:1] + [steps[1]],
                         "deadline": "2099-01-01T00:00:00+00:00"}, "tk_x")
    assert net.receive(env_)["status"] == "refused"


def test_quote_from_catalog_and_order(env, monkeypatch):
    net = _team()
    from app.avatar import service as av
    from app.net import ai, business as biz
    biz.setup("kunal", name="FNW Support", category="isp", catalog=[{"item": "ONT", "price": 1200}, {"item": "Installation", "price": 500}])
    av.save("kunal", name="Meera", gender="f", rules={"quiet": {"on": False}, "decide_alone": {"answer_faq": True}})
    prompts = []

    def fake(system, prompt, max_tokens=600, timeout=90):
        prompts.append(prompt)
        return json.dumps({"action": "reply", "text": "ONT ₹1200, installation ₹500.", "summary": "quote diya"})
    monkeypatch.setattr(ai, "llm", fake)
    from tests.test_bazar import _events
    from app.net import service as ns
    out = biz.contact("ravi", "@kunal.raj")
    r = net.send("ravi", out, "ask", {"text": "Quote chahiye: ONT aur installation"})
    assert r["status"] == "handled" and "ONT: ₹1200" in prompts[-1]
    assert "₹1200" in ev("ravi", "hoola_msg")[-1]["text"]
    r = net.send("ravi", out, "order", {"text": "Order: 1 ONT, kal install"})
    assert r["status"] == "pending"
    k = ev("kunal", "hoola_knock")[-1]
    assert k["what"] == "order dena chahte hain"
    net.decide("kunal", k["id"], "accept", note="Order pakka, kal 11 baje")
    assert "Order pakka" in ev("ravi", "hoola_msg")[-1]["text"]
    _ = (_events, ns)


def test_operator_badge_and_webhook_in(env, hooks):
    net = _team()
    from app.net import business as biz
    biz.setup("kunal", name="FNW Support", webhook_url="https://flow.example.com/hook", webhook_secret="s3cret")
    with pytest.raises(net.NetError, match="GSTIN"):
        biz.request_verification("kunal", "123")
    biz.request_verification("kunal", "27ABCDE1234F1Z5")
    from app import main
    with TestClient(main.app) as c:
        q = c.get("/api/net/operator/verifications").json()["requests"]
        assert q[0]["tenant"] == "kunal"
        assert c.post("/api/net/operator/verifications/kunal", json={"action": "approve"}).json()["status"] == "verified"
        assert biz.directory("ravi")[0]["verified"] is True
        from app.net import identity as idn
        assert idn.my_card("kunal")["business"] is True
        biz.complain("ravi", "@kunal.raj", "Bill galat aaya hai is mahine")
        import time
        body = json.dumps({"ticket": "T-1001", "status": "in_progress", "note": "Billing team dekh rahi hai", "ts": time.time(), "nonce": "n0nce-12345"}).encode()
        sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
        r = c.post("/hooks/hoola/kunal.raj/ticket", content=body, headers={"X-Hoola-Signature": sig})
        assert r.status_code == 200 and r.json()["status"] == "in_progress"
        assert c.post("/hooks/hoola/kunal.raj/ticket", content=body, headers={"X-Hoola-Signature": "sha256=bad"}).status_code == 400
    assert "kaam chal raha" in ev("ravi", "hoola_msg")[-1]["text"]
