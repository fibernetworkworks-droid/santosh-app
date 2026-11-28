"""A ROS 2 system read from what its own tools print: `ros2 node info` for every node (who publishes and subscribes what, services
and actions), `ros2 topic info -v` (each endpoint's QoS), and the tf tree from `ros2 run tf2_tools view_frames` (its frames.gv or the
frame YAML it logs). Finds topics nobody publishes, type mismatches, names that differ by a namespace or a typo, QoS settings that
stop a publisher and a subscriber from ever connecting, clients with no server, and a tf tree that is split, cycles or has gone
stale. All read from the text she pastes; nothing connects to her robot."""
from __future__ import annotations

import re
from typing import Any


class GraphError(ValueError):
    pass


SYSTEM = {"/parameter_events", "/rosout", "/clock"}
_SECT = {"subscribers": "sub", "publishers": "pub", "service servers": "srv", "service clients": "cli", "action servers": "asrv", "action clients": "acli"}
REL = {"BEST_EFFORT": 0, "RELIABLE": 1}
DUR = {"VOLATILE": 0, "TRANSIENT_LOCAL": 1}
LIV = {"AUTOMATIC": 0, "MANUAL_BY_TOPIC": 1}


def _ns(v: str) -> float | None:
    v = v.strip()
    if not v or v.lower().startswith("infinite") or v.startswith("2147483651294967295"):
        return None
    m = re.match(r"([\d.]+)\s*(nanoseconds|ns|seconds|s|milliseconds|ms)?", v)
    if not m:
        return None
    f = {"nanoseconds": 1, "ns": 1, "milliseconds": 1e6, "ms": 1e6, "seconds": 1e9, "s": 1e9}.get(m.group(2) or "nanoseconds", 1)
    return float(m.group(1)) * f


def _edit(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 9
    p = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        c = [i]
        for j, cb in enumerate(b, 1):
            c.append(min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (ca != cb)))
        p = c
    return p[-1]


def _nodes(lines: list[str]) -> dict[str, dict[str, list[tuple[str, str]]]]:
    nodes: dict[str, dict[str, list[tuple[str, str]]]] = {}
    cur = sec = None
    dup: list[str] = []
    for raw in lines:
        if not raw.strip():
            continue
        ind = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if ind == 0 and re.fullmatch(r"/[\w/~]+", s):
            if s in nodes:
                dup.append(s)
            cur, sec = s, None
            nodes.setdefault(cur, {k: [] for k in _SECT.values()})
            continue
        if cur is None:
            continue
        m = re.fullmatch(r"([A-Za-z ]+):", s)
        if m and m.group(1).lower() in _SECT:
            sec = _SECT[m.group(1).lower()]
            continue
        m = re.fullmatch(r"(/[\w/~]+):\s*([\w/]+)", s)
        if m and sec:
            nodes[cur][sec].append((m.group(1), m.group(2)))
        elif ind == 0:
            cur = sec = None
    nodes["__dup__"] = {"names": [(d, "") for d in dup]}   # type: ignore[assignment]
    return nodes


def _qos(lines: list[str]) -> list[dict[str, Any]]:
    eps: list[dict[str, Any]] = []
    topic = ""
    cur: dict[str, Any] | None = None
    for raw in lines:
        s = raw.strip()
        m = re.search(r"ros2\s+topic\s+info\b.*?(/[\w/~]+)", s) or re.match(r"^Topic(?: name)?:\s*(/[\w/~]+)", s)
        if m:
            topic = m.group(1)
            continue
        m = re.match(r"^Type:\s*(\S+)", s)
        if m and cur is None:
            continue
        if s.startswith("Node name:"):
            cur = {"topic": topic, "node": s.split(":", 1)[1].strip(), "ns": "/", "kind": "", "type": ""}
            eps.append(cur)
            continue
        if cur is None:
            continue
        k, _, v = s.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "node namespace":
            cur["ns"] = v
        elif k == "topic type":
            cur["type"] = v
        elif k == "endpoint type":
            cur["kind"] = "pub" if "PUB" in v.upper() else "sub"
        elif k == "reliability":
            cur["reliability"] = v.upper()
        elif k == "durability":
            cur["durability"] = v.upper()
        elif k.startswith("history"):
            cur["history"] = v
        elif k == "deadline":
            cur["deadline"] = _ns(v)
        elif k == "liveliness":
            cur["liveliness"] = v.upper()
        elif k == "liveliness lease duration":
            cur["lease"] = _ns(v)
    return [e for e in eps if e["kind"]]


