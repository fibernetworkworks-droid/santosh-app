"""v0.999.335 HOOLA DOD, NEVER STUCK QUIETLY (owner, after the kwant read: "Stuck bots say so instead of stopping
quietly ... work on it").

A failed round is tried again (with a growing wait) before the task fails; the coworker's rules say: retry a failed
step, then another way, never a way she said no to, and end with a 'Blocked:' line when nothing works. A 'Blocked:'
line becomes a question to her (her answer goes back to it). A reply that stops before the work is done gets up to 2
more turns, then one "Keep going?" card: Keep going, or Stop here (the work so far stays). A fake OpenClaw stands in.
"""
import json

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0999_306_dod import BASE, _call, _sse, _wait, dod  # noqa: F401


def _resp(n, out, status="completed", error=None):
    resp = {"id": f"resp_{n}", "status": status, "output": out}
    if error:
        resp["error"] = {"message": error}
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          content=_sse([{"type": "response.completed", "response": resp}]))


def _text(t):
    return [{"type": "message", "content": [{"type": "output_text", "text": t}]}]


class Script:
    """A fake Gateway that answers each round from a script: a callable (body, n) -> Response."""

    def __init__(self, step):
        self.step, self.bodies, self.n = step, [], 0

    def __call__(self, req: httpx.Request):
        if req.url.host == "openrouter.ai":
            if req.method == "POST":
                return httpx.Response(201, json={"key": "sk-or-user-1", "data": {"hash": "h1"}})
            return httpx.Response(200, json={"data": {"usage": 0.5, "limit": 10}})
        if req.url.path == "/readyz":
            return httpx.Response(200, json={"ready": True})
        body = json.loads(req.content)
        self.bodies.append(body)
        self.n += 1
        return self.step(body, self.n)


def said(body):
    return " ".join(str(i.get("content") or i.get("output") or "") for i in body["input"])


@pytest.fixture
def run(dod, monkeypatch):
    GW, S, docker = dod
    monkeypatch.setenv("DOD_ENGINE", "true")
    monkeypatch.setenv("OPENROUTER_PROVISIONING_KEY", "prov-key")
    monkeypatch.setenv("DOD_RETRY_S", "0")
    monkeypatch.setenv("DOD_REVIEW", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        def go(step, ask="Find the cheapest train to Pune"):
            claw = Script(step)
            monkeypatch.setattr(GW, "TRANSPORT", httpx.MockTransport(claw))
            c.put("/api/dod/profile", json={"name": "Ananya", "look": "f002"})
            tid = c.post("/api/dod/tasks", json={"ask": ask}).json()["task"]["id"]
            return c, tid, claw
        yield go


def test_how_a_reply_ends():
    from app.dod.service import ending
    assert ending("I tried the login twice.\nBlocked: the site wants her Aadhaar OTP") == ("blocked", "the site wants her Aadhaar OTP")
    assert ending("**Blocked:** no train data on the site")[0] == "blocked"
    assert ending("Done: the 06:15 train is cheapest at INR 420")[0] == "done"
    assert ending("I will open the booking page next.")[0] == "stopped"
    assert ending("")[0] == "stopped"
    from app.dod import service as S
    rules = S.instructions("Ananya", "task")
    assert "try it again once, then try another way" in rules and "never tried again" in rules and "'Blocked:'" in rules


def test_a_failed_round_is_tried_again(run):
    def step(body, n):
        if n <= 2:
            return _resp(n, [], status="failed", error="provider overloaded")
        return _resp(n, [_call("hoola_done", {"summary": "Done: 06:15, INR 420."}, "f1")])
    c, tid, claw = run(step)
    t = _wait(c, tid, "done")
    assert [s["title"] for s in t["steps"]].count("Something went wrong, trying again") == 2
    assert claw.n == 3 and all(b["input"] == claw.bodies[0]["input"] for b in claw.bodies), "the same round, sent again"


def test_it_fails_only_after_its_retries_and_says_why(run):
    c, tid, claw = run(lambda body, n: _resp(n, [], status="failed", error="the model refused"))
    t = _wait(c, tid, "failed")
    assert claw.n == 3 and "could not get past: the model refused" in t["error"]


def test_a_lost_connection_is_tried_again(run, monkeypatch):
    def step(body, n):
        if n == 1:
            raise httpx.ConnectError("connection reset")
        return _resp(n, [_call("hoola_done", {"summary": "Done: found it."}, "f1")])
    c, tid, claw = run(step)
    t = _wait(c, tid, "done")
    assert "Lost contact for a moment, trying again" in [s["title"] for s in t["steps"]]


def test_blocked_line_asks_her_and_her_answer_goes_back(run):
    def step(body, n):
        if n == 1:
            return _resp(n, _text("I tried the login twice and another way.\nBlocked: the site wants a one-time code sent to her phone"))
        if "answered your Blocked line: Use the email login instead" in said(body):
            return _resp(n, [_call("hoola_done", {"summary": "Done: signed in by email, the 06:15 is INR 420."}, "f1")])
        return _resp(n, _text("Blocked: still stuck"))
    c, tid, claw = run(step)
    t = _wait(c, tid, "needs_you")
    q = t["question"]
    assert q["kind"] == "blocked" and q["question"] == "the site wants a one-time code sent to her phone"
    assert "Blocked" in [s["title"] for s in t["steps"]]
    assert c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": ""}).status_code == 409
    c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "Use the email login instead"})
    t = _wait(c, tid, "done")
    assert t["reply"].startswith("Done: signed in by email")
    sent = claw.bodies[1]["input"][0]
    assert sent["type"] == "message" and sent["role"] == "user", "no tool call to answer: her words go back as a message"


