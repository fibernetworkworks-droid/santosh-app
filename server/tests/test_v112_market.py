"""v0.112 Hoola Deals phase 4: trust tiers, verified-business credential, compare quotes, standing order mandate,
promo opt-in.

Meghana ("default") / Ravi ("ravi") buy; Kunal ("kunal") and Swati ("swati") sell."""
import asyncio
import copy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_net import _connect, ev
from tests.test_net_business import _team
from tests.test_v102_deal import LIST, _stock


def _last(tenant, kind="hoola_deal"):
    return ev(tenant, kind)[-1]


def _verified_kunal(bank_ok=True):
    from app.net import business as biz, deal as dl
    biz.setup("kunal", name="Kunal Traders", category="shop")
    dl.set_rules("kunal", upi_id="kunal.traders@okhdfcbank", payee_name="Kunal Traders")
    biz.request_verification("kunal", "27ABCDE1234F1Z5", "UDYAM-MH-01-0001234")
    return biz.operator_verify("kunal", True, bank_name_ok=bank_ok)


def test_trust_tiers_drive_auto_accept_and_reports_limit(env):
    net = _connect()
    dl = _stock()
    from app.net import trust
    meg = net.resolve("kunal", "@meghana.fnw")
    t = trust.tier("kunal", meg)
    assert t["tier"] == "known" and t["word"] == "jaan-pehchaan"
    assert trust.tier("kunal", "hl_nobody@x.example")["tier"] == "stranger"
    dl.set_rules("kunal", auto_quote="connected", auto_accept=True, auto_accept_max=50000)
    # known: the quote goes by itself (her rule says connected) but the order waits for his tap
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    dl.confirm("default", bid, by_tap=True, pay="counter")
    assert dl.show("default", bid)["state"] == "confirmed" and _last("kunal")["card"] == "accept"
    # trusted (his choice): accepted inside his cap
    trust.set_trust("kunal", "@meghana.fnw", "trusted")
    assert trust.tier("kunal", meg)["tier"] == "trusted"
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    dl.confirm("default", bid, by_tap=True, pay="counter")
    assert dl.show("default", bid)["state"] == "accepted"
    assert dl.show("kunal", _last("kunal")["id"])["tier"] == "trusted"
    # his rule can open auto accept to every connection; an explicit "known" wins over that only for trust
    trust.set_trust("kunal", "@meghana.fnw", "known")
    dl.set_rules("kunal", auto_accept_who="connected")
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    dl.confirm("default", bid, by_tap=True, pay="counter")
    assert dl.show("default", bid)["state"] == "accepted"
    with pytest.raises(dl.DealError):
        dl.set_rules("kunal", auto_accept_who="everyone")
    # 5 different owners report Meghana in 10 days -> limited: blocked tier, 3 lists a day at most
    from app.db import session
    from app.net.trust import TrustReport
    with session() as s:
        for i in range(4):
            s.add(TrustReport(tenant_id=f"other{i}", peer=meg, reason="spam"))
    trust.report("kunal", "@meghana.fnw", "spam")
    trust.report("kunal", "@meghana.fnw", "spam")          # once per reporter
    assert trust.limited(meg) and trust.tier("kunal", meg)["tier"] == "blocked"
    with pytest.raises(dl.DealError, match="bahut saari"):
        dl.ask("default", "@kunal.raj", LIST[:1])
    # the tool: trust changes are the owner's word only
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(dispatch("hoola_market", {"action": "trust_set", "to": "@meghana.fnw", "level": "trusted"},
                             Ctx("kunal", net.home_conv("kunal"), actor="peer:x")))
    r = asyncio.run(dispatch("hoola_market", {"action": "trust_show", "to": "@meghana.fnw"}, Ctx("kunal", net.home_conv("kunal"))))
    assert r["tier"] == "blocked" and "shikayat" in r["why"]


