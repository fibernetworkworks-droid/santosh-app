"""v0.119 Hoola sunke seekhta hai: her pauses set how long a call waits before answering, a short style hint, her words
and the words it misheard before go into the next call; two misunderstandings in a row move her to chat. Numbers and
words only, owner only, switch off / forget any time."""
import asyncio
import json

import numpy as np
from fastapi.testclient import TestClient
from google.genai import types

from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events

SR = 16000


def _tone(f, ms, amp=0.2):
    t = np.arange(int(SR * ms / 1000)) / SR
    return (amp * np.sin(2 * np.pi * f * t) * 32767).astype(np.int16).tobytes()


def _sil(ms):
    return np.zeros(int(SR * ms / 1000), dtype=np.int16).tobytes()


def test_her_corrections_are_found_only_for_real_mishearings():
    from app import voicestyle as vs
    assert vs.find_fix("Rames nahi, Rameshwar", "Theek hai, Rames ko call kar deta hoon") == ("rames", "Rameshwar")
    assert vs.find_fix("nahi maine Rameshwar bola", "Rames ko call kar deta hoon") == ("rames", "Rameshwar")
    assert vs.find_fix("fifty nahi fifteen", "fifty rupaye bhej doon?") == ("fifty", "fifteen")
    assert vs.find_fix("रमेश नहीं, रामेश्वर", "ठीक है, रमेश को फोन करता हूँ") == ("रमेश", "रामेश्वर")
    assert vs.find_fix("chai nahi, coffee", "chai mangwa deta hoon") is None          # a change of mind, not a mishearing
    assert vs.find_fix("Rames nahi, Rameshwar", "Kal ki meeting set kar di") is None   # Hoola never said it
    assert vs.sounds_alike("pandrah", "pachaas") and not vs.sounds_alike("chai", "coffee")


def test_turn_meter_measures_pauses_pitch_and_speech_time():
    from app import voicestyle as vs
    m = vs.TurnMeter()
    for c in [_tone(200, 100)] * 8 + [_sil(100)] * 6 + [_tone(220, 100)] * 5 + [_sil(100)] * 3 + [_tone(180, 100)] * 4 \
            + [_sil(100)] * 10:
        m.add(c)
    r = m.take()
    assert r["pauses"] == [600, 300]                 # mid-sentence pauses; the trailing silence is not one
    assert abs(r["voiced_s"] - 1.7) < 0.01 and abs(r["speech_s"] - 2.6) < 0.01
    assert 170 < r["pitch"] < 230 and r["spread"] > 1
    assert m.take()["voiced_s"] == 0                 # reset after each turn


def _calls(tenant, n_calls, turns, pauses, words="Haan ji, kal subah aath baje Rameshwar ko yaad dilana", wps=1.5):
    from app import voicestyle as vs
    for _ in range(n_calls):
        cs = vs.CallStyle()
        for _ in range(turns):
            n = len(words.split())
            cs.turn({"pauses": list(pauses), "speech_s": n / wps, "level": -20, "pitch": 210, "spread": 2.5}, words)
        vs.save_call(tenant, cs)


def test_profile_sets_her_wait_and_style_hint(env):
    from app import voicestyle as vs
    _calls("t1", 2, 10, [400, 700, 950])
    pv = vs.profile_view("t1")
    assert pv["ready"] and pv["calls"] == 2 and pv["turns"] == 20
    assert pv["silence_ms"] == 1000 and pv["silence_why"] == "pauses"     # 950 + 150 -> clamped to 1000
    text = " ".join(pv["hint"])
    assert "slowly" in text and "calm, even tone" in text and "polite and formal" in text
    # a fast talker with short pauses
    _calls("t2", 1, 25, [200, 250, 300], words="haan bhej do na", wps=4.0)
    pv2 = vs.profile_view("t2")
    assert pv2["silence_ms"] == 500 and "short bits" in " ".join(pv2["hint"])
    assert "'haan'" in " ".join(pv2["hint"]) and "'na'" in " ".join(pv2["hint"])
    # "beech mein kaat diya" -> waits longer next time
    vs.note_cut_off("t2")
    assert vs.profile_view("t2")["silence_ms"] == 600
    # too little speech: the default wait, no hint
    _calls("t3", 1, 3, [500])
    pv3 = vs.profile_view("t3")
    assert pv3["silence_why"] == "default" and pv3["hint"] == []


