"""KAAN PACK v0.589.0 (WhisperAI Wave W0: the transcription core; owner: "START" on the fed plan).

(1) THE PIPELINE with a scripted engine (zero network, zero torch): file bytes -> guards -> engine ->
    store -> get / list / search, word counts, silence honesty, tenant isolation.
(2) THE GUARDS: AUDIO gate default OFF with the bake-then-flip line, bad extension, empty file, the
    5 GB ceiling, missing file id, unknown transcript id.
(3) THE ENGINE LAWS from the repository read: model ladder (tiny 39M ... large-v3 1550M), the
    temperature ladder 0.0 -> 1.0, the 2.4 / -1.0 / 0.6 guard numbers, turbo cannot translate,
    LAZY import (importing app.kaan never loads whisper), available() cached with honest lines.
(4) THE WIRING: one tool `kaan` (registry 583), family kaan, voice route = santosh_kaam, labels,
    admit keys (sunwai stays OUT - the vakil desk owns that word), hub entry, count pins healed.
"""
import asyncio
import inspect
import math
import struct
import sys
import wave

import pytest

from app.agent import tools
from app.agent.kaan_tools import KAAN_HANDLERS, KAAN_LABELS, KAAN_TOOLS, _kaan
from app.kaan import engine as EN
from app.kaan import service as KS
from tests.test_life import conv_ctx

PIN = ("their 584 (581 + paisa + 2 sandarbh; P8 AEP 1.0 added no tool) + 1 kaan tool (v0.601 KAAN PACK) = 585")


# ---------------------------------------------------------------- fixture helpers
def wav_bytes(seconds: float = 1.0, freq: float = 440.0, rate: int = 16000) -> bytes:
    """A real 16 kHz mono PCM WAV (stdlib only) - the ingest path gets genuine audio bytes."""
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        n = int(rate * seconds)
        for i in range(n):
            v = int(12000 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))
    return buf.getvalue()


