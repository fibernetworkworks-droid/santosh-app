"""F4 of docs/FINANCE_GLOBAL_PLAN.md - Tax worldwide: VAT / GST returns from her books in her country's layout, US sales tax per state,
cross-border consumer sales, withholding, e-invoice files, the personal organiser, quarterly figures, tax letters and the calendar.
The card: returns for 6 countries computed from fixed books match hand-computed answers to the cent."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _ws(tenant, cc="GB", cur="GBP"):
    from app.fin import profile as PR
    a = {**PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})["answers"], "currency": cur}
    return PR.apply(tenant, a, PR.preview(a)["hash"])["id"]


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f4 as C
    from app.fin.desks import tax as T
    r = C.run(12)
    assert r["ok"] and len(r["countries"]) == 6, [x for x in r["rows"] if not x["ok"]][:3]
    real = T._docs
    try:   # a draft or an invoice from another quarter getting in must fail the card
        T._docs = lambda tenant, ws, since, upto: real(tenant, ws, "0001-01-01", "9999-12-31")
        assert not C.run(6)["ok"]
    finally:
        T._docs = real


def test_gb_return_by_hand_and_rates_never_guessed(env):
    from app.fin.desks import books as B
    from app.fin.desks import tax as T
    ws = _ws("t1")
    B.run("t1", "bill", {"workspace": ws, "party": "US Cloud", "issue": "2026-07-05", "issue_now": True,
                         "lines": [{"price": 100, "tax_code": "rc_in"}]})
    with pytest.raises(T.TaxError) as e:
        T.run("t1", "return", {"workspace": ws, "period": "2026-Q3"})
    assert "not confirmed" in str(e.value) and "settings" in str(e.value)
    T.run("t1", "settings", {"workspace": ws, "country": "GB", "rates": {"std": 20, "reduced": 5}})
    B.run("t1", "invoice", {"workspace": ws, "party": "A", "issue": "2026-08-01", "issue_now": True,
                            "lines": [{"price": 1000.55, "tax_pct": 20}, {"price": 200, "tax_pct": 5, "tax_code": "reduced"},
                                      {"price": 50, "tax_code": "zero"}]})
    B.run("t1", "bill", {"workspace": ws, "party": "Office", "issue": "2026-08-03", "issue_now": True, "lines": [{"price": 300, "tax_pct": 20}]})
    B.run("t1", "invoice", {"workspace": ws, "party": "Draft", "issue": "2026-08-04", "lines": [{"price": 999, "tax_pct": 20}]})
    r = T.run("t1", "return", {"workspace": ws, "period": "2026-Q3"})
    b = {x["box"]: x["amount"] for x in r["boxes"]}
    assert b["1"] == 200.11 + 10 + 20 and b["4"] == 60 + 20 and b["5"] == 230.11 - 80
    assert b["6"] == 1350 and b["7"] == 400 and r["to_pay"] == 150.11       # 1250.55 + 100 reverse charge: pence dropped
    assert len(r["documents"]) == 3 and "not confirmed" in r["layout"] and "does not file" in r["says"]
    assert any("standard 20" in x for x in r["rates_used"])


def test_india_heads_and_wrong_rate(env):
    from app.fin.desks import books as B
    from app.fin.desks import tax as T
    ws = _ws("t2", "IN", "INR")
    T.run("t2", "settings", {"workspace": ws, "country": "IN", "rates": {"std": 18}})
    B.run("t2", "invoice", {"workspace": ws, "party": "Pune", "issue": "2026-08-01", "issue_now": True, "supply": {"state": "MH"},
                            "lines": [{"price": 1000, "tax_pct": 18}]})
    with pytest.raises(T.TaxError):
        T.run("t2", "return", {"workspace": ws, "period": "2026-08"})        # no home state
    T.run("t2", "settings", {"workspace": ws, "home_state": "MH"})
    B.run("t2", "invoice", {"workspace": ws, "party": "Bengaluru", "issue": "2026-08-02", "issue_now": True, "supply": {"state": "KA"},
                            "lines": [{"price": 100, "tax_pct": 12}]})
    r = T.run("t2", "return", {"workspace": ws, "period": "2026-08"})
    e = r["exact"]
    assert (e["3.1a_cgst"], e["3.1a_sgst"], e["3.1a_igst"]) == (90.0, 90.0, 12.0)
    assert len(r["warnings"]) == 1 and "12.0%" in r["warnings"][0]


def test_sales_tax_oss_withholding_einvoice(env):
    from app.fin.desks import books as B
    from app.fin.desks import tax as T
    ws = _ws("t3", "US", "USD")
    T.run("t3", "settings", {"workspace": ws, "state_rates": {"CA": 7.25}})
    B.run("t3", "invoice", {"workspace": ws, "party": "LA", "issue": "2026-08-01", "issue_now": True, "supply": {"state": "CA"},
                            "lines": [{"price": 200, "tax_pct": 7.25}, {"price": 50, "tax_code": "exempt"}]})
    B.run("t3", "invoice", {"workspace": ws, "party": "NYC", "issue": "2026-08-01", "issue_now": True, "supply": {"state": "NY"},
                            "lines": [{"price": 100, "tax_pct": 8}]})
    s = {x["state"]: x for x in T.run("t3", "sales_tax", {"workspace": ws, "period": "2026-08"})["states"]}
    assert s["CA"]["due"] == 14.5 and s["CA"]["taxable"] == 200 and s["CA"]["exempt"] == 50
    assert s["NY"]["due"] is None and "does not guess" in s["NY"]["says"]
    with pytest.raises(T.TaxError):
        T.run("t3", "return", {"workspace": ws, "period": "2026-08"})        # the US has no VAT
    w = T.run("t3", "withholding", {"currency": "USD", "payments": [{"payee": "X", "gross": 1234.56, "rate_pct": 30, "rate_source": "treaty"}]})
    assert w["payments"][0]["withheld"] == 370.37 and w["certificates_missing"] == ["X"]
    with pytest.raises(T.TaxError):
        T.run("t3", "withholding", {"payments": [{"payee": "X", "gross": 1, "rate_pct": 30}]})   # no source
    doc = B.docs("t3", ws, "sales")[0]
    e = T.run("t3", "einvoice", {"workspace": ws, "doc": doc["id"]})
    assert "<cbc:PayableAmount currencyID=\"USD\">264.50</cbc:PayableAmount>" in e["xml"] and not e["ok"]
    T.run("t3", "settings", {"workspace": ws, "seller": {"name": "Me Inc", "tax_id": "12-3456789", "country": "US"}})
    assert T.run("t3", "einvoice", {"workspace": ws, "doc": doc["id"]})["ok"]
    wd = _ws("t4", "DE", "EUR")
    T.run("t4", "settings", {"workspace": wd, "oss_rates": {"FR": 20}})
    B.run("t4", "invoice", {"workspace": wd, "party": "Paris", "issue": "2026-08-01", "issue_now": True, "supply": {"country": "FR"},
                            "lines": [{"price": 100, "tax_pct": 20, "tax_code": "oss"}]})
    o = T.run("t4", "oss", {"workspace": wd, "period": "2026-Q3"})
    assert o["countries"][0]["tax_due"] == 20.0 and o["warnings"] == []


def test_organiser_quarterly_notice_calendar(env):
    from app.fin import spine as SP
    from app.fin.desks import books as B
    from app.fin.desks import tax as T
    ws = _ws("t5")
    T.run("t5", "settings", {"workspace": ws, "country": "GB", "period_kind": "quarterly", "due_offset_days": 37})
    SP.import_statement("t5", ws, "Date,Narration,Debit,Credit\n2026-05-25,SALARY ACME,,3000.00\n2026-06-01,INTEREST PAID,,12.50\n"
                        "2026-06-03,CHARITY DONATION,20.00,\n2026-06-04,TESCO,40.00,\n", "Current", "GBP")
    o = T.run("t5", "organiser", {"workspace": ws, "year": 2026, "since": "2026-04-06", "upto": "2027-04-05",
                                  "bands": [{"upto": 10000, "pct": 10}, {"upto": None, "pct": 20}], "allowance": 0})
    assert o["income"] == {"employment": 3000.0, "interest": 12.5} and o["costs_that_may_matter"] == {"donations": 20.0}
    assert o["estimate"]["tax"] == 301.25 and "YOU gave" in o["estimate"]["says"]
    B.run("t5", "invoice", {"workspace": ws, "party": "Client", "issue": "2026-08-01", "issue_now": True, "lines": [{"price": 500}]})
    q = T.run("t5", "quarterly", {"workspace": ws, "period": "2026-Q3"})
    assert q["quarter"]["profit"] == 500.0 and q["year_to_date"]["income"]
    n = T.run("t5", "notice", {"workspace": ws, "text": "HM Revenue & Customs. HMRC reference: AB123456C. Penalty notice. You owe £100.00. "
                                                        "Please pay or appeal by 15 March 2027."})
    assert n["authority"] == "HMRC" and n["reply_by"] == "2027-03-15" and n["amount"] == "100.00" and "a penalty" in n["what_it_is"]
    cal = T.run("t5", "calendar", {"workspace": ws, "year": 2026})
    assert any(x.get("due") == "2026-11-06" for x in cal["items"])
    assert T.run("t5", "calendar", {"workspace": ws, "year": 2027})["items"][0]["due"].startswith("2027")
    with pytest.raises(PermissionError):
        T.run("t5", "file", {"workspace": ws})


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["tax_worldwide"] == "taxwide"
    assert '"tax_worldwide": {"name": "Tax Worldwide", "live": True' in open(HI.__file__).read()
    ctx = Ctx(tenant_id="t6", conversation_id="", actor="owner")
    out = asyncio.run(TL.dispatch("tax_worldwide", {"action": "codes"}, ctx))
    out = out if isinstance(out, dict) else json.loads(out)
    assert "rc_in" in out["codes"]
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("tax_worldwide", {"action": "codes"}, Ctx(tenant_id="t6", conversation_id="", actor="customer:x")))
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("tax_worldwide", {"action": "withholding", "payments": [], "password": "x"}, ctx))
    c = TestClient(app)
    assert c.post("/api/fin/tax/codes", json={}).status_code == 200
    assert c.post("/api/fin/tax/return", json={}).status_code == 400
    assert c.post("/api/fin/tax/file", json={}).status_code == 403
