"""After-sales Sahayak: installed base (import, warranty from install), schedules -> due list, reminder drafts (utility vs
marketing, opt-out), technicians -> area-grouped slots, no double booking, travel gap, visit done -> next due from real date /
usage, cover (warranty / AMC / customer), charge only by her tap, report PDF with photo + signature, business WhatsApp only by
her tap (approved template, marketing opt-in), AMC revenue, warranty claims, morning note, tools + API."""
import asyncio
import io
from datetime import date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.aftersales.service  # noqa: F401  (tables for init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 22, 9, 0)      # Thursday
SHEET = ("Customer Name,Mobile,Product,Brand,Model,Serial No,Install Date,Warranty,AMC Expiry,Area,Pincode\n"
         "Ramesh Patil,9822000001,RO purifier,Kent,Grand Plus,KT1001,2026-03-10,12,,Kothrud,411038\n"
         "Sunita Joshi,9822000002,Split AC,Voltas,183V,VL2002,2025-04-02,1 year,2026-11-10,Kothrud,411038\n"
         "Anil More,9822000003,Inverter battery,Luminous,RC18000,LM3003,2026-05-01,36,,Baner,411045\n"
         ",,,,,,,,,,\n"
         "Bad Row,12345,RO,Kent,X,KT9,2026-01-01,12,,Aundh,411007\n")


@pytest.fixture
def S(env, monkeypatch):
    from app.aftersales import service as S
    monkeypatch.setattr(S, "now_local", lambda t: NOW)
    return S


def setup(S):
    S.save_settings(T, business="Shree Sales & Service", phone="9890000000", prices={"visit": 300, "parts": {"sediment filter": 250}})
    r = S.import_units(T, SHEET.encode(), "base.csv")
    assert r["added"] == 3 and r["skipped"] == 1 and "line" in r["problems"][0]
    S.save_tech(T, "Sunil", phone="9890011111", skills=["ro", "inverter"], areas=["Kothrud", "411045"], per_day=4)
    S.save_tech(T, "Vijay", phone="9890022222", skills=["ac"], areas=[], per_day=4)


def test_rules():
    from app.aftersales import rules as R
    assert R.ptype_of("Kent RO purifier") == "ro" and R.ptype_of("Voltas split AC") == "ac" and R.ptype_of("Luminous tubular battery") == "inverter"
    assert R.ptype_of("Honda Activa") == "two_wheeler" and R.ptype_of("xyz") == "other"
    nd = R.next_due("ac", date(2026, 4, 5), None)                    # +6 months = 5 Oct -> snapped to 1 Sep (post-monsoon)
    assert nd["due"] == date(2026, 9, 1) and "garmi" in nd["why"]
    nd = R.next_due("two_wheeler", date(2026, 10, 1), None, reading=12000, per_day=60, last_reading_on=date(2026, 10, 1))
    assert nd["due"] == date(2026, 10, 1) + __import__("datetime").timedelta(days=50) and "km" in nd["why"]
    assert R.next_due("ro", None, date(2026, 3, 10), {"ro": {"months": 3}})["due"] == date(2026, 6, 10)
    w = R.warranty_until(date(2026, 3, 20), 12, date(2026, 3, 1))
    assert w["until"] == date(2027, 3, 20) and "install" in w["note"]
    assert R.coverage(date(2026, 10, 1), date(2027, 1, 1), None, "")["by"] == "warranty"
    c = R.coverage(date(2026, 10, 1), date(2026, 1, 1), date(2027, 1, 1), "non_comprehensive")
    assert c["by"] == "amc" and c["labour"] and not c["parts"]
    assert R.classify("Aapka AMC khatam, abhi renew karein 20% off") == "MARKETING" and R.classify("Service due hai") == "UTILITY"
    assert R.same_area({"pincode": "411038"}, {"pincode": "411038"}) and not R.same_area({"area": "Baner"}, {"area": "Kothrud"})
    assert R.covers_area(["4110"], {"pincode": "411038"}) and not R.covers_area(["Baner"], {"area": "Kothrud", "pincode": "411038"})
    from app.whatsapp.templates import check_template
    for k, t in R.TEMPLATES.items():
        assert check_template(k, t["language"], t["category"], t["body"], t["example"], t.get("footer"))["ok"], k


