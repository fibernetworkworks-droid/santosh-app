"""v0.427 (built as 0.425) HOOLA RUNTIME + ASK HOOLA IN THE EDITOR (Hoola Game Engine plan Phase 8): HoolaRuntime (replay recorder,
in-engine bot, opt-in telemetry) inside every Studio build; replay tests in the real Godot (a deterministic game passes,
a randomize() game is caught with its cause); telemetry only with her switch + the player's yes, never for children,
no personal data; a real MCP server (/mcp/gamedesk, JSON-RPC 2.0) behind hashed editor tokens; the Godot editor plugin
loaded by the real Godot editor."""
import asyncio
import io
import json
import os
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


def _game(st):
    from app.gamedesk import service as G
    return G._get("default", st["gid"])


# ================================================================ the runtime file + settings
def test_runtime_goes_into_builds_and_only_it_may_use_the_network(st):  # noqa: F811
    from app.gamedesk import guard, packs, service, template
    from app.gamedesk import runtime as R
    got = packs.for_game("default", st["gid"])
    txt = got["hoola_runtime.gd"][0]
    assert '"telemetry": false' in txt and "func _bot_step()" in txt and "--hoola-replay=" in txt
    assert guard.problems({"main.gd": "extends Node\n", "hoola_runtime.gd": txt}) == []
    bad = guard.problems({"main.gd": "extends Node\nvar h := HTTPRequest.new()\n"})
    assert any("network" in b for b in bad)                                           # her game's code still may not
    files = {"main.gd": "extends Node\n", "hoola_runtime.gd": "extends Node\nvar h := HTTPRequest.new() # the model's own"}
    service._own_packs(files, got)
    assert files["hoola_runtime.gd"] == txt                                           # the model's version is replaced
    assert 'HoolaRuntime="*res://hoola_runtime.gd"' in template.files("t", "portrait", {"main.gd": "", "hoola_runtime.gd": txt})["project.godot"]
    R.set_runtime("default", st["sid"], on=False)
    assert "hoola_runtime.gd" not in packs.for_game("default", st["gid"])
    R.set_runtime("default", st["sid"], on=True, telemetry=True)
    txt = packs.for_game("default", st["gid"])["hoola_runtime.gd"][0]
    g = _game(st)
    assert '"telemetry": true' in txt and f'/play/{g.token}/t' in txt


