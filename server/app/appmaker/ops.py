"""v0.546 CHALTA KAAM (App Sahayak Pillar L, Phase 62+, the last of docs/COMPLEX_APPS_PLAN.md): the app after it
ships - how many people use it, how fast it answers, what is failing, and what it COSTS her.

Pillars A-K build and prove an app. None of them tells her, a month later, that her app is slower than it was, that
one in twenty calls is failing, or that it has quietly cost Rs 900. This is the part she needs when nobody is
looking, so three rules shape all of it:

  1. MEASURED, NOT ESTIMATED. Latency and errors come from the app's OWN requests through one middleware - the real
     thing, every call, no sampling toggle to forget. Cost comes from `usage.run_meter`, the same ledger Hoola bills
     everything else with: the rupees are what her model calls really cost, not a guess from a table.
  2. WHAT IS NOT PRICED IS COUNTED AND SAID. Push, SMS and connector calls are counted, and their rupees are
     reported as `not priced` until she tells Hoola what her provider charges. The mapsbill / research-bill rule:
     an unpriced thing is never silently zero, because a zero she believes is worse than a blank she can fill.
  3. AN ALERT IS A RULE, NOT A FEELING. Each one is arithmetic over her own history with a stated threshold, and it
     reaches her chat ONCE a day per kind. An alert that cries every hour is an alert she turns off.

Latency is kept as fixed-bin histograms per hour, so four worker processes can merge their counts without a lock
fight and a fortnight of traffic stays a few KB. p50 / p95 are therefore ESTIMATED FROM BINS and the card says so -
a precise-looking number nobody can reproduce is worse than an honest band.
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ..db import now
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"seen": 0, "flushes": 0, "alerts": 0, "spend": 0}

IST = timezone(timedelta(hours=5, minutes=30))
KEEP_HOURS = 24 * 14                                     # a fortnight of hour buckets
FLUSH_EVERY = 20.0                                       # seconds; a worker holds at most this much in memory
# the bin edges, in milliseconds. A request lands in the first bin it is under.
BINS = (50, 100, 200, 400, 800, 1500, 3000, 6000, 10 ** 9)
BIN_LABELS = ("<50ms", "50-100ms", "100-200ms", "200-400ms", "400-800ms", "0.8-1.5s", "1.5-3s", "3-6s", ">6s")

# what a cost row may be. Only `model` carries real rupees today - the rest are counted and said.
KINDS = {"model": "Hoola's AI (build / logic / checks)", "push": "notifications", "sms": "SMS",
         "connect": "connector calls", "storage": "files + data"}
PRICED = ("model",)

# alert rules: (key, the line, the threshold text) - every one is arithmetic, below
ALERT_ONCE_HOURS = 24

_BUF: dict[str, dict[str, Any]] = {}                     # app_key -> {hour: {...}} waiting to be written
_LOCK = threading.Lock()
_LAST = [0.0]


# ---------------------------------------------------------------- the funnel: every app-api request
def seen(app_key: str, ms: float, status: int, path: str = "") -> None:
    """One finished request of ONE app. Cheap on purpose: a dict bump, no I/O, no lock held across work."""
    if not app_key:
        return
    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    b = 0
    for i, edge in enumerate(BINS):
        if ms < edge:
            b = i
            break
    with _LOCK:
        app = _BUF.setdefault(app_key, {})
        row = app.setdefault(hour, {"n": 0, "ms": 0.0, "err": 0, "bins": [0] * len(BINS), "slow": 0.0})
        row["n"] += 1
        row["ms"] += float(ms)
        row["bins"][b] += 1
        row["slow"] = max(row["slow"], float(ms))
        if status >= 500 or status == 0:
            row["err"] += 1
    STATS["seen"] += 1
    if time.time() - _LAST[0] > FLUSH_EVERY:
        flush()


def flush() -> None:
    """Merge this worker's counts into each app's file. Several workers merge; nobody overwrites."""
    with _LOCK:
        if not _BUF:
            _LAST[0] = time.time()
            return
        take = {k: v for k, v in _BUF.items()}
        _BUF.clear()
    _LAST[0] = time.time()
    for app_key, hours in take.items():
        try:
            _merge(app_key, hours)
        except Exception:                                           # noqa: BLE001  - telemetry never breaks a request
            log.debug("ops flush", exc_info=True)
    STATS["flushes"] += 1


def _merge(app_key: str, hours: dict[str, Any]) -> None:
    from . import backend as BE
    from . import locks as LK
    r = BE.by_key(app_key)
    f = _file(r)
    with LK.hold(f"ops:{r.id}"):
        data = _read(f)
        traf = data.setdefault("traffic", {})
        for hour, row in hours.items():
            cur = traf.setdefault(hour, {"n": 0, "ms": 0.0, "err": 0, "bins": [0] * len(BINS), "slow": 0.0})
            cur["n"] += row["n"]
            cur["ms"] += row["ms"]
            cur["err"] += row["err"]
            cur["slow"] = max(float(cur.get("slow") or 0), row["slow"])
            for i, c in enumerate(row["bins"]):
                cur["bins"][i] += c
        cut = (datetime.now(timezone.utc) - timedelta(hours=KEEP_HOURS)).strftime("%Y-%m-%dT%H")
        data["traffic"] = {h: v for h, v in traf.items() if h >= cut}
        _write(f, data)


def _file(r: AppProject):
    from . import kit as K
    d = K.app_dir(r.tenant_id, r.id) / "backend"
    d.mkdir(parents=True, exist_ok=True)
    return d / "ops.json"


def _read(f) -> dict[str, Any]:
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except (OSError, ValueError):
        return {}


def _write(f, data: dict[str, Any]) -> None:
    f.write_text(json.dumps(data, ensure_ascii=False))


# ---------------------------------------------------------------- what the app costs her
def spend(r: AppProject, kind: str, inr: float = 0.0, count: int = 1, note: str = "") -> dict[str, Any]:
    """One cost row. `model` carries real rupees from usage.run_meter; everything else is COUNTED and said."""
    from . import locks as LK
    kind = kind if kind in KINDS else "model"
    f = _file(r)
    with LK.hold(f"ops:{r.id}"):
        data = _read(f)
        rows = data.setdefault("spend", [])
        rows.append({"at": now().isoformat(), "kind": kind, "inr": round(float(inr or 0), 4),
                     "count": int(count or 1), "note": str(note or "")[:80]})
        cut = (now() - timedelta(days=120)).isoformat()
        data["spend"] = [x for x in rows if str(x.get("at", "")) >= cut][-4000:]
        _write(f, data)
    STATS["spend"] += 1
    return {"ok": True, "kind": kind, "inr": round(float(inr or 0), 4)}


def meter(r: AppProject, kind: str = "model", note: str = ""):
    """Wrap a job that calls the brain: whatever it really costs lands on THIS app's bill.

        with ops.meter(r, note="build"):
            ...the build...
    """
    from .. import usage

    class _M:
        def __enter__(self):
            self.cm = usage.run_meter()
            self.acc = self.cm.__enter__()
            return self.acc

        def __exit__(self, *a):
            self.cm.__exit__(*a)
            try:
                usd = float(self.acc.get("usd") or 0)
                if usd > 0 or self.acc.get("calls"):
                    spend(r, kind, usd * usage.usd_inr(), int(self.acc.get("calls") or 1), note)
            except Exception:                                       # noqa: BLE001
                log.debug("ops meter", exc_info=True)
            return False
    return _M()


# ---------------------------------------------------------------- reading it back
def _pcts(bins: list[int]) -> dict[str, Any]:
    """p50 / p95 ESTIMATED from the bins - reported as a band, because that is what bins can honestly say."""
    total = sum(bins)
    if not total:
        return {"p50": None, "p95": None, "estimated": True}
    out: dict[str, Any] = {"estimated": True}
    for name, want in (("p50", 0.5), ("p95", 0.95)):
        seen_n, mark = 0, total * want
        for i, c in enumerate(bins):
            seen_n += c
            if seen_n >= mark:
                out[name] = BIN_LABELS[i]
                break
        out.setdefault(name, BIN_LABELS[-1])
    return out


def traffic(r: AppProject, days: int = 14) -> dict[str, Any]:
    data = _read(_file(r))
    cut = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H")
    rows = {h: v for h, v in (data.get("traffic") or {}).items() if h >= cut}
    n = sum(int(v.get("n") or 0) for v in rows.values())
    err = sum(int(v.get("err") or 0) for v in rows.values())
    ms = sum(float(v.get("ms") or 0) for v in rows.values())
    bins = [0] * len(BINS)
    for v in rows.values():
        for i, c in enumerate(v.get("bins") or []):
            if i < len(bins):
                bins[i] += int(c)
    per_day: dict[str, int] = {}
    for h, v in rows.items():
        d = h[:10]
        per_day[d] = per_day.get(d, 0) + int(v.get("n") or 0)
    return {"days": days, "calls": n, "errors": err,
            "error_percent": round(100 * err / n, 2) if n else 0.0,
            "average_ms": round(ms / n) if n else None,
            "slowest_ms": round(max((float(v.get("slow") or 0) for v in rows.values()), default=0)),
            **_pcts(bins), "per_day": dict(sorted(per_day.items())),
            "bins": {BIN_LABELS[i]: bins[i] for i in range(len(bins)) if bins[i]}}


def cost(r: AppProject, days: int = 30) -> dict[str, Any]:
    data = _read(_file(r))
    cut = (now() - timedelta(days=days)).isoformat()
    rows = [x for x in (data.get("spend") or []) if str(x.get("at", "")) >= cut]
    by: dict[str, dict[str, Any]] = {}
    for x in rows:
        k = x.get("kind") or "model"
        b = by.setdefault(k, {"kind": k, "label": KINDS.get(k, k), "inr": 0.0, "count": 0,
                              "priced": k in PRICED})
        b["inr"] += float(x.get("inr") or 0)
        b["count"] += int(x.get("count") or 1)
    for b in by.values():
        b["inr"] = round(b["inr"], 2)
    total = round(sum(b["inr"] for b in by.values()), 2)
    unpriced = sorted(k for k, b in by.items() if not b["priced"] and b["count"])
    return {"days": days, "inr": total, "by_kind": sorted(by.values(), key=lambda x: -x["inr"]),
            "not_priced": [KINDS[k] for k in unpriced],
            "says": (f"Rs {total:.2f} spent on this app in the last {days} days"
                     + (f" (and {', '.join(KINDS[k] for k in unpriced)} has no price set yet)" if unpriced else "")
                     if (total or unpriced) else f"No cost in the last {days} days")}


# ---------------------------------------------------------------- the one card she reads
def dashboard(r: AppProject, days: int = 14) -> dict[str, Any]:
    """Users, orders, errors, latency, cost - and what is NOT measured, said out loud."""
    from . import backend as BE
    from . import meter as ME
    from . import quality as QA
    use, gaps = {}, []
    try:
        use = ME.usage(r)
    except Exception:                                               # noqa: BLE001
        gaps.append("storage / rows could not be read")
    tr = traffic(r, days)
    cs = cost(r, 30)
    try:
        field = QA.field_health(r, days)
    except Exception:                                               # noqa: BLE001
        field = {"says": "", "crashes": 0, "anrs": 0}
    orders = 0
    try:
        sch = BE.schema(r)
        key = sch.get("order") or ""
        orders = int((use.get("lists") or {}).get(key, 0)) if key else 0
    except Exception:                                               # noqa: BLE001
        pass
    if not tr["calls"]:
        gaps.append("no call has come from the app yet (nobody is using it, or the build is old)")
    if not cs["inr"] and not cs["not_priced"]:
        gaps.append("no cost has been recorded")
    return {"app": r.id, "name": r.name, "days": days,
            "people": {"accounts": int(use.get("accounts") or 0), "rows": int(use.get("rows") or 0),
                       "orders": orders, "writes_today": int(use.get("writes_today") or 0)},
            "traffic": tr, "cost": cs, "field": field,
            "limits": {"percent": use.get("percent") or {}, "full": use.get("full") or []},
            "alerts": _open_alerts(r), "not_measured": gaps, "says": _says(tr, cs, field, use)}


def _says(tr: dict[str, Any], cs: dict[str, Any], field: dict[str, Any], use: dict[str, Any]) -> str:
    bits = []
    if tr["calls"]:
        bits.append(f"{tr['calls']} calls, {tr['error_percent']}% fail, p95 {tr.get('p95') or '?'}")
    else:
        bits.append("no calls yet")
    if int(use.get("accounts") or 0):
        bits.append(f"{use['accounts']} people")
    if cs["inr"]:
        bits.append(f"Rs {cs['inr']:.2f} (30 days)")
    if field.get("crashes") or field.get("anrs"):
        bits.append(f"{field.get('crashes', 0)} crash" + (f" + {field['anrs']} ANR" if field.get("anrs") else ""))
    return "; ".join(bits) + "."


# ---------------------------------------------------------------- alerts: arithmetic, once a day, in her chat
def rules(r: AppProject, days: int = 14) -> list[dict[str, Any]]:
    """Every alert is a rule over HER OWN history with a stated threshold. Nothing here is a feeling."""
    out: list[dict[str, Any]] = []
    data = _read(_file(r))
    traf = data.get("traffic") or {}
    now_h = datetime.now(timezone.utc)
    last24 = {h: v for h, v in traf.items() if h >= (now_h - timedelta(hours=24)).strftime("%Y-%m-%dT%H")}
    before = {h: v for h, v in traf.items()
              if (now_h - timedelta(days=days)).strftime("%Y-%m-%dT%H") <= h
              < (now_h - timedelta(hours=24)).strftime("%Y-%m-%dT%H")}

    def agg(rows):
        n = sum(int(v.get("n") or 0) for v in rows.values())
        err = sum(int(v.get("err") or 0) for v in rows.values())
        ms = sum(float(v.get("ms") or 0) for v in rows.values())
        return n, err, (ms / n if n else 0.0)

    n24, e24, avg24 = agg(last24)
    nb, eb, avgb = agg(before)

    # 1. failures. 5% of a real number of calls is a real problem; below 20 calls it is noise.
    if n24 >= 20 and e24 / n24 >= 0.05:
        out.append({"key": "errors", "level": "bad",
                    "say": f"About {round(100 * e24 / n24)}% of your app's calls are failing (last 24 hours, "
                           f"{e24}/{n24}). Something is wrong with the server or the app - say 'run the app check'."})
    # 2. slower than it was. Twice her own average, not a number from a book.
    if n24 >= 20 and nb >= 50 and avgb > 0 and avg24 >= 2 * avgb and avg24 >= 400:
        out.append({"key": "slow", "level": "warn",
                    "say": f"The app has become slower than before: now {round(avg24)}ms, earlier {round(avgb)}ms "
                           f"(average of the last {days} days). The data may have grown."})
    # 3. crashes / ANRs from real phones
    try:
        from . import quality as QA
        fh = QA.field_health(r, 2)
        if fh.get("open"):
            out.append({"key": "crash", "level": "bad",
                        "say": f"{fh.get('crashes', 0)} crash(es)"
                               + (f" and {fh['anrs']} ANR (app freeze)" if fh.get("anrs") else "")
                               + " came from real phones. Say 'fix the crash'."})
    except Exception:                                               # noqa: BLE001
        pass
    # 4. the storage / rows ceiling (v0.390's own numbers, said here too)
    try:
        from . import meter as ME
        u = ME.usage(r)
        near = [k for k, v in (u.get("percent") or {}).items() if v >= 90]
        if near:
            out.append({"key": "limits", "level": "warn",
                        "say": f"The app's space is filling up ({', '.join(near)} above 90%). Delete old data "
                               "or raise the limit."})
    except Exception:                                               # noqa: BLE001
        pass
    # 5. cost: this month against the three months before it, her own numbers
    cs30 = cost(r, 30)["inr"]
    older = cost(r, 120)["inr"] - cs30
    if cs30 >= 100 and older > 0 and cs30 >= 2 * (older / 3):
        out.append({"key": "cost", "level": "warn",
                    "say": f"This app cost Rs {cs30:.0f} this month - about double the earlier months. "
                           "Say 'show the app's costs'."})
    return out


def _open_alerts(r: AppProject) -> list[dict[str, Any]]:
    try:
        return rules(r)
    except Exception:                                               # noqa: BLE001
        return []


def watch(r: AppProject) -> dict[str, Any]:
    """The worker's daily look. One line per kind per day - an alert that cries every hour is one she turns off."""
    from . import locks as LK
    told = []
    fresh = rules(r)
    if not fresh:
        return {"sent": 0}
    f = _file(r)
    with LK.hold(f"ops:{r.id}"):
        data = _read(f)
        seen_at = data.setdefault("told", {})
        cutoff = (now() - timedelta(hours=ALERT_ONCE_HOURS)).isoformat()
        for a in fresh:
            if str(seen_at.get(a["key"], "")) >= cutoff:
                continue
            seen_at[a["key"]] = now().isoformat()
            told.append(a)
        _write(f, data)
    for a in told:
        try:
            from .android.service import _note
            _note(r, a["say"])
        except Exception:                                           # noqa: BLE001
            log.debug("ops alert", exc_info=True)
    STATS["alerts"] += len(told)
    return {"sent": len(told), "alerts": told}


