"""Is a history of reads / writes / compare-and-sets linearizable? The check Jepsen's Knossos makes, done here in code with the
Wing-Gong search (Lowe's memoised version): every completed operation must appear to take effect at one instant between its call
and its return, in an order a single register could have produced. An operation that timed out ('info') may or may not have happened.
Each key is checked on its own (linearizability is compositional). The history is DATA.

Formats read: a JSON list of {process, type: invoke|ok|fail|info, f: read|write|cas, value, key?}; Jepsen EDN lines
({:type :invoke, :f :write, :value 3, :process 0}); or plain lines '0 invoke write 3' / '0 ok read 3' / '1 invoke cas [1 2]'."""
from __future__ import annotations

import json
import re
from typing import Any

MAX_OPS = 400          # per key: the search is exponential in the worst case
MAX_EVENTS = 40_000
STEPS = 400_000


class HistoryError(ValueError):
    pass


def _val(x: Any) -> Any:
    if isinstance(x, list):
        return [_val(v) for v in x]
    if isinstance(x, str):
        s = x.strip()
        if s in ("nil", "null", "None", ""):
            return None
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        m = re.fullmatch(r"\[\s*(\S+)\s+(\S+)\s*\]", s)
        if m:
            return [_val(m[1]), _val(m[2])]
        return s.strip('"')
    return x


def parse(text: str) -> list[dict[str, Any]]:
    t = str(text or "").strip()
    if not t:
        raise HistoryError("Paste the history first.")
    evs: list[dict[str, Any]] = []
    if t.startswith("["):
        try:
            raw = json.loads(t)
        except ValueError as e:
            raise HistoryError(f"Not valid JSON: {e}.")
        for x in raw:
            if isinstance(x, dict):
                evs.append({"process": x.get("process"), "type": str(x.get("type", "")).lstrip(":"), "f": str(x.get("f", "")).lstrip(":"),
                            "value": _val(x.get("value")), "key": x.get("key")})
    else:
        for ln in t.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith(("#", ";")):
                continue
            if ln.startswith("{"):
                g = lambda k: (re.search(r":" + k + r"\s+(\[[^\]]*\]|\"[^\"]*\"|[^\s,}]+)", ln) or [None, None])[1]   # noqa: E731
                evs.append({"process": _val(g("process")), "type": (g("type") or "").lstrip(":"), "f": (g("f") or "").lstrip(":"),
                            "value": _val(g("value")), "key": _val(g("key")) if g("key") else None})
            else:
                m = re.match(r"(\S+)\s+(invoke|ok|fail|info)\s+(read|write|cas)\s*(.*)$", ln, re.I)
                if not m:
                    raise HistoryError(f"Could not read this line: {ln[:80]}")
                v = m[4].strip()
                key = None
                km = re.match(r"(.*?)\s+key=(\S+)$", v)
                if km:
                    v, key = km[1], km[2]
                evs.append({"process": _val(m[1]), "type": m[2].lower(), "f": m[3].lower(), "value": _val(v) if v else None, "key": key})
    if len(evs) > MAX_EVENTS:
        raise HistoryError(f"At most {MAX_EVENTS:,} events.")
    for i, e in enumerate(evs):
        if e["type"] not in ("invoke", "ok", "fail", "info") or e["f"] not in ("read", "write", "cas"):
            raise HistoryError(f"Event {i + 1}: type must be invoke / ok / fail / info and f read / write / cas.")
        e["i"] = i
    return evs


