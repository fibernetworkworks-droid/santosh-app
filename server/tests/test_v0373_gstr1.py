"""v0.373 GSTR-1 FILE (App Sahayak Phase 37): the month's GSTR-1 JSON (GST offline tool shape) from the same numbers as her
invoices: b2b for a buyer GSTIN, b2cs netted with consumer credit notes, cdnr for a registered buyer's credit note, hsn and
doc_issue ranges; needs her GSTIN; never filed by Hoola."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0314_app_backend import _built
from tests.test_v0352_kaam_baanto import _acct, _login
from tests.test_v0355_gst_bill import GOOD
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

BUYER = "29AAACR5055K1ZZ"


def test_gstr1_json(droid_env):
    from app.appmaker import gst as G
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
    month = HS._ist(now()).strftime("%Y-%m")
    assert c.get(f"/api/apps/{aid}/gstr1", params={"month": month}).status_code == 409      # no GSTIN yet
    c.put(f"/api/apps/{aid}/gst", json={"gstin": GOOD, "rate": 5, "hsn": "1905"})
    buyer_ok = G.valid_gstin(BUYER[:14] + G.check_digit(BUYER[:14]))
    bg = BUYER[:14] + G.check_digit(BUYER[:14])
    assert buyer_ok
    mk = lambda addr, extra=None: c.post(f"{api}/c/orders", json={"name": "Asha", "phone": "9876543210", "address": addr,
                                                                  "cart": [{"id": p1["id"], "qty": 2}], **(extra or {})}, headers=ha).json()
    o1, o2, o3 = mk("Kothrud, Pune"), mk("Kothrud, Pune"), mk("Bengaluru, Karnataka")
    for o in (o1, o2, o3):
        c.post(f"{api}/c/orders/{o['id']}", json={"status": "Delivered"}, headers=hr)
        c.get(f"/api/apps/{aid}/data/orders/{o['id']}/receipt")
    c.post(f"{api}/c/orders/{o2['id']}", json={"status": "Cancelled"}, headers=hr)          # consumer credit note nets B2CS
    # o3: pretend the buyer gave a GSTIN (B2B) by writing it on the row the way a GST field would
    from app.appmaker import backend as BE
    import app.appmaker.gst as GM
    orig = GM.compute

    def with_buyer(r, col, d):
        x = orig(r, col, d)
        if d.get("name") == "B2B":
            x["buyer_gstin"] = bg
        return x
    BE._merge(o3["id"], {"name": "B2B"})
    GM.compute = with_buyer
    try:
        r = c.get(f"/api/apps/{aid}/gstr1", params={"month": month})
    finally:
        GM.compute = orig
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert f"GSTR1-{GOOD}-{month}.json" in r.headers["content-disposition"]
    j = json.loads(r.content)
    assert j["gstin"] == GOOD and j["fp"] == month[5:7] + month[:4]
    assert j["b2b"][0]["ctin"] == bg and j["b2b"][0]["inv"][0]["inum"].startswith(f"INV/{G.fy()}/")
    assert j["b2b"][0]["inv"][0]["itms"][0]["itm_det"]["iamt"] > 0                         # Karnataka buyer: IGST
    assert j["b2b"][0]["inv"][0]["idt"].count("-") == 2
    cs = j["b2cs"]
    assert len(cs) == 1 and cs[0]["sply_ty"] == "INTRA" and cs[0]["pos"] == "27" and cs[0]["rt"] == 5
    one = G.compute(BE.by_key(key), next(x for x in BE.schema(BE.by_key(key))["collections"] if x["key"] == "orders"),
                    BE._assign_info(BE.bid(BE.by_key(key)), [o1["id"]])[o1["id"]])["totals"]["taxable"]
    assert cs[0]["txval"] == pytest.approx(one, abs=0.02)                                   # o2's credit note netted it
    assert j["hsn"]["data"][0]["hsn_sc"] == "1905" and j["hsn"]["data"][0]["uqc"] == "NOS"
    docs = {d["doc_num"]: d["docs"][0] for d in j["doc_issue"]["doc_det"]}
    assert docs[1]["totnum"] == 3 and docs[5]["totnum"] == 1 and "cdnr" not in j          # the credit note was a consumer's
