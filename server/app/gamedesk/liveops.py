"""v0.428 LIVE OPS (Hoola Game Engine plan Phase 9): running a game for years, after it ships.

- LIVE CONFIG: the game asks its OWN play-link host (GET /play/<token>/live; the page's CSP allows nothing else) for
  the running A/B tests and the scheduled live events, keeps the last answer on the device (works offline) and reads
  values through HoolaRuntime.num("player.hp", fallback) / flag("double_coins"). A value can only change a number that
  is in her Game Bible, within 1/4x - 4x of the Bible's own number (a typo cannot make an enemy 1000x stronger), or a
  flag.<name> switch. Nothing reaches players before her tap (start a test / approve an event).
- A/B TESTS: a player's group = sha256(install:key) -> the same sum in GDScript and here (tested in the real engine).
  Results are measured, never guessed: players per group, the goal rate, a sample-size target from a power sum (alpha
  0.05, power 0.8, her smallest difference worth knowing), a sample-ratio check (a broken split is named and the result
  not trusted), a two-proportion z-test with Bonferroni for >2 groups. Before the target there is NO winner - looking
  early and stopping on a lucky day is how A/B tests lie. Shipping a winner = a Studio task for her board (her OK), not
  a silent change.
- LIVE EVENTS: a calendar (start / end, the values it changes). Two events (or an event and a running test) may not
  change the same value at the same time - the numbers would mean nothing.
- CRASHES: HoolaRuntime catches script errors with Godot's Logger; with the player's yes they arrive grouped (file +
  line + message, digits and anything like an e-mail scrubbed), with players, versions, first / last seen, crash-free
  players per version. One tap makes a hotfix task; "fixed" is only said when players on a newer version stop sending it.
- PATCH CHECK: before a new version goes out, every saved replay is played on it in the real engine (it must reach the
  end with no script errors) plus a fresh bot run; release notes are drafted from the tasks done.
- MONEY: Hoola sees no store. The money report uses the numbers SHE imports (a CSV from her store) and DAU from
  consenting players only - so ARPDAU is an upper bound, and it says so.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import re
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
KEY_RE = re.compile(r"^[a-z0-9_]{2,40}$")
VNAME_RE = re.compile(r"^[a-z0-9_]{1,20}$")
MAX_RUNNING = 3
MAX_EVENT_DAYS = 31
IST = timezone(timedelta(hours=5, minutes=30))
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="liveops")


class LiveOpsError(G.GameError):
    pass


class GameCrash(Base):
    __tablename__ = "game_crashes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    game_id: Mapped[str] = mapped_column(String(40), index=True)
    sig: Mapped[str] = mapped_column(String(16), index=True)
    file: Mapped[str] = mapped_column(String(120), default="")
    line: Mapped[int] = mapped_column(Integer, default=0)
    msg: Mapped[str] = mapped_column(Text, default="")
    count: Mapped[int] = mapped_column(Integer, default=0)
    installs: Mapped[list] = mapped_column(JSON, default=list)      # hashed install ids, capped
    versions: Mapped[dict] = mapped_column(JSON, default=dict)      # {"3": count}
    task: Mapped[str] = mapped_column(String(16), default="")        # the hotfix task number
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameCrash.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ the A/B group sum (same as HoolaRuntime.variant)
def bucket(install: str, key: str) -> int:
    return int(hashlib.sha256(f"{install}:{key}".encode()).hexdigest()[:8], 16) % 10000


def assign(install: str, key: str, variants: list[dict]) -> str:
    if not variants:
        return ""
    if not install:
        return variants[0]["name"]
    b, acc = bucket(install, key), 0
    for v in variants:
        acc += int(v["bp"])
        if b < acc:
            return v["name"]
    return variants[0]["name"]


# ================================================================ stats (measured, never guessed)
def _phi(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2))


def z_test(c1: int, n1: int, c2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z-test (pooled). Returns (z, two-sided p)."""
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    p = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (c2 / n2 - c1 / n1) / se
    return z, 2 * (1 - _phi(abs(z)))


