"""v0.330 DEPLOY SE NAHI RUKEGA (owner's screenshot: S-0003 "Server ruk gaya tha, kaam beech mein ruk gaya"). The server
log showed clean shutdowns, not a crash: 5 deploys in under 2 hours, and a long build that lived through two of them was
marked failed because a dead job gets only ONE automatic restart (a guard against crash loops). Now the app's shutdown
marks every running website job as stopped on purpose, so after a deploy it continues from its saved sections however
many deploys land; a real crash (no shutdown) still uses up the one restart; a site map that was being made starts again."""
import threading
from datetime import datetime, timezone

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _make(S, **fields):
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S._save(v["id"], **fields)
    return v["id"]


def _age(S, sid):
    from app.db import session
    from app.site.models import Site
    with session() as s:
        s.get(Site, sid).updated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)   # before this process started


def _record(S, monkeypatch):
    calls = []
    monkeypatch.setattr(S, "_start", lambda sid, job, **kw: calls.append((sid, job, kw)) or True)
    return calls


def test_a_deploy_never_fails_a_running_build(site_env, monkeypatch):
    from app.site import service as S
    sid = _make(S, status="building", stage="build", recovered=1, look={"tokens": {"bg": "#fff"}})   # restarted once (1st deploy)
    gate = threading.Event()
    th = threading.Thread(target=gate.wait, daemon=True)
    th.start()
    S._RUNNING[sid] = th                                                  # its thread is running in this process
    try:
        assert S.mark_clean_stop() == 1                                   # the 2nd deploy: shutdown marks it
    finally:
        gate.set()
        th.join()
        S._RUNNING.pop(sid, None)
    assert S._load(sid).recovered == 0
    _age(S, sid)
    calls = _record(S, monkeypatch)
    S.recover_stuck()                                                     # the new process boots
    assert calls == [(sid, "build", {})]
    r = S._load(sid)
    assert r.status == "building" and r.recovered == 1 and not r.error


def test_a_real_crash_still_stops_after_one_restart(site_env, monkeypatch):
    from app.site import service as S
    sid = _make(S, status="building", stage="build", recovered=1)        # restarted once, then died WITHOUT a shutdown
    _age(S, sid)
    calls = _record(S, monkeypatch)
    S.recover_stuck()
    r = S._load(sid)
    assert calls == [] and r.status == "failed" and "Phir se chalao" in r.error


def test_a_site_map_job_starts_again_after_a_restart(site_env, monkeypatch):
    from app.site import service as S
    sid = _make(S)
    calls = _record(S, monkeypatch)
    S._sitemap_begin(S._load(sid), 60, "har mithai ka page")
    assert calls[-1] == (sid, "sitemap", {"want": 60, "words": "har mithai ka page"})
    _age(S, sid)
    calls.clear()
    S.recover_stuck()
    assert calls == [(sid, "sitemap", {"want": 60, "words": "har mithai ka page"})]
    assert S._load(sid).stage == "sitemap" and not S._load(sid).error
    _age(S, sid)                                                          # dies again without a shutdown: give up, say so
    calls.clear()
    S.recover_stuck()
    assert calls == [] and S._load(sid).stage == "plan" and "phir se kahiye" in S._load(sid).error


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.334.0"
    assert "0.334.0+374" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
