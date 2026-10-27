"""Propagent Sahayak (real estate agent / broker): rules (money words, need parsing, RERA numbers, checks, matching, stamp duty
only from her rates, TDS notes, commission), listings with photos without EXIF, publish only on her tap (hash, blockers, public
page that never shows the owner, changes take it down), leads synced to the Telecaller list, share / message cards, site visits
ordered by Maps distance, deals with Pehchaan Locker IDs, money papers with fingerprint, commission, DPDP forget, worker, tools
(staff / customer actors) and API."""
import asyncio
import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.propagent.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def pa(env, monkeypatch):
    from app.propagent import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_maps_km", lambda *a, **k: None)
    monkeypatch.setattr(S, "_model_json", lambda system, prompt: {})
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def _aadhaar():
    from app import idvault
    for n in range(234512340000, 234512349999):
        if idvault.verhoeff_ok(str(n)):
            return str(n)
    raise AssertionError


def _jpeg_with_gps() -> bytes:
    from PIL import Image
    im = Image.new("RGB", (64, 48), (200, 120, 40))
    ex = Image.Exif()
    ex[0x010F] = "PhoneMaker"
    ex[0x8825] = {1: "N", 2: (18.0, 31.0, 12.0)}
    b = io.BytesIO()
    im.save(b, "JPEG", exif=ex)
    return b.getvalue()


def test_rules():
    from app.propagent import rules as R
    assert R.money("45 lakh") == 45e5 and R.money("1.2 cr") == 1.2e7 and R.money("25k") == 25000 and R.money("₹25,000") == 25000
    assert R.money("") is None and R.money("abc") is None
    n = R.parse_need("2 ya 3 BHK flat chahiye Gorakshan Road mein 40 se 55 lakh, home loan lenge")
    assert n["bhk"] == [2, 3] and n["purpose"] == "" and n["kind"] == "flat" and n["budget_min"] == 40e5 and n["budget_max"] == 55e5
    assert n["loan"] and "Gorakshan Road" in n["localities"]
    t = R.parse_need("1 BHK kiraye par chahiye 15k tak semi furnished")
    assert t["purpose"] == "rent" and t["budget_max"] == 15000 and t["furnishing"] == "semi" and t["bhk"] == [1]
    assert R.rera_project_ok("P52100012345") and not R.rera_project_ok("P1234") and R.rera_agent_ok("A51800012345")
    assert not R.rera_agent_ok("X51800012345")
    # stamp duty: never without HER rate
    e = R.stamp_estimate(60e5, None)
    assert e["stamp"] is None and "stamp duty % (aapke area ka)" in e["missing"]
    e = R.stamp_estimate(60e5, {"stamp_pct": 6, "reg_pct": 1, "reg_cap": 30000}, market_value=65e5, women=False)
    assert e["base"] == 65e5 and e["stamp"] == 390000 and e["registration"] == 30000 and e["total"] == 420000 and e["base_note"]
    w = R.stamp_estimate(60e5, {"stamp_pct": 6, "women_less_pct": 1, "reg_flat": 30000}, women=True)
    assert w["stamp"] == 300000 and w["registration"] == 30000
    assert not R.tds_sale(45e5)["applies"] and R.tds_sale(60e5)["amount"] == 60000 and "393" in R.tds_sale(60e5)["section"]
    assert R.tds_sale(45e5, 52e5)["applies"]                       # stamp value over 50 lakh counts
    assert R.tds_sale(80e5, seller_nri=True)["amount"] is None
    assert R.tds_rent(60000)["applies"] and not R.tds_rent(40000)["applies"]
    c = R.commission(60e5, pct=1, gst_on=True)
    assert c["amount"] == 60000 and c["gst"] == 10800 and c["total"] == 70800 and c["sac"] == "997222"
    assert R.commission(None, months=1, rent=20000)["amount"] == 20000 and R.commission(60e5)["amount"] is None
    L = {"id": "x", "number": "L-0001", "status": "active", "purpose": "sale", "kind": "flat", "bhk": 2, "price": 50e5,
         "locality": "Gorakshan Road", "city": "Akola"}
    m = R.match({"purpose": "sale", "bhk": [2], "budget_max": 55e5, "localities": ["gorakshan road"]}, L)
    assert m and m["score"] >= 90 and any("budget" in x for x in m["why"])
    assert R.match({"purpose": "rent"}, L) is None and R.match({"budget_max": 30e5}, L) is None
    assert R.match({"nri": True}, {**L, "kind": "land"}) is None    # FEMA: no agricultural land for NRIs
    chk = R.listing_checks({**L, "new_project": True, "photos": [], "description": "Guaranteed return, RERA approved"},
                           {"state": "MH", "rera_agent_no": ""})
    joined = " ".join(chk["block"])
    assert "Malik ki haan" in joined and "P5" in joined and "QR" in joined and "A5" in joined and "Carpet" in joined
    assert any("Guaranteed" in x for x in chk["warn"]) and any("RERA approved" in x for x in chk["warn"])
    route, known = R.visit_order([{"where": "A"}, {"where": "C"}, {"where": "B"}], lambda a, b: {"AB": 1, "AC": 5, "BC": 1}.get(
        "".join(sorted(a + b)), 9))
    assert [p["where"] for p in route] == ["A", "B", "C"] and known
    keep, known = R.visit_order([{"where": "A"}, {"where": "C"}, {"where": "B"}], lambda a, b: None)
    assert [p["where"] for p in keep] == ["A", "C", "B"] and not known


