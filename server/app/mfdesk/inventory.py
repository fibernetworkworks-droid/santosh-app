"""A whole inventory read together: programs, copybooks and JCL pasted under '## name' headings (or one after another) become one
dependency map - job -> program, program -> program (CALL, CICS LINK / XCTL), program -> copybook, program -> DB2 table, job ->
dataset. From it: what is referenced but not in the paste, programs nothing starts, cycles (programs that call each other), groups that
share tables (their data moves together), migration waves (the programs that call nothing first), and a suggested approach per
program from what it contains - each with its reason, for her to decide. Pasted sources are data."""
from __future__ import annotations

import re
from typing import Any

from . import cobol as CB, jcl as JC


class InventoryError(ValueError):
    pass


def _chunks(text: str) -> list[tuple[str, str]]:
    t = str(text or "")
    heads = list(re.finditer(r"^\s*##\s*(.+?)\s*$", t, re.M))
    if heads:
        out = []
        if t[:heads[0].start()].strip():
            out.append(("", t[:heads[0].start()]))
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
            out.append((m.group(1).strip()[:60], t[m.end():end]))
        return out
    return [("", t)]


def _kind(body: str) -> str:
    if re.search(r"^//\S*\s+(?:JOB|EXEC)\b", body, re.M):
        return "jcl"
    if re.search(r"\b(?:IDENTIFICATION|ID)\s+DIVISION\b|\bPROGRAM-ID\b", body, re.I):
        return "program"
    return "copybook"


