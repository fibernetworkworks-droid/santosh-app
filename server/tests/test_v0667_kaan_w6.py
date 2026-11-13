"""KAAN W6 (v0.670.0, owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start").

The accountability layer her audio runs on, then the unlock it buys:
- kaan_quota_audio_min: a per-tenant monthly audio-minutes cap - ffprobe estimate BEFORE the
  engine spends; live_start refuses at cap; the meter counts finished kn_ rows only (a live
  session's seconds are counted once, by the row its stop writes).
- kaan_retention_days: the daily worker sweep - unpinned kn_ rows past the cutoff go, live
  sessions go with their spine PCM files; pinned rows survive (the column W0 baked for this).
- diarize=voiceprint: real speaker names at transcribe time, matched against her enrolled
  Awaaz Pehchaan prints (voiceid.service) under the voiceid threshold law - guarded by
  KAAN_VOICEPRINT=1 AND bounded retention, refused BEFORE the engine burns a run.
Zero new tables, zero new tools (enum stays 18, registry stays 607), zero network, zero torch.
"""
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent.kaan_tools import KAAN_TOOLS, _ACTIONS
from app.kaan import limits as LM
from app.kaan import service as KS
from app.kaan import voiceprint as VP
from tests.test_v0656_kaan_w4 import capture_engine

H = {"Authorization": "Bearer k5"}


@pytest.fixture()
def w6_env(env, tmp_path, monkeypatch):
    """Fresh DB (env) + AUDIO gate ON + engine ready + gyaan sync/hash + the API key for HTTP."""
    monkeypatch.setenv("KAAN_AUDIO", "true")
    monkeypatch.setenv("KAAN_MODEL", "small")
    monkeypatch.setenv("KAAN_LIVE_DIR", str(tmp_path / "kaan_live"))
    monkeypatch.setenv("GYAAN_SYNC", "true")
    monkeypatch.setenv("GYAAN_EMBED", "hash")
    monkeypatch.setenv("API_KEY", "k5")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.kaan import engine as EN
    EN._AVAIL.clear()
    KS.EN._AVAIL.clear()                                    # service's OWN binding (the W5 lesson)
    monkeypatch.setitem(EN._AVAIL, "ok", (True, "engine ready"))
    monkeypatch.setitem(KS.EN._AVAIL, "ok", (True, "engine ready"))
    from app.gyaan import embed
    embed.reset()
    yield monkeypatch
    get_settings.cache_clear()
    EN._AVAIL.clear()
    KS.EN._AVAIL.clear()
    embed.reset()


def client():
    from app.main import app
    return TestClient(app)


def seed_row(env_m, name="t.wav", text="namaste gupta ji. kal milan hoga.", **kw):
    """One stored transcript through the REAL service, engine scripted."""
    return KS.transcribe_file("default", name=name, data=b"x", fn=capture_engine({}, text=text), **kw)


def old_row(days=40, pinned=False, tenant="default"):
    """A row aged past any sane cutoff, inserted directly (the sweep reads created_at)."""
    from app.db import now, session
    from app.kaan.models import KaanTranscript
    rid = f"kn_old{days}{'p' if pinned else ''}"
    with session() as s:
        s.add(KaanTranscript(id=rid, tenant_id=tenant, file_name="old.wav", duration_s=60.0,
                             text="purani baat", status="ready", pinned=pinned,
                             created_at=now() - timedelta(days=days)))
        s.commit()
    return rid


# ---------------------------------------------------------------- quota
def test_quota_default_is_unlimited(w6_env):
    u = LM.month_usage("default")
    assert u["unlimited"] is True and u["quota_min"] == 0 and u["audio_min_used"] == 0.0
    LM.check_quota_file("default", 10 ** 9)                 # no cap -> never raises


def test_quota_counts_finished_rows_only(w6_env, monkeypatch):
    monkeypatch.setattr(KS, "_duration_of", lambda p: 90.0)   # the ffprobe seam
    seed_row(w6_env)
    u = LM.month_usage("default")
    assert u["audio_min_used"] == 1.5                        # 90 s = 1.5 min, counted AFTER it finished
    assert u["quota_min"] == 0 and u["unlimited"] is True