def _ready_listing(S, **kw):
    S.save_settings(T, business="Ingle Realty", phone="9876500000", state="MH", rera_agent_no="A51800012345",
                    rera_valid_until=(datetime.now(timezone.utc) + timedelta(days=400)).date().isoformat())
    base = dict(purpose="sale", kind="flat", bhk=2, carpet_sqft=650, price="52 lakh", locality="Gorakshan Road", city="Akola",
                address="Flat 302, Sai Heights, Gorakshan Road", owner_name="Ramesh Patil", owner_phone="9822012345")
    base.update(kw)
    return S.save_listing(T, **base)["listing"]


def test_listing_publish_only_on_her_tap(pa):
    S = pa
    L = _ready_listing(S)
    assert L["number"] == "L-0001" and L["status"] == "active" and L["price"] == 52e5
    with pytest.raises(S.PropError) as e:                    # no owner's mandate yet
        S.publish_request(T, "L-0001")
    assert "Malik" in str(e.value)
    S.save_listing(T, "L-0001", mandate={"consent": True, "commission_pct": 1})
    ph = S.add_photo(T, "L-0001", _jpeg_with_gps())
    from PIL import Image
    p = S.photo_path(T, ph["photo"]["id"])
    assert not Image.open(p).getexif()                       # GPS / camera gone
    card = S.publish_request(T, "L-0001", "page")
    assert card["status"] == "needs_tap" and card["card"]["kind"] == "publish" and "propagent_card" in kinds(S)
    c = card["card"]
    assert "9822012345" not in c["body"]["show"] and "Sai Heights" not in c["body"]["show"] and "A51800012345" in c["body"]["show"]
    with pytest.raises(S.PropError):                         # a tool can never decide
        S.decide_card(T, c["id"], True, c["hash"])
    with pytest.raises(S.PropError):
        S.decide_card(T, c["id"], True, "wrong", by_tap=True)
    ok = S.decide_card(T, c["id"], True, c["hash"], by_tap=True)
    assert ok["card"]["status"] == "approved" and "/api/propagent/page/" in ok["result"]["url"]
    token = ok["result"]["url"].rsplit("/", 1)[1]
    code, html_ = S.page_html(token)
    assert code == 200 and "Ramesh" not in html_ and "9822012345" not in html_ and "Sai Heights" not in html_ and "52 lakh" in html_
    assert S.page_photo(token, 0) is not None and S.page_html("short")[0] == 404
    # a change takes the page down until she taps again
    out = S.save_listing(T, "L-0001", price="50 lakh")
    assert "band kiya" in out["say"] and S.page_html(token)[0] == 410
    # new project: RERA number + QR + agent number needed
    S.save_listing(T, purpose="sale", kind="flat", bhk=3, price="80 lakh", carpet_sqft=900, city="Akola", new_project=True,
                   project="Green Park", mandate={"consent": True})
    with pytest.raises(S.PropError) as e:
        S.publish_request(T, "L-0002")
    assert "RERA" in str(e.value) and "QR" in str(e.value)
    S.save_listing(T, "L-0002", rera_project_no="P52100012345")
    S.add_photo(T, "L-0002", _jpeg_with_gps(), kind="qr")
    cp = S.publish_request(T, "L-0002", "copy")["card"]
    r = S.decide_card(T, cp["id"], True, cp["hash"], by_tap=True)
    assert "P52100012345" in r["result"]["text"] and "maharera" in r["result"]["text"].lower()
    sh = S.publish_request(T, "L-0002", "sheet")["card"]
    assert S.decide_card(T, sh["id"], True, sh["hash"], by_tap=True)["result"]["file"]["file_id"]
    d = S.describe(T, "L-0001")
    assert d["by"] == "template" and "650" in d["text"]