def test_no_telemetry_for_a_childrens_game(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import packs
    from app.gamedesk import runtime as R
    from app.gamedesk import service as G
    R.set_runtime("default", st["sid"], telemetry=True)
    with session() as s:
        s.get(G.GameProject, st["gid"]).design = "# A counting game for kids aged 5"
    with pytest.raises(R.RuntimeError_, match="bachchon"):
        R.set_runtime("default", st["sid"], telemetry=True)
    assert '"telemetry": false' in packs.for_game("default", st["gid"])["hoola_runtime.gd"][0]
    assert R.settings("default", st["sid"])["kids"] is True


# ================================================================ telemetry ingest + dashboard
def test_ingest_only_with_her_switch_consent_and_clean_data(st):  # noqa: F811
    from app.gamedesk import runtime as R
    g = _game(st)
    body = lambda **k: json.dumps({"install": "a1b2c3d4e5f60718", "consent": True, "version": 2,   # noqa: E731
                                   "events": [{"e": "session_start", "f": 1}, {"e": "game_over", "f": 900}], **k}).encode()
    assert R.ingest(g.token, body()) == 0                                              # her switch is off
    R.set_runtime("default", st["sid"], telemetry=True)
    assert R.ingest(g.token, body()) == 2
    assert R.ingest(g.token, body(consent=False)) == 0                                 # no yes, nothing kept
    assert R.ingest(g.token, body(install="Robert'); DROP")) == 0
    assert R.ingest(g.token, body(events=[{"e": "Has Spaces!"}, {"e": "ok_event"}])) == 1
    assert R.ingest(g.token, b"x" * (R.MAX_BODY + 1)) == 0
    assert R.ingest("A" * 24, body()) == 0                                             # an unknown game
    d = R.dashboard("default", st["sid"])
    assert d["installs"] == 1 and d["events"] == 3 and d["funnel"][0] == {"step": "session_start", "players": 1}
    assert d["d1"]["share"] is None and "no player" in d["d1"]["note"]
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    assert c.post(f"/play/{g.token}/t", content=body()).status_code == 204
    assert c.post("/play/" + "Z" * 24 + "/t", content=b"junk").status_code == 204    # never tells a stranger anything
    assert R.delete_telemetry("default", st["sid"])["deleted"] >= 3
    assert R.dashboard("default", st["sid"])["installs"] == 0


def test_retention_from_install_cohorts(st):  # noqa: F811
    from app.db import session
    from app.gamedesk import runtime as R
    today = date.today()
    R.ensure_table()
    with session() as s:
        for inst, days in (("aaaaaaaa1", [9, 8, 2]), ("bbbbbbbb2", [9]), ("cccccccc3", [3, 2]), ("dddddddd4", [1])):
            for d in days:
                s.add(R.GameTelemetry(tenant_id="default", game_id=st["gid"], install=inst, event="session_start",
                                      day=(today - timedelta(days=d)).isoformat()))
    d = R.dashboard("default", st["sid"])
    assert d["installs"] == 4
    assert d["d1"] == {"share": round(2 / 4, 3), "cohort": 4}                          # a + c came back the next day
    assert d["d7"] == {"share": round(1 / 2, 3), "cohort": 2}                          # a came back on day 7 (of a, b)


# ================================================================ MCP + editor tokens
def _rpc(c, tok, method, params=None, rid=1):
    msg = {"jsonrpc": "2.0", "method": method}
    if rid is not None:
        msg["id"] = rid
    if params is not None:
        msg["params"] = params
    return c.post("/mcp/gamedesk", json=msg, headers={"Authorization": f"Bearer {tok}"} if tok else {})


def test_mcp_server_end_to_end(st, monkeypatch):  # noqa: F811
    from app.db import session
    from app.employee import hire
    from app.gamedesk import ai
    from app.gamedesk import editor as E
    from app.main import app
    hire.hire("default", "game_dev")
    c = TestClient(app)
    assert c.post("/api/gamedesk/editor/tokens", json={"label": "laptop"}).status_code == 200
    made = E.create_token("default", "desk pc")
    tok = made["token"]
    with session() as s:
        rows = s.query(E.EditorToken).all()
        assert all(tok not in (r.hash + r.hint + r.label) for r in rows) and any(r.hash == E._h(tok) for r in rows)
    assert _rpc(c, "", "ping").status_code == 401 and _rpc(c, "hoola_ed_wrong", "ping").status_code == 401
    r = _rpc(c, tok, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}).json()
    assert r["result"]["protocolVersion"] == "2025-06-18" and r["result"]["capabilities"]["tools"] is not None
    assert _rpc(c, tok, "notifications/initialized", rid=None).status_code == 202
    tools = _rpc(c, tok, "tools/list").json()["result"]["tools"]
    assert {t["name"] for t in tools} == {"hoola_projects", "hoola_tasks", "hoola_bible", "hoola_bugs", "hoola_ask", "hoola_add_task"}
    pj = json.loads(_rpc(c, tok, "tools/call", {"name": "hoola_projects", "arguments": {}}).json()["result"]["content"][0]["text"])
    assert pj[0]["id"] == "S-0001" and pj[0]["live_version"] == 1
    seen = {}
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=0: seen.update(p=prompt) or "Change speed in player.gd line 3.")
    out = _rpc(c, tok, "tools/call", {"name": "hoola_ask", "arguments": {"question": "why is my rickshaw slow?",
                                                                         "script": "var speed = 10", "script_name": "res://player.gd"}}).json()
    assert out["result"]["content"][0]["text"] == "Change speed in player.gd line 3." and not out["result"]["isError"]
    assert "var speed = 10" in seen["p"] and "Design doc" in seen["p"] and "Live code" in seen["p"]
    add = json.loads(_rpc(c, tok, "tools/call", {"name": "hoola_add_task", "arguments": {"title": "Make the rickshaw faster"}}).json()["result"]["content"][0]["text"])
    assert add["added"]
    tasks = json.loads(_rpc(c, tok, "tools/call", {"name": "hoola_tasks", "arguments": {}}).json()["result"]["content"][0]["text"])
    assert any(t["title"] == "Make the rickshaw faster" for t in tasks)
    assert _rpc(c, tok, "tools/call", {"name": "delete_everything", "arguments": {}}).json()["error"]["code"] == -32602
    assert _rpc(c, tok, "resources/list").json()["error"]["code"] == -32601
    err = _rpc(c, tok, "tools/call", {"name": "hoola_ask", "arguments": {"question": ""}}).json()
    assert err["result"]["isError"]
    batch = c.post("/mcp/gamedesk", json=[{"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"jsonrpc": "2.0", "method": "notifications/x"},
                                          {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}], headers={"Authorization": f"Bearer {tok}"}).json()
    assert [m["id"] for m in batch] == [1, 2]
    assert c.get("/mcp/gamedesk").status_code == 405
    lst = c.get("/api/gamedesk/editor/tokens").json()
    assert lst["mcp_url"].endswith("/mcp/gamedesk") and all("token" not in t for t in lst["tokens"])
    E.revoke("default", made["id"])
    assert _rpc(c, tok, "ping").status_code == 401


def test_plugin_zip_and_tool(st):  # noqa: F811
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.gamedesk import editor as E
    from app.main import app
    z = zipfile.ZipFile(io.BytesIO(E.plugin_zip("https://hoola.example.in/")))
    assert set(z.namelist()) == {"addons/hoola/plugin.cfg", "addons/hoola/plugin.gd", "addons/hoola/dock.gd", "addons/hoola/README.txt"}
    dock = z.read("addons/hoola/dock.gd").decode()
    assert "https://hoola.example.in" in dock and "/mcp/gamedesk" in dock and "EditorSettings" not in dock.split("\n")[0]
    assert "get_editor_settings" in dock and "token.secret = true" in dock
    hire.hire("default", "game_dev")
    c = TestClient(app)
    r = c.get("/api/gamedesk/editor/plugin.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_runtime"](ctx, action="status"))
    assert out["on"] is True and out["telemetry"] is False
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_runtime"](staff, action="set", telemetry=True))
    assert tools.FAMILY_OF["game_runtime"] == "gamedesk"
    for ask in ("mere game ka replay test chalao", "godot editor mein hoola plugin"):
        assert "gamedesk" in admit.route(ask), ask
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsRuntime" in emp and "/api/gamedesk/editor/plugin.zip" in emp and "mcpServers" in emp
    assert "class GameRuntimeScreen" in (root / "lib/ui/game_roles_screen.dart").read_text()
    from app.gamedesk import ai
    assert "HoolaRuntime" in ai.GUIDE and "NEVER call randomize()" in ai.GUIDE


