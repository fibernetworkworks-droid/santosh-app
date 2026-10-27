"""Edit Desk (video editor's professional desk on the videoedit engine): brief / timecode / licence rules, project -> engine job ->
versions, client notes with timecodes -> revision rounds counted vs the quote, extra round only by HER tap, quote / invoice / payment
with TDS, licence gate on music and final delivery, every client-facing step only by her tap with the card's hash (refund with her
fingerprint), tools + API, worker, DPDP forget."""
import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.editdesk.models  # noqa: F401  (tables for the env fixture's init_db)
import app.videoedit.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST


@pytest.fixture
def ed(env, monkeypatch):
    from app.editdesk import service as S
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


def _file(name, data=b"\x00\x00\x00\x18ftypmp42fake"):
    from app.mailbox import service as ms
    return ms.store_bytes(T, name, data, "from_phone").id


def _render(job_id, n):
    """Pretend the engine finished version n (the real render needs ffmpeg)."""
    from app.db import session
    from app.videoedit.models import VideoJob
    with session() as s:
        row = s.get(VideoJob, job_id)
        vs = json.loads(row.versions or "[]")
        vs.append({"n": n, "file_id": f"vf{n}", "url": f"/api/video/files/{job_id}/hoola_v{n}.mp4?exp=1&sig=x", "change": "",
                   "check": {"ok": True}, "at": "2026-10-23T05:00:00+00:00"})
        row.versions, row.status, row.timeline, row.pending = json.dumps(vs), "done", "{}", ""


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules():
    from app.editdesk import rules as R
    t0 = date(2026, 10, 23)
    b = R.parse_brief("Insta reel aur YouTube short chahiye, 30 sec, Hindi captions, 28/10 tak. Ref https://youtu.be/abc "
                      "music: bollywood gaana. OTP 123456", t0)
    assert b["platforms"] == ["short", "reel"] and b["length_s"] == 30 and b["due"] == "2026-10-28"
    assert b["captions"] is True and b["languages"] == ["hindi"] and b["references"] == ["https://youtu.be/abc"]
    assert "123456" not in b["text"] and b["music_said"]
    assert R.parse_brief("wedding teaser 2 min", t0)["kind"] == "wedding" and R.parse_brief("2 min", t0)["length_s"] == 120
    assert R.brief_questions({}, False, False)[0].startswith("Kis platform")
    assert R.timecode_at("0:15 pe logo chhota karo") == (15.0, "logo chhota karo")
    assert R.timecode_at("1:02:10 text galat")[0] == 3730.0
    assert R.timecode_at("45 sec par music dheema")[0] == 45.0
    assert R.timecode_at("1.20 pe cut") == (80.0, "cut")
    cs = R.parse_comments("- 0:05 intro lamba hai\n- 0:42 spelling: 'Sharma'\n- ek aur reel bhi bana do\n- color thoda warm")
    assert [c["at_s"] for c in cs] == [5.0, 42.0, None, None] and cs[2]["scope"] == "extra" and cs[0]["scope"] == "fix"
    assert R.fmt_tc(3730) == "1:02:10" and R.fmt_tc(65) == "1:05"
    bad, _ = R.licence_problems({"licence_type": "platform_only", "source": "Instagram music library"}, True, t0)
    assert bad and any("Instagram" in x for x in bad)
    bad, _ = R.licence_problems({"licence_type": "royalty_free", "source": "Artlist"}, True, t0)
    assert any("proof" in x for x in bad)
    ok, w = R.licence_problems({"licence_type": "royalty_free", "source": "Artlist", "licence_ref": "AL-77", "expires": "2026-10-30"}, True, t0)
    assert not ok and w
    bad, _ = R.licence_problems({"licence_type": "royalty_free", "licence_ref": "x", "expires": "2026-01-01"}, True, t0)
    assert any("khatam" in x for x in bad)
    bad, _ = R.licence_problems({"licence_type": "royalty_free", "licence_ref": "x", "source": "youtube se download kiya"}, True, t0)
    assert bad
    assert R.gst_split("27", "27", 18, 1000) == {"pct": 18, "cgst": 90.0, "sgst": 90.0, "igst": 0.0, "tax": 180.0, "kind": "intra"}
    assert R.gst_split("27", "29", 18, 1000)["igst"] == 180.0
    assert R.money("15k") == 15000 and R.money("1.5 lakh") == 150000 and R.money("₹2,500") == 2500
    assert R.platform_of("whatsapp status") == "status" and R.platform_of("youtube") == "youtube"
    assert R.clean("otp 123456 card 4111 1111 1111 1111") == "otp [hataya] card [hataya]"


