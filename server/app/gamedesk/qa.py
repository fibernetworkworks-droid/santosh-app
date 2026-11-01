"""v0.415 QA FARM (Hoola Game Engine plan, Phase 5): Hoola's bots play every build the way players would, on phone-
like speeds, keep the screens that she approved as GOLDEN, measure speed, and file BUGS with the exact way to repeat
them. No model calls and no money: Chromium + the web build + Hoola's probe.

- BOTS (seeded, so a run can be repeated exactly): idle (no input: does the game hold up alone, and the golden title
  screen), monkey (taps, swipes and keys at random), tapper (fast taps), keys (arrows + space), restarter (plays until
  the game says game_over, then restarts it - three times). Every action is logged: the log IS the replay.
- PROFILES: desktop (1x CPU), mid_phone (4x slower CPU, phone screen, touch), low_phone (6x). Numbers from the engine
  itself (fps, frames, memory) via the probe; the server's software graphics are slower than a phone's, so fps is
  compared with the last run, never with a fixed number alone.
- GOLDEN: the idle bot's screen after start, compared pixel by pixel (small picture) with the screen she approved;
  more than 3 % changed = "looks different", her eyes decide. No golden yet = NOT ASSESSED, never a pass.
- BUGS (`game_bugs`): a crash / script error / freeze / blank screen / broken restart becomes a numbered bug with a
  signature (repeats are counted, not duplicated), the bot + seed + profile + version that found it, the errors and
  screenshots. "Fix" makes a board task whose criterion is that the same bot no longer finds it; the next QA run
  checks every open bug's repro: gone = FIXED (verified by the bot), back on a fixed bug = REGRESSION (reopened).
The verdict (PASS / CONCERNS / FAIL / NOT ASSESSED) is counted in code."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import random
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from . import playtest as P
from . import service as G

log = logging.getLogger("santosh.gamedesk")

PROFILES = {"desktop": {"cpu": 1, "touch": False, "scale": 1}, "mid_phone": {"cpu": 4, "touch": True, "scale": 2},
            "low_phone": {"cpu": 6, "touch": True, "scale": 2}}
BOTS = ("idle", "monkey", "tapper", "keys", "restarter")
PLAN = [("idle", "desktop", 1, 6), ("monkey", "mid_phone", 1, 12), ("monkey", "desktop", 2, 12), ("keys", "desktop", 1, 10),
        ("restarter", "desktop", 1, 20), ("tapper", "low_phone", 1, 10)]
GOLDEN_DIFF = 0.03
FPS_DROP = 0.25
KEEP_RUNS = 12
SEV = ("crash", "blocker", "major", "minor", "visual", "perf")


class QaError(G.GameError):
    pass


class GameBug(Base):
    __tablename__ = "game_bugs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="major")
    status: Mapped[str] = mapped_column(String(12), default="open")    # open|fixing|fixed|wontfix|duplicate
    signature: Mapped[str] = mapped_column(String(40), default="", index=True)
    source: Mapped[str] = mapped_column(String(12), default="bot")      # bot|golden|perf|her|nightly
    repro: Mapped[dict] = mapped_column(JSON, default=dict)             # {bot, seed, profile, version, steps}
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)          # {errors, shots, numbers}
    seen: Mapped[int] = mapped_column(Integer, default=1)
    first_version: Mapped[int] = mapped_column(Integer, default=0)
    last_version: Mapped[int] = mapped_column(Integer, default=0)
    regression: Mapped[int] = mapped_column(Integer, default=0)         # times it came back after a fix
    task: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameBug.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ---------------------------------------------------------------- one bot, one profile
def _actions(bot: str, seed: int, seconds: int, vw: int, vh: int) -> list[dict[str, Any]]:
    """The bot's whole input plan up front (seeded): the plan IS the replay."""
    rnd = random.Random(f"{bot}:{seed}")
    acts: list[dict[str, Any]] = []
    t = 0.0
    end = seconds * 1000.0
    keys = ["Space", "Enter", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]
    while t < end and bot != "idle":
        if bot == "tapper":
            acts.append({"t": int(t), "a": "tap", "x": rnd.randint(20, vw - 20), "y": rnd.randint(20, vh - 20)})
            t += rnd.uniform(80, 180)
        elif bot == "keys":
            acts.append({"t": int(t), "a": "key", "k": rnd.choice(keys), "hold": rnd.randint(40, 400)})
            t += rnd.uniform(120, 420)
        elif bot == "restarter":
            acts.append({"t": int(t), "a": "tap", "x": vw // 2 + rnd.randint(-30, 30), "y": int(vh * 0.6) + rnd.randint(-30, 30)})
            t += rnd.uniform(250, 600)
        else:                                            # monkey
            r = rnd.random()
            if r < 0.45:
                acts.append({"t": int(t), "a": "tap", "x": rnd.randint(10, vw - 10), "y": rnd.randint(10, vh - 10)})
            elif r < 0.7:
                acts.append({"t": int(t), "a": "key", "k": rnd.choice(keys), "hold": rnd.randint(30, 500)})
            else:
                x0, y0 = rnd.randint(10, vw - 10), rnd.randint(10, vh - 10)
                acts.append({"t": int(t), "a": "swipe", "x": x0, "y": y0, "x2": rnd.randint(10, vw - 10), "y2": rnd.randint(10, vh - 10)})
            t += rnd.uniform(90, 500)
    return acts[:400]


def _thumb(png: bytes):
    from PIL import Image
    return Image.open(io.BytesIO(png)).convert("RGB").resize((96, 160))


def diff_share(a: bytes, b: bytes) -> float:
    """Share of pixels that changed between two screenshots (compared small, so a 1-pixel jitter is not a change)."""
    from PIL import Image, ImageChops
    ia, ib = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    size = (120, int(120 * ia.size[1] / max(1, ia.size[0])))
    d = ImageChops.difference(ia.resize(size), ib.resize(size)).convert("L")
    hist = d.histogram()
    changed = sum(hist[24:])
    return round(changed / max(1, sum(hist)), 4)


def run_bot(build: Path, out: Path, orientation: str, bot: str, seed: int = 1, seconds: int = 10,
            profile: str = "desktop", actions: list | None = None) -> dict[str, Any]:
    """Play the build with one bot on one profile. Returns the numbers, the probe's state / events, the errors, the
    screenshots and the action log (replay)."""
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    pr = PROFILES.get(profile, PROFILES["desktop"])
    vw, vh = {"portrait": (360, 640), "landscape": (640, 360), "square": (512, 512)}.get(orientation, (360, 640))
    acts = actions if actions is not None else _actions(bot, seed, seconds, vw, vh)
    res: dict[str, Any] = {"bot": bot, "seed": seed, "profile": profile, "ok": False, "errors": [], "warnings": [],
                           "shots": [], "fps": [], "load_s": None, "frames": 0, "state": {}, "events": [],
                           "game_overs": 0, "restarts": 0, "actions": acts, "stuck_s": 0.0}
    srv = P._serve(build)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(**P._launch_kw())
            try:
                ctx = b.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=pr["scale"], has_touch=pr["touch"])
                pg = ctx.new_page()
                if pr["cpu"] > 1:
                    try:
                        ctx.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": pr["cpu"]})
                    except Exception as e:              # noqa: BLE001
                        res["warnings"].append(f"CPU slow-down not available ({type(e).__name__})")
                msgs: list[str] = []
                pg.on("console", lambda m: msgs.append(m.text[:300]) if m.type in ("error", "warning") else None)
                pg.on("pageerror", lambda e: msgs.append("page error: " + str(e)[:300]))
                t0 = time.time()
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/index.html")
                try:
                    pg.wait_for_function("window.__hoola && window.__hoola.ready", timeout=90000)
                except Exception:
                    res["errors"].append("the game did not start within 90 seconds")
                    return res
                res["load_s"] = round(time.time() - t0, 1)
                # keys only reach the game when its canvas has focus (found live: the keys bot pressed into nothing)
                pg.evaluate("(() => { const c = document.querySelector('canvas'); if (c) { c.tabIndex = 0; c.focus(); } })()")
                pg.wait_for_timeout(1500)
                first = pg.evaluate("window.__hoola") or {}
                shot = pg.screenshot()
                (out / "start.png").write_bytes(shot)
                res["shots"].append("start.png")
                last_thumb, still_since = None, None
                start = time.time()
                i = 0
                next_sample = 0.0
                over_seen = 0
                while True:
                    el = (time.time() - start) * 1000
                    if el > seconds * 1000 + 300:
                        break
                    while i < len(acts) and acts[i]["t"] <= el:
                        a = acts[i]
                        i += 1
                        if a["a"] == "tap":
                            if pr["touch"]:
                                pg.touchscreen.tap(a["x"], a["y"])
                            else:
                                pg.mouse.click(a["x"], a["y"])
                        elif a["a"] == "key":
                            pg.keyboard.down(a["k"])
                            pg.wait_for_timeout(min(a.get("hold", 80), 600))
                            pg.keyboard.up(a["k"])
                        elif a["a"] == "swipe":
                            pg.mouse.move(a["x"], a["y"])
                            pg.mouse.down()
                            pg.mouse.move(a["x2"], a["y2"], steps=6)
                            pg.mouse.up()
                    if el >= next_sample:
                        next_sample = el + 1000
                        h = pg.evaluate("window.__hoola") or {}
                        if h.get("fps"):
                            res["fps"].append(int(h["fps"]))
                        ev = h.get("events") or []
                        overs = sum(1 for e in ev if (e or {}).get("e") == "game_over")
                        if bot == "restarter" and overs > over_seen:
                            over_seen = overs
                            pg.wait_for_timeout(600)
                            pg.mouse.click(vw // 2, vh // 2)
                            pg.keyboard.press("Space")
                            res["restarts"] += 1
                        th = hashlib.md5(pg.screenshot(type="jpeg", quality=30)).hexdigest()
                        if th == last_thumb and acts and bot != "idle":
                            still_since = still_since or time.time()
                        else:
                            if still_since:
                                res["stuck_s"] = max(res["stuck_s"], round(time.time() - still_since, 1))
                            still_since = None
                        last_thumb = th
                    pg.wait_for_timeout(40)
                if still_since:
                    res["stuck_s"] = max(res["stuck_s"], round(time.time() - still_since, 1))
                h = pg.evaluate("window.__hoola") or {}
                shot = pg.screenshot()
                (out / "end.png").write_bytes(shot)
                res["shots"].append("end.png")
                res["frames"] = int(h.get("frames") or 0) - int(first.get("frames") or 0)
                res["state"] = h.get("state") or {}
                res["events"] = [e.get("e") for e in (h.get("events") or []) if isinstance(e, dict)][-30:]
                res["game_overs"] = res["events"].count("game_over")
                res["mem_mb"] = round((h.get("mem") or 0) / 1048576, 1) or None
                script = [m for m in msgs if not any(n in m for n in P.NOISE) and
                          ("SCRIPT ERROR" in m or "ERROR:" in m or m.startswith("page error"))]
                res["errors"] += list(dict.fromkeys(script))[:8]
                if res["frames"] <= 0:
                    res["errors"].append("the game froze (no new frames while the bot played)")
                if P.blank(shot) and P.blank((out / "start.png").read_bytes()):
                    res["errors"].append("the screen stayed empty (one colour)")
                if res["stuck_s"] >= 6 and bot != "idle":
                    res["warnings"].append(f"the screen did not change for {res['stuck_s']} s while the bot was playing")
                if bot == "restarter" and res["game_overs"] and res["restarts"] and res["game_overs"] < 2 and seconds >= 15:
                    res["warnings"].append("after game over, a restart did not lead to another game")
                res["ok"] = not res["errors"]
                return res
            finally:
                b.close()
    except Exception as e:                              # noqa: BLE001
        res["errors"].append(f"the bot could not run: {type(e).__name__}: {str(e)[:200]}")
        return res
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- a whole farm run
def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _qdir(tenant: str, sid: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "qa" / sid


def _sig(kind: str, text: str) -> str:
    t = re.sub(r"\d+", "#", (text or "").lower())
    t = re.sub(r"0x[0-9a-f#]+|res://[\w/.]+:\#|\s+", " ", t)[:200]
    return hashlib.sha1(f"{kind}|{t}".encode()).hexdigest()[:16]


def _bug_for(run: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for e in run["errors"]:
        sev = "crash" if ("SCRIPT ERROR" in e or "page error" in e) else "blocker"
        title = ("Script error: " + re.sub(r"^.*?SCRIPT ERROR:\s*", "", e)[:120]) if "SCRIPT ERROR" in e else e[:140]
        out.append({"severity": sev, "title": title, "signature": _sig("err", e), "errors": [e]})
    for w in run["warnings"]:
        if "restart did not" in w:
            out.append({"severity": "major", "title": "Restart after game over does not start a new game",
                        "signature": _sig("restart", ""), "errors": [w]})
        elif "did not change" in w:
            out.append({"severity": "minor", "title": "Screen stops reacting while playing", "signature": _sig("stuck", run["bot"]),
                        "errors": [w]})
    return out


def _number(s, sid: str) -> str:
    n = len(s.scalars(select(GameBug.id).where(GameBug.studio_id == sid)).all())
    return f"B-{n + 1:04d}"


def file_bug(tenant: str, sid: str, b: dict[str, Any], repro: dict[str, Any], version: int, shots: list[str],
             source: str = "bot") -> tuple[str, str]:
    """New bug, or a repeat counted on the one with the same signature. Returns (number, what): new|seen|regression."""
    ensure_table()
    with session() as s:
        row = s.scalars(select(GameBug).where(GameBug.studio_id == sid, GameBug.signature == b["signature"])).first()
        if row is not None:
            row.seen = (row.seen or 0) + 1
            row.last_version = max(row.last_version or 0, version)
            row.evidence = {**(row.evidence or {}), "errors": b["errors"][:6], "shots": shots[:3], "at": now().isoformat()}
            what = "seen"
            if row.status in ("fixed",):
                row.status, row.regression, what = "open", (row.regression or 0) + 1, "regression"
            row.updated_at = now()
            return row.number, what
        row = GameBug(tenant_id=tenant, studio_id=sid, number=_number(s, sid), title=b["title"][:200], severity=b["severity"],
                      signature=b["signature"], source=source, repro={**repro, "version": version},
                      evidence={"errors": b["errors"][:6], "shots": shots[:3], "at": now().isoformat()},
                      first_version=version, last_version=version)
        s.add(row)
        s.flush()
        return row.number, "new"


def _debug_build(proj: Path, qd: Path) -> tuple[Path | None, str]:
    """A DEBUG web export of the project for the bots (release web builds print no script errors)."""
    from . import engine
    job = qd / "job"
    shutil.rmtree(job, ignore_errors=True)
    shutil.copytree(proj, job / "proj", ignore=shutil.ignore_patterns(".godot"))
    try:
        sm = engine.smoke(job)
        if not sm.get("ok"):
            return None, "the project does not start: " + "; ".join(sm.get("errors", [])[:2])
        ex = engine.export_web(job, debug=True)
        if not ex.get("ok"):
            return None, "; ".join(ex.get("errors", [])[:2])
        return job / "build_debug", ""
    except engine.EngineError as e:
        return None, str(e)


def farm(tenant: str, ref: str, proj: Path | None = None, version: int = 0, plan: list | None = None,
         build: Path | None = None) -> dict[str, Any]:
    """Every bot on its profile against one DEBUG build of the project (the live version's if none given); bugs filed,
    repros of open bugs re-run, golden compared, speed compared with the last run. Returns the report (kept on the
    project). `build` = an already exported build to play as is (tests): its name must say debug, else the report
    notes that script errors may be hidden."""
    from . import studio as S
    ensure_table()
    r = _studio(tenant, ref)
    g = G._get(tenant, r.game_id) if r.game_id else None
    if proj is None and build is None:
        good = G._good(g) if g else []
        if not good:
            return _keep(r, {"verdict": "NOT ASSESSED", "missing": ["no playable version yet"], "runs": []})
        version = good[-1]["n"]
        proj = G._vdir(g, version) / "proj"
    run_id = now().strftime("%Y%m%d%H%M%S")
    qd = _qdir(tenant, r.id) / run_id
    hidden = ""
    if build is None:
        build, why = _debug_build(proj, qd)
        if build is None:
            return _keep(r, {"verdict": "NOT ASSESSED", "missing": [why or "no debug build"], "runs": [], "version": version,
                             "id": run_id})
    elif "debug" not in build.name:
        hidden = "this run played a release build: script errors are hidden from the bots"
    if not (build / "index.html").is_file():
        return _keep(r, {"verdict": "NOT ASSESSED", "missing": [f"the web build of version {version} is not there"],
                         "runs": [], "version": version})
    runs: list[dict[str, Any]] = []
    filed: list[dict[str, str]] = []
    with session() as s:
        open_bugs = [b for b in s.scalars(select(GameBug).where(GameBug.studio_id == r.id,
                                                              GameBug.status.in_(("open", "fixing")))).all()
                     if (b.repro or {}).get("bot")]
        repro_jobs = [{"number": b.number, "bot": b.repro["bot"], "seed": b.repro.get("seed", 1), "profile": b.repro.get("profile", "desktop"),
                       "steps": b.repro.get("steps"), "signature": b.signature} for b in open_bugs][:6]
    for j, (bot, prof, seed, secs) in enumerate(plan or PLAN):
        res = run_bot(build, qd / f"{j}_{bot}_{prof}", g.orientation if g else "portrait", bot, seed, secs, prof)
        res["dir"] = f"{run_id}/{j}_{bot}_{prof}"
        runs.append(res)
        for b in _bug_for(res):
            n, what = file_bug(tenant, r.id, b, {"bot": bot, "seed": seed, "profile": prof, "seconds": secs,
                                                 "steps": res["actions"][:200]}, version,
                               [f"{res['dir']}/{x}" for x in res["shots"]])
            filed.append({"bug": n, "what": what, "title": b["title"]})
    # every open bug's own repro, exactly as it was found
    fixed_now: list[str] = []
    for rj in repro_jobs:
        res = run_bot(build, qd / f"repro_{rj['number']}", g.orientation if g else "portrait", rj["bot"], int(rj["seed"]),
                      10, rj["profile"], actions=rj.get("steps"))
        sigs = {b["signature"] for b in _bug_for(res)}
        if res["errors"][:1] and res["errors"][0].startswith("the bot could not run"):
            continue
        if rj["signature"] not in sigs:
            with session() as s:
                row = s.scalars(select(GameBug).where(GameBug.studio_id == r.id, GameBug.number == rj["number"])).first()
                if row is not None and row.status in ("open", "fixing"):
                    row.status, row.updated_at = "fixed", now()
                    row.evidence = {**(row.evidence or {}), "fixed_in": version, "fixed_at": now().isoformat()}
                    fixed_now.append(row.number)
    # golden
    golden = _golden_check(r, runs, qd)
    # speed vs the last run
    prev = next((x for x in reversed(_runs(r)) if x.get("fps_avg")), None)
    fps = [f for x in runs for f in x["fps"]]
    fps_avg = round(sum(fps) / len(fps), 1) if fps else None
    perf = {"fps_avg": fps_avg, "fps_min": min(fps) if fps else None,
            "load_s": max((x["load_s"] or 0) for x in runs) if runs else None,
            "mid_phone_fps": _avg([f for x in runs if x["profile"] == "mid_phone" for f in x["fps"]])}
    concerns, blockers, missing = [], [], []
    if perf["fps_avg"] and prev and prev.get("fps_avg") and perf["fps_avg"] < prev["fps_avg"] * (1 - FPS_DROP):
        concerns.append(f"speed dropped: {prev['fps_avg']} -> {perf['fps_avg']} fps on the same bots")
        n, what = file_bug(tenant, r.id, {"severity": "perf", "title": f"Slower than the last run ({prev['fps_avg']} -> {perf['fps_avg']} fps)",
                                          "signature": _sig("perf", str(version)), "errors": []}, {}, version, [], source="perf")
        filed.append({"bug": n, "what": what, "title": "speed dropped"})
    crashed = [x for x in runs if x["errors"]]
    if crashed:
        blockers.append(f"{len(crashed)} of {len(runs)} bot runs hit an error / freeze")
    if any("could not run" in e for x in runs for e in x["errors"]):
        missing.append("Chromium / Playwright could not run on this server")
    for x in runs:
        concerns += [f"{x['bot']} on {x['profile']}: {w}" for w in x["warnings"]]
    if golden.get("verdict") == "different":
        concerns.append(f"the start screen looks {round(golden['diff'] * 100, 1)}% different from the golden one")
    elif golden.get("verdict") == "none":
        concerns.append("no golden start screen approved yet (visual check NOT ASSESSED)")
    if hidden:
        concerns.append(hidden)
    if not any(x["state"] or x["events"] for x in runs):
        concerns.append("the game reports no state / score / events to Hoola's probe (game-over and restart not checked)")
    with session() as s:
        regress = [b.number for b in s.scalars(select(GameBug).where(GameBug.studio_id == r.id, GameBug.status == "open",
                                                                    GameBug.regression > 0)).all()]
    if regress:
        blockers.append("regression: " + ", ".join(regress[:4]) + " came back after a fix")
    none_ran = bool(runs) and all(any("could not run" in e for e in x["errors"]) for x in runs)
    verdict = "NOT ASSESSED" if (none_ran or not runs) else "FAIL" if blockers else "CONCERNS" if concerns else "PASS"
    report = {"id": run_id, "at": now().isoformat(), "version": version, "verdict": verdict, "blockers": blockers,
              "concerns": concerns[:12], "missing": missing, "filed": filed, "fixed": fixed_now, "golden": golden,
              "perf": perf, "fps_avg": fps_avg,
              "runs": [{k: x.get(k) for k in ("bot", "seed", "profile", "ok", "errors", "warnings", "load_s", "frames",
                                              "state", "events", "game_overs", "restarts", "stuck_s", "mem_mb", "dir")}
                       | {"fps": _avg(x["fps"]), "shots": [f"{x['dir']}/{s}" for s in x["shots"]]} for x in runs]}
    shutil.rmtree(qd / "job", ignore_errors=True)       # the debug build (~40 MB) is not kept
    _prune(tenant, r.id)
    S._decide(r, f"QA v{version}: {verdict}", "; ".join(blockers + concerns[:3] + missing)[:500], by="hoola")
    return _keep(r, report)


def _avg(xs: list) -> float | None:
    return round(sum(xs) / len(xs), 1) if xs else None


def _runs(r) -> list[dict]:
    from . import studio as S
    with session() as s:
        row = s.get(S.GameStudio, r.id)
        return list((row.qa or []) if row is not None else [])


def _keep(r, report: dict) -> dict:
    from . import studio as S
    report.setdefault("at", now().isoformat())
    with session() as s:
        row = s.get(S.GameStudio, r.id)
        if row is not None:
            row.qa = ((row.qa or []) + [report])[-KEEP_RUNS:]
    return report


def _prune(tenant: str, sid: str) -> None:
    d = _qdir(tenant, sid)
    runs = sorted(p for p in d.iterdir() if p.is_dir()) if d.is_dir() else []
    keep = {p.name for p in runs[-KEEP_RUNS:]}
    golden = d / "golden"
    for p in runs:
        if p.name not in keep and p != golden:
            shutil.rmtree(p, ignore_errors=True)


# ---------------------------------------------------------------- golden screens
def _golden_check(r, runs: list[dict], qd: Path) -> dict[str, Any]:
    idle = next((x for x in runs if x["bot"] == "idle" and x["shots"]), None)
    if idle is None:
        return {"verdict": "not run"}
    cur = qd.parent / idle["dir"] / "start.png"
    if not cur.is_file():
        return {"verdict": "not run"}
    gold = _qdir(r.tenant_id, r.id) / "golden" / f"{idle['profile']}.png"
    if not gold.is_file():
        return {"verdict": "none", "candidate": f"{idle['dir']}/start.png", "profile": idle["profile"]}
    d = diff_share(gold.read_bytes(), cur.read_bytes())
    return {"verdict": "different" if d > GOLDEN_DIFF else "same", "diff": d, "candidate": f"{idle['dir']}/start.png",
            "profile": idle["profile"], "golden": f"golden/{idle['profile']}.png"}


def approve_golden(tenant: str, ref: str, rel: str = "") -> dict[str, Any]:
    """Her OK: this start screen is how the game should look (default: the last run's candidate)."""
    r = _studio(tenant, ref)
    last = (_runs(r) or [{}])[-1]
    rel = rel or ((last.get("golden") or {}).get("candidate") or "")
    prof = (last.get("golden") or {}).get("profile", "desktop")
    src = _qdir(tenant, r.id) / rel
    if not rel or ".." in rel or not src.is_file():
        raise QaError("Koi screen nahi mili jise golden banaya jaye; pehle QA chalaiye.")
    dst = _qdir(tenant, r.id) / "golden" / f"{prof}.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    from . import studio as S
    S._decide(r, f"Golden start screen approved ({prof})", rel, by="her")
    return {"ok": True, "golden": f"golden/{prof}.png"}


def shot_path(tenant: str, sid: str, rel: str) -> Path | None:
    if not re.fullmatch(r"(golden/[a-z_]+|\d{14}/[\w]+)\.png|\d{14}/[\w]+/(start|end)\.png", rel or "") or ".." in rel:
        return None
    p = _qdir(tenant, sid) / rel
    return p if p.is_file() else None


# ---------------------------------------------------------------- bugs
def bug_view(b: GameBug) -> dict[str, Any]:
    return {"id": b.id, "number": b.number, "title": b.title, "detail": b.detail, "severity": b.severity, "status": b.status,
            "source": b.source, "repro": {k: v for k, v in (b.repro or {}).items() if k != "steps"},
            "steps": len((b.repro or {}).get("steps") or []), "evidence": b.evidence or {}, "seen": b.seen,
            "first_version": b.first_version, "last_version": b.last_version, "regression": b.regression, "task": b.task,
            "created_at": b.created_at.isoformat() if b.created_at else None}


def bugs(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    r = _studio(tenant, ref)
    with session() as s:
        rows = s.scalars(select(GameBug).where(GameBug.studio_id == r.id).order_by(GameBug.created_at.desc())).all()
        out = [bug_view(b) for b in rows]
    runs = _runs(r)
    return {"bugs": out, "open": sum(1 for b in out if b["status"] in ("open", "fixing")),
            "crash_open": sum(1 for b in out if b["status"] in ("open", "fixing") and b["severity"] in ("crash", "blocker")),
            "last": runs[-1] if runs else {}, "history": [{k: x.get(k) for k in ("id", "at", "version", "verdict")} for x in reversed(runs)]}


def report_bug(tenant: str, ref: str, title: str, detail: str = "", severity: str = "major") -> dict[str, Any]:
    """Her own bug report (no repro bot: she tells how it happens)."""
    ensure_table()
    title = re.sub(r"\s+", " ", title or "").strip()[:200]
    if len(title) < 4:
        raise QaError("Bug ek line mein likhiye (kya galat hota hai).")
    r = _studio(tenant, ref)
    g = G._get(tenant, r.game_id) if r.game_id else None
    ver = (G._good(g) or [{}])[-1].get("n", 0) if g else 0
    with session() as s:
        b = GameBug(tenant_id=tenant, studio_id=r.id, number=_number(s, r.id), title=title, detail=(detail or "")[:2000],
                    severity=severity if severity in SEV else "major", source="her", signature=_sig("her", title + now().isoformat()),
                    repro={"version": ver}, evidence={}, first_version=ver, last_version=ver)
        s.add(b)
        s.flush()
        return bug_view(b)


def fix_bug(tenant: str, ref: str, number: str) -> dict[str, Any]:
    """A board task for the bug: the role from its words, and the criterion that the bot which found it no longer does."""
    from . import studio as S
    r = _studio(tenant, ref)
    with session() as s:
        b = s.scalars(select(GameBug).where(GameBug.studio_id == r.id, GameBug.number == str(number).upper())).first()
        if b is None:
            raise QaError("Yeh bug nahi mila.")
        if b.task:
            raise QaError(f"{b.number} ke liye {b.task} pehle se hai.")
        rp = b.repro or {}
        crit = [{"text": f"QA bot '{rp['bot']}' (seed {rp.get('seed', 1)}, {rp.get('profile', 'desktop')}) no longer finds {b.number}",
                 "by": "test"}] if rp.get("bot") else [{"text": f"{b.title} no longer happens", "by": "her"}]
        detail = (f"Bug {b.number} ({b.severity}): {b.title}. " + (b.detail or "") + " Errors: "
                  + "; ".join((b.evidence or {}).get("errors", [])[:3]))[:1500]
        title, sev, bid = f"Fix {b.number}: {b.title}"[:200], b.severity, b.id
    t = S.add_task(tenant, r.id, title, detail, kind="fix", priority=1 if sev in ("crash", "blocker") else 2, criteria=crit)
    with session() as s:
        b = s.get(GameBug, bid)
        b.task, b.status, b.updated_at = t["number"], "fixing", now()
        s.flush()
        return {"bug": bug_view(b), "task": t}


def set_bug(tenant: str, ref: str, number: str, status: str) -> dict[str, Any]:
    if status not in ("open", "wontfix", "duplicate", "fixed"):
        raise QaError("status = open | wontfix | duplicate | fixed")
    r = _studio(tenant, ref)
    with session() as s:
        b = s.scalars(select(GameBug).where(GameBug.studio_id == r.id, GameBug.number == str(number).upper())).first()
        if b is None:
            raise QaError("Yeh bug nahi mila.")
        if status == "fixed" and (b.repro or {}).get("bot"):
            raise QaError("Bot wala bug tab 'fixed' hota hai jab wahi bot use dobara na paye: QA chalaiye.")
        b.status, b.updated_at = status, now()
        s.flush()
        return bug_view(b)


def summary_line(r) -> dict[str, Any]:
    try:
        ensure_table()
        with session() as s:
            rows = s.scalars(select(GameBug).where(GameBug.studio_id == r.id)).all()
            last = (list(r.qa or []) or [{}])[-1]
            return {"verdict": last.get("verdict", ""), "version": last.get("version"), "at": last.get("at"),
                    "open": sum(1 for b in rows if b.status in ("open", "fixing")),
                    "crash_open": sum(1 for b in rows if b.status in ("open", "fixing") and b.severity in ("crash", "blocker"))}
    except Exception:                                   # noqa: BLE001
        log.exception("qa line")
        return {}


# ---------------------------------------------------------------- background runs + signed screenshot links
import hmac as _hmac                                     # noqa: E402
import threading as _threading                           # noqa: E402
from concurrent.futures import ThreadPoolExecutor as _TPE  # noqa: E402

_QPOOL = _TPE(max_workers=1, thread_name_prefix="gameqa")
_RUN: set[str] = set()
_RLOCK = _threading.Lock()


def start(tenant: str, ref: str) -> dict[str, Any]:
    """Her 'Run QA now': the farm runs in the background (2-4 minutes); the report lands on the project."""
    import os
    r = _studio(tenant, ref)
    with _RLOCK:
        if r.id in _RUN:
            raise QaError("QA bots abhi khel rahe hain; khatam hone dijiye.")
        _RUN.add(r.id)
    if os.environ.get("GAME_WORKER", "true").lower() in ("0", "false", "off"):
        with _RLOCK:
            _RUN.discard(r.id)
        return {"started": False, "note": "worker off (tests call farm directly)"}
    _QPOOL.submit(_run_safe, tenant, r.id)
    return {"started": True}


def running(sid: str) -> bool:
    return sid in _RUN


def _run_safe(tenant: str, sid: str) -> None:
    try:
        farm(tenant, sid)
    except Exception:                                   # noqa: BLE001
        log.exception("qa farm %s", sid)
    finally:
        with _RLOCK:
            _RUN.discard(sid)


def _ssig(sid: str, rel: str, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-qa"
    return _hmac.new(f"gqa:{key}".encode(), f"{sid}/{rel}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def shot_url(sid: str, rel: str, days: int = 7) -> str:
    from urllib.parse import quote
    exp = int(time.time()) + days * 86400
    return f"/api/gamestudio/qa-shot/{sid}?rel={quote(rel)}&exp={exp}&sig={_ssig(sid, rel, exp)}"


def shot_file(sid: str, rel: str, exp: int, sig: str) -> Path | None:
    if exp < time.time() or not _hmac.compare_digest(_ssig(sid, rel, exp), sig or ""):
        return None
    from . import studio as S
    with session() as s:
        row = s.get(S.GameStudio, sid)
        if row is None:
            return None
        tenant = row.tenant_id
    return shot_path(tenant, sid, rel)


def with_links(sid: str, rep: dict[str, Any]) -> dict[str, Any]:
    """A report with signed links for every screenshot (console / phone show them without a key in the URL)."""
    rep = json.loads(json.dumps(rep or {}))
    for x in rep.get("runs") or []:
        x["shot_urls"] = [shot_url(sid, p) for p in x.get("shots") or []]
    g = rep.get("golden") or {}
    for k in ("candidate", "golden"):
        if g.get(k):
            g[k + "_url"] = shot_url(sid, g[k])
    return rep
