"""Artist Sahayak (musician's manager): rules (offer words, windows, ISRC / UPC / IPI, splits, settlement, TDS / GST notes,
release plan), roster + registrations, gigs where a double booking is refused in code (same artist, travel gap, shared band
member, her blocked days, also at the tap), holds that expire, every outgoing step only by HER tap with the card's hash, money
in plain numbers, payout statement on her fingerprint, releases with ISRC checks and final metadata, DPDP forget, worker,
tools + actors, API."""
import asyncio
import base64
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.artistmgr.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def am(env, monkeypatch):
    from app.artistmgr import service as S
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
    S.save_settings(T, agency="Sur Talent", upi_id="surtalent@okhdfc", commission_pct=15, royalty_pct=10, same_city_gap=120,
                    travel_gap=480, distributors=[{"name": "Believe", "share_pct": 15, "lead_days": 21, "payout": "monthly"}],
                    terms="Cancellation 30 din pehle: advance wapas; baad mein advance nahi.")
    S.artist_save(T, "Mehfil Band", "band", "sufi", "9822011111", city="Pune",
                  members=[{"name": "Arif", "role": "vocals", "phone": "9822022222", "split_pct": 40},
                           {"name": "Ravi", "role": "dhol", "phone": "9822033333", "split_pct": 30},
                           {"name": "Sana", "role": "keys", "split_pct": 30}],
                  min_fee=80000, rider={"tech": ["4 vocal mics", "Monitor x2"], "hospitality": ["Green room"]})
    S.artist_save(T, "Ravi Dhol Beats", "instrumentalist", city="Pune", members=[{"name": "Ravi", "phone": "9822033333"}])


def test_rules():
    from app.artistmgr import rules as R
    t0 = date(2026, 10, 23)
    o = R.parse_offer("Hi, I am Kunal from Blue Frog. Club gig 14 Nov raat 9 baje Mumbai mein, 90 min set, fee 1.5 lakh. "
                      "Call 98200 12345, kunal@bluefrog.in. OTP 445566", t0)
    assert o["day"] == "2026-11-14" and o["start"] == "21:00" and o["fee"] == 150000 and o["set_minutes"] == 90
    assert o["phone"] == "9820012345" and o["event_type"] == "club" and o["city"] == "Mumbai" and o["promoter"] == "Kunal"
    assert R.hhmm("8:30 pm") == "20:30" and R.hhmm("raat 1 baje") == "01:00" and R.hhmm("shaam 7 baje") == "19:00" and R.hhmm("") == ""
    assert R.money_of("75k") == 75000 and R.money_of("Rs 80,000") == 80000 and R.money_of("koi fee nahi") is None
    a = R.window(t0, "22:00", "01:00")
    assert a[1] - a[0] == timedelta(hours=3)
    b = R.window(t0 + timedelta(days=1), "02:00", "", 60)
    assert R.clashes(a, b, 120) and not R.clashes(a, b, 0)
    assert R.gap_needed("Pune", "pune", 120, 480) == 120 and R.gap_needed("Pune", "", 120, 480) == 480
    assert R.isrc("in-k40-14-00212") == "INK401400212" and R.isrc("INK4014002") == "" and R.isrc_pretty("INK401400212") == "IN-K40-14-00212"
    assert R.upc_ok("036000291452") and not R.upc_ok("036000291453") and R.upc_ok("4006381333931")
    assert R.ipi_ok("00052210040") and not R.ipi_ok("12345")
    assert R.split_problems([{"split_pct": 50}, {"split_pct": 40}]) and not R.split_problems([{"split_pct": 60}, {"split_pct": 40}])
    assert [x["amount"] for x in R.share(100.0, [{"split_pct": 33.33}, {"split_pct": 33.33}, {"split_pct": 33.34}])] == [33.33, 33.33, 33.34]
    m = R.settlement(100000, 90000, 10000, 15, [{"amount": 5000, "paid_by": "manager"}, {"amount": 2000, "paid_by": "artist"}])
    assert m["commission"] == 15000 and m["due_from_promoter"] == 0 and m["fully_paid"] and m["net_to_artist"] == 70000
    assert R.settlement(100000, 0, 0, None, [])["commission"] is None
    assert "194C" in R.tds_note("club", 1) and "film artist" in R.tds_note("recording", 1)
    assert R.gst_note("", "", 200000)[0] == 0 and R.gst_note("27AAPFU0939F1ZV", "classical", 120000)[0] == 0
    assert R.gst_note("27AAPFU0939F1ZV", "classical", 160000)[0] == 18 and R.gst_note("27AAPFU0939F1ZV", "", 1)[0] == 18
    assert R.gst_lines(1000, 18, True) == {"tax": 180.0, "cgst": 90.0, "sgst": 90.0, "igst": 0.0}
    plan = R.release_plan(date(2026, 12, 1), 21, t0)
    assert plan[0]["by"] == "2026-11-10" and plan[1]["by"] == "2026-11-24"
    assert R.release_plan(date(2026, 12, 1), None, t0)[0]["by"] == ""
    assert R.clean("otp 445566 card 4111 1111 1111 1111") == "otp [hataya] card [hataya]"
    assert set(R.REGS) >= {"iprs", "isamra", "ppl", "isrc", "ipi"}


