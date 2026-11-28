"""Will every task and interrupt meet its deadline? Response-time analysis for fixed-priority preemptive scheduling (an RTOS such as
FreeRTOS or Zephyr, or a bare-metal interrupt set): utilisation and the Liu & Layland bound, the worst-case response time of each
task with blocking and release jitter, the slack left, how much every execution time can grow before something misses, the
deadline-monotonic order to compare against hers, and a timeline from the moment everything is released together."""
from __future__ import annotations

import math
import re
from typing import Any


class TimingError(ValueError):
    pass


UNIT = {"ns": 0.001, "us": 1.0, "µs": 1.0, "ms": 1000.0, "s": 1_000_000.0}
FREQ = {"hz": 1.0, "khz": 1e3, "mhz": 1e6}


def _t(v: str, what: str, default_unit: str = "ms") -> float:
    m = re.fullmatch(r"\s*([\d.]+)\s*(ns|us|µs|ms|s|hz|khz|mhz)?\s*", str(v).lower())
    if not m:
        raise TimingError(f"{what}: a time like 10ms, 250us or 1s (got {v}).")
    x = float(m.group(1))
    u = m.group(2) or default_unit
    if u in FREQ:
        if x <= 0:
            raise TimingError(f"{what}: above 0.")
        return 1_000_000.0 / (x * FREQ[u])
    return x * UNIT[u]


def fmt(us: float | None) -> str:
    if us is None:
        return "-"
    if us >= 1_000_000:
        return f"{us / 1e6:.3g} s"
    if us >= 1000:
        return f"{us / 1000:.4g} ms"
    return f"{us:.4g} µs"


def parse(text: str, default_unit: str = "ms") -> list[dict[str, Any]]:
    tasks = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        ln = raw.split("#")[0].strip().rstrip(",;")
        if not ln or re.match(r"^(name|task)\b.*\bperiod\b", ln, re.I):
            continue
        parts = re.split(r"[,\t;]\s*|\s+", ln)
        name = parts[0]
        if re.fullmatch(r"[\d.]+\w*", name):
            raise TimingError(f"Line {n}: start with the task's name, e.g. 'control period=1ms wcet=200us'.")
        kv, pos = {}, []
        kind = "task"
        for p in parts[1:]:
            if not p:
                continue
            m = re.fullmatch(r"(\w+)\s*[=:]\s*(.+)", p)
            if m:
                kv[m.group(1).lower()] = m.group(2)
            elif p.lower() in ("isr", "irq", "interrupt"):
                kind = "isr"
            elif p.lower() in ("task", "thread"):
                kind = "task"
            else:
                pos.append(p)
        al = {"t": "period", "p": "period", "period": "period", "every": "period", "rate": "period", "freq": "period",
              "c": "wcet", "wcet": "wcet", "cost": "wcet", "exec": "wcet", "runtime": "wcet", "time": "wcet",
              "d": "deadline", "deadline": "deadline", "prio": "prio", "priority": "prio", "pri": "prio",
              "b": "block", "block": "block", "blocking": "block", "j": "jitter", "jitter": "jitter"}
        f: dict[str, Any] = {}
        for k, v in kv.items():
            if k not in al:
                raise TimingError(f"Line {n}: {k}= is not known (period, wcet, deadline, prio, block, jitter).")
            f[al[k]] = v
        order = ["period", "wcet", "deadline", "prio"]
        for v in pos:
            slot = next((o for o in order if o not in f), None)
            if slot is None:
                raise TimingError(f"Line {n}: too many values.")
            f[slot] = v
        if "period" not in f or "wcet" not in f:
            raise TimingError(f"Line {n} ({name}): needs a period and an execution time, e.g. '{name} period=10ms wcet=2ms'.")
        T = _t(f["period"], f"{name} period", default_unit)
        C = _t(f["wcet"], f"{name} execution time", default_unit)
        D = _t(f["deadline"], f"{name} deadline", default_unit) if f.get("deadline") else T
        if T <= 0 or C <= 0:
            raise TimingError(f"{name}: period and execution time must be above 0.")
        if C > D:
            raise TimingError(f"{name}: its execution time ({fmt(C)}) is longer than its deadline ({fmt(D)}).")
        try:
            prio = float(f["prio"]) if f.get("prio") not in (None, "") else None
        except ValueError:
            raise TimingError(f"{name}: priority must be a number.")
        tasks.append({"name": name[:40], "kind": kind, "T": T, "C": C, "D": D, "prio": prio, "B": _t(f["block"], f"{name} blocking", default_unit) if f.get("block") else 0.0,
                      "J": _t(f["jitter"], f"{name} jitter", default_unit) if f.get("jitter") else 0.0, "line": n})
    if not tasks:
        raise TimingError("One task per line: name, period, execution time - e.g. 'control period=1ms wcet=200us deadline=800us prio=5'.")
    if len(tasks) > 80:
        raise TimingError("Up to 80 tasks.")
    if len({t["name"] for t in tasks}) != len(tasks):
        raise TimingError("Two tasks share a name.")
    return tasks


