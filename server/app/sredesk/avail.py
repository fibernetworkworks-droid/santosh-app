"""Availability of a system from its parts, worked out in code.

A tree of parts: a leaf {name, availability} (99.95 or 0.9995), a group {name, all: [...]} (every part needed - in series) or
{name, any: [...], need: k} (k of the parts needed - redundancy; need defaults to 1). The result: the system's availability, its
downtime a month, the part that costs the most, and what one more replica of each part would give. Redundant parts are treated as
failing independently - real replicas share power, network, deploys and bugs, so the true number is lower; said every time."""
from __future__ import annotations

from math import comb
from typing import Any

MAX_NODES = 400


class AvailError(ValueError):
    pass


def _a(v: Any, name: str) -> float:
    try:
        x = float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        raise AvailError(f"{name}: availability must be a number like 99.95.")
    a = x / 100 if x > 1 else x
    if not 0 <= a <= 1:
        raise AvailError(f"{name}: availability between 0 and 100 %.")
    return a


def _k_of_n(ps: list[float], k: int) -> float:
    """Probability at least k of the parts are up (independent, maybe different), by dynamic programming."""
    dp = [1.0] + [0.0] * len(ps)
    for p in ps:
        for j in range(len(ps), 0, -1):
            dp[j] = dp[j] * (1 - p) + dp[j - 1] * p
        dp[0] *= (1 - p)
    return sum(dp[k:])


def _eval(node: Any, path: str, count: list[int], leaves: list[dict[str, Any]]) -> float:
    count[0] += 1
    if count[0] > MAX_NODES:
        raise AvailError(f"At most {MAX_NODES} parts.")
    if not isinstance(node, dict):
        raise AvailError(f"{path}: each part is an object with a name.")
    name = str(node.get("name") or path)[:80]
    if "all" in node or "any" in node:
        kids = node.get("all") if "all" in node else node.get("any")
        if not isinstance(kids, list) or not kids:
            raise AvailError(f"{name}: list its parts.")
        vals = [_eval(c, f"{name}/{i + 1}", count, leaves) for i, c in enumerate(kids)]
        if "all" in node:
            out = 1.0
            for v in vals:
                out *= v
            return out
        need = int(node.get("need") or 1)
        if not 1 <= need <= len(vals):
            raise AvailError(f"{name}: need must be between 1 and {len(vals)}.")
        return _k_of_n(vals, need)
    if "availability" not in node:
        raise AvailError(f"{name}: give its availability, or its parts (all / any).")
    a = _a(node["availability"], name)
    leaves.append({"name": name, "availability": a, "node": node})
    return a


def month_min(a: float) -> float:
    return 30 * 1440 * (1 - a)


def analyse(tree: Any, target: Any = None) -> dict[str, Any]:
    leaves: list[dict[str, Any]] = []
    total = _eval(tree, "system", [0], leaves)
    out: dict[str, Any] = {"ok": True, "availability": total, "downtime_month_min": round(month_min(total), 2), "parts": len(leaves), "issues": []}
    # what each part costs: the system if that part were perfect
    gains = []
    for lf in leaves:
        keep = lf["node"]["availability"]
        lf["node"]["availability"] = 1.0
        better = _eval(tree, "system", [0], [])
        # one more replica of this part: a 1-of-2 of itself
        lf["node"]["availability"] = 1 - (1 - lf["availability"]) ** 2
        twin = _eval(tree, "system", [0], [])
        lf["node"]["availability"] = keep
        gains.append({"name": lf["name"], "availability": lf["availability"], "if_perfect": better,
                      "saves_min_month": round(month_min(total) - month_min(better), 2),
                      "with_a_replica": twin, "replica_saves_min_month": round(month_min(total) - month_min(twin), 2)})
    gains.sort(key=lambda g: -g["saves_min_month"])
    out["by_part"] = gains[:60]
    if gains:
        w = gains[0]
        out["weakest"] = w["name"]
        out["issues"].append({"sev": "info", "text": f"{w['name']} costs the most: {w['saves_min_month']:.1f} min a month would go if it never failed."})
    if target not in (None, ""):
        t = _a(target, "Target")
        out["target"] = t
        if total < t:
            out["issues"].insert(0, {"sev": "bad", "text": f"{total:.4%} is below the {t:.4%} target: {month_min(total) - month_min(t):.1f} "
                                                           "min a month too much downtime."})
    out["issues"].append({"sev": "info", "text": "Redundant parts are counted as failing on their own; shared power, network, deploys and "
                                                 "bugs make the real number lower."})
    out["verdict"] = (f"The system is up {total:.4%} of the time: about {month_min(total):.1f} min down a month. "
                      + (f"The part that costs the most is {out['weakest']}." if gains else ""))
    return out


def replicas_needed(part: Any, target: Any, need: int = 1, most: int = 9) -> dict[str, Any]:
    a = _a(part, "Part")
    t = _a(target, "Target")
    rows = []
    for n in range(max(1, need), most + 1):
        v = sum(comb(n, j) * a ** j * (1 - a) ** (n - j) for j in range(need, n + 1))
        rows.append({"replicas": n, "availability": v, "downtime_month_min": round(month_min(v), 3)})
        if v >= t:
            break
    hit = next((r for r in rows if r["availability"] >= t), None)
    return {"ok": True, "part": a, "target": t, "need": need, "rows": rows, "replicas": hit["replicas"] if hit else None,
            "verdict": (f"{hit['replicas']} replicas (any {need} up) reach {t:.4%}." if hit else
                        f"Not reached with {most} replicas: make the part itself more reliable.")}
