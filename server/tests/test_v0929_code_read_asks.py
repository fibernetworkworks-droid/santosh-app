"""v0.929 (her first Qwen session, read from the deploy log: "read all fnw ai node project first properly" became a WRITE job
that planned, searched for something to change and ended "Koi file badalne layak nahi mili"; its card was lost to a
"database is locked"): reading asks are explanations, a locked card publish is tried again, and vps-ops `codelog` reads the
last Hoola Code sessions."""
from pathlib import Path

from app.devsahayak import service as S

ROOT = Path(__file__).resolve().parents[2]


def test_reading_asks_are_explanations():
    for t in ("read all fnw ai node project first properly", "Go through the repo and tell me how auth works",
              "pura project padho aur samjhao", "review the whole project", "explain the router"):
        assert S.guess_kind(t) == "explain", t
    for t, k in (("read the code and add a login page", "write"), ("Add a dark mode switch", "write"),
                 ("fix the crash in login", "fix"), ("write tests for utils", "tests")):
        assert S.guess_kind(t) == k, t


def test_a_locked_card_publish_is_tried_again(monkeypatch):
    from app import events
    calls = []

    def pub(conv, kind, payload):
        calls.append(kind)
        if len(calls) == 1:
            raise RuntimeError("(sqlite3.OperationalError) database is locked")
    monkeypatch.setattr(events.bus, "publish", pub)
    monkeypatch.setattr("time.sleep", lambda s: None)
    S._publish("t1", "devsahayak_task", {"task": {}}, "conv_1")
    assert calls == ["devsahayak_task", "devsahayak_task"]


def test_codelog_job():
    wf = (ROOT / ".github/workflows/vps-ops.yml").read_text()
    assert "          - codelog\n" in wf and "server/tools/codelog.py 6 santosh.db" in wf
    src = (ROOT / "server/tools/codelog.py").read_text()
    assert "mode=ro" in src                          # reads only


def test_version():
    main = (ROOT / "server/app/main.py").read_text()
    assert 'APP_VERSION = "0.999.50"' in main
    assert "version: 0.999.50+1048" in (ROOT / "pubspec.yaml").read_text()
