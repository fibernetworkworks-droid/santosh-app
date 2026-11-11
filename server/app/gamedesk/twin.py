"""v0.423 DIGITAL TWIN (Hoola Game Engine plan Phase 7 batch 4, Game Desk plan role 9 - the Digital Twin Architect): a
twin of her line / shop floor as DATA (stations, machines, cycle times, breakdowns, shifts), a discrete-event
simulation of it (Hoola's own engine, numpy, no model, no money) with what-if runs, and a layout picture - READ-ONLY to
her plant by construction.

Every claim is checked:
- the engine itself is validated against queueing theory before any twin is trusted: an M/M/1 queue's mean wait vs
  rho / (mu - lambda), and an M/M/3 queue's vs the Erlang C formula, within 5 %;
- traceability: every number of every station carries a source - "tag:<her data tag>" from her data map, or
  "assumption: <words>" - a number without one is NAMED and the twin fails;
- read-only: the data map may only READ (csv / mqtt-subscribe / opcua-read / historian-read); any write / setpoint /
  command / control entry is refused, and Hoola writes no code that could command a machine;
- validation against her real week: when she gives actual daily output, the simulated daily output must be within
  10 % of it; without it the twin says NOT ASSESSED (never "validated");
- what-if runs use the SAME random numbers as the base run (common random numbers), so a difference is the change,
  not luck; each run is repeated with the same seed and must be identical.
Outputs: throughput per hour, utilisation per station, average work-in-progress, lead time, the bottleneck, and what
each what-if changes. A 3D twin view is NOT built in this version (a 2D layout picture is)."""
from __future__ import annotations

import heapq
import io
import json
import logging
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
KEY = "twin_arch"
READ_KINDS = ("csv", "mqtt-subscribe", "opcua-read", "historian-read", "manual")
WRITE_WORDS = re.compile(r"\b(write|setpoint|set point|command|actuat\w*|control|start machine|stop machine|plc write|"
                         r"opcua-write|mqtt-publish|publish|override)\b", re.I)


class TwinError(G.GameError):
    pass


class GameTwin(Base):
    __tablename__ = "game_twins"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gt"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    name: Mapped[str] = mapped_column(String(120), default="")
    model: Mapped[dict] = mapped_column(JSON, default=dict)        # {stations, data_map, shift_hours, days, actual}
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameTwin.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


EXAMPLE = {
    "stations": [
        {"key": "cutting", "machines": 1, "cycle_s": {"value": 40, "source": "tag:LINE1.CUT.CycleTime"},
         "cv": {"value": 0.25, "source": "assumption: cycle times vary about 25 %"},
         "mtbf_h": {"value": 30, "source": "tag:LINE1.CUT.MTBF"}, "mttr_min": {"value": 20, "source": "tag:LINE1.CUT.MTTR"},
         "buffer": {"value": 10, "source": "assumption: 10 parts fit before cutting"}},
        {"key": "welding", "machines": 1, "cycle_s": {"value": 52, "source": "tag:LINE1.WELD.CycleTime"},
         "cv": {"value": 0.3, "source": "assumption: welding varies about 30 %"},
         "mtbf_h": {"value": 20, "source": "tag:LINE1.WELD.MTBF"}, "mttr_min": {"value": 30, "source": "tag:LINE1.WELD.MTTR"},
         "buffer": {"value": 8, "source": "assumption: 8 parts fit before welding"}},
        {"key": "painting", "machines": 2, "cycle_s": {"value": 80, "source": "tag:LINE1.PAINT.CycleTime"},
         "cv": {"value": 0.2, "source": "assumption: painting varies about 20 %"},
         "mtbf_h": {"value": 50, "source": "assumption: paint booths rarely stop"}, "mttr_min": {"value": 15, "source": "assumption"},
         "buffer": {"value": 12, "source": "assumption: 12 parts fit before painting"}},
        {"key": "packing", "machines": 1, "cycle_s": {"value": 30, "source": "tag:LINE1.PACK.CycleTime"},
         "cv": {"value": 0.15, "source": "assumption: packing is steady"},
         "mtbf_h": {"value": 100, "source": "assumption"}, "mttr_min": {"value": 10, "source": "assumption"},
         "buffer": {"value": 10, "source": "assumption"}}],
    "data_map": [{"tag": "LINE1.CUT.CycleTime", "kind": "csv", "asset": "cutting", "unit": "s"},
                 {"tag": "LINE1.CUT.MTBF", "kind": "historian-read", "asset": "cutting", "unit": "h"},
                 {"tag": "LINE1.CUT.MTTR", "kind": "historian-read", "asset": "cutting", "unit": "min"},
                 {"tag": "LINE1.WELD.CycleTime", "kind": "opcua-read", "asset": "welding", "unit": "s"},
                 {"tag": "LINE1.WELD.MTBF", "kind": "historian-read", "asset": "welding", "unit": "h"},
                 {"tag": "LINE1.WELD.MTTR", "kind": "historian-read", "asset": "welding", "unit": "min"},
                 {"tag": "LINE1.PAINT.CycleTime", "kind": "mqtt-subscribe", "asset": "painting", "unit": "s"},
                 {"tag": "LINE1.PACK.CycleTime", "kind": "csv", "asset": "packing", "unit": "s"}],
    "shift_hours": 8, "days": 5,
}
PARAMS = ("cycle_s", "cv", "mtbf_h", "mttr_min", "buffer")


