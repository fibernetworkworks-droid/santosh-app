"""v0.838 BAHI A3 - GSTR-1: build + pre-11th checks against the register, draft save on her confirm, gated EVC filing. No network."""
import json

import httpx
import pytest

G = "27ADCPI1932N1ZH"
BUYER = "29AABCU9603R1ZX"


@pytest.fixture
def a3(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_GST_CLIENT_ID": "GSTS" + "x" * 36, "WHITEBOOKS_GST_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import gstr1, wb
    from app.bahi.models import AccDoc, AccGstConn, ensure_tables
    from app.db import session
    from app.gstp.service import GstClient, GstDoc
    ensure_tables()
    with session() as s:
        c = GstClient(tenant_id="t1", name="Meghana", gstin=G, state="27", scheme="monthly")
        s.add(c)
        s.flush()
        def item(rate, tx, hsn="9983"):
            tax = round(tx * rate / 100, 2)
            return {"rate": rate, "txval": tx, "cgst": tax / 2, "sgst": tax / 2, "igst": 0, "cess": 0, "hsn": hsn, "desc": "Service", "qty": 1, "uqc": "NOS"}
        def gdoc(n, gstin, rate, tx, pos="27"):
            it = item(rate, tx)
            s.add(GstDoc(tenant_id="t1", client_id=c.id, period="2026-10", direction="out", kind="inv", number=n, doc_date="2026-10-05",
                         party_gstin=gstin, party_name="Cust", pos=pos, items=json.dumps([it]), txval=tx, cgst=it["cgst"], sgst=it["sgst"],
                         value=tx + it["cgst"] + it["sgst"], source="manual"))
        gdoc("INV-1", "", 18, 1000)                 # B2C, fine
        gdoc("INV-2", BUYER, 18, 2000, "29")        # fine B2B (inter)
        gdoc("INV-3", "29AABCU9603R1ZZ", 18, 500)   # bad check digit
        gdoc("INV-4", "", 12, 500)                  # 12% is not a slab after 22 Sep 2025
        def rdoc(n, gstin, src):
            s.add(AccDoc(tenant_id="t1", gstin=G, period="2026-10", direction="out", number=n, doc_date="2026-10-06", party_name="Shop",
                         party_gstin=gstin, igst=90, taxable=500, source=src, source_ref=n))
        rdoc("OFF-9", "", "office")                 # lives only in another engine
        rdoc("INV-1", BUYER, "app")                 # register says B2B, the bill says none
        s.add(AccGstConn(tenant_id="t1", gstin=G, state_cd="27", gst_username="u", txn="TXN", status="connected", enabled_until="2999-01-01T00:00:00+00:00"))
        s.commit()
    seen = []

    def plug(fn):
        monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(lambda r: (seen.append(r), fn(r))[1]))

    def ok(**k):
        return httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", **k})

    def routes(req):
        p = req.url.path
        if p.endswith("/gstr1/retsave"):
            return ok(header={"reference_id": "REF-1"})
        if p.endswith("/gstr1/validatehsnsum"):
            return ok(data={"status": "valid"})
        if p.endswith("/gstr1/retsum"):
            return ok(data={"gstin": G, "ret_period": "102026", "sec_sum": [{"sec_nm": "B2B", "ttl_val": 1}]})
        if p.endswith("/authentication/otpforevc"):
            return ok()
        if p.endswith("/gstr1/retevcfile"):
            return ok(data={"status": "filed", "reference_id": "REF-2"})
        return httpx.Response(404)
    plug(routes)
    yield gstr1, seen, get_settings
    get_settings.cache_clear()


def test_prepare_builds_the_return_and_checks_it_against_the_register(a3):
    gstr1, seen, _ = a3
    r = gstr1.prepare("t1", G, "2026-10")
    assert r["summary"]["b2b_invoices"] == 2 and r["plan_hash"] and r["return_id"]
    kinds = {}
    for c in r["checks"]:
        kinds.setdefault(c["kind"], []).append(c["text"])
    assert any("OFF-9" in t and "would be left out" in t for t in kinds["missing"])
    assert any("INV-1" in t and BUYER in t for t in kinds["b2b_as_b2c"])
    assert any("INV-3" in t and "check digit" in t for t in kinds["bad_gstin"])
    assert any("INV-4" in t and "12%" in t for t in kinds["rate"])
    assert seen == []                                      # nothing left Hoola


def test_save_is_a_draft_on_her_confirm_and_the_exact_plan(a3):
    gstr1, seen, _ = a3
    p = gstr1.prepare("t1", G, "2026-10")
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.save_draft("t1", G, "2026-10", p["plan_hash"], False)
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.save_draft("t1", G, "2026-10", "wrong", True)
    assert not seen
    out = gstr1.save_draft("t1", G, "2026-10", p["plan_hash"], True)
    assert out["saved"] and out["reference"] == "REF-1" and "valid" in out["validate_hsn"] and "gstin" in out["portal_summary_fields"]
    save = [r for r in seen if r.url.path.endswith("/gstr1/retsave")][0]
    body = json.loads(save.content)
    assert save.method == "PUT" and save.headers["gstin"] == G and save.headers["ret_period"] == "102026"
    assert body["gstin"] == G and body["fp"] == "102026" and "hash" not in body and "version" not in body and body["b2b"][0]["ctin"]


def test_filing_is_off_by_default_and_needs_confirm_plan_and_otp_when_on(a3, monkeypatch):
    gstr1, seen, get_settings = a3
    p = gstr1.prepare("t1", G, "2026-10")
    for call in (lambda: gstr1.request_evc_otp("t1", G, "ADCPI1932N"), lambda: gstr1.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], True)):
        with pytest.raises(gstr1.Gstr1Error) as e:
            call()
        assert "BAHI_FILING" in str(e.value)
    assert not seen
    monkeypatch.setenv("BAHI_FILING", "true")
    get_settings.cache_clear()
    assert gstr1.request_evc_otp("t1", G, "ADCPI1932N")["sent"]
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], False)
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.file_evc("t1", G, "2026-10", "ADCPI1932N", "12", p["plan_hash"], True)
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", "stale", True)
    out = gstr1.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], True)
    assert out["filed"] and "filed" in out["portal_status"]
    f = [r for r in seen if r.url.path.endswith("/gstr1/retevcfile")][0]
    assert f.url.params["evcotp"] == "123456" and f.url.params["pan"] == "ADCPI1932N" and json.loads(f.content)["content"]["gstin"] == G
    from app.bahi import register
    assert "123456" not in json.dumps(register.events("t1", 50))        # the OTP is never kept


def test_bad_inputs_and_wiring(a3):
    gstr1, _, _ = a3
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.prepare("t1", "27ADCPI1932N1ZX", "2026-10")
    with pytest.raises(gstr1.Gstr1Error):
        gstr1.prepare("t1", G, "Oct")
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/gstr1/prepare", "/api/bahi/gstr1/save", "/api/bahi/gstr1/evc-otp", "/api/bahi/gstr1/file"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "g1save" in js and "g1file" in js and "OV.filing" in js
