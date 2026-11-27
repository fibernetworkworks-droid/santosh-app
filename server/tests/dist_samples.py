"""Sample inputs for the Distributed Systems Engineer desk tests (made up)."""

TLC_FAIL = """TLC2 Version 2.18 of Day Month 20?? (rev: 4d3d2bc)
Running breadth-first search Model-Checking with fp 21 and seed -4711021 with 2 workers on 4 cores with 1752MB heap and 64MB offheap memory [pid: 1234] (Linux 6.1 amd64, Eclipse Adoptium 17.0.9 x86_64, MSBDiskFPSet, DiskStateQueue).
Parsing file /work/specs/FencedLeader.tla
Semantic processing of module FencedLeader
Starting... (2026-11-27 10:00:00)
Computing initial states...
Finished computing initial states: 1 distinct state generated at 2026-11-27 10:00:00.
Error: Invariant NoStaleWrite is violated.
Error: The behavior up to this point is:
State 1: <Initial predicate>
/\\ epoch = 0
/\\ believes = (a :> 0 @@ b :> 0)
/\\ storeEpoch = 0
/\\ writes = <<>>

State 2: <Acquire line 15, col 15 to line 18, col 49 of module FencedLeader>
/\\ epoch = 1
/\\ believes = (a :> 1 @@ b :> 0)
/\\ storeEpoch = 0
/\\ writes = <<>>

State 3: <Acquire line 15, col 15 to line 18, col 49 of module FencedLeader>
/\\ epoch = 2
/\\ believes = (a :> 1 @@ b :> 2)
/\\ storeEpoch = 0
/\\ writes = <<>>

State 4: <Write line 20, col 13 to line 27, col 44 of module FencedLeader>
/\\ epoch = 2
/\\ believes = (a :> 1 @@ b :> 2)
/\\ storeEpoch = 0
/\\ writes = <<2>>

State 5: <Write line 20, col 13 to line 27, col 44 of module FencedLeader>
/\\ epoch = 2
/\\ believes = (a :> 1 @@ b :> 2)
/\\ storeEpoch = 0
/\\ writes = <<2, 1>>

12 states generated, 9 distinct states found, 3 states left on queue.
The depth of the complete state graph search is 5.
Finished in 01s at (2026-11-27 10:00:01)
"""

TLC_PASS = """TLC2 Version 2.18 of Day Month 20?? (rev: 4d3d2bc)
Running breadth-first search Model-Checking with fp 4 and seed 123 with 2 workers on 4 cores with 1752MB heap and 64MB offheap memory [pid: 1235].
Starting... (2026-11-27 10:01:00)
Computing initial states...
Finished computing initial states: 1 distinct state generated at 2026-11-27 10:01:00.
Model checking completed. No error has been found.
  Estimates of the probability that TLC did not check all reachable states
  because two distinct states had the same fingerprint:
  calculated (optimistic):  val = 1.1E-15
1,204 states generated, 288 distinct states found, 0 states left on queue.
The depth of the complete state graph search is 11.
Finished in 01s at (2026-11-27 10:01:01)
"""

HISTORY_BAD = """0 invoke write 1
0 ok write 1
0 invoke write 2
0 ok write 2
1 invoke read
1 ok read 1
"""

HISTORY_JSON = """[{"process": 0, "type": "invoke", "f": "write", "value": 3},
 {"process": 0, "type": "info", "f": "write", "value": 3},
 {"process": 1, "type": "invoke", "f": "read", "value": null},
 {"process": 1, "type": "ok", "f": "read", "value": 3},
 {"process": 1, "type": "invoke", "f": "cas", "value": [3, 4]},
 {"process": 1, "type": "ok", "f": "cas", "value": [3, 4]},
 {"process": 2, "type": "invoke", "f": "read", "value": null, "key": "x"},
 {"process": 2, "type": "ok", "f": "read", "value": null, "key": "x"}]"""
