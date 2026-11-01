"""v0.416 GAME PLATFORMS (Hoola Game Engine plan, Phase 6): Linux / Windows / macOS downloads made on the server, Android
APK / AAB in her builds repo with the game's own upload key, every file checked in code, the package name fixed and the
version code only going up, the store kit (texts within limits, images in exact sizes, AI disclosure, Steam scripts),
the age-rating draft, and itch.io uploads only by her tap. Godot's exports, the builds repo and butler are faked here;
the desktop exports ran for real in the sandbox (see HISTORY)."""
import asyncio
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0370_game_desk import gd  # noqa: F401  (fixture)
from tests.test_v0386_game_studio import st  # noqa: F401  (fixture)


def _zip(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in entries.items():
            z.writestr(k, v)
    return buf.getvalue()


@pytest.fixture
def pf(st, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("GAME_CREW_REVIEW", "off")
    from app.gamedesk import engine
    from app.gamedesk import platforms as PF
    PF.ensure_table()
    tpl = tmp_path / "tpl"
    tpl.mkdir()
    for f in ("linux_release.x86_64", "windows_release_x86_64.exe", "macos.zip", "web_nothreads_release.zip"):
        (tpl / f).write_bytes(b"x")
    monkeypatch.setattr(engine, "templates_dir", lambda: tpl)
    monkeypatch.setattr(engine, "find", lambda: "/fake/godot")
    script = {"bad": set()}
    exports = []

    def run(job, args, log_name, timeout, holder=None):
        if "--export-release" in args:
            name, out = args[args.index("--export-release") + 1], args[args.index("--export-release") + 2]
            exports.append(name)
            p = (job / "proj" / out).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            if name == "Linux":
                p.write_bytes(b"\x7fELF" + b"0" * 100 if "linux" not in script["bad"] else b"nope")
            elif name == "Windows Desktop":
                p.write_bytes(b"MZ" + b"0" * 100 if "windows" not in script["bad"] else b"PK no")
            elif name == "macOS":
                p.write_bytes(_zip({"Game.app/Contents/Info.plist": "<plist/>", "Game.app/Contents/Resources/Game.pck": "pck"}))
        return 0, "", False
    monkeypatch.setattr(engine, "_run", run)
    monkeypatch.setattr(engine, "smoke", lambda job, frames=600, holder=None: {"ok": True, "errors": []})
    return {**st, "PF": PF, "script": script, "exports": exports}


def test_presets_for_every_platform(env):
    from app.gamedesk import template as T
    p = T.native_presets("Chai Hop", "com.hoola.chai_hop12", 7, "1.0.7", "portrait")
    for name in ('name="Web"', 'name="Linux"', 'name="Windows Desktop"', 'name="macOS"', 'name="Android"'):
        assert name in p, name
    assert 'application/bundle_identifier="com.hoola.chaihop12"' in p                     # macOS refuses '_' (found live)
    assert 'package/unique_name="com.hoola.chai_hop12"' in p and "version/code=7" in p
    assert "permissions/internet=false" in p and "binary_format/embed_pck=true" in p
    assert "keystore" not in p                                                            # keys only via env vars
    aab = T.native_presets("X", "com.hoola.x1", 1, "1.0.1", android_format="aab")
    assert "gradle_build/use_gradle_build=true" in aab and 'game.aab"' in aab


def test_desktop_release_is_checked_and_downloadable(pf):
    PF = pf["PF"]
    rel = PF.release("default", pf["sid"], ["linux", "windows", "macos", "android"])
    assert rel["number"] == "R-001" and rel["version_code"] == 1 and rel["package"].startswith("com.hoola.")
    out = PF.run_release("default", rel["id"])
    p = out["platforms"]
    assert [p[k]["status"] for k in ("linux", "windows", "macos")] == ["done", "done", "done"]
    assert p["android"]["status"] == "not assessed" and "builds repo" in p["android"]["note"]        # never a fake file
    assert out["status"] == "partial" and pf["exports"] == ["Linux", "Windows Desktop", "macOS"]
    z = zipfile.ZipFile(PF._rdir("default", pf["sid"], rel["id"]) / p["windows"]["file"])
    assert any(n.endswith("game.exe") for n in z.namelist()) and "Run anyway" in z.read([n for n in z.namelist() if n.endswith("README.txt")][0]).decode()
    assert len(p["linux"]["sha256"]) == 64 and p["linux"]["url"].startswith("/api/gamestudio/release/")
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    got = c.get(p["linux"]["url"])
    assert got.status_code == 200 and got.content[:2] == b"PK"
    assert c.get(p["linux"]["url"].replace("sig=", "sig=1")).status_code == 404
    r2 = PF.release("default", pf["sid"], ["linux"])
    assert r2["version_code"] == 2 and r2["package"] == rel["package"]                   # same name, code only goes up
    assert any(d["text"].startswith("Release R-001") for d in pf["S"].get("default", pf["sid"])["decisions"])


def test_a_broken_file_fails_its_check(pf):
    PF = pf["PF"]
    pf["script"]["bad"] = {"windows"}
    out = PF.run_release("default", PF.release("default", pf["sid"], ["windows", "linux"])["id"])
    assert out["platforms"]["windows"]["status"] == "failed" and "no Windows program" in out["platforms"]["windows"]["checks"]["errors"][0]
    assert out["platforms"]["linux"]["status"] == "done" and "url" not in out["platforms"]["windows"]


def test_missing_templates_are_not_assessed(pf, monkeypatch, tmp_path):
    from app.gamedesk import engine
    PF = pf["PF"]
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(engine, "templates_dir", lambda: empty)
    out = PF.run_release("default", PF.release("default", pf["sid"], ["macos"])["id"])
    assert out["platforms"]["macos"]["status"] == "not assessed" and "--desktop" in out["platforms"]["macos"]["note"]
    assert out["status"] == "failed"


def test_android_in_her_builds_repo_with_the_games_upload_key(pf, monkeypatch):
    PF = pf["PF"]
    from app.appmaker.android import runners
    monkeypatch.setattr(runners, "mode", lambda: "github")
    pushed = {}

    def push_tree(src, key, progress, prefix="app"):
        pushed["files"] = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file())
        pushed["key"], pushed["prefix"] = key, prefix
        pushed["json"] = json.loads((src / "keys" / "upload.json").read_text())
        return "her/builds", "build/game-s-0001", "abc123"
    monkeypatch.setattr(runners, "push_tree", push_tree)
    monkeypatch.setattr(runners, "dispatch_wait", lambda repo, branch, sha, wf, inputs, progress, t0, limit: pushed.update(wf=wf, inputs=inputs) or
                        {"id": 9, "conclusion": "success"})
    apk = _zip({"AndroidManifest.xml": "m", "classes.dex": "d", "META-INF/CERT.RSA": "s"})
    monkeypatch.setattr(runners, "artifacts", lambda repo, run, names: [_zip({"dist/android/game.apk": apk, "build.log": "ok"})])
    out = PF.run_release("default", PF.release("default", pf["sid"], ["android"])["id"])
    a = out["platforms"]["android"]
    assert a["status"] == "done" and a["format"] == "apk" and a["file"].endswith(".apk")
    assert pushed["wf"] == "hoola-game.yml" and pushed["inputs"]["format"] == "apk" and pushed["prefix"] == "hoola-game"
    assert "keys/upload.p12" in pushed["files"] and "game/export_presets.cfg" in pushed["files"] and pushed["json"]["alias"] == "upload"
    k1 = PF._upload_key("default", pf["sid"])
    assert k1["password"] == pushed["json"]["password"] and PF._upload_key("default", pf["sid"])["sha256"] == k1["sha256"]   # one key, kept
    sealed = (PF.G.root() / "default" / "releases" / pf["sid"] / "upload.key.sealed").read_text()
    assert k1["password"] not in sealed                                                    # sealed, not plain
    assert "hoola-game.yml" in runners.WORKFLOWS


def test_store_kit_limits_images_and_disclosure(pf, monkeypatch):
    PF = pf["PF"]
    from app.gamedesk import ai
    monkeypatch.setattr(ai, "ask", lambda system, prompt, max_tokens=0: json.dumps({
        "itch": {"title": "Chai Hop", "tagline": "x" * 120, "description": "Fly a cup.", "tags": ["arcade"]},
        "steam": {"short": "s" * 400, "about": "About.", "tags": ["Casual"]},
        "play": {"title": "Chai Hop: The Very Long Title Of Doom", "short": "Fly.", "full": "Full."}}))
    kit = PF.store_kit("default", pf["sid"], regen=True)
    assert len(kit["itch"]["tagline"]) <= 80 and len(kit["steam"]["short"]) <= 300 and len(kit["play"]["title"]) <= 30
    assert any("cut to" in n for n in kit["notes"]) and any("notarised" in n for n in kit["notes"])
    assert "No AI content is generated while the game is played" in kit["ai_disclosure"]
    assert kit["rating"]["expected"]["PEGI"] in ("3", "7")
    path = PF.kit_file(pf["sid"], 2 ** 40, PF._dsig("kit-" + pf["sid"], "kit", 2 ** 40))
    z = zipfile.ZipFile(path)
    names = z.namelist()
    from PIL import Image
    for k, (w, h) in PF.IMAGES.items():
        n = f"images/{k}-{w}x{h}.png"
        assert n in names and Image.open(io.BytesIO(z.read(n))).size == (w, h), k
    assert "steam/app_build.vdf" in names and "never logs into your Steam" in z.read("steam/README.txt").decode()


def test_rating_draft_follows_the_bible(pf):
    PF = pf["PF"]
    from app.gamedesk import bible as B
    B.ensure_table()
    d = PF.rating_draft("default", pf["sid"])
    assert d["expected"]["PEGI"] == "3" and d["answers"]["gambling"].startswith("no") and d["answers"]["users_interact_or_chat"].startswith("no")
    B.set_entity("default", pf["sid"], "enemy", {"id": "drone", "name": "Drone", "behaviour": "shoot"})
    d = PF.rating_draft("default", pf["sid"])
    assert d["expected"]["PEGI"] == "7" and "fantasy" in d["answers"]["violence"] and "IARC" in d["note"]


def test_itch_only_by_her_tap(pf, monkeypatch):
    PF = pf["PF"]
    out = PF.run_release("default", PF.release("default", pf["sid"], ["linux", "windows"])["id"])
    with pytest.raises(PF.PlatformError, match="itch.io API key"):
        PF.itch_card("default", pf["sid"], out["id"], "meghana/chai-hop")
    with pytest.raises(PF.PlatformError, match="jaisi"):
        PF.set_itch_key("default", "short")
    PF.set_itch_key("default", "A" * 40)
    with pytest.raises(PF.PlatformError, match="page"):
        PF.itch_card("default", pf["sid"], out["id"], "not a page")
    card = PF.itch_card("default", pf["sid"], out["id"], "meghana/chai-hop")
    assert card["channels"] == {"linux": "meghana/chai-hop:linux", "windows": "meghana/chai-hop:windows"}
    calls = []
    monkeypatch.setattr(PF, "_butler", lambda: "/fake/butler")
    monkeypatch.setattr(PF.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw["env"].get("BUTLER_API_KEY"))) or
                        type("R", (), {"returncode": 0, "stdout": "pushed " + "A" * 40, "stderr": ""})())
    with pytest.raises(PF.PlatformError, match="Card"):
        PF.itch_push("default", pf["sid"], out["id"], "wrong")
    res = PF.itch_push("default", pf["sid"], out["id"], card["hash"])
    assert res["ok"] and len(calls) == 2 and calls[0][0][1] == "push" and "--userversion" in calls[0][0] and calls[0][1] == "A" * 40
    assert "A" * 40 not in json.dumps(res)                                               # the key never comes back
    with pytest.raises(PF.PlatformError, match="Card"):
        PF.itch_push("default", pf["sid"], out["id"], card["hash"])                     # a card is used once