def test_base_due_and_reminders(S):
    setup(S)
    us = S.units(T)
    ro = next(u for u in us if u["ptype"] == "ro")
    assert ro["warranty_until"] == "2027-03-10" and ro["next_due"] == "2026-07-10" and ro["customer"]["pincode"] == "411038"
    ac = next(u for u in us if u["ptype"] == "ac")
    assert ac["amc"]["until"] == "2026-11-10" and ac["amc"]["active"] and ac["warranty_until"] == "2026-04-02"
    with pytest.raises(S.AsError):
        S.save_unit(T, ptype="ro", serial="KT1001", name="X", phone="9822000009")        # same serial twice
    d = S.due(T, 15)
    assert any(x["id"] == ro["id"] and x["overdue"] for x in d["due"]) and d["amc_ending"][0]["id"] == ac["id"]
    # her own schedule: RO every 3 months -> due moves
    sch = S.set_schedule(T, "ro", months=3)
    assert sch["updated"] == 1 and S.get_unit(T, ro["id"])["next_due"] == "2026-06-10"
    # opt-out customer gets no draft
    S.save_customer(T, phone="9822000003", no_messages=True)
    S.save_unit(T, unit="LM3003", last_service="2026-07-01")                              # inverter due 1 Oct
    r = S.remind(T, 15)
    assert len(r["messages"]) == 2 and all(m["category"] == "UTILITY" for m in r["messages"])                # RO + AC, not the opted-out one
    m1 = next(m for m in r["messages"] if m["phone"] == "9822000001")
    assert "wa.me/919822000001" in m1["wa_link"] and "Shree Sales" in m1["text"] and r["skipped"] and "mana" in r["say"]
    assert S.remind(T, 15)["messages"] == []                                                # no duplicate draft
    amc = S.remind(T, kind="amc")
    assert amc["messages"][0]["category"] == "MARKETING" and "marketing" in amc["say"]


def test_slots_booking_and_visit(S):
    setup(S)
    sl = S.slots(T, "KT1001", days=3)
    assert sl["slots"] and all(x["tech"] == "Sunil" for x in sl["slots"])             # RO skill + Kothrud area
    first = S.book(T, "KT1001", "2026-10-23 10:00", "Sunil", problem="paani kam, pin 1234 hai")
    v1 = first["visit"]
    assert v1["number"] == "V-0001" and "[hataya]" in v1["problem"] and first["message"]["category"] == "UTILITY"
    assert "V-0001" in first["message"]["text"] and "Sunil" in first["message"]["text"]
    with pytest.raises(S.AsError, match="do visit"):
        S.book(T, "LM3003", "2026-10-23 10:30", "Sunil")                                  # double booking never
    with pytest.raises(S.AsError, match="aane-jaane"):
        S.book(T, "LM3003", "2026-10-23 11:00", "Sunil")                                  # Baner after Kothrud: no travel time
    ok = S.book(T, "LM3003", "2026-10-23 11:00", "Sunil", force=True)
    assert ok["warnings"]
    # next slot for another Kothrud machine is grouped on the same day near Sunil's Kothrud visit
    S.save_unit(T, ptype="ro", brand="Aquaguard", serial="AQ1", name="Meena Kale", phone="9822000004", area="Kothrud", pincode="411038",
                installed_on="2026-01-05")
    near = S.slots(T, "AQ1", days=3)["slots"][0]
    assert near["start"].startswith("2026-10-23") and "area" in near["why"]
    with pytest.raises(S.AsError):
        S.book(T, "KT1001", "2026-10-21 10:00", "Sunil")                                  # past
    auto = S.book(T, "VL2002")                                                            # no time given: best free slot, AC tech
    assert auto["visit"]["tech"]["name"] == "Vijay"
    jc = S.job_card(T, v1["id"])
    assert "Warranty" in jc["text"] and "Sediment filter" in jc["text"] and "wa.me/919890011111" in jc["wa_link"]
    # RO in warranty: free, next due from the visit date
    done = S.complete(T, v1["id"], ["sediment", "tds"], {"tds_in": 420, "tds_out": 180}, [{"name": "Sediment filter", "qty": 1}],
                      notes="membrane theek", signed_by="Ramesh", done_at="2026-10-23 11:00")
    assert done["charge"]["status"] == "none" and done["claim_parts"] == ["Sediment filter"] and "TDS 180" in " ".join(done["flags"])
    assert S.get_unit(T, "KT1001")["next_due"] == "2027-02-23" and done["missing"]
    # AC: AMC non-comprehensive -> labour free, part charged from her list (no price -> needs her total)
    av = auto["visit"]["id"]
    d2 = S.complete(T, av, {"Filter saaf": "ok", "Gas pressure check": "not_ok"}, {"gas_psi": 60}, [{"name": "Gas top-up"}], done_at="2026-10-23 16:00")
    assert d2["charge"]["status"] == "needs_price" and d2["charge"]["lines"][0]["amount"] == 0
    with pytest.raises(S.AsError, match="tap"):
        S.decide_charge(T, av, True, 1500)                                                # the tool path can never approve
    with pytest.raises(S.AsError, match="total"):
        S.decide_charge(T, av, True, None, by_tap=True)
    ap = S.decide_charge(T, av, True, 1500, by_tap=True)
    assert ap["charge"]["status"] == "approved" and ap["charge"]["total"] == 1500
    assert "baaki" in S.mark_paid(T, av, 1000)["say"]
    # photo + signature + report
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), (30, 90, 160)).save(buf, "JPEG")
    S.add_photo(T, av, buf.getvalue(), "after")
    sig = io.BytesIO()
    Image.new("RGBA", (300, 100), (0, 0, 0, 0)).save(sig, "PNG")
    assert S.add_photo(T, av, sig.getvalue(), "signature")["signed"]
    with pytest.raises(S.AsError):
        S.add_photo(T, av, b"not a picture")
    pdf = S.report_pdf(T, av)
    assert pdf[:4] == b"%PDF" and len(pdf) > 3000
    rep = S.report(T, av)
    assert rep["file"]["name"].endswith(".pdf") and "Charge" in rep["message"]["text"] and rep["message"]["template"] == "service_visit_report"
    t = S.techs(T)
    assert next(x for x in t if x["name"] == "Vijay")["visits_done"] == 1
    with pytest.raises(S.AsError):
        S.report_pdf(T, ok["visit"]["id"])                                                # not done yet
    rs = S.reschedule(T, ok["visit"]["id"], "2026-10-24 15:00")
    assert rs["visit"]["start"] == "2026-10-24 15:00"
    assert S.set_status(T, ok["visit"]["id"], "cancelled")["visit"]["status"] == "cancelled"


