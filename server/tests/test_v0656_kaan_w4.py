"""KAAN W4 (v0.659.0, owner: "W4 (exports + translation + Gyaan unlock)" - Wave W4 of the kaan plan).

(1) THE EXPORTS: deterministic SRT / VTT / TXT / JSON of a STORED transcript - pure serializations,
    zero deps, zero network; SRT/VTT cues are exactly the W3 subtitles lines (one code path, so
    captions and exports always agree); read-only, gate-free by the W1 law (no audio ingest).
(2) THE GYAAN UNLOCK: to_gyaan puts the transcript's own words into her gyaan corpus
    (idempotent by content via add_note's content-hash ref; nothing generated).
(3) THE TRANSLATE PROOF: task=translate was wired at W0 (schema -> _sync -> engine ladder,
    turbo refuses) - W4 proves it end-to-end with a captured engine and pins the honesty:
    whisper translates X->English only, a stored row without audio cannot be re-translated.
THE GATES: no new switch - export is a read (staff ok, customers out), to_gyaan writes tenant
data (owner/approved). Registry 606 - actions, not tools; the kaan actions enum grows to 18.
Zero network, zero torch; the engine is scripted.
"""
import asyncio
import inspect
import json

import pytest

from app.agent import tools
from app.agent.kaan_tools import _kaan, _ACTIONS
from app.kaan import engine as EN
from app.kaan import exports as EX
from app.kaan import service as KS
from app.kaan import styles as ST
from tests.test_life import conv_ctx

PIN = ("their 593 + W1 (0.613) + W2 (0.618) + W3 style/vocab ACTIONS (0.637) + W4 export/to_gyaan "
       "ACTIONS (0.656) - actions, not tools, registry 606")


