"""Podcast Sahayak: rules (time codes, captions, chapters valid for Spotify / YouTube, quotes only from the transcript, ASCI #Ad at
start + end, Apple loudness / artwork, podcast:guid, stats parsing, RSS), show + artwork (EXIF dropped), guests + recording slots
that never overlap, run sheet, real ffmpeg loudness + normalised copy, transcript only from her audio / file, show notes that drop
invented quotes and numbers, licence register + releases + reads blocking publish, publish / message / invoice only by HER tap with
the card's hash, Hoola RSS feed (public, token-checked, only published episodes), analytics she pastes, worker, DPDP forget, tools + API."""
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.podcast.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
NOW = datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc)        # 10:30 am IST

VTT = """WEBVTT

00:00:00.000 --> 00:00:20.000
Meghana: Namaste, swagat hai Gaon Ki Baat podcast mein. Aaj humare saath Ramesh ji hain.

00:00:20.000 --> 00:01:10.000
Ramesh: Main pichhle 12 saal se kheti kar raha hoon, aur drip irrigation se paani bachta hai.

00:01:10.000 --> 00:02:30.000
Meghana: Yeh episode Kisan Bazaar ki taraf se sponsored hai. Kisan Bazaar se beej mangwaiye. Yeh ek paid advertisement tha.

00:02:30.000 --> 00:04:00.000
Ramesh: Mitti ki jaanch har saal karwani chahiye, yeh sabse zaroori baat hai.

00:04:00.000 --> 00:05:30.000
Meghana: Ramesh ji, kya main aapki baat record karke publish kar sakti hoon? Ramesh: Haan, main sehmat hoon, i agree.

00:05:30.000 --> 00:07:00.000
Meghana: Dhanyavaad, agle episode mein milte hain.
"""


@pytest.fixture
def pod(env, monkeypatch, tmp_path):
    from app.podcast import service as S
    events, stored = [], []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))

    def fake_store(tenant, name, data, mime, conv="", title=""):
        stored.append((name, data))
        return {"file_id": f"f{len(stored)}", "name": name}
    monkeypatch.setattr(S, "_store", fake_store)
    monkeypatch.setattr(S, "DATA_ROOT", tmp_path / "pod")
    monkeypatch.setattr(S, "_model_json", lambda *a, **k: {})
    files = {}
    monkeypatch.setattr(S, "_file_bytes", lambda tenant, fid: files[fid])
    clk = {"t": NOW}
    monkeypatch.setattr(S, "clock", lambda: clk["t"])
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.in")
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    S.EVENTS, S.STORED, S.CLK, S.FILES = events, stored, clk, files
    return S


def _tone(path, seconds=40, vol=0.05):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-af", f"volume={vol}", "-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "64k", str(path)], check=True)
    return path.read_bytes()


def _show(S):
    S.save_settings(T, show="Gaon Ki Baat", host="Meghana", author="Newtika", description="Kheti aur gaon ki baatein",
                    language="hi", category="Business", owner_email="build@ainewtika.com", upi_id="meghana@okicici",
                    gstin="27AAPFU0939F1ZV", business="Newtika Pvt Ltd")


