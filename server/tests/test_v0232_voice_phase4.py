"""v0.234.0 VOICE PHASE 4 (built as 0.231.0): call quality you can measure - scorecards saved per call (survive restarts), a grade per
call, roll-ups per version, the ear test / phone checklist marks."""
import json
import time
from pathlib import Path

import pytest

from app import callquality as cq


@pytest.fixture()
def qdir(tmp_path, monkeypatch):
    monkeypatch.setattr(cq, "DIR", tmp_path / "voice_calls")
    monkeypatch.setattr(cq, "EAR_DIR", tmp_path / "voice_eartest")
    monkeypatch.setattr(cq, "_ratings", lambda tenant: {})
    return tmp_path


def _stats(cid, tenant="t1", lat=(800, 900), end="hung_up", **kw):
    now = time.time()
    s = {"tenant": tenant, "call_id": cid, "started": now - 120, "ended": now, "turns": 4, "latency_ms": list(lat),
         "words": [5, 7], "interruptions": 1, "tools": 2, "silent_tools": 0, "gate": {"chunks": 10, "opens": 1},
         "end": end, "lang": "hi", "secret_text": "OTP 123456", "turns_log": [("a", "b")]}
    s.update(kw)
    return s


def test_record_keeps_numbers_only_and_survives(qdir):
    cq.record(_stats("c1", goaway=2, goaway_graceful=2))
    rows = cq.load("t1")
    assert len(rows) == 1 and rows[0]["call_id"] == "c1"
    raw = (qdir / "voice_calls" / "t1.jsonl").read_text()
    assert "123456" not in raw and "turns_log" not in raw and "secret_text" not in raw   # never words
    assert rows[0]["goaway_graceful"] == 2 and rows[0]["end"] == "hung_up" and rows[0]["seconds"] > 100


def test_keep_last_300(qdir, monkeypatch):
    monkeypatch.setattr(cq, "KEEP", 5)
    for i in range(8):
        cq.record(_stats(f"c{i}"))
    ids = [r["call_id"] for r in cq.load("t1")]
    assert ids == ["c3", "c4", "c5", "c6", "c7"]


def test_tenants_kept_apart_and_live_merged(qdir):
    cq.record(_stats("c1", tenant="t1"))
    cq.record(_stats("c2", tenant="t2"))
    live = [_stats("c3", tenant="t1"), _stats("c1", tenant="t1"), _stats("cx", tenant="t2")]
    ids = [c["call_id"] for c in cq.calls("t1", live)]
    assert sorted(ids) == ["c1", "c3"]   # c1 not doubled, t2 not leaked


def test_grade_rules():
    assert cq.grade(cq.compact(_stats("a")))["grade"] == "good"
    g = cq.grade(cq.compact(_stats("b", end="error")))
    assert g["grade"] == "bad" and any("tooti" in p for p in g["problems"])
    g = cq.grade(cq.compact(_stats("c", lat=[3000, 3200, 2900])))
    assert g["grade"] == "bad" and any("der se" in p for p in g["problems"])
    g = cq.grade(cq.compact(_stats("d", goaway_forced=1)))
    assert g["grade"] == "ok"
    g = cq.grade({**cq.compact(_stats("e")), "rating": False})
    assert g["grade"] == "bad"
    g = cq.grade(cq.compact(_stats("f", stall_reconnects=1)))
    assert g["grade"] == "bad"


def test_quality_rollup_and_versions(qdir):
    cq.record(_stats("c1", goaway=2, goaway_graceful=1, goaway_forced=1, news_merged=2, gap_audio_kept_s=1.5))
    cq.record(_stats("c2", end="stall", lat=[4000]))
    q = cq.quality("t1", 30)
    o = q["overall"]
    assert o["calls"] == 2 and o["broken_calls"] == 1 and o["goaway_graceful_pct"] == 50.0
    assert o["news_merged"] == 2 and o["gap_audio_kept_s"] == 1.5
    assert o["grades"]["bad"] == 1 and o["ends"] == {"hung_up": 1, "stall": 1}
    assert q["recent"][0]["call_id"] == "c2" and q["recent"][0]["grade"] == "bad"
    assert q["say"] and "2 calls" in q["say"]
    assert q["targets"]["reply_start_ms_p50"] == cq.LAT_GOOD_MS


