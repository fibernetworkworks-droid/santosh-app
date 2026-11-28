"""Does the workload fit the cluster: node pools (cores, memory, pods per node, count) less what the system keeps on each node and
the DaemonSets that run on every node, then every pod placed by its requests (largest first, on the node with the most room left),
pods that fit nowhere, how full each pool is, capacity stranded (CPU left where memory ran out, or the other way), the nodes
needed, and whether everything still fits after losing a node - or a whole zone if she gives zones.
Input lines: `node m5.xlarge cpu=4 mem=16Gi pods=58 x6 zone=a`, `daemonset cpu=100m mem=200Mi`, `pod api cpu=500m mem=1Gi x20`."""
from __future__ import annotations

import math
import re
from typing import Any

from .common import PfInputError, cores, cpu, finder, finish, gib, mem


class CapacityError(PfInputError):
    pass


def _kv(rest: str) -> dict[str, str]:
    return {k.lower(): v for k, v in re.findall(r"([A-Za-z_]+)\s*[=:]\s*([^\s,]+)", rest)}


def read(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pools, ds, pods = [], [], []
    for raw in str(text or "").splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        m = re.match(r"(?i)(node|nodes|pool|nodepool|daemonset|ds|pod|pods|deploy|deployment|statefulset|sts|job)\s+(.*)$", line)
        if not m:
            raise CapacityError(f"Could not read '{line[:60]}'. Start lines with node, daemonset or pod.")
        what, rest = m.group(1).lower(), m.group(2)
        kv = _kv(rest)
        cnt = re.search(r"(?:^|\s)[x×]\s*(\d+)\b|\bcount\s*=\s*(\d+)|\breplicas\s*=\s*(\d+)", rest)
        n = int(next(g for g in cnt.groups() if g)) if cnt else 1
        name = re.sub(r"\s.*", "", rest) if not re.match(r"[A-Za-z_]+\s*=", rest) else what
        try:
            c, mm = cpu(kv.get("cpu")), mem(kv.get("mem") or kv.get("memory"))
        except PfInputError as e:
            raise CapacityError(f"{line[:50]}: {e}")
        if what in ("node", "nodes", "pool", "nodepool"):
            if c is None or mm is None:
                raise CapacityError(f"'{line[:60]}': a node needs cpu= and mem=.")
            pools.append({"name": name, "cpu": c, "mem": mm, "pods": int(kv.get("pods") or kv.get("maxpods") or 110), "count": n, "zone": kv.get("zone", ""),
                          "alloc_cpu": cpu(kv["alloc_cpu"]) if "alloc_cpu" in kv else None, "alloc_mem": mem(kv["alloc_mem"]) if "alloc_mem" in kv else None})
        elif what in ("daemonset", "ds"):
            ds.append({"name": name, "cpu": c or 0.0, "mem": mm or 0.0})
        else:
            if c is None and mm is None:
                raise CapacityError(f"'{line[:60]}': a pod needs cpu= and / or mem= requests.")
            pods.append({"name": name, "cpu": c or 0.0, "mem": mm or 0.0, "count": n})
    if not pools:
        raise CapacityError("Give at least one node line: node m5.xlarge cpu=4 mem=16Gi x6.")
    names = [p["name"] for p in pools]
    for p in pools:   # the same node type in two zones (or two pools) gets its own name
        if names.count(p["name"]) > 1:
            p["name"] = f"{p['name']} ({'zone ' + p['zone'] if p['zone'] else 'pool ' + str(sum(1 for q in pools[:pools.index(p) + 1] if q['name'].startswith(p['name'])))})"
    if not pods:
        raise CapacityError("Give the pods: pod api cpu=500m mem=1Gi x20.")
    return pools, ds, pods


def reserved(c: float, m: float, rc: float | None, rm: float | None) -> tuple[float, float]:
    """What the system keeps on a node: her figures if given, else GKE's published tiered rule (CPU 6% of the first
    core, 1% of the next, 0.5% of the next two, 0.25% above; memory 25% of the first 4 GiB, 20% of the next 4, 10% of the next 8,
    6% of the next 112, 2% above, plus 100 MiB for eviction)."""
    if rc is None:
        rc = 0.06 * min(c, 1) + 0.01 * min(max(c - 1, 0), 1) + 0.005 * min(max(c - 2, 0), 2) + 0.0025 * max(c - 4, 0)
    if rm is None:
        rm = (0.25 * min(m, 4) + 0.2 * min(max(m - 4, 0), 4) + 0.1 * min(max(m - 8, 0), 8) + 0.06 * min(max(m - 16, 0), 112)
              + 0.02 * max(m - 128, 0) + 100 / 1024)
    return rc, rm


def _pack(nodes: list[dict[str, Any]], pods: list[tuple[str, float, float]]) -> tuple[list[str], list[dict[str, Any]]]:
    for nd in nodes:
        nd["used_cpu"], nd["used_mem"], nd["used_pods"] = nd["ds_cpu"], nd["ds_mem"], nd["ds_pods"]
    left = []
    for name, c, m in pods:
        best = None
        for nd in nodes:   # least allocated, the default scheduler's scoring: the node left with the most room spreads the pods
            fc, fm = nd["cap_cpu"] - nd["used_cpu"] - c, nd["cap_mem"] - nd["used_mem"] - m
            if fc >= -1e-9 and fm >= -1e-9 and nd["used_pods"] < nd["pods"]:
                score = (fc / nd["cap_cpu"] + fm / nd["cap_mem"]) / 2
                if best is None or score > best[0] + 1e-12:
                    best = (score, nd)
        if best is None:
            left.append(name)
        else:
            nd = best[1]
            nd["used_cpu"] += c
            nd["used_mem"] += m
            nd["used_pods"] += 1
    return left, nodes


def plan(text: str, reserve_cpu: float | None = None, reserve_mem: float | None = None) -> dict[str, Any]:
    pools, ds, pods = read(text)
    issues, add = finder()
    ds_c, ds_m = sum(d["cpu"] for d in ds), sum(d["mem"] for d in ds)

    def nodes_of(skip_pool: str | None = None, skip_zone: str | None = None, drop_one: str | None = None) -> list[dict[str, Any]]:
        out = []
        for p in pools:
            if skip_zone and p["zone"] == skip_zone:
                continue
            n = p["count"] - (1 if drop_one == p["name"] else 0)
            rc, rm = reserved(p["cpu"], p["mem"], reserve_cpu, reserve_mem)
            ac = p["alloc_cpu"] if p["alloc_cpu"] is not None else p["cpu"] - rc
            am = p["alloc_mem"] if p["alloc_mem"] is not None else p["mem"] - rm
            for i in range(max(0, n)):
                out.append({"pool": p["name"], "i": i, "cap_cpu": ac, "cap_mem": am, "pods": p["pods"], "ds_cpu": ds_c, "ds_mem": ds_m, "ds_pods": len(ds)})
        return out
    flat = sorted(((p["name"], p["cpu"], p["mem"]) for p in pods for _ in range(p["count"])), key=lambda x: -max(x[1], x[2] / 4))
    if len(flat) > 20000:
        raise CapacityError("Up to 20,000 pods.")
    left, nodes = _pack(nodes_of(), flat)
    cap_c = sum(n["cap_cpu"] for n in nodes)
    cap_m = sum(n["cap_mem"] for n in nodes)
    req_c = sum(x[1] for x in flat) + ds_c * len(nodes)
    req_m = sum(x[2] for x in flat) + ds_m * len(nodes)
    per_pool = []
    for p in pools:
        ns = [n for n in nodes if n["pool"] == p["name"]]
        if not ns:
            continue
        uc, um = sum(n["used_cpu"] for n in ns), sum(n["used_mem"] for n in ns)
        cc, cm = sum(n["cap_cpu"] for n in ns), sum(n["cap_mem"] for n in ns)
        per_pool.append({"pool": p["name"], "nodes": len(ns), "cpu": p["cpu"], "mem": p["mem"], "alloc_cpu": ns[0]["cap_cpu"], "alloc_mem": ns[0]["cap_mem"],
                         "used_cpu": uc, "used_mem": um, "cap_cpu": cc, "cap_mem": cm, "zone": p["zone"],
                         "empty": sum(1 for n in ns if n["used_cpu"] - n["ds_cpu"] < 1e-9 and n["used_mem"] - n["ds_mem"] < 1e-9)})
    node_rows = [{"pool": n["pool"], "i": n["i"], "cpu": n["used_cpu"] / n["cap_cpu"] if n["cap_cpu"] else 0, "mem": n["used_mem"] / n["cap_mem"] if n["cap_mem"] else 0,
                  "pods": n["used_pods"]} for n in nodes][:400]
    stranded_c = sum(n["cap_cpu"] - n["used_cpu"] for n in nodes if n["cap_mem"] - n["used_mem"] < 0.1 * n["cap_mem"])
    stranded_m = sum(n["cap_mem"] - n["used_mem"] for n in nodes if n["cap_cpu"] - n["used_cpu"] < 0.1 * n["cap_cpu"])
    # how many of the biggest pool's nodes the workload needs (lower bound by totals, then packed)
    big = max(pools, key=lambda p: p["cpu"] * p["mem"])
    rc0, rm0 = reserved(big["cpu"], big["mem"], reserve_cpu, reserve_mem)
    per_c, per_m = (big["alloc_cpu"] or big["cpu"] - rc0) - ds_c, (big["alloc_mem"] or big["mem"] - rm0) - ds_m
    need_lb = max(math.ceil(sum(x[1] for x in flat) / per_c) if per_c > 0 else 0, math.ceil(sum(x[2] for x in flat) / per_m) if per_m > 0 else 0,
                  math.ceil(len(flat) / max(1, big["pods"] - len(ds))))
    loss = []
    for p in pools:
        if p["count"] >= 1:
            l2, _ = _pack(nodes_of(drop_one=p["name"]), flat)
            loss.append({"what": f"one {p['name']} node", "left": len(l2)})
    zones = sorted({p["zone"] for p in pools if p["zone"]})
    if len(zones) >= 2:
        for z in zones:
            l2, _ = _pack(nodes_of(skip_zone=z), flat)
            loss.append({"what": f"zone {z}", "left": len(l2)})
    res: dict[str, Any] = {"pools": per_pool, "nodes": node_rows, "node_count": len(nodes), "pods": len(flat), "unplaced": len(left),
                           "unplaced_names": sorted({x for x in left})[:20], "cap_cpu": cap_c, "cap_mem": cap_m, "req_cpu": req_c, "req_mem": req_m,
                           "util_cpu": req_c / cap_c if cap_c else 0, "util_mem": req_m / cap_m if cap_m else 0, "daemonsets": {"count": len(ds), "cpu": ds_c, "mem": ds_m},
                           "stranded_cpu": stranded_c, "stranded_mem": stranded_m, "need_nodes": need_lb, "need_pool": big["name"], "loss": loss}
    if left:
        biggest = max((x for x in flat if x[0] in set(left)), key=lambda x: max(x[1], x[2] / 4))
        fits_any = any(biggest[1] <= n["cap_cpu"] - n["ds_cpu"] + 1e-9 and biggest[2] <= n["cap_mem"] - n["ds_mem"] + 1e-9 for n in nodes)
        add("bad", "Does not fit", f"{len(left)} pod(s) fit on no node: {', '.join(sorted(set(left))[:6])}" +
            ("" if fits_any else f" - {biggest[0]} ({cores(biggest[1])} CPU, {gib(biggest[2])}) is bigger than any node can hold after the system's share") + ".",
            "Add nodes (or a larger node type), or lower their requests.")
    for p in per_pool:
        u = max(p["used_cpu"] / p["cap_cpu"] if p["cap_cpu"] else 0, p["used_mem"] / p["cap_mem"] if p["cap_mem"] else 0)
        p["util"] = u
        if u > 0.85 and not left:
            add("warn", "Full", f"Pool {p['pool']} is {u * 100:.0f}% full by requests - a rollout (old and new pods together) may not fit.", "Leave 15-25% room for rollouts and spikes.", p["pool"])
        if p["empty"]:
            add("info", "Empty nodes", f"{p['empty']} node(s) of {p['pool']} would carry only DaemonSets.", "The cluster autoscaler can remove them.", p["pool"])
    for l in loss:
        if l["left"] and not left:
            add("bad" if "zone" in l["what"] else "warn", "Losing capacity", f"After losing {l['what']}, {l['left']} pod(s) have nowhere to go.",
                "Keep one node's worth (one zone's worth) of room, or let the autoscaler add nodes fast enough.")
    if stranded_c > 0.15 * cap_c and stranded_c >= 1:
        add("info", "Stranded CPU", f"{cores(stranded_c)} cores sit on nodes whose memory is full.", "Pick a node type with more memory per core.")
    if stranded_m > 0.15 * cap_m and stranded_m >= 2:
        add("info", "Stranded memory", f"{gib(stranded_m)} sits on nodes whose CPU is full.", "Pick a node type with more cores per GiB.")
    ds_share = (ds_c * len(nodes)) / cap_c if cap_c else 0
    if ds_share > 0.15:
        add("warn", "DaemonSets", f"DaemonSets take {ds_share * 100:.0f}% of the cluster's CPU - many small nodes pay this on each.", "Fewer, larger nodes.")
    res["verdict"] = (f"{len(left)} of {len(flat)} pods do not fit on {len(nodes)} nodes" if left else
                      f"All {len(flat)} pods fit on {len(nodes)} nodes - {res['util_cpu'] * 100:.0f}% of CPU and {res['util_mem'] * 100:.0f}% of memory requested")
    res["note"] = ("Placed by requests, largest first, each on the node with the most room left (the default scheduler's least-allocated scoring); "
                   "the real scheduler also weighs affinity, topology spread, taints and volumes, and a bin-packing setup fills nodes instead. "
                   + ("System reserve from your settings." if reserve_cpu is not None else "System reserve from GKE's published tier rule - other clouds reserve somewhat differently; set yours in Settings."))
    return finish(res, issues)
