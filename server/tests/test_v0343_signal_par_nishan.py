"""v0.343 SIGNAL PAR NISHAN: the 1 Nov deploy log ended its shutdown with "Aborted!" - the server waits for long-lived
connections (live chat streams, PC links) and is force-stopped, so v0.332's mark at the END of shutdown never ran and a
deploy could still fail a running website build. The app now wraps the stop signals at startup: the running website
jobs are marked the moment SIGINT / SIGTERM arrives, then the previous handler (uvicorn's) runs exactly as before."""
import os
import signal


def test_a_stop_signal_marks_running_jobs_first_then_hands_over(monkeypatch):
    from app import main
    from app.site import service as S
    seen = []
    old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        signal.signal(signal.SIGTERM, lambda signum, frame: seen.append(("uvicorn", signum)))
        signal.signal(signal.SIGINT, lambda signum, frame: seen.append(("uvicorn", signum)))
        monkeypatch.setattr(S, "mark_clean_stop", lambda: seen.append(("marked", 0)) or 1)
        assert main._mark_jobs_on_stop_signal() == 2
        assert main._mark_jobs_on_stop_signal() == 0                      # never wrapped twice
        os.kill(os.getpid(), signal.SIGTERM)
        assert seen == [("marked", 0), ("uvicorn", signal.SIGTERM)]     # marked FIRST, then the old handler
        seen.clear()
        os.kill(os.getpid(), signal.SIGINT)
        assert seen == [("marked", 0), ("uvicorn", signal.SIGINT)]
        # a failing mark never blocks the shutdown
        monkeypatch.setattr(S, "mark_clean_stop", lambda: (_ for _ in ()).throw(RuntimeError("db gone")))
        seen.clear()
        os.kill(os.getpid(), signal.SIGTERM)
        assert seen == [("uvicorn", signal.SIGTERM)]
    finally:
        for s, h in old.items():
            signal.signal(s, h)


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.802.0"
    assert "0.802.0+801" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