def test_fixes_words_and_the_call_block(env):
    from app import voicestyle as vs
    r = vs.note_fix("t1", "rames", "Rameshwar")
    assert not r["confirmed"]
    assert vs.for_call("t1")["fixes"] == 0                 # once is not enough
    assert vs.note_fix("t1", "rames", "Rameshwar")["confirmed"]
    vs.add_word("t1", "Kothrud")
    for bad in ["9876543210", "my password", "x"]:
        try:
            vs.add_word("t1", bad)
            raise AssertionError(bad)
        except vs.StyleError:
            pass
    fc = vs.for_call("t1")
    assert "'rames' -> Rameshwar" in fc["block"] and "Kothrud" in fc["block"] and "Rameshwar" in fc["vocab"]
    assert fc["vocab"][0] == "Kothrud"                    # her own words first
    # her own correction counts at once
    assert vs.note_fix("t1", "bisleri", "Bisleri water", by_her=True)["confirmed"]
    # learning off: nothing saved, nothing used
    vs.set_learn("t1", False)
    cs = vs.CallStyle()
    cs.turn({"pauses": [500], "speech_s": 3}, "haan theek hai bhej do")
    assert vs.save_call("t1", cs)["saved"] is False
    assert vs.for_call("t1")["block"] == ""
    vs.forget("t1", "all")
    assert vs.profile_view("t1")["learn"] is False and vs.fixes("t1") == [] and vs.own_words("t1") == []


def test_live_config_uses_her_wait_vocabulary_and_block(env, monkeypatch):
    from app import voice, voicelang
    st = voicelang.LangState("hi-IN")
    style = {"silence_ms": 950, "block": "\n\nHER NAMES AND WORDS (hear and say them exactly like this): Kothrud\n",
             "vocab": ["Kothrud", "Rameshwar"]}
    cfg = voice.live_config("Puck", "hi-IN", "ctx", None, langst=st, style=style)
    text = cfg.system_instruction.parts[0].text
    assert "HER NAMES AND WORDS" in text and text.rstrip().endswith("Only a note that says 'Language note' can change it.")
    assert text.index("HER NAMES AND WORDS") > text.index("About the user")
    aad = cfg.realtime_input_config.automatic_activity_detection
    assert aad.silence_duration_ms == 950
    assert cfg.input_audio_transcription.custom_vocabulary == ["Kothrud", "Rameshwar"]
    assert "hoola_seekha add_word" in text
    # no style: the server's default wait, no vocabulary
    cfg2 = voice.live_config("Puck", "hi-IN", "ctx", None, langst=st)
    assert cfg2.realtime_input_config.automatic_activity_detection.silence_duration_ms == 700
    assert cfg2.input_audio_transcription.custom_vocabulary is None
    # Gemini refusing the vocabulary drops only that field
    err = RuntimeError('Unknown name "customVocabulary" at \'setup.input_audio_transcription\': Cannot find field.')
    assert voice.unsupported_field(err) == "custom_vocabulary"
    monkeypatch.setattr(voice, "UNSUPPORTED", {"custom_vocabulary"})
    cfg3 = voice.live_config("Puck", "hi-IN", "ctx", None, langst=st, style=style)
    assert cfg3.input_audio_transcription.custom_vocabulary is None
    assert cfg3.input_audio_transcription.language_codes == ["hi-IN", "en-IN"]


