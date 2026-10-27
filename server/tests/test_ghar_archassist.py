"""Archassist Sahayak (architect's assistant): starter rule tables + area statement / zoning checks from her numbers, project file
with title papers, NOC triggers, drawing register + revisions, transmittals / submissions / invoices that ONLY her tap decides
(fingerprint for invoices once a phone key is active), consultants, RFIs, minutes, fee stages with GST + TDS, reminders, tools, API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.archassist.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
DAY = date(2026, 10, 23)
GSTIN_MH = "27AAPFU0939F1ZV"


@pytest.fixture
def ar(env, monkeypatch):
    from app.archassist import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "today", lambda t: DAY)
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def base(S):
    S.save_settings(T, firm="Ingle Architects", architect="Ar. Meghana Ingle", coa_no="CA/2015/12345", gstin=GSTIN_MH,
                    upi_id="ingle@okaxis", phone="9876543210")
    p = S.save_project(T, "Patil bungalow", client="Ramesh Patil", client_phone="98765 43211", site="Plot 12, Akot", pin="444101",
                       city="Akot", area="1000", road_width_m=12, survey_no="45/2")
    return p


def test_rules():
    from app.archassist import rules as R
    assert R.area_sqm("2,400 sqft") == pytest.approx(222.967, rel=1e-3) and R.area_sqm("5 guntha") == pytest.approx(505.85)
    assert R.area_sqm(450) == 450 and R.area_sqm("") is None
    rs = R.ruleset("udcpr")
    st = R.area_statement({"area_sqm": 1000, "road_width_m": 12}, {"bua_sqm": 2000, "height_m": 24, "front_m": 4.5, "side_m": 4.0}, rs)
    lay = st["statement"]
    assert lay["basic_area"] == 1100 and lay["premium_area"] == 500 and lay["tdr_area"] == 650 and lay["max_area"] == 2250
    by = {c["item"]: c for c in st["checks"]}
    assert by["FSI"]["status"] == "warn" and "TDR" in by["FSI"]["note"]
    assert by["Front margin"]["status"] == "ok" and by["Front margin"]["need"] == 4.5
    assert by["Side margin"]["status"] == "fail" and by["Side margin"]["need"] == 4.8          # H/5 for a 24 m building
    assert by["High-rise"]["status"] == "warn" and R.CHECK_LINE in st["say"]
    over = R.area_statement({"area_sqm": 1000, "road_width_m": 12}, {"bua_sqm": 2400}, rs)
    assert not over["ok"] and [c for c in over["checks"] if c["item"] == "FSI"][0]["status"] == "fail"
    # her own numbers override the starter table; unknown premium in the island table is asked, never guessed
    mine = R.area_statement({"area_sqm": 1000, "road_width_m": 12}, {"bua_sqm": 1000}, R.ruleset("udcpr", {"basic": 0.9}))
    assert mine["statement"]["basic_fsi"] == 0.9 and mine["statement"]["basic_area"] == 900
    isl = R.area_statement({"area_sqm": 500, "road_width_m": 15}, {"bua_sqm": 600}, R.ruleset("dcpr_island"))
    assert isl["statement"]["premium_fsi"] is None and any(c["item"] == "Premium / TDR" for c in isl["checks"])
    assert not R.area_statement({}, {}, rs)["ok"]
    # big plot: open space + amenity; parking only from her rule
    big = R.area_statement({"area_sqm": 25000, "road_width_m": 30}, {"bua_sqm": 40000, "units": 100, "parking": 80},
                           R.ruleset("udcpr", {"parking_per_unit": 1}))
    items = {c["item"]: c for c in big["checks"]}
    assert items["Open space"]["need"] == 2500 and items["Amenity space"]["need"] == 1250 and items["Parking"]["status"] == "fail"
    n = {x["key"] for x in R.nocs({"near_airport": True, "trees": True}, 24, 25000)}
    assert {"noc_fire", "noc_airport", "noc_tree", "noc_env", "structural"} <= n
    assert "noc_env" not in {x["key"] for x in R.nocs({}, 10, 5000)}
    g = R.gst_split(100000, GSTIN_MH, "29AAPFU0939F1ZX")
    assert g["igst"] == 18000 and g["total"] == 118000
    g2 = R.gst_split(100000, GSTIN_MH)
    assert g2["cgst"] == 9000 and g2["sgst"] == 9000
    assert not R.gst_split(100000, "")["gst"]
    assert R.tds_expected(0, 40000)["tds"] == 0 and R.tds_expected(30000, 40000)["tds"] == 7000 and R.tds_expected(60000, 40000)["tds"] == 4000
    assert R.next_rev("R0") == "R1" and R.next_rev("P3") == "P4" and R.next_rev("A") == "B" and R.next_rev("") == "R0"
    assert R.fy_of(DAY) == "2627" and R.fy_of(date(2026, 3, 1)) == "2526"
    assert R.stage_amount({"basis": "percent", "percent": 5, "project_cost": 2e7}, 20) == 200000
    assert R.stage_amount({"basis": "percent"}, 20) is None


def test_project_papers_area(ar):
    S = ar
    p = base(S)
    assert p["number"] == "P-001" and p["plot"]["area_sqm"] == 1000 and p["client_phone"] == "9876543211"
    assert "Title search" in " ".join(p["docs_missing"])
    with pytest.raises(S.ArchError):
        S.save_project(T, ref="P-001", pin="000000")
    with pytest.raises(S.ArchError):
        S.save_project(T, ref="P-001", client_gstin="27AAPFU0939F1ZA")
    with pytest.raises(S.ArchError):
        S.save_project(T, ref="P-001", client_pan_ref="ABCDE1234F")           # PAN only by locker reference
    assert S.save_project(T, ref="Patil", client_pan_ref="{id:abc123}")["client_pan_ref"] == "{id:abc123}"
    d = S.doc(T, "P-001", "7/12", "have")
    assert next(x for x in d["docs"] if x["key"] == "seven_twelve")["state"] == "have"
    S.save_project(T, ref="P-001", near_airport=True)
    r = S.area_check(T, "P-001", {"bua_sqm": 2000, "height_m": 24, "front_m": 4.5, "side_m": 5, "rear_m": 5, "units": 8, "parking": 8})
    assert r["statement"]["max_area"] == 2250 and "archassist_area" in kinds(S)
    ap = {x["key"]: x for x in S.approvals(T, "P-001")["items"]}
    assert ap["noc_fire"]["status"] == "needed" and ap["noc_airport"]["status"] == "needed" and "AAI" in ap["noc_airport"]["why"]
    assert any(c["item"] == "Parking" and c["status"] == "check" for c in r["checks"])     # no invented parking norm
    S.approval_set(T, "P-001", "noc_airport", "granted", "NOCAS/123", "2026-10-01", "2033-10-01")
    assert S.save_project(T, ref="P-001", rera_no="P50500012345")["rera_no"] == "P50500012345"
    assert S.project_view(T, "patil")["number"] == "P-001"


def test_drawings_and_transmittal(ar):
    S = ar
    base(S)
    from app import chatfiles
    fid = chatfiles.store(T, "A-101.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")["file_id"]
    d = S.drawing(T, "P-001", "a-101", "Ground floor plan", scale="1:100", file_id=fid)
    assert d["sheet"] == "A-101" and d["rev"] == "R0" and d["discipline"] == "A"
    S.drawing(T, "P-001", "S-01", "Footing layout", file_id=fid)
    with pytest.raises(S.ArchError):
        S.drawing(T, "P-001", "A-101", revise=True)                            # what changed?
    with pytest.raises(S.ArchError):
        S.drawing(T, "P-001", "bad sheet!")
    tr = S.transmittal_request(T, "P-001", "client", "Ramesh Patil", ["A-101", "S-01"], "for_approval", "9876543211")
    assert tr["status"] == "waiting" and "archassist_transmittal" in kinds(S) and "haan" in tr["say"]
    with pytest.raises(S.ArchError):
        S.decide_transmittal(T, tr["id"], True, tr["hash"])                    # tools can't issue
    with pytest.raises(S.ArchError):
        S.decide_transmittal(T, tr["id"], True, "wrong", by_tap=True)
    # a sheet revised after the card makes the card old
    tr2 = S.transmittal_request(T, "P-001", "client", "Ramesh Patil", ["A-101"])
    r = S.drawing(T, "P-001", "A-101", revise=True, note="Kitchen 30 cm badhaya", file_id=fid)
    assert r["rev"] == "R1" and len(r["revisions"]) == 2
    old = S.decide_transmittal(T, tr2["id"], True, tr2["hash"], by_tap=True)
    assert old["transmittal"]["status"] == "stale" and "file" not in old
    assert S.decide_transmittal(T, tr["id"], True, tr["hash"], by_tap=True)["transmittal"]["status"] == "stale"   # A-101 revised
    tr3 = S.transmittal_request(T, "P-001", "authority", "Akot Nagar Parishad", ["A-101"], "for_submission")
    out = S.decide_transmittal(T, tr3["id"], True, tr3["hash"], by_tap=True)
    assert out["file"]["name"].startswith("Transmittal_T-") and "wa.me/91" not in out["links"]["whatsapp"]     # no phone given
    assert "aap khud bhejiye" in out["say"]
    reg = {x["sheet"]: x for x in S.drawings(T, "P-001")}
    assert reg["A-101"]["issued"][0]["rev"] == "R1" and reg["A-101"]["issued"][0]["to"] == "Akot Nagar Parishad"
    assert S.decide_transmittal(T, tr3["id"], False, tr3["hash"], by_tap=True)["transmittal"]["status"] == "issued"   # decided once
    with pytest.raises(S.ArchError):
        S.transmittal_request(T, "P-001", "client", "Ramesh", ["Z-9"])
    c = S.rera_certificate.__wrapped__ if hasattr(S.rera_certificate, "__wrapped__") else S.rera_certificate
    with pytest.raises(S.ArchError):
        c(T, "P-001", "Wing A", 40)                                             # no RERA number yet
    S.save_project(T, ref="P-001", rera_no="P50500012345")
    rc = c(T, "P-001", "Wing A", 40)
    assert rc["sheet"].startswith("RERA-F1") and "tap" in rc["say"]
    with pytest.raises(S.ArchError):
        c(T, "P-001", "Wing A", 140)


def test_submission_gate(ar):
    S = ar
    S.save_project(T, "Shop block", area="600", road_width_m=9)
    sub = S.submission_request(T, "P-001", "building_permission")
    assert sub["blockers"] and any("CoA" in b for b in sub["blockers"]) and any("Area statement" in b for b in sub["blockers"])
    with pytest.raises(S.ArchError):
        S.decide_submission(T, sub["id"], True, sub["hash"], by_tap=True)       # blockers stay
    S.save_settings(T, coa_no="CA/2010/1111")
    for k in ("title", "property_card", "measurement", "zone", "deed"):
        S.doc(T, "P-001", k, "have")
    S.area_check(T, "P-001", {"bua_sqm": 900, "height_m": 10})
    S.drawing(T, "P-001", "A-001", "Site plan")
    with pytest.raises(S.ArchError):
        S.decide_submission(T, sub["id"], True, sub["hash"], by_tap=True)       # project changed after the card
    sub = S.submission_request(T, "P-001", "building_permission")
    assert not sub["blockers"]
    with pytest.raises(S.ArchError):
        S.decide_submission(T, sub["id"], True, sub["hash"])                    # no tap
    with pytest.raises(S.ArchError):
        S.submission_update(T, sub["id"], "submitted")                          # not approved yet
    ok = S.decide_submission(T, sub["id"], True, sub["hash"], by_tap=True)
    assert ok["status"] == "approved" and "login" in ok["say"]
    S.submission_update(T, sub["id"], "submitted", "BPMS/2026/778")
    S.submission_update(T, sub["id"], "granted", "BP/445", "2026-10-20", "2027-10-19")
    ap = {x["key"]: x for x in S.approvals(T, "P-001")["items"]}
    assert ap["building_permission"]["status"] == "granted" and ap["building_permission"]["ref"] == "BP/445"
    cc = S.submission_request(T, "P-001", "cc")
    assert not any("Building permission" in b for b in cc["blockers"])
    oc = S.submission_request(T, "P-001", "oc")
    assert any("Commencement" in b for b in oc["blockers"])


def test_fee_and_invoice(ar, monkeypatch):
    S = ar
    base(S)
    f = S.fee_set(T, "P-001", "percent", 5, 20000000)
    assert f["total"] == 1000000 and f["stages"][0]["amount"] == 100000 and "starter" in f["say"]
    with pytest.raises(S.ArchError):
        S.fee_set(T, "P-001", stages=[{"key": "a", "pct": 50}])
    inv = S.invoice_request(T, "P-001", "appointment")
    assert inv["amount"] == 100000 and inv["tax"]["cgst"] == 9000 and inv["total"] == 118000 and inv["tds"] == 10000
    assert inv["status"] == "waiting" and inv["number"] == "" and "archassist_invoice" in kinds(S)
    with pytest.raises(S.ArchError):
        S.invoice_request(T, "P-001", "appointment")                            # same stage twice
    with pytest.raises(S.ArchError):
        S.invoice_request(T, "P-001", "", None)                                 # no invented amount
    with pytest.raises(S.ArchError):
        S.decide_invoice(T, inv["id"], True, inv["hash"])
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.ArchError) as e:
        S.decide_invoice(T, inv["id"], True, inv["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.invoice_challenge(T, inv["id"])
    assert "|archassist|" in ch["message"] and ch["show"]["payee"] == "Ramesh Patil"
    with pytest.raises(S.ArchError):
        S.decide_invoice(T, inv["id"], True, inv["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "x", "signature": "AA=="},
                         by_tap=True)
    monkeypatch.setattr(S, "_verify_fingerprint", lambda *a, **k: None)
    out = S.decide_invoice(T, inv["id"], True, inv["hash"], by_tap=True)
    assert out["invoice"]["number"] == "AR/2627/001" and out["file"]["name"].endswith(".pdf")
    assert out["links"]["upi"].startswith("upi://pay?pa=ingle%40okaxis&am=118000.00") and "wa.me/919876543211" in out["links"]["whatsapp"]
    with pytest.raises(S.ArchError):
        S.invoice_paid(T, inv["id"])
    p = S.invoice_paid(T, inv["id"], 108000, 10000, ref="UTR 991")
    assert p["status"] == "paid" and p["tds_deducted"] == 10000
    i2 = S.invoice_request(T, "P-001", "concept")
    assert i2["tds"] == 20000
    assert S.decide_invoice(T, i2["id"], False, i2["hash"], by_tap=True)["invoice"]["status"] == "rejected"
    assert S.invoice_request(T, "P-001", "concept")["status"] == "waiting"      # stage free again after Mana
    extra = S.invoice_request(T, "P-001", "", 15000, "Extra site visit")
    assert extra["amount"] == 15000


def test_rfi_meeting_tick(ar, monkeypatch):
    S = ar
    base(S)
    S.consultant(T, "Er. Kulkarni", "structural", "9822012345", "k@ex.in", "Kulkarni Structurals")
    r = S.rfi(T, "P-001", "Footing depth", "Hard strata 1.2 m par mila, footing depth confirm karein?", "Kulkarni", ["S-01"], "2026-10-20")
    assert r["number"] == "RFI-001" and r["late"] and "wa.me/919822012345" in r["links"]["whatsapp"] and "email" in r["links"]
    m = S.meeting(T, "P-001", [{"point": "Elevation option B final", "by": "Client", "due": "2026-10-30"}, "Plumbing shaft size"],
                  ["Ramesh Patil", "Er. Kulkarni"])
    assert m["number"] == "M-001" and m["file"]["name"] == "MoM_M-001.docx" and "Elevation" in m["text"]
    with pytest.raises(S.ArchError):
        S.meeting(T, "P-001", [])
    S.approval_set(T, "P-001", "building_permission", "granted", "BP/1", "2025-11-01", "2026-11-10")
    S.save_settings(T, morning_time="09:00", coa_valid_to="2026-12-01")
    S.tr = S.transmittal_request(T, "P-001", "client", "Ramesh", [S.drawing(T, "P-001", "A-1", "Plan")["sheet"]])
    when = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)                    # 10:30 IST
    out = S.tick(when)
    alerts = [p["say"] for k, p in S.EVENTS if k == "archassist_alert"]
    assert any("RFI-001" in a for a in alerts) and any("BP" in a or "permission" in a for a in alerts) and out["morning"] == 1
    day = [p for k, p in S.EVENTS if k == "archassist_day"][0]
    assert "haan baaki" in day["say"] and "CoA" in day["say"]
    n = len(S.EVENTS)
    S.tick(when + timedelta(minutes=5))
    assert len(S.EVENTS) == n                                                   # once each
    assert S.rfi_answer(T, "RFI-001", "1.5 m rakhiye", close=True)["status"] == "closed"
    assert S.register_file(T, "P-001")["file"]["name"] == "Register_P-001.xlsx"
    with pytest.raises(S.ArchError):
        S.forget(T, "P-001")
    S.save_project(T, ref="P-001", status="done")
    S.forget(T, "P-001")
    assert S.project_view(T, "P-001")["client_phone"] == ""


def test_tools_and_api(ar, monkeypatch):
    S = ar
    from app.agent import archassist_tools as AT
    from app.agent.tools import Ctx, ToolError
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(AT.ARCHASSIST_HANDLERS[tool](c, **a))   # noqa: E731
    run(ctx, "archassist", action="settings", firm="Ingle Architects", coa_no="CA/2015/12345", gstin=GSTIN_MH)
    p = run(ctx, "archassist", action="project", name="Joshi row house", area="3000 sqft", road_width_m=9, client="Joshi")
    assert p["plot"]["area_sqm"] == pytest.approx(278.71, rel=1e-3)
    a = run(ctx, "archassist", action="area", project="Joshi", proposal={"bua_sqm": 300, "height_m": 9})
    assert a["statement"]["basic_fsi"] == 1.1
    staff = Ctx(T, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        run(staff, "archassist", action="fee", project="Joshi", basis="lump", lump=200000)
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9"), "archassist_dekho", what="projects")
    run(staff, "archassist", action="drawing", project="Joshi", sheet="A-01", title="Plan")
    tr = run(staff, "archassist", action="transmittal", project="Joshi", to_kind="client", to_name="Joshi", sheets=["A-01"])
    assert tr["status"] == "waiting"                                            # staff makes the card, can't issue
    assert run(ctx, "archassist_dekho", what="drawings", project="Joshi")["drawings"][0]["sheet"] == "A-01"
    assert "never" in run(ctx, "archassist_dekho", what="rules")
    assert len(AT.ARCHASSIST_TOOLS) == 2 and set(AT.ARCHASSIST_LABELS) == set(AT.ARCHASSIST_HANDLERS)

    from app.archassist.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/archassist").json()["projects"][0]["name"] == "Joshi row house"
    assert c.post(f"/api/archassist/transmittals/{tr['id']}/decide", json={}).status_code == 400
    assert c.post(f"/api/archassist/transmittals/{tr['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = c.post(f"/api/archassist/transmittals/{tr['id']}/decide", json={"yes": True, "hash": tr["hash"]})
    assert ok.status_code == 200 and ok.json()["file"]["name"].endswith(".pdf")
    c.post("/api/archassist/projects/P-001/fee", json={"basis": "lump", "lump": 200000})
    inv = c.post("/api/archassist/projects/P-001/invoices", json={"stage": "appointment"}).json()
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    r = c.post(f"/api/archassist/invoices/{inv['id']}/decide", json={"yes": True, "hash": inv["hash"]})
    assert r.status_code == 428 and r.json()["detail"] == "fingerprint_needed"
    assert c.post(f"/api/archassist/invoices/{inv['id']}/challenge").json()["challenge_id"]
    assert c.get("/api/archassist/rules").json()["fee_stages"]
    assert c.post("/api/archassist/projects/P-001/area", json={"proposal": {"bua_sqm": 600}}).json()["ok"] is False