def sample_size(p: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Players needed PER GROUP to see an absolute difference of `mde` from a base rate `p` (normal approximation)."""
    from statistics import NormalDist
    nd = NormalDist()
    za, zb = nd.inv_cdf(1 - alpha / 2), nd.inv_cdf(power)
    p = min(max(p, 0.01), 0.99)
    p2 = min(max(p + mde, 0.01), 0.99)
    return int(math.ceil((za + zb) ** 2 * (p * (1 - p) + p2 * (1 - p2)) / max(mde, 1e-6) ** 2))


def srm_p(counts: list[int], shares: list[float]) -> float:
    """Sample-ratio mismatch: chi-square of the players per group against the planned split."""
    from scipy.stats import chisquare
    tot = sum(counts)
    if tot == 0:
        return 1.0
    return float(chisquare(counts, [s * tot for s in shares]).pvalue)


# ================================================================ storage on the Studio project
def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _game(tenant: str, gid: str):
    with session() as s:
        g = s.get(G.GameProject, gid)
        if g is None or g.tenant_id != tenant:
            raise LiveOpsError("Game nahi mila.")
        s.expunge(g)
    return g


def _data(st) -> dict:
    d = dict(st.liveops or {})
    for k in ("experiments", "events", "revenue", "patches"):
        d.setdefault(k, [])
    return d


def _save(tenant: str, sid: str, d: dict) -> None:
    from . import studio as S
    with session() as s:
        row = s.get(S.GameStudio, sid)
        if row is None or row.tenant_id != tenant:
            raise LiveOpsError("Project nahi mila.")
        row.liveops = json.loads(json.dumps(d))
        row.updated_at = now()


def _bible(tenant: str, sid: str) -> dict:
    from . import bible as B
    try:
        return B._data(tenant, sid) or {}
    except Exception:                                    # noqa: BLE001
        return {}


# ================================================================ values a live change may touch
def base_values(bible: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for sec in ("player", "economy"):
        for k, v in (bible.get(sec) or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[f"{sec}.{k}"] = float(v)
    for kind, items in (bible.get("entities") or {}).items():
        for e in items or []:
            for k, v in (e or {}).items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and e.get("id"):
                    out[f"{kind}.{e['id']}.{k}"] = float(v)
    return out


def clean_set(raw: Any, bible: dict) -> dict[str, Any]:
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise LiveOpsError("Values ek list ho: {\"player.hp\": 120, \"flag.double_coins\": true}.")
    base = base_values(bible)
    out: dict[str, Any] = {}
    for k, v in list(raw.items())[:20]:
        k = str(k).strip()
        if k.startswith("flag."):
            if not VNAME_RE.match(k[5:]) or not isinstance(v, bool):
                raise LiveOpsError(f"{k}: a flag is flag.<name> = true / false.")
            out[k] = v
            continue
        if k not in base:
            raise LiveOpsError(f"{k} Game Bible mein nahi hai - live change sirf Bible ke numbers badal sakta hai "
                               f"(jaise {', '.join(list(base)[:4]) or 'player.hp'}).")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise LiveOpsError(f"{k}: a number is needed.")
        b = base[k]
        if b <= 0:
            raise LiveOpsError(f"{k}: the Bible number is {b:g}, so there is no safe range to change it live - change it in the Bible.")
        if not (b / 4 <= float(v) <= b * 4):
            raise LiveOpsError(f"{k} = {v:g} is outside 1/4x - 4x of the Bible's {b:g} ({b / 4:g} - {b * 4:g}). "
                               f"A bigger change belongs in the Bible and a new version.")
        out[k] = float(v) if isinstance(v, float) else int(v)
    return out


def _when(v: Any) -> float:
    """A time she gives: unix seconds, or an ISO date/time (India time when no zone is written)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    t = str(v or "").strip().replace(" ", "T")
    if not t:
        raise LiveOpsError("Start aur end ka samay dijiye (2026-11-15 18:00).")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        raise LiveOpsError(f"Samay samajh nahi aaya: {v!r} (2026-11-15 18:00 likhiye).")
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return d.timestamp()


def _ist(ts: float) -> str:
    return datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d %H:%M")


# ================================================================ A/B tests
def add_experiment(tenant: str, ref: str, key: str, title: str = "", goal: str = "win", variants: list | None = None,
                   mde: float = 0.05) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    key = str(key or "").strip().lower()
    if not KEY_RE.match(key):
        raise LiveOpsError("Test ka naam chhota likhiye: a-z, 0-9, _ (jaise jump_height).")
    if any(x["key"] == key for x in d["experiments"]):
        raise LiveOpsError(f"{key} naam ka test pehle se hai.")
    goal = str(goal or "").strip().lower()
    if goal != "d1" and not re.fullmatch(r"[a-z0-9_]{1,40}", goal):
        raise LiveOpsError("Goal = the event that counts as success (win, level_up, purchase...) or d1 (came back next day).")
    vs = variants or []
    if not (2 <= len(vs) <= 4):
        raise LiveOpsError("2 se 4 groups chahiye: pehla = control (aaj jaisa), baaki = badlav.")
    bible = _bible(tenant, st.id)
    out, names, total = [], set(), 0
    for i, v in enumerate(vs):
        v = v if isinstance(v, dict) else {}
        name = str(v.get("name") or ("control" if i == 0 else chr(ord("a") + i))).strip().lower()
        if not VNAME_RE.match(name) or name in names:
            raise LiveOpsError(f"Group naam {name!r} galat / dobara hai.")
        names.add(name)
        w = float(v.get("weight") or 100 / len(vs))
        if not (5 <= w <= 95):
            raise LiveOpsError("Har group ko 5% - 95% players milein.")
        st_ = clean_set(v.get("set"), bible)
        if i > 0 and not st_:
            raise LiveOpsError(f"Group {name} kuch nahi badalta - control se alag kya hai?")
        out.append({"name": name, "weight": w, "set": st_})
        total += w
    if abs(total - 100) > 0.5:
        raise LiveOpsError(f"Split 100% hona chahiye (abhi {total:g}%).")
    bp = [int(round(v["weight"] * 100)) for v in out]
    bp[0] += 10000 - sum(bp)
    for v, b in zip(out, bp):
        v["bp"] = b
    mde = float(mde or 0.05)
    if not (0.005 <= mde <= 0.5):
        raise LiveOpsError("Smallest difference worth knowing: 0.5 - 50 points (0.05 = 5 points).")
    x = {"key": key, "title": str(title or key)[:120], "goal": goal, "variants": out, "mde": mde, "status": "draft",
         "made": now().isoformat()}
    d["experiments"].append(x)
    _save(tenant, st.id, d)
    return x


def _paths_of(sets: list[dict]) -> set[str]:
    return {k for s_ in sets for k in (s_ or {})}


def start_experiment(tenant: str, ref: str, key: str) -> dict[str, Any]:
    from . import runtime as RT
    st = _studio(tenant, ref)
    d = _data(st)
    x = next((e for e in d["experiments"] if e["key"] == key), None)
    if x is None:
        raise LiveOpsError("Test nahi mila.")
    if x["status"] != "draft":
        raise LiveOpsError(f"Test {x['status']} hai.")
    if not (st.runtime or {}).get("telemetry"):
        raise LiveOpsError("Telemetry band hai - bina uske result naapa nahi ja sakta. Runtime page par telemetry chalu "
                           "kijiye (players se poocha jaata hai), phir test shuru kijiye.")
    if not RT.for_game(tenant, st.game_id):
        raise LiveOpsError("Hoola Runtime is project mein band hai.")
    running = [e for e in d["experiments"] if e["status"] == "running"]
    if len(running) >= MAX_RUNNING:
        raise LiveOpsError(f"Ek saath {MAX_RUNNING} tests tak - pehle ek band kijiye.")
    mine = _paths_of([v["set"] for v in x["variants"]])
    for e in running:
        both = mine & _paths_of([v["set"] for v in e["variants"]])
        if both:
            raise LiveOpsError(f"{', '.join(sorted(both))} test {e['key']} pehle se badal raha hai - dono ke number bekaar ho jayenge.")
    t = time.time()
    for ev in d["events"]:
        if ev["status"] == "scheduled" and ev["ends"] > t and mine & set(ev["set"]):
            raise LiveOpsError(f"Event '{ev['title']}' ({_ist(ev['starts'])} - {_ist(ev['ends'])}) bhi "
                               f"{', '.join(sorted(mine & set(ev['set'])))} badalta hai - test ke number bigad jayenge.")
    x["status"] = "running"
    x["started"] = now().isoformat()
    _save(tenant, st.id, d)
    return x


def stop_experiment(tenant: str, ref: str, key: str, ship: str = "") -> dict[str, Any]:
    from . import studio as S
    st = _studio(tenant, ref)
    d = _data(st)
    x = next((e for e in d["experiments"] if e["key"] == key), None)
    if x is None:
        raise LiveOpsError("Test nahi mila.")
    if x["status"] == "ended":
        raise LiveOpsError("Test pehle hi band hai.")
    out: dict[str, Any] = {}
    if ship:
        v = next((v for v in x["variants"] if v["name"] == ship), None)
        if v is None:
            raise LiveOpsError("Woh group is test mein nahi hai.")
        if v["set"]:
            res = results(tenant, ref, key)
            words = ", ".join(f"{k} = {val}" for k, val in v["set"].items())
            task = S.add_task(tenant, st.id, f"Make A/B group {ship} of test {key} the game's own: {words}"[:200],
                              detail=f"From the live A/B test '{x['title']}'. Result when stopped: {res['verdict']}. "
                                     f"Change these numbers in the Game Bible and rebuild; the live test is stopped.",
                              kind="content", priority=2, source="hoola")
            out["task"] = task.get("number")
        x["shipped"] = ship
    x["status"] = "ended"
    x["ended"] = now().isoformat()
    _save(tenant, st.id, d)
    return x | out


def _tel_rows(tenant: str, gid: str) -> list[tuple]:
    from . import runtime as RT
    RT.ensure_table()
    with session() as s:
        return s.execute(select(RT.GameTelemetry.install, RT.GameTelemetry.event, RT.GameTelemetry.day, RT.GameTelemetry.ab,
                                RT.GameTelemetry.value, RT.GameTelemetry.version)
                         .where(RT.GameTelemetry.tenant_id == tenant, RT.GameTelemetry.game_id == gid)).all()


def results(tenant: str, ref: str, key: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    x = next((e for e in d["experiments"] if e["key"] == key), None)
    if x is None:
        raise LiveOpsError("Test nahi mila.")
    rows = _tel_rows(tenant, st.game_id)
    grp: dict[str, str] = {}
    hit: set[str] = set()
    first: dict[str, str] = {}
    days: dict[str, set] = defaultdict(set)
    tag = f"{key}="
    for inst, ev, day, ab, _v, _ver in rows:
        for part in (ab or "").split(";"):
            if part.startswith(tag):
                grp[inst] = part[len(tag):]
        first[inst] = min(first.get(inst, day), day)
        days[inst].add(day)
        if ev == x["goal"]:
            hit.add(inst)
    today = datetime.now(timezone.utc).date()
    names = [v["name"] for v in x["variants"]]
    groups = []
    for v in x["variants"]:
        members = [i for i, g in grp.items() if g == v["name"]]
        if x["goal"] == "d1":
            members = [i for i in members if date.fromisoformat(first[i]) <= today - timedelta(days=1)]
            conv = sum(1 for i in members if (date.fromisoformat(first[i]) + timedelta(days=1)).isoformat() in days[i])
        else:
            conv = sum(1 for i in members if i in hit)
        groups.append({"name": v["name"], "players": len(members), "goal": conv,
                       "rate": round(conv / len(members), 4) if members else None, "share": v["bp"] / 10000})
    ctl = groups[0]
    base = ctl["rate"] if ctl["players"] >= 30 and ctl["rate"] is not None else 0.3
    need = sample_size(base, x["mde"])
    k = len(groups) - 1
    alpha = 0.05 / max(k, 1)
    srm = srm_p([g["players"] for g in groups], [g["share"] for g in groups]) if sum(g["players"] for g in groups) >= 50 else 1.0
    checks = []
    for g in groups[1:]:
        z, p = z_test(ctl["goal"], ctl["players"], g["goal"], g["players"])
        g["vs_control_pts"] = round(100 * ((g["rate"] or 0) - (ctl["rate"] or 0)), 2) if g["players"] and ctl["players"] else None
        g["p"] = round(p, 4)
        checks.append((g, p))
    have = min(g["players"] for g in groups)
    if srm < 0.001:
        verdict = "SPLIT BROKEN"
        note = (f"players per group do not match the planned split (sample-ratio check p = {srm:.4f}) - something "
                f"(an old cached build, a crash in one group) is breaking it; the result is not trusted")
    elif have < need:
        verdict = "NOT ENOUGH PLAYERS"
        note = (f"{have} of the {need} players each group needs to see a {round(100 * x['mde'], 1):g}-point difference "
                f"(alpha 0.05, power 0.8). No winner before that - stopping early on a good day is how tests lie.")
    else:
        wins = [(g, p) for g, p in checks if p < alpha]
        if not wins:
            verdict = "NO CLEAR DIFFERENCE"
            note = f"no group differs from {ctl['name']} at p < {alpha:.3g}" + (" (Bonferroni for several groups)" if k > 1 else "")
        else:
            best = max(wins, key=lambda w: w[0]["rate"] or 0)
            better = (best[0]["rate"] or 0) > (ctl["rate"] or 0)
            verdict = f"{best[0]['name'].upper()} {'WINS' if better else 'IS WORSE'}"
            note = (f"{best[0]['name']} {best[0]['vs_control_pts']:+g} points vs {ctl['name']} (p = {best[1]:.4f} < {alpha:.3g}); "
                    f"{'ship it with one tap (it becomes a board task)' if better else 'keep ' + ctl['name']}")
    return {"key": key, "title": x["title"], "goal": x["goal"], "status": x["status"], "groups": groups, "need_per_group": need,
            "srm_p": round(srm, 4), "alpha": alpha, "verdict": verdict, "note": note, "names": names,
            "measured_from": "players who said yes to telemetry only"}


# ================================================================ live events (calendar)
def add_event(tenant: str, ref: str, key: str, title: str, starts: Any, ends: Any, values: Any = None) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    key = str(key or "").strip().lower()
    if not KEY_RE.match(key):
        raise LiveOpsError("Event ka chhota naam: a-z, 0-9, _ (jaise diwali_2026).")
    if any(e["key"] == key for e in d["events"]):
        raise LiveOpsError(f"{key} naam ka event pehle se hai.")
    a, b = _when(starts), _when(ends)
    t = time.time()
    if b <= a:
        raise LiveOpsError("End, start ke baad ho.")
    if b - a > MAX_EVENT_DAYS * 86400:
        raise LiveOpsError(f"Ek event {MAX_EVENT_DAYS} din tak.")
    if b < t:
        raise LiveOpsError("Yeh samay beet chuka hai.")
    if a > t + 366 * 86400:
        raise LiveOpsError("Ek saal ke andar ka event.")
    vals = clean_set(values, _bible(tenant, st.id))
    if not vals:
        raise LiveOpsError("Event kya badalta hai? (jaise {\"economy.coin_multiplier\": 2} ya {\"flag.diwali\": true})")
    ev = {"key": key, "title": str(title or key)[:120], "starts": a, "ends": b, "set": vals, "status": "draft",
          "made": now().isoformat()}
    d["events"].append(ev)
    _save(tenant, st.id, d)
    return _event_view(ev)


def _event_view(ev: dict) -> dict:
    t = time.time()
    state = ev["status"]
    if state == "scheduled":
        state = "live" if ev["starts"] <= t < ev["ends"] else ("ended" if t >= ev["ends"] else "scheduled")
    return ev | {"state": state, "starts_ist": _ist(ev["starts"]), "ends_ist": _ist(ev["ends"])}


def approve_event(tenant: str, ref: str, key: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    ev = next((e for e in d["events"] if e["key"] == key), None)
    if ev is None:
        raise LiveOpsError("Event nahi mila.")
    if ev["status"] != "draft":
        raise LiveOpsError(f"Event {ev['status']} hai.")
    if ev["ends"] < time.time():
        raise LiveOpsError("Yeh samay beet chuka hai.")
    for o in d["events"]:
        if o is not ev and o["status"] == "scheduled" and o["starts"] < ev["ends"] and ev["starts"] < o["ends"]:
            both = set(o["set"]) & set(ev["set"])
            if both:
                raise LiveOpsError(f"'{o['title']}' ({_ist(o['starts'])} - {_ist(o['ends'])}) bhi {', '.join(sorted(both))} "
                                   f"badalta hai - ek samay par ek hi.")
    for x in d["experiments"]:
        if x["status"] == "running":
            both = set(ev["set"]) & _paths_of([v["set"] for v in x["variants"]])
            if both:
                raise LiveOpsError(f"Test {x['key']} {', '.join(sorted(both))} naap raha hai - event uske number bigaad dega. "
                                   f"Test band kijiye ya event doosra value badle.")
    ev["status"] = "scheduled"
    ev["approved"] = now().isoformat()
    _save(tenant, st.id, d)
    return _event_view(ev)


def cancel_event(tenant: str, ref: str, key: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    ev = next((e for e in d["events"] if e["key"] == key), None)
    if ev is None:
        raise LiveOpsError("Event nahi mila.")
    ev["status"] = "cancelled"
    _save(tenant, st.id, d)
    return _event_view(ev)


def live_config(token: str) -> dict[str, Any]:
    """GET /play/<token>/live - what the game reads. Only approved events that have not ended and running tests."""
    from . import studio as S
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,48}", token or ""):
        return {}
    with session() as s:
        g = s.scalars(select(G.GameProject).where(G.GameProject.token == token)).first()
        if g is None:
            return {}
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.game_id == g.id)).first()
        if st is None:
            return {}
        d = dict(st.liveops or {})
    t = time.time()
    return {"v": 1, "now": int(t),
            "experiments": [{"key": x["key"], "variants": [{"name": v["name"], "bp": v["bp"], "set": v["set"]} for v in x["variants"]]}
                            for x in d.get("experiments", []) if x.get("status") == "running"],
            "events": [{"key": e["key"], "title": e["title"], "starts": int(e["starts"]), "ends": int(e["ends"]), "set": e["set"]}
                       for e in d.get("events", []) if e.get("status") == "scheduled" and e["ends"] > t]}


# ================================================================ crashes
_SCRUB = [(re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"), (re.compile(r"\d{5,}"), "<n>")]


def _scrub(msg: str) -> str:
    m = str(msg or "")[:200]
    for pat, rep in _SCRUB:
        m = pat.sub(rep, m)
    return m


def record_errors(s, g, install: str, version: int, errors: list) -> int:
    ensure_table()
    hid = hashlib.sha256(install.encode()).hexdigest()[:12]
    n = 0
    for e in errors[:5]:
        if not isinstance(e, dict):
            continue
        f = str(e.get("file") or "")[:120]
        if not re.fullmatch(r"[A-Za-z0-9_./:\- ]{0,120}", f):
            continue
        line = int(e.get("line") or 0) if str(e.get("line") or "0").isdigit() else 0
        msg = _scrub(e.get("msg"))
        sig = hashlib.sha1(f"{f}:{line}:{re.sub(r'[0-9]+', '#', msg)}".encode()).hexdigest()[:16]
        row = s.scalars(select(GameCrash).where(GameCrash.game_id == g.id, GameCrash.sig == sig)).first()
        if row is None:
            row = GameCrash(tenant_id=g.tenant_id, game_id=g.id, sig=sig, file=f, line=line, msg=msg, count=0,
                            installs=[], versions={})
            s.add(row)
        row.count = (row.count or 0) + 1
        if hid not in (row.installs or []) and len(row.installs or []) < 2000:
            row.installs = list(row.installs or []) + [hid]
        vs = dict(row.versions or {})
        vs[str(version)] = int(vs.get(str(version), 0)) + 1
        row.versions = vs
        row.last_at = now()
        n += 1
    return n


def crashes(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    ensure_table()
    rows = _tel_rows(tenant, st.game_id)
    players_on: dict[int, set] = defaultdict(set)
    for inst, ev, _d, _ab, _v, ver in rows:
        players_on[int(ver or 0)].add(hashlib.sha256(inst.encode()).hexdigest()[:12])
    with session() as s:
        groups = s.scalars(select(GameCrash).where(GameCrash.tenant_id == tenant, GameCrash.game_id == st.game_id)).all()
        for x in groups:
            s.expunge(x)
    newest = max(players_on) if players_on else 0
    out = []
    crashed_on: dict[int, set] = defaultdict(set)
    for c in groups:
        vers = sorted(int(v) for v in (c.versions or {}))
        for v in vers:
            crashed_on[v] |= set(c.installs or [])
        gone = bool(vers) and newest > max(vers) and len(players_on.get(newest, ())) >= 20
        out.append({"sig": c.sig, "where": f"{c.file}:{c.line}", "msg": c.msg, "count": c.count, "players": len(c.installs or []),
                    "versions": vers, "first": c.first_at.isoformat() if c.first_at else "", "last": c.last_at.isoformat() if c.last_at else "",
                    "task": c.task, "state": "not seen on the newest version" if gone else ("fixing" if c.task else "open"),
                    "note": (f"{len(players_on[newest])} players on v{newest} and none sent it" if gone else
                             "fixed is said only when players on a newer version stop sending it")})
    out.sort(key=lambda x: (-x["players"], -x["count"]))
    free = []
    for v in sorted(players_on)[-5:]:
        n = len(players_on[v])
        free.append({"version": v, "players": n, "crash_free": round(1 - len(crashed_on.get(v, set()) & players_on[v]) / n, 4) if n else None})
    return {"groups": out[:50], "crash_free": free, "privacy": "file, line and the error text only (digits and e-mails "
            "scrubbed); install ids hashed; only from players who said yes"}


def hotfix(tenant: str, ref: str, sig: str) -> dict[str, Any]:
    from . import studio as S
    st = _studio(tenant, ref)
    ensure_table()
    with session() as s:
        c = s.scalars(select(GameCrash).where(GameCrash.tenant_id == tenant, GameCrash.game_id == st.game_id, GameCrash.sig == sig)).first()
        if c is None:
            raise LiveOpsError("Woh crash nahi mila.")
        if c.task:
            raise LiveOpsError(f"Iska hotfix task {c.task} pehle se hai.")
        where, msg, count, players, vers = f"{c.file}:{c.line}", c.msg, c.count, len(c.installs or []), sorted(c.versions or {})
    t = S.add_task(tenant, st.id, f"Hotfix: {msg[:150]} ({where})",
                   detail=f"Players' games hit this script error {count} times ({players} players) in version(s) "
                          f"{', '.join(vers)}. Fix the cause at {where}; the patch check replays saved runs on the fix.",
                   kind="fix", priority=1, source="hoola")
    with session() as s:
        c = s.scalars(select(GameCrash).where(GameCrash.game_id == st.game_id, GameCrash.sig == sig)).first()
        c.task = t.get("number") or ""
    return {"task": t.get("number"), "title": t.get("title")}


# ================================================================ patch check (real engine)
def patch_check(tenant: str, ref: str, max_replays: int = 3) -> dict[str, Any]:
    from . import engine
    from . import runtime as RT
    from . import studio as S
    if not engine.find():
        raise LiveOpsError("Godot is not installed on this server (deploy/setup_godot.py) - the patch check needs the real engine.")
    st = _studio(tenant, ref)
    g = _game(tenant, st.game_id)
    good = G._good(g)
    if not good:
        raise LiveOpsError("Pehle game ka ek chalne wala version chahiye.")
    n = good[-1]["n"]
    prev = good[-2]["n"] if len(good) > 1 else 0
    job = G._pdir(tenant, g.id) / "patch" / f"v{n}"
    t0 = time.time()
    RT.prepare(G._vdir(g, n) / "proj", job, g.title, g.orientation)
    rdir = G._pdir(tenant, g.id) / "replays"
    files = sorted(rdir.glob("r*.json"), key=lambda p: p.name)[-max_replays:] if rdir.is_dir() else []
    import base64
    runs = []
    for p in files:
        raw = p.read_text(encoding="utf-8")
        if len(raw) > 100_000:
            runs.append({"replay": p.stem, "ok": False, "errors": ["replay too big to play back"]})
            continue
        frames = int((json.loads(raw) or {}).get("frames") or 600)
        r = RT._run_mode(job, "--hoola-replay=" + base64.b64encode(raw.encode()).decode(), frames)
        runs.append({"replay": p.stem, "ok": bool(r.get("ok")) and not r.get("errors"), "frames": r.get("frames"),
                     "errors": (r.get("errors") or [])[:3]})
    bot = RT._run_mode(job, "--hoola-bot=11,900", 900)
    checks = [{"check": f"saved replay {x['replay']} plays to the end", "ok": x["ok"],
               "note": "; ".join(x["errors"]) if x["errors"] else f"{x.get('frames')} frames, no script errors"} for x in runs]
    if not runs:
        checks.append({"check": "saved replays", "ok": True, "note": "NOT ASSESSED - no saved replay yet (run a replay test first)"})
    checks.append({"check": "a fresh bot run (seed 11)", "ok": bool(bot.get("ok")) and not bot.get("errors"),
                   "note": "; ".join((bot.get("errors") or [])[:3]) or f"{bot.get('frames')} frames, no script errors"})
    open_c = [c for c in crashes(tenant, ref)["groups"] if c["state"] != "not seen on the newest version"]
    checks.append({"check": "known player crashes", "ok": True,
                   "note": (f"NOT ASSESSED until players run v{n}: {len(open_c)} crash group(s) still open" if open_c else "none open")})
    with session() as s:
        done = s.scalars(select(S.GameTask).where(S.GameTask.studio_id == st.id, S.GameTask.status == "done",
                                                  S.GameTask.version > prev)).all()
        notes = [t.title for t in done][:30]
    ok = all(c["ok"] for c in checks)
    row = {"at": now().isoformat(), "version": n, "previous": prev, "verdict": "PASS" if ok else "FAIL", "checks": checks,
           "release_notes": notes, "seconds": round(time.time() - t0, 1)}
    d = _data(_studio(tenant, ref))
    d["patches"] = (d["patches"] + [row])[-10:]
    _save(tenant, st.id, d)
    return row


def start_patch_check(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    from . import engine
    if not engine.find():
        raise LiveOpsError("Godot is not installed on this server - the patch check needs the real engine.")
    _POOL.submit(_safe_patch, tenant, st.id)
    return {"started": True, "say": "Patch check chal raha hai: saved replays naye version par, phir ek bot run."}


def _safe_patch(tenant: str, sid: str) -> None:
    try:
        patch_check(tenant, sid)
    except Exception:                                   # noqa: BLE001
        log.exception("patch check %s", sid)


# ================================================================ dashboards + money
def _num(v: str) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def dashboard(tenant: str, ref: str) -> dict[str, Any]:
    from . import runtime as RT
    st = _studio(tenant, ref)
    base = RT.dashboard(tenant, ref)
    rows = _tel_rows(tenant, st.game_id)
    first: dict[str, str] = {}
    days_of: dict[str, set] = defaultdict(set)
    dau: dict[str, set] = defaultdict(set)
    nums: dict[str, list] = defaultdict(list)
    overs: dict[str, int] = defaultdict(int)
    for inst, ev, day, _ab, val, _ver in rows:
        first[inst] = min(first.get(inst, day), day)
        days_of[inst].add(day)
        dau[day].add(inst)
        x = _num(val)
        if x is not None and val != "":
            nums[ev].append(x)
            if ev == "game_over":
                overs[str(int(x)) if x == int(x) else str(x)] += 1
    today = datetime.now(timezone.utc).date()
    cohort = [i for i, d in first.items() if date.fromisoformat(d) <= today - timedelta(days=30)]
    d30 = ({"share": round(sum(1 for i in cohort if (date.fromisoformat(first[i]) + timedelta(days=30)).isoformat() in days_of[i]) / len(cohort), 3),
            "cohort": len(cohort)} if cohort else {"share": None, "cohort": 0, "note": "no player is 30 days old yet"})
    balance = []
    for ev, xs in nums.items():
        if len(xs) < 30:
            continue
        q = statistics.quantiles(xs, n=4)
        iqr = q[2] - q[0]
        lo, hi = q[0] - 1.5 * iqr, q[2] + 1.5 * iqr
        out = [x for x in xs if x < lo or x > hi]
        balance.append({"event": ev, "samples": len(xs), "median": round(statistics.median(xs), 3), "p25": round(q[0], 3),
                        "p75": round(q[2], 3), "outliers": len(out), "outlier_share": round(len(out) / len(xs), 3),
                        "flag": len(out) / len(xs) > 0.05})
    stuck = []
    if len(overs) >= 3:
        med = statistics.median(overs.values())
        stuck = [{"level": lv, "game_overs": n, "x_median": round(n / med, 1)} for lv, n in sorted(overs.items(), key=lambda x: -x[1])
                 if med and n > 2 * med][:5]
    last14 = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    return base | {"d30": d30, "dau": {d: len(dau.get(d, ())) for d in last14}, "balance": balance, "stuck_levels": stuck,
                   "note_values": "numbers come from HoolaRuntime.track(event, value) in the game; a level with more than "
                                  "2x the median game-overs is flagged as a difficulty spike"}


def _parse_day(v: str) -> str:
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    raise LiveOpsError(f"Date samajh nahi aayi: {v!r} (2026-11-15 ya 15-11-2026).")


def import_revenue(tenant: str, ref: str, text: str, source: str = "") -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    if len(text or "") > 200_000:
        raise LiveOpsError("CSV bahut badi hai (200 KB tak).")
    rows = list(csv.reader(io.StringIO(text or "")))
    if rows and rows[0] and re.search(r"date|day|din|tarikh|month", rows[0][0] or "", re.I) and not re.search(r"\d", rows[0][0]):
        rows = rows[1:]                                 # a header line
    if not rows:
        raise LiveOpsError("CSV khaali hai: har line = date, rupees[, source].")
    if len(rows) > 1000:
        raise LiveOpsError("1000 lines tak.")
    got: dict[tuple, float] = {}
    for i, r in enumerate(rows, 1):
        if not r or not any(c.strip() for c in r):
            continue
        if len(r) < 2:
            raise LiveOpsError(f"Line {i}: date, rupees chahiye.")
        day = _parse_day(r[0])
        amt = _num(re.sub(r"[₹,\s]|Rs\.?|INR", "", r[1], flags=re.I))
        if amt is None or abs(amt) > 1e9:
            raise LiveOpsError(f"Line {i}: rupees samajh nahi aaye: {r[1]!r}.")
        src = (r[2].strip() if len(r) > 2 and r[2].strip() else source or "store")[:40]
        got[(day, src)] = got.get((day, src), 0.0) + amt
    keep = {(x["day"], x["source"]): x for x in d["revenue"]}
    for (day, src), amt in got.items():
        keep[(day, src)] = {"day": day, "source": src, "inr": round(amt, 2)}
    d["revenue"] = sorted(keep.values(), key=lambda x: (x["day"], x["source"]))[-3000:]
    _save(tenant, st.id, d)
    return money(tenant, ref) | {"imported": len(got)}


def money(tenant: str, ref: str) -> dict[str, Any]:
    from . import runtime as RT
    st = _studio(tenant, ref)
    d = _data(st)
    g = _game(tenant, st.game_id)
    rows = _tel_rows(tenant, st.game_id)
    dau: dict[str, set] = defaultdict(set)
    buyers: set[str] = set()
    for inst, ev, day, _ab, _v, _ver in rows:
        dau[day].add(inst)
        if ev == "purchase":
            buyers.add(inst)
    by_day: dict[str, float] = defaultdict(float)
    by_src: dict[str, float] = defaultdict(float)
    for x in d["revenue"]:
        by_day[x["day"]] += x["inr"]
        by_src[x["source"]] += x["inr"]
    today = datetime.now(timezone.utc).date()
    last30 = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    rev30 = sum(by_day.get(x, 0.0) for x in last30)
    dau30 = [len(dau.get(x, ())) for x in last30]
    paired = [(by_day[x], len(dau[x])) for x in last30 if x in by_day and dau.get(x)]
    arpdau = round(sum(r for r, _ in paired) / sum(n for _, n in paired), 2) if paired else None
    players = len({i for s_ in dau.values() for i in s_})
    return {"revenue_30d_inr": round(rev30, 2), "revenue_total_inr": round(sum(by_day.values()), 2),
            "by_source": {k: round(v, 2) for k, v in sorted(by_src.items(), key=lambda x: -x[1])},
            "by_day": {x: round(by_day.get(x, 0.0), 2) for x in last30}, "dau_30d": dau30, "arpdau_inr": arpdau,
            "payer_share": round(len(buyers) / players, 4) if players else None,
            "kids": RT.kid_game(g.design),
            "notes": ["Hoola does not see your store: revenue is only what you imported (CSV from Play Console / itch / "
                      "Steam / your payment gateway).",
                      "DAU counts only players who said yes to telemetry, so ARPDAU here is an UPPER bound.",
                      "Payer share needs the game to call HoolaRuntime.track(\"purchase\")."]
            + (["A children's game: no paid random items (loot boxes), no pressure to buy - Hoola will not build them."]
               if RT.kid_game(g.design) else [])}


def view(tenant: str, ref: str) -> dict[str, Any]:
    st = _studio(tenant, ref)
    d = _data(st)
    return {"studio_id": st.id, "telemetry": bool((st.runtime or {}).get("telemetry")),
            "experiments": d["experiments"], "events": [_event_view(e) for e in d["events"]],
            "patches": d["patches"][-5:], "revenue_rows": len(d["revenue"]),
            "paths": sorted(base_values(_bible(tenant, st.id)))[:80],
            "how": "The game reads live values with HoolaRuntime.num(\"player.hp\", fallback) and flag(\"name\"); it "
                   "asks only its own play-link host."}