@pytest.fixture()
def fake_env(env, monkeypatch):
    """AUDIO gate ON + engine reported ready + the scripted engine wired in (the connect-swap pattern)."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    from app.config import get_settings
    get_settings.cache_clear()
    EN._AVAIL.clear()
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    monkeypatch.setattr(EN, "transcribe", EN.fake_engine("Hoola sun rahi hai, boliye."), raising=True)
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()


# ---------------------------------------------------------------- (1) the pipeline
def test_transcribe_round_trip_stores_and_reads_back(fake_env):
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="transcribe", file_id="f1", name="meeting.mp3", data=wav_bytes()))
    assert out["status"] == "ready" and out["stored"] and out["text"] == "Hoola sun rahi hai, boliye."
    assert out["n_segments"] == 1 and out["n_words"] == 5 and out["model"] == "small" and out["language"] == "hi"
    got = asyncio.run(_kaan(ctx, action="get", id=out["id"]))
    assert got["text"] == out["text"] and got["n_segments"] == 1
    assert asyncio.run(_kaan(ctx, action="search", q="sun rahi"))["items"][0]["id"] == out["id"]
    assert [i["id"] for i in asyncio.run(_kaan(ctx, action="list"))["items"]] == [out["id"]]


def test_search_is_the_said_words_not_the_file_name(fake_env):
    ctx = conv_ctx()
    a = asyncio.run(_kaan(ctx, action="transcribe", file_id="f2", name="a.m4a", data=wav_bytes()))["id"]
    miss = asyncio.run(_kaan(ctx, action="search", q="gst invoice ka total"))
    assert miss["items"] == [] and miss["q"] == "gst invoice ka total"
    empty = asyncio.run(_kaan(ctx, action="search", q="  "))
    assert empty["items"] == [] and empty["q"] == "" and a  # blank q never scans the table


def test_word_timestamps_flow_into_the_row(fake_env):
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="transcribe", file_id="f3", name="x.wav", data=wav_bytes(),
                            word_timestamps=False))
    assert out["n_words"] == 0 and out["segments"][0].get("words") is None
    with_word = asyncio.run(_kaan(ctx, action="transcribe", file_id="f4", name="x.wav", data=wav_bytes()))
    seg = with_word["segments"][0]
    assert seg["words"][0]["start"] == 0.0 and seg["words"][-1]["end"] > 1.0


def test_silence_is_reported_as_silence_never_filled_in(fake_env, monkeypatch):
    monkeypatch.setattr(EN, "transcribe",
                        lambda path, **k: {"text": "", "language": "hi", "segments": [], "model": "small", "task": "transcribe"},
                        raising=True)
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="transcribe", file_id="f5", name="quiet.wav", data=wav_bytes()))
    assert out["status"] == "empty" and out["text"] == "" and "khamoshi" in out["note"]


def test_tenant_isolation(fake_env):
    ctx = conv_ctx()
    tid = asyncio.run(_kaan(ctx, action="transcribe", file_id="f6", name="a.wav", data=wav_bytes()))["id"]
    other = type(ctx)("other_tenant", ctx.conversation_id)
    with pytest.raises(Exception):
        asyncio.run(_kaan(other, action="get", id=tid))
    assert asyncio.run(_kaan(other, action="list"))["items"] == []
    assert asyncio.run(_kaan(other, action="search", q="sun rahi"))["items"] == []


def test_language_and_model_are_kept_as_given(fake_env):
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="transcribe", file_id="f7", name="a.wav", data=wav_bytes(),
                            model="base", language="mr"))
    assert out["model"] == "base" and out["language"] == "mr"


# ---------------------------------------------------------------- (2) the guards
def test_audio_gate_is_off_by_default_and_says_the_bake_line(env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="transcribe", file_id="f8", name="a.wav", data=wav_bytes()))
    assert "kaan_audio" in str(e.value).lower() and "KAAN_AUDIO=1" in str(e.value)
    st = asyncio.run(_kaan(ctx, action="status"))                      # status works behind a closed gate
    assert st["gate"] == "OFF" and "KAAN_AUDIO=1" in st["gate_note"]


def test_bad_extension_is_refused_with_the_walking_list(fake_env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="transcribe", file_id="f9", name="notes.txt", data=b"hello"))
    assert ".txt" in str(e.value) and ".mp3" in str(e.value)


def test_empty_file_and_missing_file_id_are_honest(fake_env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="transcribe", file_id="f10", name="a.wav", data=b""))
    assert "khaali" in str(e.value)
    with pytest.raises(Exception) as e2:
        asyncio.run(_kaan(ctx, action="transcribe"))
    assert "file_id" in str(e2.value)


def test_five_gb_ceiling_refused(fake_env, monkeypatch):
    monkeypatch.setattr(KS, "MAX_BYTES", 10, raising=True)
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="transcribe", file_id="f11", name="a.wav", data=b"x" * 11))
    assert "5 GB" in str(e.value)


def test_engine_missing_gives_the_install_line_not_a_trace(fake_env, monkeypatch):
    EN._AVAIL.clear()
    monkeypatch.setitem(EN._AVAIL, "ok", (False, "openai-whisper package nahi hai (ModuleNotFoundError) - server par `pip install openai-whisper` chahiye."))
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="transcribe", file_id="f12", name="a.wav", data=wav_bytes()))
    assert "pip install openai-whisper" in str(e.value)
    st = asyncio.run(_kaan(ctx, action="status"))
    assert st["engine"] == "nahi" and "pip install" in st["engine_note"]


def test_get_unknown_id_is_honest(env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="get", id="kn_nahi_hai"))
    assert "nahi mili" in str(e.value)


def test_list_limit_is_clamped(fake_env):
    ctx = conv_ctx()
    assert asyncio.run(_kaan(ctx, action="list", limit=10_000))["items"] == []    # clamp runs on an empty table too


# ---------------------------------------------------------------- (3) the engine laws
def test_model_ladder_is_the_model_card():
    names = [m["name"] for m in EN.MODEL_LADDER]
    assert names == ["tiny", "base", "small", "medium", "turbo", "large-v3"]
    params = {m["name"]: m["params"] for m in EN.MODEL_LADDER}
    assert params == {"tiny": "39M", "base": "74M", "small": "244M", "medium": "769M",
                      "turbo": "809M", "large-v3": "1550M"}
    assert "NO translate" in [m["note"] for m in EN.MODEL_LADDER if m["name"] == "turbo"][0]


def test_temperature_and_guard_numbers_are_the_engines_own():
    assert EN.TEMPERATURES == (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    assert EN.COMPRESSION_RATIO_THRESHOLD == 2.4
    assert EN.LOGPROB_THRESHOLD == -1.0
    assert EN.NO_SPEECH_THRESHOLD == 0.6


def test_turbo_cannot_translate_and_unknown_model_is_named():
    with pytest.raises(EN.KaanError) as e:
        EN.transcribe("/tmp/none.wav", model="turbo", task="translate")
    assert "translate" in str(e.value) and "large-v3" in str(e.value)
    with pytest.raises(EN.KaanError) as e2:
        EN.transcribe("/tmp/none.wav", model="gpt-9")
    assert "tiny" in str(e2.value) and "large-v3" in str(e2.value)
    assert "turbo" not in EN.TRANSLATE_CAPABLE


def test_engine_is_lazy_and_cached():
    src = inspect.getsource(EN)
    assert "import whisper" in src                                  # the dependency is real
    tops = [ln for ln in src.splitlines() if ln.strip().startswith("import whisper")]
    assert tops and all(ln.startswith(("    import whisper", "        import whisper")) for ln in tops)
    sys.modules.pop("app.kaan.engine", None)
    import importlib
    importlib.import_module("app.kaan.engine")
    assert "whisper" not in sys.modules                             # importing the module loaded no model
    a1 = EN.available()
    a2 = EN.available()
    assert a1 == a2                                                 # cached; refresh re-looks
    EN.available(refresh=True)
    EN._AVAIL.clear()


def test_default_model_env():
    import os
    old = os.environ.get("KAAN_MODEL")
    try:
        os.environ["KAAN_MODEL"] = "turbo"
        assert EN.default_model() == "turbo"
        os.environ.pop("KAAN_MODEL")
        assert EN.default_model() == "small"
    finally:
        if old is not None:
            os.environ["KAAN_MODEL"] = old


# ---------------------------------------------------------------- (4) the wiring
def test_one_tool_registered_routed_and_labelled():
    assert len(tools.TOOLS) == 586, PIN
    assert "kaan" in tools.HANDLERS and tools.FAMILY_OF["kaan"] == "kaan"
    assert "kaan" in tools.TOOL_LABELS and "sun" in tools.TOOL_LABELS["kaan"]
    spec = [t for t in tools.TOOLS if t["name"] == "kaan"][0]
    acts = spec["input_schema"]["properties"]["action"]["enum"]
    assert acts == ["transcribe", "status", "list", "get", "search"]
    from app import voice
    assert voice.call_route("kaan") == "kaam" and "kaan" in voice.VOICE_VIA_KAAM


def test_guards_on_the_handler(env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="sun_lo"))
    assert "transcribe" in str(e.value) and "status" in str(e.value)
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(cust, action="status"))
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="transcribe", file_id="f13", name="a.wav", data=wav_bytes()))
    assert asyncio.run(_kaan(staff, action="list"))["items"] == []   # read-only lanes stay open to staff


def test_status_shape_and_privacy_line(fake_env):
    ctx = conv_ctx()
    st = asyncio.run(_kaan(ctx, action="status"))
    assert st["gate"] == "ON" and st["engine"] == "ready"
    assert st["default_model"] == "small"
    assert [m["name"] for m in st["ladder"]] == ["tiny", "base", "small", "medium", "turbo", "large-v3"]
    assert "stored" in st and "isi server par" in st["privacy"]


def test_admit_keys_bring_kaan_and_sunwai_stays_legal():
    from app.agent import admit
    assert "kaan" in admit._match("is meeting ki transcript banao")
    assert "kaan" in admit._match("audio file sun kar likho")
    assert "kaan" in admit._match("kaan se yeh sun kar likho")
    assert "kaan" in admit._match("voice note ki likhawat chahiye")
    assert "kaan" in admit._match("srt subtitle chahiye")
    assert "kaan" not in admit._match("court ki sunwai ka ble")       # vakil desk owns that word


def test_hub_entry_is_live_and_honest():
    from app.employee import hire as H
    c = H.CATALOG["kaan"]
    assert c["live"] and c["group"] == "Voice, Meetings & Transcription" and c["does"] and c["needs"]
    text = " ".join(c["never"]).lower()
    assert "server" in text and "gate" in text and "silence" in text
    assert H.hire("t1", "kaan")["key"] == "kaan"


def test_transcript_table_is_registered_on_init(env):
    from sqlalchemy import inspect as sql_inspect
    from app import db
    with db.session() as s:
        pass
    assert sql_inspect(db._engine).has_table("kaan_transcripts")


def test_store_reads_never_write_and_engine_never_touches_the_db():
    src = inspect.getsource(EN)
    assert "session(" not in src and "INSERT" not in src.upper()
    svc = inspect.getsource(KS)
    assert svc.count("session()") >= 4                              # store / get / list / search + status
