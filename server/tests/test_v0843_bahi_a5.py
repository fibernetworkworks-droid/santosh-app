"""v0.842 BAHI A5 - e-invoice (IRN) + e-way bill. No network: the IRP / e-way bill are a MockTransport."""
import json

import httpx
import pytest

G = "27ADCPI1932N1ZH"
BUYER = "29AABCU9603R1ZX"
SELLER = {"LglNm": "MEGHANA INGLE", "Addr1": "Plot 1", "Loc": "Akola", "Pin": "444001"}


@pytest.fixture
def a5(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_EINV_CLIENT_ID": "EINS" + "x" * 36, "WHITEBOOKS_EINV_CLIENT_SECRET": "s" * 40,
                 "WHITEBOOKS_EWB_CLIENT_ID": "EWBS" + "x" * 36, "WHITEBOOKS_EWB_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-a5-0123456789abcdef")
    from app.config import get_settings
    get_settings.cache_clear()
    from datetime import date, timedelta
    from app.bahi import einv, wb
    from app.bahi.models import AccDoc, ensure_tables
    from app.db import session
    ensure_tables()
    today = date.today().isoformat()
    with session() as s:
        def doc(n, gstin="", total=1180.0, d=today):
            s.add(AccDoc(tenant_id="t1", gstin=G, period=d[:7], direction="out", kind="inv", number=n, doc_date=d, party_name="Acme Traders",
                         party_gstin=gstin, taxable=1000, igst=180, total=total, source="app", source_ref=n))
        doc("INV-1", BUYER)
        doc("INV-2", "")                                       # a consumer sale: no IRN
        doc("A" * 20, BUYER)                                   # number too long
        doc("INV-OLD", BUYER, d=(date.today() - timedelta(days=40)).isoformat())
        s.commit()
        ids = {d.number: d.id for d in s.query(AccDoc).all()}
    seen, state = [], {"mode": "ok", "dup": False}

    def ok(**k):
        return httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", **k})

    def routes(req):
        seen.append(req)
        p = req.url.path
        if p.endswith("/einvoice/authenticate"):
            return ok(data={"AuthToken": "TOK-SECRET", "Sek": "x", "TokenExpiry": "2026-11-12 23:00:00"})
        if p.endswith("/GENERATE/version/V1_03"):
            if state["mode"] == "timeout":
                raise httpx.ReadTimeout("slow", request=req)
            if state["mode"] == "dup":
                return httpx.Response(200, json={"status_cd": "0", "error": {"error_cd": "2150", "message": "Duplicate IRN"}})
            return ok(data={"Irn": "I" * 64, "AckNo": 112233, "AckDt": "2026-11-12 10:00:00"})
        if p.endswith("/GETIRNBYDOCDETAILS/version/V1_03"):
            return ok(data={"Irn": "E" * 64, "AckNo": 5, "AckDt": "2026-11-12 09:00:00"})
        if p.endswith("/CANCEL/version/V1_03"):
            return ok(data={"Irn": "I" * 64})
        if p.endswith("/GENERATE_EWAYBILL/version/V1_03"):
            return ok(data={"EwbNo": 331000000001, "EwbDt": "2026-11-12 10:30:00"})
        if p.endswith("/ewaybillapi/v1.03/authenticate"):
            return ok()
        if p.endswith("/ewayapi/canewb"):
            return ok()
        return httpx.Response(404)
    monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(routes))
    einv.connect("t1", G, "irp.user", "irp-pass-1", SELLER, ewb_username="ewb.user", ewb_password="ewb-pass-1")
    yield einv, seen, state, ids
    get_settings.cache_clear()


EXTRA = {"hsn": "9983", "buyer_addr1": "5 MG Road", "buyer_loc": "Bengaluru", "buyer_pin": "560001"}


def test_connect_seals_the_password_and_returns_no_secret(a5):
    einv, seen, _, _ = a5
    st = einv.status("t1", G)
    assert st["connected"] and st["username"] == "irp.user" and "TOK-SECRET" not in json.dumps(st) and "irp-pass-1" not in json.dumps(st)
    from app.bahi.models import AccGstConn
    from app.db import session
    with session() as s:
        r = s.query(AccGstConn).one()
        assert "irp-pass-1" not in (r.einv_password_enc or "") and "TOK-SECRET" not in (r.einv_token or "") and r.einv_password_enc
    with pytest.raises(einv.EinvError):
        einv.connect("t1", G, "u", "p", {"LglNm": "X"})            # seller address missing


def test_build_lists_what_is_missing_and_builds_a_consistent_inv01(a5):
    einv, seen, _, ids = a5
    m = einv.build("t1", G, ids["INV-1"], {})
    assert not m["ready"] and any("HSN" in x for x in m["missing"]) and any("address" in x for x in m["missing"])
    b = einv.build("t1", G, ids["INV-1"], EXTRA)
    assert b["ready"] and b["payload"]["Version"] == "1.1" and b["payload"]["DocDtls"]["No"] == "INV-1" and b["payload"]["DocDtls"]["Dt"].count("/") == 2
    v = b["payload"]["ValDtls"]
    assert v["AssVal"] == 1000 and v["IgstVal"] == 180 and v["TotInvVal"] == 1180 and b["payload"]["ItemList"][0]["GstRt"] == 18
    assert b["payload"]["BuyerDtls"]["Stcd"] == "29" and b["payload"]["SellerDtls"]["Gstin"] == G
    with pytest.raises(einv.EinvError):
        einv.build("t1", G, ids["INV-2"], EXTRA)                    # no customer GSTIN: no IRN
    assert any("16 characters" in x for x in einv.build("t1", G, ids["A" * 20], EXTRA)["missing"])


