"""v0.106 Hoola Deals phase 3: payment locked to the deal, verified / pinned payee, receipts, khata, cancel window and
requests, the buyer's check after handover, disputes, timers.

Meghana ("default") buys from Kunal ("kunal", wholesaler)."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_net import _connect, ev
from tests.test_v102_deal import LIST, _stock


def _last(tenant, kind="hoola_deal"):
    return ev(tenant, kind)[-1]


def _order(dl, pay="upi", items=None):
    """Ask -> quote -> her tap (with a pay choice) -> his accept. Returns (buyer id, seller id)."""
    bid = dl.ask("default", "@kunal.raj", items or LIST[:1])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True, pay=pay)
    dl.accept("kunal", sid)
    return bid, sid


def _shop(**rules):
    net = _connect()
    dl = _stock()
    dl.set_rules("kunal", upi_id="kunal.traders@okhdfcbank", payee_name="Kunal Traders", **rules)
    return net, dl


def test_upi_payment_locked_pinned_payee_receipt_and_check(env):
    net, dl = _shop()
    from app.net import dealpay as dp
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    q = dl.show("default", bid)
    t = q["quote"]["terms"]
    assert "upi" in t["pay_options"] and "counter" in t["pay_options"] and "khata" not in t["pay_options"]
    assert t["payee"]["upi_id"] == "kunal.traders@okhdfcbank" and t["cancel_minutes"] == 30 and t["dispute_hours"] == 48
    with pytest.raises(dl.DealError, match="khata"):          # not offered to her
        dl.confirm("default", bid, by_tap=True, pay="khata")
    from app import main
    with TestClient(main.app) as cl:
        r = cl.post(f"/api/net/deals/{bid}/confirm", json={"v": 1, "pay": "upi"})
        assert r.status_code == 200, r.text
    dl.accept("kunal", sid)
    # his rule: the UPI payment card went by itself, locked to the total (10 x 450 + 18% = 5310)
    card = _last("default")
    assert card["card"] == "pay" and card["pay"]["due_left"] == 5310 and card["pay"]["status"] == "requested"
    assert "PIN aap hi" in card["say"] and "Pehli baar" in card["say"]
    # her Hoola builds the link itself, and only after she trusts this payee (first time)
    lk = dp.pay_link("default", bid)
    assert lk["status"] == "new_payee" and "url" not in lk
    lk = dp.trust_payee("default", bid)
    assert lk["status"] == "ok" and lk["url"].startswith("upi://pay?pa=kunal.traders%40okhdfcbank") and "am=5310.00" in lk["url"]
    assert "tn=Order%20D-" in lk["url"] and "cu=INR" in lk["url"]
    # the model can't pay: the tool only points to the card (no link) and a non-owner can't claim / confirm money
    ctx = Ctx("default", net.home_conv("default"))
    r = asyncio.run(dispatch("hoola_deal", {"action": "pay", "deal_id": bid}, ctx))
    assert r["status"] == "needs_tap" and "url" not in r["card"]
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(dispatch("hoola_deal", {"action": "received", "deal_id": sid, "amount": 5310},
                             Ctx("kunal", net.home_conv("kunal"), actor="peer:x")))
    # she says she paid: only a claim at his end
    with pytest.raises(dl.DealError, match="UTR"):
        dp.claim_paid("default", bid, "12")
    dp.claim_paid("default", bid, "412345678901")
    m = _last("kunal")
    assert m["card"] == "money" and "Paisa mila" in m["say"] and dl.show("kunal", sid)["pay"]["status"] == "claimed"
    # no handover while money is open
    dl.packing("kunal", sid)
    dl.mark_ready("kunal", sid, place="Counter 1", minutes=120)
    code = _last("default")["ready"]["code"]
    with pytest.raises(dl.DealError, match="Pehle paisa"):
        dl.handed_over("kunal", sid, code)
    with pytest.raises(dl.DealError, match="zyada"):
        dp.received("kunal", sid, 9999)
    out = dp.received("kunal", sid, mode="upi", utr="412345678901")
    assert out["receipt"] == "R-0001" and out["status"] == "paid"
    rc = _last("default")
    assert rc["card"] == "receipt" and "R-0001" in rc["say"] and rc["pay"]["status"] == "paid" and rc["pay"]["due_left"] == 0
    dl.handed_over("kunal", sid, code)
    chk = _last("default")
    assert chk["card"] == "check" and chk["actions"][:2] == ["ok", "dispute"]
    dp.all_ok("default", bid)
    assert dl.show("default", bid)["state"] == "closed" and dl.show("kunal", sid)["state"] == "closed"
    hb, hs = dl._get("default", bid), dl._get("kunal", sid)
    assert hb.last_hash == hs.last_hash
    with TestClient(main.app) as cl:
        pdf = cl.get(f"/api/net/deals/{bid}/receipt.pdf")
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_amount_tamper_and_changed_payee_are_stopped(env):
    net, dl = _shop()
    from app.net import dealpay as dp
    bid, sid = _order(dl)
    dp.trust_payee("default", bid)
    # a seller-side record that asks for more than the deal: her Hoola refuses it, nothing changes on either side
    d = dl._get("kunal", sid)
    d.pay = dict(d.pay, due=99999.0, requests=[])
    dl._save(d)
    with pytest.raises(dl.DealError, match="nahi pahuncha"):
        dp.request_payment("kunal", sid)
    assert dl.show("default", bid)["pay"]["requests"][-1]["amount"] == 5310
    # a part payment only when he marks it part, never above what is due
    d = dl._get("kunal", sid)
    d.pay = dict(d.pay, due=5310.0)
    dl._save(d)
    with pytest.raises(dl.DealError, match="baaki"):
        dp.request_payment("kunal", sid, 6000)
    dp.request_payment("kunal", sid, 2000)
    assert "hissa" in _last("default")["say"] and dp.pay_link("default", bid)["amount"] == 2000
    # next order: he changed his UPI ID -> her Hoola blocks the link until she checks and taps
    dl.set_rules("kunal", upi_id="someone.else@ybl")
    bid2, sid2 = _order(dl)
    assert "UPI badla" in _last("default")["say"]
    lk = dp.pay_link("default", bid2)
    assert lk["status"] == "payee_changed" and lk["was"] == "kunal.traders@okhdfcbank" and "url" not in lk
    assert dp.trust_payee("default", bid2)["status"] == "ok"
    with pytest.raises(dl.DealError, match="UPI ID"):
        dl.set_rules("kunal", upi_id="not a vpa")


def test_cancel_window_request_and_refund_due(env):
    net, dl = _shop()
    from app.net import dealpay as dp
    bid, sid = _order(dl)
    dl.cancel("default", bid, "galti se")                     # inside the free window
    assert dl.show("kunal", sid)["state"] == "cancelled"
    # his window is 0 minutes: her cancel becomes a request he answers
    dl.set_rules("kunal", cancel_minutes=0)
    bid, sid = _order(dl)
    dp.received("kunal", sid, 1000, mode="cash")              # part paid at the counter earlier
    r = dl.cancel("default", bid, "zaroorat nahi")
    assert r["status"] == "cancel_requested" and dl.show("default", bid)["state"] == "accepted"
    assert _last("kunal")["card"] == "cancel_req" and "cancel_no" in dl.show("kunal", sid)["actions"]
    with pytest.raises(dl.DealError, match="pehle se"):
        dl.cancel("default", bid, "phir se")
    dp.cancel_answer("kunal", sid, False, "maal pack ho chuka")
    assert "nahi maana" in _last("default")["say"] and dl.show("default", bid)["state"] == "accepted"
    d = dl._get("default", bid)
    d.cancel_req = {}
    dl._save(d)
    dl.cancel("default", bid, "ab bhi nahi chahiye")
    dp.cancel_answer("kunal", sid, True)
    s, b = dl.show("kunal", sid), dl.show("default", bid)
    assert s["state"] == b["state"] == "cancelled"
    assert s["pay"]["refund_due"] == 1000 and "refund" in s["actions"] and b["pay"]["refund_due"] == 1000
    dp.refund("kunal", sid, utr="412345678901")
    assert dl.show("default", bid)["pay"]["status"] == "refunded" and dl.show("kunal", sid)["pay"]["refund_due"] == 0


def test_dispute_answer_escalate_and_window(env):
    net, dl = _shop()
    from app.net import dealpay as dp
    bid, sid = _order(dl, pay="counter", items=LIST[:2])
    dl.mark_ready("kunal", sid, place="Gate", minutes=60)
    code = _last("default")["ready"]["code"]
    with pytest.raises(dl.DealError, match="poora"):
        dl.handed_over("kunal", sid, code, collect={"mode": "cash", "amount": 100})
    dl.handed_over("kunal", sid, code, collect={"mode": "cash", "amount": dl.show("kunal", sid)["pay"]["due_left"]})
    with pytest.raises(dl.DealError, match="nahi thi"):
        dp.dispute("default", bid, "short", [{"item": "Parle-G", "qty": 50}])
    dp.dispute("default", bid, "damaged", [{"item": "Tata Salt 1kg", "qty": 2}], "do packet phate the")
    dc = _last("kunal")
    assert dc["card"] == "dispute" and "Tata Salt 1kg (2)" in dc["say"] and dl.show("kunal", sid)["state"] == "disputed"
    with pytest.raises(dl.DealError, match="wajah"):
        dp.resolve("kunal", sid, "reject")
    dp.resolve("kunal", sid, "refund", 52.5, "maafi")
    assert _last("default")["card"] == "resolve" and dl.show("default", bid)["pay"]["refund_due"] == 52.5
    r = dp.dispute_close("default", bid, False, "poora paisa chahiye")
    assert r["status"] == "escalated" and "1915" in r["official"] and "e-Daakhil" in r["official"]
    assert "nahi maana" in _last("kunal")["say"]
    dp.resolve("kunal", sid, "replace", note="kal naye packet")
    dp.dispute_close("default", bid, True)
    assert dl.show("kunal", sid)["state"] == "closed" and dl.show("default", bid)["state"] == "closed"
    # a second order: the window ends -> no dispute; the tick closes it by itself
    bid, sid = _order(dl, pay="counter")
    dl.mark_ready("kunal", sid, place="Gate", minutes=60)
    code = _last("default")["ready"]["code"]
    dl.handed_over("kunal", sid, code, collect={"mode": "upi", "amount": dl.show("kunal", sid)["pay"]["due_left"]})
    for t, i in (("default", bid), ("kunal", sid)):
        d = dl._get(t, i)
        d.handed_at = dl.now() - timedelta(hours=49)
        dl._save(d)
    with pytest.raises(dl.DealError, match="samay"):
        dp.dispute("default", bid, "short", note="kam tha")
    dp.tick()
    assert dl.show("default", bid)["state"] == "closed" and dl.show("kunal", sid)["state"] == "closed"


def test_khata_limit_book_and_settle(env):
    net, dl = _shop(khata=True)
    from app.net import dealpay as dp, khata as kh
    # no khata for her until he opens one
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    dl.send_quote("kunal", _last("kunal")["id"])
    assert "khata" not in dl.show("default", bid)["quote"]["terms"]["pay_options"]
    dl.cancel("default", bid)
    kh.open_account("kunal", "@meghana.fnw", 3000, 15)
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]       # 5310 > 3000 left
    dl.send_quote("kunal", _last("kunal")["id"])
    assert "khata" not in dl.show("default", bid)["quote"]["terms"]["pay_options"]
    dl.cancel("default", bid)
    kh.open_account("kunal", "@meghana.fnw", 10000, 15)
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    t = dl.show("default", bid)["quote"]["terms"]
    assert "khata" in t["pay_options"] and t["khata"] == {"limit_left": 10000, "days": 15}
    dl.confirm("default", bid, by_tap=True, pay="khata")
    dl.accept("kunal", sid)
    s, b = dl.show("kunal", sid), dl.show("default", bid)
    assert s["pay"]["status"] == b["pay"]["status"] == "khata" and s["pay"]["due_on"] and b["pay"]["due_on"] == s["pay"]["due_on"]
    book_s, book_b = kh.book("kunal"), kh.book("default")
    assert book_s["owed_total"] == 5310 and book_s["owed_to_me"][0]["limit_left"] == 4690
    assert book_b["owe_total"] == 5310
    # a khata order hands over without collecting
    dl.mark_ready("kunal", sid, place="Gate", minutes=60)
    dl.handed_over("kunal", sid, _last("default")["ready"]["code"])
    # settle: a payment card for the balance (never above what HER mirror says), her claim, his receipt
    kh.request("kunal", "@meghana.fnw", 3000)
    c = _last("default", "hoola_khata")
    assert c["card"] == "pay" and c["amount"] == 3000
    assert kh.pay_link("default", "@kunal.raj")["status"] == "new_payee"   # first payment to him: her tap first
    assert "am=3000.00" in kh.trust_payee("default", "@kunal.raj")["url"]
    kh.claim_paid("default", "@kunal.raj", "412345678901")
    assert _last("kunal", "hoola_khata")["card"] == "money"
    with pytest.raises(kh.KhataError, match="zyada"):
        kh.received("kunal", "@meghana.fnw", 9000)
    out = kh.received("kunal", "@meghana.fnw", 3000, "upi", "412345678901")
    assert out["receipt"].startswith("R-") and out["balance"] == 2310
    assert kh.book("default")["owe_total"] == 2310 and _last("default", "hoola_khata")["card"] == "receipt"
    # a forged khata card above her mirror is refused
    r = net._post("kunal", dl._get("kunal", sid).peer, "khata_pay",
                  {"ref": "x", "amount": 50000, "upi_id": "kunal.traders@okhdfcbank", "name": "K"}, "tk_x")
    assert r["ok"] is False


def test_unaccepted_order_auto_cancels_and_reminders(env):
    net, dl = _shop()
    from app.net import dealpay as dp
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    dl.confirm("default", bid, by_tap=True, pay="upi")
    from app.db import session
    from app.net.deal import Deal
    with session() as s:
        s.get(Deal, bid).updated_at = dl.now() - timedelta(hours=4)
    dp.tick()
    assert "pakka nahi kiya" in _last("default")["say"] and dl.show("default", bid)["state"] == "confirmed"
    with session() as s:
        s.get(Deal, bid).updated_at = dl.now() - timedelta(hours=7)
    dp.tick()
    assert dl.show("default", bid)["state"] == "cancelled" and dl.show("kunal", sid)["state"] == "cancelled"
    # unpaid payment card: one reminder after a day
    bid, sid = _order(dl)
    d = dl._get("default", bid)
    p = dict(d.pay)
    p["requests"] = [dict(p["requests"][-1], at=(dl.now() - timedelta(hours=25)).isoformat())]
    d.pay = p
    dl._save(d)
    dp.tick()
    assert "baaki hai" in _last("default")["say"]
    n = len(ev("default", "hoola_deal"))
    dp.tick()
    assert len(ev("default", "hoola_deal")) == n                       # once only
    # Mere Niyam carries the money rules and reads them back
    from app.avatar import service as av
    so = av.get("kunal")["rules"]["selling"]
    assert so["pay_before"] == "handover" and so["dispute_hours"] == 48
    assert any(x.startswith("Paisa:") for x in av.get("kunal")["rules_summary"])
    assert av.clean_rules({"selling": {"dispute_hours": 99999, "pay_before": "never"}})["selling"]["dispute_hours"] == 720
