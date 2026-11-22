"""F12 of docs/FINANCE_GLOBAL_PLAN.md - Public sector + proof. The card: G2P runs reconciled, deposit cover, benefits / supervision /
development checks, no decision taken. The proof: every card, real users per size for a month, clean packs."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f12 as C
    from app.fin.desks import public as PB
    assert C.run(3)["ok"]
    real = PB.mask
    try:      # account numbers left unmasked must fail the card
        PB.mask = lambda a: str(a)
        assert not C.run(1)["ok"]
    finally:
        PB.mask = real


def test_parts(env):
    from app.fin import laws as L
    from app.fin.desks import public as PB
    o = PB.run("u1", "overpayment", {"due": [{"period": "2026-01", "amount": 100}, {"period": "2026-02", "amount": 100}],
                                     "paid": [{"period": "2026-01", "amount": 150}, {"period": "2026-02", "amount": 80}]})
    assert o["overpaid"] == 50.0 and o["underpaid"] == 20.0 and o["net"] == 30.0
    i = PB.run("u1", "inspection", {"today": "2026-09-01", "earlier": [{"id": "E1", "area": "AML"}],
                                    "findings": [{"id": "F1", "area": "AML", "owner": "Ann", "due": "2026-08-01"},
                                                 {"id": "F2", "area": "IT", "due": "2026-12-01"}, {"id": "F3", "area": "IT", "status": "closed"}]})
    assert i["overdue"] == ["F1"] and i["repeat"] == ["F1"] and i["without_owner"] == ["F2", "F3"] and i["open"] == 2
    with pytest.raises(PB.PublicError):
        PB.run("u1", "deposit_cover", {"accounts": []})                       # the cover limit is hers
    with pytest.raises(L.Refused):
        PB.run("u1", "award_benefit", {})


def test_proof_counts_real_users_only(env):
    from app import db
    from app.fin import proof as PF
    from app.fin.models import FinEvent, FinWorkspace, ensure
    ensure()
    now = datetime.now(timezone.utc)
    with db.session() as s:
        s.add(FinWorkspace(id="fw_real", tenant_id="t_real", size="personal"))
        s.add(FinWorkspace(id="fw_card", tenant_id="card9_x", size="firm"))
        for d in (0, 30):
            s.add(FinEvent(tenant_id="t_real", workspace_id="fw_real", kind="tool", at=now - timedelta(days=d)))
            s.add(FinEvent(tenant_id="card9_x", workspace_id="fw_card", kind="tool", at=now - timedelta(days=d)))
        s.commit()
    u = PF.users(now)
    assert u["sizes"]["personal"]["a_month"] and u["sizes"]["firm"]["users"] == 0
    assert set(u["missing"]) == {"solo", "business", "firm", "institution"}
    p = PF.packs()
    assert p["countries"] >= 10 and "never used in a calculation" in p["says"]
    r = PF.cards(quick=True, only=["F8", "F12"])
    assert [x["phase"] for x in r] == ["F8", "F12"] and all(x["ok"] for x in r)


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["public_finance"] == "pubfin" and "public_finance" in HI.CATALOG
    out = asyncio.run(TL.dispatch("public_finance", {"action": "overpayment", "due": [], "paid": []},
                                  Ctx(tenant_id="u2", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert out["net"] == 0.0
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("public_finance", {"action": "g2p"}, Ctx(tenant_id="u2", conversation_id="", actor="customer:x")))
    c = TestClient(app)
    assert c.post("/api/fin/public/g2p", json={"beneficiaries": [], "payments": [], "bank_return": []}).status_code == 200
    assert c.post("/api/fin/public/benefits", json={}).status_code == 400
    assert c.post("/api/fin/public/close_bank", json={}).status_code == 403
    pr = c.get("/api/fin/proof")
    assert pr.status_code == 200 and "packs" in pr.json()
    wf = open(TL.__file__.replace("server/app/agent/tools.py", ".github/workflows/vps-ops.yml")).read()
    assert "fin_proof)" in wf and "- fin_proof" in wf
