"""P7 THE WATCH (plan section 10: deploy, watch the outage record + timings for a week; done when no one-part message
is slower than before).

Every chat message of hers is timed, through the Box or not: how long until the first word reached her screen and how
long until the turn ended. Each one lands in a group:

  box         a one-part message the Box ran (its model, its level)
  box_multi   a message with several parts (not part of the speed rule - it does more work)
  before      today's routing: either `pipeline_on` is off (the week before), or a HELD-OUT share of one-part
              messages while it is on (`pipeline_holdout_pct`, default 10) - the fair comparison in the same week,
              same chats, same server, same hours
  skipped     the Box was on but did not run it (media, no tables, a Hoola PC turn...) - counted, never compared

The outage record (`turnbox._OUT` / `_DEAD`) lives in memory and is lost at a restart; here every failure, every
banned model and every hand-over is also written down, so a week can be read back.

The verdict is code, not a feeling: after `pipeline_watch_days` (7) with at least `pipeline_watch_min` (30) timed
one-part messages in BOTH groups, the Box's median and 90th-percentile first word and total time must each be within
`pipeline_watch_slack` (10 %) + 0.3 s of `before`, and its failed share no more than 2 points higher. Anything short
of that names exactly which number is slower. Turning the Box on for good stays her tap (vps-ops `pipeline_on`).

Kept in its own small SQLite file beside the sheets (`data/pipeline/watch.db`), 60 days. No words of hers are kept -
only times, the kind of work, the level and the model.
"""
from __future__ import annotations

import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import get_settings
from . import store

log = logging.getLogger("santosh.pipeline")

KEEP_DAYS = 60
GRACE_S = 0.3
FAIL_POINTS = 2.0
IST = timezone(timedelta(hours=5, minutes=30))
GROUPS = ("box", "before", "box_multi", "skipped")
_LOCK = threading.Lock()
_OPEN: dict[str, dict] = {}          # conv -> the message being timed now (one turn per chat at a time)
STATS = {"timed": 0, "held_out": 0, "outage_rows": 0, "write_failed": 0}
_SWEPT = {"at": 0.0}


# ------------------------------------------------------------------ the file
def _db() -> sqlite3.Connection:
    store.root().mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(store.root() / "watch.db"), timeout=5)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS timing (at REAL, day TEXT, tenant TEXT, conv TEXT, grp TEXT, multi INTEGER, "
              "kind TEXT, level TEXT, model TEXT, first_s REAL, total_s REAL, ok INTEGER, handovers INTEGER, "
              "why TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS timing_at ON timing (at)")
    c.execute("CREATE TABLE IF NOT EXISTS outage (at REAL, day TEXT, model TEXT, event TEXT, why TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS outage_at ON outage (at)")
    return c


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, IST).strftime("%Y-%m-%d")


def _sweep(c: sqlite3.Connection, now: float) -> None:
    if now - _SWEPT["at"] < 3600:
        return
    _SWEPT["at"] = now
    cut = now - KEEP_DAYS * 86400
    c.execute("DELETE FROM timing WHERE at < ?", (cut,))
    c.execute("DELETE FROM outage WHERE at < ?", (cut,))


def on() -> bool:
    return bool(getattr(get_settings(), "pipeline_watch", True))


# ------------------------------------------------------------------ timing one message
def start(conv: str, tenant: str = "", actor: str = "owner", voice: bool = False,
          now: float | None = None) -> dict | None:
    """Start the clock for her chat message (owner / her approved turn, not a call). None = not timed."""
    if not on() or voice or not conv:
        return None
    actor = actor or "owner"
    if not (actor == "owner" or actor.startswith("approved:")):
        return None
    rec = {"conv": conv, "tenant": tenant or "", "t0": now if now is not None else time.time(), "first": None,
           "grp": "before", "multi": 0, "kind": "", "level": "", "model": "", "why": "", "sheet": None}
    with _LOCK:
        _OPEN[conv] = rec
    return rec


