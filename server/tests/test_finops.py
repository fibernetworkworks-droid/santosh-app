"""Vitt Sahayak (Wave 2 of docs/research/banking_finance_industry: goal planner, advance tax, TDS reconcile, ageing, 3-way match, AML triage,
sanctions name screening, credit memo). Pure engines: known numbers, her thresholds / lists / policy only, a named decider in every answer,
nothing stored, sent, filed or paid."""
import asyncio
import inspect

import pytest

from app.finops import aml, credit, goals, ledger, tax
from tests.test_life import conv_ctx


def test_goal_sip_round_trips_and_inflation():
    g = goals.goal(1000000, 10, 0, 6)
    assert g["amount_needed_then"] == round(1000000 * 1.06 ** 10, 2)
    for s in g["scenarios"]:
        assert abs(s["check_fv"] - g["amount_needed_then"]) < 1.0           # the SIP really reaches the target
    sip = {s["scenario"]: s["monthly_sip_needed"] for s in g["scenarios"]}
    assert sip["low"] > sip["mid"] > sip["high"]
    assert "ASSUMED" in g["assumed"] and "adviser" in g["decider"]
    z = goals.goal(120000, 1, 0, 0, {"zero": 0})
    assert [s for s in z["scenarios"] if s["scenario"] == "zero"][0]["monthly_sip_needed"] == 10000.0
    with pytest.raises(ValueError):
        goals.goal("x", 1)


def test_advance_tax_dates_and_amounts():
    r = goals.advance_tax(100000, 2026, 20000)
    assert [i["due"] for i in r["instalments"]] == ["2026-06-15", "2026-09-15", "2026-12-15", "2027-03-15"]
    assert [i["this_instalment"] for i in r["instalments"]] == [12000.0, 24000.0, 24000.0, 20000.0] and r["verify"]


def test_tds_reconcile_names_what_to_ask():
    r = tax.tds_reconcile([{"party": "A", "section": "194c", "tds": "1,000"}, {"party": "B", "section": "194J", "tds": 500}, {"party": "C", "section": "194C", "tds": 90}],
                          [{"party": "A", "section": "194C", "tds": 1000}, {"party": "C", "section": "194C", "tds": 100}, {"party": "D", "section": "194H", "tds": 5}])
    st = {x["party"]: x["status"] for x in r["rows"]}
    assert st == {"a": "match", "b": "not_in_portal", "c": "difference", "d": "not_in_books"} and r["to_check"] == 3 and "CA" in r["decider"]
    with pytest.raises(ValueError):
        tax.tds_reconcile([], [])


def test_ageing_buckets_and_three_way():
    r = ledger.ageing([{"party": "X", "invoice_no": 1, "due_date": "2026-09-01", "amount": 1000, "paid": 100},
                       {"party": "X", "invoice_no": 2, "due_date": "2026-12-01", "amount": 500},
                       {"party": "Y", "invoice_no": 3, "due_date": "2026-10-20", "amount": 200, "paid": 200}], "2026-11-05")
    assert r["buckets"]["61-90"] == 900.0 and r["buckets"]["not_due"] == 500.0 and r["total_outstanding"] == 1400.0 and "Y" not in r["by_party"]
    with pytest.raises(ValueError):
        ledger.ageing([{"party": "X", "due_date": "garbage", "amount": 5}])
    t = ledger.three_way([{"po": "1", "qty": 10, "price": 5}, {"po": "2", "qty": 4, "price": 9}], [{"po": "1", "qty": 8}, {"po": "2", "qty": 4}],
                         [{"invoice_no": "a", "po": "1", "qty": 10, "price": 5}, {"invoice_no": "b", "po": "2", "qty": 4, "price": 9},
                          {"invoice_no": "c", "po": "9", "qty": 1, "price": 1}, {"invoice_no": "d", "po": "2", "qty": 4, "price": 12}])
    assert {x["invoice"]: x["status"] for x in t["results"]} == {"a": "hold", "b": "match", "c": "hold", "d": "hold"}
    assert "payment" in t["decider"].lower()


def test_aml_triage_uses_her_threshold_and_never_files():
    tx = [{"account": "A1", "date": f"d{i}", "amount": 950000, "type": "cash_in", "counterparty": "x"} for i in range(3)]
    tx += [{"account": "A2", "date": "d1", "amount": 20000, "type": "cash_in"}]
    r = aml.triage(tx, cash_threshold=1000000)
    rules = [(a["account"], a["rule"]) for a in r["alerts"]]
    assert ("A1", "structuring_like") in rules and all(a["account"] != "A2" for a in r["alerts"]) and r["clean_accounts"] == 1
    assert all(a["kind"] == "heuristic" and "[analyst" in a["draft_narrative"] for a in r["alerts"])
    assert not aml.triage(tx, cash_threshold=5000000)["alerts"] or all(a["rule"] != "structuring_like" for a in aml.triage(tx, cash_threshold=5000000)["alerts"])
    pt = aml.triage([{"account": "P", "amount": 900000, "type": "credit"}, {"account": "P", "amount": 880000, "type": "debit"}])
    assert [a["rule"] for a in pt["alerts"]] == ["pass_through"] and "MLRO" in pt["decider"]


