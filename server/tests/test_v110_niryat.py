"""v0.110 Niryat Sahayak: buyer book, PI with Incoterm / FOB / checks (sanctions, FTA, CBAM, US duty, HS digits, LUT),
PI to the buyer and the commercial invoice only on her Haan, invoice + packing list PDFs, shipping bill -> RBI 9-month
(12 for INR) date + RoDTEP estimate, payments realise, reminders, register, day note, tools + API."""
import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 22)


@pytest.fixture
def nir(env, monkeypatch):
    from app.niryat import service as S
    monkeypatch.setattr(S, "today", lambda t: DAY)
    return S


def setup(S):
    S.save_settings(T, firm="Ingle Exports", address="Akola, Maharashtra", iec="ABCDE1234F", ad_bank="SBI Akola, AD code 0001234",
                    lut_no="AD270926000123X", rcmc="Spices Board RCMC 1234", rcmc_valid_to="2026-11-10", prefix="IE")
    S.save_buyer(T, "Al Noor Trading", country="UAE", currency="USD", pay_terms="advance", email="buy@alnoor.ae")
    S.save_buyer(T, "Rhein Stahl GmbH", country="Germany", currency="EUR", pay_terms="da", credit_days=60)


LINES = [{"item": "Turmeric powder", "hs": "09103030", "qty": 2000, "unit": "KGS", "rate": 2.10, "net_kg": 2000, "gross_kg": 2080,
          "packages": 80, "rodtep_pct": 1.0}]


def test_rules():
    from app.niryat import rules as R
    assert R.iec_ok("abcde1234f") and not R.iec_ok("123")
    assert R.country("Dubai") == "AE" and R.country("gb") == "GB" and R.country("Atlantis") == ""
    assert R.realise_by(date(2026, 10, 22), "USD") == date(2027, 7, 22) and R.realise_by(date(2026, 1, 31), "INR") == date(2027, 1, 31)
    assert R.fob_value(10000, "CIF", 500, 20) == 9480 and R.fob_value(10000, "CFR", 500) == 9500 and R.fob_value(10000, "FOB") == 10000
    assert R.rodtep(100000, 1.0)["amount"] == 1000 and R.rodtep(100000, 1.0, 0.2, 2000)["amount"] == 400
    assert R.rodtep(100000, 1.0, on=date(2027, 1, 5))["amount"] == 0
    ck = R.checks("RU", ["72081000"], "FOB", "advance", "USD")
    assert ck[0]["level"] == "stop"
    ck = R.checks("DE", ["72081000", "0910"], "DDP", "open", "EUR")
    texts = " ".join(c["text"] for c in ck)
    assert "CBAM" in texts and "8 ank" in texts and "DDP" in texts and "ECGC" in texts
    assert any("CETA" in c["text"] for c in R.checks("GB", ["09103030"], "FOB", "advance", "GBP"))
    assert "Insurance certificate" in R.doc_list("CIF", "lc", True)


