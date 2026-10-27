"""Influencer Sahayak: ASCI / CCPA disclosure rules (first line #ad, weak labels, video / story / podcast ticks, virtual / AI,
health qualification, disease-cure words, SEBI advice, crypto disclaimer), category gates (real-money games, tobacco /
alcohol, SEBI-regulated brand + unregistered creator, bought followers), roster + rate card from HER numbers only, PAN into the
locker, deals priced from the rate card, exclusivity clash refused in code (her force + reason), content calendar, every
outgoing step ONLY by her tap with the card's hash (stale after a change, blockers refuse), invoice with GST / TDS notes,
creator payout on her real fingerprint, receipts, metrics from her export -> report, worker alerts + morning note, DPDP forget,
tools + API."""
import asyncio
import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.influencer.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def inf(env, monkeypatch):
    from app.influencer import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    S.EVENTS, S.STORED, S.CLK = events, stored, clk
    return S


class Phone:
    def __init__(self, device_id):
        self.device_id = device_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()

    def sign(self, ch):
        sig = self.key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))
        return {"challenge_id": ch["challenge_id"], "device_id": self.device_id, "signature": base64.b64encode(sig).decode()}


def _roster(S):
    S.save_settings(T, agency="Tara Talent", gstin="27AAPFU0939F1ZV", upi_id="taratalent@okicici", commission_pct=20,
                    phone="9876543210")
    c = S.creator_save(T, name="Riya Sharma", phone="9822012345", niche="beauty, lifestyle", city="Pune", platform="instagram",
                       handle="@riyaglow", followers="1.2 lakh", avg_likes="4.5k", avg_comments="180", upi_id="riya@okaxis")
    S.rate_save(T, "Riya Sharma", "instagram", "reel", 40000, usage_days=30, usage_price=15000)
    S.rate_save(T, "Riya Sharma", "insta", "story", "8k")
    return c["creator"]


def _deal(S, **kw):
    base = dict(creator="Riya Sharma", brand="Glow Herbals", brand_contact="Anita", brand_phone="9811100022",
                brand_email="anita@glowherbals.in", brand_gstin="29AAGCB7383J1Z4", product="Aloe face wash",
                brief="Ek reel aur do stories, launch 5 Nov", deliverables=[{"platform": "instagram", "fmt": "reel", "due": "2026-11-05"},
                                                                         {"platform": "instagram", "fmt": "story", "qty": 2,
                                                                          "due": "2026-11-05"}])
    base.update(kw)
    return S.deal_save(T, **base)["deal"]


