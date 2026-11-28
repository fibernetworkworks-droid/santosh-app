"""F2 of docs/FINANCE_GLOBAL_PLAN.md - Household Money for any country: categories, budget, bills and subscriptions found in her own
statements, the forecast, goals, net worth, retirement, and country help at the level its rules have. The card: 40 households in 6
countries through the real statement readers."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _ws(tenant, cc="GB", size="personal"):
    from app.fin import profile as PR
    pv = PR.preview({"size": size, "countries": [cc], "wants": [], "people": []})
    return PR.apply(tenant, pv["answers"], pv["hash"])["id"]


def _csv(months=6):
    rows = ["Date,Narration,Debit,Credit"]
    for m in range(5, 5 + months):
        rows += [f"2026-{m:02d}-25,SALARY ACME,,3000.00", f"2026-{m:02d}-01,RENT OAKWOOD LETTINGS,900.00,",
                 f"2026-{m:02d}-08,DIRECT DEBIT BRITISH GAS 4411,{60 + m:.2f},", f"2026-{m:02d}-12,CARD PAYMENT TO NETFLIX 22,10.99,",
                 f"2026-{m:02d}-14,CARD PAYMENT TO TESCO STORES 11,{40 + 7 * m:.2f},", f"2026-{m:02d}-20,PAYMENT TO J SMITH,{15 * m:.2f},"]
    return "\n".join(rows) + "\n"


def test_the_card_passes_and_can_fail():
    from app.fin import card_f2 as C
    from app.fin.desks import household as H
    r = C.run()
    assert r["ok"] and r["households"] == 40 and len(r["countries"]) == 6, [x for x in r["rows"] if not x["ok"]][:3]
    real = H.recurring
    try:
        H.recurring = lambda rows, cur, rules=None: {**real(rows, cur, rules), "found": real(rows, cur, rules)["found"][1:]}
        assert not C.run(10)["ok"]
    finally:
        H.recurring = real


def test_statement_import_then_bills_budget_forecast(env):
    from app.fin import spine as SP
    from app.fin.desks import household as H
    ws = _ws("h1")
    assert SP.import_statement("h1", ws, _csv(), "Current account", "GBP")["added"] == 36
    bills = H.run("h1", "bills", {"workspace": ws})
    kinds = {(f["kind"], f["payee"].split()[0]) for f in bills["found"]}
    assert ("income", "salary") in kinds and ("subscription", "netflix") in kinds
    rent = next(f for f in bills["bills"] if "rent" in f["payee"])
    assert rent["every"] == "monthly" and rent["next_due"] == "2026-11-01"
    assert not any("smith" in f["payee"] for f in bills["found"])          # amounts jump about: not a bill
    assert "Hoola Wallet" in bills["pay"] and "your tap" in bills["pay"]
    b = H.run("h1", "budget", {"workspace": ws, "limits": {"groceries": 50}})
    assert b["months"][-1]["in"] == 3000.0 and b["over_budget"][0]["category"] == "groceries"
    f = H.run("h1", "forecast", {"workspace": ws, "months_ahead": 2, "start_balance": 100})
    assert f["months"][0]["month"] == "2026-11" and f["months"][0]["in"] == 3000.0 and "end_balance" in f["months"][0]


def test_her_rules_win_and_are_kept(env):
    from app.fin import spine as SP
    from app.fin.desks import household as H
    ws = _ws("h2")
    SP.import_statement("h2", ws, _csv(2), "Current", "GBP")
    with pytest.raises(ValueError):
        H.run("h2", "save_rules", {"workspace": ws, "rules": {"j smith": "made_up"}})
    H.run("h2", "save_rules", {"workspace": ws, "rules": {"J Smith": "education"}})
    rows = H.run("h2", "categorise", {"workspace": ws})["rows"]
    assert {r["category"] for r in rows if "SMITH" in r["narration"]} == {"education"}


def test_goal_net_worth_retirement():
    from app.fin.desks import household as H
    g = H.goal({"target": 1200, "by": "2027-12-01", "saved": 0, "today": "2026-12-01"})
    assert g["months"] == 12 and g["per_month"] == 100.0
    n = H.net_worth({"currency": "GBP", "items": [{"name": "Savings", "amount": 1000}, {"name": "Card", "kind": "liability", "amount": 200},
                                                   {"name": "US shares", "amount": 100, "currency": "USD"},
                                                   {"name": "Euro cash", "amount": 50, "currency": "EUR"}],
                     "fx": [{"currency": "USD", "rate": 0.8, "date": "2026-11-20", "source": "Bank of England"}, {"currency": "EUR", "rate": 0.86}]})
    assert n["net_worth"] == 880.0 and n["left_out"] == ["EUR"]
    r = H.retirement({"years": 10, "pot": 0, "monthly": 100, "real_return_pct": 0, "want_monthly": 100}, "GB")
    s = r["scenarios"][0]
    assert s["pot_at_retirement"] == 12000.0 and s["monthly_at_4pct"] == 40.0 and s["gap_monthly"] == 60.0
    assert "not added in" in r["says"] and "not confirmed" in r["state_pension"]


def test_country_help_is_labelled_and_floor_for_others():
    from app.fin.desks import household as H
    f = H.run("t", "forgotten", {"country": "AU"})
    assert any("MoneySmart" in x and "not confirmed" in x for x in f["where_to_look"])
    assert H.run("t", "benefits", {"country": "ZZ"})["checkers"] == []
    assert any("deposit" in s.lower() for s in H.run("t", "life_mode", {"country": "GB", "mode": "renter"})["steps"])
    with pytest.raises(ValueError):
        H.run("t", "life_mode", {"country": "GB", "mode": "astronaut"})
    b = H.run("t", "bereavement", {"country": "GB"})
    assert "Tell Us Once" in " ".join(b["steps"]) and b["she_sends"] and "[name]" in b["letter"]
    w = H.run("t", "will_check", {"country": "DE", "accounts": [{"name": "A", "nominee": True}, {"name": "B"}]})
    assert w["no_nominee_recorded"] == ["B"] and "does not write a will" in w["says"]


def test_tool_owner_only_and_secrets_refused(env):
    from app.agent import tools as T
    from app.agent.tools import Ctx, ToolError
    assert T.FAMILY_OF["household_money"] == "household"
    ctx = Ctx(tenant_id="h3", conversation_id="", actor="owner")
    out = asyncio.run(T.dispatch("household_money", {"action": "goal", "target": 600, "by": "2030-01-01"}, ctx))
    out = out if isinstance(out, dict) else json.loads(out)
    assert out["per_month"] > 0
    for actor in ("customer:x", "staff:y"):
        with pytest.raises(ToolError):
            asyncio.run(T.dispatch("household_money", {"action": "goal", "target": 1, "by": "2030-01-01"},
                                   Ctx(tenant_id="h3", conversation_id="", actor=actor)))
    with pytest.raises(ToolError):
        asyncio.run(T.dispatch("household_money", {"action": "bills", "rows": [], "password": "x"}, ctx))


def test_routes_and_desk(env):
    from app.employee import deskroom as D
    from app.employee import hire as HI
    from app.main import app
    assert '"keys": ["paisa_sahayak", "household_money"]' in open(D.__file__).read()
    spec = D.spec("household_money")
    assert {a["id"] for a in spec["actions"]} >= {"budget", "bills", "forecast", "goal", "retirement"}
    assert '"household_money": {"name": "Household Money", "live": True' in open(HI.__file__).read()
    c = TestClient(app)
    r = c.post("/api/fin/household/goal", json={"target": 300, "by": "2030-01-01"})
    assert r.status_code == 200 and r.json()["per_month"] > 0
    assert c.post("/api/fin/household/bills", json={}).status_code == 400
    assert c.post("/api/fin/household/transfer", json={}).status_code == 403