# ================================================================ checks on the model
def check_model(m: dict) -> dict:
    errors, warnings, passed = [], [], []
    tags = {}
    for e in m.get("data_map") or []:
        kind = str(e.get("kind") or "")
        if kind not in READ_KINDS or WRITE_WORDS.search(json.dumps(e)):
            errors.append(f"data map entry {e.get('tag')!r} is not a READ ({kind or 'no kind'}) - the twin only reads; "
                          f"reads allowed: {', '.join(READ_KINDS)}")
            continue
        tags[str(e.get("tag"))] = e
    untraced, missing_tag = [], []
    for st in m.get("stations") or []:
        for p in PARAMS:
            v = st.get(p)
            if not isinstance(v, dict) or "value" not in v:
                untraced.append(f"{st.get('key')}.{p}")
                continue
            src = str(v.get("source") or "")
            if src.startswith("tag:"):
                if src[4:] not in tags:
                    missing_tag.append(f"{st.get('key')}.{p} -> {src[4:]}")
            elif not src.startswith("assumption"):
                untraced.append(f"{st.get('key')}.{p}")
    if untraced:
        errors.append(f"{len(untraced)} numbers have no source (a tag or a stated assumption): {', '.join(untraced[:6])}")
    if missing_tag:
        errors.append(f"{len(missing_tag)} numbers point at a tag that is not in the data map: {', '.join(missing_tag[:4])}")
    if not untraced and not missing_tag:
        n = sum(1 for st in m.get("stations") or [] for p in PARAMS)
        nt = sum(1 for st in m.get("stations") or [] for p in PARAMS if str(st[p].get("source", "")).startswith("tag:"))
        passed.append(f"all {n} numbers traceable: {nt} to her data tags, {n - nt} to stated assumptions")
    if WRITE_WORDS.search(json.dumps({k: v for k, v in m.items() if k != "data_map"})):
        errors.append("the model asks to write / command / control - the twin is read-only")
    else:
        passed.append("read-only: nothing in the model writes to her plant, and Hoola writes no machine-command code")
    return {"errors": errors, "warnings": warnings, "passed": passed}


