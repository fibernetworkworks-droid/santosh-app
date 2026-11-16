"""v0.962 HOOLA CODE LIVE (built as 0.961; their HOOLA PIPELINE P1 took 0.961, both kept; owner, after the Claude Code comparison: "GO BUILD 1 2 3").
1. The words Hoola writes are PUSHED to her phone as they come (GET /api/devsahayak/tasks/{id}/stream, every 100 ms
   what changed) - the phone asked once a second, so words arrived in 1 s bursts; Claude Code streams them live.
2. A reply shows from its 4th word (was 10); one that starts like a recent message waits until a repeat can be told.
3. Hoola's words between steps are never cut (the 2-3 sentence cut stopped them mid-thought); the model keeps them short."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_live_delta_sends_only_what_changed():
    from app.devsahayak import service as S
    a = {"live": "I will read", "now": "Reading the code", "n": 4, "running": True}
    assert S.live_delta(a, dict(a)) == {}
    assert S.live_delta(a, {**a, "live": "I will read the file"}) == {"add": " the file"}
    assert S.live_delta(a, {**a, "live": "A new reply"}) == {"live": "A new reply"}
    assert S.live_delta(a, {**a, "live": ""}) == {"live": ""}                       # saved as a step: the live copy goes
    assert S.live_delta(a, {**a, "n": 5, "now": "Running the tests"}) == {"n": 5, "now": "Running the tests"}
    assert S.live_delta(a, {**a, "running": False}) == {"running": False}


def test_live_state_reads_memory_only_and_steps_are_counted():
    from app.devsahayak import engine as EN
    from app.devsahayak import service as S
    EN.LIVE_TEXT["t9"] = "Found it."
    S._RUNNING.add("t9")
    S.STEP_N["t9"] = 12
    try:
        st = S.live_state("t9")
        assert st["live"] == "Found it." and st["n"] == 12 and st["running"] is True
    finally:
        S._RUNNING.discard("t9"), EN.LIVE_TEXT.pop("t9", None), S.STEP_N.pop("t9", None)
    assert S.live_state("t9") == {"live": "", "now": "", "n": -1, "running": False}
    src = (ROOT / "server/app/devsahayak/service.py").read_text()
    assert "STEP_N[self.tid] = int(last_n) + 1" in src


def test_stream_route_refuses_a_session_that_is_not_hers(env):
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/api/devsahayak/tasks/nope/stream")
    assert r.status_code == 404
    api = (ROOT / "server/app/devsahayak/api.py").read_text()
    assert '@r.get("/tasks/{tid}/stream")' in api and "await asyncio.sleep(0.1)" in api and "text/event-stream" in api


def test_words_show_from_the_fourth_and_are_never_cut():
    from app.devsahayak import engine as EN
    EN.LIVE_TEXT.clear()
    EN.live_sink("a", "Reading the", [])
    assert "a" not in EN.LIVE_TEXT
    EN.live_sink("a", "Reading the login handler", [])
    assert EN.LIVE_TEXT["a"] == "Reading the login handler"
    long = " ".join(f"Sentence {i} says one more thing about the change." for i in range(8))
    EN.live_sink("a", long, [])
    assert EN.LIVE_TEXT["a"] == long                                      # five sentences and more: whole
    recent = ["The token check is missing in the refresh path of the handler."]
    EN.live_sink("b", "The token check is", recent)
    assert "b" not in EN.LIVE_TEXT                                        # starts like a recent message: waits
    EN.live_sink("b", recent[0], recent)
    assert "b" not in EN.LIVE_TEXT                                        # and the repeat is never shown
    src = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert "txt = short_say(txt)" not in src and "nothing is cut" in src


def test_the_phone_reads_the_stream():
    api = (ROOT / "lib/api.dart").read_text()
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "Stream<SantoshEvent> codeStream(String task)" in api and "/stream')" in api
    assert "api.codeStream(widget.id).listen(" in ses and "void _onLive(" in ses
    assert "if (_streaming) t = {...t, 'live': _streamLive};" in ses             # a late check never puts older words back
    assert "_streaming && DateTime.now().difference(_loadedAt) < const Duration(seconds: 5)" in ses
    assert "_unlisten();" in ses and "_listen();" in ses
