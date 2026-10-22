"""v0.102 Hoola Deals phase 1: buyer list -> seller's code-built quote -> buyer's tap -> accept -> pack -> ready -> handover.

Meghana ("default", her avatar Santosh) is the kirana buyer; Kunal ("kunal", his avatar Meera) is the wholesaler."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_net import _connect, ev

LIST = [{"item": "Parle-G", "qty": 10, "unit": "carton"}, {"item": "Tata Salt 1kg", "qty": 20, "unit": "packet"},
        {"item": "Fortune oil 1L", "qty": 12}]


def _stock(qty_oil=50):
    from app.net import deal as dl
    dl.set_stock("kunal", [
        {"name": "Parle-G", "price": 450, "gst_pct": 18, "qty": 40, "unit": "carton", "aliases": ["parle g biscuit"]},
        {"name": "Tata Salt 1kg", "price": 25, "gst_pct": 5, "qty": 100, "unit": "packet"},
        {"name": "Fortune Sunflower Oil 1L", "price": 150, "gst_pct": 5, "qty": qty_oil, "unit": "bottle",
         "aliases": ["fortune oil 1l"]},
    ])
    return dl


def _deal(tenant, kind="hoola_deal"):
    return ev(tenant, kind)[-1]


def test_wholesaler_flow_end_to_end(env):
    net = _connect()
    dl = _stock()
    out = dl.ask("default", "@kunal.raj", LIST, mode="pickup", note="Kal subah tak")
    buyer_id = out["deal"]["id"]
    assert out["deal"]["state"] == "asked" and out["deal"]["role"] == "buyer"
    # the wholesaler's Hoola built the quote from HIS stock list (rules are off by default -> his card, nothing sent)
    card = _deal("kunal")
    assert card["card"] == "quote" and card["role"] == "seller" and card["waiting"] == "quote"
    draft = card["draft"]
    assert [l["status"] for l in draft["lines"]] == ["ok", "ok", "ok"]
    assert draft["lines"][2]["item"] == "Fortune Sunflower Oil 1L" and draft["lines"][2]["asked_as"] == "Fortune oil 1L"
    # 10 x 450 = 4500 + 18% 810 ; 20 x 25 = 500 + 25 ; 12 x 150 = 1800 + 90  -> 6800 + 925 = 7725
    assert draft["subtotal"] == 6800 and draft["gst"] == 925 and draft["total"] == 7725
    seller_id = card["id"]
    dl.send_quote("kunal", seller_id, valid_minutes=120)
    q = _deal("default")
    assert q["card"] == "confirm" and q["state"] == "quoted" and q["quote"]["total"] == 7725 and q["waiting"] == "confirm"
    # the model can never place the order: the tool only shows the card, and confirm without a tap is refused
    ctx = Ctx("default", net.home_conv("default"))
    r = asyncio.run(dispatch("hoola_deal", {"action": "confirm", "deal_id": buyer_id}, ctx))
    assert r["status"] == "needs_tap" and r["card"]["amount"].replace(",", "").endswith("7725")
    with pytest.raises(dl.DealError, match="tap"):
        dl.confirm("default", buyer_id)
    assert dl.show("kunal", seller_id)["state"] == "quoted"
    # her tap (the API route) places it
    from app import main
    with TestClient(main.app) as cl:
        res = cl.post(f"/api/net/deals/{buyer_id}/confirm", json={"v": 1})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "confirmed"
    acc = _deal("kunal")
    assert acc["card"] == "accept" and acc["state"] == "confirmed"
    a = dl.accept("kunal", seller_id, ready_by="")
    assert a["number"] == "D-1001" and len(a["pick_list"]) == 3
    assert _deal("kunal")["card"] == "pack"
    st = {s["name"]: s for s in dl.stock("kunal")}
    assert st["Parle-G"]["reserved"] == 10 and st["Parle-G"]["free"] == 30
    assert dl.show("default", buyer_id)["state"] == "accepted" and dl.show("default", buyer_id)["number"] == "D-1001"
    dl.packing("kunal", seller_id)
    assert dl.show("default", buyer_id)["state"] == "packing"
    dl.mark_ready("kunal", seller_id, place="Counter 3", minutes=240)
    rdy = _deal("default")
    assert rdy["card"] == "ready" and rdy["ready"]["place"] == "Counter 3"
    code = rdy["ready"]["code"]
    assert len(code) == 4 and "code" not in dl.show("kunal", seller_id)["ready"]          # staff check it, never see it
    with pytest.raises(dl.DealError, match="code"):
        dl.handed_over("kunal", seller_id, code="0000" if code != "0000" else "1111")
    dl.handed_over("kunal", seller_id, code=code,         # v0.106 money first: cash taken at the counter
                   collect={"mode": "cash", "amount": dl.show("kunal", seller_id)["pay"]["due_left"]})
    assert dl.show("default", buyer_id)["state"] == "handed_over" and dl.show("kunal", seller_id)["state"] == "handed_over"
    st = {s["name"]: s for s in dl.stock("kunal")}
    assert st["Parle-G"]["qty"] == 30 and st["Parle-G"]["reserved"] == 0
    # both sides hold the same signed history
    hb, hs = dl._get("default", buyer_id), dl._get("kunal", seller_id)
    assert hb.step == hs.step == 8 and hb.last_hash == hs.last_hash        # v0.106 +1: the counter receipt


def test_rules_auto_quote_auto_accept_and_partial_stock(env):
    _connect()
    dl = _stock(qty_oil=5)
    dl.set_rules("kunal", auto_quote="connected", auto_accept=True, auto_accept_max=50000, place="Godown gate")
    from app.net import trust                       # v0.112 auto accept only for her trusted tier (the default rule)
    trust.set_trust("kunal", "@meghana.fnw", "trusted")
    # oil is short (5 of 12): an incomplete quote never goes by itself, it waits for his card
    dl.ask("default", "@kunal.raj", LIST)
    c = _deal("kunal")
    assert c["card"] == "quote" and c["draft"]["short"] == ["Fortune Sunflower Oil 1L"] and c["draft"]["lines"][2]["qty"] == 5
    # a full list inside his rule: the quote goes by itself, her tap, then his rule accepts it (stock re-checked)
    out = dl.ask("default", "@kunal.raj", LIST[:2])
    bid = out["deal"]["id"]
    q = dl.show("default", bid)
    assert q["state"] == "quoted" and q["quote"]["total"] == 4500 + 810 + 500 + 25
    assert dl.STATS["auto_quotes"] >= 1
    dl.confirm("default", bid, by_tap=True)
    b = dl.show("default", bid)
    assert b["state"] == "accepted" and b["number"].startswith("D-")
    assert "niyam" in _deal("kunal")["say"]
    # above his auto limit: his card, not an automatic yes
    dl.set_rules("kunal", auto_accept_max=1000)
    bid2 = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    dl.confirm("default", bid2, by_tap=True)
    assert dl.show("default", bid2)["state"] == "confirmed" and _deal("kunal")["card"] == "accept"


def test_buyer_checks_every_number_and_the_order_of_steps(env):
    net = _connect()
    dl = _stock()
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _deal("kunal")["id"]
    s = dl._get("kunal", sid)
    # a quote whose total doesn't add up (450 x 10 = 4500 + 810, not 3000) is refused on arrival
    bad = {"v": 1, "lines": [{"item": "Parle-G", "asked": 10, "qty": 10, "unit": "carton", "price": 450, "gst_pct": 18,
                              "amount": 4500, "gst": 810, "status": "ok"}], "subtotal": 4500, "gst": 810, "total": 3000,
           "valid_until": (dl.now() + timedelta(hours=1)).isoformat()}
    r = net._post("kunal", s.peer, "deal_quote", dict(bad, step=s.step + 1, prev=s.last_hash), s.dkey, s.thread_id)
    assert r["ok"] is False and "hisaab galat" in r["reason"]
    assert dl.show("default", bid)["state"] == "asked"
    # an accept before any quote / confirm is out of order
    r = net._post("kunal", s.peer, "deal_accept", {"number": "X-1", "step": s.step + 1, "prev": s.last_hash}, s.dkey, s.thread_id)
    assert r["ok"] is False
    # a replayed / rewritten step (wrong prev) is refused
    good = dl.build_quote("kunal", dl._get("kunal", sid).ask["items"])
    r = net._post("kunal", s.peer, "deal_quote", {"v": 1, "lines": good["lines"], "subtotal": good["subtotal"], "gst": good["gst"],
                                                  "total": good["total"], "valid_until": bad["valid_until"],
                                                  "step": s.step + 1, "prev": "f" * 64}, s.dkey, s.thread_id)
    assert r["ok"] is False and "kram" in r["reason"]
    # the buyer can't send seller steps, and a seller can't confirm for the buyer
    with pytest.raises(dl.DealError):
        dl.send_quote("default", bid)
    with pytest.raises(dl.DealError):
        dl.accept("default", bid)


def test_expiry_changed_quote_and_cancel(env):
    _connect()
    dl = _stock()
    bid = dl.ask("default", "@kunal.raj", LIST[:2])["deal"]["id"]
    sid = _deal("kunal")["id"]
    dl.send_quote("kunal", sid)
    # he revises (v2): her confirm of v1 is refused, v2 goes through
    dl.send_quote("kunal", sid, lines=[{"item": "Parle-G", "price": 440}])
    q = dl.show("default", bid)["quote"]
    assert q["v"] == 2 and q["lines"][0]["price"] == 440
    with pytest.raises(dl.DealError, match="badal"):
        dl.confirm("default", bid, v=1, by_tap=True)
    # the quote runs out of time: no confirm, and the background tick marks it on both sides
    from app.db import session
    with session() as s:
        for row in s.query(dl.Deal).all():
            row.quote = dict(row.quote, valid_until=(dl.now() - timedelta(minutes=1)).isoformat())
    with pytest.raises(dl.DealError, match="samay"):
        dl.confirm("default", bid, by_tap=True)
    dl.tick()
    assert dl.show("kunal", sid)["state"] == "expired"
    # a fresh list, accepted, then cancelled by the buyer: his held stock comes back
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _deal("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True)
    dl.accept("kunal", sid)
    assert {s["name"]: s for s in dl.stock("kunal")}["Parle-G"]["reserved"] == 10
    dl.cancel("default", bid, "Plan badal gaya")
    assert dl.show("kunal", sid)["state"] == "cancelled" and dl.show("kunal", sid)["reason"] == "Plan badal gaya"
    assert {s["name"]: s for s in dl.stock("kunal")}["Parle-G"]["reserved"] == 0
    with pytest.raises(dl.DealError):
        dl.cancel("default", bid)


def test_safety_secrets_strangers_public_counter_and_tool(env):
    from tests.test_net_business import _team
    net = _team()                    # + swati and ravi (team chain kunal -> swati -> ravi -> kunal)
    dl = _stock()
    with pytest.raises(dl.DealError, match="OTP"):
        dl.ask("default", "@kunal.raj", [{"item": "Parle-G", "qty": 1, "note": "mera OTP 482913 hai"}])
    with pytest.raises(dl.DealError):
        dl.ask("default", "@kunal.raj", [{"item": "", "qty": 0}])
    # a stranger who is not connected and not a public business can't be sent a list
    with pytest.raises(dl.DealError, match="juda nahi"):
        dl.ask("default", "@ravi.field", LIST[:1])
    # a public business counter opens a customer connection by itself
    from app.net import business as biz
    biz.setup("swati", name="Swati Stores", category="shop", public=True)
    dl.set_stock("swati", [{"name": "Tata Salt 1kg", "price": 26, "gst_pct": 5, "qty": 10}])
    out = dl.ask("ravi", "@swati.tech", [{"item": "tata salt 1kg", "qty": 2}])
    assert out["deal"]["state"] == "asked" and _deal("swati")["draft"]["total"] == 54.6
    # an item the seller doesn't have is shown, never guessed
    dl.ask("default", "@kunal.raj", [{"item": "Maggi masala", "qty": 5}])
    assert _deal("kunal")["draft"]["missing"] == ["Maggi masala"]
    # only the owner changes rules / accepts; a staff turn can't
    staff = Ctx("kunal", net.home_conv("kunal"), actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(dispatch("hoola_deal", {"action": "rules", "op": "set", "settings": {"auto_accept": True}}, staff))
    me = Ctx("default", net.home_conv("default"))
    r = asyncio.run(dispatch("hoola_deal", {"action": "ask", "to": "Kunal", "items": [{"item": "Parle-G", "qty": 2}]}, me))
    assert r["deal"]["state"] == "asked"
    assert asyncio.run(dispatch("hoola_deal", {"action": "list"}, me))["deals"]
    from app import main
    with TestClient(main.app) as cl:
        assert cl.get("/api/net/stock").json()["stock"] == []
        assert cl.get("/api/net/deals?state=open").json()["deals"]
        assert cl.put("/api/net/deal_rules", json={"auto_quote": "sab"}).status_code == 400
        assert cl.post("/api/net/deals/nope/confirm", json={}).status_code in (400, 404)
