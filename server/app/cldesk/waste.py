"""Cloud resources nobody uses, from an inventory she exports (one row per resource: id, type, state, whether it is attached,
CPU use, age, size, monthly cost): disks attached to nothing, public addresses held by nothing, machines stopped but still paying
for their disks (and, on Azure, a machine stopped without being deallocated still paying for its compute), running machines whose
CPU never rises above her idle line, snapshots older than her keep days, load balancers and databases with no traffic, and older
machine and disk generations. Money is only counted where the resource's own monthly cost is in the table - nothing is priced
from memory."""
from __future__ import annotations

import re
from typing import Any

from ..mldesk.table import TableError, read
from .common import ClInputError, amt, col, day, finder, finish, money, num


class WasteError(TableError):
    pass


TYPES = (
    ("snapshot", r"snapshot|image backup|ami"),
    ("disk", r"volume|disk|ebs|persistent ?disk|\bpd\b|managed ?disk"),
    ("ip", r"elastic ?ip|\beip\b|public ?ip|static ?ip|address"),
    ("lb", r"load ?balancer|\belb\b|\balb\b|\bnlb\b|application gateway|forwarding rule"),
    ("db", r"\brds\b|database|\bsql\b|aurora|cosmos|cloud sql|postgres|mysql"),
    ("bucket", r"bucket|\bs3\b|blob|storage account|gcs"),
    ("vm", r"instance|\bvm\b|virtual machine|\bec2\b|compute engine|\bgce\b|server|droplet"),
)
OLD_GEN = re.compile(r"^(t1|t2|m1|m2|m3|m4|c1|c3|c4|r3|r4|i2|d2|g2|p2|x1)\.|^n1-|^standard_[a-z]+\d+s?_v[12]$", re.I)


def _type(v: str) -> str:
    s = str(v or "").lower()
    for k, p in TYPES:
        if re.search(p, s):
            return k
    return "other"


def _yes(v: str) -> bool | None:
    s = str(v or "").strip().lower()
    if not s:
        return None
    if s in ("yes", "y", "true", "1", "attached", "in-use", "in use", "inuse", "associated", "used", "bound"):
        return True
    if s in ("no", "n", "false", "0", "available", "unattached", "detached", "unassociated", "free", "reserved", "none", "-"):
        return False
    return True   # an instance id, a target name ... = attached to something