def test_describe_model_numbers_guard(pa, monkeypatch):
    S = pa
    _ready_listing(S)
    monkeypatch.setattr(S, "_model_json", lambda s, p: {"text": "Sundar 2 BHK, station se 5 min, sirf 45 lakh!"})
    assert S.describe(T, "L-0001")["by"] == "template"            # invented numbers thrown away
    monkeypatch.setattr(S, "_model_json", lambda s, p: {"text": "Gorakshan Road par hawadaar 2 BHK, 650 sq ft carpet."})
    assert S.describe(T, "L-0001")["by"] == "model"


def test_leads_match_share_and_visits(pa, monkeypatch):
    S = pa
    _ready_listing(S, mandate={"consent": True})
    _ready_listing(S, bhk=3, price="90 lakh", locality="Jathar Peth", address="Lane 4, Jathar Peth", owner_phone="9822099999", mandate={"consent": True})
    out = S.save_lead(T, name="Suresh", phone="98220 11111", words="2 BHK flat Gorakshan Road mein 45 se 55 lakh", source="portal")
    assert out["new"] and out["lead"]["role"] == "buyer" and out["matches"][0]["number"] == "L-0001"
    assert out["lead"]["telecall_id"]                       # also in the Telecaller call list
    from app.telecall import service as T_
    assert any(x["name"] == "Suresh" for x in T_.leads(T))
    assert S.buyers_for(T, "L-0001")["leads"][0]["number"] == out["lead"]["number"]
    sh = S.share_request(T, "Suresh")
    assert sh["status"] == "needs_tap"
    body = sh["card"]["body"]
    assert "9822012345" not in body["text"] and "Gorakshan" in body["text"] and "A51800012345" in body["text"]
    ok = S.decide_card(T, sh["card"]["id"], True, sh["card"]["hash"], by_tap=True)
    assert ok["result"]["wa"].startswith("https://wa.me/919822011111")
    assert S.card_sent(T, sh["card"]["id"])["card"]["status"] == "sent"
    assert S.lead_view(T, "Suresh")["lead"]["stage"] == "contacted"
    cold = S.save_lead(T, name="Cold", phone="9822033333", source="cold", words="flat chahiye")
    with pytest.raises(S.PropError):
        S.share_request(T, cold["lead"]["id"])
    # site visit: Maps distance orders the stops
    dist = {("Gorakshan Road, Akola", "Jathar Peth, Akola"): (6.0, 15), ("Jathar Peth, Akola", "Gorakshan Road, Akola"): (6.0, 15)}
    monkeypatch.setattr(S, "_maps_km", lambda t, a, b: dist.get((_short(a), _short(b))))
    day = (S.today(T) + timedelta(days=2)).isoformat()
    v = S.plan_visit(T, "Suresh", ["L-0001", "L-0002"], day, "11:00")
    stops = v["visit"]["stops"]
    assert [s["number"] for s in stops] == ["L-0001", "L-0002"] and stops[0]["at"] == "11:00"
    assert len(v["cards"]) >= 2                              # client + owners: drafts on cards
    v2 = S.plan_visit(T, "Suresh", ["L-0002"], day, "11:15")
    assert any("pehle se" in w for w in v2["warn"])
    done = S.visit_done(T, v["visit"]["id"], {"L-0001": "pasand", "L-0002": "nahi"})
    assert "L-0001" in done["say"] and S.lead_view(T, "Suresh")["lead"]["stage"] == "negotiating"
    assert all(m["number"] != "L-0002" for m in S.matches(T, "Suresh")["matches"])