def test_roster_regs_and_settings(am):
    S = am
    with pytest.raises(S.ArtistError):
        S.save_settings(T, upi_id="not upi")
    with pytest.raises(S.ArtistError):
        S.save_settings(T, commission_pct=80)
    with pytest.raises(S.ArtistError):
        S.artist_save(T, "Duo", members=[{"name": "A", "split_pct": 60}, {"name": "B", "split_pct": 30}])   # splits must total 100
    with pytest.raises(S.ArtistError):
        S.artist_save(T, "Solo", actor="staff:s1")
    out = S.save_settings(T, distributors=[{"name": "DistroX"}])
    assert "lead time" in out["say"] and "commission % abhi nahi" in out["say"]
    _roster(S)
    v = S.artist_view(T, "mehfil")
    assert v["name"] == "Mehfil Band" and len(v["members"]) == 3 and v["rider"]["tech"][0] == "4 vocal mics"
    assert {r["key"] for r in v["regs"]} >= {"iprs", "isamra", "ppl"} and all(r["status"] == "none" for r in v["regs"])
    with pytest.raises(S.ArtistError):
        S.reg_set(T, "Mehfil Band", "ipi", "done", "123")
    with pytest.raises(S.ArtistError):
        S.reg_set(T, "Mehfil Band", "isrc", "done", "TOOLONG")
    S.reg_set(T, "Mehfil Band", "isrc", "done", "k40")
    S.reg_set(T, "Mehfil Band", "iprs", "applied", "M-2026-55")
    regs = {r["key"]: r for r in S.artist_view(T, "Mehfil Band")["regs"]}
    assert regs["isrc"]["ref"] == "K40" and regs["iprs"]["status"] == "applied"
    assert any("Mehfil Band" in x for x in S.day(T)["regs_missing"])