def _order(tasks: list[dict[str, Any]], higher_first: bool, mode: str) -> list[dict[str, Any]]:
    """Return tasks most urgent first. ISRs always above tasks. mode 'given' uses her priorities (missing ones by deadline)."""
    def key(t: dict[str, Any]) -> tuple:
        lvl = 0 if t["kind"] == "isr" else 1
        if mode == "given" and t["prio"] is not None:
            return (lvl, 0, -t["prio"] if higher_first else t["prio"], t["D"])
        return (lvl, 1 if mode == "given" else 0, t["D"], t["T"])
    return sorted(tasks, key=key)


def _rta(ordered: list[dict[str, Any]], scale: float = 1.0, cs: float = 0.0) -> list[float | None]:
    out: list[float | None] = []
    for i, t in enumerate(ordered):
        hp = [o for k, o in enumerate(ordered) if k < i and (o["kind"] == "isr" or t["kind"] == "task") and not _same(o, t)]
        eq = [o for k, o in enumerate(ordered) if k != i and _same(o, t)]
        C = t["C"] * scale + 2 * cs
        R = C + t["B"] + sum(o["C"] * scale + 2 * cs for o in hp + eq)
        ok = None
        for _ in range(10000):
            nxt = C + t["B"] + sum(math.ceil((R + o["J"]) / o["T"]) * (o["C"] * scale + 2 * cs) for o in hp) + sum(o["C"] * scale + 2 * cs for o in eq)
            if nxt + t["J"] > t["D"] * 50:
                ok = None
                break
            if abs(nxt - R) < 1e-9:
                ok = nxt + t["J"]
                break
            R = nxt
        out.append(ok)
    return out


def _same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a is not b and a["kind"] == b["kind"] and a.get("eff") is not None and a.get("eff") == b.get("eff") and a["kind"] == "task"


