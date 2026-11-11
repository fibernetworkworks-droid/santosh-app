"""Retail & e-commerce Waves 2 + 3 (retail_growth, retail_trust). Proposals and rule hits only: HER floors / thresholds, a named decider, nothing stored, sent, banned or changed."""
import asyncio
import inspect

import pytest

from app.retailgrowth import engines as G
from app.retailtrust import engines as T
from tests.test_life import conv_ctx


def test_growth_markdown_price_rule_and_loyalty_respect_her_limits():
    m = G.markdown([{"name": "milk", "stock": 10, "cost": 20, "price": 30, "mrp": 35, "expiry": "2026-11-08", "floor_margin_pct": 5},
                    {"name": "bread", "stock": 4, "cost": 10, "price": 20, "mrp": 22, "expiry": "2026-11-20", "floor_margin_pct": 0}], "2026-11-05")
    a = {r["name"]: r for r in m["items"]}
    assert a["milk"]["proposed_price"] == 21.0 and "floor" in a["milk"]["note"] and a["milk"]["waste_risk_at_cost"] == 200.0 and a["bread"]["discount_pct"] == 0
    p = G.price_rule([{"name": "x", "cost": 80, "price": 100, "mrp": 120, "competitor_prices": [70, 95], "floor_margin_pct": 10, "target": "match_lowest"},
                      {"name": "y", "cost": 10, "price": 50, "mrp": 55, "competitor_prices": [90], "floor_margin_pct": 0, "target": "median"}])["items"]
    assert p[0]["proposed"] == 88.0 and p[0]["needs_second_look"] and p[1]["proposed"] == 55.0          # floor held, MRP held
    l = G.loyalty([{"id": 1, "last_visit": "2026-08-01", "spend": 900, "opted_in": True, "birthday": "11-08"},
                   {"id": 2, "last_visit": "2026-08-01", "spend": 5000, "opted_in": False}], "2026-11-05")
    assert l["opted_in"] == 1 and l["left_out_no_consent"] == 1 and [x["id"] for x in l["lapsed"]] == [1] and l["birthdays_this_week"][0]["id"] == 1
    for bad in (lambda: G.loyalty([]), lambda: G.markdown([]), lambda: G.price_rule([])):
        with pytest.raises(ValueError):
            bad()


def test_growth_numbers():
    u = G.unit_economics(200, 100, 1000, 60, 50, 10, 100, 2)
    assert u["contribution_per_order"] == 340.0 and u["ltv_to_cac"] == 3.4
    assert G.unit_economics(10, 1, 100, 100, 20)["loss_per_order"]
    c = G.abc([{"sku": "a", "sales": 80, "margin": 20}, {"sku": "b", "sales": 15, "margin": 10}, {"sku": "c", "sales": 5, "margin": 2}])
    assert c["counts"] == {"A": 1, "B": 1, "C": 1} and c["range_review_candidates"] == ["c"]
    s = G.scheme({"min_qty": 10, "per_unit": 2, "cap": 100}, [{"retailer": "r", "qty": 20, "value": 500}, {"retailer": "q", "qty": 3, "value": 50}], [{"retailer": "r", "amount": 50}])
    r = {x["retailer"]: x for x in s["retailers"]}
    assert r["r"]["accrual"] == 40 and r["r"]["status"] == "dispute" and r["q"]["accrual"] == 0 and "finance" in s["decider"]
    cr = G.credit_exposure([{"retailer": "A", "outstanding": 150, "limit": 100, "oldest_days": 45, "avg_monthly_purchase": 100}])["retailers"][0]
    assert cr["suggested_limit"] == 150.0 and set(cr["flags"]) >= {"over the limit"} and "caste" in G.credit_exposure([{"retailer": "A"}])["basis"]
    b = G.beat_route({"lat": 0, "lng": 0}, [{"name": "far", "lat": 0, "lng": 2}, {"name": "near", "lat": 0, "lng": 1}])
    assert [x["name"] for x in b["order"]] == ["near", "far"] and abs(b["straight_line_km"] - 222.4) < 1
    w = G.working_capital(100, 1000, 50, 1200, 60)
    assert w["inventory_days"] == 36.5 and w["cash_cycle_days"] == 29.8
    d = G.delivery_batches([{"id": 1, "area": "Baner", "amount": 600}, {"id": 2, "area": "Baner", "amount": 500}, {"id": 3, "area": "Kothrud", "amount": 100}], 1000, 40)
    assert d["batches"][0]["area"] == "Baner" and d["batches"][0]["fee_if_one_trip"] == 0 and d["batches"][1]["fee_if_one_trip"] == 40


