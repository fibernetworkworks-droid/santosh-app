"""v0.56 Share-to-Hoola / video shrink / keep-alive: the server half (phone health check + per-family checklist)."""
import time

from fastapi.testclient import TestClient


def _now():
    return int(time.time() * 1000)


def test_classify_exits():
    from app import keepalive as k
    assert k.classify_exit({"reason": k.R_OTHER, "importance": 400, "desc": ""}) == "oem_kill"
    assert k.classify_exit({"reason": k.R_SIGNALED, "importance": 300}) == "oem_kill"
    assert k.classify_exit({"reason": k.R_OTHER, "importance": 100}) == "normal"         # the screen in use
    assert k.classify_exit({"reason": k.R_USER_REQUESTED, "desc": "remove task"}) == "recents_clear"
    assert k.classify_exit({"reason": k.R_OTHER, "importance": 400, "desc": "OneKeyClean"}) == "recents_clear"
    assert k.classify_exit({"reason": k.R_USER_REQUESTED, "desc": "force stop"}) == "user"
    assert k.classify_exit({"reason": k.R_CRASH}) == "crash"
    assert k.classify_exit({"reason": k.R_PACKAGE_UPDATED}) == "update"
    assert k.classify_exit({"reason": k.R_LOW_MEMORY}) == "low_memory"
    assert k.classify_exit({"reason": k.R_EXCESSIVE, "importance": 100}) == "oem_kill"


def test_health_problems_and_checklist_for_xiaomi():
    from app import keepalive as k
    n = _now()
    rep = {"brand": "Redmi", "battery_optimized": True, "notifications": True, "standby_bucket": 40,
           "exits": [{"ts": n - 3600_000, "reason": k.R_OTHER, "importance": 400},
                     {"ts": n - 7200_000, "reason": k.R_SIGNALED, "importance": 300},
                     {"ts": n - 9 * 86400_000, "reason": k.R_OTHER, "importance": 400},       # older than a week
                     {"ts": n - 60_000, "reason": k.R_PACKAGE_UPDATED}]}
    h = k.health(rep, n)
    codes = [p["code"] for p in h["problems"]]
    assert h["family"] == "xiaomi" and h["strict"] and not h["ok"]
    assert "battery_optimized" in codes and "oem_kills" in codes
    assert h["counts"]["oem_kill"] == 2 and h["last_kill"] == n - 3600_000
    assert "2 baar" in next(p["title"] for p in h["problems"] if p["code"] == "oem_kills")
    ids = [c["id"] for c in h["checklist"]]
    assert ids[:2] == ["autostart", "battery"] and "perms" in ids and ids[-1] == "notifications"
    assert {c["action"] for c in h["checklist"]} <= {"autostart", "battery", "maker_battery", "maker_perms", "notifications", "recents"}


def test_health_ok_phone_and_families():
    from app import keepalive as k
    h = k.health({"brand": "google", "battery_optimized": True, "exits": []})
    assert h["ok"] and h["family"] == "generic"          # Pixels don't kill: no battery nag without kills
    assert k.family("realme") == "oppo" and k.family("iQOO") == "vivo" and k.family("POCO") == "xiaomi"
    assert k.family("OnePlus") == "oneplus" and k.family("samsung") == "samsung" and k.family("Infinix") == "tecno"
    h = k.health({"brand": "vivo", "background_restricted": True, "notifications": False, "standby_bucket": 45})
    codes = [p["code"] for p in h["problems"]]
    assert codes[:2] == ["notifications_off", "bg_restricted"] and "standby_restricted" in codes
    assert any("High background power" in c["title"] for c in h["checklist"])


def test_endpoint_saves_and_tool_explains(env, tmp_path, monkeypatch):
    import asyncio
    from app import keepalive as k
    from app.main import app
    monkeypatch.setattr(k, "HEALTH_DIR", tmp_path / "h")
    c = TestClient(app)
    n = _now()
    r = c.post("/api/device/bg_health", json={"brand": "oppo", "model": "CPH2491", "sdk": 34, "battery_optimized": True,
                                             "exits": [{"ts": n - 1000, "reason": k.R_OTHER, "importance": 400, "desc": ""}]})
    assert r.status_code == 200, r.text
    assert r.json()["family"] == "oppo" and not r.json()["ok"]
    last = c.get("/api/device/bg_health").json()
    assert last["brand"] == "oppo" and last["counts"]["oem_kill"] == 1
    from app.agent.tools import HANDLERS, Ctx, TOOLS
    assert any(t["name"] == "phone_health" for t in TOOLS)
    out = asyncio.run(HANDLERS["phone_health"](Ctx(tenant_id="default", conversation_id="c")))
    assert out["known"] and out["stopped_by_phone_7d"] == 1 and "CPH2491" in out["phone"]
    from app.voice import VOICE_TOOL_NAMES
    assert "phone_health" in VOICE_TOOL_NAMES


def test_keepalive_get_carries_checklist(env, tmp_path, monkeypatch):
    import httpx
    from app import keepalive as k
    from app.main import app
    monkeypatch.setattr(k, "CACHE", tmp_path)
    monkeypatch.setattr(k, "_transport", httpx.MockTransport(lambda req: httpx.Response(404)))
    r = TestClient(app).get("/api/device/keepalive", params={"brand": "xiaomi"}).json()
    assert r["family"] == "xiaomi" and r["checklist"][0]["id"] == "autostart"
