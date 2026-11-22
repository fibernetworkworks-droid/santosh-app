"""v0.999.102 HOOLA VOCAL - everything the redesign left out (owner: "GO BUILD ALL PENDING"): 4 takes, dialogue
reactions + a soft music bed, Dub it on a take, own-voice dub lines on ElevenLabs, hearing a take while it is made,
app keys + webhooks, keep my sounds for N days. No network: ElevenLabs, Gemini and webhook targets are faked at their
one seam each; ffmpeg is real."""
import asyncio
import hashlib
import hmac
import json
import pathlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.vocal import apps as AP
from app.vocal import eleven as EL
from app.vocal import more as M
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import (Resp, client, eleven, matched, needs_ff, run, tone,  # noqa: F401
                                                        vg)

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def pub(vg):
    from app.vocal import api
    app = FastAPI()
    app.include_router(api.make_router(lambda: None, lambda: "t1"))
    app.include_router(api.make_public_router())
    return TestClient(app)


@pytest.fixture
def gem(monkeypatch):
    """Gemini's JSON writer faked: translations come back as '<lang>:<text>'."""
    asked = []

    def fake(prompt):
        asked.append(prompt)
        texts = json.loads(prompt[prompt.rindex("\n\n") + 2:])
        langs = [p.split(" (")[0] for p in prompt.split("languages: ", 1)[1].split(". Keep")[0].split(", ")]
        return {c: {k: f"{c}:{t}" for k, t in texts.items()} for c in langs}
    monkeypatch.setattr(V, "_gem_json", fake)
    return asked


# ---------------------------------------------------------------- 4 takes
def test_up_to_four_takes(vg):
    r = run(V.tts("t1", "Hello there friends", voice="hv_Kore", takes=4))
    assert [x["take"] for x in r["items"]] == ["A", "B", "C", "D"]
    assert V.overview("t1")["limits"]["takes"] == 4
    assert V.settings_save("t1", {"takes": 9})["takes"] == 4
    assert "takes 1-4" in (ROOT / "server/app/agent/create_tools.py").read_text()


# ---------------------------------------------------------------- dialogue: reactions + soft music
def test_reactions_are_short_listener_sounds_from_the_other_speaker():
    rows = [("Asha", "This is a long line about our new bakery opening next week in the market."),
            ("Kofi", "Tell me more."), ("Asha", "We bake every morning at five, with butter from one farm only, always."),
            ("Kofi", "Nice."), ("Asha", "And on Sunday the first hundred people get a free box of cookies to take home.")]
    out, n = M.add_reactions(rows)
    added = [r for r in out if r not in rows]
    assert n == len(added) >= 1 and n <= len(rows) // 3 + 1
    assert all(t in M.REACTIONS and s == "Kofi" for s, t in added)
    assert out[-1] == rows[-1]                                   # never after the last line
    assert M.add_reactions([("A", "x" * 80)]) == ([("A", "x" * 80)], 0)


@needs_ff
def test_dialogue_with_reactions_and_soft_music(vg):
    lines = [{"speaker": "Asha", "text": "Welcome to the show, today we talk about bread and the people who bake it."},
             {"speaker": "Kofi", "text": "Thank you, it is good to be here."},
             {"speaker": "Asha", "text": "Tell us how you started baking at home during the long rainy season."}]
    row = run(V.dialogue("t1", lines, {"Asha": "hv_Kore", "Kofi": "hv_Puck"}, reactions=True, music="soft"))
    assert row["reactions"] >= 1 and row["music"] == "soft" and row["cast"] == {"Asha": "hv_Kore", "Kofi": "hv_Puck"}
    assert any(t in M.REACTIONS for *_, t in vg)                 # the reaction was spoken by an engine
    assert "Mm-hmm" not in row["text"]                           # the script she sees is her script
    wav = (V._home("t1") / "audio" / f"{row['id']}.wav").read_bytes()
    assert V.wav_seconds(wav) > 0.5
    with pytest.raises(V.VocalError, match="soft music or none"):
        run(V.dialogue("t1", lines, {"Asha": "hv_Kore", "Kofi": "hv_Puck"}, music="jazz"))