def test_amc_claims_and_send(S):
    setup(S)
    from app.db import Template, session
    S.set_amc(T, "KT1001", "comprehensive", "2026-10-01", 12, 3, 1800)
    a = S.amc_view(T)
    assert a["count"] == 2 and a["yearly_value"] == 1800 and a["expiring"][30]
    assert S.get_unit(T, "KT1001")["amc"]["plan"] == "comprehensive"
    v = S.book(T, "KT1001", "2026-10-23 10:00", "Sunil", kind="repair")["visit"]
    S.complete(T, v["id"], [], {}, [{"name": "Membrane", "price": 1900}], done_at="2026-10-23 11:00")
    assert S.get_visit(T, v["id"])["charge"]["status"] == "none"                         # warranty (and comprehensive AMC) cover parts
    c = S.claim(T, visit=v["id"], fault="low flow")
    assert c["claim"]["number"] == "W-0001" and c["claim"]["part"] == "Membrane" and not c["warning"]
    up = S.claim_update(T, "W-0001", "settled", brand_ref="KNT-4471", settled=900)
    assert up["claim"]["status"] == "settled" and S.claims(T)["brand_days"]["Kent"] == 0
    # business WhatsApp only on her tap, approved template, marketing needs opt-in
    msg = S.remind(T, kind="amc")["messages"][0]
    with pytest.raises(S.AsError, match="tap"):
        asyncio.run(S.send_message(T, msg["id"], "template"))
    with pytest.raises(S.AsError, match="marketing"):
        asyncio.run(S.send_message(T, msg["id"], "template", by_tap=True))
    S.save_customer(T, phone="9822000002", marketing_ok=True)
    with pytest.raises(S.AsError, match="approved"):
        asyncio.run(S.send_message(T, msg["id"], "template", by_tap=True))
    sub = asyncio.run(S.submit_template(T, "amc_expiry_notice", by_tap=True))
    assert sub["status"] == "PENDING"
    with session() as s:
        s.query(Template).filter(Template.name == "amc_expiry_notice").update({"status": "APPROVED"})
    sent = asyncio.run(S.send_message(T, msg["id"], "template", by_tap=True))
    assert sent["status"] == "sent" and sent["via"] == "template"
    with pytest.raises(S.AsError):
        asyncio.run(S.send_message(T, msg["id"], "template", by_tap=True))               # once
    with pytest.raises(S.AsError, match="kabhi message"):
        rm = S.remind(T, 15)["messages"][0]
        asyncio.run(S.send_message(T, rm["id"], "business", by_tap=True))                # no 24 h window
    assert S.message_mark(T, rm["id"], "sent")["status"] == "sent"
    tl = S.templates(T)
    assert {t["name"] for t in tl} >= {"service_due_reminder", "amc_expiry_notice"} and all(t["check"]["ok"] for t in tl)
    d = S.day(T)
    assert d["parts"] and S.send_morning(T)["text"].startswith("After-sales:")