@pytest.fixture()
def w4_env(env, monkeypatch):
    """Fresh DB (env) + AUDIO gate ON + engine ready + gyaan sync/hash (the w3_env + gyaan fixture pattern)."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    monkeypatch.setenv("GYAAN_SYNC", "true")
    monkeypatch.setenv("GYAAN_EMBED", "hash")
    from app.config import get_settings
    get_settings.cache_clear()
    EN._AVAIL.clear()
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    from app.gyaan import embed
    embed.reset()
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()
    embed.reset()


def capture_engine(store, text="namaste gupta ji. kal milan hoga."):
    """Whisper-shaped engine that CAPTURES task + initial_prompt (the W3 pattern, + task)."""
    def _f(path, *, model="", language="", task="transcribe", word_timestamps=True,
           initial_prompt="", **_k):
        store["task"], store["prompt"] = task, initial_prompt
        words, t = [], 0.0
        for w in text.split():
            words.append({"word": w, "start": round(t, 3), "end": round(t + 0.3, 3)})
            t += 0.3
        seg = {"start": 0.0, "end": round(t, 3), "text": text}
        if word_timestamps:
            seg["words"] = words
        return {"text": text, "language": language or "hi", "segments": [seg],
                "model": model or "small", "task": task}
    return _f


def row_dict():
    """A stored-row-shaped dict: two segments with a 0.8s word gap between 'ji.' and 'kal'."""
    w1 = [{"word": "namaste", "start": 0.0, "end": 0.5}, {"word": "gupta", "start": 0.5, "end": 1.0},
          {"word": "ji.", "start": 1.0, "end": 1.4}]
    w2 = [{"word": "kal", "start": 2.2, "end": 2.6}, {"word": "milan", "start": 2.6, "end": 3.1},
          {"word": "hoga.", "start": 3.1, "end": 3.6}]
    segs = [{"start": 0.0, "end": 1.4, "text": "namaste gupta ji.", "words": w1},
            {"start": 2.2, "end": 3.6, "text": "kal milan hoga.", "words": w2}]
    return {"id": "kn_w4test", "text": "namaste gupta ji. kal milan hoga.", "segments": segs,
            "duration_s": 3.6, "file_name": "t.wav", "language": "hi", "task": "transcribe",
            "model": "small", "speakers": {}, "n_words": 6}


# ---------------------------------------------------------------- formats (unit)
def test_srt_cues_are_the_subtitles_lines():
    r = EX.render("srt", row_dict())
    subs = ST.render("subtitles", row_dict())["rendered"]["lines"]
    assert r["n_cues"] == len(subs) == 2                       # split on the 0.8s gap (the phrase rule)
    assert "namaste gupta ji." in r["text"] and "kal milan hoga." in r["text"]
    assert "00:00:00,000 --> 00:00:01,400" in r["text"]        # comma milliseconds (srt law)
    assert "00:00:02,200 --> 00:00:03,600" in r["text"]
    assert r["text"].strip().splitlines()[0] == "1"            # numbered cues


def test_srt_deterministic():
    assert EX.render("srt", row_dict())["text"] == EX.render("srt", row_dict())["text"]


def test_vtt_header_and_dots():
    r = EX.render("vtt", row_dict())
    assert r["text"].startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:01.400" in r["text"]        # dot milliseconds (vtt law)
    assert "," not in r["text"].split("WEBVTT\n\n", 1)[1]


def test_txt_verbatim():
    r = EX.render("txt", row_dict())
    assert r["text"] == "namaste gupta ji. kal milan hoga.\n"
    assert r["n_cues"] == 0 and "verbatim" in r["note"]


def test_json_full_fidelity_and_deterministic():
    a, b = EX.render("json", row_dict()), EX.render("json", row_dict())
    assert a["text"] == b["text"]                              # sort_keys = deterministic bytes
    doc = json.loads(a["text"])
    assert doc["id"] == "kn_w4test" and doc["text"] == "namaste gupta ji. kal milan hoga."
    assert doc["n_segments"] == 2 and doc["segments"][0]["words"][0]["word"] == "namaste"
    assert doc["language"] == "hi" and doc["model"] == "small"


def test_wrapped_path_without_word_timestamps():
    row = {"id": "kn_w", "text": " ".join(f"shabd{i}" for i in range(30)), "duration_s": 10.0,
           "segments": [{"start": 0.0, "end": 10.0, "text": " ".join(f"shabd{i}" for i in range(30))}]}
    r = EX.render("srt", row)
    assert r["n_cues"] == 3 and all(len(ln.split()) <= 12 for ln in r["text"].splitlines() if "-->" not in ln and not ln.isdigit())
    assert "no word timestamps" in r["note"]


def test_text_only_row_gets_one_honest_cue():
    row = {"id": "kn_t", "text": "hello there.", "segments": [], "duration_s": 5.0}
    r = EX.render("srt", row)
    assert r["n_cues"] == 1 and "00:00:00,000 --> 00:00:05,000" in r["text"]
    assert "one cue from the row text" in r["note"]


def test_empty_row_and_unknown_fmt_refused():
    with pytest.raises(ValueError) as e:
        EX.render("srt", {"id": "kn_e", "text": "", "segments": []})
    assert "nothing to export" in str(e.value)
    with pytest.raises(ValueError) as e:
        EX.render("docx", row_dict())
    assert all(f in str(e.value) for f in EX.FORMATS)


# ---------------------------------------------------------------- service (stored rows)
def test_service_export_and_gate_free_read(w4_env):
    store: dict = {}
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=capture_engine(store))
    tid = out["id"]
    w4_env.setenv("KAAN_AUDIO", "false")                       # the W1 law: reads are gate-free
    from app.config import get_settings
    get_settings.cache_clear()
    r = KS.export_transcript("default", tid, "srt")
    assert r["filename"] == f"{tid}.srt" and r["n_cues"] >= 1 and r["tid"] == tid
    assert "namaste gupta ji." in r["text"]
    get_settings.cache_clear()


def test_export_tenant_isolation(w4_env):
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=capture_engine({}))
    with pytest.raises(ValueError) as e:
        KS.export_transcript("other", out["id"], "srt")
    assert "not found" in str(e.value)


def test_to_gyaan_adds_idempotent_and_honest(w4_env):
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=capture_engine({}))
    tid = out["id"]
    g = KS.to_gyaan("default", tid)
    assert g["tid"] == tid and tid in g["title"]
    assert g["gyaan"]["status"] in ("added", "updated") and g["gyaan"]["doc_id"]
    assert g["gyaan"]["chunks"] >= 1 and "gyaan_khojo" in g["note"] and "nothing was generated" in g["note"]
    again = KS.to_gyaan("default", tid)
    assert again["gyaan"]["status"] == "same"                  # idempotent by content (the ref is a content hash)


def test_to_gyaan_empty_refused(w4_env):
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=capture_engine({}, text=""))
    with pytest.raises(ValueError) as e:
        KS.to_gyaan("default", out["id"])
    assert "nothing to put into gyaan" in str(e.value)


# ---------------------------------------------------------------- translate proof (wired at W0)
def test_translate_end_to_end_and_turbo_refusal(w4_env):
    store: dict = {}
    out = KS.transcribe_file("default", name="t.wav", data=b"x", task="translate", fn=capture_engine(store))
    assert store["task"] == "translate"                        # the engine really received it
    assert out["task"] == "translate"
    row = KS.get_transcript("default", out["id"])
    assert row["task"] == "translate"                          # the row records the task (the W4 column use)
    assert "turbo" not in EN.TRANSLATE_CAPABLE                 # the ladder's honesty: turbo cannot translate
    from app.agent.kaan_tools import KAAN_TOOLS
    assert "translate" in KAAN_TOOLS[0]["input_schema"]["properties"]["task"]["enum"]


# ---------------------------------------------------------------- gates + registry
def test_actor_lanes_export_reads_to_gyaan_writes(w4_env):
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=capture_engine({}))
    ctx = conv_ctx()
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    got = asyncio.run(_kaan(staff, action="export", id=out["id"], fmt="txt"))   # a read: staff ok
    assert got["fmt"] == "txt" and "namaste" in got["text"]
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="to_gyaan", id=out["id"]))              # tenant data write: owner lane
    with pytest.raises(Exception):
        asyncio.run(_kaan(cust, action="export", id=out["id"], fmt="txt"))
    g = asyncio.run(_kaan(ctx, action="to_gyaan", id=out["id"]))
    assert g["gyaan"]["chunks"] >= 1


def test_actions_grew_registry_did_not():
    assert len(tools.TOOLS) == 606, PIN
    assert _ACTIONS[-2:] == ["export", "to_gyaan"] and len(_ACTIONS) == 18
    spec = next(t for t in tools.TOOLS if t["name"] == "kaan")
    assert spec["input_schema"]["properties"]["action"]["enum"] == _ACTIONS
    assert "fmt" in spec["input_schema"]["properties"]
    assert len(spec["description"]) <= 1200                    # the diet
    assert "export" in spec["description"] and "to_gyaan" in spec["description"]


def test_status_carries_exports_block(w4_env):
    st = asyncio.run(_kaan(conv_ctx(), action="status"))
    assert st["exports"]["formats"] == ["srt", "vtt", "txt", "json"]
    assert "to_gyaan" in st["exports"]["note"] and "X->English" in st["exports"]["note"]
    assert st["gate"] == "ON"                                  # still the one audio gate


def test_exports_purity_and_gyaan_laziness():
    src = inspect.getsource(EX)
    assert not any(w in src for w in ("httpx", "requests", "openai", "anthropic", "socket", "subprocess"))
    fn_src = inspect.getsource(KS.to_gyaan)
    assert "from ..gyaan import ingest" in fn_src              # lazy: kaan never loads gyaan unless used
    top_src = inspect.getsource(KS)
    assert top_src.count("from ..gyaan import ingest") == 1    # only inside the function


def test_app_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.661.0"
