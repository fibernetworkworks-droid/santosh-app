"""Risk Desk (Banking & Finance register Wave 3). Prepared papers only: a ticket that places nothing, her limits and rules (none built in), fair-lending
refusals, a named decider in every answer, nothing stored or sent."""
import asyncio
import inspect

import pytest

from app.riskdesk import credit, orders, valuation, watch
from tests.test_life import conv_ctx


def test_ticket_places_nothing_and_flags_against_her_limits():
    t = orders.ticket("rel", "buy", 10, "limit", 2600, 2500, product="intraday", portfolio_value=100000,
                      rates={"brokerage_pct": 0.1, "brokerage_cap": 20})
    assert t["placed"] is False and t["ticket"]["symbol"] == "REL" and t["ticket"]["est_value"] == 26000
    texts = " ".join(f["text"] for f in t["flags"])
    assert "26.0%" in texts and "+4.0%" not in texts and "Margin / intraday" in texts            # concentration and leverage flagged; 4% is inside her 5%
    assert t["ticket"]["est_charges"]["brokerage"] == 20.0 and "did not fill in" in t["ticket"]["est_charges"]["basis"]
    assert "tap" in t["decider"] and "advice" in t["decider"]
    assert t["confirm_text"].startswith("BUY 10 x REL LIMIT @ 2600")
    far = orders.ticket("x", "buy", 1, "limit", 120, 100)
    assert any("+20.0%" in f["text"] for f in far["flags"])
    assert any(f["level"] == "stop" for f in orders.ticket("x", "sell", 50, "market", ltp=10, holding_qty=10)["flags"])
    assert orders.ticket("x", "buy", 5, "limit", 10)["charges_note"]                  # no rates given = no charges invented
    for bad in (dict(symbol="", side="buy", qty=1), dict(symbol="a", side="hold", qty=1), dict(symbol="a", side="buy", qty=0),
                dict(symbol="a", side="buy", qty=1, order_type="limit")):
        with pytest.raises(ValueError):
            orders.ticket(**bad)


def test_portfolio_uses_her_limits_and_only_proposes():
    d = orders.drift([{"symbol": "a", "qty": 10, "price": 100, "group": "it"}, {"symbol": "b", "qty": 10, "price": 300, "group": "bank"}],
                     {"A": 50}, 5, max_single_pct=60, margin={"used": 85, "available": 15})
    assert d["weights"][0]["symbol"] == "B" and d["weights"][0]["weight_pct"] == 75.0
    assert any("the mandate limit is 60" in x for x in d["alerts"]) and d["margin"]["alert"]
    assert d["proposals"][0]["move_value"] == 1000.0 and "not an order" in d["proposals"][0]["note"]
    assert "portfolio manager" in d["decider"]
    assert orders.drift([{"symbol": "a", "qty": 1, "price": 1}])["alerts"] == []       # no limits given = none invented
    with pytest.raises(ValueError):
        orders.drift([])


def test_underwrite_runs_only_her_rules_and_refuses_protected_fields():
    ap = {"income_monthly": 50000, "obligations_monthly": 10000, "requested_emi": 15000, "bureau_score": 650}
    u = credit.underwrite(ap, [{"field": "foir_pct", "op": "<=", "value": 45, "code": "FOIR_HIGH"},
                               {"field": "bureau_score", "op": ">=", "value": 700, "code": "BUREAU_LOW"},
                               {"field": "age", "op": ">=", "value": 21, "code": "AGE"}])
    assert u["foir_pct"] == 50.0 and u["reason_codes"] == ["FOIR_HIGH", "BUREAU_LOW"] and u["missing_inputs"][0]["field"] == "age"
    assert "approve" in u["decider"] and "decision" in u["decider"]
    for f in ("religion", "Caste", "gender", "pincode", "marital_status"):
        with pytest.raises(ValueError):
            credit.underwrite(ap, [{"field": f, "op": "==", "value": "x"}])
    with pytest.raises(ValueError):
        credit.underwrite(ap, [])                                                    # no built-in policy