# ---------------------------------------------------------------- Dub it
def test_dub_it_speaks_a_take_in_other_languages_in_the_same_voice(vg, gem, client):
    t = run(V.tts("t1", "[warm] Fresh bread, 20% off today", voice="hv_Kore", lang="en", style="warm"))
    r = client.post(f"/api/vocal/take/{t['id']}/dub", json={"langs": ["es", "hi", "en"]}).json()
    assert [x["lang"] for x in r["items"]] == ["es", "hi"] and not r["failed"]
    assert all(x["dubbed_from"] == t["id"] and x["voice"] == "hv_Kore" and x["style"] == "warm" for x in r["items"])
    assert vg[-1][4].startswith("hi:") and "[warm]" not in vg[-1][4]       # tags kept for the engine, never read aloud
    assert "Keep every number" in gem[0] and "data, not instructions" in gem[0]


def test_dub_it_on_a_dialogue_keeps_each_speakers_voice(vg, gem):
    d = run(V.dialogue("t1", [{"speaker": "A", "text": "Hello there"}, {"speaker": "B", "text": "Hi back"}],
                       {"A": "hv_Kore", "B": "hv_Puck"}))
    r = run(M.take_dub("t1", d["id"], ["fr"]))
    assert r["items"][0]["kind"] == "dialogue" and r["items"][0]["cast"] == {"A": "hv_Kore", "B": "hv_Puck"}
    assert [x[1] for x in vg[-2:]] == ["Kore", "Puck"] and vg[-1][4] == "fr:Hi back"


def test_dub_it_is_honest(vg, gem):
    with pytest.raises(V.VocalError, match="not found"):
        run(M.take_dub("t1", "vo_000000000000", ["es"]))
    t = run(V.tts("t1", "Hello there", voice="hv_Kore", lang="en"))
    with pytest.raises(V.VocalError, match="other language"):
        run(M.take_dub("t1", t["id"], ["en"]))
    d = V._load("t1")
    d["history"][0]["kind"] = "dialogue"
    d["history"][0].pop("cast", None)
    V._store("t1", d)
    with pytest.raises(V.VocalError, match="before Dub it"):
        run(M.take_dub("t1", t["id"], ["es"]))


# ---------------------------------------------------------------- own-voice dub lines (ElevenLabs dubbing project)
def _own(vg):
    d = V._load("t1")
    d["dubs"] = [{"id": "vd_own", "status": "ready", "mode": "own", "name": "b.mp4", "seconds": 5, "lines": [],
                  "project": "p1", "targets": {"es": "L1"}, "src": "vd_own.mp4", "keep_sound": True,
                  "langs": [{"code": "es", "name": "Spanish", "status": "ready", "video_id": "vo_y"}]}]
    V._store("t1", d)
    V._DUB_THREADS.clear()