def test_verified_business_credential_checked_in_code(env):
    net = _connect()
    dl = _stock()
    from app.net import trust
    _verified_kunal()
    cred = trust.credential("kunal")
    kunal = net.resolve("default", "@kunal.raj")
    assert cred["sub"] == kunal and cred["upi"] == "kunal.traders@okhdfcbank" and "•••" in cred["gstin"]
    assert "1234F" not in str(cred)                         # the GSTIN never travels whole
    ok = trust.check(cred, kunal)
    assert ok["ok"] and ok["name"] == "Kunal Traders"
    # tampered, someone else's, expired, untrusted issuer: all refused
    bad = copy.deepcopy(cred)
    bad["name"] = "SBI Bank"
    assert not trust.check(bad, kunal)["ok"]
    assert not trust.check(cred, net.resolve("kunal", "@meghana.fnw"))["ok"]
    other = dict(cred, iss="evil.example")
    assert "bharosemand" in trust.check(other, kunal)["why"]
    assert not trust.check({"type": "x"}, kunal)["ok"]
    # it rides in the quote; her Hoola checks it; the payee shows verified only when it is the bank-matched UPI
    bid = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid = _last("kunal")["id"]
    dl.send_quote("kunal", sid)
    b = dl.show("default", bid)
    assert b["vbc"]["ok"] and b["vbc"]["name"] == "Kunal Traders"
    dl.confirm("default", bid, by_tap=True, pay="upi")
    dl.accept("kunal", sid)
    assert "Verified business" in _last("default")["say"]
    from app.net import dealpay as dp
    assert dp.pay_link("default", bid)["business_verified"] is True
    # he changes the UPI ID afterwards: no longer the verified payee (and her Hoola says so)
    dl.set_rules("kunal", upi_id="new.number@ybl")
    bid2 = dl.ask("default", "@kunal.raj", LIST[:1])["deal"]["id"]
    sid2 = _last("kunal")["id"]
    dl.send_quote("kunal", sid2)
    dl.confirm("default", bid2, by_tap=True, pay="upi")
    dl.accept("kunal", sid2)
    assert "verified UPI kunal.traders@okhdfcbank" in _last("default")["say"]
    assert dp.pay_link("default", bid2)["business_verified"] is False
    # the operator takes the badge back: the same credential stops working at once on this server
    from app.net import business as biz
    biz.operator_verify("kunal", False)
    assert "wapas" in trust.check(cred, kunal)["why"] and trust.credential("kunal") is None
    # without the bank-name check the credential carries no UPI at all
    _verified_kunal(bank_ok=False)
    assert trust.credential("kunal")["upi"] == ""


def test_compare_three_holds_quotes_sorts_and_thanks_the_rest(env):
    net = _team()                                            # Ravi is connected to Kunal and Swati
    from app.net import deal as dl, rfq
    dl.set_stock("kunal", [{"name": "Parle-G", "price": 450, "gst_pct": 18, "qty": 40},
                           {"name": "Tata Salt 1kg", "price": 25, "gst_pct": 5, "qty": 100}])
    dl.set_stock("swati", [{"name": "Parle-G", "price": 440, "gst_pct": 18, "qty": 40},
                           {"name": "Tata Salt 1kg", "price": 24, "gst_pct": 5, "qty": 5}])
    items = [{"item": "Parle-G", "qty": 10}, {"item": "Tata Salt 1kg", "qty": 20}]
    with pytest.raises(rfq.RfqError, match="2 se 5"):
        rfq.start("ravi", ["@kunal.raj"], items)
    out = rfq.start("ravi", ["@kunal.raj", "@swati.tech", "@nobody.here"], items, window_minutes=30)
    rid = out["rfq"]["id"]
    assert len(out["rfq"]["failed"]) == 1 and out["status"] == "open"
    # sellers' cards are normal; no seller is told about the other
    k_sid = [d for d in dl.deals("kunal", role="seller")][0]["id"]
    s_sid = [d for d in dl.deals("swati", role="seller")][0]["id"]
    assert "rfq" not in str(dl._get("kunal", k_sid).ask) and "swati" not in str(dl._get("kunal", k_sid).ask)
    n_before = len(ev("ravi", "hoola_deal"))
    dl.send_quote("swati", s_sid)                            # cheaper but short of salt
    assert len([e for e in ev("ravi", "hoola_deal")[n_before:] if e.get("card") == "confirm"]) == 0     # held
    assert rfq.show("ravi", rid)["state"] == "open"
    dl.send_quote("kunal", k_sid)                            # complete
    v = rfq.show("ravi", rid)
    assert v["state"] == "ready"
    card = _last("ravi", "hoola_rfq")
    assert card["card"] == "compare" and "Kunal" in card["say"]
    rows = [r for r in v["rows"] if r["quoted"]]
    assert rows[0]["complete"] and rows[0]["best"] and "Kunal" in rows[0]["with"]      # complete first, then by total
    assert rows[1]["short"] == ["Tata Salt 1kg"] and rows[1]["tier"] == "trusted"
    # her tap on one row: the normal confirm; the other gets the polite no
    dl.confirm("ravi", rows[0]["deal_id"], by_tap=True, pay="counter")
    assert rfq.show("ravi", rid)["state"] == "chosen"
    assert dl.show("swati", s_sid)["state"] == "cancelled" and dl._get("swati", s_sid).reason == rfq.THANKS
    # the window: a compare where one seller never answers shows the table when the time is over
    out = rfq.start("ravi", ["@kunal.raj", "@swati.tech"], items[:1], window_minutes=5)
    rid2 = out["rfq"]["id"]
    s2 = [d for d in dl.deals("swati", role="seller") if d["state"] == "asked"][0]["id"]
    dl.send_quote("swati", s2)
    assert rfq.show("ravi", rid2)["state"] == "open"
    rfq._set(rid2, closes_at=dl.now() - timedelta(minutes=1))
    rfq.tick()
    v2 = rfq.show("ravi", rid2)
    assert v2["state"] == "ready" and any(r.get("say") == "abhi jawab nahi" for r in v2["rows"])
    # split order keeps the others; close thanks the rest
    rfq.set_split("ravi", rid2, True)
    q_row = [r for r in v2["rows"] if r["quoted"]][0]
    dl.confirm("ravi", q_row["deal_id"], by_tap=True, pay="counter")
    rfq.close("ravi", rid2)
    k2 = [d for d in dl.deals("kunal", role="seller") if d["reason"] == rfq.THANKS]
    assert k2
    # the API + tool
    from app import main
    with TestClient(main.app) as cl:
        assert cl.get("/api/net/rfqs?all=true").status_code == 200        # (the app's own tenant has none)
    r = asyncio.run(dispatch("hoola_market", {"action": "compare_list"}, Ctx("ravi", net.home_conv("ravi"))))
    assert r["compares"]


