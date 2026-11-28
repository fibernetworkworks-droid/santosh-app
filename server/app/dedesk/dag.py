"""A data pipeline read as a graph: Airflow-style lines (a >> b >> c, [a, b] >> c, a << b), arrows (a -> b), dependency lists
(orders: stg_orders, stg_customers) or a dbt manifest.json (nodes with depends_on, or parent_map). With durations (extract = 12m) it
finds the critical path - the chain that sets how long a run takes - and whether a run fits her window. Also: loops (a pipeline that
cannot run), tasks with no links, levels that can run side by side, heavy fan-in, links already implied by others. A Mermaid
drawing of the graph comes back too."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from .common import DeInputError, finder, finish, mins, minutes

_NAME = r"[A-Za-z_][\w.\-:]*"
_DURLINE = re.compile(rf"^\s*({_NAME})\s*=\s*([\d.:]+\s*[a-zA-Z]*)\s*$")
_LIST = re.compile(r"^\s*\[(.*)\]\s*$")


class DagError(DeInputError):
    pass


def _side(s: str) -> list[str]:
    s = s.strip()
    m = _LIST.match(s)
    parts = m.group(1).split(",") if m else [s]
    out = []
    for p in parts:
        p = p.strip().strip("'\"")
        if p:
            if not re.fullmatch(_NAME, p):
                raise DagError(f"'{p[:40]}' is not a task name.")
            out.append(p)
    return out


def _from_manifest(d: dict[str, Any]) -> tuple[set[str], list[tuple[str, str]]]:
    nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    def short(x: str) -> str:   # model.shop.orders -> orders; source.shop.raw.orders -> raw.orders
        p = x.split(".")
        if p[0] == "source" and len(p) >= 4:
            return ".".join(p[-2:])
        return p[-1] if len(p) >= 3 else x
    if isinstance(d.get("parent_map"), dict):
        for child, parents in d["parent_map"].items():
            if child.startswith("test."):
                continue
            nodes.add(short(child))
            for p in parents or []:
                if not p.startswith("test."):
                    nodes.add(short(p))
                    edges.append((short(p), short(child)))
    elif isinstance(d.get("nodes"), dict):
        for nid, n in d["nodes"].items():
            if nid.startswith("test.") or (isinstance(n, dict) and n.get("resource_type") == "test"):
                continue
            nodes.add(short(nid))
            for p in ((n or {}).get("depends_on") or {}).get("nodes") or []:
                if not p.startswith("test."):
                    nodes.add(short(p))
                    edges.append((short(p), short(nid)))
    else:
        raise DagError("A JSON pipeline must be a dbt manifest.json (with nodes or parent_map).")
    return nodes, edges


def parse(text: str) -> tuple[set[str], list[tuple[str, str]], dict[str, float]]:
    t = str(text or "").strip()
    if not t:
        raise DagError("Paste the pipeline: lines like 'extract >> transform >> load', 'a -> b', 'orders: stg_orders, stg_customers', or a dbt manifest.json.")
    if t.startswith("{"):
        try:
            d = json.loads(t)
        except ValueError:
            raise DagError("That JSON could not be read.")
        n, e = _from_manifest(d)
        return n, e, {}
    nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    dur: dict[str, float] = {}
    bad = 0
    for raw in t.splitlines():
        line = raw.split("#")[0].strip().rstrip(";")
        if not line or line.lower().startswith(("graph ", "flowchart ", "with ", "from ", "import ", "def ", "@", "dag =", "dag=")):
            continue
        m = _DURLINE.match(line)
        if m and minutes(m.group(2)) is not None:
            dur[m.group(1)] = minutes(m.group(2))
            nodes.add(m.group(1))
            continue
        line = line.replace("-->", "->").replace("→", "->")
        if ">>" in line or "<<" in line or "->" in line:
            toks = re.split(r"(>>|<<|->)", line)
            sides = [_side(x) for x in toks[0::2]]
            ops = toks[1::2]
            for i, op in enumerate(ops):
                a, b = sides[i], sides[i + 1]
                if op == "<<":
                    a, b = b, a
                for x in a:
                    for y in b:
                        edges.append((x, y))
                nodes.update(a)
                nodes.update(b)
            continue
        if ":" in line:
            head, tail = line.split(":", 1)
            head = head.strip()
            if re.fullmatch(_NAME, head):
                nodes.add(head)
                ds = [x.strip() for x in re.split(r"[,\s]+", tail.strip().strip("[]")) if x.strip()]
                for p in ds:
                    if minutes(p) is not None and not re.fullmatch(_NAME, p):
                        dur[head] = minutes(p)
                        continue
                    if not re.fullmatch(_NAME, p):
                        raise DagError(f"'{p[:40]}' is not a task name.")
                    nodes.add(p)
                    edges.append((p, head))
                continue
        if re.fullmatch(_NAME, line):
            nodes.add(line)
            continue
        bad += 1
        if bad > 3:
            raise DagError(f"Could not read: '{line[:60]}'. Use 'a >> b', 'a -> b', 'task: parent1, parent2' or 'task = 12m'.")
    if not nodes:
        raise DagError("No tasks found.")
    return nodes, list(dict.fromkeys(edges)), dur


def _cycle(nodes: set[str], kids: dict[str, list[str]]) -> list[str] | None:
    color = {n: 0 for n in nodes}
    stack: list[str] = []
    for start in sorted(nodes):
        if color[start]:
            continue
        it = [(start, iter(sorted(kids[start])))]
        color[start] = 1
        stack = [start]
        while it:
            n, ch = it[-1]
            nxt = next(ch, None)
            if nxt is None:
                color[n] = 2
                it.pop()
                stack.pop()
            elif color[nxt] == 1:
                return stack[stack.index(nxt):] + [nxt]
            elif color[nxt] == 0:
                color[nxt] = 1
                stack.append(nxt)
                it.append((nxt, iter(sorted(kids[nxt]))))
    return None


def analyse(text: str, window: float | None = None) -> dict[str, Any]:
    nodes, edges, dur = parse(text)
    issues, add = finder()
    kids: dict[str, list[str]] = defaultdict(list)
    par: dict[str, list[str]] = defaultdict(list)
    for a, b in edges:
        if a == b:
            raise DagError(f"{a} depends on itself.")
        kids[a].append(b)
        par[b].append(a)
    res: dict[str, Any] = {"tasks": len(nodes), "edges": [list(e) for e in edges], "durations": dur}
    cyc = _cycle(nodes, kids)
    if cyc:
        add("bad", "Loop", f"The pipeline has a loop: {' -> '.join(cyc)}. It can never start.", "Break the loop: one of these steps must read the previous run's output instead.")
        res.update(cycle=cyc, levels=[], critical=None, verdict=f"{len(nodes)} tasks - the pipeline has a loop and cannot run", mermaid=_mermaid(nodes, edges, set()),
                   note="A loop is found by following the links; nothing ran.")
        return finish(res, issues)
    # levels (longest distance from a root)
    order: list[str] = []
    indeg = {n: len(par[n]) for n in nodes}
    q = sorted(n for n in nodes if indeg[n] == 0)
    lvl = {n: 0 for n in q}
    while q:
        n = q.pop(0)
        order.append(n)
        for k in sorted(kids[n]):
            lvl[k] = max(lvl.get(k, 0), lvl[n] + 1)
            indeg[k] -= 1
            if indeg[k] == 0:
                q.append(k)
    levels: list[list[str]] = [[] for _ in range(max(lvl.values()) + 1)]
    for n in order:
        levels[lvl[n]].append(n)
    roots = [n for n in order if not par[n]]
    leaves = [n for n in order if not kids[n]]
    lone = [n for n in order if not par[n] and not kids[n]]
    res.update(levels=levels, roots=roots, leaves=leaves, lone=lone, depth=len(levels), widest=max(len(x) for x in levels))
    # critical path
    known = [n for n in nodes if n in dur]
    crit = None
    if known:
        fin: dict[str, float] = {}
        best_par: dict[str, str | None] = {}
        for n in order:
            st, bp = 0.0, None
            for p in par[n]:
                if fin[p] > st:
                    st, bp = fin[p], p
            fin[n] = st + dur.get(n, 0.0)
            best_par[n] = bp
        end = max(order, key=lambda n: fin[n])
        path = [end]
        while best_par[path[-1]]:
            path.append(best_par[path[-1]])
        path.reverse()
        serial = sum(dur.values())
        slack = {}
        late: dict[str, float] = {}
        for n in reversed(order):
            late[n] = min([late[k] - dur.get(k, 0.0) for k in kids[n]] or [fin[end]])
            slack[n] = late[n] - fin[n]
        crit = {"path": path, "minutes": fin[end], "serial": serial, "share": {n: dur.get(n, 0.0) / fin[end] if fin[end] else 0 for n in path},
                "finish": fin, "slack": slack}
        res["critical"] = crit
        if len(known) < len(nodes):
            missing = sorted(nodes - set(known))
            add("info", "Durations", f"{len(missing)} task(s) have no duration and count as 0: {', '.join(missing[:6])}.", "Add lines like 'task = 12m' for a true critical path.")
        top = max(path, key=lambda n: dur.get(n, 0.0))
        if fin[end] and dur.get(top, 0) / fin[end] >= 0.4 and len(path) > 1:
            add("warn", "Critical path", f"{top} takes {mins(dur[top])} - {dur[top] / fin[end] * 100:.0f}% of the whole run, and everything after it waits.",
                "Speed it up first (incremental loads, partition pruning, more parallel workers); tasks off the critical path gain nothing.", top)
        if window:
            if fin[end] > window:
                add("bad", "Window", f"A run takes {mins(fin[end])} on the critical path - over the {mins(window)} window.",
                    "Shorten the critical path or start earlier; adding workers only helps tasks that run side by side.")
            elif fin[end] > 0.8 * window:
                add("warn", "Window", f"A run takes {mins(fin[end])} - {fin[end] / window * 100:.0f}% of the {mins(window)} window, little room for a slow day.", "")
    else:
        res["critical"] = None
    # findings
    if lone and len(nodes) > 1:
        add("warn", "Lone tasks", f"{len(lone)} task(s) are linked to nothing: {', '.join(lone[:6])}.", "Link them, or they run in any order (often too early).")
    for n in order:
        if len(par[n]) >= 6:
            add("info", "Fan-in", f"{n} waits for {len(par[n])} tasks - one late upstream holds it.", "Fine if they are all needed; otherwise split the task.", n)
    red = []
    reach: dict[str, set[str]] = {}
    for n in reversed(order):
        r: set[str] = set()
        for k in kids[n]:
            r |= {k} | reach[k]
        reach[n] = r
    for a, b in edges:
        if any(b in reach[k] for k in kids[a] if k != b):
            red.append([a, b])
    if red:
        add("info", "Extra links", f"{len(red)} link(s) are already implied by others, e.g. {red[0][0]} -> {red[0][1]}.", "Harmless, but removing them makes the graph easier to read.")
    if len(roots) > 1 and len(leaves) > 1 and len(nodes) > 10:
        add("info", "Shape", f"{len(roots)} start points and {len(leaves)} end points.", "Several end points are fine; check each is consumed by something.")
    v = f"{len(nodes)} tasks in {len(levels)} levels, up to {res['widest']} side by side"
    if crit:
        v += f"; critical path {mins(crit['minutes'])} ({len(crit['path'])} tasks)"
    res["verdict"] = v
    res["redundant"] = red
    res["mermaid"] = _mermaid(nodes, edges, set(crit["path"]) if crit else set())
    res["note"] = "Worked out from the links and durations you gave - real runs add queueing, retries and pool limits."
    return finish(res, issues)


def _mermaid(nodes: set[str], edges: list[tuple[str, str]], hot: set[str]) -> str:
    ids = {n: f"n{i}" for i, n in enumerate(sorted(nodes))}
    lines = ["flowchart LR"] + [f'  {ids[n]}["{n}"]' for n in sorted(nodes)] + [f"  {ids[a]} --> {ids[b]}" for a, b in edges]
    if hot:
        lines.append("  classDef hot stroke-width:3px")
        lines.append("  class " + ",".join(ids[n] for n in sorted(hot)) + " hot")
    return "\n".join(lines)