def place(rec: dict | None, b: dict | None) -> None:
    """Which group the message is in, from what the Box did with it (`turnbox.begin`'s record, or None)."""
    if not rec:
        return
    if not bool(getattr(get_settings(), "pipeline_on", False)):
        rec["grp"], rec["why"] = "before", "pipeline_on off"
        return
    if not b:
        rec["grp"], rec["why"] = "skipped", "the Box did not open a sheet (no tables / a tapped branch)"
        return
    sh = b.get("sheet") or {}
    rec["sheet"] = sh
    parts = sh.get("parts") or []
    last = parts[-1] if parts else {}
    rec["kind"] = last.get("kind") or ""
    rec["level"] = last.get("level_used") or last.get("level") or ""
    rec["model"] = (last.get("model") or {}).get("id") or ""
    if sh.get("multi") or len(parts) > 1:
        rec["grp"], rec["multi"] = "box_multi", len(parts)
    elif last.get("applied"):
        rec["grp"] = "box"
    elif str(last.get("not_applied") or "").startswith(HELD):
        rec["grp"], rec["why"] = "before", "held out"
        rec["model"] = ""
    else:
        rec["grp"], rec["why"] = "skipped", str(last.get("not_applied") or "")[:160]


def heard(conv: str, kind: str, payload: dict | None) -> None:
    """A word reached her screen (a streamed delta, or a whole reply). Only the first one is kept."""
    rec = _OPEN.get(conv)
    if not rec or rec["first"] is not None:
        return
    p = payload or {}
    if kind == "delta":
        if not str(p.get("text") or "").strip():
            return
    elif kind == "message":
        if p.get("role") != "assistant" or p.get("ack") or p.get("source") in ("error", "budget"):
            return
        if not str(p.get("text") or "").strip():
            return
    else:
        return
    rec["first"] = round(time.time() - rec["t0"], 3)