def test_rules():
    from app.podcast import rules as R
    assert R.ts("1:02:03") == 3723 and R.ts("02:03") == 123 and R.ts("(00:01:02.500)") == 62.5 and R.ts("1:75") is None
    assert R.hms(65) == "01:05" and R.hms(3725) == "01:02:05"
    segs = R.parse_captions(VTT)
    assert len(segs) == 6 and segs[1]["speaker"] == "Ramesh" and segs[1]["start"] == 20
    srt = R.to_srt(segs)
    assert R.parse_captions(srt)[2]["start"] == 70 and R.to_vtt(segs).startswith("WEBVTT")
    # chapters: snapped to real starts, first 00:00, >= 30 s apart, no emoji
    ch = R.fix_chapters([{"start": 25, "title": "Kheti 🌾"}, {"start": 5, "title": "Intro"}, {"start": 80, "title": "Sponsor"},
                         {"start": 95, "title": "Too close"}, {"start": 160, "title": "Mitti"}, {"start": 999, "title": "Past end"}], segs, 420)
    assert [c["start"] for c in ch] == [0.0, 70, 150] and ch[0]["title"] == "Intro" and ch[1]["title"] == "Sponsor"
    assert not R.chapter_problems(ch, 420)
    assert "Kam se kam 3" in R.chapter_problems(ch[:2], 420)[0]
    assert "01:10 Sponsor" in R.chapters_text(ch)
    # quotes only if the words are in the transcript
    assert R.find_quote("mitti ki jaanch har saal karwani chahiye", segs)["start"] == 150
    assert R.find_quote("organic farming se double income", segs) is None
    assert R.unbacked_numbers("12 saal aur 40% fayda", [" ".join(s["text"] for s in segs)]) == ["40"]
    # ASCI: label at start AND end of the read
    d = R.read_disclosure("Kisan Bazaar se beej mangwaiye, 100% guarantee.")
    assert not d["ok"] and not d["start"]
    fixed = R.add_disclosure("Kisan Bazaar se beej mangwaiye.", "Kisan Bazaar")
    assert R.read_disclosure(fixed)["ok"] and fixed.count("#Ad") == 2
    assert R.risky_claims("100% guarantee milega") == ["guarantee", "100%"]
    td = R.transcript_disclosure(segs, "Kisan Bazaar")
    assert td["found"] and td["ok"]
    # Apple loudness / artwork
    assert R.loudness_verdict(-16.4, -1.5)["ok"] and not R.loudness_verdict(-23, -0.2)["ok"]
    assert len(R.loudness_verdict(-23, -0.2)["problems"]) == 2
    assert R.artwork_problems(3000, 3000, "PNG", "RGB") == []
    assert len(R.artwork_problems(1000, 800, "GIF", "CMYK")) == 4
    # podcast:guid example from the Podcast Index spec
    assert R.feed_guid("https://mp3s.nashownotes.com/pc20rss.xml/") == "917393e3-1b1e-5cef-ace4-edaa54e1f810"
    # analytics export (Spotify style CSV)
    rows = R.parse_stats("Episode,Date,Streams,Listeners,Avg consumption\nEP1 Kheti,2026-10-01,1200,800,0.55\nTotal,,1200,800,\n")
    assert rows == [{"label": "EP1 Kheti", "day": "2026-10-01", "plays": 1200.0, "listeners": 800.0, "consumption": 55.0}]
    assert R.parse_stats("random,text\n1,2") == []
    assert R.phone("+91 98220 12345") == "9822012345" and R.scrub("OTP 123456, card 4111 1111 1111 1111") == \
        "OTP [hataya] card [number hataya]"


