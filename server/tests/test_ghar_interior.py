"""Interior Sahayak: measurement maths from her numbers only, rate card + BOQ with blanks (never invented), quotation with GST
(CGST+SGST vs IGST) + design fee + stages, the quote / vendor order (real fingerprint) / price-changing change order / payment
request going ONLY by her tap with the card's hash, concept with labelled AI pictures, schedule clashes, snags with EXIF stripped,
handover warranty sheet in her words, title rule, DPDP forget, worker, tools (staff / customer actors) and API."""
import base64
import io
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.interior.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def it(env, monkeypatch):
    from app.interior import service as S
    events = []
    stored = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    S.EVENTS, S.STORED = events, stored
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _setup(S):
    S.save_settings(T, firm="Ghar Sajao Studio", gstin="27AAPFU0939F1ZV", fee_mode="percent", fee_value=10, upi_id="gharsajao@okhdfc",
                    phone="9876543210", warranty={"kitchen": "Hardware 10 saal (brand card), carcass 5 saal", "wardrobe": "5 saal carcass"})
    S.rate_save(T, "Wardrobe BWP ply + laminate", 1650, "sqft", "wardrobe", code="WD1", spec="BWP ply, 1 mm laminate")
    S.rate_save(T, "False ceiling gypsum", 95, "sqft", "false_ceiling", code="FC1")
    S.rate_save(T, "Painting Royale 2 coats", 28, "sqft", "painting", code="PT1")
    p = S.project_save(T, "Patil 2BHK", client="Sunil Patil", phone="9822012345", site="Flat 302, Baner", city="Pune", pin="411045",
                       client_state="27", home="2BHK", target_handover="2026-12-20")["project"]
    S.brief(T, p["id"], "Master bedroom", "japandi", 400000, ["sliding wardrobe", "study table"], ["glossy"], "kam furniture")
    S.measure(T, p["id"], "Master bedroom", "12'6\"", 11, 10, openings=[{"kind": "door", "w": 3, "h": 7}, {"kind": "window", "w": 5, "h": 4}])
    return p


def test_rules_measure_and_titles():
    from app.interior import rules as R
    assert R.length("12'6\"") == 12.5 and R.length("12 ft 6 in") == 12.5 and R.length("3.6 m") == pytest.approx(11.811, 0.01)
    assert R.length("3600 mm") == pytest.approx(11.811, 0.01) and R.length("") is None and R.length("abc") is None
    a = R.room_areas(12.5, 11, 10, [{"kind": "door", "w": 3, "h": 7}, {"kind": "window", "w": 5, "h": 4}])
    assert a["floor_sqft"] == 137.5 and a["perimeter_rft"] == 47 and a["openings_sqft"] == 41 and a["wall_sqft"] == 429
    assert a["skirting_rft"] == 44 and not a["missing"]
    half = R.room_areas(12, None, None)
    assert half["floor_sqft"] is None and set(half["missing"]) == {"chaudai", "unchai"}
    assert R.qty_from_area("wall", a, "sqft") == (429, "") and R.qty_from_area("floor", half, "sqft")[0] is None
    assert "ikai" in R.qty_from_area("floor", a, "nos")[1]
    assert R.kind_of("sliding wardrobe") == "wardrobe" and R.kind_of("gypsum false ceiling") == "false_ceiling"
    assert R.kind_of("modular kitchen tandem") == "kitchen" and R.style_of("Japandi vibe chahiye") == "japandi"
    assert R.title_problem("Ingle Architects") and not R.title_problem("Ingle Architects", "CA/2015/12345")
    assert not R.title_problem("Interior Designer")
    assert R.check_stages(R.DEFAULT_STAGES) == [] and R.check_stages([{"label": "A", "pct": 60}])
    assert sum(R.split_amount(100001, R.DEFAULT_STAGES)) == 100001
    assert R.gst_split(1000, 18, True) == {"cgst": 90.0, "sgst": 90.0, "igst": 0.0, "tax": 180.0}
    assert R.gst_split(1000, 18, False)["igst"] == 180.0
    assert R.clean("OTP 123456 card 4111 1111 1111 1111") == "OTP [hataya] card [hataya]"
    tasks = [{"room": "Hall", "kind": "false_ceiling", "start": "2026-11-01", "end": "2026-11-10"},
             {"room": "Hall", "kind": "flooring", "start": "2026-11-05", "end": "2026-11-08"}]
    assert R.sequence_problems(tasks)


