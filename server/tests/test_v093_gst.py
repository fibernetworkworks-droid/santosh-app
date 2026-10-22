"""v0.93 GST Sahayak: law checks (due dates, late fee, set-off, rates, HSN, POS), clients, bill checks, GSTR-1 portal JSON,
register + GSTR-2B import, reconciliation + IMS, GSTR-3B (2B-only ITC, 17(5), Rule 37, RCM in cash), her Haan before
filing, filing through the Computer Operator that stops before submit, ARN, notices, the calendar, tools + API."""
import asyncio
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx

T = "default"
CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin(body14: str) -> str:
    total = 0
    for i, ch in enumerate(body14):
        p = CH.index(ch) * (1 if i % 2 == 0 else 2)
        total += p // 36 + p % 36
    return body14 + CH[(36 - total % 36) % 36]


ME = gstin("27AAPFU0939F1Z")          # client in Maharashtra
B_MH = gstin("27AABCS1429B1Z")        # buyer in Maharashtra
B_UP = gstin("09AAACH7409R1Z")        # buyer in Uttar Pradesh
S_GJ = gstin("24AAACR5055K1Z")        # supplier in Gujarat
S_MH = gstin("27AAGCT1234K1Z")        # supplier in Maharashtra


def _fix_today(monkeypatch, d: date):
    monkeypatch.setattr("app.gstp.service.today", lambda t: d)


def test_rules():
    from app.gstp import rules as R
    assert R.due_date("gstr3b", "2026-10") == date(2026, 11, 20)
    assert R.due_date("gstr1", "2026-10") == date(2026, 11, 11)
    assert R.due_date("gstr1", "2026-09", "qrmp") == date(2026, 10, 13)
    assert R.due_date("gstr3b", "2026-09", "qrmp", "27") == date(2026, 10, 22)      # Maharashtra: 22nd group
    assert R.due_date("gstr3b", "2026-09", "qrmp", "09") == date(2026, 10, 24)      # UP: 24th group
    assert R.due_date("pmt06", "2026-10", "qrmp") == date(2026, 11, 25)
    assert R.due_date("cmp08", "2026-12", "composition") == date(2027, 1, 18)
    assert R.due_date("itc_last", "2026-02") == date(2026, 11, 30)
    assert R.due_date("gstr9", "2025-06") == date(2026, 12, 31)
    assert R.quarter_months("2026-08") == ["2026-07", "2026-08", "2026-09"] and R.fy_of("2026-02") == "2025-26"
    assert R.fp("2026-10") == "102026" and R.norm_period("10/2026") == "2026-10" and R.norm_period("102026") == "2026-10"
    assert R.late_fee("gstr3b", 10) == 500 and R.late_fee("gstr3b", 100, aato=1e7) == 2000
    assert R.late_fee("gstr3b", 400, aato=3e7) == 5000 and R.late_fee("gstr3b", 400, aato=9e7) == 10000
    assert R.late_fee("gstr3b", 100, nil=True) == 500 and R.late_fee("gstr3b", 5, nil=True) == 100
    assert R.interest(100000, 30) == 1479
    assert R.time_barred("gstr3b", "2022-06", "monthly", "27", date(2025, 8, 1))
    assert not R.time_barred("gstr3b", "2024-06", "monthly", "27", date(2025, 8, 1))
    assert R.pos_code("27-Maharashtra") == "27" and R.pos_code("Gujarat") == "24" and R.pos_code(9) == "09"
    p = R.check_line(date(2026, 10, 5), 12.0, "8471", 1e7, 1000, 0, 60, 60, True)
    assert any("purana slab" in x for x in p)
    p = R.check_line(date(2026, 10, 5), 18.0, "84", 9e7, 1000, 180, 0, 0, True)
    assert any("6 digit" in x for x in p) and any("CGST + SGST" in x for x in p)
    assert R.check_line(date(2026, 10, 5), 18.0, "998314", 1e7, 1000, 0, 90, 90, True) == []
    # set-off: IGST credit first on IGST, rest on CGST / SGST gaps; CGST can't pay SGST
    so = R.set_off({"igst": 1000, "cgst": 500, "sgst": 500}, {"igst": 1300, "cgst": 0, "sgst": 400})
    assert so["cash_total"] == 300 and so["cash"]["igst"] == 0          # 2000 tax - 1700 credit: least cash possible
    so = R.set_off({"igst": 0, "cgst": 500, "sgst": 500}, {"cgst": 900})
    assert so["cash"]["sgst"] == 500 and so["cash"]["cgst"] == 0
    so = R.set_off({"igst": 300, "cgst": 0, "sgst": 0}, {"cgst": 200, "sgst": 200})
    assert so["cash_total"] == 0


