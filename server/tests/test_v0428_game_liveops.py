"""v0.428 LIVE OPS (Hoola Game Engine plan Phase 9): A/B tests measured (sample-size target, split check, z-test, no
early winner), live events with no clashes, live values only within 1/4x - 4x of the Game Bible, the live config the game
reads from its own host, crash groups from consenting players + hotfix tasks, D30 / balance / difficulty spikes, the money
report from HER imported CSV, and in the real Godot: the same A/B group sum as the server, live values + events applied,
script errors caught by the Logger, a patch check that replays saved runs on the newest version."""
import asyncio
import base64
import json
import random
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


def _game(st):
    from app.gamedesk import service as G
    return G._get("default", st["gid"])


def _day(n: int, hm: str) -> str:
    return f"{(date.today() + timedelta(days=n)).isoformat()} {hm}"


TWO = [{"name": "control", "weight": 50, "set": {}}, {"name": "b", "weight": 50, "set": {"player.hp": 150}}]


# ================================================================ the maths
def test_stats_match_textbook_numbers():
    from app.gamedesk import liveops as L
    # 30% -> 35% at alpha 0.05 / power 0.8 needs ~1,374 per group (normal approximation, unpooled)
    assert 1350 <= L.sample_size(0.30, 0.05) <= 1400
    assert L.sample_size(0.30, 0.10) < L.sample_size(0.30, 0.05)
    z, p = L.z_test(300, 1000, 360, 1000)
    assert 2.8 < z < 2.9 and 0.003 < p < 0.006
    assert L.z_test(0, 0, 1, 1) == (0.0, 1.0)
    assert L.srm_p([500, 500], [0.5, 0.5]) > 0.9 and L.srm_p([700, 300], [0.5, 0.5]) < 1e-6


def test_assignment_is_stable_and_follows_the_split():
    from app.gamedesk import liveops as L
    vs = [{"name": "control", "bp": 2000}, {"name": "b", "bp": 8000}]
    rng = random.Random(1)
    ids = ["%016x" % rng.getrandbits(64) for _ in range(4000)]
    got = [L.assign(i, "t", vs) for i in ids]
    assert got == [L.assign(i, "t", vs) for i in ids]                         # same player, same group
    share = got.count("b") / len(got)
    assert 0.77 < share < 0.83
    assert L.assign("", "t", vs) == "control"


# ================================================================ A/B tests
def test_live_values_only_change_bible_numbers_within_range(st):  # noqa: F811
    from app.gamedesk import liveops as L
    with pytest.raises(L.LiveOpsError, match="Bible"):
        L.add_experiment("default", st["sid"], "x1", goal="win", variants=[TWO[0], {"name": "b", "set": {"enemy.boss.hp": 9}}])
    with pytest.raises(L.LiveOpsError, match="1/4x"):
        L.add_experiment("default", st["sid"], "x2", variants=[TWO[0], {"name": "b", "set": {"player.hp": 1000}}])
    with pytest.raises(L.LiveOpsError, match="flag"):
        L.add_experiment("default", st["sid"], "x3", variants=[TWO[0], {"name": "b", "set": {"flag.x": 3}}])
    with pytest.raises(L.LiveOpsError, match="alag"):
        L.add_experiment("default", st["sid"], "x4", variants=[TWO[0], {"name": "b", "set": {}}])
    with pytest.raises(L.LiveOpsError, match="100%"):
        L.add_experiment("default", st["sid"], "x5", variants=[{**TWO[0], "weight": 30}, {**TWO[1], "weight": 30}])
    x = L.add_experiment("default", st["sid"], "hp_test", "More health", "win", TWO)
    assert x["status"] == "draft" and [v["bp"] for v in x["variants"]] == [5000, 5000]
    assert L.live_config(_game(st).token)["experiments"] == []                  # a draft never reaches players