def test_tool_api_and_ui(pf):
    from app.agent import admit, tools
    from app.agent.tools import Ctx
    from app.employee import hire
    from app.main import app
    hire.hire("default", "game_dev")
    ctx = Ctx(tenant_id="default", conversation_id="c1")
    out = asyncio.run(tools.HANDLERS["game_release"](ctx, action="targets"))
    assert out["targets"]["linux"]["ready"] and not out["targets"]["android"]["ready"]
    out = asyncio.run(tools.HANDLERS["game_release"](ctx, action="build", platforms=["linux"]))
    assert out["release"] == "R-001"
    staff = Ctx(tenant_id="default", conversation_id="c1", actor="staff:x")
    with pytest.raises(tools.ToolError, match="owner"):
        asyncio.run(tools.HANDLERS["game_release"](staff, action="build", platforms=["linux"]))
    assert "itch_push" not in tools.HANDLERS["game_release"].__code__.co_names               # the tool cannot upload
    assert tools.FAMILY_OF["game_release"] == "gamedesk"
    for ask in ("game ka windows build banao", "itch.io par game daalo", "game ki age rating"):
        assert "gamedesk" in admit.route(ask), ask
    c = TestClient(app)
    d = c.get(f"/api/gamestudio/{pf['sid']}/releases").json()
    assert d["releases"][0]["number"] == "R-001" and d["identity"]["package"].startswith("com.hoola.") and d["itch_key"] is False
    assert c.post(f"/api/gamestudio/{pf['sid']}/releases", json={"platforms": ["playstation"]}).status_code == 400
    assert c.get(f"/api/gamestudio/{pf['sid']}/rating").json()["expected"]["PEGI"] == "3"
    assert c.post("/api/gamestudio/itch-key", json={"key": "B" * 32}).json()["ok"]
    root = Path(__file__).resolve().parents[2]
    emp = (root / "server/app/static/console/employees.js").read_text()
    assert "gsRelease" in emp and "/itch/push" in emp
    assert "GameReleaseScreen" in (root / "lib/ui/game_release_screen.dart").read_text()
    assert "gameReleases" in (root / "lib/api.dart").read_text()
    assert "templates/macos.zip" in (root / "server/deploy/setup_godot.py").read_text()
    wf = (root / "server/app_builder/hoola-game.yml").read_text()
    assert "GODOT_ANDROID_KEYSTORE_RELEASE_PATH" in wf and "rm -rf hoola-game/keys" in wf
