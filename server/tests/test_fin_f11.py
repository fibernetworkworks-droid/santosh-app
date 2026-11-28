"""F11 of docs/FINANCE_GLOBAL_PLAN.md - Community & Inclusive, Islamic, Digital Assets. The card: savings-group books in 4 countries
balance; zakat calculations match the fixed set (a scholar's review is still to come); crypto gains match."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f11 as C
    from app.fin.desks import digital as DG
    r = C.run(3)
    assert r["ok"], [x for x in r["rows"] if not x["ok"]][:2]
    assert r["scholar_reviewed"] is False                         # said plainly until a named scholar signs the set off
    real = DG.CRYPTO["IN"]["no_loss_offset"]
    try:      # India's crypto losses set off against gains must fail the card
        DG.CRYPTO["IN"]["no_loss_offset"] = False
        assert not C.run(1)["ok"]
    finally:
        DG.CRYPTO["IN"]["no_loss_offset"] = real


def test_cashbook_and_group(env):
    from app.fin.desks import community as CM
    cb = CM.run("c1", "cashbook", {"opening": 100, "text": "2026-09-01\nsold tea 250\npaid rent 200\nbought milk and sugar 80 120\nhello"})
    assert cb["closing"] == 150.0 and cb["could_not_read"] == ["bought milk and sugar 80 120", "hello"]
    g = CM.run("c1", "group", {"country": "KE", "members": ["A", "B"], "share_value": 100, "share_out": True, "meetings": [
        {"savings": {"A": 3, "B": 1}, "loans": [{"member": "B", "amount": 200, "rate_pct": 10, "months": 1}], "counted": 150},
        {"repayments": [{"member": "B", "amount": 220}]}]})
    assert g["balanced"] and g["count_mismatches"][0]["difference"] == -50.0 and "VSLA" in g["style"]
    assert g["share_out"]["per_member"] == {"A": 315.0, "B": 105.0}
    owe = CM.run("c1", "group", {"members": ["A", "B"], "share_out": True, "meetings": [
        {"savings": {"A": 500}, "loans": [{"member": "B", "amount": 100, "rate_pct": 5}]}]})
    assert owe["share_out"]["possible"] is False and owe["owes"] == {"B": 105.0}
    with pytest.raises(CM.CommunityError):
        CM.run("c1", "group", {"members": ["A"], "meetings": [{"savings": {"Z": 1}}]})


def test_rosca_mfi_farm_remit(env):
    from app.fin.desks import community as CM
    r = CM.run("c2", "rosca", {"members": ["a", "b", "c", "d"], "contribution": 100, "bids": [60, 40, 20, 4], "organiser_fee_pct": 1,
                               "written_record": False})
    assert r["members"]["a"]["role"].startswith("borrows") and r["members"]["d"]["gain"] == 23.0 and r["flags"]
    m = CM.run("c2", "mfi", {"amount": 10000, "installment": 230, "installments": 50, "frequency": "weekly", "upfront_fees": 200,
                             "loans": [{"lender": "x", "installment": 230, "frequency": "weekly"}, {"lender": "y", "installment": 2000},
                                       {"lender": "z", "installment": 1000}], "income_monthly": 6000})
    assert m["loan"]["yearly_rate_pct"] > 30 and m["repayments"]["over_your_limit"] and "flag" in m["repayments"]
    f = CM.run("c2", "farmer", {"threshold_yield": 20, "actual_yield": 15, "sum_insured": 40000})
    assert f["claim"]["claim"] == 10000.0 and "check this" in f["claim"]["formula"]
    rm = CM.run("c2", "remit", {"send": 1000, "mid_rate": 90, "providers": [{"name": "A", "fee": 10, "rate": 89}, {"name": "B", "fee": 0, "rate": 87}]})
    assert rm["most_arrives_with"] == "A" and rm["providers"][0]["arrives"] == 88110.0
    mm = CM.run("c2", "mobile_money", {"amount": 500, "tariff": [{"min": 1, "max": 1000, "fee": 11}], "message": "I sent you money by mistake, reverse it"})
    assert mm["fee"]["fee"] == 11.0 and len(mm["scam_signs"]) >= 2


def test_zakat_and_islamic(env):
    from app.fin import laws as L
    from app.fin.desks import community as CM
    with pytest.raises(CM.CommunityError):
        CM.run("c3", "zakat", {"cash": 1000})                                  # the nisab basis is hers
    z = CM.run("c3", "zakat", {"nisab_basis": "silver", "silver_price_per_gram": 1, "gold_price_per_gram": 80, "cash": 1000})
    assert z["zakat"] == 25.0 and "lunar_year_passed" in z["note"] and "scholar" in z["says"]
    mu = CM.run("c3", "islamic", {"structure": "murabaha", "cost": 10000, "markup_pct": 12, "installments": 12})
    assert mu["sale_price"] == 11200.0 and "Shariah board" in mu["board"]
    dm = CM.run("c3", "islamic", {"structure": "diminishing_musharaka", "price": 1000, "own_contribution": 200, "rent_pct_per_period": 1,
                                  "buyback_per_period": 100})
    assert dm["periods"] == 8 and dm["schedule"][0]["rent"] == 8.0
    md = CM.run("c3", "islamic", {"structure": "mudaraba", "profit": -500, "manager_share_pct": 40})
    assert md["capital_provider"] == -500.0 and md["manager"] == 0.0
    for w in ("issue_fatwa", "send_money", "disburse"):
        with pytest.raises(L.Refused):
            CM.run("c3", w, {})


def test_digital(env):
    from app.fin import laws as L
    from app.fin.desks import digital as DG
    w = DG.run("d1", "wallet", {"address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "chain": "bitcoin",
                                "message": "Support here on Telegram: share your 12-word recovery phrase to validate your wallet"})
    assert w["address"]["valid_shape"] and len(w["signs"]) >= 2
    with pytest.raises(DG.DigitalError):
        DG.run("d1", "wallet", {"address": "x", "chain": "bitcoin", "seed_phrase": "a b c"})
    r = DG.run("d1", "reserve", {"supply": 1000, "eligible": ["cash", "tbill"], "assets": [{"type": "cash", "value": 600, "held_at": "Bank A"},
                                 {"type": "tbill", "value": 300, "held_at": "Bank B"}, {"type": "corporate_bond", "value": 200, "held_at": "Bank A"}]})
    assert r["coverage_pct"] == 90.0 and r["shortfall"] == 100.0 and r["not_eligible"][0]["type"] == "corporate_bond"
    c = DG.run("d1", "custody", {"ledger": [{"client": "a", "asset": "BTC", "qty": 1.5}, {"client": "b", "asset": "BTC", "qty": 1}],
                                 "wallets": [{"asset": "BTC", "balance": 2.4}]})
    assert c["short"] == ["BTC"]
    t = DG.run("d1", "travel_rule", {"threshold": 1000, "transfers": [{"id": "t1", "value": 5000, "originator_name": "A", "originator_account": "1",
                                                                       "beneficiary_name": "B", "beneficiary_account": "2"}]})
    assert t["held"] == ["t1"] and t["transfers"][0]["missing"] == ["originator_address_or_id"]
    s = DG.run("d1", "surveillance", {"linked": [["u1", "u2"]], "trades": [
        {"id": 1, "time": "2026-09-01T10:00", "asset": "X", "qty": 5, "buyer": "u1", "seller": "u2"},
        {"id": 2, "time": "2026-09-01T10:05", "asset": "X", "qty": 5, "buyer": "u3", "seller": "u4"},
        {"id": 3, "time": "2026-09-01T10:10", "asset": "X", "qty": 5, "buyer": "u4", "seller": "u3"}]})
    assert s["self_trades"] == [1] and s["round_trips"] == [[2, 3]]
    for w in ("sign_transaction", "send", "withdraw", "buy"):
        with pytest.raises(L.Refused):
            DG.run("d1", w, {})


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["community_finance"] == "commfin" and TL.FAMILY_OF["digital_assets"] == "digiasset"
    assert "community_finance" in HI.CATALOG and "digital_assets" in HI.CATALOG
    out = asyncio.run(TL.dispatch("community_finance", {"action": "styles"}, Ctx(tenant_id="e1", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert "KE" in out["styles"]
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("digital_assets", {"action": "methods"}, Ctx(tenant_id="e1", conversation_id="", actor="customer:x")))
    c = TestClient(app)
    assert c.post("/api/fin/digital/methods", json={}).status_code == 200
    assert c.post("/api/fin/community/zakat", json={}).status_code == 400
    for p in ("/api/fin/digital/sign_transaction", "/api/fin/community/disburse"):
        assert c.post(p, json={}).status_code == 403, p
