"""v0.114 Bhasha pakki + sunke samjho: the call's language is kept by the server (sticky, Google's lock line at the top
and the end, transcript language hint), Hoola's own drift gets a quiet correction, unclear transcripts never become
memory, and the persona asks again / reads back instead of guessing."""
import asyncio
import json

from fastapi.testclient import TestClient
from google.genai import types

from tests.test_voice import FakeSession, _connector, _gemini_env, _msg, read_events


def test_detect_scripts_and_hindi_vs_marathi():
    from app import voicelang as v
    assert v.detect("Kal ki meeting 4 baje kar do na")["lang"] == "hi-IN"
    assert v.detect("मला उद्या सकाळी आठ वाजता आठवण करून दे")["lang"] == "mr-IN"
    assert v.detect("मुझे कल सुबह आठ बजे याद दिला देना")["lang"] == "hi-IN"
    assert v.detect("Mala udya sakali athvan karun de na, kay?")["lang"] == "mr-IN"
    assert v.detect("Please check the payment status and tell me")["lang"] == "en-IN"
    assert v.detect("Meeting ka time update kar diya, ab four baje hai")["lang"] == "hi-IN"
    assert v.detect("ஒரு செகண்ட் இருங்க நான் பார்க்கிறேன்")["lang"] == "ta-IN"
    assert v.detect("ჩემი სახელი")["lang"] == "other"
    assert v.detect("haan")["strong"] is False


def test_switch_rules_are_sticky():
    from app import voicelang as v
    s = v.LangState("hi-IN")
    # English words, greetings, numbers and one English sentence never switch
    for t in ["ok", "haan haan", "4 5 6 7", "Meeting ka update share kar do", "Please send the invoice to the client today"]:
        assert s.hear(t)["switched"] == ""
    assert s.base == "hi-IN"
    s.hear("Kal ka plan batao")                     # back to Hindi: the streak starts again
    s.hear("Please send the invoice to the client today")
    assert s.base == "hi-IN"
    assert s.hear("And also check the payment status for me today")["switched"] == "en-IN"   # two in a row
    # her explicit ask switches at once
    s2 = v.LangState("hi-IN")
    assert s2.hear("Marathi mein bolo na please")["switched"] == "mr-IN" and s2.base == "mr-IN"
    # Hindi <-> Marathi needs clear grammar, not one shared word
    s3 = v.LangState("hi-IN")
    s3.hear("आज काम है क्या")
    assert s3.base == "hi-IN"
    # a wrong-script transcript is a mis-hearing, never her language
    s4 = v.LangState("hi-IN")
    r = s4.hear("ჩემი სახელი არის")
    assert r["unclear"] and s4.base == "hi-IN"


def test_reply_drift_note_and_cooldown():
    from app import voicelang as v
    s = v.LangState("hi-IN")
    s.turns = 5
    note = s.check_reply("Sure, I have moved the meeting to four o'clock for you today.")
    assert "RESPOND UNMISTAKABLY IN HINDI" in note and "not her words" in note
    assert s.check_reply("Sure, I have moved the meeting to four o'clock for you today.") == ""   # cooldown
    assert s.drifts == 2
    assert s.check_reply("Haan, meeting ka time update kar diya, ab four baje hai.") == ""


def test_live_config_lock_top_and_end_and_transcript_hint(env):
    from app import voice, voicelang
    st = voicelang.LangState("mr-IN")
    cfg = voice.live_config("Puck", "mr-IN", "ctx", None, langst=st)
    text = cfg.system_instruction.parts[0].text
    assert text.startswith("LANGUAGE LOCK\nRESPOND IN MARATHI. YOU MUST RESPOND UNMISTAKABLY IN MARATHI.")
    assert text.rstrip().endswith("garmi.)")   # v0.201 the delivery reminder rides last
    assert "Only a note that says 'Language note' can change it." in text   # the end lock is still in
    assert "उद्याची मीटिंग" in text                  # examples in her language
    assert "follow them" not in text
    assert cfg.input_audio_transcription.language_codes == ["mr-IN", "en-IN"]
    # the persona reads key values back and asks again instead of guessing
    assert "EXCEPT the facts you are about to act on" in text and "chat mein likh dijiye" in text and "Never guess" in text