def test_trust_rule_hits_are_evidence():
    f = T.fraud_flags([{"id": i, "customer": "c", "ts": f"2026-11-05T10:0{i}:00", "amount": 1} for i in range(7)] +
                      [{"id": 20 + k, "customer": f"u{k}", "ts": "2026-11-05T11:00:00", "amount": 9000, "cod": True, "address": "12 Green Park, Pune", "device": "d1"} for k in range(3)], high_value=5000)
    rules = {h["rule"] for h in f["rule_hits"]}
    assert rules == {"order_velocity", "shared_address", "shared_device", "high_value_cod"} and "investigator" in f["decider"] or "risk" in f["decider"]
    ra = T.return_abuse([{"id": "a", "orders": 10, "returns": 6}, {"id": "b", "orders": 10, "returns": 1}, {"id": "c", "orders": 2, "returns": 2}])
    assert [x["customer"] for x in ra["above_threshold"]] == ["a"] and "appeal" in ra["decider"]
    r = T.reviews([{"id": 1, "user": "u", "text": "Great!!", "rating": 5, "date": "2026-11-01", "verified": False}, {"id": 2, "user": "v", "text": "great", "rating": 5, "date": "2026-11-01"},
                   {"id": 3, "user": "w", "text": "ok", "rating": 4, "date": "2026-11-02", "verified": True, "incentivised": True, "disclosed": False}])
    why = {x["id"]: x["why"] for x in r["flagged"]}
    assert "same text kai reviews mein" in why[1] and "verified buyer nahi" in why[1] and "inaam mila par bataya nahi" in why[3] and "moderator" in r["decider"]
    o = T.override_rate([{"model": "m", "ai_decision": "a", "human_decision": "a"}, {"model": "m", "ai_decision": "a", "human_decision": "b"}], 30)
    assert o["models"][0]["override_pct"] == 50.0 and o["models"][0]["alert"]
    pf = T.price_fairness([{"product": "p", "segment": "ios", "price": 110}, {"product": "p", "segment": "android", "price": 100}, {"product": "q", "segment": "ios", "price": 5}], 5)
    assert pf["products"][0]["review"] and not pf["products"][1]["review"]
    pa = T.promise_audit([{"id": i, "promised_days": 3, "actual_days": a} for i, a in enumerate([3, 3, 4, 5, 3, 3, 3, 3, 3, 6])])
    assert pa["on_time_pct"] == 70.0 and pa["p90_error_days"] == 3 and "wada" in pa["honest_promise_hint"]
    for bad in (lambda: T.fraud_flags([]), lambda: T.reviews([]), lambda: T.seller_kyc({}), lambda: T.fraud_flags([{"customer": "a", "ts": "garbage"}])):
        with pytest.raises(ValueError):
            bad()


def test_trust_compliance_checks():
    assert T._gstin_ok("27AAPFU0939F1ZV") == (True, "ok") and T._gstin_ok("27AAPFU0939F1ZA")[0] is False and T._gstin_ok("short")[0] is False
    k = T.seller_kyc({"name": "A Co", "gstin": "27AAPFU0939F1ZV", "pan": "AAPFU0939F", "bank_account_name": "A Co", "bank_ifsc": "HDFC0001234", "address": "x", "category": "c"})
    assert k["failed"] == [] and k["missing_documents"] == []
    bad = T.seller_kyc({"name": "A Co", "gstin": "27AAPFU0939F1ZV", "pan": "ZZZZZ9999Z", "bank_ifsc": "BAD"})
    assert "PAN GSTIN mein" in bad["failed"] and "IFSC format" in bad["failed"] and "bank_account_name" in bad["missing_documents"] and "trust team" in bad["decider"]
    lb = T.label_check({"name": "Soap", "mrp": "Rs 40"})
    assert "net maatra" in lb["missing"] and lb["verify"] and len(lb["present"]) == 2
    dp = T.dark_patterns("Only 3 left! Hurry. No thanks, I don't want savings. Offer ends soon", {"timer_is_real": False})
    assert {h["pattern"].split(" ")[0] for h in dp["text_hits"]} >= {"urgency", "confirm-shaming", "timer"} and dp["checklist_failed"]
    g = T.grievance_clock([{"id": 1, "received": "2026-10-01", "acknowledged": "2026-10-01T10:00:00", "resolved": "2026-10-10"}, {"id": 2, "received": "2026-10-01"}], "2026-11-05")
    assert [c["issues"] for c in g["complaints"]][0] == [] and "resolution deadline nikal gayi" in g["complaints"][1]["issues"] and g["late"] == 1 and g["open"] == 1


def test_tools_registered_guarded_and_routed():
    from app import voice
    from app.agent import retailgrowth_tools as RG
    from app.agent import retailtrust_tools as RT
    from app.agent import tools
    from app.agent.tools import ToolError
    for name, fam in (("retail_growth", "retailgrowth"), ("retail_trust", "retailtrust")):
        assert name in tools.HANDLERS and tools.FAMILY_OF[name] == fam and voice.call_route(name) == "kaam"
    ctx = conv_ctx()
    assert asyncio.run(RG._retail_growth(ctx, action="working_capital", inventory=100, cogs_annual=1000, receivables=50, sales_annual=1200, payables=60))["cash_cycle_days"] == 29.8
    assert asyncio.run(RT._retail_trust(ctx, action="label_check", label={"name": "x"}))["missing"]
    for fn, bad in ((RG._retail_growth, dict(action="nope")), (RG._retail_growth, dict(action="abc")), (RT._retail_trust, dict(action="seller_kyc")), (RT._retail_trust, dict(action="x"))):
        with pytest.raises(ToolError):
            asyncio.run(fn(ctx, **bad))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    for fn, act in ((RG._retail_growth, "abc"), (RT._retail_trust, "label_check")):
        with pytest.raises(ToolError):
            asyncio.run(fn(cust, action=act))


def test_no_storage_no_network_no_scraping_in_the_engines():
    for mod in (G, T):
        src = inspect.getsource(mod)
        assert "session(" not in src and "open(" not in src and "sqlite" not in src and "requests" not in src and "httpx" not in src, mod.__name__


def test_hub_lists_both_with_their_never_lists(env):
    from app.employee import hire as H
    g, t = H.CATALOG["retail_growth"], H.CATALOG["retail_trust"]
    assert g["live"] and t["live"] and g["group"] == t["group"] == "Retail & E-commerce"
    gt, tt = " ".join(g["never"]).lower(), " ".join(t["never"]).lower()
    assert "scrape" in gt and "price" in gt and "ban, block, refund, fine or remove" in tt and "takedown" in tt
    assert H.hire("t1", "retail_growth")["key"] == "retail_growth" and H.hire("t1", "retail_trust")["key"] == "retail_trust"