def _setup(S):
    S.save_settings(T, studio="Frame Cut Studio", gstin="27AAPFU0939F1ZV", gst_on=True, upi_id="framecut@okaxis", phone="9876543210",
                    rounds=2, extra_round_fee=1500, advance_pct=50,
                    rate_card=[{"code": "reel", "what": "Reel edit (30-60 s)", "rate": 3000, "unit": "nos"}])
    S.client_save(T, "Neha Kapoor", "98220 12345", "neha@example.com", "Glow Cosmetics", gstin="27AAPFU0939F1ZV")


def test_project_engine_rounds_and_extra_round(ed, monkeypatch):
    S = ed
    _setup(S)
    vid, song = _file("raw1.mp4"), _file("song.mp3", b"ID3fake")
    r = S.project_new(T, "Neha Kapoor", "Diwali reel", "Insta reel 30 sec, Hindi captions, 28/10 tak", file_ids=[vid])
    p = r["project"]
    assert p["number"] == "P-0001" and p["deliverables"][0]["platform"] == "reel" and p["due"] == "2026-10-28"
    assert p["rounds_quoted"] == 2 and p["status"] == "footage" and p["files"] == [vid]
    num = p["number"]
    S.project_update(T, num, music_file_id=song)
    with pytest.raises(S.EditError, match="licence"):
        S.edit_start(T, num)
    lic = S.licence_add(T, num, "music", "Diwali beat", "Instagram music library", "platform_only", file_id=song)
    assert not lic["licence"]["ok"]
    with pytest.raises(S.EditError, match="rukawat"):
        S.edit_start(T, num)
    S.licence_add(T, num, "music", "Diwali beat", "Artlist", "subscription", licence_ref="AL-2026-889",
                  ref=lic["licence"]["number"], file_id=song)
    out = S.edit_start(T, num)
    job = out["job"]["id"]
    assert out["project"]["status"] == "editing"
    from app.videoedit import service as V
    jv = V.get(T, job)
    assert jv["platform"] == "reel" and "Diwali reel" in jv["brief"] and jv["length_s"] == 30
    with pytest.raises(S.EditError, match="pehle se"):
        S.edit_start(T, num)
    _render(job, 1)
    sy = S.sync(T, num)
    assert sy["new"] == ["Instagram Reel v1"] and sy["project"]["status"] == "review"
    assert "editdesk_note" in kinds(S)
    assert S.sync(T, num)["new"] == []
    # review link card: only her tap, hash checked
    rv = S.review_request(T, num)
    c = rv["card"]
    with pytest.raises(S.EditError, match="tap"):
        S.decide(T, c["id"], True, c["hash"])
    with pytest.raises(S.EditError, match="badal"):
        S.decide(T, c["id"], True, "wrong", by_tap=True)
    d = S.decide(T, c["id"], True, c["hash"], by_tap=True)
    assert "wa.me/919822012345" in d["draft"]["wa"] and "hoola_v1.mp4" in d["draft"]["text"]
    # client notes -> round 1
    n = S.comments_add(T, num, "0:03 logo bada karo\n0:12 spelling 'Glow'\nek aur reel bhi bana do", version=1)
    assert len(n["comments"]) == 3 and "quote se bahar" in n["say"]
    seen = {}
    real = V.revise

    def spy(tenant, job_id, instruction):
        seen["ins"] = instruction
        return real(tenant, job_id, instruction)
    monkeypatch.setattr(V, "revise", spy)
    r1 = S.revise(T, num)
    assert r1["round"] == 1 and "at 0:03: logo bada karo" in seen["ins"] and "ek aur reel" not in seen["ins"]
    assert "data" in seen["ins"]
    with pytest.raises(S.EditError, match="khula"):
        S.revise(T, num)          # only the 'extra' note is open
    _render(job, 2)
    S.sync(T, num)
    S.comments_add(T, num, "0:20 music dheema", version=2)
    assert S.revise(T, num)["round"] == 2
    _render(job, 3)
    S.comments_add(T, num, "0:25 end card par number", version=3)
    r3 = S.revise(T, num)        # rounds over -> extra-round card at HER fee
    assert r3["status"] == "needs_tap" and r3["card"]["kind"] == "extra" and r3["card"]["show"]["amount"] == 1500
    assert S.project_view(T, num)["rounds_used"] == 2
    dx = S.decide(T, r3["card"]["id"], True, r3["card"]["hash"], by_tap=True)
    assert "Round 3" in dx["say"]
    pv = S.project_view(T, num)
    assert pv["rounds_used"] == 3 and pv["money"]["extras"][0]["amount"] == 1500
    # free round only by the owner
    _render(job, 4)
    S.comments_add(T, num, "0:01 fade in", version=4)
    with pytest.raises(S.EditError, match="owner"):
        S.revise(T, num, free=True, actor="staff:1")
    assert S.revise(T, num, free=True)["round"] == 4