def test_standing_order_signed_once_checked_every_run(env):
    net = _connect()
    dl = _stock()
    from app.net import mandate as md
    dl.set_rules("kunal", auto_quote="connected")
    until = (dl.now() + timedelta(days=60)).date().isoformat()
    # the model only drafts: nothing runs until her tap
    r = asyncio.run(dispatch("hoola_market", {"action": "standing_create", "to": "@kunal.raj", "items": LIST[:2],
                                              "days": ["mon"], "at": "10:00", "max_total": 6000, "until": until},
                             Ctx("default", net.home_conv("default"))))
    mid = r["mandate"]["id"]
    assert r["status"] == "needs_tap" and r["mandate"]["state"] == "draft" and r["mandate"]["number"] == "S-1"
    with pytest.raises(md.MandateError, match="tap"):
        md.sign("default", mid)
    with pytest.raises(md.MandateError, match="chalu nahi"):
        md.run_now("default", mid)
    from app import main
    with TestClient(main.app) as cl:
        res = cl.post(f"/api/net/mandates/{mid}/sign", json={})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "active"
    m = md.mandates("default")[0]
    assert m["next_run"] and "Somvar" in m["when"]
    # run 1: no base prices yet -> her own tap (sets the base)
    out = md.run_now("default", mid)
    bid = out["deal"]["id"]
    c = _last("default")
    assert c["card"] == "confirm" and "pehla order" in c["say"]
    dl.confirm("default", bid, by_tap=True, pay="counter")
    assert md._get("default", mid).base
    # run 2: inside the rule -> held, placed by itself after the hold
    bid = md.run_now("default", mid)["deal"]["id"]
    c = _last("default")
    assert c["card"] == "mandate" and "khud pakka" in c["say"]
    with pytest.raises(dl.DealError, match="tap"):
        dl.confirm("default", bid, by_mandate=mid)       # the hold isn't over yet
    run = [x for x in md._get("default", mid).runs if x["deal_id"] == bid][0]
    md._update_run(mid, bid, hold_until=(dl.now() - timedelta(minutes=1)).isoformat())
    md.tick()
    assert dl.show("default", bid)["state"] == "confirmed"
    assert "standing order S-1" in dl._get("kunal", _last("kunal")["id"]).history[-1]["say"]
    # run 3: his price went up 10% -> outside the rule, her tap with the reason
    dl.set_stock("kunal", [{"name": "Parle-G", "price": 495, "gst_pct": 18, "qty": 40, "unit": "carton"}])
    bid = md.run_now("default", mid)["deal"]["id"]
    c = _last("default")
    assert c["card"] == "confirm" and "Parle-G ka daam" in c["say"] and "10% zyada" in c["say"]
    md._update_run(mid, bid, status="holding", hold_until=(dl.now() - timedelta(minutes=1)).isoformat())
    assert md.allows("default", mid, dl._get("default", bid)) is False                   # code re-checks, not the status
    # run 4: back to normal price, she stops this one run
    dl.set_stock("kunal", [{"name": "Parle-G", "price": 450, "gst_pct": 18, "qty": 40, "unit": "carton"}])
    bid = md.run_now("default", mid)["deal"]["id"]
    md.hold_once("default", bid)
    md.tick()
    assert dl.show("default", bid)["state"] == "quoted"
    # an edited rule is not the signed rule
    md._set(mid, max_total=999999)
    bid = md.run_now("default", mid)["deal"]["id"]
    md._update_run(mid, bid, hold_until=(dl.now() - timedelta(minutes=1)).isoformat())
    assert md.allows("default", mid, dl._get("default", bid)) is False
    md._set(mid, max_total=6000)
    # pause / stop with one tap; the tool can't resume (that is her tap)
    md.set_state("default", mid, "pause")
    assert md._get("default", mid).state == "paused"
    with pytest.raises(ToolError, match="tap"):
        asyncio.run(dispatch("hoola_market", {"action": "standing_resume", "mandate_id": mid},
                             Ctx("default", net.home_conv("default"))))
    md.set_state("default", mid, "stop")
    assert md._get("default", mid).state == "ended"
    # the timer: next run time comes from her days / time; the end date ends it
    m2 = md.create("default", "@kunal.raj", LIST[:1], "daily", "07:00", 6000, until)["mandate"]["id"]
    md.sign("default", m2, by_tap=True)
    md._set(m2, next_run=dl.now() - timedelta(minutes=1))
    n = len(dl.deals("default", role="buyer"))
    md.tick()
    assert len(dl.deals("default", role="buyer")) == n + 1 and md._get("default", m2).next_run is not None
    _ = run