def test_double_booking_refused_in_code(am):
    S = am
    _roster(S)
    g1 = S.offer(T, "Shaadi sangeet 20 Nov shaam 7 baje Pune, fee 1.2 lakh, Mr Shah 9811100022", artist="Mehfil Band")["gig"]
    assert g1["number"] == "G-0001" and g1["status"] == "enquiry" and g1["fee"] == 120000 and g1["start"] == "19:00"
    S.gig_save(T, g1["number"], end="21:00")
    S.hold(T, g1["number"])
    # same artist, same city, 1 hour after the end (< her 120 min gap) -> refused, even as a hold, even for her
    g2 = S.offer(T, artist="Mehfil Band", day="2026-11-20", start="22:00", city="Pune", fee=90000, promoter="Club X")["gig"]
    assert "khaali nahi" in S.offer(T, artist="Mehfil Band", day="2026-11-20", start="21:30", city="Pune", fee=1)["say"]
    with pytest.raises(S.ArtistError) as e:
        S.hold(T, g2["number"])
    assert "G-0001" in str(e.value) and "double booking" in str(e.value)
    with pytest.raises(S.ArtistError):
        S.confirm_request(T, g2["number"])
    # another city the next day at noon: 15 h gap > travel gap 8 h -> fine
    g3 = S.offer(T, artist="Mehfil Band", day="2026-11-21", start="12:00", city="Mumbai", fee=100000, promoter="Corp", phone="9811100033")["gig"]
    S.hold(T, g3["number"])
    # Ravi plays in both acts: his other act can't take 20 Nov evening
    g4 = S.offer(T, artist="Ravi Dhol Beats", day="2026-11-20", start="20:00", city="Pune", fee=30000, promoter="Y")["gig"]
    with pytest.raises(S.ArtistError) as e:
        S.hold(T, g4["number"])
    assert "Ravi" in str(e.value) and "Mehfil Band" in str(e.value)
    # her blocked days
    S.block_days(T, "Mehfil Band", "2026-12-01", "2026-12-03", "studio")
    g5 = S.offer(T, artist="Mehfil Band", day="2026-12-02", start="19:00", city="Pune", fee=90000, promoter="Z")["gig"]
    with pytest.raises(S.ArtistError):
        S.hold(T, g5["number"])
    with pytest.raises(S.ArtistError):
        S.block_days(T, "Mehfil Band", "2026-11-20")                         # a gig is already there
    assert S.check(T, "Mehfil Band", "2026-11-20", "22:00", city="Pune")["free"] is False
    assert S.check(T, "Mehfil Band", "2026-11-25", "22:00", city="Pune")["free"] is True
    # moving a held gig onto a busy time is refused and nothing changes
    with pytest.raises(S.ArtistError):
        S.gig_save(T, g3["number"], day="2026-11-20", start="20:00", city="Pune")
    assert S.gig_view(T, g3["number"])["day"] == "2026-11-21"
    # the hold expires by itself -> the time frees up
    S.CLK["t"] = NOW + timedelta(hours=73)
    assert S.gig_view(T, g1["number"])["status"] == "enquiry"
    S.hold(T, g2["number"])
    # a confirm card made earlier for g1 can't win the race at the tap
    c1 = S.offer(T, artist="Mehfil Band", day="2026-11-20", start="19:00", end="21:00", city="Pune", fee=120000, promoter="Shah")["gig"]
    with pytest.raises(S.ArtistError):
        S.confirm_request(T, c1["number"])


