"""Kubernetes containers sized against what they really use: requests far above use (cores and memory paid for and never used),
use above the request (scheduled too tight, first to be evicted), memory near its limit (killed for running out), CPU near its
limit (slowed down), no requests or limits at all, and a recommended request from her headroom - with what the change saves at
her price per core and per GiB. Input: a CSV per container (namespace, workload, container, cpu / memory request and limit, the
p95 or peak use from her monitoring, replicas)."""
from __future__ import annotations

import re
from typing import Any

from ..mldesk.table import TableError, read
from .common import PfInputError, cores, cpu, finder, finish, gib, mem


class RightsizeError(TableError):
    pass


def _col(head: list[str], *pats: str) -> int | None:
    low = [re.sub(r"[^a-z0-9]", "", h.lower()) for h in head]
    for p in pats:
        for i, h in enumerate(low):
            if re.fullmatch(p, h):
                return i
    return None



def analyse(text: str, headroom: float = 0.2, cpu_price: float = 0.0, mem_price: float = 0.0) -> dict[str, Any]:
    head, rows = read(text, "The container list")
    ix = {
        "ns": _col(head, r"namespace|ns"),
        "wl": _col(head, r"workload|deployment|statefulset|app|name|pod|service"),
        "ct": _col(head, r"container|containername"),
        "cr": _col(head, r"cpurequests?|requestscpu|cpureq|reqcpu"),
        "cl": _col(head, r"cpulimits?|limitscpu|cpulim|limcpu"),
        "mr": _col(head, r"mem(ory)?requests?|requestsmem(ory)?|memreq|reqmem"),
        "ml": _col(head, r"mem(ory)?limits?|limitsmem(ory)?|memlim|limmem"),
        "cu": _col(head, r"cpu(p95|p99|peak|max|use|usage|used|avg|mean)", r"(p95|p99|peak|max|use|usage|used)cpu"),
        "mu": _col(head, r"mem(ory)?(p95|p99|peak|max|use|usage|used|workingset|avg|mean)", r"(p95|p99|peak|max|use|usage|used)mem(ory)?"),
        "rp": _col(head, r"replicas?|pods|count|instances"),
    }
    if ix["wl"] is None:
        raise RightsizeError("The list needs a workload (or name / pod) column.")
    if ix["cu"] is None and ix["mu"] is None:
        raise RightsizeError("The list needs use columns - cpu_p95 and / or mem_p95 from your monitoring - to compare with the requests.")
    g = lambda r, k: r[ix[k]] if ix[k] is not None else ""   # noqa: E731
    issues, add = finder()
    out = []
    tot = {"cpu_req": 0.0, "cpu_use": 0.0, "mem_req": 0.0, "mem_use": 0.0, "cpu_rec": 0.0, "mem_rec": 0.0}
    no_req = no_lim = 0
    for r in rows:
        try:
            cr, cl, mr, ml, cu, mu = cpu(g(r, "cr")), cpu(g(r, "cl")), mem(g(r, "mr")), mem(g(r, "ml")), cpu(g(r, "cu")), mem(g(r, "mu"))
        except PfInputError as e:
            raise RightsizeError(f"{g(r, 'wl')}: {e}")
        try:
            rep = max(1, int(float(g(r, "rp") or 1)))
        except ValueError:
            rep = 1
        name = "/".join(x for x in (g(r, "ns"), g(r, "wl"), g(r, "ct")) if x)
        row: dict[str, Any] = {"name": name, "replicas": rep, "cpu_req": cr, "cpu_lim": cl, "mem_req": mr, "mem_lim": ml, "cpu_use": cu, "mem_use": mu, "flags": []}
        rc = max(0.01, cu * (1 + headroom)) if cu is not None else None
        rm = max(32 / 1024, mu * (1 + headroom)) if mu is not None else None
        row["cpu_rec"], row["mem_rec"] = rc, rm
        if cr is None or mr is None:
            no_req += 1
            row["flags"].append("no request")
        if ml is None:
            no_lim += 1
        if mu is not None and ml is not None and mu >= 0.9 * ml:
            row["flags"].append("near memory limit")
            add("bad", "Out of memory", f"{name} uses {gib(mu)} of its {gib(ml)} memory limit - it will be killed when it goes over.",
                f"Raise the limit to about {gib(mu * 1.3)} (and the request to {gib(rm)}), or find the leak.", name)
        if cu is not None and cl is not None and cu >= 0.9 * cl:
            row["flags"].append("near CPU limit")
            add("warn", "Throttled", f"{name} uses {cores(cu)} of a {cores(cl)} CPU limit - it is slowed down at busy times.",
                "Raise or remove the CPU limit (keep the request); CPU limits mostly add latency.", name)
        if mu is not None and mr is not None and mu > mr * 1.1:
            row["flags"].append("memory above request")
            add("warn", "Too tight", f"{name} uses {gib(mu)} memory but requests {gib(mr)} - it is placed on nodes that cannot hold it and is evicted first.",
                f"Request about {gib(rm)}.", name)
        if cu is not None and cr is not None and cu > cr * 1.5 and cu - cr >= 0.1:
            row["flags"].append("CPU above request")
            add("info", "CPU above request", f"{name} uses {cores(cu)} CPU on a {cores(cr)} request - it borrows spare CPU that may not be there.", f"Request about {cores(rc)}.", name)
        waste_c = (cr - rc) * rep if cr is not None and rc is not None and cr > rc else 0.0
        waste_m = (mr - rm) * rep if mr is not None and rm is not None and mr > rm else 0.0
        if (cr and cu is not None and cr > 2 * max(cu, 0.001) and waste_c >= 0.1) or (mr and mu is not None and mr > 2 * max(mu, 0.001) and waste_m >= 0.25):
            row["flags"].append("over-provisioned")
        row["save_cpu"], row["save_mem"] = waste_c, waste_m
        row["save_money"] = (waste_c * cpu_price + waste_m * mem_price)
        for k, v, n in (("cpu_req", cr, rep), ("cpu_use", cu, rep), ("mem_req", mr, rep), ("mem_use", mu, rep)):
            if v is not None:
                tot[k] += v * n
        tot["cpu_rec"] += (rc if rc is not None else (cr or 0)) * rep
        tot["mem_rec"] += (rm if rm is not None else (mr or 0)) * rep
        out.append(row)
    out.sort(key=lambda x: -(x["save_money"] or (x["save_cpu"] + x["save_mem"] / 4)))
    over = [x for x in out if "over-provisioned" in x["flags"]]
    s_cpu = sum(x["save_cpu"] for x in out)
    s_mem = sum(x["save_mem"] for x in out)
    if over:
        top = over[0]
        add("warn", "Over-provisioned", f"{len(over)} container(s) request more than twice what they use - {cores(s_cpu)} cores and {gib(s_mem)} could be given back"
            + (f" (about {s_cpu * cpu_price + s_mem * mem_price:,.2f} a month)" if cpu_price or mem_price else "") + f"; the most: {top['name']}.",
            "Lower the requests to the recommended values, a few workloads at a time, and watch for throttling and restarts.")
    if no_req:
        add("warn", "No requests", f"{no_req} container(s) have no CPU or memory request - the scheduler places them blind and they are evicted first.", "Set requests on every container.")
    if no_lim:
        add("info", "No memory limit", f"{no_lim} container(s) have no memory limit - one leak can starve the node.", "Set a memory limit about 1.3x the peak.")
    eff_c = tot["cpu_use"] / tot["cpu_req"] if tot["cpu_req"] else None
    eff_m = tot["mem_use"] / tot["mem_req"] if tot["mem_req"] else None
    res = {"rows": out, "containers": len(out), "totals": tot, "eff_cpu": eff_c, "eff_mem": eff_m, "save_cpu": s_cpu, "save_mem": s_mem,
           "save_money": s_cpu * cpu_price + s_mem * mem_price if (cpu_price or mem_price) else None, "headroom": headroom,
           "over": len(over), "verdict": f"{len(out)} container(s): {cores(tot['cpu_req'])} cores and {gib(tot['mem_req'])} requested, "
                                         + (f"{eff_c * 100:.0f}% of CPU" if eff_c is not None else "CPU use unknown") + " and " + (f"{eff_m * 100:.0f}% of memory used" if eff_m is not None else "memory use unknown")}
    res["note"] = (f"Recommended requests = the use you gave + {headroom * 100:.0f}% headroom (at least 10m CPU and 32Mi). Use the p95 over a busy week, "
                   "not an average; batch and Java workloads need their peaks." + (" Money is per month at your prices per core and per GiB." if cpu_price or mem_price else ""))
    return finish(res, issues)