def _sim(ordered: list[dict[str, Any]], horizon: float) -> list[dict[str, Any]]:
    """Preemptive fixed-priority simulation from the critical instant: segments (task, start, end) and misses."""
    rel = {i: 0.0 for i in range(len(ordered))}
    left = {i: 0.0 for i in range(len(ordered))}
    dl = {i: 0.0 for i in range(len(ordered))}
    segs, misses = [], []
    now = 0.0
    run_i, run_s = None, 0.0
    guard = 0
    while now < horizon and guard < 20000:
        guard += 1
        for i, t in enumerate(ordered):
            if rel[i] <= now + 1e-9:
                if left[i] > 1e-9:
                    misses.append({"task": t["name"], "at": round(dl[i], 3)})
                left[i] = t["C"]
                dl[i] = rel[i] + t["D"]
                rel[i] += t["T"]
        ready = [i for i in range(len(ordered)) if left[i] > 1e-9]
        nxt_rel = min(rel.values())
        if not ready:
            if run_i is not None:
                segs.append({"task": ordered[run_i]["name"], "s": round(run_s, 3), "e": round(now, 3)})
                run_i = None
            now = nxt_rel
            continue
        i = min(ready)
        if run_i != i:
            if run_i is not None and now > run_s:
                segs.append({"task": ordered[run_i]["name"], "s": round(run_s, 3), "e": round(now, 3)})
            run_i, run_s = i, now
        step = min(left[i], nxt_rel - now, horizon - now)
        left[i] -= step
        now += step
        if left[i] <= 1e-9 and now > dl[i] + 1e-9:
            misses.append({"task": ordered[i]["name"], "at": round(dl[i], 3)})
        if left[i] <= 1e-9:
            segs.append({"task": ordered[i]["name"], "s": round(run_s, 3), "e": round(now, 3)})
            run_i = None
    if run_i is not None and now > run_s:
        segs.append({"task": ordered[run_i]["name"], "s": round(run_s, 3), "e": round(now, 3)})
    return [s for s in segs if s["e"] > s["s"]][:3000], misses[:50]