def test_sanctions_screen_explains_every_score_and_has_no_builtin_list():
    r = aml.screen(["Mohammed Rahim Khan", "Zed Quark"], [{"name": "Rahim Khaan", "list": "L1", "ref": "7"}, {"name": "Qqq Www"}])
    hit = r["results"][0]["possible_matches"][0]
    assert hit["watch_name"] == "Rahim Khaan" and hit["score"] >= 0.7 and any("khan~khaan" in w for w in hit["explained_by"])
    assert r["results"][1]["possible_matches"] == []
    with pytest.raises(ValueError):
        aml.screen(["A"], [])                         # no list of ours to fall back on
    assert "compliance" in r["decider"]


def test_credit_memo_uses_her_policy_and_decides_nothing():
    fin = {"revenue": 1000, "ebitda": 200, "interest": 50, "debt_service": 100, "current_assets": 300, "current_liabilities": 200,
           "total_debt": 400, "net_worth": 500, "net_profit": 80}
    m = credit.memo("Acme", fin, "working capital", 500, [{"revenue": 800, "ebitda": 150, "net_profit": 60}, fin], {"dscr": 2.5, "debt_to_equity": 1.0})
    assert m["ratios"]["dscr"] == 2.0 and m["ratios"]["current_ratio"] == 1.5 and m["ratios"]["interest_cover"] == 4.0
    assert len(m["policy_flags"]) == 1 and "dscr" in m["policy_flags"][0] and "revenue: +25.0%" in m["trend"][0]
    low = m["memo_markdown"].lower()
    assert "[ ]" in m["memo_markdown"] and "committee" in m["decider"] and "approve" not in low.replace("approve / decline", "")
    assert credit.memo("A", fin)["policy_flags"] == []                      # no policy given = no floor invented
    with pytest.raises(ValueError):
        credit.ratios({})


def test_tool_registered_guarded_and_routed():
    from app import voice
    from app.agent import finops_tools as FT
    from app.agent import tools
    from app.agent.tools import ToolError
    assert "vitt_sahayak" in tools.HANDLERS and tools.FAMILY_OF["vitt_sahayak"] == "finops" and voice.call_route("vitt_sahayak") == "kaam"
    ctx = conv_ctx()
    assert asyncio.run(FT._vitt_sahayak(ctx, action="goal", target=1000000, years=10))["scenarios"]
    assert asyncio.run(FT._vitt_sahayak(ctx, action="ratios", financials={"ebitda": 10, "debt_service": 5}))["ratios"]["dscr"] == 2.0
    for bad in (dict(action="nope"), dict(action="goal", target="x", years=1), dict(action="tds_reconcile")):
        with pytest.raises(ToolError):
            asyncio.run(FT._vitt_sahayak(ctx, **bad))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FT._vitt_sahayak(cust, action="goal", target=1, years=1))
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    for act in ("aml_triage", "sanctions", "credit_memo"):
        with pytest.raises(ToolError):
            asyncio.run(FT._vitt_sahayak(staff, action=act, txns=[{"account": "a", "amount": 1}], names=["a"], watch=[{"name": "a"}], financials={"ebitda": 1}))
    assert asyncio.run(FT._vitt_sahayak(staff, action="ageing", invoices=[{"party": "p", "due_date": "2026-01-01", "amount": 5}], as_of="2026-11-01"))["total_outstanding"] == 5


def test_nothing_is_stored_by_the_engines():
    for mod in (goals, tax, ledger, aml, credit):
        src = inspect.getsource(mod)
        assert "session(" not in src and "open(" not in src and "sqlite" not in src and "Base" not in src and "requests" not in src, mod.__name__


def test_hub_lists_vitt_sahayak_with_its_never_list(env):
    from app.employee import hire as H
    c = H.CATALOG["vitt_sahayak"]
    assert c["live"] and c["group"] == "Finance & Banking" and c["does"] and c["needs"]
    text = " ".join(c["never"]).lower()
    assert "str" in text and "approve / decline" in text and "move money" in text and "sanctions match" in text
    assert H.hire("t1", "vitt_sahayak")["key"] == "vitt_sahayak"