def test_rules():
    from app.influencer import rules as R
    ok = R.disclosure_check("#ad Mera naya favourite face wash\nCode RIYA10", "instagram", "post")
    assert ok["ok"] and ok["label_first"]
    assert not R.disclosure_check("Loving it #collab", "instagram", "post")["ok"]                       # weak label only
    buried = R.disclosure_check("Mera naya face wash\nbahut accha\n#ad", "instagram", "post")
    assert not buried["ok"] and "pehli line" in buried["block"][0]
    gift = R.disclosure_check("#gifted thank you brand", "instagram", "post", "barter")
    assert gift["ok"]
    vid = R.disclosure_check("#ad reel", "instagram", "reel", duration_s=30)
    keys = {c["key"] for c in vid["checklist"]}
    assert {"overlay", "spoken", "platform_tag"} <= keys and any("10 second" in w for w in vid["warn"] + [c["text"] for c in vid["checklist"]])
    assert R.video_window(12) == 3.0 and R.video_window(90) == 30.0
    assert not R.disclosure_check("#ad Hi from Kiara", "instagram", "post", virtual=True)["ok"]
    assert R.disclosure_check("#ad Hi from Kiara, a virtual influencer", "instagram", "post", virtual=True)["ok"]
    health = R.disclosure_check("#ad yeh churan diabetes jad se khatam karta hai", "instagram", "post", cats=["health"])
    assert not health["ok"] and "Drugs & Magic Remedies" in health["block"][0]
    q = R.disclosure_check("#ad mera protein shake", "instagram", "post", cats=["health"])
    assert q["ok"] and any("qualification" in w for w in q["warn"])
    fin = R.disclosure_check("#ad Is stock ko abhi kharido, target 500", "youtube", "video", cats=["finance"])
    assert any("SEBI" in b for b in fin["block"])
    assert R.disclosure_check("#ad Is stock ko abhi kharido, target 500 SEBI INH000012345", "youtube", "video", cats=["finance"],
                              sebi_reg="INH000012345")["ok"]
    assert not R.disclosure_check("#ad Buy BTC on CoinX", "instagram", "post", cats=["crypto"])["ok"]
    assert not R.disclosure_check("#ad rummy khelo", "instagram", "post", cats=["gaming_money"])["ok"]
    assert R.categories("Fantasy cricket app pe paisa jeeto") == ["gaming_money"]
    assert R.categories("Kurti sale, returns 7 din") == []                                        # 'returns' is not finance
    assert R.fake_engagement("10k followers kharid lo") and R.fake_engagement("SMM panel") and not R.fake_engagement("followers badhe")
    assert R.money("1.5 lakh") == 150000 and R.money("25k") == 25000 and R.money("") is None and R.count("1.2M") == 1200000
    g = R.gst_of(40000, True, "27", "29", False, False)
    assert g["igst"] == 7200 and g["cgst"] == 0
    assert R.gst_of(40000, True, "27", "27", False, False)["cgst"] == 3600
    assert R.gst_of(40000, False, "27", "29", False, False)["total_tax"] == 0
    assert R.gst_of(40000, True, "27", "", True, True)["total_tax"] == 0
    t = R.tds_note(40000, 25000, 20000, 0)
    assert t["fee_tds"] == 4000 and t["barter_tds"] == 2500 and "393(1)" in t["lines"][0]
    assert R.tds_note(30000, 0, 0, 0)["fee_tds"] == 0
    rows = R.parse_metrics("Report,,\nPermalink,Views,Reach,Likes,Comments,Shares,Saves\n"
                           "https://www.instagram.com/reel/AbC1/,52000,31000,2100,90,40,120\nTotal,52000,31000,2100,90,40,120\n")
    assert len(rows) == 1 and rows[0]["reach"] == 31000 and R.engagement(rows[0])["er_pct"] == round(2350 / 31000 * 100, 2)
    sig = R.fake_signals(100000, 40000, 10, [{"on": "2026-10-01", "followers": 60000}, {"on": "2026-10-05", "followers": 100000}])
    assert len(sig) == 3


def test_roster_rates_and_gates(inf):
    S = inf
    cr = _roster(S)
    assert cr["number"] == "C-001" and cr["handles"][0]["followers"] == 120000 and cr["handles"][0]["on"] == "2026-10-23"
    with pytest.raises(S.InfluencerError):
        S.rate_save(T, "Riya Sharma", "youtube", "video", None)                                   # no price = refused, never guessed
    with pytest.raises(S.InfluencerError):
        S.creator_save(T, name="Bot Bhai", notes="buy 5k followers every month")
    with pytest.raises(S.InfluencerError):
        S.creator_save(T, "Riya Sharma", sebi_reg="12345")
    S.creator_save(T, "Riya Sharma", pan="ABCPE1234F")
    v = S.creator_view(T, "@riyaglow")
    assert v["pan"].endswith("234F") or "X" in v["pan"]
    from app import idvault
    assert any(r["kind"] == "pan" for r in idvault.list_(T))
    # deal priced from the rate card
    d = _deal(S)
    assert d["fee"] == 56000 and {x["price_from"] for x in d["deliverables"]} == {"rate card"} and len(d["posts"]) == 3
    with pytest.raises(S.InfluencerError):
        _deal(S, brand="RummyKing", product="Rummy cash game")                                    # Online Gaming Act 2025
    with pytest.raises(S.InfluencerError):
        _deal(S, brand="Daaru Club soda", product="whisky")
    S.creator_save(T, name="Arjun Finance", platform="youtube", handle="@arjunfin", followers="80k")
    with pytest.raises(S.InfluencerError) as e:
        S.deal_save(T, creator="Arjun Finance", brand="ZipBroker", product="demat account", sebi_regulated=True,
                    deliverables=[{"platform": "youtube", "fmt": "video", "price": 50000}])
    assert "SEBI" in str(e.value)
    S.creator_save(T, "Arjun Finance", sebi_reg="INH000012345")
    ok = S.deal_save(T, creator="Arjun Finance", brand="ZipBroker", product="demat account", sebi_regulated=True,
                     deliverables=[{"platform": "youtube", "fmt": "video", "price": 50000}])
    assert ok["deal"]["fee"] == 50000 and "finance" in ok["deal"]["categories"]
    # unpriced deliverable stays blank
    out = S.deal_save(T, creator="Riya Sharma", brand="Nimbu Co", product="nimbu pani",
                      deliverables=[{"platform": "youtube", "fmt": "short"}])
    assert out["deal"]["fee"] is None and out["deal"]["deliverables"][0]["price"] is None and "daam nahi" in out["say"]
    pc = S.pitch_request(T, out["deal"]["number"])
    with pytest.raises(S.InfluencerError):
        S.decide(T, pc["card"]["id"], True, pc["card"]["hash"], by_tap=True)          # [daam?] blocks the pitch


