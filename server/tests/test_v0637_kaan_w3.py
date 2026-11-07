"""KAAN W3 (v0.645.0, owner: "START" + "always show result in English" - Wave W3: styles + vocabulary).

(1) THE VOCAB: per-tenant terms with two honest mechanisms - initial_prompt seeding (SOFT: whisper has
    no hard vocab biasing, from the repo read) and fix_to deterministic replacement (word-boundary,
    case-insensitive, every application counted and named in the row note - nothing silent).
(2) THE STYLES: five deterministic renders of a STORED transcript (verbatim/clean/subtitles/minutes/
    social) - extractive only, read-only, gate-free by the W1 law (no audio ingest, text already hers).
(3) THE LIVE LINK: start freezes the tenant prompt into the session; every rolling pass and the clean
    pass carry it. THE GATES: no new switch - transcribe/live stay behind kaan_audio; vocab mutations
    are owner/approved; style/vocab_list are reads. Registry 606 - actions, not tools.
Zero network, zero torch; the engine is scripted.
"""
import asyncio
import inspect
import sys

import pytest

from app.agent import tools
from app.agent.kaan_tools import _kaan
from app.kaan import engine as EN
from app.kaan import live as LV
from app.kaan import meeting as MT
from app.kaan import service as KS
from app.kaan import styles as ST
from app.kaan import vocab as VB
from tests.test_life import conv_ctx

PIN = ("their 593 + W1 (0.613) + W2 (0.618) + W3 style/vocab_add/vocab_list/vocab_remove ACTIONS (0.637) "
       "- actions, not tools, registry 606")


