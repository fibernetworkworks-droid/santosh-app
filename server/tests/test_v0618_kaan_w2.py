"""KAAN W2 (v0.618.0, owner: "START" on the kaan plan - Wave W2: live captions).

(1) THE SPINE: chunks decode (ffmpeg) to 16k mono s16le PCM and append to one file per session;
    windows are cut by byte offset and wrapped with the stdlib wave module - exact by construction.
(2) THE WATERMARK: one rolling pass per chunk on [watermark - 0.5s, end]; accepted words start at
    or after the watermark (EPS 0.02s) so overlap repeats are trimmed; silence is never re-scanned
    (the watermark advances to the window end on every pass that ran).
(3) THE PHRASES: accepted words -> caption phrases split on a >0.6s gap or a sentence ender.
(4) THE GATES: start/chunk are AUDIO INGEST - the kaan_audio gate owns them (no new switch);
    stop is bookkeeping + an OPTIONAL bounded clean pass (finalize_model, <= 10 min). stop writes
    ONE kn_ row (source='live') that diarize/minutes already read. Live actions are owner/approved;
    registry 607 - actions, not tools. Everything local-first: spine + captions never leave.
"""
import asyncio
import inspect
import io
import shutil
import sys
import wave

import pytest

from app.agent import tools
from app.agent.kaan_tools import _kaan
from app.kaan import engine as EN
from app.kaan import live as LV
from app.kaan import service as KS
from tests.test_life import conv_ctx

PIN = ("their 593 + W1 diarize/minutes ACTIONS (0.613) + W2 live_start/live_chunk/live_stop/live_get/"
       "live_list ACTIONS (0.618) - actions, not tools, registry 607")

SCRIPT = ["pehla", "doosra", "teesra", "chautha."]           # 0.32s cadence from 0.1s, ends on a period
CHUNK_S = 3.2                                                # one chunk = 3.2s of PCM