def test_clients_and_bill_checks(env, monkeypatch):
    from app.gstp import service as G
    _fix_today(monkeypatch, date(2026, 11, 2))
    with pytest.raises(G.GstError):
        G.add_client(T, "Galat", ME[:-1] + ("A" if ME[-1] != "A" else "B"))
    with pytest.raises(G.GstError):
        G.add_client(T, "Bada", ME, "qrmp", 9e7)
    c = G.add_client(T, "Sharma Traders", ME, "monthly", 3e7, portal_user="sharma_trd", contact_name="Ramesh",
                     contact_phone="9822000001")["client"]
    assert c["state"] == "27" and c["scheme"] == "monthly" and not c["einvoice"]
    r = G.add_doc(T, "Sharma", "out", "ST/001", "05-10-2026", B_MH, "Sai Agencies", items=[
        {"desc": "Steel almirah", "hsn": "9403", "qty": 2, "uqc": "NOS", "rate": 18, "txval": 20000}])
    d = r["doc"]
    assert r["saved"] and d["cgst"] == 1800 and d["sgst"] == 1800 and d["igst"] == 0 and d["pos"] == "27" and not r["problems"]
    r = G.add_doc(T, "Sharma", "out", "ST/002", "2026-10-06", B_UP, "Hari Traders", txval=50000, rate=18, hsn="9403", desc="Steel almirah")
    assert r["doc"]["igst"] == 9000 and r["doc"]["pos"] == "09"
    dup = G.add_doc(T, "Sharma", "out", "st-002", "2026-10-06", B_UP, txval=1, rate=18, hsn="9403")
    assert dup["saved"] is False and "pehle se" in dup["say"]
    bad = G.add_doc(T, "Sharma", "out", "ST/003", "07/10/2026", B_MH, txval=1000, rate=18, hsn="9403", igst=180)
    assert any("CGST + SGST" in p for p in bad["problems"])
    # purchase: car repair is 17(5) blocked; unregistered supplier gives no ITC
    p = G.add_doc(T, "Sharma", "in", "GJ-77", "2026-10-03", S_GJ, "Rathod Motors", txval=10000, rate=18, hsn="998714",
                  category="car repair")
    assert p["doc"]["itc"] is False and any("17(5)" in x for x in p["problems"]) and p["doc"]["igst"] == 1800
    u = G.add_doc(T, "Sharma", "in", "U1", "2026-10-03", "", "Local kabadi", txval=500, rate=5, hsn="7204")
    assert u["doc"]["itc"] is False


def _setup_month(G):
    G.add_client(T, "Sharma Traders", ME, "monthly", 3e7)
    G.add_doc(T, "Sharma", "out", "ST/001", "2026-10-05", B_MH, "Sai Agencies",
              items=[{"desc": "Steel almirah", "hsn": "9403", "qty": 2, "rate": 18, "txval": 20000}])
    G.add_doc(T, "Sharma", "out", "ST/002", "2026-10-06", B_UP, "Hari Traders", txval=50000, rate=18, hsn="9403", desc="Steel almirah", qty=5)
    G.add_doc(T, "Sharma", "out", "ST/003", "2026-10-07", "", "Walk-in", txval=10000, rate=18, hsn="9403", desc="Steel rack", qty=1)
    G.add_doc(T, "Sharma", "out", "ST/004", "2026-10-08", "", "Delhi customer", pos="07", txval=150000, rate=18, hsn="9403", qty=10)
    G.add_doc(T, "Sharma", "out", "CN/01", "2026-10-20", B_MH, "Sai Agencies", kind="cn", txval=2000, rate=18, hsn="9403", qty=1)
    G.add_doc(T, "Sharma", "in", "GJ/501", "2026-10-02", S_GJ, "Rathod Steel", txval=40000, rate=18, hsn="7208", desc="HR coil")
    G.add_doc(T, "Sharma", "in", "MH-88", "2026-10-04", S_MH, "Tejas Paints", txval=10000, rate=18, hsn="3208", desc="paint")
    G.add_doc(T, "Sharma", "in", "MH-90", "2026-10-09", S_MH, "Tejas Paints", txval=5000, rate=18, hsn="3208", desc="paint")
    G.add_doc(T, "Sharma", "in", "ADV-1", "2026-10-10", "", "Advocate", txval=10000, rate=18, hsn="998211", rcm=True)


