"""Formal specs: three TLA+ starter specs she can model-check (an idempotent consumer, two-phase commit, a fenced leader lease) -
each with a switch that shows the bug and the fix; the TLC output read back (no error / which invariant broke / the step-by-step
trace / deadlock, states found, depth); and a GitHub Actions workflow that runs TLC on HER specs in HER CI. TLC itself never runs
on Hoola's server: the specs and the workflow are text she adds to her repository. Pasted output is DATA."""
from __future__ import annotations

import re
from typing import Any

TLA_VERSION = "v1.8.0"
_SAFE = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")

TEMPLATES: dict[str, dict[str, Any]] = {
    "idempotent": {
        "title": "Idempotent consumer", "module": "IdempotentConsumer",
        "about": "A broker delivers each message at least once (the acknowledgement can be lost, so it delivers again). The invariant: each "
                 "message's effect is applied at most once. Dedup = FALSE should break it in two steps; Dedup = TRUE (remember what was "
                 "processed) should hold.",
        "switch": "Dedup",
        "tla": r"""---------------------------- MODULE IdempotentConsumer ----------------------------
EXTENDS Naturals
CONSTANTS Msgs, Dedup
VARIABLES inflight, applied, seen
vars == <<inflight, applied, seen>>

Init == /\ inflight = Msgs
        /\ applied = [m \in Msgs |-> 0]
        /\ seen = {}

\* The broker hands m to the consumer; until m is acknowledged it may hand it over again.
Deliver(m) == /\ m \in inflight
              /\ applied[m] < 3
              /\ IF Dedup /\ m \in seen
                    THEN applied' = applied
                    ELSE applied' = [applied EXCEPT ![m] = @ + 1]
              /\ seen' = seen \cup {m}
              /\ UNCHANGED inflight

Ack(m) == /\ m \in inflight /\ m \in seen
          /\ inflight' = inflight \ {m}
          /\ UNCHANGED <<applied, seen>>

Done == inflight = {} /\ UNCHANGED vars

Next == (\E m \in Msgs : Deliver(m) \/ Ack(m)) \/ Done
Spec == Init /\ [][Next]_vars

AppliedAtMostOnce == \A m \in Msgs : applied[m] <= 1
=============================================================================
""",
        "cfg": "CONSTANTS\n    Msgs = {m1, m2}\n    Dedup = {switch}\nSPECIFICATION Spec\nINVARIANT AppliedAtMostOnce\n",
    },
    "twophase": {
        "title": "Two-phase commit", "module": "TwoPhaseCommit",
        "about": "Resource managers prepare; the coordinator commits only when every one is prepared, else aborts (after Lamport's TwoPhase). "
                 "The invariant: no manager commits while another aborts. WaitForAll = FALSE (commit once any is prepared) should break it.",
        "switch": "WaitForAll",
        "tla": r"""---------------------------- MODULE TwoPhaseCommit ----------------------------
CONSTANTS RM, WaitForAll
VARIABLES rmState, tmState, tmPrepared, msgs
vars == <<rmState, tmState, tmPrepared, msgs>>

Init == /\ rmState = [r \in RM |-> "working"]
        /\ tmState = "init"
        /\ tmPrepared = {}
        /\ msgs = {}

TMRcvPrepared(r) == /\ tmState = "init"
                    /\ [type |-> "Prepared", rm |-> r] \in msgs
                    /\ tmPrepared' = tmPrepared \cup {r}
                    /\ UNCHANGED <<rmState, tmState, msgs>>

TMCommit == /\ tmState = "init"
            /\ IF WaitForAll THEN tmPrepared = RM ELSE tmPrepared # {}
            /\ tmState' = "committed"
            /\ msgs' = msgs \cup {[type |-> "Commit"]}
            /\ UNCHANGED <<rmState, tmPrepared>>

TMAbort == /\ tmState = "init"
           /\ tmState' = "aborted"
           /\ msgs' = msgs \cup {[type |-> "Abort"]}
           /\ UNCHANGED <<rmState, tmPrepared>>

RMPrepare(r) == /\ rmState[r] = "working"
                /\ rmState' = [rmState EXCEPT ![r] = "prepared"]
                /\ msgs' = msgs \cup {[type |-> "Prepared", rm |-> r]}
                /\ UNCHANGED <<tmState, tmPrepared>>

RMChooseToAbort(r) == /\ rmState[r] = "working"
                      /\ rmState' = [rmState EXCEPT ![r] = "aborted"]
                      /\ UNCHANGED <<tmState, tmPrepared, msgs>>

RMRcvCommitMsg(r) == /\ [type |-> "Commit"] \in msgs
                     /\ rmState' = [rmState EXCEPT ![r] = "committed"]
                     /\ UNCHANGED <<tmState, tmPrepared, msgs>>

RMRcvAbortMsg(r) == /\ [type |-> "Abort"] \in msgs
                    /\ rmState' = [rmState EXCEPT ![r] = "aborted"]
                    /\ UNCHANGED <<tmState, tmPrepared, msgs>>

Finished == /\ tmState # "init"
            /\ \A r \in RM : rmState[r] \in {"committed", "aborted"}
            /\ UNCHANGED vars

Next == \/ TMCommit \/ TMAbort \/ Finished
        \/ \E r \in RM : TMRcvPrepared(r) \/ RMPrepare(r) \/ RMChooseToAbort(r)
                         \/ RMRcvCommitMsg(r) \/ RMRcvAbortMsg(r)
Spec == Init /\ [][Next]_vars

Consistent == \A r1, r2 \in RM : ~ (rmState[r1] = "aborted" /\ rmState[r2] = "committed")
=============================================================================
""",
        "cfg": "CONSTANTS\n    RM = {r1, r2, r3}\n    WaitForAll = {switch}\nSPECIFICATION Spec\nINVARIANT Consistent\n",
    },
    "fencing": {
        "title": "Leader lease with fencing tokens", "module": "FencedLeader",
        "about": "A lock service hands out leases with an increasing number. An old leader that was paused still believes it leads. The "
                 "invariant: storage never accepts a write from an older lease after one from a newer lease. Fencing = FALSE should break it; "
                 "Fencing = TRUE (storage rejects a token older than the newest it has seen) should hold.",
        "switch": "Fencing",
        "tla": r"""---------------------------- MODULE FencedLeader ----------------------------
EXTENDS Naturals, Sequences
CONSTANTS Nodes, Fencing, MaxEpoch
VARIABLES epoch, believes, storeEpoch, writes
vars == <<epoch, believes, storeEpoch, writes>>

Init == /\ epoch = 0
        /\ believes = [n \in Nodes |-> 0]
        /\ storeEpoch = 0
        /\ writes = <<>>

\* n gets the next lease; the old holder is not told (it may be paused) and keeps its belief.
Acquire(n) == /\ epoch < MaxEpoch
              /\ epoch' = epoch + 1
              /\ believes' = [believes EXCEPT ![n] = epoch + 1]
              /\ UNCHANGED <<storeEpoch, writes>>

Write(n) == /\ believes[n] > 0
            /\ Len(writes) < 4
            /\ IF Fencing
                  THEN /\ believes[n] >= storeEpoch
                       /\ storeEpoch' = believes[n]
                  ELSE storeEpoch' = storeEpoch
            /\ writes' = Append(writes, believes[n])
            /\ UNCHANGED <<epoch, believes>>

Idle == UNCHANGED vars

Next == (\E n \in Nodes : Acquire(n) \/ Write(n)) \/ Idle
Spec == Init /\ [][Next]_vars

NoStaleWrite == \A i, j \in 1..Len(writes) : i < j => writes[i] <= writes[j]
=============================================================================
""",
        "cfg": "CONSTANTS\n    Nodes = {a, b}\n    Fencing = {switch}\n    MaxEpoch = 3\nSPECIFICATION Spec\nINVARIANT NoStaleWrite\n",
    },
}