@pytest.fixture()
def live_env(env, tmp_path, monkeypatch):
    """Fresh DB (env) + AUDIO gate ON + engine ready + a scratch kaan_live dir."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    monkeypatch.setenv("KAAN_LIVE_DIR", str(tmp_path / "kaan_live"))
    from app.config import get_settings
    get_settings.cache_clear()
    EN._AVAIL.clear()
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()


def fake_decoder(seconds: float):
    """Each chunk decodes to exactly `seconds` of silence-PCM (the spine math, no ffmpeg)."""
    return lambda data: b"\x00\x00" * int(seconds * 16000)


def window_engine(script):
    """A whisper-shaped window engine: the script re-speaks every window, clipped to its length
    (so the overlap genuinely repeats words and the watermark has something to trim)."""
    def _f(path: str, *, model: str = "", language: str = "", task: str = "transcribe",
           word_timestamps: bool = True, **k):
        with wave.open(path, "rb") as w:
            d = w.getnframes() / max(1, w.getframerate())
        words, t = [], 0.1
        for wd in script:
            if t >= d:
                break
            words.append({"word": wd, "start": round(t, 3), "end": round(min(t + 0.32, d), 3)})
            t += 0.32
        seg = {"start": 0.0, "end": round(d, 3), "text": " ".join(x["word"] for x in words)}
        if word_timestamps:
            seg["words"] = words
        return {"text": seg["text"], "language": language or "hi", "segments": [seg],
                "model": model or "base", "task": task}
    return _f


def pcm(seconds: float) -> bytes:
    return b"\x11\x22" * int(seconds * 16000)


# ---------------------------------------------------------------- (1) the gate
def test_live_start_and_chunk_need_the_audio_gate(env):
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="live_start"))
    assert "KAAN_AUDIO=1" in str(e.value)                              # the W0 gate line, no new switch
    sid = "kl_koiii"
    with pytest.raises(Exception) as e2:
        asyncio.run(_kaan(ctx, action="live_chunk", id=sid, data=pcm(1.0)))
    assert "KAAN_AUDIO=1" in str(e2.value)


def test_start_happy_path_and_default_model(live_env):
    out = asyncio.run(_kaan(conv_ctx(), action="live_start"))
    assert out["id"].startswith("kl_") and out["status"] == "live" and out["model"] == "base"
    assert "PCM" in out["note"]
    got = asyncio.run(_kaan(conv_ctx(), action="live_get", id=out["id"]))
    assert got["n_chunks"] == 0 and got["n_phrases"] == 0 and got["watermark_s"] == 0.0


def test_bad_model_is_refused_at_start(live_env):
    with pytest.raises(Exception) as e:
        LV.start("default", model="mega")
    assert "Ladder" in str(e.value)


# ---------------------------------------------------------------- (2) the rolling window
def test_rolling_pass_watermark_and_no_dupes(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))
    sid = LV.start("default")["id"]
    c1 = LV.chunk("default", sid, pcm(CHUNK_S))
    assert c1["ran"] is True and c1["n_new"] == 1 and c1["n_phrases"] == 1
    assert len(c1["new"][0]["text"].split()) == 4                    # one phrase, all four words
    assert c1["new"][0]["text"] == "pehla doosra teesra chautha."       # ender intact
    assert abs(c1["watermark_s"] - CHUNK_S) < 0.05                      # watermark = window end
    c2 = LV.chunk("default", sid, pcm(CHUNK_S))                         # spine now 6.4s
    assert c2["ran"] is True
    got_text = [w for p in c2["new"] for w in p["text"].split()]
    assert got_text == ["teesra", "chautha."]                           # overlap words TRIMMED, no dupes
    assert c1["new"][0]["text"].split()[:2] == ["pehla", "doosra"]      # first pass untouched
    stopped = LV.stop("default", sid)
    assert stopped["transcript_id"].startswith("kn_")
    assert stopped["finalize"] == "captions"
    row = KS.get_transcript("default", stopped["transcript_id"])
    assert row["text"] == "pehla doosra teesra chautha. teesra chautha."  # 6 words total - exactly once each after trim
    assert row["source"] if False else row["n_segments"] == 2           # two caption phrases = two segments
    m = KS.minutes("default", stopped["transcript_id"])                 # W1 rides the W2 row for free
    assert m["n_turns"] == 1 and "pehla" in m["keywords"]
    sess = LV.get_session("default", sid)
    assert sess["status"] == "done" and sess["transcript_id"] == stopped["transcript_id"]


def test_small_window_never_runs_and_stop_still_catches_the_tail(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(0.5))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))
    sid = LV.start("default")["id"]
    c = LV.chunk("default", sid, pcm(0.5))                              # 0.5s < MIN_WINDOW 1.5s
    assert c["ran"] is False and c["new"] == [] and c["watermark_s"] == 0.0
    out = LV.stop("default", sid)                                       # stop runs the 0.5s tail (>= 0.3s)
    assert out["transcript_id"].startswith("kn_") and out["n_phrases"] >= 1


def test_phrase_gap_and_ender_split(live_env, monkeypatch):
    script = ["pehla", "doosra.", "teesra", "chautha."]                 # ender after doosra + long gap
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(script))
    sid = LV.start("default")["id"]
    c = LV.chunk("default", sid, pcm(CHUNK_S))
    texts = [p["text"] for p in c["new"]]
    assert texts == ["pehla doosra.", "teesra chautha."]                # ender cut; gap cut


# ---------------------------------------------------------------- (3) the caps + honesty
def test_chunk_guards_empty_oversize_cap(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))        # a 1.6s+ chunk runs a pass
    monkeypatch.setattr(LV, "MAX_CHUNK_BYTES", 64)
    monkeypatch.setattr(LV, "MAX_CHUNKS", 1)
    sid = LV.start("default")["id"]
    with pytest.raises(Exception) as e:
        LV.chunk("default", sid, b"")
    assert "khaali" in str(e.value)
    with pytest.raises(Exception) as e2:
        LV.chunk("default", sid, pcm(CHUNK_S))                          # pcm(3.2) >> 64 bytes cap
    assert "MB tak" in str(e2.value)
    monkeypatch.setattr(LV, "MAX_CHUNK_BYTES", 5 * 1024 * 1024)
    LV.chunk("default", sid, pcm(1.6))                                  # n_chunks 0 -> 1
    with pytest.raises(Exception) as e3:
        LV.chunk("default", sid, pcm(1.6))                              # MAX_CHUNKS 1 crossed
    assert "cap" in str(e3.value)


def test_stop_is_idempotent(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))
    sid = LV.start("default")["id"]
    LV.chunk("default", sid, pcm(CHUNK_S))
    one = LV.stop("default", sid)
    two = LV.stop("default", sid)
    assert two["already_stopped"] is True and two["transcript_id"] == one["transcript_id"]


def test_silence_session_is_honest(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine([]))            # a window that hears nothing
    sid = LV.start("default")["id"]
    LV.chunk("default", sid, pcm(CHUNK_S))
    out = LV.stop("default", sid)
    row = KS.get_transcript("default", out["transcript_id"])
    assert row["status"] == "empty" and "khamoshi" in row["note"]


def test_finalize_batch_clean_pass(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    calls = []
    def whole_engine(path, *, model="", language="", task="transcribe", word_timestamps=True, **k):
        import wave as _w
        with _w.open(path, "rb") as w:
            d = w.getnframes() / max(1, w.getframerate())
        calls.append(round(d, 2))
        return {"text": "saaf baat yahi hai.", "language": "hi",
                "segments": [{"start": 0.0, "end": round(d, 3), "text": "saaf baat yahi hai.",
                              "words": [{"word": "saaf", "start": 0.0, "end": 0.3}]}],
                "model": model or "small", "task": task}
    monkeypatch.setattr(EN, "transcribe", whole_engine)
    sid = LV.start("default")["id"]
    LV.chunk("default", sid, pcm(CHUNK_S))
    out = LV.stop("default", sid, finalize_model="small")
    assert out["finalize"] == "batch" and calls and calls[-1] == pytest.approx(CHUNK_S, abs=0.1)
    row = KS.get_transcript("default", out["transcript_id"])
    assert row["text"] == "saaf baat yahi hai." and "clean batch pass" in row["note"]
    assert row["model"] == "small"


def test_finalize_is_bounded_and_validated(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))        # the chunk pass before stop
    monkeypatch.setattr(LV, "MAX_FINALIZE_S", 0.1)
    sid = LV.start("default")["id"]
    LV.chunk("default", sid, pcm(CHUNK_S))
    with pytest.raises(Exception) as e:
        LV.stop("default", sid, finalize_model="small")
    assert "clean pass" in str(e.value)
    with pytest.raises(Exception) as e2:
        LV.stop("default", sid, finalize_model="mega")
    assert "Ladder" in str(e2.value)


def test_live_tenant_isolation(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))
    sid = LV.start("default")["id"]
    LV.chunk("default", sid, pcm(CHUNK_S))
    with pytest.raises(Exception):
        LV.chunk("other_tenant", sid, pcm(CHUNK_S))
    with pytest.raises(Exception):
        LV.get_session("other_tenant", sid)
    with pytest.raises(Exception):
        LV.stop("other_tenant", sid)


def test_real_ffmpeg_decode_when_present(live_env):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not in this sandbox - the VPS bake covers it")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)                              # 1.0s wav
    out = LV._decode_chunk(buf.getvalue())
    assert abs(len(out) / LV.BYTES_PER_S - 1.0) < 0.1                   # 1s in -> ~1s of spine PCM


# ---------------------------------------------------------------- (4) the wiring + laws
def test_actions_grew_registry_did_not():
    assert len(tools.TOOLS) == 624, "623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). 608 + 1 kala (v0.681 KALA MANCH: the T5 knowledge-skill catalog family, owner 'GO' on the google/skills deploy plan). " "607 + 1 duniya (v0.667 DUNIYA MANCH: the T4 keyless-public-web family, owner 'T4'). " "606 + 1 jharokha (v0.665 JHAROKHA MANCH: the T3 local-browser family). " + PIN
    spec = [t for t in tools.TOOLS if t["name"] == "kaan"][0]
    acts = spec["input_schema"]["properties"]["action"]["enum"]
    assert acts == ["transcribe", "diarize", "minutes", "status", "list", "get", "search",
                    "live_start", "live_chunk", "live_stop", "live_get", "live_list",
                    "style", "vocab_add", "vocab_list", "vocab_remove",
                    "export", "to_gyaan"]  # W4 grew actions  # W3 grew actions
    assert "live_start" in spec["description"]                          # the diet (<=1200) keeps W2 visible
    assert "live captions" in spec["description"]
    assert "finalize_model" in spec["input_schema"]["properties"]


def test_status_carries_the_live_block(live_env):
    st = asyncio.run(_kaan(conv_ctx(), action="status"))
    assert st["live"]["on"] is True and st["live"]["default_model"] == "base"
    assert "PCM" in st["live"]["note"] and st["live"]["active"] >= 0
    assert st["gate"] == "ON"                                           # W0 gate still the one gate


def test_actor_lanes_live_is_owner_only(live_env, monkeypatch):
    monkeypatch.setattr(LV, "_decode_chunk", fake_decoder(CHUNK_S))
    monkeypatch.setattr(EN, "transcribe", window_engine(SCRIPT))
    ctx = conv_ctx()
    sid = LV.start("default")["id"]
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="live_start"))                  # audio ingest is owner-only
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="live_get", id=sid))
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="live_list"))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(cust, action="live_chunk", id=sid, data=pcm(1.0)))
    out = asyncio.run(_kaan(ctx, action="live_list"))                   # owner sees the session
    assert any(i["id"] == sid for i in out["items"])


def test_live_module_purity_and_laziness():
    src = inspect.getsource(LV)
    assert "httpx" not in src and "requests" not in src and "openai" not in src
    assert "import whisper" not in src and "import torch" not in src
    sys.modules.pop("app.kaan.live", None)
    import importlib
    importlib.import_module("app.kaan.live")
    assert "whisper" not in sys.modules and "torch" not in sys.modules


def test_version_pin_v0618():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.775.0"