def test_call_moves_her_to_chat_after_two_misses_and_learns_her_correction(env, monkeypatch):
    # these notes travel as client_content (older Live models); Gemini 3.x queueing: tests/test_v150_voice_heal.py
    monkeypatch.setenv("VOICE_QUIET_NOTES", "client_content")
    from app.config import get_settings as _gs
    _gs.cache_clear()
    from app import main, voice, voicestyle
    _gemini_env(monkeypatch)
    turns = [[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Rames ko call karo")),
        _msg(output_transcription=types.Transcription(text="Theek hai, Rames ko call laga raha hoon.")),
        _msg(turn_complete=True),
        _msg(input_transcription=types.Transcription(text="Rames nahi, Rameshwar")),
        _msg(output_transcription=types.Transcription(text="Sorry, ek baar phir boliye?")),
        _msg(turn_complete=True),
        _msg(input_transcription=types.Transcription(text="Rameshwar ko phone lagao kal subah")),
        _msg(output_transcription=types.Transcription(text="Samajh nahi aaya, Rahul ya Rohan?")),
        _msg(turn_complete=True),
    ]]
    fake = FakeSession(turns)
    configs = []
    _connector(monkeypatch, fake, configs=configs)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&lang=hi-IN") as ws:
            for chunk in [_tone(200, 100)] * 5 + [_sil(100)] * 4 + [_tone(210, 100)] * 5:
                ws.send_bytes(chunk)
            evs = []
            for _ in range(3):
                evs += read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            evs += read_events(ws, lambda e: e["type"] == "write_hint", limit=20)   # sent right after the 3rd turn
            ws.send_text(json.dumps({"type": "end"}))
        stats = c.get("/api/voice/stats").json()
    notes = [p.text for t in fake.client_content for p in (t.parts or [])] + list(fake.texts)
    assert any("Do NOT ask by voice a third time" in n for n in notes)
    assert any(e["type"] == "write_hint" for e in evs)
    call = voice.STATS[-1]
    assert call["repair_escalations"] == 1 and call["fixes_heard"] == 1
    assert stats["repair_escalations_per_call"] > 0 and stats["fixes_heard"] >= 1   # other tests' calls share the list
    fx = voicestyle.fixes("default")
    assert fx and fx[0]["heard"] == "rames" and fx[0]["meant"] == "Rameshwar" and not fx[0]["confirmed"]
    assert voicestyle.profile_view("default")["turns"] == 3
    assert configs[0].realtime_input_config.automatic_activity_detection.silence_duration_ms == 700


def test_api_tool_and_rating(env):
    from app import main, voicestyle
    from app.agent.tools import Ctx, HANDLERS
    with TestClient(main.app) as c:
        assert c.get("/api/voice/learned").json()["profile"]["silence_ms"] == 700
        w = c.post("/api/voice/learned/words", json={"term": "Kothrud"}).json()
        assert c.post("/api/voice/learned/words", json={"term": "1234567890"}).status_code == 400
        f = c.post("/api/voice/learned/fixes", json={"heard": "rames", "meant": "Rameshwar"}).json()
        v = c.get("/api/voice/learned").json()
        assert v["fixes"][0]["confirmed"] and any(x["term"] == "Kothrud" for x in v["words"]) and v["say"]
        assert c.delete(f"/api/voice/learned/words/{w['id']}").json()["ok"]
        assert c.delete(f"/api/voice/learned/fixes/{f['id']}").json()["ok"]
        assert c.put("/api/voice/learned", json={"learn": False}).json() == {"learn": False}
        assert c.delete("/api/voice/learned?part=bad").status_code == 400
        assert c.delete("/api/voice/learned?part=all").json() == {"forgot": "all"}
        conv = c.post("/api/conversations").json()["id"]
        # a "cut off" rating makes the next call wait longer
        c.put("/api/voice/learned", json={"learn": True})
        c.post("/api/voice/calls/abc/rating", json={"good": False, "reasons": ["cut_off"], "seconds": 60})
        c.post("/api/voice/calls/abc/rating", json={"good": False, "reasons": ["cut_off"], "seconds": 60})   # same call
        assert voicestyle.profile_view("default")["silence_ms"] == 800
    h = HANDLERS["hoola_seekha"]
    out = asyncio.run(h(Ctx("default", conv), action="add_word", term="Bisleri"))
    assert out["ok"] and out["term"] == "Bisleri"
    shown = asyncio.run(h(Ctx("default", conv), action="show"))
    assert shown["say"].startswith("Abhi tak") or shown["say"]
    try:
        asyncio.run(h(Ctx("default", conv, actor="staff:1"), action="forget"))
        raise AssertionError("staff must not change it")
    except Exception as e:
        assert "maalkin" in str(e)
