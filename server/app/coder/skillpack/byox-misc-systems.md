---
name: byox-misc-systems
description: Build a hash table, debugger, load balancer, MQTT broker, or terminal
---
GOAL: pick one and build it completely — correctness before optimisation.

OPTIONS (choose one)
A. Hash table — open addressing + Robin Hood probing; resize at 70% load; O(1) avg.
B. Debugger — ptrace(PTRACE_ATTACH); set software breakpoint (0xCC); single-step; disassemble.
C. Load balancer — health checks (TCP/HTTP); round-robin + least-connections + consistent hash.
D. MQTT broker — pub/sub topics (wildcard # and +); QoS 0 and 1; retain flag; LWT.
E. Terminal emulator — VT100 escape sequences; PTY (openpty); handle resize (SIGWINCH).

PHASES (hash table as example)
1. Array of (key, value, probe_distance) slots; hash function (FNV-1a or xxHash).
2. Insert: probe until empty or same key; Robin Hood: steal slot if dist[new] > dist[existing].
3. Lookup: probe until empty or key match; delete with tombstone or backward shift.
4. Resize at 70% load: allocate 2× array, re-insert all live entries.
5. Benchmark vs std::unordered_map; measure probe length distribution.

VERIFY (hash table): 1M insert + lookup; 0 missing keys; average probe length < 2.