def test_generate_needs_confirm_and_plan_persists_first_and_is_idempotent(a5):
    einv, seen, state, ids = a5
    b = einv.build("t1", G, ids["INV-1"], EXTRA)
    for plan, conf in ((b["plan_hash"], False), ("stale", True)):
        with pytest.raises(einv.EinvError):
            einv.generate("t1", G, ids["INV-1"], EXTRA, plan, conf)
    assert not [r for r in seen if r.url.path.endswith("/GENERATE/version/V1_03")]
    r = einv.generate("t1", G, ids["INV-1"], EXTRA, b["plan_hash"], True)
    assert r["status"] == "generated" and r["irn"] == "I" * 64 and r["ack_no"] == "112233" and r["cancel_hours_left"] is not None
    gen = [x for x in seen if x.url.path.endswith("/GENERATE/version/V1_03")][0]
    assert gen.headers["auth-token"] == "TOK-SECRET" and gen.headers["gstin"] == G
    again = einv.generate("t1", G, ids["INV-1"], EXTRA, b["plan_hash"], True)
    assert again["already"] and len([x for x in seen if x.url.path.endswith("/GENERATE/version/V1_03")]) == 1


def test_a_duplicate_or_a_timeout_adopts_what_the_irp_already_issued(a5):
    einv, seen, state, ids = a5
    b = einv.build("t1", G, ids["INV-1"], EXTRA)
    state["mode"] = "dup"
    r = einv.generate("t1", G, ids["INV-1"], EXTRA, b["plan_hash"], True)
    assert r["adopted"] and r["irn"] == "E" * 64 and r["status"] == "generated"
    assert [x for x in seen if x.url.path.endswith("/GETIRNBYDOCDETAILS/version/V1_03")][0].headers["docnum"] == "INV-1"
    assert len(einv.listing("t1", G)["irns"]) == 1


def test_window_and_cancel_rules(a5):
    einv, seen, _, ids = a5
    from app.bahi.models import AccIrn
    from app.db import session
    # a turnover of Rs 10 crore or more brings the 30-day limit: a 40-day-old invoice is refused before any call
    from app.gstp.service import GstClient
    with session() as s:
        s.add(GstClient(tenant_id="t1", name="M", gstin=G, state="27", aato=200_000_000))
        s.commit()
    b = einv.build("t1", G, ids["INV-OLD"], EXTRA)
    with pytest.raises(einv.EinvError) as e:
        einv.generate("t1", G, ids["INV-OLD"], EXTRA, b["plan_hash"], True)
    assert "30 days" in str(e.value) and not [x for x in seen if x.url.path.endswith("/GENERATE/version/V1_03")]
    w = einv.watch("t1", G)
    assert w[0]["number"] == "INV-OLD" and w[0]["days_left"] == -10
    # cancel: needs confirm; refuses with a live e-way bill; refuses after 24 hours
    b1 = einv.build("t1", G, ids["INV-1"], EXTRA)
    r = einv.generate("t1", G, ids["INV-1"], EXTRA, b1["plan_hash"], True)
    with pytest.raises(einv.EinvError):
        einv.cancel("t1", r["id"], "2", "x", False)
    e1 = einv.ewb_from_irn("t1", r["id"], {"distance": 120, "vehicle_no": "mh 30 ab 1234"}, True)
    assert e1["ewb_no"] == "331000000001"
    body = json.loads([x for x in seen if x.url.path.endswith("/GENERATE_EWAYBILL/version/V1_03")][0].content)
    assert body["Irn"] == "I" * 64 and body["VehNo"] == "MH30AB1234" and body["Distance"] == 120
    with pytest.raises(einv.EinvError) as e:
        einv.cancel("t1", r["id"], "2", "x", True)
    assert "e-way bill first" in str(e.value)
    einv.ewb_cancel("t1", r["id"], "2", "mistake", True)
    assert [x for x in seen if x.url.path.endswith("/ewayapi/canewb")]
    with session() as s:
        row = s.get(AccIrn, r["id"])
        row.ack_dt = "2020-01-01 10:00:00"
        s.commit()
    with pytest.raises(einv.EinvError) as e:
        einv.cancel("t1", r["id"], "2", "x", True)
    assert "24-hour" in str(e.value) and "credit note" in str(e.value)
    with session() as s:
        row = s.get(AccIrn, r["id"])
        row.ack_dt = einv._now().strftime("%Y-%m-%d %H:%M:%S")
        s.commit()
    assert einv.cancel("t1", r["id"], "2", "mistake", True)["status"] == "cancelled"


def test_wiring(a5):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for r in ("status", "connect", "list", "build", "generate", "cancel", "ewb", "ewb-cancel"):
        assert f"/api/bahi/einv/{r}" in api
    js = (root / "static/console/bahi.js").read_text()
    assert "eigen" in js and "eicancel" in js and "type=\"password\"" in js
    chk = (root / "bahi/wbcheck.py").read_text()
    assert "einv_gstin_details" in chk and "einv_generate" not in chk
