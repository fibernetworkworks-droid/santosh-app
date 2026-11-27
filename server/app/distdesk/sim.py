"""A small fault-injection simulator (the Jepsen idea, in code, on the server): clients read and write one replicated register while
replicas are partitioned away, crash or have skewed clocks; every operation is recorded as invoke / ok / fail / info exactly as a
client would see it, and the history is then checked for linearizability. Protocols: one leader; quorum reads and writes without and
with read repair (ABD); last-writer-wins on client clocks; asynchronous primary-backup with failover. A fixed seed gives the same
history every time, so a fix can be shown to remove an anomaly. It is a model of these protocols, not her system."""
from __future__ import annotations

import random
from typing import Any

from . import linear

PROTOCOLS = {
    "leader": "One leader: every operation goes to replica 0 (a baseline - linearizable while the leader is reachable).",
    "quorum": "Quorum reads and writes (R + W > N), reads return the newest version they saw - no read repair.",
    "quorum_repair": "Quorum reads and writes, and a read writes the value it returns back to a quorum before answering (ABD).",
    "lww": "Last writer wins: each write is stamped with the client's own clock; reads return the newest stamp they saw.",
    "async": "Asynchronous primary-backup: the primary answers at once and copies to the others later; on a crash a backup takes over.",
}
LIMITS = {"replicas": (1, 7), "clients": (1, 8), "ops": (1, 60), "duration": (1, 20)}


class SimError(ValueError):
    pass


def _cfg(d: dict[str, Any]) -> dict[str, Any]:
    c = {"protocol": str(d.get("protocol") or "quorum"), "replicas": d.get("replicas", 3), "r": d.get("r"), "w": d.get("w"),
         "clients": d.get("clients", 3), "ops": d.get("ops", 20), "duration": d.get("duration", 6), "seed": d.get("seed", 1),
         "write_share": d.get("write_share", 0.4), "lag": d.get("lag", 6), "skew": d.get("skew") or [], "partitions": d.get("partitions") or [],
         "crashes": d.get("crashes") or []}
    if c["protocol"] not in PROTOCOLS:
        raise SimError("Protocol: " + " | ".join(PROTOCOLS))
    for k, (lo, hi) in LIMITS.items():
        try:
            c[k] = int(c[k])
        except (TypeError, ValueError):
            raise SimError(f"{k}: a whole number from {lo} to {hi}.")
        if not lo <= c[k] <= hi:
            raise SimError(f"{k}: a whole number from {lo} to {hi}.")
    n = c["replicas"]
    maj = n // 2 + 1
    c["r"] = int(c["r"]) if c["r"] not in (None, "") else maj
    c["w"] = int(c["w"]) if c["w"] not in (None, "") else maj
    if not (1 <= c["r"] <= n and 1 <= c["w"] <= n):
        raise SimError("R and W must be between 1 and the number of replicas.")
    c["seed"] = int(c["seed"]) % 1_000_000
    c["write_share"] = max(0.05, min(0.95, float(c["write_share"])))
    c["lag"] = max(0, min(50, int(c["lag"])))
    c["skew"] = [max(-50, min(50, int(x))) for x in list(c["skew"])[:8]]
    parts = []
    for p in list(c["partitions"])[:6]:
        cut = [int(x) for x in (p.get("cut") or []) if 0 <= int(x) < n]
        if cut:
            parts.append({"from": max(0, int(p.get("from", 0))), "to": max(0, int(p.get("to", 0))), "cut": cut})
    c["partitions"] = parts
    c["crashes"] = [{"replica": int(x.get("replica", 0)), "at": max(0, int(x.get("at", 0)))} for x in list(c["crashes"])[:4]
                    if 0 <= int(x.get("replica", 0)) < n]
    return c