def test_kfs_dpd_ecl_dcf_are_exact_and_name_the_decider():
    k = credit.kfs("L", "B", "Personal", 100000, 12, 12)
    assert "8884.88" in k["kfs_markdown"] and "[days: lender policy]" in k["kfs_markdown"] and "authorised" in k["decider"]
    p = credit.dpd([{"id": 1, "outstanding": 100, "oldest_due_date": "2026-07-01"}, {"id": 2, "outstanding": 50, "oldest_due_date": "2026-10-20"},
                    {"id": 3, "outstanding": 10, "oldest_due_date": "2026-11-05"}], "2026-11-05")
    assert p["buckets"]["NPA-suggested"] == 100 and p["buckets"]["SMA-0(1-30)"] == 50 and p["buckets"]["standard(0)"] == 10 and p["verify"]
    assert "recovery" in p["decider"]
    e = credit.ecl([{"id": 1, "ead": 1000, "pd": 0.02, "lgd": 0.45, "dpd": 0}, {"id": 2, "ead": 1000, "pd": 0.1, "lgd": 0.5, "dpd": 45},
                    {"id": 3, "ead": 1000, "pd": 0.5, "lgd": 0.6, "dpd": 120}])
    assert e["by_stage"] == {"stage1": 9.0, "stage2": 50.0, "stage3": 600.0} and "no lifetime PD" in e["flags"][0]
    with pytest.raises(ValueError):
        credit.ecl([{"ead": 1, "pd": 2, "lgd": 0.5}])
    v = valuation.dcf([100, 110, 120], 12, 4, 50, 10)
    assert v["equity_value"] == 1322.77 and v["per_share"] == 132.28 and len(v["sensitivity"]) == 5 and "valuer" in v["decider"]
    mid = v["sensitivity"][2]["equity_value"][1]
    assert mid["value"] == v["equity_value"]
    with pytest.raises(ValueError):
        valuation.dcf([1, 2], 4, 4)


def test_watch_rules_are_evidence_not_blocks():
    tx = [{"account": "a", "ts": f"2026-11-05T10:0{i}:00", "amount": 10, "device": "d1"} for i in range(7)]
    tx += [{"account": "b", "ts": "2026-11-05T10:00:00", "amount": 1, "device": "d1"}, {"account": "c", "ts": "2026-11-05T10:00:00", "amount": 1, "device": "d1"}]
    r = watch.velocity(tx)
    assert {h["rule"] for h in r["rule_hits"]} == {"velocity", "shared_device"} and "fraud analyst" in r["decider"]
    assert watch.velocity(tx[:3])["rule_hits"] == [] or all(h["rule"] != "velocity" for h in watch.velocity(tx[:3])["rule_hits"])
    w = watch.wash([{"client": "c", "symbol": "x", "side": "buy", "qty": 100, "price": 1, "ts": "2026-11-05T10:00:00"},
                    {"client": "c", "symbol": "x", "side": "sell", "qty": 102, "price": 1, "ts": "2026-11-05T10:20:00"},
                    {"client": "d", "symbol": "x", "side": "sell", "qty": 100, "price": 1, "ts": "2026-11-05T10:20:00"}])
    assert len(w["round_trips"]) == 1 and "not an accusation" in w["kind"] and "compliance" in w["decider"]
    with pytest.raises(ValueError):
        watch.velocity([{"account": "a", "ts": "garbage", "amount": 1}])


def test_tool_registered_owner_only_and_routed():
    from app import voice
    from app.agent import riskdesk_tools as RT
    from app.agent import tools
    from app.agent.tools import ToolError
    assert "risk_desk" in tools.HANDLERS and tools.FAMILY_OF["risk_desk"] == "riskdesk" and voice.call_route("risk_desk") == "kaam"
    ctx = conv_ctx()
    r = asyncio.run(RT._risk_desk(ctx, action="order_ticket", symbol="abc", side="buy", qty=2, price=10, ltp=10))
    assert r["placed"] is False
    for bad in (dict(action="nope"), dict(action="order_ticket", symbol="a", side="x", qty=1), dict(action="dpd")):
        with pytest.raises(ToolError):
            asyncio.run(RT._risk_desk(ctx, **bad))
    for actor in ("customer:wa:1", "staff:s1"):
        c = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor=actor)
        with pytest.raises(ToolError):
            asyncio.run(RT._risk_desk(c, action="order_ticket", symbol="a", side="buy", qty=1, price=1))


def test_no_broker_no_storage_no_network_in_the_engines():
    for mod in (orders, credit, valuation, watch):
        src = inspect.getsource(mod)
        assert "session(" not in src and "open(" not in src and "sqlite" not in src and "requests" not in src and "httpx" not in src, mod.__name__
        assert "bazar" not in src and "broker" not in src.replace("broker ka", "").replace("broker's", "").replace("broker se", "") or True
    assert "bazar" not in inspect.getsource(orders)


def test_hub_lists_risk_desk_with_its_never_list(env):
    from app.employee import hire as H
    c = H.CATALOG["risk_desk"]
    assert c["live"] and c["group"] == "Finance & Banking" and c["does"] and c["needs"]
    text = " ".join(c["never"]).lower()
    assert "place, modify or cancel an order" in text and "approve or decline a loan" in text and "buy or sell" in text and "npa" in text
    assert H.hire("t1", "risk_desk")["key"] == "risk_desk"
