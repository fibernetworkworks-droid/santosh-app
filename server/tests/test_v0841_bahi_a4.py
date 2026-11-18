"""v0.840 BAHI A4 - GSTR-3B + payment plan: A2 credit brought in, least-cash set-off, portal compare, draft save, set-off on her confirm, payment
plan (no challan, no money), gated EVC filing. No network."""
import json

import httpx
import pytest

G = "27ADCPI1932N1ZH"
S1 = "29AABCU9603R1ZX"


@pytest.fixture
def a4(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_GST_CLIENT_ID": "GSTS" + "x" * 36, "WHITEBOOKS_GST_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import gstr3b, wb
    from app.bahi.models import AccGstConn, AccTwoB, ensure_tables
    from app.db import session
    from app.gstp.service import GstClient, GstDoc
    ensure_tables()
    with session() as s:
        c = GstClient(tenant_id="t1", name="Meghana", gstin=G, state="27", scheme="monthly")
        s.add(c)
        s.flush()
        it = {"rate": 18, "txval": 10000, "cgst": 900, "sgst": 900, "igst": 0, "cess": 0, "hsn": "9983", "desc": "Service", "qty": 1, "uqc": "NOS"}
        s.add(GstDoc(tenant_id="t1", client_id=c.id, period="2026-10", direction="out", kind="inv", number="S-1", doc_date="2026-10-05", party_gstin="",
                     party_name="Cust", pos="27", items=json.dumps([it]), txval=10000, cgst=900, sgst=900, value=11800, source="manual"))
        def row(n, ig, cg, sg, act):
            s.add(AccTwoB(tenant_id="t1", gstin=G, period="102026", section="b2b", ctin=S1, trdnm="ACME", inum=n, doc_type="R", dt="2026-10-05",
                          val=100, txval=100, igst=ig, cgst=cg, sgst=sg, action=act, ext="{}"))
        row("A-1", 0, 500, 500, "accept")      # counted
        row("A-2", 0, 300, 300, "pending")     # her IMS pending: not counted
        s.add(AccGstConn(tenant_id="t1", gstin=G, state_cd="27", gst_username="u", txn="TXN", status="connected", enabled_until="2999-01-01T00:00:00+00:00"))
        s.commit()
    seen = []

    def ok(**k):
        return httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", **k})

    def routes(req):
        p = req.url.path
        if p.endswith("/gstr3b/autoliab"):
            return ok(data={"osup_det": {"txval": 10000, "iamt": 0, "camt": 900, "samt": 900, "csamt": 0}})
        if p.endswith("/gstr3b/syscalcintrst"):
            return ok(data={"intr": {"iamt": 0}})
        if p.endswith("/gstr3b/retsave"):
            return ok()
        if p.endswith("/gstr3b/retsum"):
            return ok(data={"gstin": G, "tx_pmt": {"tx_py": [{"liab_ldg_id": 111, "trans_typ": 30002}]}})
        if p.endswith("/gstr3b/retoffset"):
            return ok()
        if p.endswith("/ledgers/bal"):
            return ok(data={"cash_bal": {"cgst": {"tx": 100}, "sgst": {"tx": 0}, "igst": {"tx": 0}, "cess": {"tx": 0}}})
        if p.endswith("/authentication/otpforevc"):
            return ok()
        if p.endswith("/gstr3b/retevcfile"):
            return ok(data={"status": "filed"})
        return httpx.Response(404)
    monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(lambda r: (seen.append(r), routes(r))[1]))
    yield gstr3b, seen, get_settings
    get_settings.cache_clear()


def test_prepare_uses_her_ims_decisions_and_least_cash(a4):
    g3, seen, _ = a4
    r = g3.prepare("t1", G, "2026-10")
    assert r["credit_rows_from_2b"] == 2 and not seen
    assert r["tables"]["4A"]["cgst"] == 500 and r["tables"]["4A"]["sgst"] == 500        # A-2 pending is not counted
    assert r["summary"]["liability"] == 1800 and r["summary"]["itc"] == 1000 and r["summary"]["cash"] == 800
    assert r["setoff"]["used"]["cgst->cgst"] == 500 and r["cash_to_pay"]["total"] >= 800
    assert r["plan_hash"]


def test_without_a_2b_the_credit_is_zero_and_it_says_so(a4):
    g3, seen, _ = a4
    from app.bahi.models import AccTwoB
    from app.db import session
    with session() as s:
        for x in s.query(AccTwoB).all():
            s.delete(x)
        s.commit()
    r = g3.prepare("t1", G, "2026-10")
    assert r["credit_rows_from_2b"] == 0 and "No GSTR-2B has been pulled" in r["checks"][0]