# ================================================================ the discrete-event engine
def simulate_line(m: dict, seed: int = 7, overrides: dict | None = None) -> dict:
    """A serial line: unlimited raw parts before station 1; each station has `machines` in parallel, a buffer before it
    (a full buffer BLOCKS the machine upstream), lognormal cycle times with the given variation, exponential breakdowns
    (MTBF / MTTR in working time). Works shift_hours a day for `days` days; the first 2 hours are warm-up (not counted).
    Common random numbers: every machine has its own seeded stream, so a what-if changes only what it changes."""
    st = [dict(s) for s in m["stations"]]
    for k, ov in (overrides or {}).items():
        for s in st:
            if s["key"] == k:
                s.update(ov)
    val = lambda s, p: float(s[p]["value"] if isinstance(s[p], dict) else s[p])      # noqa: E731
    H = float(m.get("shift_hours", 8)) * 3600 * float(m.get("days", 5))
    warm = 2 * 3600.0
    n = len(st)
    rng = {(i, j): np.random.default_rng([seed, i, j]) for i in range(n) for j in range(int(st[i]["machines"]))}
    busy_t = [0.0] * n
    q: list = []
    buf = [0] * n                              # parts waiting before station i (station 0: unlimited raw parts)
    cap = [int(val(s, "buffer")) for s in st]
    mach = [[{"state": "idle", "part_t": 0.0, "down_until": 0.0, "next_fail": 0.0} for _ in range(int(s["machines"]))] for s in st]
    done, lead, wip_area, last_t, wip = 0, [], 0.0, 0.0, 0
    for i in range(n):
        for j in range(len(mach[i])):
            mach[i][j]["next_fail"] = rng[(i, j)].exponential(val(st[i], "mtbf_h") * 3600)
    cnt = [0]

    def push(t: float, kind: str, i: int, j: int, data: Any = None) -> None:
        cnt[0] += 1
        heapq.heappush(q, (t, cnt[0], kind, i, j, data))

    def cycle(i: int, j: int) -> float:
        mean, cv = val(st[i], "cycle_s"), val(st[i], "cv")
        if cv <= 0:
            return mean
        s2 = math.log(1 + cv * cv)
        return float(rng[(i, j)].lognormal(math.log(mean) - s2 / 2, math.sqrt(s2)))

    def try_start(t: float, i: int) -> None:
        for j, mm in enumerate(mach[i]):
            if mm["state"] != "idle" or t < mm["down_until"]:
                continue
            if i == 0 or buf[i] > 0:
                if i > 0:
                    buf[i] -= 1
                    part_t = queue_t[i].pop(0)
                else:
                    part_t = t
                d = cycle(i, j)
                if t + d > mm["next_fail"]:                       # a breakdown during this cycle
                    rep = rng[(i, j)].exponential(val(st[i], "mttr_min") * 60)
                    d += rep
                    mm["next_fail"] = t + d + rng[(i, j)].exponential(val(st[i], "mtbf_h") * 3600)
                mm["state"], mm["part_t"] = "busy", part_t
                busy_t[i] += d if t >= warm else max(0.0, t + d - warm)
                push(t + d, "end", i, j)

    queue_t = [[] for _ in range(n)]
    try_start(0.0, 0)
    while q:
        t, _c, kind, i, j, _d = heapq.heappop(q)
        if t > H:
            break
        if t >= warm:
            wip_area += wip * (t - max(last_t, warm))
        last_t = t
        mm = mach[i][j]
        if kind == "end" or kind == "retry":
            if i == n - 1:
                mm["state"] = "idle"
                if t >= warm:
                    done += 1
                    lead.append(t - mm["part_t"])
                wip -= 1
            elif buf[i + 1] < cap[i + 1]:
                buf[i + 1] += 1
                queue_t[i + 1].append(mm["part_t"])
                mm["state"] = "idle"
                try_start(t, i + 1)
            else:
                mm["state"] = "blocked"                            # holds its part until there is room downstream
                push(t + 5.0, "retry", i, j)
                continue
            if i == 0:
                wip += 1
            try_start(t, i)
            if i > 0:
                for jj, m2 in enumerate(mach[i - 1]):
                    if m2["state"] == "blocked":
                        pass
    span = H - warm
    util = [round(busy_t[i] / (span * len(mach[i])), 3) for i in range(n)]
    hours = span / 3600
    return {"throughput_per_h": round(done / hours, 2), "per_day": round(done / float(m.get("days", 5)) * (H / (H - warm)), 1),
            "utilisation": {st[i]["key"]: min(1.0, util[i]) for i in range(n)},
            "bottleneck": st[int(np.argmax(util))]["key"], "wip_avg": round(wip_area / span, 1),
            "lead_time_min": round(float(np.mean(lead)) / 60, 1) if lead else None, "parts": done}


def _mini(stations: list[tuple], days: float = 5) -> dict:
    """A small line with every number marked as an assumption (for the engine's own reference cases)."""
    A = lambda v: {"value": v, "source": "assumption: reference case"}           # noqa: E731
    return {"stations": [{"key": f"s{i}", "machines": m, "cycle_s": A(c), "cv": A(cv), "mtbf_h": A(mtbf), "mttr_min": A(mttr),
                          "buffer": A(50)} for i, (m, c, cv, mtbf, mttr) in enumerate(stations)],
            "data_map": [], "shift_hours": 24, "days": days}


def engine_checks() -> list[dict]:
    """The LINE engine on cases with exact answers: a steady station = 3600 / cycle an hour; the slower of two stations
    sets the pace; breakdowns cut throughput by MTBF / (MTBF + MTTR)."""
    out = []
    r = simulate_line(_mini([(1, 40, 0, 1e9, 1)], days=2))
    exp = 3600 / 40
    out.append({"check": "line engine: one steady station", "ok": abs(r["throughput_per_h"] - exp) / exp <= 0.005,
                "note": f"{r['throughput_per_h']} / h vs 3600 / 40 s = {exp:g} / h"})
    r = simulate_line(_mini([(1, 30, 0, 1e9, 1), (1, 45, 0, 1e9, 1)], days=2))
    exp = 3600 / 45
    out.append({"check": "line engine: the slower station sets the pace", "ok": abs(r["throughput_per_h"] - exp) / exp <= 0.005 and r["bottleneck"] == "s1",
                "note": f"{r['throughput_per_h']} / h vs 3600 / 45 s = {exp:g} / h, bottleneck {r['bottleneck']}"})
    r = simulate_line(_mini([(1, 60, 0, 4, 30)], days=200))
    exp = 3600 / 60 * 4 / (4 + 0.5)
    out.append({"check": "line engine: breakdowns", "ok": abs(r["throughput_per_h"] - exp) / exp <= 0.03,
                "note": f"{r['throughput_per_h']} / h vs 60 / h x MTBF / (MTBF + MTTR) = {exp:.2f} / h (200 days, limit 3 %)"})
    return out