def test_experiment_needs_telemetry_then_no_early_winner_then_a_measured_one(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    L.add_experiment("default", st["sid"], "hp_test", "More health", "win", TWO, mde=0.10)
    with pytest.raises(L.LiveOpsError, match="Telemetry"):
        L.start_experiment("default", st["sid"], "hp_test")
    R.set_runtime("default", st["sid"], telemetry=True)
    assert L.start_experiment("default", st["sid"], "hp_test")["status"] == "running"
    cfg = L.live_config(_game(st).token)
    assert cfg["experiments"][0]["key"] == "hp_test" and cfg["experiments"][0]["variants"][1]["set"] == {"player.hp": 150}
    # the same value cannot be tested twice at once
    L.add_experiment("default", st["sid"], "hp_two", "", "win", [TWO[0], {"name": "b", "set": {"player.hp": 120}}])
    with pytest.raises(L.LiveOpsError, match="pehle se"):
        L.start_experiment("default", st["sid"], "hp_two")

    vs = cfg["experiments"][0]["variants"]
    rng = random.Random(4)
    R.ensure_table()
    today = date.today().isoformat()

    def add(n, rate_c, rate_b):
        with session() as s:
            for _ in range(n):
                inst = "%016x" % rng.getrandbits(64)
                grp = L.assign(inst, "hp_test", vs)
                ab = f"hp_test={grp}"
                s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="session_start", day=today, ab=ab))
                if rng.random() < (rate_b if grp == "b" else rate_c):
                    s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="win", day=today, ab=ab))
    add(200, 0.30, 0.45)
    r = L.results("default", st["sid"], "hp_test")
    assert r["verdict"] == "NOT ENOUGH PLAYERS" and "stopping early" in r["note"]   # a big gap, but too few players
    assert 300 < r["need_per_group"] < 450
    add(1000, 0.30, 0.45)
    r = L.results("default", st["sid"], "hp_test")
    assert r["verdict"] == "B WINS" and r["groups"][1]["vs_control_pts"] > 8, r
    out = L.stop_experiment("default", st["sid"], "hp_test", ship="b")
    assert out["status"] == "ended" and out["task"]
    t = next(x for x in st["S"].get("default", st["sid"])["tasks"] if x["number"] == out["task"])
    assert "player.hp = 150" in t["title"] and t["status"] == "todo"           # shipping = a board task for her OK


def test_a_broken_split_is_named(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    R.set_runtime("default", st["sid"], telemetry=True)
    L.add_experiment("default", st["sid"], "split", "", "win", TWO)
    L.start_experiment("default", st["sid"], "split")
    R.ensure_table()
    with session() as s:
        for i in range(600):
            s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=f"{i:016x}", event="session_start",
                                  day=date.today().isoformat(), ab="split=" + ("control" if i < 450 else "b")))
    r = L.results("default", st["sid"], "split")
    assert r["verdict"] == "SPLIT BROKEN" and r["srm_p"] < 0.001


# ================================================================ live events
def test_events_calendar_her_tap_and_no_clashes(st):  # noqa: F811
    from app.gamedesk import liveops as L
    t = time.time()
    with pytest.raises(L.LiveOpsError, match="End"):
        L.add_event("default", st["sid"], "bad", "Bad", t + 100, t + 50, {"flag.x": True})
    with pytest.raises(L.LiveOpsError, match="31"):
        L.add_event("default", st["sid"], "long", "Long", t, t + 40 * 86400, {"flag.x": True})
    with pytest.raises(L.LiveOpsError, match="badalta"):
        L.add_event("default", st["sid"], "empty", "Empty", t, t + 3600, {})
    ev = L.add_event("default", st["sid"], "diwali_2026", "Diwali", _day(60, "18:00"), _day(62, "18:00"),
                     {"flag.double_coins": True, "player.speed": 450})
    assert ev["status"] == "draft" and ev["starts_ist"] == _day(60, "18:00")
    from datetime import datetime
    assert ev["starts"] == datetime.fromisoformat(_day(60, "18:00")).replace(tzinfo=L.IST).timestamp()          # India time when no zone is written
    assert L.live_config(_game(st).token)["events"] == []
    L.approve_event("default", st["sid"], "diwali_2026")
    cfg = L.live_config(_game(st).token)
    assert cfg["events"][0]["set"] == {"flag.double_coins": True, "player.speed": 450}
    L.add_event("default", st["sid"], "speedy", "Speed week", _day(61, "10:00"), _day(64, "10:00"), {"player.speed": 500})
    with pytest.raises(L.LiveOpsError, match="ek samay"):
        L.approve_event("default", st["sid"], "speedy")
    now_ev = L.add_event("default", st["sid"], "now_ev", "Now", t - 60, t + 3600, {"flag.party": True})
    L.approve_event("default", st["sid"], now_ev["key"])
    assert next(e for e in L.view("default", st["sid"])["events"] if e["key"] == "now_ev")["state"] == "live"
    L.cancel_event("default", st["sid"], "now_ev")
    assert all(e["key"] != "now_ev" for e in L.live_config(_game(st).token)["events"])
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    r = c.get(f"/play/{_game(st).token}/live")
    assert r.status_code == 200 and r.json()["events"][0]["key"] == "diwali_2026" and "max-age" in r.headers["cache-control"]
    assert c.get("/play/" + "Q" * 24 + "/live").json() == {}


