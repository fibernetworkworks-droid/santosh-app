"""v0.105 Hoola Deals phase 2: stock on catalogue items, code-built quotes (bulk prices, substitutes), the auto-quote
rule in Mere Niyam, pick lists to the packers' own Hoolas, pickup code at the counter (new code when time runs out).

Meghana ("default") buys; Kunal ("kunal") sells; Swati ("swati") packs for Kunal; Ravi ("ravi") is connected to Kunal
but is NOT his packer."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_net import ev
from tests.test_net_business import _team

LIST = [{"item": "Parle-G", "qty": 10, "unit": "carton"}, {"item": "Tata Salt 1kg", "qty": 20}]


def _shop():
    net = _team()
    from app.net import deal as dl
    dl.set_stock("kunal", [
        {"name": "Parle-G", "price": 450, "gst_pct": 18, "qty": 40, "unit": "carton", "low_at": 25,
         "tiers": [{"min": 10, "price": 430}, {"min": 50, "price": 420}]},
        {"name": "Tata Salt 1kg", "price": 25, "gst_pct": 5, "qty": 100, "unit": "packet"},
        {"name": "Fortune Oil 1L", "price": 150, "gst_pct": 5, "qty": 0, "unit": "bottle", "subs": ["Saffola Oil 1L"]},
        {"name": "Saffola Oil 1L", "price": 165, "gst_pct": 5, "qty": 8, "unit": "bottle"},
        {"name": "Godown supplies", "price": 1, "qty": 999, "public": False},
    ])
    return net, dl


def _packer():
    from app.employee import service as emp
    from app.net import identity as idn
    emp.add_member("kunal", "Swati", address=idn.my_card("swati")["address"], role="staff", duties=["packing"])


def _last(tenant, kind="hoola_deal"):
    return ev(tenant, kind)[-1]


def test_mere_niyam_selling_rules_and_catalogue(env):
    net, dl = _shop()
    from app.avatar import service as av
    r = dl.set_rules("kunal", auto_quote="trusted", auto_quote_max=40000, trusted=["Meghana"], catalog="connected",
                     show_stock=True, place="Counter 3")
    rules = av.get("kunal")["rules"]["selling"]
    assert rules["auto_quote"] == "trusted" and rules["auto_quote_max"] == 40000 and rules["trusted"] == ["meghana"] or \
        rules["trusted"] == ["Meghana"]
    assert r["place"] == "Counter 3" and any("Bechna" in x for x in av.get("kunal")["rules_summary"])
    # Mere Niyam keeps its fixed limits whatever is sent
    assert av.clean_rules({"selling": {"auto_quote": "everyone", "auto_quote_max": 10 ** 12}})["selling"]["auto_quote"] == "off"
    assert av.clean_rules({"selling": {"auto_quote_max": 10 ** 12}})["selling"]["auto_quote_max"] == av.SELL_MAX
    # the buyer's avatar sees his price list (public items only, stock as yes / no because he allows it)
    cat = dl.catalog_of("default", "@kunal.raj")
    names = {i["item"]: i for i in cat["items"]}
    assert "Godown supplies" not in names and names["Parle-G"]["price"] == 450 and names["Fortune Oil 1L"]["in_stock"] is False
    dl.set_rules("kunal", catalog="off")
    with pytest.raises(dl.DealError, match="share"):
        dl.catalog_of("default", "@kunal.raj")
    # the v0.33 business price list is the stock list now
    from app.net import business as biz
    biz.setup("kunal", name="Sharma Traders", category="shop", catalog=[{"item": "Maggi 12 pack", "price": 168, "unit": "box"}])
    assert {s["name"]: s for s in dl.stock("kunal")}["Maggi 12 pack"]["price"] == 168
    assert any(c["item"] == "Maggi 12 pack" for c in biz.profile("kunal")["catalog"])
    # a stock sheet comes in from CSV
    out = dl.import_stock("kunal", "stock.csv", "Item Name,Rate,Closing Stock,GST %\nSurf Excel 1kg,120,30,18\n,,,\n".encode())
    assert out["saved"] == 1 and {s["name"]: s for s in dl.stock("kunal")}["Surf Excel 1kg"]["qty"] == 30
    with pytest.raises(dl.DealError):
        dl.import_stock("kunal", "x.csv", b"a,b\n1,2\n")


def test_bulk_price_substitute_and_auto_quote_rule(env):
    net, dl = _shop()
    dl.set_rules("kunal", auto_quote="trusted", trusted=["Meghana"], auto_quote_max=50000)
    # 10 cartons reach the bulk price (430), not 450; trusted Meghana + every line in stock -> the quote goes by itself
    bid = dl.ask("default", "@kunal.raj", LIST)["deal"]["id"]
    q = dl.show("default", bid)
    assert q["state"] == "quoted" and q["quote"]["lines"][0]["price"] == 430
    # oil is out; his own "can stand in" item is offered as a substitute line, and such a quote never goes alone
    dl.ask("default", "@kunal.raj", [{"item": "Fortune oil 1L", "qty": 5}])
    c = _last("kunal")
    lines = c["draft"]["lines"]
    assert c["card"] == "quote" and lines[0]["status"] == "out" and lines[1]["status"] == "substitute"
    assert lines[1]["item"] == "Saffola Oil 1L" and lines[1]["qty"] == 5 and lines[1]["asked_as"] == "Fortune oil 1L"
    dl.send_quote("kunal", c["id"])
    q2 = _last("default")
    assert q2["card"] == "confirm" and q2["quote"]["total"] == round(5 * 165 * 1.05, 2)
    # team members count as trusted; a business customer he removes from the list gets his card, not an automatic quote
    dl.ask("ravi", "@kunal.raj", LIST[:1])
    assert _last("kunal")["card"] == "info"
    dl.set_rules("kunal", trusted=[])
    dl.ask("default", "@kunal.raj", LIST[:1])
    assert _last("kunal")["card"] == "quote"


def test_pick_list_to_packer_packed_ready_and_counter_code(env):
    net, dl = _shop()
    _packer()
    bid = dl.ask("default", "@kunal.raj", LIST)["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True)
    a = dl.accept("kunal", sid)
    assert a["packers"] == ["Swati"] and "Swati" in _last("kunal")["say"]
    # Swati's own Hoola got the pick list
    task = _last("swati", "hoola_pick")
    assert task["card"] == "task" and task["number"] == a["number"] and len(task["lines"]) == 2
    assert task["customer"] == "Meghana ka Santosh"
    from app.net import pick as pk
    # Ravi is not a packer: a pick update from him is refused
    from app.net import identity as idn
    from app.net import service as nsvc
    s_deal = dl._get("kunal", sid)
    r = nsvc._post("ravi", idn.my_card("kunal")["address"], "pick_update", {"dkey": s_deal.dkey, "status": "packed"}, "tk_x")
    assert r["ok"] is False and "nahi di gayi" in r["reason"]
    # Swati says "packing" -> the buyer sees packing; then "packed" -> his rule (auto_ready on) sends the pickup code
    pk.mark("swati", task["id"], "packing")
    assert dl.show("default", bid)["state"] == "packing"
    out = pk.mark("swati", task["id"], "packed")
    assert out["status"] == "ready"
    rdy = _last("default")
    assert rdy["card"] == "ready" and len(rdy["ready"]["code"]) == 4
    assert _last("swati", "hoola_pick")["status"] == "ready"
    # at the counter Swati types the code the buyer shows; a wrong one is refused, the right one closes the deal
    wrong = "1111" if rdy["ready"]["code"] != "1111" else "2222"
    with pytest.raises(pk.PickError, match="code"):
        pk.handover("swati", task["id"], wrong)
    pk.handover("swati", task["id"], rdy["ready"]["code"],
                collect={"mode": "cash", "amount": _last("swati", "hoola_pick")["collect"]})
    assert dl.show("default", bid)["state"] == "handed_over" and dl.show("kunal", sid)["state"] == "handed_over"
    assert pk.picks("swati") == []
    # Parle-G fell to 30 free... its 'tell me' level is 25 -> not yet; stock moved out of the count
    st = {x["name"]: x for x in dl.stock("kunal")}
    assert st["Parle-G"]["qty"] == 30 and st["Parle-G"]["reserved"] == 0


def test_short_pick_goes_to_owner_and_no_auto_ready(env):
    net, dl = _shop()
    _packer()
    dl.set_rules("kunal", auto_ready=False)
    bid = dl.ask("default", "@kunal.raj", [{"item": "Parle-G", "qty": 20}])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True)
    dl.accept("kunal", sid)
    from app.net import pick as pk
    tid = _last("swati", "hoola_pick")["id"]
    pk.mark("swati", tid, "short", short=[{"item": "Parle-G", "qty": 18}], note="2 carton phate hue")
    c = _last("kunal")
    assert c["card"] == "pack" and "Swati" in c["say"] and "18" in c["say"]
    assert dl.show("default", bid)["state"] == "accepted"            # the buyer hears nothing until she decides
    pk.mark("swati", tid, "packed")
    assert _last("kunal")["card"] == "pack" and dl.show("default", bid)["state"] == "accepted"
    dl.mark_ready("kunal", sid, place="Counter 3", minutes=60)
    code1 = _last("default")["ready"]["code"]
    # nobody came in time: one reminder each side, then a new code and more time; the old code stops working
    from app.db import session
    with session() as s:
        for row in s.query(dl.Deal).filter(dl.Deal.state == "ready").all():
            row.ready = dict(row.ready, until=(dl.now() - timedelta(minutes=5)).isoformat())
    dl.tick()
    assert "samay par nahi" in _last("kunal")["say"] and "samay nikal" in _last("default")["say"]
    dl.mark_ready("kunal", sid, minutes=120)
    code2 = _last("default")["ready"]["code"]
    if code1 != code2:
        with pytest.raises(dl.DealError):
            dl.handed_over("kunal", sid, code1)
    dl.handed_over("kunal", sid, code2, collect={"mode": "upi", "amount": dl.show("kunal", sid)["pay"]["due_left"]})
    assert _last("swati", "hoola_pick")["status"] == "handed_over"


def test_low_stock_cancel_note_tools_and_api(env):
    net, dl = _shop()
    _packer()
    bid = dl.ask("default", "@kunal.raj", [{"item": "Parle-G", "qty": 16}])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True)
    dl.accept("kunal", sid)
    dl.mark_ready("kunal", sid)
    code = _last("default")["ready"]["code"]
    dl.handed_over("kunal", sid, code, collect={"mode": "cash", "amount": dl.show("kunal", sid)["pay"]["due_left"]})
    assert "Stock kam: Parle-G" in _last("kunal")["say"]
    assert [x["name"] for x in dl.low_stock("kunal")] == ["Parle-G"]
    # a cancelled order tells the packer to stop
    bid = dl.ask("default", "@kunal.raj", [{"item": "Tata Salt 1kg", "qty": 2}])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True)
    dl.accept("kunal", sid)
    dl.cancel("default", bid, "Nahi chahiye")
    assert _last("swati", "hoola_pick")["status"] == "cancelled"
    # tools: the packer's own Hoola, and the seller's rules (owner only)
    sw = Ctx("swati", net.home_conv("swati"))
    assert asyncio.run(dispatch("hoola_pick", {"action": "list"}, sw))["picks"] == []
    with pytest.raises(ToolError):
        asyncio.run(dispatch("hoola_pick", {"action": "packed"}, sw))
    me = Ctx("default", net.home_conv("default"))
    cat = asyncio.run(dispatch("hoola_deal", {"action": "catalog", "to": "@kunal.raj"}, me))
    assert any(i["item"] == "Parle-G" for i in cat["items"])
    kn = Ctx("kunal", net.home_conv("kunal"))
    assert asyncio.run(dispatch("hoola_deal", {"action": "stock", "op": "low"}, kn))["low"]
    staff = Ctx("kunal", net.home_conv("kunal"), actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(dispatch("hoola_deal", {"action": "stock", "op": "import", "file_id": "f"}, staff))
    from app import main
    with TestClient(main.app) as cl:
        assert cl.get("/api/net/picks").json()["picks"] == []
        r = cl.post("/api/net/stock/import", files={"file": ("s.csv", b"naam,daam,stock\nVim Bar,10,50\n", "text/csv")})
        assert r.status_code == 200 and r.json()["saved"] == 1
        assert cl.get("/api/net/deals/catalog", params={"to": "@kunal.raj"}).status_code == 200
        assert cl.put("/api/net/deal_rules", json={"catalog": "sab"}).status_code == 400
        assert cl.post("/api/net/picks/nope/packed", json={}).status_code == 400