def test_cards_only_by_her_tap_and_money(am):
    S = am
    _roster(S)
    g = S.offer(T, "Corporate annual day 5 Dec 2026, 8 pm, Pune, Mr Rao 9811100044, 1 lakh", artist="Mehfil Band")["gig"]
    assert g["event_type"] == "corporate"
    with pytest.raises(S.ArtistError):
        S.contract_request(T, g["number"])                                   # promoter name missing -> card refused
    S.gig_save(T, g["number"], promoter="Rao Events", venue="JW Marriott", set_minutes=90, travel_by="promoter")
    r = S.reply_request(T, g["number"])
    assert r["status"] == "needs_tap" and "1,00,000" in r["card"]["show"]["text"]
    assert S.reply_request(T, g["number"])["existing"]                       # same card never twice
    with pytest.raises(S.ArtistError):
        S.decide(T, r["card"]["id"], True, r["card"]["hash"])                # not her tap
    ct = S.contract_request(T, g["number"])
    S.gig_save(T, g["number"], fee=110000)                                   # change after the card -> stale
    with pytest.raises(S.ArtistError):
        S.decide(T, ct["card"]["id"], True, ct["card"]["hash"], by_tap=True)
    assert S.card_view(T, ct["card"]["id"])["status"] == "stale"
    ct = S.contract_request(T, g["number"])
    out = S.decide(T, ct["card"]["id"], True, ct["card"]["hash"], by_tap=True)
    assert "wa.me/919811100044" in out["draft"]["wa"] and S.STORED[-1][0].endswith("_performance_agreement.pdf")
    assert S.STORED[-1][1].startswith(b"%PDF")
    cf = S.confirm_request(T, g["number"])
    assert S.decide(T, cf["card"]["id"], True, cf["card"]["hash"], by_tap=True)["say"].startswith(g["number"] + " pakka")
    assert S.gig_view(T, g["number"])["status"] == "confirmed"
    with pytest.raises(S.ArtistError):
        S.gig_save(T, g["number"], fee=50000, actor="staff:s1")              # staff can't change a confirmed fee
    p = S.pay_request(T, g["number"], "advance")
    assert p["card"]["show"]["amount"] == 55000
    d = S.decide(T, p["card"]["id"], True, p["card"]["hash"], by_tap=True)
    assert d["draft"]["upi"].startswith("upi://pay?pa=surtalent%40okhdfc&") and "am=55000.00" in d["draft"]["upi"]
    with pytest.raises(S.ArtistError):
        S.paid(T, g["number"], 55000, actor="staff:s1")
    S.paid(T, g["number"], 55000, "bank", "UTR123456789")
    S.set_tds(T, g["number"], 11000)
    S.paid(T, g["number"], 44000, "upi", "UTR555")
    S.expense(T, g["number"], "Cab to venue", 3000, "manager")
    inv = S.invoice_request(T, g["number"])
    assert inv["card"]["show"]["invoice"]["gst_pct"] == 0                     # no GSTIN set -> no GST line
    S.decide(T, inv["card"]["id"], True, inv["card"]["hash"], by_tap=True)
    assert S.gig_view(T, g["number"])["invoice_no"].startswith("INV/2627/")
    m = S.done(T, g["number"])["money"]
    assert m["fully_paid"] and m["commission"] == 16500 and m["net_to_artist"] == 99000 - 16500 - 3000
    # royalty from her statement + payout statement on her fingerprint
    S.royalty_add(T, "Mehfil Band", "iprs", 10000, "2026-Q2", ref="ST-1")
    with pytest.raises(S.ArtistError):
        S.royalty_add(T, "Mehfil Band", "iprs", 10000, "2026-Q2", ref="ST-1")  # same line twice
    po = S.payout_request(T, "Mehfil Band")
    sh = po["card"]["show"]
    assert sh["total"] == 79500 + 9000 and [x["amount"] for x in sh["splits"]] == [35400.0, 26550.0, 26550.0]
    from app import approvekey as ak
    phone = Phone("phone-1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    with pytest.raises(S.ArtistError) as e:
        S.decide(T, po["card"]["id"], True, po["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, po["card"]["id"])
    with pytest.raises(S.ArtistError):
        S.decide(T, po["card"]["id"], True, po["card"]["hash"], proof=Phone("phone-1").sign(ch), by_tap=True)
    ch = S.card_challenge(T, po["card"]["id"])
    out = S.decide(T, po["card"]["id"], True, po["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    assert out["payout"] == "P-0001" and len(out["drafts"]) == 3 and S.STORED[-1][0] == "P-0001_statement.pdf"
    with pytest.raises(S.ArtistError):
        S.payout_request(T, "Mehfil Band")                                   # nothing left to pay out
    S.payout_paid(T, "P-0001", "UTR777")
    assert S.payouts(T)[0]["status"] == "paid"
    # DPDP forget after the gig
    S.forget(T, g["number"])
    v = S.gig_view(T, g["number"])
    assert v["phone"] == "" and v["promoter"] == "Promoter (hataya)" and v["money"]["received"] == 99000


def test_gst_on_invoice_and_cancel(am):
    S = am
    _roster(S)
    S.artist_save(T, "Pt. Raag", "classical", gstin="27AAPFU0939F1ZV")
    g = S.offer(T, artist="Pt. Raag", day="2026-11-28", start="18:30", city="Nashik", fee=140000, promoter="Sabha", phone="9811100055",
                promoter_gstin="27AAPFU0939F1ZV")["gig"]
    S.hold(T, g["number"])
    c = S.confirm_request(T, g["number"])
    S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    inv = S.invoice_request(T, g["number"])["card"]["show"]["invoice"]
    assert inv["gst_pct"] == 0 and "chhoot" in inv["gst_note"]                 # classical <= 1.5 lakh
    S.gig_save(T, g["number"], fee=160000)
    inv = S.invoice_request(T, g["number"])["card"]["show"]["invoice"]
    assert inv["gst_pct"] == 18 and inv["cgst"] == 14400 and inv["total"] == 188800
    with pytest.raises(S.ArtistError):
        S.cancel(T, g["number"], "")
    S.paid(T, g["number"], 50000)
    out = S.cancel(T, g["number"], "Organiser ne event radd kiya")
    assert "aap tay kijiye" in out["say"]
    assert S.check(T, "Pt. Raag", "2026-11-28", "18:30", city="Nashik")["free"]
    assert not S.cards(T, "waiting") or all(x["ref_id"] != S.gig_view(T, g["number"])["id"] for x in S.cards(T, "waiting"))


def test_release_plan_and_final_metadata(am):
    S = am
    _roster(S)
    with pytest.raises(S.ArtistError):
        S.release_save(T, "Mehfil Band", "Ishq", day="2026-12-11", upc="036000291453")
    with pytest.raises(S.ArtistError):
        S.release_save(T, "Mehfil Band", "Ishq", tracks=[{"title": "A", "isrc": "INK401400212"}, {"title": "B", "isrc": "IN-K40-14-00212"}])
    r = S.release_save(T, "Mehfil Band", "Ishq", "single", "2026-12-11", "believe",
                       tracks=[{"title": "Ishq", "isrc": "IN-K40-26-00001",
                                "writers": [{"name": "Arif", "role": "lyrics", "share": 50}, {"name": "Sana", "role": "music", "share": 40}]}])["release"]
    assert r["distributor"] == "Believe" and any("100%" in p for p in r["problems"]) and any("Artwork" in p for p in r["problems"])
    assert r["plan"][0]["by"] == "2026-11-20" and r["plan"][1]["by"] == "2026-12-04"
    with pytest.raises(S.ArtistError):
        S.release_final_request(T, r["number"])                              # problems block the card
    with pytest.raises(S.ArtistError):
        S.release_step(T, r["number"], "deliver")                            # not final yet
    r = S.release_save(T, release=r["number"], artwork=True,
                       tracks=[{"title": "Ishq", "isrc": "IN-K40-26-00001",
                                "writers": [{"name": "Arif", "role": "lyrics", "share": 50, "ipi": "00052210040"},
                                            {"name": "Sana", "role": "music", "share": 50}]}])["release"]
    assert r["problems"] == []
    c = S.release_final_request(T, r["number"])
    out = S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    assert "Believe" in out["say"] and S.STORED[-1][0] == "R-001_metadata.csv" and b"IN-K40-26-00001" in S.STORED[-1][1]
    S.release_step(T, r["number"], "deliver")
    assert S.release_view(T, r["number"])["status"] == "delivered"
    r2 = S.release_save(T, release=r["number"], day="2026-12-18")
    assert "final dobara" in r2["say"] and r2["release"]["status"] == "plan"


def test_tick_and_morning(am):
    S = am
    _roster(S)
    S.save_settings(T, morning_time="09:00", balance_days=3)
    g = S.offer(T, artist="Mehfil Band", day="2026-10-30", start="20:00", city="Pune", fee=100000, promoter="Club", phone="9811100066")["gig"]
    S.hold(T, g["number"], 20)
    o = S.tick(NOW + timedelta(hours=10))
    assert o["alerts"] >= 1 and o["morning"] == 1
    assert S.tick(NOW + timedelta(hours=10))["morning"] == 0
    assert S.tick(NOW + timedelta(hours=21))["expired"] == 1
    assert any(k == "artistmgr_alert" and p["kind"] == "hold_expired" for k, p in S.EVENTS)
    S.hold(T, g["number"])
    c = S.confirm_request(T, g["number"])
    S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    S.tick(datetime(2026, 10, 27, 5, 0, tzinfo=timezone.utc))                 # balance due 3 days before
    assert any(p.get("kind") == "balance" for k, p in S.EVENTS if k == "artistmgr_alert")
    S.tick(datetime(2026, 10, 29, 5, 0, tzinfo=timezone.utc))
    assert any(p.get("kind") == "tomorrow" for k, p in S.EVENTS if k == "artistmgr_alert")
    S.tick(datetime(2026, 10, 31, 5, 0, tzinfo=timezone.utc))
    assert any(p.get("kind") == "over" for k, p in S.EVENTS if k == "artistmgr_alert")


def test_tools_actors_and_api(am):
    S = am
    from app.agent.artistmgr_tools import ARTISTMGR_HANDLERS, ARTISTMGR_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in ARTISTMGR_TOOLS} == {"artist_manager", "artist_manager_dekho"} == set(ARTISTMGR_HANDLERS)
    for t in ARTISTMGR_TOOLS:
        assert set(t["input_schema"]["required"]) <= set(t["input_schema"]["properties"])
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(ARTISTMGR_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("artist_manager", action="settings", upi_id="mgr@okaxis", commission_pct=10)
    run("artist_manager", action="artist", name="DJ Noor", kind="dj", city="Goa")
    g = run("artist_manager", action="offer", text="I am Leo, new year party 31 Dec raat 10 baje Goa mein, 2 lakh, 9811100077")["gig"]
    assert g["artist"] == "DJ Noor" and g["start"] == "22:00" and g["fee"] == 200000
    run("artist_manager", action="hold", gig=g["number"])
    sent = run("artist_manager", action="confirm", gig=g["number"])
    assert sent["status"] == "needs_tap"
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    for a in ({"action": "settings", "commission_pct": 50}, {"action": "paid", "gig": g["number"], "amount": 10},
              {"action": "cancel", "gig": g["number"], "reason": "x"}, {"action": "royalty", "artist": "DJ Noor", "source": "iprs", "amount": 5}):
        with pytest.raises(ToolError):
            asyncio.run(ARTISTMGR_HANDLERS["artist_manager"](staff, **a))
    assert asyncio.run(ARTISTMGR_HANDLERS["artist_manager"](staff, action="reply", gig=g["number"]))["status"] == "needs_tap"
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(ARTISTMGR_HANDLERS["artist_manager"](cust, action="offer", text="x"))
    with pytest.raises(ToolError):
        run("artist_manager", action="offer", artist="DJ Noor", day="2026-12-31", start="23:00", city="Goa", fee=1)  # ok as enquiry
        run("artist_manager", action="hold", gig="G-0002")
    assert run("artist_manager_dekho", what="day")["waiting"] >= 1
    assert run("artist_manager_dekho", what="check", artist="DJ Noor", day="2026-12-31", start="23:30", city="Goa")["free"] is False

    from app.artistmgr.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    assert c.get("/api/artistmgr").status_code == 200
    cid, h = sent["card"]["id"], sent["card"]["hash"]
    assert c.post(f"/api/artistmgr/cards/{cid}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    r = c.post(f"/api/artistmgr/cards/{cid}/decide", json={"yes": True, "hash": h})
    assert r.status_code == 200 and r.json()["card"]["status"] == "approved"
    assert c.get(f"/api/artistmgr/gigs/{g['number']}").json()["status"] == "confirmed"
    assert c.get(f"/api/artistmgr/gigs/{g['number']}/contract.pdf").content.startswith(b"%PDF")
    assert c.get("/api/artistmgr/calendar", params={"month": "2026-12"}).json()["days"]["2026-12-31"]
    assert c.put("/api/artistmgr/settings", json={"upi_id": "nope"}).status_code == 400
    assert c.post(f"/api/artistmgr/gigs/{g['number']}/nope").status_code == 404
    assert c.get("/api/artistmgr/check", params={"artist": "DJ Noor", "day": "2026-12-31", "start": "22:30"}).json()["free"] is False