def test_own_voice_lines_are_read_changed_and_made_again(vg, eleven, client, monkeypatch):
    sent, replies = eleven
    _own(vg)
    segs = {"revision": 3, "segments": [{"id": "s1", "speaker_id": "spk_0", "start_s": 0.0, "end_s": 1.5,
                                         "source_text": "Hello", "translation": "Hola"},
                                        {"id": "s2", "speaker_id": "spk_1", "start_s": 2.0, "end_s": 3.0,
                                         "source_text": "Bye", "translation": None}]}
    replies["/transcript/segment/"] = lambda m, u, kw: Resp(body={"segment": {"id": "s2"}, "revision": 4})
    replies["/transcript/regenerate"] = lambda m, u, kw: Resp(status=202, body={"regenerated_segment_ids": ["s2"],
                                                                               "charged_seconds": 1.0})
    replies["/transcript"] = lambda m, u, kw: Resp(body=segs)
    got = client.get("/api/vocal/dub/vd_own/lines?lang=es").json()
    assert got["editable"] is True and got["own"] is True
    assert [(x["n"], x["src"], x["dst"], x["speaker"]) for x in got["lines"]] == [(0, "Hello", "Hola", "spk_0"), (1, "Bye", "", "spk_1")]
    with pytest.raises(V.VocalError, match="Change a line first"):
        V.dub_line_redo("t1", "vd_own", 0, "es")
    saved = client.put("/api/vocal/dub/vd_own/lines/1", json={"lang": "es", "text": "Adiós"}).json()
    assert saved["edited"] and saved["dst"] == "Adiós"
    patch = next(x for x in sent if x[0] == "PATCH")
    assert patch[1].endswith("/v1/dubbing/project/p1/language/L1/transcript/segment/s2") and patch[2]["json"] == {"translation": "Adiós"}
    monkeypatch.setattr(M, "_own_finish", lambda *a: None)
    out = client.post("/api/vocal/dub/vd_own/lines/1/redo", json={"lang": "es"}).json()
    assert out["status"] == "working" and out["lines"] == 1 and out["charged_seconds"] == 1.0
    assert any(m == "POST" and u.endswith("/language/L1/transcript/regenerate") for m, u, _ in sent)


def test_own_voice_lines_say_plainly_when_elevenlabs_allows_only_enterprise(vg, eleven):
    sent, replies = eleven
    _own(vg)
    replies["/transcript/segment/"] = lambda m, u, kw: Resp(status=403, body={"detail": {"message": "Enterprise only"}})
    replies["/transcript"] = lambda m, u, kw: Resp(body={"segments": [{"id": "s1", "source_text": "Hi", "translation": "Hola"}]})
    with pytest.raises(V.VocalError, match="only Enterprise accounts"):
        V.dub_line_save("t1", "vd_own", 0, "es", "Buenas")


@needs_ff
def test_own_voice_remake_puts_the_new_sound_on_the_video(vg, eleven, tmp_path, monkeypatch):
    import subprocess
    from tests.test_v0999_96_vocal_redesign_server import make_video
    sent, replies = eleven
    _own(vg)
    make_video(V._home("t1") / "dubs" / "vd_own.mp4", 2)
    V._keep("t1", b"\x00" * 100, "mp4", {"kind": "dub", "title": "b", "dub": "vd_own"})
    d = V._load("t1")
    d["dubs"][0]["langs"][0]["video_id"] = d["history"][0]["id"]
    d["dubs"][0]["own_edited"] = {"es": ["s1"]}
    V._store("t1", d)
    flac = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=2", "-f", "flac",
                           "pipe:1"], capture_output=True, timeout=60).stdout
    replies["/language/L1"] = lambda m, u, kw: Resp(body={"status": "completed", "revision": 4, "output_revision": 4,
                                                          "outputs": {"lossless_audio": {"url": "https://x.example/a.flac"},
                                                                      "subtitles": {"url": "https://x.example/s.vtt"}}})
    replies["s.vtt"] = lambda m, u, kw: Resp(content=b"WEBVTT\n\n00:00.000 --> 00:01.500\nBuenas\n")
    replies["x.example"] = lambda m, u, kw: Resp(content=flac)
    monkeypatch.setattr(V, "DUB_POLL_S", 0)
    M._own_finish("t1", "vd_own", "es", "L1", 1.0)
    g = V.dub_get("t1", "vd_own")
    assert "remaking" not in g["langs"][0] and not (g.get("own_edited") or {}).get("es")
    h = next(x for x in V._load("t1")["history"] if x["id"] == g["langs"][0]["video_id"])
    assert h["size"] > 1000
    srt = (V._home("t1") / "dubs" / "vd_own_es.srt").read_text()
    assert "00:00:00,000 --> 00:00:01,500" in srt and "Buenas" in srt