# ================================================================ crashes + hotfix
def test_crashes_grouped_scrubbed_only_with_consent_and_hotfix(st):  # noqa: F811
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    g = _game(st)
    err = {"file": "res://main.gd", "line": 42, "msg": "Invalid call 'boom' for player meghana@example.com score 1234567"}
    body = lambda inst, **k: json.dumps({"install": inst, "consent": True, "version": 2, "events": [{"e": "session_start", "f": 1}],  # noqa: E731
                                         "errors": [err], **k}).encode()
    R.ingest(g.token, body("a1b2c3d4e5f60718"))
    assert L.crashes("default", st["sid"])["groups"] == []                        # her switch is off: nothing kept
    R.set_runtime("default", st["sid"], telemetry=True)
    R.ingest(g.token, body("a1b2c3d4e5f60718"))
    R.ingest(g.token, body("0011223344556677"))
    R.ingest(g.token, body("8899aabbccddeeff", consent=False))
    cr = L.crashes("default", st["sid"])
    assert len(cr["groups"]) == 1
    c0 = cr["groups"][0]
    assert c0["players"] == 2 and c0["count"] == 2 and c0["where"] == "res://main.gd:42" and c0["versions"] == [2]
    assert "example.com" not in c0["msg"] and "1234567" not in c0["msg"] and "<email>" in c0["msg"]
    assert cr["crash_free"][-1]["crash_free"] == 0.0
    h = L.hotfix("default", st["sid"], c0["sig"])
    t = next(x for x in st["S"].get("default", st["sid"])["tasks"] if x["number"] == h["task"])
    assert t["kind"] == "fix" and t["priority"] == 1 and "res://main.gd:42" in t["title"]
    with pytest.raises(L.LiveOpsError, match="pehle se"):
        L.hotfix("default", st["sid"], c0["sig"])
    assert L.crashes("default", st["sid"])["groups"][0]["state"] == "fixing"


# ================================================================ dashboard + money
def test_dashboard_d30_balance_and_difficulty_spike(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    R.ensure_table()
    today = date.today()
    with session() as s:
        for i in range(40):
            inst = f"{i:016x}"
            first = today - timedelta(days=31)
            s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="session_start", day=first.isoformat()))
            if i < 10:
                s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="session_start",
                                      day=(first + timedelta(days=30)).isoformat()))
            s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="score", value=str(100 + i % 7 if i < 36 else 5000),
                                  day=today.isoformat()))
            s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="game_over",
                                  value=str(3 if i < 24 else (1, 2, 4, 5)[i % 4]), day=today.isoformat()))
    d = L.dashboard("default", st["sid"])
    assert d["d30"] == {"share": 0.25, "cohort": 40}
    sc = next(b for b in d["balance"] if b["event"] == "score")
    assert sc["outliers"] == 4 and sc["flag"] is True
    assert d["stuck_levels"][0]["level"] == "3"
    assert len(d["dau"]) == 14 and d["dau"][today.isoformat()] == 40


def test_money_only_from_her_csv(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    m = L.money("default", st["sid"])
    assert m["revenue_30d_inr"] == 0 and m["arpdau_inr"] is None and any("does not see your store" in n for n in m["notes"])
    with pytest.raises(L.LiveOpsError, match="Date"):
        L.import_revenue("default", st["sid"], "kal, 100")
    R.ensure_table()
    d1 = date.today() - timedelta(days=1)
    with session() as s:
        for i in range(10):
            s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=f"{i:016x}", event="session_start", day=d1.isoformat()))
        s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=f"{0:016x}", event="purchase", day=d1.isoformat()))
    out = L.import_revenue("default", st["sid"], f"date,amount,source\n{d1.isoformat()},\"₹1,000\",play\n{d1.strftime('%d-%m-%Y')},500,itch\n")
    assert out["imported"] == 2 and out["revenue_30d_inr"] == 1500 and out["arpdau_inr"] == 150.0
    assert out["by_source"] == {"play": 1000.0, "itch": 500.0} and out["payer_share"] == 0.1
    assert any("UPPER bound" in n for n in out["notes"])
    out = L.import_revenue("default", st["sid"], f"{d1.isoformat()},1200,play\n")       # the same day + source replaced
    assert out["revenue_30d_inr"] == 1700


