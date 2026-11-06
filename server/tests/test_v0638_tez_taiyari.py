"""v0.638 TEZ TAIYARI (her 16:36 call: `brain prep 19.6s` = memory 7.0 s + MCP 4.5 s + hint 1.8 s before Haiku's 5.9 s).
A call brain turn reads memory in parallel under a short wait, never waits on her MCP servers, skips the hint lookup."""
import asyncio
import inspect
import threading
import time
import types

from app.agent import mcp_live, santosh


def test_mcp_snapshot_fast_never_waits(monkeypatch):
    called = threading.Event()

    def slow(tenant):
        time.sleep(0.3)
        with mcp_live._lock:
            mcp_live._cache[tenant] = (time.time(), "sig", [{"pack_id": "p1", "tools": []}])
        called.set()
        return []

    monkeypatch.setattr(mcp_live, "snapshot", slow)
    mcp_live._cache.pop("tz", None)
    t0 = time.monotonic()
    assert mcp_live.snapshot_fast("tz") == []           # nothing cached yet: no MCP this ask, no wait
    assert time.monotonic() - t0 < 0.1
    assert called.wait(2)                               # refreshed in the background
    assert mcp_live.snapshot_fast("tz")[0]["pack_id"] == "p1"
    mcp_live._cache.pop("tz", None)


def test_brain_memory_leaves_out_a_slow_part(monkeypatch):
    from app import yaad, kaamwatch
    from app import coder as _coder
    monkeypatch.setattr(yaad, "turn_block", lambda *a, **k: (time.sleep(1.5), "YAAD")[1])
    monkeypatch.setattr(kaamwatch, "block", lambda *a, **k: "KAAM KA HAAL")
    monkeypatch.setattr(_coder.inject, "turn_block", lambda *a, **k: "")
    st = types.SimpleNamespace(voice_brain_memory_s=0.3)
    async def go():
        t0 = time.monotonic()
        got = await santosh._brain_memory("t", "c", "ho gaya kya", st)
        return got, time.monotonic() - t0
    out, took = asyncio.run(go())
    assert took < 1.0
    assert "KAAM KA HAAL" in out and "YAAD" not in out


def test_brain_turn_skips_hint_and_slow_mcp():
    src = inspect.getsource(santosh._steps)
    assert 'and not VOICE_BRAIN_NOW.get():' in src and "procedures.hint" in src
    src2 = inspect.getsource(santosh._steps_inner)
    assert "mcp_live.snapshot_fast(tenant_id)" in src2
    assert "_brain_memory(" in inspect.getsource(santosh._run_turn)
    from app.config import Settings
    assert Settings.model_fields["voice_brain_memory_s"].default == 2.5