# ---------------------------------------------------------------- what the next big job will cost
BIG_JOBS = {"build": "new build (Android)", "ios": "new build (iPhone)", "logic": "logic draft",
            "naksha": "plan (the whole app)", "jaanch": "test stories", "design": "design again"}


def estimate(r: AppProject, job: str = "build") -> dict[str, Any]:
    """Before a big job: what it cost HER last times, not a number from a table.

    Her own median is the only honest estimate. With nothing to go on it says so - 'pata nahi' is a real answer and
    a made-up rupee figure is not.
    """
    job = job if job in BIG_JOBS else "build"
    data = _read(_file(r))
    runs = [float(x.get("inr") or 0) for x in (data.get("spend") or [])
            if x.get("kind") == "model" and job in str(x.get("note") or "")]
    month = cost(r, 30)["inr"]
    if len(runs) >= 2:
        mid = round(statistics.median(runs), 2)
        return {"job": job, "label": BIG_JOBS[job], "inr": mid, "from_runs": len(runs), "measured": True,
                "month_so_far": month, "month_after": round(month + mid, 2),
                "says": f"{BIG_JOBS[job]} cost about Rs {mid:.2f} over the last {len(runs)} runs. "
                        f"This month so far Rs {month:.2f}; after this about Rs {month + mid:.2f}."}
    return {"job": job, "label": BIG_JOBS[job], "inr": None, "from_runs": len(runs), "measured": False,
            "month_so_far": month, "month_after": None,
            "says": f"The cost of {BIG_JOBS[job]} has not been measured yet (" + (f"it ran only {len(runs)} time(s)"
                    if runs else "it has never run") + f"). This month so far Rs {month:.2f}."}