def test_offers_need_opt_in_cap_and_one_tap_opt_out(env):
    net = _connect()
    _stock()
    from app.net import promo as pr
    _verified_kunal()
    items = [{"name": "Parle-G", "price": 430, "mrp": 450, "unit": "carton"}]
    # no opt-in: nothing reaches her (and the model / tool can never send)
    with pytest.raises(pr.PromoError, match="tap"):
        pr.send_offer("kunal", "Diwali offer", "Parle-G sasta", items)
    assert pr.send_offer("kunal", "Diwali offer", "Parle-G sasta", items, by_tap=True)["sent"] == 0
    meg = net.resolve("kunal", "@meghana.fnw")
    r = net._post("kunal", meg, "promo_offer", {"offer_id": "x", "title": "Spam", "items": items}, "tk_1")
    assert r["ok"] is False and r["reason"] == "opt_in_needed"
    # she opts in to Kunal's offers
    pr.opt_in("default", "@kunal.raj")
    assert pr.audience("kunal")["on"] == 1
    pv = pr.preview("kunal", "Diwali offer", "Parle-G sasta", items)
    assert pv["to"] == 1 and pv["status"] == "needs_tap"
    assert pr.send_offer("kunal", "Diwali offer", "Parle-G sasta", items, by_tap=True)["sent"] == 1
    c = _last("default", "hoola_promo")
    assert c["card"] == "offer" and c["verified"] and c["items"][0]["price"] == 430
    # the weekly cap: 2 per seller per buyer (both sides count)
    assert pr.send_offer("kunal", "Offer 2", "", items, by_tap=True)["sent"] == 1
    out = pr.send_offer("kunal", "Offer 3", "", items, by_tap=True)
    assert out["sent"] == 0 and out["skipped"] == 1
    r = net._post("kunal", meg, "promo_offer", {"offer_id": "y", "title": "Extra", "items": items}, "tk_2")
    assert r["ok"] is False and r["reason"] == "weekly_limit"
    # an offer becomes a normal list only by her word / tap
    o = pr.inbox("default")[0]
    d = pr.order_from("default", o["id"])
    assert d["deal"]["state"] in ("asked", "quoted") and pr.inbox("default")[0]["status"] == "ordered"
    # one tap opt-out: both sides
    pr.opt_out("default", "@kunal.raj")
    assert pr.audience("kunal")["on"] == 0 and not pr.opted_in("default", net.resolve("default", "@kunal.raj"))
    # a report also opts her out; and the API
    pr.opt_in("default", "@kunal.raj")
    from app.net import trust
    trust.report("default", "@kunal.raj", "spam", "promo_offer")
    assert pr.audience("kunal")["on"] == 0
    from app import main
    with TestClient(main.app) as cl:
        assert cl.post("/api/net/promos/optin", json={"to": "@kunal.raj"}).json()["status"] == "on"
        assert cl.get("/api/net/promos").json()["opted_in"][0]["status"] == "on"
        assert cl.post("/api/net/promos/send", json={"title": "Naya", "items": items}).status_code == 200
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(dispatch("hoola_market", {"action": "offers_optin", "to": "@kunal.raj"},
                             Ctx("default", net.home_conv("default"), actor="peer:x")))
