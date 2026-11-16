"""v0.959 HOOLA PIPELINE FEED LIMITS - her first live run on the VPS (16 Nov 2026): Hugging Face's dataset server answered
429 Too Many Requests for 29 of 30 boards (the worker's first run and her vps-ops run went at the same time, ~140 pages
each, no pause), so 10 kinds came out empty and the run still counted as today's tables. Now: one run at a time, a pause
between pages, the server's own Retry-After obeyed, boards kept with the dataset's commit (same commit = no re-read),
a failed board uses its last good read, and a run that could not read every board tries again in an hour."""
from __future__ import annotations

import asyncio

import httpx
import pytest

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("_v0958_feed", Path(__file__).with_name("test_v0958_pipeline_feed.py"))
_v0958 = importlib.util.module_from_spec(_spec)
sys.modules["_v0958_feed"] = _v0958
_spec.loader.exec_module(_v0958)
_cat, _rows = _v0958._cat, _v0958._rows


def _429(after="7"):
    req = httpx.Request("GET", "https://datasets-server.huggingface.co/rows")
    return httpx.HTTPStatusError("429", request=req, response=httpx.Response(429, headers={"Retry-After": after},
                                                                              request=req))


@pytest.fixture
def pl(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DIR", str(tmp_path / "pl"))
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import sources as S
    S.reset()
    text = []
    for c in ["overall", "creative_writing", "longer_query", "math", "hard_prompts", "coding", "instruction_following",
              "non_english", "spanish", "chinese", "french", "german", "japanese", "korean", "russian", "polish"]:
        text += _rows([(f"Model {i}", 1500 - i * 9) for i in range(30)], cat=c)
    boards = {"text": text}
    monkeypatch.setattr(S, "openrouter", _cat)
    monkeypatch.setattr(S, "dataset_sha", lambda: "sha-a")
    monkeypatch.setattr(S, "_sleep", lambda s: None)
    monkeypatch.setattr(S, "config_rows", lambda c, **k: boards.get(c, []))
    monkeypatch.setattr(S, "voi_tts", lambda: (_ for _ in ()).throw(RuntimeError("no browser here")))
    monkeypatch.setattr(S, "voi_stt", lambda: (_ for _ in ()).throw(RuntimeError("no browser here")))
    return boards


def test_rate_limit_waits_as_asked_and_pages_pause(monkeypatch):
    from app.pipeline import sources as S
    S.reset()
    slept: list[float] = []
    monkeypatch.setattr(S, "_sleep", slept.append)
    answers = [_429("7"), _429(""), {"rows": [{"row": {"a": 1}}] * 2, "num_rows_total": 4},
               {"rows": [{"row": {"a": 2}}] * 2, "num_rows_total": 4}]

    def fake(url, timeout=40.0):
        a = answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a
    monkeypatch.setattr(S, "_get", fake)
    rows = S.config_rows("agent", page=2)
    assert len(rows) == 4
    assert slept[0] == 7.0 and slept[1] == 10.0 and S.PAGE_PAUSE in slept    # Retry-After, then 5*2^1, then the page pause


def test_rate_limit_gives_up_after_its_tries(monkeypatch):
    from app.pipeline import sources as S
    S.reset()
    monkeypatch.setattr(S, "_sleep", lambda s: None)
    monkeypatch.setattr(S, "_get", lambda url, timeout=40.0: (_ for _ in ()).throw(_429("1")))
    with pytest.raises(httpx.HTTPStatusError):
        S.config_rows("agent")


def test_same_dataset_commit_reads_no_board(pl, monkeypatch):
    from app.pipeline import feed, sources as S
    first = feed.run()["doc"]
    assert first["complete"] and first["tables"]["chat"]["n"] >= 10
    monkeypatch.setattr(S, "config_rows", lambda c, **k: (_ for _ in ()).throw(AssertionError("read again")))
    d = feed.run()["doc"]
    assert d["complete"] and d["tables"]["chat"]["n"] == first["tables"]["chat"]["n"]
    assert not [w for w in d["warnings"] if "board" in w]


def test_a_board_never_read_marks_the_run_incomplete_and_the_worker_tries_again_soon(pl, monkeypatch):
    from app import worker
    from app.pipeline import feed, sources as S, store
    monkeypatch.setattr(S, "config_rows", lambda c, **k: (_ for _ in ()).throw(_429("1")))
    d = feed.run()["doc"]
    assert d["complete"] is False and "text/overall" in d["missing_boards"]
    assert store.read_current()["complete"] is False
    calls = []
    monkeypatch.setattr(feed, "run", lambda: calls.append(1))
    monkeypatch.setenv("PIPELINE_FEED", "true")
    monkeypatch.setenv("PIPELINE_RETRY_MIN", "0")
    from app.config import get_settings
    get_settings.cache_clear()
    worker._pl_last = 0.0
    asyncio.run(worker.pipeline_jobs())
    assert calls == [1]                                    # not 24 h later: the retry window (0 min here)
    monkeypatch.setenv("PIPELINE_RETRY_MIN", "60")
    get_settings.cache_clear()
    worker._pl_last = 0.0
    asyncio.run(worker.pipeline_jobs())
    assert calls == [1]                                    # inside the hour: waits


def test_one_run_at_a_time(pl):
    from app.pipeline import feed, store
    with store.lock():
        r = feed.run()
    assert r["busy"] and r["doc"] is None
    assert feed.run()["doc"]["complete"]
