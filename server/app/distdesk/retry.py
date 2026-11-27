"""Retries and timeouts worked out in code: one retry policy (attempts, backoff, cap, jitter, per-try timeout, deadline) -> the
schedule of waits, the worst-case time, how much extra load it sends while the service below is failing, and the herd it makes
without jitter (simulated with a fixed seed); a call chain (service -> service -> ...) -> retries that multiply across layers and
timeouts that do not fit inside the caller's. Numbers only from her settings."""
from __future__ import annotations

import random
from typing import Any

JITTERS = ("none", "full", "equal", "decorrelated")


class RetryError(ValueError):
    pass


def _num(d: dict[str, Any], k: str, lo: float, hi: float, default: float, what: str) -> float:
    v = d.get(k, default)
    if v in (None, ""):
        v = default
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise RetryError(f"{what}: a number from {lo:g} to {hi:g}.")
    if not lo <= x <= hi:
        raise RetryError(f"{what}: a number from {lo:g} to {hi:g}.")
    return x


def policy_of(d: dict[str, Any]) -> dict[str, Any]:
    p = {"attempts": int(_num(d, "attempts", 1, 20, 3, "Attempts (including the first)")),
         "base_ms": _num(d, "base_ms", 0, 600_000, 100, "First backoff (ms)"),
         "multiplier": _num(d, "multiplier", 1, 10, 2, "Backoff multiplier"),
         "cap_ms": _num(d, "cap_ms", 0, 3_600_000, 10_000, "Longest backoff (ms)"),
         "timeout_ms": _num(d, "timeout_ms", 1, 3_600_000, 1_000, "Timeout per try (ms)"),
         "deadline_ms": _num(d, "deadline_ms", 0, 86_400_000, 0, "Overall deadline (ms, 0 = none)"),
         "jitter": str(d.get("jitter") or "full")}
    if p["jitter"] not in JITTERS:
        raise RetryError("Jitter: " + " | ".join(JITTERS))
    return p


def _waits(p: dict[str, Any], rnd: random.Random | None) -> list[float]:
    """The wait before try 2, 3, ... (AWS Architecture Blog 'Exponential Backoff and Jitter' formulas)."""
    out, prev = [], p["base_ms"]
    for i in range(p["attempts"] - 1):
        exp = min(p["cap_ms"], p["base_ms"] * p["multiplier"] ** i)
        j = p["jitter"]
        if rnd is None:                       # the worst case: the longest wait each formula allows
            w = exp if j in ("none", "full", "equal") else min(p["cap_ms"], max(p["base_ms"], prev * 3))
        elif j == "none":
            w = exp
        elif j == "full":
            w = rnd.uniform(0, exp)
        elif j == "equal":
            w = exp / 2 + rnd.uniform(0, exp / 2)
        else:
            w = min(p["cap_ms"], rnd.uniform(p["base_ms"], max(p["base_ms"], prev * 3)))
        prev = w
        out.append(w)
    return out