def test_quality_drops_old_calls(qdir):
    cq.record(_stats("old", started=time.time() - 40 * 86400, ended=time.time() - 40 * 86400 + 60))
    cq.record(_stats("new"))
    assert [c["call_id"] for c in cq.quality("t1", 30)["recent"]] == ["new"]
    assert cq.quality("t1", 90)["overall"]["calls"] == 2


def test_ratings_join(qdir, monkeypatch):
    cq.record(_stats("c1"))
    monkeypatch.setattr(cq, "_ratings", lambda tenant: {"c1": False})
    r = cq.quality("t1")["recent"][0]
    assert r["rating"] is False and r["grade"] == "bad"


def test_eartest_marks_per_version(qdir):
    e = cq.eartest("t1", "9.9.9")
    assert e["total"] == len(cq.EAR_TESTS) >= 15 and e["done"] == 0
    assert {t["kind"] for t in cq.EAR_TESTS} == {"ear", "phone"}
    e = cq.eartest_mark("t1", "hello_speed", "pass", version="9.9.9")
    e = cq.eartest_mark("t1", "interrupt", "fail", "beech mein nahi ruka", version="9.9.9")
    assert e["passed"] == 1 and e["failed"] == 1 and e["done"] == 2
    it = {x["id"]: x for x in e["items"]}
    assert it["interrupt"]["note"] == "beech mein nahi ruka" and it["hello_speed"]["result"] == "pass"
    assert cq.eartest("t1", "10.0.0")["done"] == 0          # a new version starts fresh
    e = cq.eartest_mark("t1", "interrupt", "clear", version="9.9.9")
    assert e["done"] == 1
    assert cq.eartest_summary("t1")[0]["version"] == "9.9.9"
    with pytest.raises(KeyError):
        cq.eartest_mark("t1", "nope", "pass")
    with pytest.raises(ValueError):
        cq.eartest_mark("t1", "interrupt", "maybe")


def test_end_reason_wired_in_voice():
    src = (Path(__file__).parents[1] / "app" / "voice.py").read_text()
    assert 'self.stats["end"] = getattr(self, "_end_reason", "") or ("hung_up" if self._hung_up else "dropped")' in src
    for r in ('"stall"', '"error"', '"server_restart"', '"hold_timeout"'):
        assert f'getattr(self, "_end_reason", "") or {r}' in src or f'getattr(call, "_end_reason", "") or {r}' in src
    assert "callquality.record, self.stats" in src


def test_api_endpoints(env, qdir, monkeypatch):
    monkeypatch.setenv("API_KEY", "owner-key-phase4")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import app, APP_VERSION
    h = {"Authorization": "Bearer owner-key-phase4"}
    with TestClient(app) as c:
        r = c.get("/api/voice/quality", headers=h)
        assert r.status_code == 200 and "overall" in r.json() and r.json()["version"] == APP_VERSION
        r = c.get("/api/voice/stats", headers=h)
        assert r.status_code == 200 and "quality" in r.json()
        r = c.get("/api/voice/eartest", headers=h)
        assert r.status_code == 200 and r.json()["version"] == APP_VERSION
        r = c.post("/api/voice/eartest/song", json={"result": "pass"}, headers=h)
        assert r.status_code == 200 and r.json()["passed"] == 1
        assert c.post("/api/voice/eartest/xx", json={"result": "pass"}, headers=h).status_code == 404
        assert c.post("/api/voice/eartest/song", json={"result": "x"}, headers=h).status_code == 400


def test_phone_screen_wired():
    root = Path(__file__).parents[2]
    scr = (root / "lib" / "ui" / "call_quality_screen.dart").read_text()
    assert "voiceQuality" in scr and "voiceEarMark" in scr
    assert "CallQualityScreen" in (root / "lib" / "ui" / "profile_screen.dart").read_text()
    api = (root / "lib" / "api.dart").read_text()
    assert "/api/voice/quality" in api and "/api/voice/eartest/$id" in api


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.280.0"
