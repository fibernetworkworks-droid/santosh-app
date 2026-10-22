"""v0.117 Theka Sahayak: tenders (dates, EMD, papers), project terms, BOQ import, measurement book with deviation flags,
RA bills (cumulative - previous, GST, retention / TDS / GST TDS / cess / mobilisation recovery), her Haan to submit,
passed / paid, receivables + retention, subcontractor TDS, material, diary + EOT letter, day note, tools + API."""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)
BOQ = ("Item No,Description of item,Unit,Qty,Rate\n1,Earthwork in excavation,cum,1000,250\n2,PCC 1:4:8,cum,100,5200\n"
       "3,RCC M25 incl. shuttering,cum,200,8500\n,,,,\n")


@pytest.fixture
def tk(env, monkeypatch):
    from app.theka import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    return S


def setup(S):
    S.save_settings(T, firm="Ingle Constructions", individual=False, registration="PWD Class II", registration_valid_to="2026-12-01")
    S.save_project(T, "Akot road culvert", client="PWD Akola", govt=True, value=2500000, start="2026-07-01", end="2026-12-31", mob_advance=200000,
                   bg_amount=75000, bg_valid_to="2026-11-10")
    S.boq(T, "culvert", data=BOQ.encode(), name="boq.csv")


def test_rules():
    from app.theka import rules as R
    d = R.deductions(100000, 18000, {"retention_pct": 5, "it_tds_pct": 2, "gst_tds": True, "value": 2500000, "cess_pct": 1, "mob_pct": 10}, 5000)
    assert d["items"] == {"retention": 5000.0, "income_tax_tds": 2000.0, "gst_tds": 2000.0, "labour_cess": 1000.0, "mobilisation_recovery": 5000.0}
    assert d["net"] == 118000 - 15000
    assert "gst_tds" not in R.deductions(100000, 18000, {"gst_tds": True, "value": 200000}, 0)["items"]
    assert R.deviation(130, 100)["level"] == "stop" and R.deviation(110, 100)["level"] == "warn" and R.deviation(90, 100) is None
    assert R.deviation(5, 0)["level"] == "warn"
    dl = R.delay(date(2026, 1, 1), date(2026, 12, 31), date(2026, 10, 1), 40)
    assert dl["behind_pct"] > 30
    assert R.tender_alert(date(2026, 10, 22), DAY).startswith("Aaj")
    assert R.it_tds(25000, 0, True)["tds"] == 0 and R.it_tds(35000, 0, True)["tds"] == 350


def test_tender(tk):
    S = tk
    r = S.save_tender(T, "Construction of CC road ward 12", dept="Nagar Parishad Akot", portal="mahatenders", ref="2026_NPA_1234",
                      value=4500000, emd=45000, last_date="24-10-2026 17:00")
    v = r["tender"]
    assert v["last_date"] == "2026-10-24 17:00" and v["days_left"] == 2 and "2 din" in v["alert"] and len(v["missing"]) == len(v["docs"])
    v = S.save_tender(T, tender="2026_NPA_1234", have=["udyam", "gst", "pan"], status="preparing")["tender"]
    assert len(v["missing"]) == len(v["docs"]) - 3
    assert "Tender" in S.day(T)["say"]
    lost = S.save_tender(T, tender=v["id"], status="lost", l1=4300000)
    assert "EMD wapas" in lost["say"] and "EMD" in S.day(T)["say"]


def test_bills_flow(tk):
    S = tk
    setup(S)
    assert len(S.boq_items(T, "culvert")) == 3
    S.measure(T, "culvert", "1", 400, "ch 0+000 to 0+200", "2026-08-10", "JE Patil")
    S.measure(T, "culvert", "pcc", 50, "", "2026-08-20")
    with pytest.raises(S.ThekaError):
        S.measure(T, "culvert", "steel", 10)
    b1 = S.ra_bill(T, "culvert", "2026-08-31")
    d = b1["bill"]
    assert b1["number"] == 1 and d["this_taxable"] == 400 * 250 + 50 * 5200 and d["gst"] == round(d["this_taxable"] * 0.18, 2)
    ded = d["deductions"]
    assert ded["retention"] == round(d["this_taxable"] * 0.05, 2) and ded["income_tax_tds"] == round(d["this_taxable"] * 0.02, 2)
    assert ded["gst_tds"] == round(d["this_taxable"] * 0.02, 2) and ded["labour_cess"] == round(d["this_taxable"] * 0.01, 2)
    assert ded["mobilisation_recovery"] == round(d["this_taxable"] * 0.10, 2) and b1["file"]["name"] == "RA-Bill-1.pdf"
    assert "haan" in b1["say"]
    S.bill_status(T, b1["bill_id"], "submitted")
    # second bill only bills the new quantities
    S.measure(T, "culvert", "1", 700, "ch 0+200 to 0+500", "2026-09-15")             # cumulative 1100 > 1000 BOQ (10% over)
    m = S.measure(T, "culvert", "rcc", 30, "abutment", "2026-09-20")
    assert m["cumulative"] == 30
    b2 = S.ra_bill(T, "culvert", "2026-09-30")
    l1 = next(x for x in b2["bill"]["lines"] if x["code"] == "1")
    assert b2["number"] == 2 and l1["prev_qty"] == 400 and l1["this_qty"] == 700 and l1["upto_qty"] == 1100
    assert any("deviation" in f for f in b2["bill"]["flags"])
    rerun = S.ra_bill(T, "culvert", "2026-09-30")                                        # a draft is rebuilt, not doubled
    assert rerun["number"] == 2
    S.bill_status(T, b1["bill_id"], "passed", d["net"] - 5000)
    assert "kam" in S.bill_status(T, b1["bill_id"], "passed", d["net"] - 5000)["say"]
    paid = S.bill_status(T, b1["bill_id"], "paid")
    assert "26AS" in paid["say"] and "GSTR-7A" in paid["say"]
    pv = S.project_view(T, "culvert")
    assert pv["retention_held"] == ded["retention"] and pv["progress_pct"] > 0 and pv["delay"]["time_pct"] > 0
    rc = S.receivables(T)
    assert rc["retention"] and rc["bills"] == []
    S.bill_status(T, rerun["bill_id"], "submitted")
    assert S.receivables(T)["bills"][0]["bill"] == 2
    # extra item
    S.boq(T, "culvert", [{"code": "EI-1", "description": "Gabion wall", "unit": "cum", "rate": 3200}], extra=True)
    assert "extra item" in S.measure(T, "culvert", "EI-1", 12)["flag"]["text"]
    fb = S.ra_bill(T, "culvert", final=True)
    assert fb["bill"]["deductions"]["mobilisation_recovery"] > 0 and fb["file"]["name"] == "Final-Bill-3.pdf"
    S.bill_status(T, fb["bill_id"], "submitted")
    with pytest.raises(S.ThekaError):
        S.ra_bill(T, "culvert")


