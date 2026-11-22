"""F9 of docs/FINANCE_GLOBAL_PLAN.md - Institution mode + Financial Crime, Compliance, Risk, Audit, Governance. The card: an
institution sandbox with 1 M transactions; alert triage and SAR drafts for a human scorer; maker-checker cannot be bypassed; load."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _inst(tenant):
    from app.fin import profile as PR
    from app.fin.desks import institution as IN
    a = {**PR.preview({"size": "institution", "countries": ["GB"], "wants": [], "people": []})["answers"], "currency": "GBP"}
    ws = PR.apply(tenant, a, PR.preview(a)["hash"])["id"]
    go = lambda action, **x: IN.run(tenant, action, {"workspace": ws, **x})   # noqa: E731
    go("person_add", name="Ada", roles=["admin"])
    for n, r in (("Mia", ["maker"]), ("Cal", ["checker"]), ("Cat", ["checker"]), ("Mo", ["mlro", "checker"])):
        go("person_add", person="ada", name=n, roles=r)
    return ws, go


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f9 as C
    from app.fin import makerchecker as MC
    r = C.run(3000)
    assert r["ok"], [x for x in r["rows"] if not x["ok"]]
    real = MC.is_approved
    try:      # an approval check that trusts the stored state alone must fail the card
        MC.is_approved = lambda t, w, d: True
        assert not C.run(1000, seed=5)["ok"]
    finally:
        MC.is_approved = real


def test_maker_checker(env):
    from app.fin.desks import institution as IN
    ws, go = _inst("i1")
    go("limits", person="ada", single_check_limit=1000)
    d = go("submit", person="mia", kind="policy", body="v1")["draft"]
    for who in ("mia", "ada"):
        with pytest.raises(IN.InstError):
            go("check", person=who, draft=d["id"], verdict="approve", hash=d["hash"])
    with pytest.raises(IN.InstError):
        go("check", person="cal", draft=d["id"], verdict="approve", hash="x")
    assert go("check", person="cal", draft=d["id"], verdict="approve", hash=d["hash"])["draft"]["state"] == "approved"
    big = go("submit", person="mia", kind="limit", body="raise", amount=5000)["draft"]
    assert go("check", person="cal", draft=big["id"], verdict="approve", hash=big["hash"])["draft"]["state"] == "waiting"
    assert go("check", person="cat", draft=big["id"], verdict="approve", hash=big["hash"])["draft"]["state"] == "approved"
    with pytest.raises(PermissionError):
        go("set_state", person="ada", draft=d["id"])
    assert go("submit", person="mia", body="x", state="approved")["draft"]["state"] == "waiting"


def test_triage_sar_and_score(env):
    from app.fin.desks import institution as IN
    ws, go = _inst("i2")
    tx = [{"id": f"t{k}", "customer": "C1", "date": f"2026-03-0{k}", "amount": 9500, "direction": "in", "channel": "cash"} for k in range(1, 5)]
    tx += [{"id": "u1", "customer": "C2", "date": "2026-03-01", "amount": 100, "direction": "in", "channel": "cash"}]
    r = go("aml_triage", transactions=tx)
    assert [a["rule"] for a in r["alerts"]] == ["structuring"] and r["alerts"][0]["customer"] == "C1"
    assert "cash_threshold" in r["rules_hoola_default"]
    s = go("sar_draft", person="mia", alert=r["alerts"][0], transactions=tx, customer={"name": "X", "expected_activity": "salary"})
    assert s["checks"]["ok"] and s["draft"]["state"] == "waiting" and "38,000.00" in s["body"]
    with pytest.raises(IN.InstError):
        go("sar_score", person="cal", draft=s["draft"]["id"], scores={k: 4 for k in IN.SCORE_ON})
    sc = go("sar_score", person="mo", draft=s["draft"]["id"], scores={k: 4 for k in IN.SCORE_ON}, comment="good")
    assert sc["total"] == 20 and sc["scored_by"] == "Mo"
    with pytest.raises(PermissionError):
        go("file_sar", person="mo")


def test_compliance_risk_audit_governance(env):
    from app.fin.desks import institution as IN
    ws, go = _inst("i3")
    go("person_add", person="ada", name="Cora", roles=["compliance"])
    with pytest.raises(IN.InstError):
        go("obligations", person="cora", add=[{"name": "AML policy review"}])         # no source
    o = go("obligations", person="cora", today="2026-09-01", add=[{"name": "AML policy review", "source": "MLR 2017 reg 19",
                                                                   "owner": "Mo", "control": "annual review", "every_days": 365, "last_done": "2025-06-01"}])
    assert o["overdue"] == ["AML policy review"]
    p = go("promotion_check", text="Guaranteed 12% returns! Grew 40% last year.")
    assert not p["ok"] and len(p["problems"]) >= 3
    assert go("promotion_check", text="Capital at risk: your investment can go down. Past performance is not a guide. Fees 1%.")["ok"]
    inc = go("incident", title="Outage", detected="2026-09-01T10:00", clocks=[{"report": "initial", "hours": 4}, {"report": "final", "hours": 720}])
    assert inc["due"][0]["due"] == "2026-09-01T14:00"
    h = go("rcsa", appetite=10, risks=[{"name": "fraud", "likelihood": 4, "impact": 4}, {"name": "it", "likelihood": 2, "impact": 2}])
    assert h["over_appetite"] == ["fraud"]
    s1 = go("sample", population=list(range(100)), size=5, seed=42)
    assert s1["sample"] == go("sample", population=list(range(100)), size=5, seed=42)["sample"]
    j = go("je_test", period_end="2026-06-30", usual_users=["ann"], journals=[{"id": 1, "date": "2026-06-28", "amount": 5000, "user": "bob"}])
    assert set(j["flagged"][0]["flags"]) == {"weekend", "round amount", "near period end", "unusual user", "no description"}
    ct = go("cap_table", holders=[{"name": "A", "shares": 800}, {"name": "B", "shares": 200}], pre_money=1000000, **{"raise": 250000})
    assert ct["new_shares"] == 250 and ct["after"]["new investor"]["pct"] == 20.0
    with pytest.raises(IN.InstError):
        go("whistle", what="x", reporter_name="Jo")
    assert go("whistle", what="expense fraud", area="finance")["case"].startswith("WB-")
    k = go("api_key", person="ada", scopes=["read"])
    assert IN.key_allows("i3", ws, k["key"], "read") and not IN.key_allows("i3", ws, k["key"], "check")
    ex = go("export", person="ada")
    assert '"keys"' not in ex["file"] and ex["sha256"]


def test_tool_and_routes(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["institution_desk"] == "institution" and "institution_desk" in HI.CATALOG
    out = asyncio.run(TL.dispatch("institution_desk", {"action": "sample", "population": [1, 2, 3], "size": 2, "seed": 1},
                                  Ctx(tenant_id="i4", conversation_id="", actor="owner")))
    out = out if isinstance(out, dict) else json.loads(out)
    assert len(out["sample"]) == 2
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("institution_desk", {"action": "sample"}, Ctx(tenant_id="i4", conversation_id="", actor="customer:x")))
    c = TestClient(app)
    assert c.post("/api/fin/institution/rcsa", json={"risks": []}).status_code == 200
    assert c.post("/api/fin/institution/submit", json={}).status_code == 400
    assert c.post("/api/fin/institution/file_sar", json={}).status_code == 403