def stop(rec: dict | None, ok: bool = True, now: float | None = None) -> dict | None:
    """The turn ended: write the row. Never breaks the turn."""
    if not rec:
        return None
    t = now if now is not None else time.time()
    with _LOCK:
        if _OPEN.get(rec["conv"]) is rec:
            _OPEN.pop(rec["conv"], None)
    sh = rec.get("sheet") or {}
    if rec["grp"] in ("box", "box_multi") and sh.get("parts"):
        last = sh["parts"][-1]
        rec["model"] = last.get("ran_on") or rec["model"]
        rec["level"] = last.get("level_used") or rec["level"]
        if any(p.get("state") == "failed" for p in sh["parts"]):
            ok = False
    hand = sum(len(p.get("handover") or []) for p in (sh.get("parts") or []))
    row = (round(rec["t0"], 3), _day(rec["t0"]), rec["tenant"], rec["conv"], rec["grp"], int(rec["multi"]),
           rec["kind"], rec["level"], rec["model"], rec["first"], round(t - rec["t0"], 3), 1 if ok else 0, hand,
           rec["why"])
    try:
        with _LOCK:
            c = _db()
            try:
                c.execute("INSERT INTO timing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
                _sweep(c, t)
                c.commit()
            finally:
                c.close()
        STATS["timed"] += 1
    except Exception as e:   # noqa: BLE001 - the watch never breaks her turn
        STATS["write_failed"] += 1
        log.warning("pipeline watch: writing a timing failed (%s)", str(e)[:120])
    return {"grp": rec["grp"], "first_s": rec["first"], "total_s": row[10], "ok": ok}


# ------------------------------------------------------------------ the held-out share
HELD = "held out for the P7 watch"


def hold_out(conv: str = "") -> bool:
    """True for about `pipeline_holdout_pct` % of one-part chat messages while the Box is on: that message runs as
    today's turn and is timed as `before`, so the week has a fair comparison. C1: with a chat id the choice is made
    per CHAT (the same chat is always held out or always not), so one chat never swaps models between messages."""
    pct = float(getattr(get_settings(), "pipeline_holdout_pct", 10) or 0)
    if pct <= 0 or not on():
        return False
    if conv:
        import hashlib
        hit = int(hashlib.sha1(conv.encode()).hexdigest()[:8], 16) % 10000 < pct * 100
    else:
        hit = random.random() * 100 < pct
    if hit:
        STATS["held_out"] += 1
    return hit


# ------------------------------------------------------------------ the outage record, written down
def outage(model: str, event: str, why: str = "", now: float | None = None) -> None:
    """event: fail | dead | handover. Written for the week's read-back; the in-memory record still decides."""
    if not on() or not model:
        return
    t = now if now is not None else time.time()
    try:
        with _LOCK:
            c = _db()
            try:
                c.execute("INSERT INTO outage VALUES (?,?,?,?,?)", (round(t, 3), _day(t), str(model)[:120],
                                                                     event, str(why or "")[:200]))
                c.commit()
            finally:
                c.close()
        STATS["outage_rows"] += 1
    except Exception as e:   # noqa: BLE001
        STATS["write_failed"] += 1
        log.debug("pipeline watch: outage row failed (%s)", e)


# ------------------------------------------------------------------ reading the week back
def _pct(xs: list[float], q: float) -> float | None:
    """Nearest-rank percentile (q 0..100) - no interpolation, so a small sample is not flattered."""
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = max(1, min(len(xs), int(-(-q * len(xs) // 100))))
    return round(xs[k - 1], 2)


def _stats(rows: list[dict]) -> dict[str, Any]:
    first = [r["first_s"] for r in rows if r["first_s"] is not None]
    total = [r["total_s"] for r in rows]
    n = len(rows)
    return {"n": n, "timed_first": len(first),
            "first_med": _pct(first, 50), "first_p90": _pct(first, 90),
            "total_med": _pct(total, 50), "total_p90": _pct(total, 90),
            "failed_pct": round(100 * sum(1 for r in rows if not r["ok"]) / n, 1) if n else None,
            "no_words_pct": round(100 * (n - len(first)) / n, 1) if n else None,
            "handovers": sum(r["handovers"] for r in rows)}


def rows(days: float = 7, now: float | None = None, tenant: str = "") -> tuple[list[dict], list[dict]]:
    t = now if now is not None else time.time()
    since = t - days * 86400
    c = _db()
    try:
        c.row_factory = sqlite3.Row
        q = "SELECT * FROM timing WHERE at >= ?" + (" AND tenant = ?" if tenant else "") + " ORDER BY at"
        tim = [dict(r) for r in c.execute(q, (since, tenant) if tenant else (since,))]
        out = [dict(r) for r in c.execute("SELECT * FROM outage WHERE at >= ? ORDER BY at", (since,))]
    finally:
        c.close()
    return tim, out


def _slower(name: str, box: float | None, before: float | None, slack: float) -> str:
    if box is None or before is None:
        return ""
    if box > before * (1 + slack) + GRACE_S:
        return f"{name} {box:.1f} s vs {before:.1f} s before"
    return ""


def verdict(groups: dict[str, dict], span_days: float, now: float | None = None) -> dict[str, Any]:
    st = get_settings()
    need_days = float(getattr(st, "pipeline_watch_days", 7) or 7)
    need_n = int(getattr(st, "pipeline_watch_min", 30) or 30)
    slack = float(getattr(st, "pipeline_watch_slack", 0.10) or 0)
    bx, bf = groups.get("box") or {}, groups.get("before") or {}
    wait: list[str] = []
    if span_days < need_days:
        wait.append(f"{span_days:.1f} of {need_days:.0f} days watched")
    if (bx.get("timed_first") or 0) < need_n:
        wait.append(f"{bx.get('timed_first') or 0} of {need_n} Box messages")
    if (bf.get("timed_first") or 0) < need_n:
        wait.append(f"{bf.get('timed_first') or 0} of {need_n} messages on today's routing to compare with")
    slow = [s for s in (
        _slower("first word (median)", bx.get("first_med"), bf.get("first_med"), slack),
        _slower("first word (slowest 10 %)", bx.get("first_p90"), bf.get("first_p90"), slack),
        _slower("whole reply (median)", bx.get("total_med"), bf.get("total_med"), slack),
        _slower("whole reply (slowest 10 %)", bx.get("total_p90"), bf.get("total_p90"), slack)) if s]
    if bx.get("failed_pct") is not None and bf.get("failed_pct") is not None \
            and bx["failed_pct"] > bf["failed_pct"] + FAIL_POINTS:
        slow.append(f"failed {bx['failed_pct']:.1f} % vs {bf['failed_pct']:.1f} % before")
    if slow:
        state = "slower"
        say = "The Box is slower on one-part messages: " + "; ".join(slow) + "."
        if wait:
            say += " (Still watching: " + "; ".join(wait) + ".)"
    elif wait:
        state = "watching"
        say = "Still watching: " + "; ".join(wait) + ". Nothing slower so far." if (bx.get("n") and bf.get("n")) \
            else "Still watching: " + "; ".join(wait) + "."
    else:
        state = "ready"
        say = (f"A week watched: one-part messages through the Box are not slower than before "
               f"(first word {bx['first_med']:.1f} s vs {bf['first_med']:.1f} s, whole reply {bx['total_med']:.1f} s "
               f"vs {bf['total_med']:.1f} s). The Box can stay on for good - her tap (vps-ops pipeline_on).")
    return {"state": state, "ready": state == "ready", "say": say, "slower": slow, "waiting": wait,
            "rule": {"days": need_days, "min_messages": need_n, "slack_pct": round(slack * 100), "grace_s": GRACE_S,
                     "fail_points": FAIL_POINTS}}


def report(days: float = 7, now: float | None = None, tenant: str = "") -> dict[str, Any]:
    t = now if now is not None else time.time()
    tim, out = rows(days, t, tenant)
    by: dict[str, list[dict]] = {g: [r for r in tim if r["grp"] == g] for g in GROUPS}
    groups = {g: _stats(v) for g, v in by.items()}
    box_at = [r["at"] for r in by["box"]]
    span = round((t - min(box_at)) / 86400, 2) if box_at else 0.0
    kinds: dict[str, dict] = {}
    for g in ("box", "before"):
        for r in by[g]:
            k = r["kind"] or "?"
            kinds.setdefault(k, {"box": [], "before": []})[g].append(r)
    by_kind = {k: {g: {"n": len(v), "first_med": _pct([x["first_s"] for x in v if x["first_s"] is not None], 50),
                       "total_med": _pct([x["total_s"] for x in v], 50)} for g, v in d.items()}
               for k, d in sorted(kinds.items())}
    days_rows: dict[str, dict] = {}
    for r in tim:
        if r["grp"] not in ("box", "before"):
            continue
        d = days_rows.setdefault(r["day"], {"box": [], "before": []})
        d[r["grp"]].append(r)
    per_day = [{"day": d, **{g: {"n": len(v), "first_med": _pct([x["first_s"] for x in v
                                                                  if x["first_s"] is not None], 50)}
                             for g, v in g2.items()}} for d, g2 in sorted(days_rows.items())]
    models: dict[str, dict] = {}
    for r in by["box"] + by["box_multi"]:
        m = models.setdefault(r["model"] or "?", {"messages": 0, "failed": 0, "first": [], "fails": 0, "dead": "",
                                                  "handed_over": 0, "pauses": 0})
        m["messages"] += 1
        m["failed"] += 0 if r["ok"] else 1
        if r["first_s"] is not None:
            m["first"].append(r["first_s"])
    fail_at: dict[str, list[float]] = {}
    for o in out:
        m = models.setdefault(o["model"], {"messages": 0, "failed": 0, "first": [], "fails": 0, "dead": "",
                                           "handed_over": 0, "pauses": 0})
        if o["event"] == "fail":
            m["fails"] += 1
            fail_at.setdefault(o["model"], []).append(o["at"])
        elif o["event"] == "dead":
            m["dead"] = o["why"]
        elif o["event"] == "handover":
            m["handed_over"] += 1
    for mid, ats in fail_at.items():            # two failures within 10 minutes = one pause (turnbox's own rule)
        last = -1e18
        for i in range(1, len(ats)):
            if ats[i] - ats[i - 1] <= 600 and ats[i - 1] > last:
                models[mid]["pauses"] += 1
                last = ats[i]
    for m in models.values():
        m["first_med"] = _pct(m.pop("first"), 50)
    return {"days": days, "since": datetime.fromtimestamp(t - days * 86400, IST).isoformat(timespec="minutes"),
            "on": bool(getattr(get_settings(), "pipeline_on", False)),
            "holdout_pct": float(getattr(get_settings(), "pipeline_holdout_pct", 10) or 0),
            "span_days": span, "groups": groups, "by_kind": by_kind, "per_day": per_day,
            "models": dict(sorted(models.items(), key=lambda kv: -kv[1]["messages"])),
            "skipped_why": _top([r["why"] for r in by["skipped"]]),
            "verdict": verdict(groups, span, t), "stats": dict(STATS)}


def _top(xs: list[str], n: int = 6) -> list[dict]:
    c: dict[str, int] = {}
    for x in xs:
        c[x or "?"] = c.get(x or "?", 0) + 1
    return [{"why": k, "n": v} for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:n]]


def _f(x: float | None) -> str:
    return "-" if x is None else f"{x:.1f}s"


def main() -> int:
    r = report()
    print(f"== the P7 watch (last {r['days']:.0f} days, since {r['since']}) - pipeline_on {r['on']}, "
          f"held out {r['holdout_pct']:.0f} %")
    print(f"== verdict: {r['verdict']['state'].upper()} - {r['verdict']['say']}")
    print("\n== one-part messages            n   first-word med / p90   whole reply med / p90   failed  no words  "
          "hand-overs")
    for g in GROUPS:
        s = r["groups"][g]
        print(f"   {g:<12} {s['n']:>17}   {_f(s['first_med']):>8} / {_f(s['first_p90']):<8}   "
              f"{_f(s['total_med']):>8} / {_f(s['total_p90']):<8}   {s['failed_pct'] if s['failed_pct'] is not None else '-':>5}%  "
              f"{s['no_words_pct'] if s['no_words_pct'] is not None else '-':>6}%  {s['handovers']:>6}")
    if r["per_day"]:
        print("\n== per day (first word median)   Box / before")
        for d in r["per_day"]:
            print(f"   {d['day']}   {_f(d['box']['first_med'])} ({d['box']['n']}) / "
                  f"{_f(d['before']['first_med'])} ({d['before']['n']})")
    if r["by_kind"]:
        print("\n== per kind of work (first word median)   Box / before")
        for k, d in r["by_kind"].items():
            print(f"   {k:<16} {_f(d['box']['first_med'])} ({d['box']['n']}) / {_f(d['before']['first_med'])} "
                  f"({d['before']['n']})")
    if r["models"]:
        print("\n== models                                     messages failed first-word fails pauses hand-overs off")
        for mid, m in list(r["models"].items())[:25]:
            print(f"   {mid[:44]:<44} {m['messages']:>8} {m['failed']:>6} {_f(m['first_med']):>10} {m['fails']:>5} "
                  f"{m['pauses']:>6} {m['handed_over']:>10} {('yes: ' + m['dead'][:60]) if m['dead'] else ''}")
    if r["skipped_why"]:
        print("\n== the Box was on but did not run these")
        for s in r["skipped_why"]:
            print(f"   {s['n']:>4}  {s['why'][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
