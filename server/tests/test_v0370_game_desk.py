"""v0.370 GAME DESK (Phase 1, docs/GAME_DESK_PLAN.md): the Game Developer employee. Design doc first (her OK), then
GDScript -> guard -> headless play -> Web export -> Hoola's playtest -> a private play link; fixes from the real errors;
a change that fails keeps the last good version. Godot itself is faked here except in the last test, which builds and
plays a real game when Godot + its Web templates are installed (the sandbox / VPS check)."""
import asyncio
import gzip
import json
import re
import os
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

GAME = '''extends Node

var box: ColorRect

func _ready() -> void:
	box = ColorRect.new()
	box.color = Color(1, 0.6, 0.1)
	box.size = Vector2(80, 80)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(box)

func _process(delta: float) -> void:
	box.position.x = fmod(box.position.x + 200.0 * delta, 600.0)
'''


@pytest.fixture
def gd(env, tmp_path, monkeypatch):
    monkeypatch.setenv("GAME_DIR", str(tmp_path / "games"))
    monkeypatch.setenv("GAME_WORKER", "false")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://hoola.example.in")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gamedesk import ai, engine, playtest, service
    calls = {"code": 0, "fix": 0, "change": 0, "smoke": [], "design": 0}
    monkeypatch.setattr(ai, "design", lambda brief, o, feedback="", old="": (calls.__setitem__("design", calls["design"] + 1)
                        or f"# Chai Hop\n**Pitch:** tap to fly. {feedback}"))
    monkeypatch.setattr(ai, "code", lambda d, o, s: (calls.__setitem__("code", calls["code"] + 1) or
                                                     {"main.gd": GAME, "__notes__": "Tap or Space."}))
    monkeypatch.setattr(ai, "fix", lambda d, f, p, o, s: (calls.__setitem__("fix", calls["fix"] + 1) or {"main.gd": GAME}))
    monkeypatch.setattr(ai, "change", lambda d, f, w, o, s: (calls.__setitem__("change", calls["change"] + 1) or
                                                             {"main.gd": GAME.replace("200.0", "400.0")}))
    script = {"smoke": [], "play": []}

    def smoke(job, frames=600, holder=None):
        calls["smoke"].append((job / "proj" / "main.gd").read_text())
        errs = script["smoke"].pop(0) if script["smoke"] else []
        return {"ok": not errs, "errors": errs, "seconds": 0.1, "exit": 0}

    def export_web(job, holder=None, debug=False):
        b = job / "build"
        b.mkdir(parents=True, exist_ok=True)
        for n in ("index.html", "index.js", "index.wasm", "index.pck"):
            (b / n).write_text(f"<{n}>")
        (b / "index.wasm.gz").write_bytes(gzip.compress(b"<index.wasm>"))
        return {"ok": True, "errors": [], "seconds": 0.2, "bytes": 100, "download_bytes": 2 * 1048576}

    def play(build, out, orientation="portrait", seconds=8):
        out.mkdir(parents=True, exist_ok=True)
        (out / "shot1.png").write_bytes(b"\x89PNG")
        errs = script["play"].pop(0) if script["play"] else []
        return {"ok": not errs, "errors": errs, "warnings": [], "shots": ["shot1.png"], "fps": 44, "load_s": 1.4}

    monkeypatch.setattr(engine, "smoke", smoke)
    monkeypatch.setattr(engine, "export_web", export_web)
    monkeypatch.setattr(playtest, "run", play)
    service.ensure_table()
    return {"svc": service, "calls": calls, "script": script}


def _made(svc, tenant="default", brief="ek tap wala game jismein chai ka cup udta hai"):
    v = svc.start(tenant, "", brief, "portrait")
    svc.run_job(v["id"])
    return svc.get(tenant, v["id"])


