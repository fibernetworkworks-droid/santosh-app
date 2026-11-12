"""Dukaan Desk (Retail & e-commerce register Wave 1). Rows in, checks out: formulas shown, heuristics labelled, a named decider, nothing stored or changed."""
import asyncio
import inspect

import pytest

from app.retaildesk import online, shop
from tests.test_life import conv_ctx


def test_day_summary_forecast_and_reorder_numbers():
    d = shop.day_summary([{"time": "2026-11-05T10:15:00", "amount": 100, "mode": "cash", "item": "milk"},
                          {"time": "2026-11-05T11:05:00", "amount": 300, "mode": "UPI", "item": "rice"},
                          {"time": "2026-11-05T11:40:00", "amount": 50, "mode": "credit", "item": "rice"}])
    assert d["total"] == 450 and d["best_hour"] == 11 and d["best_hour_amount"] == 350 and d["credit_given"] == 50 and d["top_items"][0]["item"] == "rice"
    with pytest.raises(ValueError):
        shop.day_summary([])
    f = shop.forecast([100, 110, 120, 130], 2, {"2": 1.5})
    assert f["base_avg_last4"] == 115 and f["forecast"][0]["estimate"] == 120.0 and f["forecast"][1]["estimate"] == 187.5 and "not a promise" in f["decider"]
    with pytest.raises(ValueError):
        shop.forecast([1, 2, 3])
    r = shop.reorder([{"name": "a", "stock": 5, "daily_sales": 2, "lead_days": 2, "cost": 10, "last_sold": "2026-09-01", "expiry": "2026-11-20"},
                      {"name": "b", "stock": 100, "daily_sales": 1, "lead_days": 1, "cost": 5, "last_sold": "2026-11-04"}], "2026-11-05")
    assert [x["name"] for x in r["reorder"]] == ["a"] and r["reorder"][0]["order_qty"] == 13 and "7 days cover" in r["formula"]
    assert r["expiring"][0]["days_left"] == 15 and r["cash_stuck_in_dead_stock"] == 50 and "tap" in r["decider"]


def test_margin_mrp_licences_oversell():
    m = shop.margin([{"name": "x", "cost": 10, "selling": 12, "mrp": 11}, {"name": "y", "cost": 10, "selling": 8, "mrp": 20}, {"name": "z", "cost": 10, "selling": 20, "mrp": 25}])
    issues = " ".join(f["issue"] for f in m["flags"])
    assert "selling above MRP" in issues and "below the cost" in issues and len(m["flags"]) == 2 and m["items"][2]["margin_pct_on_selling"] == 50.0
    l = shop.licences([{"name": "FSSAI", "expiry": "2026-11-20"}, {"name": "Trade", "expiry": "2026-10-01"}, {"name": "Fire", "expiry": "2027-06-01"}], "2026-11-05")
    assert [x["status"] for x in l["licences"]] == ["expired", "renew soon", "ok"] and l["gst_dates"][0]["next_due"] == "2026-11-11" and l["verify"]
    o = shop.oversell([{"channel": "web", "stock": 3, "open_orders": 2}, {"channel": "amz", "stock": 2, "open_orders": 3}], 1)
    assert o["risk"] == "OVERSELL" and o["short_by"] == 1 and o["channels"][1]["oversold"]
    assert shop.oversell([{"channel": "w", "stock": 10, "open_orders": 1}])["risk"] == "ok"


