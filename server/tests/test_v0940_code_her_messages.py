"""v0.940 HOOLA CODE HER MESSAGES (owner, her phone screenshot of a Hoola Code session: "New session 1st msg sent by user
seen in chat screen .. thereafter any msg send by user not seen in chat screen").

ROOT CAUSE: the phone draws her first message from the session's text and every later one from a 'note' step - but a
follow-up after a finished round (`service.revise`, the phone's bg/revise) never wrote that step, so nothing of hers
showed after the first message. Only an answer to Hoola's question and a note taken while it worked were written."""
from pathlib import Path

import pytest

from tests.test_tech_devsahayak import FIX_ANSWER, T, dev  # noqa: F401
from tests.test_v0352_pehle_ci import _run, cidev  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _no_plan_pass(dev, monkeypatch):  # noqa: F811
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "dev_plan_first", False, raising=False)


def test_her_follow_up_on_a_pr_is_her_message_in_the_thread(cidev, monkeypatch):  # noqa: F811
    S = cidev
    v = S.start(T, "fix", "Checkout crash ho raha hai")
    _run(S.FAKE, S.FAKE.prs[1]["head"]["sha"], "success")
    S._ci_step(T, v["id"])
    assert S.get_task(T, v["id"])["status"] == "pr_open"
    monkeypatch.setattr(S, "model_json", lambda *a, **k: FIX_ANSWER)
    S.revise(T, v["id"], "Also guard the empty cart please")
    notes = [s for s in S.get_task(T, v["id"])["steps"] if s.get("k") == "note"]
    assert notes and notes[-1]["text"] == "Also guard the empty cart please" and notes[-1]["her"] is True
    # comments alone still show as one line of hers, never the raw comment block
    S.revise(T, v["id"], "", comments=[{"path": "app/calc.py", "line": 5, "code": "return s", "text": "guard it"}])
    notes = [s for s in S.get_task(T, v["id"])["steps"] if s.get("k") == "note"]
    assert notes[-1]["text"] == "Comments on 1 line of the change"


def test_every_door_writes_her_words():
    svc = (ROOT / "server/app/devsahayak/service.py").read_text()
    rev = svc[svc.index("def revise("):svc.index("def fix_ci(")]
    assert rev.count('_Step(cont).event({"k": "note", "text": said, "her": True})') == 1     # the session continues
    assert rev.count('_Step(t.id).event({"k": "note", "text": said, "her": True})') == 1     # a change on the PR
    eng = (ROOT / "server/app/devsahayak/engine.py").read_text()
    assert 'emit({"k": "note", "text": n[:6000], "her": True})' in eng                        # a note read while working


def test_the_phone_shows_her_messages_at_once_and_full_size():
    ses = (ROOT / "lib/ui/code/code_session.dart").read_text()
    assert "small: true, key: 'note" not in ses                    # her later messages look like her first one
    assert "_herWaiting(c, _sent!, 'Sending…')" in ses               # shown the moment she sends
    assert "_herWaiting(c, n, 'Hoola reads it at its next step')" in ses   # a note queued while it works is her bubble
    assert "Queued for its next step:" not in ses
    send = ses[ses.index("Future<void> _send("):ses.index("Future<void> _askMerge(")]
    assert "_sent = text;" in send and "_msg.text = text" in send     # a failed send puts her words back


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.151"' in main
    assert "version: 0.999.151+1146" in (ROOT / "pubspec.yaml").read_text()
