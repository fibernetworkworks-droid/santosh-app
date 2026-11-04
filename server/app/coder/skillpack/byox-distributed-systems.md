---
name: byox-distributed-systems
description: Build distributed consensus (Raft), queues or key-value stores
---
GOAL: a 3-node cluster that stays consistent when one node crashes.

PHASES
1. Single-node log store: append(entry) + read(index); HTTP API.
2. Leader election: each node has a term + vote; first to get quorum wins.
3. Log replication: leader appends, sends AppendEntries RPCs, followers commit.
4. Client read/write quorum; leader redirect on wrong node.
5. Fault injection: kill followers one by one; verify no data loss on rejoin.

CORE CONCEPTS
- Raft safety: a leader is elected only if it has the most up-to-date log.
- Heartbeat: leader sends empty AppendEntries every 150 ms; follower resets timer.
- Two-phase commit for multi-row transactions across nodes.

VERIFY: write 1000 entries; kill leader; new leader elected; all entries readable.
