"""v0.806 HOOLA 3D KIT (owner: "GO 3D GAMEPLAY"): the 3D gameplay pieces every small 3D game needs, written ONCE by
Hoola and proved in the real engine - a world with sky and sun, ground / blocks / moving platforms, a player who walks
and jumps by keyboard AND touch, a follow or first-person camera, coins, enemies that patrol or chase (and can be
stomped), a goal, and a HUD with on-screen controls. Before this the model wrote all of that from scratch in every 3D
game, which is where 3D builds broke.

It is a pack like the others (packs.py): `hoola_3d.gd` = the Hoola3D autoload, Hoola's own file - the model reads its
API in ai.GUIDE and never edits or re-outputs it. It rides ONLY in a game whose design is 3D (`wants`), so a 2D game
is byte-for-byte what it was.

`proof()` builds Hoola's own fixed 3D game (kit/proof_main.gd, no model call) the whole road - guard, headless play,
web export, browser playtest - and can save it as a real game she can open and play."""
from __future__ import annotations

import re
import secrets
import shutil
import tempfile
from pathlib import Path
from typing import Any

FILE = "hoola_3d.gd"
_DIR = Path(__file__).parent / "kit"

# "3D" as she or the design doc would say it; "2D" alone never matches
IS_3D = re.compile(r"(?<![A-Za-z0-9.])3[\s-]?d(?![A-Za-z0-9])|\bthree[\s-]dimension\w*|\b(?:first|third)[\s-]person\b|"
                   r"\b(?:fps|tps) (?:game|shooter|view|camera)\b|\blow[\s-]?poly\b", re.I)

PROOF_TITLE = "Diya Run 3D"
PROOF_BRIEF = "A small 3D game: run round a courtyard, collect the coins, dodge two guards and reach the green light."
PROOF_DESIGN = """# Diya Run 3D
**Pitch:** a small 3D run round a festival courtyard - collect the coins, dodge the guards, reach the green light.
## Core loop
Walk and jump round one courtyard. Collect 5 of the 8 coins, then step into the green light on the high platform.
## Controls
Keyboard: arrows or WASD to move, Space to jump, Q / E to turn the camera. Touch: left stick to move, the round
button to jump, drag on the right to look.
## Goal and game over
Win: reach the green light with 5 coins. Three lives; a guard's touch or a fall costs one. Land on a guard to remove it.
## Screens
Title "Tap to start", playing with coins and lives, game over / win with "Tap to play again".
## Look
Third-person 3D, low-poly shapes drawn in code: green ground, brown walls, an amber player, gold coins, pink guards.
## Made with
Hoola's own 3D kit (Hoola3D). This is Hoola's proof game: no model wrote any of its code.
"""


def kit() -> str:
    return (_DIR / FILE).read_text(encoding="utf-8")


def proof_main() -> str:
    return (_DIR / "proof_main.gd").read_text(encoding="utf-8")


def wants(*texts: str) -> bool:
    """True when her words or the design doc ask for a 3D game."""
    return any(IS_3D.search(t or "") for t in texts)


def for_game(tenant: str, game_id: str):
    """The pack hook (packs.for_game): the kit for a game whose brief / design is 3D, else None."""
    from ..db import session
    from .service import GameProject
    with session() as s:
        r = s.get(GameProject, game_id)
        if r is None or r.tenant_id != tenant or not wants(r.brief, r.design):
            return None
    return kit(), {}


