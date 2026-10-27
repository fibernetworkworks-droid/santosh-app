"""Customs Sahayak (import & customs desk): rules (HS format, regulators, documents, assessable value, duty from her rates, BE
deadline, demurrage / detention), shipments + lines, HS suggestion with learning, documents, landed cost, clearance timeline,
filing card decided ONLY by her tap (hash, stale after a change), tools (owner / staff / customer actors), API, worker tick."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.customs.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def cu(env, monkeypatch):
    from app.customs import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_model", lambda system, text: "")
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules():
    from app.customs import rules as R
    assert R.hs_ok("8518 22 00") and not R.hs_ok("851822") and R.hs_fmt("85182200") == "8518.22.00"
    chk = R.hs_check("85182200", "Bluetooth speaker with lithium battery")
    ids = {r["id"] for r in chk["regulators"]}
    assert {"bis", "wpc", "epr_ewaste", "epr_battery"} <= ids and chk["ok_format"] and chk["notes"]
    assert "DGFT" in chk["policy"]
    food = {r["id"] for r in R.regulators("08041020", "dates retail pack")}
    assert {"fssai", "plant_q", "legal_metrology", "epr_plastic"} <= food
    assert {r["id"] for r in R.regulators("88062100", "")} >= {"dgca"}
    assert not R.hs_check("8518")["ok_format"] and R.hs_check("8518")["problems"]
    # documents by mode / terms / FTA
    d = {x["key"]: x for x in R.docs_for("sea", "FOB", True, R.regulators("85182200", "speaker"))}
    assert {"invoice", "packing", "transport", "iec", "freight", "insurance", "coo", "form1", "reg_bis", "idpms"} <= set(d)
    assert "Bill of Lading" in d["transport"]["label"] and d["coo"]["required"]
    assert "Air Waybill" in {x["key"]: x for x in R.docs_for("air", "CIF", False, [])}["transport"]["label"]
    # assessable value (rule 10(2)): FOB invoice without freight / insurance -> 20% + 1.125%
    av = R.assessable(10000, "FOB", 0, 0, "sea", 88.0)
    assert av["fob"] == 10000 and av["freight"] == 2000 and av["insurance"] == 112.5 and av["cif"] == 12112.5
    assert av["av_inr"] == round(12112.5 * 88, 2) and av["freight_rule"] and av["insurance_rule"]
    cif = R.assessable(12000, "CIF", 1500, 60, "sea", 0)
    assert cif["fob"] == 10440 and cif["cif"] == 12000 and cif["av_inr"] is None
    air = R.assessable(10000, "FOB", 3000, 50, "air", 1)
    assert air["freight"] == 2000                       # air freight capped at 20% of FOB
    # duty only from her rates; SWS 10% of BCD by default; IGST on AV + BCD + SWS
    dl = R.duty_line(100000, 10, None, 18)
    assert dl["bcd"] == 10000 and dl["sws"] == 1000 and dl["igst"] == round(111000 * 0.18, 2) and dl["complete"]
    assert R.duty_line(100000, None, None, None)["missing"] == ["BCD", "IGST"]
    assert R.duty_line(100000, 10, 0, 18)["sws"] == 0          # SWS-exempt goods: she puts 0
    # BE deadline: end of the day before arrival; neighbours the arrival day
    assert R.be_due(date(2026, 11, 5))["due"] == date(2026, 11, 4)
    assert R.be_due(date(2026, 11, 5), "BD")["due"] == date(2026, 11, 5)
    assert R.be_due(None)["due"] is None
    c = R.free_clock(date(2026, 11, 1), 5, date(2026, 11, 8), 2500.0)
    assert c["last_free_day"] == date(2026, 11, 5) and c["over_days"] == 3 and c["amount"] == 7500 and c["level"] == "bad"
    assert R.free_clock(date(2026, 11, 1), 5, date(2026, 11, 4))["level"] == "warn"
    assert R.free_clock(date(2026, 11, 1), None, date(2026, 11, 4)) is None
    assert R.fallback_hs("Bluetooth speaker")[0]["heading"] == "8518"


def test_shipment_hs_docs_cost(cu):
    S = cu
    S.save_settings(T, firm="Ingle Imports", iec="ABCDE1234F", gstin="27ABCDE1234F1Z5", cha_name="Shree CHA", cha_phone="98220 12345")
    with pytest.raises(S.CustomsError):
        S.save_settings(T, iec="123")
    out = S.new_shipment(T, supplier="Shenzhen Sound Co", supplier_country="china", incoterm="FOB", place="Shenzhen", currency="USD",
                         invoice_value=6000, mode="sea", port="Nhava Sheva", bl_no="MSKU1234567",
                         lines=[{"desc": "Bluetooth speaker 10W with lithium battery, retail box", "qty": 500, "unit": "pcs", "value": 6000}])
    v = out["shipment"]
    assert v["number"] == "I-0001" and v["origin"] == "CN" and v["supplier_country"] == "CN" and len(v["lines"]) == 1
    assert "customs_shipment" in kinds(S) and "HS" in v["next"]
    # HS: no model -> heading table, never final
    sg = S.hs_suggest(T, "Bluetooth speaker 10W")
    assert sg["candidates"][0]["heading"] == "8518" and "andaaza" in sg["say"]
    # model suggestion validated (only 8 digits kept)
    S._model = lambda system, text: '{"candidates": [{"hs": "8518 22 00", "title": "Multiple loudspeakers", "why": "GIR 1"}, {"hs": "8518"}]}'
    sg = S.hs_suggest(T, "Bluetooth speaker 10W")
    assert [c["hs"] for c in sg["candidates"]] == ["85182200"] and sg["candidates"][0]["source"] == "model"
    S._model = lambda system, text: ""
    # filing card refused while the code is a guess / docs missing
    r = S.request_filing(T, "I-0001")
    assert r["status"] == "not_ready" and any("HS" in b for b in r["blockers"])
    hc = S.hs_confirm(T, "1", 1, "85182200")
    assert hc["shipment"]["lines"][0]["hs_confirmed"] and {"bis", "wpc"} <= {x["id"] for x in hc["check"]["regulators"]}
    # learned: same description next time comes first
    sg = S.hs_suggest(T, "Bluetooth speaker 10W with lithium battery, retail box")
    assert sg["candidates"][0]["source"] == "aapka" and sg["candidates"][0]["hs"] == "85182200"
    with pytest.raises(S.CustomsError):
        S.hs_confirm(T, "I-0001", 1, "8518")
    v = S.shipment_view(T, "I-0001")
    keys = {d["key"] for d in v["docs"]}
    assert {"reg_bis", "reg_wpc", "reg_epr_battery", "reg_legal_metrology", "freight", "insurance"} <= keys
    assert v["docs_missing"] > 0
    # cost: no fx -> asks; rates missing -> says so; with her rates -> numbers
    c = S.cost(T, "I-0001")
    assert c["landed_cost"] is None and "Exchange rate" in c["say"]
    S.update_shipment(T, "I-0001", fx=88.5)
    c = S.cost(T, "I-0001")
    assert not c["complete"] and "rate chahiye" in c["say"] and c["missing"]
    S.set_lines(T, "I-0001", [{"no": 1, "bcd": 20, "igst": 18}])
    c = S.cost(T, "I-0001")
    av = round((6000 + 1200 + 67.5) * 88.5, 2)
    assert c["complete"] and abs(c["totals"]["av"] - av) < 0.05
    assert abs(c["totals"]["bcd"] - av * 0.2) < 0.05 and abs(c["totals"]["sws"] - av * 0.02) < 0.05
    assert c["landed_cost"] == round(c["totals"]["av"] + c["totals"]["cost_duty"], 2) and "andaaza" in c["say"]
    # documents
    for d in v["docs"]:
        if d["required"]:
            S.mark_doc(T, "I-0001", d["key"], "have")
    with pytest.raises(S.CustomsError):
        S.mark_doc(T, "I-0001", "nonsense-xyz", "have")
    assert S.shipment_view(T, "I-0001")["docs_missing"] == 0
    # card numbers in notes are masked
    S.update_shipment(T, "I-0001", notes="card 4111 1111 1111 1111 mat likho")
    assert "4111" not in S.shipment_view(T, "I-0001")["notes"]


def _ready(S):
    S.save_settings(T, firm="Ingle Imports", iec="ABCDE1234F", cha_name="Shree CHA", cha_phone="9822012345", cha_email="cha@example.com")
    S.new_shipment(T, supplier="Al Noor", supplier_country="AE", incoterm="CIF", currency="USD", invoice_value=2000, freight=150, insurance=10,
                   mode="air", port="Mumbai Air Cargo", bl_no="176-12345675", fta=True,
                   lines=[{"desc": "Industrial valve brass", "qty": 40, "unit": "nos", "value": 2000, "hs": "84818090"}])
    S.hs_confirm(T, "I-0001", 1, "84818090")
    for d in S.shipment_view(T, "I-0001")["docs"]:
        if d["required"]:
            S.mark_doc(T, "I-0001", d["key"], "have")


def test_filing_only_on_her_tap(cu, monkeypatch):
    S = cu
    _ready(S)
    from app import chatfiles
    monkeypatch.setattr(chatfiles, "store", lambda tenant, name, data, ct="": {"file_id": "f1", "name": name, "size": len(data)})
    r = S.request_filing(T, "I-0001", conv="c1")
    assert r["status"] == "card_sent", r
    f = r["filing"]
    assert f["status"] == "waiting" and f["number"] == "F-0001" and len(f["hash"]) == 64
    assert "customs_filing" in kinds(S) and "haan" in r["say"].lower() and "file nahi karta" in r["say"]
    assert S.request_filing(T, "I-0001")["filing"]["id"] == f["id"]          # same data = same card
    with pytest.raises(S.CustomsError):
        S.decide_filing(T, f["id"], True, f["hash"])                          # not a tap
    with pytest.raises(S.CustomsError):
        S.decide_filing(T, f["id"], True, "0" * 64, by_tap=True)              # wrong hash
    # a change after the card makes it stale
    S.update_shipment(T, "I-0001", invoice_value=2100)
    assert S.filings(T)[0]["status"] == "stale"
    r = S.request_filing(T, "I-0001")
    f2 = r["filing"]
    assert f2["number"] == "F-0002" and f2["hash"] != f["hash"]
    out = S.decide_filing(T, f2["id"], True, f2["hash"], by_tap=True)
    assert out["filing"]["status"] == "approved" and out["file"]["file_id"] == "f1"
    assert out["drafts"]["whatsapp"].startswith("https://wa.me/919822012345") and out["drafts"]["email"].startswith("mailto:cha@example.com")
    assert out["icegate_steps"] and any("AAP" in s for s in out["icegate_steps"])
    again = S.decide_filing(T, f2["id"], False, f2["hash"], by_tap=True)
    assert again["filing"]["status"] == "approved"                            # decided once
    # after BE is filed no new card
    S.update_stage(T, "I-0001", "be_filed", "2026-11-03", be_no="7654321")
    with pytest.raises(S.CustomsError):
        S.request_filing(T, "I-0001")


def test_timeline_clocks_and_tick(cu):
    S = cu
    _ready(S)
    on = S.today(T)
    arr = on - timedelta(days=6)
    S.update_shipment(T, "I-0001", mode="sea", free_days=5, demurrage_per_day=3000, detention_free_days=14, eta=(on + timedelta(days=1)).isoformat())
    v = S.shipment_view(T, "I-0001")
    assert v["clock"]["be_due"] == on.isoformat() and any(a["key"] == "be_due" for a in v["clock"]["alerts"])
    S.update_stage(T, "I-0001", "shipped", (on - timedelta(days=20)).isoformat())
    out = S.update_stage(T, "I-0001", "arrived", arr.isoformat(), note="CHA bola", by="Shree CHA")
    v = out["shipment"]
    assert v["stage"] == "arrived" and v["status"] == "active" and v["clock"]["be_days_left"] < 0
    dem = v["clock"]["demurrage"]
    assert dem["over_days"] == 2 and dem["amount"] == 6000 and any(a["key"] == "dem_on" for a in v["clock"]["alerts"])
    assert v["clock"]["detention"]["level"] == "ok"
    with pytest.raises(S.CustomsError):
        S.update_stage(T, "I-0001", "teleported")
    # an older stage after a newer one does not move the stage back
    S.update_stage(T, "I-0001", "assessed")
    S.update_stage(T, "I-0001", "igm", igm_no="2345678")
    v = S.shipment_view(T, "I-0001")
    assert v["stage"] == "assessed" and v["igm_no"] == "2345678" and [x["stage"] for x in v["timeline"]][:3] == ["shipped", "arrived", "igm"]
    assert any(a["key"] == "duty" for a in v["clock"]["alerts"])
    S.update_stage(T, "I-0001", "duty_paid", amount=45000)
    S.update_stage(T, "I-0001", "ooc")
    v = S.update_stage(T, "I-0001", "delivered", on.isoformat())["shipment"]
    assert v["duty_paid"] == 45000 and v["clock"]["demurrage"]["stopped"] and v["status"] == "active"   # sea: waits for empty return
    # tick: alerts once, morning note once
    S.EVENTS.clear()
    n = datetime.now(timezone.utc)
    r1 = S.tick(n)
    r2 = S.tick(n + timedelta(minutes=1))
    assert r2["alerts"] == 0 and r1["morning"] <= 1 and r2["morning"] == 0
    S.update_stage(T, "I-0001", "empty_returned", on.isoformat())
    assert S.shipment_view(T, "I-0001")["status"] == "done"


def test_tools_actors_and_api(cu):
    from app.agent import customs_tools as CT
    from app.agent.tools import Ctx, ToolError
    from app.customs.api import make_router
    S = cu
    ctx = conv_ctx()
    run = asyncio.run
    out = run(CT.customs(ctx, "new", supplier="Ningbo Toys", origin="CN", invoice_value=3000, currency="USD", mode="sea",
                         lines=[{"desc": "plastic toy car retail pack", "qty": 1000, "value": 3000}]))
    num = out["shipment"]["number"]
    assert {"reg_bis", "reg_legal_metrology"} <= {d["key"] for d in out["shipment"]["docs"]}
    sg = run(CT.customs(ctx, "hs", desc="plastic toy car"))
    assert sg["candidates"][0]["heading"] == "9503"
    chk = run(CT.customs_dekho(ctx, "hs_check", hs="95030090", desc="toy"))
    assert any(r["id"] == "bis" for r in chk["regulators"])
    assert run(CT.customs(ctx, "filing", shipment=num))["status"] == "not_ready"
    # no approve action exists in the tool
    assert "approve" not in CT.CUSTOMS_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    staff = Ctx(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    run(CT.customs(staff, "stage", shipment=num, stage="shipped"))
    with pytest.raises(ToolError):
        run(CT.customs(staff, "settings", iec="ABCDE1234F"))
    with pytest.raises(ToolError):
        run(CT.customs(staff, "cancel", shipment=num))
    with pytest.raises(ToolError):
        run(CT.customs(Ctx(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1"), "new", supplier="x"))
    assert run(CT.customs_dekho(ctx, "day"))["open"]
    assert run(CT.customs_dekho(ctx, "rules"))["never"]
    assert set(CT.CUSTOMS_HANDLERS) == {t["name"] for t in CT.CUSTOMS_TOOLS} == set(CT.CUSTOMS_LABELS)
    # API
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/customs").json()["shipments"]
    r = c.put("/api/customs/settings", json={"firm": "Ingle", "iec": "ABCDE1234F"})
    assert r.status_code == 200 and r.json()["iec_ok"]
    assert c.put("/api/customs/settings", json={"iec": "bad"}).status_code == 400
    r = c.post("/api/customs/shipments", json={"supplier": "Hamburg GmbH", "origin": "DE", "invoice_value": 900, "mode": "courier"})
    sid = r.json()["shipment"]["id"]
    assert c.post(f"/api/customs/shipments/{sid}/lines", json={"desc": "spare valve", "qty": 2, "value": 900, "hs": "84819090"}).status_code == 200
    assert c.post(f"/api/customs/shipments/{sid}/hs", json={"line": 1, "hs": "84819090"}).json()["shipment"]["lines"][0]["hs_confirmed"]
    assert c.post(f"/api/customs/shipments/{sid}/stage", json={"stage": "nope"}).status_code == 400
    assert c.get(f"/api/customs/shipments/{sid}/cost").status_code == 200
    assert c.post("/api/customs/hs/suggest", json={"desc": "mobile phone"}).json()["candidates"][0]["heading"] == "8517"
    assert c.post("/api/customs/filings/nope/decide", json={"yes": True, "hash": "x"}).status_code == 400
    assert c.get("/api/customs/icegate_steps").json()["steps"]