def test_flow(nir):
    S = nir
    setup(S)
    r = S.proforma(T, "Al Noor", LINES, incoterm="FOB", place="Mundra", fx=88.5, port_loading="Mundra", port_discharge="Jebel Ali")
    v = r["shipment"]
    assert v["number"] == "IE/PI2627/001" and v["total"] == 4200 and v["fob"] == 4200 and v["fob_inr"] == 4200 * 88.5
    assert any("CEPA" in c["text"] for c in v["checks"]) and r["file"]["name"].endswith(".pdf") and "haan" in r["say"]
    d = S.pi_draft(T, v["id"])
    assert d["to"] == "buy@alnoor.ae" and "IE/PI2627/001" in d["text"]
    S.receive(T, v["id"], 1000, 82000, ref="IRM1")                         # advance before shipment
    c = S.confirm(T, v["id"])
    assert c["shipment"]["number"] == "IE/2627/001" and len(c["files"]) == 2 and "Certificate of origin (DGFT eCoO, FTA wala)" in c["docs"]
    with pytest.raises(S.NiryatError):
        S.confirm(T, v["id"])
    sh = S.shipped(T, v["id"], "1234567", "2026-10-20", "MAEU123", fx=88.9)
    x = sh["shipment"]
    assert x["realise_by"] == "2027-07-20" and x["rodtep"]["estimate"] == round(4200 * 88.9 * 0.01, 2) and "LUT" in sh["say"]
    rl = S.realisation(T)
    assert rl["shipments"][0]["outstanding"] == 3200 and rl["drafts"] and "3,200.00" in rl["drafts"][0]["text"]
    done = S.receive(T, v["id"], 3200, 284000, ref="EBRC9")
    assert done["shipment"]["status"] == "realised" and "e-BRC" in done["say"]
    assert S.realisation(T)["shipments"] == []
    # CIF to Germany, steel: CBAM + FOB less freight / insurance
    g = S.proforma(T, "Rhein", [{"item": "HR coil", "hs": "72081000", "qty": 20, "unit": "MTS", "rate": 650}], incoterm="CIF",
                   place="Hamburg", freight=900, fx=95)["shipment"]
    assert g["currency"] == "EUR" and g["insurance"] > 0 and g["fob"] == round(g["total"] - 900 - g["insurance"], 2)
    assert any("CBAM" in c["text"] for c in g["checks"]) and any("ECGC" in c["text"] for c in g["checks"])
    with pytest.raises(S.NiryatError):
        S.proforma(T, "Rhein", LINES, incoterm="CIF")                       # freight needed
    with pytest.raises(S.NiryatError):
        S.proforma(T, "Rhein", [{"item": "x", "qty": 1}])                   # rate needed
    S.save_buyer(T, "Moscow Imports", country="RU", currency="USD")
    ru = S.proforma(T, "Moscow", LINES)["shipment"]
    with pytest.raises(S.NiryatError):
        S.confirm(T, ru["id"])
    S.cancel(T, ru["id"])
    day = S.day(T)
    assert any("RCMC" in p for p in day["parts"]) and any("PI" in p for p in day["parts"])
    assert S.register_file(T)["file"]["name"].endswith(".xlsx")
    assert S.send_morning(T)["text"].startswith("Niryat:")


def test_lut_and_settings(nir):
    S = nir
    with pytest.raises(S.NiryatError):
        S.save_settings(T, iec="12")
    S.save_settings(T, firm="X", iec="ABCDE1234F")
    assert S.settings(T)["lut_ok"] is False
    S.save_buyer(T, "Sydney Spice", country="AU", currency="AUD")
    p = S.proforma(T, "Sydney", LINES)
    assert any("LUT" in c["text"] for c in p["shipment"]["checks"]) and any("ECTA" in c["text"] for c in p["shipment"]["checks"])
    with pytest.raises(S.NiryatError):
        S.save_buyer(T, "Nowhere Ltd", country="Atlantis")
    with pytest.raises(S.NiryatError):
        S.save_buyer(T, "Odd", country="US", currency="XYZ")


def test_tools_api(nir):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    assert roles.duty_of("niryat") == "export_work" and roles.kind_of("niryat_dekho") == "read" and "niryat" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["exporter"]["role"] == "export_assistant"
    S = nir
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    v = run("niryat", action="pi", buyer="Al Noor", text="Turmeric powder 1000 kg @ 2.2 HS 09103030", fx=88)["shipment"]
    assert v["lines"][0]["hs"] == "09103030" and v["total"] == 2200
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["niryat"](staff, action="confirm", shipment=v["id"]))
    assert run("niryat_dekho", what="incoterms")["incoterms"]["FOB"]
    with TestClient(main.app) as cl:
        assert "niryat" in cl.get("/healthz").json()["features"]
        assert cl.get("/api/niryat/day").json()["settings"]["iec"] == "ABCDE1234F"
        assert cl.post(f"/api/niryat/shipments/{v['id']}/confirm", json={}).json()["shipment"]["status"] == "confirmed"
        assert cl.post(f"/api/niryat/shipments/{v['id']}/shipped", json={"sb_no": "7654321"}).json()["shipment"]["realise_by"] == "2027-07-22"
        assert cl.post(f"/api/niryat/shipments/{v['id']}/receive", json={"amount": 2200}).json()["shipment"]["status"] == "realised"
        assert cl.get("/api/niryat/buyers").json()["buyers"]
        assert cl.post("/api/niryat/shipments", json={"buyer": "Nobody", "text": "x 1 kg @ 1"}).status_code == 400
        assert cl.post(f"/api/niryat/shipments/{v['id']}/bogus", json={}).status_code == 404
        assert cl.get("/api/niryat/realisation").status_code == 200
        assert cl.post("/api/niryat/register", json={}).status_code == 200