def test_refused_language_hint_drops_only_that_field(env, monkeypatch):
    from app import voice
    err = RuntimeError('Invalid JSON payload received. Unknown name "languageCodes" at '
                       "'setup.input_audio_transcription': Cannot find field.")
    assert voice.unsupported_field(err) == "language_codes"
    monkeypatch.setattr(voice, "UNSUPPORTED", {"language_codes"})
    cfg = voice.live_config("Puck", "hi-IN", "ctx", None)
    assert cfg.input_audio_transcription is not None and cfg.input_audio_transcription.language_codes is None


def test_language_learned_for_the_next_call(env):
    from app import voicelang as v
    s = v.LangState("hi-IN")
    for t in ["मला उद्या सकाळी आठ वाजता आठवण करून दे", "आज संध्याकाळी काय काम आहे ते सांगा",
              "ती फाइल कुठे आहे मला पाठवा", "बरं ठीक आहे मग उद्या बघू आपण"]:
        s.hear(t)
    assert s.base == "mr-IN"
    v.remember("default", s)
    assert v.start_state("default", "hi-IN").base == "mr-IN"
    short = v.LangState("hi-IN")
    short.hear("Hello")
    v.remember("t2", short)                          # too few turns: nothing learned
    assert v.learned("t2") is None


def test_call_sends_a_quiet_language_note_and_keeps_unclear_out_of_memory(env, monkeypatch):
    """A Hindi call: the model answers in English -> one quiet 'Language note'; a Georgian transcript is unclear."""
    # these notes travel as client_content (older Live models); Gemini 3.x queueing: tests/test_v150_voice_heal.py
    monkeypatch.setenv("VOICE_QUIET_NOTES", "client_content")
    from app.config import get_settings as _gs
    _gs.cache_clear()
    from app import main, voice
    _gemini_env(monkeypatch)
    turns = [[
        types.LiveServerMessage(setup_complete=types.LiveServerSetupComplete()),
        _msg(input_transcription=types.Transcription(text="Kal ki meeting chaar baje kar do")),
        _msg(output_transcription=types.Transcription(text="Sure, I have moved the meeting to four o'clock for you.")),
        _msg(turn_complete=True),
        _msg(input_transcription=types.Transcription(text="ჩემი სახელი არის")),
        _msg(output_transcription=types.Transcription(text="Sorry, ek baar phir boliye?")),
        _msg(turn_complete=True),
    ]]
    fake = FakeSession(turns)
    configs = []
    _connector(monkeypatch, fake, configs=configs)
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations").json()["id"]
        with c.websocket_connect(f"/api/voice/ws?conv={conv}&lang=hi-IN") as ws:
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            read_events(ws, lambda e: e["type"] == "turn_done", limit=80)
            ws.send_text(json.dumps({"type": "end"}))
        stats = c.get("/api/voice/stats").json()
    notes = [p.text for t in fake.client_content for p in (t.parts or [])] + list(fake.texts)
    assert any("Language note" in n and "UNMISTAKABLY IN HINDI" in n for n in notes)
    assert configs[0].input_audio_transcription.language_codes == ["hi-IN", "en-IN"]
    call = voice.STATS[-1]
    assert call["lang_drifts"] >= 1 and call["lang_unclear"] == 1 and call["asked_again"] >= 1
    assert stats["lang_drifts_per_100"] is not None and stats["unclear_transcripts"] >= 1


def test_chat_prompt_keeps_language_and_asks_instead_of_guessing():
    from app.agent.prompts import system_prompt
    p = system_prompt(True, "", "default")
    assert "Keep that language for the whole conversation" in p and "ask ONE short question" in p