def analyse(d: dict[str, Any], fail_rate: float = 1.0, clients: int = 1000, seed: int = 11) -> dict[str, Any]:
    p = policy_of(d)
    fail_rate = max(0.0, min(1.0, float(fail_rate)))
    clients = max(1, min(int(clients), 100_000))
    worst_waits = _waits(p, None)
    worst = p["attempts"] * p["timeout_ms"] + sum(worst_waits)
    cut = None
    if p["deadline_ms"]:
        t, tries = 0.0, 0
        for i in range(p["attempts"]):
            if t + p["timeout_ms"] > p["deadline_ms"] and i > 0:
                break
            t += p["timeout_ms"]
            tries += 1
            if i < len(worst_waits):
                t += worst_waits[i]
        cut = tries if tries < p["attempts"] else None
    # expected tries per call when each try fails independently with fail_rate
    exp_tries = sum(fail_rate ** i for i in range(p["attempts"]))
    # the herd: when the service below fails for everyone at once, when do the retries land?
    rnd = random.Random(seed)
    bucket = 10.0
    span = worst + bucket
    nb = max(1, int(span // bucket) + 1)
    hist = [0] * nb
    for _ in range(clients):
        t = 0.0
        ws = _waits(p, rnd)
        for i in range(p["attempts"]):
            hist[min(nb - 1, int(t // bucket))] += 1
            t += p["timeout_ms"]
            if i < len(ws):
                t += ws[i]
    retry_peak = max(hist[1:]) if nb > 1 else 0
    issues = []
    if p["jitter"] == "none" and p["attempts"] > 1:
        issues.append({"sev": "bad", "say": f"No jitter: all {clients:,} clients retry at the same moment ({retry_peak:,} retries inside one 10 ms window)",
                       "fix": "Use full jitter (a random wait between 0 and the backoff) - it spreads the retries and the service can recover."})
    if p["attempts"] >= 5 and fail_rate >= 0.5:
        issues.append({"sev": "warn", "say": f"{p['attempts']} tries per call: while the service is down it gets {exp_tries:.1f}x its normal traffic",
                       "fix": "Cap retries with a retry budget (e.g. at most 10% extra requests) or a circuit breaker so a struggling service is not flooded."})
    if p["deadline_ms"] and cut:
        issues.append({"sev": "warn", "say": f"The deadline ({p['deadline_ms']:g} ms) only leaves room for {cut} of {p['attempts']} tries",
                       "fix": "Lower the attempts or the per-try timeout, or the later tries never run."})
    if not p["deadline_ms"] and worst > 30_000:
        issues.append({"sev": "warn", "say": f"Without a deadline one call can take {worst / 1000:.1f} s in the worst case",
                       "fix": "Give the whole call a deadline and pass it down, so nobody waits on an answer the caller has given up on."})
    if p["base_ms"] == 0 and p["attempts"] > 1:
        issues.append({"sev": "bad", "say": "Retries without any backoff hit the service again immediately",
                       "fix": "Start the backoff at 50-200 ms and grow it."})
    if p["cap_ms"] and p["cap_ms"] < p["base_ms"]:
        issues.append({"sev": "warn", "say": "The longest backoff is shorter than the first", "fix": "Raise the cap."})
    return {"ok": True, "policy": p, "waits_worst": [round(w, 1) for w in worst_waits], "worst_ms": round(worst, 1), "deadline_cut": cut,
            "expected_tries": round(exp_tries, 3), "load_factor": round(exp_tries, 2), "fail_rate": fail_rate, "clients": clients,
            "herd": hist[:min(nb, 3000)], "bucket_ms": bucket, "retry_peak": retry_peak, "issues": issues,
            "verdict": (f"Worst case {worst / 1000:.2f} s for one call; while the service below fails {fail_rate:.0%} of the time it gets "
                        f"{exp_tries:.2f}x its traffic." + (f" {len([i for i in issues if i['sev'] == 'bad'])} serious finding(s)." if any(i['sev'] == 'bad' for i in issues) else ""))}


def chain(hops: list[dict[str, Any]]) -> dict[str, Any]:
    """hops: [{name, attempts, timeout_ms, deadline_ms?}] from the edge inwards. Retries multiply; a caller's timeout must cover its
    callee's worst case or the caller gives up while work still runs below."""
    if not hops or len(hops) > 12:
        raise RetryError("Give 1 to 12 services, the outermost first.")
    rows, mult, issues = [], 1, []
    for i, h in enumerate(hops):
        name = str(h.get("name") or f"service {i + 1}")[:60]
        p = policy_of({**h, "deadline_ms": h.get("deadline_ms", 0)})
        mult *= p["attempts"]
        rows.append({"name": name, "attempts": p["attempts"], "timeout_ms": p["timeout_ms"], "worst_ms": 0.0, "calls_to_bottom": mult, "p": p})
    for i in range(len(rows) - 1, -1, -1):
        r = rows[i]
        own = r["p"]["attempts"] * r["p"]["timeout_ms"] + sum(_waits(r["p"], None))
        r["worst_ms"] = round(own, 1)
        if i + 1 < len(rows):
            below = rows[i + 1]
            one_try_below = below["p"]["attempts"] * below["p"]["timeout_ms"] + sum(_waits(below["p"], None))
            if r["p"]["timeout_ms"] < one_try_below and below["p"]["attempts"] > 1:
                issues.append({"sev": "bad", "say": f"{r['name']} waits {r['p']['timeout_ms']:g} ms per try, but {below['name']} may keep retrying for "
                                                    f"{one_try_below:g} ms - {r['name']} gives up and retries while {below['name']} is still working",
                               "fix": f"Retry in one layer only (usually the outermost), or give {r['name']} a timeout above {one_try_below:g} ms."})
    if mult >= 8 and len(rows) > 1:
        issues.append({"sev": "bad", "say": f"One request at the edge can become {mult} requests at {rows[-1]['name']} ({' x '.join(str(r['attempts']) for r in rows)})",
                       "fix": "Retry at one layer; let the others fail fast. Or share a retry budget across the chain."})
    for r in rows:
        r.pop("p")
    return {"ok": True, "hops": rows, "amplification": mult, "issues": issues,
            "verdict": f"{len(rows)} service(s): a failure at the bottom can turn one request into {mult}." + (" Timeouts do not nest." if any("gives up" in i["say"] for i in issues) else "")}