def test_a_done_that_says_blocked_is_not_done(run):
    def step(body, n):
        if n == 1:
            return _resp(n, [_call("hoola_done", {"summary": "Could not finish.\nBlocked: the payment page needs her card"}, "f1")])
        return _resp(n, [_call("hoola_done", {"summary": "Done: booked."}, "f2")])
    c, tid, claw = run(step)
    t = _wait(c, tid, "needs_you")
    q = t["question"]
    assert q["kind"] == "blocked" and q["call_id"] == "f1" and "card" in q["question"]
    c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "Skip paying, just hold the seat"})
    _wait(c, tid, "done")
    back = claw.bodies[1]["input"][0]
    assert back == {"type": "function_call_output", "call_id": "f1", "output": back["output"]} and "hold the seat" in back["output"]


def test_stopping_halfway_gets_two_more_turns_then_keep_going(run):
    def step(body, n):
        if "keep going until the task is fully done" in said(body):
            return _resp(n, [_call("hoola_done", {"summary": "Done: the 06:15 is INR 420."}, "f1")])
        return _resp(n, _text("I will open the IRCTC page next."))
    c, tid, claw = run(step)
    t = _wait(c, tid, "needs_you")
    assert claw.n == 3, "the first stop + 2 more turns, then it asks her"
    assert [s["title"] for s in t["steps"]].count("Stopped before the end, asked to go on") == 2
    q = t["question"]
    assert q["kind"] == "keep_going" and q["options"] == ["Keep going", "Stop here"] and "IRCTC" in q["details"]
    assert "stopped before the work was done" in q["question"]
    assert c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "maybe"}).status_code == 409
    c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "Keep going"})
    t = _wait(c, tid, "done")
    assert t["reply"].startswith("Done:")


def test_stop_here_keeps_the_work_so_far(run):
    c, tid, claw = run(lambda body, n: _resp(n, _text("I found 3 trains so far; I will compare them next.")))
    q = _wait(c, tid, "needs_you")["question"]
    c.post(f"/api/dod/tasks/{tid}/answer", json={"id": q["id"], "hash": q["hash"], "choice": "Stop here"})
    t = _wait(c, tid, "stopped")
    assert "3 trains" in t["reply"] and "You stopped it here" in [s["title"] for s in t["steps"]]
    n = claw.n
    import time
    time.sleep(0.3)
    assert claw.n == n, "nothing more runs after Stop here"


def test_the_notification_and_the_page_say_it():
    from app import push
    assert push.render("dod_ask", {"name": "Ananya", "kind": "blocked", "question": "needs her OTP"}) == ("Ananya is blocked", "needs her OTP")
    assert push.render("dod_ask", {"name": "Ananya", "kind": "keep_going", "question": "x"})[0] == "Ananya stopped halfway"
    js = (BASE / "dod.js").read_text()
    for s in ("q.kind === 'blocked'", "q.kind === 'keep_going'", "data-answer=\"Keep going\"", "data-answer=\"Stop here\"",
              "keep_going: 'Stopped halfway'", "Stopped. The work so far stays."):
        assert s in js, s
