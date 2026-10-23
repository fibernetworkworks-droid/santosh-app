"""Motion designer desk: rules (platform specs, timecoded notes, storyboard numbers, licences, GST split), client brand kits with
EXIF-free logos, job tickets, storyboard -> her tap -> client's yes recorded -> renders on the engine with the CLIENT's colours,
revision rounds counted vs the quote (extra round = paid card with her fingerprint), licence register blocks the final, handover
note, invoices (advance / final less advance, GST intra / inter, blanks refused), paid, templates, tools + API, worker, DPDP forget."""
import asyncio
import base64
import io
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.motiondesk.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def md(env, monkeypatch, tmp_path):
    from app.motiondesk import service as S
    monkeypatch.setenv("MOTIONDESK_DIR", str(tmp_path / "md"))
    events, stored, started = [], [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    monkeypatch.setattr(S, "_ai_json", lambda system, prompt, max_tokens=1500: {})

    def fake_start(tenant, conv, engine, kind, data, aspect, brief, kit, logo, platform):
        started.append({"engine": engine, "kind": kind, "aspect": aspect, "brief": brief, "kit": kit, "data": data, "logo": logo})
        return {"ref": f"mv{len(started)}", "status": "queued"}
    monkeypatch.setattr(S, "_engine_start", fake_start)
    monkeypatch.setattr(S, "_engine_status", lambda tenant, engine, ref: {"status": "done", "url": f"/api/motion/files/{ref}.mp4"})
    S.EVENTS, S.STORED, S.STARTED, S.CLK = events, stored, started, clk
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


def _setup(S):
    S.save_settings(T, studio="Kala Motion Studio", gstin="27AAPFU0939F1ZV", upi_id="kala@okicici", phone="9876543210", round_fee=3000)
    c = S.client_save(T, "Sharma Sweets", phone="98220 12345", gstin="27AAACR5055K1Z7",
                      kit={"colors": {"primary": "#B71C1C", "accent": "sunehra", "light": "#FFFFFF"},
                           "fonts": [{"name": "Poppins", "source": "google_fonts"}], "tone": "warm"})["client"]
    return c


def _job(S, deliverables=("insta_reel", "youtube")):
    return S.job_new(T, "Sharma Sweets", "Diwali reel", "Sharma Sweets ki Diwali reel. Kaju katli 20% off. Order 9822012345.",
                     "motion", "offer", list(deliverables), "2026-10-28",
                     [{"text": "Diwali reel 20 sec", "qty": 1, "rate": 12000}])["job"]


def test_rules():
    from app.motiondesk import rules as R
    d = R.deliverable({"platform": "Instagram reel", "seconds": 200})
    assert d["px"] == "1080x1920" and d["max_s"] == 180 and any("180 sec" in w for w in d["warnings"])
    assert any("720x1280" in w for w in d["warnings"])
    assert R.deliverable("4:5")["engine_aspect"] == "" and R.deliverable("story")["platform"] == "insta_story"
    assert R.deliverable("kuch bhi") is None
    n = R.timecodes("0:12 logo bada karo\n00:01:05 rang halka; 12s fast; music badlo")
    assert [x["tc"] for x in n] == [12.0, 65.0, 12.0, None] and n[0]["text"] == "logo bada karo"
    assert R.tc_text(65) == "01:05"
    f, notes = R.clean_frames([{"seconds": 3, "visual": "Kaju katli", "text": "50% off, call 9999911111"}], "Kaju katli 20% off")
    assert "[?]" in f[0]["text"] and "50" not in f[0]["text"] and notes
    assert R.licence_of("adobe_fonts", "") == "adobe_fonts" and R.licence_of("", "") == "unknown"
    b, _w = R.asset_problems({"name": "X", "licence": "unknown"}, "j1", "2026-10-23")
    assert b
    b, _w = R.asset_problems({"name": "Track", "licence": "subscription_single", "project_job": "j0", "jobs": ["j0"]}, "j1", "2026-10-23")
    assert b and "naya" in b[0]
    b, w = R.asset_problems({"name": "Pic", "licence": "cc_by", "valid_until": "2026-01-01"}, "j1", "2026-10-23")
    assert b and w
    assert R.gst_split("27AAA", "29BBB") == "inter" and R.gst_split("27AAA", "27BBB") == "intra" and R.gst_split("27AAA", "") == "intra"
    st = R.round_state(2, 2)
    assert st["left"] == 0 and "paise" in st["say"]
    assert R.color("laal") == "#D32F2F" and R.color("#abcdef") == "#ABCDEF" and R.num("12k") == 12000


def test_client_kit_logo_and_job(md):
    S = md
    c = _setup(S)
    assert c["number"] == "C-001" and c["phone"] == "9822012345" and c["kit"]["colors"]["accent"] == "#C9A227"
    assert c["kit"]["fonts"][0]["licence"] == "ofl"
    from PIL import Image
    im = Image.new("RGB", (40, 40), (200, 10, 10))
    exif = Image.Exif()
    exif[0x0110] = "SecretCam"
    bio = io.BytesIO()
    im.save(bio, "JPEG", exif=exif.tobytes())
    out = S.client_logo(T, "C-001", bio.getvalue())
    assert out["client"]["logo"]
    from pathlib import Path
    with S.session() as s:
        p = s.get(S.MotiondeskClient, c["id"]).logo_path
    saved = Image.open(Path(p))
    assert not saved.getexif() and saved.format == "PNG"
    j = _job(S)
    assert j["number"] == "MJ-0001" and [d["platform"] for d in j["deliverables"]] == ["insta_reel", "youtube"]
    assert j["quote_total"] == 12000 and j["rounds"]["included"] == 2
    with pytest.raises(S.MotiondeskError):
        S.job_new(T, "", "x", "")                        # no brief
    with pytest.raises(S.MotiondeskError):
        S.job_new(T, "", "", "Ek logo animation", deadline="kal shaam")
    with pytest.raises(S.MotiondeskError):
        S.job_update(T, j["number"], "staff:s1", quote=[{"text": "x", "rate": 1}])


def test_storyboard_tap_client_ok_render_and_rounds(md, monkeypatch):
    S = md
    _setup(S)
    j = _job(S)
    monkeypatch.setattr(S, "_ai_json", lambda system, prompt, max_tokens=1500: {"frames": [
        {"seconds": 4, "visual": "Diya jalta hai, Sharma Sweets", "text": "Shubh Deepawali", "motion": "fade"},
        {"seconds": 5, "visual": "Kaju katli ka dabba", "text": "Kaju katli 20% off", "motion": "pop"},
        {"seconds": 4, "visual": "Phone number", "text": "Call 9000000000", "audio": "festive"}]})
    sb = S.storyboard(T, j["number"], 15)
    frames = sb["job"]["frames"]
    assert len(frames) == 3 and frames[1]["text"] == "Kaju katli 20% off" and "[?]" in frames[2]["text"]
    # render refused before the client said yes
    with pytest.raises(S.MotiondeskError):
        S.render(T, j["number"])
    c = S.storyboard_request(T, j["number"])
    assert c["status"] == "needs_tap" and c["card"]["kind"] == "storyboard"
    with pytest.raises(S.MotiondeskError):
        S.decide(T, c["card"]["id"], True, c["card"]["hash"])                    # not a tap
    again = S.storyboard_request(T, j["number"])
    assert again.get("existing")
    out = S.decide(T, c["card"]["id"], True, c["card"]["hash"], by_tap=True)
    assert out["draft"]["wa"].startswith("https://wa.me/919822012345") and S.STORED[-1][1].startswith(b"%PDF")
    with pytest.raises(S.MotiondeskError):
        S.client_ok(T, j["number"], actor="staff:s1")
    S.client_ok(T, j["number"], "Mr Sharma on WhatsApp")
    r = S.render(T, j["number"])
    assert [x["aspect"] for x in r["renders"]] == ["9:16", "16:9"]
    st = S.STARTED[0]
    assert st["kit"]["colors"]["primary"] == "#B71C1C" and "STORYBOARD" in st["brief"] and st["kind"] == "offer"
    with pytest.raises(S.MotiondeskError):
        S.render(T, j["number"])                                                 # one still working
    S.sync(T)
    v = S.job_view(T, j["number"])
    assert v["status"] == "review" and all(x["status"] == "done" for x in v["renders"])
    assert ("motiondesk_update", ) == tuple(k for k, _ in S.EVENTS if k == "motiondesk_update")[:1]
    # editing the storyboard drops the client's approval
    S.storyboard_edit(T, j["number"], frames[:2])
    assert not S.job_view(T, j["number"])["storyboard_approved"]
    S.client_ok(T, j["number"], "Mr Sharma")
    # two included rounds, then a paid extra round on her fingerprint
    for k in range(2):
        S.feedback(T, j["number"], f"0:0{k + 2} logo bada karo")
        rv = S.revise(T, j["number"])
        assert rv["rounds"]["used"] == k + 1
        S.sync(T)
    assert "CHANGES ASKED" in S.STARTED[-1]["brief"]
    S.feedback(T, j["number"], "0:05 rang badlo")
    with pytest.raises(S.MotiondeskError):
        S.revise(T, j["number"], actor="staff:s1")
    from app import approvekey as ak
    phone = Phone("ph1")
    ak.register(T, phone.device_id, phone.pub, "Pixel")
    x = S.extra_round_request(T, j["number"])
    assert x["card"]["money"] and x["card"]["show"]["amount"] == 3000
    with pytest.raises(S.MotiondeskError) as e:
        S.decide(T, x["card"]["id"], True, x["card"]["hash"], by_tap=True)
    assert str(e.value) == "fingerprint_needed"
    ch = S.card_challenge(T, x["card"]["id"])
    S.decide(T, x["card"]["id"], True, x["card"]["hash"], proof=phone.sign(ch), by_tap=True)
    rv = S.revise(T, j["number"])
    assert rv["rounds"]["used"] == 3 and rv["rounds"]["included"] == 3


def test_licences_final_and_handover(md):
    S = md
    _setup(S)
    j = _job(S, ("insta_reel",))
    S.storyboard(T, j["number"])
    S.client_ok(T, j["number"])
    S.render(T, j["number"])
    S.sync(T)
    S.asset_save(T, "Desi beat", "music", "", "", "")
    a = S.assets(T)
    mystery = next(x for x in a if x["name"] == "Desi beat")
    assert mystery["licence"] == "unknown"
    S.use_asset(T, j["number"], mystery["id"])
    with pytest.raises(S.MotiondeskError) as e:
        S.final_request(T, j["number"])
    assert "licence pata nahi" in str(e.value)
    S.asset_save(T, "Desi beat", source="envato", licence_ref="ENV-123", asset=mystery["id"])
    f = S.final_request(T, j["number"])
    sh = f["card"]["show"]
    assert sh["files"][0]["platform"] == "insta_reel" and any("Envato" in x["licence"] or "register" in x["say"] for x in sh["licences"])
    assert any(x["name"].startswith("Poppins") for x in sh["licences"])
    assert any("AI" in w for w in sh["warnings"])
    # a change after the card = stale
    S.job_update(T, j["number"], deliverables=["insta_reel", "square"])
    with pytest.raises(S.MotiondeskError):
        S.decide(T, f["card"]["id"], True, f["card"]["hash"], by_tap=True)
    S.job_update(T, j["number"], deliverables=["insta_reel"])
    f = S.final_request(T, j["number"])
    out = S.decide(T, f["card"]["id"], True, f["card"]["hash"], by_tap=True)
    assert "files" in out["draft"]["text"] and S.job_view(T, j["number"])["status"] == "delivered"
    assert S.STORED[-1][1].startswith(b"%PDF")
    # the single-project Envato licence is now registered to this job: re-use in another job blocks its final
    j2 = _job(S, ("insta_reel",))
    S.storyboard(T, j2["number"])
    S.client_ok(T, j2["number"])
    S.render(T, j2["number"])
    S.sync(T)
    S.use_asset(T, j2["number"], mystery["id"])
    with pytest.raises(S.MotiondeskError) as e:
        S.final_request(T, j2["number"])
    assert "naya register" in str(e.value)
    with pytest.raises(S.MotiondeskError):
        S.template_save(T, j2["number"], "Diwali offer")


def test_invoices_gst_paid_and_forget(md):
    S = md
    _setup(S)
    j = S.job_new(T, "Sharma Sweets", "Logo sting", "Logo intro 8 sec", "motion", "logo", ["square"],
                  quote=[{"text": "Logo sting", "qty": 1, "rate": None}])["job"]
    with pytest.raises(S.MotiondeskError):
        S.invoice_request(T, j["number"], "advance")                         # no price given: never guessed
    S.job_update(T, j["number"], quote=[{"text": "Logo sting", "qty": 1, "rate": 10000}])
    a = S.invoice_request(T, j["number"], "advance")
    sh = a["card"]["show"]
    assert sh["taxable"] == 5000 and sh["gst"]["cgst"] == 450 and sh["total"] == 5900
    out = S.decide(T, a["card"]["id"], True, a["card"]["hash"], by_tap=True)
    assert out["invoice"] == "MD/2627/001" and "upi://pay?pa=kala%40okicici" in out["draft"]["upi"]
    S.client_save(T, client="Sharma Sweets", gstin="29AAACR5055K1Z5")
    f = S.invoice_request(T, j["number"], "final")
    sh = f["card"]["show"]
    assert "igst" in sh["gst"] and sh["taxable"] == 10000 and sh["total"] == round(11800 - 5900, 2)
    S.decide(T, f["card"]["id"], True, f["card"]["hash"], by_tap=True)
    inv = S.job_view(T, j["number"])["invoices"]
    assert {i["number"] for i in inv} == {"MD/2627/001", "MD/2627/002"}
    with pytest.raises(S.MotiondeskError):
        S.paid(T, "MD/2627/001", 5900, actor="staff:s1")
    p = S.paid(T, "MD/2627/001", 5400, "UTR123456789012")
    assert p["invoice"]["status"] == "part"
    S.paid(T, "MD/2627/001", 500)
    assert S.invoice_pdf(T, inv[0]["id"]).startswith(b"%PDF")
    tp = S.template_save(T, j["number"], "Logo sting")
    j3 = S.job_new(T, "", "", "", template=tp["template"]["id"])["job"]
    assert j3["kind"] == "logo" and S.templates(T)[0]["uses"] == 1
    with pytest.raises(S.MotiondeskError):
        S.forget_client(T, "Sharma Sweets")                                   # job still open
    S.cancel(T, j["number"], "client ne mana kiya")
    with pytest.raises(S.MotiondeskError):
        S.forget_client(T, "Sharma Sweets")                                   # invoice 002 unpaid
    S.paid(T, "MD/2627/002", 5900)
    S.forget_client(T, "Sharma Sweets")
    c = S.clients(T)[0]
    assert c["forgotten"] and c["phone"] == "" and c["name"].startswith("Purana")


def test_tick_tools_and_api(md):
    S = md
    _setup(S)
    j = _job(S)
    S.CLK["t"] = datetime(2026, 10, 26, 5, 0, tzinfo=timezone.utc)
    out = S.tick(S.CLK["t"])
    assert out["alerts"] >= 1 and any(p.get("kind") == "deadline" for k, p in S.EVENTS if k == "motiondesk_alert")
    again = S.tick(S.CLK["t"])
    assert again["alerts"] == 0                                               # once each
    assert out["morning"] == 1
    from app.agent import motiondesk_tools as MT
    from app.agent.tools import ToolError
    ctx = conv_ctx()
    r = asyncio.run(MT.MOTIONDESK_HANDLERS["motion_desk_dekho"](ctx, what="job", job=j["number"]))
    assert r["number"] == j["number"]
    ctx.actor = "staff:s1"
    with pytest.raises(ToolError):
        asyncio.run(MT.MOTIONDESK_HANDLERS["motion_desk"](ctx, action="client_ok", job=j["number"]))
    ctx.actor = "customer:wa:1"
    with pytest.raises(ToolError):
        asyncio.run(MT.MOTIONDESK_HANDLERS["motion_desk"](ctx, action="storyboard", job=j["number"]))
    ctx.actor = "owner"
    r = asyncio.run(MT.MOTIONDESK_HANDLERS["motion_desk"](ctx, action="storyboard", job=j["number"]))
    assert r["job"]["frames"]
    for tool in MT.MOTIONDESK_TOOLS:
        props = tool["input_schema"]["properties"]
        assert all(k in props for k in tool["input_schema"]["required"])
    from app.motiondesk.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    cl = TestClient(app)
    ov = cl.get("/api/motiondesk").json()
    assert ov["jobs"][0]["number"] == j["number"] and ov["platforms"]
    c = cl.post(f"/api/motiondesk/jobs/{j['number']}/storyboard_send").json()
    bad = cl.post(f"/api/motiondesk/cards/{c['card']['id']}/decide", json={"yes": True, "hash": "x"})
    assert bad.status_code == 400
    ok = cl.post(f"/api/motiondesk/cards/{c['card']['id']}/decide", json={"yes": True, "hash": c["card"]["hash"]}).json()
    assert ok["card"]["status"] == "approved"
    assert cl.get(f"/api/motiondesk/jobs/{j['number']}/storyboard.pdf").content.startswith(b"%PDF")
    assert cl.post(f"/api/motiondesk/jobs/{j['number']}/nope").status_code == 404


def test_engine_wrapper_uses_client_colours(env, monkeypatch):
    """The real wrapper: motion plan (only when no data) + the CLIENT's colours / logo go into Hoola Motion; status maps back."""
    from app.motion import service as M
    from app.motiondesk import service as S
    got = {}
    monkeypatch.setattr(M, "plan", lambda kind, brief: {"kind": kind, "data": {"brand": "Sharma", "colors": {"bg1": "#000000"}}})

    def create(tenant, kind, data, aspect, mood, brief, conv):
        got.update(kind=kind, data=data, aspect=aspect)
        return {"id": "mv1", "status": "queued"}
    monkeypatch.setattr(M, "create", create)
    monkeypatch.setattr(M, "get", lambda tenant, vid: {"status": "done", "url": "/api/motion/files/mv1.mp4", "thumb": ""})
    kit = {"colors": {"primary": "#B71C1C", "accent": "#C9A227", "dark": "#111111"}}
    r = S._engine_start(T, "", "motion", "logo", {}, "1:1", "Logo intro", kit, "data:image/png;base64,AAAA", "square")
    assert r["ref"] == "mv1" and got["aspect"] == "1:1"
    assert got["data"]["colors"]["bg1"] == "#B71C1C" and got["data"]["colors"]["accent"] == "#C9A227"
    assert got["data"]["logo"].startswith("data:image/png") and got["data"]["brand"] == "Sharma"
    assert S._engine_status(T, "motion", "mv1")["status"] == "done"