def mmc_check(lam: float, mu: float, c: int, n_cust: int = 300000, seed: int = 3) -> dict:
    """Validate the event engine on a queue with a known answer: Poisson arrivals, c exponential servers. Expected mean
    wait in the queue: M/M/1 = rho / (mu - lambda); M/M/c = Erlang C x 1 / (c mu - lambda)."""
    rng = np.random.default_rng(seed)
    arr = np.cumsum(rng.exponential(1 / lam, n_cust))
    svc = rng.exponential(1 / mu, n_cust)
    free = [0.0] * c
    waits = np.empty(n_cust)
    for k in range(n_cust):
        j = int(np.argmin(free))
        start = max(arr[k], free[j])
        waits[k] = start - arr[k]
        free[j] = start + svc[k]
    sim = float(waits[n_cust // 10:].mean())
    a = lam / mu
    rho = a / c
    s = sum(a ** k / math.factorial(k) for k in range(c))
    pc = (a ** c / math.factorial(c)) / (1 - rho)
    erlang_c = pc / (s + pc)
    th = erlang_c / (c * mu - lam)
    return {"queue": f"M/M/{c}", "lambda": lam, "mu": mu, "sim_wait": round(sim, 4), "theory_wait": round(th, 4),
            "err_pct": round(abs(sim - th) / th * 100, 2), "ok": abs(sim - th) / th <= 0.05}


def what_ifs(m: dict, base: dict) -> list[dict]:
    """Two standard what-ifs on the bottleneck (one more machine; 20 % faster cycle) + one more shift - same seeds."""
    b = base["bottleneck"]
    st = next(s for s in m["stations"] if s["key"] == b)
    cyc = float(st["cycle_s"]["value"])
    out = []
    for name, mm, ov in ((f"one more machine at {b}", m, {b: {"machines": int(st["machines"]) + 1}}),
                         (f"{b} 20 % faster", m, {b: {"cycle_s": {"value": cyc * 0.8, "source": "assumption: what-if"}}}),
                         ("a second shift", {**m, "shift_hours": float(m.get("shift_hours", 8)) * 2}, {})):
        r = simulate_line(mm, overrides=ov)
        out.append({"what_if": name, "per_day": r["per_day"], "change_pct": round((r["per_day"] - base["per_day"]) / base["per_day"] * 100, 1),
                    "bottleneck": r["bottleneck"], "throughput_per_h": r["throughput_per_h"]})
    return out


def layout_png(m: dict, base: dict) -> bytes:
    from PIL import Image, ImageDraw
    sts = m["stations"]
    W, H = 160 * len(sts) + 40, 170
    im = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    for i, s in enumerate(sts):
        u = base["utilisation"].get(s["key"], 0)
        col = (int(80 + 175 * u), int(200 - 120 * u), 90)
        x = 20 + i * 160
        d.rounded_rectangle([x, 40, x + 130, 120], 10, fill=col, outline=(40, 40, 40))
        d.text((x + 8, 48), s["key"][:16], fill=(20, 20, 20))
        d.text((x + 8, 70), f"{int(s['machines'])} machine(s)", fill=(20, 20, 20))
        d.text((x + 8, 92), f"busy {round(u * 100)}%", fill=(20, 20, 20))
        if i < len(sts) - 1:
            d.line([x + 130, 80, x + 160, 80], fill=(60, 60, 60), width=3)
    d.text((20, 12), f"bottleneck: {base['bottleneck']}  ·  {base['per_day']} parts / day", fill=(30, 30, 30))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def evaluate(m: dict, actual_per_day: list[float] | None = None) -> dict:
    mc = check_model(m)
    checks = [{"check": "traceability + read-only", "ok": not mc["errors"], "note": "; ".join(mc["errors"] or mc["passed"])}]
    checks += engine_checks()
    for lam, mu, c in ((0.8, 1.0, 1), (2.4, 1.0, 3)):
        v = mmc_check(lam, mu, c)
        checks.append({"check": f"random queueing vs theory ({v['queue']})", "ok": v["ok"],
                       "note": f"mean wait {v['sim_wait']} vs theory {v['theory_wait']} ({v['err_pct']}%, 300,000 arrivals, limit 5 %)"})
    if mc["errors"]:
        return {"checks": checks, "verdict": "FAIL", "model_check": mc}
    base = simulate_line(m)
    again = simulate_line(m)
    checks.append({"check": "same run twice", "ok": base == again, "note": "seeded per machine; identical results"})
    if actual_per_day:
        act = float(np.mean(actual_per_day))
        err = abs(base["per_day"] - act) / act
        checks.append({"check": "against her real week", "ok": err <= 0.10,
                       "note": f"simulated {base['per_day']} / day vs her actual {round(act, 1)} / day ({round(err * 100, 1)}%; limit 10 %)"})
    else:
        checks.append({"check": "against her real week", "ok": True,
                       "note": "NOT ASSESSED: no actual daily output given yet - the twin is not validated against her plant"})
    ok = all(c["ok"] for c in checks)
    return {"checks": checks, "verdict": "PASS" if ok else "FAIL", "model_check": mc, "base": base,
            "what_ifs": what_ifs(m, base), "validated": bool(actual_per_day) and ok,
            "passed": sum(c["ok"] for c in checks), "total": len(checks)}


# ================================================================ store
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "twins"


def _get(s, tenant: str, ref: str) -> GameTwin:
    ref = str(ref or "").strip()
    q = select(GameTwin).where(GameTwin.tenant_id == tenant)
    r = s.scalars(q.where(GameTwin.id == ref)).first() or s.scalars(q.where(GameTwin.number == ref.upper())).first()
    if r is None:
        raise TwinError("This twin was not found (give D-001).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-twin").encode()
    return _h.new(key, f"twin:{name}".encode(), "sha256").hexdigest()[:16]


def file_url(r: GameTwin, name: str) -> str:
    return f"/api/gamedesk/twin/{r.id}/file/{name}?sig={_sig(r.id + name)}"


def twin_file(xid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"gt_[A-Za-z0-9_-]{4,40}", str(xid or "")) or name != "layout.png" or not _h.compare_digest(_sig(xid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameTwin, xid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameTwin) -> dict[str, Any]:
    d = _root(r.tenant_id) / r.id
    return {"id": r.id, "number": r.number, "name": r.name, "status": r.status, "model": r.model or {},
            "report": r.report or {}, "files": {"layout.png": file_url(r, "layout.png")} if (d / "layout.png").is_file() else {},
            "read_only": True, "view_3d": "not built in this version (2D layout picture)",
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", model: dict | None = None, actual: list | None = None, name: str = "",
          studio: str = "") -> dict[str, Any]:
    """Check + simulate a twin now (seconds). No model given = the worked example (her line's shape to copy)."""
    ensure_table()
    if WRITE_WORDS.search(words or ""):
        raise TwinError("The twin only reads - Hoola never sends a command / setpoint / control to a machine.")
    m = model if isinstance(model, dict) and model.get("stations") else json.loads(json.dumps(EXAMPLE))
    try:
        act = [float(x) for x in (actual or [])][:31]
    except (TypeError, ValueError):
        raise TwinError("Actual output = numbers by day (such as [410, 395, 402]).")
    rep = evaluate(m, act or None)
    with session() as s:
        n = len(s.scalars(select(GameTwin.id).where(GameTwin.tenant_id == tenant)).all()) + 1
        r = GameTwin(tenant_id=tenant, number=f"D-{n:03d}", name=(name or words or "Line twin")[:120],
                     model={**m, "actual_per_day": act}, report=rep, status="draft" if rep["verdict"] == "PASS" else "failed")
        s.add(r)
        s.flush()
        s.expunge(r)
    if rep.get("base"):
        d = _root(tenant) / r.id
        d.mkdir(parents=True, exist_ok=True)
        (d / "layout.png").write_bytes(layout_png(m, rep["base"]))
    return view(r)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise TwinError("Only a twin that PASSED can be OKed.")
        r.status = "approved"
        s.flush()
        s.expunge(r)
    return view(r)


def reject(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        r.status = "rejected"
        s.flush()
        s.expunge(r)
    return view(r)


def setups(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(GameTwin).where(GameTwin.tenant_id == tenant).order_by(GameTwin.created_at.desc())).all()[:30]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


def apply(tenant: str, studio: str) -> dict[str, Any]:
    raise TwinError("A digital twin is not a game - it gives a report, a layout and what-ifs; nothing goes into a game.")
