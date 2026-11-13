"""v0.880 TEZ CALL: a call's brain answers sooner - the PC hand-off waits 4 s (not 12), the memory read uses this
call's warm copies (and a warm-up at call start), and the OpenRouter / GLM path logs its prep + call time."""
import asyncio
import inspect
import time
import types

from app.agent import santosh, tools as T
from app.config import Settings


def test_defaults():
    f = Settings.model_fields
    assert f["voice_brain_pc_wait_s"].default == 4.0
    assert f["voice_brain_memory_s"].default == 1.5
    assert f["voice_brain_memory_warm_s"].default == 0.6
    assert f["voice_brain_prefetch"].default is True


def test_pc_handoff_waits_short_only_on_a_call():
    tok = santosh.VOICE_BRAIN_NOW.set(True)
    try:
        assert T._call_pc_wait("pc_do", {"task": "x"})["_wait"] == 4.0
        assert T._call_pc_wait("hoola_pc_do", {"task": "x"})["_wait"] == 4.0
        assert T._call_pc_wait("pc_team", {"tasks": []})["_wait"] == 4.0
        assert T._call_pc_wait("pc_do", {"task": "x", "_wait": 0})["_wait"] == 0   # a caller's own wait wins
        assert "_wait" not in T._call_pc_wait("email_draft", {"to": "a"})
    finally:
        santosh.VOICE_BRAIN_NOW.reset(tok)
    assert "_wait" not in T._call_pc_wait("pc_do", {"task": "x"})             # chat: unchanged
    assert "_call_pc_wait(name, args" in inspect.getsource(T.dispatch)


def _parts(monkeypatch, slow_s):
    from app import kaamwatch, kaamlist, events, callconv
    from app import coder as _coder
    monkeypatch.setattr(kaamwatch, "block", lambda *a, **k: "KAAM KA HAAL")
    monkeypatch.setattr(_coder.inject, "turn_block", lambda *a, **k: (time.sleep(slow_s), "CODER")[1])
    monkeypatch.setattr(kaamlist, "brief", lambda *a, **k: "")
    monkeypatch.setattr(events, "cards_block", lambda *a, **k: "")
    monkeypatch.setattr(callconv, "chat_block", lambda *a, **k: "")
    monkeypatch.setattr(santosh, "_call_chat_saar", lambda *a, **k: "")
    monkeypatch.setattr(santosh, "_call_facts", lambda *a, **k: "FACTS")


def test_warm_copies_cut_the_wait(monkeypatch):
    _parts(monkeypatch, 2.0)
    st = types.SimpleNamespace(voice_brain_memory_s=1.5, voice_brain_memory_warm_s=0.2, voice_brain_yaad=False)
    conv = "c_warm_%d" % int(time.time() * 1000)

    async def go():
        t0 = time.monotonic()
        first = await santosh._brain_memory("t", conv, "x", st)       # cold: waits the whole 1.5 s, coder late
        t1 = time.monotonic() - t0
        await asyncio.sleep(0.8)                                    # the late part finishes and is kept
        t0 = time.monotonic()
        second = await santosh._brain_memory("t", conv, "x", st)    # warm: 0.2 s, the kept copy used
        return first, t1, second, time.monotonic() - t0
    first, t1, second, t2 = asyncio.run(go())
    assert t1 >= 1.4 and "CODER" not in first and "not loaded yet" in first
    assert t2 < 0.6, t2
    assert "CODER" in second and "KAAM KA HAAL" in second and "not loaded yet" not in second


def test_prefetch_and_glm_timing_wired():
    from app import voice
    assert "brain_prefetch(" in inspect.getsource(voice.Call.run)
    src = inspect.getsource(santosh._call_brain_once)
    assert "glm call %.1fs" in src and "_prep_line()" in src


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.880.0")