def test_subs_material_diary(tk):
    S = tk
    setup(S)
    S.save_sub(T, "Raju Shuttering", "9811111111", individual=True, retention_pct=5)
    a = S.sub_bill(T, "Raju", 25000, "culvert", "2026-10-01")
    assert a["tds"]["tds"] == 0 and a["net"] == 23750
    b = S.sub_bill(T, "Raju", 80000, "culvert", "2026-10-15")
    assert b["tds"]["tds"] == 1050.0                                                     # crosses 1 lakh: 1% on 1.05 lakh
    S.material(T, "culvert", "cement bag", 500, 380)
    m = S.material(T, "culvert", "cement bag", 120, used=True)
    assert m["balance"] == 380 and S.stock(T, "culvert")[0]["used"] == 120
    S.diary(T, "culvert", 18, "PCC raft poured", day="2026-10-20")
    S.diary(T, "culvert", 5, hindrance="Drawing for wing wall not given by department", lost_hours=8, by_client=True, day="2026-10-21")
    S.diary(T, "culvert", 0, hindrance="Heavy rain", lost_hours=4, by_client=True, day="2026-10-22")
    e = S.eot_letter(T, "culvert")
    assert e["days"] == 1.5 and "Drawing for wing wall" in e["text"] and "2026-12-31" in e["text"]
    dd = S.day(T)
    assert "BG" in dd["say"] and "registration" in dd["say"]
    assert S.register_file(T)["file"]["name"].endswith(".xlsx")
    assert S.send_morning(T)["text"].startswith("Theka:")


def test_tools_api(tk):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("theka") == "contract_work" and roles.kind_of("theka_dekho") == "read" and "theka" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["contractor"]["role"] == "site_manager"
    S = tk
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("theka", action="measure", project="culvert", item="2", qty=20, day="2026-10-01")
    b = run("theka", action="ra_bill", project="culvert")
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["theka"](staff, action="bill_status", bill_id=b["bill_id"], status="submitted"))
    assert run("theka_dekho", what="boq", project="culvert")["items"][1]["done"] == 20
    with TestClient(main.app) as cl:
        assert "theka" in cl.get("/healthz").json()["features"]
        d = cl.get("/api/theka/day").json()
        pid = d["projects"][0]["id"]
        assert cl.post(f"/api/theka/bills/{b['bill_id']}", json={"status": "submitted"}).status_code == 200
        assert cl.post(f"/api/theka/projects/{pid}/measure", json={"item": "1", "qty": 50}).json()["cumulative"] == 50
        up = cl.post(f"/api/theka/projects/{pid}/boq", files={"file": ("b.csv", b"Description,Qty,Rate\nPlaster,500,320\n", "text/csv")})
        assert up.status_code == 200 and up.json()["items"] == 1, up.text
        assert len(cl.get(f"/api/theka/projects/{pid}").json()["boq"]) == 4
        clash = cl.post(f"/api/theka/projects/{pid}/boq", files={"file": ("b.csv", b"Item No,Description,Qty,Rate\n1,Painting,10,90\n", "text/csv")})
        assert clash.status_code == 400 and "naap pehle se" in clash.text
        assert cl.post(f"/api/theka/projects/{pid}/bogus", json={}).status_code == 404
        assert cl.post("/api/theka/tenders", json={"name": "Hall repair", "last_date": "2026-11-05"}).status_code == 200
        assert cl.post("/api/theka/sub_bills", json={"sub": "Nobody", "amount": 100}).status_code == 400
        assert cl.post("/api/theka/register", json={}).status_code == 200