def test_exclusivity_clash_refused(inf):
    S = inf
    _roster(S)
    d = _deal(S, excl_category="skincare face wash", excl_from="2026-11-01", excl_to="2026-12-31")
    S.stage(T, d["number"], "contracted")
    with pytest.raises(S.InfluencerError):
        S.stage(T, d["number"], "done", actor="staff:s1")
    with pytest.raises(S.InfluencerError) as e:
        _deal(S, brand="Pure Skin", product="face wash", deliverables=[{"platform": "instagram", "fmt": "reel", "due": "2026-11-20"}])
    assert "exclusivity" in str(e.value)
    with pytest.raises(S.InfluencerError):                                                         # force needs a reason
        S.deal_save(T, creator="Riya Sharma", brand="Pure Skin", product="face wash", force=True,
                    deliverables=[{"platform": "instagram", "fmt": "reel", "due": "2026-11-20"}])
    with pytest.raises(S.InfluencerError):                                                         # staff can't force
        S.deal_save(T, actor="staff:s1", creator="Riya Sharma", brand="Pure Skin", product="face wash", force=True,
                    reason="brand ne permission di", deliverables=[{"platform": "instagram", "fmt": "reel", "due": "2026-11-20"}])
    ok = S.deal_save(T, creator="Riya Sharma", brand="Pure Skin", product="face wash", force=True,
                     reason="Glow Herbals ne email par permission di", deliverables=[{"platform": "instagram", "fmt": "reel",
                                                                                     "due": "2026-11-20"}])
    assert "takrav" in ok["say"]
    # after the window: no clash
    _deal(S, brand="Fresh Face", product="face wash", deliverables=[{"platform": "instagram", "fmt": "reel", "due": "2027-01-15"}])
    with pytest.raises(S.InfluencerError):
        S.stage(T, d["number"], "lost")                                                            # needs a reason


def test_content_cards_only_by_her_tap(inf):
    S = inf
    _roster(S)
    d = _deal(S)
    p = d["posts"][0]["number"]
    with pytest.raises(S.InfluencerError):
        S.content_request(T, p)                                                                     # no caption yet
    r = S.post_save(T, p, caption="Mera naya face wash, 7 din mein glow! #collab", duration_s=30)
    assert not r["post"]["check"]["ok"]
    with pytest.raises(S.InfluencerError):
        S.golive_request(T, p)
    c = S.content_request(T, p)                                                                     # card can be made ...
    with pytest.raises(S.InfluencerError):
        S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=False)                         # ... tools never decide
    with pytest.raises(S.InfluencerError) as e:
        S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)                          # blockers refuse her Haan
    assert "Haan nahi ho sakti" in str(e.value)
    S.post_save(T, p, caption="#ad Mera naya face wash, 7 din mein glow!")
    with pytest.raises(S.InfluencerError):                                                          # old card is stale now
        S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    assert S.card_view(T, c["card"]["id"])["status"] == "stale"
    c = S.content_request(T, p)
    assert S.content_request(T, p)["existing"]
    out = S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    assert "wa.me/919811100022" in out["draft"]["wa"] and out["draft"]["mail"].startswith("mailto:anita@")
    assert S.posts(T, d["number"])[0]["status"] == "with_brand"
    g = S.golive_request(T, p)
    with pytest.raises(S.InfluencerError) as e:                                                     # brand OK not recorded
        S.decide(T, g["card"]["id"], True, g["card"]["hash"], by_tap=True)
    assert "Brand ki haan" in str(e.value)
    S.post_save(T, p, brand_ok=True)
    g = S.golive_request(T, p)
    out = S.decide(T, g["card"]["id"], True, g["card"]["hash"], by_tap=True)
    assert "#ad" in out["draft"]["text"] and "[ ]" in out["draft"]["text"]
    no = S.message_request(T, d["number"], "Kal call karein?")
    r = S.decide(T, no["card"]["id"], False, no["card"]["hash"], "abhi nahi", by_tap=True)
    assert r["card"]["status"] == "rejected"
    S.post_save(T, p, live_url="https://www.instagram.com/reel/AbC1/")
    assert S.deal_view(T, d["number"])["stage"] == "pitched" or S.deal_view(T, d["number"])["stage"] == "lead"
    with pytest.raises(S.InfluencerError):
        S.post_save(T, p, caption="changed after live")