def _short(addr: str) -> str:
    for k in ("Gorakshan Road, Akola", "Jathar Peth, Akola"):
        if k.split(",")[0] in addr:
            return k
    return addr


def test_deal_papers_commission_and_forget(pa, monkeypatch):
    S = pa
    _ready_listing(S, mandate={"consent": True})
    S.save_settings(T, sale_pct=1, gst_on=True, rates={"akola": {"stamp_pct": 6, "reg_pct": 1, "reg_cap": 30000}})
    S.save_lead(T, name="Suresh", phone="9822011111", words="2 BHK Gorakshan Road 55 lakh tak")
    aad = _aadhaar()
    d = S.deal_new(T, "L-0001", "Suresh", price="51 lakh", token="1 lakh", token_mode="UPI", market_value="53 lakh",
                   ids_text=f"buyer aadhaar {aad} pan ABCPE1234F", ids_side="buyer", ids_person="Suresh")["deal"]
    assert d["number"] == "D-0001" and d["price"] == 51e5
    st = d["estimate"]["stamp"]
    assert st["base"] == 53e5 and st["stamp"] == 318000 and st["registration"] == 30000
    assert d["estimate"]["tds"]["amount"] == 51000
    assert d["commission"]["buyer"]["amount"] == 51000 and d["commission"]["buyer"]["gst"] == 9180
    assert {x["kind"] for x in d["ids"]} == {"aadhaar", "pan"} and all(aad not in str(x) for x in d["ids"])
    from app.propagent.models import PropagentDeal
    with S.session() as s:
        assert aad not in s.get(PropagentDeal, d["id"]).ids
    assert S.listing_view(T, "L-0001")["listing"]["status"] == "under_offer"
    tr = S.document_request(T, "D-0001", "token_receipt")["card"]
    assert tr["kind"] == "document" and tr["money"] == 1e5 and aad not in tr["body"]["text"] and "DRAFT" in tr["body"]["text"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    with pytest.raises(S.PropError) as e:
        S.decide_card(T, tr["id"], True, tr["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, tr["id"])
    assert ch["message"].startswith("hoola-approve|v1|default|propagent|")
    monkeypatch.setattr(ak, "active_on", lambda tenant: False)
    out = S.decide_card(T, tr["id"], True, tr["hash"], by_tap=True)
    assert out["card"]["status"] == "approved" and len(out["result"]["files"]) >= 1
    # a deal change makes a waiting paper card stale
    ol = S.document_request(T, "D-0001", "offer_letter")["card"]
    S.deal_update(T, "D-0001", price="50 lakh")
    st_ = S.decide_card(T, ol["id"], True, ol["hash"], by_tap=True)
    assert st_["card"]["status"] == "stale" and not st_["card"]["result"]
    rc = S.commission_received(T, "D-0001", "buyer", "50000", "NEFT", "UTR123456")
    assert rc["deal"]["commission"]["received"] == 50000 and rc["deal"]["commission"]["due"] > 0
    assert S.commission_report(T)["pending"]
    with pytest.raises(S.PropError):
        S.forget_lead(T, "Suresh")
    S.deal_status(T, "D-0001", "done")
    assert S.listing_view(T, "L-0001")["listing"]["status"] == "sold"
    S.forget_lead(T, "B-0001")
    from app import idvault
    assert not [r for r in idvault.list_(T) if "suresh" in r["person"].lower()]
    S.forget_owner(T, "L-0001")
    assert S.listing_view(T, "L-0001")["listing"]["owner_name"] == ""
    # rent deal: TDS note on rent above 50k
    S.save_listing(T, purpose="rent", kind="office", rent="65k", carpet_sqft=800, city="Akola", mandate={"consent": True})
    rd = S.deal_new(T, "L-0002")["deal"]
    assert rd["estimate"]["tds"]["applies"] and rd["checklist"][0]["key"] == "agreement"


def test_tick_morning_and_reminders(pa):
    S = pa
    S.save_settings(T, morning_time="00:00", rera_agent_no="A51800012345",
                    rera_valid_until=(S.today(T) + timedelta(days=20)).isoformat())
    _ready_listing(S, mandate={"consent": True})
    S.save_settings(T, rera_valid_until=(S.today(T) + timedelta(days=20)).isoformat())
    S.save_lead(T, name="Asha", phone="9822044444", words="2 BHK 55 lakh", next_when="2020-01-01 10:00")
    tomorrow = S.today(T) + timedelta(days=1)
    S.plan_visit(T, "Asha", ["L-0001"], tomorrow.isoformat(), "10:00")
    S.EVENTS.clear()
    n = datetime.now(timezone.utc)
    r = S.tick(n)
    assert r["rera"] == 1 and r["morning"] == 1 and "propagent_day" in kinds(S)
    again = S.tick(n)
    assert again["rera"] == 0 and again["morning"] == 0
    d = S.day(T)
    assert "RERA" in d["say"] and d["follow_ups"]


def test_tools_actors_and_api(pa, monkeypatch):
    from app.agent import propagent_tools as PT
    from app.agent.tools import Ctx, ToolError
    S = pa
    ctx = conv_ctx()
    out = asyncio.run(PT.propagent(ctx, "listing", words="2 BHK flat bikri ke liye", price="40 lakh", city="Akola",
                                   carpet_sqft=600, mandate={"consent": True}))
    assert out["new"] and out["listing"]["bhk"] == 2 and out["listing"]["purpose"] == "sale"
    staff = Ctx(T, ctx.conversation_id, actor="staff:abc")
    with pytest.raises(ToolError):
        asyncio.run(PT.propagent(staff, "settings", business="x"))
    with pytest.raises(ToolError):
        asyncio.run(PT.propagent(Ctx(T, ctx.conversation_id, actor="customer:wa:1"), "lead", name="x", phone="9822000000"))
    pub = asyncio.run(PT.propagent(staff, "publish", listing="L-0001", where="copy"))
    assert pub["status"] == "needs_tap"
    assert asyncio.run(PT.propagent_dekho(ctx, "rules"))["sources"]
    assert asyncio.run(PT.propagent_dekho(ctx, "steps", step="igr"))["steps"]
    names = {t["name"] for t in PT.PROPAGENT_TOOLS}
    assert names == set(PT.PROPAGENT_HANDLERS) == set(PT.PROPAGENT_LABELS)
    from app.propagent.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.get("/api/propagent").status_code == 200
    r = c.post("/api/propagent/listings", json={"purpose": "rent", "kind": "flat", "bhk": 1, "rent": "12k", "city": "Akola",
                                                "carpet_sqft": 420})
    assert r.status_code == 200 and r.json()["listing"]["rent"] == 12000
    assert c.post("/api/propagent/listings", json={"purpose": "swap"}).status_code == 400
    lid = r.json()["listing"]["id"]
    up = c.post(f"/api/propagent/listings/{lid}/photo", files={"file": ("a.jpg", _jpeg_with_gps(), "image/jpeg")})
    assert up.status_code == 200
    x = pub["card"]
    assert c.post(f"/api/propagent/cards/{x['id']}/decide", json={"hash": x["hash"]}).status_code == 400
    assert c.post(f"/api/propagent/cards/{x['id']}/decide", json={"yes": True, "hash": "nope"}).status_code == 400
    ok = c.post(f"/api/propagent/cards/{x['id']}/decide", json={"yes": True, "hash": x["hash"]})
    assert ok.status_code == 200 and ok.json()["card"]["status"] == "approved"
    ld = c.post("/api/propagent/leads", json={"name": "Neha", "phone": "9822055555", "words": "1 BHK kiraye 15k tak Akola"})
    assert ld.status_code == 200 and ld.json()["lead"]["role"] == "tenant"
    assert c.get(f"/api/propagent/leads/{ld.json()['lead']['id']}").json()["matches"]
    pg = c.get("/api/propagent/page/notarealtokenatall123")
    assert pg.status_code == 404 and "default-src 'none'" in pg.headers["content-security-policy"]
    dl = c.post("/api/propagent/deals", json={"listing": lid, "lead": ld.json()["lead"]["id"]})
    assert dl.status_code == 200 and dl.json()["deal"]["number"].startswith("D-")
    doc = c.post(f"/api/propagent/deals/{dl.json()['deal']['id']}/document", json={"kind": "offer_letter"})
    assert doc.status_code == 200 and doc.json()["status"] == "needs_tap"
    assert c.get("/api/propagent/commission").status_code == 200 and c.get("/api/propagent/steps/rera").json()["steps"]