def _tf(text: str) -> dict[str, dict[str, Any]]:
    frames: dict[str, dict[str, Any]] = {}
    t = text.replace("\\n", "\n").replace("\\'", "'")
    for m in re.finditer(r'"([^"]+)"\s*->\s*"([^"]+)"\s*\[label="([^"]*)"', t):
        lab = m.group(3)
        rate = re.search(r"Average rate:\s*([\d.]+)", lab)
        last = re.search(r"Most recent transform:\s*([\d.]+)", lab)
        br = re.search(r"Broadcaster:\s*(\S+)", lab)
        frames[m.group(2)] = {"parent": m.group(1), "rate": float(rate.group(1)) if rate else None, "last": float(last.group(1)) if last else None,
                              "broadcaster": br.group(1) if br else ""}
    cur = None
    for raw in t.splitlines():
        s = raw.rstrip()
        m = re.match(r"^(?:frame_yaml=\"?)?([A-Za-z_/][\w/.-]*):\s*$", s.strip()) if not raw.startswith((" ", "\t")) or "frame_yaml" in raw else None
        if m and m.group(1).lower() not in ("subscribers", "publishers", "frames"):
            cur = m.group(1)
            frames.setdefault(cur, {"parent": None, "rate": None, "last": None, "broadcaster": ""})
            continue
        if cur and raw.startswith((" ", "\t")):
            k, _, v = s.strip().partition(":")
            v = v.strip().strip("'\"")
            if k == "parent":
                frames[cur]["parent"] = v
            elif k == "rate":
                try:
                    frames[cur]["rate"] = float(v)
                except ValueError:
                    pass
            elif k == "most_recent_transform":
                try:
                    frames[cur]["last"] = float(v)
                except ValueError:
                    pass
            elif k == "broadcaster":
                frames[cur]["broadcaster"] = v
    return {k: v for k, v in frames.items() if v.get("parent")}