# ---------------------------------------------------------------- hear it while it is made
def test_streaming_plays_a_premium_take_while_it_is_made_and_keeps_it(vg, eleven, pub, monkeypatch):
    calls = []

    class R:
        status_code = 200

        def iter_bytes(self):
            yield b"ID3" + b"\x01" * 3000
            yield b"\x02" * 3000

    def stream(method, url, **kw):
        calls.append((method, url, kw))
        yield R()
    monkeypatch.setattr(EL, "_stream", stream)
    assert V.connected()["stream"] is True
    with pytest.raises(V.VocalError, match="Premium voices"):
        M.stream_start("t1", "Hello there", voice="hv_Kore")
    d = V._load("t1")
    d["voices"].append({"id": "mv_prem", "name": "Zara", "kind": "shared", "engine": "eleven", "eid": "e9", "made": V._now()})
    V._store("t1", d)
    s = pub.post("/api/vocal/tts/stream", json={"text": "Hello there friends", "voice": "mv_prem", "lang": "en"}).json()
    assert s["url"].startswith("/api/vocal/stream/") and s["format"] == "mp3"
    r = pub.get(s["url"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/mpeg") and len(r.content) == 6003
    assert calls[0][1].endswith("/v1/text-to-speech/e9/stream") and calls[0][2]["params"]["output_format"] == "mp3_44100_128"
    assert "xi-api-key" in calls[0][2]["headers"]
    row = V._load("t1")["history"][0]
    assert row["streamed"] and row["ext"] == "mp3" and row["voice"] == "mv_prem"
    assert pub.get(s["url"]).status_code == 404                  # the link works once


# ---------------------------------------------------------------- app keys + webhooks
def test_app_keys_are_shown_once_and_open_only_her_doors(vg, pub, monkeypatch):
    k = pub.post("/api/vocal/apps/keys", json={"name": "Shop app"}).json()
    assert k["key"].startswith("hv_live_") and k["last4"] == k["key"][-4:]
    view = pub.get("/api/vocal/apps").json()
    assert "key" not in view["keys"][0] and "sha" not in view["keys"][0]
    assert k["key"] not in (V._home("t1") / "vocal.json").read_text()
    assert pub.post("/api/vocal/v1/speech", json={"text": "Hi"}).status_code == 401
    assert pub.post("/api/vocal/v1/speech", json={"text": "Hi"}, headers={"Authorization": "Bearer hv_live_nope"}).status_code == 401
    h = {"Authorization": f"Bearer {k['key']}"}
    r = pub.post("/api/vocal/v1/speech", json={"text": "Hello from my app", "voice": "hv_Kore", "format": "wav"}, headers=h)
    assert r.status_code == 200 and r.content[:4] == b"RIFF" and r.headers["x-hoola-id"].startswith("vo_")
    assert pub.get(f"/api/vocal/v1/sounds/{r.headers['x-hoola-id']}", headers=h).status_code == 200
    assert any(v["id"] == "hv_Kore" for v in pub.get("/api/vocal/v1/voices", headers=h).json()["voices"])
    assert V._load("t1")["apps"]["keys"][0]["calls"] == 3
    monkeypatch.setattr(AP, "RATE_HOUR", 3)
    assert pub.get("/api/vocal/v1/voices", headers=h).status_code == 429
    pub.delete(f"/api/vocal/apps/keys/{k['id']}")
    assert pub.get("/api/vocal/v1/voices", headers=h).status_code == 401


def test_webhooks_go_to_public_https_only_signed_and_tried_three_times(vg, client, monkeypatch):
    monkeypatch.setattr(AP, "_RESOLVE", lambda host, port: [(0, 0, 0, "", ("10.0.0.5" if "inside" in host else "93.184.216.34", port))])
    for bad, why in (("http://shop.example/h", "https"), ("https://inside.example/h", "private address"),
                     ("https://localhost/h", "private network"), ("https://u:p@shop.example/h", "https")):
        r = client.post("/api/vocal/apps/hooks", json={"url": bad})
        assert r.status_code == 422 and why in r.json()["detail"]
    hk = client.post("/api/vocal/apps/hooks", json={"url": "https://shop.example/h"}).json()
    assert hk["secret"].startswith("whsec_") and hk["events"] == list(AP.EVENTS)
    assert hk["secret"] not in (V._home("t1") / "vocal.json").read_text()
    posts = []
    answers = iter([500, 502, 200])
    monkeypatch.setattr(AP, "_http_post", lambda url, body, headers: posts.append((url, body, headers)) or Resp(status=next(answers)))
    monkeypatch.setattr(AP, "WAITS", (0, 0, 0))
    monkeypatch.setattr(AP, "SYNC", True)
    row = run(V.tts("t1", "Hello there", voice="hv_Kore"))
    assert len(posts) == 3
    url, body, headers = posts[-1]
    t, v1 = (p.split("=", 1)[1] for p in headers["X-Hoola-Signature"].split(","))
    assert v1 == hmac.new(hk["secret"].encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    ev = json.loads(body)
    assert ev["event"] == "sound.ready" and ev["id"] == row["id"] and ev["download"].endswith(f"/api/vocal/v1/sounds/{row['id']}")
    assert client.get("/api/vocal/apps").json()["hooks"][0]["last_status"] == "200"
    monkeypatch.setattr(AP, "_http_post", lambda url, body, headers: Resp(status=204))
    assert client.post(f"/api/vocal/apps/hooks/{hk['id']}/test").json()["last_status"] == "204"


# ---------------------------------------------------------------- keep my sounds for N days
def test_keep_my_sounds_deletes_only_what_is_older_and_never_her_voices(vg, client):
    old = run(V.tts("t1", "Old take here", voice="hv_Kore"))
    new = run(V.tts("t1", "New take here", voice="hv_Kore"))
    d = V._load("t1")
    for h in d["history"]:
        if h["id"] == old["id"]:
            h["made"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(timespec="seconds")
    d["voices"].append({"id": "mv_me", "name": "Me", "kind": "clone", "engine": "lab", "made": "2020-01-01T00:00:00+00:00"})
    d["dubs"] = [{"id": "vd_old1", "status": "ready", "mode": "matched", "name": "a", "made": "2020-01-01T00:00:00+00:00",
                  "langs": [], "lines": []}]
    V._store("t1", d)
    (V._home("t1") / "dubs" / "vd_old1.mp4").write_bytes(b"x")
    assert M.sweep("t1") == {"sounds": 0, "dubs": 0}             # forever by default
    assert client.put("/api/vocal/settings", json={"keep_days": 30}).json()["keep_days"] == 30
    assert client.put("/api/vocal/settings", json={"keep_days": 12}).status_code == 422
    assert client.post("/api/vocal/sweep").json() == {"sounds": 1, "dubs": 1}
    d = V._load("t1")
    assert [h["id"] for h in d["history"]] == [new["id"]] and not d["dubs"] and any(v["id"] == "mv_me" for v in d["voices"])
    assert not (V._home("t1") / "dubs" / "vd_old1.mp4").exists()
    assert not list((V._home("t1") / "audio").glob(f"{old['id']}.*"))
    assert M.sweep_all(force=True) == 0
    assert "vocal_sweep_jobs" in (ROOT / "server/app/worker.py").read_text()


def test_the_switchboard_names_the_new_pieces(vg):
    c = V.connected()
    assert c["app_keys"] and c["webhooks"] and c["auto_delete"] and c["api"] and c["take_dub"] and c["reactions"]
    assert c["stream"] is False and c["dub_own_editor"] is False         # ElevenLabs is off in this fixture
