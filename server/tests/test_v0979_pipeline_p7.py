"""v0.979 HOOLA PIPELINE P7 - the watch: every chat message timed (first word + whole reply), the Box vs today's
routing (a held-out share), the outage record written down, and the week's verdict. Fake models only, no network."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import time

_spec = importlib.util.spec_from_file_location(
    "_p4", pathlib.Path(__file__).with_name("test_v0969_pipeline_p4.py"))
_p4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_p4)
box = _p4.box
ROOT = pathlib.Path(__file__).resolve().parents[2]
BANNED = 'OpenRouter error 403: {"error":{"message":"Model a/mid1 is banned","code":403}}'


def _turn(monkeypatch, conv, words="Namaste!", ask="hi", tenant="t"):
    """A real santosh.run_turn whose inner turn streams one delta and then sends the reply."""
    from app.agent import santosh
    from app.events import bus

    async def fake(c, text, *a, **k):
        bus.publish(c, "message", {"role": "assistant", "text": "Ek second...", "ack": True}, ephemeral=True)
        await asyncio.sleep(0.02)
        bus.publish_live(c, "delta", {"turn": 1, "seg": 0, "seq": 1, "text": words.split()[0]})
        await asyncio.sleep(0.02)
        bus.publish(c, "message", {"role": "assistant", "text": words, "source": "agent"})
        return words

    monkeypatch.setattr(santosh, "_run_turn", fake)
    return asyncio.run(santosh.run_turn(conv, ask, tenant))


def _rows():
    from app.pipeline import watch as W
    return W.rows(days=7)[0]


def test_a_box_message_is_timed_with_its_first_word(box, monkeypatch):
    _turn(monkeypatch, "w1")
    r = [x for x in _rows() if x["conv"] == "w1"][-1]
    assert r["grp"] == "box" and r["model"] == "a/mid1" and r["level"] == "MID" and r["kind"] == "chat"
    assert r["ok"] == 1 and r["first_s"] is not None and 0.015 <= r["first_s"] <= r["total_s"]
    assert r["first_s"] >= 0.015          # the ack line ("Ek second") is not her first word


def test_box_off_is_timed_as_before(box, monkeypatch):
    monkeypatch.setenv("PIPELINE_ON", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    _turn(monkeypatch, "w2")
    r = [x for x in _rows() if x["conv"] == "w2"][-1]
    assert r["grp"] == "before" and r["model"] == "" and r["why"] == "pipeline_on off"


def test_the_held_out_share_runs_todays_way_and_is_the_comparison(box, monkeypatch):
    from app.agent import llm, santosh
    from app.config import get_settings
    monkeypatch.setenv("PIPELINE_HOLDOUT_PCT", "100")
    get_settings.cache_clear()
    seen = {}
    from app.events import bus
    got = []
    real = bus.publish

    def pub(conv, kind, payload, *a, **k):
        if kind == "model_receipt":
            got.append(payload)
        return real(conv, kind, payload, *a, **k)
    monkeypatch.setattr(bus, "publish", pub)

    async def fake(c, text, *a, **k):
        seen["model"] = llm.MODEL_NOW.get()
        bus.publish(c, "message", {"role": "assistant", "text": "ok", "source": "agent"})
        return "ok"
    monkeypatch.setattr(santosh, "_run_turn", fake)
    asyncio.run(santosh.run_turn("w3", "hi", "t"))
    assert seen["model"] == ""                     # today's model, not the Box's
    r = [x for x in _rows() if x["conv"] == "w3"][-1]
    assert r["grp"] == "before" and r["why"] == "held out"
    assert not got                                 # no receipt line: the Box did not run it
    from app.pipeline import sheet as S
    assert S.recent(conv="w3")[0]["parts"][0]["not_applied"].startswith("held out for the P7 watch")


def test_several_parts_and_calls_and_other_actors(box, monkeypatch):
    from app.pipeline import watch as W
    assert W.start("w4", voice=True) is None       # a live call is not a chat message
    assert W.start("w4", actor="team") is None     # a background / team turn is not hers
    rec = W.start("w4", actor="approved:x")
    W.place(rec, {"sheet": {"multi": True, "parts": [{"kind": "research", "applied": True},
                                                     {"kind": "write", "applied": True, "model": {"id": "a/x"}}]}})
    assert rec["grp"] == "box_multi" and rec["multi"] == 2


def test_errors_and_failed_turns(box, monkeypatch):
    from app.pipeline import watch as W
    rec = W.start("w5")
    W.place(rec, None)
    assert rec["grp"] == "skipped"
    W.heard("w5", "message", {"role": "assistant", "text": "Something went wrong", "source": "error"})
    W.heard("w5", "delta", {"text": "   "})
    assert rec["first"] is None                    # an error line and an empty delta are not words she waited for
    W.stop(rec, ok=False)
    r = [x for x in _rows() if x["conv"] == "w5"][-1]
    assert r["ok"] == 0 and r["first_s"] is None


def test_the_outage_record_is_written_down(box):
    import asyncio as _a
    from app.pipeline import runner as R, turnbox as T, watch as W
    b = box.begin("w6", "t1", "hi")
    _a.run(R.call(R.HAND.get(), _p4._maker({"a/mid1": _p4.boom(BANNED), "b/mid2": _p4.ok()}, [])))
    box.end(b, "ok")
    T.note("c/mid3", False)
    T.note("c/mid3", False)
    _, out = W.rows(days=7)
    ev = {(o["model"], o["event"]) for o in out}
    assert ("a/mid1", "dead") in ev and ("a/mid1", "handover") in ev and ("c/mid3", "fail") in ev
    rep = W.report()
    assert rep["models"]["c/mid3"]["fails"] == 2 and rep["models"]["c/mid3"]["pauses"] == 1
    assert "banned" in rep["models"]["a/mid1"]["dead"]


def _fill(W, grp, n, first, total, now, ok=True, kind="chat", spread_days=8):
    for i in range(n):
        t0 = now - spread_days * 86400 + i * (spread_days * 86400 / n)
        rec = {"conv": f"{grp}{i}", "tenant": "t", "t0": t0, "first": first, "grp": grp, "multi": 0, "kind": kind,
               "level": "MID", "model": "a/mid1" if grp == "box" else "", "why": "", "sheet": None}
        W.stop(rec, ok=ok, now=t0 + total)


def test_the_verdict_waits_then_passes(box):
    from app.pipeline import watch as W
    now = time.time()
    _fill(W, "box", 5, 1.0, 3.0, now, spread_days=2)
    v = W.report(now=now)["verdict"]
    assert v["state"] == "watching" and not v["ready"]
    assert any("days watched" in w for w in v["waiting"]) and any("Box messages" in w for w in v["waiting"])
    _fill(W, "box", 40, 1.05, 3.1, now)
    _fill(W, "before", 40, 1.0, 3.0, now)
    r = W.report(days=9, now=now)
    assert r["verdict"]["state"] == "ready" and r["verdict"]["ready"], r["verdict"]
    assert r["groups"]["box"]["n"] == 45 and r["by_kind"]["chat"]["box"]["n"] == 45


def test_the_verdict_names_what_is_slower(box):
    from app.pipeline import watch as W
    now = time.time()
    _fill(W, "box", 40, 2.5, 6.0, now)
    _fill(W, "before", 40, 1.0, 5.8, now)
    v = W.report(days=9, now=now)["verdict"]
    assert v["state"] == "slower"
    assert any(s.startswith("first word (median) 2.5 s vs 1.0 s") for s in v["slower"])
    assert not any(s.startswith("whole reply") for s in v["slower"])     # 6.0 vs 5.8 is inside the 10 % + 0.3 s


def test_more_failures_is_not_ready(box):
    from app.pipeline import watch as W
    now = time.time()
    _fill(W, "box", 30, 1.0, 3.0, now, ok=False)
    _fill(W, "box", 30, 1.0, 3.0, now)
    _fill(W, "before", 40, 1.0, 3.0, now)
    v = W.report(days=9, now=now)["verdict"]
    assert v["state"] == "slower" and any(s.startswith("failed 50.0 %") for s in v["slower"])


def test_watch_route_and_cli(box, capsys):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.pipeline import watch as W
    j = TestClient(app).get("/api/pipeline/watch").json()
    assert j["on"] is True and j["verdict"]["state"] in ("watching", "ready", "slower") and "groups" in j
    assert W.main() == 0
    assert "the P7 watch" in capsys.readouterr().out


def test_switch_off_writes_nothing(box, monkeypatch):
    monkeypatch.setenv("PIPELINE_WATCH", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.pipeline import watch as W
    assert W.start("w9") is None and W.hold_out() is False
    W.outage("a/x", "fail")
    assert W.rows(days=7) == ([], [])


def test_wiring_and_version():
    s = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "_wtch.start(" in s and "_wtch.place(_wt, _bx)" in s and "_wtch.stop(_wt" in s
    e = (ROOT / "server/app/events.py").read_text()
    assert e.count("_heard(conversation_id, kind, payload)") == 2
    y = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "pipeline_watch)" in y and "app.pipeline.watch" in y
    assert (ROOT / "server/app/main.py").read_text().count('APP_VERSION = "0.999.70"') == 1