def test_show_artwork_guests_slots_runsheet(pod):
    S = pod
    from PIL import Image
    import io
    with pytest.raises(S.PodcastError):
        S.save_settings(T, category="Gossip")
    _show(S)
    im = Image.new("RGB", (1500, 1500), (200, 40, 40))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes())
    r = S.set_artwork(T, data=buf.getvalue(), name="art.jpg")
    assert r["artwork"]["problems"] == [] and r["artwork"]["w"] == 1500
    saved = Image.open(S.DATA_ROOT / "default" / "artwork.jpg")
    assert not saved.getexif()                                     # EXIF gone
    small = io.BytesIO()
    Image.new("RGB", (800, 600)).save(small, "PNG")
    assert S.set_artwork(T, data=small.getvalue())["artwork"]["problems"]

    g = S.guest_save(T, "Ramesh Patil", "98220 12345", bio="Kisan, Akola. 12 saal se kheti. OTP 556677",
                     topics=["drip irrigation"])["guest"]
    assert g["number"] == "G-001" and "[hataya]" in g["bio"] and g["release"]["status"] == "none"
    e1 = S.episode_save(T, title="Paani bachao", topics=["drip irrigation", "mitti ki jaanch"], guests=["G-001"],
                        record_at="2026-10-25 18:00", record_minutes=60)["episode"]
    assert e1["status"] == "booked" and e1["record_at"] == "25-10-2026 18:00"
    assert S.guests(T)[0]["status"] == "confirmed"
    with pytest.raises(S.PodcastError, match="EP-001"):          # overlaps (gap 30 min)
        S.episode_save(T, title="Doosra", record_at="2026-10-25 19:15")
    e2 = S.episode_save(T, title="Doosra", record_at="2026-10-25 19:45")["episode"]
    assert e2["status"] == "booked"
    with pytest.raises(S.PodcastError, match="beet"):
        S.episode_save(T, title="Past", record_at="2026-10-20 10:00")
    # run sheet: no model -> plain prompts from her topics; with model -> its questions
    rs = S.run_sheet(T, "EP-001")["run_sheet"]
    assert rs[0]["what"].startswith("Intro") and any(x["what"] == "mitti ki jaanch" for x in rs)
    S._model_json = lambda *a, **k: {"questions": {"drip irrigation": ["Drip kab shuru kiya?"]}}
    rs2 = S.run_sheet(T, "EP-001")["run_sheet"]
    assert next(x for x in rs2 if x["what"] == "drip irrigation")["notes"] == ["Drip kab shuru kiya?"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg needed")
def test_audio_loudness_normalize_and_transcript(pod, tmp_path):
    S = pod
    _show(S)
    S.episode_save(T, title="Paani bachao")
    data = _tone(tmp_path / "quiet.mp3", 40, 0.03)
    r = S.attach_audio(T, "EP-001", data=data, name="quiet.mp3")
    lo = r["loudness"]
    assert r["audio"]["duration"] and 39 <= r["audio"]["duration"] <= 41
    assert lo["lufs"] < -20 and lo["ok"] is False
    assert S.episode_view(T, "EP-001")["status"] == "recorded"
    src = S.episode_view(T, "EP-001")
    n = S.normalize(T, "EP-001")
    assert abs(n["loudness"]["lufs"] + 16) <= 1.0 and n["loudness"]["ok"] is True
    from app.podcast.models import PodcastEpisode
    from app.db import session
    import json
    with session() as s:
        au = json.loads(s.query(PodcastEpisode).one().audio)
    assert au["normalized"] and (tmp_path / "pod").exists() and src["audio"]["name"] == "quiet.mp3"
    from pathlib import Path
    assert Path(au["original"]).exists()                            # her original is never overwritten
    with pytest.raises(S.PodcastError):
        S.attach_audio(T, "EP-001", data=b"hello", name="notes.txt")
    # transcript: engines give nothing -> plain refusal, never made up
    S._engine_transcribe = lambda *a: ([], "")
    with pytest.raises(S.PodcastError, match="SRT"):
        S.transcribe(T, "EP-001")
    S._engine_transcribe = lambda *a: ([{"start": 0, "end": 20, "text": "Namaste dosto", "speaker": "S1"},
                                        {"start": 20, "end": 39, "text": "aaj paani ki baat", "speaker": "S2"}], "gemini")
    out = S.transcribe(T, "EP-001")
    assert out["source"] == "gemini" and out["segments"] == 2
    S.set_speakers(T, "EP-001", {"S1": "Meghana"})
    data, mime, name = S.transcript_file(T, "EP-001", "srt")
    assert b"Meghana: Namaste dosto" in data and name == "EP-001_transcript.srt"


def _ready_episode(S, tmp_path, with_audio=True):
    _show(S)
    S.guest_save(T, "Ramesh Patil", "9822012345", email="ramesh@example.in")
    S.episode_save(T, title="Paani bachao", guests=["G-001"], explicit=False)
    if with_audio:
        S.attach_audio(T, "EP-001", data=_tone(tmp_path / "ep.mp3", 425, 0.1), name="ep.mp3") if shutil.which("ffmpeg") else \
            S.attach_audio(T, "EP-001", data=b"ID3" + b"\x00" * 2000, name="ep.mp3")
    S.transcribe(T, "EP-001", text=VTT)
    return S


def test_notes_drop_invented_things(pod, tmp_path):
    S = _ready_episode(pod, tmp_path)
    S._model_json = lambda *a, **k: {
        "summary": "Ramesh ji 12 saal se kheti kar rahe hain. Drip se 40% paani bachta hai.",
        "points": ["Mitti ki jaanch har saal", "50 hazaar ki bachat"],
        "chapters": [{"start": 0, "title": "Swagat"}, {"start": 22, "title": "Drip irrigation"}, {"start": 75, "title": "Sponsor"},
                     {"start": 151, "title": "Mitti ki jaanch"}, {"start": 160, "title": "Too close"}],
        "quotes": [{"text": "Mitti ki jaanch har saal karwani chahiye"}, {"text": "Kheti se crorepati bano"}]}
    nt = S.make_notes(T, "EP-001")["notes"]
    assert nt["summary"] == "Ramesh ji 12 saal se kheti kar rahe hain."          # the 40% sentence is not in the audio
    assert nt["points"] == ["Mitti ki jaanch har saal"]
    assert [c["start"] for c in nt["chapters"]] == [0.0, 70, 150]
    assert [q["text"] for q in nt["quotes"]] == ["Mitti ki jaanch har saal karwani chahiye"] and nt["quotes"][0]["start"] == 150
    assert len(nt["dropped"]) == 3
    d = S.description(T, "EP-001")
    assert "Chapters:" in d and "02:30 Mitti ki jaanch" in d and "Guest: Ramesh Patil" in d
    # her own edit: chapters as text lines, re-validated
    e = S.edit_notes(T, "EP-001", chapters="00:00 Shuru\n01:10 Sponsor\n02:30 Mitti", summary="Mera summary.")
    assert [c["title"] for c in e["notes"]["chapters"]] == ["Shuru", "Sponsor", "Mitti"] and e["problems"] == []
    cp = S.crosspost(T, "EP-001")["drafts"]
    assert len(cp["x"]) <= 280 and "Mera summary." in cp["linkedin"]


def test_publish_blockers_and_her_tap(pod, tmp_path):
    S = _ready_episode(pod, tmp_path)
    S.make_notes(T, "EP-001")                                     # no model: summary blank -> blocker
    ck = S.checks(T, "EP-001")
    assert any("release" in b for b in ck["blockers"]) and any("summary" in b for b in ck["blockers"])
    S.edit_notes(T, "EP-001", summary="Paani bachane ki baat.")
    # music with unknown licence blocks
    S.music_save(T, "Film song", "unknown")
    S.music_use(T, "EP-001", "M-001")
    with pytest.raises(S.PodcastError):
        S.music_save(T, "CC track", "cc_by")                      # credit line needed
    # sponsor read without disclosure blocks
    S.sponsor_save(T, "Kisan Bazaar", phone="9876543210")
    S.read_save(T, "EP-001", "Kisan Bazaar", "Kisan Bazaar se beej mangwaiye.", "mid", fix=False)
    ck = S.checks(T, "EP-001")
    assert any("Film song" in b for b in ck["blockers"]) and any("Kisan Bazaar read" in b for b in ck["blockers"])
    with pytest.raises(S.PodcastError, match="publish nahi"):
        S.publish_request(T, "EP-001")
    # fix: licence, disclosure, release (guest's written yes)
    S.music_save(T, "", "paid", proof="Invoice from library", music="M-001")
    S.read_save(T, "EP-001", "Kisan Bazaar", "Kisan Bazaar se beej mangwaiye.", "mid", brand_ok=True)
    rq = S.release_request(T, "G-001", "EP-001")
    assert rq["status"] == "needs_tap" and "AI se nayi awaaz" in rq["card"]["show"]["text"]
    out = S.decide(T, rq["card"]["id"], True, rq["card"]["hash"], by_tap=True)
    assert out["draft"]["wa"].startswith("https://wa.me/919822012345") and out["draft"]["mail"].startswith("mailto:ramesh@")
    assert S.guest_view(T, "G-001")["release"]["status"] == "requested"
    with pytest.raises(S.PodcastError):
        S.release_got(T, "G-001", "text", text="theek hai dekhenge")     # no clear yes
    with pytest.raises(S.PodcastError, match="owner"):
        S.release_got(T, "G-001", "text", text="I agree", actor="staff:x")
    S.release_got(T, "G-001", "text", text="Haan, main sehmat hoon. I agree.")
    assert S.checks(T, "EP-001")["blockers"] == []
    # turning the feed on, publish card -> only her tap, hash rebuilt from the state now
    S.feed_set(T, True)
    card = S.publish_request(T, "EP-001")["card"]
    assert card["show"]["where"] == "feed" and card["show"]["guests"] == [{"name": "Ramesh Patil", "release": "signed"}]
    assert S.publish_request(T, "EP-001")["existing"] is True
    with pytest.raises(S.PodcastError, match="tap"):
        S.decide(T, card["id"], True, card["hash"])
    with pytest.raises(S.PodcastError):
        S.decide(T, card["id"], True, "wrong", by_tap=True)
    S.edit_notes(T, "EP-001", summary="Badla hua summary.")      # change after the card -> stale
    with pytest.raises(S.PodcastError, match="badal"):
        S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert S.card_view(T, card["id"])["status"] == "stale"
    card = S.publish_request(T, "EP-001")["card"]
    pub = S.decide(T, card["id"], True, card["hash"], by_tap=True)
    assert "publish hua" in pub["say"] and pub["feed"].startswith("https://hoola.example.in/api/podcast/feed/")
    assert {f["name"] for f in pub["files"]} >= {"EP-001_transcript.vtt", "EP-001_show_notes.md", "EP-001_chapters.json"} or \
        {f["name"] for f in pub["files"]} >= {"EP-001_transcript.vtt", "EP-001_show_notes.md"}
    assert S.episode_view(T, "EP-001")["status"] == "published"
    # the feed: valid XML, namespaces, enclosure, transcript + person only for a released guest
    tok = S.feed_info(T)["url"].rsplit("/", 1)[1][:-4]
    x = S.feed_xml(tok)
    root = ET.fromstring(x.encode())
    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd", "podcast": "https://podcastindex.org/namespace/1.0"}
    item = root.find("channel/item")
    assert root.find("channel/title").text == "Gaon Ki Baat" and item.find("enclosure") is not None
    assert item.find("podcast:transcript", ns).get("type") == "text/vtt"
    assert [p.text for p in item.findall("podcast:person", ns)] == ["Meghana", "Ramesh Patil"]
    assert root.find("channel/podcast:locked", ns).text == "yes"
    assert "#Ad" in item.find("description").text                  # disclosure in the description too
    assert S.feed_xml("x" * 24) is None
    assert S.pub_file(tok, S.episodes(T)[0]["id"], "transcript.vtt")[1].startswith(b"WEBVTT")
    assert S.pub_file(tok, S.episodes(T)[0]["id"], "nope") is None
    # unpublish: gone from the feed and the public files
    S.unpublish(T, "EP-001", "galti")
    assert S.pub_file(tok, S.episodes(T)[0]["id"], "transcript.vtt") is None
    assert ET.fromstring(S.feed_xml(tok).encode()).find("channel/item") is None
    # revoke after publishing names the live episodes
    S.feed_set(T, True)
    card = S.publish_request(T, "EP-001")["card"]
    S.decide(T, card["id"], True, card["hash"], by_tap=True)
    rv = S.release_revoke(T, "G-001", "mann badla")
    assert rv["live_episodes"] == ["EP-001"]
    assert any("release" in b for b in S.checks(T, "EP-001")["blockers"])


def test_sponsor_invoice_money_and_messages(pod, tmp_path):
    S = pod
    _show(S)
    S.sponsor_save(T, "Kisan Bazaar", phone="9876543210", email="ads@kisan.example", gstin="27AAAAA0000A1Z5")
    with pytest.raises(S.PodcastError, match="Fees nahi pata"):
        S.invoice_request(T, "S-001")                              # never guesses the fee
    with pytest.raises(S.PodcastError, match="owner"):
        S.sponsor_save(T, sponsor="S-001", amount=25000, actor="staff:x")
    S.sponsor_save(T, sponsor="S-001", amount=25000, status="agreed")
    inv = S.invoice_request(T, "S-001")["card"]
    sh = inv["show"]
    assert sh["total"] == 29500 and sh["gst"] == {"cgst": 2250.0, "sgst": 2250.0} and sh["number"].startswith("POD/2627/")
    assert inv["money"] is True
    out = S.decide(T, inv["id"], True, inv["hash"], by_tap=True)
    assert out["draft"]["upi"].startswith("upi://pay?pa=meghana%40okicici") and "am=29500.00" in out["draft"]["upi"]
    assert S.STORED[-1][0].endswith(".pdf") and S.STORED[-1][1][:4] == b"%PDF"
    assert S.day(T)["unpaid"] == ["Kisan Bazaar"]
    with pytest.raises(S.PodcastError):
        S.paid(T, "S-001", 29500, actor="staff:x")
    S.paid(T, "S-001", 29500, "UTR998877", tds=500)
    assert S.day(T)["unpaid"] == []
    # guest who said no to messages
    S.guest_save(T, "Sunita", "9123456780", no_messages=True)
    with pytest.raises(S.PodcastError, match="message"):
        S.invite_request(T, "G-001")
    m = S.message_request(T, "S-001", "Script bhej rahe hain")
    assert m["card"]["show"]["brand"] == "Kisan Bazaar"
    rej = S.decide(T, m["card"]["id"], False, m["card"]["hash"], "abhi nahi", by_tap=True)
    assert rej["card"]["status"] == "rejected"


def test_stats_tick_forget(pod, tmp_path):
    S = pod
    _show(S)
    S.guest_save(T, "Ramesh Patil", "9822012345")
    S.episode_save(T, title="Paani bachao", guests=["G-001"], record_at="2026-10-23 20:00", publish_on="2026-10-24")
    r = S.stats_import(T, "Episode,Date,Streams,Listeners,Avg consumption\nPaani bachao,2026-10-01,1200,800,35%\n", platform="spotify")
    assert r["added"] == 1
    assert S.stats_import(T, "Episode,Date,Streams,Listeners\nPaani bachao,2026-10-01,1200,800\n", platform="spotify")["added"] == 0   # same row again
    rep = S.stats_report(T)
    assert rep["episodes"][0]["number"] == "EP-001" and "40%" in rep["say"]
    with pytest.raises(S.PodcastError):
        S.stats_import(T, "hello world")
    out = S.tick(NOW)
    kinds = [p.get("kind") for k, p in S.EVENTS if k == "podcast_alert"]
    assert "recording" in kinds and "publish_soon" in kinds and out["morning"] == 1
    n = len(S.EVENTS)
    S.tick(NOW + timedelta(minutes=1))
    assert len(S.EVENTS) == n                                     # once each, morning once a day
    S.tick(NOW + timedelta(hours=16))                              # recording passed, no audio
    assert any(p.get("kind") == "no_audio" for k, p in S.EVENTS if k == "podcast_alert")
    f = S.forget_guest(T, "G-001")
    g = S.guest_view(T, "G-001")
    assert g["phone"] == "" and g["name"] == "Ramesh Patil" and g["forgotten"] and "release" in f["say"]


def test_tools_and_api(pod, tmp_path):
    S = pod
    import asyncio
    from app.agent.podcast_tools import PODCAST_HANDLERS, PODCAST_TOOLS
    from app.agent.tools import ToolError
    for t in PODCAST_TOOLS:
        assert set(t["input_schema"]["required"]) <= set(t["input_schema"]["properties"])
    ctx = conv_ctx()
    run = lambda tool, **a: asyncio.run(PODCAST_HANDLERS[tool](ctx, **a))  # noqa: E731
    run("podcast", action="settings", show="Gaon Ki Baat", host="Meghana")
    run("podcast", action="episode", title="Paani bachao", topics=["drip"])
    assert run("podcast_dekho", what="episodes")["episodes"][0]["number"] == "EP-001"
    assert "blockers" in run("podcast_dekho", what="checks", episode="EP-001")
    ctx.actor = "staff:abc"
    with pytest.raises(ToolError, match="owner"):
        run("podcast", action="feed", on=True)
    ctx.actor = "customer:wa:91"
    with pytest.raises(ToolError, match="graahak"):
        run("podcast", action="guest", name="X")
    ctx.actor = "owner"
    # the tool can only make the card, never decide it
    run("podcast", action="sponsor", brand="Kisan Bazaar", amount=1000)
    c = run("podcast", action="invoice", sponsor="S-001")
    assert c["status"] == "needs_tap" and S.card_view(T, c["card"]["id"])["status"] == "waiting"

    from app.podcast.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    cl = TestClient(app)
    assert cl.get("/api/podcast").json()["settings"]["show"] == "Gaon Ki Baat"
    r = cl.post("/api/podcast/episodes", json={"title": "Doosra"})
    assert r.json()["episode"]["number"] == "EP-002"
    assert cl.post("/api/podcast/episodes", json={"episode": "EP-002", "kind": "bad"}).status_code == 400
    cid, h = c["card"]["id"], c["card"]["hash"]
    d = cl.post(f"/api/podcast/cards/{cid}/decide", json={"yes": True, "hash": h}).json()
    assert d["card"]["status"] == "approved"
    cl.post("/api/podcast/feed", json={"on": True})
    tok = S.feed_info(T)["url"].rsplit("/", 1)[1][:-4]
    fx = cl.get(f"/api/podcast/feed/{tok}.xml")
    assert fx.status_code == 200 and fx.headers["content-type"].startswith("application/rss+xml")
    assert cl.get("/api/podcast/feed/notatokenatall12345.xml").status_code == 404
    up = cl.post("/api/podcast/episodes/EP-002/captions", files={"file": ("c.vtt", VTT.encode(), "text/vtt")})
    assert up.status_code == 200 and up.json()["segments"] == 6
    t = cl.get("/api/podcast/episodes/EP-002/transcript.json")
    assert t.status_code == 200 and t.json()["segments"][0]["speaker"] == "Meghana"