def analyse(text: str, prio_order: str = "higher", default_unit: str = "ms", switch_us: Any = 0, cpu_mhz: Any = "") -> dict[str, Any]:
    tasks = parse(text, default_unit)
    higher_first = prio_order != "lower"
    try:
        cs = float(switch_us or 0)
    except (TypeError, ValueError):
        raise TimingError("Context switch: a number of microseconds.")
    if cs < 0 or cs > 10000:
        raise TimingError("Context switch: 0 to 10000 µs.")
    given = any(t["prio"] is not None for t in tasks)
    ordered = _order(tasks, higher_first, "given" if given else "dm")
    for k, t in enumerate(ordered):
        t["eff"] = t["prio"] if given and t["prio"] is not None else None
    R = _rta(ordered, 1.0, cs)
    U = sum(t["C"] / t["T"] for t in tasks)
    n = len(tasks)
    ll = n * (2 ** (1 / n) - 1)
    rows = []
    for k, (t, r) in enumerate(zip(ordered, R)):
        rows.append({"name": t["name"], "kind": t["kind"], "rank": k + 1, "prio": t["prio"], "T": t["T"], "C": t["C"], "D": t["D"], "B": t["B"], "J": t["J"],
                     "U": round(100 * t["C"] / t["T"], 2), "R": round(r, 3) if r is not None else None, "slack": round(t["D"] - r, 3) if r is not None else None,
                     "ok": r is not None and r <= t["D"] + 1e-9})
    ok_all = all(r["ok"] for r in rows)
    # how far every execution time can grow
    lo, hi = 0.0, 1.0
    if ok_all:
        hi = 2.0
        while all(x is not None and x <= t["D"] + 1e-9 for x, t in zip(_rta(ordered, hi, cs), ordered)) and hi < 1000:
            lo, hi = hi, hi * 2
        for _ in range(40):
            mid = (lo + hi) / 2
            if all(x is not None and x <= t["D"] + 1e-9 for x, t in zip(_rta(ordered, mid, cs), ordered)):
                lo = mid
            else:
                hi = mid
    else:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if all(x is not None and x <= t["D"] + 1e-9 for x, t in zip(_rta(ordered, mid, cs), ordered)):
                lo = mid
            else:
                hi = mid
    growth = round(100 * (lo - 1), 1)
    dm = None
    if given:
        dmo = _order(tasks, higher_first, "dm")
        for t in dmo:
            t["eff"] = None
        Rd = _rta(dmo, 1.0, cs)
        dm_ok = all(r is not None and r <= t["D"] + 1e-9 for r, t in zip(Rd, dmo))
        same = [t["name"] for t in dmo] == [t["name"] for t in ordered]
        dm = {"order": [t["name"] for t in dmo], "ok": dm_ok, "same": same}
        for t in ordered:
            t["eff"] = t["prio"] if t["prio"] is not None else None
    try:
        hyper = 1
        scale = 1000
        for t in tasks:
            v = int(round(t["T"] * scale))
            hyper = hyper * v // math.gcd(hyper, v)
            if hyper > 10 ** 13:
                raise OverflowError
        hyper = hyper / scale
    except OverflowError:
        hyper = None
    horizon = min(hyper or 1e18, max(t["T"] for t in tasks) * 2, max(max(t["D"] for t in tasks), max(t["T"] for t in tasks)) * 4)
    horizon = max(horizon, max(t["T"] for t in tasks))
    segs, misses = _sim(ordered, horizon)
    issues: list[dict[str, Any]] = []
    if U > 1:
        issues.append({"sev": "bad", "text": f"The CPU is over-loaded: utilisation {100 * U:.1f}% - no priority order can make this fit."})
    for r in rows:
        if not r["ok"]:
            issues.append({"sev": "bad", "text": f"{r['name']} can miss its deadline: worst-case response " + (fmt(r["R"]) if r["R"] is not None else "unbounded") + f" against {fmt(r['D'])}."})
        elif r["slack"] is not None and r["slack"] < 0.1 * r["D"]:
            issues.append({"sev": "warn", "text": f"{r['name']} meets its deadline with only {fmt(r['slack'])} to spare ({100 * r['slack'] / r['D']:.1f}% of it)."})
    if ok_all and U > ll:
        issues.append({"sev": "info", "text": f"Utilisation {100 * U:.1f}% is above the Liu & Layland bound ({100 * ll:.1f}% for {n}) - that bound is only a quick test; the exact analysis above shows it fits."})
    if dm and not dm["same"]:
        if dm["ok"] and not ok_all:
            issues.append({"sev": "warn", "text": "With priorities by deadline (shortest deadline most urgent) everything would meet its deadline: " + " > ".join(dm["order"]) + "."})
        else:
            issues.append({"sev": "info", "text": "Your priority order differs from the deadline-monotonic one (" + " > ".join(dm["order"]) + ")."})
    eqs = {}
    for t in ordered:
        if t.get("eff") is not None and t["kind"] == "task":
            eqs.setdefault(t["eff"], []).append(t["name"])
    for p_, names in eqs.items():
        if len(names) > 1:
            issues.append({"sev": "info", "text": f"{', '.join(names)} share priority {p_:g}: time-sliced with each other, so each is counted as delaying the others by a whole run."})
    if any(t["B"] for t in tasks):
        issues.append({"sev": "info", "text": "Blocking (a lower task holding a mutex or interrupts off) is the value given - it is only bounded if every lock uses priority inheritance and critical sections are short."})
    if ok_all:
        issues.append({"sev": "info", "text": f"Every execution time can grow by {growth:g}% before the first deadline is missed."})
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in ("bad", "warn", "info")}
    verdict = (f"{'All ' + str(n) + ' meet their deadlines' if ok_all else str(sum(1 for r in rows if not r['ok'])) + ' of ' + str(n) + ' can miss a deadline'}"
               f" - utilisation {100 * U:.1f}%" + ((f", every execution time can grow {growth:g}%" if growth > 0 else ", with no room for longer execution times") if ok_all else "") + ".")
    return {"tasks": rows, "U": round(100 * U, 2), "bound": round(100 * ll, 2), "ok": ok_all, "growth": growth, "deadline_order": dm, "hyperperiod": hyper,
            "horizon": horizon, "timeline": segs, "misses": misses, "switch_us": cs, "given": given, "issues": issues, "counts": counts, "verdict": verdict,
            "note": ("Response-time analysis for fixed-priority preemptive scheduling with every task released together (the worst case). The numbers are only as good as the "
                     "execution times given - measure them as worst cases (a cycle counter, a logic analyser), not averages. Interrupts are always placed above tasks; "
                     "tick, scheduler and cache effects are in the context-switch time only.")}
