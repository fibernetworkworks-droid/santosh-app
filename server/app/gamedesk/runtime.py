"""v0.425 HOOLA RUNTIME (Hoola Game Engine plan Phase 8): Hoola's own modules inside her game, as ONE autoload
(HoolaRuntime, GDScript - runs on every export; a C++ GDExtension would need a build per platform and is not used):

- REPLAY: every input Hoola injects is recorded per physics frame, under a fixed random seed set before her game's
  own _ready - ONLY in Hoola's test runs (normal players keep the engine's own random start). A replay test plays the recording back and the game must end in the SAME state (a fingerprint of the
  probe state + every node's position). Same result = the game is deterministic and any bug the bot finds comes with a
  replay that reproduces it. A different result is NAMED with its likely cause (randomize(), the clock).
- BOT: an in-engine input bot (keys + taps, seeded) that runs headless at full speed - no browser - for fast checks
  between the browser QA farm's runs. Its run IS the replay.
- TELEMETRY (opt-in twice): OFF unless she switches it on for the project AND the player says yes on the in-game
  consent box; never for a game made for children; no personal data (a random install id kept on the device, game
  events and frame numbers only, no device ids, no IP stored); events go only to the game's own play-link host (the
  page's CSP allows nothing else); she can delete it all. Dashboard: installs, sessions by day, D1 / D7 retention from
  install cohorts, top events, the play funnel.
HoolaRuntime is Hoola's own file (guard.HOOLA_OWN): the model never writes it; only it may use HTTPRequest (telemetry),
and only to the URL baked in at build time."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import shutil
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_runtime.gd"
KIDS = re.compile(r"\b(child|children|kids?|toddler|preschool|nursery|bachch?[eo]|bachchon|bal ?khel|class [1-5]\b|ages? [3-9]\b)", re.I)
EVENT_RE = re.compile(r"^[a-z0-9_]{1,40}$")
INSTALL_RE = re.compile(r"^[0-9a-f]{8,32}$")
MAX_EVENTS = 60
MAX_BODY = 16 * 1024
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gameruntime")
_RATE: dict[str, deque] = defaultdict(deque)


class RuntimeError_(G.GameError):
    pass


class GameTelemetry(Base):
    __tablename__ = "game_telemetry"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("te"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    game_id: Mapped[str] = mapped_column(String(40), index=True)
    install: Mapped[str] = mapped_column(String(32), index=True)
    event: Mapped[str] = mapped_column(String(40), default="")
    value: Mapped[str] = mapped_column(String(40), default="")
    frame: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    day: Mapped[str] = mapped_column(String(10), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameTelemetry.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ HoolaRuntime (Hoola's own GDScript)
GD = '''extends Node
# HoolaRuntime (an autoload): Hoola's replay recorder, in-engine bot and opt-in telemetry. Written by Hoola Studio;
# do not edit. Replay / bot run only when Hoola's test runner starts the game with --hoola-bot / --hoola-replay.
const CFG := __CFG__
const CONSENT_FILE := "user://hoola_consent.cfg"
const KEYS := [KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN, KEY_SPACE, KEY_ENTER, KEY_A, KEY_D, KEY_W, KEY_S]
var frame := 0
var mode := ""
var end_frame := 0
var rec: Array = []
var replay: Array = []
var ri := 0
var held := {}
var brng := RandomNumberGenerator.new()
var consent := false
var decided := false
var install := ""
var _tq: Array = []
var _last_f := -1
var _tt := 0.0
var _tsent := 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--hoola-bot="):
			var p: PackedStringArray = a.substr(12).split(",")
			mode = "bot"
			brng.seed = int(p[0])
			end_frame = int(p[1]) if p.size() > 1 else 1200
		elif a.begins_with("--hoola-replay="):
			mode = "replay"
			var parsed = JSON.parse_string(Marshalls.base64_to_utf8(a.substr(15)))
			replay = parsed["events"] if parsed is Dictionary else []
			end_frame = int(parsed["frames"]) if parsed is Dictionary else 0
	if mode != "":
		# ONLY in Hoola's test runs: a fixed seed so a recorded play replays exactly. Normal players keep the engine's own
		# random start - their games must not repeat the same "random" pattern every session.
		seed(int(CFG["seed"]))
	if bool(CFG["telemetry"]) and mode == "":
		_tel_load()

# ---------------------------------------------------------------- replay + bot
func _key(code: int, pressed: bool) -> void:
	var e := InputEventKey.new()
	e.keycode = code
	e.physical_keycode = code
	e.pressed = pressed
	Input.parse_input_event(e)

func _tap(x: float, y: float, pressed: bool) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.position = Vector2(x, y)
	e.global_position = Vector2(x, y)
	e.pressed = pressed
	Input.parse_input_event(e)

func _do(ev: Array) -> void:
	if String(ev[1]) == "k":
		_key(int(ev[2]), bool(ev[3]))
	else:
		_tap(float(ev[2]), float(ev[3]), bool(ev[4]))

func _emit(ev: Array) -> void:
	rec.append(ev)
	_do(ev)

func _bot_step() -> void:
	for code in held.keys():
		if int(held[code]) <= frame:
			held.erase(code)
			_emit([frame, "k", code, false])
	if brng.randf() < 0.06:
		var code: int = KEYS[brng.randi_range(0, KEYS.size() - 1)]
		if not held.has(code):
			held[code] = frame + brng.randi_range(4, 30)
			_emit([frame, "k", code, true])
	if brng.randf() < 0.03:
		var vp := get_viewport().get_visible_rect().size
		var x := snappedf(brng.randf() * vp.x, 1.0)
		var y := snappedf(brng.randf() * vp.y, 1.0)
		_emit([frame, "m", x, y, true])
		_emit([frame, "m", x, y, false])

func _physics_process(_d: float) -> void:
	frame += 1
	if mode == "bot":
		_bot_step()
	elif mode == "replay":
		while ri < replay.size() and int(replay[ri][0]) == frame:
			_do(replay[ri])
			ri += 1
	if mode != "" and frame >= end_frame:
		_finish()

func _walk(n: Node, out: PackedStringArray) -> void:
	for c in n.get_children():
		if c == self:
			continue
		if c is Node2D:
			out.append("%s:%.2f,%.2f" % [c.name, c.global_position.x, c.global_position.y])
		elif c is Node3D:
			out.append("%s:%.2f,%.2f,%.2f" % [c.name, c.global_position.x, c.global_position.y, c.global_position.z])
		elif c is Control:
			out.append("%s:%.1f,%.1f" % [c.name, c.position.x, c.position.y])
		_walk(c, out)

func fingerprint() -> String:
	var out := PackedStringArray()
	var probe = get_node_or_null("/root/HoolaProbe")
	if probe != null:
		out.append(JSON.stringify(probe._state))
	_walk(get_tree().root, out)
	return "\\n".join(out).sha256_text()

func _finish() -> void:
	var probe = get_node_or_null("/root/HoolaProbe")
	var res := {"mode": mode, "frames": frame, "fp": fingerprint(), "events": rec.size() if mode == "bot" else replay.size(),
		"state": probe._state if probe != null else {}}
	if mode == "bot":
		res["replay"] = Marshalls.utf8_to_base64(JSON.stringify({"frames": end_frame, "events": rec}))
	print("HOOLA_RT " + JSON.stringify(res))
	mode = ""
	get_tree().quit()

# ---------------------------------------------------------------- telemetry (her switch + the player's yes)
func _tel_load() -> void:
	var cf := ConfigFile.new()
	if cf.load(CONSENT_FILE) == OK:
		decided = true
		consent = bool(cf.get_value("t", "consent", false))
		install = String(cf.get_value("t", "install", ""))
	if install == "":
		var r := RandomNumberGenerator.new()
		r.randomize()
		install = "%08x%08x" % [r.randi(), r.randi()]

func needs_consent() -> bool:
	return bool(CFG["telemetry"]) and not decided

func set_consent(yes: bool) -> void:
	consent = yes
	decided = true
	var cf := ConfigFile.new()
	cf.set_value("t", "consent", yes)
	cf.set_value("t", "install", install)
	cf.save(CONSENT_FILE)
	if yes:
		_tq.append({"e": "session_start", "f": frame})

func ask_consent(parent: Node) -> void:
	# a small box: may this game send anonymous play events? Yes / No (saved on this device)
	if not needs_consent():
		return
	var layer := CanvasLayer.new()
	layer.layer = 100
	var box := PanelContainer.new()
	var v := VBoxContainer.new()
	var l := Label.new()
	l.text = "Help improve this game?\\nSend anonymous play events (no name, no device id)."
	l.autowrap_mode = TextServer.AUTOWRAP_WORD
	l.custom_minimum_size = Vector2(280, 0)
	v.add_child(l)
	var h := HBoxContainer.new()
	for pair in [["Yes", true], ["No", false]]:
		var b := Button.new()
		b.text = String(pair[0])
		var yes: bool = pair[1]
		b.pressed.connect(func(): set_consent(yes); layer.queue_free())
		h.add_child(b)
	v.add_child(h)
	box.add_child(v)
	box.position = Vector2(20, 20)
	layer.add_child(box)
	parent.add_child(layer)

func _process(delta: float) -> void:
	if not (bool(CFG["telemetry"]) and consent and String(CFG["url"]) != ""):
		return
	_tt += delta
	if _tt >= 1.0:
		_tt = 0.0
		var probe = get_node_or_null("/root/HoolaProbe")
		if probe != null:
			for ev in probe._events:
				if int(ev["f"]) > _last_f:
					_last_f = int(ev["f"])
					_tq.append({"e": String(ev["e"]).to_lower().left(40), "f": int(ev["f"])})
	_tsent += delta
	if _tq.size() >= 20 or (_tsent >= 15.0 and _tq.size() > 0):
		_flush()

func _flush() -> void:
	_tsent = 0.0
	var batch := _tq.slice(0, 60)
	_tq = _tq.slice(60)
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(func(_r, _c, _h, _b): http.queue_free())
	http.request(String(CFG["url"]), ["Content-Type: application/json"], HTTPClient.METHOD_POST,
		JSON.stringify({"install": install, "consent": true, "version": int(CFG["version"]), "events": batch}))
'''


def gd(cfg: dict) -> str:
    from .bible import _gd
    return GD.replace("__CFG__", _gd({"seed": int(cfg.get("seed", 20251101)), "telemetry": bool(cfg.get("telemetry")),
                                       "url": str(cfg.get("url") or ""), "version": int(cfg.get("version", 0))}))


# ================================================================ settings per Studio project
def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _game(tenant: str, game_id: str):
    with session() as s:
        g = s.get(G.GameProject, game_id)
        if g is None or g.tenant_id != tenant:
            raise RuntimeError_("Game nahi mila.")
        s.expunge(g)
    return g


def kid_game(design: str) -> bool:
    return bool(KIDS.search(design or ""))


def settings(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    rt = dict(st.runtime or {})
    g = _game(tenant, st.game_id)
    return {"on": bool(rt.get("on", True)), "telemetry": bool(rt.get("telemetry", False)), "kids": kid_game(g.design),
            "tests": list(rt.get("tests") or [])[-10:], "studio_id": st.id, "game_id": st.game_id,
            "telemetry_url": (G.play_url(g.token) + "t") if g.token else ""}


def set_runtime(tenant: str, ref: str, on: bool | None = None, telemetry: bool | None = None) -> dict[str, Any]:
    from . import studio as S
    st = _studio(tenant, ref)
    g = _game(tenant, st.game_id)
    if telemetry and kid_game(g.design):
        raise RuntimeError_("Yeh game bachchon ke liye hai - telemetry chalu nahi hogi (bachchon ka data maa-baap ki "
                            "marzi ke bina nahi, DPDP).")
    with session() as s:
        row = s.get(S.GameStudio, st.id)
        rt = dict(row.runtime or {"on": True, "telemetry": False, "tests": []})
        if on is not None:
            rt["on"] = bool(on)
        if telemetry is not None:
            rt["telemetry"] = bool(telemetry)
        row.runtime = rt
    return settings(tenant, ref)


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    """HoolaRuntime goes into every build of a Studio project with the runtime on (the default)."""
    from . import studio as S
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        rt = dict(st.runtime or {"on": True})
        g = s.get(G.GameProject, game_id)
        if not rt.get("on", True) or g is None:
            return None
        tel = bool(rt.get("telemetry")) and not kid_game(g.design) and bool(g.token)
        ver = max([v.get("n", 0) for v in (g.versions or [])] or [0]) + 1
        return gd({"telemetry": tel, "url": (G.play_url(g.token) + "t") if tel else "", "version": ver}), {}


# ================================================================ the replay test (real engine)
RANDOM_CAUSES = re.compile(r"\brandomize\s*\(|\bTime\s*\.\s*get_(?:ticks|unix|datetime|time)|\bOS\s*\.\s*get_(?:ticks|unix)")


def _run_mode(job: Path, arg: str, frames: int) -> dict:
    from . import engine
    code, logtxt, to = engine._run(job, ["--path", "proj", "--fixed-fps", "60", "--quit-after", str(frames + 300), "--", arg],
                                   f"rt_{arg[8:12]}.log", 180)
    m = re.search(r"HOOLA_RT (\{.*\})", logtxt or "")
    errs = engine.errors_in(logtxt or "")
    if not m:
        return {"ok": False, "errors": errs or ["the game never reached the end of the run (crash, freeze or quit)"], "log": (logtxt or "")[-300:]}
    out = json.loads(m.group(1))
    out["errors"] = errs
    out["ok"] = True
    return out


def replay_lab(proj_src: Path, job: Path, title: str, orientation: str, seed: int = 7, frames: int = 900) -> dict:
    """Copy the game's project, make sure HoolaRuntime is in it, run the bot (record), run the bot again (same seed),
    play the recording back, and compare the three end states."""
    from . import template
    shutil.rmtree(job, ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    scripts = {p.name: p.read_text(encoding="utf-8") for p in proj_src.glob("*.gd") if p.name != "hoola_probe.gd"}
    scripts[FILE] = gd({"telemetry": False})
    for name, txt in template.files(title or "Hoola game", orientation, scripts).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    for extra in ("assets",):
        if (proj_src / extra).is_dir():
            shutil.copytree(proj_src / extra, job / "proj" / extra)
    a = _run_mode(job, f"--hoola-bot={seed},{frames}", frames)
    if not a["ok"]:
        return {"verdict": "FAIL", "deterministic": None, "errors": a["errors"], "note": "the bot run did not finish"}
    b = _run_mode(job, f"--hoola-bot={seed},{frames}", frames)
    c = _run_mode(job, f"--hoola-replay={a['replay']}", frames)
    same_bot = b.get("ok") and b.get("fp") == a["fp"]
    same_replay = c.get("ok") and c.get("fp") == a["fp"]
    from .template import HOOLA_OWN
    causes = sorted({m.group(0) for n, s in scripts.items() if n not in HOOLA_OWN for m in RANDOM_CAUSES.finditer(s)})
    errors = sorted(set(a.get("errors", []) + b.get("errors", []) + c.get("errors", [])))[:6]
    checks = [{"check": "the bot played to the end", "ok": True, "note": f"{a['frames']} frames, {a['events']} inputs (seed {seed})"},
              {"check": "same seed twice = same end", "ok": bool(same_bot), "note": "the bot run repeated gives the same end state"
               if same_bot else "a second run with the same seed ended differently"},
              {"check": "the replay reproduces the run", "ok": bool(same_replay),
               "note": "playing the recorded inputs back ends in the same state" if same_replay else
               ("the replay ended differently - the game uses randomness or time outside Hoola's seed"
                + (f": {', '.join(causes)}" if causes else ""))},
              {"check": "no script errors", "ok": not errors, "note": "; ".join(errors) if errors else "none in any of the three runs"}]
    ok = all(c_["ok"] for c_ in checks)
    return {"verdict": "PASS" if ok else "FAIL", "deterministic": bool(same_bot and same_replay), "checks": checks,
            "frames": a["frames"], "inputs": a["events"], "fingerprint": a["fp"][:16], "replay_b64": a["replay"],
            "state": a.get("state"), "causes": causes, "errors": errors}


def replay_test(tenant: str, ref: str, seed: int = 7, frames: int = 900) -> dict[str, Any]:
    from . import studio as S
    st = _studio(tenant, ref)
    g = _game(tenant, st.game_id)
    good = G._good(g)
    if not good:
        raise RuntimeError_("Pehle game ka ek chalne wala version chahiye.")
    n = good[-1]["n"]
    src = G._vdir(g, n) / "proj"
    job = G._pdir(tenant, g.id) / "runtime" / f"v{n}"
    t0 = time.time()
    res = replay_lab(src, job, g.title, g.orientation, seed=seed, frames=frames)
    rdir = G._pdir(tenant, g.id) / "replays"
    rdir.mkdir(parents=True, exist_ok=True)
    rid = f"r{int(time.time())}"
    if res.get("replay_b64"):
        (rdir / f"{rid}.json").write_text(base64.b64decode(res["replay_b64"]).decode(), encoding="utf-8")
    row = {"at": now().isoformat(), "version": n, "seed": seed, "verdict": res["verdict"], "deterministic": res.get("deterministic"),
           "checks": res.get("checks", []), "frames": res.get("frames"), "inputs": res.get("inputs"), "replay": rid,
           "seconds": round(time.time() - t0, 1), "errors": res.get("errors", [])}
    with session() as s:
        r2 = s.get(S.GameStudio, st.id)
        rt = dict(r2.runtime or {"on": True, "telemetry": False})
        rt["tests"] = (list(rt.get("tests") or []) + [row])[-10:]
        r2.runtime = rt
    return row


def start_replay_test(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    _POOL.submit(_safe_test, tenant, st.id)
    return {"started": True, "say": "Replay test chal raha hai (bot khelega, phir uska replay)."}


def _safe_test(tenant: str, sid: str) -> None:
    try:
        replay_test(tenant, sid)
    except Exception:                                   # noqa: BLE001
        log.exception("replay test %s", sid)


def replay_file(tenant: str, ref: str, rid: str) -> Path | None:
    if not re.fullmatch(r"r\d{6,12}", rid or ""):
        return None
    st = _studio(tenant, ref)
    p = G._pdir(tenant, st.game_id) / "replays" / f"{rid}.json"
    return p if p.is_file() else None


# ================================================================ telemetry: ingest + dashboard + delete
def _rate_ok(key: str, limit: int = 30, window: float = 600.0) -> bool:
    q = _RATE[key]
    t = time.time()
    while q and q[0] < t - window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(t)
    return True


def ingest(token: str, raw: bytes) -> int:
    """POST /play/<token>/t from the game. Always answers 204 (never tells a stranger whether telemetry is on);
    stores only when her switch is on, the player consented, the game is not for children, and the body is clean."""
    from . import studio as S
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,48}", token or "") or len(raw or b"") > MAX_BODY:
        return 0
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:                                   # noqa: BLE001
        return 0
    install = str(body.get("install") or "")
    if body.get("consent") is not True or not INSTALL_RE.match(install) or not _rate_ok(f"{token}:{install}"):
        return 0
    ensure_table()
    with session() as s:
        g = s.scalars(select(G.GameProject).where(G.GameProject.token == token)).first()
        if g is None:
            return 0
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.game_id == g.id)).first()
        if st is None or not (st.runtime or {}).get("telemetry") or kid_game(g.design):
            return 0
        today = datetime.now(timezone.utc).date().isoformat()
        n = 0
        for ev in (body.get("events") or [])[:MAX_EVENTS]:
            name = str((ev or {}).get("e") or "")
            if not EVENT_RE.match(name):
                continue
            s.add(GameTelemetry(tenant_id=g.tenant_id, game_id=g.id, install=install, event=name,
                                value=str((ev or {}).get("v") or "")[:40], frame=int((ev or {}).get("f") or 0) if str((ev or {}).get("f") or "0").lstrip("-").isdigit() else 0,
                                version=int(body.get("version") or 0) if str(body.get("version") or "0").isdigit() else 0, day=today))
            n += 1
    return n


def dashboard(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    ensure_table()
    with session() as s:
        rows = s.execute(select(GameTelemetry.install, GameTelemetry.event, GameTelemetry.day)
                         .where(GameTelemetry.tenant_id == tenant, GameTelemetry.game_id == st.game_id)).all()
    first: dict[str, str] = {}
    days_of: dict[str, set] = defaultdict(set)
    events: dict[str, int] = defaultdict(int)
    sessions_by_day: dict[str, int] = defaultdict(int)
    reached: dict[str, set] = defaultdict(set)
    for inst, ev, day in rows:
        first[inst] = min(first.get(inst, day), day)
        days_of[inst].add(day)
        events[ev] += 1
        reached[ev].add(inst)
        if ev == "session_start":
            sessions_by_day[day] += 1
    today = datetime.now(timezone.utc).date()

    def retention(k: int) -> dict:
        cohort = [i for i, d in first.items() if date.fromisoformat(d) <= today - timedelta(days=k)]
        if not cohort:
            return {"share": None, "cohort": 0, "note": f"no player is {k} days old yet"}
        back = sum(1 for i in cohort if (date.fromisoformat(first[i]) + timedelta(days=k)).isoformat() in days_of[i])
        return {"share": round(back / len(cohort), 3), "cohort": len(cohort)}
    funnel = [{"step": e, "players": len(reached.get(e, set()))} for e in ("session_start", "playing", "level_up", "game_over", "win")]
    return {"installs": len(first), "events": sum(events.values()), "top": sorted(events.items(), key=lambda x: -x[1])[:10],
            "sessions_by_day": dict(sorted(sessions_by_day.items())[-14:]), "d1": retention(1), "d7": retention(7),
            "funnel": funnel, "telemetry_on": bool((st.runtime or {}).get("telemetry")),
            "privacy": "random install id on the device, game events and frame numbers only; no names, device ids or IP"}


def delete_telemetry(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    ensure_table()
    with session() as s:
        n = 0
        for row in s.scalars(select(GameTelemetry).where(GameTelemetry.tenant_id == tenant, GameTelemetry.game_id == st.game_id)).all():
            s.delete(row)
            n += 1
    return {"deleted": n}
