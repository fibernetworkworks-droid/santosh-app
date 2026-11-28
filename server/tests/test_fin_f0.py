"""F0 of docs/FINANCE_GLOBAL_PLAN.md - the finance core: one employee for every size (profile), country rules as checked data (packs),
the laws gate, the calculation API, the data spine with statement import, and the append-only audit log. Today's finance tools run
through it with the same results."""
import asyncio
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

CSV = "Date,Narration,Debit,Credit\n01/03/2026,SALARY MARCH,,52000\n02/03/2026,UPI-GROCERY STORE,1250.50,\n05/03/2026,ATM CASH,2000,\n"
OFX = """OFXHEADER:100
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>GBP<BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260302<TRNAMT>-12.99<FITID>A1<NAME>NETFLIX<MEMO>subscription</STMTTRN>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260303<TRNAMT>1500.00<FITID>A2<NAME>CLIENT LTD</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""
QIF = "!Type:Bank\nD03/04/2026\nT-45.20\nPCITY WATER\n^\nD03/05/2026\nT300.00\nPREFUND\n^\n"
MT940 = """:20:STMT1
:25:DE89370400440532013000
:28C:1/1
:60F:C260301EUR1000,00
:61:2603020302D150,25NTRFNONREF//B1
:86:RENT MARCH
:61:2603030303C2000,00NTRFNONREF//B2
:86:INVOICE 77 PAID
:62F:C260303EUR2849,75
"""
CAMT = """<?xml version="1.0"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"><BkToCstmrStmt><Stmt>
<Ntry><Amt Ccy="EUR">99.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>2026-03-04</Dt></BookgDt><AcctSvcrRef>R1</AcctSvcrRef>
<NtryDtls><TxDtls><RmtInf><Ustrd>Insurance premium</Ustrd></RmtInf></TxDtls></NtryDtls></Ntry>
<Ntry><Amt Ccy="EUR">10.5</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-03-05</Dt></BookgDt><AcctSvcrRef>R2</AcctSvcrRef></Ntry>
</Stmt></BkToCstmrStmt></Document>"""


def _answers(size, cc="GB", **k):
    a = {"size": size, "countries": [cc], "wants": [], "people": []}
    a.update(k)
    return a


def test_every_size_from_the_wizard(env):
    from app.fin import profile as PR
    made = {}
    for size in PR.SIZE_ORDER:
        people = [{"name": "Asha", "role": "approver"}] if size in ("business", "firm", "institution") else []
        pv = PR.preview(_answers(size, people=people))
        ws = PR.apply("t1", pv["answers"], pv["hash"])
        made[size] = ws
        assert ws["size"] == size and ws["currency"] == "GBP" and ws["settings"]["employees"]
    s = {k: v["settings"] for k, v in made.items()}
    assert s["personal"]["approvals"] == "her_tap" and s["institution"]["approvals"] == "maker_checker"
    assert s["institution"]["maker_checker"] and not s["business"]["maker_checker"]
    assert s["firm"]["clients"] and s["personal"]["tiers"] == ["A"] and "B" in s["institution"]["tiers"]
    assert "household" in s["personal"]["employees"] and "markets" not in s["personal"]["employees"]
    assert s["personal"]["year_end"] == "04-05"                       # from the GB pack (shown with its status, a default only)
    # a firm's client book sits inside the firm; not inside anything else
    pv = PR.preview(_answers("personal", name="Client A"))
    c = PR.apply("t1", pv["answers"], pv["hash"], parent_id=made["firm"]["id"])
    assert c["parent_id"] == made["firm"]["id"]
    with pytest.raises(PR.ProfileError):
        PR.apply("t1", pv["answers"], pv["hash"], parent_id=made["solo"]["id"])
    with pytest.raises(PR.ProfileError):
        PR.apply("t1", pv["answers"], "wrong")                        # her tap is bound to what she saw
    assert len(PR.workspaces("t1")) == 6 and PR.workspaces("other") == []
    pv = PR.preview(_answers("personal", wants=["markets", "safety"]))
    assert pv["settings"]["employees"] == ["safety"] and pv["settings"]["not_for_this_size"] == ["markets"]
    assert PR.approval_for(made["institution"], "draft") == "maker_checker" and PR.approval_for(made["personal"], "read") == "none"


def test_profile_rejects_bad_answers():
    from app.fin import profile as PR
    for bad in ({}, {"size": "huge", "countries": ["GB"]}, {"size": "solo", "countries": []},
                {"size": "solo", "countries": ["ZZ"]}, {"size": "solo", "countries": ["GB"], "year_end": "13-40"}):
        with pytest.raises(PR.ProfileError):
            PR.preview(bad)
    pv = PR.preview({"size": "solo", "countries": ["ZZ"], "currency": "XYZ"})   # a country with no pack still works, on the floor
    assert pv["settings"]["packs"][0]["pack"] == "floor" and any("no country pack" in x for x in pv["lines"])


def test_packs_are_checked_data():
    from app.fin import pack as P
    r = P.check_all()
    assert not r["errors"] and {"GB", "IN", "US"} <= {f["cc"] for f in r["packs"]}
    # a research value is never used where a checked one is needed - the words say what to check
    with pytest.raises(P.Unchecked) as e:
        P.value_of("GB", "tax.vat_standard_rate_pct")
    assert "Check this for GB" in str(e.value)
    with pytest.raises(P.Unchecked) as e:
        P.value_of("ZZ", "tax.vat_standard_rate_pct", need="source_read")
    assert "no rule" in str(e.value)
    assert P.freshness("ZZ")["floor"] and P.view("ZZ")["floor"]
    # India's tax rules are read from bahi/rules (one copy, never two)
    assert P.view("IN")["rows"] and any(row["path"].startswith("tax.gst_rates.") for row in P.view("IN")["rows"])


def test_pack_levels_need_official_sources_and_expire():
    from app.fin import pack as P
    base = json.loads((P.DIR / "GB.json").read_text())
    leaf = base["sections"]["tax"]["vat_standard_rate_pct"]
    leaf.update(status="source_read", source="https://blog.example.com/vat", checked_on="2026-11-01", review_by="2027-05-01", quote="20%")
    assert any("not an official host" in e for e in P.validate(base))
    leaf["source"] = "https://www.gov.uk/vat-rates"
    assert not P.validate(base)
    leaf["status"] = "checked"
    assert any("checked_by" in e for e in P.validate(base))
    leaf["checked_by"] = "A. Accountant"
    assert not P.validate(base)
    assert P._effective(leaf, date(2027, 1, 1)) == "checked" and P._effective(leaf, date(2027, 6, 1)) == "source_read"
    bad = dict(base, minor_unit=0)
    assert any("minor_unit" in e for e in P.validate(bad))


def test_calc_money_and_the_same_old_results():
    from app.fin import calc as C
    from app.finguard import loans
    assert C.to_minor("1234.565", "USD") == 123457 and C.to_minor(1000, "JPY") == 1000 and C.to_minor("1.2345", "KWD") == 1235
    assert str(C.from_minor(123457, "USD")) == "1234.57"
    with pytest.raises(C.CalcError):
        C.fx(10000, "USD", "EUR", "0.92")                             # no rate is used without its date and source
    out = C.fx(10000, "USD", "EUR", "0.92", "2026-11-20", "her bank's confirmation")
    assert out["amount_minor"] == 9200
    assert sum(C.split(1000, [1, 1, 1])) == 1000 and C.split(1000, [1, 1, 1]) == [334, 333, 333]
    for name in C.REGISTRY:
        assert callable(C.fn(name)), name
    assert C.call("loan.true_cost", 100000, 12, 24) == loans.true_cost(100000, 12, 24)
    r = C.run("loan.emi", principal=100000, annual_rate_pct=12, months=12)
    assert r["result"] == loans.emi(100000, 12, 12) and r["trace"]["calc"] == "loan.emi"


def test_laws_gate():
    from app.fin import laws as L
    assert len(L.TIER_C) == 13
    for act in ("pay", "transfer", "place_order", "approve_loan", "freeze", "file_sar", "sign_opinion"):
        with pytest.raises(L.Refused):
            L.screen("x", act, {})
    for act in ("loan", "prepay", "order_ticket", "complaint", "aml_triage", "kfs"):   # today's actions pass
        L.screen("x", act, {})
    with pytest.raises(L.Refused):
        L.screen("x", "loan", {"otp": "123456"})
    with pytest.raises(L.Refused):
        L.screen("x", "complaint", {"card_number": "4111 1111 1111 1111"})
    L.screen("x", "complaint", {"account": "1234"})                   # the last 4 are fine
    L.screen("x", "charges", {"text": "UPI/4111111111111111/REF"})    # statement text is not scanned (banks print long refs)
    assert L.advice_flags("You should switch your pension to this fund.") and not L.advice_flags("Here are the costs of both.")
    assert L.decider({"settings": {"size": "personal"}}) == "you"
    assert L.decider({"settings": {"size": "firm", "deciders": [{"name": "Ravi", "role": "reviewer"}]}}) == "Ravi"


def test_spine_imports_every_format_once(env):
    from app.fin import profile as PR, spine as SP
    pv = PR.preview(_answers("solo", cc="DE", currency="EUR"))
    ws = PR.apply("t2", pv["answers"], pv["hash"])["id"]
    for fmt, text in (("csv", CSV), ("ofx", OFX), ("qif", QIF), ("mt940", MT940), ("camt053", CAMT)):
        assert SP.detect(text) == fmt, fmt
        r = SP.import_statement("t2", ws, text, account_name=f"acc-{fmt}")
        assert r["format"] == fmt and r["added"] >= 2 and not r["unreadable"], (fmt, r)
        again = SP.import_statement("t2", ws, text, account_name=f"acc-{fmt}")
        assert again["added"] == 0 and again["already_there"] == r["added"], fmt
    acc = {a["name"]: a for a in SP.accounts("t2", ws)}
    assert acc["acc-csv"]["net_minor"] == 5200000 - 125050 - 200000
    assert acc["acc-ofx"]["currency"] == "GBP" and acc["acc-ofx"]["net_minor"] == 150000 - 1299
    assert acc["acc-mt940"]["net_minor"] == 200000 - 15025 and acc["acc-camt053"]["net_minor"] == 1050 - 9900
    rows = SP.txns("t2", ws, acc["acc-mt940"]["id"])
    assert {r["narration"] for r in rows} == {"RENT MARCH", "INVOICE 77 PAID"}
    with pytest.raises(PR.ProfileError):
        SP.txns("someone_else", ws)


def test_audit_chain(env):
    from app.db import session
    from app.fin import evidence as EV
    from app.fin.models import FinEvent
    for i in range(3):
        EV.record("t3", "", "owner", "tool", f"step {i}", {"i": i})
    assert EV.verify("t3") == {"ok": True, "rows": 3}
    with session() as db:
        r = db.query(FinEvent).filter(FinEvent.tenant_id == "t3", FinEvent.seq == 2).one()
        r.what = "edited"
    v = EV.verify("t3")
    assert not v["ok"] and v["broken_at"] == 2


def test_todays_tools_run_on_the_core_unchanged(env):
    from app.agent import tools as T
    from app.agent.tools import Ctx, ToolError
    from app.fin import evidence as EV
    from app.finguard import loans
    ctx = Ctx(tenant_id="t4", conversation_id="", actor="owner")
    out = asyncio.run(T.dispatch("paisa_sahayak", {"action": "loan", "amount": 100000, "rate": 12, "months": 24}, ctx))
    want = loans.true_cost(100000, 12, 24)
    got = out if isinstance(out, dict) else json.loads(out)
    assert got.get("emi") == want["emi"] or str(want["emi"]) in json.dumps(got)
    for tool, args in (("paisa_sahayak", {"action": "complaint", "otp": "445566"}),
                       ("vitt_sahayak", {"action": "goal", "target": 100, "years": 1, "password": "x"}),
                       ("risk_desk", {"action": "kfs", "card_number": "4111111111111111"})):
        with pytest.raises(ToolError):
            asyncio.run(T.dispatch(tool, args, ctx))
    kinds = [e["kind"] for e in EV.events("t4")]
    assert kinds.count("refused") == 3 and "tool" in kinds


def test_routes(env):
    from app.main import app
    c = TestClient(app)
    q = c.get("/api/fin/setup").json()
    assert len(q["questions"]) == 8 and len(q["employees"]) == 18
    pv = c.post("/api/fin/setup/preview", json={"answers": _answers("business", cc="US")}).json()
    assert pv["answers"]["currency"] == "USD"
    ws = c.post("/api/fin/setup/apply", json={"answers": pv["answers"], "hash": pv["hash"]}).json()
    assert c.post("/api/fin/setup/apply", json={"answers": pv["answers"], "hash": "x"}).status_code == 400
    r = c.post(f"/api/fin/{ws['id']}/import", json={"text": OFX}).json()
    assert r["added"] == 2
    assert c.get(f"/api/fin/{ws['id']}/accounts").json()["accounts"][0]["txns"] == 2
    assert c.get("/api/fin/packs").json()["errors"] == []
    assert c.get("/api/fin/packs/US").json()["currency"] == "USD"
    assert len(c.get("/api/fin/laws").json()["tier_c"]) == 13
    ev = c.get("/api/fin/events").json()
    assert ev["chain"]["ok"] and ev["events"]