def _tarjan(nodes: list[str], edges: dict[str, set[str]]) -> list[list[str]]:
    idx: dict[str, int] = {}
    low: dict[str, int] = {}
    on: set[str] = set()
    st: list[str] = []
    out: list[list[str]] = []
    c = [0]

    def go(v: str) -> None:
        idx[v] = low[v] = c[0]
        c[0] += 1
        st.append(v)
        on.add(v)
        for w in edges.get(v, ()):
            if w not in idx:
                go(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            out.append(sorted(comp))
    import sys
    lim = sys.getrecursionlimit()
    sys.setrecursionlimit(max(lim, 10000))
    try:
        for v in nodes:
            if v not in idx:
                go(v)
    finally:
        sys.setrecursionlimit(lim)
    return out


def _strategy(p: dict[str, Any], called: bool, started: bool, n_callers: int) -> tuple[str, str]:
    s = p["stats"]
    if not called and not started:
        return ("Retire?", "Nothing in the paste starts or calls it - check the scheduler, CICS transactions and dynamic calls before switching it off.")
    if s["alter"]:
        return ("Rewrite with tests", "It uses ALTER: the control flow is decided while it runs - capture its behaviour in tests, then rewrite.")
    if s["goto"] > max(5, s["paragraphs"] // 3) or s["complexity"] > 150:
        return ("Restructure, then translate", f"{s['goto']} GO TO and {s['decisions']} decisions - untangle the flow first, with its outputs captured as tests.")
    if p["online"] and p["screens"]:
        return ("Replatform the screens", f"An online program with {p['screens']} screen send / receive(s): keep the logic, replace the BMS maps with the new front end.")
    if p["tables"] and not p["online"]:
        return ("Translate (batch + DB2)", f"Batch logic over {len(p['tables'])} DB2 table(s) - translates directly; move the tables with the programs that share them.")
    if n_callers >= 3:
        return ("Translate first (shared)", f"Called by {n_callers} programs - a shared routine: translate it once, early, and call the new one from both sides while you move.")
    return ("Translate", "Plain logic with no blockers these checks see.")


def analyse(text: str) -> dict[str, Any]:
    t = str(text or "")
    if len(t) > 30_000_000:
        raise InventoryError("That is longer than 30 MB.")
    progs: dict[str, dict[str, Any]] = {}
    copybooks: dict[str, str] = {}
    jobs: list[dict[str, Any]] = []
    for head, body in _chunks(t):
        if not body.strip():
            continue
        k = _kind(body)
        if k == "jcl":
            try:
                jobs.append(JC.analyse(body))
            except JC.JclError:
                pass
        elif k == "program":
            for src in CB.split_programs(body):
                p = CB.program(src)
                if p["name"] == "(no PROGRAM-ID)" and head:
                    p["name"] = head.upper()
                progs[p["name"]] = p
        else:
            nm = (head or "").upper().split(".")[0].strip()
            if nm:
                copybooks[nm] = body
    if not progs and not jobs:
        raise InventoryError("No programs or JCL found - paste the sources, each under '## name' (copybooks need their name on the heading).")
    edges: dict[str, set[str]] = {n: set() for n in progs}
    all_calls: dict[str, set[str]] = {}
    callers: dict[str, set[str]] = {}
    missing: dict[str, set[str]] = {"program": set(), "copybook": set(), "proc": set()}
    dyn: list[str] = []
    for n, p in progs.items():
        for c in p["calls"]:
            tos = [c["to"]] if c["how"] != "dynamic" else c.get("values") or []
            if c["how"] == "dynamic" and not c.get("values"):
                dyn.append(f"{n} (CALL {c['to']})")
            for to in tos:
                if CB.SYSTEM_CALL.match(to):
                    continue
                all_calls.setdefault(n, set()).add(to)
                callers.setdefault(to, set()).add(n)
                if to in progs:
                    edges[n].add(to)
                else:
                    missing["program"].add(to)
        for cp in p["copies"]:
            if cp not in copybooks and cp not in CB.SYSTEM_COPY:
                missing["copybook"].add(cp)
    started: dict[str, list[str]] = {}
    datasets: dict[str, dict[str, set[str]]] = {}
    for jb in jobs:
        for s in jb["steps"]:
            pg = s["program"]
            where = f"{s['job']}.{s['step']}"
            if s["via"] == "PROC":
                missing["proc"].add(pg)
                continue
            if pg and pg not in JC.UTIL:
                started.setdefault(pg, []).append(where)
                if pg not in progs:
                    missing["program"].add(pg)
            for d in s["reads"]:
                datasets.setdefault(d.split("(")[0], {"read": set(), "write": set()})["read"].add(where)
            for d in s["writes"]:
                datasets.setdefault(d.split("(")[0], {"read": set(), "write": set()})["write"].add(where)
    # transactions: a CICS program reached by RETURN TRANSID / START is started too, but the transaction -> program table is CSD, not here
    sccs = _tarjan(list(progs), edges)
    comp_of = {v: i for i, c in enumerate(sccs) for v in c}
    cycles = [c for c in sccs if len(c) > 1 or (c and c[0] in edges.get(c[0], set()))]
    # waves: callees first (levels on the condensed graph)
    level: dict[int, int] = {}

    def lv(ci: int, seen: tuple = ()) -> int:
        if ci in level:
            return level[ci]
        outs = {comp_of[w] for v in sccs[ci] for w in edges.get(v, ()) if comp_of[w] != ci}
        level[ci] = 0 if not outs else 1 + max(lv(o) for o in outs)
        return level[ci]
    for i in range(len(sccs)):
        lv(i)
    waves: dict[int, list[str]] = {}
    for n in progs:
        waves.setdefault(level[comp_of[n]], []).append(n)
    # table groups: programs sharing a table move with it
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for n, p in progs.items():
        for tb in p["tables"]:
            parent[find("T:" + tb)] = find("P:" + n)
    groups: dict[str, dict[str, list[str]]] = {}
    for n, p in progs.items():
        if p["tables"]:
            g = groups.setdefault(find("P:" + n), {"programs": [], "tables": []})
            g["programs"].append(n)
    for n, p in progs.items():
        for tb in p["tables"]:
            g = groups[find("P:" + n)]
            if tb not in g["tables"]:
                g["tables"].append(tb)
    table_groups = [{"programs": sorted(g["programs"]), "tables": sorted(g["tables"])} for g in groups.values() if len(g["programs"]) > 1]
    rows = []
    for n, p in sorted(progs.items()):
        st = p["stats"]
        appr, why = _strategy(p, bool(callers.get(n)), bool(started.get(n)), len(callers.get(n, ())))
        rows.append({"name": n, "loc": p["loc"], "kind": "online" if p["online"] else "batch", "paragraphs": st["paragraphs"], "decisions": st["decisions"],
                     "goto": st["goto"], "alter": st["alter"], "dead": len(p["dead"]), "calls": sorted(all_calls.get(n, ())), "callers": sorted(callers.get(n, ())),
                     "started_by": started.get(n, [])[:10], "copies": p["copies"], "tables": p["tables"], "files": [f["dd"] for f in p["files"]],
                     "wave": level[comp_of[n]] + 1, "size": round(p["loc"] / 100 + st["decisions"] / 10, 1), "approach": appr, "why": why,
                     "risks": len([i for i in p["issues"] if i["sev"] in ("bad", "warn")])})
    issues: list[dict[str, Any]] = []
    for k, label in (("program", "program(s)"), ("copybook", "copybook(s)"), ("proc", "JCL procedure(s)")):
        if missing[k]:
            issues.append({"sev": "warn", "area": "Missing", "text": f"{len(missing[k])} {label} used but not in the paste: {', '.join(sorted(missing[k])[:12])}" + (" ..." if len(missing[k]) > 12 else "") + ".",
                           "fix": "Add them (or confirm they are vendor / system code) so the map is complete."})
    if dyn:
        issues.append({"sev": "warn", "area": "Missing", "text": f"{len(dyn)} CALL(s) through a data name with no value seen: {', '.join(dyn[:6])} - their targets are not on the map."})
    for c in cycles:
        issues.append({"sev": "warn", "area": "Cycles", "text": f"These programs call each other: {', '.join(c)} - they move in one wave, together.", "fix": "Translate them together, or break the cycle with an interface first."})
    orphans = [r["name"] for r in rows if not r["callers"] and not r["started_by"]]
    if orphans and jobs:
        issues.append({"sev": "info", "area": "Unused?", "text": f"{len(orphans)} program(s) nothing in the paste calls or runs: {', '.join(orphans[:10])} - online transactions, the scheduler or other systems may still start them."})
    for g in table_groups:
        issues.append({"sev": "info", "area": "Data", "text": f"{', '.join(g['programs'][:8])} share {', '.join(g['tables'][:6])} - move these tables and programs in the same step, or keep the data in sync while they are split."})
    total_dead = sum(len(p["dead"]) for p in progs.values())
    if total_dead:
        issues.append({"sev": "info", "area": "Dead code", "text": f"{total_dead} paragraph(s) across the programs are never reached - leave them out of the translation after checking."})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order[i["sev"]])
    nodes = ([{"id": "P:" + n, "label": n, "type": "program", "wave": level[comp_of[n]] + 1} for n in progs] +
             [{"id": "P:" + n, "label": n, "type": "missing"} for n in sorted(missing["program"])] +
             [{"id": "J:" + jb["name"], "label": jb["name"], "type": "job"} for j in jobs for jb in j["jobs"]] +
             [{"id": "T:" + tb, "label": tb, "type": "table"} for tb in sorted({tb for p in progs.values() for tb in p["tables"]})] +
             [{"id": "C:" + c, "label": c, "type": "copybook" if c in copybooks else "missing-copybook"} for c in sorted({c for p in progs.values() for c in p["copies"] if c not in CB.SYSTEM_COPY})])
    links = ([{"from": "P:" + a, "to": "P:" + b, "kind": "calls"} for a, bs in all_calls.items() for b in sorted(bs)] +
             [{"from": "J:" + w.split(".")[0], "to": "P:" + pg, "kind": "runs"} for pg, ws in started.items() for w in sorted(set(ws))] +
             [{"from": "P:" + n, "to": "T:" + tb, "kind": "uses"} for n, p in progs.items() for tb in p["tables"]] +
             [{"from": "P:" + n, "to": "C:" + c, "kind": "copies"} for n, p in progs.items() for c in p["copies"] if c not in CB.SYSTEM_COPY])
    seen = set()
    links = [lk for lk in links if not ((lk["from"], lk["to"]) in seen or seen.add((lk["from"], lk["to"])))]
    wl = [{"wave": w + 1, "programs": sorted(ps)} for w, ps in sorted(waves.items())]
    return {"programs": rows, "copybooks": sorted(copybooks), "jobs": [jb for j in jobs for jb in j["jobs"]], "steps": [s for j in jobs for s in j["steps"]][:500],
            "missing": {k: sorted(v) for k, v in missing.items()}, "cycles": cycles, "waves": wl, "table_groups": table_groups,
            "datasets": [{"dsn": d, "read": sorted(v["read"]), "write": sorted(v["write"])} for d, v in sorted(datasets.items())][:1000],
            "nodes": nodes[:1500], "links": links[:4000], "issues": issues, "counts": {k: sum(1 for i in issues if i["sev"] == k) for k in order},
            "totals": {"programs": len(progs), "loc": sum(p["loc"] for p in progs.values()), "copybooks": len(copybooks), "jobs": sum(len(j["jobs"]) for j in jobs),
                       "tables": len({tb for p in progs.values() for tb in p["tables"]}), "online": sum(1 for p in progs.values() if p["online"])},
            "verdict": (f"{len(progs)} program(s), {sum(p['loc'] for p in progs.values()):,} lines, {len(copybooks)} copybook(s), {sum(len(j['jobs']) for j in jobs)} job(s): "
                        f"{len(wl)} wave(s); {sum(len(v) for v in missing.values())} thing(s) referenced but not pasted."),
            "note": ("The map is what the sources say. The scheduler (job order), the CICS transaction table, dynamic calls with no value in the code and "
                     "other systems that read the same data are not in it. Waves put the programs that call nothing first; 'size' is a relative number "
                     "from lines and decisions, not an effort estimate. Every suggested approach is a starting point with its reason - the decision is yours.")}
