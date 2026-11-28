"""Replication and quorums worked out in code: N replicas, R / W quorums -> whether every read overlaps the last write, how many
failures reads and writes survive; consensus (Raft / Paxos majority) -> votes needed and failures tolerated; placement across zones
or regions -> whether losing one zone still leaves a majority. Pure arithmetic: the rules are the textbook ones and named."""
from __future__ import annotations

from itertools import combinations
from typing import Any


class QuorumError(ValueError):
    pass


def _i(v: Any, lo: int, hi: int, what: str) -> int:
    try:
        x = int(v)
    except (TypeError, ValueError):
        raise QuorumError(f"{what}: a whole number from {lo} to {hi}.")
    if not lo <= x <= hi:
        raise QuorumError(f"{what}: a whole number from {lo} to {hi}.")
    return x


def analyse(n: Any, r: Any = None, w: Any = None, zones: list[Any] | None = None, mode: str = "quorum") -> dict[str, Any]:
    n = _i(n, 1, 99, "Replicas")
    maj = n // 2 + 1
    out: dict[str, Any] = {"ok": True, "n": n, "mode": mode, "majority": maj, "issues": [], "notes": []}
    if mode == "consensus":
        f = (n - 1) // 2
        out.update(write_quorum=maj, read_quorum=maj, tolerates=f, overlap=True)
        if n % 2 == 0:
            out["issues"].append({"sev": "warn", "say": f"{n} voters tolerate {f} failure(s) - the same as {n - 1}",
                                  "fix": f"An even number adds a voter without adding tolerance: use {n - 1} or {n + 1}."})
        if n == 1:
            out["issues"].append({"sev": "bad", "say": "One voter tolerates no failure", "fix": "Use 3 or 5 voters."})
        out["notes"].append(f"Raft / Paxos: a leader needs {maj} of {n} votes; the cluster keeps working with up to {f} member(s) down.")
        out["verdict"] = f"{n} voters: majority {maj}, keeps working with {f} down."
    else:
        r = _i(r if r not in (None, "") else maj, 1, n, "Read quorum R")
        w = _i(w if w not in (None, "") else maj, 1, n, "Write quorum W")
        overlap = r + w > n
        out.update(read_quorum=r, write_quorum=w, overlap=overlap, read_tolerates=n - r, write_tolerates=n - w, two_writes_overlap=2 * w > n)
        if not overlap:
            out["issues"].append({"sev": "bad", "say": f"R + W = {r + w} is not more than N = {n}: a read can miss the last acknowledged write",
                                  "fix": f"Make R + W > N, e.g. R = {n - w + 1} with W = {w}."})
        if not 2 * w > n:
            out["issues"].append({"sev": "warn", "say": f"Two writes can both succeed on different replicas (2W = {2 * w} <= N = {n})",
                                  "fix": "Concurrent writes need versioning (vector clocks) or conflict resolution, or W > N/2."})
        if overlap:
            out["notes"].append("Overlap alone is not linearizability: a read that races a write in progress can see the new value and the next read "
                                "the old one, unless reads write back what they return (read repair before answering) - try it in the simulator.")
        if w == n:
            out["issues"].append({"sev": "warn", "say": "W = N: one replica down stops every write", "fix": "Lower W and raise R to keep R + W > N."})
        if r == n:
            out["issues"].append({"sev": "warn", "say": "R = N: one replica down stops every read", "fix": "Lower R and raise W to keep R + W > N."})
        out["verdict"] = (f"N={n}, R={r}, W={w}: " + ("every read meets the last acknowledged write" if overlap else "reads can be stale") +
                          f"; reads survive {n - r} down, writes survive {n - w} down.")
    if zones:
        zs = [(str(z.get("name") or f"zone {i + 1}")[:40], _i(z.get("replicas"), 0, 99, "Replicas in a zone")) for i, z in enumerate(zones) if isinstance(z, dict)]
        if sum(c for _, c in zs) != n:
            raise QuorumError(f"The zones hold {sum(c for _, c in zs)} replicas, not {n}.")
        need = out["write_quorum"]
        rows = []
        for name, c in zs:
            left = n - c
            rows.append({"zone": name, "replicas": c, "left": left, "writes": left >= need, "reads": left >= out["read_quorum"]})
        out["zones"] = rows
        bad = [z for z in rows if not z["writes"]]
        if bad:
            out["issues"].append({"sev": "bad", "say": f"Losing {bad[0]['zone']} leaves {bad[0]['left']} of {n}: writes stop",
                                  "fix": "Spread the replicas so no one zone holds as many as the quorum's slack - e.g. 2 / 2 / 1 for five across three zones."})
        two = []
        for a, b in combinations(zs, 2):
            left = n - a[1] - b[1]
            if left >= need:
                two.append(f"{a[0]} + {b[0]}")
        out["survives_two"] = two
        if len(zs) == 2:
            out["issues"].append({"sev": "warn", "say": "Two zones: losing the bigger one always loses the majority",
                                  "fix": "Use three zones (a small witness / tie-breaker in the third is enough for consensus)."})
    order = {"bad": 0, "warn": 1, "info": 2}
    out["issues"].sort(key=lambda x: order[x["sev"]])
    return out