def test_quote_invoice_paid_delivery(ed):
    S = ed
    _setup(S)
    vid = _file("raw.mp4")
    num = S.project_new(T, "Neha Kapoor", "Launch reel", "Insta reel 45 sec", file_ids=[vid])["project"]["number"]
    assert S.quote_make(T, num, [{"what": "Colour grade"}])["quote"]["blanks"]
    with pytest.raises(S.EditError, match="daam"):
        S.quote_request(T, num)
    q = S.quote_make(T, num, [{"code": "reel", "qty": 2}, {"what": "Subtitles", "qty": 1, "rate": 1000}], rounds=2)["quote"]
    assert q["subtotal"] == 7000 and q["gst"]["cgst"] == 630 and q["total"] == 8260 and q["advance"] == 4130
    card = S.quote_request(T, num)["card"]
    assert card["show"]["total"] == 8260
    # a newer draft makes the old card stale
    S.quote_make(T, num, [{"code": "reel", "qty": 1}])
    with pytest.raises(S.EditError, match="badal"):
        S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert S.cards(T, "stale")[0]["id"] == card["id"]
    S.quote_make(T, num, [{"code": "reel", "qty": 2}, {"what": "Subtitles", "qty": 1, "rate": 1000}], rounds=2)
    card = S.quote_request(T, num)["card"]
    d = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert d["file_id"] and S.STORED[-1][1][:4] == b"%PDF" and "Q/2627/001" in d["draft"]["text"]
    with pytest.raises(S.EditError, match="owner"):
        S.quote_accept(T, num, actor="staff:1")
    S.quote_accept(T, num)
    inv = S.invoice_request(T, num, "advance")["card"]
    assert inv["show"]["total"] == 4130 and inv["show"]["upi"] == "framecut@okaxis"
    di = S.decide(T, inv["id"], True, inv["hash"], by_tap=True)
    assert "upi://pay?pa=framecut%40okaxis" in di["draft"]["upi"] and "am=4130.00" in di["draft"]["upi"]
    with pytest.raises(S.EditError, match="pehle hi"):
        S.invoice_request(T, num, "advance")
    with pytest.raises(S.EditError, match="owner"):
        S.paid(T, num, 4000, actor="staff:2")
    pd = S.paid(T, num, 4000, tds=130, utr="UTR123456789")
    assert pd["receipt"] == "R/2627/001" and "TDS" in pd["say"]
    assert pd["money"]["received"] == 4130 and pd["money"]["agreed"] == 8260
    # edit + version, then delivery: no client OK -> warning; balance warns
    job = S.edit_start(T, num)["job"]["id"]
    dl = S.deliver_request(T, num)["card"]
    assert any("koi version" in b or "edit chal" in b for b in dl["show"]["blockers"])
    with pytest.raises(S.EditError, match="Rukawat"):
        S.decide(T, dl["id"], True, dl["hash"], by_tap=True)
    _render(job, 1)
    dl = S.deliver_request(T, num)["card"]
    assert not dl["show"]["blockers"] and any("OK" in w for w in dl["show"]["warnings"]) and dl["show"]["balance"] == 4130
    S.client_ok(T, num)
    dl2 = S.deliver_request(T, num)["card"]
    assert dl2["id"] != dl["id"]
    assert S.decide(T, dl["id"], True, dl["hash"], by_tap=True)["card"]["status"] == "stale"     # old card went stale
    # hold final until paid -> blocker
    S.save_settings(T, hold_final_unpaid=True)
    dl3 = S.deliver_request(T, num)["card"]
    assert any("baaki" in b for b in dl3["show"]["blockers"])
    S.save_settings(T, hold_final_unpaid=False)
    dl4 = S.deliver_request(T, num)["card"]
    dd = S.decide(T, dl4["id"], True, dl4["hash"], by_tap=True)
    assert "hoola_v1.mp4" in dd["draft"]["text"] and S.project_view(T, num)["status"] == "delivered"
    fin = S.invoice_request(T, num, "final")["card"]
    assert fin["show"]["subtotal"] == 3500 and fin["show"]["total"] == 4130
    S.decide(T, fin["id"], True, fin["hash"], by_tap=True)
    S.paid(T, num, 4130)
    assert S.project_view(T, num)["status"] == "closed"
    assert S.report(T)["received"] == 8260