def test_settings_title_rule_and_rate_card(it):
    S = it
    with pytest.raises(S.InteriorError) as e:
        S.save_settings(T, title="Interior Architect")
    assert "s.37" in str(e.value)
    with pytest.raises(S.InteriorError):
        S.save_settings(T, gstin="27AAPFU0939F1ZX")
    with pytest.raises(S.InteriorError):
        S.save_settings(T, stages=[{"label": "Advance", "pct": 30}])
    S.save_settings(T, stages=[{"label": "Advance", "pct": 20}, {"label": "Production", "pct": 50}, {"label": "Handover", "pct": 30}])
    assert not S.settings(T)["stages_starter"]
    with pytest.raises(S.InteriorError):
        S.rate_save(T, "Kitchen BWP", None)
    r = S.rate_save(T, "Kitchen base unit BWP", 2400, "rft", code="KB1")["rate"]
    assert r["kind"] == "kitchen" and r["unit"] == "rft"
    out = S.import_rates(T, data=b"Item,Unit,Rate,Category\nTV unit,sqft,1450,tv unit\nSofa 3 seater,nos,,furniture\n",
                         name="r.csv")
    assert out["added"] == 1 and len(out["bad"]) == 1
    assert {x["name"] for x in S.rates(T)} == {"Kitchen base unit BWP", "TV unit"}