TWO_B = {"data": {"gstin": ME, "rtnprd": "102026", "docdata": {
    "b2b": [{"ctin": S_GJ, "trdnm": "Rathod Steel", "supprd": "102026", "inv": [
        {"inum": "GJ/501", "dt": "02-10-2026", "val": 47200, "pos": "27", "rev": "N", "itcavl": "Y", "typ": "R",
         "items": [{"num": 1, "rt": 18, "txval": 40000, "igst": 7200, "cgst": 0, "sgst": 0, "cess": 0}]},
        {"inum": "GJ/509", "dt": "15-10-2026", "val": 1180, "pos": "27", "rev": "N", "itcavl": "Y",
         "items": [{"num": 1, "rt": 18, "txval": 1000, "igst": 180, "cgst": 0, "sgst": 0, "cess": 0}]}]},
            {"ctin": S_MH, "trdnm": "Tejas Paints", "supprd": "102026", "inv": [
                {"inum": "MH-0088", "dt": "04-10-2026", "val": 11800, "pos": "27", "rev": "N", "itcavl": "Y",
                 "items": [{"num": 1, "rt": 18, "txval": 10000, "igst": 0, "cgst": 850, "sgst": 850, "cess": 0}]}]}],
    "cdnr": [], "impg": []}}}


def test_gstr1_json_reconcile_3b_haan_file(env, monkeypatch):
    from app.gstp import service as G
    _fix_today(monkeypatch, date(2026, 11, 5))
    conv = conv_ctx().conversation_id
    _setup_month(G)
    r1 = G.prepare_gstr1(T, "Sharma", "2026-10", conv)
    v = r1["return"]
    assert v["status"] == "ready" and v["summary"]["b2b_invoices"] == 2 and v["summary"]["b2cl_invoices"] == 1
    with G.session() as s:
        j = json.loads(s.get(G.GstReturn, v["id"]).portal_json)
    assert j["gstin"] == ME and j["fp"] == "102026"
    b2b = {p["ctin"]: p for p in j["b2b"]}
    assert b2b[B_MH]["inv"][0]["idt"] == "05-10-2026" and b2b[B_MH]["inv"][0]["itms"][0]["itm_det"]["camt"] == 1800
    assert b2b[B_UP]["inv"][0]["pos"] == "09" and b2b[B_UP]["inv"][0]["itms"][0]["itm_det"]["iamt"] == 9000
    assert j["b2cl"][0]["pos"] == "07" and j["b2cl"][0]["inv"][0]["inum"] == "ST/004"     # inter-state B2C > 1 lakh
    assert j["b2cs"] == [{"sply_ty": "INTRA", "pos": "27", "typ": "OE", "rt": 18.0, "txval": 10000.0, "camt": 900.0, "samt": 900.0, "csamt": 0.0}]
    assert j["cdnr"][0]["nt"][0]["ntty"] == "C"
    assert {"hsn_b2b", "hsn_b2c"} <= set(j["hsn"]) and j["hsn"]["hsn_b2b"][0]["hsn_sc"] == "9403"
    assert j["hsn"]["hsn_b2b"][0]["txval"] == 68000.0                                        # 20000 + 50000 - 2000 (credit note)
    det = {d["doc_num"]: d["docs"][0] for d in j["doc_issue"]["doc_det"]}
    assert det[1]["totnum"] == 4 and det[5]["totnum"] == 1
    # her Haan first: filing without it is refused
    calls = []
    monkeypatch.setattr("app.operator.service.start", lambda *a, **k: calls.append((a, k)) or {"id": "op1", "task": a[1]})
    with pytest.raises(G.GstError):
        G.file_return(T, v["id"], conv)
    G.decide(T, v["id"], True)
    f = G.file_return(T, v["id"], conv)
    task = calls[0][0][1]
    assert f["return"]["status"] == "filing" and calls[0][0][3] and "STOP before 'File Statement'" in task and "Never pay" in task
    assert "password" in task and ME in task
    with pytest.raises(G.GstError):
        G.mark_filed(T, v["id"], "XYZ")
    assert G.mark_filed(T, v["id"], "AA271126012345A")["return"]["status"] == "filed"
    # GSTR-2B + reconciliation
    out = G.import_2b(T, "Sharma", "2026-10", data=json.dumps(TWO_B).encode(), name="2b.json")
    assert out["rows"] == 3
    with pytest.raises(G.GstError):
        G.import_2b(T, "Sharma", "2026-09", data=json.dumps(TWO_B).encode(), name="2b.json")
    rc = G.reconcile(T, "Sharma", "2026-10")
    assert rc["summary"]["matched"]["count"] == 1                     # GJ/501
    assert rc["summary"]["mismatch"]["count"] == 1                    # MH-0088 vs MH-88: 1700 vs 1800 tax
    assert rc["summary"]["only_2b"]["count"] == 1 and rc["only_2b"][0]["number"] == "GJ/509"
    assert rc["summary"]["only_books"]["count"] == 1 and rc["only_books"][0]["number"] == "MH-90"
    drafts = G.supplier_drafts(T, "Sharma", "2026-10")["drafts"]
    assert len(drafts) == 1 and "MH-90" in drafts[0]["text"]
    G.ims_decide(T, "Sharma", "2026-10", {rc["only_2b"][0]["id"]: "pending"})
    # GSTR-3B
    r3 = G.prepare_gstr3b(T, "Sharma", "2026-10", conv=conv)["return"]
    t = r3["tables"]
    assert t["3.1a"]["txval"] == 228000.0 and t["3.1a"]["igst"] == 36000.0 and t["3.1a"]["cgst"] == 2520.0
    assert t["3.1d"]["txval"] == 10000 and t["3.1d"]["cgst"] == 900
    assert t["4A"]["igst"] == 7200 and t["4A"]["cgst"] == 850 + 900               # 2B (pending GJ/509 left out) + RCM credit
    s3 = r3["summary"]
    assert s3["cash_split"]["cgst"] >= 900 and s3["late_days"] == 0                     # RCM always in cash
    assert any("IMS" in c for c in r3["checks"])
    msg = G.tax_message_draft(T, r3["id"])
    assert "challan" in msg["draft"]