def test_refund_fingerprint_api_and_tools(ed, monkeypatch):
    S = ed
    _setup(S)
    from app.editdesk.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    cl = TestClient(app)
    r = cl.post("/api/editdesk/projects", json={"client": "Neha Kapoor", "title": "Ad", "brief": "product ad square 20 sec"})
    assert r.status_code == 200, r.text
    num = r.json()["project"]["number"]
    assert r.json()["project"]["deliverables"][0]["platform"] == "square"
    assert cl.post(f"/api/editdesk/projects/{num}/quote", json={"lines": [{"what": "Ad edit", "rate": 10000}]}).status_code == 200
    c = cl.post(f"/api/editdesk/projects/{num}/quote_send").json()["card"]
    assert cl.post(f"/api/editdesk/cards/{c['id']}/decide", json={"yes": True, "hash": c["hash"]}).status_code == 200
    S.quote_accept(T, num)
    inv = S.invoice_request(T, num, "advance")["card"]
    S.decide(T, inv["id"], True, inv["hash"], by_tap=True)
    S.paid(T, num, 5900)
    assert cl.post(f"/api/editdesk/projects/{num}/cancel", json={"reason": "client ne project roka", "refund": 99999}).status_code == 400
    rc = cl.post(f"/api/editdesk/projects/{num}/cancel", json={"reason": "client ne project roka", "refund": 3000}).json()["card"]
    assert rc["kind"] == "refund" and rc["money"]
    from app import approvekey as ak
    monkeypatch.setattr(ak, "active_on", lambda tenant: True)
    r = cl.post(f"/api/editdesk/cards/{rc['id']}/decide", json={"yes": True, "hash": rc["hash"]})
    assert r.status_code == 428
    ch = cl.post(f"/api/editdesk/cards/{rc['id']}/challenge").json()
    assert ch["message"].startswith("hoola-approve|v1|default|editdesk|")
    monkeypatch.setattr(ak, "_check", lambda s, tenant, kind, target, proof, digest: kind == "editdesk" and proof.get("signature") == "ok")
    assert cl.post(f"/api/editdesk/cards/{rc['id']}/decide", json={"yes": True, "hash": rc["hash"], "proof": {"signature": "bad"}}).status_code == 428
    ok = cl.post(f"/api/editdesk/cards/{rc['id']}/decide", json={"yes": True, "hash": rc["hash"], "proof": {"signature": "ok"}})
    assert ok.status_code == 200 and "Refund" in ok.json()["say"]
    assert cl.get("/api/editdesk").json()["day"]["active"] == 0
    pdf = cl.get(f"/api/editdesk/quotes/{S.project_view(T, num)['quotes'][0]['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # tools
    from app.agent.editdesk_tools import EDITDESK_HANDLERS, EDITDESK_TOOLS
    from app.agent.tools import ToolError
    for tool in EDITDESK_TOOLS:
        props = tool["input_schema"]["properties"]
        assert all(k in props for k in tool["input_schema"]["required"])
    ctx = conv_ctx()
    out = asyncio.run(EDITDESK_HANDLERS["edit_desk"](ctx, action="project", client="Ravi", name="Wedding teaser",
                                                     brief="wedding teaser 1 min youtube aur insta reel, 5/11 tak"))
    assert out["project"]["kind"] == "wedding" and len(out["project"]["deliverables"]) == 2
    assert any("Haldi" == f["item"] for f in out["project"]["footage"])
    ctx.actor = "staff:7"
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(EDITDESK_HANDLERS["edit_desk"](ctx, action="paid", project=out["project"]["number"], amount=10))
    ctx.actor = "customer:wa:9822012345"
    with pytest.raises(ToolError, match="graahak"):
        asyncio.run(EDITDESK_HANDLERS["edit_desk"](ctx, action="notes", project=out["project"]["number"], text="0:10 cut"))
    ctx.actor = "owner"
    seen = asyncio.run(EDITDESK_HANDLERS["edit_desk_dekho"](ctx, what="project", project=out["project"]["number"]))
    assert seen["questions"] and seen["status"] == "brief"
    # the tool can never decide a card
    with pytest.raises(S.EditError):
        S.decide(T, rc["id"], True, rc["hash"])


def test_tick_and_forget(ed):
    S = ed
    _setup(S)
    num = S.project_new(T, "Neha Kapoor", "Reel", "insta reel 20 sec, kal tak")["project"]["number"]
    assert S.project_view(T, num)["due"] == "2026-10-24"
    out = S.tick(NOW)
    assert out["alerts"] == 1 and out["morning"] == 1
    assert "editdesk_alert" in kinds(S) and "editdesk_day" in kinds(S)
    assert S.tick(NOW)["alerts"] == 0 and S.tick(NOW)["morning"] == 0
    later = NOW + timedelta(days=3)
    S.CLK["t"] = later
    assert S.tick(later)["alerts"] == 1        # late now
    with pytest.raises(S.EditError, match="band"):
        S.forget(T, "Neha Kapoor")
    S.cancel(T, num, "client gaayab")
    out = S.forget(T, "Neha Kapoor")
    assert "hata" in out["say"]
    c = S.clients(T)[0]
    assert c["phone"] == "" and c["forgotten"] and "hataya" in c["name"]
