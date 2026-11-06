"""v0.355 GST BILL (App Sahayak Phase 19): her GSTIN (format + check digit) -> a finished row's receipt becomes a Rule 46 TAX
INVOICE: consecutive INV/<FY>/0001 numbers given once, GST-inclusive prices (total = the server's order total), CGST + SGST
inside her state, IGST outside it (place of supply from a buyer GSTIN or the address), HSN per product, total in words."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

GOOD = "27AAACR5055K1Z7"          # a real, published GSTIN (Maharashtra) - format + check digit


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def test_gstin_check_digit_words_fy():
    from app.appmaker import gst as G
    assert G.valid_gstin(GOOD) and not G.valid_gstin(GOOD[:-1] + "8") and not G.valid_gstin("99AAACR5055K1Z7")
    assert not G.valid_gstin("27AAACR5055K1Y7") and not G.valid_gstin("")
    assert G.words(1180) == "Rupees One Thousand One Hundred Eighty Only"
    assert G.words(250000.5) == "Rupees Two Lakh Fifty Thousand and Fifty Paise Only"
    from datetime import datetime
    assert G.fy(datetime(2027, 3, 31, 12)) == "2026-27" and G.fy(datetime(2027, 4, 1, 12)) == "2027-28"


def test_settings_numbers_split_and_pdf(droid_env):
    from app.appmaker import backend as BE
    from app.appmaker import gst as G
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    prods = c.get(f"/api/app-content/{key}").json()["lists"]["products"]
    p1, p2 = prods[0], prods[1]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    # settings: a wrong GSTIN / rate / HSN is refused; a right one switches invoices on
    assert c.get(f"/api/apps/{aid}/gst").json()["on"] is False
    assert c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD[:-1] + "8"}).status_code == 400
    assert c.put(f"/api/apps/{aid}/gst", json={"rate": 7}).status_code == 400
    assert c.put(f"/api/apps/{aid}/gst", json={"hsn": "12ab"}).status_code == 400
    v = c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD.lower(), "legal_name": "Sharma Traders LLP", "rate": 18, "hsn": "2106",
                                            "items": {p1["id"]: {"hsn": "1905", "rate": 5}, "nope": {"rate": 28}}}).json()
    assert v["on"] and v["gstin"] == GOOD and v["state"] == "Maharashtra"
    assert {p["id"]: p for p in v["products"]}[p1["id"]]["rate"] == 5
    mk = lambda body: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", **body,
                                                       "cart": [{"id": p1["id"], "qty": 2}, {"id": p2["id"], "qty": 1}]}, headers=ha).json()
    o1 = mk({"address": "Flat 4, Kothrud, Pune"})                  # inside her state -> CGST + SGST
    o2 = mk({"address": "12 MG Road, Bengaluru, Karnataka"})       # outside -> IGST
    for o in (o1, o2):
        c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    rows = {x["id"]: x for x in c.get(f"{api}/c/orders", headers=ha).json()["rows"]}
    assert rows[o1["id"]]["receipt_kind"] == "invoice"
    r = BE.by_key(key)
    sch = BE.schema(r)
    col = next(x for x in sch["collections"] if x["key"] == "orders")
    d1 = BE._assign_info(BE.bid(r), [o1["id"]])[o1["id"]]
    x1 = G.compute(r, col, d1)
    assert not x1["inter"] and x1["pos"] == "27"
    assert x1["totals"]["amount"] == pytest.approx(o1["total"])                      # GST-inclusive: never more than she paid
    l1 = x1["lines"][0]
    assert l1["rate"] == 5 and l1["hsn"] == "1905" and l1["cgst"] + l1["sgst"] == pytest.approx(l1["amount"] - l1["taxable"])
    assert l1["taxable"] == pytest.approx(round(l1["amount"] / 1.05, 2)) and x1["lines"][1]["rate"] == 18 and x1["lines"][1]["hsn"] == "2106"
    x2 = G.compute(r, col, BE._assign_info(BE.bid(r), [o2["id"]])[o2["id"]])
    assert x2["inter"] and x2["pos"] == "29" and x2["totals"]["cgst"] == 0 and x2["totals"]["igst"] > 0
    # the PDF: tax invoice with the particulars; numbers consecutive and given once
    pdf1 = c.get(f"/api/apps/{aid}/data/orders/{o1['id']}/receipt")
    assert pdf1.status_code == 200 and "invoice-INV-" in pdf1.headers["content-disposition"]
    t1 = _text(pdf1.content)
    fy = G.fy()
    for want in ("TAX INVOICE", GOOD, f"INV/{fy}/0001", "Place of supply: Maharashtra (27)", "CGST", "SGST", "1905",
                 "Sharma Traders LLP", "Rupees", "Authorised signatory", "reverse charge"):
        assert want in t1, want
    assert f"INV/{fy}/0002" in _text(c.get(f"/api/apps/{aid}/data/orders/{o2['id']}/receipt").content)
    assert "IGST" in _text(c.get(f"/api/apps/{aid}/data/orders/{o2['id']}/receipt").content)
    assert f"INV/{fy}/0001" in _text(c.get(f"/api/apps/{aid}/data/orders/{o1['id']}/receipt").content)   # the same number again
    assert c.get(f"/api/apps/{aid}/gst").json()["issued"] == 2
    # the customer's link gives the same invoice; GST off = plain receipts again (numbers kept)
    url = c.post(f"{api}/c/orders/{o1['id']}/receipt-link", headers=ha).json()["url"]
    assert f"INV/{fy}/0001" in _text(c.get(url[url.index("/api/app-api/"):]).content)
    assert c.put(f"/api/apps/{aid}/gst", json={"gstin": ""}).json()["on"] is False
    assert "TAX INVOICE" not in _text(c.get(f"/api/apps/{aid}/data/orders/{o1['id']}/receipt").content)
    assert c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD}).json()["issued"] == 2


def test_tool_and_ui_markers(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "gst", {"app": aid, "gst": {"gstin": GOOD, "rate": 12}})
    assert out["on"] and "Maharashtra" in out["say"] and out["rate"] == 12
    root = Path(__file__).resolve().parents[1]
    assert "Strings.invoice" in (root / "app/appmaker/android/template/app/src/main/java/hoola/kit/Pro.kt").read_text()
    assert "Words.invoice" in (root / "app/appmaker/ios/template/Sources/Kit/Pro.swift").read_text()
    js = (root / "app/static/console/build.js").read_text()
    assert "GST invoices" in js and "'/gst'" in js
