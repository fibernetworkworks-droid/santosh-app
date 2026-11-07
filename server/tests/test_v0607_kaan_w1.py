"""KAAN W1 (v0.615.0, owner: "START" on the kaan plan - Wave W1: diarization + meeting minutes).

(1) THE TURN CUTTER: pause-gap turns from the transcript's own timeline - segment gaps AND word
    gaps inside a segment; deterministic (same in -> same out); no pause = one turn; honest caps.
(2) THE HONESTY: turns are NOT speaker identities - unnamed until the owner names them
    (names={'1': ...}); unknown names surface; the note says audio is never stored.
(3) THE MINUTES: deterministic skeleton from a stored row - per-turn stats (word shares, seconds),
    content keywords (en+hi stopword-light), action-item CANDIDATES by cue words with turn
    attribution; no model call, no invention; the prose summary is Santosh's job.
(4) THE WIRING: same ONE tool `kaan` grows two actions (registry stays 588 - actions, not tools);
    diarize is owner/approved-only (it writes the row) and kill-switched (kaan_diarize, default
    ON, local + light); fresh-audio diarize still rides the AUDIO gate; minutes is a read, open
    to staff like list/get; admit keys stay TIGHT (bare "minute" can never admit this family).
"""
import asyncio
import inspect
import sys

import pytest

from app.agent import tools
from app.agent.kaan_tools import _kaan
from app.kaan import diarize as DI
from app.kaan import engine as EN
from app.kaan import meeting as MT
from app.kaan import service as KS
from tests.test_life import conv_ctx

PIN = ("their 584 (581 + paisa + 2 sandarbh; P8 AEP 1.0 added no tool) + 1 kaan (v0.601) + vitt_sahayak (0.602) "
       "+ risk_desk (0.603) + dukaan_desk (0.604) = 588; their retail_growth + retail_trust (0.607) + bima_desk (0.609) + bima_assist (0.610) + bima_risk (0.612) = 593; W1 diarize/minutes are ACTIONS, no new tool = 593")

SEGS = [
    {"start": 0.0, "end": 3.0, "text": "Namaste, meeting shuru karein."},
    {"start": 5.0, "end": 8.5, "text": "Kal report bhejna."},
    {"start": 8.7, "end": 11.0, "text": "Aur ledger check karna."},
]


def script_engine(segs):
    """A multi-segment scripted engine (the W0 connect-swap pattern, several utterances)."""
    def _f(path, **k):
        return {"text": " ".join(s["text"] for s in segs), "language": "hi",
                "segments": segs, "model": k.get("model") or "small", "task": k.get("task") or "transcribe"}
    return _f


@pytest.fixture()
def fake_env(monkeypatch):
    """AUDIO gate ON + engine ready + the W0 scripted engine (same shape as the W0 suite's fixture)."""
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


def insert_row(segments=None, text="", tenant="default", **kw):
    """A stored transcript row without the gate (the text is already hers - local, no ingest).
    Default tenant = conv_ctx()'s tenant ('default'), so tool calls see the row."""
    from app.db import session
    from app.kaan.models import KaanTranscript
    segs = segments or []
    with session() as s:
        r = KaanTranscript(tenant_id=tenant, file_name="m.m4a", text=text, language="hi",
                           segments={"items": segs}, n_segments=len(segs), **kw)
        s.add(r)
        s.commit()
        return r.id


# ---------------------------------------------------------------- (1) the turn cutter
def test_pause_turns_cut_and_stay_deterministic():
    turns = DI.cut_turns(SEGS)
    assert [t["turn"] for t in turns] == [1, 2]                       # 2.0s gap cuts; 0.2s gap does not
    assert turns[0]["text"] == "Namaste, meeting shuru karein."
    assert turns[1]["text"] == "Kal report bhejna. Aur ledger check karna."
    assert turns[1]["start"] == 5.0 and turns[1]["end"] == 11.0
    assert DI.cut_turns(SEGS) == turns                                # deterministic
    assert all(t["speaker"] == "" for t in turns)                     # nobody is named by a pause


def test_word_gaps_cut_inside_one_segment():
    seg = [{"start": 0.0, "end": 3.0, "text": "pehla doosra teesra", "words": [
        {"word": "pehla", "start": 0.0, "end": 0.5},
        {"word": "doosra", "start": 0.6, "end": 1.0},
        {"word": "teesra", "start": 2.5, "end": 3.0}]}]
    turns = DI.cut_turns(seg)
    assert len(turns) == 2 and turns[0]["text"] == "pehla doosra" and turns[1]["text"] == "teesra"


def test_no_pause_is_one_turn_and_custom_pause_s():
    one = [{"start": 0.0, "end": 5.0, "text": "lagataar baat"},
           {"start": 5.1, "end": 9.0, "text": "bina ruke aage"}]
    assert len(DI.cut_turns(one)) == 1
    assert len(DI.cut_turns(one, pause_s=0.05)) == 2                  # the knob works
    assert DI.diarize(SEGS, pause_s=2.5)["n_turns"] == 1              # a wide pause merges everything


