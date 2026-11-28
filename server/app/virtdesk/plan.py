"""Host capacity for VMs: how much each host can hold at her overcommit limits, where every VM goes (her placement checked, or one
worked out), whether the cluster survives losing any one (or two) hosts, and which VMs span NUMA nodes. Pure arithmetic on the
numbers she gives; it does not see the hosts."""
from __future__ import annotations

import itertools
import re
from typing import Any


class PlanError(ValueError):
    pass


def _num(v: str, what: str) -> float:
    try:
        x = float(str(v).strip().lower().replace("gib", "").replace("gb", "").replace("g", "") or "x")
    except ValueError:
        raise PlanError(f"{what}: '{v}' is not a number.")
    if x < 0:
        raise PlanError(f"{what}: not below 0.")
    return x


def read(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hosts: list[dict[str, Any]] = []
    vms: list[dict[str, Any]] = []
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        ln = raw.split("#", 1)[0].strip()
        if not ln:
            continue
        p = [x for x in re.split(r"\s*[,;\t]\s*|\s+", ln) if x != ""]
        k = p[0].lower()
        if k in ("type", "kind"):
            continue
        if k not in ("host", "vm"):
            raise PlanError(f"Line {n}: start with host or vm (host, name, cores, RAM GiB [, NUMA nodes] / vm, name, vCPUs, RAM GiB [, host]).")
        if len(p) < 4:
            raise PlanError(f"Line {n}: give the name, the CPUs and the RAM in GiB.")
        if k == "host":
            numa = int(_num(p[4], f"Line {n} NUMA nodes")) if len(p) > 4 else 1
            h = {"name": p[1], "cores": _num(p[2], f"Line {n} cores"), "ram": _num(p[3], f"Line {n} RAM"), "numa": max(1, numa)}
            if h["cores"] <= 0 or h["ram"] <= 0:
                raise PlanError(f"Line {n}: a host needs cores and RAM.")
            hosts.append(h)
        else:
            vms.append({"name": p[1], "vcpu": _num(p[2], f"Line {n} vCPUs"), "ram": _num(p[3], f"Line {n} RAM"), "host": p[4] if len(p) > 4 else ""})
    if not hosts:
        raise PlanError("Give at least one host: host, name, physical cores, RAM GiB.")
    if len({h["name"] for h in hosts}) != len(hosts):
        raise PlanError("Two hosts have the same name.")
    if len(hosts) > 200 or len(vms) > 5000:
        raise PlanError("Up to 200 hosts and 5,000 VMs.")
    return hosts, vms


def _cap(h: dict[str, Any], ratio: float, ram_ratio: float, res_gb: float, res_cores: float) -> tuple[float, float]:
    return max(0.0, (h["cores"] - res_cores) * ratio), max(0.0, (h["ram"] - res_gb) * ram_ratio)


def _place(vms: list[dict[str, Any]], free: dict[str, list[float]]) -> tuple[dict[str, str], list[str]]:
    """Biggest first onto the host with the most RAM left (spreads load, leaves room to take a failed host's VMs)."""
    out: dict[str, str] = {}
    left: list[str] = []
    for v in sorted(vms, key=lambda v: (-v["ram"], -v["vcpu"], v["name"])):
        fits = [h for h, (c, r) in free.items() if c + 1e-9 >= v["vcpu"] and r + 1e-9 >= v["ram"]]
        if not fits:
            left.append(v["name"])
            continue
        h = max(fits, key=lambda h: (free[h][1], free[h][0]))
        free[h][0] -= v["vcpu"]
        free[h][1] -= v["ram"]
        out[v["name"]] = h
    return out, left


def plan(text: str, ratio: float = 4.0, ram_ratio: float = 1.0, reserve_gb: float = 4.0, reserve_cores: float = 1.0, failures: int = 1) -> dict[str, Any]:
    hosts, vms = read(text)
    ratio, ram_ratio = float(ratio), float(ram_ratio)
    if not 0.1 <= ratio <= 32:
        raise PlanError("vCPUs per physical core: 0.1 to 32.")
    if not 0.5 <= ram_ratio <= 4:
        raise PlanError("RAM overcommit: 0.5 to 4 (1 = none).")
    failures = max(0, min(int(failures), 2, len(hosts) - 1))
    names = {h["name"] for h in hosts}
    cap = {h["name"]: _cap(h, ratio, ram_ratio, float(reserve_gb), float(reserve_cores)) for h in hosts}
    issues: list[dict[str, Any]] = []
    if len({v["name"] for v in vms}) != len(vms):
        issues.append({"sev": "warn", "text": "Two VMs have the same name: their rows are told apart by order only."})
    given = [v for v in vms if v["host"]]
    for v in given:
        if v["host"] not in names:
            raise PlanError(f"VM {v['name']} is on host {v['host']}, which is not in the list.")
    mode = "yours" if vms and len(given) == len(vms) else "worked out"
    if mode == "yours":
        where = {v["name"]: v["host"] for v in vms}
        left: list[str] = []
    else:
        free = {h: [c, r] for h, (c, r) in cap.items()}
        for v in given:
            free[v["host"]][0] -= v["vcpu"]
            free[v["host"]][1] -= v["ram"]
        where, left = _place([v for v in vms if not v["host"]], free)
        where.update({v["name"]: v["host"] for v in given})
    rows = []
    for h in hosts:
        on = [v for v in vms if where.get(v["name"]) == h["name"]]
        uv, ur = sum(v["vcpu"] for v in on), sum(v["ram"] for v in on)
        cv, cr = cap[h["name"]]
        rows.append({"name": h["name"], "cores": h["cores"], "ram": h["ram"], "numa": h["numa"], "vms": [v["name"] for v in on],
                     "vcpu": uv, "vcpu_cap": cv, "ram_used": ur, "ram_cap": cr, "ratio": round(uv / h["cores"], 2) if h["cores"] else None,
                     "cpu_share": round(uv / cv, 3) if cv else None, "ram_share": round(ur / cr, 3) if cr else None,
                     "over": uv > cv + 1e-9 or ur > cr + 1e-9})
        if uv > cv + 1e-9:
            issues.append({"sev": "bad" if mode == "yours" else "warn", "text": f"{h['name']}: {uv:g} vCPUs on {h['cores']:g} cores = {uv / h['cores']:.1f} per core, above your {ratio:g}."})
        if ur > cr + 1e-9:
            issues.append({"sev": "bad", "text": f"{h['name']}: {ur:g} GiB of VM memory on {cr:g} GiB it can give: the host swaps or kills VMs."})
    if left:
        issues.append({"sev": "bad", "text": f"{len(left)} VM(s) fit on no host at these limits: " + ", ".join(left[:12]) + "."})
    big_c = max(cap[h][0] for h in cap)
    big_r = max(cap[h][1] for h in cap)
    numa = []
    for v in vms:
        if v["vcpu"] > big_c or v["ram"] > big_r:
            issues.append({"sev": "bad", "text": f"VM {v['name']} ({v['vcpu']:g} vCPUs, {v['ram']:g} GiB) is bigger than any host can give."})
        h = next((x for x in hosts if x["name"] == where.get(v["name"])), None)
        if h and h["numa"] > 1:
            nc, nr = h["cores"] / h["numa"], h["ram"] / h["numa"]
            if v["vcpu"] > nc or v["ram"] > nr:
                numa.append(v["name"])
                issues.append({"sev": "info", "text": f"VM {v['name']} is larger than one NUMA node of {h['name']} ({nc:g} cores, {nr:g} GiB): "
                               "it spans nodes - give it a NUMA topology that matches, or pin it."})
    # failover
    fail = []
    if failures:
        for down in itertools.islice(itertools.combinations([h["name"] for h in hosts], failures), 400):
            free = {}
            for r in rows:
                if r["name"] in down:
                    continue
                free[r["name"]] = [r["vcpu_cap"] - r["vcpu"], r["ram_cap"] - r["ram_used"]]
            moved = [v for v in vms if where.get(v["name"]) in down]
            _, stranded = _place(moved, free)
            need = sum(v["ram"] for v in moved if v["name"] in stranded)
            fail.append({"down": list(down), "moved": len(moved), "stranded": stranded, "ram_short": round(need, 2)})
        bad_f = [f for f in fail if f["stranded"]]
        if bad_f:
            w = max(bad_f, key=lambda f: len(f["stranded"]))
            issues.append({"sev": "bad", "text": f"Losing {' + '.join(w['down'])} leaves {len(w['stranded'])} VM(s) with nowhere to restart "
                           f"({w['ram_short']:g} GiB short); {len(bad_f)} of {len(fail)} failure case(s) strand VMs."})
    tc, tr = sum(h["cores"] for h in hosts), sum(h["ram"] for h in hosts)
    uv, ur = sum(v["vcpu"] for v in vms), sum(v["ram"] for v in vms)
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    survives = all(not f["stranded"] for f in fail) if failures else None
    counts = {s: sum(1 for i in issues if i["sev"] == s) for s in order}
    hs = f"{failures} host" + ("s" if failures > 1 else "")
    tail = "" if survives is None else f"; survives losing any {hs}" if survives else f"; does NOT survive losing {hs}"
    return {"mode": mode, "hosts": rows, "vms": len(vms), "unplaced": left, "where": where, "failures": failures, "fail": fail[:60],
            "survives": survives, "numa_span": numa, "ratio": ratio, "ram_ratio": ram_ratio, "reserve_gb": float(reserve_gb),
            "reserve_cores": float(reserve_cores), "totals": {"cores": tc, "ram": tr, "vcpu": uv, "vm_ram": ur,
                                                               "vcpu_per_core": round(uv / tc, 2) if tc else None, "ram_share": round(ur / tr, 3) if tr else None},
            "issues": issues, "counts": counts,
            "verdict": (f"{len(vms)} VMs on {len(hosts)} hosts ({'your placement' if mode == 'yours' else 'placement worked out'}), "
                        f"{uv / tc:.1f} vCPUs per core, {ur / tr:.0%} of the RAM" + tail + "."),
            "note": "Arithmetic on the numbers you gave: it does not see real use. A VM's memory counts in full; CPU is shared at your vCPU-per-core limit."}
