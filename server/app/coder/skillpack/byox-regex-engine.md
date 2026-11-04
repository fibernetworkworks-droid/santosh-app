---
name: byox-regex-engine
description: Build a regex engine: NFA via Thompson construction, O(n*m) match
---
GOAL: a regex engine that matches . * + ? [] ^ $ | () without catastrophic backtracking.

PHASES
1. Match fixed strings and . (any char) via linear scan.
2. Add * and +: backtracking engine (recursive).
3. Character classes [a-z], anchors ^ $, alternation |.
4. Grouping () and backreferences.
5. Thompson NFA construction; simulate NFA with epsilon-closure; O(n*m).

CORE CONCEPTS
- NFA states: literal, split (fork), match; Thompson builds NFA fragments bottom-up.
- Epsilon-closure: set of NFA states reachable via ε-transitions from a set S.
- Subset construction: convert NFA to DFA for O(n) matching at cost of O(2^m) states.

VERIFY: `.*foo.*` matches in O(n) on a 1 MB string; no catastrophic backtracking.
