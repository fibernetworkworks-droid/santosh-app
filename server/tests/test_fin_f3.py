"""F3 of docs/FINANCE_GLOBAL_PLAN.md - Books & Accounts for any country: double-entry books, invoices and bills, receipts, cash
application, reconciliation, ageing, fixed assets, inventory cost, foreign currency, the month-end close, reports and exports.
The card: 20 business months in 6 countries."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _ws(tenant, cc="GB", cur="GBP"):
    from app.fin import profile as PR
    a = {**PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})["answers"], "currency": cur}
    return PR.apply(tenant, a, PR.preview(a)["hash"])["id"]


def test_the_card_passes(env):
    from app.fin import card_f3 as C
    r = C.run()
    assert r["ok"] and r["businesses"] == 20 and len(r["countries"]) == 6, [x for x in r["rows"] if not x["ok"]][:3]


def test_journals_balance_and_post_once(env):
    from app.fin.desks import books as B
    ws = _ws("b1")
    B.ensure_coa("b1", ws)
    with pytest.raises(B.BooksError):
        B.run("b1", "journal", {"workspace": ws, "day": "2026-10-01", "lines": [{"code": "6000", "debit": 10}, {"code": "1000", "credit": 9}]})
    with pytest.raises(B.BooksError):
        B.run("b1", "journal", {"workspace": ws, "day": "2026-10-01", "lines": [{"code": "6000", "debit": 1}, {"code": "8888", "credit": 1}]})
    B.post("b1", ws, "2026-10-01", [{"code": "6000", "debit_minor": 5}, {"code": "1000", "credit_minor": 5}], source_ref="x:1")
    with pytest.raises(B.BooksError):
        B.post("b1", ws, "2026-10-01", [{"code": "6000", "debit_minor": 5}, {"code": "1000", "credit_minor": 5}], source_ref="x:1")
    i = B.run("b1", "invoice", {"workspace": ws, "party": "A", "issue": "2026-10-02", "lines": [{"qty": 3, "price": 33.33, "tax_pct": 20}]})
    assert i["status"] == "draft" and i["net"] == 99.99 and i["tax"] == 20.0 and "not confirmed" in i["tax_note"]
    n1 = B.run("b1", "issue", {"workspace": ws, "doc": i["id"]})["number"]
    j = B.run("b1", "invoice", {"workspace": ws, "party": "B", "issue": "2026-10-03", "lines": [{"price": 1}], "issue_now": True})
    assert (n1, j["number"]) == ("INV-2026-0001", "INV-2026-0002")
    with pytest.raises(B.BooksError):
        B.run("b1", "invoice", {"workspace": ws, "party": "C", "currency": "USD", "lines": [{"price": 1}]})   # no dated rate


def test_receipt_inventory_and_reducing_balance(env):
    from app.fin.desks import books as B
    ws = _ws("b2", "DE", "EUR")
    r = B.run("b2", "receipt", {"workspace": ws, "text": "Baumarkt Schmidt GmbH\n12.10.2026\nNetto 50,00\nMwSt 19% 9,50\nTotal 59,50 EUR"})
    assert r["status"] == "draft" and r["read"] == {"seller": "Baumarkt Schmidt GmbH", "date": "2026-10-12", "total": 59.5, "tax": 9.5}
    assert r["total"] == 59.5 and r["tax"] == 9.5
    with pytest.raises(B.BooksError):
        B.run("b2", "receipt", {"workspace": ws, "text": "thank you for shopping"})
    mv = [{"day": "1", "qty": 10, "unit_cost": 2}, {"day": "2", "qty": 10, "unit_cost": 3}, {"day": "3", "qty": -15}]
    assert B.inventory_cost({"movements": mv, "method": "fifo"}) == {"method": "fifo", "cost_of_goods_out": 35.0, "qty_left": 5.0,
                                                                     "value_left": 15.0}
    av = B.inventory_cost({"movements": mv, "method": "average"})
    assert av["cost_of_goods_out"] == 37.5 and av["value_left"] == 12.5
    with pytest.raises(B.BooksError):
        B.inventory_cost({"movements": [{"day": "1", "qty": -1}]})
    B.run("b2", "asset", {"workspace": ws, "name": "Van", "cost": 12000, "start": "2026-10", "method": "reducing", "rate_pct": 24})
    assert B.run("b2", "depreciation", {"workspace": ws, "period": "2026-10"})["amount"] == 240.0
    assert B.run("b2", "depreciation", {"workspace": ws, "period": "2026-11"})["amount"] == 235.2      # 11,760 x 24% / 12
    assert B.run("b2", "depreciation", {"workspace": ws, "period": "2026-11"})["assets"] == []        # once a month


def test_close_lock_needs_her_confirm_of_the_same_checklist(env):
    from app.fin.desks import books as B
    ws = _ws("b3")
    B.run("b3", "invoice", {"workspace": ws, "party": "A", "issue": "2026-09-02", "lines": [{"price": 5}]})    # a draft
    ck = B.run("b3", "close_check", {"workspace": ws, "period": "2026-09"})
    assert not ck["ready"]
    with pytest.raises(B.BooksError):
        B.run("b3", "close_lock", {"workspace": ws, "period": "2026-09", "hash": ck["hash"]})              # not done, no reason
    with pytest.raises(B.BooksError):
        B.run("b3", "close_lock", {"workspace": ws, "period": "2026-09", "hash": "old", "exceptions": "client confirms it later"})
    assert B.run("b3", "close_lock", {"workspace": ws, "period": "2026-09", "hash": ck["hash"],
                                      "exceptions": "draft kept on purpose for next month"})["locked"]
    with pytest.raises(B.BooksError):
        B.post("b3", ws, "2026-09-30", [{"code": "6000", "debit_minor": 1}, {"code": "1000", "credit_minor": 1}])


def test_exports(env):
    from app.fin.desks import books as B
    ws = _ws("b4")
    B.run("b4", "invoice", {"workspace": ws, "party": "Acme", "issue": "2026-10-02", "lines": [{"price": 100, "tax_pct": 20}], "issue_now": True})
    a = {"workspace": ws, "since": "2026-10-01", "upto": "2026-10-31"}
    assert B.run("b4", "export", {**a, "format": "xero"})["text"].splitlines()[0].startswith("*Narration,*Date")
    q = B.run("b4", "export", {**a, "format": "quickbooks"})["text"]
    assert "Accounts receivable,120.0" in q
    t = B.run("b4", "export", {**a, "format": "tally"})["text"]
    assert t.startswith("<ENVELOPE>") and 'VCHTYPE="Journal"' in t
    rep = B.run("b4", "reports", a)
    assert rep["balanced"] and rep["profit_and_loss"]["income"] == 100.0 and rep["balance_sheet"]["checks"]


def test_tool_and_routes(env):
    from app.agent import tools as T
    from app.agent.tools import Ctx, ToolError
    from app.main import app
    ws = _ws("b5")
    assert T.FAMILY_OF["books_accounts"] == "books"
    own = Ctx(tenant_id="b5", conversation_id="", actor="owner")
    out = asyncio.run(T.dispatch("books_accounts", {"action": "chart", "workspace": ws}, own))
    out = out if isinstance(out, dict) else json.loads(out)
    assert any(a["sub"] == "bank" for a in out["accounts"])
    staff = Ctx(tenant_id="b5", conversation_id="", actor="staff:x")
    for bad in ({"action": "journal", "workspace": ws}, {"action": "close_lock", "workspace": ws}):
        with pytest.raises(ToolError):
            asyncio.run(T.dispatch("books_accounts", bad, staff))
    with pytest.raises(ToolError):
        asyncio.run(T.dispatch("books_accounts", {"action": "chart", "workspace": ws, "password": "p"}, own))
    c = TestClient(app)
    tenant = c.get("/api/fin/workspaces").json()
    assert c.post("/api/fin/books/inventory", json={"movements": [{"day": "1", "qty": 1, "unit_cost": 2}]}).json()["value_left"] == 2.0
    assert c.post("/api/fin/books/chart", json={"workspace": "nope"}).status_code == 400
    assert c.post("/api/fin/books/transfer", json={}).status_code == 403
    assert isinstance(tenant["workspaces"], list)