API = """- 3D KIT: this game's files include hoola_3d.gd (the Hoola3D autoload, Hoola's own PROVED 3D gameplay kit - NEVER edit
  or re-output it). Build the 3D game FROM IT instead of writing controllers, cameras or touch controls yourself:
  * `Hoola3D.reset()` first, every time you (re)build the level; connect its signals ONCE in _ready():
    coin_taken(total), player_hit(hp), player_fell, goal_reached (fires each time the player enters the goal - you
    decide if that is a win), enemy_stomped(left).
  * `var level := Hoola3D.world(self, sky_top, sky_horizon)` -> Node3D with sky, ambient light and a sun with shadows.
  * `Hoola3D.ground(level, Vector2(w, d), color)`; `Hoola3D.block(level, centre, size, color)` = wall / floor /
    platform (StaticBody3D); `Hoola3D.moving_block(level, from, to, size, color, seconds)` carries the player;
    `Hoola3D.tree(level, pos, height)` = decoration; `Hoola3D.mat(color, glow)` -> StandardMaterial3D for your own meshes;
    `Hoola3D.model(level, key, pos, size)` places one of her approved 3D models or returns null (keep a drawn fallback).
  * `var p := Hoola3D.spawn_player(level, pos, color, speed, jump_height, hp)` -> CharacterBody3D that already walks,
    jumps (keyboard arrows / WASD / Space AND touch stick + jump button), takes knock-back and respawns after a fall.
    A jump clears `jump_height` metres: make every step lower than that. Then `Hoola3D.follow_camera(p, 7.5)` (third
    person; distance 0 = first person). Never write your own input for moving, jumping or looking.
  * `Hoola3D.coin(level, pos)`, `Hoola3D.enemy(level, pos, patrol_to, speed, chase_range)` (touch = -1 hp, landing on
    it removes it), `Hoola3D.goal(level, pos)`, `Hoola3D.hurt(1)` for your own hazards. Counters: Hoola3D.coins,
    coins_total, enemies_left; the player is Hoola3D.player (its .hp).
  * `var hud := Hoola3D.make_hud(self)` LAST: it shows coins, lives and the touch controls. Screens are
    `hud.message("Title", "small text")` and `hud.clear()`; set `Hoola3D.playing = false` while a message is up
    (title / game over / win) and true while playing. Restart = free your level and hud, then build again.
  * Keep the level small (one courtyard / a few rooms, under 150 nodes). You still write the game: the level layout,
    the rules, the screens and HoolaProbe.state("state", ...) / event(...) as for every game. main.gd stays `extends Node`."""


# ---------------------------------------------------------------- the proof game (no model)
def proof(tenant: str = "", conv: str = "", save: bool = False, shots_to: Path | None = None) -> dict[str, Any]:
    """Hoola's own 3D game through the real pipeline: guard -> headless play -> web export -> browser playtest.
    save=True keeps it as a finished game of `tenant` (her list, a private play link). Nothing is called a pass that
    did not pass: each step carries its own errors."""
    from . import engine, guard, playtest, template
    out: dict[str, Any] = {"title": PROOF_TITLE, "health": engine.health()}
    files = {"main.gd": proof_main(), FILE: kit()}
    bad = guard.problems(files)
    out["guard"] = {"ok": not bad, "errors": bad[:6]}
    if bad or not (out["health"].get("installed") and out["health"].get("web_templates")):
        out["ok"] = False
        return out
    job = Path(tempfile.mkdtemp(prefix="hoola-3d-proof-"))
    try:
        (job / "proj").mkdir()
        for name, txt in template.files(PROOF_TITLE, "landscape", files).items():
            (job / "proj" / name).write_text(txt, encoding="utf-8")
        out["smoke"] = engine.smoke(job)
        out["export"] = engine.export_web(job) if out["smoke"]["ok"] else {"ok": False, "errors": ["not exported"]}
        play: dict[str, Any] = {"ok": False, "errors": ["not played"]}
        if out["export"].get("ok"):
            play = playtest.run(job / "build", job / "shots", "landscape")
        out["playtest"] = {k: play.get(k) for k in ("ok", "errors", "fps", "load_s", "warnings")}
        out["played"] = play_through(job) if out["smoke"]["ok"] else {"ok": False, "why": "not played"}
        out["touch"] = browser_touch(job / "build", job / "shots") if play.get("ok") else {"ok": False}
        out["kit"] = self_test()
        out["ok"] = bool(out["smoke"]["ok"] and out["export"].get("ok") and play.get("ok") and out["played"].get("ok")
                         and out["touch"].get("ok") and out["kit"].get("ok"))
        if shots_to:                                    # the pictures of the run, for a person to look at
            shutil.rmtree(shots_to, ignore_errors=True)
            if (job / "shots").is_dir():
                shutil.copytree(job / "shots", shots_to)
        if out["ok"] and save and tenant:
            out["game"] = _keep(tenant, conv, job, out["export"], play)
    finally:
        shutil.rmtree(job, ignore_errors=True)
    return out