def test_rto_reconcile_claims_landed_scam_gst():
    r = online.rto_risk([{"id": 1, "address": "near temple", "pincode": "4", "phone": "123", "cod": True, "amount": 4000, "prior_rto": 1},
                         {"id": 2, "address": "Flat 12, Green Park Society, Baner Road, Pune", "pincode": "411045", "phone": "9876543210", "cod": False}])
    assert [o["level"] for o in r["orders"]] == ["high", "low"] and r["orders"][0]["suggest"] and "verdict" in r["kind"] + r["note"]
    c = online.reconcile([{"ref": "a", "amount": 100}, {"ref": "b", "amount": 50}], [{"ref": "a", "amount": 97, "fee": 3}, {"ref": "z", "amount": 5}])
    st = {x["ref"]: x["status"] for x in c["rows"]}
    assert st == {"a": "match", "b": "not_settled", "z": "not_in_sales"} and c["fees_total"] == 3
    k = online.claims("100% genuine, cures diabetes, only 3 left, FSSAI approved")
    kinds = {f["kind"] for f in k["flags"]}
    assert {"absolute claim", "health claim"} <= kinds and "brand" in k["missing_listing_facts"] and "publish" in k["decider"]
    la = online.landed([{"seller": "A", "price": 100, "shipping": 50}, {"seller": "B", "price": 120, "shipping": 0, "coupon_off": 10}])
    assert la["cheapest"] == "B" and la["ranked"][0]["landed_total"] == 110 and la["note"]
    sc = online.shop_scam("http://paytm-kyc-update.xyz", 50, 200, "pay advance on upi now")
    assert len(sc["signals"]) == 2 and sc["link"] and "proof" in sc["kind"]
    g = online.gst_split([{"name": "t", "qty": 2, "price": 118, "gst_pct": 18, "hsn": "6109"}, {"name": "u", "qty": 1, "price": 100, "gst_pct": 5}], "MH", "MH")
    assert g["grand_total"] == 336.0 and g["lines"][0]["cgst"] == 18.0 and g["missing_hsn"] == ["u"] and "intra" in g["supply"]
    assert "igst" in online.gst_split([{"name": "t", "qty": 1, "price": 118, "gst_pct": 18}], "MH", "KA")["lines"][0]
    for bad in (lambda: online.rto_risk([]), lambda: online.landed([]), lambda: online.claims(" "), lambda: online.gst_split([])):
        with pytest.raises(ValueError):
            bad()


def test_tool_registered_routed_and_guarded():
    from app import voice
    from app.agent import retaildesk_tools as RT
    from app.agent import tools
    from app.agent.tools import ToolError
    assert "dukaan_desk" in tools.HANDLERS and tools.FAMILY_OF["dukaan_desk"] == "retaildesk" and voice.call_route("dukaan_desk") == "kaam"
    ctx = conv_ctx()
    assert asyncio.run(RT._dukaan_desk(ctx, action="margin", items=[{"name": "x", "cost": 1, "selling": 2, "mrp": 3}]))["items"]
    for bad in (dict(action="nope"), dict(action="forecast", weekly_sales=[1]), dict(action="day_summary")):
        with pytest.raises(ToolError):
            asyncio.run(RT._dukaan_desk(ctx, **bad))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(RT._dukaan_desk(cust, action="margin", items=[{"name": "x", "cost": 1, "selling": 2}]))
    assert asyncio.run(RT._dukaan_desk(cust, action="landed", offers=[{"seller": "A", "price": 1}]))["cheapest"] == "A"       # the buyer's own tools work for the buyer


def test_nothing_is_stored_or_changed_by_the_engines():
    for mod in (shop, online):
        src = inspect.getsource(mod)
        assert "session(" not in src and "open(" not in src and "sqlite" not in src and "requests" not in src and "httpx" not in src, mod.__name__


def test_hub_lists_dukaan_desk_with_its_never_list(env):
    from app.employee import hire as H
    c = H.CATALOG["dukaan_desk"]
    assert c["live"] and c["group"] == "Retail & E-commerce" and c["does"] and c["needs"]
    text = " ".join(c["never"]).lower()
    assert "price" in text and "block or blacklist" in text and "genuine" in text and "file gst" in text
    assert H.hire("t1", "dukaan_desk")["key"] == "dukaan_desk"
    assert "'Retail & E-commerce'" in open(H.__file__.replace("hire.py", "../static/console/employees.js")).read()