def run(d: dict[str, Any]) -> dict[str, Any]:
    c = _cfg(d)
    rnd = random.Random(c["seed"])
    n, proto = c["replicas"], c["protocol"]
    reps = [{"ver": (0, -1), "val": None} for _ in range(n)]
    crash_at = {x["replica"]: x["at"] for x in c["crashes"]}

    def up(i: int, t: int) -> bool:
        if i in crash_at and t >= crash_at[i]:
            return False
        return not any(p["from"] <= t < p["to"] and i in p["cut"] for p in c["partitions"])

    # timing: each client runs its operations one after another
    plan = []
    nxt = 1
    for cl in range(c["clients"]):
        t = rnd.randint(0, 3)
        for _ in range(c["ops"]):
            f = "write" if rnd.random() < c["write_share"] else "read"
            dur = (rnd.randint(max(1, c["duration"] // 2), c["duration"]) if f == "write" else
                   rnd.randint(1, max(2, c["duration"] // 3)))
            plan.append({"client": cl, "f": f, "start": t, "end": t + dur, "value": None})
            t += dur + rnd.randint(1, 3)
    plan.sort(key=lambda o: (o["start"], o["client"]))
    for o in plan:
        if o["f"] == "write":
            o["value"] = nxt
            nxt += 1
    horizon = max(o["end"] for o in plan) + c["lag"] + 2
    actions: dict[int, list] = {}

    def at(t, prio, fn):
        actions.setdefault(t, []).append((prio, len(actions.get(t, [])), fn))

    primary = {"i": 0}
    leader_like = proto in ("leader", "async")
    for o in plan:
        o["applied"], o["seen"], o["status"] = [], [], None
        s, e = o["start"], o["end"]
        if leader_like:
            when = rnd.randint(s, e)

            def act(t, o=o):
                p = primary["i"]
                if not up(p, t):
                    o["status"] = "info" if o["f"] == "write" else "fail"
                    return
                if o["f"] == "write":
                    ver = (reps[p]["ver"][0] + 1, o["client"])
                    reps[p].update(ver=ver, val=o["value"])
                    o["ver"] = ver
                    o["applied"].append(p)
                    if proto == "async":
                        for j in range(n):
                            if j != p:
                                def rep(t2, j=j, ver=ver, v=o["value"]):
                                    if up(j, t2) and reps[j]["ver"] < ver:
                                        reps[j].update(ver=ver, val=v)
                                at(t + c["lag"] + rnd.randint(0, 2), 0, rep)
                    o["status"] = "ok"
                else:
                    o["result"] = reps[p]["val"]
                    o["status"] = "ok"
            at(when, 1, act)
            continue
        # quorum / lww: a write first learns versions (or reads the clock), then sends to every replica
        if o["f"] == "write":
            def phase1(t, o=o):
                if proto == "lww":
                    o["ver"] = (t + (c["skew"][o["client"]] if o["client"] < len(c["skew"]) else 0), o["client"])
                    return
                vs = [reps[i]["ver"] for i in range(n) if up(i, t)]
                o["ver"] = ((max(vs)[0] if vs else 0) + 1, o["client"]) if len(vs) >= c["r"] else None
            at(s, 0, phase1)
            for i in range(n):
                def apply(t, o=o, i=i):
                    if o.get("ver") is None or not up(i, t):
                        return
                    if reps[i]["ver"] < o["ver"]:
                        reps[i].update(ver=o["ver"], val=o["value"])
                    o["applied"].append(i)
                at(rnd.randint(s + 1, max(s + 1, e - 1)), 1, apply)

            def done(t, o=o):
                if o.get("ver") is None:
                    o["status"] = "fail"
                else:
                    o["status"] = "ok" if len(o["applied"]) >= c["w"] else "info"
            at(e, 3, done)
        else:
            for i in range(n):
                def look(t, o=o, i=i):
                    if up(i, t):
                        o["seen"].append((reps[i]["ver"], reps[i]["val"], i))
                at(rnd.randint(s, max(s, e - 1)), 2, look)

            def done(t, o=o):
                if len(o["seen"]) < c["r"]:
                    o["status"] = "fail"
                    return
                first = o["seen"][:c["r"]]
                ver, val, _ = max(first, key=lambda x: x[0])
                if proto == "quorum_repair":
                    wrote = 0
                    for i in range(n):
                        if up(i, t):
                            if reps[i]["ver"] < ver:
                                reps[i].update(ver=ver, val=val)
                            wrote += 1
                    if wrote < c["w"]:
                        o["status"] = "fail"
                        return
                o["result"], o["status"] = val, "ok"
            at(e, 2, done)
    lost_at: list = []
    failover: list = []
    for t in range(horizon + 1):
        if proto == "async" and primary["i"] in crash_at and t >= crash_at[primary["i"]]:
            alive = [i for i in range(n) if up(i, t)]
            if alive:
                old = primary["i"]
                primary["i"] = max(alive, key=lambda i: reps[i]["ver"])
                if old != primary["i"]:
                    have = reps[primary["i"]]["ver"]
                    lost_at.extend(o["value"] for o in plan if o["f"] == "write" and o.get("status") == "ok" and o.get("ver") and o["ver"] > have)
                    failover.append({"at": t, "from": old, "to": primary["i"]})
        for _, _, fn in sorted(actions.get(t, []), key=lambda x: (x[0], x[1])):
            fn(t)
    # the history, as clients saw it
    evs = []
    for o in plan:
        st = o["status"] or ("info" if o["f"] == "write" else "fail")
        evs.append((o["start"], 0, f"{o['client']} invoke {o['f']}" + (f" {o['value']}" if o["f"] == "write" else "")))
        val = o["value"] if o["f"] == "write" else (o.get("result") if st == "ok" else "")
        evs.append((o["end"], 1, f"{o['client']} {st} {o['f']}" + (f" {'nil' if val is None else val}" if (o["f"] == "write" or st == "ok") else "")))
    evs.sort(key=lambda x: (x[0], x[1]))
    text = "\n".join(e[2] for e in evs)
    chk = linear.check(text)
    lost = sorted(set(lost_at))[:30]
    counts = {k: sum(1 for o in plan if (o["status"] or "") == k) for k in ("ok", "fail", "info")}
    return {"ok": True, "config": c, "about": PROTOCOLS[proto], "history": text, "check": chk, "counts": counts, "ticks": horizon,
            "lost_writes": lost, "failover": failover,
            "verdict": (f"{len(plan)} operations ({counts['ok']} ok, {counts['fail']} failed, {counts['info']} unknown): " + chk["verdict"] +
                        (f" {len(lost)} acknowledged write(s) were lost in the failover." if lost else ""))}


PRESETS = {
    "leader": {"protocol": "leader", "replicas": 3, "clients": 3, "ops": 20, "seed": 1},
    "quorum": {"protocol": "quorum", "replicas": 3, "clients": 4, "ops": 20, "seed": 3, "duration": 12, "write_share": 0.3},
    "quorum_repair": {"protocol": "quorum_repair", "replicas": 3, "clients": 4, "ops": 20, "seed": 3, "duration": 12, "write_share": 0.3},
    "quorum_partition": {"protocol": "quorum_repair", "replicas": 3, "clients": 3, "ops": 25, "seed": 5,
                         "partitions": [{"from": 40, "to": 80, "cut": [0, 1]}]},
    "lww_skew": {"protocol": "lww", "replicas": 3, "clients": 3, "ops": 20, "seed": 2, "skew": [0, 0, -12]},
    "async_failover": {"protocol": "async", "replicas": 3, "clients": 3, "ops": 25, "seed": 4, "lag": 8, "crashes": [{"replica": 0, "at": 60}]},
}