def browser_touch(build: Path, out: Path | None = None, wait_s: int = 70) -> dict[str, Any]:
    """The proof game's web build in a real Chromium, played by TOUCH: a tap starts it, then the left stick is held
    forward until the engine itself reports a coin (HoolaProbe score >= 1). Proves the on-screen controls where
    players use them. Software graphics on a server are slow, so it waits for the game's own clock, not ours."""
    from playwright.sync_api import sync_playwright
    from . import playtest
    srv = playtest._serve(build)
    res: dict[str, Any] = {"ok": False, "score": 0, "state": "", "seconds": None}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**playtest._launch_kw())
            try:
                pg = b.new_page(viewport={"width": 640, "height": 360})
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
                pg.wait_for_function("window.__hoola && window.__hoola.ready && window.__hoola.frames > 2", timeout=90000)
                import time as _t
                t0 = _t.time()
                pg.mouse.click(320, 180)
                pg.wait_for_function("window.__hoola.state && window.__hoola.state.state === 'playing'", timeout=30000)
                pg.mouse.move(128, 288)
                pg.mouse.down()
                for y in (268, 248, 228, 208):
                    pg.mouse.move(128, y)
                    pg.wait_for_timeout(120)
                try:
                    pg.wait_for_function("(window.__hoola.state.score || 0) >= 1", timeout=wait_s * 1000)
                except Exception:                       # noqa: BLE001  (reported below as score 0)
                    pass
                st = pg.evaluate("window.__hoola.state") or {}
                if out is not None:
                    out.mkdir(parents=True, exist_ok=True)
                    (out / "touch.png").write_bytes(pg.screenshot())
                pg.mouse.up()
                res.update(score=int(st.get("score") or 0), state=str(st.get("state") or ""), seconds=round(_t.time() - t0, 1))
                res["ok"] = res["score"] >= 1
            finally:
                b.close()
    except Exception as e:                              # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        srv.shutdown()
    return res


def self_test() -> dict[str, Any]:
    """The kit's own rules proved in the real engine (kit/selftest_main.gd): a guard's touch costs one life, landing on
    it removes it, a fall respawns, the touch stick and jump button work, a coin is taken, a lift carries the player."""
    import json
    from . import engine, template
    job = Path(tempfile.mkdtemp(prefix="hoola-3d-kit-"))
    try:
        (job / "proj").mkdir()
        files = {"main.gd": (_DIR / "selftest_main.gd").read_text(encoding="utf-8"), FILE: kit()}
        for name, txt in template.files("Hoola3D self-test", "landscape", files).items():
            (job / "proj" / name).write_text(txt, encoding="utf-8")
        engine._run(job, ["--path", "proj", "--import"], "import.log", 120)
        _c, log_txt, timed_out = engine._run(job, ["--path", "proj", "--fixed-fps", "60", "--quit-after", "4000"], "kit.log", 240)
    finally:
        shutil.rmtree(job, ignore_errors=True)
    got: dict[str, Any] = {}
    for ln in (log_txt or "").splitlines():
        if ln.startswith("KITTEST "):
            try:
                got = json.loads(ln[8:])
            except ValueError:
                got = {}
    errs = engine.errors_in(log_txt or "")
    want = ("hit", "stomp", "fall", "touch", "coin", "lift")
    ok = bool(got) and not errs and all((got.get(k) or {}).get("ok") for k in want)
    return {"ok": ok, "errors": errs[:4] + ([] if got else ["the self-test did not report" + (" (timed out)" if timed_out else "")]),
            "checks": {k: got.get(k) for k in want}}