def test_design_first_then_build_and_private_link(gd):
    svc = gd["svc"]
    v = _made(svc)
    assert v["status"] == "design_ready" and v["title"] == "Chai Hop" and "Pitch" in v["design"] and not v["play_url"]
    assert gd["calls"]["code"] == 0                                  # nothing built before her OK
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    v = svc.get("default", v["id"])
    assert v["status"] == "done" and v["version"] == 1
    assert v["play_url"].startswith("https://hoola.example.in/play/") and len(v["play_url"].split("/")[4]) >= 16
    assert [c["step"] for c in v["checks"]] == ["play_headless", "export_web", "playtest"]
    assert v["numbers"]["fps_server"] == 44 and v["numbers"]["download_mb"] == 2.0 and v["shots"][0].endswith("shots/v1/shot1.png")
    token = v["play_url"].split("/")[4]
    p, media = svc.play_file(token, "index.html")
    assert p is not None and media.startswith("text/html")
    for bad in ("../proj/main.gd", "proj/main.gd", ".xdg/x", "index.html/../../x"):
        assert svc.play_file(token, bad)[0] is None
    assert svc.play_file("A" * 24, "index.html")[0] is None
    assert svc.play_file(token, "shots/v1/shot1.png")[1] == "image/png"


def test_design_changes_before_build(gd):
    svc = gd["svc"]
    v = _made(svc)
    svc.approve("default", v["id"], feedback="make it a night theme")
    svc.run_job(v["id"])
    v = svc.get("default", v["id"])
    assert v["status"] == "design_ready" and "night theme" in v["design"] and gd["calls"]["code"] == 0


def test_real_errors_are_fixed_and_counted(gd):
    svc = gd["svc"]
    gd["script"]["smoke"] = [['SCRIPT ERROR: Parse Error: Identifier "scorex" not declared']]
    gd["script"]["play"] = [["the game froze (no new frames while playing)"]]
    v = _made(svc)
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    v = svc.get("default", v["id"])
    assert v["status"] == "done" and gd["calls"]["fix"] == 2 and v["history"][-1]["fixed"] == 2


def test_guard_refuses_network_and_programs(gd):
    from app.gamedesk import guard
    bad = guard.problems({"main.gd": "extends Node\nfunc _ready():\n\tvar h = HTTPRequest.new()\n\tOS.execute('ls', [])\n"
                                     "\tJavaScriptBridge.eval('x')\n\tvar f = FileAccess.open('/etc/passwd', FileAccess.READ)\n"})
    text = " ".join(bad)
    assert "HTTPRequest" in text and "OS.execute" in text and "JavaScriptBridge" in text and "user://" in text
    assert guard.problems({"main.gd": GAME}) == []
    assert any("extends Node" in p for p in guard.problems({"main.gd": "extends Node2D\n"}))
    assert any("bad file name" in p for p in guard.problems({"main.gd": GAME, "../x.gd": "extends Node\n"}))
    assert any("bad file name" in p for p in guard.problems({"main.gd": GAME, "hoola_probe.gd": "extends Node\n"}))


def test_guard_failure_goes_back_to_the_model(gd, monkeypatch):
    from app.gamedesk import ai
    svc = gd["svc"]
    seq = [{"main.gd": "extends Node\nfunc _ready():\n\tvar h := HTTPRequest.new()\n"}]
    monkeypatch.setattr(ai, "code", lambda d, o, s: seq.pop(0))
    v = _made(svc)
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    v = svc.get("default", v["id"])
    assert v["status"] == "done" and gd["calls"]["fix"] == 1 and "HTTPRequest" not in gd["calls"]["smoke"][0]


def test_failed_change_keeps_the_last_good_version(gd, monkeypatch):
    from app.gamedesk import ai
    svc = gd["svc"]
    v = _made(svc)
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    good_url = svc.get("default", v["id"])["play_url"]
    gd["script"]["smoke"] = [["SCRIPT ERROR: boom"]] * 5
    monkeypatch.setattr(ai, "fix", lambda d, f, p, o, s: {"main.gd": GAME})
    svc.change("default", v["id"], "add a shield")
    svc.run_job(v["id"])
    v = svc.get("default", v["id"])
    assert v["status"] == "done" and v["version"] == 1 and v["play_url"] == good_url and "old version" in v["error"]
    assert [h["ok"] for h in v["history"]] == [True, False]