def test_3b_blocked_rule37_late_and_qrmp(env, monkeypatch):
    from app.gstp import service as G
    G.add_client(T, "Patil Kirana", ME, "monthly", 1e7)
    G.add_doc(T, "Patil", "in", "C-1", "2026-03-05", S_MH, "Car Garage", txval=10000, rate=18, hsn="998714", category="car repair")
    G.add_doc(T, "Patil", "in", "M-1", "2026-03-06", S_MH, "Maal supplier", txval=20000, rate=18, hsn="1006", desc="rice")
    two_b = {"data": {"rtnprd": "032026", "docdata": {"b2b": [{"ctin": S_MH, "trdnm": "X", "inv": [
        {"inum": "C-1", "dt": "05-03-2026", "val": 11800, "rev": "N", "itcavl": "Y", "items": [{"txval": 10000, "cgst": 900, "sgst": 900}]},
        {"inum": "M-1", "dt": "06-03-2026", "val": 23600, "rev": "N", "itcavl": "Y", "items": [{"txval": 20000, "cgst": 1800, "sgst": 1800}]}]}]}}}
    G.import_2b(T, "Patil", "2026-03", data=json.dumps(two_b).encode(), name="x.json")
    _fix_today(monkeypatch, date(2026, 4, 30))                                              # 10 days late
    r = G.prepare_gstr3b(T, "Patil", "2026-03")["return"]
    assert r["tables"]["4B1"]["cgst"] == 900 and r["summary"]["late_days"] == 10 and r["summary"]["late_fee"] == 500
    # Rule 37: unpaid M-1 hits 180 days in September 2026
    G.add_doc(T, "Patil", "out", "S-9", "2026-09-02", "", "cash", txval=1000, rate=5, hsn="1006")
    _fix_today(monkeypatch, date(2026, 10, 1))
    r = G.prepare_gstr3b(T, "Patil", "2026-09")["return"]
    assert r["tables"]["4B2"]["cgst"] == 1800 and len(r["summary"]["rule37"]) == 1   # blocked car bill: no ITC taken, nothing to reverse
    G.mark_paid(T, "Patil", "M-1", "2026-08-01")
    r = G.prepare_gstr3b(T, "Patil", "2026-09")["return"]
    assert r["tables"]["4B2"]["cgst"] == 0 and not r["summary"]["rule37"]                # paid inside 180 days
    # QRMP: no monthly 3B, quarterly GSTR-1
    G.add_client(T, "Chhota Dukaan", B_UP, "qrmp", 1e7)
    with pytest.raises(G.GstError):
        G.prepare_gstr3b(T, "Chhota", "2026-08")
    G.add_doc(T, "Chhota", "out", "Q1", "2026-07-03", B_MH, txval=1000, rate=5, hsn="1006")
    G.add_doc(T, "Chhota", "out", "Q2", "2026-08-03", B_MH, txval=2000, rate=5, hsn="1006")
    _fix_today(monkeypatch, date(2026, 10, 2))
    q = G.prepare_gstr1(T, "Chhota", "2026-09")["return"]
    assert q["summary"]["b2b_invoices"] == 2 and q["summary"]["label"] == "GSTR-1"
    iff = G.prepare_gstr1(T, "Chhota", "2026-08")["return"]
    assert iff["summary"]["label"] == "IFF" and iff["summary"]["b2b_invoices"] == 1