def test_compare_save_and_setoff_need_her_confirm_and_the_exact_plan(a4):
    g3, seen, _ = a4
    p = g3.prepare("t1", G, "2026-10")
    c = g3.compare_with_portal("t1", G, "2026-10")
    assert c["compared"] and all(abs(r["diff"]) <= 1 for r in c["rows"] if r["head"] in ("cgst", "sgst"))
    for fn in (g3.save_draft, g3.apply_setoff):
        with pytest.raises(g3.Gstr3bError):
            fn("t1", G, "2026-10", p["plan_hash"], False)
        with pytest.raises(g3.Gstr3bError):
            fn("t1", G, "2026-10", "stale", True)
    assert not [r for r in seen if r.method == "PUT"]
    g3.save_draft("t1", G, "2026-10", p["plan_hash"], True)
    save = [r for r in seen if r.url.path.endswith("/gstr3b/retsave")][0]
    body = json.loads(save.content)
    assert save.method == "PUT" and body["gstin"] == G and body["ret_period"] == "102026"
    assert body["sup_details"]["osup_det"]["camt"] == 900 and body["itc_elg"]["itc_net"]["camt"] == 500
    out = g3.apply_setoff("t1", G, "2026-10", p["plan_hash"], True)
    assert out["applied"] and out["cash_still_to_pay"] == 800
    off = json.loads([r for r in seen if r.url.path.endswith("/gstr3b/retoffset")][0].content)
    assert off["pditc"]["liab_ldg_id"] == 111 and off["pditc"]["trans_typ"] == 30002 and off["pditc"]["c_pdc"] == 500 and off["pditc"]["s_pds"] == 500
    assert off["pdcash"][0]["cpd"] == 400 and off["pdcash"][0]["spd"] == 400


def test_payment_plan_names_the_bank_amount_and_creates_no_challan(a4):
    g3, seen, _ = a4
    g3.prepare("t1", G, "2026-10")
    pay = g3.payment_plan("t1", G, "2026-10")
    assert pay["cash_in_ledger"]["cgst"] == 100 and pay["short"]["cgst"] == 300 and pay["short"]["sgst"] == 400
    assert pay["pay_at_bank"] >= 700 and "Create Challan" in pay["how"] and "never moves money" in pay["how"]
    assert not [r for r in seen if "payment" in r.url.path.lower() and "ledgers" not in r.url.path]


def test_setoff_refuses_when_the_portal_gives_no_ledger_ids(a4, monkeypatch):
    g3, seen, _ = a4
    p = g3.prepare("t1", G, "2026-10")
    from app.bahi import wb
    monkeypatch.setattr(wb, "gstr3b_retsum", lambda *a, **k: {"status_cd": "1", "data": {"gstin": G}})
    with pytest.raises(g3.Gstr3bError) as e:
        g3.apply_setoff("t1", G, "2026-10", p["plan_hash"], True)
    assert "ledger ids" in str(e.value) and not [r for r in seen if r.url.path.endswith("/retoffset")]


def test_filing_is_off_by_default_then_needs_everything(a4, monkeypatch):
    g3, seen, get_settings = a4
    p = g3.prepare("t1", G, "2026-10")
    with pytest.raises(g3.Gstr3bError) as e:
        g3.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], True)
    assert "BAHI_FILING" in str(e.value)
    monkeypatch.setenv("BAHI_FILING", "true")
    get_settings.cache_clear()
    assert g3.request_evc_otp("t1", G, "ADCPI1932N")["sent"]
    with pytest.raises(g3.Gstr3bError):
        g3.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], False)
    with pytest.raises(g3.Gstr3bError):
        g3.file_evc("t1", G, "2026-10", "ADCPI1932N", "1", p["plan_hash"], True)
    out = g3.file_evc("t1", G, "2026-10", "ADCPI1932N", "123456", p["plan_hash"], True)
    assert out["filed"]
    f = [r for r in seen if r.url.path.endswith("/gstr3b/retevcfile")][0]
    assert f.url.params["evcotp"] == "123456" and f.method == "POST"
    from app.bahi import register
    assert "123456" not in json.dumps(register.events("t1", 50))


def test_wiring(a4):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for r in ("prepare", "compare", "save", "setoff", "payment", "evc-otp", "file"):
        assert f"/api/bahi/gstr3b/{r}" in api
    js = (root / "static/console/bahi.js").read_text()
    assert "g3off" in js and "g3pay" in js and "cannot be undone" in js