def test_boq_blanks_quote_gst_and_her_tap(it):
    S = it
    p = _setup(S)
    lines = [{"room": "Master bedroom", "code": "WD1", "qty": 56},
             {"room": "Master bedroom", "code": "FC1"},                      # qty from the measured ceiling
             {"room": "Master bedroom", "code": "PT1", "qty_from": "wall"},  # from the measured net wall
             {"room": "Master bedroom", "name": "Study table walnut", "unit": "nos", "qty": 1}]  # no rate anywhere = blank
    b = S.boq_set(T, p["id"], lines)["boq"]
    by = {x["name"]: x for x in b["lines"]}
    assert by["False ceiling gypsum"]["qty"] == 137.5 and by["False ceiling gypsum"]["qty_src"].startswith("naap")
    assert by["Painting Royale 2 coats"]["qty"] == 429
    assert by["Study table walnut"]["rate"] is None and by["Study table walnut"]["blanks"] == ["rate"]
    assert len(b["blanks"]) == 1
    q = S.quote_make(T, p["id"])["quote"]
    assert q["number"] == "Q-0001/R1" and q["blanks"]
    with pytest.raises(S.InteriorError):
        S.quote_request(T, q["id"])                                         # blanks first
    # she gives the rate for that one line -> new revision without blanks
    S.boq_set(T, p["id"], [{"id": by["Study table walnut"]["id"], "room": "Master bedroom", "name": "Study table walnut", "unit": "nos",
                           "qty": 1, "rate": 18000}])
    q2 = S.quote_make(T, p["id"])["quote"]
    assert q2["number"] == "Q-0001/R2" and not q2["blanks"]
    assert S.quote_view(T, q["id"])["status"] == "superseded"
    t = q2["totals"]
    works = 56 * 1650 + 137.5 * 95 + 429 * 28 + 18000
    assert t["works"] == pytest.approx(works) and t["design_fee"] == pytest.approx(works * 0.10)
    assert t["intra"] and t["tax"] == pytest.approx((works + works * 0.1) * 0.18, abs=0.05)
    assert t["total"] == pytest.approx(works * 1.1 * 1.18, abs=0.05)
    draft_pdf = S.quote_pdf(T, q2["id"])
    assert draft_pdf.startswith(b"%PDF")
    card = S.quote_request(T, q2["id"])
    assert card["status"] == "needs_tap" and "interior_quote" in kinds(S)
    with pytest.raises(S.InteriorError):
        S.decide_quote(T, q2["id"], True, card["quote"]["hash"])            # the tool path never reaches it
    with pytest.raises(S.InteriorError):
        S.decide_quote(T, q2["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.InteriorError):
        S.quote_mark(T, q2["id"], "sent")                                   # not before her Haan
    out = S.decide_quote(T, q2["id"], True, card["quote"]["hash"], by_tap=True)
    assert out["quote"]["status"] == "approved" and out["quote"]["file_id"] and "wa.me/919822012345" in out["draft"]["wa"]
    assert S.STORED[-1][0].endswith("_quotation.pdf")
    with pytest.raises(S.InteriorError):
        S.quote_mark(T, q2["id"], "accepted", actor="staff:t1")
    S.quote_mark(T, q2["id"], "sent")
    acc = S.quote_mark(T, q2["id"], "accepted")
    assert acc["quote"]["status"] == "accepted"
    st = S.stages(T, p["id"])
    assert [x["pct"] for x in st["stages"]] == [10, 50, 35, 5]
    assert sum(x["amount"] for x in st["stages"]) == pytest.approx(t["total"], abs=0.01) == st["contract_total"]
    with pytest.raises(S.InteriorError):
        S.boq_set(T, p["id"], lines)                                        # after acceptance: change orders only


def test_inter_state_igst_and_sqft_fee_blank(it):
    S = it
    S.save_settings(T, firm="Studio", gstin="27AAPFU0939F1ZV", fee_mode="sqft", fee_value=150)
    S.rate_save(T, "Wardrobe", 1500, "sqft", code="W")
    p = S.project_save(T, "Goa villa", client="D'Souza", client_state="30")["project"]
    S.boq_set(T, p["id"], [{"room": "Bed 1", "code": "W", "qty": 40}])
    q = S.quote_make(T, p["id"])["quote"]
    assert not q["totals"]["intra"] and all(g["igst"] > 0 and g["cgst"] == 0 for g in q["totals"]["gst"])
    assert any("carpet area" in b for b in q["blanks"])                     # per-sqft fee needs HER area figure
    S.project_save(T, project=p["id"], carpet_sqft=1200)
    q = S.quote_make(T, p["id"])["quote"]
    assert q["totals"]["design_fee"] == 180000 and not q["blanks"]


def _accepted(S):
    p = _setup(S)
    S.boq_set(T, p["id"], [{"room": "Master bedroom", "code": "WD1", "qty": 56}, {"room": "Master bedroom", "code": "FC1"}])
    q = S.quote_make(T, p["id"])["quote"]
    c = S.quote_request(T, q["id"])
    S.decide_quote(T, q["id"], True, c["quote"]["hash"], by_tap=True)
    S.quote_mark(T, q["id"], "accepted")
    return p


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def test_vendor_order_needs_her_tap_and_fingerprint(it, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = it
    p = _accepted(S)
    S.vendor_save(T, "Raju Carpenter", "carpenter", "9000011111")
    line = [x for x in S.boq(T, p["id"])["lines"] if x["rate_code"] == "WD1"][0]
    with pytest.raises(S.InteriorError) as e:
        S.order_request(T, p["id"], "Raju", [{"line": line["id"]}])          # vendor's rate not given = refused
    assert "vendor ka rate" in str(e.value)
    o = S.order_request(T, p["id"], "Raju", [{"line": line["id"], "rate": 1700}], start="2026-11-02", finish="2026-11-20")
    assert o["status"] == "needs_tap" and o["order"]["amount"] == 56 * 1700
    assert any("margin" in c for c in o["order"]["checks"])                 # vendor costs more than the client rate
    again = S.order_request(T, p["id"], "Raju", [{"line": line["id"], "rate": 1700}])
    assert again.get("existing")
    oid, h = o["order"]["id"], o["order"]["hash"]
    with pytest.raises(S.InteriorError):
        S.decide_order(T, oid, True, h)                                     # not from the tool
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    assert ak.active_on(T)
    with pytest.raises(S.InteriorError) as e:
        S.decide_order(T, oid, True, h, by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.order_challenge(T, oid)
    stranger = Phone("phone-1")                                             # same id, other key: a copied app can't sign
    with pytest.raises(S.InteriorError):
        S.decide_order(T, oid, True, h, proof=stranger.sign(ch), by_tap=True)
    ch = S.order_challenge(T, oid)
    out = S.decide_order(T, oid, True, h, proof=phone.sign(ch), by_tap=True)
    assert out["order"]["status"] == "approved" and "wa.me/919000011111" in out["draft"]["wa"]
    assert S.STORED[-1][0].endswith("_work_order.pdf")
    assert S.project_view(T, p["id"])["status"] == "production"


def test_change_order_payment_request_and_paid(it):
    S = it
    p = _accepted(S)
    total0 = S.stages(T, p["id"])["contract_total"]
    # no price change -> applied straight away
    z = S.change_request(T, p["id"], "Laminate colour badla", add=[], remove=[])
    assert z["change"]["status"] == "applied"
    with pytest.raises(S.InteriorError):
        S.change_request(T, p["id"], "Mirror add", add=[{"room": "Master bedroom", "name": "Mirror", "qty": 1}])  # no rate = refused
    c = S.change_request(T, p["id"], "Study table add", add=[{"room": "Master bedroom", "name": "Study table", "unit": "nos", "qty": 1,
                                                             "rate": 20000}])
    assert c["status"] == "needs_tap" and c["change"]["delta"] == pytest.approx(23600) and "interior_change" in kinds(S)
    with pytest.raises(S.InteriorError):
        S.decide_change(T, c["change"]["id"], True, c["change"]["hash"])
    d = S.decide_change(T, c["change"]["id"], True, c["change"]["hash"], by_tap=True)
    assert d["change"]["status"] == "approved"
    st = S.stages(T, p["id"])
    assert st["contract_total"] == pytest.approx(total0 + 23600) and any(x["source"] for x in st["stages"])
    assert any(x["co"] for x in S.boq(T, p["id"])["lines"])
    s1 = st["stages"][0]
    r = S.pay_request(T, s1["id"])
    assert r["status"] == "needs_tap" and "interior_payment" in kinds(S)
    with pytest.raises(S.InteriorError):
        S.decide_payment(T, s1["id"], True, r["stage"]["hash"])
    out = S.decide_payment(T, s1["id"], True, r["stage"]["hash"], by_tap=True)
    assert out["stage"]["status"] == "requested" and out["draft"]["upi"].startswith("upi://pay?pa=gharsajao%40okhdfc")
    assert f"am={s1['amount']:.2f}" in out["draft"]["upi"]
    with pytest.raises(S.InteriorError):
        S.stage_paid(T, s1["id"], actor="staff:t1")
    paid = S.stage_paid(T, s1["id"], s1["amount"] - 1000, "UTR 1234")
    assert paid["stage"]["status"] == "paid" and "kam aaya" in paid["say"]


def _jpeg_with_gps() -> bytes:
    from PIL import Image
    img = Image.new("RGB", (64, 48), (200, 100, 50))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    exif[0x0132] = "2026:10:20 10:00:00"
    b = io.BytesIO()
    img.save(b, "JPEG", exif=exif)
    assert Image.open(io.BytesIO(b.getvalue())).getexif()
    return b.getvalue()


def test_concept_schedule_snags_handover_forget_and_tick(it, monkeypatch):
    S = it
    p = _accepted(S)
    monkeypatch.setattr(S, "_make_picture", lambda prompt: b"\x89PNG fake")
    c = S.concept(T, p["id"], "Master bedroom", pictures=2, file_ids=["her1"])["concept"]
    assert c["style"] == "Japandi" and len(c["items"]) == 3 and sum(1 for i in c["items"] if i["ai"]) == 2
    assert "interior_concept" in kinds(S) and "AI" in c["ai_note"]
    with pytest.raises(S.InteriorError):
        S.render3d(T, p["id"], "Kitchen")
    S.vendor_save(T, "Raju Carpenter", "carpenter", "9000011111")
    S.task_add(T, p["id"], "False ceiling", "false_ceiling", "Master bedroom", "", "2026-11-02", "2026-11-10")
    t2 = S.task_add(T, p["id"], "Wardrobe fitting", "wardrobe", "Master bedroom", "Raju", "2026-11-05", "2026-11-12")
    assert t2["checks"] and any("pehle shuru" in x for x in t2["checks"])
    p2 = S.project_save(T, "Other flat", client="X")["project"]
    clash = S.task_add(T, p2["id"], "Wardrobe", "wardrobe", "Bed", "Raju", "2026-11-10", "2026-11-11")
    assert any("Vendor usi samay" in x for x in clash["checks"])
    sn = S.snag_add(T, p["id"], "Shutter alignment", "Master bedroom", "Raju", data=_jpeg_with_gps())["snag"]
    path = S.snag_file(T, sn["id"], sn["photos"][0]["id"])
    from PIL import Image
    assert not Image.open(path).getexif()                                  # EXIF / GPS gone
    with pytest.raises(S.InteriorError):
        S.handover(T, p["id"])                                              # snag still open
    with pytest.raises(S.InteriorError):
        S.snag_status(T, sn["id"], "closed", actor="staff:t1")
    S.snag_photo(T, sn["id"], _jpeg_with_gps(), stage="fixed")
    S.snag_status(T, sn["id"], "closed")
    with pytest.raises(S.InteriorError):
        S.handover(T, p["id"], actor="staff:t1")
    h = S.handover(T, p["id"])
    assert S.STORED[-1][0].endswith("_handover_warranty.pdf") and "False ceiling" in " ".join(h["missing_warranty"])
    rows = {r["kind"]: r for r in S.warranty_rows(T, p["id"])}
    assert rows["wardrobe"]["terms"] == "5 saal carcass"
    # worker: late task + due stage once each, morning note once
    st = S.stages(T, p["id"])["stages"]
    S.stage_due(T, st[1]["id"], "2026-11-01")
    when = datetime(2026, 11, 20, 4, 0, tzinfo=timezone.utc)                # 9:30 am IST
    monkeypatch.setattr(S, "clock", lambda: when)
    o1 = S.tick(when)
    o2 = S.tick(when)
    assert o1["alerts"] >= 2 and o2["alerts"] == 0 and o1["morning"] == 1 and o2["morning"] == 0
    f = S.forget(T, p["id"])
    v = S.project_view(T, p["id"])
    assert v["phone"] == "" and v["client"] == "Client (hataya)" and "hata di" in f["say"]
    assert not path.exists()


def test_tools_actors_and_api(it):
    S = it
    from app.agent.interior_tools import INTERIOR_HANDLERS, INTERIOR_TOOLS
    from app.agent.tools import ToolError
    import asyncio
    names = {t["name"] for t in INTERIOR_TOOLS}
    assert names == {"interior", "interior_dekho"} == set(INTERIOR_HANDLERS)
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(INTERIOR_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("interior", action="settings", firm="Studio", fee_mode="none")
    run("interior", action="rate", name="Wardrobe", rate=1500, unit="sqft", code="W")
    p = run("interior", action="project", name="Shah flat", client="Shah", phone="9811122233")["project"]
    run("interior", action="measure", project=p["id"], room="Bed", l="10", w="10", h="9")
    run("interior", action="boq", project=p["id"], lines=[{"room": "Bed", "code": "W", "qty": 30}])
    q = run("interior", action="quote", project=p["id"])["quote"]
    sent = run("interior", action="quote_send", quote=q["number"])
    assert sent["status"] == "needs_tap"
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(INTERIOR_HANDLERS["interior"](staff, action="rate", name="X", rate=1))
    with pytest.raises(ToolError):
        asyncio.run(INTERIOR_HANDLERS["interior"](staff, action="handover", project=p["id"]))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(INTERIOR_HANDLERS["interior"](cust, action="brief", project=p["id"]))
    day = run("interior_dekho", what="day")
    assert day["waiting"]["quotes"]
    assert run("interior_dekho", what="project", project="Shah flat")["boq"]

    from app.interior.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/interior").status_code == 200
    assert c.post(f"/api/interior/quotes/{q['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/interior/quotes/{q['id']}/decide", json={"yes": True, "hash": sent["quote"]["hash"]})
    assert r.status_code == 200 and r.json()["quote"]["status"] == "approved"
    pdf = c.get(f"/api/interior/quotes/{q['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    up = c.post(f"/api/interior/projects/{p['id']}/snags", data={"what": "Paint patch", "room": "Bed"},
                files={"file": ("a.jpg", _jpeg_with_gps(), "image/jpeg")})
    assert up.status_code == 200
    sid, phid = up.json()["snag"]["id"], up.json()["snag"]["photos"][0]["id"]
    assert c.get(f"/api/interior/snags/{sid}/photos/{phid}").status_code == 200
    assert c.put("/api/interior/settings", json={"title": "Architect"}).status_code == 400
    assert c.post("/api/interior/rates/import", files={"file": ("r.csv", b"Item,Rate\nPelmet,350\n", "text/csv")}).json()["added"] == 1