def analyse(text: str) -> dict[str, Any]:
    text = str(text or "")
    if len(text) > 5_000_000:
        raise GraphError("Up to 5 MB of text.")
    lines = text.splitlines()
    nodes = _nodes(lines)
    dup = [d for d, _ in nodes.pop("__dup__")["names"]]   # type: ignore[index]
    eps = _qos(lines)
    tf = _tf(text)
    if not nodes and not eps and not tf:
        raise GraphError("Nothing ROS 2 found. Paste `ros2 node info /<node>` for each node (or a loop over `ros2 node list`), `ros2 topic info -v /<topic>`, or the tf frames from `ros2 run tf2_tools view_frames`.")
    issues: list[dict[str, Any]] = []
    add = lambda sev, area, t, fix="", name="": issues.append({"sev": sev, "area": area, "text": t, "fix": fix, "fn": name})   # noqa: E731
    for d in dup:
        add("bad", "Nodes", f"Two nodes are named {d}: ROS 2 cannot tell them apart - parameters, services and logs mix up.", "Give one a different name or namespace (__node:= / __ns:= or the launch file's name / namespace).", d)
    topics: dict[str, dict[str, Any]] = {}

    def tp(name: str) -> dict[str, Any]:
        return topics.setdefault(name, {"name": name, "pub": [], "sub": [], "types": set()})

    services: dict[str, dict[str, list[str]]] = {}
    for n, d in nodes.items():
        for t, ty in d["pub"]:
            x = tp(t)
            x["pub"].append(n)
            x["types"].add(ty)
        for t, ty in d["sub"]:
            x = tp(t)
            x["sub"].append(n)
            x["types"].add(ty)
        for kind_s, kind_c, label in (("srv", "cli", "service"), ("asrv", "acli", "action")):
            for t, _ in d[kind_s]:
                services.setdefault(label + ":" + t, {"srv": [], "cli": []})["srv"].append(n)
            for t, _ in d[kind_c]:
                services.setdefault(label + ":" + t, {"srv": [], "cli": []})["cli"].append(n)
    for e in eps:
        if not e["topic"]:
            continue
        x = tp(e["topic"])
        full = (e["ns"].rstrip("/") + "/" + e["node"]) if e["node"] else ""
        if full and full not in x[e["kind"]] and e["node"] not in [y.lstrip("/") for y in x[e["kind"]]]:
            x[e["kind"]].append(full)
        if e["type"]:
            x["types"].add(e["type"])
    orphans_sub = [t for t, x in topics.items() if x["sub"] and not x["pub"] and t not in SYSTEM]
    orphans_pub = [t for t, x in topics.items() if x["pub"] and not x["sub"] and t not in SYSTEM]
    for t in orphans_sub:
        near = [p for p in orphans_pub if _edit(p, t) <= 2 or p.rsplit("/", 1)[-1] == t.rsplit("/", 1)[-1]]
        if near:
            add("bad", "Topics", f"{t} is subscribed by {', '.join(topics[t]['sub'][:3])} but nobody publishes it - while {near[0]} is published and nobody listens. Almost certainly the same topic under two names.",
                f"Remap one to the other (remappings=[('{t}', '{near[0]}')] in the launch file) or fix the namespace.", t)
        else:
            add("warn", "Topics", f"{t} is subscribed by {', '.join(topics[t]['sub'][:3])} but nothing publishes it.", "Start the node that publishes it, or check its name and namespace.", t)
    for t in orphans_pub:
        if not any(t in i["text"] for i in issues):
            add("info", "Topics", f"{t} is published by {', '.join(topics[t]['pub'][:3])} and nobody listens (fine for data you record or view).", "", t)
    for t, x in topics.items():
        if len(x["types"]) > 1:
            add("bad", "Types", f"{t} is used with different message types ({', '.join(sorted(x['types']))}) - those endpoints never connect.", "Use one message type for the topic.", t)
    for k, v in services.items():
        kind, name = k.split(":", 1)
        if v["cli"] and not v["srv"] and not name.endswith(("/describe_parameters", "/get_parameters", "/set_parameters", "/list_parameters", "/get_parameter_types", "/set_parameters_atomically", "/get_type_description")):
            add("warn", "Services", f"{', '.join(v['cli'][:3])} call{'s' if len(v['cli']) == 1 else ''} the {kind} {name}, but no node serves it.", "Start the server, or check the name.", name)
    qos_rows = []
    by_topic: dict[str, list[dict[str, Any]]] = {}
    for e in eps:
        by_topic.setdefault(e["topic"], []).append(e)
    for t, es in by_topic.items():
        pubs, subs = [e for e in es if e["kind"] == "pub"], [e for e in es if e["kind"] == "sub"]
        for s_ in subs:
            for p_ in pubs:
                why = []
                if REL.get(p_.get("reliability", ""), 1) < REL.get(s_.get("reliability", ""), 0):
                    why.append("the subscriber asks for RELIABLE and the publisher offers BEST_EFFORT")
                if DUR.get(p_.get("durability", ""), 1) < DUR.get(s_.get("durability", ""), 0):
                    why.append("the subscriber asks for TRANSIENT_LOCAL (late joiners get old messages) and the publisher is VOLATILE")
                if LIV.get(p_.get("liveliness", ""), 1) < LIV.get(s_.get("liveliness", ""), 0):
                    why.append("the subscriber asks for MANUAL_BY_TOPIC liveliness and the publisher offers AUTOMATIC")
                pd, sd = p_.get("deadline"), s_.get("deadline")
                if sd is not None and (pd is None or pd > sd):
                    why.append("the subscriber's deadline is shorter than the publisher promises")
                pl, sl = p_.get("lease"), s_.get("lease")
                if sl is not None and (pl is None or pl > sl):
                    why.append("the subscriber's liveliness lease is shorter than the publisher's")
                if why:
                    add("bad", "QoS", f"{t}: {s_['node']} never receives from {p_['node']} - {'; '.join(why)}.",
                        "Match the profiles - for sensor streams make the subscriber BEST_EFFORT (rclcpp::SensorDataQoS() / qos_profile_sensor_data).", t)
                qos_rows.append({"topic": t, "pub": p_["node"], "sub": s_["node"], "ok": not why, "why": why,
                                 "pub_qos": " · ".join(x for x in (p_.get("reliability"), p_.get("durability"), p_.get("history")) if x),
                                 "sub_qos": " · ".join(x for x in (s_.get("reliability"), s_.get("durability"), s_.get("history")) if x)})
    tf_rows, tf_roots = [], []
    if tf:
        parents = {k: v["parent"] for k, v in tf.items()}
        allf = set(parents) | set(parents.values())
        tf_roots = sorted(f for f in allf if f not in parents)
        for f in allf:
            if f.startswith("/"):
                add("warn", "tf", f"Frame '{f}' starts with a slash - tf2 frame ids must not.", "Drop the leading slash.", f)
        for f in parents:
            seen, c = set(), f
            while c in parents:
                if c in seen:
                    add("bad", "tf", f"The tf tree has a loop through {f}.", "Each frame has one parent and the chain ends at the root.", f)
                    break
                seen.add(c)
                c = parents[c]
        if len(tf_roots) > 1:
            add("bad", "tf", f"The tf tree is split into {len(tf_roots)} trees (roots: {', '.join(tf_roots[:6])}) - nothing can be looked up between them.",
                "Publish the missing transform (often map -> odom from localisation, or odom -> base_link from odometry).")
        if "base_link" in allf and "odom" in allf and parents.get("base_link") not in ("odom", "base_footprint", None) and parents.get("base_footprint") != "odom":
            add("warn", "tf", f"base_link's parent is {parents.get('base_link')}, not odom - REP 105 expects map -> odom -> base_link.", "Let odometry publish odom -> base_link and localisation map -> odom.", "base_link")
        if "map" in parents.get("base_link", "") and "odom" in allf:
            pass
        lasts = [v["last"] for v in tf.values() if v.get("last") and (v.get("rate") or 0) < 9999]
        newest = max(lasts) if lasts else None
        for f, v in sorted(tf.items()):
            rate = v.get("rate")
            static = rate is not None and rate >= 9999
            stale = newest is not None and v.get("last") and not static and newest - v["last"] > 1.0
            if stale:
                add("bad", "tf", f"{v['parent']} -> {f} stopped: its last transform is {newest - v['last']:.1f} s older than the newest.", f"Check {v.get('broadcaster') or 'the node that publishes it'}.", f)
            elif rate is not None and not static and rate < 10 and f in ("base_link", "base_footprint", "odom"):
                add("warn", "tf", f"{v['parent']} -> {f} is published at {rate:g} Hz - navigation usually wants 20 Hz or more for the robot's own pose.", "", f)
            tf_rows.append({"child": f, "parent": v["parent"], "rate": rate, "static": static, "broadcaster": v.get("broadcaster", ""), "stale": bool(stale)})
    trows = []
    for t, x in sorted(topics.items()):
        trows.append({"name": t, "types": sorted(x["types"]), "pub": x["pub"], "sub": x["sub"], "system": t in SYSTEM,
                      "state": "bad" if len(x["types"]) > 1 or any(i["fn"] == t and i["sev"] == "bad" for i in issues) else "warn" if (x["sub"] and not x["pub"]) else ""})
    out = {"nodes": [{"name": n, "pub": len(d["pub"]), "sub": len(d["sub"]), "srv": len(d["srv"]), "cli": len(d["cli"]), "asrv": len(d["asrv"]), "acli": len(d["acli"]),
                      "pubs": [t for t, _ in d["pub"] if t not in SYSTEM], "subs": [t for t, _ in d["sub"] if t not in SYSTEM]} for n, d in sorted(nodes.items())],
           "topics": trows, "qos": qos_rows, "tf": tf_rows, "tf_roots": tf_roots,
           "services": [{"name": k.split(":", 1)[1], "kind": k.split(":", 1)[0], "srv": v["srv"], "cli": v["cli"]} for k, v in sorted(services.items())
                        if not re.search(r"/(describe|get|set|list)_parameters|/get_parameter_types|/set_parameters_atomically|/get_type_description$", k)],
           "issues": issues}
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    b = out["counts"]["bad"]
    parts = [f"{len(nodes)} node{'s' if len(nodes) != 1 else ''}" if nodes else "", f"{len([t for t in topics if t not in SYSTEM])} topics" if topics else "",
             f"{len(set(r['child'] for r in tf_rows) | set(tf_roots))} tf frames" if tf_rows else ""]
    out["verdict"] = ", ".join(p for p in parts if p) + (f" - {b} thing{'s' if b > 1 else ''} that stop{'s' if b == 1 else ''} data flowing" if b else " - every link connects")
    out["note"] = ("Read from the text you pasted, at the moment it was printed: a node that was not running then is missing here. QoS is "
                   "checked only for topics whose `ros2 topic info -v` you included.")
    return out