def test_quota_refuses_transcribe_over_cap(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_QUOTA_AUDIO_MIN", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(KS, "_duration_of", lambda p: 180.0)  # 3 min file under a 2 min cap
    with pytest.raises(ValueError) as e:
        seed_row(w6_env)
    assert "Audio quota" in str(e.value) and "KAAN_QUOTA_AUDIO_MIN" in str(e.value)
    assert "resets on the 1st" in str(e.value)


def test_quota_allows_within_cap(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_QUOTA_AUDIO_MIN", "5")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(KS, "_duration_of", lambda p: 120.0)
    d = seed_row(w6_env)
    assert d["stored"] is True
    assert LM.month_usage("default")["audio_min_used"] == 2.0


def test_quota_zero_duration_never_blocks(w6_env, monkeypatch):
    """ffprobe absent -> estimate 0.0 -> the run goes through; the row still counts after."""
    monkeypatch.setenv("KAAN_QUOTA_AUDIO_MIN", "1")
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(KS, "_duration_of", lambda p: 0.0)
    d = seed_row(w6_env)
    assert d["stored"] is True and d["duration_s"] == 0.0


def test_quota_refuses_live_start_at_cap(w6_env, monkeypatch):
    monkeypatch.setattr(KS, "_duration_of", lambda p: 120.0)
    seed_row(w6_env)                                        # 2 min already spent this month
    monkeypatch.setenv("KAAN_QUOTA_AUDIO_MIN", "2")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(ValueError) as e:
        KS.live_start("default", fn=None)
    assert "no new live session" in str(e.value)
    monkeypatch.setenv("KAAN_QUOTA_AUDIO_MIN", "10")
    get_settings.cache_clear()
    sess = KS.live_start("default")
    assert sess["id"].startswith("kl_")
    KS.live_stop("default", sess["id"])                     # spine seconds land on the kn_ row
    used = LM.month_usage("default")["audio_min_used"]
    assert used >= 2.0                                      # counted once, by the finished row


# ---------------------------------------------------------------- retention
def test_retention_zero_is_an_honest_noop(w6_env):
    old_row(days=400)
    out = LM.retention_sweep()
    assert out["ran"] is False and "keep forever" in out["reason"]
    assert KS.get_transcript("default", "kn_old400")["text"] == "purani baat"


def test_retention_sweeps_old_unpinned_keeps_fresh(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    old_row(days=40)
    fresh = seed_row(w6_env)["id"]
    out = LM.retention_sweep()
    assert out["ran"] is True and out["removed_transcripts"] == 1
    with pytest.raises(ValueError):
        KS.get_transcript("default", "kn_old40")
    assert KS.get_transcript("default", fresh)["id"] == fresh


def test_retention_keeps_pinned_rows(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "7")
    from app.config import get_settings
    get_settings.cache_clear()
    rid = old_row(days=400, pinned=True)
    out = LM.retention_sweep()
    assert out["removed_transcripts"] == 0
    assert KS.get_transcript("default", rid)["pinned"] is True


def test_retention_removes_spine_files_and_sessions(w6_env, monkeypatch, tmp_path):
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "7")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import now, session
    from app.kaan.models import KaanLiveSession
    spine = tmp_path / "kl_old.pcm"
    spine.write_bytes(b"\x00" * 32000)
    with session() as s:
        s.add(KaanLiveSession(id="kl_old", tenant_id="default", pcm_path=str(spine),
                              pcm_seconds=30.0, status="done",
                              created_at=now() - timedelta(days=40)))
        s.commit()
    out = LM.retention_sweep()
    assert out["removed_live_sessions"] == 1 and out["spine_files_removed"] == 1
    assert not spine.exists()


def test_retention_block_and_last_sweep(w6_env):
    b = LM.retention_block()
    assert b["days"] == 0 and "keep forever" in b["note"]
    LM.retention_sweep()
    assert LM._last_sweep["ts"]                             # status surfaces the last sweep honestly


def test_worker_kaan_jobs_runs_the_sweep_daily(w6_env, monkeypatch):
    import app.worker as W
    calls = []
    monkeypatch.setattr(W, "_kaan_last", 0.0)
    monkeypatch.setattr("app.kaan.limits.retention_sweep", lambda: calls.append(1))
    W.kaan_jobs()
    W.kaan_jobs()                                           # the 24 h throttle eats the second call
    assert len(calls) == 1


# ---------------------------------------------------------------- voiceprint
def test_voiceprint_off_refuses_before_the_engine(w6_env, monkeypatch):
    monkeypatch.setattr(KS, "_duration_of", lambda p: 60.0)
    with pytest.raises(ValueError) as e:
        seed_row(w6_env, diarize="voiceprint")
    assert "KAAN_VOICEPRINT" in str(e.value)
    assert "biometric" in str(e.value)


def test_voiceprint_needs_bounded_retention(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_VOICEPRINT", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(ValueError) as e:
        seed_row(w6_env, diarize="voiceprint")
    assert "KAAN_RETENTION_DAYS" in str(e.value) and "expiry" in str(e.value)


def test_voiceprint_needs_enrolled_prints(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_VOICEPRINT", "true")
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.voiceid import engine as VE
    monkeypatch.setattr(VE, "available", lambda: True)     # the REAL voiceid contract: a plain bool
    with pytest.raises(ValueError) as e:
        seed_row(w6_env, diarize="voiceprint")
    assert "No enrolled voiceprints" in str(e.value)


def test_voiceprint_ready_speaks_the_real_engine_contract(w6_env, monkeypatch):
    """The W6 FIX regression: the pre-existing voiceid engine contract is a PLAIN BOOL
    (available() -> bool; only the kaan engine's EN.available() is the tuple pair). voiceprint_ready
    must consume it UNPATCHED - the live box crashed here (TypeError: cannot unpack non-iterable
    bool object) while the suite stayed green, because these tests' own patches assumed the same
    wrong tuple shape. Nothing is patched here but the env."""
    monkeypatch.setenv("KAAN_VOICEPRINT", "true")
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.voiceid import engine as VE
    assert isinstance(VE.available(), bool)          # their lane's real contract, unpatched
    ok, why = LM.voiceprint_ready("default")         # the real engine - must not raise TypeError
    assert ok is False and why                       # engine missing in tests, or no enrolment yet


def two_turn_engine(store):
    """Two segments with a 1 s word gap -> two turns: turn 1 in the \x01 pcm region, turn 2 in \x00."""
    def _f(path, *, model="", language="", task="transcribe", word_timestamps=True,
           initial_prompt="", **_k):
        w1 = [{"word": w, "start": s, "end": s + 0.4} for s, w in
              zip((0.0, 0.5, 1.0), ("namaste", "gupta", "ji."))]
        w2 = [{"word": w, "start": s, "end": s + 0.4} for s, w in
              zip((3.4, 3.9, 4.4), ("kal", "milan", "hoga."))]
        segs = [{"start": 0.0, "end": 1.4, "text": "namaste gupta ji.", "words": w1},
                {"start": 3.4, "end": 4.8, "text": "kal milan hoga.", "words": w2}]
        return {"text": "namaste gupta ji. kal milan hoga.", "language": "hi", "segments": segs,
                "model": model or "small", "task": task}
    return _f


def test_voiceprint_names_sure_turns_only(w6_env, monkeypatch, tmp_path):
    monkeypatch.setenv("KAAN_VOICEPRINT", "true")
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.voiceid import engine as VE
    from app.voiceid import service as VS
    monkeypatch.setattr(VE, "available", lambda: True)     # the REAL voiceid contract: a plain bool
    people = [{"id": "m1", "name": "Gupta ji", "relation": "family"}]
    monkeypatch.setattr(VS, "call_people", lambda t: people)
    monkeypatch.setattr(VP, "_people", lambda t: people)    # the module's OWN seams
    hit = {"member": {"name": "Gupta ji"}, "score": 0.91, "margin": 0.2, "sure": True, "closest": "Gupta ji"}
    miss = {"member": None, "score": 0.40, "margin": 0.02, "sure": False, "closest": "Gupta ji"}
    monkeypatch.setattr(VP, "_identify", lambda ppl, pcm: hit if pcm[:1] == b"\x01" else miss)
    monkeypatch.setattr(VS, "pcm16k", lambda d: b"\x01" * 32000 * 3 + b"\x00" * 32000 * 4)
    d = KS.transcribe_file("default", name="t.wav", data=b"x", fn=two_turn_engine({}),
                           diarize="voiceprint")
    sp = d["speakers"]
    assert sp["method"] == "voiceprint" and sp["n_turns"] == 2
    assert sp["named_turns"] == 1
    assert sp["turns"][0]["speaker"] == "Gupta ji"
    assert sp["turns"][1]["speaker"] == "" and sp["turns"][1]["note"].startswith("no sure match")
    assert "no guessing" in sp["note"]
    row = KS.get_transcript("default", d["id"])
    assert row["speakers"]["method"] == "voiceprint"        # persisted into the row
    assert "diarize (W6)" in row["note"]


def test_voiceprint_technical_failure_keeps_the_transcript(w6_env, monkeypatch):
    """A broken print pass degrades to an honest note - the transcript itself survives."""
    monkeypatch.setenv("KAAN_VOICEPRINT", "true")
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "30")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.voiceid import engine as VE
    from app.voiceid import service as VS
    monkeypatch.setattr(VE, "available", lambda: True)     # the REAL voiceid contract: a plain bool
    monkeypatch.setattr(VS, "call_people", lambda t: [{"id": "m1", "name": "x"}])
    monkeypatch.setattr(VP, "_people", lambda t: [{"id": "m1", "name": "x"}])
    monkeypatch.setattr(VS, "pcm16k", lambda d: (_ for _ in ()).throw(RuntimeError("no ffmpeg")))
    d = seed_row(w6_env, diarize="voiceprint")
    assert d["status"] == "ready" and d["text"]
    assert d["speakers"]["error"] and "unaffected" in d["speakers"]["note"]


def test_pause_turns_diarize_at_transcribe_time(w6_env):
    d = seed_row(w6_env, diarize="pause_turns")
    assert d["speakers"]["method"] == "pause_turns"         # the W1 law, on fresh audio, no biometrics


def test_unknown_diarize_value_refuses(w6_env):
    with pytest.raises(ValueError) as e:
        seed_row(w6_env, diarize="whisper-x")
    assert "not known" in str(e.value)


# ---------------------------------------------------------------- surfaces
def test_status_carries_w6_blocks(w6_env, monkeypatch):
    monkeypatch.setenv("KAAN_RETENTION_DAYS", "14")
    from app.config import get_settings
    get_settings.cache_clear()
    st = KS.status("default")
    assert st["usage"]["quota_min"] == 0 and "resets on the 1st" in st["usage"]["note"]
    assert st["retention"]["days"] == 14 and st["retention"]["last_sweep"] is not None
    assert st["voiceprint"]["on"] is False and "KAAN_VOICEPRINT" in st["voiceprint"]["note"]


def test_http_transcribe_diarize_param_and_refusals(w6_env, monkeypatch):
    from app.kaan import engine as EN
    monkeypatch.setattr(KS, "_duration_of", lambda p: 60.0)
    monkeypatch.setattr(EN, "transcribe", capture_engine({}))    # the binding the route dispatches through
    monkeypatch.setattr(KS.EN, "transcribe", capture_engine({}))
    r = client().post("/api/kaan/transcribe", headers=H,
                      files={"file": ("t.wav", b"x", "audio/wav")}, data={"diarize": "pause_turns"})
    assert r.status_code == 200 and r.json()["speakers"]["method"] == "pause_turns"
    r2 = client().post("/api/kaan/transcribe", headers=H,
                       files={"file": ("t.wav", b"x", "audio/wav")}, data={"diarize": "voiceprint"})
    assert r2.status_code == 400 and "KAAN_VOICEPRINT" in r2.json()["detail"]   # the honest 400 door


def test_row_dict_carries_pinned(w6_env):
    d = seed_row(w6_env)
    assert KS.get_transcript("default", d["id"])["pinned"] is False


def test_registry_and_enum_untouched(w6_env):
    from app.agent.tools import TOOLS
    assert len(TOOLS) == 629, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). W6 adds dials, not tools (608 = 607 + their duniya v0.667 growth)"
    assert len(_ACTIONS) == 18 and "export" in _ACTIONS and "to_gyaan" in _ACTIONS
    props = KAAN_TOOLS[0]["input_schema"]["properties"]
    assert props["diarize"]["enum"] == ["", "pause_turns", "voiceprint"]
    assert KAAN_TOOLS[0]["input_schema"]["properties"]["action"]["enum"] == _ACTIONS


def test_mcp_door_rides_the_same_ks(w6_env):
    from app.kaan import mcp_server as MC
    out = MC.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                     "params": {"name": "kaan", "arguments": {"action": "status"}}}, "default")
    sc = out["result"]["structuredContent"]
    assert "usage" in sc and "retention" in sc and "voiceprint" in sc   # the W6 blocks ride every door


def test_no_new_tables():
    from app.kaan import models
    tables = {t for t in vars(models).values()
              if hasattr(t, "__tablename__") and isinstance(getattr(t, "__tablename__"), str)}
    assert {t.__tablename__ for t in tables} == {"kaan_transcripts", "kaan_vocab", "kaan_live_sessions"}


def test_app_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.875.0"