# ================================================================ the REAL engine
def _godot() -> bool:
    from app.gamedesk import engine
    return bool(engine.find())


GAME = '''extends Node
var p: ColorRect
var score := 0
var enemies: Array = []
func _ready() -> void:
__RANDOMIZE__	p = ColorRect.new()
	p.size = Vector2(32, 32)
	p.position = Vector2(300, 600)
	add_child(p)
	for i in 5:
		var e := ColorRect.new()
		e.position = Vector2(randf() * 600, randf() * 300)
		add_child(e)
		enemies.append(e)
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		p.position.x = event.position.x
		score += 1
		HoolaProbe.state("score", score)
func _physics_process(delta: float) -> void:
	var d := 0.0
	if Input.is_key_pressed(KEY_LEFT): d -= 1
	if Input.is_key_pressed(KEY_RIGHT): d += 1
	p.position.x = clamp(p.position.x + d * 300 * delta, 0, 680)
	for e in enemies:
		e.position.y += 60 * delta + randf() * 2.0
'''


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_replay_test(tmp_path):
    from app.gamedesk import runtime as R
    for name, rnd in (("good", ""), ("rand", "\trandomize()\n")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "main.gd").write_text(GAME.replace("__RANDOMIZE__", rnd))
    good = R.replay_lab(tmp_path / "good", tmp_path / "j1", "T", "portrait", seed=7, frames=600)
    assert good["verdict"] == "PASS" and good["deterministic"] and good["inputs"] > 20, good
    assert good["causes"] == []
    bad = R.replay_lab(tmp_path / "rand", tmp_path / "j2", "T", "portrait", seed=7, frames=600)
    assert bad["verdict"] == "FAIL" and bad["deterministic"] is False and "randomize(" in bad["causes"]


@pytest.mark.skipif(not _godot(), reason="Godot is not installed here")
def test_real_godot_editor_loads_the_plugin(tmp_path):
    from app.gamedesk import editor as E
    r = E.editor_check(tmp_path / "ed")
    assert r["ok"], r
