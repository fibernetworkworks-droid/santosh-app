"""F7 of docs/FINANCE_GLOBAL_PLAN.md - Firm mode (Practice). The card: a firm with 50 test clients; isolation (no client sees
another), the review gate holds, drafts signed by the named person."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


def _firm(tenant):
    from app.fin import profile as PR
    from app.fin.desks import firm as F
    a = {**PR.preview({"size": "firm", "countries": ["GB"], "wants": [], "people": []})["answers"], "currency": "GBP", "name": "Firm"}
    fid = PR.apply(tenant, a, PR.preview(a)["hash"])["id"]
    go = lambda action, **x: F.run(tenant, action, {"firm": fid, **x})   # noqa: E731
    go("person_add", name="Pat", role="partner")
    return fid, go


def test_the_card_passes_and_can_fail(env):
    from app.fin import card_f7 as C
    from app.fin.desks import firm as F
    r = C.run(50)
    assert r["ok"] and r["clients"] == 50 and r["leaks"] == 0, r["problems"][:3]
    real = F._sees
    try:      # a staff member who sees every client must fail the card
        F._sees = lambda p, c: True
        assert not C.run(8, seed=3)["ok"]
    finally:
        F._sees = real


def test_people_and_isolation(env):
    from app.fin.desks import firm as F
    fid, go = _firm("f1")
    with pytest.raises(F.FirmError):
        go("person_add", person="nobody", name="Eve", role="partner")
    a = go("client_add", person="pat", name="Alpha")["client"]["id"]
    b = go("client_add", person="pat", name="Beta")["client"]["id"]
    with pytest.raises(F.FirmError):
        go("person_add", person="pat", name="Al", role="client", clients=[a, b])     # a client person has one book
    go("person_add", person="pat", name="Al", role="client", clients=[a])
    go("person_add", person="pat", name="Pip", role="preparer", clients=[b])
    assert [c["name"] for c in go("clients", person="al")["clients"]] == ["Alpha"]
    assert go("portal", person="al", client=b)["client"] == "Alpha"                 # asks for Beta, gets their own
    for action, x in (("draft", {"client": a, "kind": "memo", "body": "x", "signer": "pat"}), ("dashboard", {}), ("queue", {})):
        with pytest.raises(F.FirmError):
            go(action, person="al", **x)
    with pytest.raises(F.FirmError) as e:
        go("request", person="pip", client=a, items=["x"])
    assert str(e.value) == "No such client for this person."
    with pytest.raises(F.FirmError) as e2:
        go("request", person="pip", client="fw_does_not_exist", items=["x"])
    assert str(e2.value) == str(e.value)                                               # the same words: nothing leaks


def test_review_gate_and_signature(env):
    from app.fin.desks import firm as F
    fid, go = _firm("f2")
    c = go("client_add", person="pat", name="Gamma")["client"]["id"]
    go("person_add", person="pat", name="Sam", role="partner")
    go("person_add", person="pat", name="Ria", role="reviewer", clients="all")
    go("person_add", person="pat", name="Pip", role="preparer", clients=[c])
    d = go("draft", person="pip", client=c, kind="tax_return", body="Return v1", signer="sam")["draft"]
    with pytest.raises(F.FirmError):
        go("sign", person="sam", draft=d["id"])
    with pytest.raises(F.FirmError):
        go("review", person="pip", draft=d["id"], verdict="approve")
    with pytest.raises(F.FirmError):
        go("review", person="ria", draft=d["id"], verdict="approve", hash="stale")
    go("review", person="ria", draft=d["id"], verdict="approve", hash=d["hash"])
    with pytest.raises(F.FirmError) as e:
        go("sign", person="pat", draft=d["id"])
    assert "Sam" in str(e.value)
    s = go("sign", person="sam", draft=d["id"])["draft"]["signed"]
    assert s["name"] == "Sam" and s["hash"] == F._hash("Return v1")
    with pytest.raises(F.FirmError):
        go("edit", person="pip", draft=d["id"], body="v2")
    go("share", person="pat", draft=d["id"])
    au = go("audit", person="pat", client=c)
    assert any("signed by Sam" in x["what"] for x in au["events"]) and au["chain"]["ok"]
    with pytest.raises(PermissionError):
        go("file_return", person="pat")


def test_the_stale_approval_lock(env):
    """The signature needs the LAST approval to be of the text being signed - a second lock behind 'an edit sends it back'."""
    from app import db
    from app.fin.desks import firm as F
    from app.fin.models import FinDraft
    fid, go = _firm("f3")
    c = go("client_add", person="pat", name="Delta")["client"]["id"]
    go("person_add", person="pat", name="Ria", role="reviewer", clients="all")
    d = go("draft", person="pat", client=c, kind="letter", body="Hello", signer="pat")["draft"]
    go("review", person="ria", draft=d["id"], verdict="approve")
    with db.session() as s:                      # the text changed by some other road, the state left approved
        row = s.get(FinDraft, d["id"])
        row.body, row.hash = "Hello changed", F._hash("Hello changed")
        s.commit()
    with pytest.raises(F.FirmError) as e:
        go("sign", person="pat", draft=d["id"])
    assert "another text" in str(e.value)


def test_adviser_parts(env):
    from app.fin.desks import firm as F
    fid, go = _firm("f4")
    c = go("client_add", person="pat", name="Eps", size="personal")["client"]["id"]
    ff = go("factfind", person="pat", client=c, answers={"objectives": "retire at 60", "attitude_to_risk": "balanced", "junk": "x"})
    assert "junk" not in ff["factfind"] and "income" in ff["missing"]
    with pytest.raises(F.FirmError):
        go("suitability", person="pat", client=c)
    su = go("suitability", person="pat", client=c, recommendation="Keep the pension in the balanced fund.", signer="pat")
    assert "retire at 60 (from the fact-find)" in su["body"] and "costs and charges" in su["missing"] and su["draft"]["state"] == "waiting"
    m = go("meeting", person="pat", client=c, text="Talked.\nAction: send the pension statement by 2026-10-01\nDecided: stay invested")
    assert m["actions"][0]["due"] == "2026-10-01" and m["decisions"] == ["stay invested"]
    dr = go("drift", holdings=[{"symbol": "A", "qty": 10, "price": 80}, {"symbol": "B", "qty": 10, "price": 20}],
            targets={"A": 50, "B": 50})
    assert dr
    e = go("engagement", person="pat", client=c, services=["tax return"], fee="500", signer="pat")
    assert e["draft"]["kind"] == "engagement"
    cfo = go("cfo_pack", person="pat", client=c, since="2026-01-01", upto="2026-09-30")
    assert "profit_and_loss" in cfo


def test_tool_routes_and_console(env):
    from app.agent import tools as TL
    from app.agent.tools import Ctx, ToolError
    from app.employee import hire as HI
    from app.main import app
    assert TL.FAMILY_OF["firm_practice"] == "firmmode" and "firm_practice" in HI.CATALOG
    js = open(TL.__file__.replace("agent/tools.py", "static/console/employees.js")).read()
    for k in ("household_money", "books_accounts", "tax_worldwide", "payroll_worldwide", "cash_treasury", "credit_lending",
              "firm_practice", "payments_desk", "institution_desk", "investments_desk", "markets_desk",
              "community_finance", "digital_assets", "public_finance"):                                     # every finance-plan employee opens its desk in the console
        assert k in HI.CATALOG and f"{k}: 'deptdesk'" in js, k
    with pytest.raises(ToolError):
        asyncio.run(TL.dispatch("firm_practice", {"action": "clients", "firm": "x", "person": "y"},
                                Ctx(tenant_id="f5", conversation_id="", actor="customer:z")))
    c = TestClient(app)
    assert c.post("/api/fin/firm/clients", json={}).status_code == 400
    assert c.post("/api/fin/firm/file_return", json={"firm": "x"}).status_code == 403