def test_import_register_learning_notices_calendar(env, monkeypatch):
    from app.gstp import service as G
    _fix_today(monkeypatch, date(2026, 11, 22))
    G.add_client(T, "Sharma Traders", ME, "monthly", 3e7, contact_name="Ramesh")
    csv_ = ("Invoice No,Invoice Date,Party Name,GSTIN/UIN,Place of Supply,HSN/SAC,Item,Qty,Rate,Taxable Value,IGST,CGST,SGST,Invoice Value\n"
            f"A-1,03-10-2026,Sai Agencies,{B_MH},27-Maharashtra,9403,Steel almirah,1,18,10000,0,900,900,11800\n"
            f"A-1,03-10-2026,Sai Agencies,{B_MH},27-Maharashtra,9403,Steel rack,1,18,5000,0,450,450,17700\n"
            f"A-2,04-10-2026,Hari Traders,{B_UP},09-Uttar Pradesh,9403,Steel almirah,2,18,20000,3600,0,0,23600\n"
            "A-3,bad-date,X,,27,9403,thing,1,18,100,0,9,9,118\n")
    out = G.import_register(T, "Sharma", "out", data=csv_.encode(), name="sales.csv")
    assert out["saved"] == 2 and out["skipped"] == 1
    assert len(G.docs(T, "Sharma", "2026-10", "out")[0]["items"]) == 2
    again = G.import_register(T, "Sharma", "out", data=csv_.encode(), name="sales.csv")
    assert again["saved"] == 0 and again["duplicates"] == 2
    # approve -> item learned -> next bill without HSN / rate gets them
    r = G.prepare_gstr1(T, "Sharma", "2026-10")["return"]
    G.decide(T, r["id"], True)
    nb = G.add_doc(T, "Sharma", "out", "A-9", "2026-11-03", B_MH, items=[{"desc": "Steel almirah", "txval": 1000}])
    assert nb["doc"]["items"][0]["hsn"] == "9403" and nb["doc"]["cgst"] == 90
    # notices
    n = G.add_notice(T, "Sharma", "drc-01c", "2026-11-20", "ZD271126000123")["notice"]
    assert n["form"] == "DRC-01C" and n["due_on"] == "2026-11-27" and "Part B" in n["reply_form"]
    d = G.notice_draft(T, n["id"])
    assert ME in d["draft"] and "DRC-01C" in d["draft"]
    # calendar: October GSTR-3B (due 20 Nov) is late; October GSTR-1 was approved, not filed -> late too
    cal = G.calendar(T)
    late = {(x["kind"], x["period"]) for x in cal["late"]}
    assert ("gstr3b", "2026-10") in late and cal["late"][0].get("late_fee") is not None
    assert any(x["kind"] == "itc_last" for x in cal["due"]) and any(x["kind"] == "notice" for x in cal["due"])
    assert "Ramesh" in G.client_request_draft(T, "Sharma")["draft"]