@pytest.fixture()
def w3_env(env, tmp_path, monkeypatch):
    """Fresh DB (env) + AUDIO gate ON + engine ready (the W2 live_env pattern)."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    from app.config import get_settings
    get_settings.cache_clear()
    EN._AVAIL.clear()
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()


def prompt_engine(store, text="gupta ji bole kal milan hoga."):
    """Whisper-shaped engine that CAPTURES the initial_prompt it was handed (the W3 assertion point)."""
    def _f(path, *, model="", language="", task="transcribe", word_timestamps=True,
           initial_prompt="", **_k):
        store["prompt"] = initial_prompt
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
    """A stored-row-shaped dict: two segments, a 0.8s word gap between 'ji.' and 'kal'."""
    w1 = [{"word": "namaste", "start": 0.0, "end": 0.5}, {"word": "gupta", "start": 0.5, "end": 1.0},
          {"word": "ji.", "start": 1.0, "end": 1.4}]
    w2 = [{"word": "kal", "start": 2.2, "end": 2.6}, {"word": "milan", "start": 2.6, "end": 3.1},
          {"word": "hoga.", "start": 3.1, "end": 3.6}]
    segs = [{"start": 0.0, "end": 1.4, "text": "namaste gupta ji.", "words": w1},
            {"start": 2.2, "end": 3.6, "text": "kal milan hoga.", "words": w2}]
    return {"id": "kn_w3test", "text": "namaste gupta ji. kal milan hoga.", "segments": segs,
            "duration_s": 3.6, "file_name": "t.wav", "language": "hi", "speakers": {}, "n_words": 6}


# ---------------------------------------------------------------- (1) vocab CRUD
def test_vocab_add_list_remove_roundtrip(w3_env):
    VB.add("t1", "Gupta ji", fix_to="Gupta Ji", note="the neighbour")
    VB.add("t1", "Bhandar")
    out = VB.list_vocab("t1")
    assert out["n"] == 2 and [i["term"] for i in out["items"]] == ["Gupta ji", "Bhandar"]
    assert out["items"][0]["fix_to"] == "Gupta Ji"
    VB.remove("t1", "bhandar")                                   # case-insensitive remove
    assert VB.list_vocab("t1")["n"] == 1
    with pytest.raises(ValueError):
        VB.remove("t1", "kabhi tha hi nahi")


def test_vocab_upsert_is_case_insensitive(w3_env):
    a = VB.add("t1", "Gupta Ji")
    b = VB.add("t1", "gupta ji", fix_to="Gupta Ji")
    assert a["updated"] is False and b["updated"] is True
    assert VB.list_vocab("t1")["n"] == 1


def test_vocab_validation_honest(w3_env):
    with pytest.raises(ValueError):
        VB.add("t1", "   ")
    with pytest.raises(ValueError):
        VB.add("t1", "Kaan", fix_to="Kaan")                      # replacement identical -> refusal
    VB.add("t1", "gupta", fix_to="Gupta")                        # case-only fix = a real fix (case drift)
    assert VB.fixes_for("t1") == {"gupta": "Gupta"}
    with pytest.raises(ValueError):
        VB.add("t1", "x" * 121)


def test_vocab_tenant_isolation(w3_env):
    VB.add("tA", "Gupta ji")
    assert VB.list_vocab("tB")["n"] == 0
    assert VB.fixes_for("tB") == {} and VB.prompt_for("tB") == ("", 0, 0)
    assert VB.count("tA") == 1 and VB.count("tB") == 0


def test_vocab_prompt_cap_oldest_kept(w3_env):
    for i in range(30):
        VB.add("t1", f"term{i:02d} " + "shabd" * 6)              # ~37 chars each -> > 800 total
    prompt, n_terms, n_trunc = VB.prompt_for("t1")
    assert n_terms == 30 and len(prompt) <= VB.PROMPT_CAP and n_trunc > 0
    assert prompt.startswith("term00") and "term29" not in prompt  # oldest kept first


def test_apply_text_word_boundaries_and_counts(w3_env):
    text, segs, per, total = VB.apply_out(
        "KAAN chalu hai. Skaana nahi. kaan phir.", [], {"Kaan": "KHAAN"})
    assert text == "KHAAN chalu hai. Skaana nahi. KHAAN phir."
    assert per == {"Kaan": 2} and total == 2


# ---------------------------------------------------------------- (2) transcribe integration
def test_transcribe_seeds_prompt_and_applies_fixes(w3_env):
    store = {}
    VB.add("default", "gupta ji")
    VB.add("default", "milan", fix_to="MILAN")
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=prompt_engine(store))
    assert store["prompt"] == "gupta ji, milan"                   # the soft hint rode along
    assert out["text"] == "gupta ji bole kal MILAN hoga."         # the hard fix applied
    assert "vocab (W3): 2 term(s) seeded as initial_prompt" in out["note"]
    assert "milan x2" in out["note"] and "text + segment copies" in out["note"]
    assert out["vocab"] == {"terms": 2, "fixes": 2}


def test_transcribe_vocab_false_is_raw(w3_env):
    store = {}
    VB.add("default", "gupta ji", fix_to="Gupta Ji")
    out = KS.transcribe_file("default", name="t.wav", data=b"x", vocab=False, fn=prompt_engine(store))
    assert store["prompt"] == "" and "Gupta Ji" not in out["text"]
    assert out["vocab"] == {"applied": False} and "vocab (W3)" not in out["note"]


def test_engine_accepts_initial_prompt(tmp_path):
    assert "initial_prompt" in inspect.signature(EN.transcribe).parameters
    p = tmp_path / "a.wav"
    p.write_bytes(b"x")
    EN.fake_engine("kuch bhi")(str(p), initial_prompt="hint")   # no TypeError


# ---------------------------------------------------------------- (3) styles
def test_style_verbatim_passthrough():
    out = ST.render("verbatim", row_dict())
    assert out["rendered"]["text"] == "namaste gupta ji. kal milan hoga."
    assert "as-is" in out["note"]


def test_style_clean_is_deterministic(w3_env):
    row = {"id": "kn_c", "text": "namaste   namaste gupta ji.  aur suno.", "segments": [], "duration_s": 2.0}
    out = ST.render("clean", row)
    assert out["rendered"]["text"] == "Namaste gupta ji. Aur suno."   # dupe collapsed + ws + sentence caps
    assert "1 immediate duplicate token(s) collapsed" in out["note"]
    again = ST.render("clean", row)
    assert again["rendered"]["text"] == out["rendered"]["text"]       # same input, same output


def test_style_subtitles_split_on_gap():
    out = ST.render("subtitles", row_dict())
    lines = out["rendered"]["lines"]
    assert [ln["n"] for ln in lines] == [1, 2]                        # the 0.8s gap cut it
    assert lines[0]["text"] == "namaste gupta ji." and lines[1]["start"] == 2.2
    assert ">0.6s word gap" in out["note"]


def test_style_subtitles_wraps_without_words():
    row = {"id": "kn_w", "text": " ".join(f"shabd{i}" for i in range(30)),
           "segments": [{"start": 0.0, "end": 10.0, "text": " ".join(f"shabd{i}" for i in range(30))}]}
    out = ST.render("subtitles", row)
    lines = out["rendered"]["lines"]
    assert len(lines) == 3 and all(len(ln["text"].split()) <= 12 for ln in lines)
    assert "no word timestamps" in out["note"]


def test_style_minutes_composes_w1():
    row = row_dict()
    out = ST.render("minutes", row)
    assert out["rendered"]["minutes"] == MT.minutes(row)


def test_style_social_extractive():
    out = ST.render("social", row_dict())
    r = out["rendered"]
    assert r["hook"].startswith("namaste gupta ji.")
    assert any(b.startswith("Key words:") for b in r["bullets"])
    assert "no generation" in out["note"]


def test_style_unknown_lists_the_styles():
    with pytest.raises(ValueError) as e:
        ST.render("poetry", row_dict())
    assert "subtitles" in str(e.value)


def test_style_is_gate_free_but_transcribe_is_not(w3_env, monkeypatch):
    out = KS.transcribe_file("default", name="t.wav", data=b"x", fn=prompt_engine({}))
    tid = out["id"]
    monkeypatch.setenv("KAAN_AUDIO", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(EN.KaanError):                                 # audio path still gated
        KS.transcribe_file("default", name="t.wav", data=b"x", fn=prompt_engine({}))
    rendered = KS.style_render("default", tid, "clean")               # the stored text stays hers
    assert rendered["style"] == "clean"
    get_settings.cache_clear()


# ---------------------------------------------------------------- (4) the live link
def test_live_freezes_prompt_and_every_pass_carries_it(w3_env, monkeypatch):
    store = {}
    VB.add("default", "gupta ji")
    VB.add("default", "milan", fix_to="MILAN")
    monkeypatch.setattr(LV, "_decode_chunk", lambda data: b"\x00\x00" * 16000 * 3)  # 3s >= MIN_WINDOW
    eng = prompt_engine(store)
    monkeypatch.setattr(EN, "transcribe", eng)
    out = LV.start("default")
    sid = out["id"]
    assert out["vocab_terms"] == 2                                  # frozen at start (no engine call yet)
    frozen = VB.prompt_for("default")[0]
    assert frozen == "gupta ji, milan"
    store["prompt"] = "RESET"
    LV.chunk("default", sid, b"\x01\x02" * 100)
    assert store["prompt"] == frozen                                # rolling pass carried it
    LV.stop("default", sid, finalize_model="base")
    assert store["prompt"] == frozen                                # the clean pass carried it too


# ---------------------------------------------------------------- (5) wiring + laws
def test_actions_grew_registry_did_not():
    assert len(tools.TOOLS) == 606, PIN
    spec = [t for t in tools.TOOLS if t["name"] == "kaan"][0]
    acts = spec["input_schema"]["properties"]["action"]["enum"]
    assert acts == ["transcribe", "diarize", "minutes", "status", "list", "get", "search",
                    "live_start", "live_chunk", "live_stop", "live_get", "live_list",
                    "style", "vocab_add", "vocab_list", "vocab_remove"], PIN
    assert len(spec["description"]) <= 1200                           # the diet
    assert "vocab_add" in spec["description"] and "deterministic render" in spec["description"]
    props = spec["input_schema"]["properties"]
    assert {"style", "term", "fix_to", "vocab"} <= set(props)


def test_actor_lanes_vocab_is_owner_only(w3_env):
    ctx = conv_ctx()
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(Exception):
        asyncio.run(_kaan(staff, action="vocab_add", term="x"))       # tenant data write: owner lane
    with pytest.raises(Exception):
        asyncio.run(_kaan(cust, action="vocab_list"))
    out = asyncio.run(_kaan(ctx, action="vocab_add", term="Gupta ji", fix_to="Gupta Ji"))
    assert out["updated"] is False
    listed = asyncio.run(_kaan(ctx, action="vocab_list"))
    assert listed["n"] == 1


def test_status_carries_styles_and_vocab(w3_env):
    st = asyncio.run(_kaan(conv_ctx(), action="status"))
    assert st["styles"]["list"] == ["verbatim", "clean", "subtitles", "minutes", "social"]
    assert st["vocab"]["n_terms"] >= 0 and st["vocab"]["note"]
    assert st["gate"] == "ON"                                         # still the one audio gate


def test_w3_modules_purity_and_laziness():
    for mod in (VB, ST):
        src = inspect.getsource(mod)
        assert "httpx" not in src and "requests" not in src and "openai" not in src
        assert "import whisper" not in src and "import torch" not in src
    sys.modules.pop("app.kaan.vocab", None)
    sys.modules.pop("app.kaan.styles", None)
    import importlib
    importlib.import_module("app.kaan.vocab")
    importlib.import_module("app.kaan.styles")
    assert "whisper" not in sys.modules and "torch" not in sys.modules


def test_version_pin_v0637():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.646.0"
