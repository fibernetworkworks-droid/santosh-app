"""v0.999.110 the 6-minute silences in the portal exam (sam.gov, irs.gov): the server log showed the step's screenshot,
then nothing until the card gave up - the AI call never ended. httpx's timeout is per read and OpenRouter keeps a slow
request alive with blank bytes, so the 35 s limit never fired. Now each PC step has a hard total limit: a step that has
not answered is told to her, tried once more, then the task ends cleanly (BrainSlow)."""
from __future__ import annotations

import asyncio
import time
import types

import httpx
import pytest

from app.pc import brain


def test_a_call_that_trickles_for_ever_is_cut_at_the_limit(monkeypatch):
    calls = []

    async def slow_post(self, url, **kw):
        calls.append(time.monotonic())
        await asyncio.sleep(30)                       # a provider that never answers (blank keep-alive bytes)
    monkeypatch.setattr(httpx.AsyncClient, "post", slow_post)
    monkeypatch.setattr(brain, "qwen_route", lambda: ("https://openrouter.test/v1/chat/completions", "k", "or"))
    st = types.SimpleNamespace(pc_brain_timeout_s=0.3, pc_qwen_thinking="", pc_qwen_provider_sort="")
    monkeypatch.setattr(brain, "get_settings", lambda: st)
    slow = []
    t0 = time.monotonic()
    with pytest.raises(brain.BrainSlow):
        asyncio.run(brain.think_qwen("qwen/qwen3.8-27b", "sys", [{"role": "user", "content": "hi"}], [], 500,
                                     on_slow=lambda: slow.append(1)))
    assert time.monotonic() - t0 < 5 and len(calls) == 2 and slow == [1]      # cut, said once, tried once more


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.139"


def test_trace_reader_names_a_credit_stop_and_never_borrows_an_old_run(tmp_path):
    import json
    from app.quality import pctrace_read as R
    q = tmp_path / "quality"
    q.mkdir()
    old = tmp_path / "trace" / "t1" / "pcop_old"
    old.mkdir(parents=True)
    (old / "meta.json").write_text(json.dumps({"job": "pcop_old", "task": "Open irs.gov and go to the 'Where's My Refund' page."}))
    (q / "pccard-1.json").write_text(json.dumps({"exam": "portal", "rows": [
        {"id": "us_irs_refund", "ok": False, "job": "pcop_new", "why": "Stopped at step 0: OpenRouter credit is low: add credit"}]}))
    out = "\n".join(R.report(q / "pccard-1.json", tmp_path / "trace"))
    assert "OpenRouter credit ran out" in out and "pcop_old" not in out and "no step record found" in out