def test_tools_role_api(env, monkeypatch):
    from app import main, voice
    from app.agent.tools import HANDLERS, Ctx, ToolError
    from app.employee import roles
    from app.gstp import service as G
    assert roles.duty_of("gst") == "gst_work" and roles.kind_of("gst_dekho") == "read" and "gst" in voice.VOICE_TOOL_NAMES
    assert roles.PRESETS["gst_practitioner"]["role"] == "gst_practitioner"
    _fix_today(monkeypatch, date(2026, 11, 5))
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(HANDLERS[tool](ctx, **a))      # noqa: E731
    run("gst", action="client", name="Sharma Traders", gstin=ME, scheme="monthly", aato=3e7)
    out = run("gst", action="bill", client="Sharma", direction="out", number="T1", date="05-10-2026", party_gstin=B_UP,
              txval=1000, rate=18, hsn="9403")
    assert out["doc"]["igst"] == 180
    assert run("gst_dekho", what="gstin", gstin=ME)["state"] == "Maharashtra"
    r = run("gst", action="gstr1", client="Sharma", period="2026-10")["return"]
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["gst"](staff, action="decide", return_id=r["id"], approve=True))
    with pytest.raises(ToolError):
        asyncio.run(HANDLERS["gst"](staff, action="file", return_id=r["id"]))
    js = run("gst", action="json", return_id=r["id"])
    assert js["file"]["name"].endswith("_GSTR1_102026.json")
    with TestClient(main.app) as cl:
        assert "gst" in cl.get("/healthz").json()["features"]
        assert cl.post("/api/gst/clients", json={"name": "X", "gstin": B_MH, "password": "secret"}).status_code == 400
        assert cl.get("/api/gst/clients").json()["clients"][0]["gstin"] == ME
        up = cl.post("/api/gst/2b", files={"file": ("2b.json", json.dumps(TWO_B).encode(), "application/json")},
                     data={"client": "Sharma", "period": "2026-10"})
        assert up.status_code == 200, up.text
        assert cl.get("/api/gst/reconcile", params={"client": "Sharma", "period": "2026-10"}).json()["summary"]["only_2b"]["count"] == 3
        rid = cl.post("/api/gst/returns", json={"client": "Sharma", "period": "2026-10", "kind": "gstr3b"}).json()["return"]["id"]
        assert cl.post(f"/api/gst/returns/{rid}/decide", json={"approve": True}).json()["return"]["status"] == "approved"
        assert cl.get(f"/api/gst/returns/{r['id']}/gstr1.json").json()["fp"] == "102026"
        assert cl.get("/api/gst/today").json()["clients"] == 1
        assert cl.post("/api/gst/notices", json={"client": "Sharma", "form": "ASMT-10"}).json()["notice"]["reply_form"] == "ASMT-11"
        assert cl.post("/api/gst/returns", json={"client": "Nobody", "period": "2026-10"}).status_code == 400
    assert G.settings(T)["enabled"]