def test_money_invoice_payout_fingerprint(inf, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    S = inf
    _roster(S)
    d = _deal(S, barter_value=25000, barter_items="face wash kit", kind="mixed")
    with pytest.raises(S.InfluencerError):
        S.invoice_request(T, d["number"])                                                           # not contracted yet
    S.stage(T, d["number"], "contracted")
    m = S.deal_view(T, d["number"])["money"]
    assert m["taxable"] == 56000 and m["gst"]["igst"] == 10080 and m["total"] == 66080          # MH agency -> KA brand: IGST
    assert m["tds"]["fee_tds"] == 5600 and m["tds"]["barter_tds"] == 2500
    assert m["commission"] == 11200 and m["creator_due"] == 44800
    inv = S.invoice_request(T, d["number"])
    out = S.decide(T, inv["card"]["id"], True, inv["card"]["hash"], by_tap=True)
    assert out["invoice_no"] == "INF/2627/0001" and S.STORED[-1][1].startswith(b"%PDF")
    with pytest.raises(S.InfluencerError):
        S.invoice_request(T, d["number"])                                                           # once
    with pytest.raises(S.InfluencerError):
        S.deal_save(T, d["number"], fee=99999)                                                     # money frozen after invoice
    po = S.payout_request(T, d["number"])
    with pytest.raises(S.InfluencerError) as e:
        S.decide(T, po["card"]["id"], True, po["card"]["hash"], by_tap=True)                        # brand hasn't paid
    assert "paise darj nahi" in str(e.value)
    with pytest.raises(S.InfluencerError):
        S.received(T, d["number"], 60480, 5600, actor="staff:s1")
    r = S.received(T, d["number"], 60480, 5600, "UTR998877665544")
    assert "TDS" in r["say"] and r["money"]["outstanding"] == 0
    po = S.payout_request(T, d["number"])                                                          # received changed -> new card
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.InfluencerError) as e:
        S.decide(T, po["card"]["id"], True, po["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, po["card"]["id"])
    with pytest.raises(S.InfluencerError):
        S.decide(T, po["card"]["id"], True, po["card"]["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.card_challenge(T, po["card"]["id"])
    out = S.decide(T, po["card"]["id"], True, po["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert out["draft"]["upi"].startswith("upi://pay?pa=riya%40okaxis") and "am=44800.00" in out["draft"]["upi"]
    S.payout_sent(T, d["number"], "UTR5566")
    assert S.deal_view(T, d["number"])["payout"]["sent"] is True


def test_metrics_report_tick_forget(inf):
    S = inf
    _roster(S)
    S.save_settings(T, morning_time="09:00")
    d = _deal(S)
    S.stage(T, d["number"], "contracted")
    p0, p1, p2 = [x["number"] for x in d["posts"]]
    S.post_save(T, p0, caption="#ad Glow!")
    S.post_save(T, p0, live_url="https://www.instagram.com/reel/AbC1/")
    S.post_save(T, p1, caption="#ad story 1")
    S.post_save(T, p1, live_url="https://www.instagram.com/stories/riyaglow/111/")
    csv = ("Permalink,Views,Reach,Likes,Comments,Shares,Saves,Link clicks\n"
           "https://www.instagram.com/reel/AbC1/,52000,31000,2100,90,40,120,300\n"
           "https://www.instagram.com/stories/riyaglow/111/,9000,8000,0,0,10,0,150\n"
           "https://www.instagram.com/reel/OTHER/,1,1,1,1,1,1,1\n")
    im = S.import_metrics(T, d["number"], csv.encode())
    assert sorted(im["matched"]) == sorted([p0, p1]) and len(im["unmatched"]) == 1
    S.metrics(T, p2, views="2.1k", reach="1900", likes=0)
    rp = S.report(T, d["number"])["numbers"]
    assert rp["views"] == 63100 and rp["clicks"] == 450 and rp["cpm"] == round(56000 / 63100 * 1000, 2)
    rc = S.report_request(T, d["number"])
    out = S.decide(T, rc["card"]["id"], True, rc["card"]["hash"], by_tap=True)
    assert "63,100" in out["draft"]["text"]
    # worker: p2 due 5 Nov; on 4 Nov 10 am IST -> due tomorrow + morning note; on 6 Nov -> late
    S.CLK["t"] = datetime(2026, 11, 4, 4, 30, tzinfo=timezone.utc)
    t1 = S.tick(S.CLK["t"])
    assert t1["alerts"] >= 1 and t1["morning"] == 1
    assert S.tick(S.CLK["t"])["alerts"] == 0                                                         # once each
    S.CLK["t"] = datetime(2026, 11, 6, 4, 30, tzinfo=timezone.utc)
    S.tick(S.CLK["t"])
    kinds = [p["kind"] for k, p in S.EVENTS if k == "influencer_alert"]
    assert "due_tomorrow" in kinds and "late" in kinds
    # DPDP forget: not while deals run; after done
    with pytest.raises(S.InfluencerError):
        S.forget(T, creator="Riya Sharma")
    S.stage(T, d["number"], "done")
    S.forget(T, deal=d["number"])
    S.forget(T, creator="Riya Sharma")
    v = S.creator_view(T, "C-001")
    assert v["status"] == "forgotten" and v["phone"] == "" and v["handles"] == [] and S.deal_view(T, d["number"])["brand_phone"] == ""


def test_tools_and_api(inf):
    S = inf
    from app.agent.influencer_tools import INFLUENCER_HANDLERS, INFLUENCER_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in INFLUENCER_TOOLS} == {"influencer", "influencer_dekho"} == set(INFLUENCER_HANDLERS)
    for t in INFLUENCER_TOOLS:
        props = t["input_schema"]["properties"]
        assert all(r in props for r in t["input_schema"]["required"])
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(INFLUENCER_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("influencer", action="settings", agency="Tara Talent", upi_id="tara@okicici", commission_pct=15)
    run("influencer", action="creator", name="Kabir", platform="youtube", handle="@kabirvlogs", followers="2.3 lakh")
    run("influencer", action="rate", creator="Kabir", platform="youtube", fmt="video", price=90000)
    dd = run("influencer", action="deal", creator="Kabir", brand="TravelGo", product="trip app", brand_phone="9811100022",
             deliverables=[{"platform": "youtube", "fmt": "video", "due": "2026-11-12"}])["deal"]
    assert dd["fee"] == 90000
    sent = run("influencer", action="pitch", deal=dd["number"])
    assert sent["status"] == "needs_tap"
    chk = run("influencer", action="check", caption="TravelGo se trip book kiya #partnership")
    assert chk["ok"] is False
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    for a in ({"action": "settings", "agency": "X"}, {"action": "paid", "deal": dd["number"], "amount": 10},
              {"action": "forget", "creator": "Kabir"}):
        with pytest.raises(ToolError):
            asyncio.run(INFLUENCER_HANDLERS["influencer"](staff, **a))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(INFLUENCER_HANDLERS["influencer"](cust, action="creator", name="Y"))
    with pytest.raises(ToolError):
        run("influencer", action="creator", name="Spam", notes="engagement pod join karo")
    assert run("influencer_dekho", what="day")["waiting"] == 1
    assert run("influencer_dekho", what="ratecard", creator="Kabir")["rates"][0]["price"] == 90000

    from app.influencer.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/influencer").status_code == 200
    cid, h = sent["card"]["id"], sent["card"]["hash"]
    assert c.post(f"/api/influencer/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/influencer/cards/{cid}/decide", json={"yes": True, "hash": h})
    assert r.status_code == 200 and r.json()["card"]["status"] == "approved"
    assert S.deal_view(T, dd["number"])["stage"] == "pitched"
    assert c.get(f"/api/influencer/deals/{dd['number']}/contract.pdf").content.startswith(b"%PDF")
    assert c.get("/api/influencer/creators/Kabir/ratecard.pdf").content.startswith(b"%PDF")
    assert c.get("/api/influencer/calendar", params={"month": "2026-11"}).json()["days"]["2026-11-12"]
    assert c.put("/api/influencer/settings", json={"upi_id": "not a upi"}).status_code == 400
    assert c.post("/api/influencer/check", json={"caption": "#ad hello"}).json()["ok"] is True
    p = c.get("/api/influencer/posts", params={"deal": dd["number"]}).json()["posts"][0]["number"]
    assert c.patch(f"/api/influencer/posts/{p}", json={"caption": "#ad TravelGo se Goa"}).status_code == 200
    assert c.post(f"/api/influencer/posts/{p}/content").json()["status"] == "needs_tap"
    assert c.post(f"/api/influencer/deals/{dd['number']}/nope").status_code == 404
