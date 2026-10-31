"""v0.251.0 SIRF LINE - the owner heard English mid-call ("say it quietly and simply"): the TTS model sometimes spoke
the clip's delivery ask ("Say this quietly, half to yourself...") instead of only the line, and _trim + the file cache
replayed that English instruction in every call. A clip is now accepted only when its speech fits the line."""
from array import array
from pathlib import Path

from app import voice

ROOT = Path(__file__).resolve().parents[2]


def _speech(seconds: float, rate: int = 24000) -> bytes:
    n = int(seconds * rate)
    return b"\x00\x00" * 480 + array("h", [7000, -7000] * (n // 2)).tobytes() + b"\x00\x00" * 480


def test_speech_length_and_limit():
    assert abs(voice._speech_s(_speech(2.0)) - 2.0) < 0.05
    assert voice._speech_s(b"\x00\x00" * 24000) == 0.0
    line = "Haan, ek second."
    assert 2 < voice._max_speech_s(line) < 3.5
    ask = voice._ack_ask(line, "m")
    assert voice._max_speech_s(line) < len(ask) * 0.06      # a read-out ask (~14 chars/s) never fits the line's limit


def test_read_aloud_ask_is_rejected_and_the_bare_line_used(monkeypatch):
    asked = []

    def tts(prompt, v, client=None):
        asked.append(prompt)
        return _speech(12.0)                                 # the whole English ask spoken

    before = voice.CLIP_REJECTED["count"]
    monkeypatch.setattr(voice, "_tts_clip", lambda p, v, client=None: (asked.append(p), _speech(1.0))[1])
    clip = voice._safe_clip("Haan, ek second.", lambda: tts("Say this quickly...: Haan, ek second.", "Puck"), "Puck")
    assert clip and voice._speech_s(clip) < 1.7
    assert asked[-1] == "Haan, ek second."                   # second try = the bare line, nothing else to read
    assert voice.CLIP_REJECTED["count"] == before + 1


def test_both_tries_too_long_means_no_clip(monkeypatch):
    monkeypatch.setattr(voice, "_tts_clip", lambda p, v, client=None: _speech(10.0))
    assert voice._safe_clip("Haan...", lambda: _speech(10.0), "Puck") == b""


def test_a_good_render_is_kept_on_the_first_try(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no second render for a clip that fits")
    monkeypatch.setattr(voice, "_tts_clip", boom)
    assert voice._safe_clip("Achha, dekhta hoon.", lambda: _speech(1.1), "Puck")


def test_builders_go_through_the_check_and_clips_regenerate(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "ACK_DIR", tmp_path)
    monkeypatch.setattr(voice, "_ack_file", lambda v, g, i: tmp_path / f"{v}_{g}_{i}_{voice._ACK_GEN}.pcm")
    monkeypatch.setattr(voice, "_ack_tts", lambda text, v, g, client=None: _speech(15.0))     # always reads the ask
    monkeypatch.setattr(voice, "_tts_clip", lambda p, v, client=None: _speech(0.9))           # the bare line is fine
    voice._build_acks("t250:Puck:m", "Puck", "m")
    try:
        clips = voice._ACKS["t250:Puck:m"]
        assert len(clips) == len(voice.ACK_LINES) and all(voice._speech_s(c) < 1.7 for c in clips)
    finally:
        voice._ACKS.pop("t250:Puck:m", None)
        voice._ACK_IX.pop("t250:Puck:m", None)
    assert voice._ACK_GEN == "a3" and (voice._BC_GEN, voice._PROG_GEN) == ("b2", "p2")
    src = (ROOT / "server/app/voice.py").read_text()
    assert src.count("_safe_clip(gendered(line, gender)") == 2


def test_mid_call_notes_in_hinglish():
    src = (ROOT / "server/app/voice.py").read_text()
    assert "Ask her once more to say them slowly" not in src and "She called you by name" not in src
    assert "ek-ek karke bolne" in src and "usi ki bhasha mein" in src


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.319.0"
    assert "0.319.0+359" in (ROOT / "pubspec.yaml").read_text()