def template(key: str, fixed: bool = True) -> dict[str, Any]:
    t = TEMPLATES.get(key)
    if t is None:
        raise ValueError("Spec: " + " | ".join(TEMPLATES))
    cfg = t["cfg"].replace("{switch}", "TRUE" if fixed else "FALSE")
    return {"key": key, "title": t["title"], "about": t["about"], "module": t["module"], "switch": t["switch"], "fixed": fixed,
            "tla": t["tla"], "cfg": cfg, "files": {f"{t['module']}.tla": t["tla"], f"{t['module']}.cfg": cfg}}


def _vars(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    cur = None
    for ln in block.splitlines():
        m = re.match(r"\s*/\\\s*(\w+)\s*=\s*(.*)$", ln)
        if m:
            cur = m[1]
            out[cur] = m[2].strip()
        elif cur and ln.strip():
            out[cur] += " " + ln.strip()
    if not out:
        m = re.match(r"\s*(\w+)\s*=\s*(.*)$", block.strip(), re.S)
        if m:
            out[m[1]] = " ".join(m[2].split())
    return out


def read_output(text: str) -> dict[str, Any]:
    t = str(text or "")[:2_000_000]
    if not re.search(r"\bTLC\b|Model checking completed|states generated|Error: ", t):
        return {"ok": False, "error": "This does not look like TLC output. Paste what `java -cp tla2tools.jar tlc2.TLC ...` printed."}
    out: dict[str, Any] = {"ok": True, "result": "unknown", "invariant": "", "trace": [], "error": ""}
    m = re.search(r"([\d,]+) states generated(?: \([^)]*\))?, ([\d,]+) distinct states found(?: \([^)]*\))?, ([\d,]+) states left on queue", t)
    if m:
        out["generated"], out["distinct"], out["left"] = (int(x.replace(",", "")) for x in m.groups())
    m = re.search(r"The depth of the complete state graph search is (\d+)", t)
    out["depth"] = int(m[1]) if m else None
    m = re.search(r"Finished in (\S+)", t)
    out["time"] = m[1] if m else ""
    if "Model checking completed. No error has been found." in t:
        out["result"] = "pass"
    elif (m := re.search(r"Error: Invariant (\w+) is violated", t)):
        out["result"], out["invariant"] = "invariant", m[1]
    elif re.search(r"Error: (?:Action property .* is violated|Temporal properties were violated)", t):
        out["result"] = "property"
    elif "Error: Deadlock reached" in t:
        out["result"] = "deadlock"
    elif (m := re.search(r"Error: (.+)", t)):
        out["result"], out["error"] = "error", m[1].strip()[:400]
    parts = re.split(r"^State (\d+): ?<?([^>\n]*)>?\s*$", t, flags=re.M)
    if len(parts) > 3:
        for i in range(1, len(parts) - 1, 3):
            body = re.split(r"^(?:\d+ states generated|The number of states|Finished|Error:|State \d+:)", parts[i + 2], flags=re.M)[0]
            out["trace"].append({"n": int(parts[i]), "action": parts[i + 1].split(" line")[0].strip(), "vars": _vars(body)})
    out["trace"] = out["trace"][:200]
    for k, st in enumerate(out["trace"]):
        prev = out["trace"][k - 1]["vars"] if k else {}
        st["changed"] = [v for v, x in st["vars"].items() if prev.get(v) != x] if k else []
    out["verdict"] = {"pass": "No error found" + (f" in {out['distinct']:,} distinct states." if out.get("distinct") else "."),
                      "invariant": f"Invariant {out['invariant']} is violated - the trace shows how in {len(out['trace'])} step(s).",
                      "property": "A temporal property is violated - read the trace.",
                      "deadlock": f"Deadlock: a state with no next step ({len(out['trace'])} step(s) to reach it). If stopping is fine, add an "
                                  "idle step or run TLC with -deadlock.",
                      "error": "TLC stopped with an error: " + out["error"],
                      "unknown": "TLC did not finish - no result line found."}[out["result"]]
    return out


def workflow(specs_dir: str = "specs", version: str = TLA_VERSION, branch: str = "main") -> dict[str, Any]:
    for v, what in ((specs_dir, "Specs folder"), (branch, "Branch")):
        if not _SAFE.match(v or "") or ".." in v:
            raise ValueError(f"{what}: letters, digits and ./_- only.")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version or ""):
        raise ValueError("TLA+ tools version: like v1.8.0.")
    yml = f"""# Made by Hoola: model-checks every TLA+ spec in {specs_dir}/ that has a .cfg next to it.
# TLC runs here, in your CI - never on Hoola's server.
name: tla-check
on:
  push:
    branches: [{branch}]
    paths: ['{specs_dir}/**']
  pull_request:
    paths: ['{specs_dir}/**']
  workflow_dispatch:
jobs:
  tlc:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - name: Get TLA+ tools {version}
        run: curl -fsSL -o /tmp/tla2tools.jar https://github.com/tlaplus/tlaplus/releases/download/{version}/tla2tools.jar
      - name: Model-check each spec
        working-directory: {specs_dir}
        run: |
          set -u
          fail=0
          found=0
          for cfg in *.cfg; do
            [ -e "$cfg" ] || continue
            found=1
            spec="${{cfg%.cfg}}.tla"
            echo "::group::$spec"
            if ! java -XX:+UseParallelGC -cp /tmp/tla2tools.jar tlc2.TLC -workers auto -config "$cfg" "$spec"; then
              echo "::error file={specs_dir}/$spec::TLC found a problem in $spec"
              fail=1
            fi
            echo "::endgroup::"
          done
          [ "$found" = 1 ] || {{ echo "::error::No .cfg files in {specs_dir}/"; exit 1; }}
          exit $fail
"""
    return {"path": ".github/workflows/tla-check.yml", "yaml": yml,
            "steps": [f"Put each spec and its .cfg in {specs_dir}/", "Add this file to .github/workflows/", "Push: every change to a spec is model-checked"]}