def analyse(text: str, idle_cpu: float = 5.0, keep_days: float = 90.0, today: Any = None, currency: str = "") -> dict[str, Any]:
    head, rows = read(text, "The inventory")
    ix = {
        "id": col(head, r"resourceid", r"id", r"arn", r"name", r"resource", r"resourcename"),
        "type": col(head, r"resourcetype", r"type", r"kind", r"service"),
        "itype": col(head, r"instancetype", r"machinetype", r"vmsize", r"size", r"sku", r"volumetype", r"disktype", r"class"),
        "state": col(head, r"state", r"status", r"powerstate", r"instancestate"),
        "att": col(head, r"attached(to)?", r"attachment(s)?", r"inuse", r"associated(with)?", r"associatedto", r"usedby", r"targets?", r"connections?", r"requests?"),
        "cpu": col(head, r"cpup95", r"cpup99", r"cpumax", r"cpupeak", r"maxcpu", r"cpu", r"cpuavg", r"cpuaverage", r"avgcpu", r"cpuutili[sz]ation", r"cpupercent"),
        "age": col(head, r"agedays", r"age", r"daysold", r"idledays", r"stoppeddays"),
        "created": col(head, r"created(at|on|time|date)?", r"creationdate", r"launchtime", r"starttime", r"lastused"),
        "gb": col(head, r"sizegb", r"size(gib)?", r"gb", r"storagegb", r"capacitygb"),
        "cost": col(head, r"monthlycost", r"costpermonth", r"costmonth", r"monthly", r"cost", r"price", r"spend"),
        "region": col(head, r"region", r"zone", r"location", r"availabilityzone"),
    }
    if ix["id"] is None or ix["type"] is None:
        raise WasteError("The inventory needs an id (or name) column and a type column.")
    g = lambda r, k: r[ix[k]] if ix[k] is not None else ""   # noqa: E731
    from datetime import date
    td = day(today) if today else date.today()
    issues, add = finder()
    found: list[dict[str, Any]] = []
    kinds: dict[str, int] = {}
    total = 0.0
    for r in rows:
        try:
            cost = money(g(r, "cost"))
            cpu = num(g(r, "cpu"))
            age = num(g(r, "age"))
            if age is None and g(r, "created"):
                c = day(g(r, "created"))
                age = float((td - c).days) if c else None
        except ClInputError as e:
            raise WasteError(f"{g(r, 'id')}: {e}")
        t = _type(g(r, "type"))
        kinds[t] = kinds.get(t, 0) + 1
        total += cost or 0.0
        st = g(r, "state").lower()
        att = _yes(g(r, "att"))
        it = g(r, "itype")
        rid = g(r, "id")

        def hit(why: str, act: str, sev: str = "warn", save: float | None = cost, check: bool = False) -> None:
            found.append({"id": rid, "type": t, "itype": it, "region": g(r, "region"), "state": g(r, "state"), "why": why, "do": act, "sev": sev,
                          "save": save, "check": check, "age": age})
        if t == "disk" and (att is False or st in ("available", "unattached", "detached")):
            hit("attached to nothing", "Snapshot it if you need it, then delete it.")
        elif t == "ip" and (att is False or st in ("unassociated", "reserved", "available")):
            hit("held by nothing", "Release it (public addresses are billed while unused).")
        elif t == "vm" and "deallocat" not in st and st in ("stopped", "vm stopped", "poweredoff", "powered off") and re.search(r"azure|^vm$|virtual machine", g(r, "type"), re.I):
            hit("stopped but not deallocated - Azure still bills its compute", "Stop it with Deallocate (or delete it).", "bad")
        elif t == "vm" and st in ("stopped", "terminated", "deallocated", "stopping", "suspended", "vm deallocated"):
            if age is not None and age >= keep_days:
                hit(f"stopped for {age:.0f} days - its disks are still billed", "Image it if you need it, then delete it and its disks.", "warn", cost, True)
        elif t == "vm" and cpu is not None and cpu < idle_cpu and st in ("", "running", "vm running", "active", "on"):
            hit(f"CPU never above {cpu:g}% (under your {idle_cpu:g}% line)", "Downsize it, schedule it off out of hours, or delete it.", "warn", cost, True)
        elif t == "snapshot" and age is not None and age > keep_days:
            hit(f"{age:.0f} days old (you keep {keep_days:.0f})", "Delete it if no restore needs it.", "info")
        elif t in ("lb", "db") and att is False:
            hit("no " + ("targets or traffic" if t == "lb" else "connections"), "Delete it if nothing uses it.", "warn", cost, True)
        if it and OLD_GEN.search(it):
            found.append({"id": rid, "type": t, "itype": it, "region": g(r, "region"), "state": g(r, "state"), "why": f"{it} is an older generation",
                          "do": "Move to the current generation - usually less per unit of work; check the price in your region.", "sev": "info",
                          "save": None, "check": True, "age": age})
        if t == "disk" and it.lower() == "gp2":
            found.append({"id": rid, "type": t, "itype": it, "region": g(r, "region"), "state": g(r, "state"), "why": "gp2 volume",
                          "do": "AWS lists gp3 at a lower price per GB than gp2, with its own baseline speed - check this for your region and size.",
                          "sev": "info", "save": None, "check": True, "age": age})
    found.sort(key=lambda f: ({"bad": 0, "warn": 1, "info": 2}[f["sev"]], -(f["save"] or 0)))
    save = sum(f["save"] or 0 for f in found if f["save"])
    by: dict[str, dict[str, Any]] = {}
    for f in found:
        key = {"disk": "Unattached disks", "ip": "Unused addresses", "snapshot": "Old snapshots", "lb": "Idle load balancers", "db": "Idle databases"}.get(f["type"], "")
        if "generation" in f["why"] or f["why"] == "gp2 volume":
            key = "Older generations"
        elif f["type"] == "vm":
            key = "Not deallocated" if "deallocated" in f["why"] else "Stopped machines" if "stopped" in f["why"] else "Idle machines"
        b = by.setdefault(key or "Other", {"name": key or "Other", "count": 0, "save": 0.0})
        b["count"] += 1
        b["save"] += f["save"] or 0.0
    groups = sorted(by.values(), key=lambda b: -b["save"])
    FIX = {"Unattached disks": "Snapshot what you need, then delete the disks.", "Unused addresses": "Release them - unused public addresses are billed.",
           "Old snapshots": "Delete the ones no restore needs.", "Idle load balancers": "Delete them if nothing uses them.",
           "Idle databases": "Snapshot and delete them if nothing uses them.", "Not deallocated": "Stop them with Deallocate, or delete them.",
           "Stopped machines": "Image what you need, then delete the machines and their disks.",
           "Idle machines": "Downsize them, schedule them off out of hours, or delete them.",
           "Older generations": "Move to the current generation - check the price in your region."}
    for b in groups:
        sev = "bad" if b["name"] == "Not deallocated" else "info" if b["name"] in ("Older generations", "Old snapshots") else "warn"
        add(sev, b["name"], f"{b['count']} resource(s)" + (f" costing {amt(b['save'], currency)} a month" if b["save"] else "") + ".", FIX.get(b["name"], ""))
    if ix["cost"] is None:
        add("info", "No costs", "The inventory has no monthly cost column, so nothing is priced.", "Add each resource's monthly cost to see what cleaning it saves.")
    res = {"resources": len(rows), "kinds": kinds, "found": found[:400], "candidates": len([f for f in found if f["sev"] != "info" or f["type"] == "snapshot"]),
           "save": save, "total": total if ix["cost"] is not None else None, "groups": groups, "currency": currency, "idle_cpu": idle_cpu, "keep_days": keep_days,
           "verdict": f"{len(found)} thing(s) to look at in {len(rows)} resource(s)" + (f" - {amt(save, currency)} a month" if save else "")}
    res["note"] = ("Marked 'check this' where a number alone cannot decide - a quiet CPU can still be a busy database or a standby. The saving is the "
                   "resource's own monthly cost from your table, counted only for things that would be deleted or released.")
    return finish(res, issues)
