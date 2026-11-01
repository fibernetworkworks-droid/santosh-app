"""v0.354 RASEED (App Sahayak Phase 18): a receipt PDF for a finished order / booking - made by the server from its own row
(server-priced total, verified payment), for the customer who made it / staff / her only, through a 15-minute signed link the
installed app opens in the browser; a cancelled or unfinished row has none; Hindi names come out (shaped fonts)."""
import io
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def _text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def test_receipt_rules_link_and_pdf(droid_env):
    from app.appmaker import receipt as RC
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")):
        _acct(c, api, e, n)
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hn, hr = (_login(c, api, e, n) for e, n in (("asha@example.com", "Asha"), ("neha@example.com", "Neha"), ("ravi@example.com", "Ravi")))
    o = c.post(f"{api}/c/orders", json={"name": "आशा शर्मा", "phone": "9876543210", "address": "Flat 4, Pune",
                                        "cart": [{"id": p1["id"], "qty": 3, "price": 1}]}, headers=ha).json()
    want = round(float(p1["price"]) * 3, 2)
    # not finished: no receipt, no link
    assert c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]["receipt"] is False
    assert c.post(f"{api}/c/orders/{o['id']}/receipt-link", headers=ha).status_code == 409
    c.post(f"{api}/c/orders/{o['id']}/assign", json={"to": "me"}, headers=hr)
    c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
    assert c.get(f"{api}/c/orders", headers=ha).json()["rows"][0]["receipt"] is True
    # who: her customer and staff get a link; another customer / signed out do not
    assert c.post(f"{api}/c/orders/{o['id']}/receipt-link", headers=hn).status_code == 404
    assert c.post(f"{api}/c/orders/{o['id']}/receipt-link").status_code == 401
    assert c.post(f"{api}/c/orders/{o['id']}/receipt-link", headers=hr).status_code == 200
    url = c.post(f"{api}/c/orders/{o['id']}/receipt-link", headers=ha).json()["url"]
    path = url[url.index("/api/app-api/"):]
    assert "token" not in url and "asha" not in url.lower()
    got = c.get(path)
    assert got.status_code == 200 and got.headers["content-type"] == "application/pdf" and got.content[:5] == b"%PDF-"
    assert got.headers["content-security-policy"] == "sandbox" and "receipt-" in got.headers["content-disposition"]
    text = _text(got.content)
    assert "Receipt" in text and "not a GST tax invoice" in text and f"3 x {p1['name']}" in text and "Ravi" in text
    assert f"{want:,.0f}" in text.replace("₹", "") or f"{want:,.2f}" in text
    # a changed / expired signature or another row is refused
    assert c.get(path.replace("&s=", "&s=0")).status_code == 403
    exp = int(time.time()) - 5
    r = __import__("app.appmaker.backend", fromlist=["x"]).by_key(key)
    assert c.get(f"{api}/receipt/orders/{o['id']}?e={exp}&s={RC._sig(r, 'orders', o['id'], exp)}").status_code == 403
    o2 = c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "cart": [{"id": p1["id"], "qty": 1}]}, headers=ha).json()
    assert c.get(path.replace(o["id"], o2["id"])).status_code == 403
    # her copy from Hoola; a cancelled order never has one
    mine = c.get(f"/api/apps/{aid}/data/orders/{o['id']}/receipt")
    assert mine.status_code == 200 and mine.content[:5] == b"%PDF-" and "attachment" in mine.headers["content-disposition"]
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)
    assert c.get(f"/api/apps/{aid}/data/orders/{o2['id']}/receipt").status_code in (400, 409)
    assert RC.STATS["receipts"] >= 2 and RC.STATS["refused"] >= 3


def test_kits_and_console():
    root = Path(__file__).resolve().parents[1]
    kt = root / "app/appmaker/android/template/app/src/main/java/hoola/kit"
    pro = (kt / "Pro.kt").read_text()
    assert "fun ReceiptButton(coll: String, r: Item)" in pro and '"/c/$coll/${r.id}/receipt-link"' in pro and "Act.open(c, url)" in pro
    assert "ReceiptButton(coll, r)" in (kt / "Accounts.kt").read_text() and "val receipt" in (kt / "Strings.kt").read_text()
    sw = root / "app/appmaker/ios/template/Sources/Kit"
    assert "struct ReceiptButton: View" in (sw / "Pro.swift").read_text() and "openURL(u)" in (sw / "Pro.swift").read_text()
    assert "ReceiptButton(coll: coll, r: r)" in (sw / "Accounts.swift").read_text()
    js = (root / "app/static/console/build.js").read_text()
    assert "data-receipt" in js and "/receipt`" in js