def play_through(job: Path) -> dict[str, Any]:
    """Hoola's test player (kit/proof_bot.gd) plays the proof game in the real engine with the keys a person uses.
    A pass = it WON: walked the route, collected at least the coins the goal needs, climbed both steps and stepped
    into the goal with lives left. The bot rides only in this throwaway copy, never in a build."""
    import json
    from . import engine
    bot = job / "proj_bot"
    shutil.rmtree(bot, ignore_errors=True)
    shutil.copytree(job / "proj", bot, ignore=shutil.ignore_patterns(".godot"))
    (bot / "proof_bot.gd").write_text((_DIR / "proof_bot.gd").read_text(encoding="utf-8"), encoding="utf-8")
    pg = bot / "project.godot"
    pg.write_text(pg.read_text(encoding="utf-8").replace('HoolaProbe="*res://hoola_probe.gd"',
                  'HoolaProbe="*res://hoola_probe.gd"\nProofBot="*res://proof_bot.gd"', 1), encoding="utf-8")
    engine._run(job, ["--path", "proj_bot", "--import"], "bot_import.log", 120)
    _c, log_txt, timed_out = engine._run(job, ["--path", "proj_bot", "--fixed-fps", "60", "--quit-after", "7000"],
                                         "bot.log", engine._env_int("GAME_SMOKE_TIMEOUT_S", 120) + 120)
    got: dict[str, Any] = {}
    for ln in (log_txt or "").splitlines():
        if ln.startswith("PROOFBOT "):
            try:
                got = json.loads(ln[9:])
            except ValueError:
                got = {}
    errs = engine.errors_in(log_txt or "")
    if not got:
        return {"ok": False, "why": "the test player did not report" + (" (timed out)" if timed_out else ""), "errors": errs[:4]}
    won = got.get("state") == 3 and got.get("coins", 0) >= 5 and got.get("hp", 0) > 0 and got.get("top_y", 0) >= 1.9
    return {"ok": bool(won and not errs), "errors": errs[:4], **got}


def newest_tenant() -> str:
    """Whose list a saved proof game goes to when no tenant is named: the one who made a game most recently."""
    from sqlalchemy import select
    from ..db import session
    from . import service as G
    G.ensure_table()
    with session() as s:
        t = s.scalars(select(G.GameProject.tenant_id).where(~G.GameProject.tenant_id.like("\\_\\_%", escape="\\"))
                      .order_by(G.GameProject.created_at.desc()).limit(1)).first()
    return t or "default"


def _keep(tenant: str, conv: str, job: Path, exp: dict, play: dict) -> dict[str, Any]:
    from ..db import now, session
    from . import service as G
    G.ensure_table()
    with session() as s:
        r = G.GameProject(tenant_id=tenant, conversation_id=conv, number=G._number(tenant), title=PROOF_TITLE,
                          brief=PROOF_BRIEF, orientation="landscape", status="done", stage="", pct=100,
                          design=PROOF_DESIGN, token=secrets.token_urlsafe(18), versions=[])
        s.add(r)
        s.flush()
        s.expunge(r)
    vdir = G._vdir(r, 1)
    shutil.rmtree(vdir, ignore_errors=True)
    vdir.mkdir(parents=True)
    for part in ("proj", "build", "shots"):
        if (job / part).is_dir():
            shutil.copytree(job / part, vdir / part)
    ver = {"n": 1, "at": now().isoformat(), "words": "", "ok": True, "task": "", "base": 0, "src": G._src_hash(vdir / "proj"),
           "bible": 0, "models": [], "assets": [], "packs": [FILE], "scenes": [],
           "notes": "Hoola's own 3D proof game, built from the Hoola3D kit. No model wrote its code.", "fixed": 0,
           "checks": [{"step": "guard", "ok": True, "errors": []}, {"step": "play_headless", "ok": True, "errors": []},
                      {"step": "export_web", "ok": True, "errors": []}, {"step": "playtest", "ok": True, "errors": []}],
           "errors": [], "files": ["hoola_3d.gd", "main.gd"], "shots": play.get("shots", []), "warnings": play.get("warnings", []),
           "numbers": {"fps_server": play.get("fps"), "load_s": play.get("load_s"),
                       "download_mb": round((exp.get("download_bytes") or 0) / 1048576, 1) or None, "build_s": exp.get("seconds")}}
    with session() as s:
        row = s.get(G.GameProject, r.id)
        row.versions = [ver]
        s.flush()
        v = G.view(row)
    return {"id": v["id"], "number": v["number"], "url": v.get("url") or v.get("play_url"), "numbers": ver["numbers"]}
