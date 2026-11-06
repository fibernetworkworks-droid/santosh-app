"""Health-insurance Wave 1 (bima_desk). Worksheets and checklists: a named decider, nothing stored, sent or decided."""
import asyncio
import inspect

import pytest

from app.bimadesk import engines as E
from tests.test_life import conv_ctx


def test_claim_checklist_and_deadlines():
    r = E.claim_checklist("reimbursement", ["claim form", "policy copy", "photo id"], "2026-10-01", "2026-10-05", "2026-11-01", file_days=30)
    assert not r["complete"] and any("discharge" in m for m in r["missing"]) and r["verify"]
    assert r["deadlines"]["file_by"] == "2026-11-04" and r["deadlines"]["days_left"] == 3 and not r["deadlines"]["overdue"]
    c = E.claim_checklist("cashless", kind="accident")
    assert any("FIR" in n for n in c["needed"]) and "pre-authorisation" in c["needed"][0]
    with pytest.raises(ValueError):
        E.claim_checklist("barter")


def test_payable_worksheet_room_rent_and_gap():
    p = E.payable([{"name": "Room rent", "billed": 20000}, {"name": "Surgery", "billed": 80000, "payable_cap": 70000}, {"name": "Registration kit", "billed": 5000}],
                  sum_insured=500000, room_rent_cap=5000, room_rent_charged=10000, copay_pct=10, deductible=0, non_payable=["kit"], settled=50000)
    assert p["non_payable"] == 5000 and p["tariff_cap_cut"] == 10000
    assert p["room_rent_proportion_cut"] == 45000.0 and p["estimated_payable"] == 40500.0
    assert p["gap"] == 9500.0 and p["questions_to_ask"]
    assert p["decider"] and p["not_checked"]
    with pytest.raises(ValueError):
        E.payable([])


def test_settlement_match_and_status_message():
    m = E.settlement_match([{"claim": "A", "utr": "U1", "amount": 9000}, {"claim": "B", "utr": "U1", "amount": 100}, {"claim": "Z", "utr": "U9", "amount": 5}],
                           [{"claim": "A", "payable": 10000, "tds": 1000}, {"claim": "B", "payable": 500}, {"claim": "C", "payable": 300}])
    st = {r["claim"]: r["status"] for r in m["rows"]}
    assert st == {"A": "matched", "B": "short", "C": "not received"} and m["duplicate_utr"] == ["U1"] and m["unmatched_payments"][0]["claim"] == "Z"
    s = E.status_message("paid", "C1", "UTR9", "en")
    assert "C1" in s["message"] and s["send"] is False
    assert "faisla" in E.status_message("rejected", "C2")["message"]
    with pytest.raises(ValueError):
        E.status_message("???")


def test_ageing_renewals_grievance():
    a = E.ageing([{"id": 1, "received": "2026-09-01", "status": "open"}, {"id": 2, "received": "2026-10-20", "status": "open"}, {"id": 3, "received": "2026-01-01", "status": "paid"}],
                 "2026-11-05", 30, 5)
    assert a["open"] == 2 and [r["id"] for r in a["past_timeline"]] == [1] and a["due_soon"] == [] and a["verify"]
    r = E.renewals([{"id": "p1", "holder": "R", "renewal_date": "2026-11-20", "premium": 15000}, {"id": "p2", "holder": "S", "renewal_date": "2027-06-01"}], "2026-11-05")
    assert r["count"] == 1 and r["due"][0]["portability_note"]
    g = E.grievance([{"id": 1, "received": "2026-10-01", "text": "Claim rejected, hospital in ICU emergency"}, {"id": 2, "received": "2026-11-04", "text": "need address change"}], "2026-11-05")
    x = {i["id"]: i for i in g["items"]}
    assert x[1]["category"] == "claim" and x[1]["needs_human_now"] and x[1]["ack_late"] and x[1]["resolve_late"] and x[2]["category"] == "policy servicing" and not x[2]["ack_late"]


def test_appeal_and_kyc():
    ap = E.appeal(["Pre-existing disease not disclosed", "Documents incomplete"], today="2026-11-05", insurer_replied_on="2026-10-20")
    assert len(ap["points"]) == 2 and any("onset" in d for d in ap["points"][0]["supporting_documents"]) and ap["days_left_if_one_year"] == 349
    assert "not legal" in ap["note"].lower() and ap["decider"]
    k = E.kyc_check({"aadhaar": "1234 5678 9012", "pan": "ABCDE1234F", "ifsc": "HDFC0001234", "bank_account": "123456789012", "name": "R", "dob": "1990-01-01"})
    assert k["all_ok"] and k["checks"][0]["shown"].endswith("9012") and "1234 5678" not in str(k)
    bad = E.kyc_check({"pan": "XX", "aadhaar": "12"})
    assert not bad["all_ok"]


def test_engines_are_pure_and_tool_is_wired():
    src = inspect.getsource(E)
    for w in ("session(", "open(", "sqlite", "requests", "httpx"):
        assert w not in src
    from app.agent import tools as T
    assert "bima_desk" in T.HANDLERS and any(t["name"] == "bima_desk" for t in T.TOOLS)
    from app.employee.hire import CATALOG
    assert CATALOG["bima_desk"]["group"] == "Health Insurance" and CATALOG["bima_desk"]["never"]
    from app import voice
    assert "bima_desk" in voice.VOICE_VIA_KAAM


def test_tool_runs_and_customer_scope(env):
    ctx = conv_ctx()
    out = asyncio.run(T_run(ctx, "claim_checklist", claim_type="cashless"))
    assert out["claim_type"] == "cashless"
    ctx.actor = "customer:9"
    assert asyncio.run(T_run(ctx, "appeal", reasons=["x"]))["points"]
    from app.agent.tools import ToolError
    with pytest.raises(ToolError):
        asyncio.run(T_run(ctx, "ageing", claims=[{"id": 1, "received": "2026-01-01"}]))


def T_run(ctx, action, **a):
    from app.agent.bimadesk_tools import _bima_desk
    return _bima_desk(ctx, action, **a)
