"""F10 of docs/FINANCE_GLOBAL_PLAN.md - Investments & Markets. The card: tax lots for 6 countries' methods; reconciliation breaks
found on fixed files; no order ever placed."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f10 as C
    from app.fin.desks import investments as IV
    r = C.run(3)
    assert r["ok"] and r["countries"] == ["AU", "CA", "DE", "GB", "IN", "US"], [x for x in r["rows"] if not x["ok"]][:2]
    real = IV.METHODS["US"]["wash_days"]
    try:      # a US method with no wash-sale rule must fail the card
        IV.METHODS["US"]["wash_days"] = 0
        assert not C.run(1)["ok"]
    finally:
        IV.METHODS["US"]["wash_days"] = real


def test_lots_by_country(env):
    from app.fin.desks import investments as IV
    t = [{"date": "2025-03-01", "side": "buy", "qty": 100, "price": 50, "symbol": "INFY"},
         {"date": "2026-03-02", "side": "sell", "qty": 60, "price": 70, "symbol": "INFY"}]
    r = IV.run("v1", "lots", {"country": "IN", "trades": t})
    assert r["net"] == 1200.0 and r["by_term"] == {"long": 1200.0} and "check this" in r["method_from"] and "not worked out" in r["tax"]
    assert IV.run("v1", "lots", {"method": "fifo", "trades": t})["method_from"] == "your method"
    with pytest.raises(IV.InvestError):
        IV.run("v1", "lots", {"country": "DE", "trades": [{"date": "2026-01-01", "side": "sell", "qty": 1, "price": 1}]})
    with pytest.raises(IV.InvestError):
        IV.run("v1", "lots", {"country": "ZZ", "trades": t})


def test_investment_checks(env):
    from app.fin.desks import investments as IV
    with pytest.raises(IV.InvestError):
        IV.run("v2", "fees", {"amount": 10000, "years": 20})                    # never assumes a return
    f = IV.run("v2", "fees", {"amount": 10000, "years": 20, "return_pct": 6, "fee_pct": 1.5})
    assert f["fees_cost"] > 0 and f["end_with_fees"] < f["end_without_fees"]
    s = IV.run("v2", "scam", {"text": "Guaranteed 10% per month, risk-free, today only! Join our WhatsApp group.",
                              "firm": "Quick Gains Ltd", "register": [{"name": "Real Bank plc"}], "country": "GB"})
    assert s["level"] == "high" and s["on_your_register"] is False and "FCA" in s["check_on"]
    d = IV.run("v2", "derivatives", {"positions": [{"type": "call", "side": "long", "strike": 100, "premium": 5, "qty": 1, "multiplier": 100},
                                                   {"type": "call", "side": "short", "strike": 100, "premium": 5},
                                                   {"type": "future", "price": 20000, "qty": 1, "multiplier": 50, "margin": 100000}]})
    assert d["positions"][0]["most_you_can_lose"] == -500.0 and d["positions"][0]["break_even"] == 105.0
    assert d["positions"][1]["most_you_can_lose"] == "unlimited" and d["positions"][2]["leverage"] == 10.0
    h = IV.run("v2", "harvest", {"country": "US", "today": "2026-09-10", "holdings": [{"symbol": "A", "qty": 10, "price": 5, "cost": 100}],
                                 "recent_buys": [{"symbol": "A", "date": "2026-09-01"}]})
    assert h["losses"][0]["unrealised_loss"] == -50.0 and "2026-09-01" in h["losses"][0]["warning"]
    rt = IV.run("v2", "retirement", {"pot": 100000, "withdraw": 20000, "return_pct": 0, "inflation_pct": 0})
    assert rt["runs_out_in_year"] == 5
    n = IV.run("v2", "nav_check", {"assets": [{"value": 1010000}], "liabilities": [{"value": 10000}], "units": 100000, "reported_nav": 10.02})
    assert n["nav_per_unit"] == 10.0 and n["break"] is True
    st = IV.run("v2", "statement", {"holdings": [{"symbol": "A", "qty": 10, "price": 80}, {"symbol": "B", "qty": 10, "price": 20}], "max_pct": 50})
    assert st["over_your_limit"] == ["A"]


def test_markets_parts(env):
    from app.fin.desks import markets as MK
    ca = MK.run("m1", "corp_action", {"event": {"type": "split", "symbol": "X", "ratio": "3:2", "record_date": "2026-09-01",
                                                "cash_in_lieu_price": 10}, "positions": [{"account": "A", "symbol": "X", "qty": 101}]})
    assert ca["entitlements"][0]["after"] == 151.0 and ca["entitlements"][0]["cash_in_lieu"] == 5.0
    dv = MK.run("m1", "corp_action", {"event": {"type": "cash_dividend", "symbol": "X", "rate": 0.5, "withholding_pct": 15,
                                                "record_date": "2026-09-01"}, "positions": [{"account": "A", "symbol": "X", "qty": 200}]})
    assert dv["entitlements"][0]["net"] == 85.0
    rc = MK.run("m1", "reclaim", {"today": "2026-09-01", "treaty": {"DE": 15}, "claim_years": {"DE": 4},
                                  "dividends": [{"date": "2021-05-01", "country": "DE", "gross": 1000, "withheld": 263.75},
                                                {"date": "2025-05-01", "country": "DE", "gross": 1000, "withheld": 263.75},
                                                {"date": "2025-05-01", "country": "FR", "gross": 1000, "withheld": 250}]})
    assert rc["reclaimable"] == 113.75 and rc["expired"] == 113.75 and rc["no_treaty_rate_given_for"] == ["FR"]
    mg = MK.run("m1", "margin", {"requirement": 100000, "collateral": [{"symbol": "GILT", "value": 80000}], "haircuts": {"GILT": 5}})
    assert mg["shortfall"] == 24000.0 and "24,000.00" in mg["notice"]
    with pytest.raises(MK.MarketsError):
        MK.run("m1", "margin", {"requirement": 1, "collateral": [{"symbol": "Z", "value": 1}]})          # no haircut of hers: refused
    s = MK.run("m1", "ssi", {"instructions": [{"counterparty": "Bk", "currency": "EUR", "bic": "DEUTDEFF", "account": "1",
                                               "iban": "DE89370400440532013000"},
                                              {"counterparty": "Bk", "currency": "EUR", "bic": "DEUTDEFF", "account": "2"}]})
    assert s["instructions"][0]["ok"] and "call-back" in s["instructions"][1]["problems"][0]
    cp = MK.run("m1", "comps", {"peers": [{"name": "a", "ev": 100, "ebitda": 10}, {"name": "b", "ev": 120, "ebitda": 10}], "target": {"ebitda": 5}})
    assert cp["multiples"]["ev_ebitda"]["median"] == 11.0 and cp["implied_for_target"]["ev_ebitda"]["median"] == 55.0


def test_no_order_anywhere(env):
    from app.fin import laws as L
    from app.fin.desks import investments as IV, markets as MK
    for desk in (IV, MK):
        for w in ("place_order", "buy", "sell", "execute_trade", "cancel_order", "affirm", "allocate"):
            with pytest.raises(L.Refused):
                desk.run("n1", w, {})


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["investments_desk"] == "investdesk" and TL.FAMILY_OF["markets_desk"] == "mktdesk"
    assert "investments_desk" in HI.CATALOG and "markets_desk" in HI.CATALOG
    out = asyncio.run(TL.dispatch("investments_desk", {"action": "methods"}, Ctx(tenant_id="r1", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert set(out["methods"]) == {"GB", "US", "IN", "CA", "AU", "DE"}
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("markets_desk", {"action": "recon"}, Ctx(tenant_id="r1", conversation_id="", actor="customer:x")))
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("markets_desk", {"action": "place_order"}, Ctx(tenant_id="r1", conversation_id="", actor="owner")))
    c = TestClient(app)
    assert c.post("/api/fin/investments/methods", json={}).status_code == 200
    assert c.post("/api/fin/investments/lots", json={}).status_code == 400
    assert c.post("/api/fin/markets/recon", json={"internal": [], "custodian": []}).status_code == 200
    for p in ("/api/fin/investments/place_order", "/api/fin/markets/execute_trade", "/api/fin/markets/affirm"):
        assert c.post(p, json={}).status_code == 403, p