def test_tools_and_api(S):
    from app.agent.aftersales_tools import AFTERSALES_HANDLERS as H
    from app.agent.tools import Ctx, ToolError
    setup(S)
    ctx = conv_ctx()
    run = lambda tool, c=ctx, **a: asyncio.run(H[tool](c, **a))      # noqa: E731
    b = run("service_desk", action="book", unit="Anil", start="kal 11 baje", tech="Sunil")
    assert b["visit"]["start"] == "2026-10-23 11:00"
    staff = Ctx(T, ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        run("service_desk", c=staff, action="settings", business="X")
    with pytest.raises(ToolError):
        run("service_desk", c=staff, action="paid", visit=b["visit"]["id"], amount=100)
    dn = run("service_desk", c=staff, action="done", visit=b["visit"]["number"], checklist=["Distilled water top-up"], not_ok=["Backup test"],
             readings={"backup_minutes": 20}, done_at="2026-10-23 12:00")
    assert dn["visit"]["checklist"]["Backup test"] == "not_ok" and dn["charge"]["status"] == "none"       # inverter in warranty
    assert any("Backup" in f for f in dn["flags"])
    S.save_unit(T, ptype="ro", brand="Kent", serial="OLD1", name="Purana Graahak", phone="9822000077", area="Kothrud", pincode="411038",
                installed_on="2024-01-01", warranty_months=12)
    ov = S.book(T, "OLD1", "2026-10-24 10:00", "Sunil")["visit"]
    oc = S.complete(T, ov["id"], [], {}, [], done_at="2026-10-24 11:00")
    assert oc["charge"]["status"] == "pending" and oc["charge"]["total"] == 300
    assert run("service_desk_dekho", what="visit", visit=b["visit"]["id"])["status"] == "done"
    assert run("service_desk_dekho", what="rules")["never"]
    assert run("service_desk_dekho", what="due", within=30)["due"]
    app = FastAPI()
    from app.aftersales.api import make_router
    app.include_router(make_router(lambda: None, lambda: "default"))
    with TestClient(app) as cl:
        o = cl.get("/api/aftersales").json()
        assert o["techs"] and o["schedules"]
        vid = ov["id"]
        ch = cl.get(f"/api/aftersales/visits/{vid}").json()["charge"]
        bad = cl.post(f"/api/aftersales/visits/{vid}/charge", json={"yes": True, "hash": "wrong"})
        assert bad.status_code == 400
        ok = cl.post(f"/api/aftersales/visits/{vid}/charge", json={"yes": True, "hash": S._charge_hash(ch)})
        assert ok.status_code == 200 and ok.json()["charge"]["status"] == "approved", ok.text
        assert cl.get(f"/api/aftersales/visits/{vid}/report.pdf").content[:4] == b"%PDF"
        import base64
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), "red").save(buf, "JPEG")
        ph = cl.post(f"/api/aftersales/visits/{vid}/photo", json={"kind": "work", "data_b64": base64.b64encode(buf.getvalue()).decode()}).json()
        assert cl.get(f"/api/aftersales/visits/{vid}/photos/{ph['id']}").status_code == 200
        assert cl.post(f"/api/aftersales/visits/{vid}/bogus", json={}).status_code == 404
        imp = cl.post("/api/aftersales/import", json={"name": "b.csv", "data_b64": base64.b64encode(
            b"Name,Mobile,Product,Serial No,Install Date\nKiran,9822000099,CCTV DVR,HK77,2026-02-01\n").decode()})
        assert imp.status_code == 200 and imp.json()["added"] == 1, imp.text
        sl = cl.get("/api/aftersales/slots", params={"unit": "HK77"})
        assert sl.status_code == 200
        bk = cl.post("/api/aftersales/visits", json={"unit": "HK77"})
        assert bk.status_code == 200 and bk.json()["visit"]["number"], bk.text
        rm = cl.post("/api/aftersales/remind", json={"within": 30}).json()
        mid = rm["messages"][0]["id"] if rm["messages"] else cl.get("/api/aftersales/messages").json()["messages"][0]["id"]
        assert cl.post(f"/api/aftersales/messages/{mid}/sent").json()["status"] == "sent"
        assert cl.post(f"/api/aftersales/messages/{mid}/send", json={"via": "template"}).status_code == 400
        assert cl.get("/api/aftersales/amc").status_code == 200 and cl.get("/api/aftersales/templates").json()["templates"]
        assert cl.post("/api/aftersales/claims", json={"unit": "HK77", "part": "DVR adaptor"}).status_code == 200
        assert cl.post("/api/aftersales/units", json={"name": "Z", "phone": "123"}).status_code == 400