def test_refusals_limits_and_busy(gd):
    svc = gd["svc"]
    with pytest.raises(svc.GameError, match="copy"):
        svc.start("default", "", "Subway Surfers ka clone banao exactly same", "portrait")
    with pytest.raises(svc.GameError, match="money"):
        svc.start("default", "", "teen patti real money game banao", "portrait")
    with pytest.raises(svc.GameError, match="targeting"):
        svc.start("default", "", "missile weapon targeting simulator banao", "portrait")
    assert svc.problem("an endless runner like Subway Surfers but original") == ""   # a genre is fine
    svc.start("default", "", "ek puzzle game rangon wala", "portrait")
    with pytest.raises(svc.GameError, match="already"):
        svc.start("default", "", "ek aur game racing wala", "portrait")


def test_source_zip_opens_in_godot(gd):
    svc = gd["svc"]
    v = _made(svc)
    svc.approve("default", v["id"])
    svc.run_job(v["id"])
    data, name = svc.source_zip("default", v["id"])
    names = zipfile.ZipFile(BytesIO(data)).namelist()
    assert name.startswith("G-0001") and name.endswith(".zip")
    assert {"G-0001/main.gd", "G-0001/project.godot", "G-0001/main.tscn", "G-0001/export_presets.cfg", "G-0001/DESIGN.md"} <= set(names)
    with pytest.raises(svc.GameError):
        svc.source_zip("other-tenant", v["id"])


def test_template_is_single_threaded_web_with_probe(env):
    from app.gamedesk import template
    f = template.files("Chai Hop", "landscape", {"main.gd": GAME})
    assert 'HoolaProbe="*res://hoola_probe.gd"' in f["project.godot"] and "viewport_width=1280" in f["project.godot"]
    assert "variant/thread_support=false" in f["export_presets.cfg"] and 'platform="Web"' in f["export_presets.cfg"]
    assert "JavaScriptBridge" in f["hoola_probe.gd"] and 'type="Node"' in f["main.tscn"]


def test_api_and_play_link_headers(gd):
    from app.main import app
    svc = gd["svc"]
    with TestClient(app) as c:
        h = c.get("/api/game").json()
        assert "health" in h and h["orientations"] == ["portrait", "landscape", "square"]
        # v0.410 the route now checks the hire too (it used to start a game for anyone with the key)
        assert c.post("/api/game", json={"brief": "ek tap wala game chai ka cup"}).status_code == 400
        from app.employee import hire
        hire.hire("default", "game_dev")
        v = c.post("/api/game", json={"brief": "ek tap wala game chai ka cup", "orientation": "portrait"}).json()
        assert v["status"] == "designing"
        assert c.post("/api/game", json={"brief": "doosra game"}).status_code == 400
        svc.run_job(v["id"])
        assert c.post(f"/api/game/{v['id']}/approve", json={}).json()["status"] == "queued"
        svc.run_job(v["id"])
        g = c.get(f"/api/game/{v['id']}").json()
        path = "/" + g["play_url"].split("/", 3)[3]
        r = c.get(path + "index.html")
        assert r.status_code == 200 and "frame-ancestors 'self'" in r.headers["content-security-policy"]
        assert "connect-src 'self'" in r.headers["content-security-policy"] and r.headers["access-control-allow-origin"] == "*"
        assert r.headers["x-robots-tag"] == "noindex"
        w = c.get(path + "index.wasm", headers={"Accept-Encoding": "gzip"})
        assert w.headers.get("content-encoding") == "gzip" and w.headers["content-type"] == "application/wasm"
        assert w.content == b"<index.wasm>"
        assert c.get(path.rstrip("/")).status_code in (200, 307)
        assert c.get("/play/AAAAAAAAAAAAAAAAAAAAAA/index.html").status_code == 404
        z = c.get(f"/api/game/{v['id']}/source")
        assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
        assert c.delete(f"/api/game/{v['id']}").json()["ok"] is True
        assert c.get(path + "index.html").status_code == 404


def test_hire_card_group_and_tool_gate(gd):
    from app.agent import tools
    from app.agent.tools import Ctx
    from app.employee import hire
    cat = {e["key"]: e for e in hire.catalog("default")}
    assert cat["game_dev"]["live"] and cat["game_dev"]["group"] == hire.GAME_GROUP
    soon = [k for k, e in cat.items() if e.get("group") == hire.GAME_GROUP and not e["live"]]
    assert len(soon) == 0                                                         # v0.420-v0.423: all ten Game Desk roles live
    assert cat["procgen_dev"]["live"] and cat["physics_dev"]["live"]
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    with pytest.raises(tools.ToolError, match="hire"):
        asyncio.run(tools.HANDLERS["game_desk"](ctx, action="new", brief="ek tap wala game chai ka cup"))
    hire.hire("default", "game_dev")
    out = asyncio.run(tools.HANDLERS["game_desk"](ctx, action="new", brief="ek tap wala game chai ka cup"))
    assert out["status"] == "designing" and "background" in out["note"]
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_desk"](staff, action="cancel", id=out["id"]))


