"""F8 of docs/FINANCE_GLOBAL_PLAN.md - Payments. The card: representment packs for 3 schemes' reason codes; reconciliation of fixed
multi-gateway months."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f8 as C
    from app.fin.desks import payments as PM
    r = C.run(3)
    assert r["ok"] and r["schemes"] == ["amex", "mastercard", "visa"], [x for x in r["rows"] if not x["ok"]][:2]
    real = PM.compelling
    try:      # a compelling-evidence test that counts every earlier payment must fail the card
        PM.compelling = lambda a: {**real(a), "qualifies": True}
        assert not C.run(1)["ok"]
    finally:
        PM.compelling = real


def test_dispute_pack(env):
    from app.fin.desks import payments as PM
    r = PM.run("p1", "dispute", {"network": "mastercard", "reason_code": "4855", "amount": 80, "transaction_id": "T1",
                                 "evidence": {"proof_of_delivery": True, "signature": True}, "received": "2026-09-01", "window_days": 30})
    assert r["evidence_you_have"] == ["proof_of_delivery", "signature"] and r["evidence_missing"] == ["usage_logs", "customer_communication"]
    assert r["verdict"].startswith("the evidence answers") and r["respond_by"] == "2026-10-01" and "T1" in r["letter"]
    d = PM.run("p1", "dispute", {"network": "visa", "reason_code": "12.6.1", "evidence": {"refund_issued": True}})
    assert d["verdict"].startswith("already refunded") and "not confirmed" in d["respond_by"]
    with pytest.raises(PM.PaymentsError):
        PM.run("p1", "dispute", {"network": "visa", "reason_code": "13.1", "evidence": {"made_up": True}})
    with pytest.raises(PermissionError):
        PM.run("p1", "submit_response", {})


def test_reconcile_fees_payouts(env):
    from app.fin.desks import payments as PM
    r = PM.run("p2", "reconcile", {
        "orders": [{"id": "A", "gateway": "gw", "amount": 100}, {"id": "B", "gateway": "gw", "amount": 50}],
        "settlements": [{"gateway": "gw", "payout_id": "P1", "payout_date": "2026-08-01",
                         "lines": [{"order_id": "A", "type": "sale", "amount": 100}, {"order_id": "A", "type": "fee", "amount": 3.2},
                                   {"order_id": "A", "type": "refund", "amount": 10}]}],
        "deposits": [{"id": "D1", "date": "2026-08-03", "amount": 86.8, "narration": "GW"}, {"id": "D2", "date": "2026-08-04", "amount": 5}]})
    assert [x["order"] for x in r["orders"]["missing_at_gateway"]] == ["B"] and r["payouts"][0]["deposit"] == "D1"
    assert r["deposits_without_payout"] == ["D2"] and r["by_gateway"]["gw"]["effective_fee_pct"] == 3.2 and not r["balanced"]
    f = PM.run("p2", "fee_audit", {"contract": {"gw": {"pct": 2.9, "fixed": 0.3}},
                                   "transactions": [{"id": 1, "gateway": "gw", "amount": 100, "fee": 3.2}, {"id": 2, "gateway": "gw", "amount": 100, "fee": 3.5}]})
    assert f["overcharged_total"] == 0.3 and f["overcharged_lines"][0]["id"] == 2
    p = PM.run("p2", "payouts", {"commission_pct": 10, "orders": [{"seller": "S", "amount": 200}, {"seller": "S", "amount": 20, "type": "refund"},
                                                                  {"seller": "T", "amount": 10, "fee": 30}]})
    s = {x["seller"]: x for x in p["sellers"]}
    assert s["S"]["owed"] == 162.0 and s["T"]["carry_forward"]
    e = PM.run("p2", "export", {"invoices": [{"id": "X", "date": "2026-01-10", "amount": 1000, "currency": "USD"}],
                                "receipts": [{"invoice": "X", "amount": 400}], "realise_within_days": 270, "today": "2026-11-01"})
    assert e["invoices"][0]["outstanding"] == 600 and e["late"] == ["X"]
    dn = PM.run("p2", "dunning", {"failed": [{"customer": "c", "amount": 9.99, "date": "2026-08-01"}], "retry_days": [2, 5]})
    assert [x["retry_on"] for x in dn["customers"][0]["plan"]] == ["2026-08-03", "2026-08-06"]


def test_payment_firm_parts(env):
    from app.fin.desks import payments as PM
    k = PM.run("p3", "kyb", {"business": "Shop Ltd", "threshold_pct": 25, "documents": ["registration"],
                             "ownership": [{"owned": "Shop Ltd", "owner": "Hold Co", "pct": 80}, {"owned": "Shop Ltd", "owner": "Ana", "pct": 20, "person": True},
                                           {"owned": "Hold Co", "owner": "Ben", "pct": 50, "person": True},
                                           {"owned": "Hold Co", "owner": "Cy", "pct": 50, "person": True}]})
    assert [(b["owner"], b["pct"]) for b in k["beneficial_owners"]] == [("Ben", 40.0), ("Cy", 40.0)]
    assert "ownership chart" in k["documents_missing"]
    with pytest.raises(PM.PaymentsError):
        PM.run("p3", "kyb", {"business": "A", "threshold_pct": 25, "ownership": [{"owned": "A", "owner": "B", "pct": 100},
                                                                               {"owned": "B", "owner": "A", "pct": 100}]})
    s = PM.run("p3", "safeguarding", {"days": [{"date": "2026-08-01", "owed_to_customers": 100, "safeguarded": 100},
                                               {"date": "2026-08-02", "owed_to_customers": 150, "safeguarded": 120}]})
    assert s["shortfall_days"] == ["2026-08-02"]
    ok = ('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"><CstmrCdtTrfInitn><GrpHdr><MsgId>M1</MsgId>'
          '<CreDtTm>2026-08-01T10:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><CtrlSum>10.50</CtrlSum></GrpHdr><PmtInf><DbtrAcct><Id>'
          '<IBAN>GB82WEST12345698765432</IBAN></Id></DbtrAcct><CdtTrfTxInf><PmtId><EndToEndId>E1</EndToEndId></PmtId><Amt>'
          '<InstdAmt Ccy="EUR">10.50</InstdAmt></Amt><CdtrAgt><FinInstnId><BICFI>DEUTDEFF</BICFI></FinInstnId></CdtrAgt><CdtrAcct><Id>'
          '<IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct></CdtTrfTxInf></PmtInf></CstmrCdtTrfInitn></Document>')
    assert PM.run("p3", "iso20022", {"xml": ok})["ok"]
    bad = ok.replace("<CtrlSum>10.50", "<CtrlSum>11.00").replace("DE89370400440532013000", "DE89370400440532013001")
    r = PM.run("p3", "iso20022", {"xml": bad})
    assert not r["ok"] and any("CtrlSum" in p for p in r["problems"]) and any("check digits" in p for p in r["problems"])
    m = PM.run("p3", "merchant_risk", {"high_risk_mcc": ["7995"], "merchants": [{"name": "Bet", "mcc": "7995", "monthly_volume": [10, 10, 10, 50]}]})
    assert m["to_review"] == ["Bet"] and len(m["merchants"][0]["flags"]) == 2


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["payments_desk"] == "paydesk" and "payments_desk" in HI.CATALOG
    out = asyncio.run(TL.dispatch("payments_desk", {"action": "reasons"}, Ctx(tenant_id="p4", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert "10.4" in out["reasons"]["visa"]
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("payments_desk", {"action": "reasons"}, Ctx(tenant_id="p4", conversation_id="", actor="customer:x")))
    c = TestClient(app)
    assert c.post("/api/fin/payments/reasons", json={}).status_code == 200
    assert c.post("/api/fin/payments/dispute", json={}).status_code == 400
    assert c.post("/api/fin/payments/charge_card", json={}).status_code == 403