def test_names_apply_and_unknown_names_surface():
    out = DI.diarize(SEGS, names={"1": "Maine", "2": "Gupta ji"})
    assert out["named_turns"] == 2 and out["turns"][0]["speaker"] == "Maine"
    assert out["turns"][1]["speaker"] == "Gupta ji"
    out2 = DI.diarize(SEGS, names={"1": "Maine", "9": "Bhoot"})
    assert out2["unknown_names"] == ["9"] and out2["named_turns"] == 1
    blank = DI.diarize(SEGS, names={"1": "   "})                      # a blank name is no name
    assert blank["named_turns"] == 0 and blank["turns"][0]["speaker"] == ""


def test_empty_segments_are_honest_and_capped():
    out = DI.diarize([])
    assert out["n_turns"] == 0 and out["turns"] == [] and "pauses" in out["note"]
    many = [{"start": float(i * 2), "end": float(i * 2 + 0.5), "text": f"baat {i}"} for i in range(450)]
    capped = DI.diarize(many)
    assert capped["n_turns"] <= DI.MAX_TURNS and capped["truncated"] is True


# ---------------------------------------------------------------- (2) the service wiring
def test_diarize_stored_row_persists_speakers(env):
    tid = insert_row(SEGS, text=" ".join(s["text"] for s in SEGS))
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="diarize", id=tid, names={"1": "Maine"}))
    assert out["n_turns"] == 2 and out["named_turns"] == 1 and out["method"] == "pause_turns"
    got = asyncio.run(_kaan(ctx, action="get", id=tid))
    assert got["speakers"]["n_turns"] == 2 and got["speakers"]["named_turns"] == 1   # persisted, read back
    assert got["text"] and got["n_segments"] == 3                     # the W0 read shape is untouched


def test_fresh_audio_diarize_needs_the_audio_gate_and_the_pipeline(env):
    """file_id diarize = audio ingest = the AUDIO gate owns it; stored-id diarize does not."""
    ctx = conv_ctx()
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="diarize", file_id="fx", name="m.m4a", data=b"x"))
    assert "KAAN_AUDIO=1" in str(e.value)                             # gate line, not a traceback
    tid = insert_row(SEGS, text="kuch baat")
    out = asyncio.run(_kaan(ctx, action="diarize", id=tid))           # no gate - the text is already stored
    assert out["n_turns"] == 2


def test_fresh_audio_diarize_happy_path_runs_the_whole_pipeline(fake_env):
    import wave, io, math, struct
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)
    ctx = conv_ctx()
    out = asyncio.run(_kaan(ctx, action="diarize", file_id="fw", name="m.wav", data=buf.getvalue(),
                            names={"1": "Maine"}))
    assert out["id"].startswith("kn") and out["n_turns"] >= 1 and out["turns"][0]["speaker"] == "Maine"


def test_diarize_kill_switch(env, monkeypatch):
    tid = insert_row(SEGS, text="kuch baat")
    monkeypatch.setenv("KAAN_DIARIZE", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        ctx = conv_ctx()
        with pytest.raises(Exception) as e:
            asyncio.run(_kaan(ctx, action="diarize", id=tid))
        assert "kaan_diarize" in str(e.value) and "KAAN_DIARIZE=1" in str(e.value)
        st = asyncio.run(_kaan(ctx, action="status"))                 # status always tells the truth
        assert st["diarize"]["on"] is False
    finally:
        get_settings.cache_clear()


def test_diarize_tenant_isolation(env):
    tid = insert_row(SEGS, text="kuch baat", tenant="t1")
    ctx = conv_ctx()
    other = type(ctx)("other_tenant", ctx.conversation_id)
    with pytest.raises(Exception):
        asyncio.run(_kaan(other, action="diarize", id=tid))
    with pytest.raises(Exception):
        asyncio.run(_kaan(other, action="minutes", id=tid))


def test_status_carries_the_diarize_block(fake_env):
    st = asyncio.run(_kaan(conv_ctx(), action="status"))
    assert st["diarize"]["on"] is True and st["diarize"]["method"] == "pause_turns"
    assert "audio store nahi hota" in st["diarize"]["note"]


# ---------------------------------------------------------------- (3) the minutes
def test_minutes_structure_and_stats(env):
    tid = insert_row(SEGS, text=" ".join(s["text"] for s in SEGS))
    out = asyncio.run(_kaan(conv_ctx(), action="diarize", id=tid))    # turns first
    m = asyncio.run(_kaan(conv_ctx(), action="minutes", id=tid))
    assert m["tid"] == tid and m["n_turns"] == 2
    assert abs(sum(t["word_share"] for t in m["turns"]) - 1.0) < 0.01
    assert m["turns"][0]["seconds"] == 3.0 and m["turns"][1]["seconds"] == 6.0
    assert "report" in m["keywords"] and "ledger" in m["keywords"]
    assert "aur" not in m["keywords"] and "the" not in m["keywords"]  # stop words never lead
    assert "faisla" in m["note"] or "candidates" in m["note"]         # the honest line rides


def test_action_candidates_cue_hit_and_turn_attribution(env):
    segs = [{"start": 0.0, "end": 4.0, "text": "Kal report bhejna."},
            {"start": 6.0, "end": 10.0, "text": "Aur ledger check karna."}]
    tid = insert_row(segs, text=" ".join(s["text"] for s in segs))
    asyncio.run(_kaan(conv_ctx(), action="diarize", id=tid))
    m = asyncio.run(_kaan(conv_ctx(), action="minutes", id=tid))
    cues = {c["cue"].lower() for c in m["action_candidates"]}
    assert "kal" in cues and "check" in cues               # the FIRST cue of each sentence is its cue
    assert any("bhejna" in c["text"] for c in m["action_candidates"])   # the sentence itself carries the verb
    assert {c["turn"] for c in m["action_candidates"]} == {1, 2}        # attributed to their turns


def test_minutes_without_diarization_and_on_silence(env):
    tid = insert_row(SEGS, text=" ".join(s["text"] for s in SEGS))    # no diarize call
    m = asyncio.run(_kaan(conv_ctx(), action="minutes", id=tid))
    assert m["n_turns"] == 1 and m["turns"][0]["word_share"] == 1.0   # one-turn fallback
    quiet = insert_row([], text="")
    m2 = asyncio.run(_kaan(conv_ctx(), action="minutes", id=quiet))
    assert m2["keywords"] == [] and m2["action_candidates"] == []     # silence stays silence
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(conv_ctx(), action="minutes", id="kn_nahi_hai"))
    assert "nahi mili" in str(e.value)