def ops_of(evs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair each invoke with the next completion of the same process."""
    open_: dict[Any, dict[str, Any]] = {}
    ops: list[dict[str, Any]] = []
    for e in evs:
        p = e["process"]
        if e["type"] == "invoke":
            if p in open_:
                raise HistoryError(f"Process {p} invoked again before its last operation completed (event {e['i'] + 1}).")
            open_[p] = e
            continue
        inv = open_.pop(p, None)
        if inv is None:
            raise HistoryError(f"Event {e['i'] + 1}: process {p} completed an operation it never invoked.")
        if e["type"] == "fail":
            continue
        f = inv["f"]
        val = e["value"] if (f == "read" and e["type"] == "ok") else inv["value"]
        if f == "read" and e["type"] == "info":
            continue                    # a read that never answered constrains nothing
        if f == "cas" and not (isinstance(val, list) and len(val) == 2):
            raise HistoryError(f"Event {inv['i'] + 1}: a cas value must be [expected new].")
        ops.append({"id": len(ops), "process": p, "f": f, "value": val, "key": inv.get("key") if inv.get("key") is not None else e.get("key"),
                    "call": inv["i"], "ret": e["i"] if e["type"] == "ok" else None, "info": e["type"] == "info"})
    for p, inv in open_.items():        # never completed = like info
        if inv["f"] != "read":
            ops.append({"id": len(ops), "process": p, "f": inv["f"], "value": inv["value"], "key": inv.get("key"), "call": inv["i"], "ret": None, "info": True})
    return ops


def _step(state: Any, op: dict[str, Any]) -> tuple[bool, Any]:
    f, v = op["f"], op["value"]
    if f == "write":
        return True, v
    if f == "read":
        return v == state, state
    exp, new = v
    return (state == exp), (new if state == exp else state)


def check_key(ops: list[dict[str, Any]], init: Any = None) -> dict[str, Any]:
    if len(ops) > MAX_OPS:
        return {"result": "unknown", "why": f"{len(ops)} operations on one key - more than the {MAX_OPS} this search checks."}
    INF = float("inf")
    n = len(ops)
    must = 0
    for k, o in enumerate(ops):
        if not o["info"]:
            must |= 1 << k
    order = sorted(range(n), key=lambda k: ops[k]["call"])
    ret = [ops[k]["ret"] if ops[k]["ret"] is not None else INF for k in range(n)]
    seen: set[tuple[int, Any]] = set()
    best = {"done": 0, "n": -1}
    steps = 0

    def key_of(state):
        return json.dumps(state, sort_keys=True, default=str)

    stack = [(0, init)]
    while stack:
        done, state = stack.pop()
        if done & must == must:
            return {"result": "ok"}
        sk = (done, key_of(state))
        if sk in seen:
            continue
        seen.add(sk)
        steps += 1
        if steps > STEPS:
            return {"result": "unknown", "why": "The search took too long - check a shorter part of the history."}
        cnt = bin(done & must).count("1")
        if cnt > best["n"]:
            best = {"done": done, "n": cnt, "state": state}
        # the earliest return among operations not yet placed: only operations called before it may go next
        horizon = min((ret[k] for k in range(n) if not done >> k & 1), default=INF)
        for k in order:
            if done >> k & 1:
                continue
            if ops[k]["call"] > horizon:
                break
            ok, nxt = _step(state, ops[k])
            if ok:
                stack.append((done | 1 << k, nxt))
    # not linearizable: explain with the furthest point reached
    done, state = best["done"], best.get("state", init)
    left = [ops[k] for k in range(n) if not done >> k & 1 and not ops[k]["info"]]
    culprit = min(left, key=lambda o: o["ret"]) if left else None
    return {"result": "fail", "placed": best["n"], "state": state, "op": culprit}


def check(text: str, init: Any = None) -> dict[str, Any]:
    evs = parse(text)
    ops = ops_of(evs)
    if not ops:
        raise HistoryError("No completed operations in the history.")
    keys: dict[Any, list[dict[str, Any]]] = {}
    for o in ops:
        keys.setdefault(o["key"], []).append(o)
    res = []
    for k, lst in keys.items():
        r = check_key(lst, init)
        r["key"] = k
        r["ops"] = len(lst)
        if r["result"] == "fail" and r.get("op"):
            o = r["op"]
            what = f"cas {o['value'][0]!r} -> {o['value'][1]!r}" if o["f"] == "cas" else f"{o['f']} {o['value']!r}"
            r["say"] = (f"Process {o['process']}'s {what} (events {o['call'] + 1}-{o['ret'] + 1}) cannot be explained: after {r['placed']} operation(s) "
                        f"fit, the register can only hold {r['state']!r} by then.")
        res.append(r)
    bad = [r for r in res if r["result"] == "fail"]
    unk = [r for r in res if r["result"] == "unknown"]
    tl = [{k: o[k] for k in ("id", "process", "f", "value", "key", "call", "ret", "info")} for o in ops[:600]]
    culprits = {(r["op"]["id"]) for r in bad if r.get("op")}
    for o in tl:
        o["bad"] = o["id"] in culprits
    return {"ok": True, "events": len(evs), "ops": len(ops), "processes": len({o["process"] for o in ops}), "keys": res,
            "linearizable": not bad and not unk, "result": "fail" if bad else "unknown" if unk else "ok", "timeline": tl,
            "info_ops": sum(1 for o in ops if o["info"]),
            "verdict": (f"Not linearizable: {bad[0]['say']}" if bad else
                        f"Could not decide: {unk[0]['why']}" if unk else
                        f"Linearizable: all {len(ops)} operation(s) fit one order a single register could produce" +
                        (f" ({sum(1 for o in ops if o['info'])} timed-out operation(s) may or may not have happened)." if any(o['info'] for o in ops) else "."))}