def test_routing_and_guide(env):
    from app.agent import admit, prompts, tools
    assert tools.FAMILY_OF["game_desk"] == "gamedesk"
    for ask in ("ek racing game banao", "chai wala endless runner game bana do", "mere shop ke liye ek chhota game chahiye",
                "Godot mein project", "गेम बनाओ"):
        assert "gamedesk" in admit.route(ask), ask
    for ask in ("Rahul ko mail bhejo", "kal ka mausam"):
        assert "gamedesk" not in admit.route(ask), ask
    assert "call `game_desk`" in prompts.system_text({"gamedesk"})
    assert "call `game_desk`" not in prompts.system_text({"email"})


def test_console_and_phone_wiring():
    root = Path(__file__).resolve().parents[2]
    html = (root / "server/app/static/console/v2.html").read_text()
    js = (root / "server/app/static/console/v2.js").read_text()
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert 'id="v-gamedesk"' in html and "['game_dev', 'gamedesk', 'Game Desk']" in js and "EMP?.game(" in js
    # v0.455: the exact export string broke the moment v0.453 added `edu` (the Education Desk), which was a correct
    # change - so pin the NAMES this test cares about, not the whole list, and let a new desk be added freely.
    exported = [m for m in re.findall(r"return \{([^}]*)\};", emp) if "hub" in m]
    assert exported, "employees.js must export its desks"
    names = {x.strip() for x in exported[-1].split(",")}
    assert {"hub", "desk", "social", "cad", "game", "arch"} <= names, names
    assert 'sandbox="allow-scripts allow-pointer-lock"' in emp
    # the v0.358 merge had dropped these: the Hub, both desks, the Arena and three scripts
    for v in ("v-hire", "v-seodesk", "v-socialdesk", "v-arena"):
        assert f'id="{v}"' in html, v
    for s in ("employees.js?v=", "arena.js?v=", "charts.js?v="):
        assert s in html, s
    dart = (root / "lib/ui/employees_screen.dart").read_text()
    # v0.455: this pinned the exact spelling `GameDeskScreen(app: widget.app)`, which v0.453 correctly changed when the
    # phone started opening every hired employee on its own screen. What the test actually cares about is that the Game
    # Desk is REACHABLE from the employee list, so assert that instead of one call's punctuation.
    assert re.search(r"GameDeskScreen\(app:\s*\w+(\.\w+)?\)", dart), "the phone must open the Game Desk"
    assert "game_dev" in dart, "the Game Developer must be routed"
    assert "_s(e['group'])" in dart
    assert "gameApprove" in (root / "lib/api.dart").read_text()


@pytest.mark.skipif(not os.environ.get("GODOT_BIN"), reason="real Godot build: set GODOT_BIN (+ Web templates installed)")
def test_real_godot_build_export_and_play(env, tmp_path):
    from app.gamedesk import engine, playtest, template
    if not engine.health()["web_templates"]:
        pytest.skip("Godot Web export templates not installed")
    job = tmp_path / "job"
    (job / "proj").mkdir(parents=True)
    for n, t in template.files("Check", "portrait", {"main.gd": GAME}).items():
        (job / "proj" / n).write_text(t)
    assert engine.smoke(job)["ok"]
    bad = tmp_path / "bad"
    (bad / "proj").mkdir(parents=True)
    for n, t in template.files("Bad", "portrait", {"main.gd": GAME.replace("box.size", "boxx.size")}).items():
        (bad / "proj" / n).write_text(t)
    s = engine.smoke(bad)
    assert not s["ok"] and any("boxx" in e for e in s["errors"])
    e = engine.export_web(job)
    assert e["ok"] and e["download_bytes"] < e["bytes"]
    p = playtest.run(job / "build", job / "shots")
    assert p["ok"] and p["frames_advanced"], json.dumps(p)