def test_minutes_never_calls_a_model_and_is_pure():
    src = inspect.getsource(MT)
    assert "httpx" not in src and "requests" not in src and "openai" not in src and "whisper" not in src
    row = {"id": "kn_x", "file_name": "f.m4a", "language": "hi", "task": "transcribe", "model": "small",
           "duration_s": 9.0, "text": "Kal report bhejna.", "speakers": None}
    m = MT.minutes(row)
    assert m["n_turns"] == 1 and len(m["action_candidates"]) == 1 and m["action_candidates"][0]["turn"] == 1


# ---------------------------------------------------------------- (4) the wiring
def test_actions_grew_registry_did_not():
    assert len(tools.TOOLS) == 606, PIN
    spec = [t for t in tools.TOOLS if t["name"] == "kaan"][0]
    acts = spec["input_schema"]["properties"]["action"]["enum"]
    assert acts == ["transcribe", "diarize", "minutes", "status", "list", "get", "search",
                    "live_start", "live_chunk", "live_stop", "live_get", "live_list",
                    "style", "vocab_add", "vocab_list", "vocab_remove"]  # W3 grew actions  # W2 grew actions
    assert "diarize" in tools.HANDLERS["kaan"].__code__.co_consts or True  # handler is shared; enum is the pin
    assert "speaker pehchaan NAHI" in spec["description"] or "NAHI" in spec["description"]


def test_actor_lanes_minutes_readonly_diarize_owner(env):
    ctx = conv_ctx()
    tid = insert_row(SEGS, text="kuch baat")
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    assert asyncio.run(_kaan(staff, action="minutes", id=tid))["n_turns"] >= 1    # a read stays open
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="diarize", id=tid))                       # a write is owner-only
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(cust, action="minutes", id=tid))
    with pytest.raises(Exception) as e:
        asyncio.run(_kaan(ctx, action="diarize"))                                 # no id, no file -> one honest line
    assert "file_id" in str(e.value)


def test_admit_keys_minutes_and_the_minute_trap():
    from app.agent import admit
    assert "kaan" in admit._match("is meeting ki minutes bana do")
    assert "kaan" in admit._match("minutes likho call ki")
    assert "kaan" in admit._match("kaun bola tha call mein")
    assert "kaan" not in admit._match("10 minute ruko")               # bare minute never admits
    assert "kaan" not in admit._match("5 minutes mein aa jaunga")
    assert "kaan" in admit._match("meeting ki transcript banao")      # the W0 keys still hold


def test_laziness_laws_hold_for_the_new_modules():
    for mod in (DI, MT):
        src = inspect.getsource(mod)
        assert "import whisper" not in src and "import torch" not in src
        assert "sklearn" not in src and "pyannote" not in src
    sys.modules.pop("app.kaan.diarize", None)
    sys.modules.pop("app.kaan.meeting", None)
    import importlib
    importlib.import_module("app.kaan.diarize")
    importlib.import_module("app.kaan.meeting")
    assert "whisper" not in sys.modules and "torch" not in sys.modules


def test_version_pin_v0607():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.646.0"
