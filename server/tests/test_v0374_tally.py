"""v0.374 TALLY EXPORT (App Sahayak Phase 38): the month's invoices + credit notes as Tally XML vouchers from the same
numbers as the invoices - every voucher balances (debits = credits), a credit note is the mirror of its sale, ledger names
are hers, text is escaped."""
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)


def test_tally_xml(droid_env):
    from app.appmaker import hisaab as HS
    from app.db import now
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
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 18})
    month = HS._ist(now()).strftime("%Y-%m")
    mk = lambda name: c.post(f"{api}/c/orders", json={"name": name, "phone": "9876543210", "address": "Pune",
                                                       "cart": [{"id": p1["id"], "qty": 3}]}, headers=ha).json()
    o1, o2 = mk("Asha & Sons <Pune>"), mk("Asha")
    for o in (o1, o2):
        c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
        c.get(f"/api/apps/{aid}/data/orders/{o['id']}/receipt")
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)
    assert c.put(f"/api/apps/{aid}/tally", json={"party": "Counter Sales", "sales": "Sales @18%", "bogus": "x"}).json()["party"] == "Counter Sales"
    r = c.get(f"/api/apps/{aid}/tally", params={"month": month})
    assert r.status_code == 200 and "tally-" in r.headers["content-disposition"]
    root = ET.fromstring(r.content)                                  # well-formed (names with & and < are escaped)
    assert root.find("HEADER/TALLYREQUEST").text == "Import Data"
    vs = root.findall(".//VOUCHER")
    kinds = [v.get("VCHTYPE") for v in vs]
    assert kinds.count("Sales") == 2 and kinds.count("Credit Note") == 1
    for v in vs:
        amts = [float(e.find("AMOUNT").text) for e in v.findall("ALLLEDGERENTRIES.LIST")]
        assert sum(amts) == pytest.approx(0, abs=0.005)               # balanced
        led = {e.find("LEDGERNAME").text: e for e in v.findall("ALLLEDGERENTRIES.LIST")}
        assert {"Counter Sales", "Sales @18%", "Output CGST", "Output SGST"} <= set(led)
        party = led["Counter Sales"]
        sale = v.get("VCHTYPE") == "Sales"
        assert party.find("ISDEEMEDPOSITIVE").text == ("Yes" if sale else "No") and (float(party.find("AMOUNT").text) < 0) == sale
        assert len(v.find("DATE").text) == 8
    first = next(v for v in vs if v.get("VCHTYPE") == "Sales")
    assert first.find("BASICBUYERNAME").text == "Asha & Sons <Pune>"
    cn = next(v for v in vs if v.get("VCHTYPE") == "Credit Note")
    assert cn.find("VOUCHERNUMBER").text.startswith("CN/") and "Against INV/" in cn.find("NARRATION").text
