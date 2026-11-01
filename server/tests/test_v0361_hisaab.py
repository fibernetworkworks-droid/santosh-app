"""v0.361 HISAAB (App Sahayak Phase 25): the month's accounts for her CA - sales / invoice / credit-note registers, HSN and
rate-wise summaries, khata movements - from the same server numbers as the invoices; a ZIP of CSVs (Excel-safe cells)."""
import csv
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def _csv(z, name):
    return list(csv.reader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def test_month_report(droid_env):
    from app.appmaker import gst as G
    from app.appmaker import hisaab as HS
    from app.main import app
    c = TestClient(app)
    aid, conv, key, be = _built(droid_env)
    api = f"/api/app-api/{key}"
    p1 = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]
    _acct(c, api, "asha@example.com", "Asha")
    _acct(c, api, "ravi@example.com", "Ravi")
    mem = {m["email"]: m for m in c.get(f"/api/apps/{aid}/members").json()["members"]}
    c.post(f"/api/apps/{aid}/members/{mem['ravi@example.com']['id']}/role", json={"role": "staff"})
    ha, hr = _login(c, api, "asha@example.com", "Asha"), _login(c, api, "ravi@example.com", "Ravi")
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 5, "hsn": "1905"})
    mk = lambda name: c.post(f"{api}/c/orders", json={"name": name, "phone": "9876543210", "address": "Pune",
                                                       "cart": [{"id": p1["id"], "qty": 2}]}, headers=ha).json()
    o1, o2, o3 = mk("Asha"), mk("=HYPERLINK(\"http://x\")"), mk("Asha")
    for o in (o1, o2):
        c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
        c.get(f"/api/apps/{aid}/data/orders/{o['id']}/receipt")
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)          # -> credit note
    c.post(f"{api}/c/orders/{o3['id']}", json={"_credit": True}, headers=hr)
    c.post(f"{api}/khata/{mem['asha@example.com']['id']}/pay", json={"amount": 10}, headers=hr)
    from app.db import now
    month = HS._ist(now()).strftime("%Y-%m")
    assert c.get(f"/api/apps/{aid}/hisaab", params={"month": "2026-13"}).status_code == 400
    v = c.get(f"/api/apps/{aid}/hisaab", params={"month": month}).json()
    s = v["summary"]
    assert s["orders"] == 2 and s["cancelled"] == 1 and s["sales"] == pytest.approx(o1["total"] + o3["total"])
    assert v["counts"] == {"sales": 3, "invoices": 2, "credit_notes": 1, "khata": 2}
    assert s["gst"] > 0 and s["credit"] == pytest.approx(o2["total"]) and s["udhaar_given"] == pytest.approx(o3["total"])
    assert "orders" in v["say"] and "GST" in v["say"]
    r = c.get(f"/api/apps/{aid}/hisaab", params={"month": month, "download": 1})
    assert r.headers["content-type"] == "application/zip" and "hisaab-" in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(z.namelist())
    for k in ("sales", "invoices", "credit-notes", "hsn", "rates", "khata"):
        assert f"{month}-{k}.csv" in names
    inv = _csv(z, f"{month}-invoices.csv")
    assert inv[0][0] == "Invoice no" and inv[1][0] == f"INV/{G.fy()}/0001" and inv[1][4].startswith("27-")
    sales = _csv(z, f"{month}-sales.csv")
    assert any(row[2].startswith("'=") for row in sales[1:])                 # a formula from a customer's field is defused
    hsn = _csv(z, f"{month}-hsn.csv")
    assert hsn[1][0] == "1905" and float(hsn[1][3]) == pytest.approx(float(inv[1][5]), abs=0.02)   # 2 invoices minus 1 credit note
    cn = _csv(z, f"{month}-credit-notes.csv")
    assert cn[1][2] == f"INV/{G.fy()}/0002"
    assert "Nothing has been filed" in z.read("README.txt").decode()
    # another month is empty
    assert c.get(f"/api/apps/{aid}/hisaab", params={"month": "2020-01"}).json()["counts"]["sales"] == 0


def test_tool_and_console(droid_env):
    from app.agent.app_tools import _act
    from app.agent.tools import Ctx
    from tests.test_v128_appdesign import T
    aid, conv, key, be = _built(droid_env)
    out = _act(Ctx(tenant_id=T, conversation_id=conv), "hisaab", {"app": aid, "month": "2026-10"})
    assert out["month"] == "2026-10" and "download=1" in out["download"]
    assert "Download for CA" in (Path(__file__).resolve().parents[1] / "app/static/console/build.js").read_text()