# ================================================================ API, tool, UI
def test_api_tool_and_screens(st, monkeypatch):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    from app.main import app
    from app.employee import hire
    monkeypatch.setattr(L, "_POOL", type("X", (), {"submit": staticmethod(lambda *a, **k: None)})())
    hire.hire("default", "game_dev")
    c = TestClient(app)
    base = f"/api/gamedesk/liveops/{st['sid']}"
    assert c.get(base).json()["paths"]
    assert c.post(base + "/experiments", json={"key": "x", "variants": TWO}).status_code == 400         # name too short
    r = c.post(base + "/experiments", json={"key": "hp_test", "variants": TWO})
    assert r.status_code == 200, r.text
    assert c.post(base + "/experiments/hp_test/start").status_code == 400                               # telemetry off
    R.set_runtime("default", st["sid"], telemetry=True)
    assert c.post(base + "/experiments/hp_test/start").json()["status"] == "running"
    assert c.get(base + "/experiments/hp_test").json()["verdict"] == "NOT ENOUGH PLAYERS"
    assert c.post(base + "/events", json={"key": "ev_one", "title": "E", "starts": _day(30, "10:00"), "ends": _day(31, "10:00"),
                                          "set": {"flag.fest": True}}).status_code == 200
    assert c.post(base + "/events/ev_one/approve").json()["status"] == "scheduled"
    for part in ("/dashboard", "/crashes", "/money"):
        assert c.get(base + part).status_code == 200
    assert c.post(base + "/money", json={"csv": "2026-01-01,10"}).json()["imported"] == 1
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_liveops"](ctx, action="status"))
    assert out["experiments"][0]["status"] == "running" and out["events"][0]["key"] == "ev_one"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_liveops"](staff, action="event_approve", key="ev_one"))
    assert tools.FAMILY_OF["game_liveops"] == "gamedesk"
    for ask in ("mere game ka a/b test chalao", "game mein diwali ka live event", "game crash ka hotfix"):
        assert "gamedesk" in admit.route(ask), ask
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsLiveops" in emp and "liveops: gsLiveops" in emp and "Make hotfix task" in emp
    assert "class GameLiveopsScreen" in (root / "lib/ui/game_roles_screen.dart").read_text()
    assert "GameLiveopsScreen(" in (root / "lib/ui/game_studio_screen.dart").read_text()
    from app.gamedesk import ai
    assert "HoolaRuntime.num(" in ai.GUIDE and "loot boxes" in ai.GUIDE


def test_runtime_carries_the_live_url_and_passes_the_guard(st):  # noqa: F811
    from app.gamedesk import guard, packs
    got = packs.for_game("default", st["gid"])
    txt = got["hoola_runtime.gd"][0]
    assert "/live" in txt and "func num(" in txt and "class HoolaLog extends Logger" in txt and "OS.add_logger" in txt
    assert guard.problems({"main.gd": "extends Node\n", "hoola_runtime.gd": txt}) == []


# ================================================================ the real engine
def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


LIVE_GAME = '''extends Node
var x = null
func _physics_process(_d: float) -> void:
	if Engine.get_physics_frames() == 20:
		HoolaProbe.state("hp", HoolaRuntime.num("player.hp", 100.0))
		HoolaProbe.state("speed", HoolaRuntime.num("player.speed", 300.0))
		HoolaProbe.state("double", HoolaRuntime.flag("double_coins"))
		HoolaProbe.state("events", HoolaRuntime.active_events())
	if Engine.get_physics_frames() == 40:
		x.boom()
'''


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_groups_live_values_and_caught_errors(tmp_path):
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.gd").write_text(LIVE_GAME)
    R.prepare(tmp_path / "src", tmp_path / "job", "T", "portrait")
    vs = [{"name": "control", "bp": 5000, "set": {}}, {"name": "b", "bp": 5000, "set": {"player.hp": 150}}]
    live = {"now": 2000, "experiments": [{"key": "hp_test", "variants": vs}],
            "events": [{"key": "e", "title": "Diwali", "starts": 1000, "ends": 3000, "set": {"flag.double_coins": True, "player.speed": 450}},
                       {"key": "old", "title": "Old", "starts": 10, "ends": 20, "set": {"player.speed": 1}}]}
    arg = "--hoola-live=" + base64.b64encode(json.dumps(live).encode()).decode()
    seen = set()
    for inst in ("00000001", "abcdef12", "deadbeef99", "0123456789abcdef"):
        r = R._run_mode(tmp_path / "job", "--hoola-bot=3,90", 90, [arg, "--hoola-install=" + inst])
        want = L.assign(inst, "hp_test", vs)
        seen.add(want)
        assert r["ab"] == {"hp_test": want}, (inst, r)                         # the engine's sum == the server's
        assert r["state"]["hp"] == (150 if want == "b" else 100)
        assert r["state"]["speed"] == 450 and r["state"]["double"] is True and r["state"]["events"] == ["Diwali"]
        assert r["logged"] == 1 and r["log"][0]["file"] == "res://main.gd" and r["log"][0]["line"] == 10   # once, not per frame
    assert seen == {"control", "b"}


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_patch_check(st, monkeypatch):  # noqa: F811
    from app.gamedesk import liveops as L
    from app.gamedesk import runtime as R
    first = L.patch_check("default", st["sid"])
    assert any("NOT ASSESSED" in c["note"] for c in first["checks"])           # no saved replay yet - said, not passed silently
    R.replay_test("default", st["sid"], frames=300)
    out = L.patch_check("default", st["sid"])
    rp = [c for c in out["checks"] if c["check"].startswith("saved replay")]
    assert rp and all(c["ok"] for c in rp), out
    assert out["verdict"] == "PASS" and L.view("default", st["sid"])["patches"][-1]["version"] == out["version"]
